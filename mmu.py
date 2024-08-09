# -*- coding: UTF-8 -*-
import numpy as np
import numba as nb
from numba.experimental  import jitclass
from numba import uint8,uint16
from numba.typed import Dict,List
from numba.types import u1,u2,ListType
from numba import types

from rom import ROM

@jitclass
class MMU(object):
    RAM:uint8[:,:]
    ROM:ROM
    
    PPU_MEM_BANK:ListType(u1[::1])
    PPU_MEM_TYPE:uint8[:]

    WRAM:uint8[::1] #force array type C


    CRAM:uint8[::1] #force array type C
    VRAM:uint8[::1] #force array type C
    
    SpriteRAM:uint8[:]
    Palettes:uint8[:]

    CPUREG:uint8[:]

    NTArray:uint8[:,::1] #force array type C
    NT_BANK:ListType(u1[:,::1])

    #ATArray:uint8[:,::1] #force array type C
    
    ChannelWrite:uint8[:]    
    exsound_select:uint8

    def __init__(self):
        self.RAM = np.zeros((8,0x2000), np.uint8)
        self.ROM = ROM()
        self.WRAM = np.zeros(128*1024,np.uint8)
        self.CRAM = np.zeros(32*1024,np.uint8)
        self.VRAM = np.zeros(4*1024,np.uint8)
        self.PPU_MEM_BANK = List([np.zeros(0x400,np.uint8) for i in range(12)])
        self.PPU_MEM_TYPE = np.zeros(12,np.uint8)
        
        self.SpriteRAM = np.zeros(0x100,np.uint8)
        self.Palettes = np.zeros(0x20,np.uint8)

        self.CPUREG = np.zeros(0x18,np.uint8)
        
        self.NTArray = np.zeros((720, 768),np.uint8)
        #self.NT_BANK = List([np.zeros((240, 256),np.uint8) for i in range(4)])
        self.NT_BANK = List.empty_list(u1[:,::1])

        self.ChannelWrite = np.zeros(0x10,np.uint8)
        self.exsound_select = 0
    
    def reset(self):
        self.RAM[::] = 0
        self.WRAM[:] = 0
        self.CRAM[:] = 0
        self.VRAM[:] = 0
        self.PPU_MEM_TYPE[:] = 0
        self.SpriteRAM[:] = 0
        self.Palettes[:] = 0

        self.ChannelWrite[:] = 0
        self.exsound_select = 0
    
                    
if __name__ == '__main__':

    mem = MMU()


    

    
    
    
    








        
