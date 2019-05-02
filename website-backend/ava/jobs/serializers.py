#
# Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
#

from models import FarmNode, FarmJob, FarmNodeGroup
from rest_framework import serializers
from django.contrib.auth.models import User
from django_gravatar.helpers import get_gravatar_url

from archive.models import Take, StaticScanAsset, TrackingAsset

from taggit_serializer.serializers import (TagListSerializerField,
                                           TaggitSerializer)

class CreatableSlugRelatedField(serializers.SlugRelatedField): # https://stackoverflow.com/questions/28009829/creating-and-saving-foreign-key-objects-using-a-slugrelatedfield

    def to_internal_value(self, data):
        try:
            return self.get_queryset().get_or_create(**{self.slug_field: data})[0]
        except ObjectDoesNotExist:
            self.fail('does_not_exist', slug_name=self.slug_field, value=smart_text(data))
        except (TypeError, ValueError):
            self.fail('invalid')

class SimpleFarmNodeSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = FarmNode
        fields = ('id', 'machine_name')

class SimpleFarmJobSerializer(serializers.ModelSerializer):
    
    image_filename = serializers.CharField(read_only=True)
    mesh_filename = serializers.CharField(read_only=True)

    class Meta:
        model = FarmJob
        fields = ('job_class', 'id', 'status', 'image_filename', 'mesh_filename')

class FarmJobSerializer(TaggitSerializer, serializers.ModelSerializer):
    
    node = SimpleFarmNodeSerializer(read_only=True)
    node_name = CreatableSlugRelatedField(source='node', many=False, read_only=False, slug_field='machine_name', allow_null=True, required=False, queryset=FarmNode.objects.all())

    write_access = serializers.SerializerMethodField()

    parent_id = serializers.PrimaryKeyRelatedField(source='parent', queryset=FarmJob.objects.all(), allow_null=True, required=False)
    dependencies_id = serializers.PrimaryKeyRelatedField(source='dependencies', queryset=FarmJob.objects.all(), many=True, allow_null=True, required=False)

    ext_take_id = serializers.PrimaryKeyRelatedField(source='ext_take', queryset=Take.objects.all(), allow_null=True)
    ext_scan_assets_id = serializers.PrimaryKeyRelatedField(source='ext_scan_assets', queryset=StaticScanAsset.objects.all(), allow_null=True)
    ext_tracking_assets_id = serializers.PrimaryKeyRelatedField(source='ext_tracking_assets', queryset=TrackingAsset.objects.all(), allow_null=True)

    ext_take_name = serializers.StringRelatedField(source='ext_take', read_only=True)
    ext_scan_assets_name = serializers.StringRelatedField(source='ext_scan_assets', read_only=True)
    ext_tracking_assets_name = serializers.StringRelatedField(source='ext_tracking_assets', read_only=True)

    ext_take_prj_id = serializers.PrimaryKeyRelatedField(source='ext_take.shot.session.project', read_only=True)
    ext_scan_assets_prj_id = serializers.PrimaryKeyRelatedField(source='ext_scan_assets.project', read_only=True)
    ext_tracking_assets_prj_id = serializers.PrimaryKeyRelatedField(source='ext_tracking_assets.take.shot.session.project', read_only=True)

    created_by = serializers.CharField(required=False) # if not specified, will be set from the request User

    image_filename = serializers.CharField(required=False)
    mesh_filename = serializers.CharField(required=False)

    tags = TagListSerializerField(required=False)

    def create(self, validated_data):
        
        # Set priority from parent if it is not specified
        if not 'priority' in validated_data and 'parent' in validated_data:
            # If we didn't set a priority explicitely, and we have a parent, inherit the priority
            if validated_data['parent']:
                validated_data['priority'] = validated_data['parent'].priority

        # Add created-by if it is missing
        if not 'created_by' in validated_data:
            validated_data['created_by'] = self.context['request'].user.username

        tags_data = validated_data.pop('tags') if 'tags' in validated_data else None

        obj = FarmJob.objects.create(**validated_data)

        # Second pass for tags, to allow tags added on creation, this is necessary because the tags work like a ManyToMany relationship.
        if tags_data:
            obj.tags.add(*tags_data)

        return obj

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
            'ext_take_id', 'ext_scan_assets_id', 'ext_tracking_assets_id', 
            'ext_take_prj_id', 'ext_scan_assets_prj_id', 'ext_tracking_assets_prj_id',
            'ext_take_name', 'ext_scan_assets_name', 'ext_tracking_assets_name', 
            'priority', 'image_filename', 'mesh_filename', 'dependencies_id', 'tags')

