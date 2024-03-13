# -*- coding: UTF-8 -*-
import time
from numba  import jit
from numba.experimental import jitclass

from numba import int8,uint8,int16,uint16,uint32
import numpy as np
import numba as nb
from numba.typed import Dict
from numba import types
#自定义类
#from deco import *

#@jit
def MemCopy(dest, dest_p, src, src_p , size):
    #if type(dest) == list and type(src)== list:
        dest[dest_p:dest_p + size] = src[src_p : src_p + size]
        '''for i in range(size):
            if src_p + i <= len(src) - 1:
                dest[dest_p + i] = src[src_p + i]'''


def mcopy(src, src_p , size):
    return src

@jit(nopython=True)
def mcopy1(dest, dest_p, src, src_p , size):
    for i in range(10000):
        dest[dest_p:dest_p + size] = src[src_p : src_p + size]

reg_spec = [('PC',uint16),
            ('a',uint8),
            ('X',uint8),
            ('Y',uint8),
            ('S',uint8),
            ('p',uint16)]
#@jitclass(reg_spec)
class reg(object):
    PC = 0          
    a = 0           
    X = 0            
    Y = 0             
    S = 0              
    p = 0
    def __init__(self):
        pass
    def add(self):
        while True:
            self.a += 1 if self.a < 200 else -1
            yield self.a
 

        
#reg_type = nb.deferred_type()
#reg_type.define(reg.class_type.instance_type)

#regs = {'a':123}





if __name__ == '__main__':
    pass
       
    t=test()
    

