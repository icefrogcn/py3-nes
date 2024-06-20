# -*- coding: UTF-8 -*-
import re

import random

import time
import datetime
import threading

import codecs
#import turtle

#import cv2

from numba  import jit
from numba.experimental import jitclass
from numba import int8,uint8,int16,uint16
import numpy as np
import numba as nb

#import pylab

#自定义类
#from neshardware import * 
#from deco import *
from wrfilemod import *
from vbfun import MemCopy

from nes import NES


def rom_ok(data):
    if ''.join([chr(i) for i in data[:0x4]]) == 'NES\x1a':
        print('ROM OK!')
        return True
    else:
        return False

print('loading ROM CLASS')
'''@jitclass([('info',uint16[:]), \
           ('PROM_SIZE_array',uint8[:]), \
           ('VROM_SIZE_array',uint8[:]), \
           ('PROM_16K_SIZE',uint8), \
           ('VROM_8K_SIZE',uint8), \
           ('PROM',uint8[:]), \
           ('VROM',uint8[:]) \
           ])'''
@jitclass
class ROM(object):
    info : uint16[:]
    PROM_SIZE_array: uint8[:]
    VROM_SIZE_array: uint8[:]
    PROM_16K_SIZE: uint8
    VROM_8K_SIZE: uint8
    PROM: uint8[:]
    VROM: uint8[:]
        
    def __init__(self, PROM = np.zeros(0x40, np.uint8), VROM = np.zeros(0x40, np.uint8)):
        self.info = np.zeros(0x10, np.uint16)
        self.PROM_SIZE_array = np.zeros(0x40, np.uint8)
        self.VROM_SIZE_array = np.zeros(0x40, np.uint8)
        self.PROM_16K_SIZE = 0
        self.VROM_8K_SIZE = 0
        self.PROM = PROM
        self.VROM = VROM
        
    @property
    def Mapper(self):
        return self.info[0]
    def Mapper_W(self,value):
        self.info[0] = value

    @property
    def Trainer(self):
        return self.info[1]
    def Trainer_W(self,value):
        self.info[1] = value

    @property
    def Mirroring(self):
        return self.info[2]
    def Mirroring_W(self,value):
        self.info[2] = value
        self.info[5] = ((value + 1) % 3) * 0x400

    @property
    def FourScreen(self):
        return self.info[3]
    def FourScreen_W(self,value):
        self.info[3] = value

    @property
    def UsesSRAM(self):
        return self.info[4]
    def UsesSRAM_W(self,value):
        self.info[4] = value

    @property
    def MirrorXor(self):
        return self.info[5]
    #def MirrorXor_W(self,value):
    #    self.info[5] = value

    @property
    def PROM_8K_SIZE(self):
        return self.PROM_16K_SIZE << 1
    @property
    def PROM_32K_SIZE(self):
        return self.PROM_16K_SIZE >> 1
    @property
    def VROM_1K_SIZE(self):
        return self.VROM_8K_SIZE << 3
    @property
    def VROM_2K_SIZE(self):
        return self.VROM_8K_SIZE << 2
    @property
    def VROM_4K_SIZE(self):
        return self.VROM_8K_SIZE << 1


#ROM_class_type = nb.deferred_type()
#ROM_class_type.define(ROM.class_type.instance_type)


