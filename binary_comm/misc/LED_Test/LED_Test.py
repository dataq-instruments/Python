"""

    COPYRIGHT © 2018 BY DATAQ INSTRUMENTS, INC.


!!!!!!!!    VERY IMPORTANT    !!!!!!!!
!!!!!!!!    READ THIS FIRST   !!!!!!!!

Exercise the instrument's LED through various colors using 
the protocol 'led arg0' command. 

This program works only with the following models:
DI-1100, -1110, -2008, -1120, -2108, -4108, -4208, AND -4718B
Any other instrument model should be disconnected from the PC
to prevent the program from detecting a device with a DATAQ
Instruments VID and attempting to use it. 
Such attempts will fail.

Instruments used with this program MUST be placed in their
CDC communication mode. 
Follow this link for guidance:
https://www.dataq.com/blog/data-acquisition/usb-daq-products-support-libusb-cdc/

Any specific instrument's protocol document can be downloaded from the instrument's 
product page: Once there, click the DETAILS tab.
"""

import time
import io
import serial
import sys
import usb.core
import serial.tools.list_ports as ports

def findProdPort():
    # find USB devices
    device = usb.core.find(find_all=True)
    # loop through devices and check the hexadecimal form of each one's product id
    for cfg in device:
        regPID = hex(cfg.idVendor)

        # find a match with the target vendor id. Up to you to ensure it's a compatible model. 
        if regPID == '0x683':
            uid = cfg.idProduct

            # search through COM Ports and find location of connected product
            p_list = ports.comports()

            for com in p_list:
                #ser1 = serial.Serial('COM9', 38400, timeout=100)
                if com.pid == uid:
                    serID = str(com.device)
                    return serID

ser1 = serial.Serial(findProdPort(), 38400, timeout=100)

i = 0
while True:
   ser1.write(b"led 1\r")
   time.sleep(1)
   ser1.write(b"led 2\r")
   time.sleep(1)
   ser1.write(b"led 4\r")
   time.sleep(1)
   ser1.write(b"led 7\r")
   time.sleep(1)
   print(i)
   i=i+1
   if i > 3:
    ser1.write(b"led 6\r")
    break
