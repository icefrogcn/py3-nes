# -*- coding: UTF-8 -*-

''' Functions for emulating MMCs. Select8KVROM and the
'''

import sys
import traceback


from numba import jit
from numba import types, typed
from numba.experimental import jitclass
from numba import int8,uint8,int16,uint16
from numba.typed import Dict,List
from numba.types import u1,u2,ListType
import numpy as np
import numba as nb


from jitcompile import jitObject

from mmu import MMU
from rom import ROM

POST_ALL_RENDER = 0
PRE_ALL_RENDER  = 1
POST_RENDER     = 2
PRE_RENDER      = 3
TILE_RENDER     = 4




@jitclass
class MMC(object):
    
    MMU:MMU
    ROM:ROM

    RenderMethod: uint8
    
    def __init__(self, MMU = MMU()):

        self.MMU = MMU
        self.ROM = self.MMU.ROM
        
        self.RenderMethod = POST_ALL_RENDER

    #@property
    #def ROM(self):
    #    return self.MMU.ROM
    @property
    def RAM(self):
        return self.MMU.RAM
    
    @property
    def VRAM_HMIRROR(self):
        return 0x00	# Horizontal
    @property
    def VRAM_VMIRROR(self):
        return 0x01	# Virtical
    @property
    def VRAM_MIRROR4(self):
        return 0x02	# All screen
    @property
    def VRAM_MIRROR4L(self):
        return 0x03	# PA10 L屌掕 $2000-$23FF偺儈儔乕
    @property
    def VRAM_MIRROR4H(self):
        return 0x04	# PA10 H屌掕 $2400-$27FF偺儈儔乕


    @property
    def PPU_MEM_BANK(self):
        return self.MMU.PPU_MEM_BANK
    @property
    def PPU_MEM_TYPE(self):
        return self.MMU.PPU_MEM_TYPE
    @property
    def VRAM(self):
        return self.MMU.VRAM
    @property
    def CRAM(self):
        return self.MMU.CRAM

    @property
    def NTArray(self):
        return self.MMU.NTArray
    @property
    def NT_BANK(self):
        return self.MMU.NT_BANK


    @property
    def PROM(self):
        return self.ROM.PROM

    @property
    def VROM(self):
        return self.ROM.VROM

    
    @property
    def Mapper(self):
        return self.ROM.Mapper
    @property
    def Mirroring(self):
        return self.ROM.Mirroring
    @Mirroring.setter
    def Mirroring(self,value):
        self.ROM.Mirroring = value


    @property
    def PROM_8K_SIZE(self):
        return self.ROM.PROM_8K_SIZE
    @property
    def PROM_16K_SIZE(self):
        return self.ROM.PROM_16K_SIZE
    @property
    def PROM_32K_SIZE(self):
        return self.ROM.PROM_32K_SIZE

    @property
    def VROM_1K_SIZE(self):
        return self.ROM.VROM_1K_SIZE
    @property
    def VROM_2K_SIZE(self):
        return self.ROM.VROM_2K_SIZE
    @property
    def VROM_4K_SIZE(self):
        return self.ROM.VROM_4K_SIZE





    


        
    def reset(self):
        if self.ROM.VROM_8K_SIZE:
            self.SetVROM_8K_Bank(0)
        else:
            self.SetCRAM_8K_Bank(0)
            
        if self.ROM.Is4SCREEN:
            self.SetVRAM_Mirror( 2 )
        elif self.ROM.IsVMIRROR():
            self.SetVRAM_Mirror( 1 )
        else:
            self.SetVRAM_Mirror( 0 )

    def Write(self,addr,data):#$8000-$FFFF Memory write
        pass

    def Read(self,address):#$8000-$FFFF Memory read(Dummy)
        return self.RAM[address>>13,address & 0x1FFF]

    def ReadLow(self,address):#$4100-$7FFF Lower Memory read
        if( address >= 0x6000 ):
            return self.RAM[3, address & 0x1FFF]
        return address>>8

    def WriteLow(self,address,data): #$4100-$7FFF Lower Memory write
        #$6000-$7FFF WRAM
        if( address >= 0x6000 ) :
            self.RAM[3, address & 0x1FFF] = data
    
    def ExRead(self,address): #$4018-$40FF Extention register read/write
        return 0
    
    def ExWrite(self, address, data ):
        pass
    
    def Clock(self, cycle ):
        return False
    def HSync(self, cycle ):
        return False
    

    def SetPROM_8K_Bank(self, page, bank):
        
        bank %= self.ROM.PROM_8K_SIZE
        self.RAM[page] = self.PROM[0x2000 * bank : 0x2000 * bank + 0x2000]

        
            
    def SetPROM_16K_Bank(self,page, bank):
        self.SetPROM_8K_Bank( page+0, bank*2+0 )
        self.SetPROM_8K_Bank( page+1, bank*2+1 )
        
    def SetPROM_32K_Bank0(self,bank):
        self.SetPROM_8K_Bank( 4, bank*4 + 0 )
        self.SetPROM_8K_Bank( 5, bank*4 + 1 )
        self.SetPROM_8K_Bank( 6, bank*4 + 2 )
        self.SetPROM_8K_Bank( 7, bank*4 + 3 )

    def SetPROM_32K_Bank(self,bank0,bank1,bank2,bank3):
        self.SetPROM_8K_Bank( 4, bank0 )
        self.SetPROM_8K_Bank( 5, bank1 )
        self.SetPROM_8K_Bank( 6, bank2 )
        self.SetPROM_8K_Bank( 7, bank3 )
	
    def SetCRAM_8K_Bank(self,bank):
        for i in range(8):
            self.SetCRAM_1K_Bank( i, bank * 8 + i )
        


    def SetCRAM_1K_Bank(self, page, bank):
        print("Set PPU bank CRAM",page)
        bank &= 0x1F
        ptr = 0x0400 * bank
        self.PPU_MEM_BANK[page] = self.CRAM[ptr:ptr+0x400]
        self.PPU_MEM_TYPE[page] = 0x01
        print(self.PPU_MEM_BANK[page],bank)

    def SetVRAM_1K_Bank(self, page, bank):
        # "Set VRAM"
        bank &= 0x3
        ptr = 0x0400 * (bank & 0x3)
        self.PPU_MEM_BANK[page] = self.VRAM[ptr:ptr+0x400]
        self.PPU_MEM_TYPE[page] = 0x80


    def SetVRAM_Bank(self, bank0, bank1, bank2, bank3 ):

        self.SetVRAM_1K_Bank(  8, bank0 )
        self.SetVRAM_1K_Bank(  9, bank1 )
        self.SetVRAM_1K_Bank( 10, bank2 )
        self.SetVRAM_1K_Bank( 11, bank3 )

    def SetVRAM_Mirror(self, Mirror ):
        if Mirror == self.VRAM_HMIRROR:
            self.SetVRAM_Bank( 0, 0, 1, 1 )
            #self.SetNT_bank(0, 0, 1, 1)
			
        elif Mirror == self.VRAM_VMIRROR:
            self.SetVRAM_Bank( 0, 1, 0, 1 )
            #self.SetNT_bank( 0, 1, 0, 1 )
			
        elif Mirror == self.VRAM_MIRROR4L:
            self.SetVRAM_Bank( 0, 0, 0, 0 )
            #self.SetNT_bank( 0, 0, 0, 0 )
			
        elif Mirror == self.VRAM_MIRROR4H:
            self.SetVRAM_Bank( 1, 1, 1, 1 )
            #self.SetNT_bank( 1, 1, 1, 1 )
			
        elif Mirror == self.VRAM_MIRROR4:
            self.SetVRAM_Bank( 0, 1, 2, 3 )
            #self.SetNT_bank( 0, 1, 2, 3 )


    def SetNT_bank(self, bank0, bank1, bank2, bank3):
        self.NT_BANK[bank0] = self.NTArray[0:240,0:256]
        self.NT_BANK[bank1] = self.NTArray[0:240,256:512]
        self.NT_BANK[bank0] = self.NTArray[0:240,512:768]
        self.NT_BANK[bank2] = self.NTArray[240:480,0:256]
        self.NT_BANK[bank3] = self.NTArray[240:480,256:512]
        self.NT_BANK[bank2] = self.NTArray[240:480,512:768]
        
        self.NT_BANK[bank0] = self.NTArray[480:720,0:256]
        self.NT_BANK[bank1] = self.NTArray[480:720,256:512]
        

    def SetVROM_8K_Bank(self,bank):
        for i in range(8):
            self.SetVROM_1K_Bank( i, bank * 8 + i )

    def SetVROM_8K_Bank8(self, bank0, bank1, bank2, bank3,
			 bank4, bank5, bank6, bank7 ):
        self.SetVROM_1K_Bank( 0, bank0)
        self.SetVROM_1K_Bank( 1, bank1)
        self.SetVROM_1K_Bank( 2, bank2)
        self.SetVROM_1K_Bank( 3, bank3)
        self.SetVROM_1K_Bank( 4, bank4)
        self.SetVROM_1K_Bank( 5, bank5)
        self.SetVROM_1K_Bank( 6, bank6)
        self.SetVROM_1K_Bank( 7, bank7)

        

    def SetVROM_4K_Bank(self, page, bank):
        self.SetVROM_1K_Bank( page+0, bank*4+0 );
        self.SetVROM_1K_Bank( page+1, bank*4+1 );
        self.SetVROM_1K_Bank( page+2, bank*4+2 );
        self.SetVROM_1K_Bank( page+3, bank*4+3 );

    def SetVROM_2K_Bank(self, page, bank):
        self.SetVROM_1K_Bank( page+0, bank*2+0 );
        self.SetVROM_1K_Bank( page+1, bank*2+1 );

    def SetVROM_1K_Bank(self, page, bank):
        
        bank %= self.ROM.VROM_1K_SIZE
        #self.VRAM[page*0x400:page*0x400 + 0x400] = self.VROM[0x0400*bank:0x0400*bank + 0x400]
        self.PPU_MEM_BANK[page] = self.VROM[0x0400*bank:0x0400*bank + 0x400]
        self.PPU_MEM_TYPE[page] = 0x00


def MMC_spec():
    MMC_type = nb.deferred_type()
    MMC_type.define(MMC.class_type.instance_type)
    addition_spec = {
            'MMC': MMC_type,
            }
    return addition_spec

def import_MMC_class(jit = True):
    return jitObject(MMC, [], jit = jit)

def load_MMC(MMU = MMU(), jit = True):
    mmc_class, mmc_type = import_MMC_class(jit = jit)
    mmc = mmc_class(MMU)
    return mmc, mmc_type


        
if __name__ == '__main__':
    #mapper = import_MAPPER()
    #print(mapper)
    from rom import ROM ,nesROM
    mmc = MMC(MMU(nesROM().LoadROM('roms//1942.nes')))
    mmc.reset()
    



        
