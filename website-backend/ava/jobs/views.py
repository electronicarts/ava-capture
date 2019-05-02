#
# Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
#

import json
import traceback
import logging
import datetime
import os
import urllib2

import aws

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
from serializers import FarmNodeSerializer, FarmJobSerializer, FarmJobDetailedSerializer, FarmNodeGroupSerializer, FarmNodeSerializerDetails

from django.core.mail import send_mail

from ava.settings import FRONTEND_URL, ADMIN_EMAIL, BASE_DIR, SLACK_NOTIF_HOOK, NOTIFICATION_EMAIL

from prometheus_client import Gauge, Counter

from raven.contrib.django.raven_compat.models import client

from ansi2html import Ansi2HTMLConverter

g_logger = logging.getLogger('dev')

metrics_client_cpu = Gauge('job_client_cpu', 'CPU Usage of each node client', ['machine_name'])
metrics_client_last_seen = Gauge('job_client_last_seen', 'When was this job client las seen', ['machine_name'])
metrics_job_success_count = Counter('jobs_success', 'Number of successful jobs', ['machine_name'])
metrics_job_failed_count = Counter('jobs_failed', 'Number of successful jobs', ['machine_name'])
metrics_client_nb_running = Gauge('job_client_nb_running', 'Number of jobs running on job client', ['machine_name'])

@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def submit_test_job(request):

    # TODO Access rights
    if not request.user.is_superuser:
        return HttpResponse(status=403)

    # DEBUGGING ONLY

    job = FarmJob(job_class='jobs.test.DummyJob', created_by='submit_test_job', params=request.body, status = 'ready')
    job.save()

    return HttpResponse()

@api_view(['GET'])
@permission_classes((IsAuthenticated,))
def node_detailed(request, node_id="0"):

    node = FarmNode.objects.get(pk=int(node_id))

    if not node:
        return HttpResponse(status=404)    

    serializer = FarmNodeSerializerDetails(node, many=False, context={'request':request})

    return JSONResponse(serializer.data)

@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def job_mesh(request, job_id="0"):

    job_id = int(job_id)
    job = FarmJob.objects.get(pk=job_id)

    if not job:
        return HttpResponse(status=404)

    if not request.FILES:
        return HttpResponse(status=500)

    ext = os.path.splitext(request.FILES['file'].name)[1]

    filename = 'j%08d_%s%s' % (job_id, uuid_node_base36(), ext)
    filepath = os.path.join(BASE_DIR, 'static', 'thumb', filename)

    # Write file to disk
    try:
        f = request.FILES['file']
        with open(filepath, 'wb') as destination:
            for chunk in f.chunks():
                destination.write(chunk)                

        job.mesh_filename = filename
        job.save()

    except Exception as e:
        client.captureException()
        return JSONResponse({'message':'%s' % e}, status=500)

    return HttpResponse()

@api_view(['GET', 'POST'])
@permission_classes((IsAuthenticated,))
def job_output(request, job_id="0"):
    job_id = int(job_id)

    job = FarmJob.objects.get(pk=job_id)
    if not job:
        return HttpResponse(status=404)

    filepath = os.path.join(BASE_DIR, 'static', 'thumb', '%08d.output' % job_id)
    if request.method == 'POST':
        f = request.FILES['file']
        #print('Writing %d bytes to %s' % (f.size,filepath))
        with open(filepath, 'ab') as destination:
            for chunk in f.chunks():
                destination.write(chunk)
        return HttpResponse()
    if request.method == 'GET':
        offset = int(request.GET.get('offset', 0))
        length = int(request.GET.get('length', 1024*1024)) # max chunk size
        # Return content of stored file
        try:
            with open(filepath, 'rb') as f:
                f.seek(offset)
                data = f.read(length)
                try:
                    conv = Ansi2HTMLConverter()
                    html = conv.convert(data.decode('utf-8'), full=False)
                    return JSONResponse({'content':html, 'length':len(data), 'status':job.status})
                except:
                    return JSONResponse({'content':data, 'length':len(data), 'status':job.status})
        except Exception as e:
            return HttpResponse('Exception: %s' % e, status=404)

