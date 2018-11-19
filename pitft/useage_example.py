#!/usr/bin/python3

import pitft
from time import sleep

# configuration
pitft.state_guiOnOff = [0, 0, 0, 1, 1]
pitft.begin()

print("pitft.begin() done...")

while True:

    pitft.pushbutton_callback()

    pitft.display_time()

    sleep(0.05)
    
