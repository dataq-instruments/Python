"""

    COPYRIGHT © 2018 BY DATAQ INSTRUMENTS, INC.


!!!!!!!!    VERY IMPORTANT    !!!!!!!!
!!!!!!!!    READ THIS FIRST   !!!!!!!!

This program works only with the following models:
DI-1120, -2108, -4108, -4208, AND -4718B
Any other instrument model should be disconnected from the PC
to prevent the program from detecting a device with a DATAQ
Instruments VID and attempting to use it. 
Such attempts will fail.

You'll need to uncomment the appropriate 

slist
analog_ranges

tuples for the instrument model you will use with this program.
Prototypes are provided for each supported model, so it's a
simple matter of commenting the ones that don't apply, and 
uncommenting the one that does. In its as-delivered state
the program assumes that model DI-2108 is connected. 

Instruments used with this program MUST be placed in their
CDC communication mode. 
Follow this link for guidance:
https://www.dataq.com/blog/data-acquisition/usb-daq-products-support-libusb-cdc/

Any specific instrument's protocol document can be downloaded from the instrument's 
product page: Once there, click the DETAILS tab.
"""


import serial
import serial.tools.list_ports
import keyboard
import time

"""
Uncomment the slist tuple depending upon the hardware model you're using. 
You can modify the example tuples to change the measurement configuration
as needed. Refer to the instrument's protocol for details. Note that 
only one slist tuple can be enabled at a time. 
"""
""" 
slist for models DI-1120 and DI-4208
0x0300 = Analog channel 0, ±10 V range
0x0401 = Analog channel 1, ±5 V range
0x0709 = Rate input, 0-500 Hz range
0x000A = Counter input
"""
#slist = [0x0300,0x0401,0x0709,0x000A]

""" 
slist for model DI-4108
0x0000 = Analog channel 0, ±10 V range
0x0101 = Analog channel 1, ±5 V range
0x0709 = Rate input, 0-500 Hz range
0x000A = Counter input
"""
#slist = [0x0000,0x0101,0x0709,0x000A]

""" 
slist for model DI-2108
0x0000 = Analog channel 0, ±10 V range
0x0001 = Analog channel 1, ±10 V range
0x0709 = Rate input, 0-500 Hz range
0x000A = Counter input
"""
slist = [0x0000,0x0001,0x0709,0x000A]

""" 
slist for model DI-4718B (untested, but should work)
0x0000 = Analog channel 0, ±5 V range
0x0001 = Analog channel 1, ±5 V range
"""
#slist = [0x0000,0x0001]

"""
Uncomment an analog_ranges tuple depending upon the hardware model you're using. 
Note that only one can be enabled at a time. 
The first item in the tuple is the lowest gain code (e.g. ±100 V range = gain code 0)
for the DI-4208. Some instrument models do not support programmable gain, so 
their tuples contain only one value (e.g. model DI-2108.)
"""
# Analog ranges for models DI-4208 and -1120
#analog_ranges = tuple((100,50,20,10,5,2))

# Analog ranges for model DI-4108
#analog_ranges = tuple((10,5,2,1,0.5,0.2))

# Analog ranges for model DI-2108 (fixed ±10 V measurement range)
analog_ranges = [10]

# Analog ranges for model DI-4718B (fixed ±5 V measurement range)
#analog_ranges = [5]

"""
Define a tuple that contains an ordered list of rate measurement ranges supported by the hardware. 
The first item in the list is the lowest gain code (e.g. 50 kHz range = gain code 1).
"""
rate_ranges = tuple((50000,20000,10000,5000,2000,1000,500,200,100,50,20,10))

# This is a list of analog and rate ranges to apply in slist order
range_table = list(())

ser=serial.Serial()

# Define flag to indicate if acquiring is active 
acquiring = False

""" Discover DATAQ Instruments devices and models.  Note that if multiple devices are connected, only the 
device discovered first is used. We leave it to you to ensure that it's the desired device model."""
def discovery():
    # Get a list of active com ports to scan for possible DATAQ Instruments devices
    available_ports = list(serial.tools.list_ports.comports())
    # Will eventually hold the com port of the detected device, if any
    hooked_port = "" 
    for p in available_ports:
        # Do we have a DATAQ Instruments device?
        if ("VID:PID=0683" in p.hwid):
            # Yes!  Dectect and assign the hooked com port
            hooked_port = p.device
            break

    if hooked_port:
        print("Found a DATAQ Instruments device on",hooked_port)
        ser.timeout = 0
        ser.port = hooked_port
        ser.baudrate = '115200'
        ser.open()
        return(True)
    else:
        # Get here if no DATAQ Instruments devices are detected
        print("Please connect a DATAQ Instruments device")
        input("Press ENTER to try again...")
        return(False)

