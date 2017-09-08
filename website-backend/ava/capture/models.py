#
# Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
#

from __future__ import unicode_literals
import datetime

from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

from archive.models import Project as ArchiveProject
from archive.models import Session as ArchiveSession
from archive.models import Shot as ArchiveShot

class CaptureLocation(models.Model):
    name = models.CharField(max_length=200)
    users = models.ManyToManyField(User, through='LocationAccess', related_name='access_rights')

    # Location Config
    hardware_sync_frequency = models.IntegerField(default=30)
    pulse_duration = models.IntegerField(default=2000)
    external_sync = models.BooleanField(default=False)
    display_focus_peak = models.BooleanField(default=False)
    display_overexposed = models.BooleanField(default=False)
    display_histogram = models.BooleanField(default=False)
    bitdepth_avi = models.IntegerField(default=8)
    bitdepth_single = models.IntegerField(default=12)

    cur_project = models.ForeignKey(ArchiveProject, on_delete=models.SET_NULL, null=True, default=None, blank=True)
    cur_session = models.ForeignKey(ArchiveSession, on_delete=models.SET_NULL, null=True, default=None, blank=True)
    cur_shot = models.ForeignKey(ArchiveShot, on_delete=models.SET_NULL, null=True, default=None, blank=True)

    read_access_all = models.BooleanField(default=False)

    def __str__(self):
        return self.name

class LocationAccess(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    location = models.ForeignKey(CaptureLocation, on_delete=models.CASCADE)
    read_access = models.BooleanField(default=False)
    write_access = models.BooleanField(default=False)

    def __str__(self):
        return '%s/%s' % (self.user, self.location.name)

class CaptureNode(models.Model):
    ip_address = models.CharField(max_length=200)
    machine_name = models.CharField(max_length=200)
    os = models.CharField(max_length=80, null=True)
    last_seen = models.DateTimeField('last seen', auto_now_add=True)
    online = models.BooleanField(default=False)
    location = models.ForeignKey(CaptureLocation, on_delete=models.SET_NULL, related_name='nodes', null=True)
    sync_found = models.BooleanField(default=False)
    drive_info = models.CharField(max_length=2048, default="")
    code_version = models.IntegerField(default=0)

    class Meta:
        permissions = (
            ("view_nodes", "Can see list of nodes and cameras"),
            ("control_cameras", "Can change camera settings and record"),
        )

    def is_active(self):
        return self.online and self.last_seen >= timezone.now() - datetime.timedelta(seconds=90)

    def __str__(self):
        return '%s (%s)' % (self.machine_name, self.ip_address)

class Camera(models.Model):
    node = models.ForeignKey(CaptureNode, on_delete=models.CASCADE, related_name='cameras')
    unique_id = models.CharField(max_length=200)
    model = models.CharField(max_length=200)
    version = models.CharField(max_length=200, default='')

    exposure = models.FloatField(default=5000.0)
    gain = models.FloatField(default=0.0)
    lens_aperture = models.FloatField(default=5.6)
    using_sync = models.BooleanField(default=True)
    rotation = models.IntegerField(default=0)

    def is_active(self):
        return self.node.is_active()

    def __str__(self):
        return '%s (%s) on %s' % (self.unique_id, self.model, self.node.machine_name)
