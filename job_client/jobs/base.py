#
# Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
#

from __future__ import absolute_import

from builtins import object
import tempfile
import os
import subprocess
import requests
import threading
import cv2
import json

from .credentials import DEFAULT_USERNAME, DEFAULT_PASSWORD, DEFAULT_SERVER
from .common import PopenWithTimeout

class YieldToChildrenException(Exception):
    def __init__(self, children_list):
        self.children = children_list

class BaseJob(object):

    def __init__(self):

        self.job_id = None

        self.USERNAME = DEFAULT_USERNAME
        self.PASSWORD = DEFAULT_PASSWORD
        self.server_url = DEFAULT_SERVER

        self.s = requests.Session()
        self.s.auth = (self.USERNAME, self.PASSWORD)

    def check_requirements(self):
        # Implement checks in each job class, this will run once on initialization to see if we can run this job
        pass

    def server_get(self, url, **kwargs):
        # Make HTTP GET request on the server
        return self.s.get(self.server_url + url, verify=False, **kwargs)

    def server_post(self, url, **kwargs):
        # Make HTTP POST request on the server
        return self.s.post(self.server_url + url, verify=False, **kwargs)

    def server_patch(self, url, **kwargs):
        # Make HTTP PATCH request on the server
        return self.s.patch(self.server_url + url, verify=False, **kwargs)

    def server_get_json(self, url):

        r = self.server_get(url)

        if not r.status_code==200:
            raise Exception('%s Status:%d Content:%s' % (url, r.status_code, r.content))

        return r.json()

    def get_job_info(self, job_id=None):
        if job_id is None and self.job_id is None:
            return None        
        url = '/jobs/farm_job/%d' % (job_id if job_id else self.job_id)
        return self.server_get_json(url)

    def get_scan_asset_info(self, id):
        url = '/archive/staticscanasset/%d' % int(id)
        return self.server_get_json(url)
    
    def get_tracking_asset_info(self, id):
        url = '/archive/trackingasset/%d' % int(id)
        return self.server_get_json(url)

    def get_take_info(self, id):
        url = '/archive/take/%d' % int(id)
        return self.server_get_json(url)

    def run_subprocess(self, cmd, log, cwd=None, check_output=False, timeout=None):

        ''' Helper function to run a subprocess, and capture its output in the log.
            Returns a tuple with the process return code and its output.  
        '''

        retcode = -1
        output = ''

        if log:
            log.info(cmd)

        temp_filename = None
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_filename = f.name
            
            if timeout is None:
                p = subprocess.Popen(cmd, stdout=f, stderr=f, cwd=cwd)
                p.wait()
                retcode = p.returncode
            else:
                p = PopenWithTimeout(cmd)
                retcode, _, _ = p.run(timeout, stdout=f, stderr=f, cwd=cwd)

        with open(temp_filename, 'r') as f:
            output = f.read()
            if log:
                log.info(output)
        os.remove(temp_filename)

        if check_output and not retcode==0:
            raise subprocess.CalledProcessError(retcode, cmd, output)
        
        return (retcode, output)

    def launch_job(self, job_class, node_name=None, params='', req_gpu=False, 
        ext_take_id=None, ext_scan_assets_id=None, ext_tracking_assets_id=None, 
        as_child=True, dependency_list=[], status='ready', tags=None):
        delayed_status = dependency_list or tags
        d = {
            "job_class": job_class,
            "parent_id": self.job_id if as_child else None,
            "status": 'created' if delayed_status else status,
            "params" : params,
            "req_gpu": req_gpu,
            "ext_take_id": ext_take_id,
            "ext_scan_assets_id": ext_scan_assets_id,
            "ext_tracking_assets_id": ext_tracking_assets_id,
            "node_name": node_name
            }
        r = self.server_post('/jobs/farm_jobs/', json=d)
        if r.status_code != 201:
            raise Exception('launch_job failed : ' + r.text)

        j = json.loads(r.content)
        job_id = int(j['id'])

        # If there are dependencies, need to create job in two passes because of the ManyToMany relationship
        if dependency_list:
            d = {
                "dependencies_id": dependency_list
                }
            r = self.server_patch('/jobs/farm_jobs/%d/' % job_id, json=d)
            if r.status_code != 200:
                raise Exception('job set dependencies failed : ' + r.text)

        # If there are tags, need to create job in two passes because of the ManyToMany relationship
        if tags:
            d = {
                "tags": tags
                }
            r = self.server_patch('/jobs/farm_jobs/%d/' % job_id, json=d)
            if r.status_code != 200:
                raise Exception('job set tags failed : ' + r.text)

        if delayed_status:
            d = {
                "status": status
                }
            r = self.server_patch('/jobs/farm_jobs/%d/' % job_id, json=d)
            if r.status_code != 200:
                raise Exception('job set status failed : ' + r.text)

        return job_id

    def yieldToChildren(self, children_list):

        if not isinstance(children_list, list):
            raise Exception('children_list passed to yieldToChildren must be a list')

        for d in children_list:
            if not isinstance(d, dict):
                raise Exception('children_list passed to yieldToChildren must be a list of dictionaries')

        if not len(children_list):
            raise Exception('children_list passed to yieldToChildren must have at least one element')

        # Launch Child Jobs directly
        for d in children_list:           
            self.launch_job(**d)
        children_list = []

        raise YieldToChildrenException(children_list)

    def set_job_image(self, img, resize=True):

        if isinstance(img, basestring) and not resize:

            fileext = os.path.splitext(img)[1]

            # Upload to server
            with open(img, 'rb') as f:
                files={'file':('job_%d%s' % (self.job_id, fileext), f)}
                r = self.server_post('/jobs/job_image/%d' % (self.job_id), files=files)
                if r.status_code != 200:
                    raise Exception('Could not upload job thumbnail to server code:%d %s' % (r.status_code, r.text))

        else:

            if isinstance(img, basestring):
                img = cv2.imread(img, cv2.IMREAD_UNCHANGED)

            # Check image resolution
            if resize:
                max_width = 512
                height, width = img.shape[:2]
                if width>max_width:
                    img = cv2.resize(img, (max_width, max_width*height/width), interpolation=cv2.INTER_AREA)

            # Store image in a temporary thumbnail
            tmp_jpg = tempfile.mktemp(suffix='.jpg')

            try:
        
                cv2.imwrite(tmp_jpg, img)

                # Upload to server
                with open(tmp_jpg, 'rb') as f:
                    files={'file':('job_%d.jpg' % self.job_id, f)}
                    r = self.server_post('/jobs/job_image/%d' % (self.job_id), files=files)
                    if r.status_code != 200:
                        raise Exception('Could not upload job thumbnail to server code:%d %s' % (r.status_code, r.text))

            finally:
                if os.path.exists(tmp_jpg):
                    os.remove(tmp_jpg)