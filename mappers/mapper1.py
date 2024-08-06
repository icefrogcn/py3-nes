# -*- coding: UTF-8 -*-

import sys

from numba import objmode
from numba import jit
from numba.experimental import jitclass
from numba import int8,uint8,int16,uint16,uint32
import numba as nb
import numpy as np

import spec
from mmc import MMC

mapper_spec = [
        ('reg',uint8[:]),
        ('last_addr',uint16),
        ('patch',uint8),
        ('wram_patch',uint8),
        ('wram_bank',uint8),
        ('wram_count',uint8),
        ('shift',uint8),       
        ('regbuf',uint8),
        ('RenderMethod',uint8)        
        ]
@jitclass
class MAPPER(object):
    MMC:MMC
    last_addr:uint16
    
    patch:uint8
    wram_patch:uint8
    wram_bank:uint8
    wram_count:uint8
    
    reg:uint8[:]
    shift:uint8   
    regbuf:uint8
    
    RenderMethod:uint8  

    def __init__(self,MMC=MMC()):
        self.MMC = MMC

        self.reg = np.zeros(0x4, np.uint8)
        self.last_addr = 0
        self.patch = 0
        self.wram_patch = 0
        self.wram_bank = 0
        self.wram_count = 0
        
        self.shift = 0
        self.regbuf = 0

        self.RenderMethod = 0

    @property
    def Mapper(self):
        return 1

    def Clock(self,cycles):
        return False
    
    def reset(self):
        self.reg[0] = 0x0C
        #reg[1] = reg[2] = reg[3] = 0
        #shift = regbuf = 0

        if( self.MMC.PROM_16K_SIZE < 32 ):
            
            self.MMC.SetPROM_32K_Bank(0, 1, self.MMC.PROM_8K_SIZE-2, self.MMC.PROM_8K_SIZE-1)
        else:
            self.MMC.SetPROM_16K_Bank( 4, 0 )
            self.MMC.SetPROM_16K_Bank( 6, 16-1 )

            self.patch = 1
            
        return 1

    
    def Write(self,address,data):#$8000-$FFFF Memory write
        if( self.patch != 1 ):
            if((address & 0x6000) != (self.last_addr & 0x6000)):
                self.shift = 0
                self.regbuf = 0
            self.last_addr = address
        
        if( data & 0x80 ):
            self.shift = 0
            self.regbuf = 0
            self.reg[0] |= 0x0C
            return
            
        if( data & 0x01 ):
            self.regbuf |= (1 << self.shift)
            #self.regbuf = self.regbuf 
            
        self.shift += 1
        if( self.shift < 5 ):return

        addr = (address & 0x7FFF) >> 13
        self.reg[addr] = self.regbuf

        self.shift = 0
        self.regbuf = 0

        if self.patch != 1:
            #with objmode():
                #print "#For Normal Cartridge"
            if addr == 0:
                if( self.reg[0] & 0x02 ):
                    self.MMC.SetVRAM_Mirror(0 if( self.reg[0] & 0x01 ) else 1)
                else:
                    self.MMC.SetVRAM_Mirror(4 if( self.reg[0] & 0x01 ) else 3)
                #self.MMC.MirrorXor_W(((self.MMC.Mirroring + 1) % 3) * 0x400)
            elif addr == 1:
                if self.MMC.VROM_1K_SIZE:
                    if( self.reg[0] & 0x10 ):
                        self.MMC.SetVROM_4K_Bank( 0, self.reg[1] )
                    else:
                        self.MMC.SetVROM_8K_Bank(self.reg[1] >> 1 )
            elif addr == 2:
                if self.MMC.VROM_1K_SIZE:
                    if( self.reg[0] & 0x10 ):
                        self.MMC.SetVROM_4K_Bank(4, self.reg[2] )
                        
            elif addr == 3:
                if (self.reg[0] & 0x08):
                    if( self.reg[0] & 0x04 ):
                        self.MMC.SetPROM_16K_Bank( 4, self.reg[3] )
                        self.MMC.SetPROM_16K_Bank( 6, self.MMC.PROM_16K_SIZE - 1 )
                    else:
                        self.MMC.SetPROM_16K_Bank( 6, self.reg[3] )
                        self.MMC.SetPROM_16K_Bank( 4, 0)
                else:
                    self.MMC.SetPROM_32K_Bank0( self.reg[3]>>1 )


        else:
            print("For 512K/1M byte Cartridge")
            if addr == 0:
                if( self.reg[0] & 0x02 ):
                    self.MMC.SetVRAM_Mirror(0 if( self.reg[0] & 0x01 ) else 1)
                else:
                    self.MMC.SetVRAM_Mirror(4 if( self.reg[0] & 0x01 ) else 3)
                #self.MMC.MirrorXor_W(((self.MMC.Mirroring + 1) % 3) * 0x400)
            if self.MMC.VROM_1K_SIZE:
                    if( self.reg[0] & 0x10 ):
                        self.MMC.SetVROM_4K_Bank(0, self.reg[1] )
                        self.MMC.SetVROM_4K_Bank(4, self.reg[2] )
                    else:
                        self.MMC.SetVROM_8K_Bank(self.reg[1] >> 1 )
            else:
                print("Romancia")

            PROM_BASE = (self.reg[1] & 0x10) if( self.MMC.PROM_16K_SIZE >= 32 ) else 0

            if(self.reg[0] & 0x08):
                if( self.reg[0] & 0x04 ):
                    self.MMC.SetPROM_16K_Bank(4, PROM_BASE + ((self.reg[3] & 0x0F)) )
                    if( self.MMC.PROM_16K_SIZE >= 32 ):
                        self.MMC.SetPROM_16K_Bank( 6, PROM_BASE + 16 - 1 )
                else:
                    self.MMC.SetPROM_16K_Bank( 6, PROM_BASE + ((self.reg[3] & 0x0F)) )
                    if( self.MMC.PROM_16K_SIZE >= 32 ):
                        self.MMC.SetPROM_16K_Bank( 4, PROM_BASE )
            else:
                self.MMC.SetPROM_32K_Bank0((self.reg[3] & (0xF + PROM_BASE))>>1)
                        
		
                        
        

if __name__ == '__main__':
    mapper = MAPPER()
    print(mapper)









        
