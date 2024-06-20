# -*- coding: UTF-8 -*-

''' Functions for emulating MMCs. Select8KVROM and the
'''

import sys
import traceback


from numba import jit
from numba import types, typed
from numba.experimental import jitclass
from numba import int8,uint8,int16,uint16
import numpy as np
import numba as nb


from jitcompile import jitObject

from rom import ROM #,ROM_class_type
from memory import Memory

POST_ALL_RENDER = 0
PRE_ALL_RENDER  = 1
POST_RENDER     = 2
PRE_RENDER      = 3
TILE_RENDER     = 4


__all__ = [#'MAPPER',
           'POST_ALL_RENDER',
           'PRE_ALL_RENDER',
           'POST_RENDER',
           'PRE_RENDER',
           'TILE_RENDER'
           ]
#MAPPER

MMC_spec = [('ROM',ROM), \
           ('PROM_SIZE_array',uint8[:]), \
           ('VROM_SIZE_array',uint8[:]), \
           ('PRGRAM',uint8[:,:]), \
           ('VRAM',uint8[:]), \
           ('PROM',uint8[:]), \
           ('VROM',uint8[:]), \
           ('RenderMethod',uint8)
           ]


'''
@jitclass()'''
@jitclass
class MMC(object):
    
    ROM: ROM
    PROM_SIZE_array: uint8[:]
    VROM_SIZE_array: uint8[:]
    PRGRAM: uint8[:,:]
    VRAM: uint8[:]
    PROM: uint8[:]
    VROM: uint8[:]
    RenderMethod: uint8
    
    def __init__(self, ROM = ROM(), memory = Memory()):

        self.ROM = ROM

        self.PROM_SIZE_array = ROM.PROM_SIZE_array
        self.VROM_SIZE_array = ROM.VROM_SIZE_array
      
        self.PRGRAM = memory.RAM
        self.VRAM = memory.VRAM
        self.PROM = ROM.PROM
        self.VROM = ROM.VROM

        self.RenderMethod = POST_ALL_RENDER

    @property
    def Mapper(self):
        return self.ROM.Mapper
    @property
    def Mirroring(self):
        return self.ROM.Mirroring
    @property
    def MirrorXor(self):
        return self.ROM.MirrorXor

    @property
    def PROM_8K_SIZE(self):
        return self.ROM.PROM_8K_SIZE
    @property
    def PROM_16K_SIZE(self):
        return self.ROM.PROM_16K_SIZE
    @property
    def PROM_32K_SIZE(self):
        return self.ROM.PROM_32K_SIZE

    @property
    def VROM_1K_SIZE(self):
        return self.ROM.VROM_1K_SIZE
    @property
    def VROM_2K_SIZE(self):
        return self.ROM.VROM_2K_SIZE
    @property
    def VROM_4K_SIZE(self):
        return self.ROM.VROM_4K_SIZE





    
    def MirrorXor_W(self,value):
        self.ROM.MirrorXor_W(value)    
    def Mirroring_W(self,value):
        self.ROM.Mirroring_W(value)  
        
    def reset(self):
        pass
        

    def Write(self,addr,data):#$8000-$FFFF Memory write
        pass

    def Read(self,address):#$8000-$FFFF Memory read(Dummy)
        return self.PRGRAM[addr>>13,address & 0x1FFF]

    def ReadLow(self,address):#$4100-$7FFF Lower Memory read
        if( address >= 0x6000 ):
            return self.PRGRAM[3, address & 0x1FFF]
        return address>>8

    def WriteLow(self,address,data): #$4100-$7FFF Lower Memory write
        #$6000-$7FFF WRAM
        if( address >= 0x6000 ) :
            self.PRGRAM[3, address & 0x1FFF] = data
    
    def ExRead(self,address): #$4018-$40FF Extention register read/write
        return 0
    
    def ExWrite(self, address, data ):
        pass
    
    def Clock(self, cycle ):
        return False
    def HSync(self, cycle ):
        return False
    

    def SetPROM_8K_Bank(self, page, bank):
        
        bank %= self.ROM.PROM_8K_SIZE
        self.PRGRAM[page] = self.PROM[0x2000 * bank : 0x2000 * bank + 0x2000]

        
            
    def SetPROM_16K_Bank(self,page, bank):
        self.SetPROM_8K_Bank( page+0, bank*2+0 )
        self.SetPROM_8K_Bank( page+1, bank*2+1 )
        
    def SetPROM_32K_Bank0(self,bank):
        self.SetPROM_8K_Bank( 4, bank*4 + 0 )
        self.SetPROM_8K_Bank( 5, bank*4 + 1 )
        self.SetPROM_8K_Bank( 6, bank*4 + 2 )
        self.SetPROM_8K_Bank( 7, bank*4 + 3 )

    def SetPROM_32K_Bank(self,bank0,bank1,bank2,bank3):
        self.SetPROM_8K_Bank( 4, bank0 )
        self.SetPROM_8K_Bank( 5, bank1 )
        self.SetPROM_8K_Bank( 6, bank2 )
        self.SetPROM_8K_Bank( 7, bank3 )
	


    def SetCRAM_1K_Bank(self, page, bank):
        #print "Set CRAM"
        bank &= 0x1F
        #CRAM = 0x8000 + 0x0400 * bank
        CRAM = 0x0400 * (bank & 0x7)
        self.VRAM[page*0x400:page*0x400 + 0x400] = self.PRGRAM[(bank & 0x18 >> 3) + 4][CRAM:CRAM + 0x400]

    def SetVRAM_1K_Bank(self, page, bank):
        #print "Set VRAM"
        bank &= 0x3
        VRAM = 0x0400 * bank + 4096
        self.VRAM[page*0x400:page*0x400 + 0x400] = self.VRAM[VRAM:VRAM + 0x400]

    def SetVROM_8K_Bank(self,bank):
        for i in range(8):
            self.SetVROM_1K_Bank( i, bank * 8 + i )

    def SetVROM_8K_Bank8(self, bank0, bank1, bank2, bank3,
			 bank4, bank5, bank6, bank7 ):
        self.SetVROM_1K_Bank( 0, bank0)
        self.SetVROM_1K_Bank( 1, bank1)
        self.SetVROM_1K_Bank( 2, bank2)
        self.SetVROM_1K_Bank( 3, bank3)
        self.SetVROM_1K_Bank( 4, bank4)
        self.SetVROM_1K_Bank( 5, bank5)
        self.SetVROM_1K_Bank( 6, bank6)
        self.SetVROM_1K_Bank( 7, bank7)

        

    def SetVROM_4K_Bank(self, page, bank):
        self.SetVROM_1K_Bank( page+0, bank*4+0 );
        self.SetVROM_1K_Bank( page+1, bank*4+1 );
        self.SetVROM_1K_Bank( page+2, bank*4+2 );
        self.SetVROM_1K_Bank( page+3, bank*4+3 );

    def SetVROM_2K_Bank(self, page, bank):
        self.SetVROM_1K_Bank( page+0, bank*2+0 );
        self.SetVROM_1K_Bank( page+1, bank*2+1 );

    def SetVROM_1K_Bank(self, page, bank):
        #print (bank,self.ROM.VROM_1K_SIZE)
        bank %= self.ROM.VROM_1K_SIZE
        self.VRAM[page*0x400:page*0x400 + 0x400] = self.VROM[0x0400*bank:0x0400*bank + 0x400]


def MMC_spec():
    MMC_type = nb.deferred_type()
    MMC_type.define(MMC.class_type.instance_type)
    addition_spec = {
            'MMC': MMC_type,
            }
    return addition_spec

def import_MAPPER(mapper = 0, jit = True):
    mapper_mod = __import__('mappers.mapper%d' %mapper, fromlist=['MAPPER','mapper_spec'])

    return jitObject(mapper_mod.MAPPER, mapper_mod.mapper_spec, MMC_spec(), jit = jit) 

def load_MAPPER(consloe, jit = True):
    mapper_class, mapper_type = import_MAPPER(mapper = consloe.ROM.Mapper, jit = jit)

    mapper = mapper_class(MMC(consloe.ROM, consloe.memory))
    return mapper, mapper_type

if __name__ == '__main__':
    print(import_MAPPER())
    



        
