# -*- coding: UTF-8 -*-
import numpy as np
import numba as nb
from numba.experimental  import jitclass
from numba import uint8,uint16
from numba.typed import Dict,List
from numba.types import u1,u2,ListType
from numba import types

from jitcompile import jitObject,jitType

from rom import ROM

@jitclass
class MMU(object):
    RAM:uint8[:,:]
    ROM:ROM
    
    PPU_MEM_BANK:ListType(uint8[::1])
    PPU_MEM_TYPE:uint8[:]

    WRAM:uint8[::1] #force array type C


    CRAM:uint8[::1] #force array type C
    VRAM:uint8[::1] #force array type C
    
    SpriteRAM:uint8[:]
    Palettes:uint8[:]

    CPUREG:uint8[:]

    NTArray:uint8[:,::1] #force array type C
    NT_BANK:ListType(uint8[:,::1])

    #ATArray:uint8[:,::1] #force array type C
    
    ChannelWrite:uint8[:]    
    SoundWrite:uint8[:]    
    exsound_select:uint8

    dpcm_value:uint8
        
    def __init__(mmu):
        mmu.RAM = np.zeros((8,0x2000), np.uint8)
        mmu.ROM = ROM()
        mmu.WRAM = np.zeros(128*1024,np.uint8)
        mmu.CRAM = np.zeros(32*1024,np.uint8)
        mmu.VRAM = np.zeros(4*1024,np.uint8)
        mmu.PPU_MEM_BANK = List([np.zeros(0x400,np.uint8) for i in range(12)])
        mmu.PPU_MEM_TYPE = np.zeros(12,np.uint8)
        
        mmu.SpriteRAM = np.zeros(0x100,np.uint8)
        mmu.Palettes = np.zeros(0x20,np.uint8)

        mmu.CPUREG = np.zeros(0x18,np.uint8)
        
        mmu.NTArray = np.zeros((720, 768),np.uint8)
        #mmu.NT_BANK = List([np.zeros((240, 256),np.uint8) for i in range(4)])
        mmu.NT_BANK = List.empty_list(u1[:,::1])

        mmu.ChannelWrite = np.zeros(0x10,np.uint8)
        mmu.SoundWrite = np.zeros(0x18,np.uint8)
        mmu.exsound_select = uint8(0)
    
    def reset(mmu):
        mmu.RAM[::] = 0
        mmu.WRAM[:] = 0
        mmu.CRAM[:] = 0
        mmu.VRAM[:] = 0
        mmu.PPU_MEM_TYPE[:] = 0
        mmu.SpriteRAM[:] = 0
        mmu.Palettes[:] = 0

        mmu.ChannelWrite[:] = 0
        mmu.exsound_select = 0


    def read(mmu,addr):
        return mmu.RAM[addr>>13][addr & 0x1FFF]


        
def jit_MMU_class(jit = 1):
    return jitObject(MMU, [] , jit = jit)

if __name__ == '__main__':
    
    #mmu = jit_MMU_class(1)()
    mmu =MMU()
    print(mmu)


    

    
    
    
    








        
