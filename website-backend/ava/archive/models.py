#
# Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved
#

from __future__ import unicode_literals
from django.db import models
from django.db.models import Sum, Max, Q
from django.apps import apps
from model_utils import Choices
from model_utils.fields import StatusField

import os

class Project(models.Model):
    name = models.CharField(max_length=200)
    archived = models.BooleanField(default=False)

    def best_staticscanassets(self):
        # Return all StaticScanAsset related to this Project
        return StaticScanAsset.objects.filter(project=self, take__flag='best').order_by('id')

    def calib_staticscanassets(self):
        # Return all StaticScanAsset related to this Project
        return StaticScanAsset.objects.filter(project=self).filter(Q(take__flag='calib') | Q(take__flag='colorchart')).order_by('id')

    def all_trackingassets(self):
        # Return all TrackingAssets related to this Project
        return TrackingAsset.objects.filter(take__shot__session__project=self).order_by('id')

    def best_trackingassets(self):
        # Return all TrackingAssets related to this Project
        return TrackingAsset.objects.filter(take__shot__session__project=self, take__flag='best').order_by('id')

    def bested_takes(self):
        return Take.objects.filter(shot__session__project=self, flag='best').order_by('id')

    def calib_takes(self):
        # Return all Calibration takes related to this Project
        return Take.objects.filter(shot__session__project=self).filter(flag='calib').order_by('id')

    def colorchart_takes(self):
        # Return all Color Chart takes related to this Project
        return Take.objects.filter(shot__session__project=self).filter(flag='colorchart').order_by('id')

    def singleframe_takes(self):
        # Return all Bested Single Frame Takes
        return Take.objects.filter(shot__session__project=self, flag='best').annotate(max_frame_count=Max('cameras__frame_count')).filter(max_frame_count=1).order_by('id')

    def __str__(self):
        return self.name

