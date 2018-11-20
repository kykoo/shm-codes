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
state_guiOnOff = [0, 1]
state = [0, 0]
state_max = len(state_guiOnOff)-1

def pushbutton_callback():
    global  state, state_max

    # print('pushbutton_callback')
    n = getButtonStroke()
    # print(n, state)
    if n:
        if n == pinUpButton and state[1] < state_max:
            state[0] = state[1]
            state[1] = state[1] + 1
        elif n == pinDownButton and state[1] > 0:
            state[0] = state[1]
            state[1] = state[1] - 1 
        print('state = {}'.format(state))
        # ON/OFF GUI
        guiOnOff(state_guiOnOff[state[1]])
        
    return

def begin():
    global Buttons, state_max
    
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
    state_max = len(state_guiOnOff) - 1
    # print("pitft.begin() done.")

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

def guiOnOff(x):
    if x == 1:
        pygame.display.init()
        lcd = pygame.display.set_mode((320,240))
        pygame.mouse.set_visible(False)
    elif x == 0:
        pygame.display.quit()
    return

def display_time():
    if state_guiOnOff[state[1]] == 1:
        lcd = pygame.display.set_mode((320, 240))
        pygame.mouse.set_visible(False)

        feed_surface = pygame.image.load("sin-curve.png").convert()
        #lcd.blit(feed_surface, (0,0))
        
        nowStr = datetime.datetime.now().strftime('%Y %m-%d %H:%M:%S')
        color = (0,0,0)
        font_big = pygame.font.SysFont(None, 18)
        text_surface = font_big.render(nowStr, True, color)
        rect = text_surface.get_rect(topleft=(3,3))
        rect2 = text_surface.get_rect(topleft=(160,120))
        lcd.blit(feed_surface,(0,0))
        lcd.blit(text_surface, rect)

        pygame.display.update()

# PYGAME
os.putenv('SDL_FBDEV', '/dev/fb1')
pygame.init()

GPIO.setmode(GPIO.BCM)
GPIO.setup(pinDownButton, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(pinUpButton, GPIO.IN, pull_up_down=GPIO.PUD_UP)



if __name__ == '__main__':

    # TEST FOR ButtonStroke Detection
    if False:
        begin()
        while True:
            # PROCESS COMMANDS FROM PUSH BUTTONS
            n = getButtonStroke()
            if n:
                print(n, ' Pressed')

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
    if True:
    
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
        pygame.
