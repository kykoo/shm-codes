#!/usr/bin/python3
#
#  GOM-ADC-VS1002 DAQ System
#
#
#  written by k.y.koo@exeter.ac.uk
#
#
# 11 May 2018
#

from time import sleep

import pitft
import gom
from shm_daq_files import shm_daq_files
# < KEYSTROKE READING-----
import select
import tty
import termios
import sys
#   KEYSTROKE READING >---

#------------------------------------
# STATE OF MACHINE
#
# 1 = PPS MODE
# 2 = SILENCE MODE
# 3 = DAQ MODE 
# 4 = DAQ MODE WITH TIME-HISOTRY PLOT
# 5 = DAQ MODE WITH PSD PLOT
#------------------------------------

states = [1, 1]  # [PREVIOUS STATE, CURRENT STATE] OF THE MACHINE

# Display Time History graph automatically
AutoStart = True

# PITFT module for buttons and display
pitft.begin()
 
# GOM module for serial, parsing, resampling
gom.begin()

# File object for saving files
#accDAQfile = shm_daq_files('acc', 60)
accDAQfile = shm_daq_files('acc', 3600)

def pushbutton_callback():
    global  states
    n = pitft.getButtonStroke()
    # print(n, states)
    if n:
        if n == pitft.pinUpButton and states[1] < 5:
            states = [states[1], states[1]+1]
            # SEND UP COMMAND TO GOM
            gom.ser.write('u'.encode())
        if n == pitft.pinDownButton and states[1] > 1:
            states = [states[1], states[1]-1]
            # SEND DOWN COMMAND TO GOM
            gom.ser.write('d'.encode())
    return

def state_transition_callback():
    global states
    if states[1] == 4 and states[0] == 3:
        pitft.guiOn()
    elif states[1] == 3 and states[0] == 4:
        pitft.guiOff()
    return

def isKeyStrokeAvailable():
    import select
    return select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], [])

def keyboardStroke_callback():
    global states
    
    if isKeyStrokeAvailable():
        c = sys.stdin.read(1)
        # ESC stroke
        if c == '\x1b':	    
            return True
        # (U)P stroke
        if c == '\x75' and states[1] < 5:	    
            states = [states[1], states[1]+1]
            # SEND UP COMMAND TO GOM
            gom.ser.write('u'.encode())
        # (D)OWN stroke
        if c == '\x64' and states[1] > 1:	    
            states = [states[1], states[1]-1]
            # SEND DOWN COMMAND TO GOM
            gom.ser.write('d'.encode())
    return False

def AutoStartSequence():
    global states, AutoStart
    
    if states[1] == 1 and gom.n_pps == 3:
        states = [1, 2]
        gom.ser.write('u'.encode())
    if states[1] == 2:
        sleep(1)
        states = [2, 3]
        gom.ser.write('u'.encode())
        AutoStart = False
    # if states[1] == 3:
    #     sleep(1)
    #     states = [3, 4]
    #     gom.ser.write('u'.encode())
    #if states[1] == 4:
    #    sleep(1)
    #    states = [4, 5]
    #    gom.ser.write('u'.encode())
        
    return

def isRebooting():
    if len(gom.DAQ_resampled) ==0 or len(gom.DAQ_resampled[-1]) == 0:
        return False
    time = gom.DAQ_resampled[-1][0]
    sec  = time % (3600*24)  # number of seconds after the last midnight
    sec_trigger = 3600*23.75
    # sec = time % (60*10)
    # sec_trigger = 60*8
    if sec_trigger < sec and sec < sec_trigger + 20:
        return True
    else:
        return False


# LOOP
try:
    while(True):
     
        # This uses isKeyStrokeAvailable function
        if keyboardStroke_callback() is True:
            break
	
        # Pushbutton_callback uses pitft module in the background
        pushbutton_callback()

        # Auto Start to STATE4: Time History Plotting
        if AutoStart is True:
            AutoStartSequence()
            
        # Based on variable "states", on/off the gui mode on pitft
        state_transition_callback()
     
        # Read in comming characters from Serial and store it gom.rx_buff
        gom.rx_callback()
     
        # Parse gom.rx_buff and resamples
        gom.parse_rx_buff_and_resamples()
     
        # Logging
        # accDAQfile.log(messages)
     
        # Plotting a graph
        if states[1] == 4:
            # pass
            pitft.plot_vs1002(list(gom.DAQ_resampled))

        if states[1] == 5:
            pitft.plot_vs1002_psd(gom.DAQ_resampled[:])

        # Saving data
        accDAQfile.save(gom.DAQ_resampled)

        # Rebooting at 23:45 every night
        if isRebooting() is True:
            break;
        
        gom.DAQ_resampled = []
        
    gom.end()
except:
    gom.end()
    raise
    


