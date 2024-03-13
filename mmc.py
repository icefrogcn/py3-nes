# -*- coding: UTF-8 -*-

''' Functions for emulating MMCs. Select8KVROM and the
' like
' 16.07.00'''

from nes import NES
from rom import nesROM as ROM

class MMC(ROM, NES):
    CurrVr  = 0 #As Byte
    PrgSwitch1 =0 # Byte
    PrgSwitch2 =0 # Byte
    SpecialWrite6000 = False # Boolean

    
    swap = False

    #MMC3[Mapper #4] infos
    MMC3_Command = 0# Byte
    MMC3_PrgAddr= 0# Byte
    MMC3_ChrAddr= 0# Integer
    MMC3_IrqVal= 0# Byte
    MMC3_TmpVal= 0# Byte
    irq_enable= False# Boolean

    def MMC3_HBlank(self, Scanline, two): # As Boolean
    
        if Scanline == 0 :
            self.MMC3_IrqVal = self.MMC3_TmpVal
            return False
        
        elif Scanline > 239:
            return
        
        elif self.irq_enable & (two & 0x18):
            self.MMC3_IrqVal = self.MMC3_IrqVal - 1
            if (self.MMC3_IrqVal == 0):
                self.MMC3_IrqVal = self.MMC3_TmpVal
                return True

    def SetPROM_Banks(self):
        pass

    def Select8KVROM(self, val1, VROM):
        val1 = MaskVROM(val1, NES.VROM_8K_SIZE)
        return VROM[val1 * 0x2000 : val1 * 0x2000 + 0x2000]
    


def MaskVROM(page, mask):
    return page and (mask - 1)

'''
def Select8KVROM(val1):
    val1 = MaskVROM(val1, ChrCount)
    MemCopy VRAM(0), VROM(val1 * &H2000&), &H2000&

def Select4KVROM(val1 As Byte, bank As Byte)
    val1 = MaskVROM(val1, ChrCount * 2)
    MemCopy VRAM(bank * &H1000&), VROM(val1 * &H1000&), &H1000&

def Select2KVROM(val1 As Byte, bank As Byte)
    val1 = MaskVROM(val1, ChrCount * 4)
    If Mapper = 4 Then
        MemCopy VRAM(MMC3_ChrAddr Xor (bank * &H800&)), VROM(val1 * &H800&), &H800&
    Else
        MemCopy VRAM(bank * &H800&), VROM(val1 * &H800&), &H800&
    End If

def Select1KVROM(val1 As Byte, bank As Byte)
    val1 = MaskVROM(val1, ChrCount * 8)
    Select Case Mapper
    Case 4
        MemCopy VRAM(MMC3_ChrAddr Xor (bank * &H400&)), VROM(val1 * &H400&), &H400&
    Case 23
        MemCopy VRAM(bank * &H400&), VROM(val1 * &H400&), &H400&
    Case Else
        MemCopy VRAM(bank * &H400&), VROM(val1 * &H400&), &H400&
    End Select

'''


if __name__ == '__main__':
    pass

        










        
