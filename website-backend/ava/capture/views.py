#
# Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
#

import datetime
import urllib2
import json
import time
import os
import signal
import re
import logging

from ava.settings import BASE_DIR, DDNS_SERVER, DDNS_KEYFILE

from base64 import b64encode, b64decode

from rest_framework import viewsets

from models import CaptureNode, Camera, CaptureLocation
from serializers import CaptureNodeSerializer, CameraSerializer, CaptureLocationSerializer

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from common.views import JSONResponse
from common.uuid_utils import uuid_node_base36

from django.utils import timezone
from django.http import HttpResponse
from django.views.decorators.cache import never_cache
from django.db.models import Count

from rest_framework import permissions

from archive.models import Project as ArchiveProject
from archive.models import Session as ArchiveSession
from archive.models import Shot as ArchiveShot
from archive.models import Take as ArchiveTake
from archive.models import Camera as ArchiveCamera

from jobs.models import FarmJob, FarmNode

from multiprocessing.pool import ThreadPool

from raven.contrib.django.raven_compat.models import client

g_pool = ThreadPool(32)
g_logger = logging.getLogger('dev')

DEFAULT_NODE_HTTP_TIMEOUT = 5

class LocationsViewSet(viewsets.ModelViewSet):
    queryset = CaptureLocation.objects.all().order_by('name')
    serializer_class = CaptureLocationSerializer


def has_write_access_location_id(request, location_id):
    return request.user.access_rights.filter(id=location_id, locationaccess__write_access=True).count()>0

def has_write_access_node(request, node):
    return has_write_access_location_id(request, node.location.id)

def create_session_shot(loc, session_id, shot_name):

    # When a new take begins, create new entries in the database for the session and shot, if necessary
    changed = False

    # Clean wierd characters
    shot_name = re.sub('[^a-zA-Z0-9_-]', '', shot_name)

    # We are capturing on a specific session
    if session_id is not None and not loc.cur_session == session_id:
        loc.cur_session = ArchiveSession.objects.get(pk=session_id)
        changed = True

    if (not loc.cur_shot) or (not loc.cur_shot.name == shot_name):
        if not shot_name or shot_name=='-new-': # if shot is unnamed, make up a name from the index
            shot_name = "Shot_%03d"%loc.cur_session.shots.count()
        shot = ArchiveShot(name=shot_name, session=loc.cur_session)
        shot.save()
        loc.cur_shot = shot
        changed = True

    if changed:
        loc.save()

def register_new_take(loc, summary, is_burst, is_scan):
    # Record information about this take in the database
    # Session and Shot should already be created and referenced in cur_session and cur_shot
    if loc.cur_project:
        if not loc.cur_session or not loc.cur_shot:
            print 'ERROR> Session and Shot should be created'
            return

        # Create Take
        take = ArchiveTake(name='Take_%04d'%loc.cur_shot.next_take, shot=loc.cur_shot, sequence=loc.cur_shot.next_take, is_burst=is_burst, is_scan_burst=is_scan)
        take.save()

        # Add cameras to take
        for node in summary['nodes']:
            if 'summary' in node:
                if 'cameras' in node['summary']:

                    # Locate capture node and cameras
                    db_capture_nodes = CaptureNode.objects.filter(location=loc, machine_name=node['machine_name'])

                    cam_index = 0
                    for cam in node['summary']['cameras']:

                        unique_id = cam['camera']['unique_id']

                        # clash (takeids are not unique across machines)
                        if 'jpeg_thumbnail' in cam:
                            filename = '%08d_%03d_%s_%s.jpg' % (take.id, cam_index, unique_id, uuid_node_base36())
                            filepath = os.path.join(BASE_DIR, 'static', 'thumb', filename)
                            try:
                                base64_thumbnail = b64decode(cam['jpeg_thumbnail']+'='*10)
                                with open(filepath, 'wb') as f:
                                    f.write(base64_thumbnail)
                            except Exception as e:
                                client.captureException()
                                print e

                            cam['thumb_filename'] = filename

                        all_files = []
                        if 'recorder' in cam:
                            all_files.extend(cam['recorder']['filenames'])
                        if 'meta' in cam:
                            all_files.append(cam['meta']['meta_filename'])
                        if 'audio' in cam:
                            all_files.append(cam['audio']['filename'])

                        # Find associated camera in db
                        db_cam = Camera.objects.filter(node__location=loc, node__machine_name=node['machine_name'], unique_id=unique_id)[0]

                        if 'recorder' in cam and 'meta' in cam:

                            # New extended camar parameters
                            exposure = 0.0
                            if 'camera_params' in cam:
                                exposure = cam['camera_params']['exposure']/1000.0 if 'exposure' in cam['camera_params'] else 0.0

                            camera = ArchiveCamera(
                                take=take,
                                unique_id=unique_id,
                                machine_name=node['machine_name'],
                                model=cam['camera']['model'],
                                version=cam['camera']['version'],
                                using_sync=cam['camera']['using_hardware_sync'],
                                folder=cam['recorder']['filenames'][0],
                                thumbnail_filename=filename,
                                width=cam['camera']['width'],
                                height=cam['camera']['height'],
                                bitdepth=cam['meta']['bitdepth'],
                                exposure_ms=exposure,
                                frame_count=cam['meta']['frame_count'],
                                dropped_frames=cam['meta']['missing_frames'],
                                total_size=cam['recorder']['total_size'],
                                duration=cam['meta']['duration'],
                                framerate=cam['camera']['framerate'],
                                rotation=db_cam.rotation,
                                all_files=';'.join(all_files)
                            )
                            camera.save()

                        elif 'audio' in cam:

                            camera = ArchiveCamera(
                                take=take,
                                unique_id=unique_id,
                                machine_name=node['machine_name'],
                                model=cam['camera']['model'],
                                version=cam['camera']['version'],
                                using_sync=False,
                                folder=cam['audio']['filename'][0],
                                thumbnail_filename=None,
                                width=0,
                                height=0,
                                bitdepth=cam['audio']['bits_per_sample'],
                                frame_count=cam['audio']['recorded_samples'],
                                dropped_frames=0,
                                total_size=0,
                                duration=cam['audio']['duration'],
                                framerate=cam['audio']['sample_rate'],
                                rotation=0,
                                all_files=';'.join(all_files)
                            )
                            camera.save()

                        cam_index = cam_index + 1

        summary['project_name'] = loc.cur_project.name
        summary['session_name'] = loc.cur_session.name
        summary['shot_name'] = loc.cur_shot.name
        summary['take_index'] = take.sequence
        summary['take_id'] = take.id

        loc.cur_shot.increment_take()
        loc.save()

