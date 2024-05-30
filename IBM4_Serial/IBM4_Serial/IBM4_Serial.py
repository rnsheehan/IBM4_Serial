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

# Notes on do-while equivalent in Python
# https://stackoverflow.com/questions/743164/how-to-emulate-a-do-while-loop
# Also take a look at your MATLAB code for Thorlabs CLD1015
# R. Sheehan 27 - 5 - 2024

import serial # import the pySerial module pip install pyserial
import pyvisa
import time
import numpy

import IBM4_Library

MOD_NAME_STR = "IBM4_Serial"
HOME = False
USER = 'Robert' if HOME else 'robertsheehan/OneDrive - University College Cork/Documents'

def Serial_Attempt():

    # After checking again it seems that Serial comms to IBM4 via python does not work
    # Python can open and close the serial channel
    # However, writing commands to the IBM4 has no effect other than printing the command on the device buffer
    # Stick with VISA
    # R. Sheehan 14 - 5 - 2024
    
    # This may be because you're not configuring the serial open correctly
    # R. Sheehan 28 - 5 - 2024

    # Attempting to communicate with the ItsyBitsy M4 via Serial comms
    # It isn't really working, but it seems to work fine with the Arduino Micro
    # Going to try VISA comms instead
    # R. Sheehan 30 - 11 - 2020

    # Online documentation
    # https://pyserial.readthedocs.io/en/latest/shortintro.html 
    # https://pyserial.readthedocs.io/en/latest/pyserial_api.html

    FUNC_NAME = ".Serial_Attempt()" # use this in exception handling messages
    ERR_STATEMENT = "Error: " + MOD_NAME_STR + FUNC_NAME

    try:
        DELAY = 1 # timed delay in units of seconds

        #DEVICE = 'COM14' # Address / Port of the device that you want to communicate with, check device manager
        DEVICE = 'COM3' # Address / Port of the device that you want to communicate with, check device manager
        
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
        
        #ser = serial.Serial()
        ser.port = DEVICE
        ser.open()

        time.sleep(DELAY)

        if ser.isOpen():
            print("Talking to Port: ",ser.name) # check the name of the port being used

            #ser.flushInput() # flush input buffer, discarding all its contents, deprecated since version 3.0 
            ser.reset_input_buffer()

            #ser.flushOutput() # flush output buffer, aborting current output and discard all that is in buffer, deprecated since version 3.0
            ser.reset_output_buffer()

            # Here is where things start to go to shit
            # It can execute the write command, but the command is no recognized by the board at all
            # This means that it is not really writing and reading in the way that you expect it to
            # However, it does work with the Arduino Micro
            # R. Sheehan 30 - 11 - 2020

            #ser.write(b"a0.0\r\n") # write a command to the device

            #ser.write(b"b0.0\r\n") # write a command to the device
            #time.sleep(DELAY)

            ser.write(b"l") # write a command to the device
            time.sleep(DELAY)
            print(ser.read_all())
            time.sleep(DELAY)
            print(ser.read_all())

            #nbytes = 50
            #count = 0
            #while count < 10: 
            #    #data = ser.read_until(b'\n',nbytes)
            #    #data = ser.readline() # expect this to give me back what I'm looking when I'm directly writing to the board via console
            #    print(count, ser.readline())
            #    print(count, ser.readline())
            #    count = count + 1 

            print('Closing serial port')
            ser.close() # close the serial port
        else:
            ERR_STATEMENT = ERR_STATEMENT + "\nCannot open Port: " + DEVICE + "\n"
            raise Exception
    except Exception as e: 
        print(ERR_STATEMENT)
        print(e)
        
