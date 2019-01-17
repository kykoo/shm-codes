#
#
#


import serial
from time import sleep
import RPi.GPIO as GPIO
from numpy import *


# SERIAL OBJECT
ser = serial.Serial(
    port='/dev/serial0',
    baudrate=115200,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout=0.1
)

# RX BUFFER
rx_buff = ''

# MESSAGES FROM GOM
messages = []

# LATEST PPS INFORMATION FROM GOM
PPS_latest = {'t': [], 'CC': [], 'Fclk': []}

# LATEST DAQ INFORMATION FROM GOM
DAQ_latest = {'t': 0, 'CC': 0, 'Values': []}

# RESAMPLING FREQUENCY
Fs = 300

# DAQ RESAMPLED
DAQ_resampled = []   # [timestamp, data1, data2, ...]

# THE CURRENT TIME FOR RESAMPLING 
tk = 0

# Number of PPS
n_pps = 0


def resamples():
    # Use the resampling algorithms on DAQ_latest and tk and
    # store it in "DAQ_resampled"
    
    global tk, DAQ_latest, DAQ_resampled

    #print(DAQ_latest['tj'])
    

def parse_rx_buff_and_resamples():
    global rx_buff, messages, tk, n_pps, PPS_latest, DAQ_latest, DAQ_resampled
    
    if(len(rx_buff) == 0):
        return

    while True:
        # GET A SINGLE LINE OR BREAK
        idx = rx_buff.find('\r\n')
        if idx == -1:
            break

        if False:
            # print(rx_buff[:idx] + '\r')
            rx_buff = rx_buff[(idx+2):]
            continue

        # PARSE INFO-LINE "0,*" and store it in "messages"
        if rx_buff[0] == '0':
            print(rx_buff[:idx] )
            messages.append(rx_buff[:idx])

        # PARSE PPS-LINE WITH TIMESTAMP "1,*" and store it in PPS_latest            
        if rx_buff[0] == '1':
            rx_buff_split = rx_buff[:idx].split(',')
            print(rx_buff[:idx])
            try:
                t = float(rx_buff_split[3])
                CC = float(rx_buff_split[1])*2**16 + float(rx_buff_split[2])
                if not PPS_latest['t']:
                    PPS_latest['t'] = t
                    PPS_latest['CC'] = CC
                else:
                    PPS_latest['Fclk'] = (CC -  PPS_latest['CC'])/(t - PPS_latest['t'])
                    PPS_latest['t'] = t
                    PPS_latest['CC'] = CC
                # Count n_pps for AutoStart
                if  n_pps < 3:
                    n_pps += 1
            except:
                rx_buff = rx_buff[(idx+2):]
                # raise
                continue
            
        # PARSE DAQ-LINE "2,*" and store it in DAQ_latest
        if rx_buff[0] == '2':
            rx_buff_split = rx_buff[:idx].split(',')
            # print(rx_buff[:idx] + '\n')            
            try:
                # PARSING
                CC = float(rx_buff_split[1])*2**16 + float(rx_buff_split[2])
                Values = []
                scaleFactor = 2.5/(2**23 -1) /1.35 # Unit is g
                for icol in range(3, 5): #len(rx_buff_split)):
                    Values.append(float(rx_buff_split[icol]) * scaleFactor)
                t = PPS_latest['t'] + (CC - PPS_latest['CC']) / PPS_latest['Fclk'] * 1.0
                # print([t]+ Values)

                if DAQ_latest['t'] == 0:
                    # Initialisation when 'tj' empty
                    DAQ_latest['t'] = t
                    DAQ_latest['CC'] = CC
                    DAQ_latest['Values'] = Values
                    # Set the resampling timestamp
                    tk  = float(round(t*Fs + 1))/Fs
                elif t < tk:
                    DAQ_latest['t'] = t
                    DAQ_latest['CC'] = CC
                    DAQ_latest['Values'] = Values
                elif tk <= t:
                    # RESAMPLING
                    while tk < t:
                        Values_k = []
                        for icol in range(0, 2):
                            Values_intp = interp(tk, [DAQ_latest['t'], t],
                                                 [DAQ_latest['Values'][icol], Values[icol]])
                            Values_k.append(Values_intp)
                        DAQ_resampled.append([tk]+ Values_k)

                        # DISPLAY MEASUMENTS TWICE A SECOND
                        if remainder(int((tk-floor(tk))*Fs), 150) == 0:
                            print('{:18.6f}, {:8.5f}, {:8.5f}'.format(tk,Values_k[0], Values_k[1]), end='\r')
                        
                        # MOVE TO THE NEXT RESAMPLING TIMESTAMP
                        tk = round(tk * Fs + 1.0) / Fs
                    DAQ_latest['t'] = t
                    DAQ_latest['Values'] = Values
            except:
                rx_buff = rx_buff[(idx+2):]
                # raise
                continue

        # PARSE PPS-LINE WITHOUT TIMESTAMP "3,*" and store it in PPS_latest
        if rx_buff[0] == '3':
            rx_buff_split = rx_buff[:idx].split(',')
            # print(rx_buff[:idx])            
            try:
                # Estimate the current timestamp from PPS_latest and CC
                CC = float(rx_buff_split[1])*2**16 + float(rx_buff_split[2])
                dT = float(round((CC - PPS_latest['CC'])/PPS_latest['Fclk']))
                PPS_latest['CC'] = CC
                PPS_latest['t'] = PPS_latest['t'] + dT
            except:
                rx_buff = rx_buff[(idx+2):]
                # raise
                continue
        rx_buff = rx_buff[(idx+2):]
    return

def rx_callback():
    global rx_buff
    
    #while ser.inWaiting() > 0:
    try:
        rx_buff += ser.read(1000).decode('UTF-8')
    except:
        pass
    return

def begin():
    # RESET THE NODE
    GPIO.setup(16, GPIO.OUT)
    GPIO.output(16, GPIO.LOW)
    sleep(1)
    GPIO.output(16, GPIO.HIGH)
    sleep(1)

def end():
    GPIO.output(16, GPIO.LOW)
    # GPIO.cleanup()
    
# ERROR CHECKING
if(ser.isOpen() is False):
    sys.exit('Serial is not open!')
    
# FLUSH INPUT BUFFER
while ser.inWaiting() > 0:
    # ser.reset_input_buffer() <- This simple approach doesn't work. Why?
    ser.read(1)