@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def post_toggle_using_sync(request):
    if request.method == 'POST':
        j = json.loads(request.body)
        if 'camera_id' in j:
            camera = Camera.objects.get(pk=j['camera_id'])
            if camera:

                if not has_write_access_node(request, camera.node):
                    return HttpResponse(status=403)

                camera.using_sync = not camera.using_sync
                camera.save()

                # Send new option to node
                return_msgs = []
                options = {
                    "camera_params": [{
                        "unique_id": camera.unique_id,
                        "using_sync": camera.using_sync
                    }]
                    }            
                apply_options_on_node((camera.node, json.dumps(options), return_msgs))
                
                return HttpResponse()

@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def post_close_node(request):
    if request.method == 'POST':
        j = json.loads(request.body)
        if 'node_id' in j:
            node = CaptureNode.objects.get(pk=j['node_id'])
            if node:
                print node
                url = 'http://%s:8080/close_node' % (node.ip_address)

                try:
                    urllib2.urlopen(url, data="", timeout=DEFAULT_NODE_HTTP_TIMEOUT).read()
                except Exception as e:
                    client.captureException()
                    g_logger.error('%s: %s' % (url, e))                                   
                
    return HttpResponse()

@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def post_set_camera_rotation(request):
    if request.method == 'POST':
        j = json.loads(request.body)
        if 'camera_id' in j and 'angle' in j:

            cam = Camera.objects.get(pk=j['camera_id'])

            if not has_write_access_node(request, cam.node):
                return HttpResponse(status=403)

            cam.rotation = j['angle']
            cam.save()

            # Send new option to node
            return_msgs = []
            options = {
                "camera_params": [{
                    "unique_id": cam.unique_id,
                    "image_rotation": cam.rotation
                }]
                }            
            apply_options_on_node((cam.node, json.dumps(options), return_msgs))

            return HttpResponse()

@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def post_toggle_capturing(request):
    if request.method == 'POST':
        j = json.loads(request.body)
        if 'camera_id' in j:
            cam = Camera.objects.get(pk=j['camera_id'])
            if cam:

                if not has_write_access_node(request, cam.node):
                    return HttpResponse(status=403)

                url = 'http://%s:8080/toggle_capturing/%s/' % (cam.node.ip_address, cam.unique_id)

                try:
                    urllib2.urlopen(url, data="", timeout=DEFAULT_NODE_HTTP_TIMEOUT).read()
                except Exception as e:
                    client.captureException()
                    g_logger.error('%s: %s' % (url, e))                    

                return HttpResponse()

            return JSONResponse({'message':'Camera %d not found' % j['camera_id']}, status=404)

    return HttpResponse(status=500)

def parallel_all_prepare_multi1(node):
    try:

        # Prepare a list of flags for cameras in this node
        params = {
            'cameras': [{'uniqueid': cam.unique_id, 'rotation': cam.rotation} for cam in node.cameras.all()]
        }
        
        serialized_data = urllib2.urlopen('http://%s:8080/all_prepare_multi1' % node.ip_address, data=json.dumps(params), timeout=20).read()
    except Exception as e:
        client.captureException()
        g_logger.error('parallel_all_prepare_multi1 %s: %s' % (node.machine_name, e))

    # TODO Check result from every node, otherwise, cancel the recording

def parallel_all_prepare_multi2(node):
    try:
        serialized_data = urllib2.urlopen('http://%s:8080/all_prepare_multi2' % node.ip_address, data="", timeout=DEFAULT_NODE_HTTP_TIMEOUT).read()
    except Exception as e:
        client.captureException()
        g_logger.error('parallel_all_prepare_multi2 %s: %s' % (node.machine_name, e))

    # TODO Check result from every node, otherwise, cancel the recording

def parallel_all_start_multi(node):
    try:
        serialized_data = urllib2.urlopen('http://%s:8080/all_start_multi' % node.ip_address, data="", timeout=DEFAULT_NODE_HTTP_TIMEOUT).read()
    except Exception as e:
        client.captureException()
        g_logger.error('parallel_all_start_multi %s: %s' % (node.machine_name, e))

    # TODO Check result from every node, otherwise, cancel the recording

