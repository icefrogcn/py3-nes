# -*- coding: UTF-8 -*-
import time


import numpy as np
import numba as nb

from numba.experimental import jitclass
from numba import uint8,uint16,uint32
from numba.typed import Dict
from numba import types

from memory import Memory#,memory_type
from ppu_memory import PPU_Memory#,PPU_memory_type
from rom import ROM#,ROM_class_type

#PPU REGISTER


PPU_BGTBL_BIT = 0x10
PPU_SPTBL_BIT = 0x08

@jitclass#([('ver',uint8)])
class PPUBIT(object):
    ver:uint8
    def __init__(self):
        self.ver = 0
    # PPU Control Register #1	PPU #0 $2000


    @property
    def PPU_VBLANK_BIT(self):
        return 0x80
    @property
    def PPU_SPHIT_BIT(self):
        return 0x40		
    @property
    def PPU_SP16_BIT(self):
        return 0x20
    @property
    def PPU_BGTBL_BIT(self):
        return 0x10
    @property
    def PPU_SPTBL_BIT(self):
        return 0x08
    @property
    def PPU_INC32_BIT(self):
        return 0x04
    @property
    def PPU_NAMETBL_BIT(self):
        return 0x03

    # PPU Control Register #2	PPU #1 $2001
    @property
    def PPU_BGCOLOR_BIT(self):
        return 0xE0
    @property
    def PPU_SPDISP_BIT(self):
        return 0x10
    @property
    def PPU_BGDISP_BIT(self):
        return 0x08
    @property
    def PPU_SPCLIP_BIT(self):
        return 0x04
    @property
    def PPU_BGCLIP_BIT(self):
        return 0x02
    @property
    def PPU_COLORMODE_BIT(self):
        return 0x01

    # PPU Status Register	PPU #2 $2002
    @property
    def PPU_VBLANK_FLAG(self):
        return 0x80
    @property
    def PPU_SPHIT_FLAG(self):
        return 0x40
    @property
    def PPU_SPMAX_FLAG(self):
        return 0x20
    @property
    def PPU_WENABLE_FLAG(self):
        return 0x10

    # SPRITE Attribute
    @property
    def SP_VMIRROR_BIT(self):
        return 0x80
    @property
    def SP_HMIRROR_BIT(self):
        return 0x40
    @property
    def SP_PRIORITY_BIT(self):
        return 0x20
    @property
    def SP_COLOR_BIT(self):
        return 0x03



'''@jitclass([('bit',PPU_bit_type), \
           ('memory',PPU_memory_type), \
           ('reg',uint16[:]), \
           ('ROM',ROM_class_type), \
           ('VRAM',uint8[:]), \
           ('SpriteRAM',uint8[:]), \
           ('Palettes',uint8[:]), \
           ('RAM',uint8[:,:]) 
           ])'''

