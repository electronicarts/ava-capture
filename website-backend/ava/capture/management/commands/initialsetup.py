#
# Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
#

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from capture.models import CaptureLocation, LocationAccess

class Command(BaseCommand):
    help = 'Initial setup, add default users and capture location'

    def handle(self, *args, **options):
            
        queryset = User.objects.filter(username='pythonscript')
        if not queryset:
            print('Creating user pythonscript')
            user = User(username='pythonscript')
            user.is_staff = False
            user.is_superuser = False
            user.set_password('xxPASSWORDxx')
            user.save()

        queryset = User.objects.filter(username='admin')
        if not queryset:
            print('Creating user admin')
            user = User(username='admin')
            user.is_staff = True
            user.is_superuser = True
            user.set_password('admin')
            user.save()
        else:
            user = queryset[0]

        queryset = CaptureLocation.objects.filter(name='local')
        if not queryset:
            print('Creating local location')
            loc = CaptureLocation(name='local')
            loc.read_access_all = True
            loc.save()
        else:
            loc = queryset[0]

        queryset = LocationAccess.objects.filter(user=user, location=loc)
        if not queryset:
            print('Creating LocationAccess')
            loc = LocationAccess(user=user,location=loc)
            loc.read_access = True
            loc.write_access = True
            loc.save()

