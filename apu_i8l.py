# -*- coding: UTF-8 -*-

import time

import numpy as np
import numba as nb
from numba import jit
from numba.experimental import jitclass
from numba import uint8,uint16,uint32,int8,int32,float32

@jitclass
class RECTANGLE:
    no:uint8
    
    reg:uint8[:]
    enable:uint8
    holdnote:uint8
    volume:uint8
    complement:uint8

    'for render'
    phaseacc:uint32
    freq:uint32
    freqlimit:uint32
    adder:uint32
    duty:uint32
    len_count:uint32

    nowvolume:uint32

    'for envelope'
    env_fixed:uint8
    env_decay:uint8
    env_count:uint8
    dummy0:uint8
    env_vol:uint32

    'for sweep'
    swp_on:uint8
    swp_inc:uint8
    swp_shift:uint8
    swp_decay:uint8
    swp_count:uint8
    dummy1:uint8[:]

    'for sync'
    sync_reg:uint8[:]
    sync_outpu_enable:uint8
    sync_enable:uint8
    sync_holdnote:uint8
    dummy2:uint8
    sync_len_count:uint32
    
    def __init__(rect,MMU,no):
        rect.no = no
        rect.reg = MMU.RAM[2][no * 4: no * 4 + 0x4]
        rect.enable = 0
        rect.holdnote = 0
        rect.volume = 0
        rect.complement = 0

        'for render'
        rect.phaseacc = 0
        rect.freq = 0
        rect.freqlimit = 0
        rect.adder = 0
        rect.duty = 0
        rect.len_count = 0

        rect.nowvolume = 0

        'for envelope'
        rect.env_fixed = 0
        rect.env_decay = 0
        rect.env_count = 0
        rect.dummy0 = 0
        rect.env_vol = 0

        'for sweep'
        rect.swp_on = 0
        rect.swp_inc = 0
        rect.swp_shift = 0
        rect.swp_decay = 0
        rect.swp_count = 0
        rect.dummy1 = np.zeros(3,np.uint8)

        'for sync'
        rect.sync_reg = np.zeros(4,np.uint8)
        rect.sync_outpu_enable = 0
        rect.sync_enable = 0
        rect.sync_holdnote = 0
        rect.dummy2 = 0
        rect.sync_len_count = 0

    @property
    def Sound(self):
        return 0

@jitclass
class TRIANGLE:
    no:uint8
    reg:uint8[:]
    
    enable:uint8
    holdnote:uint8
    counter_start:uint8
    dummy0:uint8

    'for render'
    phaseacc:uint32
    freq:uint32
    lin_count:uint32
    len_count:uint32
    adder:uint32
    
    nowvolume:uint32


    'for sync'
    sync_reg:uint8[:]
    sync_enable:uint8
    sync_holdnote:uint8
    sync_counter_start:uint8
    
    sync_len_count:uint32
    sync_lin_count:uint32
    
    def __init__(tri,MMU):
        tri.no = 2
        tri.reg = MMU.RAM[2][0x8: 0xC]
        
        tri.enable = 0
        tri.holdnote = 0
        tri.counter_start = 0
        tri.dummy0 = 0
        
        'for render'
        tri.phaseacc = 0
        tri.freq = 0
        tri.len_count = 0
        tri.lin_count = 0
        tri.adder = 0

        tri.nowvolume = 0

        'for sync'
        tri.sync_reg = np.zeros(4,np.uint8)
        tri.sync_counter_start = 0
        tri.sync_enable = 0
        tri.sync_holdnote = 0
        
        tri.sync_len_count = 0
        tri.sync_lin_count = 0

@jitclass
class NOISE:
    no:uint8
    reg:uint8[:]
    
    enable:uint8
    holdnote:uint8
    volume:uint8
    xor_tap:uint8
    shift_reg:uint32

    'for render'
    phaseacc:uint32
    freq:uint32
    len_count:uint32

    nowvolume:uint32
    output:uint32

    'for envelope'
    env_fixed:uint8
    env_decay:uint8
    env_count:uint8
    dummy0:uint8
    env_vol:uint32

    'for sync'
    sync_reg:uint8[:]
    sync_outpu_enable:uint8
    sync_enable:uint8
    sync_holdnote:uint8
    dummy1:uint8
    sync_len_count:uint32
    
    def __init__(noise,MMU):
        noise.no = 3
        noise.reg = MMU.RAM[2][0x11: 0x14]
        
        noise.enable = 0
        noise.holdnote = 0
        noise.volume = 0
        noise.xor_tap = 0
        noise.shift_reg = 0

        'for render'
        noise.phaseacc = 0
        noise.freq = 0
        noise.len_count = 0

        noise.nowvolume = 0
        noise.output = 0

        'for envelope'
        noise.env_fixed = 0
        noise.env_decay = 0
        noise.env_count = 0
        noise.dummy0 = 0
        noise.env_vol = 0

        'for sync'
        noise.sync_reg = np.zeros(4,np.uint8)
        noise.sync_outpu_enable = 0
        noise.sync_enable = 0
        noise.sync_holdnote = 0
        noise.dummy1 = 0
        noise.sync_len_count = 0

