"""Minimal MCS-51 (8051) disassembler."""

SFR = {0x80:'P0',0x81:'SP',0x82:'DPL',0x83:'DPH',0x87:'PCON',0x88:'TCON',0x89:'TMOD',
0x8A:'TL0',0x8B:'TL1',0x8C:'TH0',0x8D:'TH1',0x90:'P1',0x98:'SCON',0x99:'SBUF',
0xA0:'P2',0xA8:'IE',0xB0:'P3',0xB8:'IP',0xC8:'T2CON',0xC9:'T2MOD',0xCA:'RCAP2L',
0xCB:'RCAP2H',0xCC:'TL2',0xCD:'TH2',0xD0:'PSW',0xE0:'ACC',0xF0:'B'}

BITNAMES = {
0x88:'IT0',0x89:'IE0',0x8A:'IT1',0x8B:'IE1',0x8C:'TR0',0x8D:'TF0',0x8E:'TR1',0x8F:'TF1',
0x98:'RI',0x99:'TI',0x9A:'RB8',0x9B:'TB8',0x9C:'REN',0x9D:'SM2',0x9E:'SM1',0x9F:'SM0',
0xA8:'EX0',0xA9:'ET0',0xAA:'EX1',0xAB:'ET1',0xAC:'ES',0xAD:'ET2',0xAF:'EA',
0xB8:'PX0',0xB9:'PT0',0xBA:'PX1',0xBB:'PT1',0xBC:'PS',0xBD:'PT2',
0xD0:'P',0xD2:'OV',0xD3:'RS0',0xD4:'RS1',0xD5:'F0',0xD6:'AC',0xD7:'CY',
0xC8:'CPRL2',0xC9:'CT2',0xCA:'TR2',0xCB:'EXEN2',0xCC:'TCLK',0xCD:'RCLK',0xCE:'EXF2',0xCF:'TF2',
}

def dname(a):
    if a in SFR: return SFR[a]
    if a >= 0x80: return 'SFR_%02X' % a
    return '%02Xh' % a

def bname(a):
    if a in BITNAMES: return BITNAMES[a]
    if a >= 0x80:
        base = a & 0xF8
        return '%s.%d' % (dname(base), a & 7)
    return '%02Xh.%d' % (0x20 + (a >> 3), a & 7)

# (mnemonic-template, length)  placeholders: {d}=direct {b}=bit {i}=imm8 {I}=imm16 {r}=rel-target {a}=addr11/16
TAB = {}
def _s(op, m, l): TAB[op] = (m, l)

for n in range(8):
    _s(0x08+n, 'INC   R%d'%n,1); _s(0x18+n,'DEC   R%d'%n,1)
    _s(0x28+n, 'ADD   A,R%d'%n,1); _s(0x38+n,'ADDC  A,R%d'%n,1)
    _s(0x48+n, 'ORL   A,R%d'%n,1); _s(0x58+n,'ANL   A,R%d'%n,1)
    _s(0x68+n, 'XRL   A,R%d'%n,1); _s(0x78+n,'MOV   R%d,#{i}'%n,2)
    _s(0x88+n, 'MOV   {d},R%d'%n,2); _s(0x98+n,'SUBB  A,R%d'%n,1)
    _s(0xA8+n, 'MOV   R%d,{d}'%n,2); _s(0xB8+n,'CJNE  R%d,#{i},{r}'%n,3)
    _s(0xC8+n, 'XCH   A,R%d'%n,1); _s(0xD8+n,'DJNZ  R%d,{r}'%n,2)
    _s(0xE8+n, 'MOV   A,R%d'%n,1); _s(0xF8+n,'MOV   R%d,A'%n,1)
