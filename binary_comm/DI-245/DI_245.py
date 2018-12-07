"""

    COPYRIGHT © 2018 BY DATAQ INSTRUMENTS, INC.


!!!!!!!!    VERY IMPORTANT    !!!!!!!!
!!!!!!!!    READ THIS FIRST   !!!!!!!!

This program works only with the following models:
DI-245.

Any other instrument model should be disconnected from the PC
to prevent the program from detecting a device with a DATAQ
Instruments VID and attempting to use it. 
Such attempts will fail.

"""


import serial
import serial.tools.list_ports
import keyboard
import time

"""
Change slist tuple to vary analog channel configuration.
Refer to the protocol for details.
"""
slist = [0x0A00,0x0B01,0x1702,0x1303]
""" slist Tuple Example Interpretation (from protocol)
0x0A00 = Channel 0, ±10 V range
0x0B01 = Channel 1, ±5 V range
0x1702 = Channel 2, T-type TC
0x1303 = Channel 3. K-type TC


Define analog_ranges tuple to contain an ordered list of analog measurement ranges supported by the DI-245. 
This tuple begins with gain code 0 (±500 mV) and ends gain code 0xD (±1 V) and is padded with 0 values
as place holders for undefined codes (see protocol.)
"""
analog_ranges = [.5, 0.25, 0.1, .05, .025, .01, 0, 0, 50 ,25, 10, 5, 2.5, 1, 0, 0]

"""
m and b TC scaling constants in TC type order: B, E, J, K, N, R, S, T
See protocol
"""
tc_m = [0.095825,0.073242,0.08606,0.095947,0.091553,0.110962,0.110962,0.036621]
tc_b = [1035,400,495,586,550,859,859,100]


"""
Define a list of analog voltage ranges to apply in slist order.
Value 0 is appended as a placeholder for enabled TC channels. 
This list is populated in the config_scn_lst() routine based upon 
slist contents.
"""
range_table = list(())

"""
Set the dig_inputs flag to display digital input states.
"""
dig_inputs = False

ser=serial.Serial()

"""
Discover DATAQ Instruments devices.  Note that if multiple devices are connected, only the 
device discovered first is used. We leave it to you to ensure that it's model DI-245
"""
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
        input("Press ENTER to try again...")
        return (False)

# Sends a passed command string after appending <cr>
def send_cmd(command):
    ser.write((command+'\r').encode())
    time.sleep(.1)

    # Echo most commands
    while True:
        if(ser.inWaiting() > 0):
            while True:
                try:
                    s = ser.readline().decode()
                    s = s.strip('\n')
                    s = s.strip('\r')
                    s = s.strip(chr(0))
                    if (command == "S1") or (command == "S0"):
                        # Don't echo start or stop commands
                        return
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
        send_cmd("chn "+ str(position ) + " " + str(item))
        position += 1
        # Update the Range table. slist bit 12 is cleared for voltage, and set for TC channels
        if ((item) & (0x1000)) == 0:
            # This is a voltage input channel. 
            range_table.append(analog_ranges[item >> 8])
        else:
            # This is a thermocouple channel. Append 0 as a place holder
            range_table.append(0) 

while discovery() == False:
    discovery()
# Stop in case Device was left running
send_cmd("stop")
# Configure the instrument's scan list
config_scn_lst()
"""
Define sample rate = 20 Hz (refer to protocol):
Sinc4 = 1
AF = 1
SF = 0x63
"""
send_cmd("xrate 4451 20")
if dig_inputs:
    # Enable digital inputs
    send_cmd("dchn 1")
print("")
print("Ready to acquire...")
print ("")
print("Press <g> to go, <s> to stop, and <q> to quit:")

"""
This is the slist position pointer. Ranges from 0 (first position)
to len(slist).
"""
slist_pointer = 0
"""
This is the constructed output string, which we append
data to for each item in slist
"""
output_string = ""

