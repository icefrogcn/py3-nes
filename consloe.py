# -*- coding: UTF-8 -*-
import os,shutil,re
import traceback

import time

import datetime
import threading
import multiprocessing

import rtmidi
import keyboard
import cv2
import pyglet
from numba import njit
from numba.experimental import jitclass
import numpy as np
import numba as nb

#自定义类
from deco import *
from wrfilemod import read_file_to_array

import memory

import rom
from rom import nesROM
from rom import get_Mapper_by_fn


from cpu6502_opcodes import init6502







from apu import APU
from joypad import JOYPAD
#import mappers
#from mappers.main import cartridge, cartridge_spec

from vbfun import MemCopy

from nes import NES

#from mmc import MMC






class CONSLOE(NES):       
    #EmphVal =0

    romName =''

    FrameSkip = 0 #'Integer


    
    def __init__(self,debug = False, jit = True):
        NESLoop = 0
        CPURunning = 1
        FirstRead = 1

        self.memory = memory.Memory()
        self.RAM = self.memory.RAM
    
        self.debug = debug
        self.jit = jit
        self.nesROM = nesROM()

        self.SoundData = []
        
        #self.Mapper = 999
        #self.APU.pAPUinit()
        #self.JOYPAD = JOYPAD()
        #self.JOYPAD2 = JOYPAD()

        #self.FrameBuffer = np.zeros((720, 768, 3),np.uint8)
               
        #self.CPURunning = cpu6502.CPURunning
        
    @property
    def status(self):
        return "PC:%d,clockticks:%d PPUSTATUS:%d,Frames %d,CurrLine:%d a:%d X:%d Y:%d S:%d p:%d opcode:%d " %self.CPU.status()


    def LoadROM(self,filename):
        self.ROM = self.nesROM.LoadROM(filename)
        #self.Mapper = self.ROM.Mapper

    def LoadCheatCode(self,filename):
        self.CheatCode = []
        cheat_file = '%s.txt' %filename[:-4]
        if os.path.exists(cheat_file):
            for item in bytearray(read_file_to_array(cheat_file)).decode('utf8').split('\n'):
                if '#' in item:
                    self.CheatCode.append(item.split()[1])
            Log_SYS('CheatCode File Found...Loading')
        else:
            Log_SYS('CheatCode File Not Found...')
        
            
    def PowerON(self):
        NES.CPURunning = True

    def PowerOFF(self):
        self.ShutDown()
        #self.APU.ShutDown()

    def initMIDI(self):
        pass


    def Load_MAPPER(self):
        Log_SYS('loading MAPPER CLASS')
        from mmc import load_MAPPER
        self.MAPPER, self.MAPPER_type = load_MAPPER(self, jit = self.jit)
        Log_SYS('init MAPPER')
    
        
    def Load_PPU(self):
        Log_SYS('loading PPU CLASS')
        from ppu import load_PPU
        self.PPU, self.PPU_type = load_PPU(self, jit = self.jit)
        print(self.PPU)
        Log_SYS('init PPU')
        self.PPU.pPPUinit(self.PPU_Running,self.PPU_render,self.PPU_debug)
            
    def Load_CPU(self):
        Log_SYS('loading CPU CLASS')
        from cpu import load_CPU
        addition_spec = {
            'PPU': self.PPU_type,
            'MAPPER':self.MAPPER_type
            }
        self.CPU, self.CPU_type = load_CPU(self, addition_spec, jit = self.jit)
        Log_SYS('init CPU')
       

    
    def StartingUp(self):
        Log_SYS('RESET')
        self.memory.RAM[::] = 0
        self.memory.VRAM[:] = 0
        self.memory.SpriteRAM[:] = 0
        
        Log_SYS('init APU')
        self.APU = APU(self.memory)
        
        init6502()

        try:
            self.Load_MAPPER()
            
            self.Load_PPU()
            self.Load_CPU()
            
            self.CPU.SET_NEW_MAPPER_TRUE()
            self.CPU.MAPPER.reset()
            
            LoadNES = 1
            Log_SYS("NEW MAPPER process")


        except:
            print (traceback.print_exc())
            
        print(self.CPU.RAM)
        print(type(self.CPU.RAM))

        
        if LoadNES == 0 :
            return False

 
        Log_SYS("Successfully loaded %s" %self.nesROM.filename)
        
        self.start = time.time()
        self.totalFrame = 0

        #self.PPU.ScrollToggle = 1
        self.PowerON()
        
        
        Log_SYS("The number of CPU is:",str(multiprocessing.cpu_count()))
        Log_SYS('Parent process %s.' % os.getpid())
        self.pool = multiprocessing.Pool(multiprocessing.cpu_count())
            
        self.Running = 1

        self.CPU.reset6502()
        print ('6502 reset:', self.status )

        self.thread_show(target = self.Waiting_compiling)
        
        self.thread_show(target = self.ShowFPS)
        
        #if self.PPU_Running and self.PPU_render:

        #    blit_thread.start()

        self.ScreenShow()

        self.run()

        self.PowerOFF()
        
    def thread_show(self,target):
        Waiting_thread = threading.Thread(target = target)
        Waiting_thread.daemon = True
        Waiting_thread.start()

        
    def run(self):
        blit_delay = 0
        self.realFrames = 0
        wish_fps = 60
        start = time.time()
        exec_cycles = 0
        forceblit = 0
        while self.Running:
            #t = threading.Thread(target = self.CPU.exec6502)
            #t.start()
            Flag = self.CPU.run6502()

            if Flag == self.CPU.FrameSound:
                pass
                #Log_HW('Play Sound')
                self.APU.updateSounds(self.CPU.Frames)
                #self.SaveSounds()
            
            if Flag == self.CPU.FRAME_RENDER:
                #self.CPU.FrameRender_ZERO()
                #Frames = self.CPU.Frames
                if forceblit or self.CPU.Frames % wish_fps == 0 or blit_delay/((self.CPU.Frames % wish_fps) + 1) <= (1.000/wish_fps):
                    self.blitFrame()
                    self.realFrames += 1

                blit_delay += (time.time() - start)
                

                if self.CPU.Frames % wish_fps == wish_fps - 1:
                    blit_delay = 0
                start = time.time()


    
                self.Running = JOYPAD_CHK(self.CPU)

                self.Cheat()


    def SaveSounds(self):
        #self.SoundData.append('%d,%s' %(self.CPU.Frames,','.join(self.APU.Sound[0:0x15]])))
        with open('sounddata.txt','a') as f:
            f.write('%d,%s;' %(self.CPU.Frames,','.join([str(i) for i in self.APU.Sound[0:0x15]])))
            
        #print()
        
    def Cheat(self):
        if self.CheatCode:
            for item in self.CheatCode:
                CheatCode = item.split('-')
                addr = eval('0x' + CheatCode[0])
                size = int(CheatCode[1])
                value = eval('0x' + CheatCode[2])
                self.RAM[0,addr] = value
                
    def Waiting_compiling(self):
        if not self.jit:return
        Log_SYS('First runing jitclass, compiling is a very time-consuming process...')
        Log_SYS('take about 120 seconds (i3-6100U)...ooh...waiting...')
        start = time.time()
        while self.CPU.Frames == 0:
            Log_SYS('jitclass is compiling...%f %% %d' %((time.time()- start) / 1.20 , self.CPU.clockticks6502))
            #print '6502:',self.status
            if self.CPU.clockticks6502 > 0:break
            if ((time.time()- start) / 3.00) > 150:break
            time.sleep(5)
        Log_SYS('jitclass compiled...')
            
    def blitFrame(self):
        if self.PPU_Running:
            if self.CPU.Frames:
                if self.PPU_render:
                    self.PPU.RenderFrame()
                    
                    if self.debug:
                        pass
                        self.blitPatternTable()
                        self.blitPal()
                        #self.batch.draw()
                    else:
                        self.blitScreen()
                        self.blitPal()

    def blitFrame_thread(self):

            print ('blitFrame: ',self.CPU.Frames)
            if self.CPU.Frames:
                self.FrameBuffer = paintBuffer(self.PPU.FrameArray,self.PPU.Pal,self.PPU.Palettes)
                
                if self.debug == False and self.PPU_render:
                    pass
                    self.blitScreen()
                    self.blitPal()
                    
                else:
                    self.blitPatternTable()
                    self.blitPal()
            
    def ScreenShow(self):
        if self.PPU_Running == 0:
            self.PPU_render = False
            return
        if self.PPU_Running and self.PPU_render and self.debug == False:
            cv2.namedWindow('Main', cv2.WINDOW_NORMAL)
            cv2.namedWindow('Pal', cv2.WINDOW_NORMAL)
            #self.win_pal = pyglet.window.Window(visible=False)
            #self.win_pal.set_size(320, 16)
            #self.win_pal.on_draw = on_draw
            #self.win_pal.set_visible(True)
            #self.batch = pyglet.graphics.Batch()
            
        else:
            cv2.namedWindow('Pal', cv2.WINDOW_NORMAL)
            cv2.namedWindow('PatternTable0', cv2.WINDOW_NORMAL)
            cv2.namedWindow('SC_TEST', cv2.WINDOW_NORMAL)
        #cv2.namedWindow('PatternTable2', cv2.WINDOW_NORMAL)
        #cv2.namedWindow('PatternTable3', cv2.WINDOW_NORMAL)
    def ShutDown(self):
        if self.PPU_render:
            cv2.destroyAllWindows()
        if self.APU.available_ports:
            self.APU.midiout.close_port()
        del self.CPU
        del self.PPU
        del self.MAPPER
            
    def blitScreen(self):
        self.FrameBuffer = paintBuffer(self.PPU.FrameArray[self.PPU.scY:self.PPU.scY + 240,self.PPU.scX:self.PPU.scX+256],self.PPU.Pal,self.PPU.Palettes)
        cv2.imshow("Main", self.FrameBuffer)
        cv2.waitKey(1)

    def blitPal(self):
        cv2.imshow("Pal", np.array([[self.PPU.Pal[i] for i in self.PPU.Palettes]]))
        cv2.waitKey(1)

    def blitPatternTable(self):
        self.FrameBuffer = paintBuffer(self.PPU.FrameArray,self.PPU.Pal,self.PPU.Palettes)
        cv2.line(self.FrameBuffer,(0,240),(768,240),(0,255,0),1) 
        cv2.line(self.FrameBuffer,(0,480),(768,480),(0,255,0),1) 
        cv2.line(self.FrameBuffer,(256,0),(256,720),(0,255,0),1) 
        cv2.line(self.FrameBuffer,(512,0),(512,720),(0,255,0),1) 
        cv2.rectangle(self.FrameBuffer, (self.PPU.scX,self.PPU.scY),(self.PPU.scX+255,self.PPU.scY + 240),(0,0,255),1)
        cv2.imshow("PatternTable0", self.FrameBuffer)
        cv2.waitKey(1)
        
    def ShowFPS(self):
        while self.CPU.Frames == 0:
            pass
            
        start = time.time()
        totalFrame = 0
        while self.Running:
            time.sleep(2)
            if self.CPU.Frames > 1 and self.CPU.Frames == totalFrame:break
            nowFrames = self.CPU.Frames
            duration = time.time() - start
            #if duration > 4:
            start = time.time()
            FPS =  'FPS: %d / %d' %(int((nowFrames - totalFrame) / duration), int(self.realFrames/duration))  #
            print (self.PPU.VRAM)
            #cv2.setWindowTitle('Main',"%s %d %d %d"%(FPS,self.CPU.PPU.CurrentLine,self.CPU.PPU.vScroll,self.CPU.PPU.HScroll))
            self.realFrames = 0
            print (FPS, nowFrames, self.CPU.FrameFlag,self.APU.ChannelWrite, self.CPU.clockticks6502)#,self.CPU.PPU.render,self.CPU.PPU.tilebased
            print (self.PPU.Palettes)
            
            totalFrame = nowFrames
        

            


