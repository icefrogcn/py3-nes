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
from jitcompile import jitObject

from memory import Memory
from ppu_reg import PPUREG, PPUBIT
from ppu_memory import PPU_Memory
#from ppu_memory import PPU_memory_type
from rom import ROM#,ROM_class_type

from pal import BGRpal

#PPU
PPU_Memory_type = nb.deferred_type()
PPU_Memory_type.define(PPU_Memory.class_type.instance_type)
PPU_Reg_type = nb.deferred_type()
PPU_Reg_type.define(PPUREG.class_type.instance_type)
ROM_class_type = nb.deferred_type()
ROM_class_type.define(ROM.class_type.instance_type)
        
lookup_l = np.array([[(i & (1 << b))>>b for b in np.arange(7,-1,-1)] for i in np.arange(256)], np.uint8)
lookup_h = np.array([[(i & (1 << b))>>b<<1 for b in np.arange(7,-1,-1)] for i in np.arange(256)], np.uint8)
     

ppu_spec = [('CurrentLine',uint16),
            ('HScroll',uint16),
            ('vScroll',uint16),
            ('scX',uint16),
            ('scY',uint16), \
           ('reg',PPU_Reg_type),
           ('memory',PPU_Memory_type),
           ('ROM',ROM_class_type),
           #('lookup_l',uint8[:,:]),
           #('lookup_h',uint8[:,:]),
           ('PatternTableTiles',uint8[:,:,:]),
           ('Pal',uint8[:,:]), 
           ('ScreenArray',uint8[:,:]),
           ('FrameArray',uint8[:,:]),
           ('FrameNT0',uint8[:,:]),
           ('FrameNT1',uint8[:,:]),
           ('FrameNT2',uint8[:,:]),
           ('FrameNT3',uint8[:,:]),
           ('FrameBuffer',uint8[:,:,:]),
           ('Running',uint8),
           ('render',uint8),
           ('tilebased',uint8),
           ('debug',uint8),
           ('ScanlineSPHit',uint8[:])
    ]

