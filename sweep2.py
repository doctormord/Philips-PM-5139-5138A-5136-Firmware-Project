import emu
rom=open('M27512_PM5139_V13.bin','rb').read()
STUBS={0x5187,0x51A1,0x51C1,0x5194,0x37DB,0x392F,0x5061,0x5066}
def build(pre=None, mod=None):
    c=emu.CPU(rom); c.run(0x3C2E)
    if pre: pre(c)
    if mod: mod(c)
    c.run(0x3381, stubs=STUBS, maxsteps=200000)
    return bytes(c.ram[0x30:0x44])
pre = lambda c: c.ram.__setitem__(0x2E, c.ram[0x2E] | 0x04)   # 2Eh.2 setzen
base=build(pre)
print('base with 2Eh.2:', ' '.join('%02X'%b for b in base))
print()
for byte in range(0x20,0x30):
    for bit in range(8):
        if (byte,bit)==(0x2E,2): continue
        def mod(c,b=byte,n=bit): c.ram[b] ^= (1<<n)
        try: out=build(pre,mod)
        except Exception: print('  %02Xh.%d -> Fehler'%(byte,bit)); continue
        d=[(0x30+i,base[i],out[i]) for i in range(20) if base[i]!=out[i]]
        if d: print('  %02Xh.%d  '%(byte,bit) + '  '.join('%02X: %02X->%02X'%x for x in d))
