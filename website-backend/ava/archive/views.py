#
# Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
#

import json
import os
import logging

import urllib2
import zipfile
import StringIO

from ava.settings import BASE_DIR

from django.shortcuts import render
from django.http import HttpResponse

from models import Project, Session, Take, Camera, StaticScanAsset, TrackingAsset

from common.views import JSONResponse
from common.uuid_utils import uuid_node_base36

from rest_framework import viewsets
from serializers import *

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

from jobs.models import FarmNode, FarmJob
from jobs.views import make_sure_node_exists
from accounts.models import UserData
from capture.models import CaptureNode

from raven.contrib.django.raven_compat.models import client

DEFAULT_NODE_HTTP_TIMEOUT = 5

g_logger = logging.getLogger('dev')

class ProjectsViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.filter(archived=False).order_by('name')
    serializer_class = ProjectSerializer

class ProjectArchiveViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all().order_by('name')
    serializer_class = ProjectArchiveSerializer

class ProjectAssetsViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all().order_by('name')
    serializer_class = ProjectAssetSerializer

class SessionViewSet(viewsets.ModelViewSet):

    filter_backends = (DjangoFilterBackend, filters.OrderingFilter, )
    filter_fields = ('project', )
    ordering_fields = ('start_time', )

    queryset = Session.objects.all().order_by('id')
    serializer_class = SessionSerializer

class SessionDetailsViewSet(viewsets.ModelViewSet):

    filter_backends = (DjangoFilterBackend, filters.OrderingFilter, )
    filter_fields = ('project', )
    ordering_fields = ('start_time', )

    queryset = Session.objects.all().order_by('id')
    serializer_class = SessionDetailsSerializer

class SessionExportViewSet(viewsets.ModelViewSet):
    # Viewset specific to exporting/importing from different databases
    queryset = Session.objects.all().order_by('id')
    serializer_class = SessionExportSerializer

class StaticScanAssetViewSet(viewsets.ModelViewSet):
    queryset = StaticScanAsset.objects.all().order_by('id')
    serializer_class = StaticScanAssetSerializer

class TrackingAssetViewSet(viewsets.ModelViewSet):
    queryset = TrackingAsset.objects.all().order_by('id')
    serializer_class = TrackingAssetTakeSerializer

class TakeViewSet(viewsets.ModelViewSet):
    queryset = Take.objects.all().order_by('id')
    serializer_class = TakeSerializer

class ShotViewSet(viewsets.ModelViewSet):
    queryset = Shot.objects.all().order_by('id')
    serializer_class = ShotSerializer

def full_thumb_path(filename):
    return os.path.join(BASE_DIR, 'static', 'thumb', filename)

@api_view(['GET'])
@permission_classes((IsAuthenticated,))
def get_archive_json_file(request, session_id="0"):
    session_id = int(session_id)

    queryset = Session.objects.get(pk=session_id)

    if not queryset:
        return HttpResponse(status=404)

    serializer = SessionExportSerializer(queryset, many=False, context={'request':request})

    response = JSONResponse(serializer.data)

    filename = 'exported_session_%d.json' % session_id

    response['Content-Disposition'] = 'attachment; filename=%s' % filename

    return response

@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def post_create_tracking_asset(request):
    if request.method == 'POST':

        # TODO Access rights
        if not request.user.is_superuser:
            return HttpResponse(status=403)

        j = json.loads(request.body)

        src_take = Take.objects.get(pk=j['take_id'])
        if not src_take:
            return HttpResponse(status=404)

        newasset = TrackingAsset(take=src_take, start_time=j['start_time'], end_time=j['end_time'])
        newasset.save()

        newasset.work_folder = os.path.join(os.path.join(src_take.export_path, 'work_TA%d' % newasset.id))
        newasset.save()

        # Automatically Launch thumbnail job
        job = FarmJob(job_class='jobs.thumbnails.GenerateThumbnail', created_by=request.user.username, status='ready', ext_tracking_assets=newasset, req_gpu=False)
        job.save()
        
    return HttpResponse()

@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def post_set_frontal_cam(request):
    if request.method == 'POST':

        # TODO Access rights
        if not request.user.is_superuser:
            return HttpResponse(status=403)

        j = json.loads(request.body)

        session = Session.objects.get(pk=j['session_id'])
        session.frontal_cam_id = j['cam_unique_id']
        session.save()

    return HttpResponse()

