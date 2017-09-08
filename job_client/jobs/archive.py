#
# Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
#

import json
import shutil
import os
import time
import logging

from base import BaseJob

class ExportTake(BaseJob):
    def __call__(self, parameters, pipe, log):

        params = json.loads(parameters)

        if not 'root_export_path' in params:
            raise Exception('Error in parameters, "root_export_path" not found')
        if not 'nodes' in params:
            raise Exception('Error in parameters, "nodes" not found')

        child_to_launch = []

        # Launch one child job for each node that needs to copy files
        for node_name in params['nodes']:
            file_list = params['nodes'][node_name]            

            child_params = {'file_list':file_list, 'root_export_path':params['root_export_path'], 'delete_source_files':True}

            child_launch_info = {}
            child_launch_info['job_class'] = 'jobs.archive.CopyFiles'
            child_launch_info['params'] = json.dumps(child_params)
            child_launch_info['node_name'] = node_name
            child_launch_info['req_gpu'] = False

            child_to_launch.append(child_launch_info)

        self.yieldToChildren(child_to_launch)

    class Meta:
        description = 'This job is used to copy files from a local folder to a network storage'

def safeCopyFileGenerator(src, dest, block_size = 64*1024*1024):  

    if os.path.exists(dest):
        os.remove(dest)

    with open(src, 'rb') as fin:
        with open(dest, 'wb') as fout:
            arr = fin.read(block_size)
            while arr != "":
                fout.write(arr)
                yield len(arr)
                arr = fin.read(block_size)

class CopyFiles(BaseJob):
    def __call__(self, parameters, pipe, log):

        params = json.loads(parameters)

        delete_src_files = 'delete_source_files' in params and params['delete_source_files']

        if 'file_list' in params:

            copied_size = 0
            start_time = time.time()
            file_count = len(params['file_list'])
            copy_speed = 0

            for i,t in enumerate(params['file_list']):

                src,dest = t

                # destination folder
                try:
                    os.makedirs(dest)
                except:
                    pass
                if not os.path.exists(dest):
                    raise Exception('Cannot create folder %s' % dest)

                dest_file = os.path.join(dest,os.path.split(src)[1])
                log.info('Copy %s to %s' % (src, dest_file))                

                # Check if file already exists and should be skipped
                skip_file = False
                if os.path.exists(dest_file) and not os.path.exists(src):
                    log.info('Skip existing file: %s' % dest_file)
                    skip_file = True

                if not skip_file:
                    if not os.path.exists(src):
                        raise Exception('Source file does not exist: %s' % src)

                    file_size = os.path.getsize(src)

                    for copied in safeCopyFileGenerator(src, dest_file):
                        # Update stats
                        copied_size += copied

                        elapsed = time.time() - start_time
                        if elapsed > 0.0:
                            copy_speed = copied_size/1024/1024/elapsed

                        pipe.send('Copying file %d of %d (%d MB/s)' % (i+1,file_count,int(copy_speed)))

                    if not os.path.exists(dest_file):
                        raise Exception('Destination file does not exist: %s' % dest_file)
                    if not os.path.getsize(dest_file) == file_size:
                        raise Exception('File size mismatch: %s' % dest_file)
                
            # Everything copied, delete source files
            if delete_src_files:
                for src,dest in params['file_list']:
                    if os.path.exists(src):
                        log.debug('Deleting %s' % src)
                        try:
                            os.remove(src)
                        except:
                            log.error('Could not delete %s' % src)
        
        log.info('Done')

    class Meta:
        description = 'This job is used to copy files from a local folder to a network storage'

if __name__ == "__main__":

    # Test SafeCopyFile

    print 'Test SafeCopyFile'

    src = r'C:\ava_capture\20170508_094614\26681150_000.avi'
    dest = r'C:\ava_capture\20170508_094614\26681150_000b.avi'

    file_size = os.path.getsize(src)
    total = 0
    for x in safeCopyFileGenerator(src, dest, 8*1024*1024):
        total += x
        print total*100/file_size
