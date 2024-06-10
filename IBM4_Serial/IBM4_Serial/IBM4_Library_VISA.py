"""
Python library for interacting with the IBM4 using VISA
Assumes that the IBM4 is configured with the correct UCC source code and that serial comms have been established
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

MOD_NAME_STR = "IBM4_library_VISA"

# Dictionaries for the Read, Write Channels
Read_Chnnls = {"A2":0, "A3":1, "A4":2, "A5":3, "D2":4}
Write_Chnnls = {"A0":0, "A1":1}

# Comms Signal Value
COMMS = False

# Timed Delay Value
# It can often be useful for there to be a known finite delay between the sending of a write command
# and observing its effect on the DUT
DELAY = 1 # delay value in units of seconds

VMAX = 3.4 # Strict upper bound for Analog output voltage

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
                
                # Some issues around opening the resource that need to be addressed
                # LabVIEW and PUTTY work no problem, 
                # Issue with the VISA setup of the device. 
                # What's going on? 
                # R. Sheehan 28 - 5 - 2024
                # Do you need to open and close it as a serial device first, then open it as a VISA resource? 
                # FHP has apparently solved this problem
                # 4 - 6 - 2024
                
                #instr.read_termination = '\n'
                #instr.write_termination = '\n'
                time.sleep(DELAY)
                if instr is not None:
                    instr.query('*IDN')
                    str_val = instr.read()
                    if "ISBY" in str_val:
                        print('Opened comms:',instr.resource_name)
                        return instr # return the instr object so that it can be referenced elsewhere
                        break
                else:
                    continue
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
            #instr.read_termination = '\n'
            #instr.write_termination = '\n'
            
            time.sleep(DELAY)
            
            if instr is not None:
                instr.query('*IDN')
                str_val = instr.read()
                if "ISBY" in str_val:
                    print('Opened comms:',instr.resource_name)
                    instr.write('a0') # zero both outputs before proceeding
                    instr.write('b0')
                    instr.clear() # clear the IBM4 buffer
                    return instr # return the instr object so that it can be referenced elsewhere
                else:
                    ERR_STATEMENT = ERR_STATEMENT + '\nDevice: ' + dev_addr + ' is not correctly configured'
                    raise Exception
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

def Read_Single_Chnnl(instrument_obj, input_channel, no_averages, loud = False):
    
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
            #read_cmd = 'Average%(v1)d:%(v2)d'%{"v1":Read_Chnnls[input_channel], "v2":no_averages}
            #print(instrument_obj.query(read_cmd))
            #time.sleep(1)
            #print(instrument_obj.read())
            instrument_obj.query(read_cmd) # send the read command to the device
            read_result = instrument_obj.read() # read the result of the read command
            vals = re.findall(r'[-+]?\d+[\.]?\d*', read_result) # parse the numeric values of read_result into a list                                 
            if loud: 
                print(read_result)
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

def Read_All_Chnnl(instrument_obj, no_averages = 10, loud = False):
    
    # This method interfaces with the IBM4 to perform an averaging read operation on all read channels
    # returns a list of voltage readings at each analog input channel [A2, A3, A4, A5, D2]

    # instrument_obj is the open visa resource connected to dev_addr
    # no_averages is the number of averages to perform on each voltage reading

    FUNC_NAME = ".Read_All_Chnnl()" # use this in exception handling messages
    ERR_STATEMENT = "Error: " + MOD_NAME_STR + FUNC_NAME

    try:
        c1 = True if instrument_obj is not None else False # confirm that the intstrument object has been instantiated
        c3 = True if no_averages > 3 and no_averages < 103 else False # confirm that no. averages being taken is a sensible value
        
        c10 = c1 and c3 # if all conditions are true then write can proceed
        
        if c10:
            read_vals = numpy.array([]) # instantiate an empty numpy array
            for item in Read_Chnnls:
                value = Read_Single_Chnnl(instrument_obj, item, no_averages, loud)
                read_vals = numpy.append(read_vals, value)
                if loud: print('Voltages at AI: ',read_vals)
            return read_vals
        else:
            if not c1:
                ERR_STATEMENT = ERR_STATEMENT + '\nCould not read from instrument\nNo comms established'
            if not c3:
                ERR_STATEMENT = ERR_STATEMENT + '\nCould not read from instrument\nno_averages outside range [3, 103]'
            raise Exception
    except Exception as e:
        print(ERR_STATEMENT)
        print(e)

def Diff_Read(instrument_obj, pos_channel, neg_channel, no_averages, loud = False):

    # This VI interfaces with the IBM4 to perform a differential read operation.
    # The input channels must be between 0 and 4, and the number of readings to be averaged should be greater than zero. 
    # At some point the number of readings will be too high and will cause a timeout error. This should only happen for numbers 
    # larger than 10000. The output will be a single Voltage (floating point) value representing the average of the multiple readings.
    
    # instrument_obj is the open visa resource connected to dev_addr
    # pos_channel is one of A2, A3, A4, A5, D2
    # neg_channel is one of A2, A3, A4, A5, D2, accepting that it is not the same as pos_channel    
    # no_averages is the num. of readings that are to be averaged

    FUNC_NAME = ".Diff_Read()" # use this in exception handling messages
    ERR_STATEMENT = "Error: " + MOD_NAME_STR + FUNC_NAME
    
    try:
        c1 = True if instrument_obj is not None else False # confirm that the intstrument object has been instantiated
        c2 = True if pos_channel in Read_Chnnls else False # confirm that the positive channel label is correct
        c3 = True if neg_channel in Read_Chnnls else False # confirm that the positive channel label is correct
        c4 = True if neg_channel != pos_channel else False # confirm that the positive channel label is correct
        c5 = True if no_averages > 2 and no_averages < 104 else False # confirm that no. averages being taken is a sensible value
        
        c10 = c1 and c2 and c3 and c4 and c5 # if all conditions are true then write can proceed
        if c10:
            read_cmd = 'Diff_Read%(v1)d:%(v2)d:%(v3)d\n'%{"v1":Read_Chnnls[pos_channel], "v2":Read_Chnnls[neg_channel], "v3":no_averages}
            instrument_obj.query(read_cmd) # send the read command to the device
            read_result = instrument_obj.read() # read the result of the read command
            vals_str = re.findall(r'[-+]?\d+[\.]?\d*', read_result) # parse the numeric values of read_result into a list of strings
            #vals_flt = [float(x) for x in vals_str] # convert the list of strings to floats, save as a list
            vals_flt = numpy.float_(vals_str) # convert the list of strings to floats using numpy, save as numpy array (better)
            if loud: 
                print(read_result)
                print(vals_flt) # print the parsed values
            instrument_obj.clear() # clear the IBM4 buffer after each read            
            vals_mean = numpy.mean(vals_flt) # compute the average of all the diff_reads
            vals_delta = 0.5*( numpy.max(vals_flt) - numpy.min(vals_flt) ) # compute the range of the diff_read
            return [vals_mean, vals_delta, vals_flt] # return the relevant numerical values
        else:
            if not c1:
                ERR_STATEMENT = ERR_STATEMENT + '\nCould not read from instrument\nNo comms established'
            if not c2:
                ERR_STATEMENT = ERR_STATEMENT + '\nCould not read from instrument\npos_channel outside range {A0, A1}'
            if not c3:
                ERR_STATEMENT = ERR_STATEMENT + '\nCould not read from instrument\npos_channel outside range {A0, A1}'
            if not c4:
                ERR_STATEMENT = ERR_STATEMENT + '\nCould not read from instrument\npos_channel cannot be the same as neg_channel'
            if not c5:
                ERR_STATEMENT = ERR_STATEMENT + '\nCould not read from instrument\nno_averages outside range [3, 103]'
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
        c3 = True if set_voltage >= 0.0 and set_voltage < VMAX else False # confirm that the set voltage value is in range
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

def Write_PWM(instrument_obj, percentage):
    
    # This method interfaces with the IBM4 to set a pulse wave modulated (PWM) output signal.
    # The output Pin# must be: 5,7,9,10-13.
    # The PWM output must be between 0 and 100, and is a floating point value.
    
    # instrument_obj is the open visa resource connected to dev_addr
    # percentage must be in the range [0.0, 100]

    FUNC_NAME = ".PWM()" # use this in exception handling messages
    ERR_STATEMENT = "Error: " + MOD_NAME_STR + FUNC_NAME

    try:
        c1 = True if instrument_obj is not None else False # confirm that the intstrument object has been instantiated
        c3 = True if percentage >= 0 and percentage < 101 else False # confirm that no. averages being taken is a sensible value
        
        c10 = c1 and c3 # if all conditions are true then write can proceed
        if c10:
            output_channel = 9 # when using the IBM4 enhancement board the PWM is fixed to D9
            write_cmd = 'PWM%(v1)d:%(v2)d'%{"v1":output_channel, "v2":percentage}
            instrument_obj.write(write_cmd)
            time.sleep(DELAY)
            instrument_obj.clear()
        else:
            if not c1:
                ERR_STATEMENT = ERR_STATEMENT + '\nCould not write to instrument\nNo comms established'
            if not c3:
                ERR_STATEMENT = ERR_STATEMENT + '\nCould not write to instrument\npercentage outside range [0, 100]'
            raise Exception
    except Exception as e:
        print(ERR_STATEMENT)
        print(e)
        
def Linear_Sweep(instrument_obj, output_channel, v_strt, v_end, no_steps, no_averages, loud = False):
    
    # Enable the microcontroller to perform a linear sweep of measurements using a single channel
    # start at v_strt, set voltage, read inputs, increment_voltage, return voltage readings at all inputs
    # format the voltage readings after the fact
    
    # instrument_obj is the device performing the measurement
    # output_channel is the channel being used as a voltage source
    # v_strt is the initial voltage
    # v_end is the final voltage
    # no_steps is the number of voltage steps
    # caveat emptor no_steps is constrained by fact that smallest voltage increment is 0.1V
    # R. Sheehan 30 - 5 - 2024

    FUNC_NAME = ".Linear_Sweep()" # use this in exception handling messages
    ERR_STATEMENT = "Error: " + MOD_NAME_STR + FUNC_NAME

    try:
        delta_v_min = 0.01 # smallest reliable voltage increment for IBM4 is 10mV
        
        c1 = True if instrument_obj is not None else False # confirm that the intstrument object has been instantiated
        c2 = True if output_channel in Write_Chnnls else False # confirm that the output channel label is correct             
        c3 = True if v_strt >= 0.0 and v_strt < v_end else False # confirm that the voltage sweep bounds are in range
        c4 = True if v_end > v_strt and v_end < VMAX else False # confirm that the voltage sweep bounds are in range
        c5 = True if (v_end - v_strt) > delta_v_min else False # confirm that the voltage sweep bounds are in range
        c6 = True if no_steps > 2 else False # confirm that the no. of steps is appropriate
        c7 = True if no_averages > 3 and no_averages < 103 else False # confirm that no. averages being taken is a sensible value
        c10 = c1 and c2 and c3 and c4 and c5 and c6 and c7
        
        if c10:
            # Proceed with the single channel linear voltage sweep
            voltage_data = numpy.array([]) # instantiate an empty numpy array to store the sweep data
            delta_v = max( (v_end - v_strt) / float(no_steps - 1), delta_v_min) # Determine the sweep voltage increment, this is bounded below by delta_v_min
            v_set = v_strt # initialise the set-voltage
            # perform the sweep
            print('Sweeping voltage on Analog Output: ',output_channel)
            count = 0
            while v_set < v_end:
                step_data = numpy.array([]) # instantiate an empty numpy array to hold the data for each step of the sweep
                Write_Single_Chnnl(instrument_obj, output_channel, v_set) # set the voltage at the analog output channel
                time.sleep(0.25*DELAY) # Apply a fixed delay
                chnnl_values = Read_All_Chnnl(instrument_obj, no_averages, loud) # read the averaged voltages at all analog input channels
                # save the data
                step_data = numpy.append(step_data, v_set) # store the set-voltage value for this step
                step_data = numpy.append(step_data, chnnl_values) # store the  measured voltage values from all channels for this step
                # store the  set-voltage and the measured voltage values from all channels for this step
                # use append on the first step to initialise the voltage_data array
                # use vstack on subsequent steps to build up the 2D array of data
                voltage_data = numpy.append(voltage_data, step_data) if count == 0 else numpy.vstack([voltage_data, step_data])
                v_set = v_set + delta_v # increment the set-voltage
                count = count + 1 if count == 0 else count # only need to increment count once to build up the array
            print('Sweep complete')
            return voltage_data
        else:
            if not c1:
                ERR_STATEMENT = ERR_STATEMENT + '\nCould not write to instrument\nNo comms established'
            if not c2:
                ERR_STATEMENT = ERR_STATEMENT + '\nCould not write to instrument\noutput_channel outside range {A0, A1}'
            if not c3 or not c4 or not c5:
                ERR_STATEMENT = ERR_STATEMENT + '\nCould not write to instrument\nvoltage sweep bounds not appropriate for range [0.0, 3.3)'
            if not c6:
                ERR_STATEMENT = ERR_STATEMENT + '\nCould not write to instrument\nn_steps not defined correctly'
            if not c7:
                ERR_STATEMENT = ERR_STATEMENT + '\nCould not write to instrument\nn_averages not defined correctly'
            raise Exception        
    except Exception as e:
        print(ERR_STATEMENT)
        print(e)

def Multimeter_Mode(instrument_obj):
    
    # Method for interfacing to the IBM4 and using it as a digitial multimeter
    # Output voltage from the Analog outs, Read voltage from the Analog inputs
    # Switch the PWM output On / Off as required
    # Perform differential measurements
    # It will be assumed that comms to the device is open
    # R. Sheehan 31 - 5 - 2024

    FUNC_NAME = ".Multimeter_Mode()" # use this in exception handling messages
    ERR_STATEMENT = "Error: " + MOD_NAME_STR + FUNC_NAME

    try:
        if instrument_obj is not None:
            # Simple menu allows you to operate the IBM4 continuously
            
            # Start do-while loop to process the multimeter options
            do = True        
            while do: 
                action = int( input( multimeter_prompt() ) )
                if action == -1:
                    print('\nEnd Program\n')
                    do = False
                elif action == 1:
                    idn_prompt(instrument_obj)
                    continue
                elif action == 2:
                    volt_output_prompt(instrument_obj, 'A0')
                    continue
                elif action == 3:
                    volt_output_prompt(instrument_obj, 'A1')
                    continue
                elif action == 4:
                    pwm_output_prompt(instrument_obj)
                    continue
                elif action == 5:
                    zero_IBM4(instrument_obj)
                    continue
                elif action == 6:
                    read_inputs_prompt(instrument_obj)
                    continue
                elif action == 7:
                    diff_read_prompt(instrument_obj)
                    continue
                else:
                    #action = int(input(prompt)) # don't make this call here, otherwise prompt for input is executed twice
                    continue
        else:
            ERR_STATEMENT = ERR_STATEMENT + '\nCould not write to instrument\nNo comms established'
            raise Exception
    except Exception as e:
        print(ERR_STATEMENT)
        print(e)
        
def multimeter_prompt():
    # text processing for the multimeter mode prompt
    
    # Define options for menu
    start = 'Options for IBM4 Multimeter Mode:\n';
    option1 = 'Identify Device = 1\n'; # Query *IDN
    option2 = 'Set Analog Output A0 = 2\n'; # Set voltage at A0
    option3 = 'Set Analog Output A1 = 3\n'; # Set voltage at A1
    option4 = 'Set PWM = 4\n'; # Set PWM 
    option5 = 'Re-Set Analog Outputs = 5\n'; # Gnd all outputs
    option6 = 'Read All Analog Inputs = 6\n'; # Read voltages at each of the Analog inputs
    option7 = 'Perform Differential Measurement = 7\n'; # Perform differential voltage measurement
    option8 = 'End program Input = -1\n';
    message = 'Input: ';
    newline = '\n';
    prompt = newline + start + option1 + option2 + option3 + option4 + option5 + option6 + option7 + option8 + message
    
    return prompt

def idn_prompt(instrument_obj):
    # perform the *IDN action
    # R. Sheehan 4 - 6-  2024    
    instrument_obj.query('*IDN')
    str_val = instrument_obj.read()
    if "ISBY" in str_val:
        print('\nCurrent Device:',instrument_obj.resource_name)
    instrument_obj.clear()

def volt_output_prompt(instrument_obj, output_channel):
    # Method for requesting the user input a voltage value to output from some channel
    # R. Sheehan 4 - 6 - 2024

    print('\nSet Analog Output %(v1)s'%{"v1":output_channel})
    axvolt = float(input('Enter a voltage value: '))
    Write_Single_Chnnl(instrument_obj, output_channel,axvolt)
    
def zero_IBM4(instrument_obj):
    # zero both analog output channels
    # R. Sheehan 4 - 6-  2024
    print('\nRe-Set Analog Outputs\n')
    Write_Single_Chnnl(instrument_obj, 'A0', 0.0)
    Write_Single_Chnnl(instrument_obj, 'A1', 0.0)
    
def read_inputs_prompt(instrument_obj):
    
    print('\nRead All Analog Inputs')
    ch_vals = Read_All_Chnnl(instrument_obj, 10)
    print('AI voltages: ',ch_vals)
    
def pwm_output_prompt(instrument_obj):
    # Method for getting the IBM4 to output PWM signal
    # R. Sheehan 4 - 6 - 2024

    print('\nSet PWM Output')
    pwmval = int( input( 'Enter PWM percentage: ' ) )
    Write_PWM(instrument_obj, pwmval)
    
def diff_read_prompt(instrument_obj):
    
    print('\nPerform Differential Measurement')
    pos_chn = str( input('Enter pos-chan: ') )
    neg_chn = str( input('Enter neg-chan: ') )
    n_ave = int( input('Enter no. averages: ') )
    diff_res = Diff_Read(instrument_obj, pos_chn, neg_chn, n_ave)
    print('Differential Read Value = %(v1)0.3f +/- %(v2)0.3f'%{"v1":diff_res[0], "v2":diff_res[1]})