@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def post_start_recording(request):
    if request.method == 'POST':
        j = json.loads(request.body)
        if 'location' in j:
            location_id = j['location']

            if not has_write_access_location_id(request, location_id):
                return HttpResponse(status=403)

            loc = CaptureLocation.objects.get(pk=location_id)

            session_id = j['session_id'] if 'session_id' in j else None
            shot_name = j['shot'] if 'shot' in j else None
            create_session_shot(loc, session_id, shot_name)

            nodes = CaptureNode.objects.filter(location__id=location_id, online=True)

            # Prepare Multi Image Capture
            g_pool.map(parallel_all_prepare_multi1, nodes)
            g_pool.map(parallel_all_prepare_multi2, nodes)

            # Start Multi Image Capture
            g_pool.map(parallel_all_start_multi, nodes)

            return HttpResponse()

def parallel_stop_sync(node):
    try:
        serialized_data = urllib2.urlopen('http://%s:8080/all_stop_sync' % node.ip_address, data="", timeout=DEFAULT_NODE_HTTP_TIMEOUT).read()
    except Exception as e:
        client.captureException()
        g_logger.error('parallel_stop_sync %s: %s' % (node.machine_name, e))

def parallel_resume_preview(node):
    try:
        serialized_data = urllib2.urlopen('http://%s:8080/resume_preview' % node.ip_address, data="", timeout=DEFAULT_NODE_HTTP_TIMEOUT).read()
    except Exception as e:
        client.captureException()
        g_logger.error('parallel_resume_preview %s: %s' % (node.machine_name, e))

def parallel_all_stop_recording(p):

    node, summary = p

    try:
        serialized_data = urllib2.urlopen('http://%s:8080/all_stop_recording' % node.ip_address, data="", timeout=DEFAULT_NODE_HTTP_TIMEOUT).read()

        j = json.loads(serialized_data)
        if 'summary' in j:
            node_summary = {}
            node_summary['machine_name'] = node.machine_name
            node_summary['ip_address'] = node.ip_address
            node_summary['summary'] = j['summary']
            summary.append(node_summary)              

    except Exception as e:
        client.captureException()
        g_logger.error('parallel_all_stop_recording %s: %s' % (node.machine_name, e))

def parallel_send_message(p):

    node, msg = p

    try:
        serialized_data = urllib2.urlopen('http://%s:8080/message' % node.ip_address, data=msg, timeout=DEFAULT_NODE_HTTP_TIMEOUT).read()

    except Exception as e:
        client.captureException()
        g_logger.error('parallel_send_message %s: %s' % (node.machine_name, e))

def add_rotation_info_to_cameras(summary):
    # Add rotation flag to all cameras (this info is in th DB, and does not come from the nodes)
    for node_summary in summary['nodes']:
        for camera_summary in node_summary['summary']['cameras']:
            try:
                camera_summary['rotation'] = Camera.objects.filter(unique_id=camera_summary['camera']['unique_id'], node__machine_name=node_summary['machine_name'])[0].rotation
            except Exception as e:
                client.captureException()
                g_logger.error('Could not get rotation flag : %s' % (e))
    
@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def post_message(request):
    if request.method == 'POST':
        j = json.loads(request.body)
        if 'location_id' in j and 'message' in j:
            location_id = int(j['location_id'])
            message = j['message']

            if not has_write_access_location_id(request, location_id):
                return HttpResponse(status=403) 

            # Send generic message to all nodes
            nodes = CaptureNode.objects.filter(location__id=location_id, online=True)
            g_pool.map(parallel_send_message, [(n,message) for n in nodes])

            return HttpResponse(status=200)     
    
    return HttpResponse(status=500)     

@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def post_stop_recording(request):
    if request.method == 'POST':
        j = json.loads(request.body)
        if 'location' in j:
            location_id = j['location']

            if not has_write_access_location_id(request, location_id):
                return HttpResponse(status=403) 

            summary = {}
            summary['result'] = 'OK'
            summary['nodes'] = []

            loc = CaptureLocation.objects.get(pk=location_id)
            nodes = CaptureNode.objects.filter(location__id=location_id, online=True)

            # Pause Sync all nodes
            g_pool.map(parallel_stop_sync, nodes)

            # Delay for all cameras to catch up for the last frame being transfered from the camera
            time.sleep(0.5)

            # Stop Recording All Nodes
            g_pool.map(parallel_all_stop_recording, [(n,summary['nodes']) for n in nodes])

            # Resume sync for preview on all nodes
            g_pool.map(parallel_resume_preview, nodes)

            # Add rotation flag to all cameras (this info is in th DB, and does not come from the nodes)
            add_rotation_info_to_cameras(summary)

            # Store capture in archive
            register_new_take(loc, summary, is_burst=False, is_scan=False)

            return JSONResponse(summary)

def parallel_all_prepare_single(t):
    try:
        node,burst_length = t

        # Prepare a list of flags for cameras in this node
        params = {
            'cameras': [{'uniqueid': cam.unique_id, 'rotation': cam.rotation} for cam in node.cameras.all()]
        }

        serialized_data = urllib2.urlopen('http://%s:8080/all_prepare_single/%d' % (node.ip_address, burst_length), data=json.dumps(params), timeout=30).read()
    except Exception as e:
        client.captureException()
        g_logger.error('parallel_all_prepare_single %s: %s' % (node.machine_name, e))

    # TODO Check that we got a result from all computers, otherwise, cancel this recording and set error
    # TODO Send a cancel to all nodes?

