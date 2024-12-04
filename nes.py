# -*- coding: UTF-8 -*-
import os,re

import time
import datetime



from numba.experimental import jitclass
from numba import uint8,uint16,uint32,uint64,float32
from numba.typed import Dict
from numba import types
import numpy as np
import numba as nb

import pyglet
from pyglet.window import key

import win32com.directsound.directsound as Win32ds

from deco import *
from jitcompile import jitObject,jitType

#Log_SYS('import ROM class')
#from rom import LoadROM


Log_SYS('import MMU class')
from mmu import MMU, jit_MMU_class


Log_SYS('import MAPPER class')
from mmc import MMC
from mapper import MAPPER, jit_MAPPER_class


Log_SYS('import PPU CLASS')
from ppu_reg import PPUREG, PPUBIT
from ppu import PPU,jit_PPU_class

Log_SYS('import CPU CLASS')
from cpu import CPU6502, jit_CPU_class


Log_SYS('import APU CLASS')
from apu import APU, initMidi,playmidi,stopmidi,MixerOutRender
from directsound import dsbdesc#, DSBUFFERDESC

Log_SYS('import JOYPAD CLASS')
from joypad import JOYPAD,JOYPAD_CHK


ScanlineCycles = 1364
FETCH_CYCLES = 8
HDrawCycles = 1024
HBlankCycles = 340


POST_ALL_RENDER = 0
PRE_ALL_RENDER  = 1
POST_RENDER     = 2
PRE_RENDER      = 3
TILE_RENDER     = 4



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
        
        self.APU = APU(self.MMU)
        print(self.APU)

        self.CPU = CPU6502(self.MMU, self.PPU, self.MAPPER, self.JOYPAD)
        print(self.CPU)


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
        self.MMU.ROM.insertCARD(data)
    
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
        Frames = 0
        while True:
            Frames += self.EmulateFrame(isDraw)
            self.APU.updateSounds() 
            self.PPU.paintScreen(isDraw)
            if self.PPU.showNT:
                self.PPU.paintVRAM(isDraw)
            if self.PPU.showPT:
                self.PPU.paintPT(isDraw)
            
            yield Frames

    
def jit_NES_class(jit = 1):
    
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
    nes_class = jit_NES_class(jit)
    return nes_class()    


class SCREEN(pyglet.window.Window):

    isDraw:uint8
    pad1bit:uint16
    interval:float32
    PowerON:uint8
    
    def __init__(self,nes):
        super().__init__(width=256, height=240, visible=True,vsync = False)
        self.label = pyglet.text.Label('pyNES')
        self.NES = nes
        self.isDraw = 1
        self.pad1bit = 0

        self.fps_display = pyglet.window.FPSDisplay(self)
            #Player1   B     A     SE    ST    UP    DN    LF    RT    BBB   AAA
        self.P1_PAD = [key.K,key.J,key.V,key.B,key.W,key.S,key.A,key.D,key.I,key.U]

        self.interval = 0.00
        self.PowerON = 0
        self.mixerRender = MixerOutRender(self.NES.APU,1.0/59.94)
        self.mixerdata = self.NES.APU.MixerRenderData()
        pyglet.clock.schedule_interval(self.update, 1.0/60.0)
        global DSBUFFERDESC
        DSBUFFERDESC = dsbdesc(self.NES.APU.BufferSize)

        
        print('HARDWARE Ready')

        
    def update(self,event):
        if self.PowerON:
            #t = time.time()
            next(self.nesrun, self.isDraw)
            #self.NES.run(self.isDraw)
            #SaveSounds(self.NES)
            self.JOYPAD_CHK(event)

            #playsound(self.NES.APU,event)
            
            #MixerOut(self.NES.APU,event).play()
            #next(self.mixerRender).play()
            self.NES.APU.interval = event
            next(self.mixerdata)
            DSBUFFERDESC.Update(0, self.NES.APU.SoundBuffer.tobytes())
            #DSBUFFERDESC.SetCurrentPosition(0)
            #DSBUFFERDESC.Play(1)

            
        
    def on_key_press(self, symbol, modifiers):
        for i,k in enumerate(self.P1_PAD):
            if symbol == k:
                self.pad1bit |= 1 << i

        if symbol == key._1:
            self.NES.APU.m_bMute[1] ^= 1
        if symbol == key._2:
            self.NES.APU.m_bMute[2] ^= 1
        if symbol == key._3:
            self.NES.APU.m_bMute[3] ^= 1
        if symbol == key._4:
            self.NES.APU.m_bMute[4] ^= 1
        if symbol == key._5:
            self.NES.APU.m_bMute[5] ^= 1
        print(self.NES.APU.m_bMute)
        
    def on_key_release(self, symbol, modifiers):
        for i,k in enumerate(self.P1_PAD):
            if symbol == k:
                self.pad1bit &= ~(1 << i)
                
        if symbol == key.P:
            self.run()
            
        if symbol == key.R:
            if self.PowerON == 1:
                self.reset()
            
        if symbol == key._0:
            print('POWER OFF')
            self.PowerON = 0
            pyglet.app.exit()
            
    def JOYPAD_CHK(self,event):
        self.NES.JOYPAD.padbitsync[0] = self.pad1bit
        self.NES.JOYPAD.SyncSub()
        
    def on_draw(self):

        if self.isDraw:
            self.clear()
            pyglet.image.ImageData(256,240,'BGR', self.NES.PPU.ScreenBuffer.ctypes.data).blit(0,0)

            self.fps_display.draw()

    def reset(self):
        print('RESET HARDWARE')
        self.PowerON = 0
        self.NES.PowerON()
        self.nesrun = self.NES.run(self.isDraw)
        self.update(1)
        self.PowerON = 1
        
    def run(self):
        if self.PowerON == 0:
            self.reset()
            self.PowerON = 1
            DSBUFFERDESC.Play(1)
            pyglet.app.run()
        

def SaveSounds(NES):
    fn = 'sounddata-%s.txt' %bytes(NES.ROM.name).decode('utf8')
    #if os.exists(fn):
    #    os.remove(fn)
    with open(fn,'a') as f:
            f.write('%d;%s' %(NES.CPU.Frames,','.join([str(i) for i in NES.APU.Sound])))
            f.write(';%s' %(','.join([str(i) for i in NES.APU.ChannelStatus])))
            f.write(';%s' %(','.join([str(i) for i in NES.APU.SoundStatus])))
            f.write('\n')
        

  
if __name__ == '__main__':
    nes = load_NES(1)







        
