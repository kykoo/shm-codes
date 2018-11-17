#!/usr/bin/python3

import os
import glob
import time
import subprocess
import datetime
from numpy import *
import socket


# SAMPLING PERIOD (SEC)
Ts = 2
# LOG FILE PATH
path = '/home/pi/data/'


# TIME FOR NEXT SAMPLING
time_k = ceil(datetime.datetime.now().timestamp() / Ts) * Ts
# 1-WIRE DRIVER
os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')
base_dir = '/sys/bus/w1/devices/'
device_folder = glob.glob(base_dir + '28*')[0]
device_file = device_folder + '/w1_slave'
# FILENAME
fileName = ''
# FILE OBJECT
file = ''
# HOSTNAME
hostName = socket.gethostname()


def read_temp():
    lines = read_temp_raw()
    while lines[0].strip()[-3:] != 'YES':
        time.sleep(0.2)
        lines = read_temp_raw()
    equals_pos = lines[1].find('t=')
    if equals_pos != -1:
        temp_string = lines[1][equals_pos + 2:]
        temp_c = float(temp_string) / 1000.0
        return temp_c


def read_temp_raw():
    catdata = subprocess.Popen(['cat', device_file], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = catdata.communicate()
    out_decode = out.decode('utf-8')
    lines = out_decode.split('\n')
    return lines


def save(time, temperature):
    global hostName, path, fileName, file
    time_ = floor(time / (3600 * 24)) * 3600 * 24
    fileName_ = hostName + '-tmp-' + \
                datetime.datetime.fromtimestamp(time_).strftime('%Y%m%d') + \
                '.txt'
    if len(fileName) == 0:
        fileName = fileName_
        file = open(path + fileName, 'a')
    elif fileName != fileName_:
        file.close()
        fileName = fileName_
        file = open(path + fileName, 'a')
    file.write(datetime.datetime.fromtimestamp(time).strftime('%Y-%m-%d %H:%M:%S') +
               ', ' + str(temperature) + '\n')
    # file.flush()
    # os.fsync(file)
    return


def measure():
    global time_k
    time_now = datetime.datetime.now().timestamp()
    temperature = read_temp()
    if time_k < time_now:
        save(time_k, temperature)
        # print(datetime.datetime.fromtimestamp(time_now).strftime('%Y-%m-%d %H:%M:%S'), temperature)
        time_k = ceil(time_now / Ts) * Ts
    return


def set_Ts(samplingPeriod):
    global Ts, time_k
    Ts = samplingPeriod
    time_k = ceil(datetime.datetime.now().timestamp() / Ts) * Ts
    return


if __name__ == '__main__':

    while True:
        # print(read_temp_raw())
        # print(read_temp())
        # time.sleep(1)
        measure()
