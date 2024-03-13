# -*- coding: UTF-8 -*-
from numba import objmode
from numba import jit
from numba.experimental import jitclass
from numba import int8,uint8,int16,uint16,uint32
import numba as nb
import numpy as np

from main import MAPPER,MAIN_class_type

spec = [('cartridge',MAIN_class_type),
        ('reg',uint8[:]),
        ('last_addr',uint8),
        ('patch',uint8),
        ('wram_patch',uint8),
        ('wram_bank',uint8),
        ('wram_count',uint8),
        ('shift',uint16),       
        ('regbuf',uint16),
        ('RenderMethod',uint8)        
        ]
@jitclass(spec)
class MAPPER(object):


    def __init__(self,cartridge = MAPPER()):
        self.cartridge = cartridge

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

        if( self.cartridge.PROM_16K_SIZE < 32 ):
            
            self.cartridge.SetPROM_32K_Bank(0, 1, self.cartridge.PROM_8K_SIZE-2, self.cartridge.PROM_8K_SIZE-1)
        else:
            self.cartridge.SetPROM_16K_Bank( 4, 0 )
            self.cartridge.SetPROM_16K_Bank( 6, 16-1 )

            self.patch = 1
            
        return 1
    def WriteLow(self,address,data):
        self.cartridge.WriteLow(address,data)

    def ReadLow(self,address):
        return self.cartridge.ReadLow(address)
    
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
                    self.cartridge.Mirroring_W(0 if( self.reg[0] & 0x01 ) else 1)
                else:
                    self.cartridge.Mirroring_W(2)#4 if( self.reg[0] & 0x01 ) else 3)
                self.cartridge.MirrorXor_W(((self.cartridge.Mirroring + 1) % 3) * 0x400)
            elif addr == 1:
                if self.cartridge.VROM_1K_SIZE:
                    if( self.reg[0] & 0x10 ):
                        self.cartridge.SetVROM_4K_Bank( 0, self.reg[1] )
                    else:
                        self.cartridge.SetVROM_8K_Bank(self.reg[1] >> 1 )
            elif addr == 2:
                if self.cartridge.VROM_1K_SIZE:
                    if( self.reg[0] & 0x10 ):
                        self.cartridge.SetVROM_4K_Bank(4, self.reg[2] )
                        
            elif addr == 3:
                if (self.reg[0] & 0x08):
                    if( self.reg[0] & 0x04 ):
                        self.cartridge.SetPROM_16K_Bank( 4, self.reg[3] )
                        self.cartridge.SetPROM_16K_Bank( 6, self.cartridge.PROM_16K_SIZE - 1 )
                    else:
                        self.cartridge.SetPROM_16K_Bank( 6, self.reg[3] )
                        self.cartridge.SetPROM_16K_Bank( 4, 0)
                else:
                    self.cartridge.SetPROM_32K_Bank0( self.reg[3]>>1 )


        else:
            with objmode():
                print "For 512K/1M byte Cartridge"
            if addr == 0:
                if( self.reg[0] & 0x02 ):
                    self.cartridge.Mirroring_W(0 if( self.reg[0] & 0x01 ) else 1)
                else:
                    self.cartridge.Mirroring_W(4 if( self.reg[0] & 0x01 ) else 3)
                self.cartridge.MirrorXor_W(((self.cartridge.Mirroring + 1) % 3) * 0x400)
            if self.cartridge.VROM_1K_SIZE:
                    if( self.reg[0] & 0x10 ):
                        self.cartridge.SetVROM_4K_Bank(0, self.reg[1] )
                        self.cartridge.SetVROM_4K_Bank(4, self.reg[2] )
                    else:
                        self.cartridge.SetVROM_8K_Bank(self.reg[1] >> 1 )
            else:
                with objmode():
                    print "Romancia"

            PROM_BASE = ((self.reg[1] & 0x10) << 1) if( self.cartridge.PROM_16K_SIZE >= 32 ) else 0

            if(self.reg[0] & 0x08):
                if( self.reg[0] & 0x04 ):
                    self.cartridge.SetPROM_16K_Bank(4, PROM_BASE + ((self.reg[3] & 0x0F) * 2) )
                    if( self.cartridge.PROM_16K_SIZE >= 32 ):
                        self.cartridge.SetPROM_16K_Bank( 6, PROM_BASE - 1 )
                else:
                    self.cartridge.SetPROM_16K_Bank( 6, PROM_BASE + ((self.reg[3] & 0x0F) * 2) )
                    if( self.cartridge.PROM_16K_SIZE >= 32 ):
                        self.cartridge.SetPROM_16K_Bank( 4, PROM_BASE - 1 )
            else:
                self.cartridge.SetPROM_32K_Bank0((self.reg[3] & 0xF) + PROM_BASE)
                        
		
                        
        
        

MAPPER_type = nb.deferred_type()
MAPPER_type.define(MAPPER.class_type.instance_type)




if __name__ == '__main__':
    mapper = MAPPER()











        