def FHP_Serial():
    
    # Examination of pyserial by FHP
    # 30 - 5 - 2024

    # Configure the serial port (example configuration)
    port = 'COM4' 
    baud_rate = 9600  # Set the baud rate
    
    try:
        # Open the serial port
        #ser = serial.Serial(port, baud_rate, timeout=3, stopbits=serial.STOPBITS_ONE)
        ser = serial.Serial(port, baud_rate, timeout = 0, write_timeout = 0.5, stopbits=serial.STOPBITS_ONE) # solves the timeout issue
        
        # Check if the serial port is open
        if ser.is_open:
            print(f"Serial port {port} opened successfully.")
        else:
            print(f"Failed to open serial port {port}.") 

        # Example: Write data to the serial port
        num = ser.write(b'*IDN\r\n')
        print(f"Bytes written: {num}:")
 

       # Example: Read data from the serial port
        response = " "
        response = ser.readline()
        print(f"Received: {response}")
        
    except Exception as e: 
        print(e)

def VISA_Attempt_1():
    # Attempt to talk to ItsyBitsy M4 via VISA 
    # R. Sheehan 30 - 11 - 2020

    # online documentation: 
    # https://pyvisa.readthedocs.io/en/latest/
    # https://pyvisa.readthedocs.io/en/1.8/api/index.html

    # the documentation is not great
    # some functions being used here have no documentation at all
    
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
            print('')

            # Create an instance of the instrument at a particular address
            #instr = rm.open_resource(rm.list_resources()[1], open_timeout = TIMEOUT)
            
            DEVICE = 'COM3'
            instr = rm.open_resource(DEVICE, open_timeout = TIMEOUT)

            #instr.read_termination = '\n'
            #instr.write_termination = '\n'
            time.sleep(DELAY)

            if instr:
                print(instr)
                
                #print(instr.read_stb()) # doesn't work with IBM4
                #print(instr.read_termination)
                #pyvisa.log_to_screen()

                # zero both output channels
                instr.clear()
                
                instr.write('a0')
                instr.write('b1.5')
                instr.query('*IDN') # query doesn't work with IBM4 the way you think it should
                instr.query('Average0:10')
                #instr.query('l')
                #instr.write('*IDN') # Must do a write, followed by two reads in order to see the response of the device

                #print(instr.buffer_read()) # does not work with IBM4
                print(instr.read_raw())
                print(instr.read_raw())
                print(instr.read_raw())
                print(instr.read_raw())

                instr.clear()

                # would like a way to step through all the lines in the device buffer
                #while True:
                #    print(instr.read_bytes(1))
            
                RUN_SWEEP = False
                if RUN_SWEEP:
                    count_lim = 5       
                    volt_lim = 2.6
                    volt = 1.0            
                    while volt < volt_lim:
                        # Write a command to that instrument
                        cmd_str = "a%(v1)0.2f"%{"v1":volt}
                        print(cmd_str)                 
                
                        instr.write(cmd_str)
                        time.sleep(3*DELAY)
                        instr.clear() # clears the resource, empties the buffer presumably

                        # In order to read a single measurement it looks like you need to execute two read commands
                        # one command to read the string that holds the command string
                        # second command to read the data that is output by the device
                        # R. Sheehan 14 - 5 - 2024

                        count = 0
                        while count < count_lim:
                            # read data from the instrument
                            instr.write('l')
                                        
                            #print(count, instr.read()) # read the string that was written to the device
                            #print(count, instr.read()) # read the output from the device after the command was executed
                    
                            #print(count, ",", instr.query('l') ) # this has the same effect as instr.read(), stick with instr.read() to be less ambiguous
                            #print(count, ",", instr.query('l') ) # this has the same effect as instr.read(), stick with instr.read() to be less ambiguous

                            #print(count, instr.read('l'))
                            #print(count, instr.query_ascii_values('l')) # this has the advantage of returning a list of numerical values
                    
                            instr.query('l') # make the call to skip the line containing the command but don't bother printing it
                            print(count, instr.query_ascii_values('l', container = numpy.array)) # this has the advantage of returning a list of numerical values

                            #print(count, instr.read_raw()) # this will return the unformatted string that is printed to the device output buffer
                            #print(count, instr.read_raw()) # need to call this for each line of the buffer
                                                            
                            time.sleep(0.5*DELAY)

                            count = count + 1

                        # Attempt a different read method
                        #instr.write('l')
                        #instr.clear()
                        #values = instr.read_raw()
                        #print(values)

                        volt = volt + 0.5

                print("Closing instrument")

                # zero both output channels
                instr.write('a0')
                instr.write('b0')
                instr.clear() # clear the buffers on the device

                # close the device
                instr.close()
            else:
                ERR_STATEMENT = ERR_STATEMENT + "\nCould not open resource: " + DEVICE; 
                raise Exception
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

