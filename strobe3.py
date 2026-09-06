import emu
rom=open('M27512_PM5139_V13.bin','rb').read()
STUBS={0x5187,0x51A1,0x51C1,0x5194,0x37DB,0x392F,0x5061,0x5066,0x645A,0x64F7}
DATA=[(0x44A7,0x4EBD),(0x4EE7,0x5060),(0x7752,0x8870),(0x9F47,0xFFFF),(0x2019,0x2040)]
HW={1:'RAM U4 D101',2:'RAM U4 D102/D103',3:'Ampl.Mod./PulseGen',4:'Burst-Logik',
    5:'Mod.Oszillator',6:'TWS D331',7:'DC-Generator',8:'Sweep-Ausgang',9:'Ampl.Controller'}
def wild(pc): return any(a<=pc<=b for a,b in DATA)
def run(token=None, budget=60000):
    c=emu.CPU(rom)
    for a in range(0x8000,0x9000): c.xram[a]=0x10
    c.run(0x3C2E)
    if token is not None:
        c.ram[0x10]=token; c.ram[0x11]=0; c.ram[0x15]=1; c.ram[0x16]=0
        try: c.run(0x71BF, stubs=STUBS, maxsteps=300000)
        except Exception: return None
    c.trace_xram=[]; c.push(0xFF); c.push(0xFF); c.pc=0x090C
    for i in range(budget):
        if c.pc==0xFFFF or wild(c.pc): break
        if c.pc in STUBS:
            h=c.pop(); l=c.pop(); c.pc=(h<<8)|l; continue
        try: c.step()
        except Exception: break
    s=[]
    for d,v in c.trace_xram:
        if d>=0x8000:
            n=(d>>8)&0x0F
            if n and n not in s: s.append(n)
    return s
tab={}; a=0x7752
while True:
    nm=rom[a:a+14].split(b'\x00')[0].decode('latin1')
    if not nm: break
    for t in (rom[a+14],rom[a+15]):
        if t not in (0,0xFF): tab.setdefault(t,nm)
    a+=16
base=run() or []
print('Basis-Strobes:', [HW.get(x,x) for x in base])
print()
for t in sorted(tab):
    if t>=0x40: continue
    s=run(t)
    if s is None: continue
    neu=[x for x in s if x not in base]
    if neu: print('  %02X  %-13s -> %s'%(t,tab[t],', '.join(HW.get(x,'STR%d'%x) for x in neu)))
