#_*_coding:utf-8*_
import time


 
def print_now():
    return time.strftime("%b %d %H:%M:%S", time.localtime())

def debug(func):    
    def wrapper(*args, **kwargs):
        print(print_now(),"[DEBUG]: {}()".format(func.__name__),func(*args, **kwargs),'\n')
        return func(*args, **kwargs)
    return wrapper

def deco(func):
    def wrapper(*args, **kwargs):
        print(print_now(),func(*args, **kwargs))#,'\n'
        return func(*args, **kwargs)
    return wrapper

def deco_print(print_info):
    def deco(func):
        def wrapper(*args, **kwargs):
            print(print_now(),print_info,func(*args, **kwargs))
            return func(*args, **kwargs)
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
    
    #print u"%s 分类共有 %s" %(self.logo,str(len(category_list)))
