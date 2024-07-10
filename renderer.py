# -*- coding: UTF-8 -*-
import os,re

import pyglet

import numpy as np
#from numba import jit

#自定义类

#import mmc








def fillTLook():
    tLook = []#[0] * 0x80000
    for b1 in range(0x100):             #= 0 To 255
        for b2 in range(0x100):              #= 0 To 255
            for X in range(0x8):                #= 0 To 7
                c = 1 if b1 & pow2[X] else  0
                c += 2 if b2 & pow2[X]  else 0
                tLook.append(c)
                #tLook[b1 * 2048 + b2 * 8 + X] = c
    return tLook



#@window.event  #装饰器
def on_draw():#重写on_draw方法
    window.clear() #窗口清除
    background_color = [0, 255, 255]
    background = pyglet.image.ImageData(720, 768, "RGB", bytes(np.zeros((720, 768, 3),np.uint8)))
    background.blit(0,0) #重绘窗口

if __name__ == '__main__':

    window = pyglet.window.Window(visible=False)
    window.set_size(720, 768)
    window.on_draw = on_draw
    window.set_visible(True)
    window.clear()
    #frame = pyglet.graphics.Batch()
    background_color = [0, 255, 255]
    background = pyglet.image.ImageData(720, 768, "RGB", bytes(background_color * 720 * 768))
    background.blit(0,0)
    #pyglet.sprite.Sprite(background, batch=frame)
    pyglet.app.run()
    print(1)
    
    
        










        
