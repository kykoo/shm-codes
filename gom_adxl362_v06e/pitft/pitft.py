#!/usr/bin/python3

#
# PITFT
#
# 1. Detect pushbutton pushes
#    - change state as required
#    - turn on/off gui mode as required
# 2. Time history plot
#
# 3. PSD plot
#


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


# BUTTON SETTING
pinUpButton = 22
pinDownButton = 17
pinResetButton = 27

debounce = datetime.timedelta(0, 0, 0, 200)
now = datetime.datetime.now()

Buttons = [{'Number': pinDownButton,
            'prevReading': 1,
            'detectedTime': now,
            'isPressed': False,
            'dstate': -1},
           {'Number': pinUpButton,
            'prevReading': 1,
            'detectedTime': now,
            'isPressed': False,
            'dstate': 1},
           {'Number': pinResetButton,
            'prevReading': 1,
            'detectedTime': now,
            'isPressed': False,
            'dstate': 1}]

lcd = ''

# PLOT CONFIGURATION
timeLengthPlot = 5  # of sec for time history plot
Fs = 100.0
dt = 1/Fs
npoints_PSD = 2**10  # of data points in PSD calculation
NFFT = 2**9

dataBuff = []       # data buffer 
xaxislimit = [0, 0] # of the next time history plot 
data4plot = []      # data corresponding to xaxislimit






def pushButton_Polling():
    
    global Buttons
    for button in Buttons:
        reading = GPIO.input(button['Number'])
        prevReading = button['prevReading']
        time_ = button['detectedTime']
        now = datetime.datetime.now()
        if(reading == 0 and prevReading == 1 and now - time_ > debounce):
            button['isPressed'] = True
            button['detectedTime'] = datetime.datetime.now()
            # print('Button {} Pressed'.format(button['Number']))
            # return button['Number']
        button['prevReading'] = reading
    return

def guiOnOff(x):
    global pygame, lcd
    
    if x == 1:
        pygame.display.init()
        lcd = pygame.display.set_mode((320,240))
        pygame.mouse.set_visible(False)
    elif x == 0:
        pygame.display.quit()
    return

def timehistory_Plot():
    global data4plot, Fs, dt
    global pygame, lcd
     
    dpi = 80
    figure(1, figsize=(320/dpi, 240/dpi))
    clf()
    # import pdb;pdb.set_trace()
    plot(data4plot[:,0], data4plot[:,1:])
    ylabel('ACC (g)')
    xlabel('Time (MM:SS)')
    gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    gca().set_xlim([data4plot[0,0],
                    data4plot[0,0] + datetime.timedelta(seconds=timeLengthPlot)])
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
    # print('timehistoryPlot executed')
    return

def display(resampledData):
    if not resampledData:
        return
    if storeData(resampledData):
        # print('true from storeData')
        timehistory_Plot()
    return

    
def storeData(resampledData):
    global dataBuff, xaxislimit, data4plot, timeLengthPlot

    data4plot_Ready = False
    
    for dataRow in resampledData:
        tk = dataRow[0]
        if xaxislimit[0] == 0:
            xaxislimit = [ceil(tk/timeLengthPlot)*timeLengthPlot,
                          ceil(tk/timeLengthPlot)*timeLengthPlot+timeLengthPlot]
        elif tk < xaxislimit[0]:
            pass
        elif  tk < xaxislimit[1]:
            dataBuff.append([datetime.datetime.fromtimestamp(tk)] + \
                             dataRow[1:])
        elif xaxislimit[1] <= tk:
            data4plot = array(dataBuff)
            dataBuff = []
            xaxislimit = [round(tk/timeLengthPlot)*timeLengthPlot,
                          round(tk/timeLengthPlot)*timeLengthPlot + timeLengthPlot]
            dataBuff.append([datetime.datetime.fromtimestamp(tk)] + \
                             dataRow[1:])
            data4plot_Ready = True

    return data4plot_Ready


def wind_plot(tk, data_k):
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
        gca().set_xlim([Time_plot[0], Time_plot[0] + datetime.timedelta(seconds=dt)])
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

   
def end():
    GPIO.cleanup()

def display_time():
    global pygame, lcd

    if lcd:
        nowStr = datetime.datetime.now().strftime('%Y %m-%d %H:%M:%S')
        color = (0,0,0)
        font_big = pygame.font.SysFont(None, 18)
        text_surface = font_big.render(nowStr, True, color,(255,255,255))
        rect = text_surface.get_rect(topleft=(3,3))
        lcd.blit(text_surface, rect)
        pygame.display.update()

# PYGAME
os.putenv('SDL_FBDEV', '/dev/fb1')
pygame.init()

# Push Button Setup
GPIO.setmode(GPIO.BCM)
for button in Buttons:
    GPIO.setup(button['Number'], GPIO.IN, pull_up_down=GPIO.PUD_UP)


if __name__ == '__main__':

    # TEST FOR ButtonStroke Detection
    if True:
        print('pitft started...')
        while True:
            # PROCESS COMMANDS FROM PUSH BUTTONS
            pushButton_Polling()
            
            for button in Buttons:
                if button['isPressed'] == True:
                    print('Button {} pressed.'.format(button['Number']))
                    button['isPressed'] = False
                    

    # TEST FOR Graphics mode
    if False:
        begin()
        lcd = pygame.display.set_mode((320, 240))
        lcd.fill((255,0,0))
        pygame.display.update()
        pygame.mouse.set_visible(False)
        lcd.fill((0,0,0))
        pygame.display.update()

        while True:
            print('')

    # Test for graphs
    if False:
    
        from numpy import *
        from matplotlib.pyplot import *

        Tend = 1
        Fs = 100.0
        dt = 1/Fs
        F = 1
        t = array([i*dt for i in range(int(round(Tend/dt)))])
        y = sin(2*pi*F*t)

        figure(1, figsize=(4,3))
        clf()
        plot(t,y)

        #set_size_inches(4, 3)
        gca().axes.get_xaxis().set_visible(False)
        savefig('sin-curve.png', dpi = 80)
        close(1)

        pygame.init()
        lcd = pygame.display.set_mode((320, 240))

        feed_surface = pygame.image.load("sin-curve.png")
        lcd.blit(feed_surface, (0,0))
        pygame.display.update()

        sleep(3)
