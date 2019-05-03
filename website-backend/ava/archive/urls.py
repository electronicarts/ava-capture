#
# Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
#

from django.conf.urls import url, include
from rest_framework import routers

from . import views

router = routers.DefaultRouter()

router.register(r'archive_projects', views.ProjectsViewSet)
router.register(r'asset_projects', views.ProjectAssetsViewSet)

router.register(r'archive_project', views.ProjectArchiveViewSet)
router.register(r'archive_session', views.SessionDetailsViewSet)
router.register(r'archive_session_export', views.SessionExportViewSet)

router.register(r'staticscanasset', views.StaticScanAssetViewSet)
router.register(r'trackingasset', views.TrackingAssetViewSet)

router.register(r'take', views.TakeViewSet)
router.register(r'shot', views.ShotViewSet)
router.register(r'session', views.SessionViewSet)

urlpatterns = [
    url(r'^', include(router.urls)),
    url(r'^archive_session_export_json/(?P<session_id>[0-9]+)', views.get_archive_json_file),
    url(r'^get_export_path', views.get_last_export_path), # Get last export path for the user
    url(r'^export_takes', views.post_export_takes),
    url(r'^delete_takes', views.post_delete_takes),
    url(r'^set_take_flag', views.post_set_take_flag),    
    url(r'^set_frontal_cam', views.post_set_frontal_cam),    
    url(r'^create_tracking_asset', views.post_create_tracking_asset),
    url(r'^take_video_thumbnail/(?P<take_id>[0-9]+)', views.post_take_video_thumbnail),
    url(r'^tracking_asset_thumbnail/(?P<asset_id>[0-9]+)', views.post_tracking_video_thumbnail),
    url(r'^tracking_asset_frame_thumbnail/(?P<asset_id>[0-9]+)/(?P<frame>[0-9a-z_]+)', views.post_tracking_asset_thumbnail),
    url(r'^scan_asset_thumbnail/(?P<asset_id>[0-9]+)/(?P<asset_type>[0-9a-z_]+)', views.post_scan_asset_thumbnail),
    url(r'^import_session/(?P<project_id>[0-9]+)', views.post_import_session),   
    url(r'^download_original', views.download_original),   
    ]

