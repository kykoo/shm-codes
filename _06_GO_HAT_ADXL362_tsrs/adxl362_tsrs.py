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
import serial
import RPi.GPIO as GPIO
import sys
sys.path.append('/home/pi/codes/ds18b20')
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
# import ds18b20


# CONFIGURATION
nsec_timehistoryPlot = 4  # of sec for time history plot
npoints_PSD = 2**10  # of data points in PSD calculation
NFFT = 2**9
# Fs = 100.0
Fs = 100.0

#
# STATE OF THE MACHINE
#
# SOM is identified by messages from GOM
#
# 0 = UNKNOWN
# 1 = OUTPUTTING CC AND TIME OF PPS
# 2 = SILENCE
# 3 = DAQ
# 4 = TIME HISTORY PLOT
# 5 = PSD PLOT
state = 0
bootSequence = True
iPPS = 0

# TABLES FOR CC-Time for PPS, CC-XYZ for DAQ Point
ppsCC_Time = {'t1': [], 'CC1': [], 'Fclk': []}
daqCC_XYZ = {'CCi': [], 'valXYZ': [], 'ti': []}
tk = []
dt = 1/Fs
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
# PYGAME
os.putenv('SDL_FBDEV', '/dev/fb1')
pygame.init()

def log(line):
    import time
    
    global hostName, logfilePath, logfileName, logfile

    time_now = time.mktime(datetime.datetime.now().timetuple())
    time_ = floor(time_now / (3600 * 24)) * 3600 * 24
    logfileName_ = hostName + '-acc-' + \
                datetime.datetime.fromtimestamp(time_).strftime("%Y%m%d") + ".log"
    if len(logfileName) == 0:
        logfile = open(logfilePath + logfileName_, "a")
        logfileName = logfileName_
        logfile.write(line + '\n')
    elif logfileName == logfileName_:
        logfile.write(line + '\n')
    else:
        logfile.close()
        logfile = open(logfilePath + logfileName_, "a")
        logfileName = logfileName_
        logfile.write(line + '\n')
    return    


def save(time, data):
    
    global hostName, path, fileName, file

    time_ = floor(time / (3600 * 24)) * 3600 * 24
    # time_ = floor(time / (3600 * 1)) * 3600 * 1
    fileName_ = hostName + '-acc-' + \
                datetime.datetime.fromtimestamp(time_).strftime("%Y%m%d")
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


def isKeyStrokeAvailable():
    import select
    return select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], [])


def PSD_Plot():
    global dataPSD, nAverageOfPSD, NFFT, Pxx, Fs

    nAverageOfPSD += 1
    dpi = 80
    figure(1, figsize=(320/dpi, 240/dpi))
    clf()
    for i in range(3):
        f, Pxx_ = signal.welch(signal.detrend(data4PSD[:, i]), int(Fs), nperseg=NFFT)
        Pxx[:, i] = (nAverageOfPSD - 1) / nAverageOfPSD * Pxx[:, i] + Pxx_ / (nAverageOfPSD)
        semilogy(f, Pxx[:, i])
    xlabel('Frequency (Hz)')
    ylabel('PSD (g^2/Hz)')
    Fn = Fs/2
    gca().set_xlim([0, Fn])
    gca().yaxis.set_label_coords(-0.10, 0.5)
    subplots_adjust(left=0.13, bottom=0.15, right=0.95, top=0.95)
    savefig('.psd.png', dpi=80)
    close(1)

    pygame.display.init()
    pygame.mouse.set_visible(False)
    lcd = pygame.display.set_mode((320, 240))
    feed_surface = pygame.image.load('.psd.png')
    lcd.blit(feed_surface, (0, 0))
    pygame.display.update()
    sleep(0.05)
    return

    
