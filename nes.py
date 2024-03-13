# -*- coding: UTF-8 -*-
import os,re

import time
import datetime

import numpy as np
from numba import jit

#自定义类
from wrfilemod import read_file_to_array

#import mmc



from vbfun import MemCopy






def fillTLook():
    tLook = []#[0] * 0x80000
    for b1 in range(0x100):             #= 0 To 255
        for b2 in range(0x100):              #= 0 To 255
            for X in range(0x8):                #= 0 To 7
                c = 1 if b1 & pow2[X] else  0
                c += 2 if b2 & pow2[X]  else 0
                tLook.append(c)
                #tLook[b1 * 2048 + b2 * 8 + X] = c
    return tLook


class NES(object):       

    'DF: powers of 2'
    pow2 = [2**i for i in range(31)]#*(31) #As Long
    #pow2 = [2**i for i in range(32)]#*(31) #As Long
    pow2 +=  [-2147483648]
    

    'DF: powers of 2'


    
    bank_regs = [0]*16 #Byte

    maxCycles1 = 114
    Mapper = 0

    PROM = []
    PROM_8K_SIZE  = 0
    PROM_16K_SIZE = 0
    PROM_32K_SIZE = 0



    VROM = []
    VROM_1K_SIZE = 0
    VROM_2K_SIZE = 0
    VROM_4K_SIZE = 0
    VROM_8K_SIZE = 0

    
    Mapper, Mirroring, Trainer, FourScreen = 0,0,0,0
    MirrorXor = 0 # As Long 'Integer
    UsesSRAM = False #As Boolean
    
    SpecialWrite6000 = False
    
    CPUPaused = False #As Boolean

    CPURunning = 0

    APURunning = 1
    
    PPURunning = 1
    
    Frames = 0

    newmapper_debug = 0

    Running = 1
    
    def __init__(self,debug = False):
        NESLoop = 0

        FirstRead = True

        self.debug = False





if __name__ == '__main__':
    pass

    
    
        










        
