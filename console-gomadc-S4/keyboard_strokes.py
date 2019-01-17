#!/usr/bin/python3
#
#


import sys
import select
import tty
import termios
from time import sleep


def isKeyStrokeAvailable():
    import select
    return select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], [])

def begin():
    global old_settings
    # STORE TERMINAL SETTING
    old_settings = termios.tcgetattr(sys.stdin)

def get_keyboard_stroke():
    if isKeyStrokeAvailable():
        c = sys.stdin.read(1)
        return c
    else:
        return 

def end():
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)


old_settings = ''

if __name__ == '__main__':
    begin()
    while True:
        c = get_keyboard_stroke()
        if c:
            print(ord(c))
        sleep(0.05)
    end()
            