def timehistoryPlot():
    global data4THP, Fs, dt

    dpi = 80
    figure(1, figsize=(320/dpi, 240/dpi))
    clf()
    plot(time4THP, data4THP)
    ylabel('ACC (g)')
    xlabel('Time (MM:SS)')
    gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    gca().set_xlim([time4THP[0], time4THP[-1] + datetime.timedelta(seconds=dt)])
    gca().yaxis.set_label_coords(-0.10, 0.5)
    subplots_adjust(left=0.13, bottom=0.15, right=0.95, top=0.95)
    savefig('.thp.png', dpi=80)
    close(1)

    pygame.display.init()
    pygame.mouse.set_visible(False)
    lcd = pygame.display.set_mode((320, 240))
    feed_surface = pygame.image.load('.thp.png')
    lcd.blit(feed_surface, (0, 0))
    pygame.display.update()
    sleep(0.05)
    return

def parse(rx_buff):
    # from numpy import *
    global ppsCC_Time
    global daqCC_XYZ
    global dt
    global Fs
    global tk
    global dispFreq
    global dispCount
    global time4THP, data4THP, data4PSD, curDataTHP, curDataPSD, waitUntilStoreTH, waitUntilStorePSD
    global npoints_PSD
    global bootSequence, iPPS, state
    global nsec_timehistoryPlot

    while True:
        idx = rx_buff.find('\r\n')
        if idx == -1:
            break
        # PRINT OUT MESSAGE
        if rx_buff[0] == '0':
            sys.stdout.write(rx_buff[:idx] + '\n')
            log(rx_buff[:idx])
            # AUTO-STARTUP
            if bootSequence is True and rx_buff[0:8] == '0,state=':
                state = int(rx_buff[8])
                if state == 2:
                    Buttons[1]['isPressed'] = True
                if state == 3:
                    # pass
                    Buttons[1]['isPressed'] = True
                if state == 4:
                    bootSequence = False  # FINISH BOOT SEQEUNCE                    
            rx_buff = rx_buff[(idx+2):]
        # UPDATE ppsCC_Time
        elif rx_buff[0] == '1':
            rx_buff_split = rx_buff[:idx].split(',')
            sys.stdout.write(rx_buff[:idx] + '\n')
            log(rx_buff[:idx])
            t1_ = float(rx_buff_split[3])
            CC1_ = float(rx_buff_split[1])*2**16 + float(rx_buff_split[2])
            # print(t1_)
            if not ppsCC_Time['t1']:
                ppsCC_Time['t1'] = t1_
                ppsCC_Time['CC1'] = CC1_
            else:
                ppsCC_Time['Fclk'] = (CC1_ -  ppsCC_Time['CC1'])/(t1_ - ppsCC_Time['t1'])
                ppsCC_Time['t1'] = t1_
                ppsCC_Time['CC1'] = CC1_
            rx_buff = rx_buff[(idx+2):]
            # AUTO-STARTUP
            if bootSequence is True and state == 0:
                iPPS += 1
                if iPPS > 2:
                    Buttons[1]['isPressed'] = True
        # TIMESTAMPING
        elif rx_buff[0] == '2':
            rx_buff_split = rx_buff[:idx].split(',')
            # sys.stdout.write(rx_buff[:idx] + '\n')
            log(rx_buff[:idx])
            try:
                CCi_ = float(rx_buff_split[1])*2**16 + float(rx_buff_split[2])
                valXYZ_ = [float(rx_buff_split[3]), float(rx_buff_split[4]), float(rx_buff_split[5])]
                ti_ = ppsCC_Time['t1'] + (CCi_ - ppsCC_Time['CC1']) / ppsCC_Time['Fclk'] * 1.0
            except:
                rx_buff = rx_buff[(idx+2):]
                continue
            # STORE INITIAL MEASUREMENT
            if not daqCC_XYZ['CCi']:
                # sys.stdout.write('first daq data' + '\n')
                daqCC_XYZ['CCi'] = CCi_
                daqCC_XYZ['valXYZ'] = valXYZ_
                daqCC_XYZ['ti'] = ti_
                tk = float(ceil(daqCC_XYZ['ti']*Fs))/Fs
            # TIMESTAMPING
            elif tk <= ti_:
                # sys.stdout.write('next daq data' + '\n')
                # import pdb;pdb.set_trace()
                while tk <= ti_:
                    valXYZ_intp = [0, 0, 0]
                    for j in range(3):
                        valXYZ_intp[j] = interp(tk, [daqCC_XYZ['ti'], ti_],
                                                [daqCC_XYZ['valXYZ'][j], valXYZ_[j]])
                    outString = '{:.3f}, {:.6f}, {:.6f}, {:.6f}'.format(
                        tk, valXYZ_intp[0], valXYZ_intp[1], valXYZ_intp[2])
                    if dispCount == dispFreq:
                        dispCount = 1
                        # sys.stdout.write(outString + '\n')
                        print(outString, end='\r')
                    else:
                        dispCount += 1
                    # SAVE DATA TO DISK
                    save(tk, [tk, valXYZ_intp[0], valXYZ_intp[1], valXYZ_intp[2]])
                    # PROCESS DATA FOR TIME HISTORY PLOT
                    if waitUntilStoreTH == True:
                        # print(tk, floor(tk / nsec_timehistoryPlot) * nsec_timehistoryPlot)
                        if tk == floor(tk / nsec_timehistoryPlot) * nsec_timehistoryPlot:
                            waitUntilStoreTH = False
                    if waitUntilStoreTH == False:
                        time4THP[curDataTHP] = datetime.datetime.fromtimestamp(tk)
                        data4THP[curDataTHP, :] = [valXYZ_intp[0], valXYZ_intp[1], valXYZ_intp[2]]
                        curDataTHP += 1
                        if curDataTHP == npoints_THP:
                            if state == 4:
                                timehistoryPlot()
                            curDataTHP = 0
                    # PROCESS DATA FOR PSD PLOT
                        # time4PSD[curDataPSD] = datetime.datetime.fromtimestamp(t_)
                        data4PSD[curDataPSD, :] = [valXYZ_intp[0], valXYZ_intp[1], valXYZ_intp[2]]
                        curDataPSD += 1
                        if curDataPSD == npoints_PSD:
                            if state == 5:
                                PSD_Plot()
                            curDataPSD = 0
                    #sys.stdout.write('output daq data' + '\n')
                    tk = round(tk * Fs + 1.0) / Fs
                # Replacing daqCC_XYZ with new values
                daqCC_XYZ['CCi'] = CCi_
                daqCC_XYZ['valXYZ'] = valXYZ_
                daqCC_XYZ['ti'] = ti_
            # REPLACING daqCC_XYZ with new values
            elif tk > ti_:
                # print('replacing daqCC_XYZ with new values')
                daqCC_XYZ['CCi'] = CCi_
                daqCC_XYZ['valXYZ'] = valXYZ_
                daqCC_XYZ['ti'] = ti_
            rx_buff = rx_buff[(idx+2):]
        # UPDATE ppsCC_Time based on CC only
        elif rx_buff[0] == '3': # CC without PPS-time
            rx_buff_split = rx_buff[:idx].split(',')
            # sys.stdout.write(rx_buff[:idx] + '\n')
            log(rx_buff[:idx])
            CC1_ = float(rx_buff_split[1])*2**16 + float(rx_buff_split[2])
            dT = float(round((CC1_ - ppsCC_Time['CC1']) / ppsCC_Time['Fclk']))
            ppsCC_Time['CC1'] = CC1_
            ppsCC_Time['t1'] = ppsCC_Time['t1'] + dT
            # print('')
            # print(ppsCC_Time['t1'])
            rx_buff = rx_buff[(idx+2):]
        # UNRECOGNISED DATA
        else:
            print('unrecognised data')
            sys.stdout.write(rx_buff)
            log(rx_buff[:idx])
            rx_buff = rx_buff[(idx+2):]
    return rx_buff    


