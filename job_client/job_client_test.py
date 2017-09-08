#
# Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
#

import unittest
import tempfile
import job_client
import os

class TestJobs(unittest.TestCase):

    testparams = {'value':42, 'name':'hello'}

    def test_DummyJob(self):
        job1 = job_client.JobInstance(self.testparams, 'jobs.test.DummyJob') 
        r = job1.blocking_run()

        self.assertTrue('success' in r)
        self.assertTrue(r['success'])
      
    def test_DummyJobRaisingException(self):
        job1 = job_client.JobInstance(self.testparams, 'jobs.test.DummyJobRaisingException') 
        r = job1.blocking_run()      

        self.assertTrue('success' in r)
        self.assertFalse(r['success'])

        self.assertTrue('exception' in r)
        self.assertTrue(len(r['exception'])>10)

    def test_DummyJobSubprocess(self):
        job1 = job_client.JobInstance(self.testparams, 'jobs.test.DummyJobSubprocess') 
        r = job1.blocking_run()

        self.assertTrue('success' in r)
        self.assertTrue(r['success'])

    def test_DummyJobSubprocessFail(self):
        job1 = job_client.JobInstance(self.testparams, 'jobs.test.DummyJobSubprocessFail') 
        r = job1.blocking_run()

        self.assertTrue('success' in r)
        self.assertFalse(r['success'])

    def test_DummyJobSubprocessCaptureOutput(self):

        logfilename = os.path.join(tempfile.gettempdir(), 'test_DummyJobSubprocessCaptureOutput.txt')

        job1 = job_client.JobInstance(self.testparams, 'jobs.test.DummyJobSubprocessCaptureSmallOutput', log_filename=logfilename) 
        r = job1.blocking_run()
        self.assertTrue('success' in r)
        self.assertTrue(r['success'])

        self.assertGreater(os.path.getsize(logfilename), 500)
        os.remove(logfilename)

        job1 = job_client.JobInstance(self.testparams, 'jobs.test.DummyJobSubprocessCaptureOutput', log_filename=logfilename) 
        r = job1.blocking_run()
        self.assertTrue('success' in r)
        self.assertTrue(r['success'])

        os.remove(logfilename)

        job1 = job_client.JobInstance(self.testparams, 'jobs.test.DummyJobSubprocessCaptureOutputFail', log_filename=logfilename) 
        r = job1.blocking_run()
        self.assertTrue('success' in r)
        self.assertFalse(r['success'])

        os.remove(logfilename)

    def test_DummyJobWithLog(self):
        logfilename = os.path.join(tempfile.gettempdir(), 'test_DummyJobWithLog.txt')
        if os.path.exists(logfilename):
            os.remove(logfilename)

        job1 = job_client.JobInstance(self.testparams, 'jobs.test.DummyJobWithLog', log_filename=logfilename) 
        r = job1.blocking_run()

        self.assertTrue(os.path.exists(logfilename))
        os.remove(logfilename)

        self.assertTrue('success' in r)
        self.assertTrue(r['success'])

        # These jobs should also run if there is no log filename provided      
        job1 = job_client.JobInstance(self.testparams, 'jobs.test.DummyJobWithLog') 
        r = job1.blocking_run()
        self.assertTrue(r['success'])

        job1 = job_client.JobInstance(self.testparams, 'jobs.test.DummyJobSubprocessCaptureOutput') 
        r = job1.blocking_run()
        self.assertTrue(r['success'])

class TestJobContainer(unittest.TestCase):

    testparams = {'value':43, 'name':'hello'}

    def test_simple(self):
        container = job_client.JobContainer(tempfile.gettempdir())
    
    def test_submit(self):
        container = job_client.JobContainer(tempfile.gettempdir())
        container.submit_job(self.testparams, 'jobs.test.DummyJob', 1)
        container.submit_job(self.testparams, 'jobs.test.DummyJob', 2)
        self.assertEqual(container.running_jobs_count() + container.finished_jobs_count(), 2)
        container.wait()
        self.assertEqual(container.running_jobs_count(), 0)
        self.assertEqual(container.finished_jobs_count(), 2)
        container.submit_job(self.testparams, 'jobs.test.DummyJob', 3)
        container.wait()
        self.assertEqual(container.running_jobs_count(), 0)
        self.assertEqual(container.finished_jobs_count(), 3)

class TestJobs_VH27(unittest.TestCase):

    testparams = {}

    def test_DummyJobVH27(self):
        job1 = job_client.JobInstance(self.testparams, 'jobs.test.DummyJobVH27') 
        r = job1.blocking_run()

        self.assertTrue('success' in r)
        self.assertTrue(r['success'])

if __name__ == '__main__':
    unittest.main()
