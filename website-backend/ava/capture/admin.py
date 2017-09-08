#
# Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
#

from django.contrib import admin

from models import CaptureLocation, CaptureNode, Camera, LocationAccess

admin.site.register(CaptureLocation)
admin.site.register(CaptureNode)
admin.site.register(Camera)
admin.site.register(LocationAccess)