class nesROM(NES):
    HEADER_SIZE = 16
    ROMCtrl = 0
    ROMCtrl2 = 0
    PrgCount = 0 # As Byte
    PrgCount2 = 0 # As Long
    ChrCount = 0 # As Byte,
    ChrCount2 = 0 # As Long
    data = []
    filename = ''

    VROM = []

    def __init__(self):
        pass


    def LoadROM(self,filename):
        
        self.filename = filename
        self.data = read_file_to_array(filename)
        self.NESHEADER = self.data[:0x20]
        if not rom_ok(self.NESHEADER):
            print ('Invalid Header')
            return False
            

        self.SpecialWrite6000 = False

    
        self.PrgCount = self.GetPROM_SIZE(); self.PrgCount2 = self.PrgCount      #'16kB ROM banks 的数量
        print ("[ " , self.PrgCount , " ] 16kB ROM Bank(s)")
        self.SetPROM()

        self.ChrCount = self.GetVROM_SIZE(); self.ChrCount2 = self.ChrCount      #'8kB VROM banks 的数量
        print ("[ " , self.ChrCount , " ] 8kB CHR Bank(s)")
        self.SetVROM()
    
        self.ROMCtrl = self.data[6]
        print ("[ " , self.ROMCtrl , " ] ROM Control Byte #1")

        self.ROMCtrl2 = self.data[7]
        print ("[ " , self.ROMCtrl2 , " ] ROM Control Byte #2")
    
        '****计算Mapper类型****'
        self.Mapper = (self.ROMCtrl & 0xF0) >> 4
        self.Mapper = self.Mapper + self.ROMCtrl2
        print ("[ " , self.Mapper , " ] Mapper")
        NES.Mapper = self.Mapper

        self.PROM_8K_SIZE  = self.GetPROM_SIZE() * 2
        self.PROM_16K_SIZE = self.GetPROM_SIZE()
        self.PROM_32K_SIZE = self.GetPROM_SIZE() / 2

        self.VROM_1K_SIZE = self.GetVROM_SIZE() * 8
        self.VROM_2K_SIZE = self.GetVROM_SIZE() * 4
        self.VROM_4K_SIZE = self.GetVROM_SIZE() * 2
        self.VROM_8K_SIZE = self.GetVROM_SIZE()

        NES.PROM_8K_SIZE  = self.GetPROM_SIZE() * 2
        NES.PROM_16K_SIZE = self.GetPROM_SIZE()
        NES.PROM_32K_SIZE = self.GetPROM_SIZE() / 2

        NES.VROM_1K_SIZE = self.GetVROM_SIZE() * 8
        NES.VROM_2K_SIZE = self.GetVROM_SIZE() * 4
        NES.VROM_4K_SIZE = self.GetVROM_SIZE() * 2
        NES.VROM_8K_SIZE = self.GetVROM_SIZE()
    
        self.Trainer = self.ROMCtrl & 0x4
        self.Mirroring = self.ROMCtrl & 0x1
        self.FourScreen = self.ROMCtrl & 0x8
        self.UsesSRAM = True if self.ROMCtrl & 0x2 else False

        NES.Trainer = self.ROMCtrl & 0x4
        NES.Mirroring = self.ROMCtrl & 0x1
        NES.FourScreen = self.ROMCtrl & 0x8
        
        NES.UsesSRAM = True if self.ROMCtrl & 0x2 else False
        print ("Mirroring=" , NES.Mirroring , " Trainer=" , NES.Trainer , " FourScreen=" , NES.FourScreen , " SRAM=" , NES.UsesSRAM)
    
        #Dim PrgMark As Long
        self.PrgMark = (self.PrgCount2 * 0x4000) - 1
        #self.PrgMark = (self.PrgCount2 * 0x4000) - 1
        self.MirrorXor = ((NES.Mirroring + 1) % 3) * 0x400

        NES.MirrorXor = ((NES.Mirroring + 1) % 3) * 0x400
        
        if NES.Trainer:
            print ("Error: Trainer not yet supported.") #, VERSION
            return 0

        self.ROM = ROM(self.PROM, self.VROM)
        self.ROM.Mapper_W(self.Mapper)

        self.ROM.Trainer_W(self.Trainer)
        self.ROM.Mirroring_W(self.Mirroring)
        self.ROM.FourScreen_W(self.FourScreen)
        self.ROM.UsesSRAM_W(self.UsesSRAM)

        #self.ROM.MirrorXor_W(self.MirrorXor)


        self.ROM.PROM_16K_SIZE = self.PROM_16K_SIZE
       
        self.ROM.VROM_8K_SIZE = self.VROM_8K_SIZE       

        
        return self.ROM
        
    def GetPROM_SIZE(self):
        return self.data[0x4]

    def GetVROM_SIZE(self):
        return self.data[0x5]

    def SetPROM(self):
        '****读取PRG数据****'
        self.PROM = np.array(self.data[self.HEADER_SIZE: self.PrgCount2 * 0x4000 + self.HEADER_SIZE], np.uint8)

    def SetVROM(self):
        '****读取CHR数据****'
        self.PrgMark = 0x4000 * self.PrgCount2 + self.HEADER_SIZE
        self.VROM = np.zeros(self.ChrCount2 * 0x2000, np.uint8)
        if self.ChrCount2:
            self.VROM = np.array(self.data[self.PrgMark: self.ChrCount2 * 0x2000 + self.PrgMark], np.uint8)
            
            #MemCopy (NES.VROM,0, self.data, self.PrgMark, self.ChrCount2 * 0x2000)
            self.AndIt = self.ChrCount - 1


