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
        }
        if t in tab:
            self.db(*tab[t]); return
        m = re.fullmatch(r'MOV DPTR,#(\S+)', t)
        if m:
            self.out.append(0x90); self._target(m.group(1), 'abs16'); return
        m = re.fullmatch(r'MOV R([0-7]),#(\S+)', t)
        if m:
            self.out.append(0x78 | int(m.group(1))); self.db(self._number(m.group(2))); return
        m = re.fullmatch(r'MOV ([0-9A-F]{2}h),A', t)
        if m:
            self.out.append(0xF5); self.db(self._number(m.group(1))); return
        m = re.fullmatch(r'MOV A,([0-9A-F]{2}h)', t)
        if m:
            self.out.append(0xE5); self.db(self._number(m.group(1))); return
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
