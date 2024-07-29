# -*- coding: UTF-8 -*-

''' Functions for emulating MAPPER. 
'''

import sys
import traceback
import ctypes


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
    MAPPER3:mapper3.MAPPER
    MAPPER4:mapper4.MAPPER
    #M_List:ListType(L)
    
    
    def __init__(self, MMC = MMC()):

        #self.VRAM = memory.VRAM
        self.MMC = MMC
        self.MAPPER0 = mapper0.MAPPER(self.MMC)
        self.MAPPER2 = mapper2.MAPPER(self.MMC)
        self.MAPPER3 = mapper3.MAPPER(self.MMC)
        self.MAPPER4 = mapper4.MAPPER(self.MMC)
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
            
        elif self.Mapper == 3:
            self.MAPPER3.reset()
            
        elif self.Mapper == 4:
            self.MAPPER4.reset()
        else:
            print('reset mapper',self.Mapper)

    def Write(self,addr,data):#$8000-$FFFF Memory write
        if self.Mapper == 0:
            if hasattr(self.MAPPER0,'Write'):self.MAPPER0.Write(addr,data)
        
        elif self.Mapper == 2:
            if hasattr(self.MAPPER2,'Write'):self.MAPPER2.Write(addr,data)
        
        elif self.Mapper == 3:
            self.MAPPER4.Write(addr,data)
        elif self.Mapper == 4:
            self.MAPPER4.Write(addr,data)
        else:
            print('Write mapper',self.Mapper)
        pass
            
    def Read(self,address):#$8000-$FFFF Memory read(Dummy)
        try:
            if self.Mapper == 0:
                if hasattr(self.MAPPER0,'Read'):return self.MAPPER0.Read(address)
            
            elif self.Mapper == 2:
                if hasattr(self.MAPPER2,'Read'):return self.MAPPER2.Read(address)
                
            elif self.Mapper == 4:
                return self.MAPPER4.Read(address)
        except:
            print(f'Read mapper {self.Mapper} Failed')
            return self.MMC.Read(address)
        

    def ReadLow(self,address):#$4100-$7FFF Lower Memory read
        return self.MMC.ReadLow(address)

    def WriteLow(self,address,data): #$4100-$7FFF Lower Memory write
        self.MMC.WriteLow(address,data)
    
    def ExRead(self,address): #$4018-$40FF Extention register read/write
        return 0
    
    def ExWrite(self, address, data ):
        pass
    
    def Clock(self, cycle ):
        if self.Mapper == 4:
            return self.MAPPER4.Clock(cycle)
        return False
    def HSync(self, cycle ):
        if self.Mapper == 4:
            return self.MAPPER4.HSync(cycle)
        return False

if __name__ == '__main__':
    #mapper = import_MAPPER()
    #print(mapper)
    from rom import ROM ,nesROM
    from mmu import MMU
    mmc = MMC(MMU(nesROM().LoadROM('roms//kage.nes')))
    m = MAPPER(mmc)
    



        
