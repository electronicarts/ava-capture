#
# Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
#

from django.contrib.auth.models import User, Group
from rest_framework import serializers

class UserSerializer(serializers.HyperlinkedModelSerializer):

    last_login = serializers.DateTimeField(read_only=True, format=None)

    class Meta:
        model = User
        fields = ('url', 'id', 'username', 'email', 'groups', 'first_name', 'last_name', 'last_login')

class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Group
        fields = ('url', 'name')



