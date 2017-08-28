#
# Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
#

import json
import traceback
import logging
import datetime
import os

from django.shortcuts import render
from django.http import HttpResponse
from django.db.models import Q
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from common.views import JSONResponse
from models import FarmNode, FarmJob, FarmNodeGroup
from django.utils import timezone
from django.contrib.auth.models import User

from common.uuid_utils import uuid_node_base36

from rest_framework import viewsets, filters, mixins
from serializers import FarmNodeSerializer, FarmJobSerializer, FarmJobDetailedSerializer, FarmNodeGroupSerializer

from django.core.mail import send_mail

from ava.settings import FRONTEND_URL, ADMIN_EMAIL, BASE_DIR

g_logger = logging.getLogger('dev')

@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def submit_test_job(request):

    # TODO Access rights
    if not request.user.is_superuser:
        return HttpResponse(status=403)

    # DEBUGGING ONLY

    job = FarmJob(job_class='jobs.test.DummyJob', created_by='submit_test_job', params=request.body, status = 'ready')
    job.save()

    return HttpResponse('OK')

@api_view(['GET'])
@permission_classes((IsAuthenticated,))
def node_detailed(request, node_id="0"):

    node = FarmNode.objects.get(pk=int(node_id))

    if not node:
        return HttpResponse(status=404)

    serializer = FarmNodeSerializer(node, many=False, context={'request':request})

    return JSONResponse(serializer.data)

@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def job_image(request, job_id="0"):

    job_id = int(job_id)
    job = FarmJob.objects.get(pk=job_id)

    if not job:
        return HttpResponse(status=404)

    if not request.FILES:
        return HttpResponse(status=500)

    filename = 'j%08d_%s.jpg' % (job_id, uuid_node_base36())
    filepath = os.path.join(BASE_DIR, 'static', 'thumb', filename)

    # Write file to disk
    try:
        f = request.FILES['file']
        with open(filepath, 'wb') as destination:
            for chunk in f.chunks():
                destination.write(chunk)                

        job.image_filename = filename
        job.save()

    except Exception as e:
        return HttpResponse(e, status=500)

    return HttpResponse('OK')

@api_view(['GET'])
@permission_classes((IsAuthenticated,))
def job_detailed(request, job_id="0"):

    job = FarmJob.objects.get(pk=int(job_id))

    if not job:
        return HttpResponse(status=404)

    serializer = FarmJobDetailedSerializer(job, many=False, context={'request':request})

    return JSONResponse(serializer.data)

@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def post_reload_client(request):

    if not 'node_id' in request.data:
        return HttpResponse(status=500)

    if request.data['node_id']<0:
        # Reload All Node clients

        # todo access rights

        FarmNode.objects.all().update(req_restart=True)

    else:
        # Reload one client

        node = FarmNode.objects.get(pk=request.data['node_id'])
        if not node:
            return HttpResponse(status=404)
        if not node.has_write_access(request.user):
            return HttpResponse(status=403)

        node.req_restart = True
        node.save()

    return HttpResponse('OK')

@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def restart_job(request):

    if not 'job_id' in request.data:
        return HttpResponse(status=500)

    clone_job = request.data['clone_job'] if 'clone_job' in request.data else False
    use_same_machine = request.data['use_same_machine'] if 'use_same_machine' in request.data else False

    # Find Job to be restarted
    src_job = FarmJob.objects.get(pk=request.data['job_id'])

    if not src_job:
        return HttpResponse(status=404)

    if not src_job.has_write_access(request.user):
        return HttpResponse(status=403)

    if clone_job:

        # Create duplicate job
        job = FarmJob(job_class=src_job.job_class, 
                    created_by=request.user.username, 
                    params=src_job.params,
                    node=src_job.node if use_same_machine else None,
                    ext_take=src_job.ext_take,
                    ext_scan_assets=src_job.ext_scan_assets,
                    ext_tracking_assets=src_job.ext_tracking_assets,
                    req_gpu=src_job.req_gpu,
                    priority=src_job.priority,
                    status = 'ready')
        job.save()

        g_logger.info('Job #%d restarted as job #%d' % (src_job.id,job.id))      

    else:

        # Delete all child jobs 
        src_job.children.all().delete()

        # Update job status
        src_job.status = 'ready'
        src_job.exception = None
        src_job.image_filename = None
        src_job.progress = None
        if not use_same_machine:
            src_job.node = None
        src_job.save()

        g_logger.info('Job #%d restarted' % (src_job.id))      

    return HttpResponse('OK')

