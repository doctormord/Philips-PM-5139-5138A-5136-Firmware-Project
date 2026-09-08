"""Builds a synthetic D310 image with arbitrary curves.

CAUTION: since the device was really read out, `D310_image.bin` is the
X28C64 as read (section 32). This script therefore writes to
`D310_image_synthetic.bin` and no longer overwrites the real image.
The synthetic one only serves as a counter-check.
"""
import emu, math
rom=open('M27512_PM5139_V13.bin','rb').read()
SLOTS=15
def pack(samples):
    """1024 values of 10 bit -> 1280 bytes in the format of the instrument."""
    out=bytearray()
    for i in range(0,1024,4):
        grp=samples[i:i+4]
        ext=0
        for k,v in enumerate(grp):
            out.append((v>>2)&0xFF)          # high byte
            ext |= (v & 3) << (2*k)          # two extra bits
        out.append(ext)
    # order: 4 high bytes, then the collecting byte
    fixed=bytearray()
    for i in range(0,len(out),5):
        blk=out[i:i+5]; fixed += blk
    return bytes(fixed)
def curve(kind):
    if kind=='sine':  return [int(511+511*math.sin(2*math.pi*i/1024)) for i in range(1024)]
    if kind=='triangle':return [int(abs(1023-2*abs(i*2-512)%2048)) if False else int(1023*(1-abs(2*i/1024-1))) for i in range(1024)]
    if kind=='ramp':  return [i for i in range(1024)]
    if kind=='noise':
        st=0xACE1; o=[]
        for i in range(1024):
            st=((st>>1)^(-(st&1)&0xB400))&0xFFFF; o.append(st&0x3FF)
        return o
    return [512]*1024
kinds=['sine','triangle','ramp','noise']+['empty']*11
ee=bytearray(0x8000)
for n in range(1,SLOTS+1):
    data=pack(curve(kinds[n-1]))
    base=((n-1)*5+1)*0x100
    ee[base:base+1280]=data
ee[0]=0x8F                     # 32K fit, 15 slots
# have the original code compute the checksum and min/max per slot
c=emu.CPU(rom); c.xram[:0x8000]=ee
for n in range(1,SLOTS+1):
    c.setA(n); c.run(0x95C1, maxsteps=200000)
    chk=c.getR(4); lo=(c.ram[0x1A],c.ram[0x1B]); hi=(c.ram[0x1C],c.ram[0x1D])
    d=7+(n-1)*5
    ee[d]=chk; ee[d+1],ee[d+2]=lo; ee[d+3],ee[d+4]=hi
    if n<=3: print('  slot %2d  checksum %02X  min %02X%02X  max %02X%02X'%(n,chk,lo[0],lo[1],hi[0],hi[1]))
# header checksum: 55h + ee[0] + sum of ee[2..2+5n+5-1]
r3=(ee[0]&0x0F)*5+5
s=(0x55+ee[0]+sum(ee[2:2+r3]))&0xFF
ee[1]=s
print('header: code %02X, checksum %02X over %d bytes from 0002h'%(ee[0],s,r3))
open('D310_image_synthetic.bin','wb').write(ee)
print('written: D310_image_synthetic.bin, %d bytes'%len(ee))
