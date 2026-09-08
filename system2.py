"""A system with a complete I2C slave: PCF8576 (70h), PCF8570 RAM (A0h)
and optionally the interface card (5Eh).

The card is only served when `iface` is set; the object needs
start(dir), wr(byte) and rd() -> byte. Without `iface` the core behaves
wie zuvor. Gegenstueck zu core.js, damit beide Kerne dasselbe liefern.
"""
import emu, system

class System2(system.System):
    def __init__(self, rom, nvram=None):
        super().__init__(rom)
        self.nv = bytearray(nvram or bytes(256))   # PCF8570, 256 Byte
        self.act=False; self.stage=None; self.dir='w'
        self.nbits=0; self.shift=0; self.ph='bits'
        self.sel=False; self.mack=True; self.tx=0; self.ptr=0
        self.disp=[]
        self.iface=None          # Schnittstellenkarte auf 5Eh
        self.iface_int=False     # INT0 auf P3.2, aktiv-low
        self.adr_ack=False
    def rx(self, b):
        if self.stage=='addr':
            self.i2c_log.append(b)
            base=b & 0xFE
            self.sel = base in (0x70, 0xA0) or (self.iface is not None and base==0x5E)
            self.dir = 'r' if (b & 1) else 'w'
            self.stage = 'word' if (base==0xA0 and self.dir=='w') else 'data'
            self.dev = base
            # Only for the interface card: the ACK directly after the
            # read address comes from the slave and must not overwrite
            # mack. The display and the NVRAM stay untouched so that the
            # earlier measurements remain valid.
            if self.dir=='r' and base==0x5E and self.iface is not None:
                self.mack=True; self.adr_ack=True
            if self.iface is not None and base==0x5E: self.iface.start(self.dir)
            return
        if self.dev==0x5E:
            if self.iface is not None: self.iface.wr(b)
            return
        if self.dev==0xA0:
            if self.stage=='word': self.ptr=b; self.stage='data'
            else:
                self.nv[self.ptr]=b; self.ptr=(self.ptr+1)&0xFF
        else:
            self.i2c_log.append(b)
    def nvread(self):
        v=self.nv[self.ptr]; self.ptr=(self.ptr+1)&0xFF; return v
    def i2c_watch(self, old, new):
        scl_o,sda_o=(old>>6)&1,(old>>7)&1
        scl,sda=(new>>6)&1,(new>>7)&1
        if scl and scl_o and sda_o and not sda:            # START
            self.act=True; self.stage='addr'; self.dir='w'; self.dev=0
            self.nbits=0; self.shift=0; self.ph='bits'; self.sel=False
            self.sda_slave=1; return
        if scl and scl_o and not sda_o and sda:            # STOP
            self.act=False; self.stage=None; self.sda_slave=1; return
        if not self.act: return
        if scl and not scl_o:                              # steigende Flanke
            if self.ph=='bits':
                if self.dir=='w': self.shift=((self.shift<<1)|sda)&0xFF
                self.nbits+=1
            else:
                if self.dir=='r' and not self.adr_ack: self.mack=(sda==0)
            return
        if scl_o and not scl:                              # fallende Flanke
            if self.ph=='bits' and self.nbits==8:
                self.nbits=0
                from_master = (self.dir=='w')     # remember the direction before decoding
                if vom_master: self.rx(self.shift)
                self.ph='ack'
                self.sda_slave = 0 if (vom_master and self.sel) else 1
                return
            if self.ph=='ack':
                self.ph='bits'; self.nbits=0; self.adr_ack=False
                if self.dir=='r' and self.sel and self.mack:
                    self.tx = (self.iface.rd() if (self.dev==0x5E and self.iface is not None)
                               else self.nvread())
                    self.sda_slave=(self.tx>>7)&1
                else:
                    self.sda_slave=1
                return
            if self.dir=='r' and self.sel and self.nbits<8:
                self.sda_slave=(self.tx>>(7-self.nbits))&1

    # ---- interface card: interrupt and status bit -----------------------
    def dget(self, a):
        if a == 0xB0:                      # P3.2 = INT0, aktiv-low
            v = self.sfr[0xB0] & self.p3
            return (v & ~0x04 & 0xFF) if self.iface_int else (v | 0x04)
        return super().dget(a)
    def xread(self, d):
        v = super().xread(d)
        if d >= 0x8000 and self.iface_int:
            v |= 0x08                      # Bit 3: Schnittstelle meldet ein Ereignis
        return v
