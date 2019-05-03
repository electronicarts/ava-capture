#
# Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
#

from django.test import TestCase
from models import FarmNode, FarmJob, FarmNodeGroup

class FarmJobTestCase(TestCase):
    def setUp(self):
        job = FarmJob.objects.create(job_class='jobs.thumbnails.GenerateThumbnail', created_by='username', status='ready')
        self.test_job_id = job.id

    def test_job_created(self):
        job = FarmJob.objects.get(id=self.test_job_id)
        self.assertEqual(job.status, 'ready')
