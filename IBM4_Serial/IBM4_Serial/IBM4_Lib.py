"""
Python library for interacting with the IBM4 using Serial
Assumes that the IBM4 is configured with the correct UCC circuit python source code
This module replicates the existing code that was written for LabmethodEW by Frank Peters
R. Sheehan 11 - 6 - 2024
"""

# Some notes on python writing style, not rigourously adhered to
# https://peps.python.org/pep-0008/

# For the official notes on implementation of classes in Python, see
# https://docs.python.org/3/tutorial/classes.html
# Another good source of notes is the following
# https://www.geeksforgeeks.org/python-classes-and-objects/?ref=lbp
# For notes on proper object oriented programming consult a book on C++
# I recommend ``Introducing C++ for Scientists, Engineers and Mathematicians'' by D. W. Capper

# Python does not want you to do constructor overloading
# Use if-else ladders to implement the same effect
# https://www.geeksforgeeks.org/method-and-constructor-overloading-in-python/
# or use something called classmethods
# https://docs.python.org/3/library/functions.html#classmethod
# https://stackoverflow.com/questions/141545/how-to-overload-init-method-based-on-argument-type
# https://stackoverflow.com/questions/682504/what-is-a-clean-pythonic-way-to-implement-multiple-constructors
# https://stackoverflow.com/questions/58858556/how-can-i-perform-constructor-overloading-in-python
# R. Sheehan 12 - 6 - 2024

# Python 3.X and encoding str as bytes
# https://stackoverflow.com/questions/7585435/best-way-to-convert-string-to-bytes-in-python-3
# https://www.geeksforgeeks.org/python-convert-string-to-bytes/

# Python Serial Online Documentation
# https://pyserial.readthedocs.io/en/latest/index.html
# https://pyserial.readthedocs.io/en/latest/pyserial_api.html

# Trying to give some thought as to how to correctly implement all the different read methods
# I was thinking about sophisticated OO concepts like Dynamic Binding and polymorphism
# but these are not really appropriate in this case where you have a single object with multiple types of read
# https://www.tutorialspoint.com/python/python_dynamic_binding.htm
# https://stackoverflow.com/questions/8980676/dynamically-bind-method-to-class-instance-in-python
# https://www.programiz.com/python-programming/polymorphism
# https://www.w3schools.com/python/python_polymorphism.asp

# It all comes down to method overloading which it looks like you implement using an if-else ladder
# https://stackoverflow.com/questions/10202938/how-do-i-use-method-overloading-in-python
# There is also something called Dispatch Decorators, however, I'm going to take the "Simple is better than complex" approach
# https://www.geeksforgeeks.org/python-method-overloading/
# Implement the read methods using single access function that calls protected read methods of the various types
# use protected methods because private methods can be easily accessed via name mangling
# https://www.geeksforgeeks.org/private-methods-in-python/
# https://stackoverflow.com/questions/70528/why-are-pythons-private-methods-not-actually-private
# https://stackoverflow.com/questions/11483366/protected-method-in-python
# R. Sheehan 9 - 7 - 2024

# Output formatting in python
# https://docs.python.org/3/tutorial/inputoutput.html
# https://www.geeksforgeeks.org/python-output-formatting/
# https://realpython.com/python-formatted-output/
# https://python-course.eu/python-tutorial/formatted-output.php
# R. Sheehan 10 - 7 - 2024

# import required libraries
from ast import Try
import os
import sys
import glob
import re
import serial
import time
import numpy

MOD_NAME_STR = "IBM4_Lib"

# define the class for interfacing to an IBM4

