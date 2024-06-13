"""
Python library for interacting with the IBM4 using Serial
Assumes that the IBM4 is configured with the correct UCC circuit python source code
This module replicates the existing code that was written for LabVIEW by Frank Peters
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

# import required libraries
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
        
        if self.IBM4Port is not None and self.instr_obj.is_open:
            # close the link to the instrument object when it goes out of scope
            print('Closing Serial link with:',self.instr_obj.name)
            self.ResetIBM4()
            self.instr_obj.close()
        else:
            # Do nothing, no link to IBM4 established
            pass
            
    def __str__(self):
        """
        return a string the describes the class
        """
        
        return "class for interfacing to an IBM4"
    
    def CommsStatus(self):
        """
        investigate the status of the serial comms link
        """
        
        if self.IBM4Port is not None and self.instr_obj.is_open:
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
                self.ResetIBM4()

                self.CommsStatus()
            else:
                self.ERR_STATEMENT = self.ERR_STATEMENT + '\nNo IBM4 attached to PC'
                raise Exception
        except Exception as e:
            print(self.ERR_STATEMENT)
            print(e)
            
    def ResetIBM4(self):
        """
        zero the analog and PWM outputs of the IBM4
        """
        
        self.FUNC_NAME = ".ResetIBM4()" # use this in exception handling messages
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
        read_mode = 'DC' =>  IBM4 assumes analog inputs in the range [0, 3.3)
        read_mode = 'AC' =>  IBM4 assumes analog inputs in the range [-8, +8]
        read_mode = 'AC' requires BP2UP board be used with IBM4
        """
        
        self.FUNC_NAME = ".SetMode()" # use this in exception handling messages
        self.ERR_STATEMENT = "Error: " + MOD_NAME_STR + self.FUNC_NAME

        try:
            c1 = True if self.instr_obj.isOpen() else False # confirm that the intstrument object has been instantiated
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
    
    def WriteSingleChnnl(self, output_channel, set_voltage = 0.0):
        
        """
        This method interfaces with the IBM4 to perform a write operation where a Voltage is output on one of the analog output pins of the IBM4.
        The output channel must be 0 or 1, while the output value should be specified in Volts (thus, floating point)

        output_channel is one of A0, A1
        set_voltage is the desired voltage output value from the channel
        set_voltage must be in the range [0.0, 3.3)
        """

        self.FUNC_NAME = ".WriteSingleChnnl()" # use this in exception handling messages
        self.ERR_STATEMENT = "Error: " + MOD_NAME_STR + self.FUNC_NAME

        try:
            c1 = True if self.instr_obj.isOpen() else False # confirm that the intstrument object has been instantiated
            c2 = True if output_channel in self.Write_Chnnls else False # confirm that the output channel label is correct
            c3 = True if set_voltage >= self.VMIN and set_voltage < self.VMAX else False # confirm that the set voltage value is in range
            c10 = c1 and c2 and c3 # if all conditions are true then write can proceed
        
            if c10:
                write_cmd = 'Write%(v1)d:%(v2)0.2f\r\n'%{"v1":self.Write_Chnnls[output_channel], "v2":set_voltage}
                self.instr_obj.write( str.encode(write_cmd) ) # when using serial str must be encoded as bytes
                #time.sleep(DELAY) # no need for explicit delay, this is handled by write_timeout
                #self.instr_obj.clear() # do you need to reset the buffer? 
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
            c1 = True if self.instr_obj.isOpen() else False # confirm that the intstrument object has been instantiated
            c3 = True if percentage >= 0 and percentage < 101 else False # confirm that no. averages being taken is a sensible value
        
            c10 = c1 and c3 # if all conditions are true then write can proceed
            if c10:
                output_channel = 9 # when using the IBM4 enhancement board the PWM is fixed to D9
                write_cmd = 'PWM%(v1)d:%(v2)d'%{"v1":output_channel, "v2":percentage}
                self.instr_obj.write( str.encode(write_cmd) ) # when using serial str must be encoded as bytes
                #time.sleep(DELAY) # no need for explicit delay, this is handled by write_timeout
                #self.instr_obj.clear() # do you need to reset the buffer? 
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
    
    