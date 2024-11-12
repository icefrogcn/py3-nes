# -*- coding: UTF-8 -*-

import time
import rtmidi
import math

import struct as _struct
from ctypes import * 
import random



from pyglet.media.codecs.base import AudioData, AudioFormat, Source
from pyglet.media.synthesis import SynthesisSource,Envelope,FlatEnvelope

import numpy as np
import numba as nb
from numba import jit
from numba.experimental import jitclass
from numba import uint8,uint16,uint32,int8,int16,int32,float32,float64
from numba.typed import List,Dict
from numba.types import ListType,DictType,unicode_type
from numba import types

from jitcompile import jitObject,jitType

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
sample_rate = nRate	= 22050
cycle_rate = int((APU_CLOCK)/nRate) #<< 16

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
noise_note = np.array([110, 98, 86, 74, 62, 55, 50, 46, 42, 38, 31, 26, 19, 14, 2, 0], np.uint8)

'DF: powers of 2'
pow2 = np.array([2**i for i in range(31)] + [-2147483648],np.int32) #*(31) 

dpcm_cycles = np.array([
	428, 380, 340, 320, 286, 254, 226, 214,
	190, 160, 142, 128, 106,  85,  72,  54],np.uint16)

#pulse_tone = np.zeros(0x800,np.uint16)
#t21to95 = ['0x07F0', '0x077C', '0x0710', '0x06AC', '0x064C', '0x05F2', '0x059E', '0x054C', '0x0501', '0x04B8', '0x0474', '0x0434', '0x03F8', '0x03BE', '0x0388', '0x0356', '0x0326', '0x02F9', '0x02CF', '0x02A6', '0x0280', '0x025C', '0x023A', '0x021A', '0x01FC', '0x01DF', '0x01C4', '0x01AB', '0x0193', '0x017C', '0x0167', '0x0153', '0x0140', '0x012E', '0x011D', '0x010D', '0x00FE', '0x00EF', '0x00E2', '0x00D5', '0x00C9', '0x00BE', '0x00B3', '0x00A9', '0x00A0', '0x0097', '0x008E', '0x0086', '0x007E', '0x0077', '0x0071', '0x006A', '0x0064', '0x005F', '0x0059', '0x0054', '0x0050', '0x004B', '0x0047', '0x0043', '0x003F', '0x003B', '0x0038', '0x0035', '0x0032', '0x002F', '0x002C', '0x002A', '0x0028', '0x0026', '0x0024', '0x0022', '0x0020', '0x001E', '0x001C']
#for t,freq in enumerate(t21to95):
#    pulse_tone[eval(freq)] = t + 21

            
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
    ChannelPluse:uint8[:]
    notes_on:uint8[:,::1]
    notes_off:uint8[:,::1]

    wave_on:uint8[:]
    wave:float32[:,::1]

    mixbuffer:int16[::1]
    
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
        self.ch3 = NOISE(self.MMU,cycle_rate)
        self.ch4 = DPCM(self.MMU)
        
        self.tones = np.zeros(nVolumeChannel,np.float32)
        self.volume = np.zeros(nVolumeChannel,np.uint16)

        self.lastFrame = np.zeros(nVolumeChannel,np.uint16)
        self.stopTones = np.zeros(nVolumeChannel,np.uint8)

        self.ChannelStatus = np.zeros(nVolumeChannel,np.uint8)
        self.ChannelPluse = np.zeros(nVolumeChannel,np.uint8)
        self.ChannelUpdate = np.zeros(nVolumeChannel,np.uint8)

        self.notes_on = np.zeros((nVolumeChannel,4),np.uint8)
        self.notes_off = np.zeros((nVolumeChannel,4),np.uint8)

        self.wave = np.zeros((nVolumeChannel,3),np.float32)
        self.wave_on = np.zeros(nVolumeChannel,np.uint8)

        self.mixbuffer = np.zeros(int(sample_rate * 1/60), dtype = np.int16)
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

    def reset(self):
        pass
        #self.ch3.reset()
    
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
        else:
            self.ch2.enable    = 0xFF
            
        if(not(self.SoundCtrl(3)) ):
            self.ch3.enable    = 0
            self.ch3.len_count = 0
        else:
            self.ch3.enable    = 0xFF
            
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
        self.ChannelStatus = self.ChannelWrite.copy()
        
        #self.set_FRAMES(Frames)
        
        if self.doSound :
            #print 'playing'
            self.ReallyStopTones()
            self.updateReg4015()
            self.PlayDMC(self.ch4)
            self.PlayRect(self.ch0)
            self.PlayRect(self.ch1)
            self.PlayTriangle(self.ch2)
            self.PlayNoise()
            
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
            ch.volume       = ch.reg[0] & 0x0F# if ch.env_fixed else 8
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
            #ch.freq = ch.reg[2] + (ch.freq&~0xFF)

            'addr 3'
            ch.freq = ((ch.reg[3]&0x7) << 8) + ch.reg[2]#(ch.freq&0xFF)# + 1
            ch.len_count = vbl_lengths[ch.reg[3] >> 3] * 2
            ch.env_vol   = 0x0F
            ch.env_count = ch.env_decay+1
            ch.adder     = 0
            
            if(self.SoundCtrl(ch.no) ):
                ch.enable    = 0xFF
            
            self.ChannelUpdate[ch.no] = 1
        

    def UpdateRect(self, ch):
        if (not ch.enable) or ch.len_count <=0:
            return

        if ch.len_count and (not ch.holdnote):
            if (ch.len_count):
                ch.len_count -= 1

        #The sweep unit continuously calculates each pulse channel's target period
        if ch.swp_on and ch.swp_shift:
            if ch.swp_count:
                ch.swp_count -= 1
            if ch.swp_count == 0:
                ch.swp_count = ch.swp_decay#(ch.swp_decay + 1)//2 #The divider's period is P + 1 half-frames 
                self.ChannelUpdate[ch.no] = 1
                if ch.swp_inc:
                    if ch.complement:
                        ch.freq -= (ch.freq >> ch.swp_shift) #CH 1
                    else:
                        ch.freq += ~(ch.freq >> ch.swp_shift)#CH 0
                else:
                    ch.freq += (ch.freq >> ch.swp_shift)
                    #if ch.freq > ch.freqlimit:
                    #    self.ChannelUpdate[ch.no] = 0

        if( ch.env_count ):
            ch.env_count -= 1
        if ch.env_count == 0:
            ch.env_count = ch.env_decay

            if ch.holdnote:
                ch.env_vol = (ch.env_vol-1)&0x0F
            elif ch.env_vol:
                ch.env_count -= 1
        if not ch.env_fixed:
            ch.nowvolume = ch.env_vol 
            

        self.ChannelPluse[ch.no] = self.ChannelUpdate[ch.no]
        
    def RenderRectangle(self, ch: RECTANGLE):
        if (not ch.enable) or ch.len_count <=0:
            return 0
        if ch.freq < 8 or ((not ch.swp_inc) and ch.freq > ch.freqlimit):
            return 0
        if( ch.env_fixed ):ch.nowvolume = ch.volume
        
        volume = ch.nowvolume

        total = 0.0
        sample_weight = ch.phaseacc
        if( sample_weight > cycle_rate ):
            sample_weight = cycle_rate

        total = sample_weight if (ch.adder < ch.duty) else -sample_weight
        #freq = (ch.freq + 1)<<16 
        freq = ch.freq + 1
        ch.phaseacc -= cycle_rate
        while( ch.phaseacc < 0 ):
            ch.phaseacc += freq
            ch.adder = (ch.adder+1)&0x0F

            sample_weight = freq
            if( ch.phaseacc > 0 ):
                sample_weight -= ch.phaseacc

            total += sample_weight if (ch.adder < ch.duty) else -sample_weight

        return math.floor(volume * total/cycle_rate + 0.5)
        
    def ch01_generator(self, ch:RECTANGLE, sample_rate: float = 22050):
        while True:
            #yield self.RenderRectangle(ch)
            yield self.RenderRectangle_chg(ch)


            
    def PulseFreq(self, t):
        return 1789772.5/(16.0 * (t + 1))        
    
    def RenderRectangle_chg(self, ch: RECTANGLE):
        if (not ch.enable) or ch.len_count <=0:
            return 0
        if ch.freq < 8 or ((not ch.swp_inc) and ch.freq > ch.freqlimit):
            return 0
        if( ch.env_fixed ):ch.nowvolume = ch.volume

        volume = ch.nowvolume
        
        ch.phaseacc -= (cycle_rate)
        if ch.phaseacc >= 0:
            return volume if (ch.adder < ch.duty) else -volume

        freq = ch.freq + 1
        if freq > (cycle_rate):
            ch.phaseacc += freq 
            ch.adder += 1
            ch.adder &= 0xF
            return volume if (ch.adder < ch.duty) else -volume
            
        num_times = 0
        total = 0
        while( ch.phaseacc < 0):
            ch.phaseacc += freq 
            ch.adder += 1
            ch.adder &= 0xF
            total += volume if (ch.adder < ch.duty) else -volume
            num_times += 1
        
        return int(total/num_times)
            
    def pulse_generator(self, ch: RECTANGLE, duty_cycle: float = 50.0):
        duty_cycle = [12.5,25,50,75][ch.reg[0]>>6]
        period_length = int(sample_rate / self.PulseFreq(ch.freq)) #<< 1
        duty_cycle = int(duty_cycle * period_length / 100)
        volume = ch.nowvolume if ch.env_fixed else ch.volume
        if (not ch.enable) or ch.len_count <=0:volume = 0
        if ch.len_count <= 0: volume = 0
        if ch.freq < 8 or ((not ch.swp_inc) and ch.freq > ch.freqlimit): volume = 0
        #volume *= 0.00752 #
        i = 0
        while True:
            if period_length:
                #vol = 1 if True else 1
                output = int(i % period_length < duty_cycle) * 2.0 - 1.0
        
                #output = 1 if (i < duty_cycle) else -1
                yield output * volume
            else:
                yield 0
            i += 1.0
            #if i > period_length: i = 0
            


            
    def PlayRect(self,ch: RECTANGLE):
        self.WriteRect(ch)
        self.UpdateRect(ch)
        self.midiRect(ch)

        
            
        
    def midiRect(self,ch):
        no = ch.no
        
        if self.SoundCtrl(no):
            if ch.volume > 0 :
                if ch.freq < 8 or ((not (ch.swp_inc)) and ch.freq > ch.freqlimit) :
                    self.stopTone(no)
                else:
                    if self.ChannelWrite[no]:
                        #Ensures that a note doesn't replay unless memory written
                        self.ChannelWrite[no] = 0
                        self.playTone(no, self.getRectTone(ch.freq), ch.nowvolume )
                    elif self.ChannelUpdate[no]:
                        self.ChannelUpdate[no] = 0
                        self.playTone(no, self.getRectTone(ch.freq), ch.nowvolume )
                    
            else:
                self.stopTone(no)
        else:
            self.ChannelWrite[no] = 1
            self.stopTone(no)

        if ch.len_count <= 0: 
            self.stopTone(no)
        

    def WriteTriangle(self,ch2):
        if self.ChannelWrite[ch2.no]:
            ch2.holdnote     = ch2.reg[0] & 0x80
            'addr 2'
            #ch.freq = (ch.freq&0xFFFF00) + ch.reg[2]

            'addr 3'
            ch2.freq = (((ch2.reg[3]&0x7) << 8) + ch2.reg[2]) #<< 1
            ch2.len_count = vbl_lengths[ch2.reg[3] >> 3] #* 2
            ch2.counter_start = 0x80
            
            if(self.SoundCtrl(2) ):
                ch2.enable    = 0xFF
            
    def UpdateTriangle(self, ch2):
        if not ch2.enable:
            return
        
        if ch2.counter_start:
            ch2.lin_count = ch2.reg[0] & 0x7F
        elif ch2.lin_count:
            ch2.lin_count -= 1
        if (not ch2.holdnote) and ch2.lin_count:
            ch2.counter_start = 0
            
        if not ch2.holdnote:
            ch2.len_count -= 1 

    
    def PlayTriangle(self,ch2):
        self.WriteTriangle(ch2)
        self.UpdateTriangle(ch2)
        #self.RenderTriangle(ch2)
        self.playMidiTriangle(ch2)

        #if ch2.lin_count <= 0:
        #    ch2.len_count = 0

    def RenderTriangle(self,ch2):
        vol = (256 - int((self.ch4.reg[1]&0x01) + self.ch4.dpcm_value * 2))/256
        if (not self.ch2.enable) or (self.ch2.len_count <= 0) or (self.ch2.lin_count <= 0):
            return ch2.nowvolume * vol# * 2 - 0xF
        if (self.ch2.freq < 8):
            return ch2.nowvolume * vol# * 2 - 0xF
        
        ch2.phaseacc -= cycle_rate
        if ch2.phaseacc >= 0:
            return ch2.nowvolume * vol# * 2 - 0xF
        
        if ch2.freq > cycle_rate:
            ch2.phaseacc += ch2.freq 
            ch2.adder = (ch2.adder+1)&0x1F
            if( ch2.adder < 0x10 ):
                ch2.nowvolume = (ch2.adder&0x0F)#<<TRIANGLE_VOL_SHIFT
            else:
                ch2.nowvolume = (0x0F-(ch2.adder&0x0F))#<<TRIANGLE_VOL_SHIFT
            return ch2.nowvolume * vol# * 2 - 0xF
        num_times = 0
        total = 0
        while( ch2.phaseacc < 0):
            ch2.phaseacc += ch2.freq 
            ch2.adder = (ch2.adder+1)&0x1F
            if( ch2.adder < 0x10 ):
                ch2.nowvolume = (ch2.adder&0x0F)#<<TRIANGLE_VOL_SHIFT
            else:
                ch2.nowvolume = (0x0F-(ch2.adder&0x0F))#<<TRIANGLE_VOL_SHIFT
            total += ch2.nowvolume
            num_times += 1
        
        return int(total/num_times) * vol * 2 - 0xF

    def Ch2Generator(self, sample_rate: float = 22050):
        while True:
            yield self.RenderTriangle(self.ch2)

    @property
    def TriangleFreq(self):
        return int(1789772.5/(32.0 * (self.ch2.freq + 1)))
    
    def triangle_generator(self):
        ch2 = self.ch2
        frequency = self.TriangleFreq
        step = 4.0 * frequency / sample_rate
        value = 0.0#ch2.nowvolume
        volume = 0xF
        vol = (256 - int((self.ch4.reg[1]&0x01) + self.ch4.dpcm_value * 2))/256
        if (not self.ch2.enable) or (self.ch2.len_count <= 0) or (self.ch2.lin_count <= 0) or (self.ch2.freq < 8):
           value = 0.0
           volume = 0
        volume *= vol
        while True:
            if value > 1.0:
                value = 2.0 - value
                step = -step
            if value < -1.0:
                value = -2.0 - value
                step = -step
            ch2.nowvolume = value
            yield value * volume
            value += step

    def triangle_render(self):
        ch2 = self.ch2
        frequency = self.TriangleFreq
        step = int(4.0 * 0x7FFF * frequency / sample_rate)
        volume = 1#0xF  #if ch2.enable and self.ch2.freq > 0 else 0
        #if ch2.len_count <= 0 or ch2.lin_count <= 0: volume =  0.0
        vol = (256 - int((self.ch4.reg[1]&0x01) + self.ch4.dpcm_value * 2))/256
        if (not ch2.enable) or (ch2.len_count <= 0) or (ch2.lin_count <= 0) or (ch2.freq < 8):
            pass
            #volume *= 0

        #volume *= 0.00851
        #value = 0.0
        #while True:
        if ch2.nowvolume > 0x7FFF:
                ch2.nowvolume = 0x7FFF - (ch2.nowvolume - 0x7FFF)
                step = -step
        if ch2.nowvolume < -0x7FFF:
                ch2.nowvolume = -0x7FFF - (ch2.nowvolume + 0x7FFF)
                step = -step
        ch2.nowvolume += step
        #if ch2.nowvolume > 0.5:print(ch2.nowvolume)
        return (ch2.nowvolume - step) / 0x7FFF
            

    def ch2_generator(self, sample_rate: float = 22050):
        while True:
            yield self.triangle_render()
            
    def playMidiTriangle(self, ch):
        no = ch.no
        if self.SoundCtrl(no)  or ch.enable:
            if ch.volume > 0 :
                if ch.freq > 0 :
                    if self.ChannelWrite[no] : #Ensures that a note doesn't replay unless memory written
                        self.ChannelWrite[no] = 0
                        self.lastFrame[no] = ch.len_count #self.Frames + length
                        self.playTone(no, self.getTriangleTone(ch.freq), ch.volume )
                else:
                    self.stopTone(no)
                
            else:
                self.stopTone(no)
            
        else:
            self.ChannelWrite[no] = 1
            self.stopTone(no)

        if ch.len_count <= 0: #self.Frames >= self.lastFrame[ch]:
            self.stopTone(no)
        #if self.lastFrame[no] == 0: #self.Frames >= self.lastFrame[ch]:
        #    self.stopTone(no)
        #self.lastFrame[no] -= 0 if ch.holdnote else 1
        
        
    def PlayNoise(self):
        if self.ChannelWrite[self.ch3.no]:
            self.ch3.write()
            if self.SoundCtrl(3):
                self.ch3.enable    = 0xFF
        self.ch3.update()

        self.playMidiNoise(self.ch3)
            
    def noise_generator(self):
        period_length = int(sample_rate / self.WNoiseSamplerate)
        volume = self.ch3.nowvolume if self.ch3.enable else 0
        if self.ch3.len_count <= 0: volume = 0.0
        vol = (256 - int((self.ch4.reg[1]&0x01) + self.ch4.dpcm_value * 2))/256
        volume *= vol
        step = 0
        while True:
            if step == 0:
                step = period_length
                value = volume if random.randint(0,1) else -volume
                
            else:
                step -= 1
            if period_length == 0:
                value = 0
            yield value
                
    @property
    def NoiseSamplerate(self):
        return int(1789772.5 / self.ch3.freq)
    @property
    def WNoiseSamplerate(self):
        freq = self.ch3.freq if 8 <  self.ch3.freq <= 1016 else 0
        freq = 16 if self.ch3.freq < 16 else freq
        freq = 1016 if self.ch3.freq > 1016 else freq
        return int(1789772.5 / freq)            

        
    def playMidiNoise(self, ch):
        no = ch.no
        if self.SoundCtrl(no)  or ch.enable:
            if ch.nowvolume > 0 :
                if ch.freq > 1 :
                    if self.ChannelWrite[no] : #Ensures that a note doesn't replay unless memory written
                        self.ChannelWrite[no] = 0
                        #self.lastFrame[no] = ch.len_count #self.Frames + length
                        self.playTone(no, noise_note[ch.reg[2] & 0xF], ch.nowvolume )
                else:
                    self.stopTone(no)
                
            else:
                self.stopTone(no)
            
        else:
            self.ChannelWrite[no] = 1
            self.stopTone(no)

        #if self.lastFrame[no] == 0: #self.Frames >= self.lastFrame[ch]:
        if ch.len_count <= 0: #self.Frames >= self.lastFrame[ch]:
            self.stopTone(no)
        #self.lastFrame[no] -= 0 if ch.holdnote else 1
        
    
    def PlayDMC(self, ch4):
        if self.ChannelWrite[ch4.no]:
            self.WriteDMC(self.ch4)

        ch4.len_count = 1
        
        #self.RenderDMC(ch4)
        ch4.nowvolume = ch4.output
        
        #self.playfun(ch4)

    def WriteDMC(self,ch4):
        ch4.freq = dpcm_cycles[(ch4.reg[0] & 0xF)]
        ch4.looping = ch4.reg[0]&0x40

        ch4.dpcm_value = (ch4.reg[1]&0x7F)>>1

        'Sample address = %11AAAAAA.AA000000 = $C000 + (A * 64)'
        ch4.cache_addr = 0xC000+(ch4.reg[2]<<6)

        'Sample length = %LLLL.LLLL0001 = (L * 16) + 1 bytes'
        ch4.cache_dmalength = ((ch4.reg[3]<<4)+1)#<<3
        
    def UpdateDMC(self,ch4):
        pass
        
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
                if not ch4.dmalength:
                    if ch4.looping:
                        ch4.address = ch4.cache_addr
                        ch4.dmalength = ch4.cache_dmalength
                    else:
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
        return ch4.output/0x40

    def ch4_generator(self, sample_rate: float = 22050):
        while True:
            yield self.RenderDMC(self.ch4) * 0xF

    def DMC_generator(self, sample_rate: float = 22050):
        ch4 = self.ch4
        #volume = (ch4.reg[1]&0x01)+ ch4.dpcm_value*2)
        period_length = int(sample_rate / self.DMCfreq)
        
        i = 0
        while True:
            
            if i <= 0 and period_length > 0 :
                i = period_length
                if( ch4.dmalength ):
                    if ch4.dmalength&7 == 0:
                        ch4.cur_byte = self.MMU.read( ch4.address )
                        if( 0xFFFF == ch4.address ):
                            ch4.address = 0x8000
                        else:
                            ch4.address += 1
                    ch4.dmalength -= 1
                    if( ch4.dmalength ) == 0:
                        if ch4.looping:
                            ch4.address = ch4.cache_addr
                            ch4.dmalength = ch4.cache_dmalength
                        else:
                            ch4.enable = 0
                            #ch4.output = 0.0
                    if( ch4.cur_byte&(1<<((ch4.dmalength&7)^7)) ):
                        if ( ch4.dpcm_value < 0x3F ):
                            ch4.dpcm_value += 1
                    else:
                        if ( ch4.dpcm_value >1 ):
                            ch4.dpcm_value -= 1
                    ch4.output = ((ch4.reg[1]&0x01)+ ch4.dpcm_value*2) #if( ch4.dmalength  and ch4.enable) else 0
                else:
                    ch4.output = 0
            else:
                i -= 1
            
            if period_length == 0:ch4.output = 0
            yield ch4.output/128.0
            

    @property
    def DMCfreq(self):
        
        return int(1789772.5 / self.ch4.freq) if self.ch4.freq else int(1789772.5 / 428)
    
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

        if self.lastFrame[no] == 0:
            self.stopTone(no)
        self.lastFrame[no] -= 0 if ch.holdnote else 1
        
    


    def ToneOn(self, channel, tone, volume):
        if tone < 0:tone = 0 
        if tone > 255:tone = 255 
        #tone = 127 if tone > 127 else 127
        note_on = [0x90 + channel, tone, volume] 
        self.notes_on[channel][0] = 1
        self.notes_on[channel][1:] = note_on
            


    def ToneOff(self, channel,tone):
        if tone < 0:tone = 0 
        if tone > 255:tone = 255 
        #tone = 127 if tone > 127 else 127
        note_off = [0x80 + channel, tone, 0]
        self.notes_off[channel][0] = 1
        self.notes_off[channel][1:] = note_off
            

    



    
    def getRectTone(self, Pulsetimer):
        if Pulsetimer < 8:
            return 0

        f = self.PulseFreq(Pulsetimer + 1)
        t = np.log2(f/440.0) * 12.0 + 69.0
        
        if t < 0:t = 0 
        if t > 127:t = 127 

        return int(t)

    def getTriangleTone(self, freq): #As Long
        if freq < 8:
            return 0
        
        f = 1789772.5/(32.0 * (freq + 1 + 1))
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

    def APU_TO_FIXED(self,x):
        return x<<16
    
    # Waveform generators
    def silence_generator(self):# -> Generator[float]:
        while True:
            yield 0.0
        
   

    def MixerGeneratorRender(self):
        ch0 = self.ch01_generator(self.ch0)
        ch1 = self.ch01_generator(self.ch1)
        ch2 = self.Ch2Generator()
        ch3 = self.ch3.generator()

        ch4 = self.DMC_generator()
        #ch4 = self.silence_generator()
        'HPF TEST'
        cutofftemp = (2.0*3.141592653579*40.0)/0x7FFF
        cutoff = cutofftemp/22050
        tmp = 0.0
        #out = 0.0
        while True:
            pulse_out = 0.00752 * (next(ch0) + next(ch1))
            tnd_out = (0.00851 * next(ch2)) + (0.00494 * next(ch3)) + (0.00335 * next(ch4))
            m_in = pulse_out + tnd_out
            #yield m_in * 2
            m_out = m_in - tmp
            tmp = tmp + cutoff * m_out

            f_out = m_out * 2
            if f_out > 1:
                f_out = 1
            elif f_out < -1:
                f_out = -1
            yield f_out

    def MixerGeneratorAPI(self):
        ch0 = self.pulse_generator(self.ch0)
        ch1 = self.pulse_generator(self.ch1)
        ch2 = self.triangle_generator()
        ch3 = self.noise_generator()
        #ch4 = self.DMC_generator()
        ch4 = self.silence_generator()
        'HPF TEST'
        cutofftemp = (2.0*3.141592653579*40.0)/0x7FFF
        cutoff = cutofftemp/22050
        tmp = 0.0
        #out = 0.0
        while True:
            pulse_out = 0.00752 * (next(ch0) + next(ch1))
            tnd_out = 0#(0.00851 * next(ch2)) + (0.00494 * next(ch3)) + (0.00335 * next(ch4))
            m_in = pulse_out + tnd_out
            #yield m_in * 2
            m_out = m_in - tmp
            tmp = tmp + cutoff * m_out

            f_out = m_out
            if f_out > 1:
                f_out = 1
            elif f_out < -1:
                f_out = -1
            yield f_out

    @property
    def MixerOutData(self):
        samples = len(self.mixbuffer)#_max_offset >> 1
        out = self.MixerGeneratorRender()
        return np.array([int(0x7FFF * next(out)) for _ in range(samples)], dtype = np.int16)


