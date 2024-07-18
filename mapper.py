# -*- coding: UTF-8 -*-

''' Functions for emulating MAPPER. 
'''

import sys
import traceback


from numba import jit
from numba import types, typed, typeof
from numba.experimental import jitclass
from numba import int8,uint8,int16,uint16
from numba.typed import Dict,List
from numba.types import u1,u2,ListType
import numpy as np
import numba as nb

from jitcompile import jitObject


from mmc import MMC

from mappers import *
#import mappers


@jitclass
class MAPPER(object):
    
    MMC:MMC
    MAPPER0:mapper0.MAPPER
    MAPPER2:mapper2.MAPPER
    #MAPPER4:mapper4.MAPPER
    #MAPPER3:mapper3.MAPPER
    #M_List:ListType(L)
    
    
    def __init__(self, MMC = MMC()):

        #self.VRAM = memory.VRAM
        self.MMC = MMC
        self.MAPPER0 = mapper0.MAPPER(self.MMC)
        self.MAPPER2 = mapper2.MAPPER(self.MMC)
        #self.M_List.append(self.MAPPER0)
        #self.M_List.append(self.MAPPER2)
        
    @property
    def Mapper(self):
        return self.MMC.Mapper

    @property
    def RenderMethod(self):
        return self.MMC.RenderMethod
    '''
    @property
    def Ma(self):
        if self.Mapper == 0:
            return self.MAPPER0
        
        else:# self.Mapper == 2:
            return self.MAPPER2
        #else:
        #    print('Unsupport mapper',self.Mapper)
            #return None
    '''

    
    def reset(self):
        if self.Mapper == 0:
            self.MAPPER0.reset()
        
        elif self.Mapper == 2:
            self.MAPPER2.reset()
        else:
            print('reset mapper',self.Mapper)

    def Write(self,addr,data):#$8000-$FFFF Memory write
        if self.Mapper == 0:
            if hasattr(self.MAPPER0,'Write'):self.MAPPER0.Write(addr,data)
        
        elif self.Mapper == 2:
            if hasattr(self.MAPPER2,'Write'):self.MAPPER2.Write(addr,data)
        #    self.Ma.Write(addr,data)
        else:
            print('Write mapper',self.Mapper)
        pass
            
    def Read(self,address):#$8000-$FFFF Memory read(Dummy)
        if self.Mapper == 0:
            if hasattr(self.MAPPER0,'Read'):return self.MAPPER0.Read(address)
        
        elif self.Mapper == 2:
            if hasattr(self.MAPPER2,'Read'):return self.MAPPER2.Read(address)
        
        #print('Read mapper',self.Mapper)
        return self.MMC.Read(address)
        pass

    def ReadLow(self,address):#$4100-$7FFF Lower Memory read
        return self.MMC.ReadLow(address)

    def WriteLow(self,address,data): #$4100-$7FFF Lower Memory write
        self.MMC.WriteLow(address,data)
    
    def ExRead(self,address): #$4018-$40FF Extention register read/write
        return 0
    
    def ExWrite(self, address, data ):
        pass
    
    def Clock(self, cycle ):
        return False
    def HSync(self, cycle ):
        return False

print('LOAD MAPPER')

if __name__ == '__main__':
    #mapper = import_MAPPER()
    #print(mapper)
    from rom import ROM ,nesROM
    mmc = MMC(nesROM().LoadROM('roms//1944.nes'))
    m = MAPPER(mmc)
    



        