@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def delete_job(request):

    if not 'job_id' in request.data:
        return HttpResponse(status=500)

    # Find Job to be restarted
    src_job = FarmJob.objects.get(pk=request.data['job_id'])

    if not src_job:
        return HttpResponse(status=404)

    if not src_job.has_write_access(request.user):
        return HttpResponse(status=403)

    # If Job is ready, success or failed, we can simply delete it.
    deleted = FarmJob.objects.filter(id=src_job.id).filter(status__in=['ready','success','failed']).delete()
    if 'jobs.FarmJob' in deleted and deleted['jobs.FarmJob']>0:
        g_logger.info('Job #%d deleted' % (src_job.id))     
        return HttpResponse('OK')

    return HttpResponse(status=404)

@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def kill_job(request):

    if not 'job_id' in request.data:
        return HttpResponse(status=500)

    # Find Job to be restarted
    src_job = FarmJob.objects.get(pk=request.data['job_id'])

    if not src_job:
        return HttpResponse(status=404)

    if not src_job.has_write_access(request.user):
        return HttpResponse(status=403)

    # Terminate job
    killed = FarmJob.objects.filter(id=src_job.id, status='running').update(status='terminating')
    if killed>0:
        g_logger.info('Job #%d killed' % (src_job.id))      
        return HttpResponse('OK')

    return HttpResponse(status=404)
 
def UpdateParentJob(job, request):
    if job.status=='waiting':
        success_count = job.children.filter(status='success').count()
        failed_count = job.children.filter(status='failed').count()
        all_count = job.children.count()

        job.progress = '%d/%d Success, %d/%d Failed' % (success_count, all_count, failed_count, all_count)

        if all_count>0 and success_count+failed_count == all_count:
            # If there are no child in a status that is not success or failed
            previous_status = job.status
            job.status = 'failed' if failed_count>0 else 'success'
            if not job.status == previous_status:
                g_logger.info('Job #%d status set to %s in UpdateParentJob' % (job.id, job.status))      
                job.end_time = timezone.now()
                onJobChanged(job, request)

        job.save()


def sendEmailToOwner(job, request):

    try:

        recipients = [ADMIN_EMAIL]

        user = User.objects.all().filter(username=job.created_by)
        if user:
            recipients.append(user[0].email)

        url = request.build_absolute_uri(FRONTEND_URL + '/app/job_details/%d' % job.id)

        html = "<html><body style='font-family:sans-serif;'>Job id: #%d %s<br>status:%s<br>owner:%s<br><a href=\"%s\">Go to Job Description</a><br>params:%s<br>Exception:%s</body></html>" % (
            job.id, job.job_class, job.status, job.created_by, url, job.params, job.exception, )

        send_mail(
            'JOB Failed #%d' % job.id,
            "Job id: #%d %s\nstatus:%s\nowner:%s\nparams:%s\nException:%s" % (
            job.id, job.job_class, job.status, job.created_by, job.params, job.exception),
            ADMIN_EMAIL,
            recipients,
            fail_silently=True,
            html_message = html
        )
    except:
        pass                
    
def onJobChanged(job, request):

    if job.status=='failed' and job.parent==None:
        # Send email notification if status is 'failed'
        sendEmailToOwner(job, request)

    if job.parent:
        UpdateParentJob(job.parent, request)