@jit
def MixerOutData(APU):
    samples = int(sample_rate/60)
    out = APU.MixerGeneratorRender()
    while True:
        yield np.array([int(0x7FFF * next(out)) for _ in range(samples)], dtype = np.int16)

# Waveform generators
@jit
def silence_generator():# -> Generator[float]:
    while True:
        yield 0.0

@jit
def noise_generator(frequency: float, sample_rate: float):# -> Generator[float]:
    while True:
        yield random.uniform(-1.0, 1.0)

@jit
def sine_generator(frequency: float, sample_rate: float):# -> Generator[float]:
    step = 2.0 * math.pi * frequency / sample_rate
    i = 0.0
    while True:
        yield math.sin(i * step)
        i += 1.0

@jit
def triangle_generator(frequency: float, sample_rate: float):# -> Generator[float]:
    step = 4.0 * frequency / sample_rate
    value = 0.0
    while True:
        if value > 1.0:
            value = 1.0 - (value - 1.0)
            step = -step
        if value < -1.0:
            value = -1.0 - (value - -1.0)
            step = -step
        yield value
        value += step

@jit
def sawtooth_generator(frequency: float, sample_rate: float):# -> Generator[float]:
    period_length = int(sample_rate / frequency)
    step = 2.0 * frequency / sample_rate
    i = 0.0
    while True:
        yield step * (i % period_length) - 1.0
        i += 1.0

