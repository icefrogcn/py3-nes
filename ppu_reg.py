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
    reg:uint16[:]
    loopy_x:uint16
    _loopy_v:uint16
    _loopy_t:uint16
    
    def __init__(self, MMU = MMU()):
        self.bit = PPUBIT()
        self.MMU = MMU
        self.reg = np.zeros(0x20, np.uint16) 
        
        #self.ROM = ROM
        
        self.ScrollToggle = 0
        self.loopy_x = 0
        self._loopy_v = 0
        self._loopy_t = 0
        
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
        self._loopy_v = 0
        self._loopy_t = 0
        
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
            self.PPUCTRL = value
        elif addr == 0x01:
            self.PPUMASK = value
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

    '''
    @property
    def Mirroring(self):
        return self.ROM.Mirroring
    @property
    def MirrorXor(self):
        return self.ROM.MirrorXor
'''
    def ver(self):
        print('ver')
        
    @property       #2000
    def PPUCTRL(self):
        return self.reg[0]
    @PPUCTRL.setter
    def PPUCTRL(self,value):
        # NT t:0001100 00000000 = d:00000011
        self.loopy_t = (self.loopy_t & 0xF3FF)|((value & 0x03)<<10)
        self.reg[12] = self.loopy_t
        self.reg[0] = value

    @property
    def PPU_BGTBL_BIT(self):
        return self.PPUCTRL & PPU_BGTBL_BIT
        
    @property
    def PPU_SPTBL_BIT(self):
        return self.PPUCTRL & PPU_SPTBL_BIT
        
    @property
    def PPU_NAMETBL(self):
        return self.PPUCTRL & PPU_NAMETBL_BIT
        
    @property       #2001
    def PPUMASK(self):
        return self.reg[1]
    @PPUMASK.setter
    def PPUMASK(self,value):
        self.reg[1] = value
        
    @property
    def PPUSTATUS(self):        #2002
        ret = self.reg[2]
        #ret = (self.PPU7_Temp & 0x1F) | self.reg[2]
        self.ScrollToggle = 0
        #if ret & 0x80:
        #    self.reg[2] &= 0x60 #PPU_SPHIT_FLAG + PPU_SPMAX_FLAG
        self.reg[2] &= 0x7F # cleared vblank after reading $2002  ~self.bit.PPU_VBLANK_FLAG
        return ret
    @PPUSTATUS.setter    
    def PPUSTATUS(self,value):
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
        temp = self.reg[9]
        self.reg[9] = 0 if self.reg[9] else 1
        return temp
    @ScrollToggle.setter
    def ScrollToggle(self,value):
        self.reg[9] = value
        
    def ScrollToggle_W(self): 
        self.reg[9] = 0 if self.reg[9] else 1
    @property
    def HScroll(self): #HScroll
        return self.reg[10]
    @property
    def vScroll(self): #vScroll
        return self.reg[11]

    
    @property
    def loopy_t(self): #AddressHi
        return self._loopy_t #reg[12]
    @loopy_t.setter
    def loopy_t(self,value):
        self._loopy_t = value #reg[12] = value



    def PPUSCROLL_W(self,value):#2005
        if self.ScrollToggle:       #w2
            self.reg[11] = value
            #tile Y t:0000001111100000=d:11111000
            self.loopy_t = (self.loopy_t & 0xFC1F)|((value & 0xF8) << 2)
            #scroll offset Y t:0111000000000000=d:00000111
            self.loopy_t = (self.loopy_t & 0x8FFF)|((value & 0x07) << 12)            
        else:                       #w1
            self.reg[10] = value
            self.loopy_t = (self.loopy_t & 0xFFE0)|(value >> 3)
            self.loopy_x = value & 0x07

        self.reg[12] = self.loopy_t
        #self.ScrollToggle_W()
        #self.reg[5] = value
        
    @property
    def PPUADDR(self):          #2006
        return self.reg[6]
    @property
    def loopy_v(self):
        return self._loopy_v #self.reg[6]
    @loopy_v.setter
    def loopy_v(self,value):
        self._loopy_v = value #reg[6] = value
    
    def PPUADDR_W(self,value):  #2006 W
        if self.ScrollToggle:   #w2
            self.reg[12] = (self.reg[12] & 0xFF00) | value
            self.reg[6] = self.reg[12] | value
            self.loopy_t = (self.loopy_t & 0xFF00) | value
            self.loopy_v = self.loopy_t
        else:                   #w1
            #self.reg[12] = value << 8
            self.reg[12] = (self.reg[12] & 0xFF)|((value & 0x3F) << 8)
            self.loopy_t = (self.loopy_t & 0x00FF)|((value & 0x3F) << 8)
        #self.ScrollToggle_W()
        #self.reg[6] = value
        
    @property
    def PPUDATA(self):          #2007 R
        data = self.PPU7_Temp
        addr = self.reg[6] & 0x3FFF
        addr = self.loopy_v & 0x3FFF
        self.reg[6] += 32 if self.reg[0] & 0x04 else 1
        self.loopy_v += 32 if self.reg[0] & 0x04 else 1
        if(addr >= 0x3000):
            if addr >= 0x3F00:
                data &= 0x3F
                return self.Palettes[addr & 0x1F]
            addr &= 0xEFFF
        #else:
            #self.reg[8] = self.VRAM[addr & 0x3FFF]
        self.reg[8] = self.PPU_MEM_BANK[addr>>10][addr&0x03FF]
        
        return data
    
    def PPUDATA_W(self,value):  #2007 W
        #self.PPU7_Temp_W(value)
        #self.reg[6] &= 0x3FFF
        vaddr = self.reg[6] & 0x3FFF
        vaddr = self.loopy_v & 0x3FFF
        self.reg[6] += 32 if self.reg[0] & 0x04 else 1
        self.loopy_v += 32 if self.reg[0] & 0x04 else 1
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
        
            #self.Palettes[self.PPUADDR & 0x1F] = value
            #if self.PPUADDR & 3 == 0 and value:
            #    self.Palettes[(self.PPUADDR & 0x1F) ^ 0x10] = value
        #else:
        #    self.VRAM[self.PPUADDR] = value
        #    if (self.PPUADDR & 0x3000) == 0x2000:
        #        self.VRAM[self.PPUADDR ^ self.ROM.MirrorXor] = value
            #self.VRAM[self.PPUADDR] = value
        
        if self.PPU_MEM_TYPE[vaddr>>10] != 0x00: #VRAM/CRAM
           self.PPU_MEM_BANK[vaddr>>10][vaddr&0x03FF] = value
            


        
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
    reg = PPUREG()
    print(reg)
    
    

    
    
    
    








        