def make_sure_node_exists(nodename):
    nodes = FarmNode.objects.filter(machine_name__iexact=nodename)
    if nodes:
        return nodes[0]
    else:
        # Node does not exist, create it
        node = FarmNode(ip_address="0.0.0.0", machine_name=nodename)
        node.save()
        return node

def cleanup_dead_jobs(request):
    for lost_job in FarmJob.objects.filter(Q(status='running') | Q(status='terminating')).filter(node__last_seen__lt=timezone.now() - datetime.timedelta(hours=2)): # Jobs will timeout after 2h
        # Jobs that are running according to the DB, but the node has not been seen since 2 hours
        g_logger.info('Job #%d failed because node is not runnnig' % (lost_job.id))      
        lost_job.status = 'failed'
        lost_job.save()
        onJobChanged(lost_job, request)

@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def post_client_discover(request):
    if request.method == 'POST':
        
        cleanup_dead_jobs(request) # TODO This could be on a schedule

        # Update database from recieved data
        r = json.loads(request.body)

        if 'status' not in r:
            raise Exception('Invalid request')

        # Look for existing machine in the database, with the same ip
        nodes = FarmNode.objects.filter(machine_name__iexact=r['machine_name'])
        if nodes:
            # Node exists in database, update it
            node = nodes[0]
            node.ip_address = request.data['ip_address']
            node.last_seen = timezone.now()

        else:
            # Node does not exist, create it
            node = FarmNode(ip_address=r['ip_address'], machine_name=r['machine_name'])

        if 'system' in r:
            node.system = r['system']
        if 'system_bits' in r:
            node.system_bits = r['system_bits']
        if 'cpu_brand' in r:
            node.cpu_brand = r['cpu_brand']
        if 'cpu_cores' in r:
            node.cpu_cores = r['cpu_cores']
        if 'cuda_device_count' in r:
            node.gpu_count = r['cuda_device_count']
        if 'restarted' in r and r['restarted']:
            node.req_restart = False
        if 'cpu_percent' in r:
            node.cpu_percent = r['cpu_percent']
            
        node.code_version = r['code_version'] if 'code_version' in r else 0
        node.status = r['status']
        node.save()

        available_jobs = r['available_jobs'] if 'available_jobs' in r else []
        jobs_to_terminate = [job.id for job in FarmJob.objects.filter(status='terminating', node=node)]

        # Update database from running and finished jobs (if they are not 'terminating')
        if 'running_jobs_progress' in r:
            for job_id,progress in r['running_jobs_progress']:
                FarmJob.objects.filter(id=job_id).filter(~Q(status='terminating')).update(status='running', progress=progress)
        elif 'running_jobs' in r:
            for job_id in r['running_jobs']:
                FarmJob.objects.filter(id=job_id).filter(~Q(status='terminating')).update(status='running')

        if 'finished_jobs' in r:
            for job in r['finished_jobs']:

                progress = job['progress'] if 'progress' in job else ''

                try:

                    # Update job with new status
                    this_job = FarmJob.objects.get(pk=job['job_id'])
                    if 'children' in job:
                        # Yield to children
                        for job_info in job['children']:

                            if isinstance(job_info, dict):
                                # Create child job
                                target_node = None
                                if 'node_name' in job_info:
                                    target_node = make_sure_node_exists(job_info['node_name'])

                                child = FarmJob(job_class=job_info['job_class'], created_by=this_job.created_by, params=job_info['params'], status='ready', parent=this_job, node=target_node, req_version=this_job.req_version, req_gpu=this_job.req_gpu)
                                child.save()
                            else:
                                # Backward compatibility code
                                child = FarmJob(job_class=job_info[0], created_by=this_job.created_by, params=job_info[1], status = 'ready', parent=this_job)
                                child.save()

                        g_logger.info('Job #%s set to WAITING' % (job['job_id']))    
                        FarmJob.objects.filter(id=job['job_id']).update(status='waiting', progress=progress)
                    elif 'success' in job and job['success']:
                        g_logger.info('Job #%s set to SUCCESS' % (job['job_id']))    
                        FarmJob.objects.filter(id=job['job_id']).update(status='success', progress=progress, end_time=timezone.now())
                    else:
                        g_logger.info('Job #%s set to FAILED' % (job['job_id']))    
                        FarmJob.objects.filter(id=job['job_id']).update(status='failed', exception=job['exception'], progress=progress, end_time=timezone.now())

                    # Update parent job, if it exists
                    this_job.refresh_from_db()
                    onJobChanged(this_job, request)

                except ObjectDoesNotExist:
                    pass # Job does not exist anymore

        if 'running_jobs' in r:
            # Jobs that are running according to the DB, but not according to the node
            for lost_job in FarmJob.objects.filter(Q(status='running') | Q(status='terminating')).filter(node=node).exclude(pk__in=r['running_jobs']):
                g_logger.info('Job #%d failed because not in running_jobs' % (lost_job.id))      
                lost_job.status = 'failed'
                lost_job.save()
                onJobChanged(lost_job, request)

        data = {}

        if node.status == 'accepting':

            data['jobs'] = []
            data['jobs_to_kill'] = []
            data['req_restart'] = node.req_restart

            # Scheduler, reserve some tasks for specific machines
            if not node.req_restart:
                try:
                    with transaction.atomic():
                        if FarmJob.objects.filter(status='running', node=node).count() == 0: # If node is not doing anything                    
                            
                            if node.active:
                                next_jobs = FarmJob.objects.select_for_update().filter(status='ready', req_version__lte=node.code_version).filter(Q(node=node) | Q(node=None)).filter(job_class__in=available_jobs)
                            else:
                                next_jobs = FarmJob.objects.select_for_update().filter(status='ready', req_version__lte=node.code_version).filter(Q(node=node)).filter(job_class__in=available_jobs)

                            if node.gpu_count <= 0:
                                next_jobs = next_jobs.filter(req_gpu=False)
                            next_jobs = next_jobs.order_by('-priority')
                            
                            for next_job in next_jobs:

                                # Check Job Dependencies (filter if that there are no dependencies that are not 'success')
                                if next_job.dependencies.filter(~Q(status='success')).count()==0:
                                    
                                    # TODO This should be in the same query, otherwise we may be looping for no reason
                                
                                    g_logger.info('Job #%s RESERVED for %s' % (next_job.id, node.machine_name))    
                                
                                    # Send a single job to this machine
                                    next_job.status = 'reserved'
                                    next_job.node = node
                                    next_job.exception = None
                                    next_job.start_time = timezone.now()
                                    next_job.save()

                                    break

                except Exception as e:
                    g_logger.error('Scheduler failed %s' % e)

            # Send reserved jobs to node
            jobs = FarmJob.objects.filter(status='reserved', node=node)
            for job in jobs:

                g_logger.info('Job #%s SUBMIT to %s' % (job.id, node.machine_name))    

                job_data = {'job_id':job.id, 'job_class':job.job_class, 'params':job.params}
                data['jobs'].append(job_data)

            # Send jobs to kill to node
            for job_id in jobs_to_terminate:

                g_logger.info('Job #%s KILL to %s' % (job_id, node.machine_name))    

                data['jobs_to_kill'].append(job_id)

        return JSONResponse(data)

class FarmGroupsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = FarmNodeGroup.objects.all().order_by('name')
    serializer_class = FarmNodeGroupSerializer

class FarmNodeViewSet(viewsets.ModelViewSet):
    queryset = FarmNode.objects.all().order_by('status', 'machine_name')
    serializer_class = FarmNodeSerializer

class FarmJobsViewSet(viewsets.ModelViewSet):

    filter_backends = (filters.DjangoFilterBackend, filters.SearchFilter,)
    filter_fields = ('status', )
    search_fields = ('job_class', 'node__machine_name', 'created_by')
        
    queryset = FarmJob.objects.filter(Q(parent=None) | Q(status='running')).order_by('-status_changed')
    serializer_class = FarmJobSerializer
