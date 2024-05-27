"""
Python library for interacting with the IBM4
Assumes that the IBM4 is configured with the correct UCC source code
This module replicates the existing code that was written for LabVIEW by Frank Peters
R. Sheehan 27 - 5 - 2024
"""

# Some notes on python writing style, not rigourously adhered to
# https://peps.python.org/pep-0008/

# import required libraries
import serial
import pyvisa
import time
import numpy
import re

MOD_NAME_STR = "IBM4_library"

# Dictionaries for the Read, Write Channels
Read_Chnnls = {"A2":0, "A3":1, "A4":2, "A5":3, "D2":4}
Write_Chnnls = {"A0":0, "A1":1}

# Comms Signal Value
COMMS = False

# Timed Delay Value
# It can often be useful for there to be a known finite delay between the sending of a write command
# and observing its effect on the DUT
DELAY = 1 # delay value in units of seconds

def Find():
    
    # This method searches for the first available IBM4 and then opens it.
    # If the code returns an error, then there are no IBM4s available with the correct UCC source code.

    FUNC_NAME = ".Find()" # use this in exception handling messages
    ERR_STATEMENT = "Error: " + MOD_NAME_STR + FUNC_NAME

    try:
        rm = pyvisa.ResourceManager() # determine the addresses of the devices attached to the PC
        
        if rm.list_resources() is not None:
            print("No. connected devices: ",len(rm.list_resources()))
            print("The following devices are connected: ")
            print(rm.list_resources())
            print('')
            DELAY = 1 # timed delay in units of seconds            
            TIMEOUT = 1000 * 60 # timeout, seemingly has to be in milliseconds
            for x in rm.list_resources():
                instr = rm.open_resource(x, open_timeout=TIMEOUT)
                time.sleep(DELAY)
                if instr is not None:
                    instr.query('*IDN')
                    str_val = instr.read()
                    if "ISBY" in str_val:
                        print('Opened comms:',instr.resource_name)
                        return instr # return the instr object so that it can be referenced elsewhere
                        break
        else:
            ERR_STATEMENT = ERR_STATEMENT + '\nCannot find any IBM4 attached to PC'
            raise Exception
    except Exception as e:
        print(ERR_STATEMENT)
        print(e)

def Open_Comms(dev_addr):
    
    # This method is used to open the IBM4 (Itsybitsy M4). This should always be the first method called, when communicating with the IBM4. 
    # The COM Port must be the correct one for the IBM4, or else an error will be returned. In addition, if the IBM4 has not been 
    # loaded with the correct Circuit Python code, an error will also be generated.
    # If a properly configured IBM4 exists at that port, then an instrument object for the IBM4 will be returned
    # Remember to also close the device at the end of a session. 
    # If this is not done, you may need to reboot your computer to free up resources.
    
    # dev_addr is the address of the IBM4 attached to the PC

    FUNC_NAME = ".Open_Comms()" # use this in exception handling messages
    ERR_STATEMENT = "Error: " + MOD_NAME_STR + FUNC_NAME

    try:
        rm = pyvisa.ResourceManager() # determine the addresses of the devices attached to the PC
        
        if rm.list_resources() is not None:
            DELAY = 1 # timed delay in units of seconds            
            TIMEOUT = 1000 * 60 # timeout, seemingly has to be in milliseconds
            
            instr = rm.open_resource(dev_addr, open_timeout = TIMEOUT) # opens comms
            
            time.sleep(DELAY)
            
            if instr is not None:
                print('Opened comms:',dev_addr)
                
                instr.write('a0') # zero both outputs before proceeding
                instr.write('b0')
                instr.clear() # clear the IBM4 buffer
                
                return instr # return the instr object so that it can be referenced elsewhere
            else:
                ERR_STATEMENT = ERR_STATEMENT + '\nCould not open comms to: ' + dev_addr
                raise Exception
        else:
            ERR_STATEMENT = ERR_STATEMENT + '\nCannot find any IBM4 attached to PC'
            raise Exception
    except Exception as e:
        print(ERR_STATEMENT)
        print(e)

