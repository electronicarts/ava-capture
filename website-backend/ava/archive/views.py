#
# Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
#

import json
import os

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

from jobs.models import FarmNode, FarmJob
from accounts.models import UserData

class ProjectsViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all().order_by('name')
    serializer_class = ProjectSerializer

class ProjectArchiveViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all().order_by('name')
    serializer_class = ProjectArchiveSerializer

class ProjectAssetsViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all().order_by('name')
    serializer_class = ProjectAssetSerializer

class SessionDetailsViewSet(viewsets.ModelViewSet):
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

        newasset = TrackingAsset(take=src_take, start_time=j['start_time'], end_time=j['end_time'], calib_file=j['calib_file'])
        newasset.save()

        # TODO Launch Job to generate thumbnail for newasset
        
    return HttpResponse('Ok')

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

    return HttpResponse('Ok')

@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def post_set_take_flag(request):
    if request.method == 'POST':

        # TODO Access rights
        if not request.user.is_superuser:
            return HttpResponse(status=403)

        j = json.loads(request.body)

        take_id = j['take_id']

        take = Take.objects.get(pk=take_id)

        if j['flag_set']:
            take.flag = j['flag_name']
        else:
            take.flag = 'none'

        take.save()

    return HttpResponse('Ok')

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

            Take.objects.filter(pk__in=list_of_take_ids).delete()

    return HttpResponse('Ok')

def getUserData(request):
    if not hasattr(request.user, 'userdata'):
        request.user.userdata = UserData()
        request.user.userdata.save()
    return request.user.userdata

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
            return HttpResponse('Invalid Data', status=500)

        serializer.save()        

    except Exception as e:
        return HttpResponse('Error: %s' % e, status=500)

    return HttpResponse('Ok')

@api_view(['GET', 'POST'])
@permission_classes((IsAuthenticated,))
def post_scan_asset_thumbnail(request, asset_id="0", asset_type="front"):

    if request.method == 'POST':

        # TODO Access rights

        if not request.FILES:
            return HttpResponse(status=500)

        asset_id = int(asset_id)
        asset = StaticScanAsset.objects.get(pk=asset_id)

        filename = 's%08d_%s_%s.jpg' % (asset_id, asset_type, uuid_node_base36())
        filepath = os.path.join(BASE_DIR, 'static', 'thumb', filename)

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
            print e

    return HttpResponse('Ok')

@api_view(['GET', 'POST'])
@permission_classes((IsAuthenticated,))
def post_tracking_asset_thumbnail(request, asset_id="0"):

    if request.method == 'POST':

        # TODO Access rights

        if not request.FILES:
            return HttpResponse(status=500)

        asset_id = int(asset_id)
        tracking_asset = TrackingAsset.objects.get(pk=asset_id)

        filename = 'tr%08d_front_%s.mp4' % (tracking_asset.id, uuid_node_base36())
        filepath = os.path.join(BASE_DIR, 'static', 'thumb', filename)

        # Write file to disk
        try:
            f = request.FILES['file']
            with open(filepath, 'wb') as destination:
                for chunk in f.chunks():
                    destination.write(chunk)                

            tracking_asset.video_thumb = filename
            tracking_asset.save()

        except Exception as e:
            print e

    return HttpResponse('Ok')

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
        filepath = os.path.join(BASE_DIR, 'static', 'thumb', filename)

        # Write file to disk
        try:
            f = request.FILES['file']
            with open(filepath, 'wb') as destination:
                for chunk in f.chunks():
                    destination.write(chunk)                

            take.video_thumb = filename
            take.save()

        except Exception as e:
            print e

    return HttpResponse('Ok')

@api_view(['GET', 'POST'])
@permission_classes((IsAuthenticated,))
def take_export_path(request, take_id="0"):
    take_id = int(take_id)

    take = Take.objects.get(pk=take_id)

    if request.method == 'POST':
        j = json.loads(request.body)
        take.export_path = j['export_path']
        take.save()
        return JSONResponse({'result':'OK', 'export_path':take.export_path})
    elif request.method == 'GET':
        return JSONResponse({'export_path':take.export_path})
    else:
        return HttpResponse(status=500)


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
                take.export_path = os.path.join(export_path, take.shot.session.name, take.shot.name, take.name)
                take.save()

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
                job1 = FarmJob(job_class='jobs.archive.ExportTake', created_by=request.user.username, params=params_json, status='ready', ext_take=take, req_gpu=False)
                job1.save()

                # Create Job for GenerateThumbnails
                # TODO Only if AVI, not if Single shot TIF
                params = {}
                params['take_export_path'] = take.export_path
                params_json = json.dumps(params)
                job2 = FarmJob(job_class='jobs.thumbnails.GenerateThumbnail', created_by=request.user.username, params=params_json, status='created', ext_take=take, req_gpu=False)
                job2.save()
                job2.dependencies.add(job1)
                job2.status='ready'
                job2.save()

    return HttpResponse('Ok')

