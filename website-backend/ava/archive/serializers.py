#
# Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
#


from models import Project, Session, Shot, Take, Camera, StaticScanAsset, TrackingAsset
from rest_framework import serializers

from jobs.serializers import SimpleFarmJobSerializer

class StaticScanAssetFromTakeSerializer(serializers.ModelSerializer):

    class Meta:
        model = StaticScanAsset
        fields = ('id', 'name', 'image_folder', 'calib_file', 'work_folder', 
            'thumbnail_filename', 
            'take_mixed_w_time', 'take_pattern_start_time', 'take_pattern_last_time')

class CameraSerializer(serializers.HyperlinkedModelSerializer):    

    class Meta:
        model = Camera
        fields = ('id', 'machine_name', 'unique_id', 'model', 'version', 'using_sync', 'thumbnail_filename', 'folder',
            'width', 'height', 'frame_count', 'dropped_frames', 'framerate', 'total_size', 'duration', 'bitdepth', 'all_files', 'rotation')

class TakeSerializer(serializers.HyperlinkedModelSerializer):    

    cameras = CameraSerializer(many=True)
    capture_time = serializers.DateTimeField()

    total_size = serializers.ReadOnlyField()
    write_access = serializers.SerializerMethodField()

    related_jobs = SimpleFarmJobSerializer(many=True, read_only=True, source='ext_jobs')
    related_staticscans = StaticScanAssetFromTakeSerializer(many=True, read_only=True, source='staticscanasset_related')

    frontal_cam_uid = serializers.ReadOnlyField(source='shot.session.frontal_cam_id')

    def get_write_access(self, obj):
        return obj.has_write_access(self.context['request'].user)

    class Meta:
        model = Take
        fields = ('id', 'name', 'sequence', 'capture_time', 'flag', 'cameras', 'total_size', 'write_access', 'related_jobs', 'export_path', 'video_thumb', 'frontal_cam_uid', 'related_staticscans')

class ShotSerializer(serializers.HyperlinkedModelSerializer):    

    takes = TakeSerializer(many=True)

    class Meta:
        model = Shot
        fields = ('id', 'name', 'takes')

class SessionDetailsSerializer(serializers.HyperlinkedModelSerializer):
    
    shots = ShotSerializer(many=True, read_only=True)
    project_name = serializers.ReadOnlyField(source='project.name')    

    class Meta:
        model = Session
        fields = ('id', 'name', 'start_time', 'shots', 'project_name', 'frontal_cam_id')

class SessionSerializer(serializers.HyperlinkedModelSerializer):    

    class Meta:
        model = Session
        fields = ('id', 'name', 'start_time', 'shot_count', 'take_count', 'frontal_cam_id')

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
        fields = ('project_id', 'name', 'start_time', 'shots', 'frontal_cam_id')

# Assets

class StaticScanAssetSerializer(serializers.ModelSerializer):

    related_jobs = SimpleFarmJobSerializer(many=True, read_only=True, source='ext_jobs')
    project_id = serializers.PrimaryKeyRelatedField(source='project', queryset=Project.objects.all())

    take_id = serializers.PrimaryKeyRelatedField(source='take', queryset=Take.objects.all())
    take_name = serializers.ReadOnlyField(source='take.name')

    class Meta:
        model = StaticScanAsset
        fields = ('id', 'name', 'image_folder', 'calib_file', 'work_folder', 
            'related_jobs', 'thumbnail_filename', 'project_id',
            'take_id', 'take_name', 
            'take_mixed_w_time', 'take_pattern_start_time', 'take_pattern_last_time')

class TrackingAssetTakeSerializer(serializers.ModelSerializer):    

    take = TakeSerializer()

    class Meta:
        model = TrackingAsset
        fields = ('id', 'calib_file', 'start_time', 'end_time', 'take', 'video_thumb')

class TrackingAssetSerializer(serializers.ModelSerializer):    

    take_id = serializers.PrimaryKeyRelatedField(source='take', queryset=Take.objects.all())
    take_name = serializers.ReadOnlyField(source='take.name')
    take_export_path = serializers.ReadOnlyField(source='take.export_path')    

    related_jobs = SimpleFarmJobSerializer(many=True, read_only=True, source='ext_jobs')

    class Meta:
        model = TrackingAsset
        fields = ('id', 'calib_file', 'start_time', 'end_time', 'video_thumb', 'take_id', 'take_name', 'take_export_path', 'related_jobs')

class ProjectArchiveSerializer(serializers.ModelSerializer):

    sessions = SessionDetailsSerializer(many=True, read_only=True)

    class Meta:
        model = Project
        fields = ('id', 'name', 'sessions')

class ProjectAssetSerializer(serializers.ModelSerializer):
    
    staticscanasset_related = StaticScanAssetSerializer(many=True, read_only=True)
    trackingassets_related = TrackingAssetSerializer(many=True, read_only=True, source='all_trackingassets')

    class Meta:
        model = Project
        fields = ('id', 'name', 'staticscanasset_related', 'trackingassets_related')
