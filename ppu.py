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

from mmu import MMU

from ppu_reg import PPUREG, PPUBIT


from pal import BGRpal


        
lookup_l = np.array([[(i & (1 << b))>>b for b in np.arange(7,-1,-1)] for i in np.arange(256)], np.uint8)
lookup_h = np.array([[(i & (1 << b))>>b<<1 for b in np.arange(7,-1,-1)] for i in np.arange(256)], np.uint8)

lookup_PT = np.array([[((i>>8 & 1<<b)>>b<<1) + ((i & 1<<b)>>b) for b in range(0x8)][::-1] for i in range(0x10000)], np.uint8)
     



#@jitclass
class PPU(object):
    reg:PPUREG
    #ROM:ROM
    
    CurrentLine:uint16
    HScroll:uint16
    vScroll:uint16
    scX:uint16
    scY:uint16

    PatternTableTiles:uint8[:,:,::1]
    Pal:uint8[:,:]

    ScreenArray:uint8[:,:]
    ATarray:uint8[:,:]
    #NT_BANK:ListType(uint8[::1])
    #FrameNT0:uint8[:,:]
    #FrameNT1:uint8[:,:]
    #FrameNT2:uint8[:,:]
    #FrameNT3:uint8[:,:]
    FrameBuffer:uint8[:,:,:]
    Running:uint8
    render:uint8
    tilebased:uint8
    debug:uint8
    ScanlineSPHit:uint8[:]

    def __init__(self, reg = PPUREG(), pal = BGRpal(), debug = 0):
        self.CurrentLine = 0 
        self.HScroll = 0
        self.vScroll = 0        
        self.scX = 0
        self.scY = 0

        self.reg = reg
        


    
        self.PatternTableTiles = np.zeros((0x2000 >> 4, 8, 8),np.uint8)
        self.Pal        = pal

        self.ScreenArray = np.zeros((240, 256),np.uint8)
        self.ATarray = np.zeros((256, 256),np.uint8)
        #self.NT_BANK = List([np.zeros((240, 256),np.uint8) for i in range(4)])
        #self.FrameNT0 = self.NTArray[0:240,0:256]
        #self.FrameNT1 = self.NTArray[0:240,256:512]
        #self.FrameNT2 = self.NTArray[240:480,0:256]
        #self.FrameNT3 = self.NTArray[240:480,256:512]
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
    def MMU(self):
        return self.reg.MMU
    @property
    def VRAM(self):
        return self.reg.VRAM
    @property
    def SpriteRAM(self):
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

    

    #@property
    #def ROM(self):
    #    return self.ROM
    @property
    def PPU_MEM_BANK(self):
        return self.reg.PPU_MEM_BANK
    @property
    def PPU_MEM_TYPE(self):
        return self.reg.PPU_MEM_TYPE

        
    @property
    def Mirroring(self):
        return 1 #self.ROM.Mirroring
    #@property
    #def MirrorXor(self):
    #    return self.ROM.MirrorXor
    
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

                    
    

    #@property
    def PatternTables(self):
        #if self.Control2 & (PPU_SPDISP_BIT|PPU_BGDISP_BIT) == 0 :return

        #PatternTablesAddress,PatternTablesSize = (0x1000,0x1000) if self.reg.PPUCTRL & self.reg.bit.PPU_SPTBL_BIT else (0,0x1000)
        PatternTablesAddress,PatternTablesSize = (0x1000,0x1000) if self.reg.PPU_SPTBL_BIT else (0,0x1000)
        
        #return self.PatternTableArr(self.VRAM[PatternTablesAddress:PatternTablesAddress + 0x1000])



        
    def RenderFrame(self):
        #return
        if self.reg.PPUMASK & (self.reg.bit.PPU_SPDISP_BIT|self.reg.bit.PPU_BGDISP_BIT) == 0 :return
        
        self.calc_PatternTableTiles()

        #NTnum = (self.loopy_v0 & 0x0FFF) >>10
        #NTnum = self.reg.PPUCTRL & self.reg.bit.PPU_NAMETBL_BIT
        NTnum = self.reg.PPU_NAMETBL_BIT

        #fineYscroll = self.loopy_v >>12
        #coarseYscroll  = (self.loopy_v & 0x03FF) >> 5
        #coarseXscroll = self.loopy_v & 0x1F

        if self.Mirroring:
            #self.scY = (coarseYscroll << 3) + fineYscroll + ((NTnum>>1) * 240) 
            #self.scX = (coarseXscroll << 3)+ self.loopy_x0 #self.HScroll
            self.scY = self.reg.vScroll + ((NTnum>>1) * 240)
            self.scX = self.reg.HScroll + ((NTnum & 1) * 256)
            
        if self.Mirroring == 0:
            #self.scY = (coarseYscroll << 3) + fineYscroll + ((NTnum>>1) * 240) #if self.loopy_v&0x0FFF else self.scY
            self.scY = self.reg.vScroll + ((NTnum>>1) * 240) 
            #if self.loopy_v&0x0FFF else self.scY
        
        self.RenderBG()

        self.RenderSprites()
        
        #self.paintBuffer()

        
    def paintBuffer(self):
        [rows, cols] = self.NTArray.shape
        for i in range(rows):
            for j in range(cols):
                self.FrameBuffer[i, j] = self.Pal[self.Palettes[self.NTArray[i, j]]]
        #return FrameBuffer

    def blitFrame(self):
        paintBuffer(self.NTArray,self.Pal,self.Palettes)

    @property    
    def PPU_SPTBL_OFFSET(self):
        if self.sp16:
            return 0x0
        return 0x1000 if self.reg.PPU_SPTBL_BIT else 0x0
    @property
    def PPU_SPTBL_TILE_OFFSET(self):
        return self.PPU_SPTBL_OFFSET >> 4
    
    def RenderSprites(self):
        self.RenderSpriteArray(self.NTArray, self.SpriteRAM)
         


    #@njit
    def calc_PatternTableTiles(self):
        for TileIndex in range(len(self.PatternTableTiles)):
            page = TileIndex >> 6
            ptr = (TileIndex & 0x3F) << 4
            for TileY in range(8):
                self.PatternTableTiles[TileIndex,TileY] = lookup_l[self.PPU_MEM_BANK[page][ptr + TileY]] \
                                                        + lookup_h[self.PPU_MEM_BANK[page][ptr + TileY + 8]]


    @property
    def PPU_BGTBL_OFFSET(self):
        return self.reg.PPU_BGTBL_BIT << 8
    @property
    def PPU_BGTBL_TILE_OFFSET(self):
        return self.reg.PPU_BGTBL_BIT << 4

    def RenderBG(self):
        
        self.calc_NameTable()
        self.calc_AttributeTable()
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

    def calc_AttributeTable(self):
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

    def MirrorNT(self):
            self.NTArray[0:240,512:768] = self.NTArray[0:240,0:256]     #0
            self.NTArray[480:720,0:256] = self.NTArray[0:240,0:256]     #0

            self.NTArray[480:720,256:512] = self.NTArray[0:240,256:512] #1
            self.NTArray[240:480,512:768] = self.NTArray[240:480,0:256] #2            

        
    def RenderNameTableH(self, nt0, nt1):
        tempBuffer0 = self.NameTableArr(nt0)
        self.RenderNameTable(self.AttributeTables_data(nt0), tempBuffer0)
        
        tempBuffer1 = self.NameTableArr(nt1)
        self.RenderNameTable(self.AttributeTables_data(nt1), tempBuffer1)
        
        self.NTArray[0:480,0:768] = np.row_stack((np.column_stack((tempBuffer0,tempBuffer1,tempBuffer0)),np.column_stack((tempBuffer0,tempBuffer1,tempBuffer0))))

    
    def RenderNameTableV(self, nt0, nt2):
        tempBuffer0 = self.NameTableArr(nt0)
        self.RenderNameTable(self.AttributeTables_data(nt0), tempBuffer0)
        
        tempBuffer2 = self.NameTableArr(nt2)
        self.RenderNameTable(self.AttributeTables_data(nt2), tempBuffer2)
        
        self.NTArray[0:720,0:512] =  np.column_stack((np.row_stack((tempBuffer0,tempBuffer2,tempBuffer0)),np.row_stack((tempBuffer0,tempBuffer2,tempBuffer0))))


    def RenderAttributeTables(self,offset):
        AttributeTablesAddress = 0x2000 + (offset * 0x400 + 0x3C0)
        AttributeTablesSize = 0x40

    

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



#PPU
#PPU_Memory_type = nb.deferred_type()
#PPU_Memory_type.define(PPU_Memory.class_type.instance_type)
#PPU_Reg_type = nb.deferred_type()
#PPU_Reg_type.define(PPUREG.class_type.instance_type)
#ROM_class_type = nb.deferred_type()
#ROM_class_type.define(ROM.class_type.instance_type)
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
           ('FrameBuffer',uint8[:,:,:]),
           ('Running',uint8),
           ('render',uint8),
           ('tilebased',uint8),
           ('debug',uint8),
           ('ScanlineSPHit',uint8[:])
    ]
'''

def import_PPU_class(jit = True):
    return jitObject(PPU, [], jit = jit)

def load_PPU(MMU = MMU(), jit = True):
    ppu_class, ppu_type = import_PPU_class(jit = jit)
    ppu = ppu_class(PPUREG(MMU))
    return ppu, ppu_type
    
                    
if __name__ == '__main__':
    pass

    print(PPU())
    ppu, ppu_type = load_PPU()


    
    
    
    








        
