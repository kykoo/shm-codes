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
import glob


class shm_daq_files:
    'Class for handling data files from a SHM system'
    dataType = 0
    timeLength = 0
    hostName = ''
    datafilePath = '/home/pi/data'
    datafileName = ''
    dataFile = ''
    now = 0
    minDiskSpace = 0 # MB, If free diskspace is lower than this, delete datafiles

    def __init__(self, dataType, timeLength, minDiskSpace = 100):
        self.dataType = dataType
        self.timeLength = timeLength
        self.hostName = socket.gethostname()
        self.datafilePath = '/home/pi/data/'
        self.datafileName = ''
        self.dataFile = ''
        self.now = datetime.datetime.now()
        self.minDiskSpace = minDiskSpace

        # CREATE DIRECTORY IF NOT EXISTS
        directories = []
        if self.datafilePath:
            directories.append(self.datafilePath)
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory)
        return


    def save(self, resampledData):
               
        isDataSaved = False
        logger = logging.getLogger(__name__)
        for dataRow in resampledData:
            time = dataRow[0]
            time_ = floor(time / (self.timeLength)) * self.timeLength
            datafileName_ = self.hostName + '-' + self.dataType +'-' + \
                            datetime.datetime.fromtimestamp(time_).strftime("%Y%m%d-%H%M%S")
            if len(self.datafileName) == 0:
                # CHECK FREE DISK-SPACE 
                s = os.statvfs('/')
                free_space = (s.f_bavail * s.f_frsize) # Bytes
                logger.info('Free DiskSpace= {:,.0f}(MB), DAQ timeLength= {:.0f}(Hr)'.format(
                    free_space/1024/1000,free_space/(8*4*400*3600)))

                # CREATING THE FIRST DATA FILE
                self.datafileName = datafileName_
                self.dataFile = open(self.datafilePath + self.datafileName, "ba")
                logger.info('File Created: {}'.format(self.datafileName) +\
                            ' ' * (53 - 14 - len(self.datafileName)))
            elif self.datafileName != datafileName_:
                self.dataFile.close()

                # DELETE FILES IF FREE DISK-SPACE IS LOWER THAN minDiskSpace
                files = sorted(glob.glob(
                    self.datafilePath + self.hostName + '-' + self.dataType + '*'))
                s = os.statvfs('/')
                # logger.info('minDiskSpace={}'.format(self.minDiskSpace))
                while (s.f_bavail*s.f_frsize)/1024/1000 < self.minDiskSpace:
                    os.remove(files[0])
                    str = 'File Deleted: ' + os.path.basename(files[0]) + ' FDS= {:,.0f}'.format(
                        (s.f_bavail*s.f_frsize)/1024/1000)
                    logger.info(str + ' ' * (53 - len(str)))
                    s = os.statvfs('/')
                    files = sorted(glob.glob(
                        self.datafilePath + self.hostName + '-' + self.dataType + '*'))

                # MOVES TO NEXT FILE
                self.datafileName = datafileName_
                self.dataFile = open(self.datafilePath + self.datafileName, "ba")
                logger.info('File Created: {}'.format(self.datafileName) +\
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
