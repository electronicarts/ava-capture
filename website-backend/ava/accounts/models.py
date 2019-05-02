#
# Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
#

from __future__ import unicode_literals

from django.db import models
from django.contrib.auth.models import User

class UserData(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    export_path = models.CharField(max_length=255)
