#
# Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
#

from django.contrib import admin

from models import Project, Session, Shot, Take, Camera, StaticScanAsset, TrackingAsset

admin.site.register(Project)

class SessionAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'name', 'project')
    list_filter = ('project', )
    list_select_related = ('project', )
admin.site.register(Session, SessionAdmin)

class ShotAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'name', 'session')
    list_filter = ('session__project', )
    list_select_related = ('session', 'session__project')
admin.site.register(Shot, ShotAdmin)

class CameraInline(admin.TabularInline):
    model = Camera
    extra = 0

class TakeAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'name', 'flag', 'shot')
    inlines = [
        CameraInline,
    ]
admin.site.register(Take, TakeAdmin)

class CameraAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'unique_id', 'machine_name', 'model', 'take')
admin.site.register(Camera, CameraAdmin)

class StaticScanAssetAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'project')
    list_filter = ('project', )
    list_select_related = ('project', )
admin.site.register(StaticScanAsset, StaticScanAssetAdmin)

class TrackingAssetAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'take')
admin.site.register(TrackingAsset, TrackingAssetAdmin)
