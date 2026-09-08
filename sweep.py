import emu, copy
rom=open('M27512_PM5139_V13.bin','rb').read()
STUBS={0x5187,0x51A1,0x51C1,0x5194,0x37DB,0x392F,0x5061,0x5066}
def build(mod=None):
    c=emu.CPU(rom); c.run(0x3C2E)
    if mod: mod(c)
    c.run(0x3381, stubs=STUBS, maxsteps=200000)
    return bytes(c.ram[0x30:0x44])
base=build()
print('Basis:', ' '.join('%02X'%b for b in base))
print()
print('Flag        Puffer-Aenderung')
hits=0
for byte in range(0x20,0x30):
    for bit in range(8):
        def mod(c,b=byte,n=bit): c.ram[b] ^= (1<<n)
        try: out=build(mod)
        except Exception as e: print('  %02Xh.%d  -> Fehler'%(byte,bit)); continue
        d=[(0x30+i,base[i],out[i]) for i in range(20) if base[i]!=out[i]]
        if d:
            hits+=1
            print('  %02Xh.%d  '%(byte,bit) + '  '.join('%02X: %02X->%02X'%x for x in d))
print()
print('%d of 128 flags affect the display'%hits)