for i in (0,1):
    _s(0x06+i,'INC   @R%d'%i,1); _s(0x16+i,'DEC   @R%d'%i,1)
    _s(0x26+i,'ADD   A,@R%d'%i,1); _s(0x36+i,'ADDC  A,@R%d'%i,1)
    _s(0x46+i,'ORL   A,@R%d'%i,1); _s(0x56+i,'ANL   A,@R%d'%i,1)
    _s(0x66+i,'XRL   A,@R%d'%i,1); _s(0x76+i,'MOV   @R%d,#{i}'%i,2)
    _s(0x86+i,'MOV   {d},@R%d'%i,2); _s(0x96+i,'SUBB  A,@R%d'%i,1)
    _s(0xA6+i,'MOV   @R%d,{d}'%i,2); _s(0xB6+i,'CJNE  @R%d,#{i},{r}'%i,3)
    _s(0xC6+i,'XCH   A,@R%d'%i,1); _s(0xD6+i,'XCHD  A,@R%d'%i,1)
    _s(0xE6+i,'MOV   A,@R%d'%i,1); _s(0xF6+i,'MOV   @R%d,A'%i,1)
    _s(0xE2+i,'MOVX  A,@R%d'%i,1); _s(0xF2+i,'MOVX  @R%d,A'%i,1)
one = {0x00:'NOP',0x03:'RR    A',0x04:'INC   A',0x13:'RRC   A',0x14:'DEC   A',
 0x22:'RET',0x23:'RL    A',0x32:'RETI',0x33:'RLC   A',0x73:'JMP   @A+DPTR',
 0x83:'MOVC  A,@A+PC',0x84:'DIV   AB',0x93:'MOVC  A,@A+DPTR',0xA3:'INC   DPTR',
 0xA4:'MUL   AB',0xB3:'CPL   C',0xC3:'CLR   C',0xC4:'SWAP  A',0xD3:'SETB  C',
 0xD4:'DA    A',0xE0:'MOVX  A,@DPTR',0xE4:'CLR   A',0xF0:'MOVX  @DPTR,A',
 0xF4:'CPL   A',0xA5:'DB    0A5h'}
for k,v in one.items(): _s(k,v,1)
d1 = {0x05:'INC   {d}',0x15:'DEC   {d}',0x25:'ADD   A,{d}',0x35:'ADDC  A,{d}',
 0x42:'ORL   {d},A',0x45:'ORL   A,{d}',0x52:'ANL   {d},A',0x55:'ANL   A,{d}',
 0x62:'XRL   {d},A',0x65:'XRL   A,{d}',0x75:None,0x85:None,0x95:'SUBB  A,{d}',
 0xC0:'PUSH  {d}',0xC5:'XCH   A,{d}',0xD0:'POP   {d}',0xE5:'MOV   A,{d}',0xF5:'MOV   {d},A'}
for k,v in d1.items():
    if v: _s(k,v,2)
_s(0x75,'MOV   {d},#{i}',3)
_s(0x85,'MOV   {d2},{d}',3)   # 85 src dst
_s(0x43,'ORL   {d},#{i}',3); _s(0x53,'ANL   {d},#{i}',3); _s(0x63,'XRL   {d},#{i}',3)
_s(0x24,'ADD   A,#{i}',2); _s(0x34,'ADDC  A,#{i}',2); _s(0x44,'ORL   A,#{i}',2)
_s(0x54,'ANL   A,#{i}',2); _s(0x64,'XRL   A,#{i}',2); _s(0x74,'MOV   A,#{i}',2)
_s(0x94,'SUBB  A,#{i}',2); _s(0x90,'MOV   DPTR,#{I}',3)
_s(0x02,'LJMP  {a}',3); _s(0x12,'LCALL {a}',3)
_s(0x80,'SJMP  {r}',2); _s(0x40,'JC    {r}',2); _s(0x50,'JNC   {r}',2)
_s(0x60,'JZ    {r}',2); _s(0x70,'JNZ   {r}',2)
_s(0x10,'JBC   {b},{r}',3); _s(0x20,'JB    {b},{r}',3); _s(0x30,'JNB   {b},{r}',3)
_s(0x72,'ORL   C,{b}',2); _s(0x82,'ANL   C,{b}',2); _s(0x92,'MOV   {b},C',2)
_s(0xA0,'ORL   C,/{b}',2); _s(0xA2,'MOV   C,{b}',2); _s(0xB0,'ANL   C,/{b}',2)
_s(0xB2,'CPL   {b}',2); _s(0xC2,'CLR   {b}',2); _s(0xD2,'SETB  {b}',2)
_s(0xB4,'CJNE  A,#{i},{r}',3); _s(0xB5,'CJNE  A,{d},{r}',3)
_s(0xD5,'DJNZ  {d},{r}',3)
for h in range(8):
    _s(h*0x20+0x01,'AJMP  {a}',2); _s(h*0x20+0x11,'ACALL {a}',2)

