#
# Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
#

from django.conf.urls import url, include
from rest_framework import routers

from . import views

router = routers.DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'groups', views.GroupViewSet)

urlpatterns = [
    url(r'^', include(router.urls)),
    url(r'^$', views.index, name='index'),
    url(r'^current_user$', views.current_user),
    url(r'^all_users$', views.all_users),
    url(r'^login$', views.login, name='login'),
    url(r'^logout$', views.logout, name='logout'),
    url(r'^info$', views.info, name='info'),
    ]
