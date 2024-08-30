# py3-nes
NES(FC) Emulator in Python 3.12.2 + jitclass

#features
1. cpu6502 running
2. Limited graphics
3. Limited sound support（ch0-3）
4. 1P control
Player1   B   A  SE  ST  UP  DN  LF  RT  BBB AAA
P1_PAD   'k','j','v','b','w','s','a','d','i','u'
5. interpreted way to implement the instructions too slow. 
6. support MAPPER in mapper...

#performance
1. CPU: 5ms / frame
2. PPU: 10~35ms / frame

#environment
Python 3.12.2
numba           0.60.0
numpy           1.26.4
opencv-python   4.9.0.80
keyboard        0.13.5
python-rtmidi   1.5.8

#reference
VirtuaNES
basicNES
NESTER