@jitclass
class PPUREG(object):
    bit:PPUBIT
    memory:PPU_Memory
    reg:uint16[:]
    ROM:ROM
    VRAM:uint8[:]
    SpriteRAM:uint8[:]
    Palettes:uint8[:]
    RAM:uint8[:,:]
    def __init__(self, memory = PPU_Memory(), ROM = ROM()):
        self.bit = PPUBIT()
        self.memory = memory
        self.reg = np.zeros(0x20, np.uint16) 
        self.VRAM = self.memory.VRAM 
        self.SpriteRAM = self.memory.SpriteRAM
        self.Palettes = self.memory.Palettes
        
        self.ROM = ROM
        self.RAM = self.memory.PRGRAM
        self.reg[9] = 1

    def read(self,address):
        if address == 0x2002:
            return self.PPUSTATUS
        elif address == 0x2004:
            return self.OAMDATA
        elif address == 0x2007:
            return self.PPUDATA
        else:
            return 0xFF
        
    def write(self,address,value):
        self.reg[8] = value
        addr = address & 0xFF
        if addr == 0:
            self.PPUCTRL_W(value)
        elif addr == 0x01:
            self.PPUMASK_W(value)
        elif addr == 0x02:
            pass
            #self.PPU7_Temp_W(value)
        elif addr == 0x03:
            self.OAMADDR_W(value)
        elif addr == 0x04:
            self.OAMDATA_W(value)
        elif addr == 0x05:
            self.PPUSCROLL_W(value)
        elif addr == 0x06:
            self.PPUADDR_W(value)
        elif addr == 0x07:
            self.PPUDATA_W(value)
        elif addr == 0x14:
            self.OAMDMA_W(value)
        
    @property
    def Mirroring(self):
        return self.ROM.Mirroring
    @property
    def MirrorXor(self):
        return self.ROM.MirrorXor

        
    @property       #2000
    def PPUCTRL(self):
        return self.reg[0]
    def PPUCTRL_W(self,value): 
        self.reg[0] = value

    @property
    def PPU_BGTBL_BIT(self):
        return self.PPUCTRL & PPU_BGTBL_BIT
        
    @property
    def PPU_SPTBL_BIT(self):
        return self.PPUCTRL & PPU_SPTBL_BIT
        
    @property
    def PPU_NAMETBL_BIT(self):
        return self.PPUCTRL & self.bit.PPU_NAMETBL_BIT
        
    @property       #2001
    def PPUMASK(self):
        return self.reg[1]
    def PPUMASK_W(self,value):
        self.reg[1] = value
        
    @property
    def PPUSTATUS(self):        #2002
        #ret = self.reg[2]
        ret = (self.PPU7_Temp & 0x1F) | self.reg[2]
        if ret & 0x80:
            self.reg[2] &= 0x60 #PPU_SPHIT_FLAG + PPU_SPMAX_FLAG
        return ret
        
    def PPUSTATUS_W(self,value):
        self.reg[2] = value
    def PPUSTATUS_ZERO(self):
        self.reg[2] = 0
        
        
    @property
    def OAMADDR(self):          #2003
        return self.reg[3]
    def OAMADDR_W(self,value):
        self.reg[3] = value
        
    @property
    def OAMDATA(self):          #2004
        data = self.PPU7_Temp
        self.reg[8] = self.SpriteRAM[self.reg[3]]
        self.reg[3] += 1
        self.reg[3] &= 0xFF
        return data
    def OAMDATA_W(self,value):
        self.SpriteRAM[self.OAMADDR] = value
        self.reg[3] = (self.reg[3] + 1) & 0xFF
        
    @property
    def ScrollToggle(self): #AddressIsHi #$2005-$2006 Toggle PPU56Toggle
        return self.reg[9]
    def ScrollToggle_W(self): 
        self.reg[9] = 0 if self.reg[9] else 1
    @property
    def HScroll(self): #HScroll
        return self.reg[10]
    @property
    def vScroll(self): #vScroll
        return self.reg[11]
    @property
    def AddressHi(self): #AddressHi
        return self.reg[12]

    def PPUSCROLL_W(self,value):#2005
        if self.ScrollToggle:
            self.reg[10] = value
        else:
            self.reg[11] = value
        self.ScrollToggle_W()
        #self.reg[5] = value
        
    @property
    def PPUADDR(self):          #2006
        return self.reg[6]
    
    def PPUADDR_W(self,value):
        if self.reg[9]:
            self.reg[12] = value << 8
        else:
            self.reg[6] = self.reg[12] | value
        self.ScrollToggle_W()
        #self.reg[6] = value
        
    @property
    def PPUDATA(self):          #2007 R
        data = self.PPU7_Temp
        addr = self.reg[6] & 0x3FFF
        self.reg[6] += 32 if self.reg[0] & 0x04 else 1
        if(addr >= 0x3000):
            if addr >= 0x3F00:
                data &= 0x3F
                return self.Palettes[addr & 0x1F]
            addr &= 0xEFFF
        else:
            self.reg[8] = self.VRAM[addr & 0x3FFF]
        self.reg[8] = 0xFF #self.VRAM[addr>>10][addr&0x03FF]
        
        return data
    
    def PPUDATA_W(self,value):  #2007 W
        self.PPU7_Temp_W(value)
        self.reg[6] &= 0x3FFF
        if self.PPUADDR >= 0x3F00:
            value &= 0x3F
            if self.PPUADDR & 0xF == 0:
                self.Palettes[0x0] = self.Palettes[0x10] = value
            elif self.PPUADDR & 0x10 == 0:
                self.Palettes[self.PPUADDR & 0xF] = value #BG
            else:
                self.Palettes[self.PPUADDR & 0x1F] = value #SP
            self.Palettes[0x04] = self.Palettes[0x08] = self.Palettes[0x0C] = self.Palettes[0x00]
            self.Palettes[0x10] = self.Palettes[0x14] = self.Palettes[0x18] = self.Palettes[0x1C] = self.Palettes[0x00]
            #self.Palettes[self.PPUADDR & 0x1F] = value
            #if self.PPUADDR & 3 == 0 and value:
            #    self.Palettes[(self.PPUADDR & 0x1F) ^ 0x10] = value
        else:
            self.VRAM[self.PPUADDR] = value
            if (self.PPUADDR & 0x3000) == 0x2000:
                self.VRAM[self.PPUADDR ^ self.ROM.MirrorXor] = value
            #self.VRAM[self.PPUADDR] = value
        
        self.reg[6] += 32 if self.reg[0] & 0x04 else 1
                                        #PPU_INC32_BIT

        
    @property
    def PPU7_Temp(self):            #reg[8]
        return self.reg[8]
    def PPU7_Temp_W(self,value):
        self.reg[8] = value

    
    #@property
    def OAMDMA_W(self,value):
        addr = value << 8
        self.SpriteRAM[0:0x100] = self.RAM[0,value * 0x100:value * 0x100 + 0x100]
        #for i in range(0x100):
            #self.SpriteRAM[i] = self.RAM[0,addr + i]

#PPU_reg_type = nb.deferred_type()
#PPU_reg_type.define(PPUREG.class_type.instance_type)

        

         
if __name__ == '__main__':
    pass
    #dd = jit_class_test()
    print(PPUBIT())
    print(PPUREG())
    #t1 = jit_class_test()
    #t2 = class_test()
    #start = time.time()
    #print t1.test
    #print time.time() - start
    #start = time.time()
    #print t2.test
    #print time.time() - start
   #reg.PPUCTRL_W(1)
    #print reg.PPUCTRL,reg.Palettes
    

    
    
    
    








        
