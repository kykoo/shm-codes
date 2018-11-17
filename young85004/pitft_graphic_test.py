#!/usr/bin/python3

from numpy import *
from matplotlib.pyplot import *
import pygame
import os


os.putenv('SDL_FBDEV', '/dev/fb1')
pygame.init()
#lcd = pygame.display.set_mode((320, 240))
# 
#Tend = 1
#Fs = 100.0
#dt = 1/Fs
#F = 1
#t = array([i*dt for i in range(int(round(Tend/dt)))])
#y = sin(2*pi*F*t)
# 
#figure(1)
#clf()
#plot(t,y)
# 
#set_size_inches(4, 3)
#gca().axes.get_xaxis().set_visible(False)
#savefig('sin-curve.png', dpi = 80)
#close(1)

#feed_surface = pygame.image.load("sin-curve.png")
#lcd.blit(feed_surface, (0,0))
#pygame.display.update()
