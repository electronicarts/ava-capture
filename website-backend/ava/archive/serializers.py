#
# Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved
#


from archive.models import Project, Session, Shot, Take, Camera, StaticScanAsset, TrackingAsset
from rest_framework import serializers

from ava.settings import BASE_DIR
from base64 import b64decode
import uuid
import os

from jobs.serializers import SimpleFarmJobSerializer

class StaticScanAssetFromTakeSerializer(serializers.ModelSerializer):

    take_id = serializers.PrimaryKeyRelatedField(source='take', read_only=True)

    class Meta:
        model = StaticScanAsset
        fields = ('id', 'name', 'image_folder', 'calib_file', 'work_folder',
            'thumbnail_filename', 'take_id', 'has_tracking',
            'take_mixed_w_time', 'take_pattern_start_time', 'take_pattern_last_time', 'take_neutral_start_time', 'take_neutral_end_time')

class TrackingAssetFromTakeSerializer(serializers.ModelSerializer):

    take_id = serializers.PrimaryKeyRelatedField(source='take', read_only=True)

    class Meta:
        model = TrackingAsset
        fields = ('id', 'calib_file', 'start_time', 'end_time', 'video_thumb', 'take_id')

class CameraSerializer(serializers.HyperlinkedModelSerializer):

    b64_thumb = serializers.CharField(max_length=1024*1024, write_only=True, allow_null=True)

    def validate(self, data):
        if 'b64_thumb' in data:
            # Special write_only serializer for thumbnail, the field b64_thumb contains a base64 encoded
            # thumbnail, it will be writen to disk and converted to the field 'thumbnail_filename'.

            b64_thumb = data['b64_thumb']
            del data['b64_thumb']

            try:

                filename = '%s_%s.jpg' % (uuid.uuid4(), data['unique_id'])
                filepath = os.path.join(BASE_DIR, 'static', 'thumb', filename)

                jpg_data = b64decode(b64_thumb)
                with open(filepath, 'wb') as f:
                    f.write(jpg_data)

                data['thumbnail_filename'] = filename

            except:

                print('Could not decode and store thumbnail')


        return data

    class Meta:
        model = Camera
        fields = ('id', 'b64_thumb', 'machine_name', 'unique_id', 'model', 'version', 'using_sync', 'thumbnail_filename', 'folder',
            'width', 'height', 'frame_count', 'dropped_frames', 'framerate', 'total_size', 'duration', 'bitdepth', 'all_files', 'rotation', 'exposure_ms')

class MinimalTakeSerializer(serializers.ModelSerializer):

    shot_name = serializers.ReadOnlyField(source='shot.name')
    session_name = serializers.ReadOnlyField(source='shot.session.name')

    class Meta:
        model = Take
        fields = ('id', 'name', 'shot_name', 'session_name')

class TakeSerializer(serializers.HyperlinkedModelSerializer):

    cameras = CameraSerializer(many=True)
    capture_time = serializers.DateTimeField()

    total_size = serializers.ReadOnlyField()
    write_access = serializers.SerializerMethodField()

    related_jobs = SimpleFarmJobSerializer(many=True, read_only=True, source='ext_jobs')
    related_staticscans = StaticScanAssetFromTakeSerializer(many=True, read_only=True, source='staticscanasset_related')
    related_trackingassets = TrackingAssetFromTakeSerializer(many=True, read_only=True, source='trackingasset_related')

    # These fields are related to the Session
    frontal_cam_uid = serializers.ReadOnlyField(source='shot.session.frontal_cam_id')
    invert_polarization = serializers.ReadOnlyField(source='shot.session.invert_polarization')
    session_master_calib_path = serializers.ReadOnlyField(source='shot.session.session_master_calib_path')
    session_master_colorchart_path = serializers.ReadOnlyField(source='shot.session.session_master_colorchart_path')
    session_neutral_work_path = serializers.ReadOnlyField(source='shot.session.get_neutral_work_folder')
    session_neutral_take_frame = serializers.ReadOnlyField(source='shot.session.get_neutral_frame')

    # These fields are related to the Shot
    shot_name = serializers.ReadOnlyField(source='shot.name')
    shot_id = serializers.PrimaryKeyRelatedField(source='shot', read_only=True)

    allowed_actions = serializers.ReadOnlyField(source='get_allowed_actions')
    max_frame_count = serializers.ReadOnlyField(source='frame_count')

    def get_write_access(self, obj):
        return obj.has_write_access(self.context['request'].user)

    class Meta:
        model = Take
        fields = ('id', 'name', 'shot_name', 'shot_id', 'sequence', 'capture_time', 'flag', 'is_scan_burst', 'is_burst',
            'cameras', 'total_size', 'write_access', 'max_frame_count',
            'related_jobs', 'export_path', 'colorspace', 'work_folder', 'video_thumb', 'frontal_cam_uid', 'related_staticscans', 'related_trackingassets',
            'session_master_calib_path', 'session_master_colorchart_path', 'session_neutral_work_path', 'session_neutral_take_frame', 'allowed_actions', 'invert_polarization')