def parallel_all_prepare_single2(node):
    try:
        serialized_data = urllib2.urlopen('http://%s:8080/all_prepare_single2' % node.ip_address, data="", timeout=DEFAULT_NODE_HTTP_TIMEOUT).read()
    except Exception as e:
        client.captureException()
        g_logger.error('parallel_all_prepare_single2 %s: %s' % (node.machine_name, e))

    # TODO Check result from every node, otherwise, cancel the recording

def parallel_all_start_single(node):
    try:
        serialized_data = urllib2.urlopen('http://%s:8080/all_start_single' % node.ip_address, data="", timeout=DEFAULT_NODE_HTTP_TIMEOUT).read()
    except Exception as e:
        client.captureException()
        g_logger.error('parallel_all_start_single %s: %s' % (node.machine_name, e))

    # TODO If we did not get a reply from all computers, continue, but mark this recording as bad

def parallel_all_finalize_single(p):

    node, summary = p

    try:
        serialized_data = urllib2.urlopen('http://%s:8080/all_finalize_single' % node.ip_address, data="", timeout=20).read()

        j = json.loads(serialized_data)
        if 'summary' in j:
            node_summary = {}
            node_summary['machine_name'] = node.machine_name
            node_summary['ip_address'] = node.ip_address
            node_summary['summary'] = j['summary']
            summary.append(node_summary)

    except Exception as e:
        client.captureException()
        g_logger.error('parallel_all_finalize_single %s: %s' % (node.machine_name, e))

@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def post_record_single_image(request):
    if request.method == 'POST':
        j = json.loads(request.body)
        if 'location' in j:
            location_id = j['location']
            burst_length = int(j['burst_length']) if 'burst_length' in j else 1
            burst_is_scan = bool(j['burst_is_scan']) if 'burst_is_scan'in j else False

            if not has_write_access_location_id(request, location_id):
                return HttpResponse(status=403) 

            nodes = CaptureNode.objects.filter(location__id=location_id, online=True)

            summary = {}
            summary['result'] = 'OK'
            summary['nodes'] = []
            summary['timings'] = []

            timings_start = time.time()

            # Prepare Single Image Capture
            g_pool.map(parallel_all_prepare_single, zip(nodes, [burst_length]*len(nodes)))

            summary['timings'].append( ('parallel_all_prepare_single', time.time() - timings_start) )
            timings_start = time.time()

            g_pool.map(parallel_all_prepare_single2, nodes)

            summary['timings'].append( ('parallel_all_prepare_single2', time.time() - timings_start) )
            timings_start = time.time()

            # Start Single Image Capture
            g_pool.map(parallel_all_start_single, nodes)

            summary['timings'].append( ('parallel_all_start_single', time.time() - timings_start) )
            timings_start = time.time()

            # Finalize Single Image Capture
            g_pool.map(parallel_all_finalize_single, [(n,summary['nodes']) for n in nodes])

            summary['timings'].append( ('parallel_all_finalize_single', time.time() - timings_start) )
            timings_start = time.time()

            # Add rotation flag to all cameras (this info is in th DB, and does not come from the nodes)
            add_rotation_info_to_cameras(summary)

            summary['timings'].append( ('add_rotation_info_to_cameras', time.time() - timings_start) )
            timings_start = time.time()

            # Store in DB
            loc = CaptureLocation.objects.get(pk=location_id)

            # Create shot
            session_id = j['session_id'] if 'session_id' in j else None
            shot_name = j['shot'] if 'shot' in j else None
            create_session_shot(loc, session_id, shot_name)

            summary['timings'].append( ('create_session', time.time() - timings_start) )
            timings_start = time.time()

            # Store capture in archive
            register_new_take(loc, summary, is_burst=burst_length>1, is_scan=burst_is_scan and burst_length>1)

            summary['timings'].append( ('register_new_take', time.time() - timings_start) )
            timings_start = time.time()

            #print summary['timings']

            return JSONResponse(summary)

@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def post_new_session(request, location_id="0"):
    if request.method == 'POST':
        location_id = int(location_id)

        # Check user permission
        locs = request.user.access_rights.filter(id=location_id, locationaccess__write_access=True)
        if not locs:
            return HttpResponse(status=403)
        loc = locs[0]

        # Get parameters from request
        j = json.loads(request.body)
        if not 'name' in j:
            return HttpResponse(status=500)
        session_name = j['name']

        # Clean weird characters
        session_name = re.sub('[^a-zA-Z0-9_-]', '', session_name)

        if not session_name:
            return HttpResponse(status=500)

        project = loc.cur_project

        # Create or select project for this new session
        if 'project_id' in j:
            # Add session to existing project
            project = ArchiveProject.objects.get(pk=int(j['project_id']))
        if 'project_name' in j:
            # Create new project
            project = ArchiveProject(name=j['project_name'])
            project.save()

        # Is the session name unique?
        i = 0
        while ArchiveSession.objects.filter(name=session_name, project=project).count()>0:
            session_name = '%s_%03d' % (j['name'], i)
            i = i + 1

        # Create New Session
        session = ArchiveSession(name=session_name, project=project)
        session.save()

        # Create New Shot
        shot = ArchiveShot(name='Shot_000', session=session)
        shot.save()

        # Save Location
        loc = CaptureLocation.objects.get(pk=location_id)
        loc.cur_project = project
        loc.cur_session = session
        loc.cur_shot = shot
        loc.save()

        # Return result
        result = {}
        result['session_name'] = session.name
        result['session_id'] = session.id
        result['shot_name'] = shot.name
        result['shot_id'] = shot.id
        result['project_name'] = session.project.name
        result['project_id'] = session.project.id

        return JSONResponse(result)

