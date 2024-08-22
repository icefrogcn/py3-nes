# -*- coding: UTF-8 -*-
import traceback

import numba as nb
from numba.experimental import jitclass

from deco import *

def jitObject(classObject, Object_spec, ObjectAddition={}, jit = True):
    if jit:
        try:
            #if not hasattr(classObject, "class_type"):
                for key in ObjectAddition:
                    if ObjectAddition[key]:
                        Object_spec.append((key, ObjectAddition[key]))
                jitObject = jitclass(classObject, Object_spec)
                Log_SYS(f'{classObject.__name__} jit ok')
                return jitObject
        except:
            print(traceback.print_exc())
    Log_SYS(f'{classObject.__name__} not jit')
    return classObject    

def jitType(jitObject):
    try:
        Object_type = nb.deferred_type()
        Object_type.define(jitObject.class_type.instance_type)
        return Object_type
    except:
        print(traceback.print_exc())
    return 0  
                    
if __name__ == '__main__':
    pass
    #jitObject()

    

    
    
    
    








        