class FarmJobDetailedSerializer(TaggitSerializer, serializers.ModelSerializer):
    
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

    ext_take_prj_id = serializers.PrimaryKeyRelatedField(source='ext_take.shot.session.project', read_only=True)
    ext_scan_assets_prj_id = serializers.PrimaryKeyRelatedField(source='ext_scan_assets.project', read_only=True)
    ext_tracking_assets_prj_id = serializers.PrimaryKeyRelatedField(source='ext_tracking_assets.take.shot.session.project', read_only=True)

    image_filename = serializers.CharField(read_only=True)
    mesh_filename = serializers.CharField(read_only=True)

    tags = TagListSerializerField(required=False)

    def get_write_access(self, obj):
        return obj.has_write_access(self.context['request'].user)

    class Meta:
        model = FarmJob
        fields = ('job_class', 'id', 'created_by', 'params', 'exception', 'status', 'node', 'status_changed', 'created', 'modified', 'parent', 'children', 
            'dependencies', 'progress', 'start_time', 'end_time', 'req_version', 'req_gpu', 
            'ext_take_id', 'ext_scan_assets_id', 'ext_tracking_assets_id', 
            'ext_take_prj_id', 'ext_scan_assets_prj_id', 'ext_tracking_assets_prj_id',
            'ext_take_name', 'ext_scan_assets_name', 'ext_tracking_assets_name', 
            'priority', 'write_access', 'image_filename', 'mesh_filename', 'tags')

class FarmNodeSerializer(TaggitSerializer, serializers.ModelSerializer):
    
    active = serializers.BooleanField(source='is_active', read_only=True) # Connected and listenning to commands
    status = serializers.CharField(source='actual_status', read_only=True)
    running_jobs = FarmJobSerializer(many=True, read_only=True)

    accepting = serializers.BooleanField(source='active', read_only=True) # Accepting jobs

    group = serializers.SlugRelatedField(many=False, read_only=False, slug_field='name', allow_null=True, required=False, queryset=FarmNodeGroup.objects.all())

    tags = TagListSerializerField(required=False)

    class Meta:
        model = FarmNode
        fields = ('ip_address', 'id', 'machine_name', 'last_seen', 'status', 'active', 'running_jobs', 'system', 
            'code_version', 'git_version', 'cpu_brand', 'cpu_percent', 'cpu_cores', 'gpu_count', 'virt_percent', 'os_version', 'accepting', 'group', 
            'system', 'system_bits', 'tags', 'aws_instance_id', 'aws_instance_state')

class FarmNodeSerializerDetails(FarmNodeSerializer):
    
    recent_jobs = FarmJobSerializer(many=True, read_only=True)

    class Meta:
        model = FarmNode
        fields = ('ip_address', 'id', 'machine_name', 'last_seen', 'status', 'active', 'running_jobs', 'recent_jobs', 'system', 
            'code_version', 'git_version', 'cpu_brand', 'cpu_percent', 'cpu_cores', 'gpu_count', 'virt_percent', 'os_version', 'accepting', 'group', 
            'system', 'system_bits', 'tags', 'aws_instance_id', 'aws_instance_state')

class FarmNodeGroupSerializer(serializers.ModelSerializer):

    nodes = FarmNodeSerializer(many=True)

    class Meta:
        model = FarmNodeGroup
        fields = ('name', 'nodes')