class ShotSerializer(serializers.HyperlinkedModelSerializer):

    takes = TakeSerializer(many=True)

    session_id = serializers.PrimaryKeyRelatedField(source='session', required=False, queryset=Session.objects.all())

    def create(self, validated_data):
        takes_data = validated_data.pop('takes')
        shot = Shot.objects.create(**validated_data)
        for take_data in takes_data:
            if 'cameras' in take_data:
                cameras_data = take_data.pop('cameras')
                take = Take.objects.create(shot=shot, **take_data)
                for camera_data in cameras_data:
                    Camera.objects.create(take=take, **camera_data)
            else:
                Take.objects.create(shot=shot, **take_data)

        return shot

    class Meta:
        model = Shot
        fields = ('id', 'name', 'takes', 'session_id')

class ProjectSpecialTakesSerializer(serializers.ModelSerializer):

    calib_takes = MinimalTakeSerializer(many=True, read_only=True)
    colorchart_takes = MinimalTakeSerializer(many=True, read_only=True)
    bested_takes = MinimalTakeSerializer(many=True, read_only=True)

    class Meta:
        model = Project
        fields = ('id', 'calib_takes', 'colorchart_takes', 'bested_takes')

class SessionDetailsSerializer(serializers.HyperlinkedModelSerializer):

    session_master_calib_id = serializers.PrimaryKeyRelatedField(source='session_master_calib', queryset=Take.objects.all(), allow_null=True)
    session_master_colorchart_id = serializers.PrimaryKeyRelatedField(source='session_master_colorchart', queryset=Take.objects.all(), allow_null=True)
    session_neutral_take_id = serializers.PrimaryKeyRelatedField(source='session_neutral_take', queryset=Take.objects.all(), allow_null=True)

    shots = ShotSerializer(many=True, read_only=True)
    project_name = serializers.ReadOnlyField(source='project.name')

    project_special = ProjectSpecialTakesSerializer(read_only=True, source='project')

    class Meta:
        model = Session
        fields = ('id', 'name', 'start_time', 'shots', 'project_name', 'frontal_cam_id', 'session_master_calib_id', 'session_master_colorchart_id', 'session_neutral_take_id', 'project_special')

class SessionSerializer(serializers.HyperlinkedModelSerializer):

    project_id = serializers.PrimaryKeyRelatedField(queryset=Project.objects.all())
    project_name = serializers.ReadOnlyField(source='project.name')

    class Meta:
        model = Session
        fields = ('id', 'project_id', 'name', 'start_time', 'shot_count', 'take_count', 'frontal_cam_id', 'project_name')

class ProjectSerializer(serializers.HyperlinkedModelSerializer):

    sessions = SessionSerializer(many=True, read_only=True)

    class Meta:
        model = Project
        fields = ('id', 'name', 'sessions')

# Serializers for Export/Import from different servers

class SessionExportSerializer(serializers.ModelSerializer):

    project_id = serializers.PrimaryKeyRelatedField(queryset=Project.objects.all())
    start_time = serializers.DateTimeField()
    shots = ShotSerializer(many=True)

    def create(self, validated_data):
        shots_data = validated_data.pop('shots')
        project = validated_data.pop('project_id')
        session = Session.objects.create(project=project, **validated_data)
        for shot_data in shots_data:
            takes_data = shot_data.pop('takes')
            shot = Shot.objects.create(session=session, **shot_data)
            for take_data in takes_data:
                if 'cameras' in take_data:
                    cameras_data = take_data.pop('cameras')
                    take = Take.objects.create(shot=shot, **take_data)
                    for camera_data in cameras_data:
                        Camera.objects.create(take=take, **camera_data)
                else:
                    Take.objects.create(shot=shot, **take_data)

        return session

    class Meta:
        model = Session
        fields = ('id', 'project_id', 'name', 'start_time', 'shots', 'frontal_cam_id')

