# Copyright (C) 2017 Electronic Arts Inc.  All rights reserved.

import sys
import os
import subprocess
site_packages_path = os.path.join(os.path.split(__file__)[0], 'site-packages')
if os.path.exists(site_packages_path):
    sys.path.append(site_packages_path)

import hardware_sync
import avacapture

# Initialize Arduino-based hardware sync
port = hardware_sync.ArduinoHardWareSync.auto_detect_port()
if port:
	sync = hardware_sync.ArduinoHardWareSync(port)
	if sync.ok:
		avacapture.set_sync(sync)


# Notification Listener will recieve events from avacapture
class DefaultNotificationListener():
	def __init__(self):
		pass
	def receiveMessage(self, message):
		#print "PYTHON> TODO Receive Generic Message : %s" % message
		pass
	def changeState(self, state):
		#print "PYTHON> TODO Listener Change State : %s" % state
		pass

avacapture.add_listener(DefaultNotificationListener())
