# -*- coding: UTF-8 -*-
import time


import numpy as np
import numba as nb

from numba.experimental import jitclass
from numba import uint8,uint16,uint32
from numba.typed import Dict
from numba import types

from mmu import MMU


#PPU REGISTER


PPU_BGTBL_BIT = 0x10
PPU_SPTBL_BIT = 0x08
PPU_INC32_BIT = 0x04
PPU_NAMETBL_BIT = 0x03


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
        return uint8(0x80)
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


@jitclass
class PPUREG(object):
    bit:PPUBIT
    MMU:MMU
    reg:uint8[:]
    loopy_x:uint16
    loopy_v:uint16
    loopy_t:uint16

    PPU56Toggle:uint8

    PPU7_Temp:uint8
    
    #PPU_ADDR_INC:uint16

    HScroll:uint8
    vScroll:uint8
    
    def __init__(self, MMU = MMU()):
        self.bit = PPUBIT()
        self.MMU = MMU
        self.reg = np.zeros(0x4, np.uint8) 
        
        self.PPU56Toggle = 0
        
        self.loopy_x = 0
        self.loopy_v = 0
        self.loopy_t = 0
        
        #self.PPU_ADDR_INC = 0

        self.PPU7_Temp = 0xFF

        self.HScroll = 0
        self.vScroll = 0
    
    @property
    def RAM(self):
        return self.MMU.RAM 

    @property
    def VRAM(self):
        return self.MMU.VRAM 

    @property
    def SpriteRAM(self):
        return self.MMU.SpriteRAM
    @property
    def Palettes(self):
        return self.MMU.Palettes 

    @property
    def PPU_MEM_BANK(self):
        return self.MMU.PPU_MEM_BANK
    @property
    def PPU_MEM_TYPE(self):
        return self.MMU.PPU_MEM_TYPE
    
    def reset(self):
        self.reg[:] = 0
        self.ScrollToggle = 0
        self.loopy_x = 0
        self.loopy_v = 0
        self.loopy_t = 0
        self.PPU7_Temp = 0x00

        
    def read(self,address):
        addr = address & 0xFF
        if addr == 0x02:
            return self.PPUSTATUS
        elif addr == 0x04:
            return self.OAMDATA
        elif addr == 0x07:
            return self.PPUDATA
        else:
            '2000,2001,2003,2005,2006'
            return self.PPU7_Temp
        
    def write(self,address,value):
        #self.reg[8] = value
        addr = address & 0xFF
        if addr == 0:               
            self.PPUCTRL = value
        elif addr == 0x01:
            self.PPUMASK = value
        elif addr == 0x02:
            pass
        elif addr == 0x03:
            self.OAMADDR = value
        elif addr == 0x04:
            self.OAMDATA = value
        elif addr == 0x05:
            self.PPUSCROLL_W(value)
        elif addr == 0x06:
            self.PPUADDR_W(value)
        elif addr == 0x07:
            self.PPUDATA_W(value)
        elif addr == 0x14:
            self.OAMDMA_W(value)

       
    @property       #2000
    def PPUCTRL(self):
        return self.reg[0]
    @PPUCTRL.setter
    def PPUCTRL(self,value):
        ' NT t:0001100 00000000 = d:00000011  '
        self.loopy_t = (self.loopy_t & 0xF3FF)|((value & 0x03)<<10)
        self.reg[0] = value
        #self.PPU_ADDR_INC = 32 if value & 0x04 else 1

    @property
    def PPU_BGTBL_BIT(self):
        return self.PPUCTRL & PPU_BGTBL_BIT
    @property
    def PPU_SPTBL_BIT(self):
        return self.PPUCTRL & PPU_SPTBL_BIT
    @property
    def PPU_NAMETBL(self):
        return self.PPUCTRL & PPU_NAMETBL_BIT
    @property
    def PPU_ADDR_INC(self):
        return 32 if self.PPUCTRL & 0x04 else 1
        
        
    @property       #2001
    def PPUMASK(self):
        return self.reg[1]
    @PPUMASK.setter
    def PPUMASK(self,value):
        self.reg[1] = value
        
    @property
    def PPUSTATUS(self):        #2002
        ret = self.reg[2] 
        self.ScrollToggle = 0   # clear toggle
        self.reg[2] &= 0x7F     # cleared vblank after reading $2002  ~self.bit.PPU_VBLANK_FLAG
        return ret
    @PPUSTATUS.setter    
    def PPUSTATUS(self,value):
        self.reg[2] = value
    def PPUSTATUS_ZERO(self):
        self.reg[2] = 0
        
    'SPR-RAM Address Register(W)'
    @property
    def OAMADDR(self):          #2003
        return self.reg[3]
    @OAMADDR.setter
    def OAMADDR(self,value):
        self.reg[3] = value
        
    @property
    def OAMDATA(self):          #2004
        data = self.SpriteRAM[self.OAMADDR]
        self.OAMADDR += 1
        self.OAMADDR &= 0xFF
        return data
    @OAMADDR.setter
    def OAMDATA(self,value):
        self.SpriteRAM[self.OAMADDR] = value
        self.OAMADDR = (self.OAMADDR + 1) & 0xFF
        
    @property
    def ScrollToggle(self): #AddressIsHi #$2005-$2006 Toggle PPU56Toggle
        temp = self.PPU56Toggle
        self.PPU56Toggle = 0 if self.PPU56Toggle else 1
        return temp
    @ScrollToggle.setter
    def ScrollToggle(self,value):
        self.PPU56Toggle = value
        

    def PPUSCROLL_W(self,value):#2005
        if self.ScrollToggle:       #w2
            self.vScroll = value
            'tile Y t:0000001111100000=d:11111000'
            self.loopy_t = (self.loopy_t & 0xFC1F)|((value & 0xF8) << 2)
            'scroll offset Y t:0111000000000000=d:00000111'
            self.loopy_t = (self.loopy_t & 0x8FFF)|((value & 0x07) << 12)            
        else:                       #w1
            self.HScroll = value
            'tile X t:0000000000011111=d:11111000'
            self.loopy_t = (self.loopy_t & 0xFFE0)|(value >> 3)
            'scroll offset X x=d:00000111'
            self.loopy_x = value & 0x07

        
    @property
    def PPUADDR(self):          #2006
        return self.reg[6]
    
    def PPUADDR_W(self,value):  #2006 W
        if self.ScrollToggle:   #w2
            't:0000000011111111 = d:11111111'
            self.loopy_t = (self.loopy_t & 0xFF00) | value
            'v = t'
            self.loopy_v = self.loopy_t
        else:                   #w1
            't:0011111100000000 = d:00111111'
            't:1100000000000000 = 0'
            self.loopy_t = (self.loopy_t & 0x00FF)|((value & 0x3F) << 8)
        

        
    @property
    def PPUDATA(self):          #2007 R
        data = self.PPU7_Temp
        addr = self.loopy_v & 0x3FFF
        self.loopy_v += self.PPU_ADDR_INC#32 if self.reg[0] & 0x04 else 1
        if(addr >= 0x3000):
            if addr >= 0x3F00:
                data &= 0x3F
                return self.Palettes[addr & 0x1F]
            addr &= 0xEFFF


        self.PPU7_Temp = self.PPU_MEM_BANK[addr>>10][addr&0x03FF]
        
        return data
    
    def PPUDATA_W(self,value):  #2007 W

        vaddr = self.loopy_v & 0x3FFF

        self.loopy_v += self.PPU_ADDR_INC#32 if self.reg[0] & 0x04 else 1
                                        #PPU_INC32_BIT
        if vaddr >= 0x3000:
            if vaddr >= 0x3F00:
                value &= 0x3F
                if vaddr & 0xF == 0:
                    self.Palettes[0x0] = self.Palettes[0x10] = value
                elif vaddr & 0x10 == 0:
                    self.Palettes[vaddr & 0xF] = value #BG
                else:
                    self.Palettes[vaddr & 0x1F] = value #SP
                self.Palettes[0x04] = self.Palettes[0x08] = self.Palettes[0x0C] = self.Palettes[0x00]
                self.Palettes[0x10] = self.Palettes[0x14] = self.Palettes[0x18] = self.Palettes[0x1C] = self.Palettes[0x00]
                return
            vaddr &=0xEFFF
        
        
        if self.PPU_MEM_TYPE[vaddr>>10] != 0x00: #VRAM/CRAM
           self.PPU_MEM_BANK[vaddr>>10][vaddr&0x03FF] = value
            

    #@property
    def OAMDMA_W(self,value):
        addr = value << 8
        self.SpriteRAM[0:0x100] = self.RAM[0,value * 0x100:value * 0x100 + 0x100]


         
if __name__ == '__main__':
    pass
    print(PPUBIT())
    reg = PPUREG()
    print(reg)
    
    

    
    
    
    








        