def apply_set_roi(p):

    node, body = p

    try:
        result = urllib2.urlopen('http://%s:8080/camera/%s/%s' % (node.ip_address, 'all', 'roi'), data=body, timeout=DEFAULT_NODE_HTTP_TIMEOUT).read()
    except Exception as e:
        client.captureException()
        g_logger.error('post_set_roi %s: %s' % (node.machine_name, e))


@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def post_set_roi(request):
    if request.method == 'POST':

        j = json.loads(request.body)
        camera_id = int(j['camera_id'])
        location_id = int(j['loc_id'])

        if camera_id>0:

            # Set ROI on one single camera

            camera = Camera.objects.get(pk=camera_id)
            location_id = camera.node.location.id
            write_access = request.user.access_rights.filter(id=location_id, locationaccess__write_access=True).count()>0
            if not write_access:
                return HttpResponse(status=403)

            # TODO Update ROI in DB for camera

            try:
                result = urllib2.urlopen('http://%s:8080/camera/%s/%s' % (camera.node.ip_address, camera.unique_id, 'roi'), data=request.body, timeout=DEFAULT_NODE_HTTP_TIMEOUT).read()
            except Exception as e:
                client.captureException()
                g_logger.error('post_set_roi %s: %s' % (camera.node.machine_name, e))

        elif location_id>0:                      

            # Set ROI on all cameras of this location

            write_access = request.user.access_rights.filter(id=location_id, locationaccess__write_access=True).count()>0
            if not write_access:
                return HttpResponse(status=403)

            nodes = CaptureNode.objects.filter(location=location_id, online=True)
            g_pool.map(apply_set_roi, [(n, request.body) for n in nodes])

        return HttpResponse(status=200)

@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def post_reset_roi(request):
    if request.method == 'POST':

        j = json.loads(request.body)
        camera_id = int(j['camera_id'])
        location_id = int(j['loc_id'])

        if camera_id>0:

            # Reset ROI on one single camera

            camera = Camera.objects.get(pk=camera_id)
            location_id = camera.node.location.id
            write_access = request.user.access_rights.filter(id=location_id, locationaccess__write_access=True).count()>0
            if not write_access:
                return HttpResponse(status=403)

            # TODO Update ROI in DB for camera

            try:
                result = urllib2.urlopen('http://%s:8080/camera/%s/%s' % (camera.node.ip_address, camera.unique_id, 'roi'), data="", timeout=DEFAULT_NODE_HTTP_TIMEOUT).read()
            except Exception as e:
                client.captureException()
                g_logger.error('post_reset_roi %s: %s' % (camera.node.machine_name, e))

        elif location_id>0:                      

            # Reset ROI on all cameras of this location

            write_access = request.user.access_rights.filter(id=location_id, locationaccess__write_access=True).count()>0
            if not write_access:
                return HttpResponse(status=403)

            nodes = CaptureNode.objects.filter(location=location_id, online=True)
            g_pool.map(apply_set_roi, [(n, "") for n in nodes])

        return HttpResponse(status=200)

def unique_shot_name(shot_name, session):

    shot_name = re.sub('[^a-zA-Z0-9_-]', '', shot_name)

    if not shot_name:
        shot_name = 'Shot'

    i = 0
    shot_name_prefix = shot_name + '_'

    m = re.match(r'(.+?)(\d+)$',shot_name)
    if m:
        shot_name_prefix = m.group(1)
        i = int(m.group(2))

    while ArchiveShot.objects.filter(name=shot_name, session=session).count()>0:
        shot_name = '%s%03d' % (shot_name_prefix, i)
        i = i + 1

    return shot_name 

@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def post_new_shot(request, location_id="0"):
    if request.method == 'POST':
        location_id = int(location_id)

        # security check
        loc = request.user.access_rights.filter(id=location_id, locationaccess__write_access=True)
        if not loc:
            return HttpResponse(status=403)
        
        # read option from request
        j = json.loads(request.body)
        if not 'name' in j:
            return HttpResponse(status=500)
        shot_name = j['name']

        # Check if shot name is unique, otherwise, increment it
        shot_name = unique_shot_name(shot_name, loc[0].cur_session)

        # Create new shot
        shot = ArchiveShot(name=shot_name, session=loc[0].cur_session)
        shot.save()
        loc[0].cur_shot = shot
        loc[0].save()

        return JSONResponse({'id':shot.id, 'name':shot.name})

