#!/usr/bin/python3
#
#  ADXL INTERFACE APPLICATION
#
#  
#  - Time Sampling
#  - Resampling
#
#  written by k.y.koo@exeter.ac.uk
#
#
# ADXL362: 400 Hz Fs
#          LPF@200Hz
#          Ultralow noise mode
#
# 29 Nov 2018: 400 Hz version, logging added
# 20 Mar 2018: Auto Starting procedure implemented
#




import time
from time import sleep
import sys
sys.path.append('./pitft')

import pitft
import keyStroke
import shm_serial
from shm_daq_files import shm_daq_files

import RPi.GPIO as GPIO
import os
import socket
import datetime
from numpy import *
from matplotlib.pyplot import *
import matplotlib.dates as mdates
from scipy import signal
import array as array_
import re
import logging, logging.handlers


Fs = 400.0
SENSITIVITY = 0.004
# |    | Sensitivity |
# |----+-------------|
# | 2g |       0.001 |
# | 4g |       0.002 |
# | 8g |       0.004 |

# PiTFT CONFIGURATION
pitft.timehistoryPlot = 4  # of sec for time history plot
pitft.Fs = Fs
pitft.npoints_PSD = 2**10  # of data points in PSD calculation
pitft.NFFT = 2**9

#----------------------------------------------------------------------
# STATE OF THE MACHINE SOM
#
# SOM is identified by messages from GOM
#
# 0 = NOT USED
# 1 = OUTPUTTING CC AND TIME OF PPS
# 2 = SILENCE
# 3 = DAQ
# 4 = TIME HISTORY PLOT
# 5 = PSD PLOT

state = [1, 1]
state_guiOnOff = [0, 0, 0, 0, 1, 1]
state_max = len(state_guiOnOff) -1
bootSequence = True
arduinoCMD = '' # Command to be sent to Arduino via UART

ppsCC_Time = {'t':None, 'CC':None, 'Fclk':None}
daqCC_Values = {'t':None, 'CC':None, 'valXYZ':None}
tk = []
resampledData = []
nPPS = 0
writeCount = 0
ppsString = ''  # "3,CC_H,CC_H"

def pushButton_keyStroke_callback():

    # pushButton_callback
    global  state, pitft, keyStroke, arduinoCMD

    # Up button
    if pitft.Buttons[1]['isPressed'] == True:
        if state[1] < state_max:
            state[0] = state[1]
            state[1] = state[1] + 1
            pitft.Buttons[1]['isPressed'] = False
            arduinoCMD = 'u'
            logger.debug('state = {}'.format(state))

    # Down button
    if pitft.Buttons[0]['isPressed'] == True:
        if state[1] > 1:
            state[0] = state[1]
            state[1] = state[1] - 1
            pitft.Buttons[0]['isPressed'] = False
            arduinoCMD = 'd'
            logger.debug('state = {}'.format(state))
            
    # keyStroke_callback
    if keyStroke.keyNumber == 117: # 'u'
        arduinoCMD = 'u'        
        # print('u pressed')
    if keyStroke.keyNumber == 100: # 'd'
        arduinoCMD = 'd'
        # print('d pressed')
    if keyStroke.keyNumber == 113: # 'q'
        return True
    
    keyStroke.keyNumber = 0

    # ON/OFF GUI
    if state_guiOnOff[state[1]] == 0:
        # pitft.guiOnOff(state_guiOnOff[state[1]])
        pitft.guiOnOff(0)

    # SENDING arduinoCMD
    if arduinoCMD:
        shm_serial.ser.write(arduinoCMD.encode())
        logger.debug('Arduino cmd = {} sent'.format(arduinoCMD))
        arduinoCMD = ''

    return False 

#def print_std(string):
    
