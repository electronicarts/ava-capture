#
# Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
#

from django.conf.urls import url, include
from rest_framework import routers

from . import views

router = routers.DefaultRouter()
router.register(r'loc', views.LocationsViewSet)

urlpatterns = [
    url(r'^', include(router.urls)),
    url(r'^cameras_detailed/(?P<location_id>[0-9]+)', views.cameras_detailed),
    url(r'^camera_detailed/(?P<location_id>[0-9]+)/(?P<camera_id>[0-9]+)', views.camera_detailed),
    url(r'^location/(?P<location_id>[0-9]+)', views.location),
    url(r'^locations', views.get_locations),
    url(r'^node_discover', views.node_discover),
    url(r'^node_shutdown', views.node_shutdown),
    url(r'^location_config/(?P<location_id>[0-9]+)', views.location_config),
    url(r'^camera_parameter/(?P<location_id>[0-9]+)', views.camera_parameter),
    url(r'^new_session/(?P<location_id>[0-9]+)', views.post_new_session),
    url(r'^new_shot/(?P<location_id>[0-9]+)', views.post_new_shot),
    url(r'^start_recording', views.post_start_recording),    
    url(r'^stop_recording', views.post_stop_recording),    
    url(r'^record_single_image', views.post_record_single_image),    
    url(r'^toggle_using_sync', views.post_toggle_using_sync),    
    url(r'^toggle_capturing', views.post_toggle_capturing),    
    url(r'^set_camera_rotation', views.post_set_camera_rotation),    
    url(r'^close_node', views.post_close_node),
    url(r'^camera_set_roi', views.post_set_roi),
    url(r'^camera_reset_roi', views.post_reset_roi),
    url(r'^message', views.post_message),    
    ]
