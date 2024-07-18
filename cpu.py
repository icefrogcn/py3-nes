# -*- coding: UTF-8 -*-

import time
from numba import jit,objmode
from numba import types, typed
from numba.experimental import jitclass
from numba import int8,uint8,int16,uint16,uint32,uint64
import numpy as np
import numba as nb

import traceback


#CPU Memory Map

#自定义类
from deco import *
from jitcompile import jitObject
         
#import memory
from nes import NES

from mmc import *

from mmu import MMU
from cpu_reg import CPU_Reg
from cpu_memory import CPU_Memory

#from apu import APU#,APU_type
from ppu import PPU
from mapper import MAPPER
from joypad import JOYPAD




C_FLAG = np.uint8(0x01)	#	# 1: Carry
Z_FLAG = np.uint8(0x02)	#	# 1: Zero
I_FLAG = np.uint8(0x04)	#	# 1: Irq disabled
D_FLAG = np.uint8(0x08)	#	# 1: Decimal mode flag (NES unused)
B_FLAG = np.uint8(0x10)	#	# 1: Break
R_FLAG = np.uint8(0x20)	#	# 1: Reserved (Always 1)
V_FLAG = np.uint8(0x40)	#	# 1: Overflow
N_FLAG = np.uint8(0x80)	#	# 1: Negative

# Interrupt
NMI_FLAG = 0x01
IRQ_FLAG = 0x02

# Vector
NMI_VECTOR = 0xFFFA
RES_VECTOR = 0xFFFC
IRQ_VECTOR = 0xFFFE

ScanlineCycles = 1364
FETCH_CYCLES = 8
HDrawCycles = 1024
HBlankCycles = 340

CPU_Memory_type = nb.deferred_type()
CPU_Memory_type.define(CPU_Memory.class_type.instance_type)
CPU_Reg_type = nb.deferred_type()
CPU_Reg_type.define(CPU_Reg.class_type.instance_type)
#PPU_type = nb.deferred_type()
#PPU_type.define(PPU.class_type.instance_type)
JOYPAD_type = nb.deferred_type()
JOYPAD_type.define(JOYPAD.class_type.instance_type)

cpu_spec = [#('PC',uint16),
            #('A',uint8),
            #('X',uint8),
            #('Y',uint8),
            #('S',uint8),
            #('P',uint16),
            #('reg',CPU_Reg_type),
            #('INT_pending',uint8),
            #('nmicount',int16),
            #('DT',uint8),
            #('WT',uint16),
            #('EA',uint16),
            #('ET',uint16),
            #('clockticks6502',uint32),
            #('exec_cycles',uint8),
            #('emul_cycles',uint64),
            #('base_cycles',uint64),
            #('TOTAL_cycles',uint32),
            #('DMA_cycles',uint32),
            #('opcode',uint8),
            #('STACK',uint8[:]),
            #('ZN_Table',uint8[:]),
            #('memory',CPU_Memory_type),
            #('RAM',uint8[:,:]),
            #('bank0',uint8[:]),
            #('Sound',uint8[:]),
            #('NewMapperWriteFlag',uint8),
            #('isMapperWrite',uint8),
            #('MapperWriteData',uint8),
            #('MapperWriteAddress',uint16),
            #('FrameFlag',uint8),
            #('isDraw',uint8),
            #('Frames',uint32),
            #('PPU',PPU_type),
            #('RenderMethod',uint8),
            #('ChannelWrite',uint8[:]),
            #('MAPPER',MAPPER),
            #('JOYPAD',JOYPAD_type),
            #('Running',uint8),
            #('addrmode',uint8[:]),
            #('instructions',uint8[:]),
            #('Ticks',uint8[:])#,

            ]
ChannelWrite = np.zeros(0x4,np.uint8)


#print('loading CPU CLASS')  
        
