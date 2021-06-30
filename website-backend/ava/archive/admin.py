#
# Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
#

from django.contrib import admin

from archive.models import Project, Session, Shot, Take, Camera, StaticScanAsset, TrackingAsset

def archive_project(modeladmin, request, queryset):
    queryset.update(archived=True)

class ProjectAdmin(admin.ModelAdmin):
    list_filter = ('archived', )
    actions = [archive_project]
admin.site.register(Project, ProjectAdmin)

class SessionAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'name', 'project')
    list_filter = ('project', )
    list_select_related = ('project', )
admin.site.register(Session, SessionAdmin)

class ShotAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'name', 'session')
    list_filter = ('session__project', )
    list_select_related = ('session', 'session__project')
    raw_id_fields = ('session', )
admin.site.register(Shot, ShotAdmin)

class CameraInline(admin.TabularInline):
    model = Camera
    extra = 0

class TakeAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'name', 'flag', 'shot')
    inlines = [
        CameraInline,
    ]
    raw_id_fields = ('shot', )
admin.site.register(Take, TakeAdmin)

class CameraAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'unique_id', 'machine_name', 'model', 'take')
admin.site.register(Camera, CameraAdmin)

class StaticScanAssetAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'take', 'project')
    list_filter = ('project', )
    list_select_related = ('project', )
    raw_id_fields = ('take', 'associated_tracking_asset')
admin.site.register(StaticScanAsset, StaticScanAssetAdmin)

class TrackingAssetAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'take')
    raw_id_fields = ('take', )
admin.site.register(TrackingAsset, TrackingAssetAdmin)