P1_PAD = ['k','j','v','b','w','s','a','d','i','u']

def JOYPAD_PRESS(PAD_SET):
    padbit = 0
    for i,key in enumerate(P1_PAD):
        if keyboard.is_pressed(key):padbit |= 1 << i
    return padbit

    
def JOYPAD_CHK(CPU):
    #pad1bit = 0
    
    #CPU.JOYPAD.AAA_press(keyboard.is_pressed('i'))
    #print CPU.JOYPAD1.Joypad[0]
    #CPU.JOYPAD.BBB_press(keyboard.is_pressed('u'))
    #print CPU.JOYPAD1.Joypad[1]
    #CPU.JOYPAD.A_press(keyboard.is_pressed('k'))
    #CPU.JOYPAD.B_press(keyboard.is_pressed('j'))
    #CPU.JOYPAD.SELECT_press(keyboard.is_pressed('v'))
    #CPU.JOYPAD.START_press(keyboard.is_pressed('b'))
    #CPU.JOYPAD.UP_press(keyboard.is_pressed('w'))
    #CPU.JOYPAD.DOWN_press(keyboard.is_pressed('s'))
    #CPU.JOYPAD.LEFT_press(keyboard.is_pressed('a'))
    #CPU.JOYPAD.RIGHT_press(keyboard.is_pressed('d'))
    CPU.JOYPAD.pad1bit = JOYPAD_PRESS(P1_PAD)
    CPU.JOYPAD.SyncSub()
    #print  'set pad1bit' , bin(CPU.JOYPAD.pad1bit)
    if keyboard.is_pressed('0'):
        print ("turnoff")
        return 0
    else:
        return 1
    

