# -*- coding: UTF-8 -*-
import os,re

import time
import datetime


from numba.experimental import jitclass
from numba import uint8,uint16,uint32,uint64
from numba.typed import Dict
from numba import types
import numpy as np
import numba as nb

from deco import *
from jitcompile import jitObject,jitType

#Log_SYS('import ROM class')
#from rom import LoadROM


Log_SYS('import MMU class')
from mmu import MMU


Log_SYS('import MAPPER class')
from mmc import MMC
POST_ALL_RENDER = 0
PRE_ALL_RENDER  = 1
POST_RENDER     = 2
PRE_RENDER      = 3
TILE_RENDER     = 4
from mapper import MAPPER


Log_SYS('import PPU CLASS')
from ppu_reg import PPUREG, PPUBIT
from ppu import PPU, load_PPU, jit_PPU_class

Log_SYS('import CPU CLASS')
#from cpu import CPU6502 as CPU
from cpu import CPU6502, cpu_spec,jit_CPU_class


ScanlineCycles = 1364
FETCH_CYCLES = 8
HDrawCycles = 1024
HBlankCycles = 340

Log_SYS('import APU CLASS')
from apu import APU


nes_spec = [
    ]
#@jitclass
class NES(object):
    
    MMU:MMU
    MMC:MMC
    MAPPER:MAPPER
    
    PPUREG:PPUREG
    #PPU:PPU
    #CPU:CPU
    APU:APU
    
    NES_scanline:uint16

    Frames:uint32

    emul_cycles: uint64
    base_cycles: uint64


    
    
    def __init__(self):

        
        self.MMU = MMU()
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

        self.APU = APU(self.MMU)
        print(self.APU)


        self.NES_scanline = 0

        self.Frames = 0

        self.base_cycles = self.emul_cycles = 0

        print(self)
        
    @property
    def RAM(self):
        return self.MMU.RAM
    @property
    def ROM(self):
        return self.MMU.ROM

    @property
    def RenderMethod(self):
        return 0

    def EmulationCPU(self,basecycles):
        self.base_cycles += basecycles
        cycles = (self.base_cycles//12) - self.emul_cycles
        if cycles > 0:
            self.emul_cycles += self.CPU.EXEC6502(cycles)

    def EmulationCPU_BeforeNMI(self,cycles):
        self.base_cycles += cycles
        self.emul_cycles += self.CPU.EXEC6502(cycles//12)

        
    def EmulateFrame(self, isDraw=1):
        #scanline = 0
        for scanline in range(262):
        #while True:
            if( self.RenderMethod != TILE_RENDER ):
                if scanline == 0:
                    if( self.RenderMethod < POST_RENDER ):
                        self.EmulationCPU(ScanlineCycles)
                        self.PPU.FrameStart()
                        self.PPU.ScanlineNext()
                        if self.MAPPER.HSync(scanline, self.PPU.isDispON):
                            self.CPU.IRQ_NotPending()
                        self.PPU.ScanlineStart()
                    else:
                        self.EmulationCPU(HDrawCycles)
                        self.PPU.FrameStart()
                        self.PPU.ScanlineNext()
                        if self.MAPPER.HSync(scanline, self.PPU.isDispON):
                            self.CPU.IRQ_NotPending()
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
                            
                        if self.MAPPER.HSync(scanline, self.PPU.isDispON):
                            self.CPU.IRQ_NotPending()
                        self.PPU.ScanlineStart()
                    else:
                        if( self.RenderMethod == POST_RENDER ):
                            self.EmulationCPU(HDrawCycles)
                        if isDraw:
                            self.PPU.RenderScanline(scanline)

                        if( self.RenderMethod == PRE_RENDER ):
                            self.EmulationCPU(HDrawCycles)

                        self.PPU.ScanlineNext()

                        if self.MAPPER.HSync(scanline, self.PPU.isDispON):
                            self.CPU.IRQ_NotPending()
                        self.EmulationCPU(FETCH_CYCLES*32)
                        self.PPU.ScanlineStart()
                        self.EmulationCPU(FETCH_CYCLES*10 + 4 )



                    
                elif scanline == 240:
                    #mapper->VSync()
                   
                    if( self.RenderMethod < POST_RENDER ):
                        self.EmulationCPU(ScanlineCycles)
                        if self.MAPPER.HSync( scanline , self.PPU.isDispON):
                            self.CPU.IRQ_NotPending()
                    else:
                        self.EmulationCPU(HDrawCycles)
                        if self.MAPPER.HSync( scanline , self.PPU.isDispON):
                            self.CPU.IRQ_NotPending()
                        self.EmulationCPU(HBlankCycles)
                        
                    
                    
                elif scanline <= 261: #VBLANK
                    #self.isDraw = 0
                        
                    if scanline == 261:
                        self.PPU.VBlankEnd()

                    if( self.RenderMethod < POST_RENDER ):
                        if scanline == 241:
                            self.PPU.VBlankStart()
                            self.EmulationCPU_BeforeNMI(4*12)
                            if self.PPU.reg.PPUCTRL & 0x80:
                                self.CPU.NMI()
                            self.EmulationCPU(ScanlineCycles-(4*12))
                        else:
                            self.EmulationCPU(ScanlineCycles)

                        if self.MAPPER.HSync( scanline , self.PPU.isDispON):
                            self.CPU.IRQ_NotPending()
                    else:
                        if scanline == 241:
                            self.PPU.VBlankStart()
                            self.EmulationCPU_BeforeNMI(4*12)
                            if self.PPU.reg.PPUCTRL & 0x80:
                                self.CPU.NMI()
                            self.EmulationCPU(HDrawCycles-(4*12))
                        else:
                            self.EmulationCPU(HDrawCycles)
                        if self.MAPPER.HSync( scanline , self.PPU.isDispON):
                            self.CPU.IRQ_NotPending()
                        self.EmulationCPU(HBlankCycles)

                    if scanline == 261:
                        break
                #scanline = scanline + 1
        return 1

    def insertCARD(self,data):
        self.MMU.ROM.data = data
        self.MMU.ROM.info()
    
    def PowerON(self):
        print('NES Power ON')
        self.reset()
        
    def reset(self):
        print('RESET')
        self.Frames = 0
        
        self.MMU.reset()

        self.MMC.reset()
        self.MAPPER.reset()
        print(self.CPU.RAM)
        
        self.PPU.reset()

        self.CPU.reset6502()
        print ('6502 reset:', self.CPU.status )  


        self.base_cycles = self.emul_cycles = 0

    def run(self,isDraw = 1):
        self.Frames += self.EmulateFrame(isDraw)
        self.PPU.paintScreen(isDraw)
        self.APU.updateSounds(self.Frames)
        
        return 1






def jit_NES_class(jit = 1):
    global PPU
    PPU = jit_PPU_class(jit = jit)
    PPU_type = jitType(PPU)
    
    global CPU
    CPU = jit_CPU_class({'PPU': PPU_type}, jit = jit)
    CPU_type = jitType(CPU)
    NES_spec = {
            'CPU': CPU_type,
            'PPU': PPU_type
            }
    
    return jitObject(NES, NES_spec , jit = jit)

def load_NES(jit = 1):
    nes_class, nes_type = import_NES_class(jit = jit)
    return nes_class, nes_type        


if __name__ == '__main__':
    from rom import LoadROM

    nesj = jit_NES_class(jit = 1)()
    #n = nesc()
    #nesj.insertCARD(LoadROM('roms//Sangokushi 2 - Hanou No Tairiku (J).nes'))
    nesj.insertCARD(LoadROM('roms//1944.nes'))
    #nesj.insertCARD(LoadROM('roms//kage.nes'))
   
    import cv2
    cv2.namedWindow('Main', cv2.WINDOW_NORMAL)

    nesj.PowerON()

    Frames = 0

    from apu import initMidi,playmidi
    import rtmidi

    from joypad import JOYPAD_CHK
    import keyboard
    
    initMidi()
    while True:
        Frames += nesj.run()
        playmidi(nesj.APU)
        JOYPAD_CHK(nesj.CPU.JOYPAD)
        cv2.imshow("Main", nesj.PPU.ScreenBuffer)
        key = cv2.waitKey(1)
        #print(key)
        








        
