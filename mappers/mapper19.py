# -*- coding: UTF-8 -*-
from numba import jit
from numba.experimental import jitclass
from numba import int8,uint8,int16,uint16,uint32
import numba as nb
import numpy as np

from main import *
from main import MAPPER,MAIN_class_type

spec = [('cartridge',MAIN_class_type),
        ('reg',uint8[:]),
        ('exram',uint8[:]),
        ('irq_enable',uint8),
        ('irq_counter',uint8),
        ('exsound_enable',uint8),
        ('patch',uint8),
        ('RenderMethod',uint8)        
        ]
@jitclass(spec)
class MAPPER(object):
    
    def __init__(self,cartridge = MAPPER()):
        self.cartridge = cartridge

        self.patch = 0
        self.exsound_enable = 0
    
        self.reg = np.zeros(0x3, np.uint8)
        self.exram = np.zeros(128, np.uint8)
        self.irq_enable = 0
        self.irq_counter = 0

        self.RenderMethod = POST_RENDER

    @property
    def Mapper(self):
        return 19    

    def reset(self):
        
        self.cartridge.SetPROM_32K_Bank(0, 1, self.cartridge.ROM.PROM_8K_SIZE-2, self.cartridge.ROM.PROM_8K_SIZE-1 )

        if( self.cartridge.ROM.VROM_1K_SIZE >= 8 ):
            self.cartridge.SetVROM_8K_Bank( self.cartridge.ROM.VROM_8K_SIZE - 1 );
        self.exsound_enable = 0xFF
        return 1

    def ReadLow(self,address):
        #print "ReadLow 19"
        #addr = address & 0xF800
        if (address & 0xF800) in (0x6000,0x6800,0x7000,0x7800):
            return self.cartridge.ReadLow(address)
        return 0
            
    def WriteLow(self,address,data):
        #print "WriteLow 19"
        addr = address & 0xF800
        if addr == 0x5800:
            #print "irq_enable try"
            self.irq_counter = (self.irq_counter & 0x00FF) | ((data & 0x7F) << 8)
            self.irq_enable  = data & 0x80
            if self.irq_enable:
                self.irq_counter += 1
            
        elif addr in (0x6000,0x6800,0x7000,0x7800):
            return self.cartridge.WriteLow(address,data)
        
    def Write(self,address,data):#$8000-$FFFF Memory write
        addr = address & 0xF800

        if addr == 0x8000:
            if ( (data < 0xE0) or (self.reg[0] != 0) ):
                self.cartridge.SetVROM_1K_Bank( 0, data )
            else:
                self.cartridge.SetCRAM_1K_Bank( 0, data&0x1F )
                
        elif addr == 0x8800:
            if ( (data < 0xE0) or (self.reg[0] != 0) ):
                self.cartridge.SetVROM_1K_Bank( 1, data )
            else:
                self.cartridge.SetCRAM_1K_Bank( 1, data&0x1F )
                
        elif addr == 0x9000:
            if ( (data < 0xE0) or (self.reg[0] != 0) ):
                self.cartridge.SetVROM_1K_Bank( 2, data )
            else:
                self.cartridge.SetCRAM_1K_Bank( 2, data&0x1F )
                
        elif addr == 0x9800:
            if ( (data < 0xE0) or (self.reg[0] != 0) ):
                self.cartridge.SetVROM_1K_Bank( 3, data )
            else:
                self.cartridge.SetCRAM_1K_Bank( 3, data&0x1F )
                
        elif addr == 0xA000:
            if ( (data < 0xE0) or (self.reg[1] != 0) ):
                self.cartridge.SetVROM_1K_Bank( 4, data )
            else:
                self.cartridge.SetCRAM_1K_Bank( 4, data&0x1F )
                
        elif addr == 0xA800:
            if ( (data < 0xE0) or (self.reg[1] != 0) ):
                self.cartridge.SetVROM_1K_Bank( 5, data )
            else:
                self.cartridge.SetCRAM_1K_Bank( 5, 5 )
                
        elif addr == 0xB000:
            if ( (data < 0xE0) or (self.reg[1] != 0) ):
                self.cartridge.SetVROM_1K_Bank( 6, data )
            else:
                self.cartridge.SetCRAM_1K_Bank( 6, data&0x1F )
        elif addr == 0xB800:
            if ( (data < 0xE0) or (self.reg[1] != 0) ):
                self.cartridge.SetVROM_1K_Bank( 7, data )
            else:
                self.cartridge.SetCRAM_1K_Bank( 7, data&0x1F )

        elif addr == 0xC000:
            if not self.patch:
                if ( (data <= 0xDF)):
                    self.cartridge.SetVROM_1K_Bank( 8, data )
                else:
                    self.cartridge.SetVRAM_1K_Bank( 8, data&0x01 )

        elif addr == 0xC800:
            if not self.patch:
                if ( (data <= 0xDF)):
                    self.cartridge.SetVROM_1K_Bank( 9, data )
                else:
                    self.cartridge.SetVRAM_1K_Bank( 9, data&0x01 )

        elif addr == 0xD000:
            if not self.patch:
                if ( (data <= 0xDF)):
                    self.cartridge.SetVROM_1K_Bank( 10, data )
                else:
                    self.cartridge.SetVRAM_1K_Bank( 10, data&0x01 )

        elif addr == 0xD800:
            if not self.patch:
                if ( (data <= 0xDF)):
                    self.cartridge.SetVROM_1K_Bank( 11, data )
                else:
                    self.cartridge.SetVRAM_1K_Bank( 11, data&0x01 )

        elif addr == 0xE000:
            self.cartridge.SetPROM_8K_Bank( 4, data & 0x3F )
            #patch
            
        elif addr == 0xE800:
            self.reg[0] = data & 0x40
            self.reg[1] = data & 0x80
            self.cartridge.SetPROM_8K_Bank( 5, data & 0x3F )
                
        elif addr == 0xF000:
            self.cartridge.SetPROM_8K_Bank( 6, data & 0x3F )

        elif addr == 0xF800:
            if self.exsound_enable:
                #print "apu_ExWrite"
                return 1
            self.reg[2] = data
            
    def HSync(self,scanline):
        return False

    def Clock(self,cycles):
        if( self.irq_enable):
            self.irq_counter += cycles
            if(self.irq_counter >= 0x7FFF ):
                self.irq_counter = 0x7FFF
                return True
        return False

MAPPER_type = nb.deferred_type()
MAPPER_type.define(MAPPER.class_type.instance_type)

if __name__ == '__main__':
    mapper = MAPPER()











        
