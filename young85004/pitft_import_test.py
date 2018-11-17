#!/usr/bin/python3


import pitft


pitft.pinUpButton = 27
pitft.pinDownButton = 22
pitft.begin()

while True:
    n = pitft.getButtonStroke()
    if n:
        print(n)
        
