import sys
import os 

# add path to our file
#sys.path.append('c:/Users/Robert/Programming/Python/Common/')
#sys.path.append('c:/Users/Robert/Programming/Python/Plotting/')

# The aim here is to write a script for interfacing to the ItsyBitsyM4
# Want to be able to write voltage out commands and read voltage in data
# Some online references
# https://pyserial.readthedocs.io/en/latest/shortintro.html
# https://pyserial.readthedocs.io/en/latest/pyserial_api.html
# R. Sheehan 30 - 11 - 2020

import serial # import the pySerial module pip install pyserial
import pyvisa
import time

MOD_NAME_STR = "IBM4_Serial"
HOME = False
USER = 'Robert' if HOME else 'robertsheehan/OneDrive - University College Cork/Documents'

def Serial_Attempt():
    # Attempting to communicate with the ItsyBitsy M4 via Serial comms
    # It isn't really working, but it seems to work fine with the Arduino Micro
    # Going to try VISA comms instead
    # R. Sheehan 30 - 11 - 2020

    # Online documentation
    # https://pyserial.readthedocs.io/en/latest/shortintro.html 

    FUNC_NAME = ".Serial_Attempt()" # use this in exception handling messages
    ERR_STATEMENT = "Error: " + MOD_NAME_STR + FUNC_NAME

    try:
        DELAY = 1 # timed delay in units of seconds

        #DEVICE = 'COM14' # Address / Port of the device that you want to communicate with, check device manager
        DEVICE = 'COM6' # Address / Port of the device that you want to communicate with, check device manager
        
        timeout = DELAY # finite timeout requried for reading
        
        baudrate = 9600 # All these defaults are fine, 
        bytesize = serial.EIGHTBITS
        parity = serial.PARITY_NONE
        stopbits = serial.STOPBITS_ONE 
        xonxoff = False
        rtscts = False
        write_timeout = DELAY
        dsrdtr = False
        inter_byte_timeout = DELAY
        exclusive = None

        ser = serial.Serial(DEVICE, baudrate, bytesize, parity, stopbits, timeout, xonxoff, rtscts, write_timeout, dsrdtr, inter_byte_timeout, exclusive) # open a serial port

        time.sleep(DELAY)

        if ser.isOpen():
            print("Talking to Port: ",ser.name) # check the name of the port being used

            ser.flushInput() # flush input buffer, discarding all its contents

            ser.flushOutput() # flush output buffer, aborting current output and discard all that is in buffer

            # Here is where things start to go to shit
            # It can execute the write command, but the command is no recognized by the board at all
            # This means that it is not really writing and reading in the way that you expect it to
            # However, it does work with the Arduino Micro
            # R. Sheehan 30 - 11 - 2020

            ser.write(b"a0.5") # write a command to the device
            time.sleep(DELAY)

            ser.write(b"a1.5") # write a command to the device
            time.sleep(DELAY)

            ser.write(b"l") # write a command to the device
            time.sleep(DELAY)

            nbytes = 50
            count = 0
            while count < 10: 
                #data = ser.read_until(b'\n',nbytes)
                data = ser.readline() # expect this to give me back what I'm looking when I'm directly writing to the board via console
                print(data) # however, this is just returning bullshit, suspect that it is not operating in the way I expect, will try VISA instead
                count = count + 1 

            ser.close() # close the serial port
        else:
            ERR_STATEMENT = ERR_STATEMENT + "\nCannot open Port: " + DEVICE + "\n"
            raise Exception
    except Exception as e: 
        print(ERR_STATEMENT)
        print(e)

def VISA_Attempt_1():
    # Attempt to talk to ItsyBitsy M4 via VISA 
    # R. Sheehan 30 - 11 - 2020

    # online documentation: 
    # https://pyvisa.readthedocs.io/en/latest/
    
    FUNC_NAME = ".VISA_Attempt()" # use this in exception handling messages
    ERR_STATEMENT = "Error: " + MOD_NAME_STR + FUNC_NAME

    try:
        DELAY = 1 # timed delay in units of seconds
        TIMEOUT = 1000 * 60 # timeout, seemingly has be in milliseconds
        rm = pyvisa.ResourceManager() # determine the addresses of the devices attached to the PC
        if rm.list_resources():
            # Make a list of the devices attached to the PC
            print("The following devices are connected: ")
            print(rm.list_resources())

            # Create an instance of the instrument at a particular address
            #instr = rm.open_resource(rm.list_resources()[0], open_timeout = TIMEOUT)
            instr = rm.open_resource('COM37')
            #instr.read_termination = '\n'
            #instr.write_termination = '\n'
            time.sleep(DELAY)
            print(instr)
            
            count_lim = 3           
            volt_lim = 2.6
            volt = 1.0            
            while volt < volt_lim:
                # Write a command to that instrument
                cmd_str = "a%(v1)0.2f"%{"v1":volt}
                print(cmd_str)                 
                
                instr.write(cmd_str)
                time.sleep(3*DELAY)

                count = 0
                while count < count_lim:
                    # read data from the instrument
                    instr.write('l')
                    time.sleep(DELAY)
                    print(count, instr.read()) # the syncing of the read command is all fucked up, i don't know what's going on
                    #print(count, ",", instr.query('l') )
                    time.sleep(DELAY)
                    count = count + 1

                volt = volt + 0.5

            print("Closing instrument")

            # clear the buffers on the device
            volt = 0
            cmd_str = "a%(v1)0.2f"%{"v1":volt}
            instr.write(cmd_str)
            instr.clear() # not sure if this is configured for the IBM4 so leave it out for now

            # close the device
            instr.close()
        else:
            ERR_STATEMENT = ERR_STATEMENT + "\nNo devices connected"; 
            raise Exception
    except Exception as e: 
        print(ERR_STATEMENT)
        print(e)