def Close_Comms(instrument_obj):
    
    # This method is used to close the IBM4. This should always be the last method called. 
    # If it is neglected, your computer may run out of resources, and eventually you will not be able to connect to the IBM4. 
    # This can sometimes be rectifies by calling this method repeatedly. Otherwise, you may need to reboot your computer.
    # For proper operation, the input COM port must be one that has previously been opened by the method Open_Comms.
    
    # instrument_obj is the open visa resource connected to dev_addr

    FUNC_NAME = ".Close_Comms()" # use this in exception handling messages
    ERR_STATEMENT = "Error: " + MOD_NAME_STR + FUNC_NAME

    try:
        if instrument_obj is not None:
            dev_name = instrument_obj.resource_name
            instrument_obj.write('a0') # zero both outputs before closing
            instrument_obj.write('b0')
            instrument_obj.clear()
            instrument_obj.close()            
            print('Closed comms:',dev_name)
        else:
            ERR_STATEMENT = ERR_STATEMENT + '\nCould not close comms'
            raise Exception
    except Exception as e:
        print(ERR_STATEMENT)
        print(e)

def Read_Single_Chnnl(instrument_obj, input_channel, no_averages):
    
    # This method interfaces with the IBM4 to perform a read operation on a single read channel
    # The input channel must be between 0 and 3, And the number of readings should be greater than zero. 
    # At some point the number of reading will be too high and will cause a timeout error. This should 
    # only happen for numbers larger than 10000. The output will be a single Voltage (floating point) value representing the average of the multiple readings.
    # Alternate read operations exist covering binary or floating point, single reading, multiple readings, and an average of multiple readings (floating point only).
    
    # instrument_obj is the open visa resource connected to dev_addr
    # input_channel is one of A2, A3, A4, A5, D2
    # no_averages is the num. of readings that are to be averaged
    
    # Python nonsense
    # Use of vals = re.findall("[-+]?\d+[\.]?\d*", instrument_obj.read()) throws an error in Python 3.12
    # SyntaxWarning: invalid escape sequence '\d' vals = re.findall("[-+]?\d+[\.]?\d*", instrument_obj.read())
    # Explanation given here, use of \d will not be allowed in future versions of python so fix the problem now
    # https://stackoverflow.com/questions/77531208/python3-12-syntaxwarning-on-triplequoted-string-d-must-be-d
    # https://stackoverflow.com/questions/57645829/why-am-i-getting-a-syntaxwarning-invalid-escape-sequence-s-warning
    # https://stackoverflow.com/questions/50504500/deprecationwarning-invalid-escape-sequence-what-to-use-instead-of-d
    # Solution is to use vals = re.findall(r'[-+]?\d+[\.]?\d*', instrument_obj.read()) instead, tell the interpreter to view the regex cmd as a raw string
    # Alternatively use vals = re.findall('[-+]?\\d+[\\.]?\\d*', instrument_obj.read()), but this is less like true regex so use the other way
    # R. Sheehan 27 - 5 - 2024

    FUNC_NAME = ".Read_Single_Chnnl()" # use this in exception handling messages
    ERR_STATEMENT = "Error: " + MOD_NAME_STR + FUNC_NAME

    try:
        c1 = True if instrument_obj is not None else False # confirm that the intstrument object has been instantiated
        c2 = True if input_channel in Read_Chnnls else False # confirm that the input channel label is correct
        c3 = True if no_averages > 2 and no_averages < 104 else False # confirm that no. averages being taken is a sensible value
        
        c10 = c1 and c2 and c3 # if all conditions are true then write can proceed
        
        if c10:
            read_cmd = 'Average%(v1)d:%(v2)d\n'%{"v1":Read_Chnnls[input_channel], "v2":no_averages}
            instrument_obj.query(read_cmd) # send the read command to the device
            read_result = instrument_obj.read() # read the result of the read command
            vals = re.findall(r'[-+]?\d+[\.]?\d*', read_result) # parse the numeric values of read_result into a list            
            #print(read_result)                        
            print(vals) # print the parsed values
            instrument_obj.clear() # clear the IBM4 buffer after each read
            return float(vals[1]) # return the relevant numerical value
        else:
            if not c1:
                ERR_STATEMENT = ERR_STATEMENT + '\nCould not read from instrument\nNo comms established'
            if not c2:
                ERR_STATEMENT = ERR_STATEMENT + '\nCould not read from instrument\ninput_channel outside range {A0, A1}'
            if not c3:
                ERR_STATEMENT = ERR_STATEMENT + '\nCould not read from instrument\nno_averages outside range [3, 103]'
            raise Exception
    except Exception as e:
        print(ERR_STATEMENT)
        print(e)

