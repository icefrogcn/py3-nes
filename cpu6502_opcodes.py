# -*- coding; UTF-8 -*-
from numba import jit
from numba import int8,uint8,int16,uint16
import numpy as np
import numba as nb
import time

#CPU Memory Map
'''
' Declarations for M6502
' Addressing Modes
'''
ADR_ABS = 0
ADR_ABSX = 1
ADR_ABSY  = 2
ADR_IMM = 3
ADR_IMP = 4
ADR_INDABSX = 5
ADR_IND = 6
ADR_INDX = 7
ADR_INDY = 8
ADR_INDZP = 9
ADR_REL = 10
ADR_ZP = 11
ADR_ZPX = 12
ADR_ZPY = 13



' Opcodes'
INS_ADC = 0
INS_AND = 1
INS_ASL = 2
INS_ASLA = 3
INS_BCC = 4
INS_BCS = 5
INS_BEQ = 6
INS_BIT = 7
INS_BMI = 8
INS_BNE = 9
INS_BPL = 10
INS_BRK = 11
INS_BVC = 12
INS_BVS = 13
INS_CLC = 14
INS_CLD = 15
INS_CLI = 16
INS_CLV = 17
INS_CMP = 18
INS_CPX = 19
INS_CPY = 20
INS_DEC = 21
INS_DEA = 22
INS_DEX = 23
INS_DEY = 24
INS_EOR = 25
INS_INC = 26
INS_INX = 27
INS_INY = 28
INS_JMP = 29
INS_JSR = 30
INS_LDA = 31
INS_LDX = 32
INS_LDY = 33
INS_LSR = 34
INS_LSRA = 35
INS_NOP = 36
INS_ORA = 37
INS_PHA = 38
INS_PHP = 39
INS_PLA = 40
INS_PLP = 41
INS_ROL = 42
INS_ROLA = 43
INS_ROR = 44
INS_RORA = 45
INS_RTI = 46
INS_RTS = 47
INS_SBC = 48
INS_SEC = 49
INS_SED = 50
INS_SEI = 51
INS_STA = 52
INS_STX = 53
INS_STY = 54
INS_TAX = 55
INS_TAY = 56
INS_TSX = 57
INS_TXA = 58
INS_TXS = 59
INS_TYA = 60
INS_BRA = 61
INS_INA = 62
INS_PHX = 63
INS_PLX = 64
INS_PHY = 65
INS_PLY = 66
Ticks = np.zeros(0x100,np.uint8)#[0] * 0x100 # As Byte
addrmode = np.zeros(0x100,np.uint8)#[0] * 0x100 # As Byte
instruction = np.zeros(0x100,np.uint8)#[0] * 0x100 # As Byte
#Ticks = [0] * 0x100 # As Byte
#addrmode = [0] * 0x100 # As Byte
#instruction = [0] * 0x100 # As Byte

