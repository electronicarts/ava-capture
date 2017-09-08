# Copyright (C) 2017 Electronic Arts Inc.  All rights reserved.

import serial # conda install PySerial
import time
import sys

class ArduinoHardWareSync():

    def __init__(self, comport):

        self.ok = False
        self.port = comport

        try:
            self.ser = serial.Serial(comport, 115200)
            self.ser.timeout = 0.5 # 1/2 second timeout
            self.ok = self.check_hw()

            if not self.ok: # Some serial ports need a moment to initialize
                time.sleep(1.0)
                self.ok = self.check_hw()
        except:
            # print 'Could no open COM Port %s' % comport
            pass

    @staticmethod
    def auto_detect_port():
        for i in range(10):
            if sys.platform == 'win32':
                comport = 'COM%d' % i
            else:
                comport = '/dev/ttyACM%d' % i
            test = ArduinoHardWareSync(comport) 
            if test.ok:
                return comport

    def is_active(self):
        return self.ok

    def check_hw(self):
        self.ser.write('I')
        return self.ser.read(2) == 'OK' 

    def read_char(self, nb_char=1, timeout_ms=500):
        start_time = time.time()
        while self.ser.inWaiting() < nb_char:
            wait_ms = (time.time() - start_time) * 1000.0
            if wait_ms > timeout_ms:
                raise Exception('Timeout reading serial')
        ret = self.ser.read(nb_char)
        return ret

    def current_framerate(self):
        if self.ok:
            for retry in range(5):
                try:
                    self.purge_port()
                    self.ser.write('F')
                    byte1 = ord(self.read_char())
                    byte2 = ord(self.read_char())
                    framerate = byte1*255 + byte2
                    byte1 = ord(self.read_char())
                    byte2 = ord(self.read_char())
                    duration = byte1*255 + byte2
                    return (framerate, duration)
                except:
                    print 'Failed current_framerate(), retrying %d' % retry 

    def start(self, framerate, duration_us=2000, external_sync=False):
        if self.ok:
            print 'HARDWARE SYNC - Start %d fps, %d us %s' % (framerate, duration_us, 'Slave' if external_sync else 'Master')
            framerate = min(max(framerate, 1), 300)
            duration = min(max(duration_us, 100), 65000)
            for retry in range(5):
                try:
                    self.purge_port()
                    if external_sync:
                        self.ser.write('E'+chr(framerate/255)+chr(framerate%255)+chr(duration/255)+chr(duration%255))
                    else:
                        self.ser.write('S'+chr(framerate/255)+chr(framerate%255)+chr(duration/255)+chr(duration%255))
                    ack = self.read_char(2)
                    break
                except:
                    print 'Failed start(), retrying %d' % retry 

    def stop(self):
        if self.ok:
            print 'HARDWARE SYNC - Stop'
            for retry in range(5):
                try:
                    self.purge_port()
                    self.ser.write('X')
                    ack = self.ser.read(2)
                    break
                except:
                    print 'Failed stop(), retrying %d' % retry 

    def purge_port(self):
        if self.ok:  
            while self.ser.inWaiting():
                self.read_one_char()

if __name__ == "__main__":

    # Test

    import time

    port = ArduinoHardWareSync.auto_detect_port()
    
    print 'Autodetected: %s' % port

    sync = ArduinoHardWareSync(port)
    if not sync.ok:
        print 'Failed'
        exit(1)

    for i in range(20):
        print 'Start %d Hz' % (10+i*10)
        sync.start(10+i*10, 1000, 0)
        print 'Current: %s Hz, duration is %s us' % sync.current_framerate()
        time.sleep(3)

    for i in range(20):
        print 'Start 60 Hz %d us' % (i*1000+1000)
        sync.start(60, i*1000+1000)
        print 'Current: %s Hz, duration is %s us' % sync.current_framerate()
        time.sleep(3)

    print 'Stopping'
    sync.stop()

    time.sleep(5)
