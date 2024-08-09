#_*_coding:utf-8*_
import time

def Log_SYS(*args):
    print(print_now(),'SYSTEM:',' '.join(args))

def Log_HW(*args):
    print(print_now(),'HARDWARE:',' '.join(args))
 
def print_now():
    return time.strftime("%b %d %H:%M:%S", time.localtime())

def debug(func):    
    def wrapper(*args, **kwargs):
        results = func(*args, **kwargs)
        print(print_now(),"[DEBUG]: {}()".format(func.__name__),results,'\n')
        return results
    return wrapper

def deco(func):
    def wrapper(*args, **kwargs):
        results = func(*args, **kwargs)
        print(print_now(),results)#,'\n'
        return results
    return wrapper

def deco_print(print_info):
    def deco(func):
        def wrapper(*args, **kwargs):
            results = func(*args, **kwargs)
            print(print_now(),print_info,results)
            return results
        return wrapper
    return deco
    
    

def err_print(e):
    if hasattr(e, 'code'):
        print('Error code:',e.code)
    if hasattr(e,"reason"):
        print("Error",e.reason,"Retry 1 Second.")
        print(ERROR_times, "retry")
    return e


if __name__ == '__main__':
    pass

