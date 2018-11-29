#!/bin/bash

# Add following to your crontab
# * * * * * /home/pi/codes/shm-codes/wifi-reconnect/wifi-recon.sh


if ! [ "$(ping -c 1 192.168.3.1)" ]; then
    /usr/bin/sudo /sbin/ifdown wlan0
    /usr/bin/sudo /sbin/ifup wlan0
fi
