"""

    COPYRIGHT © 2018 BY DATAQ INSTRUMENTS, INC.


!!!!!!!!    VERY IMPORTANT    !!!!!!!!
!!!!!!!!    READ THIS FIRST   !!!!!!!!

This program works only with model:
DI-2008

Any other instrument model should be disconnected from the PC
to prevent the program from detecting a device with a DATAQ
Instruments VID and attempting to use it. 
Such attempts will fail.

The DI-2008 MUST be placed in its CDC communication mode. 
Follow this link for guidance:
https://www.dataq.com/blog/data-acquisition/usb-daq-products-support-libusb-cdc/

The instrument's protocol document, referred to often throughout, can be found here:
https://www.dataq.com/resources/pdfs/misc/di-2008%20protocol.pdf

"""


import serial
import serial.tools.list_ports
import keyboard
import time

"""
Change slist tuple to vary analog channel configuration.
Refer to the protocol for details.
"""
slist = [0x0A00,0x0B01,0x1702,0x1303,0x0709,0x000A,0x0008]
""" slist Tuple Example Interpretation (from protocol)
0x0A00 = Channel 0, ±10 V range
0x0B01 = Channel 1, ±5 V range
0x1702 = Channel 2, T-type TC
0x1303 = Channel 3. K-type TC
0x0709 = Rate channel, 500 Hz range
0x000A = Count channel
0x0008 = Digital inputs


Define analog_ranges tuple to contain an ordered list of analog measurement ranges supported by the DI-2008. 
This tuple begins with gain code 0 (±500 mV) and ends gain code 0xD (±1 V) and is padded with 0 values
as place holders for undefined codes (see protocol.)
"""
analog_ranges = [.5, 0.25, 0.1, .05, .025, .01, 0, 0, 50 ,25, 10, 5, 2.5, 1, 0, 0]

"""
Define a tuple that contains an ordered list of rate measurement ranges supported by the DI-2008. 
The first item in the list is the lowest gain code (e.g. 50 kHz range = gain code 1).
"""
rate_ranges = tuple((50000,20000,10000,5000,2000,1000,500,200,100,50,20,10))

"""
m and b TC scaling constants in TC type order: B, E, J, K, N, R, S, T
See protocol
"""
tc_m = [0.023956,0.018311,0.021515,0.023987,0.022888,0.02774,0.02774,0.009155]
tc_b = [1035,400,495,586,550,859,859,100]


"""
Define a list of analog voltage and rate ranges to apply in slist order.
Value 0 is appended as a placeholder for enabled TC and dig-in channels. 
This list is populated in the config_scn_lst() routine based upon 
slist contents.
"""
range_table = list(())

# Define flag to indicate if acquiring is active 
acquiring = False

ser=serial.Serial()


""" Discover DATAQ Instruments devices and models.  Note that if multiple devices are connected, only the 
device discovered first is used. We leave it to you to ensure that the device is a model DI-2008 """
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
        return (True)
    else:
        # Get here if no DATAQ Instruments devices are detected
        print("Please connect a DATAQ Instruments device")
        input("Press ENTER to continue...")
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
        if (item & 0xf < 8) and (item & 0x1000 == 0):
            # This is a voltage channel.
            range_table.append(analog_ranges[item >> 8])

        elif (item & 0xf < 8) and (item & 0x1000 != 0):
            # This is a TC channel. Append 0 as a placeholder
            range_table.append(0)

        elif item & 0xf == 8:
            # This is a dig in channel. No measurement range support. 
            # Append 0 as a placeholder
            range_table.append(0) 

        elif item & 0xf == 9:
            """
            This is a rate channel
            Rate ranges begin with 1, so subtract 1 to maintain zero-based index
            in the rate_ranges tuple
            """
            range_table.append(rate_ranges[(item >> 8)-1]) 

        else:
            """
            This is a count channel. No measurement range support. 
            Append 0 as a placeholder
            """
            range_table.append(0)

while discovery() == False:
    discovery()
# Stop in case Device was left running
send_cmd("stop")
# Keep the packet size small for responsiveness
send_cmd("ps 0")
# Configure the instrument's scan list
config_scn_lst()
# Define sample rate = 10 Hz (refer to protocol:)
# 800/(srate * dec) = 800/(4 * 20) = 10 Hz
send_cmd("dec 20")
send_cmd("srate 4")
print("")
print("Ready to acquire...")
print ("")
print("Press <g> to go, <s> to stop, <r> resets counter channel, and <q> to quit:")

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
    # If key 'esc' stop scanning
    if keyboard.is_pressed('s' or 'S'):
         keyboard.read_key()
         send_cmd("stop")
         time.sleep(1)
         #ser.flushInput()
         print ("")
         print ("stopped")
         ser.flushInput()
         acquiring = False
    # If key 'q' exit 
    if keyboard.is_pressed('q' or 'Q'):
         keyboard.read_key()
         send_cmd("stop")
         break
        # If key 'r' reset counter 
    if keyboard.is_pressed('r' or 'R'):
         keyboard.read_key()
         send_cmd("reset 1")
    while (ser.inWaiting() > (2 * len(slist))):
         for i in range(len(slist)):
            # The four LSBs of slist determine measurement function
            function = slist[slist_pointer] & 0xf
            mode_bit = slist[slist_pointer] & 0x1000
            # Always two bytes per sample...read them
            bytes = ser.read(2)
            if (function < 8) and (not(mode_bit)):
                # Working with a Voltage input channel. Scale accordingly.
                result = range_table[slist_pointer] * int.from_bytes(bytes,byteorder='little', signed=True) / 32768
                output_string = output_string + "{: 3.3f}, ".format(result)
            elif (function < 8) and (mode_bit):
                """
                Working with a TC channel.
                Convert to temperature if no errors.
                First, test for TC error conditions.
                """
                result = int.from_bytes(bytes,byteorder='little', signed=True)
                if result == 32767:
                    output_string = output_string + "cjc error, "
                        
                elif result == -32768:
                    output_string = output_string + "open, "
                        
                else:
                    # Get here if no errors, so isolate TC type
                    tc_type = slist[slist_pointer] & 0x0700
                    # Move TC type into 3 LSBs to form an index we'll use to select m & b scaling constants
                    tc_type = tc_type >> 8
                    result = tc_m[tc_type] * result + tc_b[tc_type]
                    output_string = output_string + "{: 3.3f}, ".format(result)

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
                print(output_string.rstrip(", ") + "             ", end="\r") 
                output_string = ""
                slist_pointer = 0
SystemExit