@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def post_set_take_flag(request):
    if request.method == 'POST':

        # TODO Access rights
        if not request.user.is_superuser:
            return HttpResponse(status=403)

        j = json.loads(request.body)

        take_ids = []
        if 'take_id' in j:
            take_ids.append(j.get('take_id'))
        if 'take_ids' in j:
            take_ids.extend(j.get('take_ids'))

        flag_name = j.get('flag_name') if j.get('flag_set') else 'none'
        Take.objects.filter(id__in=take_ids).update(flag=flag_name)

    return HttpResponse()

@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def post_delete_takes(request):
    if request.method == 'POST':

        # TODO Access rights
        if not request.user.is_superuser:
            return HttpResponse(status=403)

        j = json.loads(request.body)

        if 'takeid_list' in j:

            # List of take ids to delete
            list_of_take_ids = j['takeid_list']

            # Go thru the list of takes to delete, and check if we should delete the captured files
            local_files_to_delete = []
            remote_files_to_delete = {}

            # Create list of files to delete, both on server and on the nodes, and on the exported location
            for take in Take.objects.filter(pk__in=list_of_take_ids):

                if take.video_thumb:
                    local_files_to_delete.append(full_thumb_path(take.video_thumb)) # delete thumbnail from server

                for cam in take.cameras.all():
                    
                    if cam.thumbnail_filename:
                        local_files_to_delete.append(full_thumb_path(cam.thumbnail_filename)) # delete thumbnail from server

                    # if the take is not exported yet, delete on local capture machines
                    files = cam.all_files.split(';')

                    if take.export_path:
                        # Take is exported, need to delete files from the server
                        files.extend([os.path.join(take.export_path, os.path.split(f.replace('\\','/'))[1]) for f in cam.all_files.split(';')])

                    if cam.machine_name not in remote_files_to_delete:
                        remote_files_to_delete[cam.machine_name] = []
                    remote_files_to_delete[cam.machine_name].extend( files )

            # Delete takes from database
            Take.objects.filter(pk__in=list_of_take_ids).delete()

            # Create jobs to delete local files on nodes, or exported files
            for key in remote_files_to_delete:

                params = {}
                params['files'] = remote_files_to_delete[key]
                params['node'] = key
                params_json = json.dumps(params)

                # Create Job
                job = FarmJob(job_class='jobs.archive.DeleteFiles', created_by=request.user.username, params=params_json, status='ready', req_gpu=False, node=make_sure_node_exists(key))
                job.save()            

            # Delete local server files (thumbnails)
            for f in local_files_to_delete:
                try:
                    os.remove(f)
                except:
                    pass

    return HttpResponse()

def getUserData(request):
    if not hasattr(request.user, 'userdata'):
        request.user.userdata = UserData()
        request.user.userdata.save()
    return request.user.userdata

class ImagePacker():
    def __init__(self):
        self.files = []
        self.zip_filename = 'test.zip'
    def add(self, filename, data, content_type):
        self.files.append({
            'filename': filename,
            'data': data,
            'content_type': content_type,
        })
    def response(self):
        if not self.files:
            return JSONResponse({'message':'No images received from ' + cam.machine_name}, status=500)
        elif len(self.files) == 1:
            response = HttpResponse(self.files[0].get('data'), content_type=self.files[0].get('content_type'))
            response['Content-Disposition'] = 'attachment; filename="%s"' % self.files[0].get('filename')
            return response
        else:
            buff = StringIO.StringIO()
            zip_archive = zipfile.ZipFile(buff, mode='w')
            for f in self.files:
                zip_archive.writestr(f['filename'], f['data'])
            zip_archive.close()
            response = HttpResponse(buff.getvalue(), content_type='compressed/zip')
            response['Content-Disposition'] = 'attachment; filename="%s"' % self.zip_filename
            return response

