import emu
rom=open('M27512_PM5139_V13.bin','rb').read()
STUBS={0x5187,0x51A1,0x51C1,0x5194,0x37DB,0x392F,0x5061,0x5066,0x645A,0x64F7,0x2DC1,0x2C55}
def run(token=None):
    c=emu.CPU(rom); c.run(0x3C2E)
    if token is not None:
        c.ram[0x10]=token; c.ram[0x11]=0; c.ram[0x15]=1; c.ram[0x16]=0
        try: c.run(0x71BF, stubs=STUBS, maxsteps=200000)
        except Exception as e: return None,str(e)
    try: c.run(0x3381, stubs=STUBS, maxsteps=200000)
    except Exception as e: return None,str(e)
    return bytes(c.ram[0x30:0x44]), (bytes(c.ram[0x20:0x30]))
base,bflags=run()
# Tokens aus der Befehlstabelle einlesen
tab={}
a=0x7752
while True:
    name=rom[a:a+14].split(b'\x00')[0].decode('latin1')
    if not name: break
    for t in (rom[a+14], rom[a+15]):
        if t not in (0x00,0xFF): tab.setdefault(t,name)
    a+=16
print('Token  Befehl        Anzeige-Aenderung')
for t in sorted(tab):
    if t>=0x40: continue
    out,fl=run(t)
    if out is None: continue
    d=[(0x30+i,base[i],out[i]) for i in range(20) if base[i]!=out[i]]
    if d:
        print('  %02X  %-12s %s'%(t,tab[t],'  '.join('%02X:%02X>%02X'%x for x in d)))