# GPIO SETTING
GPIO.setmode(GPIO.BCM)
GPIO.setup(22, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(17, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# SERIAL SETTING
ser = serial.Serial(
    port='/dev/serial0',
    baudrate=115200,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS
)
if(ser.isOpen() is False):
    sys.exit('Serial is not open!')
# RX BUFFER
rx_buff = ''


# FILE SETTING
hostName = socket.gethostname()
now = datetime.datetime.now()
path = '/home/pi/data/'
logfilePath = '/home/pi/log/'
fileName = ''
file = ''
logfileName = ''
logfile = ''
# create directory if not exists
directories = [path, logfilePath]
for directory in directories:
    if not os.path.exists(directory):
        os.makedirs(directory)

# BUTTON SETTING
Buttons = [{'Number': 17,
            'readingPrev': 1,
            'timeDetected': now,
            'isPressed': False,
            'cmd': 'd',
            'dstate': -1},
           {'Number': 22,
            'readingPrev': 1,
            'timeDetected': now,
            'isPressed': False,
            'cmd': 'u',
            'dstate': 1}]
debounce = datetime.timedelta(0, 0, 0, 200)

# print(len(Buttons))
# print(Buttons[0]['Number'])
# print(GPIO.input(17))
# sys.exit()

# RESET THE NODE
GPIO.setup(16, GPIO.OUT)
GPIO.output(16, GPIO.LOW)
sleep(1)
GPIO.output(16, GPIO.HIGH)
sleep(1)

# STORE TERMINAL SETTING
old_settings = termios.tcgetattr(sys.stdin)

# FLUSH INPUT BUFFER
while ser.inWaiting() > 0:
    ser.read(1)
# ser.reset_input_buffer() <- This simple approach doesn't work. Why?

# # DS18B20
# ds18b20.set_Ts(60)  # measurement period 60 seconds

cmd = ''
# LOOP
while(True):
    # PROCESS COMMANDS FROM KEYBOARD
    if isKeyStrokeAvailable():
        c = sys.stdin.read(1)
        if c == '\x1b':	    # x1b is ESC
            break
        if c == '\x75':	    # (u)p
            Buttons[1]['isPressed'] = True
        if c == '\x64':	    # (d)own
            Buttons[0]['isPressed'] = True
        if c == '\x6e':     # (n)ew file
            file.close()
            now = datetime.datetime.now()
            fileName = hostName + '-acc-' + now.strftime("%Y%m%d-%H%M%S")
            + ".txt"
            file = open(path + fileName, "w")
            print("New file created: {}".format(fileName))

    # PROCESS COMMANDS FROM PUSH BUTTONS
    for ibutton in range(0, len(Buttons)):
        button = Buttons[ibutton]
        reading = GPIO.input(button['Number'])
        readingPrev = button['readingPrev']
        time_ = button['timeDetected']
        now = datetime.datetime.now()
        if(reading == 0 and readingPrev == 1 and now - time_ > debounce):
            button['isPressed'] = True
            button['timeDetected'] = datetime.datetime.now()
            # print('Button {} Pressed'.format(button['Number']))
        button['readingPrev'] = reading

    # HAND OVER COMMAND TO GOM OVER SERIAL 
    for ibutton in range(0, len(Buttons)):
        if Buttons[ibutton]['isPressed'] is True:
            cmd = Buttons[ibutton]['cmd']
            dstate = Buttons[ibutton]['dstate']
            ser.write(cmd.encode())
            # print('Command sent')
            Buttons[ibutton]['isPressed'] = False

            if state == 4:
                if dstate == -1:
                    pygame.display.quit()
            state += dstate
            if state > 5:
                state = 5
            if state < 1:
                state = 1

    # PROCESS OUTPUTS FROM GOM 
    # while ser.inWaiting() > 0:
    while ser.in_waiting > 0:
        try:
            rx_buff += ser.read(1).decode('UTF-8')
        except:
            sys.stdout.write('')
    if(len(rx_buff) > 0):
        rx_buff = parse(rx_buff)

    # ds18b20.measure()
    sleep(0.05)


termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
GPIO.cleanup()
file.close()