@api_view(['GET', 'POST'])
@permission_classes((IsAuthenticated,))
def camera_parameter(request, location_id="0"):

    location_id = int(location_id)

    if request.method == 'POST':

        location_id = int(location_id)

        g = request.user.access_rights.filter(id=location_id, locationaccess__write_access=True)
        if not g:
            return HttpResponse(status=403)

        j = json.loads(request.body)

        camera = Camera.objects.get(pk=j['cam_id'])    
        if not camera:
            return HttpResponse(status=404)

        # Some parameters are saved in the DB
        # TODO Generalize DB for parameters
        if j['parameter_name'] == 'exposure':
            camera.exposure = j['value']
            camera.save()
        if j['parameter_name'] == 'lens_aperture_value':
            camera.lens_aperture = j['value']
            camera.save()
        if j['parameter_name'] == 'gain':
            camera.gain = j['value']
            camera.save()

        # Update Node with new value
        try:
            result = urllib2.urlopen('http://%s:8080/camera/%s/%s/%s' % (camera.node.ip_address, camera.unique_id, j['parameter_name'], j['value']), data="", timeout=DEFAULT_NODE_HTTP_TIMEOUT).read()
            return JSONResponse(result)
        except Exception as e:
            client.captureException()
            g_logger.error('camera_parameter %s: %s' % (camera.node.machine_name, e))                    

def apply_options_on_node(p):

    node, body, msgs = p

    try:
        serialized_data = urllib2.urlopen('http://%s:8080/options/' % (node.ip_address), data=body, timeout=DEFAULT_NODE_HTTP_TIMEOUT).read()
        msgs.append('Options set on %s\n' % node.ip_address)
    except Exception as e:
        client.captureException()
        msgs.append('Error setting option on %s\n' % node.ip_address)
        g_logger.error('location_config %s: %s' % (node.machine_name, e))                    

@api_view(['GET', 'POST'])
@permission_classes((IsAuthenticated,))
def location_config(request, location_id="0"):

    location_id = int(location_id)

    if request.method == 'GET':

        loc = CaptureLocation.objects.filter(id=location_id, read_access_all=True) # Try with locations readable by all
        if not loc:
            loc = request.user.access_rights.filter(id=location_id, locationaccess__read_access=True) # Filter by access rights
        if loc:
            result = {}
            result['hardware_sync_frequency'] = loc[0].hardware_sync_frequency
            result['pulse_duration'] = loc[0].pulse_duration
            result['external_sync'] = loc[0].external_sync
            return JSONResponse(result)

        return HttpResponse(status=403)

    if request.method == 'POST':

        msgs = []

        location_id = int(location_id)
        g = request.user.access_rights.filter(id=location_id, locationaccess__write_access=True)
        if g:
            j = json.loads(request.body)

            # Store location options in DB       
            if 'pulse_duration' in j:
                g[0].pulse_duration = int(j['pulse_duration'])
            if 'frequency' in j:
                g[0].hardware_sync_frequency = int(j['frequency'])
            if 'external_sync' in j:
                g[0].external_sync = bool(j['external_sync'])
            if 'display_focus_peak' in j:
                g[0].display_focus_peak = bool(j['display_focus_peak'])
            if 'display_overexposed' in j:
                g[0].display_overexposed = bool(j['display_overexposed'])
            if 'display_histogram' in j:
                g[0].display_histogram = bool(j['display_histogram'])
            if 'bitdepth_avi' in j:
                g[0].bitdepth_avi = int(j['bitdepth_avi'])
            if 'bitdepth_single' in j:
                g[0].bitdepth_single = int(j['bitdepth_single'])
            if 'image_format' in j:
                g[0].image_format = j['image_format']
            if 'wb_R' in j:
                g[0].wb_R = float(j['wb_R'])
            if 'wb_G' in j:
                g[0].wb_G = float(j['wb_G'])
            if 'wb_B' in j:
                g[0].wb_B = float(j['wb_B'])

            # set options on all nodes
            nodes = CaptureNode.objects.filter(online=True, location__id=location_id)
            g_pool.map(apply_options_on_node, [(n, request.body, msgs) for n in nodes])

            g[0].save()

        return JSONResponse({'messages':msgs})

@api_view(['GET'])
@permission_classes((IsAuthenticated,))
def get_locations(request):

    # Use this opportunity to update any timed-out location
    CaptureNode.objects.filter(online=True, last_seen__lt=timezone.now() - datetime.timedelta(seconds=90)).update(online=False)

    result = {}
    result['locations'] = []

    for loc in CaptureLocation.objects.all():
        read_access = loc.read_access_all or loc.users.filter(id=request.user.id, locationaccess__read_access=True).count()>0
        result['locations'].append({
            'name':loc.name, 
            'id':loc.id, 
            'active':Camera.objects.filter(node__online=True, node__last_seen__gt=timezone.now() - datetime.timedelta(seconds=90), node__location=loc.id).count(),
            'access':read_access})
    unknown_count = Camera.objects.filter(node__online=True, node__last_seen__gt=timezone.now() - datetime.timedelta(seconds=90), node__location__isnull=True).count()
    if unknown_count>0:
        result['locations'].append({
            'name':'Unknown', 
            'id':0, 
            'active':unknown_count, 
            'access':True})

    # Add extra statistics about the whole system
    result['nb_running_jobs'] = FarmJob.objects.filter(status='running').count()
    result['nb_queued_jobs'] = FarmJob.objects.filter(status='ready').count()
    result['nb_farmnodes_active'] = FarmNode.objects.filter(status='accepting').filter(last_seen__gt=timezone.now() - datetime.timedelta(seconds=90)).count()

    return JSONResponse(result)

