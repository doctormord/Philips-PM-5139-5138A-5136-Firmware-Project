"""PM5139 system emulator: CPU + timers + interrupts + I2C slave + strobes."""
import emu

class System(emu.CPU):
    VEC = {0:0x0003, 1:0x000B, 2:0x0013, 3:0x001B, 4:0x0023}
    def __init__(self, rom):
        super().__init__(rom)
        self.cycles = 0
        self.real_timers = True
        self.in_isr = False
        self.sda_slave = 1          # I2C-Slave laesst SDA los
        self.scl_prev = 1; self.sda_prev = 1
        self.i2c_bits = 0; self.i2c_active = False; self.i2c_ack = 0
        self.i2c_log = []; self.i2c_byte = 0
        self.strobe_toggle = 0
        self.keyq = []              # anstehende Tastenworte
        self.p3 = 0xFF
        self.serial_pending = 0
    # ---- Ports -------------------------------------------------
    def dget(self, a):
        if a == 0x90:               # P1 lesen: offener Drain
            v = self.sfr[0x90]
            if not self.sda_slave: v &= 0x7F
            return v
        if a == 0xB0:               # P3 lesen
            return self.sfr[0xB0] & self.p3
        return super().dget(a)
    def dset(self, a, v):
        if a == 0x90:
            old = self.sfr[0x90]; self.sfr[0x90] = v & 0xFF
            self.i2c_watch(old, v & 0xFF); return
        if a == 0x99:
            self.sfr[0x99] = v & 0xFF; self.serial_pending = 10; return
        super().dset(a, v)
    def bset(self, b, val):         # route bit accesses on P1 through dset
        base, n, sfr = self.bitaddr(b)
        if sfr and base == 0x90:
            v = self.sfr[0x90]
            v = (v | (1 << n)) if val else (v & ~(1 << n) & 0xFF)
            self.dset(0x90, v); return
        super().bset(b, val)
    def bget(self, b):
        base, n, sfr = self.bitaddr(b)
        if sfr and base in (0x90, 0xB0):
            return (self.dget(base) >> n) & 1
        return super().bget(b)
    # ---- I2C slave ---------------------------------------------
    def i2c_watch(self, old, new):
        scl_o, sda_o = (old>>6)&1, (old>>7)&1
        scl, sda = (new>>6)&1, (new>>7)&1
        if scl and scl_o and sda_o and not sda:      # START
            self.i2c_active = True; self.i2c_bits = 0; self.i2c_byte = 0
            self.sda_slave = 1; return
        if scl and scl_o and not sda_o and sda:      # STOP
            self.i2c_active = False; self.sda_slave = 1; return
        if self.i2c_active and scl_o and not scl and self.i2c_ack == 2:
            self.i2c_ack = 0; self.sda_slave = 1; return   # release after the ACK clock
        if self.i2c_active and scl and not scl_o:    # steigende SCL-Flanke
            if self.i2c_ack == 1:
                self.i2c_ack = 2                      # ACK-Takt laeuft
            elif self.i2c_ack == 2:
                pass
            else:
                self.i2c_byte = ((self.i2c_byte<<1) | sda) & 0xFF
                self.i2c_bits += 1
                if self.i2c_bits == 8:
                    self.i2c_log.append(self.i2c_byte)
                    self.i2c_bits = 0; self.i2c_byte = 0
                    self.i2c_ack = 1; self.sda_slave = 0     # ACK vorbereiten
    # ---- external memory / strobes -----------------------------
    def xread(self, d):
        if d >= 0x8000:
            self.strobe_toggle ^= 1
            return 0x10 if self.strobe_toggle else 0x00
        return self.xram[d]
    # ---- timers and interrupts ---------------------------------
    def tick(self):
        self.cycles += 1
        tcon = self.sfr[0x88]; tmod = self.sfr[0x89]
        if tcon & 0x10:                                   # TR0
            v = ((self.sfr[0x8C]<<8)|self.sfr[0x8A]) + 1
            if v > 0xFFFF: v = 0; self.sfr[0x88] |= 0x20   # TF0
            self.sfr[0x8C] = (v>>8)&0xFF; self.sfr[0x8A] = v & 0xFF
        if tcon & 0x40:                                   # TR1
            v = ((self.sfr[0x8D]<<8)|self.sfr[0x8B]) + 1
            if v > 0xFFFF: v = 0; self.sfr[0x88] |= 0x80   # TF1
            self.sfr[0x8D] = (v>>8)&0xFF; self.sfr[0x8B] = v & 0xFF
        if self.serial_pending:
            self.serial_pending -= 1
            if self.serial_pending == 0: self.sfr[0x98] |= 0x02   # TI
    def irq(self):
        if self.in_isr: return
        ie = self.sfr[0xA8]
        if not (ie & 0x80): return
        tcon = self.sfr[0x88]
        src = None
        if (ie & 0x01) and (tcon & 0x02): src, clr = 0, 0x02
        elif (ie & 0x02) and (tcon & 0x20): src, clr = 1, 0x20
        elif (ie & 0x04) and (tcon & 0x08): src, clr = 2, 0x08
        elif (ie & 0x08) and (tcon & 0x80): src, clr = 3, 0x80
        if src is None: return
        self.sfr[0x88] &= ~clr & 0xFF
        self.push(self.pc & 0xFF); self.push((self.pc>>8)&0xFF)
        self.pc = self.VEC[src]; self.in_isr = True
    def step(self):
        op = self.rom[self.pc]
        if op == 0x32: self.in_isr = False          # RETI
        if op == 0xE0: self.setA(self.xread(self.dptr())); self.pc += 1; self.tick(); return
        super().step()
        self.tick()
        self.irq()
