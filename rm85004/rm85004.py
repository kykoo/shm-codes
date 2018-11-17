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
import RPi.GPIO as GPIO
import sys
import os
import socket
import datetime
# KEYSTROKE READING
import select
import tty
import termios
# TIME SAMPLING AND RESAMPLING
import datetime
from numpy import *
from matplotlib.pyplot import *
import pygame
import os
import matplotlib.dates as mdates
from scipy import signal
import array as array_


def save(time, data):

    global fileName, file

    # time_ = floor(time / (3600 * 24)) * 3600 * 24
    time_ = floor(time / (3600 * 1)) * 3600 * 1
    fileName_ = hostName + '-acc-' + \
                datetime.datetime.fromtimestamp(time_).strftime("%Y%m%d-%H")
    if len(fileName) == 0:
        file = open(path + fileName_, "ba")
        fileName = fileName_
    elif fileName != fileName_:
        file.close()
        file = open(path + fileName_, "ba")
        fileName = fileName_
    data4file = array_.array('d', data)
    data4file.tofile(file)
    return


def parse(rx_buff):

def check_keyboard_inputs():
    global Buttons
    if isKeyStrokeAvailable():
        c = sys.stdin.read(1)
        if c == '\x1b':	    # x1b is ESC
            return True
        elif c == '\x75':	    # (u)p
            Buttons[1]['isPressed'] = True
            return False
        elif c == '\x64':	    # (d)own
            Buttons[0]['isPressed'] = True
            return False
    else:
        return False    

def check_pushbutton_inputs():
    global Buttons
    for ibutton in range(0, len(Buttons)):
        button = Buttons[ibutton]
        reading = GPIO.input(button['Number'])
        readingPrev = button['readingPrev']
        time_ = button['timeDetected']
        now = datetime.datetime.now()
        if(reading == 0 and readingPrev == 1 and now - time_ > debounce):
            button['isPressed'] = True
            button['timeDetected'] = datetime.datetime.now()
        button['readingPrev'] = reading

def check_statetransition():
    global Buttons
    # HAND OVER COMMAND TO GOM OVER SERIAL 
    for ibutton in range(0, len(Buttons)):
        if Buttons[ibutton]['isPressed'] is True:
            cmd = Buttons[ibutton]['cmd']
            dstate = Buttons[ibutton]['dstate']
            ser.write(cmd.encode())
            Buttons[ibutton]['isPressed'] = False

            if state == 4:
                if dstate == -1:
                    pygame.display.quit()
            state += dstate
            if state > 5:
                state = 5
            if state < 1:
                state = 1
def check_serial_rx():
    # PROCESS OUTPUTS FROM GOM 
    while ser.inWaiting() > 0:
        try:
            rx_buff += ser.read(1).decode('UTF-8')
        except:
            sys.stdout.write('')
    if(len(rx_buff) > 0):
        # rx_buff = parse(rx_buff)
        # pass
        print(rx_buff)
        rx_buff = ''

                  
# SETUP

# CONFIGURATION
nsec_timehistoryPlot = 4  # of sec for time history plot
npoints_PSD = 2**10  # of data points in PSD calculation
NFFT = 2**9
# Fs = 100.0
Fs = 50.0
dt = 1/Fs
tk = []

#
# STATE OF MACHINE
#
# SOM is identified by messages from GOM
#
# 0 = UNKNOWN
# 1 = DAQ
# 2 = TIME HISTORY PLOT
# 3 = PSD PLOT

state = [0, 0] # [previous_state, current_state]
bootSequence = True

dispFreq = 10
dispCount = 1

npoints_THP = int(Fs) * nsec_timehistoryPlot
now = datetime.datetime.now()
time4THP = array([now for i in range(npoints_THP)]) 
data4THP = zeros((npoints_THP, 3))   # X, Y, Z
data4PSD = zeros((npoints_PSD, 3))   # X, Y, Z
Pxx = zeros((int(NFFT/2) + 1, 3))    # Pxx, Pyy, Pzz
curDataTHP = 0
curDataPSD = 0
nAverageOfPSD = 0
waitUntilStoreTH = True
waitUntilStorePSD = True


# SERIAL SETTING
# ser = serial.Serial(
#     port='/dev/serial0',
#     baudrate=115200,
#     parity=serial.PARITY_NONE,
#     stopbits=serial.STOPBITS_ONE,
#     bytesize=serial.EIGHTBITS
# )
ser = serial.Serial(
    port='/dev/ttyUSB0',
    baudrate=9600,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS
)
if(ser.isOpen() is False):
    sys.exit('Serial is not open!')
## FLUSH INPUT BUFFER
while ser.inWaiting() > 0:
    ser.read(1)  # ser.reset_input_buffer() <- This simple approach doesn't work. Why?
## RX BUFFER
rx_buff = ''


# FILE SETTING
hostName = socket.gethostname()
now = datetime.datetime.now()
path = '/home/pi/data/'
fileName = ''
file = ''
## create directory if not exists
directories = [path]
for directory in directories:
    if not os.path.exists(directory):
        os.makedirs(directory)




cmd = ''

# LOOP
while(True):
    if(check_keyboard_strokes()):
        break
    check_pushbutton_strokes()
    check_state_transition()
    check_serial_rx()
    sleep(0.05)

GPIO.cleanup()
file.close()
