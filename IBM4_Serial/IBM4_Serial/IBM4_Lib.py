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
# For notes on proper object oriented programming consult a book on C++
# I recommend ``Introducing C++ for Scientists, Engineers and Mathematicians'' by D. W. Capper

# import required libraries
import os
import sys
import glob
import serial
import pyvisa
import time
import numpy
import re

MOD_NAME_STR = "IBM4_Lib"

# define the class for interfacing to an IBM4

class Ser_Iface(object):
    """
    class for interfacing to an IBM4
    """
    
    # default constructor
    # attempts to locate an IBM4 attached to the PC and opens a serial comms link to that port
    # define default arguments inside
    def __init__(self):
        try:
            self.FUNC_NAME = ".Ser_Iface()" # use this in exception handling messages
            self.ERR_STATEMENT = "Error: " + MOD_NAME_STR + self.FUNC_NAME
            
            # parameters to be passed to the serial open command
            self.dev_addr = self.FindIBM4() # string containing the port no. of the device
            self.baud_rate = 9600 # serial comms baud_rate
            self.read_timeout = 3 # timeout for reading data from the IBM4, units of second
            self.write_timeout = 0.5 # timeout for writing data to the IBM4, units of second
            
            # open the serial comms link to port_name
            self.instr_obj = serial.Serial(self.dev_addr, self.baud_rate, timeout = self.read_timeout, write_timeout = self.write_timeout, stopbits=serial.STOPBITS_ONE) 

        except TypeError as e:
            print(self.ERR_STATEMENT)
            print(e)

    # constructor
    # opens a serial link to a known serial port      
    # define default arguments inside
    def __init__(self, port_name):
        try:
            self.FUNC_NAME = ".Ser_Iface()" # use this in exception handling messages
            self.ERR_STATEMENT = "Error: " + MOD_NAME_STR + self.FUNC_NAME
            
            # parameters to be passed to the serial open command
            self.dev_addr = port_name # string containing the port no. of the device
            self.baud_rate = 9600 # serial comms baud_rate
            self.read_timeout = 3 # timeout for reading data from the IBM4, units of second
            self.write_timeout = 0.5 # timeout for writing data to the IBM4, units of second
            
            # open the serial comms link to port_name
            self.instr_obj = serial.Serial(self.dev_addr, self.baud_rate, timeout = self.read_timeout, write_timeout = self.write_timeout, stopbits=serial.STOPBITS_ONE) 

        except TypeError as e:
            print(self.ERR_STATEMENT)
            print(e)
        except serial.SerialException as e:
            print(self.ERR_STATEMENT)
            print(e)

    # destructor            
    def __del__(self):
        # close the link to the instrument object when it goes out of scope
        if self.instr_obj.is_open:
            self.instr_obj.close()
            
    # return a string the describes the class
    def __str__(self):
        return "class for interfacing to an IBM4"
    
    # investigate the status of the serial comms link
    def comms_status(self):
        if self.instr_obj.is_open:
            print('Communication with: ',self.instr_obj.name,' is open')
            return True
        else:
            print('Communication with: ',self.instr_obj.name,' is not open')
            
    def FindIBM4(loud = False):
        # Goes through all listed serial ports looking for an IBM4
        # Once a port is found, return the port name
        # FHP 30 - 5 - 2024
    
        FUNC_NAME = ".FindIBM4()" # use this in exception handling messages
        ERR_STATEMENT = "Error: " + MOD_NAME_STR + FUNC_NAME
    
        try:
            if sys.platform.startswith('win'):
                ports = ['COM%s'%(i+1) for i in range(256)]
            elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
                # this excludes your current terminal "/dev/tty"
                ports = glob.glob('/dev/tty[A-Za-z]*')
            elif sys.platform.startswith('darwin'):
                ports = glob.glob('/dev/tty.*')
            else:
                ERR_STATEMENT = ERR_STATEMENT + '\nUnsupported platform'
                raise EnvironmentError('Unsupported platform')
        
            baud_rate = 9600
        
            IBM4Port = None # assign IBM4Port to None 

            for port in ports:
                try:
                    if loud: print('Trying: ',port)
                    s = serial.Serial(port, baud_rate, timeout = 0.05, write_timeout = 0.1, inter_byte_timeout = 0.1, stopbits=serial.STOPBITS_ONE)
                    s.write(b'*IDN\r\n')
                    response = s.read_until('\n',size=None)
                    Code=response.rsplit(b'\r\n')
                    if len(Code) > 2:
                        #if Code[1]==b'ISBY-UCC-RevA.1':
                        # test to see if Code[1] contains "ISBY" this is more generic
                        # will allow for updated rev. no. without necessitating a change in code
                        if "ISBY" in Code[1]:
                            if loud: print(f'IBM4 found at {port}')
                            IBM4Port = port
                            s.close()
                            break # stop the search for an IBM4 at the first one you find   
                except(OSError, serial.SerialException):
                    # Ignore the errors that arise from non-IBM4 serial ports
                    pass
        
            return IBM4Port
        except Exception as e:
            print(ERR_STATEMENT)
            print(e)
            
    # methods for writing data to the IBM4
    
    # methods for obtaining data from the IBM4
    
    # 