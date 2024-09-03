# -*- coding: UTF-8 -*-

import time
import rtmidi
import math
import numpy as np
import numba as nb
from numba import jit
from numba.experimental import jitclass
from numba import uint8,uint16,uint32,int8,int32,float32
from numba.typed import List,Dict
from numba.types import ListType,DictType,unicode_type
from numba import types

from midiconstants import *
from apu_i8l import RECTANGLE,TRIANGLE,NOISE,DPCM
from mmu import MMU

# Volume adjust
# Internal sounds
RECTANGLE_VOL	=0x0F0
TRIANGLE_VOL	=0x130
NOISE_VOL	=0x0C0
DPCM_VOL	=0x0F0
# Extra sounds
VRC6_VOL	=0x0F0
VRC7_VOL	=0x130
FDS_VOL		=0x0F0
MMC5_VOL	=0x0F0
N106_VOL	=0x088
FME7_VOL	=0x130

SMF_EVENT_CONTROL =0xB0

'Dummy'
APU_CLOCK = 1789772.5
nRate	= 22050
cycle_rate = int((APU_CLOCK * 65536)/nRate)

' Volume shift'
RECTANGLE_VOL_SHIFT=8
TRIANGLE_VOL_SHIFT=9
NOISE_VOL_SHIFT=8
DPCM_VOL_SHIFT=8
'''
	//  0:Master
	//  1:Rectangle 1
	//  2:Rectangle 2
	//  3:Triangle
	//  4:Noise
	//  5:DPCM
	//  6:VRC6
	//  7:VRC7
	//  8:FDS
	//  9:MMC5
	// 10:N106
	// 11:FME7
'''
nVolumeChannel = 0x10

'Lookup table used by nester.'
#fillArray vlengths, 
vbl_lengths = np.array([ 5, 127,  10,   1,  19,   2,  40,  3,
                        80,   4,  30,   5,   7,   6,  13,  7,
                         6,   8,  12,   9,  24,  10,  48, 11,
                        96,  12,  36,  13,   8,  14,  16, 15],np.uint8)

freq_limit = np.array([0x03FF, 0x0555, 0x0666, 0x071C, 0x0787, 0x07C1, 0x07E0, 0x07F0], np.uint16)

duty_lut = np.array([2,  4,  8, 12], np.uint8)

noise_freq = np.array([4, 8, 16, 32, 64, 96, 128, 160, 202, 254, 380, 508, 762, 1016, 2034, 4068], np.uint16)

'DF: powers of 2'
pow2 = np.array([2**i for i in range(31)] + [-2147483648],np.int32) #*(31) 

dpcm_cycles = np.array([
	428, 380, 340, 320, 286, 254, 226, 214,
	190, 160, 142, 128, 106,  85,  72,  54],np.uint16)

pulse_tone = np.zeros(0x800,np.uint16)
t21to95 = ['0x07F0', '0x077C', '0x0710', '0x06AC', '0x064C', '0x05F2', '0x059E', '0x054C', '0x0501', '0x04B8', '0x0474', '0x0434', '0x03F8', '0x03BE', '0x0388', '0x0356', '0x0326', '0x02F9', '0x02CF', '0x02A6', '0x0280', '0x025C', '0x023A', '0x021A', '0x01FC', '0x01DF', '0x01C4', '0x01AB', '0x0193', '0x017C', '0x0167', '0x0153', '0x0140', '0x012E', '0x011D', '0x010D', '0x00FE', '0x00EF', '0x00E2', '0x00D5', '0x00C9', '0x00BE', '0x00B3', '0x00A9', '0x00A0', '0x0097', '0x008E', '0x0086', '0x007E', '0x0077', '0x0071', '0x006A', '0x0064', '0x005F', '0x0059', '0x0054', '0x0050', '0x004B', '0x0047', '0x0043', '0x003F', '0x003B', '0x0038', '0x0035', '0x0032', '0x002F', '0x002C', '0x002A', '0x0028', '0x0026', '0x0024', '0x0022', '0x0020', '0x001E', '0x001C']
for t,freq in enumerate(t21to95):
    pulse_tone[eval(freq)] = t + 21
