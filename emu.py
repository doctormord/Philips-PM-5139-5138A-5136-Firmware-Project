"""A minimal MCS-51 interpreter for the PM5139 firmware."""
class CPU:
    def __init__(self, rom):
        self.rom = rom
        self.ram = bytearray(256)      # internes RAM 00-FF (indirekt)
        self.sfr = bytearray(256)      # direkt >= 80h
        self.xram = bytearray(0x10000) # externes RAM / EEPROM
        self.pc = 0
        self.sfr[0x81] = 0x6B          # SP
        self.trace_xram = []
        self.calls = 0
    # --- accesses -------------------------------------------------
    def bank(self): return (self.sfr[0xD0] >> 3) & 3
    def getR(self, n): return self.ram[self.bank()*8 + n]
    def setR(self, n, v): self.ram[self.bank()*8 + n] = v & 0xFF
    def dget(self, a):  return self.sfr[a] if a >= 0x80 else self.ram[a]
    def dset(self, a, v):
        v &= 0xFF
        if a >= 0x80:
            self.sfr[a] = v
            if a == 0x99: self.ti_at = getattr(self,'ticks',0) + 12  # sending takes time
        else: self.ram[a] = v
    def iget(self, a): return self.ram[a]
    def iset(self, a, v): self.ram[a] = v & 0xFF
    def bitaddr(self, b):
        if b >= 0x80: return (b & 0xF8, b & 7, True)
        return (0x20 + (b >> 3), b & 7, False)
    def bget(self, b):
        base, n, sfr = self.bitaddr(b)
        v = self.sfr[base] if sfr else self.ram[base]
        return (v >> n) & 1
    def bset(self, b, val):
        base, n, sfr = self.bitaddr(b)
        tgt = self.sfr if sfr else self.ram
        if val: tgt[base] |= (1 << n)
        else:   tgt[base] &= ~(1 << n) & 0xFF
    # accumulator / PSW
    def A(self): return self.sfr[0xE0]
    def setA(self, v):
        v &= 0xFF; self.sfr[0xE0] = v
        p = bin(v).count('1') & 1
        self.sfr[0xD0] = (self.sfr[0xD0] & 0xFE) | p
    def C(self): return (self.sfr[0xD0] >> 7) & 1
    def setC(self, v):
        if v: self.sfr[0xD0] |= 0x80
        else: self.sfr[0xD0] &= 0x7F
    def dptr(self): return (self.sfr[0x83] << 8) | self.sfr[0x82]
    def setdptr(self, v):
        self.sfr[0x83] = (v >> 8) & 0xFF; self.sfr[0x82] = v & 0xFF
    def push(self, v):
        self.sfr[0x81] = (self.sfr[0x81] + 1) & 0xFF
        self.ram[self.sfr[0x81]] = v & 0xFF
    def pop(self):
        v = self.ram[self.sfr[0x81]]
        self.sfr[0x81] = (self.sfr[0x81] - 1) & 0xFF
        return v

    # --- execution ------------------------------------------------
    def step(self):
        # a rough model of the peripherals: timers run, the transmitter finishes at once
        self.ticks = getattr(self, 'ticks', 0) + 1
        if not getattr(self,'real_timers',False) and self.ticks & 0x1F == 0:
            t = self.sfr[0x88]                 # TCON
            if t & 0x10: self.sfr[0x88] = t | 0x20   # TR0 -> TF0
            t = self.sfr[0x88]
            if t & 0x40: self.sfr[0x88] = t | 0x80   # TR1 -> TF1
        if getattr(self,'ti_at',None) is not None and self.ticks >= self.ti_at:
            self.sfr[0x98] |= 0x02; self.ti_at = None
        m = self.rom; pc = self.pc; op = m[pc]
        lo = op & 0x0F; hi = op & 0xF0
        def b1(): return m[(pc+1) & 0xFFFF]
        def b2(): return m[(pc+2) & 0xFFFF]
        def rel(x): return x - 256 if x > 127 else x
        n = lo & 7           # Rn-Nummer bei lo>=8
        # --- operand helpers for the regular groups
        def src(ln):         # lo 4..F for "A,<src>"
            if ln == 4: return b1(), 2
            if ln == 5: return self.dget(b1()), 2
            if ln in (6,7): return self.iget(self.getR(ln-6)), 1
            return self.getR(ln-8), 1
        A = self.A()
        if op == 0x00: self.pc = pc+1; return
        lo5 = op & 0x1F
        if lo5 == 0x01:    # AJMP
            self.pc = ((pc+2) & 0xF800) | ((op & 0xE0) << 3) | b1(); return
        if lo5 == 0x11:    # ACALL
            t = ((pc+2) & 0xF800) | ((op & 0xE0) << 3) | b1()
            self.push((pc+2) & 0xFF); self.push(((pc+2) >> 8) & 0xFF)
            self.pc = t; self.calls += 1; return
        if op == 0x02: self.pc = (b1()<<8)|b2(); return
        if op == 0x12:
            self.push((pc+3) & 0xFF); self.push(((pc+3) >> 8) & 0xFF)
            self.pc = (b1()<<8)|b2(); self.calls += 1; return
        if op in (0x22, 0x32):
            h = self.pop(); l = self.pop(); self.pc = (h<<8)|l; return
        if op == 0x03: self.setA(((A>>1)|(A<<7))&0xFF); self.pc=pc+1; return
        if op == 0x23: self.setA(((A<<1)|(A>>7))&0xFF); self.pc=pc+1; return
        if op == 0x13:
            c=self.C(); self.setC(A&1); self.setA((A>>1)|(c<<7)); self.pc=pc+1; return
        if op == 0x33:
            c=self.C(); self.setC((A>>7)&1); self.setA(((A<<1)|c)&0xFF); self.pc=pc+1; return
        if op == 0x04: self.setA(A+1); self.pc=pc+1; return
        if op == 0x14: self.setA(A-1); self.pc=pc+1; return
        if op == 0xE4: self.setA(0); self.pc=pc+1; return
        if op == 0xF4: self.setA(~A); self.pc=pc+1; return
        if op == 0xC4: self.setA(((A<<4)|(A>>4))&0xFF); self.pc=pc+1; return
        if op == 0xC3: self.setC(0); self.pc=pc+1; return
        if op == 0xD3: self.setC(1); self.pc=pc+1; return
        if op == 0xB3: self.setC(1-self.C()); self.pc=pc+1; return
        if op == 0xA3: self.setdptr((self.dptr()+1)&0xFFFF); self.pc=pc+1; return
        if op == 0x90: self.setdptr((b1()<<8)|b2()); self.pc=pc+3; return
        if op == 0x93: self.setA(m[(self.dptr()+A)&0xFFFF]); self.pc=pc+1; return
        if op == 0x83: self.setA(m[(pc+1+A)&0xFFFF]); self.pc=pc+1; return
        if op == 0x73: self.pc=(self.dptr()+A)&0xFFFF; return
        if op == 0xE0: self.setA(self.xram[self.dptr()]); self.pc=pc+1; return
        if op == 0xF0:
            d=self.dptr(); self.trace_xram.append((d,A))
            if d < 0x8000: self.xram[d]=A
            self.pc=pc+1; return
        if op in (0xE2,0xE3): self.setA(self.xram[self.getR(op-0xE2)]); self.pc=pc+1; return
        if op in (0xF2,0xF3): self.xram[self.getR(op-0xF2)]=A; self.pc=pc+1; return
        if op == 0xA4:
            b=self.sfr[0xF0]; r=A*b; self.setA(r&0xFF); self.sfr[0xF0]=(r>>8)&0xFF
            self.setC(0); self.pc=pc+1; return
        if op == 0x84:
            b=self.sfr[0xF0]
            if b==0: self.sfr[0xD0]|=0x04
            else: self.setA(A//b); self.sfr[0xF0]=A%b
            self.setC(0); self.pc=pc+1; return
        if op == 0xD4:  # DA A (vereinfacht)
            a=A
            if (a & 0x0F) > 9 or (self.sfr[0xD0]>>6)&1: a += 6
            if ((a>>4) & 0x0F) > 9 or self.C(): a += 0x60; self.setC(1)
            self.setA(a); self.pc=pc+1; return
        # jump instructions
        if op == 0x80: self.pc = pc+2+rel(b1()); return
        if op in (0x40,0x50): 
            t=pc+2+rel(b1()); self.pc = t if (self.C()==(1 if op==0x40 else 0)) else pc+2; return
        if op in (0x60,0x70):
            t=pc+2+rel(b1()); z=(A==0)
            self.pc = t if (z if op==0x60 else not z) else pc+2; return
        if op in (0x20,0x30):
            v=self.bget(b1()); t=pc+3+rel(b2())
            self.pc = t if (v if op==0x20 else not v) else pc+3; return
        if op == 0x10:
            v=self.bget(b1()); t=pc+3+rel(b2())
            if v: self.bset(b1(),0); self.pc=t
            else: self.pc=pc+3
            return
        self.pc = -1  # handled by group2
        self._group2(op, pc, b1, b2, rel, n, src)

    def _group2(self, op, pc, b1, b2, rel, n, src):
        m=self.rom; A=self.A(); lo=op&0x0F; hi=op&0xF0
        def alu(f, carry_in=0):
            if lo>=4:
                v,ln = src(lo); r = f(A, v, carry_in); self.pc=pc+ln
                return r
        # ADD/ADDC/SUBB
        if hi in (0x20,0x30,0x90) and lo>=4:
            v,ln = src(lo)
            ci = self.C() if hi in (0x30,0x90) else 0
            if hi==0x90:
                r = A - v - ci
                self.setC(1 if r<0 else 0)
                ac = 1 if ((A & 0x0F) - (v & 0x0F) - ci) < 0 else 0
                ov = ((A^v)&(A^(r&0xFF)))>>7 & 1
            else:
                r = A + v + ci
                self.setC(1 if r>0xFF else 0)
                ac = 1 if ((A & 0x0F) + (v & 0x0F) + ci) > 0x0F else 0
                ov = ((~(A^v))&(A^(r&0xFF)))>>7 & 1
            self.sfr[0xD0] = (self.sfr[0xD0] & ~0x40 & 0xFF) | (ac << 6)
            self.sfr[0xD0] = (self.sfr[0xD0]&~0x04)|(ov<<2)
            self.setA(r); self.pc=pc+ln; return
        if hi in (0x40,0x50,0x60) and lo>=4 and op not in (0x42,0x43,0x52,0x53,0x62,0x63):
            v,ln = src(lo)
            self.setA({0x40:A|v,0x50:A&v,0x60:A^v}[hi]); self.pc=pc+ln; return
        if op in (0x42,0x52,0x62):
            d=b1(); cur=self.dget(d)
            self.dset(d, {0x42:cur|A,0x52:cur&A,0x62:cur^A}[op]); self.pc=pc+2; return
        if op in (0x43,0x53,0x63):
            d=b1(); i=b2(); cur=self.dget(d)
            self.dset(d, {0x43:cur|i,0x53:cur&i,0x63:cur^i}[op]); self.pc=pc+3; return
        # MOV A,<src> / MOV <dst>,A
        if hi==0xE0 and lo>=4: v,ln=src(lo); self.setA(v); self.pc=pc+ln; return
        if hi==0xF0 and lo>=5:
            if lo==5: self.dset(b1(),A); self.pc=pc+2
            elif lo in (6,7): self.iset(self.getR(lo-6),A); self.pc=pc+1
            else: self.setR(lo-8,A); self.pc=pc+1
            return
        # MOV <dst>,#imm
        if hi==0x70 and lo>=4:
            if lo==4: self.setA(b1()); self.pc=pc+2
            elif lo==5: self.dset(b1(),b2()); self.pc=pc+3
            elif lo in (6,7): self.iset(self.getR(lo-6),b1()); self.pc=pc+2
            else: self.setR(lo-8,b1()); self.pc=pc+2
            return
        # MOV direct,<src>
        if hi==0x80 and lo>=5:
            if lo==5: self.dset(b2(), self.dget(b1())); self.pc=pc+3
            elif lo in (6,7): self.dset(b1(), self.iget(self.getR(lo-6))); self.pc=pc+2
            else: self.dset(b1(), self.getR(lo-8)); self.pc=pc+2
            return
        # MOV <dst>,direct
        if hi==0xA0 and lo>=6:
            if lo in (6,7): self.iset(self.getR(lo-6), self.dget(b1())); self.pc=pc+2
            else: self.setR(lo-8, self.dget(b1())); self.pc=pc+2
            return
        # INC/DEC
        if hi in (0x00,0x10) and lo>=5:
            d = 1 if hi==0x00 else -1
            if lo==5: self.dset(b1(), self.dget(b1())+d); self.pc=pc+2
            elif lo in (6,7):
                a=self.getR(lo-6); self.iset(a, self.iget(a)+d); self.pc=pc+1
            else: self.setR(lo-8, self.getR(lo-8)+d); self.pc=pc+1
            return
        # CJNE
        if hi==0xB0 and lo>=4:
            if lo==4: x,y,ln = A,b1(),3
            elif lo==5: x,y,ln = A,self.dget(b1()),3
            elif lo in (6,7): x,y,ln = self.iget(self.getR(lo-6)),b1(),3
            else: x,y,ln = self.getR(lo-8),b1(),3
            self.setC(1 if x<y else 0)
            self.pc = pc+ln+rel(b2()) if x!=y else pc+ln; return
        # DJNZ
        if op==0xD5:
            d=b1(); v=(self.dget(d)-1)&0xFF; self.dset(d,v)
            self.pc = pc+3+rel(b2()) if v else pc+3; return
        if hi==0xD0 and lo>=8:
            v=(self.getR(lo-8)-1)&0xFF; self.setR(lo-8,v)
            self.pc = pc+2+rel(b1()) if v else pc+2; return
        # PUSH/POP/XCH/XCHD
        if op==0xC0: self.push(self.dget(b1())); self.pc=pc+2; return
        if op==0xD0: self.dset(b1(), self.pop()); self.pc=pc+2; return
        if hi==0xC0 and lo>=5:
            if lo==5: t=self.dget(b1()); self.dset(b1(),A); self.setA(t); self.pc=pc+2
            elif lo in (6,7):
                a=self.getR(lo-6); t=self.iget(a); self.iset(a,A); self.setA(t); self.pc=pc+1
            else:
                t=self.getR(lo-8); self.setR(lo-8,A); self.setA(t); self.pc=pc+1
            return
        if op in (0xD6,0xD7):
            a=self.getR(op-0xD6); t=self.iget(a)
            self.iset(a,(t&0xF0)|(A&0x0F)); self.setA((A&0xF0)|(t&0x0F)); self.pc=pc+1; return
        # bit instructions
        if op==0xC2: self.bset(b1(),0); self.pc=pc+2; return
        if op==0xD2: self.bset(b1(),1); self.pc=pc+2; return
        if op==0xB2: self.bset(b1(),1-self.bget(b1())); self.pc=pc+2; return
        if op==0xA2: self.setC(self.bget(b1())); self.pc=pc+2; return
        if op==0x92: self.bset(b1(),self.C()); self.pc=pc+2; return
        if op==0x72: self.setC(self.C()|self.bget(b1())); self.pc=pc+2; return
        if op==0xA0: self.setC(self.C()|(1-self.bget(b1()))); self.pc=pc+2; return
        if op==0x82: self.setC(self.C()&self.bget(b1())); self.pc=pc+2; return
        if op==0xB0: self.setC(self.C()&(1-self.bget(b1()))); self.pc=pc+2; return
        if op==0xA5: self.pc=pc+1; return
        raise Exception('unbekannter Opcode %02X @ %04X' % (op, pc))

    def run(self, addr, maxsteps=2_000_000, stubs=()):
        """Calls addr like an LCALL and runs until the matching RET."""
        self.push(0xFF); self.push(0xFF)   # Ruecksprungmarke FFFF
        self.pc = addr; depth = 0
        for i in range(maxsteps):
            if self.pc == 0xFFFF: return i
            if self.pc in stubs:            # Unterprogramm ueberspringen
                h=self.pop(); l=self.pop(); self.pc=(h<<8)|l; continue
            self.step()
        raise Exception('Zeitueberschreitung bei PC=%04X' % self.pc)
