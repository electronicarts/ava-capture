#
# Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
#

from __future__ import print_function
from __future__ import absolute_import

from builtins import object
from .base import BaseJob

import time
import subprocess
import logging
import json
import os

class JobTestFixture(object):
    def __init__(self):
        FORMAT = "[MAIN] %(message)s"
        logging.basicConfig(format=FORMAT)
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.DEBUG)
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        class MockPipe(object):
            def send(self,str):
                print('PIPE> %s' % str)
        self.pipe = MockPipe()

    def __call__(self, job, parameters):
        job(parameters, self.pipe, self.logger)

class DummyJob(BaseJob):
    def __call__(self, parameters, pipe, log):
        pipe.send('Progress 0%')
        time.sleep(0.3)
        pipe.send('Progress 40%')
        time.sleep(0.3)
        pipe.send('Progress 60%')
        time.sleep(0.3)
        pipe.send('Progress 100%')

    class Meta(object):
        description = 'This is a test Job'

class DummyJobLaunch(BaseJob):
    def __call__(self, parameters, pipe, log):
        pipe.send('Launch new job')
        new_job_id = self.launch_job('jobs.test.DummyJob', tags=['alpha','bravo'])
        pipe.send('Launched %d' % new_job_id)

    class Meta(object):
        description = 'This is a test Job'

class DummyJobWithImage(BaseJob):
    def __call__(self, parameters, pipe, log):
        
        import cv2
        import numpy as np

        height = 512
        width = 512

        img = np.zeros((height,width,3), np.uint8)
        img[:,0:int(0.5*width)] = (255,0,0)      # (B, G, R)
        img[:,int(0.5*width):width] = (0,255,0)

        pipe.send('Uploading JPG thumbnail...')

        self.set_job_image(img)


    class Meta(object):
        description = 'This is a test Job'

class HttpTestJob(BaseJob):
    def __call__(self, parameters, pipe, log):
        r = self.server_get('/archive/archive_session/3/', json={'asdf':'asdf'})
        print(r.status_code)
        if not r.status_code==200:
            raise Exception('Status:%d Content:%s' % (r.status_code, r.content))

    class Meta(object):
        description = 'This is a test Job'

class DummyJobWithChildren(BaseJob):
    def __call__(self, parameters, pipe, log):
        pipe.send('Begin DummyJobWithChildren')

        child_launch_info = {}
        child_launch_info['job_class'] = 'jobs.test.DummyJob'
        child_launch_info['params'] = 'parameters'
        child_launch_info['req_gpu'] = False
        #child_launch_info['node_name'] = node_name
        
        self.yieldToChildren([child_launch_info, child_launch_info, child_launch_info])

        # anything after yieldToChildren will not be executed

    class Meta(object):
        description = 'This is a test Job With Children'

class DummyJobWithLog(BaseJob):
    def __call__(self, parameters, pipe, log):
        log.info('Begin DummyJobWithLog')
        log.warning('DummyJobWithLog warning')
        log.info('End DummyJobWithLog')

    class Meta(object):
        description = 'This is a test Job'

class DummyJobRaisingException(BaseJob):
    def __call__(self, parameters, pipe, log):
        pipe.send('Before Exception')
        time.sleep(0.3)
        raise Exception('This job is raising an exception')
        pipe.send('After Exception')

    class Meta(object):
        description = 'This is a test Job, which raises an Exception'

class DummyJobSubprocess(BaseJob):
    def __call__(self, parameters, pipe, log):

        # Run a subprocess without capturing its output.
        # The prefered method is to use run_subprocess()
        p = subprocess.Popen(["ipconfig", "/all"])
        p.wait()

        # Run a subprocess without capturing its output, will raise an exception if the process 
        # has a return code different than 0.
        # The prefered method is to use run_subprocess()
        subprocess.check_output(["ipconfig", "/all"])

    class Meta(object):
        description = 'This is a test Job, launching a subprocess'

class DummyJobSubprocessFail(BaseJob):
    def __call__(self, parameters, pipe, log):

        # Runs a subprocess that fails, the resulting exception will be logged, but not the process output
        # The prefered method is to use run_subprocess()
        subprocess.check_output("exit 1", shell=True)

    class Meta(object):
        description = 'This is a test Job, launching a subprocess'

class DummyJobSubprocessCaptureSmallOutput(BaseJob):
    def __call__(self, parameters, pipe, log):

        # This will work for commands with a small output, but as mentionned in the Python documentation,
        # it may hang if the process outputs a lot of data.
        # Using self.run_subprocess should be the prefered method to launch a subprocess.
        p = subprocess.Popen(["ipconfig", "/all"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        if stdout:
            log.info(stdout.decode())
        if stderr:
            log.error(stderr.decode())

class DummyJobSubprocessCaptureOutput(BaseJob):
    def __call__(self, parameters, pipe, log):

        (retcode, output) = self.run_subprocess(["ipconfig", "/all"], log)

        if not retcode==0:
            raise Exception('Expecting retcode=0')

    class Meta(object):
        description = 'This is a test Job, launching a subprocess'

class DummyJobSubprocessCaptureOutputFail(BaseJob):
    def __call__(self, parameters, pipe, log):

        self.run_subprocess(["ipkasdjhfgak"], log)

    class Meta(object):
        description = 'This is a test Job, launching a subprocess that doesnt exist'


    class Meta(object):
        description = 'Test transfer speed to a fileserver'
