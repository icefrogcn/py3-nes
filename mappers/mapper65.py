# -*- coding: UTF-8 -*-
import sys
sys.path.append("..")



#MAPPER
from mapper import MAPPER



class MAPPER(MAPPER,NES):

    def __init__(self,debug = False):
         pass

    def reset(self):
        self.SetPROM_32K_Bank( 0, 1, NES.PROM_8K_SIZE-2, NES.PROM_8K_SIZE-1 );

	if( NES.VROM_8K_SIZE ) :
		self.SetVROM_8K_Bank( 0 )
   
        return 1

    
    def Write(self,addr,data):#$8000-$FFFF Memory write
        if addr == 0x8000:
            self.SetPROM_8K_Bank( 4, data )
        elif addr & 0xB000 == 0xB000:
            self.SetVROM_1K_Bank( addr & 0x0007, data )
        elif addr == 0xA000:
            SetPROM_8K_Bank( 5, data )
        elif addr == 0xC000:
            SetPROM_8K_Bank( 6, data )

if __name__ == '__main__':
    mapper = MAPPER()











        
