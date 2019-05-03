#
# Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
#

from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
import django.contrib.auth as auth
from django.template import RequestContext, Template

from django.contrib.auth.models import User, Group
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from accounts.serializers import UserSerializer, GroupSerializer

from django.contrib.humanize.templatetags.humanize import naturaltime

from common.views import JSONResponse

from django_gravatar.helpers import get_gravatar_url

# Create your views here.

# ViewSets for all users and groups

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer

class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer

# View single user

@api_view(['GET'])
def current_user(request):
    serializer = UserSerializer(request.user, context={'request':request})
    data = serializer.data
    data['gravatar'] = get_gravatar_url(data['email'], size=150)
    return JSONResponse(data)

@api_view(['GET'])
def all_users(request):
    queryset = User.objects.all().order_by('-last_login')
    serializer = UserSerializer(queryset, many=True, context={'request':request})
    data = serializer.data
    for u in data:
        u['gravatar'] = get_gravatar_url(u['email'], size=150)
        u['lastMessage'] = naturaltime(u['last_login'])
        u['messages'] = []
# [{
#     //     text: 'Hey! What\'s up?'
#     //   }, {
#     //     text: 'Are you there?'
#     //   }, {
#     //     text: 'Let me know when you come back.'
#     //   }, {
#     //     text: 'I am here!',
#     //     fromMe: true
#     //   }]        
    return JSONResponse(data)

# Login

def index(request):
    return HttpResponse("Hello!!")

def info(request):
    if request.user.is_authenticated:
        return HttpResponse("info about user (authenticated)" + request.user.username)
    else:
        return HttpResponse("info about user " + request.user.username)

def login(request):
    if 'username' in request.POST and 'password' in request.POST:
        username = request.POST['username']
        password = request.POST['password']
        user = auth.authenticate(username=username, password=password)
        if user is not None:
            auth.login(request,user)
            return HttpResponse("login ok " + request.user.username)
        else:
            return HttpResponse("login error")
    else:
        # display login form
        template = Template('<html><body><form method="post" action="/accounts/login"><input type="text" name="username"><input type="password" name="password"><input type="submit" value="Login">{% csrf_token %}</form></body></html>')
        c = RequestContext(request, { 'foo': 'bar', })
        return HttpResponse(template.render(c))

def logout(request):
    auth.logout(request)
    return HttpResponse("logout")

