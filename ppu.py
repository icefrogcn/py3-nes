# -*- coding: UTF-8 -*-

import time
import math
import traceback


import numpy as np
import numba as nb
#from numba import jit,njit
from numba.experimental import jitclass
from numba import uint8,uint16

#自定义类
from deco import *
from jitcompile import jitObject,jitType

from mmu import MMU

from ppu_reg import PPUREG, PPUBIT

from pal import BGRpal

from renderer import lookup_l,lookup_h,lookup_NtAt
     

#@jitclass
class PPU(object):
    reg: PPUREG
    
    loopy_y:uint16
    loopy_shift:uint16
    
    CurrentLine:uint16
    HScroll:uint16
    #vScroll:uint16
    scX:uint16
    scY:uint16

    PatternTableTiles:uint8[:,:,::1]
    Pal:uint8[:,::1]

    ScreenArray:uint8[:,::1]
    ATarray:uint8[:,::1]
    #NT_BANK:ListType(uint8[::1])

    ScreenBuffer:uint8[:,:,::1]
    gletBuffer:uint8[:,:,::1]
    #PalBuffer:uint8[:,:,::1]
    PTBuffer:uint8[:,:,::1]
    NTBuffer:uint8[:,:,::1]
    Running:uint8
    
    tilebased:uint8
    #debug:uint8
    ScanlineSPHit:uint8[:]

    render:uint8
    
    showNT:uint8
    showPT:uint8

    def __init__(self, reg = PPUREG()):
        self.reg = reg

        self.loopy_y = 0
        self.loopy_shift = 0
    
        self.CurrentLine = 0 
        self.HScroll = 0
        #self.vScroll = 0        
        self.scX = 0
        self.scY = 0

        

        self.PatternTableTiles = np.zeros((0x2000 >> 4, 8, 8),np.uint8)
        self.Pal        = BGRpal
        

        self.ScreenArray = np.zeros((240, 256),np.uint8)
        self.ScreenBuffer = np.zeros((240, 256, 3),np.uint8)
        self.gletBuffer = np.zeros((240, 256, 3),np.uint8)
        #self.PalBuffer = np.zeros((0x20, 3),np.uint8)
        self.ATarray = np.zeros((256, 256),np.uint8)
        #self.NT_BANK = List([np.zeros((240, 256),np.uint8) for i in range(4)])

        self.PTBuffer = np.zeros((128, 384, 3),np.uint8)
        self.NTBuffer = np.zeros((720, 768, 3),np.uint8)
        
        #self.BGPAL = [0] * 0x10
        #self.SPRPAL = [0] * 0x10
        
        self.Running = 1
        
        self.render = 1

        self.tilebased = 0
        
        self.ScanlineSPHit = np.zeros(257, np.uint8)

        self.showNT = self.showPT = 0

        
    @property
    def bit(self):
        return 0
    @property
    def MMU(self):
        return self.reg.MMU
    @property
    def VRAM(self):
        return self.reg.VRAM
    @property
    def SpriteRAM(self):
        return self.reg.SpriteRAM
    @property
    def SPRAM(self):
        return self.reg.SpriteRAM
    @property
    def Palettes(self):
        return self.reg.Palettes
    @property
    def NTArray(self):
        return self.MMU.NTArray
    @property
    def NT_BANK(self):
        return self.MMU.NT_BANK


    @property
    def PPU_MEM_BANK(self):
        return self.reg.PPU_MEM_BANK
    @property
    def PPU_MEM_TYPE(self):
        return self.reg.PPU_MEM_TYPE

        
    @property
    def Mirroring(self):
        return 0 #self.ROM.Mirroring

    
    def pPPUinit(self,Running = 1,render = 1,debug = 0):
        self.Running = Running
        self.render = render
        #self.debug = debug
        
    def reset(self):
        self.ScreenArray[:] = 0
        self.NTBuffer[:] = 0
        self.PTBuffer.fill(0)
        self.reg.reset()
        



    @property
    def sp16(self):
        return self.reg.PPUCTRL & self.reg.bit.PPU_SP16_BIT

    @property
    def spH(self):
        return 0x10 if self.sp16 else 0x8

    
    def Read(self,addr):
        return self.reg.read(addr)

        
    def Write(self,address,value):
        self.reg.write(address,value)

    def VBlankStart(self):
        self.reg.reg[2] |= 0x80     #PPU_VBLANK_FLAG
    def VBlankEnd(self):
        self.reg.PPUSTATUS = 0
        #self.reg.reg[2] &= ~0x80
        #self.reg.reg[2] &= ~0x40
        
 
    def CurrentLine_ZERO(self):
        self.CurrentLine = 0
                
    def CurrentLine_increment(self,value):
        self.CurrentLine += value

    @property
    def NTnum(self):
        #0 0yy NN YY YYY XXXXX
        return (self.loopy_v & 0b0000110000000000) >> 10

    @property
    def vScroll(self):
        return self.reg.vScroll
    @property
    def vRow(self):
        return (self.loopy_v & 0b0000001111100000) >> 5 
        #return (self.vScroll + self.CurrentLine - 1) >> 3
    @property
    def vCol(self):
        return self.loopy_v & 0b0000000000011111
        #return self.reg.vScroll
    @property
    def TileY(self):
        return self.loopy_y#(self.loopy_t >> 12) & 0x7
        #return (self.vScroll + self.CurrentLine - 1) & 0x7
    @property
    def TileX(self):
        return self.loopy_x  & 0x7
    @property
    def ATX(self):
        return self.TileX + ((self.vCol & 0x3) << 3)
        

    @property
    def NT_addr(self):
        return self.loopy_v & 0b0000001111111111

    @property
    def VRAM_BANK(self):
        return 8 | self.NTnum#((self.loopy_v & 0b0000110000000000) >> 10) ^ self.NTnum
        #return 8 | (self.NTnum ^ (0x2 if self.vRow > 30 else 0))

    @property
    def AT_addr(self):
        return 0x3C0 | ((self.loopy_v >> 4) & 0x38) | ((self.loopy_v >> 2) & 0x07)
        

    @property
    def RowNT(self):
        ptr = self.NT_addr
        drift = self.vCol
        return np.hstack((self.PPU_MEM_BANK[self.VRAM_BANK][ptr:ptr + 32 - drift],
                          self.PPU_MEM_BANK[self.VRAM_BANK ^ 1][ptr - drift:ptr + 1]))
        

    def GetPT_Tile_data(self,ptr):
        return self.PPU_MEM_BANK[(ptr>>6)][(ptr<<4) & 0x3F0 : ((ptr<<4)&0x3F0)+0x10]


    def NTTile(self,data):
        Tile = np.zeros((8, 8),np.uint8)
        for TileY in range(8):
            Tile[TileY] = lookup_l[data[TileY]] + lookup_h[data[TileY + 8]]
        return Tile

    @property
    def RowNTTiles(self):
        Tiles = np.zeros((8, 264),np.uint8)

        for i,ptr in enumerate(self.RowNT):
            Tiles[0:8, i<<3: (i<<3) + 8] = self.NTTile(self.GetPT_Tile_data(ptr | self.PPU_BGTBL_TILE_OFFSET))
        return Tiles

    def NTline(self,data):
        return np.add(lookup_l[data[self.TileY]],lookup_h[data[self.TileY + 8]])

    @property
    def RowNTline(self):
        line = np.zeros(264,np.uint8)

        for i,ptr in enumerate(self.RowNT):
            line[i<<3: (i<<3) + 8] = self.NTline(self.GetPT_Tile_data(ptr | self.PPU_BGTBL_TILE_OFFSET))
            
        return line[self.TileX:self.TileX+256]

    
    @property
    def RowAT(self):
        ptr = self.AT_addr
        drift = ptr & 7
        if drift:
            pass
        return np.hstack((self.PPU_MEM_BANK[self.VRAM_BANK][ptr:ptr + 8 - drift],
                        self.PPU_MEM_BANK[self.VRAM_BANK ^ 1][ptr - drift:ptr + 1]))
        
    
    def ATTile(self,data):
        Tile = np.zeros((8, 32),np.uint8)
        if self.vRow & 0b10:
            Tile[0:8,16:32] = (data & 0b11000000) >> 4
            Tile[0:8,0 :16] = (data & 0b00110000) >> 2
        else:
            Tile[0:8,16:32] = (data & 0b00001100)
            Tile[0:8,0 :16] = (data & 0b00000011) << 2

        return Tile

    @property        
    def RowATTiles(self):
        Tiles = np.zeros((8, 288),np.uint8)
        for i,data in enumerate(self.RowAT):
            if data:
                Tiles[0:8, i<<5: (i<<5) + 32] = self.ATTile(data)
        return Tiles

    def ATline(self,data):
        line = np.zeros(32,np.uint8)
        if self.vRow & 0b10:
            line[16:32] = (data & 0b11000000) >> 4
            line[0 :16] = (data & 0b00110000) >> 2
        else:
            line[16:32] = (data & 0b00001100)
            line[0 :16] = (data & 0b00000011) << 2

        return line

    @property        
    def RowATline(self):
        line = np.zeros(288,np.uint8)
        for i,data in enumerate(self.RowAT):
            if data:
                line[i<<5: (i<<5) + 32] = self.ATline(data)
        return line[self.ATX:self.ATX+256]
        
    def RenderScanline(self,scanline):
        if scanline == 0:
            pass
            
        elif self.render and scanline < 240:
            self.RenderBG(scanline)
            self.RenderSprites(scanline)
            

    def RenderBG(self,scanline):
        if self.IsBGON:#  and (scanline & 7 == 1 or ):
            self.ScreenArray[scanline]  = self.RowNTline
            self.ScreenArray[scanline] |= self.RowATline
            #self.ScreenArray[scanline]  = self.RowNTTiles[self.TileY][self.TileX:self.TileX+256]
            #self.ScreenArray[scanline] |= self.RowATTiles[self.TileY][self.ATX:self.ATX+256]
            #self.ScreenArray[scanline:scanline + 8 - self.TileY] = self.RowNTTiles[self.TileY:][self.TileX:self.TileX+256]
            #self.ScreenArray[scanline:scanline + 8 - self.TileY] |= self.RowATTiles[self.TileY:][self.ATX:self.ATX+256]
            #LeftClipif
        else:
             self.ScreenArray[scanline] = 0
             
    def RenderSprites(self,scanline):
        self.reg.reg[2] &=  ~0x20 #PPU_SPMAX_FLAG
        if not self.IsSPON:
            return

        spH = self.spH
            
        for sp_inx in range(63,-1,-1):
            spriteOffset =  sp_inx << 2
            sp_Y = self.SPRAM[spriteOffset]
            if sp_Y >= 240: continue
            sp_X = self.SPRAM[spriteOffset + 3]
            if sp_X >= 248: continue
            tileY = scanline - sp_Y
            if not(0 <= tileY < spH):continue
            
            if self.sp16:
                chr_index = ((self.SPRAM[spriteOffset + 1] & 1)<< 8) | ((self.SPRAM[spriteOffset + 1] & 0xFE))
                if self.SPRAM[spriteOffset + 2] & 0x80:     #垂直翻转
                    tileY ^= 7;chr_index ^= 1
                if (tileY & 8):chr_index ^= 1
            else:
                chr_index = self.SPRAM[spriteOffset + 1] | self.PPU_SPTBL_TILE_OFFSET
                if self.SPRAM[spriteOffset + 2] & 0x80:     #垂直翻转
                    tileY ^= 7

            spTile = self.NTTile(self.GetPT_Tile_data(chr_index))
            spLine = spTile[tileY & 7]

            if self.SPRAM[spriteOffset + 2] & 0x40:         #左右翻转
                spLine = spLine[::-1]


            if sp_inx == 0 and (not (self.reg.reg[2] &  0x40)):#PPU_SPHIT_FLAG
                #BGpos = ((sp_X &0xF8) + ((loopy_shift + (sp_X&7))&8))>>3
                #BGsft = 8 - ((loopy_shift + sp_X)&7)
                BGmsk = self.ScreenArray[scanline][sp_X:sp_X + 8]
                
                if(spLine & BGmsk).any():
                    self.reg.reg[2] |= 0x40
            
            hiColor = ((self.SPRAM[spriteOffset + 2] & 0x03) << 2) + 0x10
                
            spLine = np.add(spLine,hiColor)
                    
            BGPriority = self.SPRAM[spriteOffset + 2] & 0x20 #SP_PRIORITY_BIT
            
            if BGPriority:
                for i,data in enumerate(spLine):
                    if self.ScreenArray[scanline][sp_X + i] & 3 == 0:
                        self.ScreenArray[scanline][sp_X + i] = data
            else:
                for i,data in enumerate(spLine):
                    if data & 3 > 0:
                        self.ScreenArray[scanline][sp_X + i] = data

    def DummyScanline(self,scanline):
        self.reg.reg[2] &= ~0x20 #PPU_SPMAX_FLAG
           
    @property
    def loopy_v(self):
        return self.reg.loopy_v
    @loopy_v.setter
    def loopy_v(self,value):
        self.reg.loopy_v = value
    @property
    def loopy_x(self):
        return self.reg.loopy_x
    @loopy_x.setter
    def loopy_x(self,value):
        self.reg.loopy_x = value
    @property
    def loopy_t(self):
        return self.reg.loopy_t
    @loopy_t.setter
    def loopy_t(self,value):
        self.reg.loopy_t = value
                
    def FrameStart(self):
        if self.isDispON:
            self.loopy_v = self.loopy_t
            self.loopy_shift = self.loopy_x
            self.loopy_y = (self.loopy_v & 0x7000)>>12
    
    def ScanlineStart(self):
        if self.isDispON :
            self.loopy_v = (self.loopy_v & 0xFBE0)|(self.loopy_t & 0x041F)  
            self.loopy_shift = self.loopy_x
            self.loopy_y = (self.loopy_v&0x7000)>>12
            #nes->mapper->PPU_Latch( 0x2000 + (loopy_v & 0x0FFF) );
                
    def ScanlineNext(self):
        if self.isDispON:
            if( (self.loopy_v & 0x7000) == 0x7000 ):            #FineY = 7
                self.loopy_v &= 0x8FFF                          #FineY = 0
                if( (self.loopy_v & 0x03E0) == 0x03A0 ):        #Row = 29 
                    self.loopy_v ^= 0x0800                      #nt chg
                    self.loopy_v &= 0xFC1F
                else:
                    if( (self.loopy_v & 0x03E0) == 0x03E0 ):    #Row = 31
                        self.loopy_v &= 0xFC1F
                    else:
                        self.loopy_v += 0x0020                  #Row < 30 next Row
            else :
                self.loopy_v += 0x1000                          #FineY += 1

            self.loopy_y = (self.loopy_v&0x7000)>>12
                    
    

    @property
    def isDispON(self):
        return self.reg.PPUMASK & (self.reg.bit.PPU_SPDISP_BIT|self.reg.bit.PPU_BGDISP_BIT)
    @property
    def IsBGON(self):
        return self.reg.PPUMASK & self.reg.bit.PPU_BGDISP_BIT
    @property
    def IsSPON(self):
        return self.reg.PPUMASK & self.reg.bit.PPU_SPDISP_BIT
        
    def RenderVRAM(self):
        #return
        if self.reg.PPUMASK & (self.reg.bit.PPU_SPDISP_BIT|self.reg.bit.PPU_BGDISP_BIT) == 0 :return
        
        
        NTnum = self.reg.PPU_NAMETBL


        self.scY = self.reg.vScroll + ((NTnum>>1) * 240)
        self.scX = self.reg.HScroll + ((NTnum & 1) * 256)

        self.CalcPatternTableTiles()

        self.RenderNT()

        self.RenderSpritesNT()

        
    def paintBuffer(self):
        #[rows, cols] = self.NTArray.shape
        #for i in range(rows):
        #    for j in range(cols):
        #        self.NTBuffer[i, j] = self.Pal[self.Palettes[self.NTArray[i, j]]]

        for index,item in np.ndenumerate(self.NTArray):
            self.NTBuffer[index] = self.Pal[self.Palettes[item]]

    def blitFrame(self):
        self.paintBuffer()

    def RenderSpritesNT(self):
        if self.IsSPON:
            self.RenderSpriteArray(self.NTArray[self.scY:self.scY + 240, self.scX:self.scX + 256], self.SpriteRAM)



    #@njit
    def CalcPatternTableTiles(self):
        #for TileIndex in range(len(self.PatternTableTiles)):
        for TileIndex in range(len(self.PatternTableTiles)):
            page = TileIndex >> 6
            ptr = (TileIndex & 0x3F) << 4
            for TileY in range(8):
                self.PatternTableTiles[TileIndex,TileY] = lookup_l[self.PPU_MEM_BANK[page][ptr + TileY]] \
                                                        + lookup_h[self.PPU_MEM_BANK[page][ptr + TileY + 8]]


    @property
    def PPU_BGTBL_BANK(self):
        return self.reg.PPU_BGTBL_BIT >> 2
    @property
    def PPU_BGTBL_OFFSET(self):
        return self.reg.PPU_BGTBL_BIT << 8
    @property
    def PPU_BGTBL_TILE_OFFSET(self):
        return self.reg.PPU_BGTBL_BIT << 4
    @property    
    def PPU_SPTBL_BANK(self):
        return self.reg.PPU_SPTBL_BIT >> 1
    @property    
    def PPU_SPTBL_OFFSET(self):
        return self.reg.PPU_SPTBL_BIT << 9
    @property
    def PPU_SPTBL_TILE_OFFSET(self):
        return self.reg.PPU_SPTBL_BIT  << 5 
    

    def RenderNT(self):
        if self.IsBGON:
            self.calc_NameTable()
            self.CalcAttributeTable()
            self.MirrorNT()
            
    def GetNameTable(self,nt):
        return self.PPU_MEM_BANK[nt|8][0: 0x3C0]
    @property
    def NameTables(self):
        return self.PPU_MEM_BANK[8:12]#[0: 0x3C0]
    
    def calc_NameTable(self):
        for nt,NameTable in enumerate(self.NameTables):
            #NameTable = self.GetNameTable(nt)
            
            for index, ptr in enumerate(NameTable[0:0x3C0]):
                x = ((index & 31) << 3)  + (256 * (nt & 1))
                y = (index >> 5 << 3) + (240 * ((nt & 2) >> 1))
                self.NTArray[y:y + 8, x : x + 8] = self.PatternTableTiles[ptr + self.PPU_BGTBL_TILE_OFFSET]

    def GetAttributeTable(self,nt):
        return self.PPU_MEM_BANK[nt|8][0x3C0: 0x3C0 + 0x40]
    @property
    def AttributeTables(self):
        return self.NameTables#[0x3C0: 0x3C0 + 0x40]

    def CalcAttributeTable(self):
        for nt,NameTable in enumerate(self.NameTables):
            for index, value in enumerate(NameTable[0x3C0: 0x3C0 + 0x40]):
                col = index >> 3; row = index & 7
                if value == 0:
                    #self.ATarray[(col << 5) :(col << 5) + 32 ,  (row << 5)  : (row  << 5) + 32] = 0
                    continue
                self.ATarray[(col << 5)        :(col << 5) + 16 ,  (row << 5)      : (row  << 5) + 16] = (value & 0b11) << 2
                self.ATarray[(col << 5) + 16   :(col << 5) + 32 ,  (row << 5)      : (row  << 5) + 16] = (value & 0b110000) >> 2
                self.ATarray[(col << 5)        :(col << 5) + 16 ,  (row << 5) + 16 : (row  << 5) + 32] = (value & 0b1100)
                self.ATarray[(col << 5) + 16   :(col << 5) + 32 ,  (row << 5) + 16 : (row  << 5) + 32] = (value & 0b11000000) >> 4
            x = 256 * (nt & 1)
            y = 240 * ((nt & 2) >> 1)
            self.NTArray[y:y+240,x:x+256] |= self.ATarray[0:240,0:256]
            self.ATarray[::] = 0
            
            

    def MirrorNT(self):
            self.NTArray[0:240,512:768] = self.NTArray[0:240,0:256]     #0
            self.NTArray[480:720,0:256] = self.NTArray[0:240,0:256]     #0

            self.NTArray[480:720,256:512] = self.NTArray[0:240,256:512] #1
            self.NTArray[240:480,512:768] = self.NTArray[240:480,0:256] #2            

        
    def RenderAttributeTables(self,offset):
        AttributeTablesAddress = 0x2000 + (offset * 0x400 + 0x3C0)
        AttributeTablesSize = 0x40

    

    def RenderNameTable(self,AttributeTables, NTBuffer):
        tempFrame = np.zeros((257, 257),np.uint8)
        for i in range(len(AttributeTables)):
            col = i >> 3; row = i & 7
            if AttributeTables[i] == 0:
                continue
            tempFrame[(col << 5)        :(col << 5) + 16 ,  (row << 5)      : (row  << 5) + 16] = (AttributeTables[i] & 0b11) << 2
            tempFrame[(col << 5) + 16   :(col << 5) + 32 ,  (row << 5)      : (row  << 5) + 16] = (AttributeTables[i] & 0b110000) >> 2
            tempFrame[(col << 5)        :(col << 5) + 16 ,  (row << 5) + 16 : (row  << 5) + 32] = (AttributeTables[i] & 0b1100)
            tempFrame[(col << 5) + 16   :(col << 5) + 32 ,  (row << 5) + 16 : (row  << 5) + 32] = (AttributeTables[i] & 0b11000000) >> 4

        
        NTBuffer |= tempFrame[0:240,0:256]

        [rows, cols] = NTBuffer.shape
        for i in range(rows):
            for j in range(cols):
                if NTBuffer[i,j] & 3 == 0: 
                    NTBuffer[i,j] == 0




    def RenderSpriteArray(self, BGbuffer, SPRAM):
        SpriteArr = np.zeros((16, 8),np.uint8) if self.sp16 else np.zeros((8, 8),np.uint8)
        
        for spriteIndex in range(63,-1,-1):
            spriteOffset =  spriteIndex * 4
            if SPRAM[spriteOffset] >= 240: continue
            
            spriteY = SPRAM[spriteOffset]# + self.scY
            spriteX = SPRAM[spriteOffset + 3]# + self.scX
            

            
            if self.sp16:
                
                chr_index = ((SPRAM[spriteOffset + 1] & 1)<< 8) | ((SPRAM[spriteOffset + 1] & 0xFE))
                
                chr_l = self.NTTile(self.GetPT_Tile_data(chr_index))
                chr_h = self.NTTile(self.GetPT_Tile_data(chr_index + 1))
                SpriteArr = np.row_stack((chr_l,chr_h))
                if SPRAM[spriteOffset + 2] & 0x40:
                    SpriteArr = SpriteArr[:,::-1]

                if SPRAM[spriteOffset + 2] & 0x80:
                    #SpriteArr = np.row_stack((chr_l,chr_h))
                    SpriteArr = SpriteArr[::-1]

                    
                
            else:
                chr_index = SPRAM[spriteOffset + 1] | self.PPU_SPTBL_TILE_OFFSET
                SpriteArr = self.NTTile(self.GetPT_Tile_data(chr_index))
                if SPRAM[spriteOffset + 2] & 0x40:SpriteArr = SpriteArr[:,::-1]
                if SPRAM[spriteOffset + 2] & 0x80:SpriteArr = SpriteArr[::-1]
            
            hiColor = ((SPRAM[spriteOffset + 2] & 0x03) << 2) + 0x10

            [rows, cols] = SpriteArr.shape
            for i in range(rows):
                for j in range(cols):
                    SpriteArr[i,j] += hiColor
                    
            spriteW = 8 
            spriteH = SpriteArr.shape[0] 
            
            if BGbuffer.shape[0] - spriteY > spriteH and BGbuffer.shape[1] - spriteX > spriteW :
                BGPriority = SPRAM[spriteOffset + 2] & 0x20 #SP_PRIORITY_BIT

                if BGPriority:
                    for i in range(spriteW):
                        for j in range(spriteH):
                            if BGbuffer[spriteY + j, spriteX + i] & 3 == 0:
                                BGbuffer[spriteY + j, spriteX + i] = SpriteArr[j,i]
                else:
                    for i in range(spriteW):
                         for j in range(spriteH):
                            if SpriteArr[j,i] & 3 > 0:
                                BGbuffer[spriteY + j, spriteX + i] = SpriteArr[j,i]


    def paintVRAM(self,isDraw = 1):
        if isDraw and self.showNT:
            self.RenderVRAM()
            #for i in range(720):
            #    for j in range(768):
            #        self.NTBuffer[i, j] = self.Pal[self.Palettes[self.NTArray[i, j]]]
            for index,item in np.ndenumerate(self.NTArray):
                self.NTBuffer[index] = self.Pal[self.Palettes[item]]
                
            self.NTBuffer[240]  = np.array([0,255,0],np.uint8)
            self.NTBuffer[480]  = np.array([0,255,0],np.uint8)
            self.NTBuffer[:,256]  = np.array([0,255,0],np.uint8)
            self.NTBuffer[:,512]  = np.array([0,255,0],np.uint8)

 
    def paintScreen(self,isDraw = 1):
        if isDraw:
            ScreenArray1 = np.flipud(self.ScreenArray)   #pyglet (0,0) downleft
            #for i in range(240):
            #    for j in range(256):
            #        self.ScreenBuffer[i, j] = self.Pal[self.Palettes[ScreenArray1[i, j]]]
            
            for index,item in np.ndenumerate(ScreenArray1):
                self.ScreenBuffer[index] = self.Pal[self.Palettes[item]]
            
            'numba Unsupport'
            #for p in self.Palettes:
                #self.ScreenBuffer[self.ScreenArray == p] = self.Pal[p]
            #for i in range(240):
            #    self.ScreenBuffer[i] = np.array([self.Pal(self.Palettes[p]) for p in self.ScreenArray[i]],np.uint8)
    
    def paintPT(self,isDraw = 1):
        if isDraw and self.showPT:
            #TileBuff = np.zeros((8,8,3), np.uint8)
            for i,Tile in enumerate(self.PatternTableTiles):
                p = i 
                px = ((i & 0xF) << 3) + ((i & 0x100)>>1)
                py = (i & 0xF0) >> 1
                for tx in range(8):
                    for ty in range(8):
                        self.PTBuffer[ty + py, tx + px] = self.Pal[self.Palettes[Tile[ty, tx]]]
                #self.PTBuffer[py:py+8,px:px+8] = TileBuff

    def blitPal(self,isDraw = 1):
        if isDraw:
            for i in enumerate(self.NES.PPU.Palettes):
                #self.PalBuffer[i] =  self.NES.PPU.Pal[i]
                pass


