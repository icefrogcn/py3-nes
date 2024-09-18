# -*- coding: UTF-8 -*-
import os,re

import time

import datetime
import threading


import numpy as np

from numba import njit
from numba.experimental import jitclass
from numba.types import Tuple



lookup_l = np.array([[(i & (1 << b))>>b for b in np.arange(7,-1,-1)] for i in np.arange(256)], np.uint8)
lookup_h = np.array([[(i & (1 << b))>>b<<1 for b in np.arange(7,-1,-1)] for i in np.arange(256)], np.uint8)

lookup_PT = np.array([[((i>>8 & 1<<b)>>b<<1) + ((i & 1<<b)>>b) for b in range(0x8)][::-1] for i in range(0x10000)], np.uint8)

lookup_NtAt = np.array([((i>> 4) & 0x38) | ((i >> 2) & 0x7) for i in range(0x3C0)], np.uint8)

#@window.event  #装饰器
def on_draw():#重写on_draw方法
    window.clear() #窗口清除
    background_color = [0, 255, 255]
    background = pyglet.image.ImageData(720, 768, "RGB", bytes(np.zeros((720, 768, 3),np.uint8)))
    background.blit(0,0) #重绘窗口

@njit
def calc_PatternTableTiles(PPU_MEM_BANK):
        PatternTableTiles = np.zeros((len(PPU_MEM_BANK)>> 4, 8, 8),np.uint8)
        for index,Tile in enumerate(PatternTableTiles):
            page = index >> 6
            ptr = (index & 0x3F) << 4
            #print(page,ptr,index)
            for TileY in range(8):
                PatternTableTiles[index,TileY] = lookup_l[PPU_MEM_BANK[ptr + TileY]] \
                                               + lookup_h[PPU_MEM_BANK[ptr + TileY + 8]]
        #cv2.imshow("PatternTable0", paintBuffer(np.concatenate(PatternTableTiles,axis=1)))
        #return np.concatenate(PatternTableTiles,axis=1)
        return PatternTableTiles#(i for i in PatternTableTiles)#np.hstack(Tuple(i for i in PatternTableTiles))

from numpy.ctypeslib import as_ctypes
import ctypes
@njit
def paintBuffer(NTArray):
        [rows, cols] = NTArray.shape
        FrameBuffer = np.zeros((rows, cols, 3),np.uint8)
        for i in range(rows):
            for j in range(cols):
                FrameBuffer[i, j] = BGRpal[NTArray[i, j]]
        return FrameBuffer.ctypes.data
        #return ctypes.cast(FrameBuffer.ctypes.data, ctypes.POINTER(ctypes.c_int8))
@njit
def test():
    return [np.hstack((calc_PatternTableTiles(i))) for i in mmc.PPU_MEM_BANK[:4]]





    
if __name__ == '__main__':
    pass









        
