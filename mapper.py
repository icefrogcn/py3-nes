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
    MAPPER1:mapper1.MAPPER
    MAPPER2:mapper2.MAPPER
    MAPPER3:mapper3.MAPPER
    MAPPER4:mapper4.MAPPER
    MAPPER19:mapper19.MAPPER
    MAPPER23:mapper23.MAPPER
    #M_List:ListType(L)
    
    
    def __init__(self, MMC = MMC()):

        #self.VRAM = memory.VRAM
        self.MMC = MMC
        self.MAPPER0 = mapper0.MAPPER(self.MMC)
        self.MAPPER1 = mapper1.MAPPER(self.MMC)
        self.MAPPER2 = mapper2.MAPPER(self.MMC)
        self.MAPPER3 = mapper3.MAPPER(self.MMC)
        self.MAPPER4 = mapper4.MAPPER(self.MMC)
        self.MAPPER19 = mapper19.MAPPER(self.MMC)
        self.MAPPER23 = mapper23.MAPPER(self.MMC)
        #self.M_List.append(self.MAPPER0)
        #self.M_List.append(self.MAPPER2)
        
    @property
    def ROM(self):
        return self.MMC.ROM

    @property
    def Mapper(self):
        return self.MMC.Mapper

    @property
    def RenderMethod(self):
        return self.MMC.RenderMethod


    
    def reset(self):
        if self.Mapper == 0:
            self.MAPPER0.reset()
        
        elif self.Mapper == 1:
            self.MAPPER1.reset()

        elif self.Mapper == 2:
            self.MAPPER2.reset()
            
        elif self.Mapper == 3:
            self.MAPPER3.reset()
            
        elif self.Mapper == 4:
            self.MAPPER4.reset()
            
        elif self.Mapper == 19:
            self.MAPPER19.reset()

        elif self.Mapper == 23:
            self.MAPPER23.reset()

        print('reset mapper',self.Mapper)

    def Write(self,addr,data):#$8000-$FFFF Memory write
        if self.Mapper == 0:
            if hasattr(self.MAPPER0,'Write'):self.MAPPER0.Write(addr,data)
        
        elif self.Mapper == 1:
            if hasattr(self.MAPPER1,'Write'):self.MAPPER1.Write(addr,data)
        
        elif self.Mapper == 2:
            if hasattr(self.MAPPER2,'Write'):self.MAPPER2.Write(addr,data)
        
        elif self.Mapper == 3:
            self.MAPPER3.Write(addr,data)
            
        elif self.Mapper == 4:
            self.MAPPER4.Write(addr,data)
            
        elif self.Mapper == 19:
            self.MAPPER19.Write(addr,data)
            
        elif self.Mapper == 23:
            self.MAPPER23.Write(addr,data)
        else:
            #print('Write mapper',self.Mapper)
            pass
            
    def Read(self,address):#$8000-$FFFF Memory read(Dummy)
        try:
            if self.Mapper == 0:
                if hasattr(self.MAPPER0,'Read'):return self.MAPPER0.Read(address)
            
            elif self.Mapper == 2:
                if hasattr(self.MAPPER2,'Read'):return self.MAPPER2.Read(address)
                
            elif self.Mapper == 4:
                #print('Read mapper 4')
                return self.MAPPER4.Read(address)
        except:
            print(f'Read mapper {self.Mapper} Failed')
            return self.MMC.Read(address)
        

    def ReadLow(self,address):#$4100-$7FFF Lower Memory read
        if self.Mapper == 19:
            return self.MAPPER19.ReadLow(address)
        #print('ReadLow mapper 4')
        return self.MMC.ReadLow(address)

    def WriteLow(self,address,data): #$4100-$7FFF Lower Memory write
        if self.Mapper == 2:
            self.MAPPER2.WriteLow(address,data)
        elif self.Mapper == 19:
            self.MAPPER19.WriteLow(address,data)
        else:
            #print('WriteLow mapper 4')
            self.MMC.WriteLow(address,data)
    
    def ExRead(self,address): #$4018-$40FF Extention register read/write
        #print('ExRead mapper')
        return self.MMC.ExRead(address)
    
    def ExWrite(self, address, data ):
        #print('ExWrite mapper')
        self.MMC.ExWrite(address,data)
    
    def Clock(self, cycle ):
        if self.Mapper == 4:
            return self.MAPPER4.Clock(cycle)
        elif self.Mapper == 19:
            return self.MAPPER19.Clock(cycle)
        elif self.Mapper == 23:
            return self.MAPPER23.Clock(cycle)
        return False

    
    def HSync(self, scanline, ppuShow ):
        if self.Mapper == 4:
            return self.MAPPER4.HSync(scanline, ppuShow)
        return False

    #@property
    def MAPPERS(self,mapper):
        '''m = [self.MAPPER0,
        self.MAPPER1,
        self.MAPPER2,
        self.MAPPER3,
        self.MAPPER4,
        self.MAPPER19,
        self.MAPPER23
            ]'''
        
        if mapper == 0:
            m = self.MAPPER0
        elif mapper == 1:
            m = self.MAPPER1
        elif mapper == 2:
            m = self.MAPPER2
        elif mapper == 3:
            m = self.MAPPER3

        return m

    def resetn(self):
        self.MAPPERS().reset()



        
if __name__ == '__main__':
    #mapper = import_MAPPER()
    #print(mapper)
    from rom import LoadROM
    from mmu import MMU
    data = LoadROM('roms//kage.nes')
    MMU = MMU()
    MMU.ROM.data = data
    mmc = MMC(MMU)
    m = MAPPER(mmc)
    #m = MAPPER()
    



        