@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def job_image(request, job_id="0"):

    job_id = int(job_id)
    job = FarmJob.objects.get(pk=job_id)

    if not job:
        return HttpResponse(status=404)

    if not request.FILES:
        return HttpResponse(status=500)

    ext = os.path.splitext(request.FILES['file'].name)[1]

    filename = 'j%08d_%s%s' % (job_id, uuid_node_base36(), ext)
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
        client.captureException()
        return JSONResponse({'message':'%s' % e}, status=500)

    return HttpResponse()

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
def post_aws_start_instance(request):

    if not 'node_id' in request.data:
        return HttpResponse(status=500)

    node = FarmNode.objects.get(pk=request.data['node_id'])
    if not node:
        return HttpResponse(status=404)
    if not node.has_write_access(request.user):
        return HttpResponse(status=403)

    if node.aws_instance_id:
        state = aws.start_instance(node.aws_instance_id, node.aws_instance_region)
        if state:
            node.aws_instance_state = state
            node.save()

    return HttpResponse()

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

    return HttpResponse()

def on_job_restart(job_id):
    # When a job is restarted, clear output log
    try:
        filepath = os.path.join(BASE_DIR, 'static', 'thumb', '%08d.output' % job_id)
        os.remove(filepath)
    except:
        pass

@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def restart_job_failed_child(request):

    if not 'job_id' in request.data:
        return HttpResponse(status=500)

    use_same_machine = request.data['use_same_machine'] if 'use_same_machine' in request.data else False

    # Find Job to be restarted
    src_job = FarmJob.objects.get(pk=request.data['job_id'])

    if not src_job:
        return HttpResponse(status=404)

    if not src_job.has_write_access(request.user):
        return HttpResponse(status=403)

    queryset = FarmJob.objects.filter(parent=src_job).filter(status='failed')
    nb_restart = queryset.count()

    if nb_restart>0:
        for job in queryset:
            on_job_restart(job.id)

        if use_same_machine:
            queryset.update(status='ready', exception=None, image_filename=None, mesh_filename=None, progress=None, start_time=None, end_time=None, modified=timezone.now())
        else:
            queryset.update(status='ready', node=None, exception=None, image_filename=None, mesh_filename=None, progress=None, start_time=None, end_time=None, modified=timezone.now())

        src_job.status = 'waiting'
        src_job.save()

    g_logger.info('Child of Job #%d restarted' % (src_job.id))      

    return HttpResponse()

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
                    status = 'created')
        job.save()
        # copy tags in a second pass (required for ManyToMany)
        job.tags.set(*src_job.tags.names(), clear=True)
        job.status='ready'
        job.save()

        g_logger.info('Job #%d restarted as job #%d' % (src_job.id,job.id))      

    else:

        # If some child are still running, refust to restart
        if src_job.children.filter(Q(status='running')|Q(status='waiting')).count() > 0:
            return JSONResponse({'message':'Error, child running'}, status=403)

        # Delete all child jobs 
        src_job.children.all().delete()

        on_job_restart(src_job.id)

        # Update job status
        src_job.status = 'ready'
        src_job.exception = None
        src_job.image_filename = None
        src_job.mesh_filename = None
        src_job.progress = None
        src_job.start_time = None
        src_job.end_time = None
        if not use_same_machine:
            src_job.node = None
        src_job.save()

        g_logger.info('Job #%d restarted' % (src_job.id))      

    return HttpResponse()

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
    deleted_count,deleted_by_type = FarmJob.objects.filter(id=src_job.id).filter(status__in=['ready','success','failed']).delete()
    if 'jobs.FarmJob' in deleted_by_type and deleted_by_type['jobs.FarmJob']>0:
        g_logger.info('Job #%d deleted' % (src_job.id))     
        return HttpResponse()

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
    killed = FarmJob.objects.filter(id=src_job.id, status='running').update(status='terminating', modified=timezone.now())
    if killed>0:
        g_logger.info('Job #%d killed' % (src_job.id))      
        return HttpResponse()

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
        client.captureException()

