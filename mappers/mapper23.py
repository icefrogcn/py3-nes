# -*- coding: UTF-8 -*-

import sys

from numba import jit
from numba.experimental import jitclass
from numba import int8,uint8,int16,uint16,uint32
import numba as nb
import numpy as np




mapper_spec = [#('MMC',MMC_type),
        ('reg',uint8[:]),
        ('irq_enable',uint8),
        ('irq_counter',uint8),
        ('irq_latch',uint8),
        ('irq_clock',uint16),
        ('irq_occur',uint8),
        ('addrmask',uint16),
        ('RenderMethod',uint8)
        ]
#@jitclass(spec)
class MAPPER(object):


    def __init__(self,MMC):
        self.MMC = MMC

        self.reg = np.zeros(0x9, np.uint8)
        self.irq_enable = 0
        self.irq_counter = 0
        self.irq_latch = 0
        self.irq_clock = 0
        self.irq_occur = 0
        
        self.addrmask = 0xFFFF

        self.RenderMethod = 0#POST_RENDER

    @property
    def Mapper(self):
        return 23
         
    def reset(self):
        for i in range(8):
            self.reg[i] = i

        self.reg[8] = 0

        self.reg[9] = 1
        self.MMC.SetPROM_32K_Bank(0, 1, self.MMC.ROM.PROM_8K_SIZE-2, self.MMC.ROM.PROM_8K_SIZE-1 )
        self.MMC.SetVROM_8K_Bank(0)
	
        return 1

    def WriteLow(self,address,data):
        self.MMC.WriteLow(address,data)

    def ReadLow(self,address):
        return self.MMC.ReadLow(address)

    def Write(self,address,data):#$8000-$FFFF Memory write
        addr = address & self.addrmask
        #print 'irq_occur: ',self.irq_occur
        if addr in (0x8000,0x8004,0x8008,0x800C):
            if self.reg[8]:
                self.MMC.SetPROM_8K_Bank( 6, data )
            else:
                self.MMC.SetPROM_8K_Bank( 4, data )
                
        elif addr ==0x9000:
            #print "data",data
            if data != 0xFF:
                
                data &= 0x03
                if data == 0:self.MMC.Mirroring_W(1)
                elif data == 1:self.MMC.Mirroring_W(2)
                elif data == 2:self.MMC.Mirroring_W(3) #VRAM_MIRROR4L
                else:self.MMC.Mirroring_W(4) #VRAM_MIRROR4H
                #print "Mirroring",NES.Mirroring
                self.MMC.MirrorXor_W(((self.MMC.Mirroring + 1) % 3) * 0x400)
                
        elif addr == 0x9008:
            self.reg[8] = data & 0x02

        elif addr in (0xA000,0xA004,0xA008,0xA00C):
            self.MMC.SetPROM_8K_Bank( 5, data )

        elif 0xB000 <= addr < 0xF000: 
            if (addr & 0xF) == 0x000:
                page = ((addr >> 12) - 11) * 2
                self.reg[page] = (self.reg[page] & 0xF0) | (data & 0x0F)
                self.MMC.SetVROM_1K_Bank( page, self.reg[page] )
                
            elif (addr & 0xF) in (0x001,0x004):
                page = ((addr >> 12) - 11) * 2
                self.reg[page] = (self.reg[page] & 0x0F) | ((data & 0x0F) << 4)
                self.MMC.SetVROM_1K_Bank( page, self.reg[page])
                            
            elif (addr & 0xF) in (0x002,0x008):
                page = ((addr >> 12) - 11) * 2 + 1
                self.reg[page] = (self.reg[page] & 0xF0) | (data & 0x0F)
                self.MMC.SetVROM_1K_Bank( page, self.reg[page] )

                            
            elif (addr & 0xF) in (0x003,0x00C):
                page = ((addr >> 12) - 11) * 2 + 1
                self.reg[page] = (self.reg[page] & 0x0F) | ((data & 0x0F) << 4);
                self.MMC.SetVROM_1K_Bank( page, self.reg[page] )

        elif addr == 0xF008:
            self.irq_enable = data & 0x03
            if( self.irq_enable & 0x02 ):
                self.irq_counter = self.irq_latch
                self.irq_clock = 0
            self.irq_occur = 0

            
			
        elif addr == 0xF00C:
            self.irq_enable = (self.irq_enable & 0x01) * 3
            self.irq_occur = 0
                    

    def Clock(self,cycles):
        if( self.irq_enable & 0x02 ):
            self.irq_clock += cycles
            if( self.irq_clock >= 0x72 ):
                    self.irq_clock -= 0x72
                    if(self. irq_counter == 0xFF ):
                        self.irq_occur = 0xFF
                        self.irq_counter = self.irq_latch
                        self.irq_enable = (self.irq_enable & 0x01) * 3
                    else:
                        self.irq_counter += 1
            if( self.irq_occur ):
                return True
        return False
            
    def HSync(self,scanline):
        return False




if __name__ == '__main__':
    sys.path.append('..')
    from mmc import MMC,MMC_spec
    from jitcompile import jitObject
    mapper_class, mapper_type = jitObject(MAPPER, mapper_spec,MMC_spec(), jit = True)

    mapper = mapper_class(MMC())
    print(mapper)











        
