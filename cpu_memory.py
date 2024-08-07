# -*- coding: UTF-8 -*-
import numpy as np
import numba as nb
from numba.experimental import jitclass
from numba import uint8,uint16

from mmu import MMU

'''@jitclass([('memory',memory_type), \
           ('RAM',uint8[:,:]), \
           #('PRGRAM',uint8[:,:]), \
           #('Sound',uint8[:]) \
           ])'''
@jitclass
class CPU_Memory(object):
    
    MMU:MMU
    #RAM:uint8[:,:]

    def __init__(self, MMU = MMU()):
        self.MMU = MMU
        #self.RAM = self.MMU.RAM

        #self.bank0 = self.RAM[0] #  RAM 
        #self.bank6 = self.RAM[3] #  SaveRAM 
        #self.bank8 = self.RAM[4] #  8-E are PRG-ROM
        #self.bankA = self.RAM[5] # 
        #self.bankC = self.RAM[6] # 
        #self.bankE = self.RAM[7] # 

    @property
    def RAM(self):
        return self.MMU.RAM
    
    def Read(self,address):
        bank = address >> 13
        value = 0
        if bank == 0x00:                        # Address >=0x0 and Address <=0x1FFF:
            return self.RAM[0, address & 0x7FF]
        elif bank > 0x03:                       # Address >=0x8000 and Address <=0xFFFF
            return self.RAM[bank, address & 0x1FFF]

    def write(self,address):
        pass

#CPU_Memory_type = nb.deferred_type()
#CPU_Memory_type.define(CPU_Memory.class_type.instance_type)
        

                    
if __name__ == '__main__':

    ram = CPU_Memory()

    

    
    
    
    








        