def Read_All_Chnnl(instrument_obj, no_averages):
    
    # This method interfaces with the IBM4 to perform an averaging read operation on all read channels

    # instrument_obj is the open visa resource connected to dev_addr

    FUNC_NAME = ".Read_All_Chnnl()" # use this in exception handling messages
    ERR_STATEMENT = "Error: " + MOD_NAME_STR + FUNC_NAME

    try:
        c1 = True if instrument_obj is not None else False # confirm that the intstrument object has been instantiated
        c3 = True if no_averages > 3 and no_averages < 103 else False # confirm that no. averages being taken is a sensible value
        
        c10 = c1 and c3 # if all conditions are true then write can proceed
        
        if c10:
            read_vals = [] # list for storing the values at each analog input
            for item in Read_Chnnls:
                value = Read_Single_Chnnl(instrument_obj, item, no_averages)
                read_vals.append(value)
            print('Voltages at AI: ',read_vals)
        else:
            if not c1:
                ERR_STATEMENT = ERR_STATEMENT + '\nCould not read from instrument\nNo comms established'
            if not c3:
                ERR_STATEMENT = ERR_STATEMENT + '\nCould not read from instrument\nno_averages outside range [3, 103]'
            raise Exception
    except Exception as e:
        print(ERR_STATEMENT)
        print(e)

def Diff_Read():

    # This VI interfaces with the IBM4 to perform a differential read operation.
    # The input channels must be between 0 and 4, and the number of readings to be averaged should be greater than zero. 
    # At some point the number of readings will be too high and will cause a timeout error. This should only happen for numbers 
    # larger than 10000. The output will be a single Voltage (floating point) value representing the average of the multiple readings.

    FUNC_NAME = ".Diff_Read()" # use this in exception handling messages
    ERR_STATEMENT = "Error: " + MOD_NAME_STR + FUNC_NAME
    
    try:
        pass
    except Exception as e:
        print(ERR_STATEMENT)
        print(e)

def Write_Single_Chnnl(instrument_obj, output_channel, set_voltage = 0.0):
    
    # This method interfaces with the IBM4 to perform a write operation where a Voltage is output on one of the analog output pins of the IBM4.
    # The output channel must be 0 or 1, while the output value should be specified in Volts (thus, floating point)

    # output_channel is one of A0, A1
    # set_voltage is the desired voltage output value from the channel
    # set_voltage must be in the range [0.0, 3.3)

    FUNC_NAME = ".Write_Single_Chnnl()" # use this in exception handling messages
    ERR_STATEMENT = "Error: " + MOD_NAME_STR + FUNC_NAME

    try:
        c1 = True if instrument_obj is not None else False # confirm that the intstrument object has been instantiated
        c2 = True if output_channel in Write_Chnnls else False # confirm that the output channel label is correct
        c3 = True if set_voltage >= 0.0 and set_voltage < 3.3 else False # confirm that the set voltage value is in range
        c10 = c1 and c2 and c3 # if all conditions are true then write can proceed
        
        if c10:
            write_cmd = 'Write%(v1)d:%(v2)0.2f'%{"v1":Write_Chnnls[output_channel], "v2":set_voltage}
            instrument_obj.write(write_cmd)
            time.sleep(DELAY)
            instrument_obj.clear()
        else:
            if not c1:
                ERR_STATEMENT = ERR_STATEMENT + '\nCould not write to instrument\nNo comms established'
            if not c2:
                ERR_STATEMENT = ERR_STATEMENT + '\nCould not write to instrument\noutput_channel outside range {A0, A1}'
            if not c3:
                ERR_STATEMENT = ERR_STATEMENT + '\nCould not write to instrument\nset_voltage outside range [0.0, 3.2]'
            raise Exception
    except Exception as e:
        print(ERR_STATEMENT)
        print(e)

def PWM():
    
    # This method interfaces with the IBM4 to set a pulse wave modulated (PWM) output signal.
    # The output Pin# must be: 5,7,9,10-13.
    # The PWM output must be between 0 and 100, and is a floating point value.

    FUNC_NAME = ".PWM()" # use this in exception handling messages
    ERR_STATEMENT = "Error: " + MOD_NAME_STR + FUNC_NAME

    try:
        pass
    except Exception as e:
        print(ERR_STATEMENT)
        print(e)