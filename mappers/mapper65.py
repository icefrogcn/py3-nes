# -*- coding: UTF-8 -*-
from numba import jit
from numba.experimental import jitclass
from numba import int8,uint8,int16,uint16,uint32
import numba as nb
import numpy as np

import spec
from mmc import MMC
mapper_spec = []

#Mapper065  Irem H3001


@jitclass
class MAPPER(object):
    MMC: MMC

    irq_enable: uint8
    irq_counter: uint16
    irq_latch:uint16
    
    patch: uint8
	
    def __init__(self,MMC = MMC()):
        self.MMC = MMC
        self.irq_enable = 0
        self.irq_counter = 0
        self.irq_latch = 0

        self.patch = 0
	
    @property
    def RenderMethod(self):
        return 0
    @property
    def Mapper(self):
        return 65

    def reset(self):

        self.patch = 0

        self.MMC.SetPROM_32K_Bank( 0, 1, self.MMC.PROM_8K_SIZE-2, self.MMC.PROM_8K_SIZE-1 );

        if( self.MMC.VROM_8K_SIZE ) :
            self.MMC.SetVROM_8K_Bank( 0 )
   
        self.irq_enable = 0
        self.irq_counter = 0


    
    def Write(self,addr,data):#$8000-$FFFF Memory write
        match addr:
            case 0x8000:
                self.MMC.SetPROM_8K_Bank( 4, data )

            case 0x9003:
                self.irq_enable = data & 0x80
                #clrIRQ
            case 0x9004:
                self.irq_counter = self.irq_latch
            case 0x9005:
                self.irq_latch = (self.irq_latch & 0x00FF)|(data<<8)
            case 0x9006:
                self.irq_latch = (self.irq_latch & 0xFF00)|data
            
            case  0xB000|0xB001|0xB002|0xB003|0xB004|0xB005|0xB006|0xB007:
                self.MMC.SetVROM_1K_Bank( addr & 0x0007, data )
                
            case  0xA000:
                self.MMC.SetPROM_8K_Bank( 5, data )
                
            case   0xC000:
                self.MMC.SetPROM_8K_Bank( 6, data )

    def HSync(self,scanline):
        pass
        #if patch

    def Clock(self, cycles):
        if not self.patch:
            if self.irq_enable:
                if self.irq_counter <= 0:
                    return True
                else:
                    self.irq_counter -= cycles
        return False
                    

if __name__ == '__main__':
    mapper = MAPPER()











        