@api_view(['GET'])
def download_original(request):

    take_id = int(request.GET.get('take', 0))
    cam_uid = request.GET.get('camera')

    take = Take.objects.get(pk=take_id)

    # Look for this camera in the Take
    cams = take.cameras.filter(unique_id=cam_uid)
    if cams:
        cam = cams[0] # Camera found

        if take.frame_count() > 1 and not (take.is_burst or take.is_scan_burst):
            return JSONResponse({'message':'Download not supported for sequences'}, status=500)

        frame_index_list = [0]

        # Find node associated with this file
        node = CaptureNode.objects.filter(machine_name=cam.machine_name)
        if not node:
            # Node not found in db
            return JSONResponse({'message':'Capture node not found: ' + cam.machine_name}, status=500)

        if take.is_burst or take.is_scan_burst:
            print('Downloading %d frames' % take.frame_count())
            frame_index_list = range(take.frame_count())

        # try to guess file extention from the all_files field on the camera
        extension = 'tif'
        if not '.tif' in cam.all_files and '.raw' in cam.all_files:
            extension = 'raw'

        image_packer = ImagePacker()
        image_packer.zip_filename = 'Take_%04d_raw.zip' % take_id

        for frame_index in frame_index_list:

            json_data = json.dumps({
                'folder': os.path.split(cam.folder)[0],
                'unique_id': cam_uid,
                'frame_index': frame_index,
                'extension': extension
            })

            if take.export_path:
                # Take was already exported, need to get image from exported location (if accessible)
                json_data['folder'] = take.export_path

            url = 'http://%s:8080/download/' % (node[0].ip_address)           
            try:

                result = urllib2.urlopen(url, data=json_data, timeout=DEFAULT_NODE_HTTP_TIMEOUT)
                file_data = result.read()

                basename = 'take_%d_%s_%04d.%s' % (take_id, cam_uid, frame_index, extension)

                image_packer.add(basename, file_data, result.info().type)

            except Exception as e:
                client.captureException()
                g_logger.error('post_toggle_using_sync %s: %s' % (cam.machine_name, e))  
                return JSONResponse({'message':'Could not download file from %s' % cam.machine_name}, status=500)                  

        return image_packer.response()
        

    # Camera not found in take
    return HttpResponse(status=404)


@api_view(['GET'])
@permission_classes((IsAuthenticated,))
def get_last_export_path(request):
    userdata = getUserData(request)
    return JSONResponse({'path':userdata.export_path})

@api_view(['GET', 'POST'])
@permission_classes((IsAuthenticated,))
def post_import_session(request, project_id="0"):

    project_id = int(project_id)

    try:
        # Accumulate content from uploaded file
        f = request.FILES['userfile']
        content = ''
        for chunk in f.chunks():
            content = content + chunk

        j = json.loads(content)
        j['project_id'] = project_id # change project to target project_id

        # Import data into database, using the same serializer used to export
        serializer = SessionExportSerializer(data=j)
        if not serializer.is_valid():
            return JSONResponse({'message':'Invalid Data'}, status=500)

        serializer.save()        

    except Exception as e:
        client.captureException()
        return JSONResponse({'message':'Error: %s' % e}, status=500)

    return HttpResponse()

@api_view(['GET', 'POST'])
@permission_classes((IsAuthenticated,))
def post_tracking_asset_thumbnail(request, asset_id="0", frame="0"):

    if request.method == 'POST':

        # TODO Access rights

        if not request.FILES:
            return HttpResponse(status=500)

        asset_id = int(asset_id)
        frame = int(frame)
        asset = TrackingAsset.objects.get(pk=asset_id)

        filename = 'track%d_f%d.jpg' % (asset_id, frame)
        filepath = full_thumb_path(filename)

        g_logger.info('Writing %s' % filepath)    

        # Write file to disk
        try:
            f = request.FILES['file']
            with open(filepath, 'wb') as destination:
                for chunk in f.chunks():
                    destination.write(chunk)                

        except Exception as e:
            client.captureException()
            print e

    return HttpResponse()

@api_view(['GET', 'POST'])
@permission_classes((IsAuthenticated,))
def post_scan_asset_thumbnail(request, asset_id="0", asset_type="front"):

    if request.method == 'POST':

        # TODO Access rights

        if not request.FILES:
            return HttpResponse(status=500)

        asset_id = int(asset_id)
        asset = StaticScanAsset.objects.get(pk=asset_id)

        if asset_type.isdigit():
            filename = 's%08d_f%d_%s.jpg' % (asset_id, int(asset_type), uuid_node_base36())
        else:
            filename = 's%08d_%s_%s.jpg' % (asset_id, asset_type, uuid_node_base36())
        
        filepath = full_thumb_path(filename)

        g_logger.info('Writing %s' % filepath)    

        # Write file to disk
        try:
            f = request.FILES['file']
            with open(filepath, 'wb') as destination:
                for chunk in f.chunks():
                    destination.write(chunk)                

            if asset_type=='front':
                asset.thumbnail_filename = filename
                asset.save()

        except Exception as e:
            client.captureException()
            print e

    return HttpResponse()