def decode(mem, pc):
    """returns (length, text, targets, kind) kind in call/jmp/cjmp/ret/normal"""
    op = mem[pc]
    tmpl, ln = TAB[op]
    b = mem[pc:pc+ln]
    tgt = None; kind='normal'
    t = tmpl
    lo = op & 0x1F
    if lo in (0x01,0x11):   # AJMP/ACALL
        tgt = ((pc+2) & 0xF800) | ((op & 0xE0) << 3) | b[1]
        t = t.replace('{a}', 'X%04Xh' % tgt)
        kind = 'jmp' if lo==0x01 else 'call'
    elif op in (0x02,0x12):
        tgt = (b[1]<<8)|b[2]
        t = t.replace('{a}','X%04Xh' % tgt)
        kind = 'jmp' if op==0x02 else 'call'
    else:
        i = 1
        if op == 0x85:
            t = t.replace('{d2}', dname(b[2])).replace('{d}', dname(b[1])); i = 3
        else:
            if '{b}' in t: t = t.replace('{b}', bname(b[i])); i += 1
            if '{d}' in t: t = t.replace('{d}', dname(b[i])); i += 1
            if '{I}' in t: t = t.replace('{I}', '%04Xh' % ((b[i]<<8)|b[i+1])); i += 2
            if '{i}' in t: t = t.replace('{i}', '0%02Xh'%b[i] if b[i]>=0xA0 else '%02Xh'%b[i]); i += 1
        if '{r}' in t:
            rel = b[i]; rel = rel-256 if rel>127 else rel
            tgt = (pc + ln + rel) & 0xFFFF
            t = t.replace('{r}', 'X%04Xh' % tgt)
            kind = 'cjmp' if op != 0x80 else 'jmp'
    if op in (0x22,0x32): kind='ret'
    if op == 0x73: kind='ijmp'
    return ln, t, tgt, kind


# --- machine cycles ---------------------------------------------------
# One machine cycle is 12 oscillator periods, so at the 12 MHz of the
# PM5139 (crystal G816 on unit 2) exactly 1 us. The emulators count one
# tick per *instruction*, which is fine for orderings but wrong by about
# a factor of two for absolute timings; this table is what makes real
# times measurable. Figures from the MCS-51 data sheet.
CYCLES = [1] * 256
def _c(ops, n):
    for op in ops: CYCLES[op] = n

_c([0x02, 0x12, 0x22, 0x32], 2)                 # LJMP LCALL RET RETI
_c([h*0x20 + 0x01 for h in range(8)], 2)        # AJMP
_c([h*0x20 + 0x11 for h in range(8)], 2)        # ACALL
_c([0x80, 0x40, 0x50, 0x60, 0x70, 0x73], 2)     # SJMP JC JNC JZ JNZ JMP @A+DPTR
_c([0x10, 0x20, 0x30], 2)                       # JBC JB JNB
_c([0xB4, 0xB5, 0xB6, 0xB7], 2)                 # CJNE A / @Ri
_c(range(0xB8, 0xC0), 2)                        # CJNE Rn
_c([0xD5], 2); _c(range(0xD8, 0xE0), 2)         # DJNZ direct / Rn
_c([0x83, 0x93], 2)                             # MOVC
_c([0xE0, 0xF0, 0xE2, 0xE3, 0xF2, 0xF3], 2)     # MOVX
_c([0xA3, 0x90], 2)                             # INC DPTR, MOV DPTR,#imm16
_c([0xC0, 0xD0], 2)                             # PUSH POP
_c([0x75, 0x85], 2)                             # MOV direct,#imm / direct,direct
_c(range(0x88, 0x90), 2); _c(range(0xA8, 0xB0), 2)   # MOV direct,Rn / Rn,direct
_c([0x86, 0x87, 0xA6, 0xA7], 2)                 # MOV direct,@Ri / @Ri,direct
_c([0x43, 0x53, 0x63], 2)                       # ORL/ANL/XRL direct,#imm
_c([0x72, 0x82, 0xA0, 0xB0, 0x92], 2)           # ORL/ANL C,bit and MOV bit,C
_c([0x84, 0xA4], 4)                             # DIV MUL

def cycles(op):
    """Machine cycles of one instruction, by opcode."""
    return CYCLES[op]
