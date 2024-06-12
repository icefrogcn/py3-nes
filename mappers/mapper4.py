# -*- coding: UTF-8 -*-

import sys

from numba import jit
from numba.experimental import jitclass
from numba import int8,uint8,int16,uint16,uint32
import numba as nb
import numpy as np


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
#@jitclass(spec)
class MAPPER(object):


    def __init__(self,MMC):
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
        for i in range(8):
            self.reg[i] = 0

        self.prg0 = 0
        self.prg1 = 1

        self.SetBank_CPU()
        self.chr01 = 0
        self.chr23 = 2
        self.chr4 = 4
        self.chr5 = 5
        self.chr6 = 6
        self.chr7 = 7

        self.SetBank_PPU()
        
        self.we_sram  = 0;	# Disable
        self.irq_enable = 0;	# Disable
        self.irq_counter = 0;
        self.irq_latch = 0xFF;
        self.irq_request = 0;
        self.irq_preset = 0;
        self.irq_preset_vbl = 0;

        self.irq_type = 0
        
        return 1

    def WriteLow(self,address,data):
        self.MMC.WriteLow(address,data)

    def ReadLow(self,address):
        return self.MMC.ReadLow(address)

    def Write(self,address,data):#$8000-$FFFF Memory write
        addr = address & 0xE001
        #print 'irq_occur: ',self.irq_occur
        if addr == 0x8000:
            self.reg[0] = data
            self.SetBank_CPU()
            self.SetBank_PPU()
                
        elif addr ==0x8001:
            self.reg[1] = data
            bank = self.reg[0] & 0x07
            if bank == 0x00:
                    self.chr01 = data & 0xFE
                    self.SetBank_PPU()
            elif bank == 0x01:
                    self.chr23 = data & 0xFE
                    self.SetBank_PPU()
            elif bank == 0x02:
                    self.chr4 = data
                    self.SetBank_PPU()
            elif bank == 0x03:
                    self.chr5 = data
                    self.SetBank_PPU()
            elif bank == 0x04:
                    self.chr6 = data
                    self.SetBank_PPU()
            elif bank == 0x05:
                    self.chr7 = data
                    self.SetBank_PPU()
            elif bank == 0x06:
                    self.prg0 = data
                    self.SetBank_CPU()
            elif bank == 0x07:
                    self.prg1 = data
                    self.SetBank_CPU()

        elif addr == 0xA000:
            self.reg[2] = data
            if data & 0x01:
                self.MMC.Mirroring_W(0)
            else:
                self.MMC.Mirroring_W(1)
                #elif data == 2:self.MMC.Mirroring_W(3) #VRAM_MIRROR4L
                #else:self.MMC.Mirroring_W(4) #VRAM_MIRROR4H
                #print "Mirroring",NES.Mirroring
                #self.MMC.MirrorXor_W(((self.MMC.Mirroring + 1) % 3) * 0x400)
        elif addr == 0xA001:
            self.reg[3] = data
                   
        elif addr == 0xC000:
            self.reg[4] = data
            self.irq_latch = data
            if self.irq_type == MMC3_IRQ_KLAX:
                self.irq_counter = data

        elif addr == 0xC001:
            self.reg[5] = data
            if self.scanline < 240:
                self.irq_counter |= 0x80
                self.irq_preset = 0xFF
            else:
                self.irq_counter |= 0x80
                self.irq_preset_vbl = 0xFF
                self.irq_preset = 0
            

        elif addr == 0xE000:
            self.reg[6] = data
            self.irq_enable = 0
            self.irq_request = 0
            
        elif addr == 0xE001:
            self.reg[7] = data
            self.irq_enable = 1
            self.irq_request = 0


                    
    def HSync(self,scanline):
        self.scanline = scanline
        if( (scanline >= 0 and scanline <= 239) ):
            if( self.irq_preset_vbl ):
                self.irq_counter = self.irq_latch
                self.irq_preset_vbl = 0
            
            if( self.irq_preset ):
                self.irq_counter = self.irq_latch;
                self.irq_preset = 0
            elif (self.irq_counter > 0):
                self.irq_counter -= 1

            if ( self.irq_counter == 0 ):
                if( self.irq_enable ):
                    self.irq_request = 0xFF
                self.irq_preset = 0xFF

        #if( self.irq_request && (nes->GetIrqType() == NES::IRQ_HSYNC) ):
            #return True

        return False

            
        
        
    
    def Clock(self,cycles): #default IRQ_CLOCK
        if( self.irq_request ):
            return True
        return False

    def SetBank_CPU(self):
        if( self.reg[0] & 0x40 ):
            self.MMC.SetPROM_32K_Bank( self.MMC.PROM_8K_SIZE-2, self.prg1, self.prg0, self.MMC.PROM_8K_SIZE-1 );
        else:
            self.MMC.SetPROM_32K_Bank( self.prg0, self.prg1, self.MMC.PROM_8K_SIZE-2, self.MMC.PROM_8K_SIZE-1 );
    

    def SetBank_PPU(self):
        if( self.MMC.VROM_1K_SIZE ):
            if( self.reg[0] & 0x80 ):
                self.MMC.SetVROM_8K_Bank8( self.chr4, self.chr5, self.chr6, self.chr7,
                                                 self.chr01, self.chr01+1, self.chr23, self.chr23+1 )
            else:
                self.MMC.SetVROM_8K_Bank8( self.chr01, self.chr01+1, self.chr23, self.chr23+1,
                                                 self.chr4, self.chr5, self.chr6, self.chr7 );
            

#MAPPER_type = nb.deferred_type()
#MAPPER_type.define(MAPPER.class_type.instance_type)


if __name__ == '__main__':
    sys.path.append('..')
    from mmc import MMC
    mapper = MAPPER(MMC())
    print(mapper)











        