@jitclass()
class APU(object):
    MMU:MMU
    ch0:RECTANGLE
    ch1:RECTANGLE
    ch2:TRIANGLE
    ch3:NOISE
    ch4:DPCM
    tones:float32[:]
    volume:uint16[:]
    lastFrame:uint16[:]
    stopTones:uint8[:]

    ChannelStatus:uint8[:]
    ChannelUpdate:uint8[:]
    
    notes_on:uint8[:,::1]
    notes_off:uint8[:,::1]

    Frames:uint32

    doSound:uint8

    vlengths:uint8[:]
    freq_limit:uint16[:]
    duty_lut:uint16[:]
    noise_freq:uint16[:]
    
    pow2:int32[:]

    
    def __init__(self,MMU = MMU()):
        self.MMU = MMU
        self.ch0 = RECTANGLE(self.MMU, 0)
        self.ch1 = RECTANGLE(self.MMU, 1)
        self.ch2 = TRIANGLE(self.MMU)
        self.ch3 = NOISE(self.MMU)
        self.ch4 = DPCM(self.MMU)
        
        self.tones = np.zeros(nVolumeChannel,np.float32)
        self.volume = np.zeros(nVolumeChannel,np.uint16)

        self.lastFrame = np.zeros(nVolumeChannel,np.uint16)
        self.stopTones = np.zeros(nVolumeChannel,np.uint8)

        self.ChannelStatus = np.zeros(nVolumeChannel,np.uint8)
        self.ChannelUpdate = np.zeros(nVolumeChannel,np.uint8)

        self.notes_on = np.zeros((nVolumeChannel,4),np.uint8)
        self.notes_off = np.zeros((nVolumeChannel,4),np.uint8)
        
        self.Frames = 0

        self.doSound = 1

        



    @property
    def Sound(self):
        return self.MMU.RAM[2][0:0x100]
    @property
    def ChannelWrite(self):
        return self.MMU.ChannelWrite
                
    #@property
    def SoundCtrl(self,ch):
        return self.Sound[0x15] & (1 << ch)
    
    @property
    def Reg4015(self):
        temp = self.MMU.SoundWrite[0x15]
        self.MMU.SoundWrite[0x15] = 0
        return temp


    def SoundChannel_ZERO(self,ch):
        self.SoundChannel[ch] = 0
    def SoundChannel_ONE(self,ch):
        self.SoundChannel[ch] = 1

    def frameBuffer_decrement(self,ch):
        self.frameBuffer[ch] -= 1

    def set_FRAMES(self,frame):
        self.Frames  = frame

    def updateReg4015(self):
        if self.Reg4015 == 0:
            return
        if(not(self.SoundCtrl(0)) ):
            self.ch0.enable    = 0
            self.ch0.len_count = 0
        if(not(self.SoundCtrl(1)) ):
            self.ch1.enable    = 0
            self.ch1.len_count = 0
        if(not(self.SoundCtrl(2)) ):
            self.ch2.enable    = 0
            self.ch2.len_count = 0
            self.ch2.lin_count = 0
            self.ch2.counter_start = 0
        if(not(self.SoundCtrl(3)) ):
            self.ch3.enable    = 0
            self.ch3.len_count = 0
        if(not(self.SoundCtrl(4)) ):
            self.ch4.enable    = 0
            self.ch4.dmalength = 0
        else:
            self.ch4.enable = 0xFF
            if( not self.ch4.dmalength ):
                self.ch4.address   = self.ch4.cache_addr
                self.ch4.dmalength = self.ch4.cache_dmalength
                self.ch4.phaseacc  = 0
    
    def updateSounds(self):
        self.ChannelStatus = self.ChannelWrite[:]
        
        #self.set_FRAMES(Frames)
        
        if self.doSound :
            #print 'playing'
            self.ReallyStopTones()
            self.updateReg4015()
            self.PlayDMC(self.ch4)
            self.PlayRect(self.ch0)
            self.PlayRect(self.ch1)
            self.PlayTriangle(self.ch2)
            self.PlayNoise(self.ch3)
            
        else:
            self.stopTone(0)
            self.stopTone(1)
            self.stopTone(2)
            self.stopTone(3)
            self.stopTone(4)
            self.ReallyStopTones()
            

    
    def playTone(self,channel, tone, v):
        if tone != self.tones[channel]  or v == 0 or v < self.volume[channel] - 3 or v > self.volume[channel]:
            if self.tones[channel] != 0:
                self.ToneOff(channel, self.tones[channel])
                self.tones[channel] = 0
                self.volume[channel] = 0
            if self.doSound and tone > 0 and tone <= 127 and v > 0 :
                self.volume[channel] = v
                self.tones[channel] = tone
                self.ToneOn(channel, tone, v * 8)

        #else:
            #self.SoundChannel[channel] = 0



    def stopTone(self,channel):
        if self.tones[channel] != 0:
            #self.ToneOff(channel, self.tones[channel])
            self.stopTones[channel] = self.tones[channel]
            self.tones[channel] = 0
            self.volume[channel] = 0
            



    def ReallyStopTones(self):
        for channel in range(nVolumeChannel):
            if self.stopTones[channel] !=0 and self.stopTones[channel] != self.tones[channel]:
                self.ToneOff(channel, self.stopTones[channel])
                self.stopTones[channel] = 0
            #self.stopTone(channel)

    def WriteRect(self,ch):
        if self.ChannelWrite[ch.no]:
            'addr 0'
            ch.holdnote     = ch.reg[0] & 0x20
            ch.env_fixed    = ch.reg[0] & 0x10
            ch.volume       = ch.reg[0] & 0x0F if ch.env_fixed else 8
            #ch.volume <<= 3
            ch.env_decay    = (ch.reg[0] & 0x0F) +1
            ch.duty         = duty_lut[ch.reg[0]>>6]

            'addr 1'
            ch.swp_on = ch.reg[1] & 0x80
            ch.swp_inc = ch.reg[1] & 0x8
            ch.swp_shift = ch.reg[1] & 0x7
            ch.swp_decay = ((ch.reg[1]>>4)&0x07)+1
            ch.swp_count = 0
            ch.freqlimit = freq_limit[ch.swp_shift]
            
            'addr 2'
            ch.freq = ch.reg[2] + (ch.freq&~0xFF)

            'addr 3'
            ch.freq = ((ch.reg[3]&0x7) << 8) + (ch.freq&0xFF)# + 1
            ch.len_count = vbl_lengths[ch.reg[3] >> 3]# * 2
            self.ChannelUpdate[ch.no] = 1

    def UpdateRect(self, ch):
        #The sweep unit continuously calculates each pulse channel's target period
        if ch.swp_on and ch.swp_shift:
            if ch.swp_count:
                ch.swp_count -= 1
            if ch.swp_count == 0:
                ch.swp_count = (ch.swp_decay + 1)//2 #The divider's period is P + 1 half-frames 
                if ch.swp_inc:
                    ch.freq -= (ch.freq >> ch.swp_shift)
                else:
                    ch.freq += (ch.freq >> ch.swp_shift)
                self.ChannelUpdate[ch.no] = 1
            
    def PlayRect(self,ch):
        self.WriteRect(ch)
        #ch.nowvolume = ch.volume
        self.UpdateRect(ch)
        self.RenderRect(ch)
        ch.len_count -= 0 if ch.holdnote else 1
        
    def RenderRect(self,ch):
        no = ch.no
        if ch.len_count == 0: 
            self.stopTone(no)
        if self.SoundCtrl(no):
            if ch.volume > 0 :
                if ch.freq > 1 :
                    if self.ChannelWrite[no] or self.ChannelUpdate[no]:
                        #Ensures that a note doesn't replay unless memory written
                        self.ChannelWrite[no] = 0
                        self.ChannelUpdate[no] = 0
                        self.playTone(no, self.getTone(ch.freq), ch.volume )
                else:
                    self.stopTone(no)
            else:
                self.stopTone(no)
        else:
            self.ChannelWrite[no] = 1
            self.stopTone(no)

    def WriteTriangle(self,ch2):
        if self.ChannelWrite[ch2.no]:
            ch2.holdnote     = ch2.reg[0] & 0x80
            'addr 2'
            #ch.freq = (ch.freq&0xFFFF00) + ch.reg[2]

            'addr 3'
            ch2.freq = (((ch2.reg[3]&0x7) << 8) + (ch2.reg[2]) + 1) << 1
            ch2.len_count = vbl_lengths[ch2.reg[3] >> 3]# * 2
            ch2.counter_start = 0x80
        
            ch2.nowvolume = 9 #'triangle'
            
    def UpdateTriangle(self, ch2):
        if ch2.counter_start:
            ch2.lin_count = ch2.reg[0] & 0x7F
        elif ch2.lin_count:
            ch2.lin_count -= 1
        if (not ch2.holdnote) and ch2.lin_count:
            ch2.counter_start = 0


    
    def PlayTriangle(self,ch2):
        self.WriteTriangle(ch2)
        self.UpdateTriangle(ch2)
        self.RenderTriangle(ch2)
        self.playfun(ch2)
        #self.playfun(2, frequency * 2, volume, length)
        ch2.len_count -= 0 if ch2.holdnote else 1
        if ch2.lin_count <= 0:
            ch2.len_count = 0

    def RenderTriangle(self,ch2):
        ch2.phaseacc -= cycle_rate
        if ch2.phaseacc >= 0:
            #ch2.nowvolume 100%
            return
        if ch2.freq > cycle_rate:
            ch2.phaseacc += ch2.freq
            ch2.adder += (ch2.adder+1)&0x1F
            if( ch2.adder < 0x10 ):
                ch2.nowvolume = (ch2.adder&0x0F)#<<TRIANGLE_VOL_SHIFT
            else:
                ch2.nowvolume = (0x0F-(ch2.adder&0x0F))#<<TRIANGLE_VOL_SHIFT
            return
        num_times = total = 0
        while( ch2.phaseacc < 0  and ch2.freq > 0):
            ch2.phaseacc += ch2.freq
            ch2.adder = (ch2.adder+1)&0x1F
            if( ch2.adder < 0x10 ):
                ch2.nowvolume = (ch2.adder&0x0F)#<<TRIANGLE_VOL_SHIFT
            else:
                ch2.nowvolume = (0x0F-(ch2.adder&0x0F))#<<TRIANGLE_VOL_SHIFT
            total += ch2.nowvolume
            num_times += 1
        ch2.nowvolume = int(total/num_times) if num_times > 0 else total
        return 
        
    def PlayNoise(self,ch3):
        #ch = self.ch3
        ch3.holdnote    = ch3.reg[0]&0x20
        ch3.volume      = ch3.reg[0]&0x0F
        ch3.env_fixed   = ch3.reg[0]&0x10
        ch3.env_decay   = (ch3.reg[0]&0x0F)+1

        ch3.freq = noise_freq[ch3.reg[2] & 0xF]
        ch3.xor_tap = 0x40 if ch3.reg[2]&0x80 else 0x02
        
        ch3.len_count = vbl_lengths[ch3.reg[3] >> 3]# * 2
        ch3.env_count = ch3.env_decay+1
                               
        ch3.nowvolume = ch3.volume #8 * 8 #'Noise'
        self.playfun(ch3)
    

    def PlayDMC(self, ch4):
        ch4.freq = APU_CLOCK // dpcm_cycles[(ch4.reg[0] & 0xF)]
        ch4.looping = ch4.reg[0]&0x40

        ch4.dpcm_value = (ch4.reg[1]&0x7F)>>1

        'Sample address = %11AAAAAA.AA000000 = $C000 + (A * 64)'
        ch4.cache_addr = 0xC000+(ch4.reg[2]<<6)

        'Sample length = %LLLL.LLLL0001 = (L * 16) + 1 bytes'
        ch4.cache_dmalength = ((ch4.reg[3]<<4)+1)#<<3

        ch4.len_count = 1
        
        self.RenderDMC(ch4)
        ch4.nowvolume = ch4.output
        
        self.playfun(ch4)

    def RenderDMC(self,ch4):
        if ch4.dmalength:
            ch4.phaseacc -= cycle_rate

            while ch4.phaseacc < 0:
                ch4.phaseacc += ch4.freq
                if( not (ch4.dmalength&7) ):
                    ch4.cur_byte = self.MMU.read( ch4.address )
                    if( 0xFFFF == ch4.address ):
                        ch4.address = 0x8000
                    else:
                        ch4.address += 1
                ch4.dmalength -= 1
                if ch4.dmalength == 0:
                    ch4.enable = 0
                    break

                if( ch4.cur_byte&(1<<((ch4.dmalength&7)^7)) ):
                    if ( ch4.dpcm_value < 0x3F ):
                        ch4.dpcm_value += 1
                else:
                    if ( ch4.dpcm_value >1 ):
                        ch4.dpcm_value -= 1
        ch4.dpcm_output_real = int((ch4.reg[1]&0x01)+ch4.dpcm_value*2)-0x40
        if( abs(ch4.dpcm_output_real-ch4.dpcm_output_fake) <= 8 ):
            ch4.dpcm_output_fake = ch4.dpcm_output_real
            ch4.output = int(ch4.dpcm_output_real)#<<DPCM_VOL_SHIFT
        else:
            if( ch4.dpcm_output_real > ch4.dpcm_output_fake ):
                ch4.dpcm_output_fake += 8
            else:
                ch4.dpcm_output_fake -= 8
            ch4.output = int(ch4.dpcm_output_fake)#<<DPCM_VOL_SHIFT
                
    def playfun(self, ch):
        no = ch.no
        if self.SoundCtrl(no)  or ch.enable:
            if ch.nowvolume > 0 :
                if ch.freq > 1 :
                    if self.ChannelWrite[no] : #Ensures that a note doesn't replay unless memory written
                        self.ChannelWrite[no] = 0
                        self.lastFrame[no] = ch.len_count #self.Frames + length
                        self.playTone(no, self.getTone(ch.freq), ch.nowvolume )
                else:
                    self.stopTone(no)
                
            else:
                self.stopTone(no)
            
        else:
            self.ChannelWrite[no] = 1
            self.stopTone(no)

        if self.lastFrame[no] == 0: #self.Frames >= self.lastFrame[ch]:
            self.stopTone(no)
        self.lastFrame[no] -= 0 if ch.holdnote else 1
        
    


    def ToneOn(self, channel, tone, volume):
        #if self.available_ports :
            if tone < 0:tone = 0 
            if tone > 255:tone = 255 
            #tone = 127 if tone > 127 else 127
            note_on = [0x90 + channel, tone, volume] # channel 1, middle C, velocity 112
            self.notes_on[channel][0] = 1
            self.notes_on[channel][1:] = note_on
            
            #midiout.send_message(note_on)


    def ToneOff(self, channel,tone):
        #if self.available_ports :
            if tone < 0:tone = 0 
            if tone > 255:tone = 255 
            #tone = 127 if tone > 127 else 127
            note_off = [0x80 + channel, tone, 0]
            self.notes_off[channel][0] = 1
            self.notes_off[channel][1:] = note_off
            
            #midiout.send_message(note_off)


    def getRectTone(self, freq): #As Long
        if freq < 8:
            return 0
        if pulse_tone[freq]:
            return pulse_tone[freq]

        f = 1789772.5/(16.0 * (freq + 1))
        t = np.log2(f/440.0) * 12.0 + 69.0
        
        if t < 0:t = 0 
        if t > 127:t = 127 

        return int(t)

    def getTone(self, freq): #As Long
        if freq < 8:
            return 0
        
        #freq = 65536 / freq
        #freq = 111861 / (freq + 1)
        f = 1789772.5/(16.0 * (freq + 1))
        t = np.log2(f/440.0) * 12.0 + 69.0
        #t = math.log(freq / 8.176) / math.log(1.059463)# = 17.31236
        
        if t < 0:t = 0 
        if t > 127:t = 127 

        return int(t)

    def playtest(self,mididev):
        pass

    def APU_TO_FIXED(self,x):
        return x<<16


