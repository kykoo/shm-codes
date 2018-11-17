# Field Measurement System SW for GOM Nodes
#
#
#
# gui stop keyboard stroke
# plot range option

from numpy import *
from time import sleep
import datetime
import os
import sys
from matplotlib.pyplot import *
import scanf
import csv
from drawnow import drawnow
import matplotlib.dates as mdates


def keypress_callback(event):
    global reload
    if event.key == 'q':
        reload = False


nodeType = 'gom'
nodeNums = arange(3, 5)
TimeWindow = 30  # seconds
Fs = 100
NFFT = 2**5
rootDir = '/home/kykoo/Dropbox/experiments/nodes/'

gom = empty((5), dtype=object)

# CHECK IF ACCESSIBLE TO NODE NFS DIRECTORIES
for inode in nodeNums:
    hostName = nodeType + str(inode)
    pathFull = rootDir + hostName
    files = [x for x in os.listdir(pathFull) if x.endswith(".txt")]
    file = open(pathFull + "/" + files[-1], "rb")
    gom[inode] = {'file': [], 't': [], 'acc': [], 'plot': []}
    gom[inode]['file'] = file

ion()
fig = figure(1)
clf()
grid(True)
fig.canvas.mpl_connect('key_press_event', keypress_callback)
reload = True
while True:
    for inode in nodeNums:
        title('Loading data from gom' + str(inode) + '...')
        pause(0.05)
        lines = gom[inode]['file'].read().decode('UTF-8').splitlines()
        title('Loading data from gom' + str(inode) + '... done.')
        pause(0.05)
        t = []
        acc = []
        for line in lines:
            r = scanf.scanf('%f, %f, %f, %f', line)
            t.append(datetime.datetime.fromtimestamp(r[0]))
            acc.append([r[1], r[2], r[3]])
        if len(t) == 0:
            continue
        if len(gom[inode]['t']) == 0:
            gom[inode]['t'] = array(t)
            gom[inode]['acc'] = array(acc)
        else:
            gom[inode]['t'] = append(gom[inode]['t'], t)
            gom[inode]['acc'] = append(gom[inode]['acc'], array(acc), axis=0)
        # REMOVE OLD DATA
        idx = nonzero(gom[inode]['t'] < datetime.datetime.now() - datetime.timedelta(seconds=TimeWindow))
        gom[inode]['t'] = delete(gom[inode]['t'], idx)
        gom[inode]['acc'] = delete(gom[inode]['acc'], idx, axis=0)

    title('plotting...')
    pause(0.05)
    for inode in nodeNums:
        if len(gom[inode]['plot']) == 0:
            print('first plot')
            gom[inode]['plot'] = plot(gom[inode]['t'], gom[inode]['acc'])
        else:
            print('updating plot')
            for j in range(3):
                gom[inode]['plot'][j].set_xdata(gom[inode]['t'])
                gom[inode]['plot'][j].set_ydata(gom[inode]['acc'][:, j])
            fig.canvas.draw()
    gca().set_ylim([-1, 2])
    gca().set_xlim([datetime.datetime.now() - datetime.timedelta(seconds=20),
                    datetime.datetime.now()])
    gca().xaxis.set_major_formatter(mdates.DateFormatter('%M:%S'))
    title('plotting... done')
    pause(0.05)
    sleep(1)
    if reload is False:
        pause(0.5)
        break

while True:
    pause(0.05)
