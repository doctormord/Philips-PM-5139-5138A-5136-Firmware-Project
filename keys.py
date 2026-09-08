"""Key input: an SAA3007 word, pulse-width coded on P3.3, ready signal on P1.2."""
import system2

HIGH_1 = 8000     # Pulslaenge Bitwert 1
HIGH_0 = 2500     # Pulslaenge Bitwert 0
GAP    = 900      # gap between the bits

class Geraet(system2.System2):
    def __init__(self, rom, nvram=None):
        super().__init__(rom, nvram)
        self.wave = []
        self.p33 = 0
        self.ktg = 0
    def dget(self, a):
        v = super().dget(a)
        if a == 0x90:
            v &= ~0x1C & 0xFF                     # IDR/ITG in Ruhe
            if self.ktg: v |= 0x04                # KTG = Tastenwort bereit
        if a == 0xB0:
            v = (v | 0x08) if self.p33 else (v & ~0x08 & 0xFF)
        return v
    def xread(self, d):
        if d >= 0x8000:
            self.strobe_toggle ^= 1
            return 0x11 if self.strobe_toggle else 0x01
        return self.xram[d]
    def taste(self, code, toggle=1):
        """A start bit, then 11 data bits, MSB first."""
        wort = ((toggle & 3) << 9) | (code & 0x3F)
        w = [(0, GAP), (1, HIGH_0), (0, GAP)]     # Startbit
        for i in range(10, -1, -1):
            w.append((1, HIGH_1 if (wort >> i) & 1 else HIGH_0))
            w.append((0, GAP))
        w.append((1, HIGH_0)); w.append((0, GAP))   # Abschlusspuls
        w.append((0, 4000))
        self.wave = w
        self.ktg = 1
    def tick(self):
        super().tick()
        alt = self.p33
        while self.wave:
            lvl, rest = self.wave[0]
            if rest <= 0:
                self.wave.pop(0); continue
            self.p33 = lvl
            self.wave[0] = (lvl, rest - 1)
            break
        else:
            self.p33 = 0; self.ktg = 0
        if alt and not self.p33:                  # fallende Flanke -> IE1
            self.sfr[0x88] |= 0x08
