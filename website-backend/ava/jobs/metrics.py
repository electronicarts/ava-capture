
from prometheus_client import Gauge
from models import FarmJob

def job_count_running(status):
    return FarmJob.objects.filter(status=status).count()

def setup():
    d = Gauge('job_count_ready', 'Number of jobs currently ready')
    d.set_function(lambda: job_count_running('ready'))
    d = Gauge('job_count_running', 'Number of jobs currently running')
    d.set_function(lambda: job_count_running('running'))