@api_view(['GET', 'POST'])
@permission_classes((IsAuthenticated,))
def post_tracking_video_thumbnail(request, asset_id="0"):

    if request.method == 'POST':

        # TODO Access rights

        if not request.FILES:
            return HttpResponse(status=500)

        asset_id = int(asset_id)
        tracking_asset = TrackingAsset.objects.get(pk=asset_id)

        filename = 'tr%08d_front_%s.mp4' % (tracking_asset.id, uuid_node_base36())
        filepath = full_thumb_path(filename)

        # Write file to disk
        try:
            f = request.FILES['file']
            with open(filepath, 'wb') as destination:
                for chunk in f.chunks():
                    destination.write(chunk)                

            tracking_asset.video_thumb = filename
            tracking_asset.save()

        except Exception as e:
            client.captureException()
            print e

    return HttpResponse()

@api_view(['GET', 'POST'])
@permission_classes((IsAuthenticated,))
def post_take_video_thumbnail(request, take_id="0"):

    if request.method == 'POST':

        # TODO Access rights

        if not request.FILES:
            return HttpResponse(status=500)

        take_id = int(take_id)
        take = Take.objects.get(pk=take_id)

        filename = 't%08d_front_%s.mp4' % (take.id, uuid_node_base36())
        filepath = full_thumb_path(filename)

        # Write file to disk
        try:
            f = request.FILES['file']
            with open(filepath, 'wb') as destination:
                for chunk in f.chunks():
                    destination.write(chunk)                

            take.video_thumb = filename
            take.save()

        except Exception as e:
            client.captureException()
            print e

    return HttpResponse()

@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def post_export_takes(request):
    if request.method == 'POST':

        # TODO Access rights
        if not request.user.is_superuser:
            return HttpResponse(status=403)

        j = json.loads(request.body)

        # Submit jobs to export these Take IDs on each node

        if 'takeid_list' in j and 'export_path' in j:

            job_priority = 50

            # Create list of machines, and the list of files to copy for each machine
            list_of_take_ids = j['takeid_list']
            export_path = j['export_path']

            userdata = getUserData(request)
            userdata.export_path = export_path
            userdata.save()

            for take_id in list_of_take_ids:

                # Create a list of files to export for each node
                files_to_export = {}

                take = Take.objects.get(pk=take_id)
                take.export_path = os.path.join(export_path, take.shot.session.name, take.shot.name, '%s_%d' % (take.name, take_id))
                take.work_folder = os.path.join(take.export_path, 'work_T%d' % int(take_id))
                take.save()

                take_frame_count = take.frame_count()

                # Set job priority according to take type
                if take.flag=='calib':
                    job_priority = 55
                elif take.flag=='best':
                    job_priority = 52
                if take_frame_count==1:
                    job_priority = job_priority + 1

                # Build list of nodes and files
                for cam in take.cameras.all():

                    if cam.machine_name not in files_to_export:
                        files_to_export[cam.machine_name] = []

                    for filepath in cam.all_files.split(';'):
                        files_to_export[cam.machine_name].append((filepath, take.export_path))

                params = {}
                params['root_export_path'] = export_path
                params['export_path'] = take.export_path
                params['nodes'] = files_to_export
                params_json = json.dumps(params)

                # Create Job
                job1 = FarmJob(job_class='jobs.archive.ExportTake', created_by=request.user.username, params=params_json, status='ready', ext_take=take, req_gpu=False, priority=job_priority)
                job1.save()

                if take.is_scan_burst:
                    # If there is no scan asset associated with this Take, create it
                    if not StaticScanAsset.objects.filter(take=take).exists():
                        asset = StaticScanAsset(
                            project=take.shot.session.project, 
                            name=take.full_name(), 
                            take=take,
                            image_folder=take.export_path,
                            has_tracking=False # because this asset was created with the Burst button
                            )
                        asset.save()
                        asset.work_folder = os.path.join(take.export_path, 'work_SA%d' % asset.id)
                        asset.save()

                        # Create Job for GenerateThumbnails for the new static scan asset
                        params = {}
                        params['take_export_path'] = take.export_path
                        params_json = json.dumps(params)
                        job2 = FarmJob(job_class='jobs.thumbnails.GenerateThumbnail', created_by=request.user.username, params=params_json, status='created', ext_scan_assets=asset, req_gpu=False, priority=job_priority)
                        job2.save()
                        job2.dependencies.add(job1)
                        job2.status='ready'
                        job2.save()

                # Create Job for GenerateThumbnails
                if not take_frame_count==1:
                    params = {}
                    params['take_export_path'] = take.export_path
                    params_json = json.dumps(params)
                    job2 = FarmJob(job_class='jobs.thumbnails.GenerateThumbnail', created_by=request.user.username, params=params_json, status='created', ext_take=take, req_gpu=False, priority=job_priority)
                    job2.save()
                    job2.dependencies.add(job1)
                    job2.status='ready'
                    job2.save()

    return HttpResponse()

