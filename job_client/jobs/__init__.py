#
# Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
#

from __future__ import print_function
from __future__ import absolute_import

import traceback
import importlib


from .base import BaseJob


import os
import sys

# Import all job modules
module_list = ['archive','test']

for module_name in module_list:
    try:
        importlib.import_module('.'+module_name,__name__)
    except:
        print('Could not import %s\n%s' % (module_name, traceback.format_exc(limit=3)))
