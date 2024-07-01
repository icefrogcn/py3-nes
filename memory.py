# -*- coding: UTF-8 -*-
import numpy as np
import numba as nb
from numba.experimental  import jitclass
from numba import uint8,uint16
from numba.typed import Dict
from numba import types

#print('loading MEMORY CLASS')
'''@jitclass([('VRAM',uint8[:]), \
           ('SpriteRAM',uint8[:]), \
           ('RAM',uint8[:,:]) \
           ])'''
@jitclass
class Memory(object):
    VRAM:uint8[:,:] 
    SpriteRAM:uint8[:]
    RAM:uint8[:,:]
    
    def __init__(self):
        self.VRAM = np.zeros((12,0x1000),np.uint8)
        #self.VRAM = np.zeros(0x4000,np.uint8)
        self.SpriteRAM = np.zeros(0x100,np.uint8)
        self.RAM = np.zeros((8,0x2000), np.uint8)

    def reset(self):
        self.VRAM = np.zeros((12,0x1000),np.uint8)
        self.SpriteRAM = np.zeros(0x100,np.uint8)
        self.RAM = np.zeros((8,0x2000), np.uint8)
        
#memory_type = nb.deferred_type()
#memory_type.define(Memory.class_type.instance_type)
        

                    
if __name__ == '__main__':

    mem = Memory()


    

    
    
    
    








        