#@jitclass
class PPU(object):
    '''
    CurrentLine:uint16
    HScroll:uint16
    vScroll:uint16
    scX:uint16
    scY:uint16
    reg:PPUREG
    memory:PPU_Memory
    ROM:ROM
    PatternTableTiles:uint8[:,:,:]
    Pal:uint8[:,:]
    FrameArray:uint8[:,:]
    FrameNT0:uint8[:,:]
    FrameNT1:uint8[:,:]
    FrameNT2:uint8[:,:]
    FrameNT3:uint8[:,:]
    FrameBuffer:uint8[:,:,:]
    Running:uint8
    render:uint8
    tilebased:uint8
    debug:uint8
    ScanlineSPHit:uint8[:]
'''
    def __init__(self, memory = Memory(), ROM = ROM(), pal = BGRpal(), debug = 0):
        self.CurrentLine = 0 
        self.HScroll = 0
        self.vScroll = 0        
        self.scX = 0
        self.scY = 0

        self.ROM = ROM
        self.memory = PPU_Memory(memory)
        self.reg = PPUREG(self.memory, self.ROM)
        


    
        self.PatternTableTiles = np.zeros((0x2000 >> 4, 8, 8),np.uint8)
        self.Pal        = pal

        self.ScreenArray = np.zeros((240, 256),np.uint8)
        self.FrameArray = np.zeros((720, 768),np.uint8)
        self.FrameNT0 = self.FrameArray[0:240,0:256]
        self.FrameNT1 = self.FrameArray[0:240,256:512]
        self.FrameNT2 = self.FrameArray[240:480,0:256]
        self.FrameNT3 = self.FrameArray[240:480,256:512]
        #self.FrameBuffer = np.zeros((720, 768, 3),np.uint8)
        
        #self.BGPAL = [0] * 0x10
        #self.SPRPAL = [0] * 0x10
        
        self.debug = debug
        
        self.Running = 1
        
        self.render = 1

        self.ScanlineSPHit = np.zeros(257, np.uint8)

        self.tilebased = 0

        
    @property
    def bit(self):
        return 0
    @property
    def VRAM(self):
        return self.memory.VRAM
    @property
    def SpriteRAM(self):
        return self.memory.SpriteRAM
    @property
    def Palettes(self):
        return self.memory.Palettes
    @property
    def PRGRAM(self):
        return self.memory.PRGRAM



        
    @property
    def Mirroring(self):
        return self.ROM.Mirroring
    @property
    def MirrorXor(self):
        return self.ROM.MirrorXor
    
    def pPPUinit(self,Running = 1,render = 1,debug = 0):
        self.Running = Running
        self.render = render
        self.debug = debug
        

        #self.ScrollToggle = 0 #$2005-$2006 Toggle PPU56Toggle

        #self.loopy_v = 0
        #self.loopy_t = 0
        #self.loopy_x = 0
        #self.loopy_y = 0
        #self.loopy_shift = 0

        #self.loopy_v0 = 0
        #self.loopy_t0 = 0
        #self.loopy_x0 = 0
        #self.loopy_y0 = 0
        #self.loopy_shift0 = 0


        #self.MirrorXor = 0
        
        

        #self.width,self.height = 257,241

        #
        
        #self.blankPixel = 0 #np.array([16,16,16] ,dtype=np.uint8)
        
        #self.blankLine = np.array([self.blankPixel] * self.width ,dtype=np.uint8)
        #self.blankLine = [[0,0,16]] * self.height 
        
        #'DF: array to draw each frame to'
        #self.vBuffer = [16]* (256 * 241 - 1) 
        #'256*241 to allow for some overflow     可以允许一些溢出'
        #self.vBuffer = np.random.randint(0,1,size = (self.height,self.width,3),dtype=np.uint8)
        
        #self.vBuffer = np.array([self.blankLine] * self.height ,dtype=np.uint8)
        
        
        
        #self.PatternTable = np.uint8(0)

        #self.Pal = np.array([[item >> 16, item >> 8 & 0xFF ,item & 0xFF] for item in NES.CPal])
    @property
    def sp16(self):
        return 1 if self.reg.PPUCTRL & self.reg.bit.PPU_SP16_BIT else 0

    
    def Read(self,addr):
        return self.reg.read(addr)

        
    def Write(self,address,value):
        self.reg.write(address,value)

    def VBlankStart(self):
        self.reg.reg[2] |= 0x80#PPU_VBLANK_FLAG
    def VBlankEnd(self):
        self.reg.PPUSTATUS_ZERO()

    def CurrentLine_ZERO(self):
        self.CurrentLine = 0
                
    def CurrentLine_increment(self,value):
        self.CurrentLine += value
                
    def RenderScanline(self):
        if self.CurrentLine == 0:
            pass
            '''
            self.FrameStart()
            self.ScanlineNext()
            #mapper->HSync( scanline )
            self.ScanlineStart()

            self.loopy_v0 = self.loopy_v
            self.loopy_t0 = self.loopy_t
            self.loopy_x0 = self.loopy_x
            self.loopy_y0 = self.loopy_y
            self.loopy_shift0 = self.loopy_shift
            
            self.NTnum = self.Control1 & PPU_NAMETBL_BIT
        '''
        elif self.CurrentLine < 240:
            pass
            '''
            self.ScanlineNext()
            #mapper->HSync( scanline )
            self.ScanlineStart()
            '''

        if self.CurrentLine > 239:return
        
        
        #if self.CurrentLine < 8 :
            #self.Status = self.Status & 0x3F

        if self.CurrentLine == 239 :
            #self.Status = self.Status | 0x80#PPU_VBLANK_FLAG
            self.reg.PPUSTATUS_W(self.reg.PPUSTATUS | 0x80) #PPU_VBLANK_FLAG

        if self.CurrentLine > self.SpriteRAM[0] + 8:
            self.reg.PPUSTATUS_W(self.reg.PPUSTATUS | 0x40)#PPU_SPHIT_FLAG

        if self.Running == 0:
            if self.reg.PPUMASK & self.reg.bit.PPU_SPDISP_BIT == 0 :return
            if self.reg.PPUSTATUS & 0x40 :return #PPU_SPHIT_FLAG
            
            return

        self.ScanlineSPHit[self.CurrentLine] =  1 if self.reg.PPUSTATUS & self.reg.bit.PPU_SPHIT_FLAG else 0

        '''self.sp_h = 16 if self.Control1 & PPU_SP16_BIT else 8

'''

    def ScanlineStart(self):
        if( self.reg.PPUMASK & (PPU_BGDISP_BIT|PPU_SPDISP_BIT) ):
            self.loopy_v = (self.loopy_v & 0xFBE0)|(self.loopy_t & 0x041F)
            self.loopy_shift = self.loopy_x
            self.loopy_y = (self.loopy_v&0x7000)>>12
            #nes->mapper->PPU_Latch( 0x2000 + (loopy_v & 0x0FFF) );
                
    def ScanlineNext(self):
        if( self.reg.PPUMASK & (PPU_BGDISP_BIT|PPU_SPDISP_BIT) ):
            if( (self.loopy_v & 0x7000) == 0x7000 ):
                self.loopy_v &= 0x8FFF
                if( (self.loopy_v & 0x03E0) == 0x03A0 ):
                    self.loopy_v ^= 0x0800
                    self.loopy_v &= 0xFC1F
                else:
                    if( (self.loopy_v & 0x03E0) == 0x03E0 ):
                        self.loopy_v &= 0xFC1F
                    else:
                        self.loopy_v += 0x0020
            else :
                self.loopy_v += 0x1000

            self.loopy_y = (self.loopy_v&0x7000)>>12
                
    def FrameStart(self):
        if self.reg.PPUMASK & (PPU_SPDISP_BIT|PPU_BGDISP_BIT):
            self.loopy_v = self.loopy_t
            self.loopy_shift = self.loopy_x
            self.loopy_y = (self.loopy_v & 0x7000)>>12

                    
    

    @property
    def PatternTables(self):
        #if self.Control2 & (PPU_SPDISP_BIT|PPU_BGDISP_BIT) == 0 :return

        #PatternTablesAddress,PatternTablesSize = (0x1000,0x1000) if self.reg.PPUCTRL & self.reg.bit.PPU_SPTBL_BIT else (0,0x1000)
        PatternTablesAddress,PatternTablesSize = (0x1000,0x1000) if self.reg.PPU_SPTBL_BIT else (0,0x1000)
        
        return self.PatternTableArr(self.VRAM[PatternTablesAddress:PatternTablesAddress + 0x1000])

        '''img = np.zeros((8,256,3),np.uint8)
        for y in range(8):
            for index in range(32):
                for x in range(8):
                    img[y][index * 8 + x] = self.Pal[PatternTable[index][y][x]]
                #print img_line[y]

        #print img[0]
        return img#np.array(img,np.uint8)'''
    #@property
    def NameTables_data(self,offset):
        NameTablesAddress = 0x2000 + offset * 0x400
        NameTablesSize = 0x3C0
        
        return self.VRAM[NameTablesAddress: NameTablesAddress + NameTablesSize]
    
        
    def RenderFrame(self):
        #return
        if self.reg.PPUMASK & (self.reg.bit.PPU_SPDISP_BIT|self.reg.bit.PPU_BGDISP_BIT) == 0 :return
        
        self.PatternTableTiles = self.PatternTableArr(self.VRAM[0 : 0x2000])

        #NTnum = (self.loopy_v0 & 0x0FFF) >>10
        #NTnum = self.reg.PPUCTRL & self.reg.bit.PPU_NAMETBL_BIT
        NTnum = self.reg.PPU_NAMETBL_BIT

        #fineYscroll = self.loopy_v >>12
        #coarseYscroll  = (self.loopy_v & 0x03FF) >> 5
        #coarseXscroll = self.loopy_v & 0x1F

        if self.reg.Mirroring:
            #self.scY = (coarseYscroll << 3) + fineYscroll + ((NTnum>>1) * 240) 
            #self.scX = (coarseXscroll << 3)+ self.loopy_x0 #self.HScroll
            self.scY = self.reg.vScroll + ((NTnum>>1) * 240)
            self.scX = self.reg.HScroll + ((NTnum & 1) * 256)
            
        if self.reg.Mirroring == 0:
            #self.scY = (coarseYscroll << 3) + fineYscroll + ((NTnum>>1) * 240) #if self.loopy_v&0x0FFF else self.scY
            self.scY = self.reg.vScroll + ((NTnum>>1) * 240) 
            #if self.loopy_v&0x0FFF else self.scY
        
        self.RenderBG()

        self.RenderSprites()
        
        #self.paintBuffer()

        
    def paintBuffer(self):
        [rows, cols] = self.FrameArray.shape
        for i in range(rows):
            for j in range(cols):
                self.FrameBuffer[i, j] = self.Pal[self.Palettes[self.FrameArray[i, j]]]
        #return FrameBuffer

    def blitFrame(self):
        paintBuffer(self.FrameArray,self.Pal,self.Palettes)

    @property    
    def PPU_SPTBL_OFFSET(self):
        if self.sp16:
            return 0x0
        return 0x1000 if self.reg.PPU_SPTBL_BIT else 0x0
    @property
    def PPU_SPTBL_TILE_OFFSET(self):
        return self.PPU_SPTBL_OFFSET >> 4
    
    def RenderSprites(self):
        
        #PatternTablesAddress,PatternTablesSize = (0x1000,0x1000) if self.reg.PPUCTRL & self.reg.bit.PPU_SPTBL_BIT and self.sp16 else (0 ,0x1000)
        #PatternTablesAddress = self.GET_PPU_SPTBL
        #PatternTablesSize = 0x1000 if self.GET_PPU_SPTBL else 0x2000
        #PatternTable_Array = self.PatternTableArr(self.VRAM[PatternTablesAddress : PatternTablesAddress + PatternTablesSize])
        #PatternTable_Array = self.PatternTableArr(self.VRAM[0 : 0x2000])
        self.RenderSpriteArray(self.FrameArray, self.SpriteRAM)
         

    def RenderAttributeTables(self,offset):
        AttributeTablesAddress = 0x2000 + (offset * 0x400 + 0x3C0)
        AttributeTablesSize = 0x40
        
        return self.VRAM[AttributeTablesAddress: AttributeTablesAddress + AttributeTablesSize]
    

    #@njit
    def PatternTableArr(self, Pattern_Tables):
        PatternTable = np.zeros((len(Pattern_Tables)>>4,8,8),np.uint8)
        bitarr = range(0x7,-1,-1)
        for TileIndex in range(len(PatternTable)):
            for TileY in range(8):
                PatternTable[TileIndex,TileY] = lookup_l[Pattern_Tables[(TileIndex << 4) + TileY]] + lookup_h[Pattern_Tables[(TileIndex << 4) + TileY + 8]]
