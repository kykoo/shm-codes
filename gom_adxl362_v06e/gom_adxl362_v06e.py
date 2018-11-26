#!/usr/bin/python3
#
#  ADXL INTERFACE APPLICATION
#
#  - Time Sampling
#  - Resampling
#
#  written by k.y.koo@exeter.ac.uk
#
#
# ADXL362: 50 Hz Fs
#          LPF@12.5Hz
#          Ultralow noise mode
#
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
#import resample


import RPi.GPIO as GPIO
import os
import socket
import datetime
from numpy import *
from matplotlib.pyplot import *
import matplotlib.dates as mdates
from scipy import signal
import array as array_


Fs = 100.0

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
# 0 = UNKNOWN
# 1 = OUTPUTTING CC AND TIME OF PPS
# 2 = SILENCE
# 3 = DAQ
# 4 = TIME HISTORY PLOT
# 5 = PSD PLOT

state = [1, 1]
state_guiOnOff = [0, 0, 0, 0, 1, 1]
state_max = len(state_guiOnOff) - 1
bootSequence = True
logging = False
arduinoCMD = '' # Command to be sent to Arduino via UART

ppsCC_Time = {'t':None, 'CC':None, 'Fclk':None}
daqCC_Values = {'t':None, 'CC':None, 'valXYZ':None}
tk = []
resampledData = []
nPPS = 0

def pushButton_keyStroke_callback():

    # pushButton_callback
    global  state, pitft, keyStroke, arduinoCMD

    # Down button
    if pitft.Buttons[0]['isPressed'] == True and state[1] > 1:
        state[0] = state[1]
        state[1] = state[1] - 1
        pitft.Buttons[0]['isPressed'] = False
        
        # formatting screen output
        if state[1] == 2:
            print('')
        if state[1] == 3:
            print('')
            print('')

        # print('state = {}'.format(state))
        arduinoCMD = 'd'

    # Up button
    if pitft.Buttons[1]['isPressed'] == True and state[1] < state_max:
        state[0] = state[1]
        state[1] = state[1] + 1
        pitft.Buttons[1]['isPressed'] = False
        # print('state = {}'.format(state))
        arduinoCMD = 'u'

        # formatting screen output
        if state[1] == 4:
            print('')
            
    # keyStroke_callback
    if keyStroke.keyNumber == 117: # 'u'
        arduinoCMD = 'u'        
        # print('u pressed')
    if keyStroke.keyNumber == 100: # 'd'
        arduinoCMD = 'd'
        # print('d pressed')
    if keyStroke.keyNumber == 113: # 'q'
        keyStroke.end()
        GPIO.cleanup()
        # file.close()
        sys.exit()
    keyStroke.keyNumber = 0

    # ON/OFF GUI
    if state_guiOnOff[state[1]] == 0:
        # pitft.guiOnOff(state_guiOnOff[state[1]])
        pitft.guiOnOff(0)

    # SENDING arduinoCMD
    if arduinoCMD:
        shm_serial.ser.write(arduinoCMD.encode())
    arduinoCMD = ''

    return