#@jit
def init6502():
      global Ticks,addrmode,instruction
      Ticks[0x0] = 7; instruction[0x0] = INS_BRK; addrmode[0x0] = ADR_IMP
      Ticks[0x1] = 6; instruction[0x1] = INS_ORA; addrmode[0x1] = ADR_INDX
      Ticks[0x2] = 2; instruction[0x2] = INS_NOP; addrmode[0x2] = ADR_IMP
      Ticks[0x3] = 2; instruction[0x3] = INS_NOP; addrmode[0x3] = ADR_IMP
      Ticks[0x4] = 3; instruction[0x4] = INS_NOP; addrmode[0x4] = ADR_ZP
      Ticks[0x5] = 3; instruction[0x5] = INS_ORA; addrmode[0x5] = ADR_ZP
      Ticks[0x6] = 5; instruction[0x6] = INS_ASL; addrmode[0x6] = ADR_ZP
      Ticks[0x7] = 2; instruction[0x7] = INS_NOP; addrmode[0x7] = ADR_IMP
      Ticks[0x8] = 3; instruction[0x8] = INS_PHP; addrmode[0x8] = ADR_IMP
      Ticks[0x9] = 3; instruction[0x9] = INS_ORA; addrmode[0x9] = ADR_IMM
      Ticks[0xA] = 2; instruction[0xA] = INS_ASLA; addrmode[0xA] = ADR_IMP
      Ticks[0xB] = 2; instruction[0xB] = INS_NOP; addrmode[0xB] = ADR_IMP
      Ticks[0xC] = 4; instruction[0xC] = INS_NOP; addrmode[0xC] = ADR_ABS
      Ticks[0xD] = 4; instruction[0xD] = INS_ORA; addrmode[0xD] = ADR_ABS
      Ticks[0xE] = 6; instruction[0xE] = INS_ASL; addrmode[0xE] = ADR_ABS
      Ticks[0xF] = 2; instruction[0xF] = INS_NOP; addrmode[0xF] = ADR_IMP
      Ticks[0x10] = 2; instruction[0x10] = INS_BPL; addrmode[0x10] = ADR_REL
      Ticks[0x11] = 5; instruction[0x11] = INS_ORA; addrmode[0x11] = ADR_INDY
      Ticks[0x12] = 3; instruction[0x12] = INS_ORA; addrmode[0x12] = ADR_INDZP
      Ticks[0x13] = 2; instruction[0x13] = INS_NOP; addrmode[0x13] = ADR_IMP
      Ticks[0x14] = 3; instruction[0x14] = INS_NOP; addrmode[0x14] = ADR_ZP
      Ticks[0x15] = 4; instruction[0x15] = INS_ORA; addrmode[0x15] = ADR_ZPX
      Ticks[0x16] = 6; instruction[0x16] = INS_ASL; addrmode[0x16] = ADR_ZPX
      Ticks[0x17] = 2; instruction[0x17] = INS_NOP; addrmode[0x17] = ADR_IMP
      Ticks[0x18] = 2; instruction[0x18] = INS_CLC; addrmode[0x18] = ADR_IMP
      Ticks[0x19] = 4; instruction[0x19] = INS_ORA; addrmode[0x19] = ADR_ABSY
      Ticks[0x1A] = 2; instruction[0x1A] = INS_INA; addrmode[0x1A] = ADR_IMP
      Ticks[0x1B] = 2; instruction[0x1B] = INS_NOP; addrmode[0x1B] = ADR_IMP
      Ticks[0x1C] = 4; instruction[0x1C] = INS_NOP; addrmode[0x1C] = ADR_ABS
      Ticks[0x1D] = 4; instruction[0x1D] = INS_ORA; addrmode[0x1D] = ADR_ABSX
      Ticks[0x1E] = 7; instruction[0x1E] = INS_ASL; addrmode[0x1E] = ADR_ABSX
      Ticks[0x1F] = 2; instruction[0x1F] = INS_NOP; addrmode[0x1F] = ADR_IMP
      Ticks[0x20] = 6; instruction[0x20] = INS_JSR; addrmode[0x20] = ADR_ABS
      Ticks[0x21] = 6; instruction[0x21] = INS_AND; addrmode[0x21] = ADR_INDX
      Ticks[0x22] = 2; instruction[0x22] = INS_NOP; addrmode[0x22] = ADR_IMP
      Ticks[0x23] = 2; instruction[0x23] = INS_NOP; addrmode[0x23] = ADR_IMP
      Ticks[0x24] = 3; instruction[0x24] = INS_BIT; addrmode[0x24] = ADR_ZP
      Ticks[0x25] = 3; instruction[0x25] = INS_AND; addrmode[0x25] = ADR_ZP
      Ticks[0x26] = 5; instruction[0x26] = INS_ROL; addrmode[0x26] = ADR_ZP
      Ticks[0x27] = 2; instruction[0x27] = INS_NOP; addrmode[0x27] = ADR_IMP
      Ticks[0x28] = 4; instruction[0x28] = INS_PLP; addrmode[0x28] = ADR_IMP
      Ticks[0x29] = 3; instruction[0x29] = INS_AND; addrmode[0x29] = ADR_IMM
      Ticks[0x2A] = 2; instruction[0x2A] = INS_ROLA; addrmode[0x2A] = ADR_IMP
      Ticks[0x2B] = 2; instruction[0x2B] = INS_NOP; addrmode[0x2B] = ADR_IMP
      Ticks[0x2C] = 4; instruction[0x2C] = INS_BIT; addrmode[0x2C] = ADR_ABS
      Ticks[0x2D] = 4; instruction[0x2D] = INS_AND; addrmode[0x2D] = ADR_ABS
      Ticks[0x2E] = 6; instruction[0x2E] = INS_ROL; addrmode[0x2E] = ADR_ABS
      Ticks[0x2F] = 2; instruction[0x2F] = INS_NOP; addrmode[0x2F] = ADR_IMP
      Ticks[0x30] = 2; instruction[0x30] = INS_BMI; addrmode[0x30] = ADR_REL
      Ticks[0x31] = 5; instruction[0x31] = INS_AND; addrmode[0x31] = ADR_INDY
      Ticks[0x32] = 3; instruction[0x32] = INS_AND; addrmode[0x32] = ADR_INDZP
      Ticks[0x33] = 2; instruction[0x33] = INS_NOP; addrmode[0x33] = ADR_IMP
      Ticks[0x34] = 4; instruction[0x34] = INS_BIT; addrmode[0x34] = ADR_ZPX
      Ticks[0x35] = 4; instruction[0x35] = INS_AND; addrmode[0x35] = ADR_ZPX
      Ticks[0x36] = 6; instruction[0x36] = INS_ROL; addrmode[0x36] = ADR_ZPX
      Ticks[0x37] = 2; instruction[0x37] = INS_NOP; addrmode[0x37] = ADR_IMP
      Ticks[0x38] = 2; instruction[0x38] = INS_SEC; addrmode[0x38] = ADR_IMP
      Ticks[0x39] = 4; instruction[0x39] = INS_AND; addrmode[0x39] = ADR_ABSY
      Ticks[0x3A] = 2; instruction[0x3A] = INS_DEA; addrmode[0x3A] = ADR_IMP
      Ticks[0x3B] = 2; instruction[0x3B] = INS_NOP; addrmode[0x3B] = ADR_IMP
      Ticks[0x3C] = 4; instruction[0x3C] = INS_BIT; addrmode[0x3C] = ADR_ABSX
      Ticks[0x3D] = 4; instruction[0x3D] = INS_AND; addrmode[0x3D] = ADR_ABSX
      Ticks[0x3E] = 7; instruction[0x3E] = INS_ROL; addrmode[0x3E] = ADR_ABSX
      Ticks[0x3F] = 2; instruction[0x3F] = INS_NOP; addrmode[0x3F] = ADR_IMP
      Ticks[0x40] = 6; instruction[0x40] = INS_RTI; addrmode[0x40] = ADR_IMP
      Ticks[0x41] = 6; instruction[0x41] = INS_EOR; addrmode[0x41] = ADR_INDX
      Ticks[0x42] = 2; instruction[0x42] = INS_NOP; addrmode[0x42] = ADR_IMP
      Ticks[0x43] = 2; instruction[0x43] = INS_NOP; addrmode[0x43] = ADR_IMP
      Ticks[0x44] = 2; instruction[0x44] = INS_NOP; addrmode[0x44] = ADR_IMP
      Ticks[0x45] = 3; instruction[0x45] = INS_EOR; addrmode[0x45] = ADR_ZP
      Ticks[0x46] = 5; instruction[0x46] = INS_LSR; addrmode[0x46] = ADR_ZP
      Ticks[0x47] = 2; instruction[0x47] = INS_NOP; addrmode[0x47] = ADR_IMP
      Ticks[0x48] = 3; instruction[0x48] = INS_PHA; addrmode[0x48] = ADR_IMP
      Ticks[0x49] = 3; instruction[0x49] = INS_EOR; addrmode[0x49] = ADR_IMM
      Ticks[0x4A] = 2; instruction[0x4A] = INS_LSRA; addrmode[0x4A] = ADR_IMP
      Ticks[0x4B] = 2; instruction[0x4B] = INS_NOP; addrmode[0x4B] = ADR_IMP
      Ticks[0x4C] = 3; instruction[0x4C] = INS_JMP; addrmode[0x4C] = ADR_ABS
      Ticks[0x4D] = 4; instruction[0x4D] = INS_EOR; addrmode[0x4D] = ADR_ABS
      Ticks[0x4E] = 6; instruction[0x4E] = INS_LSR; addrmode[0x4E] = ADR_ABS
      Ticks[0x4F] = 2; instruction[0x4F] = INS_NOP; addrmode[0x4F] = ADR_IMP
      Ticks[0x50] = 2; instruction[0x50] = INS_BVC; addrmode[0x50] = ADR_REL
      Ticks[0x51] = 5; instruction[0x51] = INS_EOR; addrmode[0x51] = ADR_INDY
      Ticks[0x52] = 3; instruction[0x52] = INS_EOR; addrmode[0x52] = ADR_INDZP
      Ticks[0x53] = 2; instruction[0x53] = INS_NOP; addrmode[0x53] = ADR_IMP
      Ticks[0x54] = 2; instruction[0x54] = INS_NOP; addrmode[0x54] = ADR_IMP
      Ticks[0x55] = 4; instruction[0x55] = INS_EOR; addrmode[0x55] = ADR_ZPX
      Ticks[0x56] = 6; instruction[0x56] = INS_LSR; addrmode[0x56] = ADR_ZPX
      Ticks[0x57] = 2; instruction[0x57] = INS_NOP; addrmode[0x57] = ADR_IMP
      Ticks[0x58] = 2; instruction[0x58] = INS_CLI; addrmode[0x58] = ADR_IMP
      Ticks[0x59] = 4; instruction[0x59] = INS_EOR; addrmode[0x59] = ADR_ABSY
      Ticks[0x5A] = 3; instruction[0x5A] = INS_PHY; addrmode[0x5A] = ADR_IMP
      Ticks[0x5B] = 2; instruction[0x5B] = INS_NOP; addrmode[0x5B] = ADR_IMP
      Ticks[0x5C] = 2; instruction[0x5C] = INS_NOP; addrmode[0x5C] = ADR_IMP
      Ticks[0x5D] = 4; instruction[0x5D] = INS_EOR; addrmode[0x5D] = ADR_ABSX
      Ticks[0x5E] = 7; instruction[0x5E] = INS_LSR; addrmode[0x5E] = ADR_ABSX
      Ticks[0x5F] = 2; instruction[0x5F] = INS_NOP; addrmode[0x5F] = ADR_IMP
      Ticks[0x60] = 6; instruction[0x60] = INS_RTS; addrmode[0x60] = ADR_IMP
      Ticks[0x61] = 6; instruction[0x61] = INS_ADC; addrmode[0x61] = ADR_INDX
      Ticks[0x62] = 2; instruction[0x62] = INS_NOP; addrmode[0x62] = ADR_IMP
      Ticks[0x63] = 2; instruction[0x63] = INS_NOP; addrmode[0x63] = ADR_IMP
      Ticks[0x64] = 3; instruction[0x64] = INS_NOP; addrmode[0x64] = ADR_ZP
      Ticks[0x65] = 3; instruction[0x65] = INS_ADC; addrmode[0x65] = ADR_ZP
      Ticks[0x66] = 5; instruction[0x66] = INS_ROR; addrmode[0x66] = ADR_ZP
      Ticks[0x67] = 2; instruction[0x67] = INS_NOP; addrmode[0x67] = ADR_IMP
      Ticks[0x68] = 4; instruction[0x68] = INS_PLA; addrmode[0x68] = ADR_IMP
      Ticks[0x69] = 3; instruction[0x69] = INS_ADC; addrmode[0x69] = ADR_IMM
      Ticks[0x6A] = 2; instruction[0x6A] = INS_RORA; addrmode[0x6A] = ADR_IMP
      Ticks[0x6B] = 2; instruction[0x6B] = INS_NOP; addrmode[0x6B] = ADR_IMP
      Ticks[0x6C] = 5; instruction[0x6C] = INS_JMP; addrmode[0x6C] = ADR_IND
      Ticks[0x6D] = 4; instruction[0x6D] = INS_ADC; addrmode[0x6D] = ADR_ABS
      Ticks[0x6E] = 6; instruction[0x6E] = INS_ROR; addrmode[0x6E] = ADR_ABS
      Ticks[0x6F] = 2; instruction[0x6F] = INS_NOP; addrmode[0x6F] = ADR_IMP
      Ticks[0x70] = 2; instruction[0x70] = INS_BVS; addrmode[0x70] = ADR_REL
      Ticks[0x71] = 5; instruction[0x71] = INS_ADC; addrmode[0x71] = ADR_INDY
      Ticks[0x72] = 3; instruction[0x72] = INS_ADC; addrmode[0x72] = ADR_INDZP
      Ticks[0x73] = 2; instruction[0x73] = INS_NOP; addrmode[0x73] = ADR_IMP
      Ticks[0x74] = 4; instruction[0x74] = INS_NOP; addrmode[0x74] = ADR_ZPX
      Ticks[0x75] = 4; instruction[0x75] = INS_ADC; addrmode[0x75] = ADR_ZPX
      Ticks[0x76] = 6; instruction[0x76] = INS_ROR; addrmode[0x76] = ADR_ZPX
      Ticks[0x77] = 2; instruction[0x77] = INS_NOP; addrmode[0x77] = ADR_IMP
      Ticks[0x78] = 2; instruction[0x78] = INS_SEI; addrmode[0x78] = ADR_IMP
      Ticks[0x79] = 4; instruction[0x79] = INS_ADC; addrmode[0x79] = ADR_ABSY
      Ticks[0x7A] = 4; instruction[0x7A] = INS_PLY; addrmode[0x7A] = ADR_IMP
      Ticks[0x7B] = 2; instruction[0x7B] = INS_NOP; addrmode[0x7B] = ADR_IMP
      Ticks[0x7C] = 6; instruction[0x7C] = INS_JMP; addrmode[0x7C] = ADR_INDABSX
      Ticks[0x7D] = 4; instruction[0x7D] = INS_ADC; addrmode[0x7D] = ADR_ABSX
      Ticks[0x7E] = 7; instruction[0x7E] = INS_ROR; addrmode[0x7E] = ADR_ABSX
      Ticks[0x7F] = 2; instruction[0x7F] = INS_NOP; addrmode[0x7F] = ADR_IMP
      Ticks[0x80] = 2; instruction[0x80] = INS_BRA; addrmode[0x80] = ADR_REL
      Ticks[0x81] = 6; instruction[0x81] = INS_STA; addrmode[0x81] = ADR_INDX
      Ticks[0x82] = 2; instruction[0x82] = INS_NOP; addrmode[0x82] = ADR_IMP
      Ticks[0x83] = 2; instruction[0x83] = INS_NOP; addrmode[0x83] = ADR_IMP
      Ticks[0x84] = 2; instruction[0x84] = INS_STY; addrmode[0x84] = ADR_ZP
      Ticks[0x85] = 2; instruction[0x85] = INS_STA; addrmode[0x85] = ADR_ZP
      Ticks[0x86] = 2; instruction[0x86] = INS_STX; addrmode[0x86] = ADR_ZP
      Ticks[0x87] = 2; instruction[0x87] = INS_NOP; addrmode[0x87] = ADR_IMP
      Ticks[0x88] = 2; instruction[0x88] = INS_DEY; addrmode[0x88] = ADR_IMP
      Ticks[0x89] = 2; instruction[0x89] = INS_BIT; addrmode[0x89] = ADR_IMM
      Ticks[0x8A] = 2; instruction[0x8A] = INS_TXA; addrmode[0x8A] = ADR_IMP
      Ticks[0x8B] = 2; instruction[0x8B] = INS_NOP; addrmode[0x8B] = ADR_IMP
      Ticks[0x8C] = 4; instruction[0x8C] = INS_STY; addrmode[0x8C] = ADR_ABS
      Ticks[0x8D] = 4; instruction[0x8D] = INS_STA; addrmode[0x8D] = ADR_ABS
      Ticks[0x8E] = 4; instruction[0x8E] = INS_STX; addrmode[0x8E] = ADR_ABS
      Ticks[0x8F] = 2; instruction[0x8F] = INS_NOP; addrmode[0x8F] = ADR_IMP
      Ticks[0x90] = 2; instruction[0x90] = INS_BCC; addrmode[0x90] = ADR_REL
      Ticks[0x91] = 6; instruction[0x91] = INS_STA; addrmode[0x91] = ADR_INDY
      Ticks[0x92] = 3; instruction[0x92] = INS_STA; addrmode[0x92] = ADR_INDZP
      Ticks[0x93] = 2; instruction[0x93] = INS_NOP; addrmode[0x93] = ADR_IMP
      Ticks[0x94] = 4; instruction[0x94] = INS_STY; addrmode[0x94] = ADR_ZPX
      Ticks[0x95] = 4; instruction[0x95] = INS_STA; addrmode[0x95] = ADR_ZPX
      Ticks[0x96] = 4; instruction[0x96] = INS_STX; addrmode[0x96] = ADR_ZPY
      Ticks[0x97] = 2; instruction[0x97] = INS_NOP; addrmode[0x97] = ADR_IMP
      Ticks[0x98] = 2; instruction[0x98] = INS_TYA; addrmode[0x98] = ADR_IMP
      Ticks[0x99] = 5; instruction[0x99] = INS_STA; addrmode[0x99] = ADR_ABSY
      Ticks[0x9A] = 2; instruction[0x9A] = INS_TXS; addrmode[0x9A] = ADR_IMP
      Ticks[0x9B] = 2; instruction[0x9B] = INS_NOP; addrmode[0x9B] = ADR_IMP
      Ticks[0x9C] = 4; instruction[0x9C] = INS_NOP; addrmode[0x9C] = ADR_ABS
      Ticks[0x9D] = 5; instruction[0x9D] = INS_STA; addrmode[0x9D] = ADR_ABSX
      Ticks[0x9E] = 5; instruction[0x9E] = INS_NOP; addrmode[0x9E] = ADR_ABSX
      Ticks[0x9F] = 2; instruction[0x9F] = INS_NOP; addrmode[0x9F] = ADR_IMP
      Ticks[0xA0] = 3; instruction[0xA0] = INS_LDY; addrmode[0xA0] = ADR_IMM
      Ticks[0xA1] = 6; instruction[0xA1] = INS_LDA; addrmode[0xA1] = ADR_INDX
      Ticks[0xA2] = 3; instruction[0xA2] = INS_LDX; addrmode[0xA2] = ADR_IMM
      Ticks[0xA3] = 2; instruction[0xA3] = INS_NOP; addrmode[0xA3] = ADR_IMP
      Ticks[0xA4] = 3; instruction[0xA4] = INS_LDY; addrmode[0xA4] = ADR_ZP
      Ticks[0xA5] = 3; instruction[0xA5] = INS_LDA; addrmode[0xA5] = ADR_ZP
      Ticks[0xA6] = 3; instruction[0xA6] = INS_LDX; addrmode[0xA6] = ADR_ZP
      Ticks[0xA7] = 2; instruction[0xA7] = INS_NOP; addrmode[0xA7] = ADR_IMP
      Ticks[0xA8] = 2; instruction[0xA8] = INS_TAY; addrmode[0xA8] = ADR_IMP
      Ticks[0xA9] = 3; instruction[0xA9] = INS_LDA; addrmode[0xA9] = ADR_IMM
      Ticks[0xAA] = 2; instruction[0xAA] = INS_TAX; addrmode[0xAA] = ADR_IMP
      Ticks[0xAB] = 2; instruction[0xAB] = INS_NOP; addrmode[0xAB] = ADR_IMP
      Ticks[0xAC] = 4; instruction[0xAC] = INS_LDY; addrmode[0xAC] = ADR_ABS
      Ticks[0xAD] = 4; instruction[0xAD] = INS_LDA; addrmode[0xAD] = ADR_ABS
      Ticks[0xAE] = 4; instruction[0xAE] = INS_LDX; addrmode[0xAE] = ADR_ABS
      Ticks[0xAF] = 2; instruction[0xAF] = INS_NOP; addrmode[0xAF] = ADR_IMP
      Ticks[0xB0] = 2; instruction[0xB0] = INS_BCS; addrmode[0xB0] = ADR_REL
      Ticks[0xB1] = 5; instruction[0xB1] = INS_LDA; addrmode[0xB1] = ADR_INDY
      Ticks[0xB2] = 3; instruction[0xB2] = INS_LDA; addrmode[0xB2] = ADR_INDZP
      Ticks[0xB3] = 2; instruction[0xB3] = INS_NOP; addrmode[0xB3] = ADR_IMP
      Ticks[0xB4] = 4; instruction[0xB4] = INS_LDY; addrmode[0xB4] = ADR_ZPX
      Ticks[0xB5] = 4; instruction[0xB5] = INS_LDA; addrmode[0xB5] = ADR_ZPX
      Ticks[0xB6] = 4; instruction[0xB6] = INS_LDX; addrmode[0xB6] = ADR_ZPY
      Ticks[0xB7] = 2; instruction[0xB7] = INS_NOP; addrmode[0xB7] = ADR_IMP
      Ticks[0xB8] = 2; instruction[0xB8] = INS_CLV; addrmode[0xB8] = ADR_IMP
      Ticks[0xB9] = 4; instruction[0xB9] = INS_LDA; addrmode[0xB9] = ADR_ABSY
      Ticks[0xBA] = 2; instruction[0xBA] = INS_TSX; addrmode[0xBA] = ADR_IMP
      Ticks[0xBB] = 2; instruction[0xBB] = INS_NOP; addrmode[0xBB] = ADR_IMP
      Ticks[0xBC] = 4; instruction[0xBC] = INS_LDY; addrmode[0xBC] = ADR_ABSX
      Ticks[0xBD] = 4; instruction[0xBD] = INS_LDA; addrmode[0xBD] = ADR_ABSX
      Ticks[0xBE] = 4; instruction[0xBE] = INS_LDX; addrmode[0xBE] = ADR_ABSY
      Ticks[0xBF] = 2; instruction[0xBF] = INS_NOP; addrmode[0xBF] = ADR_IMP
      Ticks[0xC0] = 3; instruction[0xC0] = INS_CPY; addrmode[0xC0] = ADR_IMM
      Ticks[0xC1] = 6; instruction[0xC1] = INS_CMP; addrmode[0xC1] = ADR_INDX
      Ticks[0xC2] = 2; instruction[0xC2] = INS_NOP; addrmode[0xC2] = ADR_IMP
      Ticks[0xC3] = 2; instruction[0xC3] = INS_NOP; addrmode[0xC3] = ADR_IMP
      Ticks[0xC4] = 3; instruction[0xC4] = INS_CPY; addrmode[0xC4] = ADR_ZP
      Ticks[0xC5] = 3; instruction[0xC5] = INS_CMP; addrmode[0xC5] = ADR_ZP
      Ticks[0xC6] = 5; instruction[0xC6] = INS_DEC; addrmode[0xC6] = ADR_ZP
      Ticks[0xC7] = 2; instruction[0xC7] = INS_NOP; addrmode[0xC7] = ADR_IMP
      Ticks[0xC8] = 2; instruction[0xC8] = INS_INY; addrmode[0xC8] = ADR_IMP
      Ticks[0xC9] = 3; instruction[0xC9] = INS_CMP; addrmode[0xC9] = ADR_IMM
      Ticks[0xCA] = 2; instruction[0xCA] = INS_DEX; addrmode[0xCA] = ADR_IMP
      Ticks[0xCB] = 2; instruction[0xCB] = INS_NOP; addrmode[0xCB] = ADR_IMP
      Ticks[0xCC] = 4; instruction[0xCC] = INS_CPY; addrmode[0xCC] = ADR_ABS
      Ticks[0xCD] = 4; instruction[0xCD] = INS_CMP; addrmode[0xCD] = ADR_ABS
      Ticks[0xCE] = 6; instruction[0xCE] = INS_DEC; addrmode[0xCE] = ADR_ABS
      Ticks[0xCF] = 2; instruction[0xCF] = INS_NOP; addrmode[0xCF] = ADR_IMP
      Ticks[0xD0] = 2; instruction[0xD0] = INS_BNE; addrmode[0xD0] = ADR_REL
      Ticks[0xD1] = 5; instruction[0xD1] = INS_CMP; addrmode[0xD1] = ADR_INDY
      Ticks[0xD2] = 3; instruction[0xD2] = INS_CMP; addrmode[0xD2] = ADR_INDZP
      Ticks[0xD3] = 2; instruction[0xD3] = INS_NOP; addrmode[0xD3] = ADR_IMP
      Ticks[0xD4] = 2; instruction[0xD4] = INS_NOP; addrmode[0xD4] = ADR_IMP
      Ticks[0xD5] = 4; instruction[0xD5] = INS_CMP; addrmode[0xD5] = ADR_ZPX
      Ticks[0xD6] = 6; instruction[0xD6] = INS_DEC; addrmode[0xD6] = ADR_ZPX
      Ticks[0xD7] = 2; instruction[0xD7] = INS_NOP; addrmode[0xD7] = ADR_IMP
      Ticks[0xD8] = 2; instruction[0xD8] = INS_CLD; addrmode[0xD8] = ADR_IMP
      Ticks[0xD9] = 4; instruction[0xD9] = INS_CMP; addrmode[0xD9] = ADR_ABSY
      Ticks[0xDA] = 3; instruction[0xDA] = INS_PHX; addrmode[0xDA] = ADR_IMP
      Ticks[0xDB] = 2; instruction[0xDB] = INS_NOP; addrmode[0xDB] = ADR_IMP
      Ticks[0xDC] = 2; instruction[0xDC] = INS_NOP; addrmode[0xDC] = ADR_IMP
      Ticks[0xDD] = 4; instruction[0xDD] = INS_CMP; addrmode[0xDD] = ADR_ABSX
      Ticks[0xDE] = 7; instruction[0xDE] = INS_DEC; addrmode[0xDE] = ADR_ABSX
      Ticks[0xDF] = 2; instruction[0xDF] = INS_NOP; addrmode[0xDF] = ADR_IMP
      Ticks[0xE0] = 3; instruction[0xE0] = INS_CPX; addrmode[0xE0] = ADR_IMM
      Ticks[0xE1] = 6; instruction[0xE1] = INS_SBC; addrmode[0xE1] = ADR_INDX
      Ticks[0xE2] = 2; instruction[0xE2] = INS_NOP; addrmode[0xE2] = ADR_IMP
      Ticks[0xE3] = 2; instruction[0xE3] = INS_NOP; addrmode[0xE3] = ADR_IMP
      Ticks[0xE4] = 3; instruction[0xE4] = INS_CPX; addrmode[0xE4] = ADR_ZP
      Ticks[0xE5] = 3; instruction[0xE5] = INS_SBC; addrmode[0xE5] = ADR_ZP
      Ticks[0xE6] = 5; instruction[0xE6] = INS_INC; addrmode[0xE6] = ADR_ZP
      Ticks[0xE7] = 2; instruction[0xE7] = INS_NOP; addrmode[0xE7] = ADR_IMP
      Ticks[0xE8] = 2; instruction[0xE8] = INS_INX; addrmode[0xE8] = ADR_IMP
      Ticks[0xE9] = 3; instruction[0xE9] = INS_SBC; addrmode[0xE9] = ADR_IMM
      Ticks[0xEA] = 2; instruction[0xEA] = INS_NOP; addrmode[0xEA] = ADR_IMP
      Ticks[0xEB] = 2; instruction[0xEB] = INS_NOP; addrmode[0xEB] = ADR_IMP
      Ticks[0xEC] = 4; instruction[0xEC] = INS_CPX; addrmode[0xEC] = ADR_ABS
      Ticks[0xED] = 4; instruction[0xED] = INS_SBC; addrmode[0xED] = ADR_ABS
      Ticks[0xEE] = 6; instruction[0xEE] = INS_INC; addrmode[0xEE] = ADR_ABS
      Ticks[0xEF] = 2; instruction[0xEF] = INS_NOP; addrmode[0xEF] = ADR_IMP
      Ticks[0xF0] = 2; instruction[0xF0] = INS_BEQ; addrmode[0xF0] = ADR_REL
      Ticks[0xF1] = 5; instruction[0xF1] = INS_SBC; addrmode[0xF1] = ADR_INDY
      Ticks[0xF2] = 3; instruction[0xF2] = INS_SBC; addrmode[0xF2] = ADR_INDZP
      Ticks[0xF3] = 2; instruction[0xF3] = INS_NOP; addrmode[0xF3] = ADR_IMP
      Ticks[0xF4] = 2; instruction[0xF4] = INS_NOP; addrmode[0xF4] = ADR_IMP
      Ticks[0xF5] = 4; instruction[0xF5] = INS_SBC; addrmode[0xF5] = ADR_ZPX
      Ticks[0xF6] = 6; instruction[0xF6] = INS_INC; addrmode[0xF6] = ADR_ZPX
      Ticks[0xF7] = 2; instruction[0xF7] = INS_NOP; addrmode[0xF7] = ADR_IMP
      Ticks[0xF8] = 2; instruction[0xF8] = INS_SED; addrmode[0xF8] = ADR_IMP
      Ticks[0xF9] = 4; instruction[0xF9] = INS_SBC; addrmode[0xF9] = ADR_ABSY
      Ticks[0xFA] = 4; instruction[0xFA] = INS_PLX; addrmode[0xFA] = ADR_IMP
      Ticks[0xFB] = 2; instruction[0xFB] = INS_NOP; addrmode[0xFB] = ADR_IMP
      Ticks[0xFC] = 2; instruction[0xFC] = INS_NOP; addrmode[0xFC] = ADR_IMP
      Ticks[0xFD] = 4; instruction[0xFD] = INS_SBC; addrmode[0xFD] = ADR_ABSX
      Ticks[0xFE] = 7; instruction[0xFE] = INS_INC; addrmode[0xFE] = ADR_ABSX
      Ticks[0xFF] = 2; instruction[0xFF] = INS_NOP; addrmode[0xFF] = ADR_IMP
      return Ticks, instruction, addrmode




def tt(t):
      Ticks = t 
      start = time.clock()
      for i in range(10000000):
            aa = t[0xFF]
      print(time.clock() - start)

if __name__ == '__main__':
      #nes_ROM_data = read_file_to_array['mario.nes']
      #nes_head = nes_ROM_data[:0x20]
      init6502()
      #print Ticks

      commands = commands(Ticks, instruction, addrmode)
      t = TicksC(Ticks)
      tt(Ticks)
    









        
