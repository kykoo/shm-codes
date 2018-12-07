#!/usr/bin/python3

#
# Module for saving data and logging messages
#
#

import array as array_
import datetime
import socket
import os
from numpy import *
import time
import logging


class shm_daq_files:
    'Class for handling data files from a SHM system'
    dataType = 0
    timeLength = 0
    hostName = ''
    datafilePath = '/home/pi/data'
    datafileName = ''
    dataFile = ''
    now = 0

    def __init__(self, dataType, timeLength):
        self.dataType = dataType
        self.timeLength = timeLength
        self.hostName = socket.gethostname()
        self.datafilePath = '/home/pi/data/'
        self.datafileName = ''
        self.dataFile = ''
        self.now = datetime.datetime.now()

        # CREATE DIRECTORY IF NOT EXISTS
        directories = []
        if self.datafilePath:
            directories.append(self.datafilePath)
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory)

        
    def save(self, resampledData):

        isDataSaved = False
        for dataRow in resampledData:
            time = dataRow[0]
            time_ = floor(time / (self.timeLength)) * self.timeLength
            datafileName_ = self.hostName + '-' + self.dataType +'-' + \
                            datetime.datetime.fromtimestamp(time_).strftime("%Y%m%d-%H%M%S")
            if len(self.datafileName) == 0:
                # CREATING THE FIRST DATA FILE
                
                # calculate how long daq can be carried out 
                s = os.statvfs('/')
                free_space = (s.f_bavail * s.f_frsize) / 1024
                logger.info('Free Disk Space = {:.0f} (MB), DAQ time-length = {:.1f} (hr)'.format(
                    free/1024,free/(8*4*400*3600)))
                
                self.datafileName = datafileName_
                self.dataFile = open(self.datafilePath + self.datafileName, "ba")
                logger = logging.getLogger(__name__)
                logger.info('file created: {}'.format(self.datafileName) +\
                            ' ' * (53 - 14 - len(self.datafileName)))
            elif self.datafileName != datafileName_:
                self.dataFile.close()
                self.datafileName = datafileName_
                self.dataFile = open(self.datafilePath + self.datafileName, "ba")
                logger = logging.getLogger(__name__)
                logger.info('file created: {}'.format(self.datafileName) +\
                            ' ' * (53 - 14 - len(self.datafileName)))
            data4file = array_.array('d', dataRow)
            data4file.tofile(self.dataFile)
            isDataSaved = True
        return isDataSaved

    def end(self):
        if not isinstance(self.dataFile,str):
            self.dataFile.close()


if __name__ == '__main__':
    testFile = shm_daq_files('test', 5)
    while True:
        t = datetime.datetime.now().timestamp()
        data  = [1, 2, 3]
        testFile.save(t, data)
        
        
    

#    def log(self, line):
#        time_now = time.mktime(datetime.datetime.now().timetuple())
#        time_ = floor(time_now / (3600 * 24)) * 3600 * 24
#        # time_ = floor(time_now / (10)) * 10
#        logfileName_ = self.hostName + '-' + self.dataType + '-' + \
#                    datetime.datetime.fromtimestamp(time_).strftime("%Y%m%d") + ".log"
#        if len(self.logfileName) == 0:
#            self.logfileName = logfileName_
#            self.logFile = open(self.logfilePath + self.logfileName, "a")
#            self.logFile.write(line + '\n')
#        elif self.logfileName == logfileName_:
#            self.logFile.write(line + '\n')
#        else:
#            self.logFile.close()
#            self.logfileName = logfileName_
#            self.logFile = open(self.logfilePath + self.logfileName, "a")
#            self.logFile.write(line + '\n')
#        return
