#
# Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
#

from base import BaseJob

import os
import sys

# Import all job modules

try:
    import archive
except:
    print 'Could not import archive'

try:
    import thumbnails
except:
    print 'Could not import thumbnails'

try:
    import test
except:
    print 'Could not import test'