def parse_rx_buff():
    global shm_serial, bootSequence, pitft
    global ppsCC_Time, daqCC_Values, tk, resampledData, nPPS, ppsString

    printed_with_end_option = False
    # True if print(...,end='\r') is executed.
    # Then, a LF needs to be inserted to make the output correct
   
    while True:

        # Find \r\n to identify msgID and msg Content
        match = re.search(b'\r\n', shm_serial.rx_buff)

        # In case no CR/NL found, break to wait till new data comes
        if not match:
            break

        # In case the data string is empty, skip to next data string after CR/NL
        if match.start() == 0:
            shm_serial.rx_buff = shm_serial.rx_buff[match.end():]
            continue
        
        # msgID = 0: MESSAGES
        if shm_serial.rx_buff[0] == 48: # 0
            if printed_with_end_option:
                sys.stdout.write('\n')
                printed_with_end_option = False 
            logger.info(shm_serial.rx_buff[:match.start()].decode('UTF-8'))

            # AUTO-STARTUP
            if bootSequence is True and shm_serial.rx_buff[0:8].decode('UTF-8') == '0,state=':
                ARD_state = shm_serial.rx_buff[8]
                if ARD_state == 50: # 2
                    pitft.Buttons[1]['isPressed'] = True
                if ARD_state == 51: # 3
                    bootSequence = False  # FINISH BOOT SEQEUNCE

        # msgID = 1: UPDATE ppsCC_Time
        elif shm_serial.rx_buff[0] == 49: # 1
            logger.info(shm_serial.rx_buff[:match.start()].decode('UTF-8'))

            try:
                rx_buff_split = shm_serial.rx_buff[:match.start()].decode('UTF-8').split(',')
                t = float(rx_buff_split[3])
                CC = float(rx_buff_split[1])*2**16 + float(rx_buff_split[2])
            except:
                shm_serial.rx_buff = shm_serial.rx_buff[match.end():]
                logger.debug("parsing PPS-CC of msgID=1 failed. Byte array = {}".format(
                    shm_serial.rx_buff[:match.start()]))
                continue
                
            if not ppsCC_Time['t']:
                ppsCC_Time['t'] = t
                ppsCC_Time['CC'] = CC
            else:
                ppsCC_Time['Fclk'] = (CC -  ppsCC_Time['CC'])/(t - ppsCC_Time['t'])
                ppsCC_Time['t'] = t
                ppsCC_Time['CC'] = CC

            # AUTO-STARTUP
            if bootSequence is True:
                if state[1] == 1:
                    nPPS += 1
                    if nPPS > 2:
                        pitft.Buttons[1]['isPressed'] = True


        # msgID = 2: DAQ with TIMESTAMP
        elif shm_serial.rx_buff[0] == 50: # 2
            try:
                CC = float(int.from_bytes(shm_serial.rx_buff[1:5],'little',signed=True) * 2**16 + \
                           int.from_bytes(shm_serial.rx_buff[5:7],'little',signed=True))
                valXYZ = [float(int.from_bytes(shm_serial.rx_buff[7:9  ],'little',signed=True))*SENSITIVITY,
                          float(int.from_bytes(shm_serial.rx_buff[9:11 ],'little',signed=True))*SENSITIVITY,
                          float(int.from_bytes(shm_serial.rx_buff[11:13],'little',signed=True))*SENSITIVITY]
                t = ppsCC_Time['t'] + (CC - ppsCC_Time['CC']) / ppsCC_Time['Fclk'] * 1.0
            except:
                shm_serial.rx_buff = shm_serial.rx_buff[match.end():]
                logger.debug("parsing DAQ byte array of msgID=2 failed. Byte array = {}".format(
                    shm_serial.rx_buff[:match.start()]))
                continue
             
            # STORE INITIAL MEASUREMENT
            if not daqCC_Values['CC']:
                daqCC_Values['CC'] = CC
                daqCC_Values['valXYZ'] = valXYZ
                daqCC_Values['t'] = t
                tk = float(ceil(daqCC_Values['t']*Fs))/Fs
             
            # Resampling
            elif tk <= t:
                # import pdb;pdb.set_trace()
                while tk <= t:
                    valXYZ_intp = [0, 0, 0]
                    for j in range(3):
                        valXYZ_intp[j] = interp(tk, [daqCC_Values['t'], t],
                                                [daqCC_Values['valXYZ'][j], valXYZ[j]])
                    if round(tk*10)/10 == tk:
                        timeString = datetime.datetime.fromtimestamp(tk).strftime('%H:%M:%S.') +\
                                     '{:0>3d}'.format(round((tk%1)*1000))
                        outString = '{}, {:.3f}, {:.3f}, {:.3f}'.format(
                            timeString[:12], valXYZ_intp[0], valXYZ_intp[1], valXYZ_intp[2])
                        #outString = '{:.3f}, {:.3f}, {:.3f}, {:.3f} {}'.format(
                        #    tk, valXYZ_intp[0], valXYZ_intp[1], valXYZ_intp[2], ppsString)
                        outString = outString + ' ' * (53-len(outString)-len(ppsString)) + ppsString
                        print(outString, end='\r')
                        printed_with_end_option = True 

                    # store resampled data
                    resampledData.append([tk, valXYZ_intp[0], valXYZ_intp[1], valXYZ_intp[2]])

                    tk = round(tk * Fs + 1.0) / Fs
                # Replacing daqCC_Values with new values
                daqCC_Values['CC'] = CC
                daqCC_Values['valXYZ'] = valXYZ
                daqCC_Values['t'] = t
             
            # REPLACING daqCC_Values with new values
            elif tk > t:
                daqCC_Values['CC'] = CC
                daqCC_Values['valXYZ'] = valXYZ
                daqCC_Values['t'] = t

        # msgID = 3 : UPDATE ppsCC_Time based on CC only
        elif shm_serial.rx_buff[0] == 51: # 3

            ppsString = '('+shm_serial.rx_buff[:match.start()].decode('UTF-8') + ')'
            # sys.stdout.write(outString.expandtabs(53-len(outString)+2-2))
            logger.debug(ppsString[1:-1])
            try:
                rx_buff_split = shm_serial.rx_buff[:match.start()].decode('UTF-8').split(',')
                CC = float(rx_buff_split[1])*2**16 + float(rx_buff_split[2])
                dT = float(round((CC - ppsCC_Time['CC']) / ppsCC_Time['Fclk']))
                ppsCC_Time['CC'] = CC
                ppsCC_Time['t'] = ppsCC_Time['t'] + dT
            except:
                logger.debug("parsing msgID=3 failed. MSG content is {}".format(shm_serial.rx_buff[:match.start()]))

        # unknown msgID : UNRECOGNISED DATA
        else:
            logger.debug('Unrecognised msgID = {}, byte array [2:]={}'.format(
                shm_serial.rx_buff[0],shm_serial.rx_buff[:match.start()]))
            

        # MOVE TO THE NEXT DATA STRING
        shm_serial.rx_buff = shm_serial.rx_buff[match.end():]

    return



