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
# Use if-else ladders to implement the same effect, or use comething called classmethods
# https://www.geeksforgeeks.org/method-and-constructor-overloading-in-python/
# or use comething called classmethods
# https://docs.python.org/3/library/functions.html#classmethod
# https://stackoverflow.com/questions/141545/how-to-overload-init-method-based-on-argument-type
# https://stackoverflow.com/questions/682504/what-is-a-clean-pythonic-way-to-implement-multiple-constructors
# https://stackoverflow.com/questions/58858556/how-can-i-perform-constructor-overloading-in-python
# R. Sheehan 12 - 6 - 2024

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
    def __init__(self, port_name = None):
        """
        Constructor for the IBM4 Serial Interface
        """        
        try:
            self.FUNC_NAME = ".Ser_Iface()" # use this in exception handling messages
            self.ERR_STATEMENT = "Error: " + MOD_NAME_STR + self.FUNC_NAME
            
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
            self.open_comms()
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
            self.instr_obj.close()
        else:
            # Do nothing no link to IBM4 established
            pass
            
    def __str__(self):
        """
        return a string the describes the class
        """
        return "class for interfacing to an IBM4"
    
    def comms_status(self):
        """
        investigate the status of the serial comms link
        """
        if self.IBM4Port is not None and self.instr_obj.is_open:
            print('Communication with:',self.instr_obj.name,' is open')
            return True
        else:
            print('Communication with: IBM4 is not open')
            return False
            
    def open_comms(self):
        """
        open a serial link to a COM port attached to an IBM4
        """
        try:
            if self.IBM4Port is not None:
                # open a serial link to a device
                self.instr_obj = serial.Serial(self.IBM4Port, self.baud_rate, timeout = self.read_timeout, write_timeout = self.write_timeout, stopbits=serial.STOPBITS_ONE)
        
                self.comms_status()
            else:
                self.ERR_STATEMENT = self.ERR_STATEMENT + '\nNo IBM4 attached to PC'
                raise Exception
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
            
    # methods for writing data to the IBM4
    
    # methods for obtaining data from the IBM4
    
    # 