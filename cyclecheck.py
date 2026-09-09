#!/usr/bin/env python3
"""Checks that the machine-cycle tables of the two emulators agree.

core.js carries the table as a 256-character string so it stays readable;
mcs51.py builds it from the MCS-51 data sheet. They must not drift apart,
so this runs as part of the smoke test.

    python3 cyclecheck.py
"""
import re, sys
import mcs51

js = open('core.js').read()
m = re.search(r"var MCYC=\((.*?)\)\s*\.split", js, re.S)
if not m:
    raise SystemExit('the MCYC table was not found in core.js')
digits = ''.join(re.findall(r"'([124]+)'", m.group(1)))

if len(digits) != 256:
    raise SystemExit('core.js has %d entries, expected 256' % len(digits))

bad = [i for i in range(256) if int(digits[i]) != mcs51.CYCLES[i]]
if bad:
    for op in bad[:20]:
        print('%02Xh  %-22s  core.js %s, mcs51.py %d'
              % (op, mcs51.TAB[op][0], digits[op], mcs51.CYCLES[op]))
    raise SystemExit('%d opcodes differ' % len(bad))

n = {c: mcs51.CYCLES.count(c) for c in (1, 2, 4)}
print('the tables agree: %d opcodes at 1 cycle, %d at 2, %d at 4'
      % (n[1], n[2], n[4]))
