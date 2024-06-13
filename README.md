# py3-nes
NES(FC) Emulator in Python 3.12 + jitclass

#features
1. cpu6502 running
2. Limited graphics
3. Limited sound support
4. 1P control
5. interpreted way to implement the instructions too slow. 
6. support MAPPER in mapper...

#performance
1. CPU: 5ms / frame
2. PPU: 15~35ms / frame

try:
nuitka --msvc=14.2 --module --show-progress --output-dir=out *.py