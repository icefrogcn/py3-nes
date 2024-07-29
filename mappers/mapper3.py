# -*- coding: UTF-8 -*-

from numba import jit
from numba.experimental import jitclass
from numba import int8,uint8,int16,uint16,uint32
import numba as nb
import numpy as np

import spec
from mmc import MMC
mapper_spec = []

@jitclass
class MAPPER(object):
    MMC: MMC
    def __init__(self,MMC = MMC()):
        self.MMC = MMC
        

    @property
    def RenderMethod(self):
        return 0
    
    @property
    def Mapper(self):
        return 3

    def reset(self):
        self.MMC.SetVROM_8K_Bank(0)
        if self.MMC.ROM.PROM_16K_SIZE == 1: # 16K only
            self.MMC.SetPROM_16K_Bank( 4, 0 )
            self.MMC.SetPROM_16K_Bank( 6, 0 )
            
        elif self.MMC.ROM.PROM_16K_SIZE == 2:	#// 32K
            self.MMC.SetPROM_32K_Bank( 0,1,2,3 )

        
        return 1

    def Write(self,addr,data):
        #print "Mapper Write",hex(Address),value
        self.MMC.SetVROM_8K_Bank( data & (data -1) )

    '''
    def ReadLow(self,address):#$4100-$7FFF Lower Memory read
        return self.MMC.ReadLow(address)

    def WriteLow(self,address,data): #$4100-$7FFF Lower Memory write
        self.MMC.WriteLow(address,data)
'''
    def Clock(self,sc):
        return False
    def HSync(self,scanline):
        return False



if __name__ == '__main__':
    mapper = MAPPER()











        
