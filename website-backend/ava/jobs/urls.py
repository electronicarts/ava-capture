#
# Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
#

from django.conf.urls import url, include
from rest_framework import routers

from . import views
from . import metrics

router = routers.DefaultRouter()
router.register(r'farm_nodes', views.FarmNodeViewSet)
router.register(r'farm_groups', views.FarmGroupsViewSet)
router.register(r'recent_farm_jobs', views.RecentFarmJobsViewSet)
router.register(r'recent_finished_jobs', views.RecentFinishedFarmJobsViewSet)
router.register(r'farm_jobs', views.FarmJobsViewSet)

urlpatterns = [
    url(r'^', include(router.urls)),
    url(r'^client_discover', views.post_client_discover),   
    url(r'^submit_test_job', views.submit_test_job),   
    url(r'^delete_job', views.delete_job),   
    url(r'^kill_job', views.kill_job),   
    url(r'^restart_failed_child_job', views.restart_job_failed_child),   
    url(r'^restart_job', views.restart_job),   
    url(r'^reload_client', views.post_reload_client),
    url(r'^aws_start_instance', views.post_aws_start_instance),
    url(r'^job_image/(?P<job_id>[0-9]+)', views.job_image),
    url(r'^job_mesh/(?P<job_id>[0-9]+)', views.job_mesh),
    url(r'^job_output/(?P<job_id>[0-9]+)', views.job_output),
    url(r'^farm_job/(?P<job_id>[0-9]+)', views.job_detailed),
    url(r'^farm_node/(?P<node_id>[0-9]+)', views.node_detailed),
    ]

metrics.setup()
