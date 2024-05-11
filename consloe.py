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
from mappers.main import cartridge, cartridge_spec

from vbfun import MemCopy

from nes import NES

from mmc import MMC






class CONSLOE(MMC, NES):       
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

        
        #self.Mapper = 999
        #self.APU.pAPUinit()
        #self.JOYPAD = JOYPAD()
        #self.JOYPAD2 = JOYPAD()

        #self.FrameBuffer = np.zeros((720, 768, 3),np.uint8)
               
        #self.CPURunning = cpu6502.CPURunning
        
    @property
    def status(self):
        return "PC:%d,clockticks:%d PPUSTATUS:%d,Frames %d,CurrLine:%d a:%d X:%d Y:%d S:%d p:%d opcode:%d " %self.CPU.status()

    def CreateMapper(self, mapper = 0):
        Log_SYS("loading MAPPER CLASS %d" %mapper)
        MAPPER = __import__('mappers.mapper%d' %mapper, fromlist=['MAPPER','mapper_spec'])
        C_MAPPER = MAPPER.MAPPER
        mapper_spec = MAPPER.mapper_spec
        MAPPER_type = nb.deferred_type()
        if self.jit:
            try:
                if not hasattr(C_MAPPER,"class_type"):
                    cartridge_type = nb.deferred_type()
                    cartridge_type.define(cartridge.class_type.instance_type)
                    mapper_spec.append(('cartridge',cartridge_type))
                    C_MAPPER = jitclass(C_MAPPER, mapper_spec)
                MAPPER_type.define(C_MAPPER.class_type.instance_type)
                    
            except:
                print(traceback.print_exc())
            
        return C_MAPPER, MAPPER_type

    def LoadROM(self,filename):
        self.ROM = self.nesROM.LoadROM(filename)
        #self.Mapper = self.ROM.Mapper

    def LoadCheatCode(self,filename):
        self.CheatCode = []
        cheat_file = filename[:-3] + 'txt'
        if os.path.exists(cheat_file):
            for item in str(bytearray(read_file_to_array(cheat_file))).split('\n'):
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

    def jitObject(self, classObject, classObject_spec, classObject_type, classObjectAddition={}):
        if self.jit:
            try:
                if not hasattr(classObject,"class_type"):
                    for key in classObjectAddition:
                        #Object_type = nb.deferred_type()
                        #Object_type.define(classObjectAddition[key].class_type.instance_type)
                        classObject_spec.append((key,classObjectAddition[key]))
                    #print(classObject_spec)
                    jitObject = jitclass(classObject, classObject_spec)
                    #jitObject_type = nb.deferred_type()
                    classObject_type.define(jitObject.class_type.instance_type)

                    return jitObject
            except:
                print(traceback.print_exc())
            
        return classObject
        
    def import_MAPPER_class(self):
        Log_SYS('init MAPPER')
        C_MAPPER,self.MAPPER_type = self.CreateMapper(self.ROM.Mapper)  #choose correct mapper class without jit
        
        #cart = cartridge(self.ROM, self.memory)
        self.MAPPER = C_MAPPER(cartridge(self.ROM, self.memory))
        #self.MAPPER_type = 
        print(type(self.MAPPER))

        #return 

    def import_CPU_class(self):
        Log_SYS('loading CPU CLASS')
        from cpu import cpu6502,cpu_spec
        addition_spec = {
            'PPU': self.PPU_type,
            'MAPPER':self.MAPPER_type
            }
        self.CPU_type = nb.deferred_type()
        return self.jitObject(cpu6502, cpu_spec, self.CPU_type, addition_spec)
        
            
    def Load_CPU(self):
        cpu = self.import_CPU_class()
        self.CPU = cpu(MAPPER = self.MAPPER,
                        memory = self.memory,
                        PPU = self.PPU,
                        ChannelWrite = self.APU.ChannelWrite)#, #self.APU,)
        Log_SYS('init CPU')

    def import_PPU_class(self):
        Log_SYS('loading PPU CLASS')
        from ppu import PPU,ppu_spec
        self.PPU_type = nb.deferred_type()
        return self.jitObject(PPU, ppu_spec, self.PPU_type)
        
    def Load_PPU(self):
        cPPU = self.import_PPU_class()
        self.PPU = cPPU(self.memory, self.ROM)
        print(self.PPU)
        Log_SYS('init PPU')
        self.PPU.pPPUinit(self.PPU_Running,self.PPU_render,self.PPU_debug)

    
    def StartingUp(self):
        Log_SYS('RESET')
        self.memory.RAM[::] = 0
        self.memory.VRAM[:] = 0
        self.memory.SpriteRAM[:] = 0
        
        Log_SYS('init APU')
        self.APU = APU(self.memory)
        
        init6502()
        #PPU = __import__('ppu',fromlist = ['PPU'])
        
        #self.FrameBuffer = self.PPU.FrameBuffer
        
        

        try:
            
            self.import_MAPPER_class()
            
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
        self.ScreenShow()

        
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

                
            
            #if self.CPU.isMapperWrite:
            #    self.MapperWrite(self.CPU.MapperWriteAddress, self.CPU.MapperWriteData)
           
            
            

        
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
        
        #while self.CPU.FrameFlag & self.CPU.FrameRender:
        #    self.blitFrame()
        #    print time.time()-start
        #    start = time.time()
        #print print_now(),'Waiting_compiling  compiled...'
        
    
    
    
            
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
            if self.CPU.Frames == nowFrames:break
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
        
    #@deco
    def MaskVROM(self, page, mask):
        return page & (mask - 1)


    def Select8KVROM(self, val1):
        #val1 = self.MaskVROM(val1, NES.VROM_8K_SIZE)
        #self.cpu6502.PPU.VRAM[0:0x2000] = MMC.Select8KVROM(self, val1, self.ROM.VROM)
        self.PPU.VRAM[0:0x2000] = self.nesROM.VROM[val1 * 0x2000 : val1 * 0x2000 + 0x2000]
        #BankSwitch 0, val1 * 8, 8

    def Select4KVROM(self, val1, bank):
        val1 = self.MaskVROM(val1, self.nesROM.ChrCount * 2)
        self.PPU.VRAM[bank * 4 * 0x400: (bank + 1) * 4 * 0x400] = self.nesROM.VROM[val1 * 4 * 0x400 : val1 * 4 * 0x400 + 4 * 0x400]
        #BankSwitch bank * 4, val1 * 4, 4

    def Select2KVROM(self, val1, bank):
        val1 = self.MaskVROM(val1, self.nesROM.ChrCount * 4)
        self.PPU.VRAM[bank * 2 * 0x400: (bank + 1) * 2 * 0x400] = self.nesROM.VROM[val1 * 2 * 0x400 : val1 * 2 * 0x400 + 2 * 0x400]
        #BankSwitch bank * 2, val1 * 2, 2


    def Select1KVROM(self, val1, bank):
        val1 = self.MaskVROM(val1, self.nesROM.ChrCount * 8)
        if NES.Mapper == 4:
            MemCopy(self.PPU.VRAM, (MMC.MMC3_ChrAddr ^ (bank * 0x400)), self.nesROM.VROM, (val1 * 0x400), 0x400)
            
        elif NES.Mapper == 23:
            pass
            #MemCopy VRAM(bank * &H400&), VROM(val1 * &H400&), &H400&
        else:
            pass
            self.PPU.VRAM[bank * 0x400: (bank + 1) * 0x400] = self.nesROM.VROM[val1 * 0x400 : val1 * 0x400 + 0x400]


    #'only switches banks when needed
    #'******只有需要时才切换******
    def SetupBanks(self):

        self.reg8 = MaskBankAddress(self.reg8,self.nesROM.PrgCount)
        self.regA = MaskBankAddress(self.regA,self.nesROM.PrgCount)
        self.regC = MaskBankAddress(self.regC,self.nesROM.PrgCount)
        self.regE = MaskBankAddress(self.regE,self.nesROM.PrgCount)
        
        '''
        self.cpu6502.bank8 = np.array(self.PRGROM[self.reg8 * 0x2000: self.reg8 * 0x2000 + 0x2000], np.uint8)
        self.cpu6502.bankA = np.array(self.PRGROM[self.regA * 0x2000: self.regA * 0x2000 + 0x2000], np.uint8)
        self.cpu6502.bankC = np.array(self.PRGROM[self.regC * 0x2000: self.regC * 0x2000 + 0x2000], np.uint8)
        self.cpu6502.bankE = np.array(self.PRGROM[self.regE * 0x2000: self.regE * 0x2000 + 0x2000], np.uint8)
        '''

        MemCopy(self.RAM[4], 0, self.nesROM.PROM, self.reg8 * 0x2000, 0x2000)
        MemCopy(self.RAM[5], 0, self.nesROM.PROM, self.regA * 0x2000, 0x2000)
        MemCopy(self.RAM[6], 0, self.nesROM.PROM, self.regC * 0x2000, 0x2000)
        MemCopy(self.RAM[7], 0, self.nesROM.PROM, self.regE * 0x2000, 0x2000)
        #print len(self.CPU.bankE)

    
    
    #@deco
    def MaskBankAddress(self,bank):
        if bank >= self.nesROM.PrgCount * 2 :
            i = 0xFF
            while (bank & i) >= self.nesROM.PrgCount * 2:
                i = i // 2
            
            MaskBankAddress = (bank & i)
        else:
            MaskBankAddress = bank
        return MaskBankAddress

    def SetPROM_8K_Bank(self, page, bank ):
        pass
	#'''bank %= NES.PROM_8K_SIZE;
	#CPU_MEM_BANK[page] = PROM+0x2000*bank;
	#CPU_MEM_TYPE[page] = BANKTYPE_ROM;
	#CPU_MEM_PAGE[page] = bank;'''


    def MMC3_Sync(self):
        if MMC.swap:
            self.reg8 = 0xFE
            self.regA = MMC.PrgSwitch2
            self.regC = MMC.PrgSwitch1
            self.regE = 0xFF
        else:
            self.reg8 = MMC.PrgSwitch1
            self.regA = MMC.PrgSwitch2
            self.regC = 0xFE
            self.regE = 0xFF
        
        self.SetupBanks()

    def MMC3Write(self,value, Address):
        if Address == 0x8000:
                MMC.MMC3_Command = value & 0x7
                MMC.MMC3_ChrAddr == 0x1000 if value & 0x80 else  0
                MMC.swap = 1 if value & 0x40 else 0
                
        elif Address == 0x8001:
            if MMC.MMC3_Command == 0:
                self.Select1KVROM( value, 0)
                self.Select1KVROM( value + 1, 1)
            elif MMC.MMC3_Command == 1:
                self.Select1KVROM( value, 2)
                self.Select1KVROM( value + 1, 3)
            elif MMC.MMC3_Command == 2:
                self.Select1KVROM( value, 4)
            elif MMC.MMC3_Command == 3:
                self.Select1KVROM( value, 5)
            elif MMC.MMC3_Command == 4:
                self.Select1KVROM( value, 6)
            elif MMC.MMC3_Command == 5:
                self.Select1KVROM( value, 7)
            elif MMC.MMC3_Command == 6:
                MMC.PrgSwitch1 = value
                self.MMC3_Sync()
            elif MMC.MMC3_Command == 7:
                MMC.PrgSwitch2 = value
                self.MMC3_Sync()
                
        elif Address == 0xA000:
            NES.Mirroring = 0 if value & 1 else 1
            NES.MirrorXor = ((NES.Mirroring + 1) % 3) * 0x400

        elif Address == 0xA001:
            NES.UsesSRAM = True if value else False
        elif Address == 0xC000:
            MMC.MMC3_IrqVal = value
        elif Address == 0xC001:
            MMC.MMC3_TmpVal = value
        elif Address == 0xE000:
            MMC.irq_enable = False
            MMC.MMC3_IrqVal = MMC.MMC3_TmpVal
        elif Address == 0xE001:
            MMC.irq_enable = True


    def map1_write(self, Address  , value ):

        bank_select = 0 #int16

        if (value & 0x80) :
            self.data[0] = self.data[0] | 0xC
            self.accumulator = self.data[(Address // 0x2000) & 3]
            self.sequence = 5
        else:
            if value & 1 : self.accumulator = self.accumulator | (2 ** sequence)
            self.sequence = self.sequence + 1
        

        if (self.sequence == 5) :
            self.data[(Address // 0x2000) & 3] = self.accumulator
            self.sequence = 0
            self.accumulator = 0

            #'MirrorXor = pow2((data(0) And &H3) + 10)
            
            if (self.nesROM.PrgCount == 0x20) :# '/* 512k cart */'
                bank_select = (self.data[1] & 0x10) * 2
            else:# '/* other carts */'
                bank_select = 0
           
            
            if self.data[0] & 2 :# 'enable panning
                NES.Mirroring = (self.data[0] & 1) ^ 1
            else:# 'disable panning
                NES.Mirroring = 2
            
            #DoMirror
            #Select Case Mirroring
            #Case 0
            #    MirrorXor = &H400
            #Case 1
            #    MirrorXor = &H800
            #Case 2
            #    MirrorXor = 0
            #End Select
            
            if (self.data[0] & 8) == 0 :# 'base boot select $8000?
                self.reg8 = 4 * (self.data[3]& 15) + bank_select
                self.regA = 4 * (self.data[3]& 15) + bank_select + 1
                self.regC = 4 * (self.data[3]& 15) + bank_select + 2
                self.regE = 4 * (self.data[3]& 15) + bank_select + 3
                self.SetupBanks()
            elif (self.data[0]& 4) :# '16k banks
                self.reg8 = ((self.data[3]& 15) * 2) + bank_select
                self.regA = ((self.data[3]& 15) * 2) + bank_select + 1
                self.regC = 0xFE
                self.regE = 0xFF
                self.SetupBanks()
            else: #'32k banks
                self.reg8 = 0
                self.regA = 1
                self.regC = ((self.data[3] & 15) * 2) + bank_select
                self.regE = ((self.data[3] & 15) * 2) + bank_select + 1
                self.SetupBanks()
            
            
            if (self.data[0]& 0x10) :# '4k
                self.Select4KVROM(self.data[1], 0)
                self.Select4KVROM(self.data[2], 1)
            else:# '8k
                self.Select8KVROM(self.data[1] // 2)
            


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

        










        
