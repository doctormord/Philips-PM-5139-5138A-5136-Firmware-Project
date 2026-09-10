#!/usr/bin/env python3
"""A tiny MCS-51 assembler — only as much as ROM extensions need.

Not a complete assembler: it knows the instructions that occur in the
patch routines of this project, and it resolves labels. `mcs51.py` serves
as the counter-check by translating the result back.

    asm = Asm(0xB3CB)
    asm.op('MOV DPTR,#%s' % 'table')
    ...
    code = asm.finish()
"""
import re
import mcs51

# Names resolved out of mcs51.py so the two files cannot drift apart.
_SFR = {name: addr for addr, name in mcs51.SFR.items()}
_BIT = {name: addr for addr, name in mcs51.BITNAMES.items()}
# the bit-addressable SFRs, so P1.5 or ACC.4 can be written directly
for _a in (0x80, 0x88, 0x90, 0x98, 0xA0, 0xA8, 0xB0, 0xB8, 0xC8, 0xD0, 0xE0, 0xF0):
    for _n in range(8):
        _BIT.setdefault('%s.%d' % (mcs51.SFR.get(_a, 'SFR_%02X' % _a), _n), _a + _n)


class Asm:
    def __init__(self, base):
        self.base = base
        self.out = bytearray()
        self.labels = {}
        self.pending = []        # (position, label, kind)

    def label(self, name):
        self.labels[name] = self.base + len(self.out)

    def db(self, *values):
        for v in values:
            self.out.append(v & 0xFF)

    def _direct(self, s):
        """A direct address: 99h, or an SFR by name such as SBUF or P1."""
        s = s.strip()
        if s in _SFR:
            return _SFR[s]
        return self._number(s)

    def _bitaddr(self, s):
        """A bit address: TI, P1.5, ACC.4 or 22h.7."""
        s = s.strip()
        if s in _BIT:
            return _BIT[s]
        m = re.fullmatch(r'([0-9A-F]{2})h\.([0-7])', s)
        if m:                                  # 20h..2Fh are bit addressable
            base = int(m.group(1), 16)
            if not 0x20 <= base <= 0x2F:
                raise SystemExit('%s is not in the bit-addressable RAM' % s)
            return (base - 0x20) * 8 + int(m.group(2))
        raise SystemExit('unknown bit: %r' % s)

    def _number(self, s):
        s = s.strip()
        if s.startswith('#'):
            s = s[1:]
        if s.endswith('h'):
            return int(s[:-1], 16)
        return int(s, 0)

    def op(self, text):
        t = ' '.join(text.split())
        p = self.base + len(self.out)

        # --- instructions with a jump target ---
        m = re.fullmatch(r'(LJMP|LCALL) (\S+)', t)
        if m:
            self.out.append(0x02 if m.group(1) == 'LJMP' else 0x12)
            self._target(m.group(2), 'abs16')
            return
        m = re.fullmatch(r'(SJMP|DJNZ R([0-7]),) ?(\S+)', t)
        if m and m.group(1) == 'SJMP':
            self.out.append(0x80); self._target(m.group(3), 'rel')
            return
        m = re.fullmatch(r'DJNZ R([0-7]),(\S+)', t)
        if m:
            self.out.append(0xD8 | int(m.group(1))); self._target(m.group(2), 'rel')
            return
        m = re.fullmatch(r'(JB|JNB|JBC) (\S+),(\S+)', t)
        if m:
            self.out.append({'JB': 0x20, 'JNB': 0x30, 'JBC': 0x10}[m.group(1)])
            self.db(self._bitaddr(m.group(2)))
            self._target(m.group(3), 'rel'); return
        m = re.fullmatch(r'CJNE A,#(\S+),(\S+)', t)
        if m:
            self.out.append(0xB4); self.db(self._number(m.group(1)))
            self._target(m.group(2), 'rel'); return
        m = re.fullmatch(r'CJNE R([0-7]),#(\S+),(\S+)', t)
        if m:
            self.out.append(0xB8 | int(m.group(1))); self.db(self._number(m.group(2)))
            self._target(m.group(3), 'rel'); return
        m = re.fullmatch(r'DJNZ (\S+h),(\S+)', t)
        if m:
            self.out.append(0xD5); self.db(self._direct(m.group(1)))
            self._target(m.group(2), 'rel'); return
        m = re.fullmatch(r'(JC|JNC) (\S+)', t)
        if m:
            self.out.append(0x40 if m.group(1) == 'JC' else 0x50)
            self._target(m.group(2), 'rel'); return
        m = re.fullmatch(r'JZ (\S+)', t)
        if m:
            self.out.append(0x60); self._target(m.group(1), 'rel'); return
        m = re.fullmatch(r'JNZ (\S+)', t)
        if m:
            self.out.append(0x70); self._target(m.group(1), 'rel'); return

        # --- instructions without a jump target ---
        tab = {
            'CLR A': [0xE4], 'MOVC A,@A+DPTR': [0x93], 'INC DPTR': [0xA3],
            'RET': [0x22], 'NOP': [0x00],
            'PUSH DPH': [0xC0, 0x83], 'PUSH DPL': [0xC0, 0x82],
            'POP DPL': [0xD0, 0x82], 'POP DPH': [0xD0, 0x83],
            'PUSH ACC': [0xC0, 0xE0], 'POP ACC': [0xD0, 0xE0],
            'MOVX @DPTR,A': [0xF0], 'MOVX A,@DPTR': [0xE0],
            'CLR C': [0xC3], 'SETB C': [0xD3], 'CPL C': [0xB3],
            'CPL A': [0xF4], 'RR A': [0x03], 'RL A': [0x23],
            'RRC A': [0x13], 'RLC A': [0x33], 'SWAP A': [0xC4],
            'INC A': [0x04], 'DEC A': [0x14],
        }
        if t in tab:
            self.db(*tab[t]); return
        m = re.fullmatch(r'(PUSH|POP) (\S+h|R[0-7])', t)
        if m:
            reg = m.group(2)
            addr = (int(reg[1]) if re.fullmatch(r'R[0-7]', reg)   # bank 0
                    else self._direct(reg))
            self.out.append(0xC0 if m.group(1) == 'PUSH' else 0xD0)
            self.db(addr); return
        m = re.fullmatch(r'(CLR|SETB|CPL) (\S+\.\S+|[A-Z][A-Z0-9]*)', t)
        if m and m.group(2) not in ('A', 'C'):
            self.out.append({'CLR': 0xC2, 'SETB': 0xD2, 'CPL': 0xB2}[m.group(1)])
            self.db(self._bitaddr(m.group(2))); return
        m = re.fullmatch(r'MOV (\S+),C', t)
        if m and m.group(1) not in ('A',):
            self.out.append(0x92); self.db(self._bitaddr(m.group(1))); return
        m = re.fullmatch(r'MOV C,(\S+)', t)
        if m:
            self.out.append(0xA2); self.db(self._bitaddr(m.group(1))); return
        m = re.fullmatch(r'(ORL|ANL|XRL|ADD|SUBB) A,#(\S+)', t)
        if m:
            self.out.append({'ORL': 0x44, 'ANL': 0x54, 'XRL': 0x64,
                             'ADD': 0x24, 'SUBB': 0x94}[m.group(1)])
            self.db(self._number(m.group(2))); return
        m = re.fullmatch(r'MOV A,#(\S+)', t)
        if m:
            self.out.append(0x74); self.db(self._number(m.group(1))); return
        m = re.fullmatch(r'MOV (\S+),#(\S+)', t)
        if m and m.group(1) != 'DPTR' and not re.fullmatch(r'R[0-7]', m.group(1)):
            self.out.append(0x75); self.db(self._direct(m.group(1)))
            self.db(self._number(m.group(2))); return
        m = re.fullmatch(r'(INC|DEC) R([0-7])', t)
        if m:
            self.out.append((0x08 if m.group(1) == 'INC' else 0x18) | int(m.group(2)))
            return
        m = re.fullmatch(r'(INC|DEC) (\S+h)', t)
        if m:
            self.out.append(0x05 if m.group(1) == 'INC' else 0x15)
            self.db(self._direct(m.group(2))); return
        m = re.fullmatch(r'MOV DPTR,#(\S+)', t)
        if m:
            self.out.append(0x90); self._target(m.group(1), 'abs16'); return
        m = re.fullmatch(r'MOV R([0-7]),#(\S+)', t)
        if m:
            self.out.append(0x78 | int(m.group(1))); self.db(self._number(m.group(2))); return
        m = re.fullmatch(r'MOV ([0-9A-F]{2}h|[A-Z][A-Z0-9]*),A', t)
        if m and m.group(1) != 'C' and not re.fullmatch(r'R[0-7]', m.group(1)):
            self.out.append(0xF5); self.db(self._direct(m.group(1))); return
        m = re.fullmatch(r'MOV A,([0-9A-F]{2}h|[A-Z][A-Z0-9]*)', t)
        if m and not re.fullmatch(r'R[0-7]', m.group(1)):
            self.out.append(0xE5); self.db(self._direct(m.group(1))); return
        m = re.fullmatch(r'MOV A,R([0-7])', t)
        if m:
            self.out.append(0xE8 | int(m.group(1))); return
        m = re.fullmatch(r'MOV R([0-7]),A', t)
        if m:
            self.out.append(0xF8 | int(m.group(1))); return
        raise SystemExit('unknown instruction: %r' % t)

    def _target(self, name, kind):
        # a number (such as 0A28h) is inserted immediately, everything
        # else counts as a label and is resolved in finish()
        if re.fullmatch(r'[0-9A-F]+h|[0-9]+|0x[0-9A-Fa-f]+', name):
            value = self._number(name)
            if kind == 'abs16':
                self.db((value >> 8) & 0xFF, value & 0xFF)
            else:
                d = value - (self.base + len(self.out) + 1)
                if not -128 <= d <= 127:
                    raise SystemExit('jump too far: %s' % name)
                self.db(d)
            return
        self.pending.append((len(self.out), name, kind))
        self.out.append(0)
        if kind == 'abs16':
            self.out.append(0)

    def finish(self):
        for pos, name, kind in self.pending:
            if name not in self.labels:
                raise SystemExit('label missing: %s' % name)
            target = self.labels[name]
            if kind == 'abs16':
                self.out[pos] = (target >> 8) & 0xFF
                self.out[pos+1] = target & 0xFF
            else:
                d = target - (self.base + pos + 1)
                if not -128 <= d <= 127:
                    raise SystemExit('jump too far: %s (%d)' % (name, d))
                self.out[pos] = d & 0xFF
        return bytes(self.out)