@jit
def pulse_generator(frequency: float, sample_rate: float, duty_cycle: float = 50.0):# -> Generator[float]:
    period_length = int(sample_rate / frequency)
    duty_cycle = int(duty_cycle * period_length / 100)
    i = 0.0
    while True:
        yield int(i % period_length < duty_cycle) * 2.0 - 1.0
        i += 1.0
@jit
def pulse_generatorT(frequency: float, sample_rate: float, duty_cycle: float = 50.0):# -> Generator[float]:
    period_length = int(sample_rate / frequency)
    duty_cycle = int(duty_cycle * period_length / 100)
    i = 0.0
    while True:
        yield int(i % period_length < duty_cycle) * 1.0
        i += 1.0
        

def SaveSounds(APU):
        with open('sounddata.txt','a') as f:
            f.write('%d;%s' %(self.NES.CPU.Frames,','.join([str(i) for i in self.NES.APU.Sound])))
            f.write(';%s' %(','.join([str(i) for i in self.NES.APU.ChannelStatus])))
            f.write('\n')
        
            
      

'Calculates a midi tone given an nes frequency.'
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
    midiout.send_message([0xC2,81]) #Triangle wave
    midiout.send_message([0xC3,127]) #Noise. Used gunshot. Poor but sometimes works.'
    midiout.send_message([0xC4,87]) #DPCM.'
    return midiout
    
