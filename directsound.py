# -*- coding: UTF-8 -*-
import os
import time

import math
import random
import struct as _struct
from ctypes import *
import ctypes
import uuid

import win32com.directsound.directsound as Win32ds
import pywintypes

def pcmwf(rate = 22050, channels = 1, bits = 16 ):
    pcmwf = pywintypes.WAVEFORMATEX()
    pcmwf.wFormatTag = pywintypes.WAVE_FORMAT_PCM
    pcmwf.wBitsPerSample = bits
    pcmwf.nSamplesPerSec = rate
    pcmwf.nChannels = channels
    pcmwf.nBlockAlign = int(channels * bits / 8.0)
    pcmwf.nAvgBytesPerSec = rate * pcmwf.nBlockAlign
    return pcmwf

def dsbdesc(duration = 1/60, rate = 22050, channels = 1, bits = 16 ):
    m_lpDS = Win32ds.DirectSoundCreate(None, None)
    m_lpDS.SetCooperativeLevel(None, Win32ds.DSSCL_PRIORITY)
    dsbdesc = Win32ds.DSBUFFERDESC()
    dsbdesc.dwFlags       = Win32ds.DSBCAPS_LOCSOFTWARE | Win32ds.DSBCAPS_GETCURRENTPOSITION2 | Win32ds.DSBCAPS_GLOBALFOCUS #| Win32ds.DSBCAPS_CTRLPOSITIONNOTIFY
    #dsbdesc.dwFlags      = Win32ds.DSBCAPS_PRIMARYBUFFER
    dsbdesc.lpwfxFormat   = pcmwf(rate = rate, channels = channels, bits = bits )
    dsbdesc.dwBufferBytes = int(duration * dsbdesc.lpwfxFormat.nAvgBytesPerSec)
    buffer = m_lpDS.CreateSoundBuffer(dsbdesc, None)
    return buffer

#DSBUFFERDESC = dsbdesc()




if __name__ == '__main__':
    pass



    
    
    
    