def calculate_Mapper(NESHEADER):
    return  (NESHEADER[6] & 0xF0) // 16 + NESHEADER[7]

def get_Mapper_by_fn(filename):
    return calculate_Mapper(read_file_to_array(filename))

#@deco
def get_16k_rom_num(NESHEADER):
    return NESHEADER[0x4]
#@deco
def get_8k_vrom_num(NESHEADER):
    return NESHEADER[0x5]

def get_block(block_start,block_num,block_len):
    block=[]
    for i in range(block_num):
        
        block_t = nesROMdata[block_start:(block_start + block_len)]
        
        block.append(block_t)

        block_start += block_len
        
        
    return block,block_start

#@deco
def Tile_(data):
    Tile = []
    for item in data:
        Tile.append('{:0^8}'.format((bin(item))[2:]))
    return Tile

#@deco
def getTile(block_num,offset):
    return VROM[block_num][offset:(offset+0x10)]

def HEX_RGB(value):
    digit = int(filter(lambda x:x in '0123456789ABCDEF',value),16)
    a1 = digit // 0xFFFF
    a2 = (digit - a1) // 0xFF
    a3 = digit % 0xFF
    return (a1, a2, a3)
#print HEX_RGB('#80')


def pal_array(cpal):
    pal_arr = []
    for i in cpal:
        pal_arr.append(HEX_RGB(i))
    return pal_arr

def draw_str(Tiles,i):
        Tile_color = ['white','yellow','red','green']
        #global image
        #print Tiles
        #print i/2,
        digit = list(map(str, range(10))) + list("ABCDEF")
        pos_x = (i * 8) % s_w * ratio
        pos_y = (i // (s_w / 8)) * 8 * ratio
        #print pos_x,pos_y
        for y,Tile in enumerate(Tiles):
            point_y = pos_y + y * ratio
            for x,c in enumerate(Tile):
                point_x = pos_x + x*ratio
                image[point_y, point_x] = pal_array[int(c)]
                #image[point_y, point_x, 0] = digit.index(CPal[int(c)][1]) * 16 + digit.index(CPal[int(c)][2])
                #image[point_y, point_x, 1] = digit.index(CPal[int(c)][3]) * 16 + digit.index(CPal[int(c)][4])
                #image[point_y, point_x, 2] = digit.index(CPal[int(c)][5]) * 16 + digit.index(CPal[int(c)][6])
                


def Tiles_array(Tiles):
    Tiles_arr = []
    for y,Tile in enumerate(Tiles):
        Tile_arr = []
        for x,c in enumerate(Tile):
            Tile_arr.append(BGRpal[int(c)])
        Tiles_arr.append(Tile_arr)
    return np.array(Tiles_arr,np.uint8)



def rndColor():
    return random.randint(64,255),random.randint(64,255),random.randint(64,255)

if __name__ == '__main__':
    #print NES.CPal
    #CPal = [[item >> 16, item >> 8 & 0xFF ,item & 0xFF] for item in NES.CPal]
    #print CPal
    ROM_info = ROM()
    nesROM().LoadROM('roms//1942.nes')
    romt = ROM(np.zeros(0x40, np.uint8),np.zeros(0x40, np.uint8))
    print (dir(romt))










        