def SaveSounds(APU):
        #self.SoundData.append('%d,%s' %(self.CPU.Frames,','.join(self.APU.Sound[0:0x15]])))
        with open('sounddata.txt','a') as f:
            f.write('%d;%s' %(self.NES.CPU.Frames,','.join([str(i) for i in self.NES.APU.Sound])))
            f.write(';%s' %(','.join([str(i) for i in self.NES.APU.ChannelStatus])))
            f.write('\n')
        #print()
            
      

#'Calculates a midi tone given an nes frequency.
@jit(uint8(uint16),nopython=True)
def getTone(freq): 
        if freq <= 0:
            return 0
        
        #freq = 65536 / freq
        #freq = 111861 / (freq + 1)
        f = (1789772.5/(16.0 * (freq + 1)))
        #t = math.log(freq / 8.176) * 17.31236   # 1 / math.log(1.059463) = 17.31236
        
        t = np.log2(f/440.0) * 12.0 + 69.0
        if t < 0:t = 0 
        if t > 127:t = 127 

        return t


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
def play_note(note, length, track, base_num=0, delay=0, velocity=1.0, channel=0):

    bpm = 125

    meta_time = 60 / bpm * 1000 # 一拍多少毫秒，一拍等于一个四分音符

    major_notes = [0, 2, 2, 1, 2, 2, 2, 1]

    base_note = 60 # C4对应的数字

    track.append(Message('note_on', note=base_note + base_num*12 + sum(major_notes[0:note]), velocity=round(64*velocity), time=round(delay*meta_time), channel=channel))

    track.append(Message('note_off', note=base_note + base_num*12 + sum(major_notes[0:note]), velocity=round(64*velocity), time=round(meta_time*length), channel=channel))
    

