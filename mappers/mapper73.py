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
        return 73

    
    def reset(self):
        self.MMC.SetPROM_32K_Bank(0,1,self.MMC.PROM_8K_SIZE-2,
                                    self.MMC.PROM_8K_SIZE-1)

	#patch = 0
            

     
    def Write(self,addr,data):#$8000-$FFFF Memory write
        if addr == 0xF000:
            self.MMC.SetPROM_16K_Bank(4, data )



if __name__ == '__main__':
    mapper = MAPPER()











        
