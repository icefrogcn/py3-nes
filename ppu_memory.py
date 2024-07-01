# -*- coding: UTF-8 -*-

import traceback

import numpy as np
import numba as nb
from numba.experimental import jitclass
from numba import uint8,uint16
from numba.typed import Dict
from numba import types


from memory import Memory#,memory_type

#print('loading PPU MEMORY INFO CLASS')
'''@jitclass([('memory',memory_type), \
           ('PRGRAM',uint8[:,:]), \
           ('VRAM',uint8[:]), \
           ('SpriteRAM',uint8[:]), \
           ('Palettes',uint8[:])
           ])'''

@jitclass
class PPU_Memory(object):
    memory:Memory
    PRGRAM:uint8[:,:]
    VRAM:uint8[:,:]
    SpriteRAM:uint8[:]
    Palettes:uint8[:]

    
    def __init__(self, memory = Memory()):
        self.memory = memory
        self.PRGRAM     = self.memory.RAM
        self.VRAM       = self.memory.VRAM
        self.SpriteRAM  = self.memory.SpriteRAM
        #self.Palettes   = self.VRAM[0x3F00:0x3F20]#np.zeros(0x20, np.uint8) 
        self.Palettes   = np.zeros(0x20, np.uint8) 
        
        
        

    #@property
    #def VRAM(self):
    #    return self.memory.VRAM
    '''
    def read(self,address):
        addr = address & 0x3FFF
        data = 0
        if 0x2000<= addr <0x3F00:
            t_address = addr - 0x2000
            t_address %= 0x1000
            return self.VRAM[t_address + 0x2000]
        elif(addr >= 0x3000):
            if addr >= 0x3F00:
                data &= 0x3F
                data = self.Palettes[addr & 0x1F]
            addr &= 0xEFFF
        else:
            return self.VRAM[addr]
        return data
        '''

                    
if __name__ == '__main__':

    ppu_ram = PPU_Memory()
    print(ppu_ram)

    

    
    
    
    








        
