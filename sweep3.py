import emu, itertools, sys
rom=open('M27512_PM5139_V13.bin','rb').read()
STUBS={0x5187,0x51A1,0x51C1,0x5194,0x37DB,0x392F,0x5061,0x5066}
def build(sets):
    c=emu.CPU(rom); c.run(0x3C2E)
    for b,n in sets: c.ram[b] ^= (1<<n)
    c.run(0x3381, stubs=STUBS, maxsteps=100000)
    return bytes(c.ram[0x30:0x44])
base=build([])
# flags that have no effect on their own
solo_wirkung=set()
for b in range(0x20,0x30):
    for n in range(8):
        try:
            if build([(b,n)])!=base: solo_wirkung.add((b,n))
        except Exception: pass
stumm=[(b,n) for b in range(0x20,0x30) for n in range(8) if (b,n) not in solo_wirkung]
print('%d Flags wirken allein, %d bleiben stumm'%(len(solo_wirkung),len(stumm)))
print()
print('Paar-Suche: welches Vorbedingungs-Flag schaltet ein stummes Flag frei?')
gefunden={}
for pre in [(b,n) for b in range(0x20,0x30) for n in range(8)]:
    try: pbase=build([pre])
    except Exception: continue
    for t in stumm:
        if t==pre: continue
        try: out=build([pre,t])
        except Exception: continue
        if out!=pbase:
            d=[(0x30+i,pbase[i],out[i]) for i in range(20) if pbase[i]!=out[i]]
            gefunden.setdefault(t,[]).append((pre,d))
for t in sorted(gefunden):
    pres=gefunden[t]
    pre,d=pres[0]
    print('  %02Xh.%d  (frei ab %02Xh.%d, %d Vorbed.)  '%(t[0],t[1],pre[0],pre[1],len(pres))
          + '  '.join('%02X: %02X->%02X'%x for x in d))
