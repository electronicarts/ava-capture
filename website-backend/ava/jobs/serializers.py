#
# Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
#

from models import FarmNode, FarmJob, FarmNodeGroup
from rest_framework import serializers
from django.contrib.auth.models import User
from django_gravatar.helpers import get_gravatar_url

from archive.models import Take, StaticScanAsset, TrackingAsset

class SimpleFarmNodeSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = FarmNode
        fields = ('id', 'machine_name')

class SimpleFarmJobSerializer(serializers.ModelSerializer):
    
    image_filename = serializers.CharField(read_only=True)

    class Meta:
        model = FarmJob
        fields = ('job_class', 'id', 'status', 'image_filename')

class FarmJobSerializer(serializers.ModelSerializer):
    
    node = SimpleFarmNodeSerializer(read_only=True)
    node_name = serializers.SlugRelatedField(source='node', many=False, read_only=False, slug_field='machine_name', allow_null=True, required=False, queryset=FarmNode.objects.all())

    write_access = serializers.SerializerMethodField()

    parent_id = serializers.PrimaryKeyRelatedField(source='parent', queryset=FarmJob.objects.all(), allow_null=True, required=False)

    ext_take_id = serializers.PrimaryKeyRelatedField(source='ext_take', queryset=Take.objects.all(), allow_null=True)
    ext_scan_assets_id = serializers.PrimaryKeyRelatedField(source='ext_scan_assets', queryset=StaticScanAsset.objects.all(), allow_null=True)
    ext_tracking_assets_id = serializers.PrimaryKeyRelatedField(source='ext_tracking_assets', queryset=TrackingAsset.objects.all(), allow_null=True)

    ext_take_name = serializers.StringRelatedField(source='ext_take', read_only=True)
    ext_scan_assets_name = serializers.StringRelatedField(source='ext_scan_assets', read_only=True)
    ext_tracking_assets_name = serializers.StringRelatedField(source='ext_tracking_assets', read_only=True)

    created_by = serializers.CharField(required=False) # if not specified, will be set from the request User

    image_filename = serializers.CharField(required=False)

    def create(self, validated_data):
        if not 'created_by' in validated_data:
            validated_data['created_by'] = self.context['request'].user.username
        return FarmJob.objects.create(**validated_data)

    def get_write_access(self, obj):
        return obj.has_write_access(self.context['request'].user)

    def get_gravatar(self, obj):
        user = User.objects.all().filter(username=obj.created_by)
        if user:
            return get_gravatar_url(user[0].email, size=50)
        return None

    class Meta:
        model = FarmJob
        fields = ('job_class', 'id', 'parent_id', 'created_by', 'status', 'node', 'node_name', 'status_changed', 'created', 'modified', 'write_access', 'progress', 
            'start_time', 'end_time', 'req_gpu', 'req_version', 'params',
            'ext_take_id', 'ext_scan_assets_id', 'ext_tracking_assets_id', 'ext_take_name', 'ext_scan_assets_name', 'ext_tracking_assets_name', 'priority', 'image_filename')

class FarmJobDetailedSerializer(serializers.ModelSerializer):
    
    node = SimpleFarmNodeSerializer(read_only=True)
    parent = FarmJobSerializer(read_only=True)
    children = FarmJobSerializer(many=True, read_only=True)
    dependencies = FarmJobSerializer(many=True, read_only=True)

    write_access = serializers.SerializerMethodField()

    ext_take_id = serializers.PrimaryKeyRelatedField(source='ext_take', read_only=True)
    ext_scan_assets_id = serializers.PrimaryKeyRelatedField(source='ext_scan_assets', read_only=True)
    ext_tracking_assets_id = serializers.PrimaryKeyRelatedField(source='ext_tracking_assets', read_only=True)

    ext_take_name = serializers.StringRelatedField(source='ext_take', read_only=True)
    ext_scan_assets_name = serializers.StringRelatedField(source='ext_scan_assets', read_only=True)
    ext_tracking_assets_name = serializers.StringRelatedField(source='ext_tracking_assets', read_only=True)

    image_filename = serializers.CharField(read_only=True)

    def get_write_access(self, obj):
        return obj.has_write_access(self.context['request'].user)

    class Meta:
        model = FarmJob
        fields = ('job_class', 'id', 'created_by', 'params', 'exception', 'status', 'node', 'status_changed', 'created', 'modified', 'parent', 'children', 
            'dependencies', 'progress', 'start_time', 'end_time', 'req_version', 'req_gpu', 
            'ext_take_id', 'ext_scan_assets_id', 'ext_tracking_assets_id', 'ext_take_name', 'ext_scan_assets_name', 'ext_tracking_assets_name', 'priority', 'write_access', 'image_filename')

class FarmNodeSerializer(serializers.ModelSerializer):
    
    active = serializers.BooleanField(source='is_active', read_only=True) # Connected and listenning to commands
    status = serializers.CharField(source='actual_status', read_only=True)
    running_jobs = FarmJobSerializer(many=True, read_only=True)

    accepting = serializers.BooleanField(source='active', read_only=True) # Accepting jobs

    group = serializers.SlugRelatedField(many=False, read_only=False, slug_field='name', allow_null=True, required=False, queryset=FarmNodeGroup.objects.all())

    class Meta:
        model = FarmNode
        fields = ('ip_address', 'id', 'machine_name', 'last_seen', 'status', 'active', 'running_jobs', 'system', 'code_version', 'cpu_brand', 'cpu_percent', 'cpu_cores', 'gpu_count', 'accepting', 'group')

class FarmNodeGroupSerializer(serializers.ModelSerializer):

    nodes = FarmNodeSerializer(many=True)

    class Meta:
        model = FarmNodeGroup
        fields = ('name', 'nodes')

