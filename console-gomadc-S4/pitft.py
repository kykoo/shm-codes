#!/usr/bin/python3


import time
from time import sleep
import serial
import RPi.GPIO as GPIO
import sys
import os
import socket
import datetime
import datetime
from numpy import *
from matplotlib.pyplot import *
import pygame
import os
import matplotlib.dates as mdates
from scipy import signal
import array as array_


# CONFIGURATION
timeLengthPlot = 4  # of sec for time history plot
Fs = 300.0
daq_data = []  # [timestamp, data1, data2, ...]

npts_psd = 2**10 # of data points in PSD calculation
NFFT = 2**9

# INTERNAL VARIALBS
timeWindow = [0, 0]   # left end of the plotting time-window
daq_data_4plot = []    # [timestamp, data1, data2, ...]

dt = 1/Fs
nAverageOfPSD = 0
Pxx = zeros((int(NFFT/2) + 1, 4))    # Pxx, Pyy, Pzz


# BUTTON SETTING
pinUpButton = 22
pinDownButton = 17
Buttons = ''
debounce = datetime.timedelta(0, 0, 0, 200)
now = datetime.datetime.now()


def begin():
    global Buttons
    Buttons = [{'Number': pinDownButton,
                'readingPrev': 1,
                'timeDetected': now,
                'isPressed': False,
                'cmd': 'd',
                'dstate': -1},
               {'Number': pinUpButton,
                'readingPrev': 1,
                'timeDetected': now,
                'isPressed': False,
                'cmd': 'u',
                'dstate': 1}]

def getButtonStroke():
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
            # print('Button {} Pressed'.format(button['Number']))
            return button['Number']
        button['readingPrev'] = reading
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


# def plotyy(tk, data_k):
#     global time4plot, data4plot
#     if storeData(tk, data_k):
#         dpi = 80
#         fig, ax1 = subplots(figsize=(320/dpi, 240/dpi))
#         ax2 = ax1.twinx()
#         
#         ax1.plot(time4plot, data4plot[:,0],color='b')
#         ax1.set_ylabel('Wind Speed (m/s)')
#         ax1.set_xlabel('Time (MM:SS)')
#         ax1.yaxis.label.set_color('blue')
#         ax1.set_ylim([0, 20])
#  
#         ax2.plot(time4plot, data4plot[:, 1],color='r')
#         ax2.yaxis.label.set_color('red')
#         ax2.set_ylabel('Wind Direction (degree)')
#         ax2.set_ylim([0, 540])
#         gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
#         gca().set_xlim([time4plot[0], time4plot[-1] + datetime.timedelta(seconds=dt)])
#         # gca().yaxis.set_label_coords(-0.10, 0.5)
#         subplots_adjust(left=0.20, bottom=0.15, right=0.85, top=0.95)
#         savefig('.thp.png', dpi=80)
#         close(1)
#  
#         pygame.display.init()
#         pygame.mouse.set_visible(False)
#         lcd = pygame.display.set_mode((320, 240))
#         feed_surface = pygame.image.load('.thp.png')
#         lcd.blit(feed_surface, (0, 0))
#         pygame.display.update()
#         sleep(0.05)
#     return

def plot_vs1002(data):
    global daq_data_4plot
    if storeData(data):
        dpi = 80
        figure(1, figsize=(320/dpi, 240/dpi))
        clf()
        time = []
        for t in daq_data_4plot[:,0]:
            time.append(datetime.datetime.fromtimestamp(t))
        # print('------size {}'.format(len(time)))
        # import pdb; pdb.set_trace()
        plot(time, daq_data_4plot[:,1:])
        ylabel('ACC (g)')
        xlabel('Time (MM:SS)')
        gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        gca().set_xlim([time[0], time[-1] + datetime.timedelta(seconds=dt)])
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


def storeData(data):
    global timeWindow, daq_data, daq_data_4plot
    for datum in data:
        t = datum[0]
        if timeWindow[0] == 0:
            timeWindow[0] = round(t/timeLengthPlot + 1)*4
            timeWindow[1] = timeWindow[0] + timeLengthPlot
            # print('Timewindow set: {} {}'.format(timeWindow[0], timeWindow[1]))
        elif t < timeWindow[0]:
            # print('t < timeWindow[0]: data skipped')
            pass
    
        elif  t < timeWindow[1]:
            # print(' t < timeWindow[1]: data stored')
            daq_data.append(datum)
        elif timeWindow[1] <= t:
            # print('Generting plot: the size={}'.format(
            #    len(daq_data)))
            daq_data_4plot = array(list(daq_data))
            daq_data = []
            daq_data.append(datum)
            timeWindow = [timeWindow[1], timeWindow[1]+timeLengthPlot]
            return True
    return False

def storeData4psd(data):
    global daq_data, daq_data_4plot
    for datum in data:
        # import pdb; pdb.set_trace()
        daq_data.append(datum)
        #print('len(daq_data)={}, npts_psd = {}'.format(len(daq_data), npts_psd))
        if len(daq_data) >= npts_psd:
            daq_data_4plot = array(list(daq_data))
            daq_data = []
            return True
    return False

def plot_vs1002_psd(data):
    global daq_data, daq_data_4plot, nAverageOfPSD, NFFT, Pxx

    if storeData4psd(data):
        nAverageOfPSD += 1
        dpi = 80
        figure(1, figsize=(320/dpi, 240/dpi))
        clf()
        for i in range(1, daq_data_4plot.shape[1]):
            f, Pxx_ = signal.welch(signal.detrend(daq_data_4plot[:, i]), int(Fs), nperseg=NFFT)
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

   
def end():
    GPIO.cleanup()

def guiOn():
    pygame.init()
    return

def guiOff():
    pygame.display.quit()
    return


# PYGAME
os.putenv('SDL_FBDEV', '/dev/fb1')
pygame.init()

GPIO.setmode(GPIO.BCM)
GPIO.setup(pinDownButton, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(pinUpButton, GPIO.IN, pull_up_down=GPIO.PUD_UP)

if __name__ == '__main__':
    begin()
    while True:
        # PROCESS COMMANDS FROM PUSH BUTTONS
        n = getButtonStroke()
        if n:
            print(n, ' Pressed')
