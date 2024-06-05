# -*- coding: UTF-8 -*-
import numba as nb
from numba.experimental import jitclass


def jitObject(classObject, Object_spec, ObjectAddition={}, jit = True):
    if jit:
        try:
            if not hasattr(classObject, "class_type"):

                for key in ObjectAddition:
                    if ObjectAddition[key]:
                        Object_spec.append((key, ObjectAddition[key]))
                
                jitObject = jitclass(classObject, Object_spec)
                Object_type = nb.deferred_type()
                Object_type.define(jitObject.class_type.instance_type)

                return jitObject,Object_type
        except:
            print(traceback.print_exc())
            
    return classObject,None    

                    
if __name__ == '__main__':
    pass
    #jitObject()

    

    
    
    
    








        
