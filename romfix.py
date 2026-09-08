#!/usr/bin/env python3
"""PM5139/PM5138A: check and correct the checksum of an EPROM image.

At power-up the firmware sums all bytes from 0000h up to an end address
and compares the result with the byte immediately after it. If it does
not match, it shows Err 1 and stays in an endless loop.

The end address sits in the ROM itself: the check routine loads it with
    MOV 10h,#hi   (75 10 hi)
    MOV 11h,#lo   (75 11 lo)
"""
import sys, re

def endadresse(rom):
    """Read the end address out of the check routine."""
    hits = []
    for m in re.finditer(rb'\x75\x10(.)\x75\x11(.)', rom):
        adr = (m.group(1)[0] << 8) | m.group(2)[0]
        if 0x8000 <= adr < 0x10000:          # a plausible ROM size
            hits.append((m.start(), adr))
    if not hits:
        raise SystemExit('check routine not found')
    return hits[-1]

def summe(rom, end):
    s = 0
    for i in range(0, end + 1):
        s = (s + rom[i]) & 0xFF
    return s

def check(rom):
    where, end = endadresse(rom)
    actual = summe(rom, end)
    stored = rom[end + 1]
    return where, end, actual, stored

def main(argv):
    if len(argv) < 2:
        print(__doc__)
        print('usage:  romfix.py <image.bin> [output.bin]')
        return 1
    rom = bytearray(open(argv[1], 'rb').read())
    where, end, actual, stored = check(rom)
    print('check routine at %04Xh, range 0000h-%04Xh' % (where, end))
    print('the checksum byte sits at %04Xh' % (end + 1))
    print('  stored    : %02Xh' % stored)
    print('  computed  : %02Xh' % actual)
    if actual == stored:
        print('  -> matches, the image starts without errors')
    else:
        print('  -> wrong, the instrument would show Err 1')
    if len(argv) > 2:
        rom[end + 1] = actual
        open(argv[2], 'wb').write(bytes(rom))
        print('corrected image written to %s' % argv[2])
        _, _, a2, s2 = check(rom)
        print('counter-check: computed %02Xh, stored %02Xh -> %s'
              % (a2, s2, 'ok' if a2 == s2 else 'FAILED'))
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
