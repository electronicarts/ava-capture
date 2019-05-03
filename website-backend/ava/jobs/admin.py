#
# Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
#

from django.contrib import admin
from models import FarmNodeGroup, FarmNode, FarmJob

import aws

admin.site.register(FarmNodeGroup)

def aws_start_instance(modeladmin, request, queryset):
    nodes = queryset.exclude(aws_instance_id=None)
    for node in nodes:
        if node.aws_instance_id:
            state = aws.start_instance(node.aws_instance_id, node.aws_instance_region)
            if state:
                node.aws_instance_state = state
                node.save()

def aws_stop_instance(modeladmin, request, queryset):
    nodes = queryset.exclude(aws_instance_id=None)
    for node in nodes:
        if node.aws_instance_id:
            state = aws.stop_instance(node.aws_instance_id, node.aws_instance_region)
            if state:
                node.aws_instance_state = state
                node.save()

class FarmNodeAdmin(admin.ModelAdmin):
    list_display = ('machine_name', 'ip_address', 'status', 'git_version', 'group', 'tag_list', 'aws_instance_state')
    list_filter = ('status', 'group')
    actions = [aws_stop_instance, aws_start_instance]

    def get_queryset(self, request):
        return super(FarmNodeAdmin, self).get_queryset(request).prefetch_related('tags')

    def tag_list(self, obj):
        return u", ".join(o.name for o in obj.tags.all())

admin.site.register(FarmNode, FarmNodeAdmin)

class FarmJobAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'status', 'node', 'tag_list')
    exclude = ('progress', 'status_changed', 'start_time', 'end_time')
    list_filter = ('status', 'node__machine_name', 'job_class')
    list_select_related = ('node', )
    raw_id_fields = ('parent', 'ext_take', 'ext_scan_assets', 'ext_tracking_assets', 'dependencies')

    def get_queryset(self, request):
        return super(FarmJobAdmin, self).get_queryset(request).prefetch_related('tags')

    def tag_list(self, obj):
        return u", ".join(o.name for o in obj.tags.all())

admin.site.register(FarmJob, FarmJobAdmin)