@njit
def MaskBankAddress(bank, PrgCount):
        if bank >= PrgCount * 2 :
            i = 0xFF
            while (bank & i) >= PrgCount * 2:
                i = i // 2
            
            MaskBankAddress = (bank & i)
        else:
            MaskBankAddress = bank
        return MaskBankAddress
@njit
def paintBuffer(FrameBuffer,Pal,Palettes):
    [rows, cols] = FrameBuffer.shape
    img = np.zeros((rows, cols,3),np.uint8)
    for i in range(rows):
        for j in range(cols):
            img[i, j] = Pal[Palettes[FrameBuffer[i, j]]]
    return img
    
def show_rom_info(ROM):
    print ("[ " , ROM.PrgCount , " ] 16kB ROM Bank(s)")
    print ("[ " , ROM.ChrCount , " ] 8kB CHR Bank(s)")
    print ("[ " , ROM.ROMCtrl , " ] ROM Control Byte #1")
    print ("[ " , ROM.ROMCtrl2 , " ] ROM Control Byte #2")
    print ("[ " , ROM.Mapper , " ] Mapper")
    print ("Mirroring=" , ROM.Mirroring , " Trainer=" , ROM.Trainer , " FourScreen=" , ROM.FourScreen , " SRAM=" , ROM.UsesSRAM)
    

