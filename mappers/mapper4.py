# -*- coding: UTF-8 -*-

import sys

from numba import jit
from numba.experimental import jitclass
from numba import int8,uint8,int16,uint16,uint32
import numba as nb
import numpy as np

import spec
from mmc import MMC

MMC3_IRQ_KLAX = 1
MMC3_IRQ_SHOUGIMEIKAN = 2
MMC3_IRQ_DAI2JISUPER = 3


mapper_spec = [#('MMC',MAIN_class_type),
        ('reg',uint8[:]),
        ('prg0',uint8), ('prg1',uint8),
        ('chr01',uint8),('chr23',uint8),('chr4',uint8),('chr5',uint8),('chr6',uint8),('chr7',uint8),
        ('we_sram',uint8),
        ('irq_type',uint8),
        ('irq_enable',uint8),
        ('irq_counter',uint8),
        ('irq_latch',uint8),
        ('irq_request',uint8),
        ('irq_preset',uint8),
        ('irq_preset_vbl',uint8),
        ('scanline',uint16),
        ('RenderMethod',uint8)
        ]
@jitclass
class MAPPER():
    MMC: MMC

    reg:uint8[:]
    prg0:uint8
    prg1:uint8
    chr01:uint8
    chr23:uint8
    chr4:uint8
    chr5:uint8
    chr6:uint8
    chr7:uint8
    we_sram:uint8
    irq_type:uint8
    irq_enable:uint8
    irq_counter:uint8
    irq_latch:uint8
    irq_request:uint8
    irq_preset:uint8
    irq_preset_vbl:uint8
    scanline:uint16
    RenderMethod:uint8

    def __init__(self,MMC = MMC()):
        self.MMC = MMC

        self.reg = np.zeros(0x8, np.uint8)
        self.prg0 = self.prg1 = 0
        self.chr01 = self.chr23 = self.chr4 = self.chr5 = self.chr6 = self.chr7 = 0
        self.we_sram = 0
        
        self.irq_type = 0
        self.irq_enable = 0
        self.irq_counter = 0
        self.irq_latch = 0
        self.irq_request = 0
        self.irq_preset = 0
        self.irq_preset_vbl = 0

        self.scanline = 0

        self.RenderMethod = 0#POST_RENDER

    @property
    def Mapper(self):
        return 4
         
    def reset(self):
        self.reg[:] = 0

        self.prg0 = 0
        self.prg1 = 1
        self.MMC3_SetBank_CPU()
        
        #if( self.MMC.VROM_1K_SIZE ):
        self.chr01 = 0
        self.chr23 = 2
        self.chr4 = 4
        self.chr5 = 5
        self.chr6 = 6
        self.chr7 = 7
        self.MMC3_SetBank_PPU()
        #else:
            #self.chr01 = self.chr23 = self.chr4 = self.chr5 = self.chr6 = self.chr7 = 0
        
        self.we_sram  = 0;	# Disable
        self.irq_enable = 0;	# Disable
        self.irq_counter = 0;
        self.irq_latch = 0xFF;
        self.irq_request = 0;
        self.irq_preset = 0;
        self.irq_preset_vbl = 0;

        #IRQ_CLOCK == 1  default IRQ type
        self.irq_type = 0
        
        return 1


    def Write(self,address,data):#$8000-$FFFF Memory write
        addr = address & 0xE001
        #print 'irq_occur: ',self.irq_occur
        if addr == 0x8000:
            self.reg[0] = data
            self.MMC3_SetBank_CPU()
            self.MMC3_SetBank_PPU()
                
        elif addr ==0x8001:
            self.reg[1] = data
            bank = self.reg[0] & 0x07
            if bank == 0x00:
                    self.chr01 = data & 0xFE
                    self.MMC3_SetBank_PPU()
            elif bank == 0x01:
                    self.chr23 = data & 0xFE
                    self.MMC3_SetBank_PPU()
            elif bank == 0x02:
                    self.chr4 = data
                    self.MMC3_SetBank_PPU()
            elif bank == 0x03:
                    self.chr5 = data
                    self.MMC3_SetBank_PPU()
            elif bank == 0x04:
                    self.chr6 = data
                    self.MMC3_SetBank_PPU()
            elif bank == 0x05:
                    self.chr7 = data
                    self.MMC3_SetBank_PPU()
            elif bank == 0x06:
                    self.prg0 = data
                    self.MMC3_SetBank_CPU()
            elif bank == 0x07:
                    self.prg1 = data
                    self.MMC3_SetBank_CPU()

        elif addr == 0xA000:
            self.reg[2] = data
            if data & 0x01:
                self.MMC.SetVRAM_Mirror(0)
            else:
                self.MMC.SetVRAM_Mirror(1)

        elif addr == 0xA001:
            self.reg[3] = data
                   
        elif addr == 0xC000:
            self.reg[4] = data
            #self.irq_latch = data       #----- remove
            self.irq_counter = data    #------ add
            #if self.irq_type == MMC3_IRQ_KLAX:
                #self.irq_counter = data

        elif addr == 0xC001:
            self.reg[5] = data
            self.irq_latch = data
            #if self.scanline < 240:
            #    self.irq_counter |= 0x80
            #    self.irq_preset = 0xFF
            #else:
            #    self.irq_counter |= 0x80
            #    self.irq_preset_vbl = 0xFF
            #    self.irq_preset = 0
            

        elif addr == 0xE000:
            self.reg[6] = data
            self.irq_enable = 0
            self.irq_request = 0
            
        elif addr == 0xE001:
            self.reg[7] = data
            self.irq_enable = 1
            self.irq_request = 0


                    
    def HSync(self,scanline, ppuShow):
        self.scanline = scanline
        if( self.irq_enable and (scanline >= 0 and scanline <= 239) and ppuShow):
            #if( self.irq_preset_vbl ):
            #    self.irq_counter = self.irq_latch
            #    self.irq_preset_vbl = 0
            
            #if( self.irq_preset ):
            #    self.irq_counter = self.irq_latch;
            #    self.irq_preset = 0
                
            #elif (self.irq_counter > 0):
            #    self.irq_counter -= 1

            #if ( self.irq_counter == 0 ):
            #    if( self.irq_enable ):
            #        self.irq_request = 0xFF
            #    self.irq_preset = 0xFF

            self.irq_counter -= 1
            if  ( self.irq_counter == 0 ):
                self.irq_counter = self.irq_latch
                return True
        #if( self.irq_request && (nes->GetIrqType() == NES::IRQ_HSYNC) ):
            #return True

        return False

            
        
        
    
    def Clock(self,cycles): #default IRQ_CLOCK
        #if( self.irq_request ):
            #return True
        return False

    def MMC3_SetBank_CPU(self):
        if( self.reg[0] & 0x40 ):
            self.MMC.SetPROM_32K_Bank( self.MMC.PROM_8K_SIZE-2, self.prg1, self.prg0, self.MMC.PROM_8K_SIZE-1 );
        else:
            self.MMC.SetPROM_32K_Bank( self.prg0, self.prg1, self.MMC.PROM_8K_SIZE-2, self.MMC.PROM_8K_SIZE-1 );
    

    def MMC3_SetBank_PPU(self):
        if( self.MMC.VROM_1K_SIZE ):
            if( self.reg[0] & 0x80 ):
                self.MMC.SetVROM_8K_Bank8( self.chr4, self.chr5, self.chr6, self.chr7,
                                           self.chr01, self.chr01+1, self.chr23, self.chr23+1 )
            else:
                self.MMC.SetVROM_8K_Bank8( self.chr01, self.chr01+1, self.chr23, self.chr23+1,
                                           self.chr4, self.chr5, self.chr6, self.chr7 );
            return 1

        else:
            if ( self.reg[0] & 0x80 ):
                self.MMC.SetCRAM_1K_Bank( 4, (self.chr01+0)&0x07 )
                self.MMC.SetCRAM_1K_Bank( 5, (self.chr01+1)&0x07 )
                self.MMC.SetCRAM_1K_Bank( 6, (self.chr23+0)&0x07 )
                self.MMC.SetCRAM_1K_Bank( 7, (self.chr23+1)&0x07 )
                self.MMC.SetCRAM_1K_Bank( 0, (self.chr4)&0x07 )
                self.MMC.SetCRAM_1K_Bank( 1, (self.chr5)&0x07 )
                self.MMC.SetCRAM_1K_Bank( 2, (self.chr6)&0x07 )
                self.MMC.SetCRAM_1K_Bank( 3, (self.chr7)&0x07 )
            else:
                self.MMC.SetCRAM_1K_Bank( 0, (self.chr01+0)&0x07 )
                self.MMC.SetCRAM_1K_Bank( 1, (self.chr01+1)&0x07 )
                self.MMC.SetCRAM_1K_Bank( 2, (self.chr23+0)&0x07 )
                self.MMC.SetCRAM_1K_Bank( 3, (self.chr23+1)&0x07 )
                self.MMC.SetCRAM_1K_Bank( 4, (self.chr4)&0x07 )
                self.MMC.SetCRAM_1K_Bank( 5, (self.chr5)&0x07 )
                self.MMC.SetCRAM_1K_Bank( 6, (self.chr6)&0x07 )
                self.MMC.SetCRAM_1K_Bank( 7, (self.chr7)&0x07 )
               
                

#MAPPER_type = nb.deferred_type()
#MAPPER_type.define(MAPPER.class_type.instance_type)


if __name__ == '__main__':
    #sys.path.append('..')
    #from mmc import MMC
    mapper = MAPPER()
    print(mapper)











        
