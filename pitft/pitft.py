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
Fs = 4.0
Time = []
Data = []
time0 = 0
time1 = 0
Time_plot = []
Data_plot = []
dt = 1/Fs

npoints_PSD = 2**10  # of data points in PSD calculation
NFFT = 2**9

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

def plotyy(tk, data_k):
    global Time_plot, Data_plot
    if storeData(tk, data_k):
        dpi = 80
        fig, ax1 = subplots(figsize=(320/dpi, 240/dpi))
        ax2 = ax1.twinx()
        
        ax1.plot(Time_plot, Data_plot[:,0],color='b')
        ax1.set_ylabel('Wind Speed (m/s)')
        ax1.set_xlabel('Time (MM:SS)')
        ax1.yaxis.label.set_color('blue')
        ax1.set_ylim([0, 20])

        ax2.plot(Time_plot, Data_plot[:, 1],color='r')
        ax2.yaxis.label.set_color('red')
        ax2.set_ylabel('Wind Direction (degree)')
        ax2.set_ylim([0, 540])
        gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        gca().set_xlim([Time_plot[0], Time_plot[-1] + datetime.timedelta(seconds=dt)])
        # gca().yaxis.set_label_coords(-0.10, 0.5)
        subplots_adjust(left=0.20, bottom=0.15, right=0.85, top=0.95)
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

def storeData(t_ks, data_ks):
    global time0, time1, Time, Data, Time_plot, Data_plot
    for i in range(len(t_ks)):
        tk = t_ks[i]
        data_k = data_ks[i]
        if time0 == 0:
            time0 = ceil(tk/timeLengthPlot)*4
            time1 = time0 + timeLengthPlot
        elif tk < time0:
            pass
        elif  tk < time1:
            Time.append(datetime.datetime.fromtimestamp(tk))
            Data.append(data_k)
        elif time1 <= tk:
            Time_plot = array(list(Time))
            Data_plot = array(list(Data))
            Time = []
            Data = []
            Time.append(datetime.datetime.fromtimestamp(tk))
            Data.append(data_k)
            time0 = time1
            time1 = round(time1/timeLengthPlot+1)*timeLengthPlot
            return True
        return False
   
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