#                PatternTable[TileIndex,TileY] = np.array([1 if (Pattern_Tables[(TileIndex << 4) + TileY]) & (2**bit) else 0 for bit in bitarr], np.uint8) + \
#                                                np.array([2 if (Pattern_Tables[(TileIndex << 4) + TileY + 8]) & (2**bit) else 0 for bit in bitarr], np.uint8)

        return PatternTable

    @property
    def PPU_BGTBL_OFFSET(self):
        return self.reg.PPU_BGTBL_BIT << 8
    @property
    def PPU_BGTBL_TILE_OFFSET(self):
        return self.reg.PPU_BGTBL_BIT << 4

    def RenderBG(self):
        
        #PatternTablesAddress = self.PPU_BGTBL_OFFSET
        
        #PatternTable_Array = self.PatternTableArr(self.VRAM[PatternTablesAddress : PatternTablesAddress + 0x1000])

        if self.ROM.Mirroring == 1:
            self.RenderNameTableH(0,1)

        elif self.ROM.Mirroring == 0 :
            
            self.RenderNameTableV(0,2)
            
        elif self.ROM.Mirroring == 2:
            self.RenderNameTables(0,1,2,3)
        else:
            self.RenderNameTables(0,1,2,3)

            
    
    def RenderNameTableH(self, nt0, nt1):
        tempBuffer0 = self.NameTableArr(nt0)
        self.RenderNameTable(self.AttributeTables_data(nt0), tempBuffer0)
        
        tempBuffer1 = self.NameTableArr(nt1)
        self.RenderNameTable(self.AttributeTables_data(nt1), tempBuffer1)
        
        self.FrameArray[0:480,0:768] = np.row_stack((np.column_stack((tempBuffer0,tempBuffer1,tempBuffer0)),np.column_stack((tempBuffer0,tempBuffer1,tempBuffer0))))

    
    def RenderNameTableV(self, nt0, nt2):
        tempBuffer0 = self.NameTableArr(nt0)
        self.RenderNameTable(self.AttributeTables_data(nt0), tempBuffer0)
        
        tempBuffer2 = self.NameTableArr(nt2)
        self.RenderNameTable(self.AttributeTables_data(nt2), tempBuffer2)
        
        self.FrameArray[0:720,0:512] =  np.column_stack((np.row_stack((tempBuffer0,tempBuffer2,tempBuffer0)),np.row_stack((tempBuffer0,tempBuffer2,tempBuffer0))))

    def RenderNameTables(self,nt0,nt1,nt2,nt3):
            
        #tempBuffer0 = self.AttributeTableArr(AttributeTables_data(VRAM,nt0), NameTableArr(NameTables_data(VRAM,nt0),PatternTables))
        
        tempBuffer0 = self.NameTableArr(nt0)
        self.RenderNameTable(self.AttributeTables_data(nt0), tempBuffer0)
        #tempBuffer1 = self.AttributeTableArr(AttributeTables_data(VRAM,nt1), NameTableArr(NameTables_data(VRAM,nt1),PatternTables))
        tempBuffer1 = self.NameTableArr(nt1)
        self.RenderNameTable(self.AttributeTables_data(nt1), tempBuffer1)
        #tempBuffer2 = self.AttributeTableArr(AttributeTables_data(VRAM,nt2), NameTableArr(NameTables_data(VRAM,nt2),PatternTables))
        tempBuffer2 = self.NameTableArr(nt2)
        self.RenderNameTable(self.AttributeTables_data(nt2), tempBuffer2)
        #tempBuffer3 = self.AttributeTableArr(AttributeTables_data(VRAM,nt3), NameTableArr(NameTables_data(VRAM,nt3),PatternTables))
        tempBuffer3 = self.NameTableArr(nt3)
        self.RenderNameTable(self.AttributeTables_data(nt3), tempBuffer3)

        self.FrameArray[0:480,0:512] =  np.row_stack((np.column_stack((tempBuffer3,tempBuffer2)),np.column_stack((tempBuffer1,tempBuffer0))))
    
    #@property
    def AttributeTables_data(self,offset):
        AttributeTablesAddress = 0x2000 + (offset * 0x400 + 0x3C0)
        AttributeTablesSize = 0x40
        return self.VRAM[AttributeTablesAddress: AttributeTablesAddress + AttributeTablesSize]

    def RenderSpriteArray(self, BGbuffer, SPRAM):
        SpriteArr = np.zeros((16, 8),np.uint8) if self.sp16 else np.zeros((8, 8),np.uint8)
        
        for spriteIndex in range(63,-1,-1):
            spriteOffset =  spriteIndex * 4
            if SPRAM[spriteOffset] >= 240: continue
            
            spriteY = SPRAM[spriteOffset] + self.scY
            spriteX = SPRAM[spriteOffset + 3] + self.scX
            

            
            #chr_index = SPRAM[spriteOffset + 1]# + self.GET_PPU_SPTBL >> 4
            if self.sp16:
                #chr_index = ((chr_index & 1)<< 7) + (chr_index ^ (chr_index & 1))
                chr_index = ((SPRAM[spriteOffset + 1] & 1)<< 8) + ((SPRAM[spriteOffset + 1] & 0xFE))
            else:
                chr_index = SPRAM[spriteOffset + 1] + self.PPU_SPTBL_TILE_OFFSET
            
            chr_l = self.PatternTableTiles[chr_index]
            chr_h = self.PatternTableTiles[chr_index + 1]
     
                
            if SPRAM[spriteOffset + 2] & 0x40:
                chr_l = chr_l[:,::-1]    
                if self.sp16:
                    chr_h = chr_h[:,::-1]
                    

            if SPRAM[spriteOffset + 2] & 0x80:
                chr_l = chr_l[::-1] 
                if self.sp16:
                    chr_h = chr_h[::-1]
                    chr_l,chr_h = chr_h,chr_l
            
            SpriteArr = np.row_stack((chr_l,chr_h)) if self.sp16 else chr_l

            #SpriteArr = np.add(SpriteArr, ((SPRAM[spriteOffset + 2] & 0x03) << 2) + 0x10)
            hiColor = ((SPRAM[spriteOffset + 2] & 0x03) << 2) + 0x10
            #SpriteArr += hiColor
            [rows, cols] = SpriteArr.shape
            for i in range(rows):
                for j in range(cols):
                    SpriteArr[i,j] += hiColor
                    
            spriteW = 8 
            spriteH = SpriteArr.shape[0] 
            
            if BGbuffer.shape[0] - spriteY > spriteH and BGbuffer.shape[1] - spriteX > spriteW :
                BGPriority = SPRAM[spriteOffset + 2] & 0x20 #SP_PRIORITY_BIT

                for i in range(spriteW):
                     for j in range(spriteH):
                        if BGPriority:
                            if BGbuffer[spriteY + j, spriteX + i] & 3 == 0:
                                BGbuffer[spriteY + j, spriteX + i] = SpriteArr[j,i]
                        else:
                            if SpriteArr[j,i] & 3 > 0:
                                BGbuffer[spriteY + j, spriteX + i] = SpriteArr[j,i]
                                


    def NameTableArr(self, nt):
        NameTables = self.NameTables_data(nt)
        width = 8 * 32 if len(NameTables) > 0x1f else len(NameTables)  #256
        height = ((len(NameTables) - 1) // 32 + 1) * 8 #240
        ntbuffer = np.zeros((height + 1,width + 1), np.uint8)
        for row in range(width / 8):
            for col in range(height / 8):
                if NameTables[col * 32 + row] == 0:
                    continue
                ntbuffer[col << 3 :(col << 3) + 8 ,row  << 3: (row  << 3) + 8] = self.PatternTableTiles[NameTables[col * 32 + row] + self.PPU_BGTBL_TILE_OFFSET]
        
        return ntbuffer[0:height,0:width]

    def RenderNameTable(self,AttributeTables, FrameBuffer):
        tempFrame = np.zeros((257, 257),np.uint8)
        for i in range(len(AttributeTables)):
            col = i >> 3; row = i & 7
            if AttributeTables[i] == 0:
                continue
            tempFrame[(col << 5)        :(col << 5) + 16 ,  (row << 5)      : (row  << 5) + 16] = (AttributeTables[i] & 0b11) << 2
            tempFrame[(col << 5) + 16   :(col << 5) + 32 ,  (row << 5)      : (row  << 5) + 16] = (AttributeTables[i] & 0b110000) >> 2
            tempFrame[(col << 5)        :(col << 5) + 16 ,  (row << 5) + 16 : (row  << 5) + 32] = (AttributeTables[i] & 0b1100)
            tempFrame[(col << 5) + 16   :(col << 5) + 32 ,  (row << 5) + 16 : (row  << 5) + 32] = (AttributeTables[i] & 0b11000000) >> 4

        
        FrameBuffer |= tempFrame[0:240,0:256]

        [rows, cols] = FrameBuffer.shape
        for i in range(rows):
            for j in range(cols):
                if FrameBuffer[i,j] & 3 == 0: 
                    FrameBuffer[i,j] == 0
    '''            
    def PatternTableArr(self, Pattern_Tables):
        PatternTable = np.zeros((len(Pattern_Tables)>>4,8,8),np.uint8)
        bitarr = range(0x7,-1,-1)
        for TileIndex in range(len(Pattern_Tables)>>4):
            for TileY in range(8):
                PatternTable[TileIndex,TileY] = np.array([1 if (Pattern_Tables[(TileIndex << 4) + TileY]) & (2**bit) else 0 for bit in bitarr], np.uint8) + \
                                                np.array([2 if (Pattern_Tables[(TileIndex << 4) + TileY + 8]) & (2**bit) else 0 for bit in bitarr], np.uint8)

        return PatternTable'''


def import_PPU_class(jit = True):
    return jitObject(PPU, ppu_spec, jit = jit)

def load_PPU(consloe, jit = True):
    ppu_class, ppu_type = import_PPU_class(jit = True)
    ppu = ppu_class(consloe.memory, consloe.ROM)
    return ppu, ppu_type
    
                    
if __name__ == '__main__':
    pass
    pt_l = np.array([[int(b) for b in (bin(i))[2:].rjust(8,'0')] for i in range(256)], np.uint8)
    pt_h = np.array([[int(b)<<1 for b in (bin(i))[2:].rjust(8,'0')] for i in range(256)], np.uint8)

    print(pt_l)
    print(pt_h)
    #ppu = import_PPU_class()
    #print(ppu)
    #print(jitObject(PPU, ppu_spec))
    #print(jitObject(PPU, ppu_spec, jit = False))

    
    
    
    








        