class Session(models.Model):

    name = models.CharField(max_length=200)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='sessions')
    start_time = models.DateTimeField('start time', auto_now_add=True)

    frontal_cam_id = models.CharField(max_length=200, null=True, blank=True)

    # Some takes can have a specific meaning
    session_master_calib = models.ForeignKey('Take', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    session_master_colorchart = models.ForeignKey('Take', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    session_neutral_take = models.ForeignKey('Take', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')

    # This is only used to fix sessions where the polarizers were inverted (90 degrees off)
    invert_polarization = models.BooleanField(default=False)

    def get_neutral_work_folder(self):
        # if there is a StaticSsset associated with the neutral take, return its work folder, otherwise return the work folder of the Take
        if not self.session_neutral_take:
            return None
        scan = apps.get_model(app_label='archive', model_name='StaticScanAsset').objects.all().filter(take=self.session_neutral_take)
        if scan:
            return scan[0].work_folder
        return self.session_neutral_take.work_folder

    def get_neutral_frame(self):
        # if there is a static asset associated with the neutral take, return its mixed_w frame, otherwise
        # return 0 for single-frame takes.
        if not self.session_neutral_take:
            return None
        scan = apps.get_model(app_label='archive', model_name='StaticScanAsset').objects.all().filter(take=self.session_neutral_take)
        if scan and scan[0].has_tracking:
            # If a scan exist for this take, use it to find the frame index corresponding to mixed_w
            # TODO Note that we are using the first scan for the take, so only 1 scan per take is supported at this time for the neutral
            framerate = self.session_neutral_take.frontal_framerate()
            if framerate:
                return int(scan[0].take_mixed_w_time * framerate)

        return 0

    def session_master_calib_path(self):
        if self.session_master_calib and self.session_master_calib.work_folder:
            return os.path.join(self.session_master_calib.work_folder, 'session_calib.xml')
        else:
            return None

    def session_master_colorchart_path(self):
        if self.session_master_colorchart and self.session_master_colorchart.work_folder:
            return os.path.join(self.session_master_colorchart.work_folder, 'colorcorrection_crosspolarized.txt')
        else:
            return None

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


class AddDependency():
    # Helper to create the dependency rules for Jobs on Assets

    class Target():
        def __init__(self, model, label, job_class, tags, options):
            self.job_class = job_class
            self.label = label
            self.tags = tags
            self.options = options

    def __init__(self, model, label, job_class, tags=[], options=[]):
        self.allow = True
        self.reason = ''
        self.targets = [AddDependency.Target(model, tl, tc, tags, options) for tl,tc in zip(label.split('|'),job_class.split('|'))]
        self.done = model.ext_jobs.filter(job_class__in=job_class.split('|')).filter(Q(status='success')|Q(status='ready')|Q(status='running')|Q(status='waiting')).exists()
    def make_fail_if(self, condition, reason):
        if condition:
            self.allow = False
            self.reason = reason
    def make_fail(self, reason):
        self.make_fail_if(True, reason)
    def job_success(self, model, dep_job_class):
        if self.allow:
            for c in dep_job_class.split('|'):
                job_exists = model.ext_jobs.filter(job_class=c, status='success').exists()
                if job_exists:
                    return self
            self.make_fail('Missing successful job %s for %s' % (dep_job_class,model) )
        return self
    def condition(self, success, reason):
        if self.allow:
            self.make_fail_if(not success, reason)
        return self
    def add_to(self, l):
        jobs = [{'label':target.label, 'class':target.job_class, 'tags':target.tags, 'options':target.options} for target in self.targets]
        l.append( {'done':self.done, 'allow':self.allow, 'reason':self.reason, 'jobs':jobs} )

class Take(models.Model):
    name = models.CharField(max_length=200)
    shot = models.ForeignKey(Shot, on_delete=models.CASCADE, related_name='takes')
    capture_time = models.DateTimeField('capture time', auto_now_add=True)
    sequence = models.IntegerField(default=1)
    export_path = models.CharField(max_length=250, null=True, blank=True)
    work_folder = models.CharField(max_length=250, null=True, blank=True)
    video_thumb = models.CharField(max_length=250, null=True, blank=True)

    FLAG = Choices('none', 'best', 'bad', 'calib', 'colorchart')
    flag = StatusField(choices_name='FLAG', default='none', db_index=True)

    is_burst = models.BooleanField(default=False)
    is_scan_burst = models.BooleanField(default=False)

    colorspace = models.CharField(max_length=32, null=True, blank=True) # Linear16, raw, sRGB

    def get_allowed_actions(self):
        # Returns list of jobs we can run on this asset
        allowed_jobs = []
        return allowed_jobs

    def sorted_cameras(self):
        return self.cameras.all().order_by('unique_id')

    def frontal_framerate(self):
        cam = self.cameras.filter(unique_id=self.shot.session.frontal_cam_id)
        if cam:
            return cam[0].framerate
        return None

    def has_write_access(self, user):
        # TODO Access rights
        return user.is_superuser

    def frame_count(self):
        return self.cameras.all().aggregate(Max('frame_count'))['frame_count__max']

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
    exposure_ms = models.FloatField(default=0.0)

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
    take_neutral_start_time = models.FloatField(null=True, blank=True)
    take_neutral_end_time = models.FloatField(null=True, blank=True)
    take_mixed_w_time = models.FloatField(null=True, blank=True)
    take_pattern_start_time = models.FloatField(null=True, blank=True)
    take_pattern_last_time = models.FloatField(null=True, blank=True)
    has_tracking = models.BooleanField(default=True)

    associated_tracking_asset = models.ForeignKey('TrackingAsset', on_delete=models.SET_NULL, related_name='%(class)s_related', null=True, blank=True)
    associated_tracking_asset_time = models.FloatField(null=True, blank=True)

    def scanAssetHasSequence(self):
        return None not in [self.take_neutral_start_time, self.take_neutral_end_time, self.take_mixed_w_time, self.take_pattern_start_time, self.take_pattern_last_time]

    def get_allowed_actions(self):

        allowed_jobs = []
        return allowed_jobs

    def __str__(self):
        return '#%d-%s' % (self.id, self.name)

class TrackingAsset(models.Model):
    take = models.ForeignKey(Take, on_delete=models.CASCADE, related_name='%(class)s_related')
    calib_file = models.CharField(max_length=255, null=True, blank=True)
    work_folder = models.CharField(max_length=255, null=True, blank=True)

    start_time = models.FloatField(default=0)
    end_time = models.FloatField(default=0)

    video_thumb = models.CharField(max_length=250, null=True, blank=True)

    def get_allowed_actions(self):
        # Returns list of jobs we can run on this asset
        allowed_jobs = []
        return allowed_jobs

    def __str__(self):
        return '#%d' % (self.id)
