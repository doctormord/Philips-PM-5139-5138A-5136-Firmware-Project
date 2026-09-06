import collections
from mcs51 import decode

VEC = [0x0000,0x0003,0x000B,0x0013,0x001B,0x0023,0x002B]

class Prog:
    def __init__(self, path):
        self.mem = open(path,'rb').read()
        self.insn = {}
        self.calls = collections.defaultdict(set)
        self.jumps = collections.defaultdict(set)
        self.entries = set()
        self.ijmp = []
        self.tables = {}      # table addr -> (stride, count)
        self.work = []

    def trace(self, seeds):
        self.work += list(seeds)
        while self.work:
            pc = self.work.pop()
            while True:
                if pc in self.insn or pc > 0xFFFD: break
                l,t,tg,k = decode(self.mem, pc)
                self.insn[pc] = (l,t,tg,k)
                if k=='call':
                    self.calls[tg].add(pc); self.entries.add(tg); self.work.append(tg)
                elif k in ('jmp','cjmp'):
                    self.jumps[tg].add(pc)
                    if tg not in self.insn: self.work.append(tg)
                    if k=='jmp': break
                elif k=='ret': break
                elif k=='ijmp':
                    self.ijmp.append(pc); self.do_table(pc); break
                pc += l

    def do_table(self, pc):
        # find preceding MOV DPTR,#imm  (search back up to 20 bytes among known insns)
        prev = [a for a in self.insn if a < pc and a > pc-24]
        dp = None
        for a in sorted(prev):
            if self.mem[a] == 0x90 and self.insn[a][0]==3:
                dp = (self.mem[a+1]<<8)|self.mem[a+2]
        if dp is None: return
        # determine stride from scaling ops between
        stride = 2
        ops = [self.mem[a] for a in sorted(prev) if a > (pc-14)]
        if 0xA4 in ops: stride = 3            # MUL AB (B=#3)
        elif ops.count(0x23) + ops.count(0x33) >= 2: stride = 4  # RL A twice
        # walk table
        n = 0; a = dp
        while n < 64:
            op = self.mem[a]
            if stride == 3 and op != 0x02: break
            if stride == 2 and not ((op & 0x1F) == 0x01 or op == 0x80 or op == 0x00): break
            if op == 0x00: a += stride; n += 1; continue
            if stride == 4 and not (op in (0x02,0x12) or (op&0x1F) in (0x01,0x11)): break
            l,t,tg,k = decode(self.mem, a)
            if tg is not None and tg < 0x10000:
                self.work.append(a); self.entries.add(tg)
            a += stride; n += 1
        self.tables[dp] = (stride, n)

def load(v, extra=()):
    p = Prog('M27512_PM5139_V%s.bin' % v)
    p.entries.update(VEC)
    p.trace(list(VEC)+list(extra))
    return p

if __name__ == '__main__':
    for v in ('13','15'):
        p = load(v)
        cov = sum(l for l,_,_,_ in p.insn.values())
        print('V%s: %d Instr, %d Code-Bytes (%.1f%%), %d Funktionen, Tabellen: %s'
              % (v, len(p.insn), cov, cov*100/65536, len(p.entries),
                 {'%04X'%k:v2 for k,v2 in p.tables.items()}))
