# -*- coding: UTF-8 -*-
from numba import jit
from numba.experimental import jitclass
from numba import int8,uint8,int16,uint16,uint32
import numba as nb
import numpy as np

from main import MAPPER, MAIN_class_type


spec = [('cartridge',MAIN_class_type),
        ('RenderMethod',uint8)              
        ]
@jitclass(spec)
class MAPPER(object):

    def __init__(self,cartridge=MAPPER()):
        self.cartridge = cartridge
        self.RenderMethod = 0

    @property
    def Mapper(self):
        return 2
    
    def reset(self):
        self.cartridge.SetPROM_32K_Bank(0, 1, self.cartridge.ROM.PROM_8K_SIZE - 2, self.cartridge.ROM.PROM_8K_SIZE - 1)

        patch = 0

        return 1
    def Clock(self,cycles):
        return False
    def HSync(self,scanline):
        return False 
    
    def Write(self,addr,data):#$8000-$FFFF Memory write
        self.cartridge.SetPROM_16K_Bank(4, data )

    def ReadLow(self,address):#$4100-$7FFF Lower Memory read
        return self.cartridge.ReadLow(address)

    def WriteLow(self,address,data): #$4100-$7FFF Lower Memory write
        self.cartridge.WriteLow(address,data)

MAPPER_type = nb.deferred_type()
MAPPER_type.define(MAPPER.class_type.instance_type)


if __name__ == '__main__':
    mapper = MAPPER()











        
