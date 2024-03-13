# -*- coding: UTF-8 -*-

from numba import jit
from numba.experimental import jitclass
from numba import int8,uint8,int16,uint16,uint32
import numba as nb
import numpy as np

#from main import cartridge


#@jitclass
class MAPPER:
    #cartridge: cartridge
    #RenderMethod: uint8
    
    def __init__(self,cartridge):
        self.cartridge = cartridge
        #self.RenderMethod = 0
        
    @property
    def RenderMethod(self):
        return 0
    @property
    def Mapper(self):
        return 0
    
    def reset(self):
        self.cartridge.SetVROM_8K_Bank(0)

        if self.cartridge.ROM.PROM_16K_SIZE == 1: # 16K only
            self.cartridge.SetPROM_16K_Bank( 4, 0 )
            self.cartridge.SetPROM_16K_Bank( 6, 0 )
            
        elif self.cartridge.ROM.PROM_16K_SIZE == 2:	#// 32K
            self.cartridge.SetPROM_32K_Bank( 0,1,2,3 )
        #print "RESET SUCCESS MAPPER ", self.Mapper

    def Write(self,address,data):
        pass
    def ReadLow(self,address):#$4100-$7FFF Lower Memory read
        return self.cartridge.ReadLow(address)

    def WriteLow(self,address,data):
        self.cartridge.WriteLow(address,data)

    def Clock(self, cycle ):
        return False
    def HSync(self,scanline):
        return False
#MAPPER_type = nb.deferred_type()
#MAPPER_type.define(MAPPER.class_type.instance_type)





if __name__ == '__main__':
    from main import cartridge
    mapper = MAPPER(cartridge())
    print(mapper)










        
