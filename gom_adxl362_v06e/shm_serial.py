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
import serial
from time import sleep


ser = ''
port = '/dev/serial0'
baudrate = 115200 
parity = serial.PARITY_NONE
stopbits = serial.STOPBITS_ONE
bytesize = serial.EIGHTBITS

rx_buff = bytes()
#rx_buff = ''


def begin():
    global ser
    
    # SERIAL OBJECT
    ser = serial.Serial(
        port = port,
        baudrate = baudrate,
        parity = parity,
        stopbits = stopbits,
        bytesize = bytesize,
        timeout = 0.01
    )
    # ERROR CHECKING
    if(ser.isOpen() is False):
        sys.exit('Serial is not open!')

    # FLUSH INPUT BUFFER
    ser.reset_input_buffer()
    #while ser.inWaiting() > 0:
    #    # ser.reset_input_buffer() <- This simple approach doesn't work. Why?
    #    ser.read(1)


def rx_polling():
    global ser, rx_buff
    # PROCESS OUTPUTS FROM GOM
    if ser.in_waiting > 0:
        try:
            #rx_buff += ser.read(100).decode('UTF-8')
            rx_buff += ser.read(100)
        except:
            pass
    return


if __name__ == '__main__':

    begin()
    sleep(0.01)
    while True:
        # print(ser.inWaiting())
        rx_polling()
        if len(rx_buff)>0:
            #print(rx_buff.decode('utf-8'))
            # rx_buff = bytes()
            print(rx_buff)
            rx_buff = ''
        #sleep(0.1)
            
            
        