class Ser_Iface(object):
    """
    class for interfacing to an IBM4
    """
    
    # python does not want you to use constructor overloading

    # constructor
    # opens a serial link to a known serial port      
    # define default arguments inside
    def __init__(self, port_name = None, read_mode = 'DC'):
        """
        Constructor for the IBM4 Serial Interface
        
        port_name is the name of the COM port to which the IBM4 is attached
        port_name = None => PC will search for 1st available IBM4
        
        read_mode is the reading mode of the IBM4 
        read_mode = 'DC' =>  IBM4 assumes analog inputs in the range [0, 3.3)
        read_mode = 'AC' =>  IBM4 assumes analog inputs in the range [-8, +8]
        """        
        try:
            self.FUNC_NAME = ".Ser_Iface()" # use this in exception handling messages
            self.ERR_STATEMENT = "Error: " + MOD_NAME_STR + self.FUNC_NAME

            # Dictionaries for the Read, Write Channels
            self.Read_Chnnls = {"A2":0, "A3":1, "A4":2, "A5":3, "D2":4}
            self.Write_Chnnls = {"A0":0, "A1":1}
            
            # Dictionary for the Read Mode
            self.Read_Modes = {"DC":0, "AC":1}
            
            # Dictionary for Accessing the Different Read Types
            self.Read_Types = {"Single Binary":0, "Multiple Binary":1, "Single Voltage":2, "Multiple Voltage":3, "Average Voltage":4}

            # Voltage Bounding Values
            self.VMAX = 3.3 # Max output voltage from IBM4
            self.VMIN = 0.0 # Min output voltage from IBM4
            self.DELTA_VMIN = 0.01 # Min voltage increment from IBM4
            
            # # parameters to be passed to the serial open command
            self.baud_rate = 9600 # serial comms baud_rate
            self.read_timeout = 3 # timeout for reading data from the IBM4, units of second
            self.write_timeout = 0.5 # timeout for writing data to the IBM4, units of second
            self.instr_obj = None # assign a default argument to the instrument object
            
            # identify the port name
            if port_name is not None:
                self.IBM4Port = port_name # string containing the port no. of the device
            else:
                self.FindIBM4() # find the IBM4 port attached to the PC
            
            # open the serial comms link to port_name
            self.OpenComms(read_mode)
        except TypeError as e:
            print(self.ERR_STATEMENT)
            print(e)
        except serial.SerialException as e:
            print(self.ERR_STATEMENT)
            print(e)

    # destructor  
    # https://www.geeksforgeeks.org/destructors-in-python/          
    def __del__(self):
        """
        close the link to the instrument object when it goes out of scope
        """
        
        if self.IBM4Port is not None and self.instr_obj.isOpen():
            # close the link to the instrument object when it goes out of scope
            print('Closing Serial link with:',self.instr_obj.name)
            self.ZeroIBM4()
            self.instr_obj.close()
        else:
            # Do nothing, no link to IBM4 established
            pass
            
    def __str__(self):
        """
        return a string the describes the class
        """
        
        return "class for interfacing to an IBM4"
    
    def ResetBuffer(self):
        
        """
        In order to be able to sweep correctly the buffer must be reset between write, read command pairs
        """

        self.FUNC_NAME = ".ResetBuffer()" # use this in exception handling messages
        self.ERR_STATEMENT = "Error: " + MOD_NAME_STR + self.FUNC_NAME

        try:            
            # confirm that the instrument object has been instantiated
            if self.instr_obj.isOpen():
                self.instr_obj.reset_input_buffer()
                #self.instr_obj.reset_output_buffer() # this appears to have no effect
            else:
                self.ERR_STATEMENT = self.ERR_STATEMENT + '\nCould not read from instrument\nNo comms established'
                raise Exception
        except Exception as e:
            print(self.ERR_STATEMENT)
            print(e)

    def CommsStatus(self):
        """
        investigate the status of the serial comms link
        """
        
        if self.IBM4Port is not None and self.instr_obj.isOpen():
            print('Communication with:',self.instr_obj.name,' is open')
            return True
        else:
            print('Communication with: IBM4 is not open')
            return False
            
    def OpenComms(self, read_mode = 'DC'):
        """
        open a serial link to a COM port attached to an IBM4
        """
        
        self.FUNC_NAME = ".OpenComms()" # use this in exception handling messages
        self.ERR_STATEMENT = "Error: " + MOD_NAME_STR + self.FUNC_NAME

        try:
            if self.IBM4Port is not None:
                # open a serial link to a device
                self.instr_obj = serial.Serial(self.IBM4Port, self.baud_rate, timeout = self.read_timeout, write_timeout = self.write_timeout, stopbits=serial.STOPBITS_ONE)
                
                # Specify the reading mode for the IBM4
                self.SetMode(read_mode)

                # zero the analog and PWM outputs
                # this is necessary because when the IBM4 is connected the AO are set to arbitrary values
                self.ZeroIBM4()

                self.CommsStatus()
                
                self.ResetBuffer() # delete all text from the IB4 Buffer
            else:
                self.ERR_STATEMENT = self.ERR_STATEMENT + '\nNo IBM4 attached to PC'
                raise Exception
        except Exception as e:
            print(self.ERR_STATEMENT)
            print(e)
            
    def ZeroIBM4(self):
        """
        zero the analog and PWM outputs of the IBM4
        """
        
        self.FUNC_NAME = ".ZeroIBM4()" # use this in exception handling messages
        self.ERR_STATEMENT = "Error: " + MOD_NAME_STR + self.FUNC_NAME

        try:
            if self.instr_obj.isOpen():
                self.instr_obj.write(b'a0\r\n')
                self.instr_obj.write(b'b0\r\n')
                self.instr_obj.write(b'PWM9:0\r\n')
            else:
                # Do nothing, no link to IBM4 established
                pass
        except Exception as e:
            print(self.ERR_STATEMENT)
            print(e)
           
    def FindIBM4(self, loud = False):
        """
        Goes through all listed serial ports looking for an IBM4
        Once a port is found, return the port name
        FHP 30 - 5 - 2024
        """
    
        self.FUNC_NAME = self.FUNC_NAME + ".FindIBM4()" # use this in exception handling messages
        self.ERR_STATEMENT = "Error: " + MOD_NAME_STR + self.FUNC_NAME
    
        try:
            if sys.platform.startswith('win'):
                ports = ['COM%s'%(i+1) for i in range(256)]
            elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
                # this excludes your current terminal "/dev/tty"
                ports = glob.glob('/dev/tty[A-Za-z]*')
            elif sys.platform.startswith('darwin'):
                ports = glob.glob('/dev/tty.*')
            else:
                self.ERR_STATEMENT = self.ERR_STATEMENT + '\nUnsupported platform'
                raise EnvironmentError('Unsupported platform')
        
            baud_rate = 9600
        
            self.IBM4Port = None # assign IBM4Port to None 

            for port in ports:
                try:
                    if loud: print('Trying: ',port)
                    s = serial.Serial(port, baud_rate, timeout = 0.05, write_timeout = 0.1, inter_byte_timeout = 0.1, stopbits=serial.STOPBITS_ONE)
                    s.write(b'*IDN\r\n')
                    response = s.read_until('\n',size=None)
                    Code=response.rsplit(b'\r\n')
                    if len(Code) > 2:
                        #if Code[1]==b'ISBY-UCC-RevA.1':
                        # test to see if Code[1] contains 'ISBY' this is more generic
                        # will allow for updated rev. no. without necessitating a change in code
                        # Must encode the test string as bytes because Python 3.X is really pedantic
                        #print(type('ISBY')) # type str
                        #print(type(Code[1])) # type bytes
                        if b'ISBY' in Code[1]:
                            if loud: print(f'IBM4 found at {port}')
                            self.IBM4Port = port
                            s.close()
                            break # stop the search for an IBM4 at the first one you find   
                except(OSError, serial.SerialException):
                    # Ignore the errors that arise from non-IBM4 serial ports
                    pass
        except Exception as e:
            print(self.ERR_STATEMENT)
            print(e)
        except EnvironmentError as e:
            print(self.ERR_STATEMENT)
            print(e)
            
    # methods for writing data to the IBM4
    
    def SetMode(self, read_mode = 'DC'):
        """
        read_mode is the reading mode of the IBM4 
        
        Inputs: 
        read_mode = 'DC' =>  IBM4 assumes analog inputs in the range [0, 3.3)
        read_mode = 'AC' =>  IBM4 assumes analog inputs in the range [-8, +8]
        read_mode = 'AC' requires BP2UP board be used with IBM4
        """
        
        self.FUNC_NAME = ".SetMode()" # use this in exception handling messages
        self.ERR_STATEMENT = "Error: " + MOD_NAME_STR + self.FUNC_NAME

        try:
            c1 = True if self.instr_obj.isOpen() else False # confirm that the instrument object has been instantiated
            c3 = True if read_mode in self.Read_Modes else False # confirm that read_mode choice is a valid one
        
            c10 = c1 and c3 # if all conditions are true then write can proceed
            if c10:
                write_cmd = 'Mode%(v1)d\r\n'%{"v1":self.Read_Modes[read_mode]}
                self.instr_obj.write( str.encode(write_cmd) ) # when using serial str must be encoded as bytes
            else:
                if not c1:
                    self.ERR_STATEMENT = self.ERR_STATEMENT + '\nCould not write to instrument\nNo comms established'
                if not c3:
                    self.ERR_STATEMENT = self.ERR_STATEMENT + '\nCould not write to instrument\nInvalid read mode specified'
                raise Exception
        except Exception as e:
            print(self.ERR_STATEMENT)
            print(e)
    
    def WriteVoltage(self, output_channel, set_voltage = 0.0):
        
        """
        This method interfaces with the IBM4 to perform a write operation where a Voltage is output on one of the analog output pins of the IBM4.
        The output channel must be 0 or 1, while the output value should be specified in Volts (thus, floating point)

        Inputs: 
        output_channel is one of A0, A1
        set_voltage is the desired voltage output value from the channel
        set_voltage must be in the range [0.0, 3.3)
        """

        self.FUNC_NAME = ".WriteSingleChnnl()" # use this in exception handling messages
        self.ERR_STATEMENT = "Error: " + MOD_NAME_STR + self.FUNC_NAME

        try:
            c1 = True if self.instr_obj.isOpen() else False # confirm that the instrument object has been instantiated
            c2 = True if output_channel in self.Write_Chnnls else False # confirm that the output channel label is correct
            c3 = True if set_voltage >= self.VMIN and set_voltage < self.VMAX else False # confirm that the set voltage value is in range
            c10 = c1 and c2 and c3 # if all conditions are true then write can proceed
        
            if c10:
                write_cmd = 'Write%(v1)d:%(v2)0.2f\r\n'%{"v1":self.Write_Chnnls[output_channel], "v2":set_voltage}
                self.instr_obj.write( str.encode(write_cmd) ) # when using serial str must be encoded as bytes
                #time.sleep(DELAY) # no need for explicit delay, this is handled by write_timeout
                #self.ResetBuffer() # reset buffer between write, read cmd pairs
            else:
                if not c1:
                    self.ERR_STATEMENT = self.ERR_STATEMENT + '\nCould not write to instrument\nNo comms established'
                if not c2:
                    self.ERR_STATEMENT = self.ERR_STATEMENT + '\nCould not write to instrument\noutput_channel outside range {A0, A1}'
                if not c3:
                    self.ERR_STATEMENT = self.ERR_STATEMENT + '\nCould not write to instrument\nset_voltage outside range [0.0, 3.2]'
                raise Exception
        except Exception as e:
            print(self.ERR_STATEMENT)
            print(e)
    
    def WritePWM(self, percentage):

        """
        This method interfaces with the IBM4 to set a pulse wave modulated (PWM) output signal.
        The output Pin# must be: 5,7,9,10-13.
        The PWM output must be between 0 and 100, and is a floating point value.
    
        instrument_obj is the open visa resource connected to dev_addr
        percentage must be in the range [0.0, 100]
        """

        self.FUNC_NAME = ".WritePWM()" # use this in exception handling messages
        self.ERR_STATEMENT = "Error: " + MOD_NAME_STR + self.FUNC_NAME

        try:
            c1 = True if self.instr_obj.isOpen() else False # confirm that the instrument object has been instantiated
            c3 = True if percentage >= 0 and percentage < 101 else False # confirm that no. averages being taken is a sensible value
        
            c10 = c1 and c3 # if all conditions are true then write can proceed
            if c10:
                output_channel = 9 # when using the IBM4 enhancement board the PWM is fixed to D9
                write_cmd = 'PWM%(v1)d:%(v2)d'%{"v1":output_channel, "v2":percentage}
                self.instr_obj.write( str.encode(write_cmd) ) # when using serial str must be encoded as bytes
                #self.ResetBuffer() # reset buffer between write, read cmd pairs
            else:
                if not c1:
                    self.ERR_STATEMENT = self.ERR_STATEMENT + '\nCould not write to instrument\nNo comms established'
                if not c3:
                    self.ERR_STATEMENT = self.ERR_STATEMENT + '\nCould not write to instrument\npercentage outside range [0, 100]'
                raise Exception
        except Exception as e:
            print(self.ERR_STATEMENT)
            print(e)
    
    # methods for obtaining data from the IBM4
    def ReadVoltage(self, input_channel, read_type = 'Single Voltage', no_reads = 10, loud = False):
        
        """
        Method for accessing the various types of Voltage Readings that are available
        """

        # This method is the equivalent of the polymorphic VI implementation of Read in LabVIEW
        # Python is flexible enough that it can handle a function with multiple return types
        # R. Sheehan 9 - 7 - 2024

        self.FUNC_NAME = ".ReadVoltage()" # use this in exception handling messages
        self.ERR_STATEMENT = "Error: " + MOD_NAME_STR + self.FUNC_NAME

        try:
            c1 = True if self.instr_obj.isOpen() else False # confirm that the instrument object has been instantiated
            c2 = True if input_channel in self.Read_Chnnls else False # confirm that the input channel label is correct
            c3 = True if no_reads > 2 and no_reads < 10000 else False # confirm that no. averages being taken is a sensible value
            c4 = True if read_type in self.Read_Types else False # confirm that the read_type has been chosen correctly
        
            c10 = c1 and c2 and c3 and c4 # if all conditions are true then write can proceed
            
            if c10:
                if read_type == 'Single Voltage':
                    return self.ReadSingleVoltage(input_channel)
                elif read_type == 'Multiple Voltage':
                    return self.ReadMultipleVoltage(input_channel, no_reads)
                elif read_type == 'Average Voltage':
                    return self.ReadAverageVoltage(input_channel, no_reads)
                elif read_type == 'Single Binary':
                    return self.ReadSingleBinary(input_channel)
                elif read_type == 'Multiple Binary':
                    return self.ReadMultipleBinary(input_channel, no_reads)
                else:
                    return self.ReadSingleVoltage(input_channel)
            else:
                if not c1:
                    self.ERR_STATEMENT = self.ERR_STATEMENT + '\nCould not read from instrument\nNo comms established'
                if not c2:
                    self.ERR_STATEMENT = self.ERR_STATEMENT + '\nCould not read from instrument\ninput_channel outside range {A0, A1}'
                if not c3:
                    self.ERR_STATEMENT = self.ERR_STATEMENT + '\nCould not read from instrument\nno_reads outside range [3, 10001]'
                if not c4:
                    self.ERR_STATEMENT = self.ERR_STATEMENT + '\nCould not read from instrument\nread_type incorrectly specified'
                raise Exception
        except Exception as e:
            print(self.ERR_STATEMENT)
            print(e)    
            
    def DifferentialRead(self, pos_channel, neg_channel, read_type = 'Single Voltage', no_reads = 10, loud = False):
        
        """
        Method for accessing the various types of Differential Voltage Readings that are available
        """

        # This method is the equivalent of the polymorphic VI implementation of DRead in LabVIEW
        # Python is flexible enough that it can handle a function with multiple return types
        # R. Sheehan 9 - 7 - 2024

        self.FUNC_NAME = ".DifferentialRead()" # use this in exception handling messages
        self.ERR_STATEMENT = "Error: " + MOD_NAME_STR + self.FUNC_NAME

        try:
            c1 = True if self.instr_obj.isOpen() else False # confirm that the instrument object has been instantiated
            c2 = True if pos_channel in self.Read_Chnnls else False # confirm that the positive channel label is correct
            c3 = True if neg_channel in self.Read_Chnnls else False # confirm that the positive channel label is correct
            c4 = True if neg_channel != pos_channel else False # confirm that the positive channel label is correct
            c5 = True if no_reads > 2 and no_reads < 10000 else False # confirm that no. averages being taken is a sensible value
        
            c10 = c1 and c2 and c3 and c4 and c5 # if all conditions are true then write can proceed
            
            if c10:
                if read_type == 'Single Voltage':
                    return self.DiffReadSingle(pos_channel, neg_channel)
                elif read_type == 'Multiple Voltage':
                    return self.DiffReadMultiple(pos_channel, neg_channel, no_reads)
                elif read_type == 'Average Voltage':
                    return self.DiffReadAverage(pos_channel, neg_channel, no_reads)
                elif read_type == 'Single Binary':
                    return self.DiffReadSingleBinary(pos_channel, neg_channel)
                elif read_type == 'Multiple Binary':
                    return self.DiffReadMultipleBinary(pos_channel, neg_channel, no_reads)
                else:
                    return self.DiffReadSingle(pos_channel, neg_channel)
            else:
                if not c1:
                    self.ERR_STATEMENT = self.ERR_STATEMENT + '\nCould not read from instrument\nNo comms established'
                if not c2:
                    self.ERR_STATEMENT = self.ERR_STATEMENT + '\nCould not read from instrument\npos_channel outside range {A0, A1}'
                if not c3:
                    self.ERR_STATEMENT = self.ERR_STATEMENT + '\nCould not read from instrument\npos_channel outside range {A0, A1}'
                if not c4:
                    self.ERR_STATEMENT = self.ERR_STATEMENT + '\nCould not read from instrument\npos_channel cannot be the same as neg_channel'
                if not c5:
                    self.ERR_STATEMENT = self.ERR_STATEMENT + '\nCould not read from instrument\nno_averages outside range [3, 10000]'
                raise Exception
        except Exception as e:
            print(self.ERR_STATEMENT)
            print(e)    
    
    # single ended voltage reading methods

    def ReadSingleVoltage(self, input_channel, loud = False):
        
        """        
        This method interfaces with the IBM4 to perform a read operation. The output will in floating point format (thus, in Volts).
        Only a single read operation is made with this method. Alternate read operations exist covering binary or floating point, single reading, 
        multiple readings, and an average of multiple readings (floating point only).
            
        Inputs:
        input_channel (type: str) is one of the labels for the analog input channels 'A2', 'A3', 'A4', 'A5', 'D2'
        
        Outputs:
        res (type: float) is the voltage reading at input_channel
        """
        
        self.FUNC_NAME = ".ReadSingleVoltage()" # use this in exception handling messages
        self.ERR_STATEMENT = "Error: " + MOD_NAME_STR + self.FUNC_NAME

        try:
            c1 = True if self.instr_obj.isOpen() else False # confirm that the instrument object has been instantiated
            c2 = True if input_channel in self.Read_Chnnls else False # confirm that the input channel label is correct
        
            c10 = c1 and c2 # if all conditions are true then write can proceed
            
            if c10:
                no_reads = 1 # 
                read_cmd = 'Read%(v1)d:%(v2)d\r\n'%{"v1":self.Read_Chnnls[input_channel], "v2":no_reads} # generate the read command
                self.instr_obj.write( str.encode(read_cmd) ) # when using serial str must be encoded as bytes                
                read_result = self.instr_obj.read_until('\n',size=None) # read_result returned as bytes, must be cast to str before being parsed                
                vals = re.findall(r'[-+]?\d+[\.]?\d*', str(read_result) ) # parse the numeric values of read_result into a list
                res = float(vals[-1])
                self.ResetBuffer() # reset buffer between write, read cmd pairs
                if loud: 
                    print(read_result)
                    print(vals) # print the parsed values
                return res # return the relevant value
            else:
                if not c1:
                    self.ERR_STATEMENT = self.ERR_STATEMENT + '\nCould not read from instrument\nNo comms established'
                if not c2:
                    self.ERR_STATEMENT = self.ERR_STATEMENT + '\nCould not read from instrument\ninput_channel outside range {A0, A1}'
                raise Exception
        except Exception as e:
            print(self.ERR_STATEMENT)
            print(e)
            
    def ReadSingleBinary(self, input_channel, loud = False):
        
        """        
        This method interfaces with the IBM4 to perform a read operation. The output will in binary format (thus, integer). Only a single read operation is made with this method.  
        Alternate read operations exist covering binary or floating point, single reading, multiple readings, and an average of multiple readings (floating point only).
            
        Inputs:
        input_channel (type: str) is one of the labels for the analog input channels 'A2', 'A3', 'A4', 'A5', 'D2'
        
        Outputs:
        res (type: int) is the voltage reading at input_channel
        """
        
        self.FUNC_NAME = ".ReadSingleBinary()" # use this in exception handling messages
        self.ERR_STATEMENT = "Error: " + MOD_NAME_STR + self.FUNC_NAME

        try:
            c1 = True if self.instr_obj.isOpen() else False # confirm that the instrument object has been instantiated
            c2 = True if input_channel in self.Read_Chnnls else False # confirm that the input channel label is correct
        
            c10 = c1 and c2 # if all conditions are true then write can proceed
            
            if c10:
                no_reads = 1 # 
                read_cmd = 'BRead%(v1)d:%(v2)d\r\n'%{"v1":self.Read_Chnnls[input_channel], "v2":no_reads} # generate the read command
                self.instr_obj.write( str.encode(read_cmd) ) # when using serial str must be encoded as bytes                
                read_result = self.instr_obj.read_until('\n',size=None) # read_result returned as bytes, must be cast to str before being parsed                
                vals = re.findall(r'[-+]?\d+[\.]?\d*', str(read_result) ) # parse the numeric values of read_result into a list
                res = int(vals[-1])
                self.ResetBuffer() # reset buffer between write, read cmd pairs
                if loud: 
                    print(read_result)
                    print(vals) # print the parsed values
                return res # return the relevant value
            else:
                if not c1:
                    self.ERR_STATEMENT = self.ERR_STATEMENT + '\nCould not read from instrument\nNo comms established'
                if not c2:
                    self.ERR_STATEMENT = self.ERR_STATEMENT + '\nCould not read from instrument\ninput_channel outside range {A0, A1}'
                raise Exception
        except Exception as e:
            print(self.ERR_STATEMENT)
            print(e)

    def ReadAverageVoltage(self, input_channel, no_reads = 10, loud = False):
        
        """        
        This method interfaces with the IBM4 to perform a read operation on a single read channel. The input channel must be between 0 and 3, 
        and the number of readings should be greater than zero. At some point the number of reading will be too high and will cause a timeout error. This should 
        only happen for numbers larger than 10000. The output will be a single Voltage (floating point) value representing the average of the multiple readings.
        Alternate read operations exist covering binary or floating point, single reading, multiple readings, and an average of multiple readings (floating point only).
            
        Inputs:
        input_channel (type: str) is one of the labels for the analog input channels 'A2', 'A3', 'A4', 'A5', 'D2'
        no_reads (type: int) is the num. of readings to be taken at the analog input channel
        
        Outputs:
        res (type: float) is the averaged voltage reading at input_channel
        """
        
        # Python nonsense
        # Use of vals = re.findall("[-+]?\d+[\.]?\d*", instrument_obj.read()) throws an error in Python 3.12
        # SyntaxWarning: invalid escape sequence '\d' vals = re.findall("[-+]?\d+[\.]?\d*", instrument_obj.read())
        # Explanation given here, use of \d will not be allowed in future versions of python so fix the problem now
        # https://stackoverflow.com/questions/77531208/python3-12-syntaxwarning-on-triplequoted-string-d-must-be-d
        # https://stackoverflow.com/questions/57645829/why-am-i-getting-a-syntaxwarning-invalid-escape-sequence-s-warning
        # https://stackoverflow.com/questions/50504500/deprecationwarning-invalid-escape-sequence-what-to-use-instead-of-d
        # Solution is to use vals = re.findall(r'[-+]?\d+[\.]?\d*', instrument_obj.read()) instead, tell the interpreter to view the regex cmd as a raw string
        # Alternatively use vals = re.findall('[-+]?\\d+[\\.]?\\d*', instrument_obj.read()), but this is less like true regex so use the other way
        
        # A bad method of doing this is to make repeated calls to readline
        # read_result = self.instr_obj.readline()
        # print(read_result)
        # read_result = self.instr_obj.readline()
        # print(read_result)
        # read_result = self.instr_obj.readline()
        # print(read_result)
        # read_result = self.instr_obj.readline()
        # print(read_result)
        # read_result = self.instr_obj.readline()
        # print(read_result)
                
        # If you don't want to continually call ResetBuffer
        # then you need to implement something like read_tail which can read from the end of the buffer
        # it might be possible to do this using readline to copy the entire IBM4 buffer into a local memory buffer
        # but the overhead on that would be just as bad as what I've implemented here
        # It seems other have attempted to solve this problem but have ended up implementing what I have here
        # other solutions seem to involve building the serial monitor loop inside this code, similar to what's been implemented in LabmethodEW
        # https://stackoverflow.com/questions/1093598/pyserial-how-to-read-the-last-line-sent-from-a-serial-device
        # R. Sheehan 8 - 7 - 2024

        self.FUNC_NAME = ".ReadAverageVoltage()" # use this in exception handling messages
        self.ERR_STATEMENT = "Error: " + MOD_NAME_STR + self.FUNC_NAME

        try:
            c1 = True if self.instr_obj.isOpen() else False # confirm that the instrument object has been instantiated
            c2 = True if input_channel in self.Read_Chnnls else False # confirm that the input channel label is correct
            c3 = True if no_reads > 2 and no_reads < 10000 else False # confirm that no. averages being taken is a sensible value
        
            c10 = c1 and c2 and c3 # if all conditions are true then write can proceed
            
            if c10:
                read_cmd = 'Average%(v1)d:%(v2)d\r\n'%{"v1":self.Read_Chnnls[input_channel], "v2":no_reads} # generate the read command
                self.instr_obj.write( str.encode(read_cmd) ) # when using serial str must be encoded as bytes                
                # Working
                read_result = self.instr_obj.read_until('\n',size=None) # read_result returned as bytes, must be cast to str before being parsed                
                vals = re.findall(r'[-+]?\d+[\.]?\d*', str(read_result) ) # parse the numeric values of read_result into a list
                res = float(vals[-1])
                self.ResetBuffer() # reset buffer between write, read cmd pairs
                if loud: 
                    print(read_result)
                    print(vals) # print the parsed values
                return res # return the relevant value
            else:
                if not c1:
                    self.ERR_STATEMENT = self.ERR_STATEMENT + '\nCould not read from instrument\nNo comms established'
                if not c2:
                    self.ERR_STATEMENT = self.ERR_STATEMENT + '\nCould not read from instrument\ninput_channel outside range {A0, A1}'
                if not c3:
                    self.ERR_STATEMENT = self.ERR_STATEMENT + '\nCould not read from instrument\nno_reads outside range [3, 10001]'
                raise Exception
        except Exception as e:
            print(self.ERR_STATEMENT)
            print(e)
            
    def ReadAverageVoltageAllChnnl(self, no_reads = 10, loud = False):
    
        """
        This method interfaces with the IBM4 to perform an averaging read operation on all read channels
        returns a list of voltage readings at each analog input channel [A2, A3, A4, A5, D2]

        Inputs: 
        no_reads (type: int) is the num. of readings to be taken at the analog input channel
        
        Outputs: 
        read_vals (type: numpy array) contains the averaged voltage reading at each analog input channel
        """
        
        FUNC_NAME = ".ReadAverageVoltageAllChnnl()" # use this in exception handling messages
        ERR_STATEMENT = "Error: " + MOD_NAME_STR + FUNC_NAME

        try:
            c1 = True if self.instr_obj.isOpen() else False # confirm that the instrument object has been instantiated
            c3 = True if no_reads > 3 and no_reads < 10000 else False # confirm that no. averages being taken is a sensible value
        
            c10 = c1 and c3 # if all conditions are true then write can proceed
        
            if c10:
                read_vals = numpy.array([]) # instantiate an empty numpy array
                for item in self.Read_Chnnls:
                    value = self.ReadAverageVoltage(item, no_reads, loud)
                    read_vals = numpy.append(read_vals, value)
                    if loud: 
                        print('Voltages at AI: ',read_vals)
                return read_vals
            else:
                if not c1:
                    self.ERR_STATEMENT = self.ERR_STATEMENT + '\nCould not read from instrument\nNo comms established'
                if not c3:
                    self.ERR_STATEMENT = self.ERR_STATEMENT + '\nCould not read from instrument\nno_reads outside range [3, 10001]'
                raise Exception
        except Exception as e:
            print(self.ERR_STATEMENT)
            print(e)
            
    def ReadMultipleVoltage(self, input_channel, no_reads = 10, loud = False):
        
        """
        This method interfaces with the IBM4 to perform a read operation.
        The number of readings should be greater than zero. At some point the number of reading will be too high and will cause a timeout error. 
        This should only happen for numbers larger than 10000. The output will be an array of floating point (Voltage) values.
        Alternate read operations exist covering binary or floating point, single reading, multiple readings, and an average of multiple readings (floating point only).
        
        Inputs:
        input_channel (type: str) is one of the labels for the analog input channels 'A2', 'A3', 'A4', 'A5', 'D2'
        no_reads (type: int) is the num. of readings that are to be averaged
        
        Outputs: 
        res (type: list) contains three elements
        res[0] = average of all voltage readings
        res[1] = amplitude voltage readings
        res[2] = numpy array with all voltage read values
        """

        self.FUNC_NAME = ".ReadMultipleVoltage()" # use this in exception handling messages
        self.ERR_STATEMENT = "Error: " + MOD_NAME_STR + self.FUNC_NAME

        try:
            c1 = True if self.instr_obj.isOpen() else False # confirm that the instrument object has been instantiated
            c2 = True if input_channel in self.Read_Chnnls else False # confirm that the input channel label is correct
            c3 = True if no_reads > 2 and no_reads < 10000 else False # confirm that no. averages being taken is a sensible value
        
            c10 = c1 and c2 and c3 # if all conditions are true then write can proceed
            
            if c10:
                read_cmd = 'Read%(v1)d:%(v2)d\r\n'%{"v1":self.Read_Chnnls[input_channel], "v2":no_reads} # generate the read command
                self.instr_obj.write( str.encode(read_cmd) ) # when using serial str must be encoded as bytes                
                # Working
                read_result = self.instr_obj.read_until('\n',size=None) # read_result returned as bytes, must be cast to str before being parsed                
                vals_str = re.findall(r'[-+]?\d+[\.]?\d*', str(read_result) ) # parse the numeric values of read_result into a list
                self.ResetBuffer() # reset buffer between write, read cmd pairs
                vals_flt = numpy.float_(vals_str[-no_reads:]) # convert the list of strings to floats using numpy, save as numpy array (better)
                vals_mean = numpy.mean(vals_flt) # compute the average of all the diff_reads
                vals_delta = 0.5*( numpy.max(vals_flt) - numpy.min(vals_flt) ) # compute the range of the diff_read
                res = [vals_mean, vals_delta, vals_flt]
                if loud: 
                    print(read_result)
                    print(vals_flt) # print the parsed values
                return res # return the array containing all the voltage values
            else:
                if not c1:
                    self.ERR_STATEMENT = self.ERR_STATEMENT + '\nCould not read from instrument\nNo comms established'
                if not c2:
                    self.ERR_STATEMENT = self.ERR_STATEMENT + '\nCould not read from instrument\ninput_channel outside range {A0, A1}'
                if not c3:
                    self.ERR_STATEMENT = self.ERR_STATEMENT + '\nCould not read from instrument\nno_averages outside range [3, 10001]'
                raise Exception
        except Exception as e:
            print(self.ERR_STATEMENT)
            print(e)
            
    def ReadMultipleBinary(self, input_channel, no_reads = 10, loud = False):
        
        """
        This VI interfaces with the IBM4 to perform a read operation. The number of readings should be greater than zero. At some point the 
        number of reading will be too high and will cause a timeout error. This should only happen for numbers larger than 10000. The output will be an array of integer 
        values. Alternate read operations exist covering binary or floating point, single reading, multiple readings, and an average of multiple readings (floating point only).
        
        Inputs:
        input_channel (type: str) is one of the labels for the analog input channels 'A2', 'A3', 'A4', 'A5', 'D2'
        no_reads (type: int) is the num. of readings that are to be averaged
        
        Outputs: 
        vals_int (type: numpy array) contains binary read values
        """

        self.FUNC_NAME = ".ReadMultipleBinary()" # use this in exception handling messages
        self.ERR_STATEMENT = "Error: " + MOD_NAME_STR + self.FUNC_NAME

        try:
            c1 = True if self.instr_obj.isOpen() else False # confirm that the instrument object has been instantiated
            c2 = True if input_channel in self.Read_Chnnls else False # confirm that the input channel label is correct
            c3 = True if no_reads > 2 and no_reads < 10000 else False # confirm that no. averages being taken is a sensible value
        
            c10 = c1 and c2 and c3 # if all conditions are true then write can proceed
            
            if c10:
                read_cmd = 'BRead%(v1)d:%(v2)d\r\n'%{"v1":self.Read_Chnnls[input_channel], "v2":no_reads} # generate the read command
                self.instr_obj.write( str.encode(read_cmd) ) # when using serial str must be encoded as bytes                
                # Working
                read_result = self.instr_obj.read_until('\n',size=None) # read_result returned as bytes, must be cast to str before being parsed                
                vals_str = re.findall(r'[-+]?\d+[\.]?\d*', str(read_result) ) # parse the numeric values of read_result into a list
                self.ResetBuffer() # reset buffer between write, read cmd pairs
                vals_int = numpy.int_(vals_str[-no_reads:]) # convert the list of strings to ints using numpy, save as numpy array (better)
                if loud: 
                    print(read_result)
                    print(vals_int) # print the parsed values
                return vals_int # return the array containing all the binary values
            else:
                if not c1:
                    self.ERR_STATEMENT = self.ERR_STATEMENT + '\nCould not read from instrument\nNo comms established'
                if not c2:
                    self.ERR_STATEMENT = self.ERR_STATEMENT + '\nCould not read from instrument\ninput_channel outside range {A0, A1}'
                if not c3:
                    self.ERR_STATEMENT = self.ERR_STATEMENT + '\nCould not read from instrument\nno_averages outside range [3, 10001]'
                raise Exception
        except Exception as e:
            print(self.ERR_STATEMENT)
            print(e)
    
    # differential voltage reading methods

    def DiffReadSingle(self, pos_channel, neg_channel, loud = False):
        
        """
        This method interfaces with the IBM4 to perform a differential read operation.
        The input channels must be between 0 and 4, and the number of readings to be averaged should be greater than zero. 
        At some point the number of readings will be too high and will cause a timeout error. This should only happen for numbers 
        larger than 10000. The output will be a single Voltage (floating point) value.
    
        Inputs:
        pos_channel (type: str) is one of the labels for the analog input channels 'A2', 'A3', 'A4', 'A5', 'D2'
        neg_channel (type: str) is one of the labels for the analog input channels 'A2', 'A3', 'A4', 'A5', 'D2', accepting that it is not the same as pos_channel    
        
        Outputs:
        res (type: float) is the voltage reading at input_channel
        """

        self.FUNC_NAME = ".DiffReadSingle()" # use this in exception handling messages
        self.ERR_STATEMENT = "Error: " + MOD_NAME_STR + self.FUNC_NAME
    
        try:
            c1 = True if self.instr_obj.isOpen() else False # confirm that the instrument object has been instantiated
            c2 = True if pos_channel in self.Read_Chnnls else False # confirm that the positive channel label is correct
            c3 = True if neg_channel in self.Read_Chnnls else False # confirm that the positive channel label is correct
            c4 = True if neg_channel != pos_channel else False # confirm that the positive channel label is correct
        
            c10 = c1 and c2 and c3 and c4 # if all conditions are true then write can proceed
            
            if c10:
                no_reads = 1
                read_cmd = 'Diff_Read%(v1)d:%(v2)d:%(v3)d\r\n'%{"v1":self.Read_Chnnls[pos_channel], "v2":self.Read_Chnnls[neg_channel], "v3":no_reads}
                self.instr_obj.write( str.encode(read_cmd) ) # when using serial str must be encoded as bytes
                read_result = self.instr_obj.read_until('\n',size=None) # read_result returned as bytes, must be cast to str before being parsed
                vals_str = re.findall(r'[-+]?\d+[\.]?\d*', str(read_result) ) # parse the numeric values of read_result into a list of strings
                res = float(vals_str[-1])
                self.ResetBuffer() # clear the IBM4 buffer after each read            
                if loud: 
                    print(read_result)
                    print(res) 
                return res
            else:
                if not c1:
                    self.ERR_STATEMENT = self.ERR_STATEMENT + '\nCould not read from instrument\nNo comms established'
                if not c2:
                    self.ERR_STATEMENT = self.ERR_STATEMENT + '\nCould not read from instrument\npos_channel outside range {A0, A1}'
                if not c3:
                    self.ERR_STATEMENT = self.ERR_STATEMENT + '\nCould not read from instrument\npos_channel outside range {A0, A1}'
                if not c4:
                    self.ERR_STATEMENT = self.ERR_STATEMENT + '\nCould not read from instrument\npos_channel cannot be the same as neg_channel'
                raise Exception
        except Exception as e:
            print(self.ERR_STATEMENT)
            print(e) 
            
    def DiffReadAverage(self, pos_channel, neg_channel, no_reads, loud = False):
        
        """
        This method interfaces with the IBM4 to perform a differential read operation.
        The input channels must be between 0 and 4, and the number of readings to be averaged should be greater than zero. 
        At some point the number of readings will be too high and will cause a timeout error. This should only happen for numbers 
        larger than 10000. The output will be a single Voltage (floating point) value representing the average of the multiple readings.
    
        Inputs:
        pos_channel (type: str) is one of the labels for the analog input channels 'A2', 'A3', 'A4', 'A5', 'D2'
        neg_channel (type: str) is one of the labels for the analog input channels 'A2', 'A3', 'A4', 'A5', 'D2', accepting that it is not the same as pos_channel    
        no_reads (type: int) is the num. of readings to be taken at the analog input channel
        
        Outputs:
        res (type: float) is the voltage reading at input_channel
        """

        self.FUNC_NAME = ".DiffReadSingle()" # use this in exception handling messages
        self.ERR_STATEMENT = "Error: " + MOD_NAME_STR + self.FUNC_NAME
    
        try:
            c1 = True if self.instr_obj.isOpen() else False # confirm that the instrument object has been instantiated
            c2 = True if pos_channel in self.Read_Chnnls else False # confirm that the positive channel label is correct
            c3 = True if neg_channel in self.Read_Chnnls else False # confirm that the positive channel label is correct
            c4 = True if neg_channel != pos_channel else False # confirm that the positive channel label is correct
            c5 = True if no_reads > 2 and no_reads < 10000 else False # confirm that no. averages being taken is a sensible value
        
            c10 = c1 and c2 and c3 and c4 and c5 # if all conditions are true then write can proceed
            
            if c10:
                read_cmd = 'Diff_Average%(v1)d:%(v2)d:%(v3)d\r\n'%{"v1":self.Read_Chnnls[pos_channel], "v2":self.Read_Chnnls[neg_channel], "v3":no_reads}
                self.instr_obj.write( str.encode(read_cmd) ) # when using serial str must be encoded as bytes
                read_result = self.instr_obj.read_until('\n',size=None) # read_result returned as bytes, must be cast to str before being parsed
                vals_str = re.findall(r'[-+]?\d+[\.]?\d*', str(read_result) ) # parse the numeric values of read_result into a list of strings
                res = float(vals_str[-1])
                self.ResetBuffer() # clear the IBM4 buffer after each read            
                if loud: 
                    print(read_result)
                    print(res) 
                return res
            else:
                if not c1:
                    self.ERR_STATEMENT = self.ERR_STATEMENT + '\nCould not read from instrument\nNo comms established'
                if not c2:
                    self.ERR_STATEMENT = self.ERR_STATEMENT + '\nCould not read from instrument\npos_channel outside range {A0, A1}'
                if not c3:
                    self.ERR_STATEMENT = self.ERR_STATEMENT + '\nCould not read from instrument\npos_channel outside range {A0, A1}'
                if not c4:
                    self.ERR_STATEMENT = self.ERR_STATEMENT + '\nCould not read from instrument\npos_channel cannot be the same as neg_channel'
                if not c5:
                    self.ERR_STATEMENT = self.ERR_STATEMENT + '\nCould not read from instrument\nno_averages outside range [3, 10000]'
                raise Exception
        except Exception as e:
            print(self.ERR_STATEMENT)
            print(e) 
            
    def DiffReadMultiple(self, pos_channel, neg_channel, no_reads = 10, loud = False):
        
        """
        This method interfaces with the IBM4 to perform a differential read operation.
        The input channels must be between 0 and 4, and the number of readings to be averaged should be greater than zero. 
        At some point the number of readings will be too high and will cause a timeout error. This should only happen for numbers 
        larger than 10000. The output will be an array of Voltage (floating point) values.
    
        Inputs:
        pos_channel (type: str) is one of the labels for the analog input channels 'A2', 'A3', 'A4', 'A5', 'D2'
        neg_channel (type: str) is one of the labels for the analog input channels 'A2', 'A3', 'A4', 'A5', 'D2', accepting that it is not the same as pos_channel    
        no_reads (type: int) is the num. of readings to be taken at the analog input channel
        
        Outputs:
        res (type: list) contains three elements
        res[0] = average of all differential readings
        res[1] = variation in differential readings
        res[2] = numpy array with all differential read values
        """

        self.FUNC_NAME = ".DiffReadMultiple()" # use this in exception handling messages
        self.ERR_STATEMENT = "Error: " + MOD_NAME_STR + self.FUNC_NAME
    
        try:
            c1 = True if self.instr_obj.isOpen() else False # confirm that the instrument object has been instantiated
            c2 = True if pos_channel in self.Read_Chnnls else False # confirm that the positive channel label is correct
            c3 = True if neg_channel in self.Read_Chnnls else False # confirm that the positive channel label is correct
            c4 = True if neg_channel != pos_channel else False # confirm that the positive channel label is correct
            c5 = True if no_reads > 2 and no_reads < 10000 else False # confirm that no. averages being taken is a sensible value
        
            c10 = c1 and c2 and c3 and c4 and c5 # if all conditions are true then write can proceed
            
            if c10:
                read_cmd = 'Diff_Read%(v1)d:%(v2)d:%(v3)d\r\n'%{"v1":self.Read_Chnnls[pos_channel], "v2":self.Read_Chnnls[neg_channel], "v3":no_reads}
                self.instr_obj.write( str.encode(read_cmd) ) # when using serial str must be encoded as bytes
                read_result = self.instr_obj.read_until('\n',size=None) # read_result returned as bytes, must be cast to str before being parsed
                vals_str = re.findall(r'[-+]?\d+[\.]?\d*', str(read_result) ) # parse the numeric values of read_result into a list of strings
                #vals_flt = [float(x) for x in vals_str] # convert the list of strings to floats, save as a list
                # only interested in the last no_reads values so read backwards into the vals_str list using list-slice operator
                vals_flt = numpy.float_(vals_str[-no_reads:]) # convert the list of strings to floats using numpy, save as numpy array (better)
                if loud: 
                    print(read_result)
                    print(vals_flt) # print the parsed values
                self.ResetBuffer() # clear the IBM4 buffer after each read            
                vals_mean = numpy.mean(vals_flt) # compute the average of all the diff_reads
                vals_delta = 0.5*( numpy.max(vals_flt) - numpy.min(vals_flt) ) # compute the range of the diff_read
                res = [vals_mean, vals_delta, vals_flt]
                return res # return the relevant numerical values
            else:
                if not c1:
                    self.ERR_STATEMENT = self.ERR_STATEMENT + '\nCould not read from instrument\nNo comms established'
                if not c2:
                    self.ERR_STATEMENT = self.ERR_STATEMENT + '\nCould not read from instrument\npos_channel outside range {A0, A1}'
                if not c3:
                    self.ERR_STATEMENT = self.ERR_STATEMENT + '\nCould not read from instrument\npos_channel outside range {A0, A1}'
                if not c4:
                    self.ERR_STATEMENT = self.ERR_STATEMENT + '\nCould not read from instrument\npos_channel cannot be the same as neg_channel'
                if not c5:
                    self.ERR_STATEMENT = self.ERR_STATEMENT + '\nCould not read from instrument\nno_averages outside range [3, 10000]'
                raise Exception
        except Exception as e:
            print(self.ERR_STATEMENT)
            print(e) 
            
    def DiffReadSingleBinary(self, pos_channel, neg_channel, loud = False):
        
        """
        This method interfaces with the IBM4 to perform a differential read operation.
        The input channels must be between 0 and 4, and the number of readings to be averaged should be greater than zero. 
        At some point the number of readings will be too high and will cause a timeout error. This should only happen for numbers 
        larger than 10000. The output will in binary format (thus, integer). Only a single read operation is made with this method. 
    
        Inputs:
        pos_channel (type: str) is one of the labels for the analog input channels 'A2', 'A3', 'A4', 'A5', 'D2'
        neg_channel (type: str) is one of the labels for the analog input channels 'A2', 'A3', 'A4', 'A5', 'D2', accepting that 
        it is not the same as pos_channel    
        
        Outputs:
        res (type: int) is the voltage reading at input_channel
        """

        self.FUNC_NAME = ".DiffReadSingleBinary()" # use this in exception handling messages
        self.ERR_STATEMENT = "Error: " + MOD_NAME_STR + self.FUNC_NAME
    
        try:
            c1 = True if self.instr_obj.isOpen() else False # confirm that the instrument object has been instantiated
            c2 = True if pos_channel in self.Read_Chnnls else False # confirm that the positive channel label is correct
            c3 = True if neg_channel in self.Read_Chnnls else False # confirm that the positive channel label is correct
            c4 = True if neg_channel != pos_channel else False # confirm that the positive channel label is correct
        
            c10 = c1 and c2 and c3 and c4 # if all conditions are true then write can proceed
            
            if c10:
                no_reads = 1
                read_cmd = 'Diff_BRead%(v1)d:%(v2)d:%(v3)d\r\n'%{"v1":self.Read_Chnnls[pos_channel], "v2":self.Read_Chnnls[neg_channel], "v3":no_reads}
                self.instr_obj.write( str.encode(read_cmd) ) # when using serial str must be encoded as bytes
                read_result = self.instr_obj.read_until('\n',size=None) # read_result returned as bytes, must be cast to str before being parsed
                vals_str = re.findall(r'[-+]?\d+[\.]?\d*', str(read_result) ) # parse the numeric values of read_result into a list of strings
                res = int(vals_str[-1])
                self.ResetBuffer() # clear the IBM4 buffer after each read            
                if loud: 
                    print(read_result)
                    print(res) 
                return res
            else:
                if not c1:
                    self.ERR_STATEMENT = self.ERR_STATEMENT + '\nCould not read from instrument\nNo comms established'
                if not c2:
                    self.ERR_STATEMENT = self.ERR_STATEMENT + '\nCould not read from instrument\npos_channel outside range {A0, A1}'
                if not c3:
                    self.ERR_STATEMENT = self.ERR_STATEMENT + '\nCould not read from instrument\npos_channel outside range {A0, A1}'
                if not c4:
                    self.ERR_STATEMENT = self.ERR_STATEMENT + '\nCould not read from instrument\npos_channel cannot be the same as neg_channel'
                raise Exception
        except Exception as e:
            print(self.ERR_STATEMENT)
            print(e)
            
    def DiffReadMultipleBinary(self, pos_channel, neg_channel, no_reads = 10, loud = False):
        
        """
        This method interfaces with the IBM4 to perform a differential read operation.
        The input channels must be between 0 and 4, and the number of readings to be averaged should be greater than zero. 
        At some point the number of readings will be too high and will cause a timeout error. This should only happen for numbers 
        larger than 10000. The output will be an array of integer values.
    
        Inputs:
        pos_channel (type: str) is one of the labels for the analog input channels 'A2', 'A3', 'A4', 'A5', 'D2'
        neg_channel (type: str) is one of the labels for the analog input channels 'A2', 'A3', 'A4', 'A5', 'D2', accepting that it is not the same as pos_channel    
        no_reads (type: int) is the num. of readings to be taken at the analog input channel
        
        Outputs:
        vals_int (type: int) numpy array with all differential read values
        """

        self.FUNC_NAME = ".DiffReadMultiple()" # use this in exception handling messages
        self.ERR_STATEMENT = "Error: " + MOD_NAME_STR + self.FUNC_NAME
    
        try:
            c1 = True if self.instr_obj.isOpen() else False # confirm that the instrument object has been instantiated
            c2 = True if pos_channel in self.Read_Chnnls else False # confirm that the positive channel label is correct
            c3 = True if neg_channel in self.Read_Chnnls else False # confirm that the positive channel label is correct
            c4 = True if neg_channel != pos_channel else False # confirm that the positive channel label is correct
            c5 = True if no_reads > 2 and no_reads < 10000 else False # confirm that no. averages being taken is a sensible value
        
            c10 = c1 and c2 and c3 and c4 and c5 # if all conditions are true then write can proceed
            
            if c10:
                read_cmd = 'Diff_BRead%(v1)d:%(v2)d:%(v3)d\r\n'%{"v1":self.Read_Chnnls[pos_channel], "v2":self.Read_Chnnls[neg_channel], "v3":no_reads}
                self.instr_obj.write( str.encode(read_cmd) ) # when using serial str must be encoded as bytes
                read_result = self.instr_obj.read_until('\n',size=None) # read_result returned as bytes, must be cast to str before being parsed
                vals_str = re.findall(r'[-+]?\d+[\.]?\d*', str(read_result) ) # parse the numeric values of read_result into a list of strings
                #vals_flt = [float(x) for x in vals_str] # convert the list of strings to floats, save as a list
                # only interested in the last no_reads values so read backwards into the vals_str list using list-slice operator
                vals_int = numpy.int_(vals_str[-no_reads:]) # convert the list of strings to floats using numpy, save as numpy array (better)
                self.ResetBuffer() # clear the IBM4 buffer after each read            
                if loud: 
                    print(read_result)
                    print(vals_int) # print the parsed values                
                return vals_int # return the relevant numerical values
            else:
                if not c1:
                    self.ERR_STATEMENT = self.ERR_STATEMENT + '\nCould not read from instrument\nNo comms established'
                if not c2:
                    self.ERR_STATEMENT = self.ERR_STATEMENT + '\nCould not read from instrument\npos_channel outside range {A0, A1}'
                if not c3:
                    self.ERR_STATEMENT = self.ERR_STATEMENT + '\nCould not read from instrument\npos_channel outside range {A0, A1}'
                if not c4:
                    self.ERR_STATEMENT = self.ERR_STATEMENT + '\nCould not read from instrument\npos_channel cannot be the same as neg_channel'
                if not c5:
                    self.ERR_STATEMENT = self.ERR_STATEMENT + '\nCould not read from instrument\nno_averages outside range [3, 10000]'
                raise Exception
        except Exception as e:
            print(self.ERR_STATEMENT)
            print(e)
            
    # methods to initiate multimeter mode
    
    def MultimeterMode(self):
    
        """
        Method for interfacing to the IBM4 and using it as a digitial multimeter
        Output voltage from the Analog outs, Read voltage from the Analog inputs
        Switch the PWM output On / Off as required
        Perform differential measurements
        It will be assumed that comms to the device is open
        """        

        self.MultimeterMode = ".Multimeter_Mode()" # use this in exception handling messages
        self.ERR_STATEMENT = "Error: " + MOD_NAME_STR + self.FUNC_NAME

        try:
            if self.instr_obj.isOpen():
                # Simple menu allows you to operate the IBM4 continuously
            
                # Start do-while loop to process the multimeter options
                do = True        
                while do: 
                    action = int( input( self.MultimeterPrompt() ) )
                    if action == -1:
                        print('\nEnd Program\n')
                        self.ZeroIBM4()
                        do = False
                    elif action == 1:
                        #idn_prompt(instrument_obj)
                        continue
                    elif action == 2:
                        self.VoltOutputPrompt('A0')
                        continue
                    elif action == 3:
                        self.VoltOutputPrompt('A1')
                        continue
                    elif action == 4:
                        self.PWMPrompt()
                        continue
                    elif action == 5:
                        self.GroundIBM4Prompt()
                        continue
                    elif action == 6:
                        self.ReadInputsPrompt()
                        continue
                    elif action == 7:
                        self.DiffReadPrompt()
                        continue
                    else:
                        #action = int(input(prompt)) # don't make this call here, otherwise prompt for input is executed twice
                        continue
            else:
                self.ERR_STATEMENT = self.ERR_STATEMENT + '\nCould not write to instrument\nNo comms established'
                raise Exception
        except Exception as e:
            print(self.ERR_STATEMENT)
            print(e)
    
    def MultimeterPrompt(self):
        """
        text processing for the multimeter mode prompt
        """
        
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

    # def IDNPprompt(self):
    #     # perform the *IDN action
    #     # R. Sheehan 4 - 6-  2024    
    #     self.query('*IDN')
    #     str_val = self.read()
    #     if "ISBY" in str_val:
    #         print('\nCurrent Device:',self.resource_name)
    #     self.clear()

    def VoltOutputPrompt(self, output_channel):
        """
        Method for requesting the user input a voltage value to output from some channel
        """
        
        print('\nSet Analog Output %(v1)s'%{"v1":output_channel})
        axvolt = float(input('Enter a voltage value: '))
        self.WriteVoltage(output_channel, axvolt)
    
    def GroundIBM4Prompt(self):
        """
        zero both analog output channels
        """
        
        print('\nGround Analog Outputs\n')
        self.ZeroIBM4()
    
    def ReadInputsPrompt(self):
        """
        Read the voltage at all analog inputs
        """
        
        print('\nRead All Analog Inputs')
        ch_vals = self.ReadAverageVoltageAllChnnl()
        print('AI voltages: ',ch_vals)
    
    def PWMPrompt(self):
        """
        Method for getting the IBM4 to output PWM signal
        """

        print('\nSet PWM Output')
        pwmval = int( input( 'Enter PWM percentage: ' ) )
        self.WritePWM(pwmval)
    
    def DiffReadPrompt(self):
        """
        Method for performing a differential read
        """
        
        print('\nPerform Differential Measurement')
        pos_chn = str( input('Enter pos-chan: ') )
        neg_chn = str( input('Enter neg-chan: ') )
        #n_ave = int( input('Enter no. averages: ') )
        diff_res = self.DiffReadMultiple(pos_chn, neg_chn)
        print('Differential Read Value = %(v1)0.3f +/- %(v2)0.3f (V)'%{"v1":diff_res[0], "v2":diff_res[1]})
        
    # methods for initiating voltage sweeps
        