def playmidi(APU):
    for ch in range(5):
        #print(apu.notes[note])
        if APU.notes_off[ch][0]:
            APU.notes_off[ch][0] = 0
            midiout.send_message(APU.notes_off[ch][1:])
                    
        if APU.notes_on[ch][0]:
            APU.notes_on[ch][0] = 0
            midiout.send_message(APU.notes_on[ch][1:])

def playsound(APU,event):
    for ch in [0,1,2,4]:
        #print(apu.notes[note])
        if APU.notes_off[ch][0]:
            APU.notes_off[ch][0] = 0
            midiout.send_message(APU.notes_off[ch][1:])
                    
        if APU.notes_on[ch][0]:
            APU.notes_on[ch][0] = 0
            midiout.send_message(APU.notes_on[ch][1:])

    SynthesisOut(generator = APU.noise_generator(),
                                         duration = event).play()
def MixerOutRender(APU,event):
    out = APU.MixerGeneratorRender()
    while True:
        yield SynthesisOut(out,duration = event)


def MixerOutAPI(APU,event):
    while True:
        yield SynthesisOut(APU.MixerGeneratorAPI(),duration = event)

def stopmidi(APU):
    APU.notes_on[0][3] = 0
    APU.notes_on[1][3] = 0
    APU.notes_on[2][3] = 0
    APU.notes_on[3][3] = 0
    APU.notes_on[4][3] = 0
    midiout.send_message(APU.notes_on[0][1:])
    midiout.send_message(APU.notes_on[1][1:])
    midiout.send_message(APU.notes_on[2][1:])
    midiout.send_message(APU.notes_on[3][1:])
    midiout.send_message(APU.notes_on[4][1:])

        