@jitclass
class DPCM:
    reg:uint8[:]
    
    enable:uint8
    looping:uint8
    cur_byte:uint8
    dpcm_value:uint32

    'for render'
    phaseacc:uint32
    freq:uint32
    output:uint32


    address:uint16
    cache_addr:uint16
    dmalength:uint32
    cache_dmalength:uint8
    dpcm_output_real:uint32
    dpcm_output_fake:uint32
    dpcm_output_old:uint32
    dpcm_output_offset:uint32

    'for sync'
    sync_reg:uint8[:]
    sync_enable:uint8
    sync_looping:uint8
    sync_irq_gen:uint8
    sync_irq_enable:uint8
    sync_cycles:uint32
    sync_cache_cycles:uint32
    sync_dmalength:uint32
    sync_cache_dmalength:uint32
    
    def __init__(dpcm,MMU):
        dpcm.reg = MMU.RAM[2][0xC: 0x10]
        
        dpcm.enable = 0
        dpcm.looping = 0
        dpcm.cur_byte = 0
        dpcm.dpcm_value = 0
        

        'for render'
        dpcm.phaseacc = 0
        dpcm.freq = 0
        dpcm.output = 0

        
        dpcm.address = 0
        dpcm.cache_addr = 0
        dpcm.dmalength = 0
        dpcm.cache_dmalength = 0
        dpcm.dpcm_output_real = 0
        dpcm.dpcm_output_fake = 0
        dpcm.dpcm_output_old = 0
        dpcm.dpcm_output_offset = 0

        'for sync'
        dpcm.sync_reg = np.zeros(4,np.uint8)
        dpcm.sync_enable = 0
        dpcm.sync_looping = 0
        dpcm.sync_irq_gen = 0
        dpcm.sync_irq_enable = 0
        dpcm.sync_cycles = 0
        dpcm.sync_cache_cycles = 0
        dpcm.sync_dmalength = 0
        dpcm.sync_cache_dmalength = 0

        
if __name__ == '__main__':
    pass
#print(RECTANGLE())
a='''
A-1 	07F0,
Bb1 	077C,
B-1 	0710,
C-2 	06AC,
C#2 	064C,
D-2 	05F2,
Eb2 	059E,
E-2 	054C,
F-2 	0501,
F#2 	04B8,
G-2 	0474,
Ab2 	0434,
A-2 	03F8,
Bb2 	03BE,
B-2 	0388,
C-3 	0356,
C#3 	0326,
D-3 	02F9,
Eb3 	02CF,
E-3 	02A6,
F-3 	0280,
F#3 	025C,
G-3 	023A,
Ab3 	021A,
A-3 	01FC,
Bb3 	01DF,
B-3 	01C4,
C-4 	01AB,
C#4 	0193,
D-4 	017C,
Eb4 	0167,
E-4 	0153,
F-4 	0140,
F#4 	012E,
G-4 	011D,
Ab4 	010D,
A-4 	00FE,
Bb4 	00EF,
B-4 	00E2,
C-5 	00D5,
C#5 	00C9,
D-5 	00BE,
Eb5 	00B3,
E-5 	00A9,
F-5 	00A0,
F#5 	0097,
G-5 	008E,
Ab5 	0086,
A-5 	007E,
Bb5 	0077,
B-5 	0071,
C-6 	006A,
C#6 	0064,
D-6 	005F,
Eb6 	0059,
E-6 	0054,
F-6 	0050,
F#6 	004B,
G-6 	0047,
Ab6 	0043,
A-6 	003F,
Bb6 	003B,
B-6 	0038,
C-7 	0035,
C#7 	0032,
D-7 	002F,
Eb7 	002C,
E-7 	002A,
F-7 	0028,
F#7 	0026,
G-7 	0024,
Ab7 	0022,
A-7 	0020,
Bb7 	001E,
B-7 	001C,
'''