def slack_notification(message, color='good', extra_attributes={}):
    if SLACK_NOTIF_HOOK:
        try:            
            # Slack channel

            url = 'https://hooks.slack.com/services/%s' % SLACK_NOTIF_HOOK

            data_att = {"color": color, 'text':message, 'fallback':message}
            data_att.update(extra_attributes)
            data_str = json.dumps( {'attachments': [data_att]} )

            req = urllib2.Request(url, data_str, {'Content-Type': 'application/json', 'Content-Length': len(data_str)})
            result = urllib2.urlopen(req).read()

        except Exception as e:
            client.captureException()
            g_logger.error('Slack notification failed %s' % e)

def job_notification(job, request):

    # Send email notification if status is 'failed'
    if job.status=='failed' and job.parent==None and NOTIFICATION_EMAIL:
        sendEmailToOwner(job, request)

    # Slack channel
    if job.parent==None and not job.status=='waiting':

        if job.status=='failed':
            color = 'danger'
        elif job.status=='success':
            color = 'good'
        else:
            color = 'warning'
        
        notif_text = 'Job #%d %s: *%s* (%s)' % (job.id, job.job_class, job.status, job.created_by)
        if job.ext_take:
            notif_text += '\nTake: #%d %s' % (job.ext_take.id, job.ext_take.full_name())
        if job.ext_scan_assets:
            notif_text += '\nTake: #%d %s' % (job.ext_scan_assets.take.id, job.ext_scan_assets.take.full_name())
            notif_text += '\nScanAsset: #%d %s' % (job.ext_scan_assets.id, job.ext_scan_assets.name)
        if job.ext_tracking_assets:
            notif_text += '\nTrackingAsset: #%d %s' % (job.ext_tracking_assets.id, job.ext_tracking_assets.take.full_name())       
        if job.status=='failed':
            notif_text += '\nException: ```%s```' % job.exception

        data_att = {}
        # Images on internal network doesn't work
        #if job.image_filename:
        #    data_att['image_url'] = request.build_absolute_uri('/static/thumb/' + job.image_filename)
        if job.end_time:
            data_att['ts'] = int(job.end_time.strftime('%s'))

        slack_notification(notif_text, color=color, extra_attributes=data_att)


def onJobChanged(job, request):

    job_notification(job, request)

    if job.parent:
        UpdateParentJob(job.parent, request)

def make_sure_node_exists(nodename):
    nodes = FarmNode.objects.filter(machine_name__iexact=nodename)
    if nodes:
        return nodes[0]
    else:
        # Node does not exist, create it
        node = FarmNode(machine_name=nodename)
        node.save()
        return node

def cleanup_dead_jobs(request):
    for lost_job in FarmJob.objects.filter(Q(status='running') | Q(status='terminating')).filter(node__last_seen__lt=timezone.now() - datetime.timedelta(hours=2)): # Jobs will timeout after 2h
        # Jobs that are running according to the DB, but the node has not been seen since 2 hours
        g_logger.info('Job #%d failed because node is not runnnig' % (lost_job.id))      
        lost_job.status = 'failed'
        lost_job.save()
        onJobChanged(lost_job, request)

def or_list(q_list):
    # returns a list of Q or'd toghether
    first_q = q_list.pop()
    for other_q in q_list:
        first_q |= other_q
    return first_q

