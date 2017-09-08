#
# Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
#

from django.contrib import admin

from models import FarmNodeGroup, FarmNode, FarmJob

admin.site.register(FarmNodeGroup)

class FarmNodeAdmin(admin.ModelAdmin):
    list_display = ('machine_name', 'ip_address', 'status', 'code_version', 'group')
    list_filter = ('status', 'group')
admin.site.register(FarmNode, FarmNodeAdmin)

class FarmJobAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'status', 'node')
    exclude = ('progress', 'status_changed', 'start_time', 'end_time')
    list_filter = ('status', 'node__machine_name', 'job_class')
    list_select_related = ('node', )
admin.site.register(FarmJob, FarmJobAdmin)
