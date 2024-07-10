# -*- coding: UTF-8 -*-
import os,re

import time
import datetime
import numpy as np
import numba as nb

from numba.experimental import jitclass
from numba import uint8,uint16,uint32
from numba.typed import Dict
from numba import types

import mmu

#import rom

FETCH_CYCLES = 8
ScanlineCycles = 1364
HDrawCycles = 1024


nes_spec = [('NES_scanline',uint16),
            ]
class NES(object):       

    def __init__(self,debug = False):
        
        self.NES_scanline = 0

        FirstRead = True

        self.debug = False

    def RenderMethod(self):
        return 0
    
    def EmulateFrame(self):
        scanline = 0

        #cheatCODE
        
        self.NES_scanline = scanline

        if( self.RenderMethod != TILE_RENDER ):
            while True:
                #self.PPU.SetRenderScanline( scanline )
                
                if scanline == 0:
                    if( self.RenderMethod < POST_RENDER ):
                        self.CPU.EmulationCPU(ScanlineCycles)
                        #ppu->FrameStart();
			#ppu->ScanlineNext();
                        if self.MAPPER.HSync(scanline):self.CPU.IRQ_NotPending()
                        #ppu->ScanlineStart();
                    else:
                        self.EmulationCPU(HDrawCycles)
                        #ppu->FrameStart();
			#ppu->ScanlineNext();
                        if self.MAPPER.HSync(scanline):self.CPU.IRQ_NotPending()
                        self.CPU.EmulationCPU(FETCH_CYCLES*32)
                        #ppu->ScanlineStart();
                        self.CPU.EmulationCPU(FETCH_CYCLES*10 + 4 )

                elif scanline < 240:
                    if( self.RenderMethod < POST_RENDER ):
                        if( self.RenderMethod == POST_ALL_RENDER ):
                            self.CPU.EmulationCPU(ScanlineCycles)
                        #self.PPU.Scanline()

                        #ppu->ScanlineNext();
                        if( self.RenderMethod == PRE_ALL_RENDER ):
                            self.CPU.EmulationCPU(ScanlineCycles )
                            
                        if self.MAPPER.HSync(scanline):self.CPU.IRQ_NotPending()
                        #ppu->ScanlineStart();
                    else:
                        if( self.RenderMethod == POST_RENDER ):
                            self.CPU.EmulationCPU(HDrawCycles)
                        #self.PPU.Scanline()

                        if( self.RenderMethod == PRE_RENDER ):
                            self.EmulationCPU(HDrawCycles)

                        #ppu->ScanlineNext();
                        if self.MAPPER.HSync(scanline):self.IRQ_NotPending()
                        self.CPU.EmulationCPU(FETCH_CYCLES*32)
                        #ppu->ScanlineStart();
                        self.CPU.EmulationCPU(FETCH_CYCLES*10 + 4 )

                elif scanline == 240:
                    #mapper->VSync()
                    if( self.RenderMethod == POST_RENDER ):
                        self.CPU.EmulationCPU(ScanlineCycles)
                        if self.MAPPER.HSync(scanline):self.IRQ_NotPending()
                    else:
                        self.CPU.EmulationCPU(HDrawCycles)
                        if self.MAPPER.HSync(scanline):self.IRQ_NotPending()
                        self.CPU.EmulationCPU(HBlankCycles)
                    
                    #self.Frames += 1
                    
                elif scanline <= 261: #VBLANK

                        
                    if self.PPU.CurrentLine == 261:
                        self.PPU.VBlankEnd()
                        self.FrameFlag |= self.FRAME_RENDER

                    if( self.RenderMethod == POST_RENDER ):
                        if scanline == 241:
                            self.PPU.VBlankStart()
                            self.CPU.EmulationCPU_BeforeNMI(4*12)
                            if self.PPU.reg.PPUCTRL & 0x80:
                                self.CPU.NMI()
                            self.CPU.EmulationCPU(ScanlineCycles-(4*12))
                        else:
                            self.CPU.EmulationCPU(ScanlineCycles)

                        if self.MAPPER.HSync(scanline):self.IRQ_NotPending()
                    else:
                        if scanline == 241:
                            self.PPU.VBlankStart()
                            self.CPU.EmulationCPU_BeforeNMI(4*12)
                            if self.PPU.reg.PPUCTRL & 0x80:
                                self.CPU.NMI()
                            self.CPU.EmulationCPU(HDrawCycles-(4*12))
                        else:
                            self.CPU.EmulationCPU(HDrawCycles)
                        if self.MAPPER.HSync(scanline):self.IRQ_NotPending()
                        self.CPU.EmulationCPU(HBlankCycles)

                    if self.scanline == 262:
                        return 1
                        #self.PPU.CurrentLine_ZERO()
                        #return 0

                scanline += 1

                self.NES_scanline = scanline
                #self.PPU.CurrentLine_increment(1)

        



if __name__ == '__main__':
    pass

    
    
        










        
