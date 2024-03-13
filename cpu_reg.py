# -*- coding: UTF-8 -*-
import numpy as np
import numba as nb

from numba.experimental import jitclass
from numba import uint8,uint16
from numba.typed import Dict
from numba import types

C_FLAG = 0x01	#	// 1: Carry
Z_FLAG = 0x02	#	// 1: Zero
I_FLAG = 0x04	#	// 1: Irq disabled
D_FLAG = 0x08	#	// 1: Decimal mode flag (NES unused)
B_FLAG = 0x10	#	// 1: Break
R_FLAG = 0x20	#	// 1: Reserved (Always 1)
V_FLAG = 0x40	#	// 1: Overflow
N_FLAG = 0x80	#	// 1: Negative

reg_spec = [('PC',uint16),
            ('A',uint8),
            ('X',uint8),
            ('Y',uint8),
            ('S',uint8),
            ('P',uint16)
            ]

@jitclass(reg_spec)
class CPU_Reg(object):


    def __init__(self):
        #self.reg = np.zeros(0x20, np.uint16) 

        self.PC = 0          
        self.A = 0           
        self.X = 0            
        self.Y = 0             
        self.S = 0              
        self.P = 0 
        #self.savepc = 0
        #self.saveflags = 0
        #self.clockticks6502  = 0

    def status(self):
        return self.PC,self.A,self.X,self.Y,self.S,self.P
        
CPU_reg_type = nb.deferred_type()
CPU_reg_type.define(CPU_Reg.class_type.instance_type)
'''
reg = CPU_Reg()
@jitclass([('A',uint8),
           ])
class test(object):
    def __init__(self):
        pass
        self.A = 0
        #self.reg = reg

    def add1(self):
        #reg = self.reg
        pass
        reg.PC += 1
        '''
                    
if __name__ == '__main__':

    #reg = CPU_Reg()
    t = CPU_Reg()

    

    
    
    
    








        
