#
# Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
#

from __future__ import absolute_import
import threading
import subprocess
import traceback

class PopenWithTimeout(object):
    """
    Enables to run subprocess commands in a different thread with TIMEOUT option.
    based on https://gist.github.com/kirpit/1306188
    """
    command = None
    process = None
    status = None
    output, error = '', ''

    def __init__(self, command):
        self.command = command

    def run(self, timeout, **kwargs):
        """ Run a command then return: (status, output, error). """
        def target(**kwargs):
            try:
                self.process = subprocess.Popen(self.command, **kwargs)
                self.output, self.error = self.process.communicate()
                self.status = self.process.returncode
            except:
                self.error = traceback.format_exc()
                self.status = -1
        # default stdout and stderr
        if 'stdout' not in kwargs:
            kwargs['stdout'] = subprocess.PIPE
        if 'stderr' not in kwargs:
            kwargs['stderr'] = subprocess.PIPE
        # thread
        thread = threading.Thread(target=target, kwargs=kwargs)
        thread.start()
        thread.join(timeout)
        if thread.is_alive():
            self.process.kill()
            thread.join()
        return self.status, self.output, self.error