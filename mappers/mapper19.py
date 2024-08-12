# -*- coding: UTF-8 -*-

import sys

from numba import jit
from numba.experimental import jitclass
from numba import int8,uint8,int16,uint16,uint32
import numba as nb
import numpy as np

import spec
from mmc import MMC

mapper_spec = [#('MMC',MMC_type),
        ('reg',uint8[:]),
        ('exram',uint8[:]),
        ('irq_enable',uint8),
        ('irq_counter',uint8),
        ('exsound_enable',uint8),
        ('patch',uint8),
        ('RenderMethod',uint8)        
        ]
@jitclass()
class MAPPER(object):
    MMC: MMC
    reg:uint8[:]
    exram:uint8[:]
    
    irq_enable:uint8
    irq_counter:uint16
    
    exsound_enable:uint8
    patch:uint8
    
    RenderMethod:uint8
    
    def __init__(self,MMC = MMC()):
        self.MMC = MMC

        self.patch = 0
        self.exsound_enable = 0
    
        self.reg = np.zeros(0x3, np.uint8)
        self.exram = np.zeros(128, np.uint8)
        self.irq_enable = 0
        self.irq_counter = 0

        self.RenderMethod = 0#POST_RENDER

    @property
    def Mapper(self):
        return 19    

    def reset(self):
        
        self.MMC.SetPROM_32K_Bank(0, 1, self.MMC.PROM_8K_SIZE-2, self.MMC.PROM_8K_SIZE-1 )

        if( self.MMC.VROM_1K_SIZE >= 8 ):
            self.MMC.SetVROM_8K_Bank( self.MMC.VROM_8K_SIZE - 1 )
            
        self.exsound_enable = 0xFF

        if self.exsound_enable:
            self.MMC.SelectExSound(0x10)

        self.reg[:] = 0
        return 1

    def ReadLow(self,address):
        #print "ReadLow 19"
        addr = address & 0xF800
        if addr in (0x6000,0x6800,0x7000,0x7800):
            return self.MMC.ReadLow(address)
        
        elif addr == 0x4800:
            if self.exsound_enable:
                self.MMC.ExRead(address)
                data = self.exram[self.reg[2]&0x7F]
            else:
                data = self.MMC.WRAM[self.reg[2]&0x7F]
            if self.reg[2]&0x80:
                self.reg[2] = (self.reg[2] + 1 )|0x80
            return data
        elif addr == 0x5000:
            return uint8(self.irq_counter & 0x00FF)
        elif addr == 0x5800:
            return uint8((self.irq_counter >> 8 ) & 0x7F)
            
        return uint8(addr>>8)
            
    def WriteLow(self,address,data):
        #print "WriteLow 19"
        addr = address & 0xF800
        
        if addr == 0x4800:
            if self.exsound_enable:
                self.MMC.ExWrite(address, data )
                self.exram[self.reg[2]&0x7F] = data
            else:
                self.MMC.WRAM[self.reg[2]&0x7F] = data
            if self.reg[2]&0x80:
                self.reg[2] = (self.reg[2] + 1 )|0x80
                self.reg[2] = ((self.reg[2] & 0x7F) + 1 )|0x80
            
        elif addr == 0x5000:
            self.irq_counter = (self.irq_counter & 0xFF00) | uint16(data)
            #if self.irq_enable:            #----- remove
                #self.irq_counter += 1
                
        elif addr == 0x5800:
            #print "irq_enable try"
            self.irq_counter = (self.irq_counter & 0x00FF) | uint16((data & 0x7F) << 8)
            self.irq_enable  = data & 0x80
            #if self.irq_enable:             #----- remove
                #self.irq_counter += 1
                
            
        elif addr in (0x6000,0x6800,0x7000,0x7800):
            return self.MMC.WriteLow(address,data)
        
    def Write(self,address,data):#$8000-$FFFF Memory write
        addr = address & 0xF800

        if addr == 0x8000:
            if ( (data < 0xE0) or (self.reg[0] != 0) ):
                self.MMC.SetVROM_1K_Bank( 0, data )
            else:
                self.MMC.SetCRAM_1K_Bank( 0, data&0x1F )
                
        elif addr == 0x8800:
            if ( (data < 0xE0) or (self.reg[0] != 0) ):
                self.MMC.SetVROM_1K_Bank( 1, data )
            else:
                self.MMC.SetCRAM_1K_Bank( 1, data&0x1F )
                
        elif addr == 0x9000:
            if ( (data < 0xE0) or (self.reg[0] != 0) ):
                self.MMC.SetVROM_1K_Bank( 2, data )
            else:
                self.MMC.SetCRAM_1K_Bank( 2, data&0x1F )
                
        elif addr == 0x9800:
            if ( (data < 0xE0) or (self.reg[0] != 0) ):
                self.MMC.SetVROM_1K_Bank( 3, data )
            else:
                self.MMC.SetCRAM_1K_Bank( 3, data&0x1F )
                
        elif addr == 0xA000:
            if ( (data < 0xE0) or (self.reg[1] != 0) ):
                self.MMC.SetVROM_1K_Bank( 4, data )
            else:
                self.MMC.SetCRAM_1K_Bank( 4, data&0x1F )
                
        elif addr == 0xA800:
            if ( (data < 0xE0) or (self.reg[1] != 0) ):
                self.MMC.SetVROM_1K_Bank( 5, data )
            else:
                self.MMC.SetCRAM_1K_Bank( 5, 5 )
                
        elif addr == 0xB000:
            if ( (data < 0xE0) or (self.reg[1] != 0) ):
                self.MMC.SetVROM_1K_Bank( 6, data )
            else:
                self.MMC.SetCRAM_1K_Bank( 6, data&0x1F )
        elif addr == 0xB800:
            if ( (data < 0xE0) or (self.reg[1] != 0) ):
                self.MMC.SetVROM_1K_Bank( 7, data )
            else:
                self.MMC.SetCRAM_1K_Bank( 7, data&0x1F )

        elif addr == 0xC000:
            if not self.patch:
                if ( (data <= 0xDF)):
                    self.MMC.SetVROM_1K_Bank( 8, data )
                else:
                    self.MMC.SetVRAM_1K_Bank( 8, data&0x01 )

        elif addr == 0xC800:
            if not self.patch:
                if ( (data <= 0xDF)):
                    self.MMC.SetVROM_1K_Bank( 9, data )
                else:
                    self.MMC.SetVRAM_1K_Bank( 9, data&0x01 )

        elif addr == 0xD000:
            if not self.patch:
                if ( (data <= 0xDF)):
                    self.MMC.SetVROM_1K_Bank( 10, data )
                else:
                    self.MMC.SetVRAM_1K_Bank( 10, data&0x01 )

        elif addr == 0xD800:
            if not self.patch:
                if ( (data <= 0xDF)):
                    self.MMC.SetVROM_1K_Bank( 11, data )
                else:
                    self.MMC.SetVRAM_1K_Bank( 11, data&0x01 )

        elif addr == 0xE000:
            self.MMC.SetPROM_8K_Bank( 4, data & 0x3F )
            #patch
            
        elif addr == 0xE800:
            self.reg[0] = data & 0x40
            self.reg[1] = data & 0x80
            self.MMC.SetPROM_8K_Bank( 5, data & 0x3F )
                
        elif addr == 0xF000:
            self.MMC.SetPROM_8K_Bank( 6, data & 0x3F )

        elif addr == 0xF800:
            if address == 0xF800:
                if self.exsound_enable:
                    #print "apu_ExWrite"
                    self.MMC.ExWrite(address,data)   
                #return 1
                self.reg[2] = data
            

    def Clock(self,cycles):
        if( self.irq_enable):
            self.irq_counter += cycles
            if(self.irq_counter >= 0x7FFF ):
                self.irq_counter = 0x7FFF
                self.irq_enable = 0  #------------- 
                return True
        return False



if __name__ == '__main__':
    mapper = MAPPER()
    print(mapper)











        
