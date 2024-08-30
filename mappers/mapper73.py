# -*- coding: UTF-8 -*-
from numba import jit
from numba.experimental import jitclass
from numba import int8,uint8,int16,uint16,uint32
import numba as nb
import numpy as np

import spec
from mmc import MMC
mapper_spec = []

#Mapper073  Konami VRC3
@jitclass
class MAPPER(object):
    MMC: MMC
    
    irq_enable:uint8
    irq_counter:uint32
    
    def __init__(self,MMC = MMC()):
        self.MMC = MMC

        self.irq_enable = 0
        self.irq_counter = 0

    @property
    def RenderMethod(self):
        return 0
    @property
    def Mapper(self):
        return 73

    
    def reset(self):

        self.irq_enable = 0
        self.irq_counter = 0
        
        self.MMC.SetPROM_32K_Bank(0,1,self.MMC.PROM_8K_SIZE-2,
                                    self.MMC.PROM_8K_SIZE-1)


            

     
    def Write(self,addr,data):#$8000-$FFFF Memory write
        match addr :
            case 0xF000:
                self.MMC.SetPROM_16K_Bank(4, data )
            case 0x8000:
                self.irq_counter = (self.irq_counter & 0xFFF0)|(data & 0xF)
            case 0x9000:
                self.irq_counter = (self.irq_counter & 0xFF0F)|((data & 0xF)<<4)
            case 0xA000:
                self.irq_counter = (self.irq_counter & 0xF0FF)|((data & 0xF)<<8)
            case 0xB000:
                self.irq_counter = (self.irq_counter & 0x0FFF)|((data & 0xF)<<12)
            case 0xC000:
                self.irq_enable = data & 0x02
            case 0xD000:
                pass


    def Clock(self, cycles):
        if self.irq_enable:
            self.irq_counter += cycles
            if self.irq_counter >= 0xFFFF:
                self.irq_enable = 0
                self.irq_counter &= 0xFFFF
                return True


if __name__ == '__main__':
    mapper = MAPPER()











        
