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
from mmu import MMU, jit_MMU_class


POST_ALL_RENDER = 0
PRE_ALL_RENDER  = 1
POST_RENDER     = 2
PRE_RENDER      = 3
TILE_RENDER     = 4

Log_SYS('import MAPPER class')
from mmc import MMC
from mapper import MAPPER, jit_MAPPER_class


Log_SYS('import PPU CLASS')
from ppu_reg import PPUREG, PPUBIT
from ppu import PPU,jit_PPU_class

Log_SYS('import CPU CLASS')
from cpu import CPU6502, jit_CPU_class


ScanlineCycles = 1364
FETCH_CYCLES = 8
HDrawCycles = 1024
HBlankCycles = 340

Log_SYS('import APU CLASS')
from apu import APU

Log_SYS('import JOYPAD CLASS')
from joypad import JOYPAD


nes_spec = [
    ]
#@jitclass
class NES(object):
    
    MMU:MMU
    MMC:MMC
    MAPPER:MAPPER
    
    PPUREG:PPUREG
    PPU:PPU
    CPU:CPU6502
    APU:APU
    JOYPAD:JOYPAD
    
    
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
        
        self.JOYPAD = JOYPAD()
        print(self.JOYPAD)
        
        self.CPU = CPU6502(self.MMU, self.PPU, self.MAPPER, self.JOYPAD)
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
        return 3

    def EmulationCPU(self,basecycles):
        self.base_cycles += basecycles
        cycles = int((self.base_cycles//12) - self.emul_cycles)
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
                        else:
                            pass
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
                        else:
                            pass

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
        LOGHW('NES Power ON')
        self.reset()
        
    def reset(self):
        LOGHW('NES RESET')
        self.Frames = 0
        
        self.MMU.reset()

        self.MMC.reset()
        self.MAPPER.reset()
        print(self.CPU.RAM)
        
        self.PPU.reset()

        self.CPU.reset6502()

        self.JOYPAD.reset()
        


        self.base_cycles = self.emul_cycles = 0

    def run(self,isDraw = 1):
        self.Frames += self.EmulateFrame(isDraw)
        self.APU.updateSounds() 
        self.PPU.paintScreen(isDraw)
        if self.PPU.showNT:
            self.PPU.paintVRAM(isDraw)
        if self.PPU.showPT:
            self.PPU.paintPT(isDraw)
        
        #return self.Frames


def import_NES_class(jit = 1):
    
    global MAPPER
    MAPPER = jit_MAPPER_class(jit = jit)
    MAPPER_type = jitType(MAPPER)
    
    global PPU
    PPU = jit_PPU_class(jit = jit)
    PPU_type = jitType(PPU)
    
    global CPU6502
    CPU6502 = jit_CPU_class(
            {'MAPPER': MAPPER_type,
            'PPU': PPU_type}, jit = jit)
    CPU_type = jitType(CPU6502)

    NES_spec = {
            'MAPPER': MAPPER_type,
            'CPU': CPU_type,
            'PPU': PPU_type
            }
    
    return jitObject(NES, NES_spec , jit = jit)

def load_NES(jit = 1):
    nes_class = import_NES_class(jit)
    return nes_class()    

async def FPS():
        loop = asyncio.get_running_loop()
        end_time = loop.time() + 5.0
        sf = nes.Frames
        while True:
            if (loop.time() + 1.0) >= end_time:
                break
            await asyncio.sleep(1)
            t = time.time() - st
            fps = (nes.Frames - sf) // t
            cv2.setWindowTitle('Main',f'{fps}')
            
        
async def show():
        cv2.imshow("Main", nes.PPU.ScreenBuffer)
        key = cv2.waitKey(1)
        
async def run():
        while True:
            nes.run()
            JOYPAD_CHK(nes.JOYPAD)
            playmidi(nes.APU)
            await show()
            #await FPS()
if __name__ == '__main__':
    from rom import LoadROM

    nes = load_NES(1)
    #nes.insertCARD(LoadROM('roms//Sangokushi 2 - Hanou No Tairiku (J).nes'))
    #nes.insertCARD(LoadROM('roms//魂斗罗1代 无限人+散弹枪.nes'))
    #nes.insertCARD(LoadROM('roms//1944.nes'))
    #nes.insertCARD(LoadROM('roms//1942.nes'))
    nes.insertCARD(LoadROM('roms//kage.nes'))
    #nes.insertCARD(LoadROM('roms//Dr Mario (JU).nes'))
   
    import cv2
    cv2.namedWindow('Main', cv2.WINDOW_NORMAL)

    nes.PowerON()

    Frames = 0

    from apu import initMidi,playmidi
    import rtmidi

    from joypad import JOYPAD_CHK
    import keyboard

    import asyncio
    
    initMidi()

    
    asyncio.run(run())      #协程模式运行







        
