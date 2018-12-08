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
import multiprocessing
import logging


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
lock_data4plot = multiprocessing.Lock()

# STATUS LED
statusLED = 0
statusLED_PIN = 21
count_toggleStatusLED = 0

plotUpdated = multiprocessing.Value('i', 0)
lock_plotUpdated = multiprocessing.Lock()
nAverageOfPSD = multiprocessing.Value('i', 0)
Pxx = multiprocessing.Array('d', [0.0]* (3*(int(NFFT/2)+1)))

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

def genTimeHistoryPlot(
        data4plot, lock_data4plot, plotUpdated, lock_plotUpdated):
    #global data4plot, Fs, dt
    #global pygame, lcd
    import datetime
    from matplotlib.pyplot import plot, ylabel, xlabel, gca, subplots_adjust, savefig, close
    import matplotlib.dates as mdates

    dpi = 80
    figure(1, figsize=(320/dpi, 240/dpi))
    clf()
     
    # import pdb;pdb.set_trace()
     
    lock_data4plot.acquire()
    plot(data4plot[:,0], data4plot[:,1:])
    lock_data4plot.release()
     
    ylabel('ACC (g)')
    xlabel('Time (MM:SS)')
    gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    gca().set_xlim([data4plot[0,0],
                    data4plot[0,0] + datetime.timedelta(seconds=timeLengthPlot)])
    gca().yaxis.set_label_coords(-0.10, 0.5)
    subplots_adjust(left=0.13, bottom=0.15, right=0.95, top=0.95)
    savefig('.thp.png', dpi=80)
    close(1)
    
    lock_plotUpdated.acquire()
    plotUpdated.value = 1
    lock_plotUpdated.release()
   
    # print('timehistoryPlot executed')

    return

def displayGraph(graphType, resampledData):
    # graphType = 0: TimeHistory Plot
    #             1: PSD plot
    global lock_data4plot, pygame, lcd, plotUpdated, lock_plotUpdated
    global nAverageOfPSD, Pxx

    logger  = logging.getLogger(__name__)
    
    if not resampledData:
        return
    
    if storeData(resampledData):
        # MULTIPROCESSING 
        plotUpdated.value = 0

        if graphType == 0:  # time history plot 
            p = multiprocessing.Process(target=genTimeHistoryPlot,args=(
                data4plot, lock_data4plot, plotUpdated, lock_plotUpdated,))
            p.start()
        elif graphType == 1: # PSD plot 
            # genPSD_Plot
            p = multiprocessing.Process(target=genPSD_Plot,args=(
                data4plot, lock_data4plot, plotUpdated, lock_plotUpdated,
                Fs, NFFT, nAverageOfPSD, Pxx))
            p.start()

    # DRAW PLOT IF UPDATED
    lock_plotUpdated.acquire()
    if plotUpdated.value == 1:
        feed_surface = pygame.image.load('.thp.png')
        lcd.blit(feed_surface, (0, 0))
        pygame.display.update()
        plotUpdated.value = 0
    lock_plotUpdated.release()
    
    return

def genPSD_Plot(data4plot, lock_data4plot, plotUpdated, lock_plotUpdated,
                Fs, NFFT, nAverageOfPSD, Pxx):
    from matplotlib.pyplot import semilogy, ylabel, xlabel, gca, subplots_adjust, savefig, close
    from scipy import signal
    from numpy import array, transpose 

    nAverageOfPSD.value += 1
    Pxx_ = array(Pxx).reshape((3,int(NFFT/2)+1)).transpose()

    n = nAverageOfPSD.value 
    # logger = logging.getLogger(__name__)
    dpi = 80
    figure(1, figsize=(320/dpi, 240/dpi))
    clf()
    lock_data4plot.acquire()
    for i in range(3):
        f, Pxx__ = signal.welch(signal.detrend(data4plot[:, i+1]), int(Fs),
                                nperseg=NFFT)
        Pxx_[:, i] = (n-1.0)/n*Pxx_[:, i] + Pxx__/n    
        semilogy(f, Pxx_[:,i])
    lock_data4plot.release()
    xlabel('Frequency (Hz)')
    ylabel('PSD (g^2/Hz)')
    Fn = Fs/2
    gca().set_xlim([0, Fn])
    gca().yaxis.set_label_coords(-0.10, 0.5)
    subplots_adjust(left=0.13, bottom=0.15, right=0.95, top=0.95)
    lock_plotUpdated.acquire()
    savefig('.thp.png', dpi=80)
    plotUpdated.value = 1
    lock_plotUpdated.release()
    close(1)

    # RETURNING Pxx average
    for i in range(3):
        for j in range(int(NFFT/2)+1):
            Pxx[i*(int(NFFT/2)+1)+j] = Pxx_[j,i]
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

            lock_data4plot.acquire()
            data4plot = array(dataBuff)
            lock_data4plot.release()
            
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
    write2LED(0)
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


def toggleStatusLED(n):
    global statusLED, count_toggleStatusLED
    
    count_toggleStatusLED += 1
    if count_toggleStatusLED > n:
        if statusLED == 0:
            statusLED = 1
            write2LED(statusLED)
        else:
            statusLED = 0
            write2LED(statusLED)
        count_toggleStatusLED = 0
    return
        
def write2LED(cmd):
    if cmd == 1:
        GPIO.output(statusLED_PIN, GPIO.HIGH)
    elif cmd == 0:
        GPIO.output(statusLED_PIN, GPIO.LOW)
        
    
# PYGAME
os.putenv('SDL_FBDEV', '/dev/fb1')
pygame.init()

# Push Button Setup
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
for button in Buttons:
    GPIO.setup(button['Number'], GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(statusLED_PIN, GPIO.OUT)
GPIO.output(statusLED_PIN, GPIO.LOW)

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