def IBM4_Lib_Hacking():
    
    # Testing the IBM4 library
    # R. Sheehan 27 - 5 - 2024
    
    # Some issues around opening the resource that need to be addressed
    # Comms works no problem when first opened with LabVIEW open.vi
    # Issue with the VISA setup of the device. 
    # What's going on? 
    # R. Sheehan 28 - 5 - 2024
    # Do you need to open and close it as a serial device first, then open it as a VISA resource?
    
    the_instr = IBM4_Library.Find()
    
    #dev_addr = 'COM3'
    #the_instr = IBM4_Library.Open_Comms(dev_addr)
    
    IBM4_Library.Write_Single_Chnnl(the_instr, 'A1', 1.5)
    
    #IBM4_Library.Read_Single_Chnnl(the_instr, 'A2', 10)
    # IBM4_Library.Read_Single_Chnnl(the_instr, 'A3', 10)
    # IBM4_Library.Read_Single_Chnnl(the_instr, 'A4', 10)
    # IBM4_Library.Read_Single_Chnnl(the_instr, 'A5', 10)
    # IBM4_Library.Read_Single_Chnnl(the_instr, 'D2', 10)
    
    IBM4_Library.Read_All_Chnnl(the_instr, 20)

    IBM4_Library.Close_Comms(the_instr)
    
def Sweep_Test():
    
    # Test the linear voltage sweep
    # R. Sheehan 30 - 5 - 2024
    
    the_instr = IBM4_Library.Find()

    v_start = 0.0
    v_end = 3.0
    n_steps = 5
    n_avg = 5
    the_data = IBM4_Library.Linear_Sweep(the_instr, 'A1', v_start, v_end, n_steps, n_avg)
    
    for i in range(0, len(the_data), 1):
        print(the_data[i])
    print("")
        
    # An example of how to process the data for the diode measurement
    print('Sample Processing for Diode Measurement')
    print('Vset: ',the_data[:,0]) # v-set
    print('Vset A2-Gnd', the_data[:,1]-the_data[:,3]) # v-set-measured by A2
    print('Vsense A2-A3: ', (the_data[:,1]-the_data[:,2])) # v-sense A2 - A3
    print('Isense A2-A3/Rsense: ', (the_data[:,1]-the_data[:,2])/(10.0/1000.0)) # I-sense A2 - A3 / Rsense
    print('Vdiode A3-Gnd: ', the_data[:,2]-the_data[:,3]) # v-diode A3
    print('Gnd A4: ', the_data[:,3]) # v-low gnd at A4
    print('Gnd A5: ', the_data[:,4]) # v-low gnd at A5
    print('Gnd D2: ', the_data[:,5]) # v-low gnd at D2
    
    IBM4_Library.Close_Comms(the_instr)

def main():
    pass

if __name__ == '__main__':
    main()

    pwd = os.getcwd() # get current working directory

    print(pwd)

    #Serial_Attempt()

    #VISA_Attempt_1()

    #VISA_Attempt_2(2.0)

    #VISA_Attempt_2(3.0)

    #VISA_Attempt_2(0.0)
    
    #IBM4_Lib_Hacking()
    
    Sweep_Test()