"""

    COPYRIGHT © 2018 BY DATAQ INSTRUMENTS, INC.


!!!!!!!!    VERY IMPORTANT    !!!!!!!!
!!!!!!!!    READ THIS FIRST   !!!!!!!!

This program works only with model DI-1110. 

Disconnect any other instrument models to prevent the program from 
detecting a different device model with a DATAQ Instruments VID and attempting to use it. 
Such attempts will fail.

While the DI-1110's protocol is similar to model DI-2108, it doesn't support
a decimation function. Therefore, its minimum sample rate of ~915 Hz is 
too fast for this program to work properly because of its heavy
use of print statements. This program overcomes that problem 
through use of a 'decimation_factor' variable to slow scan rate to an 
acceptable level. 

The DI-1110 used with this program MUST be placed in its CDC communication mode. 
Follow this link for guidance:
https://www.dataq.com/blog/data-acquisition/usb-daq-products-support-libusb-cdc/

The DI-1110 protocol this program uses can be downloaded from the instrument's 
product page:
https://www.dataq.com/resources/pdfs/misc/di-1110-protocol.pdf
"""


import serial
import serial.tools.list_ports
import keyboard
import time

""" 
Example slist for model DI-1110
0x0000 = Analog channel 0, ±10 V range
0x0001 = Analog channel 1, ±10 V range
0x0709 = Rate input, 0-500 Hz range
0x000A = Counter input
0x0008 = Digital input ports
"""
slist = [0x0000,0x0001,0x0709,0x0008,0x000A]

"""
Define a tuple that contains an ordered list of rate measurement ranges supported by the DI-1110. 
The first item in the list is the lowest gain code (e.g. 50 kHz range = gain code 1).
"""
rate_ranges = tuple((50000,20000,10000,5000,2000,1000,500,200,100,50,20,10))

ser=serial.Serial()

"""
Since model DI-1110 cannot scan slower that 915 Hz at the protocol level, 
and that rate or higher is not practical for this program, define a decimation 
factor to slow scan rate to a practical level. It defines the number of analog and rate readings to average
before displaying them. By design, and if enabled, digital inputs and the counter values display instantaneously
without averaging at the same rate as decimated analog and rate values.

Averaging n values on each analog and/or rate channel is more difficult than simply using
every nth value, but is recommended since it reduces noise by a factor of n^0.5 

'decimation_factor' must be an integer value greater than zero. 
'decimation_factor' = 1 disables decimation and attemps to output all values.
"""
# Define a decimation factor variable
decimation_factor = 1000

# Contains accumulated values for each analog channel used for the average calculation
achan_accumulation_table = list(())

# Init variable to contain accumulated rate channel reading for an average calculation. 
rate_accum = 0 

# Define flag to indicate if acquiring is active 
acquiring = False

""" Discover DATAQ Instruments devices and models.  Note that if multiple devices are connected, only the 
device discovered first is used. We leave it to you to ensure that it's a DI-1110."""
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
    # Define rate_range globally, since we need it to scale the rate channel while scanning
    global rate_range
    for item in slist:
        send_cmd("slist "+ str(position ) + " " + str(item))
        
        if ((item) & (0xf)) < 8:
            # This is an analog channel. Refer to the slist DI-1110 prototype
            # as defined in its protocol. Add the channel to the logical list.
            achan_accumulation_table.append(0)

        if ((item) & (0xf)) == 9:
            # This is a Rate channel. Set rate_range to the defined range.
            # Refer to the protocol document for details. 
            rate_range = rate_ranges[(slist[position] >> 8)-1]
        position += 1

while discovery() == False:
    discovery()
# Stop in case DI-1110 is already scanning
send_cmd("stop")
# Define binary output mode
send_cmd("encode 0")
# Keep the packet size small for responsiveness
send_cmd("ps 0")
# Configure the instrument's scan list
config_scn_lst()

# Define sample rate = 1 Hz, where decimation_factor = 1000:
# 60,000,000/(srate) = 60,000,000 / 60000 / decimation_factor = 1 Hz
send_cmd("srate 60000")
print("")
print("Ready to acquire...")
print ("")
print("Press <g> to go, <s> to stop, <r> to reset counter, and <q> to quit:")

# This is the slist position pointer. Ranges from 0 (first position)
# to len(slist)
slist_pointer = 0

# Init a decimation counter:
dec_count = decimation_factor

# Init the logical channel number for enabled analog channels
achan_number = 0

# This is the constructed output string
output_string = ""

# This is the main program loop, broken only by typing a command key as defined
while True:
    # If key 'G' start scanning
    if keyboard.is_pressed('g' or  'G'):
         keyboard.read_key()
         acquiring = True
         send_cmd("start")
    # If key 'r' reset counter
    if keyboard.is_pressed('r' or  'R'):
         keyboard.read_key()
         send_cmd("reset 1")
    # If key 'S' stop scanning
    if keyboard.is_pressed('s' or 'S'):
         keyboard.read_key()
         send_cmd("stop")
         time.sleep(1)
         ser.flushInput()
         print ("")
         print ("stopped")
         acquiring = False
    # If key 'Q' exit 
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
                result = int.from_bytes(bytes,byteorder='little', signed=True)
                achan_accumulation_table[achan_number] = result + achan_accumulation_table[achan_number]
                achan_number += 1
                if dec_count == 1:
                    # Get here if decimation count has expired. Scale & output the average of 'decimation_factor' number of values
                    output_string = output_string + "{: 3.3f}, ".format(achan_accumulation_table[achan_number-1] * 10 / 32768 / decimation_factor)

            elif function == 8:
                # Working with the Digital input channel 
                if dec_count == 1:
                    result = (int.from_bytes(bytes,byteorder='big', signed=False)) & (0x007f)
                    output_string = output_string + "{: 3d}, ".format(result)

            elif function == 9:
                # Working with the Rate input channel
                result = (int.from_bytes(bytes,byteorder='little', signed=True) + 32768)
                rate_accum = rate_accum + result
                if dec_count == 1:
                    # Get here if decimation count has expired. Scale & output the average of 'decimation_factor' number of values
                    output_string = output_string + "{: 3.1f}, ".format(rate_accum / 65535 * rate_range / decimation_factor)              

            else:
                # Working with the Counter input channel
                if dec_count == 1:
                    result = (int.from_bytes(bytes,byteorder='little', signed=True)) + 32768
                    output_string = output_string + "{: 1d}, ".format(result)

            # Get the next position in slist
            slist_pointer += 1

            if (slist_pointer + 1) > (len(slist)):
                # End of a pass through slist items
                if dec_count == 1:
                    # Get here if decimation loop has expired
                    dec_count = decimation_factor
                    # Reset the Rate channel accumulator
                    rate_accum = 0
                    # Reset analog channel accumulators to zero
                    achan_accumulation_table = [0] * len(achan_accumulation_table)
                    print(output_string.rstrip(", ") + "           ", end="\r") 
                    output_string = ""
                else:
                    dec_count -= 1             
                slist_pointer = 0
                achan_number = 0
ser.close()
SystemExit



