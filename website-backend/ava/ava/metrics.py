
# Prometheus Metrics

from prometheus_client import Gauge
from ava.settings import BASE_DIR
import os

def storage_available_thumb():
    # returns the storage space available for thumbnails
    s = os.statvfs(os.path.join(BASE_DIR, 'static', 'thumb'))
    return s.f_bsize * s.f_bavail

def setup():
    d = Gauge('storage_space_thumb', 'Available Storage Space for Thumbnails')
    d.set_function(storage_available_thumb)
