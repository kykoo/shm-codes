#!/usr/bin/python3
# 
# DAQ FOR ANEMOMETER RM YOUNG 85004
# 
# 
# 
# 
# 

import time
from time import sleep
import serial
# TIME SAMPLING AND RESAMPLING
import datetime
from numpy import *
from matplotlib.pyplot import *
import pygame
import os
import matplotlib.dates as mdates
from scipy import signal

import pitft
import resample
from shm_daq_files import shm_daq_files


def parse_rx_buff():
    global rx_buff, windDAQfile

    while True:
        idx = rx_buff.find('\r')
        if idx == -1:
            break
        line  = rx_buff[:idx]
        try:
            data = line.split(' ')
            # DATA 
            windSpeed = float(data[1])
            windDir = float(data[2])
            status = float(data[3].split('*')[0])
            time = datetime.datetime.now().timestamp()
        except:
            windDAQfile.log('Error in converting str to float: line = [' + line)
        try:
            # print(time, windSpeed, windDir, status)
            time_k, data_k = resample.resample(Fs, time, [windSpeed, windDir, status])
            for j in range(len(time_k)):
                timestamp = datetime.datetime.fromtimestamp(time_k[j]).strftime('%m-%d %H:%M:%S.%f')
                print('{}, Ws={:5.1f} (m/s), Wd={:3.0f} (deg)'.format(
                    timestamp[0:-4],
                    data_k[j][0], data_k[j][1]))
            try:
                windDAQfile.save(time_k, data_k)
            except:
                windDAQfile.log('Error in data saving')
        except:
            windDAQfile.log('Error in resampling')
        # try:
        if state[1] == 2:
            pitft.plotyy(time_k, data_k)
        #except:
        #    windDAQfile.log('Error in plotyy')

        rx_buff = rx_buff[(idx+2):]
    return



def serial_rx_callback():
    global rx_buff
    # PROCESS OUTPUTS FROM GOM 
    while ser.inWaiting() > 0:
        try:
            rx_buff += ser.read(1).decode('UTF-8')
        except:
            pass
    if(len(rx_buff) > 0):
        parse_rx_buff()

def pushbutton_callback():
    global  state
    n = pitft.getButtonStroke()
    # print(n, state)
    if n:
        if state[1] == 1 and n == pitft.pinUpButton:
            state = [1, 2]
        elif state[1] == 2 and n == pitft.pinDownButton:
            state = [2, 1]
        # print(state)
    return

def state_transition_callback():
    global state
    if state[1] - state[0] == 1:
        pitft.guiOn()
        state[0] = state[1]
    elif state[1] - state[0] == -1:
        pitft.guiOff()
        state[0] = state[1]

# SETUP

 
#-------------------------
# STATE OF MACHINE
#
# 1 = DAQ
# 2 = TIME HISTORY PLOT
#-------------------------
state = [2, 2]  # [state_previous, state_current]

# BUTTON SETTING
pitft.pinUpButton = 27
pitft.pinDownButton = 22
pitft.begin()

#
# SERIAL OBJECT
#
ser = serial.Serial(
    port='/dev/ttyUSB0',
    baudrate=9600,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS
)
# ERROR CHECKING
if(ser.isOpen() is False):
    sys.exit('Serial is not open!')
    
# FLUSH INPUT BUFFER
while ser.inWaiting() > 0:
    # ser.reset_input_buffer() <- This simple approach doesn't work. Why?
    ser.read(1)

# RX BUFFER
rx_buff = ''

Fs = 4.0

# PYGAME
os.putenv('SDL_FBDEV', '/dev/fb1')
pygame.init()

#
# FILE OBJECT
#
windDAQfile = shm_daq_files('wnd', 3600*24)

# LOOP
while(True):

    pushbutton_callback()

    state_transition_callback()

    serial_rx_callback()

    sleep(0.05)

GPIO.cleanup()