@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def post_client_discover(request):
    if request.method == 'POST':

        update_aws_status = False
        
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

            if node.aws_instance_state != 'running':
                update_aws_status = True

            node.last_seen = timezone.now()

        else:
            # Node does not exist, create it
            node = FarmNode(ip_address=r['ip_address'], machine_name=r['machine_name'])
            update_aws_status = True

        metrics_client_last_seen.labels(node.machine_name).set_to_current_time()

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
            metrics_client_cpu.labels(node.machine_name).set(node.cpu_percent)
        if 'mem_used' in r:
            node.virt_percent = r['mem_used']
        if 'os_version' in r:
            node.os_version = r['os_version']

        # AWS Cloud integration
        if update_aws_status:
            node.aws_instance_id, node.aws_instance_region, node.aws_instance_state = aws.instance_id_from_private_ip(node.ip_address)
        else:
            # AWS, check if this instance should be stopped for inactivity
            if node.aws_instance_should_be_stopped():
                nb_aws_running = FarmNode.objects.filter(aws_instance_state='running').count()
                slack_notification('Stopping inactive AWS instance: *%s* (running:%d)' % (node.machine_name, nb_aws_running-1), color='warning')
                node.aws_instance_state = aws.stop_instance(node.aws_instance_id, node.aws_instance_region)

        if FarmJob.objects.filter(status='running', node=node).count()>0:
            node.last_job_activity = timezone.now()
        node.code_version = r['code_version'] if 'code_version' in r else 0
        node.git_version = r['git_version'] if 'git_version' in r else ''   
        node.status = r['status']
        node.save()

        # Update tags on farm node, if client_tags are supplied, otherwise, keep tags in DB
        if 'client_tags' in r:
            tags = r.get('client_tags',[])
            if node.aws_instance_id:
                tags.append('aws')
            if tags != node.tags:
                with transaction.atomic():
                    node.tags.set(*tags, clear=True) # don't need node.save()
        else:
            # client did not specify any tags, use the ones in DB
            tags = node.tags.names()

        # In order to filter jobs by tags, we start with the list of all possible tags, then 
        # remove the tags supported by this node. What remains is the list of tags that
        # cannot be fulfilled. Jobs with these tags should be filtered out.
        all_possible_tags = FarmNode.tags.all().values_list('name', flat=True)
        excluded_tags = [x for x in all_possible_tags if not x in tags]

        available_jobs = r['available_jobs'] if 'available_jobs' in r else []
        jobs_to_terminate = [job.id for job in FarmJob.objects.filter(status='terminating', node=node)]

        # Update database from running and finished jobs (if they are not 'terminating')
        if 'running_jobs_progress' in r:
            for job_id,progress in r['running_jobs_progress']:
                FarmJob.objects.filter(id=job_id).filter(~Q(status='terminating')).filter(~Q(status='running') | ~Q(progress=progress)).update(status='running', progress=progress, modified=timezone.now())

        elif 'running_jobs' in r:
            FarmJob.objects.filter(id__in=r['running_jobs']).filter(~Q(status='terminating')).filter(~Q(status='running')).update(status='running', modified=timezone.now())

        if 'finished_jobs' in r:
            for job in r['finished_jobs']:

                progress = job['progress'] if 'progress' in job else ''

                try:

                    # Update job with new status
                    this_job = FarmJob.objects.get(pk=job['job_id'])
                    this_job.progress = progress
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
                        this_job.status = 'waiting'
                    elif 'success' in job and job['success']:
                        g_logger.info('Job #%s set to SUCCESS' % (job['job_id']))
                        this_job.status = 'success'
                        this_job.end_time = timezone.now()
                        metrics_job_success_count.labels(node.machine_name).inc()
                    else:
                        g_logger.info('Job #%s set to FAILED' % (job['job_id']))
                        this_job.status = 'failed'
                        this_job.exception = job['exception']
                        this_job.end_time = timezone.now()
                        metrics_job_failed_count.labels(node.machine_name).inc()

                    # Update parent job, if it exists
                    this_job.save()
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

        if node.status == 'accepting' and (node.aws_instance_id is None or node.aws_instance_state=='running'):

            data['jobs'] = []
            data['jobs_to_kill'] = []
            data['req_restart'] = node.req_restart

            # Scheduler, reserve some tasks for specific machines
            if not node.req_restart:
                try:
                    with transaction.atomic():

                        # Classes representing 2 different job channels, one for light jobs,  one for heavy jobs
                        # These two channels will be executing concurrently on the machines
                        light_job_classes = ['jobs.thumbnails.GenerateThumbnail', 
                                             'jobs.test.SpeedTest']
                        class Channel():                        
                            def __init__(self):
                                self.max_instances = 1
                                self.nb_running = FarmJob.objects.filter(status='running', node=node).filter(self.filter_q()).count()
                            def can_run(self):
                                return self.nb_running < self.max_instances
                        class LightChannel(Channel):
                            def filter_q(self):
                                return Q(job_class__in=light_job_classes)
                        class HeavyChannel(Channel):
                            def filter_q(self):
                                return ~Q(job_class__in=light_job_classes)
                        
                        channels = [LightChannel(), HeavyChannel()]

                        if True in [c.can_run() for c in channels]:
                            
                            # Query for all jobs we could run on this node
                            if node.active:
                                next_jobs = FarmJob.objects.select_for_update().filter(status='ready', req_version__lte=node.code_version).filter(Q(node=node) | Q(node=None)).filter(job_class__in=available_jobs).exclude(tags__name__in=excluded_tags)
                            else:
                                next_jobs = FarmJob.objects.select_for_update().filter(status='ready', req_version__lte=node.code_version).filter(Q(node=node)).filter(job_class__in=available_jobs).exclude(tags__name__in=excluded_tags)

                            # Add filter for GPU 
                            if node.gpu_count <= 0:
                                next_jobs = next_jobs.filter(req_gpu=False)

                            # Sort jobs by priority
                            next_jobs = next_jobs.order_by('-priority')

                            # Create filters for each channel
                            filter_q_list = [c.filter_q() for c in channels if c.can_run()]
                            if filter_q_list:

                                # Apply filter for each channel
                                next_jobs = next_jobs.filter(or_list(filter_q_list))
                            
                                # Go thru each job, check dependency, and exit as soon as one good job is found
                                for next_job in next_jobs:

                                    # Check Job Dependencies (filter if that there are no dependencies that are not 'success')
                                    if next_job.dependencies.filter(~Q(status='success')).count()==0:
                                        
                                        # TODO This should be in the same query, otherwise we may be looping for no reason
                                    
                                        g_logger.info('Job #%s RESERVED for %s' % (next_job.id, node.machine_name))    

                                        # Make sure there are no child on this job
                                        next_job.children.all().delete()
                                    
                                        # Send a single job to this machine
                                        next_job.status = 'reserved'
                                        next_job.node = node
                                        next_job.exception = None
                                        next_job.start_time = timezone.now()
                                        next_job.save()

                                        break

                except Exception as e:
                    client.captureException()
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

            metrics_client_nb_running.labels(node.machine_name).set(node.jobs.filter(status='running').count())

        return JSONResponse(data)

class FarmGroupsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = FarmNodeGroup.objects.all().order_by('name')
    serializer_class = FarmNodeGroupSerializer

class FarmNodeViewSet(viewsets.ModelViewSet):

    filter_backends = (filters.DjangoFilterBackend, )
    filter_fields = ('status', 'active', )

    queryset = FarmNode.objects.all().order_by('status', 'machine_name')
    serializer_class = FarmNodeSerializer

class RecentFarmJobsViewSet(viewsets.ModelViewSet):

    filter_backends = (filters.DjangoFilterBackend, filters.SearchFilter,)
    filter_fields = ('status', )
    search_fields = ('job_class', 'node__machine_name', 'created_by')
        
    queryset = FarmJob.objects.filter(Q(parent=None) | Q(status='running')).order_by('-modified')
    serializer_class = FarmJobSerializer

class RecentFinishedFarmJobsViewSet(viewsets.ModelViewSet):

    filter_backends = (filters.DjangoFilterBackend, filters.SearchFilter,)
    filter_fields = ('status', )
    search_fields = ('job_class', 'node__machine_name', 'created_by')
        
    queryset = FarmJob.objects.filter(Q(parent=None) & (Q(status='success') | Q(status='failed'))).order_by('-modified')
    serializer_class = FarmJobSerializer

class FarmJobsViewSet(viewsets.ModelViewSet):

    filter_backends = (filters.DjangoFilterBackend, filters.SearchFilter,)
    filter_fields = ('status', )
    search_fields = ('job_class', 'node__machine_name', 'created_by')
        
    queryset = FarmJob.objects.order_by('-modified')
    serializer_class = FarmJobSerializer
