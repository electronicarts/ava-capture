#
# Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
#

import json
import shutil
import os
import glob
import tempfile
import logging

import cv2
import numpy as np

from lightstage import load_cameras_from_file
from lightstage_tools.dcraw import convert_cr2
from lightstage_tools.avi_tools import extract_one_frame_from_avi

from base import BaseJob

def read_meta_txt(filename):
    d = {}
    with open(filename) as f:
        for line in f.readlines():
            if ':' in line:
                pair = line.strip().split(': ')
                if len(pair)==2:
                    d[pair[0]] = pair[1]
            if line=='':
                return d
    return d

def get_ffmpeg_path():
    ffmpeg_exe = os.path.abspath(r'..\bin\ffmpeg\ffmpeg.exe')
    if not os.path.exists(ffmpeg_exe):
        ffmpeg_exe = os.path.abspath(r'bin\ffmpeg\ffmpeg.exe') # To be cleanedup for deployed version, this is a hack
        if not os.path.exists(ffmpeg_exe):
            raise Exception('cannot find ffmpeg.exe at %s' % ffmpeg_exe)
    return ffmpeg_exe

class GenerateThumbnail(BaseJob):

    def __call__(self, parameters, pipe, log):

        params = json.loads(parameters) if parameters else None

        # Child Job, create one thumbnail from an AVI file
        if params and 'txt_file' in params and 'avi_file' in params:
        
            log.info('GenerateThumbnail for %s' % params['avi_file'])   

            ffmpeg_exe = get_ffmpeg_path()

            meta = read_meta_txt(params['txt_file'])
            if 'Framerate' in meta and 'Threads' in meta:

                filename = os.path.split(params['avi_file'])[1]

                fps = int(meta['Framerate']) / int(meta['Threads'])

                if 'start_time' in params and 'end_time' in params:
                    frame_range = (params['start_time']*fps, params['end_time']*fps)
                    output_file = os.path.splitext(params['avi_file'])[0] + ('_preview_%d_%d.mp4' % frame_range)
                    cmd = [ffmpeg_exe, '-ss', str(params['start_time']), '-t', str(params['end_time']-params['start_time']), '-y', '-r %d' % fps, '-i', params['avi_file'], '-vf scale=320:-1 -vcodec libx264 -g 35', output_file]
                else:
                    output_file = os.path.splitext(params['avi_file'])[0] + '_preview.mp4'
                    cmd = [ffmpeg_exe, '-y', '-r %d' % fps, '-i', params['avi_file'], '-vf scale=320:-1 -vcodec libx264 -g 35', output_file]

                pipe.send('Generating video thumbnail')
                self.run_subprocess(' '.join(cmd), log)

                # If this thumbnail is to be associated with a Take
                if 'take_id' in params:

                    with open(output_file, 'rb') as f:
                        files={'file':(('t%08d_'%params['take_id']) + filename, f)}

                        # Upload this thumbnail as the official thumbnail for this take
                        pipe.send('Uploading thumbnail to server')
                        r = self.server_post('/archive/take_video_thumbnail/%d/' % params['take_id'], files=files)

                        if r.status_code != 200:
                            raise Exception('Could not upload thumbnail to server code:%d %s' % (r.status_code, r.text))

                # If this thumbnail is to be associated with a Tracking Asset
                if 'tracking_asset_id' in params:

                    with open(output_file, 'rb') as f:
                        files={'file':(('tr%08d_'%params['tracking_asset_id']) + filename, f)}

                        # Upload this thumbnail as the official thumbnail for this take
                        pipe.send('Uploading thumbnail to server')
                        r = self.server_post('/archive/tracking_asset_thumbnail/%d/' % params['tracking_asset_id'], files=files)

                        if r.status_code != 200:
                            raise Exception('Could not upload thumbnail to server code:%d %s' % (r.status_code, r.text))

        else:

            # Parent Job

            child_to_launch = []

            job_info = self.get_job_info()
            
            # If this Job is associated with a Take
            if 'ext_take_id' in job_info and job_info['ext_take_id']:

                take_id = int(job_info['ext_take_id'])
                take_info = self.get_take_info(take_id)
                take_export_path = take_info['export_path']

                if not take_export_path:
                    raise Exception('Take has to be exported first')
                
                log.info('GenerateThumbnail for Take %s in %s' % (take_id, take_export_path))   

                frontal_camera_uid = take_info['frontal_cam_uid'] if 'frontal_cam_uid' in take_info else None

                # For each AVI file in this Take, launch a new Child Job
                for txt_file in glob.glob(os.path.join(take_export_path,'*.txt')):
                    avi_file = os.path.splitext(txt_file)[0] + '_000.avi'
                    if os.path.exists(avi_file):

                        child_params = {'txt_file':txt_file, 'avi_file':avi_file}

                        if frontal_camera_uid and frontal_camera_uid in avi_file:
                            child_params['take_id'] = take_id

                        child_launch_info = {}
                        child_launch_info['job_class'] = 'jobs.thumbnails.GenerateThumbnail'
                        child_launch_info['params'] = json.dumps(child_params)
                        child_launch_info['req_gpu'] = False

                        child_to_launch.append(child_launch_info)

            # If this Job is associated with a Static Scan Asset
            if 'ext_scan_assets_id' in job_info and job_info['ext_scan_assets_id']:

                scan_asset_id = int(job_info['ext_scan_assets_id'])
                asset_info = self.get_scan_asset_info(scan_asset_id)

                log.info('GenerateThumbnail for Scan Asset %s' % (scan_asset_id))

                # Check if there is a Take associated to this scan asset, if this is the case,
                # we have a few more thumbnails to generate.
                related_take_id = asset_info['take_id']
                if related_take_id:
                    related_take_info = self.get_take_info(int(related_take_id))
                    if related_take_info:
                        frontal_camera_uid = related_take_info['frontal_cam_uid']
                        take_export_path = related_take_info['export_path']
                        if take_export_path:


                            # Get rotation angle from frontal camera
                            rotation = 0
                            for cam in related_take_info['cameras']:
                                if cam['unique_id']==frontal_camera_uid:
                                    rotation = cam['rotation']
                                    break

                            print 'Associated Take : #%d at %s' % (related_take_id, take_export_path)

                            frames = ['take_mixed_w_time','take_pattern_start_time','take_pattern_last_time']
                            for frame in frames:
                                if asset_info[frame]:
                                    img = extract_one_frame_from_avi(take_export_path, frontal_camera_uid, frame_time=asset_info[frame], rotation=rotation)
                                    height, width = img.shape[:2]
                                    img = cv2.resize(img, (512, 512*height/width), interpolation=cv2.INTER_AREA)
                                    if img.dtype==np.uint16:
                                        img = img / 256.0 # need to be in 8 bit range before saving to JPG
                                    jpg_file = os.path.join(take_export_path,'%s_%s.jpg' % (frontal_camera_uid,frame))
                                    cv2.imwrite(jpg_file, img)

                                    # Upload to server
                                    pipe.send('Uploading JPG "%s" thumbnail...' % frame)
                                    with open(jpg_file, 'rb') as f:
                                        files={'file':(os.path.split(jpg_file)[1], f)}
                                        r = self.server_post('/archive/scan_asset_thumbnail/%d/%s' % (scan_asset_id, frame), files=files)
                                        if r.status_code != 200:
                                            raise Exception('Could not upload thumbnail to server code:%d %s' % (r.status_code, r.text))
                
                # Get most frontal camera name from calibration file
                calib_file = asset_info['calib_file']
                cam_group = load_cameras_from_file(calib_file)

                while 1:
                    frontal_cam = cam_group.most_frontal_camera()
                    src_cr2 = os.path.join(asset_info['image_folder'], frontal_cam.label, 'mixed_w.CR2')
                    if not os.path.exists(src_cr2):
                        # Try another frontal camera
                        cam_group.cameras.remove(frontal_cam)
                        if not cam_group.cameras:
                            raise Exception('Could not find a frontal camera that exists on disk')
                    else:
                        break
                
                pipe.send('Copying CR2...')
                tmp_cr2 = tempfile.mktemp(suffix='.cr2')
                shutil.copyfile(src_cr2, tmp_cr2)
                
                pipe.send('Converting CR2 to JPG...')
                tmp_tif = convert_cr2(tmp_cr2, options='-T')

                tmp_jpg = tempfile.mktemp(suffix='.jpg')

                img = cv2.imread(tmp_tif, cv2.IMREAD_UNCHANGED)
                height, width = img.shape[:2]
                img = cv2.resize(img, (512, 512*height/width), interpolation=cv2.INTER_AREA)
                # TODO Color correction?
                cv2.imwrite(tmp_jpg, img)

                pipe.send('Uploading JPG "front" thumbnail...')
                with open(tmp_jpg, 'rb') as f:
                    files={'file':('s%08d_%s.jpg'%(scan_asset_id, frontal_cam), f)}
                    r = self.server_post('/archive/scan_asset_thumbnail/%d/front' % scan_asset_id, files=files)
                    if r.status_code != 200:
                        raise Exception('Could not upload thumbnail to server code:%d %s' % (r.status_code, r.text))

                os.remove(tmp_jpg)
                os.remove(tmp_cr2)
                os.remove(tmp_tif)

            # If this Job is associated with a Static Scan Asset
            if 'ext_tracking_assets_id' in job_info and job_info['ext_tracking_assets_id']:

                tracking_assets_id = int(job_info['ext_tracking_assets_id'])
                asset_info = self.get_tracking_asset_info(tracking_assets_id)

                take_info = asset_info['take']
                take_id = int(take_info['id'])
                take_export_path = take_info['export_path']

                if not take_export_path:
                    raise Exception('Take has to be exported first')
                
                log.info('GenerateThumbnail for Take %s in %s from %s to %s' % (take_id, take_export_path, asset_info['start_time'], asset_info['end_time']))

                frontal_camera_uid = take_info['frontal_cam_uid'] if 'frontal_cam_uid' in take_info else None

                # For each AVI file in this Take, launch a new Child Job
                for txt_file in glob.glob(os.path.join(take_export_path,'*.txt')):
                    avi_file = os.path.splitext(txt_file)[0] + '_000.avi'
                    if os.path.exists(avi_file):

                        child_params = {'txt_file':txt_file, 'avi_file':avi_file, 'start_time':asset_info['start_time'], 'end_time':asset_info['end_time']}

                        if frontal_camera_uid and frontal_camera_uid in avi_file:
                            child_params['tracking_asset_id'] = tracking_assets_id

                        child_launch_info = {}
                        child_launch_info['job_class'] = 'jobs.thumbnails.GenerateThumbnail'
                        child_launch_info['params'] = json.dumps(child_params)
                        child_launch_info['req_gpu'] = False

                        child_to_launch.append(child_launch_info)

                

            if child_to_launch:
                self.yieldToChildren(child_to_launch)

if __name__ == "__main__":

    print 'TEST'

    from test import JobTestFixture

    fixture = JobTestFixture()
    fixture(GenerateThumbnail(), r'{"take_export_path":"C:\\Users\\edanvoye\\Desktop\\video"}')
