#!/usr/bin/env python3
"""Builds a version V2.0 with a corrected arbitrary curve 3 from V1.5 (or V1.3).

Finding (see section 34): the built-in arbitrary curve 3 is the same
waveform as the computed level-series table (ten sine arcs, each 3.33 dB
smaller), but noisy — a standard deviation of about 4 LSB and 563
direction changes against 13 in the original. It was apparently sampled
from an analogue source instead of being computed.

The fix replaces the noisy curve with the clean one. Both tables are
1024 bytes of 8 bit, so the replacement is neutral in size and touches no
code. In addition the identification string is set to V2.0 so that the
version is recognisable through *IDN?, and the checksum is carried along.

The addresses are found by signature rather than entered as constants —
that way the same script runs on both source versions.

    python3 mkv20.py                     from V1.5  -> M27512_PM5139_V20.bin
    python3 mkv20.py M27512_PM5139_V13.bin target.bin
"""
import sys
import romfix
import waveforms

LENGTH = 1024

# The start of the noisy curve and of the clean template, read off V1.3.
# Both sequences occur exactly once in both versions.
SIG_NOISY = bytes.fromhex('020205090d22202c374547')
SIG_CLEAN = bytes.fromhex('00000009131c252e3740')
SIG_PULSE = bytes.fromhex('807b76716c67625d')   # start of pulse curves 1 and 2


def find(rom, sig, what):
    hits = []
    p = rom.find(sig)
    while p >= 0:
        hits.append(p)
        p = rom.find(sig, p + 1)
    if len(hits) != 1:
        raise SystemExit('%s: %d occurrences, expected exactly one' % (what, len(hits)))
    return hits[0]


def main(argv):
    source = argv[1] if len(argv) > 1 else 'M27512_PM5139_V15.bin'
    target = argv[2] if len(argv) > 2 else 'M27512_PM5139_V20.bin'
    rom = bytearray(open(source, 'rb').read())
    print('base: %s (%d bytes)' % (source, len(rom)))

    # 1. replace the noisy curve with the clean one
    arb3 = find(bytes(rom), SIG_NOISY, 'noisy arbitrary curve')
    clean = find(bytes(rom), SIG_CLEAN, 'clean AM curve')
    old = bytes(rom[arb3:arb3+LENGTH])
    rom[arb3:arb3+LENGTH] = rom[clean:clean+LENGTH]
    n = sum(1 for i in range(LENGTH) if old[i] != rom[arb3+i])
    print('arbitrary curve 3 at %04Xh replaced by %04Xh: %d of %d bytes changed'
          % (arb3, clean, n, LENGTH))

    # 2. version identification in the identification string
    i = rom.find(b'PHILIPS,PM5139')
    if i < 0:
        raise SystemExit('identification string not found')
    n = rom[i-1]                                   # length byte in front of it
    s = bytes(rom[i:i+n]).decode('ascii')
    new = s.replace('V1.5', 'V2.0').replace('V1.3', 'V2.0')
    if new == s:
        raise SystemExit('version number in the string not recognised: %r' % s)
    assert len(new) == len(s), 'the length of the string must not change'
    rom[i:i+n] = new.encode('ascii')
    print('identification at %04Xh: %r -> %r' % (i, s, new))

    # 3. Replace arbitrary curve 2 with a logarithmic chirp. In the
    #    original, curves 1 and 2 differ in exactly two bytes (one needle
    #    pulse more), so curve 2 is practically redundant.
    arb1 = bytes(rom).find(SIG_PULSE)          # occurs twice: curves 1 and 2
    arb2 = bytes(rom).find(SIG_PULSE, arb1 + 1)
    if arb1 < 0 or arb2 < 0 or arb2 - arb1 != LENGTH:
        raise SystemExit('the two pulse curves do not lie as expected')
    rom[arb2:arb2+LENGTH] = waveforms.as_rom(waveforms.chirp())
    print('arbitrary curve 2 at %04Xh replaced by a logarithmic chirp '
          '(1 to 40 periods)' % arb2)

    # 4. Version indication in the display. The reset sequence sets two
    #    display cells and sends them: 3Fh the first position with the
    #    separator, 40h the second (segment encoding, section 15).
    import re
    hits = [m for m in re.finditer(rb'\x75\x3f(.)\x75\x40(.)', bytes(rom))
            if m.group(1)[0] == 0x0E]
    if len(hits) != 1:
        raise SystemExit('version indication not found unambiguously')
    m = hits[0]
    old3f, old40 = m.group(1)[0], m.group(2)[0]
    DIGIT = {0:0xED,1:0x0C,2:0x79,3:0x3D,4:0x9C,5:0xB5,6:0xF5,7:0x2C,8:0xFD,9:0xBD}
    rom[m.start()+2] = DIGIT[2] | 0x02      # "2." first position with separator
    rom[m.start()+5] = DIGIT[0]             # "0"  second position
    print('version indication at %04Xh: %02X %02X -> %02X %02X  (display "2.0")'
          % (m.start()+2, old3f, old40, rom[m.start()+2], rom[m.start()+5]))

    # 5. Carry the checksum along: the firmware sums 0000h..end and
    #    compares it with the byte at end+1 (see romfix.py)
    _, end = romfix.endadresse(bytes(rom))
    rom[end+1] = romfix.summe(bytes(rom), end)
    print('checksum over 0000h..%04Xh: %02Xh, stored at %04Xh'
          % (end, rom[end+1], end+1))

    open(target, 'wb').write(bytes(rom))
    print('written: %s' % target)


if __name__ == '__main__':
    main(sys.argv)
