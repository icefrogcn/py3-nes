# -*- coding: UTF-8 -*-

from numba  import jit
from numba.experimental import jitclass
from numba import int8,uint8,int16,uint16
import numpy as np
import numba as nb



#自定义类
#from deco import *
#from wrfilemod import read_file_to_array


@jitclass
class ROM(object):
    data: uint8[::1]    #force array type C
    REG: uint16[:]
        
    def __init__(self):#, data = np.zeros(0x20, np.uint8)):
        self.REG = np.zeros(0x10, np.uint16)

        self.data = np.zeros(0x100020, np.uint8)


    @property
    def PROM_SIZE(self):
        return self.PROM_16K_SIZE
    @property
    def VROM_SIZE(self):
        return self.VROM_8K_SIZE
    @property
    def AndIt(self):
        if self.VROM_SIZE:
            return self.VROM_SIZE - 1
    
    @property
    def PROM(self):
        return self.data[16: self.PROM_SIZE * 0x4000 + 16]
    @property
    def VROM(self):
        PrgMark = self.PROM_SIZE * 0x4000 + 16
        if self.VROM_SIZE:
            return self.data[PrgMark: self.VROM_SIZE * 0x2000 + PrgMark]
        else:
            return np.zeros(0x0, np.uint8)

    @property
    def Mapper(self):
        return self.ROMCtrl2 + ((self.ROMCtrl & 0xF0) >> 4)

    @property
    def Trainer(self):
        return self.ROMCtrl & 0x4

    @property
    def Mirroring(self):
        return self.ROMCtrl & 0x1
    #@Mirroring.setter
    #def Mirroring(self,value):
        #self.REG[0] = value

    def IsVMIRROR(self):
        return self.Mirroring & 1

    @property
    def FourScreen(self):
        return self.ROMCtrl & 0x8
    @property
    def Is4SCREEN(self):
        return self.FourScreen

    @property
    def UsesSRAM(self):
        return True if self.ROMCtrl & 0x2 else False


    @property
    def PROM_8K_SIZE(self):
        return self.PROM_16K_SIZE << 1
    @property
    def PROM_16K_SIZE(self):
        return self.data[0x4]
    @property
    def PROM_32K_SIZE(self):
        return self.PROM_16K_SIZE >> 1
    @property
    def VROM_1K_SIZE(self):
        return self.VROM_8K_SIZE << 3
    @property
    def VROM_2K_SIZE(self):
        return self.VROM_8K_SIZE << 2
    @property
    def VROM_4K_SIZE(self):
        return self.VROM_8K_SIZE << 1
    @property
    def VROM_8K_SIZE(self):
        return self.data[0x5]

    @property
    def ROMCtrl(self):
        return self.data[6]
    @property
    def ROMCtrl2(self):
        return self.data[7]

    @property
    def NESHEADER_SIZE(self):
        return 0x20
    
    def info(self):
    
        print ("[ " , self.PROM_16K_SIZE , " ] 16kB ROM Bank(s)")
        print ("[ " , self.VROM_8K_SIZE , " ] 8kB CHR Bank(s)")
        print ("[ " , self.ROMCtrl , " ] ROM Control Byte #1")
        print ("[ " , self.ROMCtrl2 , " ] ROM Control Byte #2")
        print ("[ " , self.Mapper , " ] Mapper")
        print ("Mirroring =" , self.Mirroring , "Trainer =" , self.Trainer , "FourScreen =" , self.FourScreen , "SRAM =" , self.UsesSRAM , "")
        if self.Trainer:
            print ("Error: Trainer not yet supported.") 


class nesROM():

    def __init__(self):
        pass


    def LoadROM(self,filename):

        #self.data = np.array(read_file_to_array(filename),dtype=np.uint8)
        self.data = np.fromfile(filename,dtype=np.uint8)
        
        if ''.join([chr(i) for i in self.data[:0x4]]) == 'NES\x1a':
            print(f'{filename} ROM OK!')
        else:
            print(f'{filename} Invalid Header')
            return 0
        
        #self.ROM = ROM(self.data)

        #self.ROM.info()
        
        
    
        return self.data#self.ROM
            
    def info(self):
    
        print (f"[ {self.ROM.PROM_16K_SIZE:3} ] 16kB ROM Bank(s)")
        print (f"[ {self.ROM.VROM_8K_SIZE:3} ] 8kB CHR Bank(s)")
        print (f"[ {self.ROM.ROMCtrl:3} ] ROM Control Byte #1")
        print (f"[ {self.ROM.ROMCtrl2:3} ] ROM Control Byte #2")
        print (f"[ {self.ROM.Mapper:3} ] Mapper")
        print (f"Mirroring={self.ROM.Mirroring}  Trainer={self.ROM.Trainer}  FourScreen={self.ROM.FourScreen}  SRAM={self.ROM.UsesSRAM}")
        if self.ROM.Trainer:
            print ("Error: Trainer not yet supported.") #, VERSION 


def LoadROM(filename):

        #self.data = np.array(read_file_to_array(filename),dtype=np.uint8)
        data = np.fromfile(filename,dtype=np.uint8)
        
        if ''.join([chr(i) for i in data[:0x4]]) == 'NES\x1a':
            print(f'{filename} ROM OK!')
        else:
            print(f'{filename} Invalid Header')
            return 0
        return data
        
def calculate_Mapper(NESHEADER):
    return  (NESHEADER[6] & 0xF0) // 16 + NESHEADER[7]

def get_Mapper_by_fn(filename):
    return calculate_Mapper(np.fromfile(filename,dtype=np.uint8))


if __name__ == '__main__':
    rom = ROM()
    rom.data = LoadROM('roms//Contra (J).nes')
    rom.info()
    import os
    for i,item in enumerate([item for item in os.listdir('roms') if ".nes" in item.lower()]):
        print(i,item)
        rom.data = LoadROM('roms//' + item)
        rom.info()










        