ROMS_DIR = os.getcwd()+ '\\roms\\'
#ROMS_DIR = 'F:\\individual_\\Amuse\\EMU\FCSpec\\'

def roms_list():
    return [item for item in os.listdir(ROMS_DIR) if ".nes" in item.lower()]

def get_roms_mapper(roms_list):
    roms_info = []
    for i,item in enumerate(roms_list):
        mapper = get_Mapper_by_fn(ROMS_DIR + item)
        #if mapper in [0,2]:
            
        roms_info.append([i,item,get_Mapper_by_fn(ROMS_DIR + item)])
    return roms_info
        
def show_choose(ROMS_INFO):
    for item in ROMS_INFO:
        print (item[0],item[1],item[2])
    print ("---------------")
    print ('choose a number as a selection.')

def fresh_pyc(pyc):
    if '.pyc' in pyc:
        if os.path.exists(pyc):os.remove(pyc)

def run(debug = False, jit = True):
    ROMS = roms_list()
    ROMS_INFO = get_roms_mapper(ROMS)
    fc = CONSLOE(debug,jit)

    while True:
        show_choose(ROMS_INFO)
        gn = input("choose a number: ")
        print (gn)
        if gn == 999:
            break
        if not int(gn) <= len(ROMS):
            continue
        #fc.debug = True
        fc.LoadROM(ROMS_DIR + ROMS[int(gn)])
        fc.LoadCheatCode(ROMS_DIR + ROMS[int(gn)])
        print (fc.CheatCode)
        fc.PPU_Running = 1
        fc.PPU_render = 1
        fc.PPU_debug = debug
        fc.StartingUp()


if __name__ == '__main__':

    run(debug = True)
    #run(debug = True, jit = False)
    #run()

        










        
