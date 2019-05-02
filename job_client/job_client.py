#
# Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
#

from __future__ import print_function
from future.standard_library import install_aliases
install_aliases()
from builtins import object
from builtins import str
import json
import time
import argparse
import requests
import socket
import traceback
import tempfile
from threading import Thread
import logging
import os
import sys
import datetime
from multiprocessing import Process, Pool, Pipe, Queue
from contextlib import contextmanager

import importlib
import inspect

import platform
import cpuinfo
import psutil

from jobs.base import BaseJob, YieldToChildrenException
from jobs.credentials import DEFAULT_USERNAME, DEFAULT_PASSWORD, DEFAULT_SERVER

from version import VERSION

global_exit_signal = False

# Unfortunatly we cannot verify certificates with this version, see https://urllib3.readthedocs.io/en/latest/user-guide.html#ssl-py2
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

def get_local_ip_for_server(url):
    # Returns the IP Address of the adapter used to reach a specific URL
    try:
        from urllib.parse import urlparse
        parsed_uri = urlparse(url)

        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect((parsed_uri.netloc, 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except:
        return socket.gethostbyname(socket.gethostname())

def kill_process_tree(pid, including_parent=True):
    parent = psutil.Process(pid)
    children = parent.children(recursive=True)
    for child in children:
        try:
            child.kill()
        except:
            pass # we prefer to silently ignore than to get stuck
    gone, still_alive = psutil.wait_procs(children, timeout=5)
    if including_parent:
        try:
            parent.kill()
            parent.wait(5)
        except:
            pass # we prefer to silently ignore than to get stuck

def class_from_string(name):
    return getattr(importlib.import_module('.'.join(name.split('.')[:-1])), name.split('.')[-1])

def job_process(job_id, job_class, parameters, q, pipe, server_url, context, log_filename=None):

    logger = None
    try:
        # Initialize log
        logger = logging.getLogger('JobProcessLogger') # TODO we may need a unique name in linux ?
        logger.setLevel(logging.DEBUG)

        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)        
        logger.addHandler(ch)

        # Log File Handler
        if log_filename:
            log = open(log_filename, 'w') # Overwrite, filename should be unique
            handler = logging.StreamHandler(log)
            formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            handler.setLevel(logging.DEBUG)
            logger.addHandler(handler)
            logger.info('Launching Job #%d' % job_id)
            if parameters:
                logger.info('Parameters: %s' % parameters)

        job = job_class()
        job.job_id = job_id
        job.server_url = server_url
        retcode = job(parameters, pipe, logger)

        q.put({'job_id':job_id, 'success':True, 'retcode':retcode})        

        logger.info('Job Success: #%d' % job_id)

        pipe.close()

    except YieldToChildrenException as e:
        if logger:
            logger.debug("Job Yield to children")

        # Place job output in the queue
        q.put({'job_id':job_id, 'waiting':True, 'retcode':0, 'children':e.children})

        logger.info('Job YieldToChildren: #%d' % job_id)

    except:

        exception_details = traceback.format_exc()
        if logger:
            logger.error(exception_details)

        q.put({'job_id':job_id, 'success':False, 'retcode':1, 'exception':exception_details})

        logger.info('Job Failed: #%d' % job_id)

    finally:
        if logger:
            logger.handlers = []

class JobInstance(object):

    def __str__(self):
        return 'Job #%d %s' % (self.job_id, self.status)

    def __init__(self, params, job_class, server_url, context, job_id=0, log_filename=None):
        self.parameters = params
        self.server_url = server_url
        self.job_class = job_class
        self.log_filename = log_filename
        self.job_id = job_id
        self.result = None
        self.completed = False
        self.status = ''
        self.p = None
        self.terminated = False
        self.context = context

        try:
            if isinstance(job_class, str) or isinstance(job_class.decode(), str):
                self.job_class = class_from_string(job_class)

            if not self.job_class.__module__.startswith('jobs.'):
                raise Exception('Job classes must be in the "jobs" module.')

            if not issubclass(self.job_class, BaseJob):
                raise Exception('Jobs must inherit from jobs.base.BaseJob')

        except Exception as e:
            self.completed = True
            exception_details = traceback.format_exc()
            self.result = {'job_id':self.job_id, 'success':False, 'retcode':1, 'exception':exception_details, 'progress':self.status}
    
    def output_received_from_job(self, data):
        print('Job #%d> %s' % (self.job_id, data))
        self.status = data

    def terminate(self):
        print('Terminate Job #%d' % (self.job_id))
        try:
            if self.p:
                if not self.p.is_alive():
                    return
                kill_process_tree(self.p.pid, True)
        except Exception as e:
            print('Could not terminate job cleanly #%d : %s' % (self.job_id, e))
        finally:
            self.terminated = True                


    def blocking_run(self):
        parent_conn, child_conn = Pipe()
        q = Queue()
        self.p = Process(target=job_process, 
            args=(self.job_id, self.job_class, self.parameters, q, child_conn, self.server_url, self.context, self.log_filename, ))
        self.p.start()
        while self.p.is_alive() and not self.terminated:
            while parent_conn.poll():
                self.output_received_from_job(parent_conn.recv())
            time.sleep(1)
        self.p.join()
        try:
            while parent_conn.poll():
                msg = parent_conn.recv()
                self.output_received_from_job(msg)
        except:
            print('Exception while gathering job process output')

        try:
            if self.terminated:
                # Job was terminated from user request
                self.result = {'job_id':self.job_id, 'success':False, 'retcode':1, 'exception':'Terminated by server', 'progress':'terminated'}
            else:
                if q.empty():
                    # Job process error, the job should always place its output in the queue
                    self.result = {'job_id':self.job_id, 'success':False, 'retcode':1, 'exception':'Job process terminated abnormally', 'progress':'failed'}
                else:                
                    # Job terminated normally
                    self.result = q.get()
                    self.result['progress'] = self.status
        except:
            print('Exception while gathering job output')

        parent_conn.close()   
        return self.result

class JobContainer(object):
    def __init__(self, log_folder, server_url, context):
        self.log_folder = log_folder
        self.server_url = server_url
        self.running_jobs = {}
        self.finished_jobs = {}
        self.context = context

        if not os.path.exists(self.log_folder):
            os.makedirs(self.log_folder)

    def wrapper(self, job_id, j):
        if not j.completed:
            j.blocking_run()
        self.finished_jobs[job_id] = j
        del self.running_jobs[job_id]

    def terminate_job(self, job_id):
        if job_id in self.running_jobs:
            t,j = self.running_jobs[job_id]
            j.terminate()

    def submit_job(self, params, job_class, job_id):
        ''' Launch a single job. The log filename is generated from the job id and a timestamp '''

        if job_id in self.running_jobs:
            raise Exception('job_id must be unique')

        log_filename = os.path.join(self.log_folder, 
            '%s__%d__%s.txt' % (job_class.replace('.','_'), job_id, datetime.datetime.now().strftime('%Y%m%d_%H%M%S')))

        # Launch Thread to run this JobInstance
        j = JobInstance(params, job_class, server_url=self.server_url, context=self.context, job_id=job_id, log_filename=log_filename)
        t = Thread(target=self.wrapper, args=(job_id, j))
        self.running_jobs[job_id] = (t,j)
        t.start()

    def running_jobs_count(self):
        return len(self.running_jobs)

    def finished_jobs_count(self):
        return len(self.finished_jobs)

    def wait(self):
        ''' Wait for all current jobs to be finished '''
        for t,j in list(self.running_jobs.values()):
            t.join()

class JobClient(object):

    LOG_FOLDER = os.path.abspath('logs')
    PHONEHOME_DELAY = 4 # seconds

    def __init__(self, server, git_version, tags):

        print('Logs will be written to %s' % self.LOG_FOLDER)

        self.USERNAME = DEFAULT_USERNAME
        self.PASSWORD = DEFAULT_PASSWORD

        if not os.path.exists(self.LOG_FOLDER):
            os.makedirs(self.LOG_FOLDER)

        self.log_folder = self.LOG_FOLDER
        self.server = server
        self.hostname = socket.gethostname()
        self.ip = get_local_ip_for_server(server)
        self.status_changed = True
        self.info = cpuinfo.get_cpu_info()
        self.s = requests.Session()
        self.first_update = True
        self.need_restart = False
        self.cpu_percent = 0.0
        self.mem_used = 0.0
        self.git_version = git_version
        self.tags = tags if tags else []

        # Log File Logger
        self.logger = logging.getLogger('JobClientLogger')
        self.logger.setLevel(logging.DEBUG)
        handler = logging.FileHandler(os.path.join(self.log_folder, 'JobClient.log'))
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        self.logger.addHandler(ch)

        self.logger.info('Launching JobClient (Code Version %d)' % VERSION)

        try:
            import vhtrack
            self.cuda_device_count = vhtrack.query_cuda_device_count()
            if self.cuda_device_count > 0:
                di = vhtrack.DeviceInfo(0)
                if di.isCompatible():
                    total_memory = di.totalMemory()
                    vram_in_GB = total_memory >> 30
                    if vram_in_GB < 4 or di.majorVersion() < 5:
                        self.cuda_device_count = 0

                    self.logger.info('%d CUDA GPU Detected %s with %d GB VRAM' % (self.cuda_device_count, di.name(), vram_in_GB))
                else:
                    self.cuda_device_count = 0
        except:
            self.cuda_device_count = 0
        
        if self.cuda_device_count > 0:
            self.tags.append('gpu')
        else:
            self.logger.info('No CUDA GPU Detected')

        self.tags.append('py%d%d' % (sys.version_info.major, sys.version_info.minor))

        self.context = {}
        self.context['user'] = {
            'git_version': self.git_version,
            'server': self.server,
            'hostname': self.hostname,
            'ip_address': self.ip,            
            'cpu_brand' : self.info['brand'],
            'cpu_cores' : self.info['count'],
            'cuda_device_count' : self.cuda_device_count,
            'client_tags' : self.tags            
        }
        self.context['tags'] = {
            'system' : platform.system(),
            'python_version' : platform.python_version()
        }

        self.container = JobContainer(self.log_folder, server, self.context)

        self.available_job_classes = create_available_job_list(self.logger)

    def notify_exit(self):
        print('Attempting graceful exit....')
        payload = {
            'machine_name': self.hostname, 
            'ip_address': self.ip,
            'status': 'offline'
            }
        r = self.s.post('%s/jobs/client_discover/' % self.server, json=payload, auth=(self.USERNAME, self.PASSWORD), verify=False)

    def phone_home(self):

        payload = {
            'machine_name': self.hostname, 
            'ip_address': self.ip,
            'status': 'accepting',
            'restarted': self.first_update,
            'code_version': VERSION,
            'running_jobs': list(self.container.running_jobs.keys()),
            'running_jobs_progress': [(key,self.container.running_jobs[key][1].status) for key in self.container.running_jobs],
            'finished_jobs': [j.result for j in list(self.container.finished_jobs.values())],
            'system' : platform.system(),
            'system_bits' : self.info['bits'],
            'cpu_brand' : self.info['brand'],
            'cpu_cores' : self.info['count'],
            'cuda_device_count' : self.cuda_device_count,
            'available_jobs' : self.available_job_classes,
            'cpu_percent' : self.cpu_percent,
            'mem_used' : self.mem_used,
            'git_version' : self.git_version,
            'client_tags' : self.tags
            }

        for j in payload['finished_jobs']:
            self.logger.info('Job Finished: %s' % (j))

        r = self.s.post('%s/jobs/client_discover/' % self.server, json=payload, auth=(self.USERNAME, self.PASSWORD), verify=False)
        if (r.status_code==200):

            self.first_update = False

            # Purge local list of finished jobs
            for x in payload['finished_jobs']:
                del self.container.finished_jobs[x['job_id']]

            # Launch new jobs we just received
            try:
                data = r.json()

                if 'req_restart' in data and data['req_restart']:
                    if not self.need_restart:
                        self.logger.info('Received Restart Request')
                    self.need_restart = True

                if 'jobs' in data:
                    for new_job in data['jobs']:
                        self.logger.info('Job received: #%d %s' % (new_job['job_id'], new_job['job_class']))
                        self.container.submit_job(**new_job)
                        self.status_changed = True

                if 'jobs_to_kill' in data:
                    for job_id in data['jobs_to_kill']:
                        self.container.terminate_job(job_id)                        

            except Exception as e:
                self.logger.error('received invalid data from server. %s' % e)
        else:
            self.logger.error("Unexpected return code while contacting server %s (%d)" % (self.server, r.status_code))
            self.logger.error(r.text)

    def loop_forever(self):
        try:
            print('Waiting for jobs...')
            while not global_exit_signal:
                try:
                    self.status_changed = False
                    self.phone_home()

                except Exception as e:
                    self.logger.error('Failed to contact server. %s' % e)

                if self.need_restart and not self.container.running_jobs and not self.container.finished_jobs:
                    print('Restarting...')
                    # End current process and launch a new one with the same command line parameters
                    #os.execvp('python.exe', ['python.exe'] + sys.argv)
                    exit(3)

                if not self.status_changed:
                    self.cpu_percent = psutil.cpu_percent(interval=self.PHONEHOME_DELAY)
                    self.mem_used = psutil.virtual_memory().percent

        except KeyboardInterrupt:
            pass
        finally:
           self.notify_exit()

class SingleInstance(object):
    def __init__(self, name):
        self.locked = False
        self.lock_file = os.path.abspath(os.path.join(os.path.split(sys.modules[__name__].__file__)[0], name+'.lock'))
        if sys.platform == 'win32':
            # Windows
            self.fd = None
            try:
                if os.path.exists(self.lock_file):
                    os.unlink(self.lock_file)
                self.fd = os.open(self.lock_file, os.O_CREAT | os.O_EXCL | os.O_RDWR)
                self.locked = True
            except OSError:
                type, e, tb = sys.exc_info()
                if e.errno == 13:
                    raise Exception('Process %s Already Running' % name)
        else:
            # Linux
            import fcntl
            self.fp = open(self.lock_file, 'w')
            self.fp.flush()
            try:
                fcntl.lockf(self.fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
                self.locked = True
            except IOError:
                raise Exception('Process %s Already Running' % name)


    def __del__(self):
        if self.locked:
            if sys.platform == 'win32':
                # Windows
                if self.fd:
                    os.close(self.fd)
                    os.unlink(self.lock_file)
            else:
                # Linux
                import fcntl
                fcntl.lockf(self.fp, fcntl.LOCK_UN)
                # os.close(self.fp)
                if os.path.isfile(self.lock_file):
                    os.unlink(self.lock_file)

# To use with statement below - make sure __init__ and __del__ above are always called
@contextmanager
def make_single_instance(name):
    si = None
    try:
        si = SingleInstance(name)
        yield
    finally:
        del si

def create_available_job_list(logger):
    # Make list of available Job classes
    import sys, inspect
    avalable_job_classes = []
    for module_name in sys.modules:
        if module_name.split('.')[0]=='jobs':
            m = sys.modules[module_name]
            for name, obj in inspect.getmembers(m):
                if inspect.isclass(obj):
                    if issubclass(obj, BaseJob) and name!='BaseJob':
                        avalable_job_classes.append(obj)
    # Instanciate each job and check requirements
    job_class_names = []
    for c in avalable_job_classes:
        try:
            job = c()
            job.check_requirements()
            class_name = str(c)
            if "'" in class_name:
                class_name = class_name.split("'")[1]
            job_class_names.append(class_name)
            print(' OK %s' % c)
        except Exception as e:
            print(' Not Available: %s (%s)' % (c,str(e)))
    return job_class_names

if __name__ == "__main__":
    import multiprocessing
    if hasattr(multiprocessing, 'set_start_method'):
        multiprocessing.set_start_method('spawn')

    with make_single_instance('AvaJobClient'):

        # Workaround for crash in windows when user presses Ctrl-C
        # forrtl: error (200): program aborting due to control-C event
        if sys.platform == 'win32':
            try:
                import win32api # pip install pywin32
                def consoleCtrlHandler(sig, func=None):
                    print('Caught CTRL-C, exiting...')
                    global global_exit_signal
                    global_exit_signal = True
                    return True
                win32api.SetConsoleCtrlHandler(consoleCtrlHandler, 1)
            except:
                print('Missing pywin32')

        parser = argparse.ArgumentParser(description='Launch Job Client')
        parser.add_argument('server', nargs='?', type=str, help='Http URL of Server, default is %s' % DEFAULT_SERVER, default=DEFAULT_SERVER)
        parser.add_argument('--git-version', dest='version', nargs='?', type=str, help='Git Version description', default='unknown')
        parser.add_argument('--tag', action='append')

        args = parser.parse_args()

        print('Job Client Running (%s) ... Press Ctrl-C to stop' % args.server)

        client = JobClient(args.server, args.version, args.tag)
        client.loop_forever()
