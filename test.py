# -*- coding: UTF-8 -*-
import numpy as np
import numba as nb
from numba import jitclass
from numba import uint8,uint16
from numba.typed import Dict
from numba import types


from cpu import n_map,setmap

setmap(1)


from cpu import cpu6502
                    
if __name__ == '__main__':

    cpu = cpu6502()







        