#@jitclass
class CPU6502(object):
    'Registers & tempregisters'
    PC:uint16
    A: uint8
    X: uint8
    Y: uint8
    S: uint8
    P: uint16
    reg: CPU_Reg
    INT_pending: uint8
    nmicount: int16
    DT: uint8
    WT: uint16
    EA: uint16
    ET: uint16
    clockticks6502: uint32
    exec_cycles: uint8
    emul_cycles: uint64
    base_cycles: uint64
    TOTAL_cycles: uint32
    DMA_cycles: uint32
    opcode: uint8
    ZN_Table: uint8[:]
    
    FrameFlag: uint8
    Frames: uint32
    #PPU: PPU
    RenderMethod: uint8
    ChannelWrite: uint8[:]
    
    JOYPAD: JOYPAD
    Running: uint8


    '32bit instructions are faster in protected mode than 16bit'

    MAPPER: MAPPER
    
    def __init__(self,
                 MAPPER,# = MAPPER(),
                 MMU = MMU(),
                 PPU = PPU(),
                 ChannelWrite = ChannelWrite,
                 reg = CPU_Reg(),
                 JOYPAD = JOYPAD()
                 ):

        #self.AddressMask =0 #Long 'Integer
        self.reg = reg
        self.PC = 0          
        self.A = np.uint8(0)           
        self.X = np.uint8(0)             
        self.Y = np.uint8(0)              
        self.S = np.uint8(0)               
        self.P = 0            
        self.DT = np.uint8(0) 
        self.WT = np.uint16(0) 
        self.EA = np.uint16(0)
        self.ET = np.uint16(0)
        self.INT_pending = 0
        self.nmicount = 0

        self.clockticks6502 = 0
        self.exec_cycles = 0
        self.opcode = 0

        self.base_cycles = self.emul_cycles = self.DMA_cycles = 0
        self.TOTAL_cycles = 0

        self.ZN_Table = np.zeros(256,dtype = np.uint8)
        self.ZN_Table[0] = Z_FLAG
        for i in range(1,256):
            self.ZN_Table[i] = N_FLAG if i&0x80 else 0

        self.MMU = MMU

        
        #self.debug = 0


        self.FrameFlag = 0
        self.isDraw = 0
        self.Frames = 0

        self.PPU = PPU
        
        #self.APU = APU
        self.ChannelWrite = ChannelWrite

        self.MAPPER = MAPPER

        self.JOYPAD = JOYPAD

        self.RenderMethod = self.MAPPER.RenderMethod
        
        
        self.Running = 1
        

    @property
    def RAM(self):
        return self.MMU.RAM
    @property
    def bank0(self):
        return self.RAM[0]
    @property
    def STACK(self):
        return self.bank0[0x100:0x200]
    @property
    def Sound(self):
        return self.MMU.RAM[2][0:0x100]
    
        
    @property
    def CpuClock(self):
        return 1789772.5
    @property
    def ScanlineCycles(self):
        return 114
    @property
    def FrameCycles(self):
        return 29780.5
    @property
    def FrameIrqCycles(self):
        return 29780.5

    @property
    def debug(self):
        return 0
    def ZPRD(self,A):
        return self.bank0[A & 0xFF]
    def ZPRDW(self,A):
        return self.bank0[A & 0xFF] + (self.bank0[(A + 1)& 0xFF] << 8)
    
    def ZPWR(self,A,V):
        self.bank0[A & 0xFF] = V
    def ZPWRW(self,A,V):
        self.bank0[A & 0xFF] = V & 0xFF
        self.bank0[(A+1) & 0xFF] = V >> 8
        
    
    def ADD_CYCLE(self,V):self.exec_cycles += V
    
    def CHECK_EA(self):
        if((self.ET&0xFF00) != (self.EA&0xFF00) ):self.ADD_CYCLE(1); 
    
    def SET_ZN_FLAG(self,A):
        self.P &= ~(Z_FLAG|N_FLAG)
        self.P |= self.ZN_Table[A & 0xFF]
    
    def SET_FLAG(self, V):
        self.P |=  V
    def CLR_FLAG(self, V):
        self.P &= ~(V)
    def TST_FLAG(self, F, V):
        self.P &= ~(V);
        if (F):self.P |= V
    def CHK_FLAG(self, V):
        return self.P & V

    'WT .... WORD TEMP'
    'EA .... EFFECTIVE ADDRESS'
    'ET .... EFFECTIVE ADDRESS TEMP'
    'DT .... DATA'

    def MR_IM(self):
        self.DT = self.OP6502(self.PC);self.PC += 1
    def MR_ZP(self):
        self.EA = self.OP6502(self.PC);self.PC += 1
        self.DT = self.ZPRD(self.EA)
    def MR_ZX(self):
        DT = self.OP6502(self.PC);self.PC += 1
        self.EA = DT + self.X
        self.DT = self.ZPRD(self.EA)
    def MR_ZY(self):
        DT = self.OP6502(self.PC);self.PC += 1
        self.EA = DT + self.Y
        self.DT = self.ZPRD(self.EA)
        
    def MR_AB(self):
        self.EA_AB()
        self.DT = self.RD6502(self.EA)
    def MR_AX(self):
        self.EA_AX()
        self.DT = self.RD6502(self.EA)
    def MR_AY(self):
        self.EA_AY()
        self.DT = self.RD6502(self.EA)

    def MR_IX(self):
        self.EA_IX()
        self.DT = self.RD6502(self.EA)
    def MR_IY(self):
        self.EA_IY()
        self.DT = self.RD6502(self.EA)
    
    'EFFECTIVE ADDRESS'
    def EA_ZP(self):
        self.EA = self.OP6502(self.PC);self.PC += 1
    def EA_ZX(self):
        self.DT = self.OP6502(self.PC);self.PC += 1
        self.EA = self.DT + self.X
    def EA_ZY(self):
        self.DT = self.OP6502(self.PC);self.PC += 1
        self.EA = self.DT + self.Y
    def EA_AB(self):
        self.EA = self.OP6502W(self.PC);self.PC += 2
    def EA_AX(self):
        self.ET = self.OP6502W(self.PC);self.PC += 2
        self.EA = self.ET + self.X
    def EA_AY(self):
        self.ET = self.OP6502W(self.PC);self.PC += 2
        self.EA = self.ET + self.Y
    def EA_IX(self):
        self.DT = self.OP6502(self.PC);self.PC += 1
        self.EA = self.ZPRDW(self.DT + self.X)
    def EA_IY(self):
        self.DT = self.OP6502(self.PC);self.PC += 1
        self.ET = self.ZPRDW(self.DT)
        self.EA = self.ET + self.Y

    def MW_ZP(self):
        self.ZPWR(self.EA, self.DT)
    def MW_EA(self):
        self.WR6502(self.EA, self.DT)

    'STACK'
    def PUSH(self,value):
        self.STACK[self.S & 0xFF] = value;self.S -= 1;self.S &= 0xFF
      
    def POP(self):
        self.S += 1
        self.S &= 0xFF
        return self.STACK[self.S]

    
    ' This is where all 6502 instructions are kept.'
    ' ADC (NV----ZC) '
    def ADC(self):
        self.WT = self.A + self.DT + (self.P & C_FLAG)		
        self.TST_FLAG( self.WT > 0xFF, C_FLAG )	
        self.TST_FLAG( ((~(self.A^self.DT)) & (self.A ^ self.WT) & 0x80), V_FLAG )	
        self.A = self.WT & 0xFF		
        self.SET_ZN_FLAG(self.A)

    ' SBC (NV----ZC) '
    def SBC(self): 		
        self.WT = self.A - self.DT - (~self.P & C_FLAG)
        self.TST_FLAG( ((self.A^self.DT) & (self.A^self.WT)&0x80), V_FLAG )
        self.TST_FLAG( self.WT < 0x100, C_FLAG )	
        self.A = self.WT & 0xFF	
        self.SET_ZN_FLAG(self.A)

    
    ' INC (N-----Z-) '
    def INC(self):			
        self.DT += 1;self.DT &= 0xFF
        self.SET_ZN_FLAG(self.DT);	
    
    ' INX (N-----Z-) '
    def	INX(self) :		
        self.X += 1;self.X &= 0xFF		
        self.SET_ZN_FLAG(self.X);	
    
    ' INY (N-----Z-) '
    def	INY(self):
        self.Y += 1;self.Y &= 0xFF
        self.SET_ZN_FLAG(self.Y);	
    
    ' DEC (N-----Z-) '
    def DEC(self):			
        self.DT -= 1;self.DT &= 0xFF
        self.SET_ZN_FLAG(self.DT);	
    
    ' DEX (N-----Z-) '
    def	DEX(self) :		
        self.X -= 1;self.X &= 0xFF		
        self.SET_ZN_FLAG(self.X);	
    
    ' DEY (N-----Z-) '
    def	DEY(self):
        self.Y -= 1;self.Y &= 0xFF
        self.SET_ZN_FLAG(self.Y);

    'AND(N - ----Z -) '
    def AND(self) :
        self.A &= self.DT;
        self.SET_ZN_FLAG(self.A);

    '*ORA(N - ----Z -)'
    def ORA(self):
        self.A |= self.DT;
        self.SET_ZN_FLAG(self.A);

    'EOR(N - ----Z -)'
    def EOR(self):
        self.A ^= self.DT;
        self.SET_ZN_FLAG(self.A);

    '/ *ASL_A(N - ----ZC) * /'
    def ASL_A(self):
        self.TST_FLAG(self.A & 0x80, C_FLAG); \
        self.A <<= 1; \
        self.SET_ZN_FLAG(self.A); \


    '/ *ASL(N - ----ZC) * /'
    def ASL(self):
        self.TST_FLAG(self.DT & 0x80, C_FLAG); \
        self.DT <<= 1; \
        self.SET_ZN_FLAG(self.DT); \

    '/ *LSR_A(N - ----ZC) * /'
    def LSR_A(self):			\
        self.TST_FLAG(self.A & 0x01, C_FLAG); \
        self.A >>= 1; \
        self.SET_ZN_FLAG(self.A); \

    '/ *LSR(N - ----ZC) * /'
    def	LSR(self):			\
        self.TST_FLAG(self.DT & 0x01, C_FLAG); \
        self.DT >>= 1; \
        self.SET_ZN_FLAG(self.DT);
    '/* ROL_A (N-----ZC) */'
    def	ROL_A(self):				
        if( self.P & C_FLAG ):		
            self.TST_FLAG(self.A&0x80,C_FLAG);	
            self.A = (self.A<<1)|0x01;		
        else:			\
            self.TST_FLAG(self.A&0x80,C_FLAG);	\
            self.A <<= 1;			\

        self.SET_ZN_FLAG(self.A);
        
    '/* ROL (N-----ZC) */'
    def	ROL(self):				
        if( self.P & C_FLAG ):			\
            self.TST_FLAG(self.DT&0x80,C_FLAG);	\
            self.DT = (self.DT<<1)|0x01;		
        else:
            self.TST_FLAG(self.DT&0x80,C_FLAG);	\
            self.DT <<= 1;
            
        self.SET_ZN_FLAG(self.DT);			\


    '/* ROR_A (N-----ZC) */'
    def	ROR_A(self):				
        if( self.P & C_FLAG ):			
            self.TST_FLAG(self.A&0x01,C_FLAG);	
            self.A = (self.A>>1)|0x80;		
        else:				
            self.TST_FLAG(self.A&0x01,C_FLAG);	\
            self.A >>= 1;
        
        self.SET_ZN_FLAG(self.A);			\
    
    '/* ROR (N-----ZC) */'
    def	ROR(self):					
        if( self.P & C_FLAG ):		
            self.TST_FLAG(self.DT&0x01,C_FLAG);	
            self.DT = (self.DT>>1)|0x80;		
        else :
            self.TST_FLAG(self.DT&0x01,C_FLAG);	
            self.DT >>= 1;			
        
        self.SET_ZN_FLAG(self.DT);			

    '/* BIT (NV----Z-) */'
    def	BIT(self):					\
        self.TST_FLAG( (self.DT&self.A)==0, Z_FLAG );	\
        self.TST_FLAG( self.DT&0x80, N_FLAG );		\
        self.TST_FLAG( self.DT&0x40, V_FLAG );

    '/* LDA (N-----Z-) */'
    def LDA(self):
        self.A = self.DT; self.SET_ZN_FLAG(self.A); 
    '/* LDX (N-----Z-) */'
    def LDX(self):
        self.X = self.DT; self.SET_ZN_FLAG(self.X); 
    '/* LDY (N-----Z-) */'
    def LDY(self):
        self.Y = self.DT; self.SET_ZN_FLAG(self.Y); 

    '/* STA (--------) */'
    def	STA(self):
        self.DT = self.A; 
    '/* STX (--------) */'
    def	STX(self):
        self.DT = self.X; 
    '/* STY (--------) */'
    def	STY(self):
        self.DT = self.Y;

    '/* TAX (N-----Z-) */'
    def	TAX(self):
        self.X = self.A; self.SET_ZN_FLAG(self.X); 
    '/* TXA (N-----Z-) */'
    def	TXA(self):
        self.A = self.X; self.SET_ZN_FLAG(self.A); 
    '/* TAY (N-----Z-) */'
    def	TAY(self):
        self.Y = self.A; self.SET_ZN_FLAG(self.Y); 
    '/* TYA (N-----Z-) */'
    def	TYA(self):
        self.A = self.Y; self.SET_ZN_FLAG(self.A); 
    '/* TSX (N-----Z-) */'
    def	TSX(self):
        self.X = self.S; self.SET_ZN_FLAG(self.X); 
    '/* TXS (--------) */'
    def	TXS(self):
        self.S = self.X; 


    '/* CMP (N-----ZC) */'
    def	CMP(self): 				
        self.WT = self.A - self.DT;				
        self.TST_FLAG( (self.WT&0x8000)==0, C_FLAG )	
        self.SET_ZN_FLAG( self.WT )		
    
    '/* CPX (N-----ZC) */'
    def	CPX(self):			\
        self.WT = self.X - self.DT;				\
        self.TST_FLAG( (self.WT&0x8000)==0, C_FLAG );	\
        self.SET_ZN_FLAG( self.WT );		\
    
    '/* CPY (N-----ZC) */'
    def	CPY(self) :				\
        self.WT = self.Y - self.DT;				\
        self.TST_FLAG( (self.WT&0x8000)==0, C_FLAG );	\
        self.SET_ZN_FLAG( self.WT );

    def JMP_ID(self):			\
        self.WT = self.OP6502W(self.PC);			\
        self.EA = self.RD6502(self.WT);			\
        self.WT = (self.WT&0xFF00)|((self.WT+1)&0x00FF);	\
        self.PC = self.EA+self.RD6502(self.WT)*0x100;		\

    def JMP(self):			\
        self.PC = self.OP6502W( self.PC );

    def JSR(self):			\
        self.EA = self.OP6502W( self.PC );	\
        self.PC += 1 ;			\
        self.PUSH( self.PC>>8 );	\
        self.PUSH( self.PC&0xFF );	\
        self.PC = self.EA;

    def RTS(self):			\
        self.PC  = self.POP();		\
        self.PC |= self.POP()*0x0100;	\
        self.PC += 1 ;			\
    
    def	RTI(self):		\
        self.P   = self.POP() | R_FLAG;	\
        self.PC  = self.POP();		\
        self.PC |= self.POP()*0x0100;	\

    @property
    def nmibasecount(self):
        return 0

    def DMA(self,cycles):
        self.DMA_cycles += cycles
    
    def NMI(self):
        self.INT_pending |= NMI_FLAG;
        self.nmicount = self.nmibasecount;

    def IRQ(self):
        self.INT_pending |= IRQ_FLAG;

    def IRQ_NotPending(self):
        if( not (self.P & I_FLAG) ):
            self.INT_pending |= IRQ_FLAG;

        
    def	_NMI(self):		\
        self.PUSH( self.PC>>8 );		\
        self.PUSH( self.PC&0xFF );		\
        self.CLR_FLAG( B_FLAG );		\
        self.PUSH( self.P );			\
        self.SET_FLAG( I_FLAG );		\
        self.PC = self.RD6502W(NMI_VECTOR);	\
        self.INT_pending &= ~NMI_FLAG;	\
        self.exec_cycles += 6;		\
    
    def	_IRQ(self):			
        if( not(self.P & I_FLAG) ):
            self.PUSH( self.PC>>8 );		\
            self.PUSH( self.PC&0xFF );		\
            self.CLR_FLAG( B_FLAG );		\
            self.PUSH( self.P );			\
            self.SET_FLAG( I_FLAG );		\
            self.PC = self.RD6502W(IRQ_VECTOR);	\
            self.exec_cycles += 6;		\
            self.INT_pending &= ~IRQ_FLAG;	

    def BRK(self):				
        self.PC += 1 ;				\
        self.PUSH( self.PC>>8 );		\
        self.PUSH( self.PC&0xFF );		\
        self.SET_FLAG( B_FLAG );		\
        self.PUSH( self.P );			\
        self.SET_FLAG( I_FLAG );		\
        self.PC = self.RD6502W(IRQ_VECTOR);

    def REL_JUMP(self):		\
        self.ET = self.PC;		\
        self.EA = self.PC + np.int8(self.DT);	\
        self.PC = self.EA;		\
        self.ADD_CYCLE(1);		\
        self.CHECK_EA();

    def	BCC(self):
        if( not (self.P & C_FLAG) ): self.REL_JUMP(); 
    def	BCS(self):
        if(  (self.P & C_FLAG) ): self.REL_JUMP(); 
    def	BNE(self):
        if( not (self.P & Z_FLAG) ): self.REL_JUMP(); 
    def	BEQ(self):
        if(  (self.P & Z_FLAG) ): self.REL_JUMP(); 
    def	BPL(self):
        if( not (self.P & N_FLAG) ): self.REL_JUMP(); 
    def	BMI(self):
        if(  (self.P & N_FLAG) ): self.REL_JUMP(); 
    def	BVC(self):
        if( not (self.P & V_FLAG) ): self.REL_JUMP(); 
    def	BVS(self):
        if(  (self.P & V_FLAG) ): self.REL_JUMP(); 


    def	CLC(self):
        self.P &= ~C_FLAG; 
    def	CLD(self):
        self.P &= ~D_FLAG; 
    def	CLI(self):
        self.P &= ~I_FLAG; 
    def	CLV(self):
        self.P &= ~V_FLAG; 
    def	SEC(self):
        self.P |= C_FLAG; 
    def	SED(self):
        self.P |= D_FLAG; 
    def	SEI(self):
        self.P |= I_FLAG; 

    '// Unofficial'
    def	ANC(self):				
        self.A &= self.DT;			\
        self.SET_ZN_FLAG( self.A );		\
        self.TST_FLAG( self.P&N_FLAG, C_FLAG );

    def	ANE(self):			
        self.A = (self.A|0xEE)&self.X&self.DT;	\
        self.SET_ZN_FLAG( self.A );

    def	ARR(self):				\
        self.DT &= self.A;				\
        self.A = (self.DT>>1)|((self.P&C_FLAG)<<7);	\
        self.SET_ZN_FLAG( self.A );			\
        self.TST_FLAG( self.A&0x40, C_FLAG );		\
        self.TST_FLAG( (self.A>>6)^(self.A>>5), V_FLAG );	
    

    def	ASR(self):			\
        self.DT &= self.A;			\
        self.TST_FLAG( self.DT&0x01, C_FLAG );	\
        self.A = self.DT>>1;			\
        self.SET_ZN_FLAG( self.A );		

    def	DCP(self):			
        self.DT -= 1;				\
        self.CMP();				\
    
    def	DOP(self):				
        self.PC += 1;				\
    
    def	ISB(self):				
        self.DT += 1;				\
        self.SBC();				

    def	LAS(self):				
        self.A = self.X = self.S = (self.S & self.DT);	\
        self.SET_ZN_FLAG( self.A );		
    
    def	LAX(self):				
        self.A = self.DT;			\
        self.X = self.A;			\
        self.SET_ZN_FLAG( self.A );		
    
    def	LXA(self):				
        self.A = self.X = ((self.A|0xEE)&self.DT);	\
        self.SET_ZN_FLAG( self.A );		


    def	RLA(self):					
        if( self.P & C_FLAG ) :			
            self.TST_FLAG( self.DT&0x80, C_FLAG );	
            self.DT = (self.DT<<1)|1;			
        else:
            self.TST_FLAG( self.DT&0x80, C_FLAG );	
            self.DT <<= 1;			

        self.A &= self.DT;				
        self.SET_ZN_FLAG( self.A );			
    

    def	RRA(self):				
        if(self.P & C_FLAG ):			
            self.TST_FLAG( self.DT&0x01, C_FLAG );	
            self.DT = (self.DT>>1)|0x80;		
        else:				
            self.TST_FLAG( self.DT&0x01, C_FLAG );	
            self.DT >>= 1;			
        
        self.ADC();



    def	SAX(self):			
        self.DT = self.A & self.X;			\

    def	SBX(self):
        self.WT = (self.A&self.X)-self.DT;		\
        self.TST_FLAG( self.WT < 0x100, C_FLAG );	\
        self.X = self.WT&0xFF;			\
        self.SET_ZN_FLAG( self.X );		\

    def	SHA(self):
        self.DT = self.A & self.X & (((self.EA>>8)+1)&0xFF);	\

    def	SHS(self):
        self.S = self.A & self.X;		\
        self.DT = self.S & (((self.EA>>8)+1)&0xFF);	\
    

    def	SHX(self):
        self.DT = self.X & (((self.EA>>8)+1)&0xFF);	\
    

    def	SHY(self):
        self.DT = self.Y & (((self.EA>>8)+1)&0xFF);	\
    

    def	SLO(self):
        self.TST_FLAG( self.DT&0x80, C_FLAG );	\
        self.DT <<= 1;			\
        self.A |= self.DT;			\
        self.SET_ZN_FLAG( self.A );		\
    

    def	SRE(self):
        self.TST_FLAG( self.DT&0x01, C_FLAG );	\
        self.DT >>= 1;			\
        self.A ^= self.DT;			\
        self.SET_ZN_FLAG( self.A );		\
    

    def	TOP(self):
        self.PC += 2;			\
    






    def FrameFlag_ZERO(self):
        self.FrameFlag = 0

       
    def implied6502(self):
        return

    @property
    def status(self):
        return self.PC,self.exec_cycles,self.PPU.reg.PPUSTATUS,self.Frames,self.PPU.CurrentLine,self.A,self.X,self.Y,self.S,self.P,self.opcode

    def log(self,*args):
        if self.debug:
            pass
        #print(args)



    @property
    def ttime(self):
        with objmode(time1='f8'):
            time1 = time.time()
        return time1

    def FrameRender_ZERO(self):
        self.FrameFlag &= ~self.FrameRender
    def FrameSound_ZERO(self):
        self.FrameFlag &= ~self.FrameSound
    #def MapperWriteFlag_ZERO(self):
        #self.isMapperWrite = 0

    def EmulationCPU(self,basecycles):
        self.base_cycles += basecycles
        cycles = int(self.base_cycles//12) - self.emul_cycles
        if cycles > 0:
            self.emul_cycles += self.EXEC6502(cycles)

    def EmulationCPU_BeforeNMI(self,cycles):
        self.base_cycles += cycles
        self.emul_cycles += self.EXEC6502(cycles//12)



    @property
    def FRAME_RENDER(self):
        return np.uint8(0x1)
    @property
    def isFrameRender(self):
        return self.FrameFlag & self.FRAME_RENDER
    @property
    def FrameSound(self):
        return np.uint8(0x2)
    @property
    def isFrameSound(self):
        return self.FrameFlag & self.FrameSound

    
    def run6502(self):
        while self.Running:
            if self.isFrameRender:
                self.FrameFlag &= ~self.FRAME_RENDER
                return self.FRAME_RENDER
            #if self.isDraw:
                #continue

            if self.isFrameSound:
                self.FrameFlag &= ~self.FrameSound
                return self.FrameSound
                
            #if self.isMapperWrite:
                #return self.FrameFlag

            if self.PPU.CurrentLine in (0,131):
                self.FrameFlag |= self.FrameSound
                        
            if( self.RenderMethod != TILE_RENDER ):
                if self.PPU.CurrentLine == 0:
                    if( self.RenderMethod < POST_RENDER ):
                        self.EmulationCPU(ScanlineCycles)
                        self.PPU.FrameStart()
                        self.PPU.ScanlineNext()
                        if self.MAPPER.HSync( self.PPU.CurrentLine ):self.IRQ_NotPending()
                        self.PPU.ScanlineStart()
                    else:
                        self.EmulationCPU(HDrawCycles)
                        self.PPU.FrameStart()
                        self.PPU.ScanlineNext()
                        if self.MAPPER.HSync( self.PPU.CurrentLine ):self.IRQ_NotPending()
                        self.EmulationCPU(FETCH_CYCLES*32)
                        self.PPU.ScanlineStart()
                        self.EmulationCPU( FETCH_CYCLES*10 + 4 )
                    
                elif self.PPU.CurrentLine < 240:
                    if( self.RenderMethod < POST_RENDER ):
                        if( self.RenderMethod == POST_ALL_RENDER ):
                            self.EmulationCPU(ScanlineCycles)
                        self.PPU.RenderScanline()
                        self.PPU.ScanlineNext()
                        if( self.RenderMethod == PRE_ALL_RENDER ):
                            self.EmulationCPU(ScanlineCycles )
                            
                        if self.MAPPER.HSync( self.PPU.CurrentLine ):self.IRQ_NotPending()
                        self.PPU.ScanlineStart()
                    else:
                        if( self.RenderMethod == POST_RENDER ):
                            self.EmulationCPU(HDrawCycles)
                        self.PPU.RenderScanline()

                        if( self.RenderMethod == PRE_RENDER ):
                            self.EmulationCPU(HDrawCycles)

                        self.PPU.ScanlineNext()

                        if self.MAPPER.HSync( self.PPU.CurrentLine ):self.IRQ_NotPending()
                        self.EmulationCPU(FETCH_CYCLES*32)
                        self.PPU.ScanlineStart()
                        self.EmulationCPU(FETCH_CYCLES*10 + 4 )



                    
                elif self.PPU.CurrentLine == 240:
                    #mapper->VSync()
                    self.FrameFlag |= self.FRAME_RENDER
                    #self.isDraw = 1
                    
                    if( self.RenderMethod == POST_RENDER ):
                        self.EmulationCPU(ScanlineCycles)
                        if self.MAPPER.HSync( self.PPU.CurrentLine ):self.IRQ_NotPending()
                    else:
                        self.EmulationCPU(HDrawCycles)
                        if self.MAPPER.HSync( self.PPU.CurrentLine ):self.IRQ_NotPending()
                        self.EmulationCPU(HBlankCycles)
                        
                    self.Frames += 1
                    
                    
                elif self.PPU.CurrentLine <= 261: #VBLANK
                    self.isDraw = 0
                        
                    if self.PPU.CurrentLine == 261:
                        self.PPU.VBlankEnd()
                        #self.FrameFlag |= self.FRAME_RENDER

                    if( self.RenderMethod == POST_RENDER ):
                        if self.PPU.CurrentLine == 241:
                            self.PPU.VBlankStart()
                            self.EmulationCPU_BeforeNMI(4*12)
                            if self.PPU.reg.PPUCTRL & 0x80:
                                self.NMI()
                            self.EmulationCPU(ScanlineCycles-(4*12))
                        else:
                            self.EmulationCPU(ScanlineCycles)

                        if self.MAPPER.HSync( self.PPU.CurrentLine ):self.IRQ_NotPending()
                    else:
                        if self.PPU.CurrentLine == 241:
                            self.PPU.VBlankStart()
                            self.EmulationCPU_BeforeNMI(4*12)
                            if self.PPU.reg.PPUCTRL & 0x80:
                                self.NMI()
                            self.EmulationCPU(HDrawCycles-(4*12))
                        else:
                            self.EmulationCPU(HDrawCycles)
                        if self.MAPPER.HSync( self.PPU.CurrentLine ):self.IRQ_NotPending()
                        self.EmulationCPU(HBlankCycles)

                    if self.PPU.CurrentLine == 261:
                        
                        self.PPU.CurrentLine_ZERO()
                        #return 0

                self.PPU.CurrentLine_increment(1)
            
            #TILE_RENDER
            '''
            if self.PPU.CurrentLine == 0:
                self.EmulationCPU(FETCH_CYCLES*128)
                self.EmulationCPU(FETCH_CYCLES*16)
                #mapper->HSync( scanline )
                self.EmulationCPU(FETCH_CYCLES*16)
                self.EmulationCPU( FETCH_CYCLES*10 + 4 )
                
            elif self.PPU.CurrentLine < 240:
                self.PPU.RenderScanline()
                self.EmulationCPU( FETCH_CYCLES*16 )
                #mapper->HSync( scanline )
                self.EmulationCPU( FETCH_CYCLES*16 )
                self.EmulationCPU( FETCH_CYCLES*10 + 4 )
                
            elif self.PPU.CurrentLine == 240:
                #mapper->VSync()
                self.EmulationCPU(HDrawCycles)
                #mapper->HSync( scanline )
                self.EmulationCPU(HBlankCycles)
            elif self.PPU.CurrentLine <= 261:
                
                if self.PPU.CurrentLine == 261:
                    self.PPU.VBlankEnd()

                if self.PPU.CurrentLine == 241:
                    self.PPU.VBlankStart()

                    if self.PPU.reg.PPUCTRL & 0x80:
                        self.EmulationCPU_BeforeNMI(4*12)
                        self.NMI()
                        self.EmulationCPU(HDrawCycles-(4*12))
                    else:
                        self.EmulationCPU(HDrawCycles)
                else:
                    self.EmulationCPU(HDrawCycles)

                #mapper->HSync( scanline )
                self.EmulationCPU(HBlankCycles)

                if self.PPU.CurrentLine == 261:
                    self.PPU.CurrentLine_ZERO()
                    break
                '''

            
        
    def EXEC6502(self,request_cycles):

        OLD_cycles = self.TOTAL_cycles
        
        
        
        while request_cycles > 0:
            self.exec_cycles = 0

            if (self.DMA_cycles):
                if request_cycles <= self.DMA_cycles:
                    self.DMA_cycles -= request_cycles
                    self.TOTAL_cycles += request_cycles
                    if self.MAPPER.Clock( request_cycles ):self.IRQ_NotPending()

                    return self.TOTAL_cycles - OLD_cycles
                
                else:
                    self.exec_cycles += self.DMA_cycles
                    request_cycles -= self.DMA_cycles
                    self.DMA_cycles = 0
                    
            
            if( self.INT_pending ):
                if( self.INT_pending & NMI_FLAG ):
                    if( self.nmicount <= 0 ):
                        self._NMI();
                    else:
                        self.nmicount -= 1;
                else:
                    self._IRQ();

            self.exec_opcode()
            
            request_cycles -= self.exec_cycles
            self.TOTAL_cycles += self.exec_cycles

            if self.MAPPER.Clock(self.exec_cycles):self.IRQ_NotPending()

            
            self.clockticks6502 += self.exec_cycles
            if self.clockticks6502 >= self.CpuClock:
                self.clockticks6502 -= self.CpuClock
                
            
            
        return self.TOTAL_cycles - OLD_cycles
            


    def OP6502(self,addr):
        return self.RD6502(addr)
        #return self.RAM[addr>>13, addr&0x1FFF]
    def OP6502W(self,addr):
        return self.RD6502W(addr)
        #return self.RAM[addr>>13, addr&0x1FFF] + (self.PRGRAM[addr>>13,(addr&0x1FFF)+1]<<8)
    

        #"DF: reordered the the elif opcode =='s. Made address long (was variant)."
    
      

    def reset6502(self):
        self.A = 0; self.X = 0; self.Y = 0; self.P = Z_FLAG|R_FLAG;#0x22
        self.S = 0xFF
        self.PC = self.RD6502W(RES_VECTOR) #0xFFFC
        self.INT_pending = 0



    def RD6502W(self,addr):
        return self.RD6502(addr) + (self.RD6502(addr + 1) << 8)

    
    def RD6502(self, address):
        bank = address >> 13
        value = 0
        #if bank == 0 or bank >= 0x04: #in (0x00,0x04,0x05,0x06,0x07):  
            #return self.RAM.Read(address)
        if bank == 0x00:                        # 0x0 - 0x1FFF:
            return self.RAM[0, address & 0x7FF]
        elif bank > 0x03:                       # 0x8000 - 0xFFFF
            return self.RAM[bank, address & 0x1FFF]
        
        elif bank == 0x01: 
            return self.PPU.Read(address)

        elif (address >=0x4000 and address <=0x4013) or address == 0x4015:
            return self.Sound[address - 0x4000]
            #return self.APU.Sound[address - 0x4000]
        
        elif address in (0x4016,0x4017): #"Read PAD"
            return self.JOYPAD.Read(address) | 0x40

            
        elif bank == 0x03: #0x6000 - 0x7FFF:
            return self.MAPPER.ReadLow(address)
            
        return 0  


    def WR6502(self,address,value):
        bank = address >> 13
        addr2 = address >> 15
        if bank == 0x00:
            'Address >=0x0 and Address <=0x1FFF:'
            self.bank0[address & 0x7FF] = value
            #self.RAM[0][address & 0x7FF] = value
            #RamWrite(address,value,self.PRGRAM)
            
        elif bank == 0x01:# or address == 0x4014:
            '$2000-$3FFF'
            #print "PPU Write" ,Address
            if( address == 2000 and (value & 0x80) and (not (self.PPU.reg.reg[0] & 0x80)) and (self.PPU.reg.reg[2] & 0x80) ):
                #if self.MAPPER.Mapper != 69:
                    #self.emul_cycles += self.EXEC6502(1)
                    #self.exec_opcode()
                #self.emul_cycles += self.EXEC6502(1)
                self.NMI()
            self.PPU.Write(address,value)

            
        elif bank == 0x02:# and address != 0x4014:
            '$4000-$5FFF'
            if address < 0x4100:
                self.WriteReg(address,value)
        
        elif bank == 0x03:#Address >= 0x6000 and Address <= 0x7FFF:
            return self.MAPPER.WriteLow(address, value)

        elif bank >= 0x04: #Address >=0x8000 and Address <=0xFFFF:
            self.MapperWrite(address, value)
            

                    
        else:
            pass
            #print hex(Address)
            #print "Write HARD bRK"

            
    def WriteReg(self,address,value):
        addr = address & 0xFF
        if addr == 0x15:
            self.Sound[0x15] = value

        elif addr <= 0x13:
            self.Sound[addr] = value
            n = addr >> 2
            if n < 4 :
                self.ChannelWrite[n] = 1
                      
            #self.APU.Write(addr,value)
                
        elif addr == 0x14:

            self.PPU.Write(address,value)

            self.DMA(514) #unsupport????why
            
        elif addr in (0x16,0x17):

            self.JOYPAD.Write(addr,value)

        else:
            pass

    
    def MapperWrite(self,address, value):
        #print "MapperWrite"
        self.MAPPER.Write(address, value)
        #    exsound_enable =  self.MAPPER.Write(Address, value)
                
        #    if exsound_enable:
        #        self.APU.ExWrite(Address, value)
                    

    

    def exec_opcode(self):
        self.opcode = self.OP6502(self.PC);
        self.PC += 1
        opcode = self.opcode

        if opcode ==	0x69: # ADC #$??
            self.MR_IM(); self.ADC();
            self.ADD_CYCLE(2);
        elif opcode ==	0x65: # ADC $??
            self.MR_ZP(); self.ADC();
            self.ADD_CYCLE(3);
        elif opcode ==	0x75: # ADC $??,X
            self.MR_ZX(); self.ADC()
            self.ADD_CYCLE(4);
        elif opcode ==	0x6D: # ADC $????
            self.MR_AB(); self.ADC();
            self.ADD_CYCLE(4);
        elif opcode ==	0x7D: # ADC $????,X
            self.MR_AX(); self.ADC(); self.CHECK_EA();
            self.ADD_CYCLE(4);
        elif opcode ==	0x79: # ADC $????,Y
            self.MR_AY(); self.ADC(); self.CHECK_EA();
            self.ADD_CYCLE(4);
        elif opcode ==	0x61: # ADC ($??,X)
            self.MR_IX(); self.ADC();
            self.ADD_CYCLE(6);
        elif opcode ==	0x71: # ADC ($??),Y
            self.MR_IY(); self.ADC(); self.CHECK_EA();
            self.ADD_CYCLE(4);
        elif opcode ==	0xE9: # SBC #$??
            self.MR_IM(); self.SBC();
            self.ADD_CYCLE(2);
        elif opcode ==	0xE5: # SBC $??
            self.MR_ZP(); self.SBC();
            self.ADD_CYCLE(3);
            
        elif opcode ==	0xF5: # SBC $??,X
            self.MR_ZX(); self.SBC();
            self.ADD_CYCLE(4);
            
        elif opcode ==	0xED: # SBC $????
            self.MR_AB(); self.SBC();
            self.ADD_CYCLE(4);
            
        elif opcode ==	0xFD: # SBC $????,X
            self.MR_AX(); self.SBC(); self.CHECK_EA();
            self.ADD_CYCLE(4);
            
        elif opcode ==	0xF9: # SBC $????,Y
            self.MR_AY(); self.SBC(); self.CHECK_EA();
            self.ADD_CYCLE(4);
            
        elif opcode ==	0xE1: # SBC ($??,X)
            self.MR_IX(); self.SBC();
            self.ADD_CYCLE(6);
            
        elif opcode ==	0xF1: # SBC ($??),Y
            self.MR_IY(); self.SBC(); self.CHECK_EA();
            self.ADD_CYCLE(5);

        elif opcode ==	0xC6: # DEC $??
            self.MR_ZP(); self.DEC();	self.MW_ZP();
            self.ADD_CYCLE(5);
            
        elif opcode ==	0xD6: # DEC $??,X
            self.MR_ZX(); self.DEC(); self.MW_ZP();
            self.ADD_CYCLE(6);
            
        elif opcode ==	0xCE: # DEC $????
            self.MR_AB(); self.DEC(); self.MW_EA();
            self.ADD_CYCLE(6);
            
        elif opcode ==	0xDE: # DEC $????,X
            self.MR_AX(); self.DEC();self.MW_EA();
            self.ADD_CYCLE(7);
            

        elif opcode ==	0xCA: # DEX
            self.DEX();
            self.ADD_CYCLE(2);
            
        elif opcode ==	0x88: # DEY
            self.DEY();
            self.ADD_CYCLE(2);
            

        elif opcode ==	0xE6: # INC $??
            self.MR_ZP(); self.INC(); self.MW_ZP();
            self.ADD_CYCLE(5);
            
        elif opcode ==	0xF6: # INC $??,X
            self.MR_ZX(); self.INC(); self.MW_ZP();
            self.ADD_CYCLE(6);
            
        elif opcode ==	0xEE: # INC $????
            self.MR_AB(); self.INC(); self.MW_EA();
            self.ADD_CYCLE(6);
            
        elif opcode ==	0xFE: # INC $????,X
            self.MR_AX(); self.INC(); self.MW_EA();
            self.ADD_CYCLE(7);
            

        elif opcode ==	0xE8: # INX
            self.INX();
            self.ADD_CYCLE(2);
            
        elif opcode ==	0xC8: # INY
            self.INY();
            self.ADD_CYCLE(2);
            

        elif opcode ==	0x29: # AND #$??
            self.MR_IM(); self.AND();
            self.ADD_CYCLE(2);
            
        elif opcode ==	0x25: # AND $??
            self.MR_ZP(); self.AND();
            self.ADD_CYCLE(3);
            
        elif opcode ==	0x35: # AND $??,X
            self.MR_ZX(); self.AND();
            self.ADD_CYCLE(4);
            
        elif opcode ==	0x2D: # AND $????
            self.MR_AB(); self.AND();
            self.ADD_CYCLE(4);
            
        elif opcode ==	0x3D: # AND $????,X
            self.MR_AX(); self.AND(); self.CHECK_EA();
            self.ADD_CYCLE(4);
            
        elif opcode ==	0x39: # AND $????,Y
            self.MR_AY(); self.AND(); self.CHECK_EA();
            self.ADD_CYCLE(4);
            
        elif opcode ==	0x21: # AND ($??,X)
            self.MR_IX(); self.AND();
            self.ADD_CYCLE(6);
            
        elif opcode ==	0x31: # AND ($??),Y
            self.MR_IY(); self.AND(); self.CHECK_EA();
            self.ADD_CYCLE(5);
            

        elif opcode ==	0x0A: # ASL A
            self.ASL_A();
            self.ADD_CYCLE(2);
            
        elif opcode ==	0x06: # ASL $??
            self.MR_ZP(); self.ASL(); self.MW_ZP();
            self.ADD_CYCLE(5);
            
        elif opcode ==	0x16: # ASL $??,X
            self.MR_ZX(); self.ASL(); self.MW_ZP();
            self.ADD_CYCLE(6);
            
        elif opcode ==	0x0E: # ASL $????
            self.MR_AB(); self.ASL(); self.MW_EA();
            self.ADD_CYCLE(6);
            
        elif opcode ==	0x1E: # ASL $????,X
            self.MR_AX(); self.ASL(); self.MW_EA();
            self.ADD_CYCLE(7);
            

        elif opcode ==	0x24: # BIT $??
            self.MR_ZP(); self.BIT();
            self.ADD_CYCLE(3);
            
        elif opcode ==	0x2C: # BIT $????
            self.MR_AB(); self.BIT();
            self.ADD_CYCLE(4);
            

        elif opcode ==	0x49: # EOR #$??
            self.MR_IM(); self.EOR();
            self.ADD_CYCLE(2);
            
        elif opcode ==	0x45: # EOR $??
            self.MR_ZP(); self.EOR();
            self.ADD_CYCLE(3);
            
        elif opcode ==	0x55: # EOR $??,X
            self.MR_ZX(); self.EOR();
            self.ADD_CYCLE(4);
            
        elif opcode ==	0x4D: # EOR $????
            self.MR_AB(); self.EOR();
            self.ADD_CYCLE(4);
            
        elif opcode ==	0x5D: # EOR $????,X
            self.MR_AX(); self.EOR(); self.CHECK_EA();
            self.ADD_CYCLE(4);
            
        elif opcode ==	0x59: # EOR $????,Y
            self.MR_AY(); self.EOR(); self.CHECK_EA();
            self.ADD_CYCLE(4);
            
        elif opcode ==	0x41: # EOR ($??,X)
            self.MR_IX(); self.EOR();
            self.ADD_CYCLE(6);
            
        elif opcode ==	0x51: # EOR ($??),Y
            self.MR_IY(); self.EOR(); self.CHECK_EA();
            self.ADD_CYCLE(5);
            

        elif opcode ==	0x4A: # LSR A
            self.LSR_A();
            self.ADD_CYCLE(2);
            
        elif opcode ==	0x46: # LSR $??
            self.MR_ZP(); self.LSR(); self.MW_ZP();
            self.ADD_CYCLE(5);
            
        elif opcode ==	0x56: # LSR $??,X
            self.MR_ZX(); self.LSR(); self.MW_ZP();
            self.ADD_CYCLE(6);
            
        elif opcode ==	0x4E: # LSR $????
            self.MR_AB(); self.LSR(); self.MW_EA();
            self.ADD_CYCLE(6);
            
        elif opcode ==	0x5E: # LSR $????,X
            self.MR_AX(); self.LSR(); self.MW_EA();
            self.ADD_CYCLE(7);
            

        elif opcode ==	0x09: # ORA #$??
            self.MR_IM(); self.ORA();
            self.ADD_CYCLE(2);
            
        elif opcode ==	0x05: # ORA $??
            self.MR_ZP(); self.ORA();
            self.ADD_CYCLE(3);
            
        elif opcode ==	0x15: # ORA $??,X
            self.MR_ZX(); self.ORA();
            self.ADD_CYCLE(4);
            
        elif opcode ==	0x0D: # ORA $????
            self.MR_AB(); self.ORA();
            self.ADD_CYCLE(4);
            
        elif opcode ==	0x1D: # ORA $????,X
            self.MR_AX(); self.ORA(); self.CHECK_EA();
            self.ADD_CYCLE(4);
            
        elif opcode ==	0x19: # ORA $????,Y
            self.MR_AY(); self.ORA(); self.CHECK_EA();
            self.ADD_CYCLE(4);
            
        elif opcode ==	0x01: # ORA ($??,X)
            self.MR_IX(); self.ORA();
            self.ADD_CYCLE(6);
            
        elif opcode ==	0x11: # ORA ($??),Y
            self.MR_IY(); self.ORA(); self.CHECK_EA();
            self.ADD_CYCLE(5);
            

        elif opcode ==	0x2A: # ROL A
            self.ROL_A();
            self.ADD_CYCLE(2);
            
        elif opcode ==	0x26: # ROL $??
            self.MR_ZP(); self.ROL(); self.MW_ZP();
            self.ADD_CYCLE(5);
            
        elif opcode ==	0x36: # ROL $??,X
            self.MR_ZX(); self.ROL(); self.MW_ZP();
            self.ADD_CYCLE(6);
            
        elif opcode ==	0x2E: # ROL $????
            self.MR_AB(); self.ROL(); self.MW_EA();
            self.ADD_CYCLE(6);
            
        elif opcode ==	0x3E: # ROL $????,X
            self.MR_AX(); self.ROL(); self.MW_EA();
            self.ADD_CYCLE(7);
            

        elif opcode ==	0x6A: # ROR A
            self.ROR_A();
            self.ADD_CYCLE(2);
            
        elif opcode ==	0x66: # ROR $??
            self.MR_ZP(); self.ROR(); self.MW_ZP();
            self.ADD_CYCLE(5);
            
        elif opcode ==	0x76: # ROR $??,X
            self.MR_ZX(); self.ROR(); self.MW_ZP();
            self.ADD_CYCLE(6);
            
        elif opcode ==	0x6E: # ROR $????
            self.MR_AB(); self.ROR(); self.MW_EA();
            self.ADD_CYCLE(6);
            
        elif opcode ==	0x7E: # ROR $????,X
            self.MR_AX(); self.ROR(); self.MW_EA();
            self.ADD_CYCLE(7);
            

        elif opcode ==	0xA9: # LDA #$??
            self.MR_IM(); self.LDA();
            self.ADD_CYCLE(2);
            
        elif opcode ==	0xA5: # LDA $??
            self.MR_ZP(); self.LDA();
            self.ADD_CYCLE(3);
            
        elif opcode ==	0xB5: # LDA $??,X
            self.MR_ZX(); self.LDA();
            self.ADD_CYCLE(4);
            
        elif opcode ==	0xAD: # LDA $????
            self.MR_AB(); self.LDA();
            self.ADD_CYCLE(4);
            
        elif opcode ==	0xBD: # LDA $????,X
            self.MR_AX(); self.LDA(); self.CHECK_EA();
            self.ADD_CYCLE(4);
            
        elif opcode ==	0xB9: # LDA $????,Y
            self.MR_AY(); self.LDA(); self.CHECK_EA();
            self.ADD_CYCLE(4);
            
        elif opcode ==	0xA1: # LDA ($??,X)
            self.MR_IX(); self.LDA();
            self.ADD_CYCLE(6);
            
        elif opcode ==	0xB1: # LDA ($??),Y
            self.MR_IY(); self.LDA(); self.CHECK_EA();
            self.ADD_CYCLE(5);
            

        elif opcode ==	0xA2: # LDX #$??
            self.MR_IM(); self.LDX();
            self.ADD_CYCLE(2);
            
        elif opcode ==	0xA6: # LDX $??
            self.MR_ZP(); self.LDX();
            self.ADD_CYCLE(3);
            
        elif opcode ==	0xB6: # LDX $??,Y
            self.MR_ZY(); self.LDX();
            self.ADD_CYCLE(4);
            
        elif opcode ==	0xAE: # LDX $????
            self.MR_AB(); self.LDX();
            self.ADD_CYCLE(4);
            
        elif opcode ==	0xBE: # LDX $????,Y
            self.MR_AY(); self.LDX(); self.CHECK_EA();
            self.ADD_CYCLE(4);
            

        elif opcode ==	0xA0: # LDY #$??
            self.MR_IM(); self.LDY();
            self.ADD_CYCLE(2);
            
        elif opcode ==	0xA4: # LDY $??
            self.MR_ZP(); self.LDY();
            self.ADD_CYCLE(3);
            
        elif opcode ==	0xB4: # LDY $??,X
            self.MR_ZX(); self.LDY();
            self.ADD_CYCLE(4);
            
        elif opcode ==	0xAC: # LDY $????
            self.MR_AB(); self.LDY();
            self.ADD_CYCLE(4);
            
        elif opcode ==	0xBC: # LDY $????,X
            self.MR_AX(); self.LDY(); self.CHECK_EA();
            self.ADD_CYCLE(4);
            

        elif opcode ==	0x85: # STA $??
            self.EA_ZP(); self.STA(); self.MW_ZP();
            self.ADD_CYCLE(3);
            
        elif opcode ==	0x95: # STA $??,X
            self.EA_ZX(); self.STA(); self.MW_ZP();
            self.ADD_CYCLE(4);
            
        elif opcode ==	0x8D: # STA $????
            self.EA_AB(); self.STA(); self.MW_EA();
            self.ADD_CYCLE(4);
            
        elif opcode ==	0x9D: # STA $????,X
            self.EA_AX(); self.STA(); self.MW_EA();
            self.ADD_CYCLE(5);
            
        elif opcode ==	0x99: # STA $????,Y
            self.EA_AY(); self.STA(); self.MW_EA();
            self.ADD_CYCLE(5);
            
        elif opcode ==	0x81: # STA ($??,X)
            self.EA_IX(); self.STA(); self.MW_EA();
            self.ADD_CYCLE(6);
            
        elif opcode ==	0x91: # STA ($??),Y
            self.EA_IY(); self.STA(); self.MW_EA();
            self.ADD_CYCLE(6);
            

        elif opcode ==	0x86: # STX $??
            self.EA_ZP(); self.STX(); self.MW_ZP();
            self.ADD_CYCLE(3);
            
        elif opcode ==	0x96: # STX $??,Y
            self.EA_ZY(); self.STX(); self.MW_ZP();
            self.ADD_CYCLE(4);
            
        elif opcode ==	0x8E: # STX $????
            self.EA_AB(); self.STX(); self.MW_EA();
            self.ADD_CYCLE(4);
            

        elif opcode ==	0x84: # STY $??
            self.EA_ZP(); self.STY(); self.MW_ZP();
            self.ADD_CYCLE(3);
            
        elif opcode ==	0x94: # STY $??,X
            self.EA_ZX(); self.STY(); self.MW_ZP();
            self.ADD_CYCLE(4);
            
        elif opcode ==	0x8C: # STY $????
            self.EA_AB(); self.STY(); self.MW_EA();
            self.ADD_CYCLE(4);
            

        elif opcode ==	0xAA: # TAX
            self.TAX();
            self.ADD_CYCLE(2);
            
        elif opcode ==	0x8A: # TXA
            self.TXA();
            self.ADD_CYCLE(2);
            
        elif opcode ==	0xA8: # TAY
            self.TAY();
            self.ADD_CYCLE(2);
            
        elif opcode ==	0x98: # TYA
            self.TYA();
            self.ADD_CYCLE(2);
            
        elif opcode ==	0xBA: # TSX
            self.TSX();
            self.ADD_CYCLE(2);
            
        elif opcode ==	0x9A: # TXS
            self.TXS();
            self.ADD_CYCLE(2);
            

        elif opcode ==	0xC9: # CMP #$??
            self.MR_IM(); self.CMP();
            self.ADD_CYCLE(2);
            
        elif opcode ==	0xC5: # CMP $??
            self.MR_ZP(); self.CMP();
            self.ADD_CYCLE(3);
            
        elif opcode ==	0xD5: # CMP $??,X
            self.MR_ZX(); self.CMP();
            self.ADD_CYCLE(4);
            
        elif opcode ==	0xCD: # CMP $????
            self.MR_AB(); self.CMP();
            self.ADD_CYCLE(4);
            
        elif opcode ==	0xDD: # CMP $????,X
            self.MR_AX(); self.CMP(); self.CHECK_EA();
            self.ADD_CYCLE(4);
            
        elif opcode ==	0xD9: # CMP $????,Y
            self.MR_AY(); self.CMP(); self.CHECK_EA();
            self.ADD_CYCLE(4);
            
        elif opcode ==	0xC1: # CMP ($??,X)
            self.MR_IX(); self.CMP();
            self.ADD_CYCLE(6);
            
        elif opcode ==	0xD1: # CMP ($??),Y
            self.MR_IY(); self.CMP(); self.CHECK_EA();
            self.ADD_CYCLE(5);
            

        elif opcode ==	0xE0: # CPX #$??
            self.MR_IM(); self.CPX();
            self.ADD_CYCLE(2);
            
        elif opcode ==	0xE4: # CPX $??
            self.MR_ZP(); self.CPX();
            self.ADD_CYCLE(3);
            
        elif opcode ==	0xEC: # CPX $????
            self.MR_AB(); self.CPX();
            self.ADD_CYCLE(4);
            

        elif opcode ==	0xC0: # CPY #$??
            self.MR_IM(); self.CPY();
            self.ADD_CYCLE(2);
            
        elif opcode ==	0xC4: # CPY $??
            self.MR_ZP(); self.CPY();
            self.ADD_CYCLE(3);
            
        elif opcode ==	0xCC: # CPY $????
            self.MR_AB(); self.CPY();
            self.ADD_CYCLE(4);
            

        elif opcode ==	0x90: # BCC
            self.MR_IM(); self.BCC();
            self.ADD_CYCLE(2);
            
        elif opcode ==	0xB0: # BCS
            self.MR_IM(); self.BCS();
            self.ADD_CYCLE(2);
            
        elif opcode ==	0xF0: # BEQ
            self.MR_IM(); self.BEQ();
            self.ADD_CYCLE(2);
            
        elif opcode ==	0x30: # BMI
            self.MR_IM(); self.BMI();
            self.ADD_CYCLE(2);
            
        elif opcode ==	0xD0: # BNE
            self.MR_IM(); self.BNE();
            self.ADD_CYCLE(2);
            
        elif opcode ==	0x10: # BPL
            self.MR_IM(); self.BPL();
            self.ADD_CYCLE(2);
            
        elif opcode ==	0x50: # BVC
            self.MR_IM(); self.BVC();
            self.ADD_CYCLE(2);
            
        elif opcode ==	0x70: # BVS
            self.MR_IM(); self.BVS();
            self.ADD_CYCLE(2);
            

        elif opcode ==	0x4C: # JMP $????
            self.JMP();
            self.ADD_CYCLE(3);
            
        elif opcode ==	0x6C: # JMP ($????)
            self.JMP_ID();
            self.ADD_CYCLE(5);
            

        elif opcode ==	0x20: # JSR
            self.JSR();
            self.ADD_CYCLE(6);
            

        elif opcode ==	0x40: # RTI
            self.RTI();
            self.ADD_CYCLE(6);
            
        elif opcode ==	0x60: # RTS
            self.RTS();
            self.ADD_CYCLE(6);
            

        # 僼儔僌惂屼宯
        elif opcode ==	0x18: # CLC
            self.CLC();
            self.ADD_CYCLE(2);
            
        elif opcode ==	0xD8: # CLD
            self.CLD();
            self.ADD_CYCLE(2);
            
        elif opcode ==	0x58: # CLI
            self.CLI();
            self.ADD_CYCLE(2);
            
        elif opcode ==	0xB8: # CLV
            self.CLV();
            self.ADD_CYCLE(2);
            

        elif opcode ==	0x38: # SEC
            self.SEC();
            self.ADD_CYCLE(2);
            
        elif opcode ==	0xF8: # SED
            self.SED();
            self.ADD_CYCLE(2);
            
        elif opcode ==	0x78: # SEI
            self.SEI();
            self.ADD_CYCLE(2);
            

        # STACK
        elif opcode ==	0x48: # PHA
            self.PUSH( self.A );
            self.ADD_CYCLE(3);
            
        elif opcode ==	0x08: # PHP
            self.PUSH( self.P | B_FLAG );
            self.ADD_CYCLE(3);
            
        elif opcode ==	0x68: # PLA (N-----Z-)
            self.A = self.POP();
            self.SET_ZN_FLAG(self.A); # (T_T)
            self.ADD_CYCLE(4);
            
        elif opcode ==	0x28: # PLP
            self.P = self.POP() | R_FLAG;
            self.ADD_CYCLE(4);
            

        # 偦偺懠
        elif opcode ==	0x00: # BRK
            self.BRK();
            self.ADD_CYCLE(7);
            

        elif opcode ==	0xEA: # NOP
            self.ADD_CYCLE(2);
            

        # 枹岞奐柦椷孮
        elif opcode in (0x0B,0x2B): # ANC #$??
        #elif opcode ==	0x2B: # ANC #$??
            self.MR_IM(); self.ANC();
            self.ADD_CYCLE(2);
            

        elif opcode ==	0x8B: # ANE #$??
            self.MR_IM(); self.ANE();
            self.ADD_CYCLE(2);
            

        elif opcode ==	0x6B: # ARR #$??
            self.MR_IM(); self.ARR();
            self.ADD_CYCLE(2);
            

        elif opcode ==	0x4B: # ASR #$??
            self.MR_IM(); self.ASR();
            self.ADD_CYCLE(2);
            

        elif opcode ==	0xC7: # DCP $??
            self.MR_ZP(); self.DCP(); self.MW_ZP();
            self.ADD_CYCLE(5);
            
        elif opcode ==	0xD7: # DCP $??,X
            self.MR_ZX(); self.DCP(); self.MW_ZP();
            self.ADD_CYCLE(6);
            
        elif opcode ==	0xCF: # DCP $????
            self.MR_AB(); self.DCP(); self.MW_EA();
            self.ADD_CYCLE(6);
            
        elif opcode ==	0xDF: # DCP $??,X
            self.MR_AX(); self.DCP(); self.MW_EA();
            self.ADD_CYCLE(7);
            
        elif opcode ==	0xDB: # DCP $??,X
            self.MR_AY(); self.DCP(); self.MW_EA();
            self.ADD_CYCLE(7);
            
        elif opcode ==	0xC3: # DCP ($??,X)
            self.MR_IX(); self.DCP(); self.MW_EA();
            self.ADD_CYCLE(8);
            
        elif opcode ==	0xD3: # DCP ($??),Y
            self.MR_IY(); self.DCP(); self.MW_EA();
            self.ADD_CYCLE(8);
            

        elif opcode ==	0xE7: # ISB $??
            self.MR_ZP(); self.ISB(); self.MW_ZP();
            self.ADD_CYCLE(5);
            
        elif opcode ==	0xF7: # ISB $??,X
            self.MR_ZX(); self.ISB(); self.MW_ZP();
            self.ADD_CYCLE(5);
            
        elif opcode ==	0xEF: # ISB $????
            self.MR_AB(); self.ISB(); self.MW_EA();
            self.ADD_CYCLE(5);
            
        elif opcode ==	0xFF: # ISB $????,X
            self.MR_AX(); self.ISB(); self.MW_EA();
            self.ADD_CYCLE(5);
            
        elif opcode ==	0xFB: # ISB $????,Y
            self.MR_AY(); self.ISB(); self.MW_EA();
            self.ADD_CYCLE(5);
            
        elif opcode ==	0xE3: # ISB ($??,X)
            self.MR_IX(); self.ISB(); self.MW_EA();
            self.ADD_CYCLE(5);
            
        elif opcode ==	0xF3: # ISB ($??),Y
            self.MR_IY(); self.ISB(); self.MW_EA();
            self.ADD_CYCLE(5);
            

        elif opcode ==	0xBB: # LAS $????,Y
            self.MR_AY(); self.LAS(); self.CHECK_EA();
            self.ADD_CYCLE(4);
            


        elif opcode ==	0xA7: # LAX $??
            self.MR_ZP(); self.LAX();
            self.ADD_CYCLE(3);
            
        elif opcode ==	0xB7: # LAX $??,Y
            self.MR_ZY(); self.LAX();
            self.ADD_CYCLE(4);
            
        elif opcode ==	0xAF: # LAX $????
            self.MR_AB(); self.LAX();
            self.ADD_CYCLE(4);
            
        elif opcode ==	0xBF: # LAX $????,Y
            self.MR_AY(); self.LAX(); self.CHECK_EA();
            self.ADD_CYCLE(4);
            
        elif opcode ==	0xA3: # LAX ($??,X)
            self.MR_IX(); self.LAX();
            self.ADD_CYCLE(6);
            
        elif opcode ==	0xB3: # LAX ($??),Y
            self.MR_IY(); self.LAX(); self.CHECK_EA();
            self.ADD_CYCLE(5);
            

        elif opcode ==	0xAB: # LXA #$??
            self.MR_IM(); self.LXA();
            self.ADD_CYCLE(2);
            

        elif opcode ==	0x27: # RLA $??
            self.MR_ZP(); self.RLA(); self.MW_ZP();
            self.ADD_CYCLE(5);
            
        elif opcode ==	0x37: # RLA $??,X
            self.MR_ZX(); self.RLA(); self.MW_ZP();
            self.ADD_CYCLE(6);
            
        elif opcode ==	0x2F: # RLA $????
            self.MR_AB(); self.RLA(); self.MW_EA();
            self.ADD_CYCLE(6);
            
        elif opcode ==	0x3F: # RLA $????,X
            self.MR_AX(); self.RLA(); self.MW_EA();
            self.ADD_CYCLE(7);
            
        elif opcode ==	0x3B: # RLA $????,Y
            self.MR_AY(); self.RLA(); self.MW_EA();
            self.ADD_CYCLE(7);
            
        elif opcode ==	0x23: # RLA ($??,X)
            self.MR_IX(); self.RLA(); self.MW_EA();
            self.ADD_CYCLE(8);
            
        elif opcode ==	0x33: # RLA ($??),Y
            self.MR_IY(); self.RLA(); self.MW_EA();
            self.ADD_CYCLE(8);
            

        elif opcode ==	0x67: # RRA $??
            self.MR_ZP(); self.RRA(); self.MW_ZP();
            self.ADD_CYCLE(5);
            
        elif opcode ==	0x77: # RRA $??,X
            self.MR_ZX(); self.RRA(); self.MW_ZP();
            self.ADD_CYCLE(6);
            
        elif opcode ==	0x6F: # RRA $????
            self.MR_AB(); self.RRA(); self.MW_EA();
            self.ADD_CYCLE(6);
            
        elif opcode ==	0x7F: # RRA $????,X
            self.MR_AX(); self.RRA(); self.MW_EA();
            self.ADD_CYCLE(7);
            
        elif opcode ==	0x7B: # RRA $????,Y
            self.MR_AY(); self.RRA(); self.MW_EA();
            self.ADD_CYCLE(7);
            
        elif opcode ==	0x63: # RRA ($??,X)
            self.MR_IX(); self.RRA(); self.MW_EA();
            self.ADD_CYCLE(8);
            
        elif opcode ==	0x73: # RRA ($??),Y
            self.MR_IY(); self.RRA(); self.MW_EA();
            self.ADD_CYCLE(8);
            

        elif opcode ==	0x87: # SAX $??
            self.MR_ZP(); self.SAX(); self.MW_ZP();
            self.ADD_CYCLE(3);
            
        elif opcode ==	0x97: # SAX $??,Y
            self.MR_ZY(); self.SAX(); self.MW_ZP();
            self.ADD_CYCLE(4);
            
        elif opcode ==	0x8F: # SAX $????
            self.MR_AB(); self.SAX(); self.MW_EA();
            self.ADD_CYCLE(4);
            
        elif opcode ==	0x83: # SAX ($??,X)
            self.MR_IX(); self.SAX(); self.MW_EA();
            self.ADD_CYCLE(6);
            

        elif opcode ==	0xCB: # SBX #$??
            self.MR_IM(); self.SBX();
            self.ADD_CYCLE(2);
            

        elif opcode ==	0x9F: # SHA $????,Y
            self.MR_AY(); self.SHA(); self.MW_EA();
            self.ADD_CYCLE(5);
            
        elif opcode ==	0x93: # SHA ($??),Y
            self.MR_IY(); self.SHA(); self.MW_EA();
            self.ADD_CYCLE(6);
            

        elif opcode ==	0x9B: # SHS $????,Y
            self.MR_AY(); self.SHS(); self.MW_EA();
            self.ADD_CYCLE(5);
            

        elif opcode ==	0x9E: # SHX $????,Y
            self.MR_AY(); self.SHX(); self.MW_EA();
            self.ADD_CYCLE(5);
            

        elif opcode ==	0x9C: # SHY $????,X
            self.MR_AX(); self.SHY(); self.MW_EA();
            self.ADD_CYCLE(5);
            

        elif opcode ==	0x07: # SLO $??
            self.MR_ZP(); self.SLO(); self.MW_ZP();
            self.ADD_CYCLE(5);
            
        elif opcode ==	0x17: # SLO $??,X
            self.MR_ZX(); self.SLO(); self.MW_ZP();
            self.ADD_CYCLE(6);
            
        elif opcode ==	0x0F: # SLO $????
            self.MR_AB(); self.SLO(); self.MW_EA();
            self.ADD_CYCLE(6);
            
        elif opcode ==	0x1F: # SLO $????,X
            self.MR_AX(); self.SLO(); self.MW_EA();
            self.ADD_CYCLE(7);
            
        elif opcode ==	0x1B: # SLO $????,Y
            self.MR_AY(); self.SLO(); self.MW_EA();
            self.ADD_CYCLE(7);
            
        elif opcode ==	0x03: # SLO ($??,X)
            self.MR_IX(); self.SLO(); self.MW_EA();
            self.ADD_CYCLE(8);
            
        elif opcode ==	0x13: # SLO ($??),Y
            self.MR_IY(); self.SLO(); self.MW_EA();
            self.ADD_CYCLE(8);
            

        elif opcode ==	0x47: # SRE $??
            self.MR_ZP(); self.SRE(); self.MW_ZP();
            self.ADD_CYCLE(5);
            
        elif opcode ==	0x57: # SRE $??,X
            self.MR_ZX(); self.SRE(); self.MW_ZP();
            self.ADD_CYCLE(6);
            
        elif opcode ==	0x4F: # SRE $????
            self.MR_AB(); self.SRE(); self.MW_EA();
            self.ADD_CYCLE(6);
            
        elif opcode ==	0x5F: # SRE $????,X
            self.MR_AX(); self.SRE(); self.MW_EA();
            self.ADD_CYCLE(7);
            
        elif opcode ==	0x5B: # SRE $????,Y
            self.MR_AY(); self.SRE(); self.MW_EA();
            self.ADD_CYCLE(7);
            
        elif opcode ==	0x43: # SRE ($??,X)
            self.MR_IX(); self.SRE(); self.MW_EA();
            self.ADD_CYCLE(8);
            
        elif opcode ==	0x53: # SRE ($??),Y
            self.MR_IY(); self.SRE(); self.MW_EA();
            self.ADD_CYCLE(8);
            

        elif opcode ==	0xEB: # SBC #$?? (Unofficial)
            self.MR_IM(); self.SBC();
            self.ADD_CYCLE(2);
            

        #elif opcode ==	0x1A: # NOP (Unofficial)
        #elif opcode ==	0x3A: # NOP (Unofficial)
        #elif opcode ==	0x5A: # NOP (Unofficial)
        #elif opcode ==	0x7A: # NOP (Unofficial)
        #elif opcode ==	0xDA: # NOP (Unofficial)
        #elif opcode ==	0xFA: # NOP (Unofficial)
        elif opcode in (0x1A,0x3A,0x5A,0x7A,0xDA,0xFA): 
                self.ADD_CYCLE(2);
            
        #elif opcode ==	0x80: # DOP (CYCLES 2)
        #elif opcode ==	0x82: # DOP (CYCLES 2)
        #elif opcode ==	0x89: # DOP (CYCLES 2)
        #elif opcode ==	0xC2: # DOP (CYCLES 2)
        #elif opcode ==	0xE2: # DOP (CYCLES 2)
        elif opcode in (0x80,0x82,0x89,0xC2,0xE2): 
            self.PC += 1
            self.ADD_CYCLE(2)
            
        #elif opcode ==	0x04: # DOP (CYCLES 3)
        #elif opcode ==	0x44: # DOP (CYCLES 3)
        #elif opcode ==	0x64: # DOP (CYCLES 3)
        elif opcode in (0x04,0x44,0x64): 
            self.PC += 1
            self.ADD_CYCLE(3);
            
        #elif opcode ==	0x14: # DOP (CYCLES 4)
        #elif opcode ==	0x34: # DOP (CYCLES 4)
        #elif opcode ==	0x54: # DOP (CYCLES 4)
        #elif opcode ==	0x74: # DOP (CYCLES 4)
        #elif opcode ==	0xD4: # DOP (CYCLES 4)
        #elif opcode ==	0xF4: # DOP (CYCLES 4)
        elif opcode in (0x14,0x34,0x54,0x74,0xD4,0xF4): 
            self.PC += 1
            self.ADD_CYCLE(4);
            
        #elif opcode ==	0x0C: # TOP
        #elif opcode ==	0x1C: # TOP
        #elif opcode ==	0x3C: # TOP
        #elif opcode ==	0x5C: # TOP
        #elif opcode ==	0x7C: # TOP
        #elif opcode ==	0xDC: # TOP
        #elif opcode ==	0xFC: # TOP
        elif opcode in (0x0C,0x1C,0x3C,0x5C,0x7C,0xDC,0xFC): 
            self.PC += 2;
            self.ADD_CYCLE(4);
            
            
        #elif opcode ==	0x02:  /* JAM */
        #elif opcode ==	0x12:  /* JAM */
        #elif opcode ==	0x22:  /* JAM */
        #elif opcode ==	0x32:  /* JAM */
        #elif opcode ==	0x42:  /* JAM */
        #elif opcode ==	0x52:  /* JAM */
        #elif opcode ==	0x62:  /* JAM */
        #elif opcode ==	0x72:  /* JAM */
        #elif opcode ==	0x92:  /* JAM */
        #elif opcode ==	0xB2:  /* JAM */
        #elif opcode ==	0xD2:  /* JAM */
        #elif opcode ==	0xF2:  /* JAM */ 
        elif opcode in (0x02,0x12,0x22,0x32,0x42,0x52,0x62,0x72,0x92,0xB2,0xD2,0xF2): 
            self.PC -= 1;
            self.ADD_CYCLE(4);
        
def import_CPU_class(addition_spec, jit = True):
    return jitObject(CPU6502, cpu_spec, addition_spec, jit = jit)

def load_CPU(consloe, addition_spec,jit = True):
    cpu_class, cpu_type = import_CPU_class(addition_spec,jit = jit)
    cpu = cpu_class(MAPPER = consloe.MAPPER,
                        MMU = consloe.MMU,
                        PPU = consloe.PPU,
                        ChannelWrite = consloe.APU.ChannelWrite)#, #consloe.APU,)
    return cpu, cpu_type

if __name__ == '__main__':
    #cpu_ram = Memory()
    
    #cpu6502 = jitObject(cpu6502, cpu_spec)
    
    cpu = CPU6502(MAPPER = MAPPER())
    print(cpu.CpuClock)
    
        










        