# Assets

class StaticScanAssetSerializer(serializers.ModelSerializer):

    project_id = serializers.PrimaryKeyRelatedField(source='project', queryset=Project.objects.all())

    take_id = serializers.PrimaryKeyRelatedField(source='take', queryset=Take.objects.all())
    take_name = serializers.ReadOnlyField(source='take.name')
    take_flag = serializers.ReadOnlyField(source='take.flag')
    take_path = serializers.ReadOnlyField(source='take.export_path')

    associated_tracking_asset_id = serializers.PrimaryKeyRelatedField(source='associated_tracking_asset', required=False, queryset=TrackingAsset.objects.all())

    shot_name = serializers.ReadOnlyField(source='take.shot.name')

    related_jobs = SimpleFarmJobSerializer(many=True, read_only=True, source='ext_jobs')

    allowed_actions = serializers.ReadOnlyField(source='get_allowed_actions')

    class Meta:
        model = StaticScanAsset
        fields = ('id', 'name', 'image_folder', 'calib_file', 'work_folder',
            'related_jobs', 'thumbnail_filename', 'project_id',
            'take_id', 'take_name', 'take_flag', 'shot_name', 'take_path', 'has_tracking',
            'take_mixed_w_time', 'take_pattern_start_time', 'take_pattern_last_time', 'take_neutral_start_time', 'take_neutral_end_time', 'allowed_actions',
            'associated_tracking_asset_id', 'associated_tracking_asset_time')

class TrackingAssetTakeSerializer(serializers.ModelSerializer):

    take = TakeSerializer()

    class Meta:
        model = TrackingAsset
        fields = ('id', 'calib_file', 'work_folder', 'start_time', 'end_time', 'take', 'video_thumb')

class TrackingAssetSerializer(serializers.ModelSerializer):

    take_id = serializers.PrimaryKeyRelatedField(source='take', queryset=Take.objects.all())
    take_name = serializers.ReadOnlyField(source='take.name')
    take_flag = serializers.ReadOnlyField(source='take.flag')
    take_export_path = serializers.ReadOnlyField(source='take.export_path')

    shot_name = serializers.ReadOnlyField(source='take.shot.name')

    related_jobs = SimpleFarmJobSerializer(many=True, read_only=True, source='ext_jobs')

    allowed_actions = serializers.ReadOnlyField(source='get_allowed_actions')

    class Meta:
        model = TrackingAsset
        fields = ('id', 'calib_file', 'start_time', 'end_time', 'video_thumb', 'take_id', 'work_folder', 'take_name', 'take_flag', 'shot_name', 'take_export_path', 'related_jobs', 'allowed_actions')

class ProjectArchiveSerializer(serializers.ModelSerializer):

    sessions = SessionDetailsSerializer(many=True, read_only=True)

    class Meta:
        model = Project
        fields = ('id', 'name', 'sessions')

class ProjectAssetSerializer(serializers.ModelSerializer):

    sessions = SessionSerializer(many=True, read_only=True)

    staticscanasset_best = StaticScanAssetSerializer(many=True, read_only=True, source='best_staticscanassets')
    staticscanasset_calib = StaticScanAssetSerializer(many=True, read_only=True, source='calib_staticscanassets')
    trackingassets_best = TrackingAssetSerializer(many=True, read_only=True, source='best_trackingassets')
    calibration_takes = TakeSerializer(many=True, read_only=True, source='calib_takes')
    colorchart_takes = TakeSerializer(many=True, read_only=True)
    single_frame_takes = TakeSerializer(many=True, read_only=True, source='singleframe_takes')

    class Meta:
        model = Project
        fields = ('id', 'name', 'sessions', 'staticscanasset_best', 'staticscanasset_calib', 'trackingassets_best', 'calibration_takes', 'colorchart_takes', 'single_frame_takes')

