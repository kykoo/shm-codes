#!/usr/bin/python3

import array as array_
import datetime
import socket
import os
from numpy import *
import time

class shm_daq_files:
    'Class for handling data files from SHM systems'
    dataType = 0
    timeLength = 0
    hostName = ''
    datafilePath = '/home/pi/data'
    datafileName = ''
    logfilePath = '/home/pi/log'
    logfileName = ''
    dataFile = ''
    logFile = ''
    now = 0

    def __init__(self, dataType, timeLength):
        self.dataType = dataType
        self.timeLength = timeLength
        self.hostName = socket.gethostname()
        self.datafilePath = '/home/pi/data/'
        self.datafileName = ''
        self.logfilePath = '/home/pi/log/'
        self.logfileName = ''
        self.dataFile = ''
        self.logFile = ''
        self.now = datetime.datetime.now()

        # CREATE DIRECTORY IF NOT EXISTS
        directories = []
        if self.datafilePath:
            directories.append(self.datafilePath)
        if self.logfilePath:
            directories.append(self.logfilePath)
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory)

        
    def save(self, times, data):
        for i in range(len(times)):
            time_ = floor(times[i] / (self.timeLength)) * self.timeLength
            datafileName_ = self.hostName + '-' + self.dataType +'-' + \
                            datetime.datetime.fromtimestamp(time_).strftime("%Y%m%d-%H%M%S")
            if len(self.datafileName) == 0:
                self.datafileName = datafileName_
                self.dataFile = open(self.datafilePath + self.datafileName, "ba")
            elif self.datafileName != datafileName_:
                self.dataFile.close()
                self.datafileName = datafileName_
                self.dataFile = open(self.datafilePath + self.datafileName, "ba")
            data4file = array_.array('d', [times[i]] + data[i])
            data4file.tofile(self.dataFile)
        return

    def log(self, line):
        time_now = time.mktime(datetime.datetime.now().timetuple())
        time_ = floor(time_now / (3600 * 24)) * 3600 * 24
        # time_ = floor(time_now / (10)) * 10
        logfileName_ = self.hostName + '-' + self.dataType + '-' + \
                    datetime.datetime.fromtimestamp(time_).strftime("%Y%m%d") + ".log"
        if len(self.logfileName) == 0:
            self.logfileName = logfileName_
            self.logFile = open(self.logfilePath + self.logfileName, "a")
            self.logFile.write(line + '\n')
        elif self.logfileName == logfileName_:
            self.logFile.write(line + '\n')
        else:
            self.logFile.close()
            self.logfileName = logfileName_
            self.logFile = open(self.logfilePath + self.logfileName, "a")
            self.logFile.write(line + '\n')
        return

    def end(self):
        if not self.logFile:
            self.logFile.close()
        if not self.dataFile:
            self.dataFile.close()


if __name__ == '__main__':
    testFile = shm_daq_files('test', 5)
    while True:
        t = datetime.datetime.now().timestamp()
        data  = [1, 2, 3]
        testFile.save(t, data)
        
        