# Sends a passed command string after appending <cr>
def send_cmd(command):
    ser.write((command+'\r').encode())
    time.sleep(.1)
    if not(acquiring):
        # Echo commands if not acquiring
        while True:
            if(ser.inWaiting() > 0):
                while True:
                    try:
                        s = ser.readline().decode()
                        s = s.strip('\n')
                        s = s.strip('\r')
                        s = s.strip(chr(0))
                        break
                    except:
                        continue
                if s != "":
                    print (s)
                    break

# Configure the instrment's scan list
def config_scn_lst():
    # Scan list position must start with 0 and increment sequentially
    position = 0 
    for item in slist:
        send_cmd("slist "+ str(position ) + " " + str(item))
        position += 1
        # Update the Range table
        if ((item) & (0xf)) < 8:
            # This is an analog channel. Refer to the slist prototype for your instrument
            # as defined in the instrument protocol. 
            range_table.append(analog_ranges[item >> 8])

        elif ((item) & (0xf)) == 8:
            # This is a dig in channel. No measurement range support. 
            # Update range_table with any value to keep it aligned.
            range_table.append(0) 

        elif ((item) & (0xf)) == 9:
            # This is a rate channel
            # Rate ranges begin with 1, so subtract 1 to maintain zero-based index
            # in the rate_ranges tuple
            range_table.append(rate_ranges[(item >> 8)-1]) 

        else:
            # This is a count channel. No measurement range support.
            # Update range_table with any value to keep it aligned.
            range_table.append(0)

while discovery() == False:
    discovery()
# Stop in case Device was left running
send_cmd("stop")
# Define binary output mode
send_cmd("encode 0")
# Keep the packet size small for responsiveness
send_cmd("ps 0")
# Configure the instrument's scan list
config_scn_lst()
# Define sample rate = 10 Hz:
# 60,000,000/(srate * dec) = 60,000,000/(11718 * 512) = 10 Hz
send_cmd("dec 512")
send_cmd("srate 11718")
print("")
print("Ready to acquire...")
print ("")
print("Press <g> to go, <s> to stop, <r> to reset counter, and <q> to quit:")

# This is the slist position pointer. Ranges from 0 (first position)
# to len(slist)
slist_pointer = 0
# This is the constructed output string
output_string = ""

while True:
    # If key 'SPACE' start scanning
    if keyboard.is_pressed('g' or  'G'):
         keyboard.read_key()
         acquiring = True
         send_cmd("start")
    # If key 'r' reset counter
    if keyboard.is_pressed('r' or  'R'):
         keyboard.read_key()
         send_cmd("reset 1")
    # If key 'esc' stop scanning
    if keyboard.is_pressed('s' or 'S'):
         keyboard.read_key()
         send_cmd("stop")
         time.sleep(1)
         ser.flushInput()
         print ("")
         print ("stopped")
         acquiring = False
    # If key 'q' exit 
    if keyboard.is_pressed('q' or 'Q'):
         keyboard.read_key()
         send_cmd("stop")
         ser.flushInput()
         break
    while (ser.inWaiting() > (2 * len(slist))):
         for i in range(len(slist)):
            # The four LSBs of slist determine measurement function
            function = (slist[slist_pointer]) & (0xf)
            # Always two bytes per sample...read them
            bytes = ser.read(2)
            if function < 8:
                # Working with an Analog input channel
                result = range_table[slist_pointer] * int.from_bytes(bytes,byteorder='little', signed=True) / 32768
                output_string = output_string + "{: 3.5f}, ".format(result)

            elif function == 8:
                # Working with the Digital input channel 
                result = (int.from_bytes(bytes,byteorder='big', signed=False)) & (0x007f)
                output_string = output_string + "{: 3d}, ".format(result)

            elif function == 9:
                # Working with the Rate input channel
                result = (int.from_bytes(bytes,byteorder='little', signed=True) + 32768) / 65535 * (range_table[slist_pointer])
                output_string = output_string + "{: 3.1f}, ".format(result)

            else:
                # Working with the Counter input channel
                result = (int.from_bytes(bytes,byteorder='little', signed=True)) + 32768
                output_string = output_string + "{: 1d}, ".format(result)

            # Get the next position in slist
            slist_pointer += 1

            if (slist_pointer + 1) > (len(slist)):
                # End of a pass through slist items...output, reset, continue
                print(output_string.rstrip(", ") + "           ", end="\r") 
                output_string = ""
                slist_pointer = 0
ser.close()
SystemExit


