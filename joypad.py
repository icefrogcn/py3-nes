# -*- coding: UTF-8 -*-

import time
import numpy as np
import numba as nb
from numba import jit,njit,objmode
from numba.experimental import jitclass
from numba import uint8,uint16,int32,uint32,float32
from numba.typed import Dict
from numba import types

#JOYPAD
#from nes import NES

spec = [('Joypad',uint8[:]),
        ('padbit',uint16[:]),
        ('pad1bit',uint32),
        ('pad2bit',uint32),
        ('pad3bit',uint32),
        ('pad4bit',uint32),
        ('padcnt',uint8[:,:]),
        ('bStrobe',uint8),
        ('Joypad_Count',uint8)
        ]

@jitclass(spec)
class JOYPAD(object):
    ren15fps:uint8[:]
    padbitsync:uint16[:]
    
    def __init__(self):
        #self.consloe = consloe
        self.Joypad = np.full(0x8,0x40,np.uint8)
        self.padbit = np.zeros(0x4, np.uint16)
        self.padbitsync = np.zeros(0x4, np.uint16)
        #self.Joypad = [0x00] * 0x8
        self.pad1bit = 0
        self.pad2bit = 0
        self.pad3bit = 0
        self.pad4bit = 0
        self.padcnt = np.zeros((0x4,2), np.uint8)

        self.ren15fps = np.array([1,1,0,0], np.uint8)
        
        self.bStrobe = 0
        self.Joypad_Count = 0

    @property
    def btn_A(self):
        return np.uint8(0x1)
    @property
    def btn_B(self):
        return np.uint8(0x2)#1<< 1
    @property
    def btn_SELECT(self):
        return np.uint8(0x4)#1<< 2
    @property
    def btn_START(self):
        return np.uint8(0x8)#1<< 3
    @property
    def btn_UP(self):
        return np.uint8(0x10)#1<< 4
    @property
    def btn_DOWN(self):
        return np.uint8(0x20)#1<< 5
    @property
    def btn_LEFT(self):
        return np.uint8(0x40)#1<< 6
    @property
    def btn_RIGHT(self):
        return np.uint8(0x80)#1<< 7
    @property
    def btn_AAA(self):
        return np.uint16(0x100)#1<< 8
    @property
    def btn_BBB(self):
        return np.uint16(0x200)#1<< 9
    @property
    def btn_RELEASE(self):
        return 0x40

    
    def AAA_press(self,pressed):

        if pressed:
            if self.padcnt[0,0] < 4:
                if self.ren15fps[self.padcnt[0,0]]:
                    self.pad1bit |= self.btn_A
                self.padcnt[0,0] += 1
            else:
                self.padcnt[0,0] = 0
        else:
            self.padcnt[0,0] = 0
        
    def BBB_press(self,pressed):
        if pressed:
            if self.padcnt[0,1] < 4:
                if self.ren15fps[self.padcnt[0,1]]:
                    self.pad1bit |= self.btn_B
                self.padcnt[0,1] += 1
            else:
                self.padcnt[0,1] = 0
        else:
            self.padcnt[0,1] = 0
        
    def A_press(self,pressed):
        if pressed:self.pad1bit |= self.btn_A
    def B_press(self,pressed):
        if pressed:self.pad1bit |= self.btn_B
    def SELECT_press(self,pressed):
        if pressed:self.pad1bit |= self.btn_SELECT
    def START_press(self,pressed):
        if pressed:self.pad1bit |= self.btn_START
    def UP_press(self,pressed):
        if pressed:self.pad1bit |= self.btn_UP
    def DOWN_press(self,pressed):
        if pressed:self.pad1bit |= self.btn_DOWN
    def LEFT_press(self,pressed):
        if pressed:self.pad1bit |= self.btn_LEFT
    def RIGHT_press(self,pressed):
        if pressed:self.pad1bit |= self.btn_RIGHT

    def Joypad_Count_ZERO(self,addr):
        self.Joypad_Count = 0

    def Strobe(self):
        self.pad1bit = self.padbit[0]
        self.pad2bit = self.padbit[1]
        self.pad3bit = self.padbit[2]
        self.pad4bit = self.padbit[3]
        
    def SyncSub(self):
        self.padbit[0] = self.chk_Rapid(self.padbitsync[0])
        
    def chk_Rapid(self, padbit):
        if padbit & self.btn_AAA:
            
            if self.padcnt[0,0] >= 4:
                self.padcnt[0,0] = 0
                
            if self.ren15fps[self.padcnt[0,0]]:
                padbit |= self.btn_A
            else:
                padbit &= ~self.btn_A

            self.padcnt[0,0] += 1
            
                
        else:
            self.padcnt[0,0] = 0

        if padbit & self.btn_BBB:
            if self.padcnt[0,1] < 4:
                if self.ren15fps[self.padcnt[0,1]]:
                    padbit |= self.btn_B
                else:
                    padbit &= ~self.btn_B
                self.padcnt[0,1] += 1
            else:
                self.padcnt[0,1] = 0
        else:
            self.padcnt[0,1] = 0
        return padbit & 0xFF
    
    def Write(self,addr,data):
        if addr == 0x16:
            if data & 1 :
                self.bStrobe = 1
            elif self.bStrobe:
                self.bStrobe = 0
                self.Strobe()
            
        
    def Read(self,addr):
        #print self.Joypad_Count
        data = 0x00
        if addr == 0x4016:
            data = self.pad1bit & 0x1
            self.pad1bit >>= 1
            data |= (self.pad3bit & 0x1) << 1
            self.pad3bit >>= 1
            
        elif addr == 0x4017:
            data = self.pad2bit & 0x1
            self.pad2bit >>= 1

        return data

    def reset(self):
        self.pad1bit = self.pad2bit = 0

JOYPAD_type = nb.deferred_type()
JOYPAD_type.define(JOYPAD.class_type.instance_type)



import keyboard
#Player1   B   A  SE  ST  UP  DN  LF  RT  BBB AAA
P1_PAD = ['k','j','v','b','w','s','a','d','i','u']

def JOYPAD_PRESS(PAD_SET):
    padbit = 0
    for i,key in enumerate(PAD_SET):
        if keyboard.is_pressed(key):padbit |= 1 << i
    return padbit


def JOYPAD_CHK(JOYPAD):
    JOYPAD.padbitsync[0] = JOYPAD_PRESS(P1_PAD)
    JOYPAD.SyncSub()
    #print  'set pad1bit' , bin(CPU.JOYPAD.pad1bit)


    
if __name__ == '__main__':
    JOYPAD = JOYPAD()











        
