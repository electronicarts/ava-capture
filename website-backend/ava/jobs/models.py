#
# Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
#

from __future__ import unicode_literals

import datetime

from django.db import models
from django.utils import timezone

from model_utils.fields import MonitorField, StatusField
from model_utils.models import TimeStampedModel
from model_utils import Choices

from archive.models import Take, StaticScanAsset, TrackingAsset

class FarmNodeGroup(models.Model):
    name = models.CharField(max_length=200)

    def __str__(self):
        return '%s' % (self.name)

class FarmNode(models.Model):

    # Fields
    ip_address = models.CharField(max_length=200)
    machine_name = models.CharField(max_length=200)
    last_seen = models.DateTimeField('last seen', auto_now_add=True)

    code_version = models.IntegerField(default=1)
    req_restart = models.BooleanField(default=False)
    active = models.BooleanField(default=True) # Server-side active switch, set to false to prevent jobs from being dispatched to this node

    system = models.CharField(max_length=80, null=True)
    system_bits = models.IntegerField(null=True)
    cpu_brand = models.CharField(max_length=80, null=True)
    cpu_cores = models.IntegerField(null=True)
    gpu_count = models.IntegerField(null=True)
    cpu_percent = models.FloatField(default=0.0)

    STATUS = Choices('offline', 'accepting') # Client-side status, reported by the node itself
    status = StatusField()

    group = models.ForeignKey(FarmNodeGroup, on_delete=models.SET_NULL, null=True, blank=True, related_name='nodes')

    # TODO Add Features (string comma separated keywords)

    def has_write_access(self, user):
        # TODO Access rights
        return user.is_superuser

    def running_jobs(self):
        return self.jobs.filter(status='running')

    def actual_status(self):
        if not self.is_active():
            return 'offline'
        return self.status

    def is_active(self):
        return self.status=='accepting' and self.last_seen >= timezone.now() - datetime.timedelta(seconds=90)

    def __str__(self):
        return '%s' % (self.machine_name)

class FarmJob(TimeStampedModel):

    # Fields
    job_class = models.CharField(max_length=200)
    created_by = models.CharField(max_length=200)
    params = models.TextField(null=True, blank=True)
    exception = models.CharField(max_length=800, null=True, blank=True)
    node = models.ForeignKey(FarmNode, on_delete=models.CASCADE, null=True, blank=True, related_name='jobs')
    progress = models.CharField(max_length=200, null=True, blank=True)

    req_version = models.IntegerField(default=1)
    req_gpu = models.BooleanField(default=True)

    priority = models.IntegerField(default=50)

    # Relationships
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    dependencies = models.ManyToManyField('self', related_name='dependants', blank=True, symmetrical=False)

    # Job Status
    STATUS = Choices('created', 'ready', 'reserved', 'running', 'failed', 'success', 'waiting', 'terminating')
    status = StatusField()
    status.db_index = True
    status_changed = MonitorField(monitor='status', db_index=True)

    # Start/end time for the 'running' status
    start_time = models.DateTimeField('start time', null=True, blank=True)
    end_time = models.DateTimeField('end time', null=True, blank=True)

    # External Relationships
    ext_take = models.ForeignKey(Take, on_delete=models.SET_NULL, null=True, blank=True, related_name='ext_jobs')
    ext_scan_assets = models.ForeignKey(StaticScanAsset, on_delete=models.SET_NULL, null=True, blank=True, related_name='ext_jobs')
    ext_tracking_assets = models.ForeignKey(TrackingAsset, on_delete=models.SET_NULL, null=True, blank=True, related_name='ext_jobs')

    image_filename = models.CharField(max_length=250, null=True, blank=True)

    # TODO Requirements (must match Node Features) (string comma separated keywords)
    # TODO Start/stop time, duration
    # TODO Status change log ?

    def has_write_access(self, user):
        # TODO Access rights
        return self.created_by == user.username or user.is_superuser

    def __str__(self):
        return '#%d (%s) %s' % (self.id, self.job_class, self.status)

    def get_absolute_url(self):
        return "/static/d/index.html#/app/job_details/%i" % self.id