@api_view(['GET'])
@permission_classes((IsAuthenticated,))
def location(request, location_id="0"):

    location_id = int(location_id)

    if not location_id:
        return HttpResponse(status=404)

    loc = CaptureLocation.objects.get(pk=location_id)
    if loc:
        return HttpResponse(loc.name)

    return HttpResponse(status=404)

def fetch_camera_details_from_node(n):

    try:
        # Fetch additional data directly from capture node
        serialized_data = urllib2.urlopen('http://%s:8080/cameras' % n['ip_address'], timeout=DEFAULT_NODE_HTTP_TIMEOUT).read()
        #print serialized_data
        n['camera_details'] = json.loads(serialized_data)

    except Exception as e:
        client.captureException()
        g_logger.error('fetch_camera_details_from_node %s: %s' % (n['ip_address'], e))

@api_view(['GET'])
@permission_classes((IsAuthenticated,))
def cameras_detailed(request, location_id="0"):

    # Get details from all cameras, including details obtained from the node itself (includes small thumbnail)

    location_id = int(location_id)

    # Check permission for this location_id
    read_access = True
    write_access = False
    if not location_id:
        return HttpResponse(status=500) 
    loc = CaptureLocation.objects.get(pk=location_id)
    read_access = loc.read_access_all or request.user.access_rights.filter(id=location_id, locationaccess__read_access=True).count()>0
    if not read_access:
        return HttpResponse(status=403) 
    write_access = request.user.access_rights.filter(id=location_id, locationaccess__write_access=True).count()>0

    # filter nodes by location
    if location_id>0:
        nodes = CaptureNode.objects.filter(location=location_id, online=True, last_seen__gt=timezone.now() - datetime.timedelta(seconds=90)).order_by('machine_name')
    else:
        nodes = CaptureNode.objects.filter(location__isnull=True, online=True, last_seen__gt=timezone.now() - datetime.timedelta(seconds=90)).order_by('machine_name')

    serializer = CaptureNodeSerializer(nodes, many=True, context={'request':request})
    nodes = serializer.data

    result = {}

    # # Check if the current session is from a different day, in that case we always start a new session
    # if loc.cur_session:
    #     current_tz = timezone.get_current_timezone()
    #     if not timezone.now().date() == loc.cur_session.start_time.date():
    #         print 'Current Session is from a different date'
    #         loc.cur_session = None
    #         loc.cur_shot = None
    #         loc.save()

    # Add location information
    result['read_access'] = read_access
    result['write_access'] = write_access
    if not loc.cur_project:
        # Create default project for this location
        prj = ArchiveProject(name='Default_'+loc.name)
        prj.save()
        loc.cur_project = prj
        loc.save()
    if loc.cur_project:
        result['project_id'] = loc.cur_project.id
        result['project_name'] = loc.cur_project.name
    if loc.cur_session:
        result['session_id'] = loc.cur_session.id
        result['session_name'] = loc.cur_session.name
    else:
        result['session_id'] = None
        result['session_name'] = "-new-"
    if loc.cur_shot:
        result['shot_id'] = loc.cur_shot.id
        result['shot_name'] = loc.cur_shot.name
        result['next_take'] = loc.cur_shot.next_take
    else:
        result['shot_id'] = None
        result['shot_name'] = "-new-"
        result['next_take'] = 1

    result['location'] = {}
    result['location']['show_focus_peak'] = loc.display_focus_peak
    result['location']['show_overexposed'] = loc.display_overexposed
    result['location']['show_histogram'] = loc.display_histogram
    result['location']['bitdepth_avi'] = loc.bitdepth_avi
    result['location']['bitdepth_single'] = loc.bitdepth_single
    result['location']['image_format'] = loc.image_format
    result['location']['wb_R'] = loc.wb_R
    result['location']['wb_G'] = loc.wb_G
    result['location']['wb_B'] = loc.wb_B    
    result['location']['hardware_sync_frequency'] = loc.hardware_sync_frequency  
    result['location']['pulse_duration'] = loc.pulse_duration
    result['location']['external_sync'] = loc.external_sync

    result['nodes'] = nodes

    # Fetch data from each node in parallel
    g_pool.map(fetch_camera_details_from_node, nodes)

    # Find corresponding database id for each camera
    for node in nodes:

        if 'camera_details' in node:

            # get map of database id vs unique_id from the CaptureNodeSerializer
            cam_id_map = {}
            for x in node['cameras']:
                cam_id_map[x['unique_id']] = x
            
            # Add database id to each camera
            for cam in node['camera_details']:
                cam['ip_address'] = node['ip_address']
                cam['machine_name'] = node['machine_name']
                if cam['unique_id'] in cam_id_map:
                    cam['id'] = cam_id_map[cam['unique_id']]['id']
                    cam['rotation'] = cam_id_map[cam['unique_id']]['rotation']

    return JSONResponse(result)

