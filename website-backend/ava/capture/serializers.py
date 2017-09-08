#
# Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
#

from models import CaptureNode, Camera
from rest_framework import serializers

import json

class ShortCameraSerializer(serializers.ModelSerializer):

    class Meta:
        model = Camera
        fields = ('id', 'unique_id', 'rotation')

class CaptureNodeSerializer(serializers.HyperlinkedModelSerializer):
    
    cameras = ShortCameraSerializer(many=True, read_only=True)
    active = serializers.BooleanField(source='is_active', read_only=True)

    class Meta:
        model = CaptureNode
        fields = ('ip_address', 'id', 'machine_name', 'os', 'last_seen', 'cameras', 'active', 'sync_found', 'drive_info', 'code_version')

    def to_representation(self, instance):
        ret = super(CaptureNodeSerializer, self).to_representation(instance)
        try:
            ret['drive_info'] = json.loads(ret['drive_info']) # drive_info is a json string in the database, it is expanded to basic python data here
        except:
            pass # string is not valid json
        return ret

class CameraSerializer(serializers.HyperlinkedModelSerializer):

    ip_address = serializers.ReadOnlyField(source='node.ip_address')
    active = active = serializers.BooleanField(source='is_active', read_only=True)
    last_seen = serializers.ReadOnlyField(source='node.last_seen')

    class Meta:
        model = Camera
        fields = ('id', 'unique_id', 'model', 'ip_address', 'active', 'last_seen', 'version')