# RESET GOM
RESET_PIN = 16
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(RESET_PIN, GPIO.OUT)
GPIO.output(RESET_PIN, GPIO.LOW)
sleep(1)
GPIO.output(RESET_PIN, GPIO.HIGH)
sleep(1)

# Start Modules and Class
keyStroke.begin()
shm_serial.begin()
# accDAQfile = shm_daq_files('acc',3600*24)
accDAQfile = shm_daq_files('acc',60)
# Logger Setup
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
fh = logging.handlers.TimedRotatingFileHandler('/home/pi/log/gom_adxl362.log', when='d', interval=1, backupCount=90)
fh.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)
logger.addHandler(ch)


logger.info('--------------------------')
logger.info(' gom_adxl362_v06e started')
logger.info('--------------------------')

try:
    # LOOP
    while(True):

        #
        # SEND COMMANDS TO GOM
        #

        pitft.pushButton_Polling()

        keyStroke.polling()

        if pushButton_keyStroke_callback():
            break

        #
        # READ OUTPUTS FROM GOM
        #

        shm_serial.rx_polling()

        parse_rx_buff()

        #
        # STORE AND DISPLAY DATA
        #

        if accDAQfile.save(resampledData):
            # Toggle LED every n-writing
            n = 5
            writeCount += 1
            if writeCount > n:
                pitft.toggleStatusLED()
                writeCount = 0

        if state_guiOnOff[state[1]] == 1:
            pitft.display(resampledData)
            # HEART BEAT
            pitft.display_time()

        resampledData = []

        # sleep(0.05)

    # CLEAN UP
    keyStroke.end()
    pitft.end()
    accDAQfile.end()
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(RESET_PIN, GPIO.OUT)
    GPIO.output(RESET_PIN, GPIO.LOW)

except:
    logger.exception("Execption in the outter while loop")


logger.debug('------------------------')
logger.debug(' gom_adxl362_v06e ended ')
logger.debug('------------------------')
        