def parse_rx_buff():
    global shm_serial, bootSequence, pitft
    global ppsCC_Time, daqCC_Values, tk, resampledData, nPPS

    linefeed = False # flag to show if a linefeed is needed or not
    while True:
        idx = shm_serial.rx_buff.find('\r\n')

        # In case no CR/NL found, wait till new data comes
        if idx == -1:
            break

        # In case the data string is empty, skip to next data string after CR/NL
        if idx == 0:
            shm_serial.rx_buff = shm_serial.rx_buff[(idx+2):]
            continue
        
        # MESSAGES
        if shm_serial.rx_buff[0] == '0':
            if linefeed:
                sys.stdout.write('\n')
                linefeed = False 
            sys.stdout.write(shm_serial.rx_buff[:idx] + '\n')

            # if logging:
            #     log(shm_serial.rx_buff[:idx])
            #  
            # AUTO-STARTUP
            if bootSequence is True and shm_serial.rx_buff[0:8] == '0,state=':
                state_ = int(shm_serial.rx_buff[8])
                if state_ == 2:
                    pitft.Buttons[1]['isPressed'] = True
                if state_ == 3:
                    bootSequence = False  # FINISH BOOT SEQEUNCE

        # UPDATE ppsCC_Time
        elif shm_serial.rx_buff[0] == '1':
            rx_buff_split = shm_serial.rx_buff[:idx].split(',')
            sys.stdout.write(shm_serial.rx_buff[:idx] + '\n')

            # if logging:
            #     log(shm_serial.rx_buff[:idx])
              
            t = float(rx_buff_split[3])
            CC = float(rx_buff_split[1])*2**16 + float(rx_buff_split[2])

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


        # TIMESTAMPING
        elif shm_serial.rx_buff[0] == '2':
            rx_buff_split = shm_serial.rx_buff[:idx].split(',')
            # sys.stdout.write(shm_serial.rx_buff[:idx] + '\n')

            # if logging:
            #     log(shm_serial.rx_buff[:idx])
            #  
            try:
                CC = float(rx_buff_split[1])*2**16 + float(rx_buff_split[2])
                valXYZ = [float(rx_buff_split[3]), float(rx_buff_split[4]), float(rx_buff_split[5])]
                t = ppsCC_Time['t'] + (CC - ppsCC_Time['CC']) / ppsCC_Time['Fclk'] * 1.0
            except:
                shm_serial.rx_buff = shm_serial.rx_buff[(idx+2):]
                continue
             
            # STORE INITIAL MEASUREMENT
            if not daqCC_Values['CC']:
                # sys.stdout.write('first daq data' + '\n')
                daqCC_Values['CC'] = CC
                daqCC_Values['valXYZ'] = valXYZ
                daqCC_Values['t'] = t
                tk = float(ceil(daqCC_Values['t']*Fs))/Fs
             
            # Resampling
            elif tk <= t:
                # sys.stdout.write('next daq data' + '\n')
                # import pdb;pdb.set_trace()
                while tk <= t:
                    valXYZ_intp = [0, 0, 0]
                    for j in range(3):
                        valXYZ_intp[j] = interp(tk, [daqCC_Values['t'], t],
                                                [daqCC_Values['valXYZ'][j], valXYZ[j]])
                    outString = '{:.3f}, {:.3f}, {:.3f}, {:.3f}'.format(
                        tk, valXYZ_intp[0], valXYZ_intp[1], valXYZ_intp[2])
                    if round(tk*10)/10 == tk:
                        if state[1] == 3:
                            print(outString, end='\r')
                            linefeed = True 
                        else:
                            print(outString)


                    # store resampled data
                    resampledData.append([tk, valXYZ_intp[0], valXYZ_intp[1], valXYZ_intp[2]])
                    # print('len(resampledData)={}'.format(len(resampledData)))
                    
                    #sys.stdout.write('output daq data' + '\n')
                    tk = round(tk * Fs + 1.0) / Fs
                # Replacing daqCC_Values with new values
                daqCC_Values['CC'] = CC
                daqCC_Values['valXYZ'] = valXYZ
                daqCC_Values['t'] = t
             
            # REPLACING daqCC_Values with new values
            elif tk > t:
                # print('replacing daqCC_Values with new values')
                daqCC_Values['CC'] = CC
                daqCC_Values['valXYZ'] = valXYZ
                daqCC_Values['t'] = t

        # UPDATE ppsCC_Time based on CC only
        elif shm_serial.rx_buff[0] == '3': # CC without PPS-time
            rx_buff_split = shm_serial.rx_buff[:idx].split(',')
            outString = '\t('+shm_serial.rx_buff[:idx] + ')\r'
            sys.stdout.write(outString.expandtabs(37))

            #  
            # if logging:
            #     log(shm_serial.rx_buff[:idx])

            CC = float(rx_buff_split[1])*2**16 + float(rx_buff_split[2])
            dT = float(round((CC - ppsCC_Time['CC']) / ppsCC_Time['Fclk']))
            ppsCC_Time['CC'] = CC
            ppsCC_Time['t'] = ppsCC_Time['t'] + dT

        # UNRECOGNISED DATA
        else:
            sys.stdout.write(shm_serial.rx_buff[:idx] + '\n')
            # print('Parsing failed: unrecognised data string header = {}, data string[2:]={} '.format(ord(shm_serial.rx_buff[0]),shm_serial.rx_buff[2:]))

            # if logging:
            #     log(shm_serial.rx_buff[:idx])

            # shm_serial.rx_buff = shm_serial.rx_buff[(idx+2):]

        # MOVE TO THE NEXT DATA STRING
        shm_serial.rx_buff = shm_serial.rx_buff[(idx+2):]

    return



# RESET GOM
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(16, GPIO.OUT)
GPIO.output(16, GPIO.LOW)
sleep(1)
GPIO.output(16, GPIO.HIGH)
sleep(1)

# Start Modules and Class
keyStroke.begin()
shm_serial.begin()
accDAQfile = shm_daq_files('acc',60)

print('gom_adxl362_v06e started.')

# LOOP
while(True):

    #
    # SEND COMMANDS TO GOM
    #
    pitft.pushButton_Polling()

    keyStroke.polling()

    pushButton_keyStroke_callback()

    #
    # READ OUTPUTS FROM GOM
    #
    shm_serial.rx_polling()

    parse_rx_buff()

    #
    # STORE AND DISPLAY DATA
    #
    accDAQfile.save(resampledData)
    
    if state_guiOnOff[state[1]] == 1:
        pitft.display(resampledData)
        # HEART BEAT
        pitft.display_time()

    resampledData = []

    # sleep(0.05)