# Loop continuously until the quit command
while True:
    # If key 'g' start scanning
    if keyboard.is_pressed('g' or  'G'):
         keyboard.read_key()
         ser.flushInput()
         ser.flushOutput()
         send_cmd("S1")
    # If key 's' stop scanning
    if keyboard.is_pressed('s' or 'S'):
         keyboard.read_key()
         send_cmd("S0")
         time.sleep(1)
         #ser.flushInput()
         print ("")
         print ("stopped")
    # If key 'q' exit 
    if keyboard.is_pressed('q' or 'Q'):
         keyboard.read_key()
         send_cmd("S0")
         break

    while (ser.inWaiting() > (2 * len(slist))):
         for i in range(len(slist)):
            # slist Mode bit (bit 12) determines measurement function
            function = (slist[slist_pointer]) & (0x1000)
            # Always two bytes per sample...read them now
            bytes = ser.read(2)
            # slist contains only voltage and TC channels, so convert 'bytes' to counts
            # Clone high byte (bytes[1])
            high_byte = bytes[1]
            # Invert the sign bit
            high_byte = high_byte ^ 0x80
            # New byte array containing low and high byte with inverted sign bit
            _bytes = [bytes[0], high_byte]
            """
            Convert _bytes into signed integer.
            Sync bits still need to be removed along with some bit repositioning 
            for useful ADC counts (-8192 to +8191.)
            """
            counts = int.from_bytes(_bytes,byteorder='little', signed=True)
            """
            Remove sync bits and reposition to yield final ADC counts.
            Start by removing sync bit from LS byte.
            """
            counts = counts >> 1
            # Now preserve LS byte data
            ls_byte = counts & 0x7F
            # Shift to remove sync bit from MS byte
            counts = counts >> 8
            # Shift to move MS byte back into original position, minus 1
            counts = counts << 7
            # Restore LS byte
            counts = counts | ls_byte
            # Finally ready to convert final ADC counts into engineering units
            if function == 0:
                # Convert to volts
                result = range_table[slist_pointer] * counts / 8192
                output_string = output_string + "{: 3.3f}, ".format(result)
            else:
                """
                Convert to temperature if no errors.
                First, test for TC error conditions.
                """
                if counts == 8191:
                    output_string = output_string + "cjc error, "
                        
                elif counts == -8192:
                    output_string = output_string + "open, "
                        
                else:
                    # Get here if no errors, so isolate TC type
                    tc_type = slist[slist_pointer] & 0x0700
                    # Move TC type into 3 LSBs to form an index we'll use to select m & b scaling constants
                    tc_type = tc_type >> 8
                    result = tc_m[tc_type] * counts + tc_b[tc_type]
                    output_string = output_string + "{: 3.3f}, ".format(result)

            # Get the next position in slist
            slist_pointer += 1

            if (slist_pointer + 1) > (len(slist)):
                """
                We're at the end of the slist and all enabled analog channels. 
                Digital inputs, if enabled, are served after analog channels.
                """
                if dig_inputs:
                    # Capture an additional 2 bytes for the digital inputs
                    bytes = ser.read(2)
                    # More bitwise gymnastics to remove sync bits and position D0 and D1 for output (see protocol.)
                    high_byte = bytes[1]
                    # Strip sync bit so D1 moves to LSB
                    high_byte = high_byte >>1
                    # New byte array containing modified high_byte
                    _bytes = [bytes[0], high_byte]
                    # Combine both bytes into an unsigned integer
                    counts = int.from_bytes(_bytes,byteorder='little', signed=False)
                    """
                    Shift bits right so that D1 and D0 appear in LSB+1 and LSB positions respectively
                    to display values in the range of 0-3.
                    """
                    counts = counts >> 7
                    output_string = output_string + str(counts)
                # End of a pass through all slist items...output, reset, continue
                print(output_string.rstrip(", ") + "              ", end="\r") 
                output_string = ""
                slist_pointer = 0
SystemExit()