class SynthesisOut(SynthesisSource):
    """Base class for synthesized waveforms.
    """
    def __init__(self, generator, duration: float, sample_rate: int = 22050, envelope: Envelope | None = None):
        super().__init__(generator, duration, sample_rate, envelope)

    def get_audio_data(self, num_bytes: int, compensation_time: float = 0.0) -> AudioData | None:
        """Return ``num_bytes`` bytes of audio data."""
        num_bytes = min(num_bytes, self._max_offset - self._offset)
        if num_bytes <= 0:
            return None

        timestamp = self._offset / self._bytes_per_second
        duration = num_bytes / self._bytes_per_second
        self._offset += num_bytes

        # Generate bytes:
        samples = num_bytes >> 1
        generator = self._generator
        envelope = self._envelope_generator
        #data = (c_int16 * samples)(*[int(next(generator) * next(envelope) * 0x7fff) for _ in range(samples)])
        data = (c_int16 * samples)(*map(lambda x:int(next(generator) * next(envelope) * 0x7fff), range(samples)))
        return AudioData(data, num_bytes, timestamp, duration, [])

class SynthesisOutT(SynthesisSource):
    """Base class for synthesized waveforms.
    """
    def __init__(self, generator, duration: float, sample_rate: int = 22050, envelope: Envelope | None = None):
        super().__init__(generator, duration, sample_rate, envelope)

    def get_audio_data(self, num_bytes: int, compensation_time: float = 0.0) -> AudioData | None:
        """Return ``num_bytes`` bytes of audio data."""
        num_bytes = min(num_bytes, self._max_offset - self._offset)
        if num_bytes <= 0:
            return None

        timestamp = self._offset / self._bytes_per_second
        duration = num_bytes / self._bytes_per_second
        self._offset += num_bytes

        # Generate bytes:
        samples = num_bytes >> 1
        generator = self._generator
        envelope = self._envelope_generator
        data = (c_uint16 * samples)(*map(lambda x:int(next(generator) * next(envelope) * 0xffff), range(samples)))
        return AudioData(data, num_bytes, timestamp, duration, [])


    
if __name__ == '__main__':
    print(getTone(300))
    #apu=APU()

    
    