'''
ppu_spec = [('CurrentLine',uint16),
            ('HScroll',uint16),
            ('vScroll',uint16),
            ('scX',uint16),
            ('scY',uint16), \
           #('reg',PPU_Reg_type),
           #('MMU',PPU_Memory_type),
           #('ROM',ROM_class_type),
           #('lookup_l',uint8[:,:]),
           #('lookup_h',uint8[:,:]),
           ('PatternTableTiles',uint8[:,:,::1]),
           ('Pal',uint8[:,:]), 
           ('ScreenArray',uint8[:,:]),
           ('NTArray',uint8[:,:]),
           ('FrameNT0',uint8[:,:]),
           ('FrameNT1',uint8[:,:]),
           ('FrameNT2',uint8[:,:]),
           ('FrameNT3',uint8[:,:]),
           ('NTBuffer',uint8[:,:,:]),
           ('Running',uint8),
           ('render',uint8),
           ('tilebased',uint8),
           ('debug',uint8),
           ('ScanlineSPHit',uint8[:])
    ]
'''

def jit_PPU_class(jit = 1):
    return jitObject(PPU, [], jit = jit)

def load_PPU(MMU = MMU(), jit = 1):
    ppu_class  = jit_PPU_class(jit = jit)
    ppu_type = jitType(ppu_class)
    ppu = ppu_class(PPUREG(MMU))
    return ppu, ppu_type
    
                    
if __name__ == '__main__':
    pass

    #print(PPU())
    ppu, ppu_type = load_PPU()


    
    
    
    








        
