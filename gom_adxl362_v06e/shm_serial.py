#!/usr/bin/python3

#
# Module for handling serial for SHMS
#
#

import array as array_
import datetime
import socket
import os
from numpy import *
import time

ser = ''
port = '/dev/ttyUSB0'
baudrate = 9600 
parity = serial.PARITY_NONE
stopbits = serial.STOPBITS_ONE
bytesize = serial.EIGHTBITS

rx_buff = ''


def begin():
    global ser
    
    # SERIAL OBJECT
    ser = serial.Serial(
        port = port,
        baudrate = baudrate,
        parity = parity
        stopbits = stopbits
        bytesize = bytesize
    )
    # ERROR CHECKING
    if(ser.isOpen() is False):
        sys.exit('Serial is not open!')

    # FLUSH INPUT BUFFER
    while ser.inWaiting() > 0:
        # ser.reset_input_buffer() <- This simple approach doesn't work. Why?
        ser.read(1)


def rx_callback():
    global rx_buff
    # PROCESS OUTPUTS FROM GOM 
    while ser.inWaiting() > 0:
        try:
            rx_buff += ser.read(1).decode('UTF-8')
        except:
            pass
    if(len(rx_buff) > 0):
        parse_rx_buff()


if __name__ == '__main__':

    while True:
        pass
        
