# -*- coding: UTF-8 -*-
import os,re

import time
import datetime


from numba.experimental import jitclass
from numba import uint8,uint16,uint32
from numba.typed import Dict
from numba import types
import numpy as np
import numba as nb

from deco import *
from jitcompile import jitObject,jitType

Log_SYS('import ROM class')
from rom import ROM


Log_SYS('import MMU class')
from mmu import MMU


Log_SYS('import MAPPER class')
from mmc import MMC
from mapper import MAPPER


Log_SYS('import PPU CLASS')
from ppu_reg import PPUREG, PPUBIT
from ppu import PPU, load_PPU, jit_PPU_class

Log_SYS('import CPU CLASS')
from cpu import CPU6502, cpu_spec,jit_CPU_class
CPU = jit_CPU_class({ 'PPU': jitType(PPU)})



#import rom

FETCH_CYCLES = 8
ScanlineCycles = 1364
HDrawCycles = 1024


nes_spec = [
    ]
#@jitclass
class NES(object):
    jit:uint8
    
    MMU:MMU
    MMC:MMC
    MAPPER:MAPPER
    
    PPUREG:PPUREG
    PPU:PPU
    CPU:CPU
    NES_scanline:uint16
    
    def __init__(self,
                 ROM = ROM(),
                 jit = 1):

        self.jit = jit

        self.MMU = MMU(ROM)
        print(self.MMU)
        
        self.MMC = MMC(self.MMU)
        print(self.MMC)
        
        self.MAPPER = MAPPER(self.MMC)
        print(self.MAPPER)
        
        #self.PPUREG = PPUREG(self.MMU)
        #print(self.PPUREG)
        
        self.PPU = PPU(PPUREG(self.MMU))
        print(self.PPU)
        
        self.CPU = CPU(self.MMU, self.PPU)
        print(self.CPU)
        
        self.NES_scanline = 0

        
        
    @property
    def RAM(self):
        return self.MMU.RAM
    @property
    def ROM(self):
        return self.MMU.ROM

    def RenderMethod(self):
        return 0

    def PowerON(self):
        print('RESET')
        self.MMU.reset()

        self.MMC.reset()
        self.MAPPER.reset()

        print(self.CPU.RAM)
        print(type(self.CPU.RAM))
    
    def EmulateFrame(self,isDraw=1):
        scanline = 0
        while True:
            if( self.RenderMethod != TILE_RENDER ):
                if scanline == 0:
                    if( self.RenderMethod < POST_RENDER ):
                        self.EmulationCPU(ScanlineCycles)
                        self.PPU.FrameStart()
                        self.PPU.ScanlineNext()
                        if self.MAPPER.HSync(scanline):self.IRQ_NotPending()
                        self.PPU.ScanlineStart()
                    else:
                        self.EmulationCPU(HDrawCycles)
                        self.PPU.FrameStart()
                        self.PPU.ScanlineNext()
                        if self.MAPPER.HSync(scanline):self.IRQ_NotPending()
                        self.EmulationCPU(FETCH_CYCLES*32)
                        self.PPU.ScanlineStart()
                        self.EmulationCPU( FETCH_CYCLES*10 + 4 )
                    
                elif scanline < 240:
                    if( self.RenderMethod < POST_RENDER ):
                        if( self.RenderMethod == POST_ALL_RENDER ):
                            self.EmulationCPU(ScanlineCycles)
                        if isDraw:
                            self.PPU.RenderScanline(scanline)
                        self.PPU.ScanlineNext()
                        if( self.RenderMethod == PRE_ALL_RENDER ):
                            self.EmulationCPU(ScanlineCycles )
                            
                        if self.MAPPER.HSync(scanline):self.IRQ_NotPending()
                        self.PPU.ScanlineStart()
                    else:
                        if( self.RenderMethod == POST_RENDER ):
                            self.EmulationCPU(HDrawCycles)
                        if isDraw:
                            self.PPU.RenderScanline(scanline)

                        if( self.RenderMethod == PRE_RENDER ):
                            self.EmulationCPU(HDrawCycles)

                        self.PPU.ScanlineNext()

                        if self.MAPPER.HSync(scanline):self.IRQ_NotPending()
                        self.EmulationCPU(FETCH_CYCLES*32)
                        self.PPU.ScanlineStart()
                        self.EmulationCPU(FETCH_CYCLES*10 + 4 )



                    
                elif scanline == 240:
                    #mapper->VSync()
                    #self.isDraw = 1
                    
                    if( self.RenderMethod == POST_RENDER ):
                        self.EmulationCPU(ScanlineCycles)
                        if self.MAPPER.HSync( scanline ):self.IRQ_NotPending()
                    else:
                        self.EmulationCPU(HDrawCycles)
                        if self.MAPPER.HSync( scanline ):self.IRQ_NotPending()
                        self.EmulationCPU(HBlankCycles)
                        
                    self.Frames += 1
                    
                    
                elif scanline <= 261: #VBLANK
                    self.isDraw = 0
                        
                    if scanline == 261:
                        self.PPU.VBlankEnd()
                        
                    if( self.RenderMethod < POST_RENDER ):
                        if scanline == 241:
                            self.PPU.VBlankStart()
                            self.EmulationCPU_BeforeNMI(4*12)
                            if self.PPU.reg.PPUCTRL & 0x80:
                                self.NMI()
                            self.EmulationCPU(ScanlineCycles-(4*12))
                        else:
                            self.EmulationCPU(ScanlineCycles)

                        if self.MAPPER.HSync( scanline ):self.IRQ_NotPending()
                    else:
                        if scanline == 241:
                            self.PPU.VBlankStart()
                            self.EmulationCPU_BeforeNMI(4*12)
                            if self.PPU.reg.PPUCTRL & 0x80:
                                self.NMI()
                            self.EmulationCPU(HDrawCycles-(4*12))
                        else:
                            self.EmulationCPU(HDrawCycles)
                        if self.MAPPER.HSync( scanline ):self.IRQ_NotPending()
                        self.EmulationCPU(HBlankCycles)

                    if scanline == 261:
                        scanline = 0
                        return 1
                scanline += 1

def jit_NES_class(jit = 1):
    CPU_type = jitType(CPU)
    
    NES_spec = {
            'CPU': CPU_type
            }
    
    return jitObject(NES, NES_spec , jit = jit)

def load_NES(jit = 1):
    nes_class, nes_type = import_NES_class(jit = jit)
    return nes_class, nes_type        



if __name__ == '__main__':
    from rom import nesROM
    ROM = nesROM().LoadROM('roms//1942.nes')
    #jit_CPU_class({ 'PPU': jitType(PPU)})
    #CPU = jit_CPU_class({ 'PPU': jitType(PPU)})
    nes = NES(ROM)
    print(nes)
    #PPU = jit_PPU_class()
    #CPU = jit_CPU_class({})
    nesc = jit_NES_class()
    print(nesc)
    #nesj = nesc(ROM)

    
    
        










        