@api_view(['GET'])
@permission_classes((IsAuthenticated,))
def camera_detailed(request, location_id="0", camera_id="0"):

    # Get details of one camera, including large thumbnail

    location_id = int(location_id)
    camera_id = int(camera_id)

    # Check permission for this location_id
    read_access = True
    write_access = False
    if location_id:
        read_access = CaptureLocation.objects.get(pk=location_id).read_access_all or request.user.access_rights.filter(id=location_id, locationaccess__read_access=True).count()>0
        if not read_access:
            return HttpResponse(status=403) 
        write_access = request.user.access_rights.filter(id=location_id, locationaccess__write_access=True).count()>0

    # filter camera by location and id
    cameras = Camera.objects.filter(node__location=location_id, id=camera_id)

    if cameras:

        camera = cameras[0]

        serializer = CameraSerializer(camera, many=False, context={'request':request})
        data = serializer.data

        result = {}
        result['camera'] = data

        # Fetch image data directly from capture node
        try:
            jpeg_data = urllib2.urlopen('http://%s:8080/camera/%s/large_preview' % (camera.node.ip_address, camera.unique_id), timeout=DEFAULT_NODE_HTTP_TIMEOUT).read()
            result['jpeg_full'] = b64encode(jpeg_data)
        except Exception as e:
            g_logger.error('large_preview %s: %s' % (camera.node.machine_name, e))           

        return JSONResponse(result)
    else:
        return HttpResponse(status=404)

@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def node_discover(request):
   
    g_logger.debug('Node Discover %s' % request.data['machine_name'])
   
    # Look for existing machine in the database, with the same name
    nodes = CaptureNode.objects.filter(machine_name=request.data['machine_name'])

    if nodes:
        # Node exists in database, update it
        node = nodes[0]
        ip_has_changed = node.ip_address != request.data['ip_address']
        node.ip_address = request.data['ip_address']
        node.last_seen = timezone.now()
    else:
        # Node does not exist, create it
        node = CaptureNode(ip_address=request.data['ip_address'], machine_name=request.data['machine_name'])
        ip_has_changed = True

    if 'sync_found' in request.data:
        node.sync_found = request.data['sync_found']
    if 'os' in request.data:
        node.os = request.data['os']
    node.online = True
    node.code_version = request.data['code_version'] if 'code_version' in request.data else 0
    node.build_version = request.data['build_version'] if 'build_version' in request.data else ""

    if node.code_version < 1024:
        return JSONResponse({'Result':'avacapture.exe Version Too Old'}, status=426)

    # Update drive info
    if 'drives' in request.data:
        node.drive_info = json.dumps(request.data['drives'])

    # If this is a new node and it does not have a location, add it to LOCAL
    if not node.location:
        try:
            node.location = CaptureLocation.objects.get(name='local')
        except:
            pass

    node.save()

    # If needed, update ava hosts file for DNS
    if ip_has_changed and DDNS_SERVER:
        import tempfile
        import subprocess
        f = tempfile.NamedTemporaryFile(delete=False)
        try:
            print 'Updating Dynamic DNS for all nodes'
            content = 'server ' + DDNS_SERVER + '\n'
            for item in CaptureNode.objects.filter(machine_name__contains='.ava.ea.com'):
                content += ('update add ' + item.machine_name + ' 600 a ' + item.ip_address + '\n')
            content += 'send' + '\n'
            f.write(content)
            f.close()

            # Need to send SIGHUP to dnsmasq
            cmd = ['nsupdate', '-k', DDNS_KEYFILE, f.name]
            subprocess.call(cmd)

        except:
            g_logger.debug('Error updating Dynamic DNS')
        finally:
            os.unlink(f.name)

    # Update list of cameras 
    if 'cameras' in request.data:

        # TODO We should be getting each cameras Model and Version here, to update the DB

        if type(request.data) is dict:
            cam_list = request.data['cameras']
        else:
            cam_list = request.data.getlist('cameras')
        for unique_id in cam_list:            
            # if camera does no exist, create it
            obj = Camera.objects.filter(unique_id=unique_id, node=node)
            if not obj:
                obj = Camera(node=node, unique_id=unique_id)
                obj.save()
        # delete any cameras that are not in the list
        for item in Camera.objects.filter(node=node).exclude(unique_id__in=cam_list):
            item.delete()

    if node.location:
        result = {'Result':'OK', 
            'sync_freq':node.location.hardware_sync_frequency,
            'pulse_duration':node.location.pulse_duration,
            'external_sync':node.location.external_sync,
            'display_focus_peak' : node.location.display_focus_peak,
            'display_overexposed' : node.location.display_overexposed,
            'display_histogram' : node.location.display_histogram,
            'bitdepth_avi' : node.location.bitdepth_avi,
            'bitdepth_single' : node.location.bitdepth_single,
            'image_format' : node.location.image_format,
            'wb_R' : node.location.wb_R,
            'wb_G' : node.location.wb_G,
            'wb_B' : node.location.wb_B,
        }
    else:
        return HttpResponse("Node not registered", status=403)

    if 'request_camera_params' in request.data:
        # client is requesting the current parameters of the cameras
        cameras = Camera.objects.filter(node=node)

        # TODO Generalize DB for parameters
        result['camera_params'] = [dict(unique_id=cam.unique_id, 
            lens_aperture_value=cam.lens_aperture, 
            exposure=cam.exposure, 
            gain=cam.gain,
            using_sync=cam.using_sync,
            image_rotation=cam.rotation) for cam in cameras]

        # TODO Camera roi

    # return JSON data for the current machine
    return JSONResponse(result)

@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def node_shutdown(request):

    g_logger.debug('Node Shutdown %s' % request.data['ip_address'])

    nodes = CaptureNode.objects.filter(ip_address=request.data['ip_address'])

    for node in nodes:
        node.online = False
        node.save()

    return JSONResponse({'Result':'OK'})