def VISA_Attempt_2(voltage):
    # Attempt to talk to ItsyBitsy M4 via VISA 
    # R. Sheehan 30 - 11 - 2020

    # When you call a read command the fucking thing goes back to start of the buffer or something
    
    FUNC_NAME = ".VISA_Attempt()" # use this in exception handling messages
    ERR_STATEMENT = "Error: " + MOD_NAME_STR + FUNC_NAME

    try:
        DELAY = 1 # timed delay in units of seconds
        TIMEOUT = 1000 * 60 # timeout, seemingly has be in milliseconds
        rm = pyvisa.ResourceManager() # determine the addresses of the devices attached to the PC
        if rm.list_resources():
            # Make a list of the devices attached to the PC
            print("The following devices are connected: ")
            print(rm.list_resources())

            # Create an instance of the instrument at a particular address
            instr = rm.open_resource(rm.list_resources()[0], open_timeout = TIMEOUT)
            #instr.read_termination = '\n'
            #instr.write_termination = '\n'
            time.sleep(DELAY)
            print(instr)

            cmd_str = "a%(v1)0.2f"%{"v1":voltage}
            instr.write(cmd_str)
            time.sleep(DELAY)
            count = 0
            count_lim = 10
            while count < count_lim:
                instr.write("l")
                time.sleep(DELAY)
                print(count,",",instr.read())
                count = count + 1
            
            # trying to simulate what the actual terminal looks like
            #buf_list = []
            #count = 0
            #run_loop = True
            #while run_loop:
            #    print("Enter a command: ")
            #    cmd_str = input()
            #    if cmd_str == 'exit':
            #        run_loop = False
            #    elif cmd_str.startswith("l"):
            #        instr.write(cmd_str)
            #        time.sleep(DELAY) 
            #        data = instr.read()
            #        buf_list.append(data)
            #        print(count,",",data)
            #    else:
            #        instr.write(cmd_str)
            #        time.sleep(DELAY) 

            # One way to make this work will be to proceed as follows
            # 1 open comms
            # 2 write voltage
            # 3 perform multiple reads
            # 4 save buffer data
            # 5 close comms
            # 6 process data
            # goto 1

            print("Closing instrument")

            # clear the buffers on the device
            #instr.clear() # not sure if this is configured for the IBM4 so leave it out for now

            # close the device
            instr.close()

            #for i in range(0, len(buf_list), 1):
            #    print(i,",",buf_list[i])

        else:
            ERR_STATEMENT = ERR_STATEMENT + "\nNo devices connected"; 
            raise Exception
    except Exception as e: 
        print(ERR_STATEMENT)
        print(e)

def Linear_Sweep(addr, src_chn, read_chn, v_strt, v_end, n_steps):
    
    # Enable the microcontroller to perform a linear sweep of measurements
    # start at v_strt, set voltage, read inputs, format inputs, increment_voltage, plot results
    # addr is the address of the device performing the measurement
    # src_chn is the channel being used as a voltage source
    # read_chn is the list of channel being used to read the voltages from the circuit
    # v_strt is the initial voltage
    # v_end is the final voltage
    # n_steps is the number of voltage steps
    # caveat emptor n_steps is constrained by fact that smallest voltage increment is 0.1V
    # R. Sheehan 14 - 5 - 2024

    pass

def main():
    pass

if __name__ == '__main__':
    main()

    pwd = os.getcwd() # get current working directory

    print(pwd)

    #Serial_Attempt()

    VISA_Attempt_1()

    #VISA_Attempt_2(2.0)

    #VISA_Attempt_2(3.0)

    #VISA_Attempt_2(0.0)

    