def initMidi():
    global midiout
    midiout = rtmidi.MidiOut()
    available_ports = midiout.get_ports()
    print(available_ports)
    #print self.midiout.getportcount()
        
    if available_ports:
        midiout.open_port(0)
    else:
        midiout.open_virtual_port("My virtual output")

    midiout.send_message([0xC0,80]) #'Square wave'
    midiout.send_message([0xC1,80]) #'Square wave'
    #midiout.send_message([0xC2,39]) #Triangle wave
    midiout.send_message([0xC2,81]) #Triangle wave
    midiout.send_message([0xC3,127]) #Noise. Used gunshot. Poor but sometimes works.'
    midiout.send_message([0xC4,87]) #DPCM.'

    #midiout.send_message([0xB0,100]) #'Square wave'
    #midiout.send_message([0xB1,100]) #'Square wave'
    #midiout.send_message([0xB2,100]) #Triangle wave
    #midiout.send_message([0xB3,100]) #Noise. Used gunshot. Poor but sometimes works.'

    #return midiout

def updateSounds(f):
    global apu
    apu.updateSounds()
    
def playmidi(APU):
    for ch in range(5):
        #print(apu.notes[note])
        if APU.notes_off[ch][0]:
            APU.notes_off[ch][0] = 0
            midiout.send_message(APU.notes_off[ch][1:])
                    
        if APU.notes_on[ch][0]:
            APU.notes_on[ch][0] = 0
            midiout.send_message(APU.notes_on[ch][1:])

