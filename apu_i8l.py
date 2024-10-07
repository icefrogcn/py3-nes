# -*- coding: UTF-8 -*-

import time

import numpy as np
import numba as nb
from numba import jit
from numba.experimental import jitclass
from numba import uint8,uint16,uint32,int8,int32,float32

'''
MIDI instrument list. Ripped off some website I've forgotten which

0=Acoustic Grand Piano
1=Bright Acoustic Piano
2=Electric Grand Piano
3=Honky-tonk Piano
4=Rhodes Piano
5=Chorus Piano
6=Harpsi -chord
7=Clavinet
8=Celesta
9=Glocken -spiel
10=Music Box
11=Vibra -phone
12=Marimba
13=Xylo-phone
14=Tubular Bells
15=Dulcimer
16=Hammond Organ
17=Percuss. Organ
18=Rock Organ
19=Church Organ
20=Reed Organ
21=Accordion
22=Harmonica
23=Tango Accordion
24=Acoustic Guitar (nylon)
25=Acoustic Guitar (steel)
26=Electric Guitar (jazz)
27=Electric Guitar (clean)
28=Electric Guitar (muted)
29=Overdriven Guitar
30=Distortion Guitar
31=Guitar Harmonics
32=Acoustic Bass
33=Electric Bass (finger)
34=Electric Bass (pick)
35=Fretless Bass
36=Slap Bass 1
37=Slap Bass 2
38=Synth Bass 1
39=Synth Bass 2
40=Violin
41=Viola
42=Cello
43=Contra Bass
44=Tremolo Strings
45=Pizzicato Strings
46=Orchestral Harp
47=Timpani
48=String Ensemble 1
49=String Ensemble 2
50=Synth Strings 1
51=Synth Strings 2
52=Choir Aahs
53=Voice Oohs
54=Synth Voice
55=Orchestra Hit
56=Trumpet
57=Trombone
58=Tuba
59=Muted Trumpet
60=French Horn
61=Brass Section
62=Synth Brass 1
63=Synth Brass 2
64=Soprano Sax
65=Alto Sax
66=Tenor Sax
67=Baritone Sax
68=Oboe
69=English Horn
70=Bassoon
71=Clarinet
72=Piccolo
73=Flute
74=Recorder
75=Pan Flute
76=Bottle Blow
77=Shaku
78=Whistle
79=Ocarina
80=Lead 1 (square)
81=Lead 2 (saw tooth)
82=Lead 3 (calliope lead)
83=Lead 4 (chiff lead)
84=Lead 5 (charang)
85=Lead 6 (voice)
86=Lead 7 (fifths)
87=Lead 8 (bass + lead)
88=Pad 1 (new age)
89=Pad 2 (warm)
90=Pad 3 (poly synth)
91=Pad 4 (choir)
92=Pad 5 (bowed)
93=Pad 6 (metallic)
94=Pad 7 (halo)
95=Pad 8 (sweep)
96=FX 1 (rain)
97=FX 2 (sound track)
98=FX 3 (crystal)
99=FX 4 (atmo - sphere)
100=FX 5 (bright)
101=FX 6 (goblins)
102=FX 7 (echoes)
103=FX 8 (sci-fi)
104=Sitar
105=Banjo
106=Shamisen
107=Koto
108=Kalimba
109=Bagpipe
110=Fiddle
111=Shanai
112=Tinkle Bell
113=Agogo
114=Steel Drums
115=Wood block
116=Taiko Drum
117=Melodic Tom
118=Synth Drum
119=Reverse Cymbal
120=Guitar Fret Noise
121=Breath Noise
122=Seashore
123=Bird Tweet
124=Telephone Ring
125=Helicopter
126=Applause
127=Gunshot
'''

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
    freq:int32
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
        rect.complement = 0xFF if no else 0x00

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
    phaseacc:int32
    freq:int32
    lin_count:int32
    len_count:int32
    adder:int32
    
    nowvolume:int32


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
    phaseacc:int32
    freq:uint32
    len_count:int32

    nowvolume:uint32
    output:int32

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
        noise.reg = MMU.RAM[2][0x0C: 0x10]
        
        noise.enable = 0
        noise.holdnote = 0
        noise.volume = 0
        noise.xor_tap = 0
        noise.shift_reg = 0x4000

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
        
    def reset(noise):
        noise.shift_reg = 0x4000

@jitclass
class DPCM:
    no: uint8
    reg:uint8[:]
    
    enable:uint8
    looping:uint8
    cur_byte:uint8
    dpcm_value:uint8

    'for render'
    phaseacc:int32
    freq:int32
    output:int32
    nowvolume:int32

    len_count:uint32
    
    address:    uint16
    cache_addr: uint16
    dmalength:          int32
    cache_dmalength:    int32
    dpcm_output_real:   int32
    dpcm_output_fake:   int32
    dpcm_output_old:    int32
    dpcm_output_offset: int32

    'for sync'
    sync_reg:uint8[:]
    sync_enable:uint8
    sync_looping:uint8
    sync_irq_gen:uint8
    sync_irq_enable:uint8
    sync_cycles:        int32
    sync_cache_cycles:  int32
    sync_dmalength:     int32
    sync_cache_dmalength:int32
    
    def __init__(dpcm,MMU):
        dpcm.no = 4
        
        dpcm.reg = MMU.RAM[2][0x10: 0x14]
        
        dpcm.enable = 0
        dpcm.looping = 0
        dpcm.cur_byte = 0
        dpcm.dpcm_value = 0
        

        'for render'
        dpcm.phaseacc = 0
        dpcm.freq = 0
        dpcm.output = 0
        dpcm.nowvolume = 0

        dpcm.len_count = 0
        
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

    @property
    def holdnote(dpcm):
        return dpcm.looping
        
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
