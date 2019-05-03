#
# Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
#

from django.contrib import admin

from models import CaptureLocation, CaptureNode, Camera, LocationAccess

class CaptureNodeAdmin(admin.ModelAdmin):
    list_display = ('machine_name', 'ip_address', 'os', 'location', 'build_version')
    list_filter = ('location', 'os')
admin.site.register(CaptureNode, CaptureNodeAdmin)

admin.site.register(CaptureLocation)
admin.site.register(Camera)
admin.site.register(LocationAccess)