async def playfile(sf):
    global apu
    s = bytearray(np.fromfile(sf,dtype=np.uint8)).decode('utf8').split('\n')
    for fsound in s:
        t=time.time()
        sdata = [int(i) for i in fsound.split(';')[1].split(',')]
        f = uint32(fsound.split(';')[0])
        cw = [int(i) for i in fsound.split(';')[2].split(',')]

        #print(f,sdata,cw)
        apu.Sound[0:0x100] = sdata
        apu.MMU.ChannelWrite[0:0x10] = cw
            
        updateSounds(f)

        playmidi(apu)
            
        while time.time()-t<0.016:
            pass

def loadfile(fn):
    f = bytearray(np.memmap(fn,dtype=np.uint8, mode = 'r')).decode('utf8').split('\n')
    return f



def stopmidi():
    midiout.send_message([0x80, 60, 0])
    midiout.send_message([0x81, 60, 0])
    midiout.send_message([0x82, 60, 0])
    midiout.send_message([0x83, 60, 0])


def GetFreq(channel):
    freq = 0
    if channel in (0,1):
        pass
        
    
if __name__ == '__main__':
    print(getTone(300))
    
    
    initMidi()
    #note_on = [0x93, 60, 112] # channel 1, middle C, velocity 112
    #note_off = [0x83, 60, 0]
    #apu.midiout.send_message([192,127])
    #midiout.send_message(note_on)
    #time.sleep(0.5)
    #midiout.send_message([0x90, 60, 8])
    #time.sleep(3)
    #c
    #time.sleep(0.5)
    #midiout.send_message([0x90, 60, 100])
    #time.sleep(3)
    #midiout.send_message([0x80, 60, 0])
    #time.sleep(0.5)
    def sweepD(swp,length):
        s = length / swp
        for v in range(swp):
            midiout.send_message([0x90, 100 - v, 120])
            time.sleep(s)
            #midiout.send_message([0x90, 60 - v - 1, 80])
            midiout.send_message([0x80, 100 - v, 0])
        #midiout.send_message([0x80, 60 - swp, 0])
    def sweepU(swp,length):
        s = length / swp
        for v in range(swp):
            midiout.send_message([0x90, 20 + v, 120])
            time.sleep(s)
            #midiout.send_message([0x90, 60 - v - 1, 80])
            midiout.send_message([0x80, 20 + v, 0])
        #midiout.send_message([0x80, 60 - swp, 0])
    #sweepD(80,1)
    #time.sleep(1)
    #sweepD(80,2)
    #time.sleep(1)
    #sweepU(80,1)
    #time.sleep(1)
    sweepU(80,0.2)
    time.sleep(1)
    #notes = np.zeros((12,3),np.uint8)
    #note_on = np.array([0x93, 60, 112],np.uint8) # channel 1, middle C, velocity 112
    #notes[3] = [0x93, 60, 112]
    #note_off = np.array([0x83, 60, 0],np.uint8)
    #midiout.send_message(notes[3])
    #time.sleep(0.5)
    apu = APU()
    import asyncio
    asyncio.run(playfile('sounddata.txt'))

    import pyglet
    
    s = loadfile('sounddata.txt')
    player = pyglet.media.Player()
    player.loop = True
    def my_playlist():
        length = 0
        for i,fsound in enumerate(loadfile('sounddata.txt')):
            print(i)
            if length:
                length -= 1
                continue
            sdata = [int(i) for i in fsound.split(';')[1].split(',')]
            f = uint32(fsound.split(';')[0])
            cw = [int(i) for i in fsound.split(';')[2].split(',')]

            freq = sdata[0 * 4 + 2]  + (sdata[0 * 4 + 3] & 7) * 256
            frequency = uint16(freq) + 1#uint32(1789772.5/(16.0 * (freq + 1)))
            length = vbl_lengths[sdata[0 * 4 + 3] >> 3]
            Square1 = pyglet.media.synthesis.Square(length * 0.016, frequency=frequency, sample_rate=44100)
            
            yield Square1
            #player.queue(Square1)
            #while time.time()-t<0.016:
                #pass
    #plist = my_playlist
    #player.queue(my_playlist())
    #player.play()
    ###pyglet.app.run()
    #player.queue(pyglet.media.synthesis.Square(3.0, frequency=440, sample_rate=44800))
    #my_playlist()
    #pyglet.options['audio'] = ('xaudio2', 'directsound', 'openal', 'pulse', 'silent')
    #Square = pyglet.media.synthesis.Square(1.0, frequency=440, sample_rate=44100)
    #Triangle = pyglet.media.synthesis.Triangle(3.0, frequency=440, sample_rate=44800)
    #Square.play()
    #Triangle.play()
    
    length = 0
    for  i,fsound in enumerate(loadfile('sounddata.txt')):
        #print(i)
        if length:
            length -= 1
            continue
        t=time.time()
        sdata = [int(i) for i in fsound.split(';')[1].split(',')]
        f = uint32(fsound.split(';')[0])
        cw = [int(i) for i in fsound.split(';')[2].split(',')]

        freq = sdata[0 * 4 + 2]  + (sdata[0 * 4 + 3] & 7) * 256
        frequency = uint16(freq) + 1#uint32(1789772.5/(16.0 * (freq + 1)))
        length = vbl_lengths[sdata[0 * 4 + 3] >> 3]
        #print(frequency)
        Square1 = pyglet.media.synthesis.Square(0.016 * length, frequency=frequency, sample_rate=44100)
        
        #player.queue(Square1)
        #Square1.play()
        while time.time() - t < 0.016 * length:
            pass
    #player.play()
    #pyglet.app.run()
