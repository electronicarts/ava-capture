#
# Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
#

from __future__ import unicode_literals
from django.db import models
from django.db.models import Sum
from model_utils import Choices
from model_utils.fields import StatusField

class Project(models.Model):
    name = models.CharField(max_length=200)

    def all_trackingassets(self):
        # Return all TrackingAssets related to this Project
        return TrackingAsset.objects.filter(take__shot__session__project=self)

    def __str__(self):
        return self.name

class Session(models.Model):    
    name = models.CharField(max_length=200)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='sessions')
    start_time = models.DateTimeField('start time', auto_now_add=True)
    frontal_cam_id = models.CharField(max_length=200, null=True, blank=True)

    def shot_count(self):
        return self.shots.count()

    def take_count(self):
        return Take.objects.filter(shot__session=self).count()

    def full_name(self):
        return '%s/%s' % (self.name, self.project.name)

    def __str__(self):
        return '#%d' % (self.id)

    def get_absolute_url(self):
        return "/static/d/index.html#/app/archive-session/%i" % self.id

class Shot(models.Model):    
    name = models.CharField(max_length=200)
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='shots')
    next_take = models.IntegerField(default=1)

    def increment_take(self):
        self.next_take = self.next_take + 1
        self.save()

    def full_name(self):
        return '%s/%s' % (self.name, self.session.full_name())        

    def __str__(self):
        return '#%d' % (self.id)

class Take(models.Model):    
    name = models.CharField(max_length=200)
    shot = models.ForeignKey(Shot, on_delete=models.CASCADE, related_name='takes')
    capture_time = models.DateTimeField('capture time', auto_now_add=True)
    sequence = models.IntegerField(default=1)
    export_path = models.CharField(max_length=250, null=True, blank=True)
    video_thumb = models.CharField(max_length=250, null=True, blank=True)

    FLAG = Choices('none', 'best', 'bad')
    flag = StatusField(choices_name='FLAG', default='none')

    def has_write_access(self, user):
        # TODO Access rights
        return user.is_superuser

    def total_size(self):
        return self.cameras.all().aggregate(Sum('total_size'))['total_size__sum']

    def full_name(self):
        return '%s/%s' % (self.name, self.shot.full_name())        

    def __str__(self):
        return '#%d' % (self.id)

class Camera(models.Model):
    take = models.ForeignKey(Take, on_delete=models.CASCADE, related_name='cameras')

    machine_name = models.CharField(max_length=200)
    unique_id = models.CharField(max_length=200, db_index=True)
    model = models.CharField(max_length=200)
    version = models.CharField(max_length=200)
    using_sync = models.BooleanField(default=False)
    folder = models.CharField(max_length=250)
    thumbnail_filename = models.CharField(max_length=250, null=True, blank=True)
    width = models.IntegerField()
    height = models.IntegerField()
    bitdepth = models.IntegerField(default=8)
    frame_count = models.IntegerField()
    dropped_frames = models.IntegerField()
    total_size = models.BigIntegerField()
    duration = models.FloatField(default=0.0)
    framerate = models.FloatField(default=0.0)
    all_files = models.TextField(null=True)
    rotation = models.IntegerField(default=0)

    def full_name(self):
        return '%s(%s)/%s' % (self.unique_id, self.model, self.take.full_name())        

    def __str__(self):
        return '#%d' % (self.id)

    class Meta:
        ordering = ('unique_id',)

class StaticScanAsset(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='%(class)s_related')
    name = models.CharField(max_length=120)
    image_folder = models.CharField(max_length=255)
    calib_file = models.CharField(max_length=255)
    work_folder = models.CharField(max_length=255)
    thumbnail_filename = models.CharField(max_length=250, null=True, blank=True)

    # Related Take
    # One Take (so one AVI) can contain multiple Static Scans (wich basically represent a frame range)
    take = models.ForeignKey(Take, on_delete=models.SET_NULL, related_name='%(class)s_related', null=True, blank=True)

    # List of relevant frames in the take. (this could be generalized in a different table)
    take_neutral_start_time = models.FloatField(null=True, blank=True)
    take_neutral_end_time = models.FloatField(null=True, blank=True)
    take_mixed_w_time = models.FloatField(null=True, blank=True)
    take_pattern_start_time = models.FloatField(null=True, blank=True)
    take_pattern_last_time = models.FloatField(null=True, blank=True)


    def __str__(self):
        return '#%d-%s' % (self.id, self.name)

class TrackingAsset(models.Model):
    take = models.ForeignKey(Take, on_delete=models.CASCADE, related_name='%(class)s_related')
    calib_file = models.CharField(max_length=255)
    
    start_time = models.FloatField(default=0)
    end_time = models.FloatField(default=0)

    video_thumb = models.CharField(max_length=250, null=True, blank=True)

    def __str__(self):
        return '#%d' % (self.id)
