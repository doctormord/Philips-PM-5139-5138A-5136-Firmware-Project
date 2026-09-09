#!/usr/bin/env python3
"""Writes our own waveforms into an arbitrary EEPROM image (D310).

The format, documented in section 32:

    0000h   number of curves n in the lower nibble
    0001h   check byte: 55h + header byte + sum over n*5+5 bytes from 0002h
    0002h   directory, n+1 records of five bytes each:
            [identity][min high][min low][max high][max low]
            min and max are 10-bit values, left-aligned by six bits;
            512 is the zero.
    0100h   curve data, 1280 bytes each: 1024 points of 10 bit,
            four values packed into five bytes.

Curve k begins at 0100h + (k-1)*1280, k = 1..n.

    python3 mkarb.py            -> D310_image_V20.bin   (test waveforms)
    python3 mkarb.py --chords   -> D310_image_chords.bin (six chords)
"""
import sys
import waveforms
import mkchord

BASE   = 'D310_image.bin'          # the X28C64 that was read out
TARGET = 'D310_image_V20.bin'
TARGET_CHORDS = 'D310_image_chords.bin'
RECORD = 1280
DATA   = 0x100

# All six slots are filled — burning the device is only worth doing once.
# Slot 5 gets the shape that sat there in the EEPROM read out (a
# full-wave rectified sine), but computed instead of sampled.
NEW = {1: ('sinc',      waveforms.sinc),
       2: ('ringing',   waveforms.ringing),
       3: ('ecg',       waveforms.ecg),
       4: ('staircase', waveforms.staircase),
       5: ('rectified', waveforms.rectified),
       6: ('multitone', waveforms.multitone)}

# `python3 mkarb.py --chords` fills the six slots with chords instead.
#
# This is polyphony without touching the firmware at all: the table in
# the arbitrary EEPROM is one period of the output, exactly as the
# waveform RAM is, so a sum of harmonics plays as a chord (section 36).
# Write the EEPROM, pick the slot on the front panel, set the frequency
# by hand — the instrument sounds h * f for every harmonic number h.
#
# Six slots, so six chords. They are chosen to be usable together: a
# fifth and a power chord for riffs, major and minor for triads, and two
# sevenths.
CHORDS = {1: 'fifth', 2: 'power', 3: 'major',
          4: 'minor', 5: 'dom7',  6: 'min7'}


def unpack(d, at):
    w = []
    for i in range(0, RECORD, 5):
        b = d[at+i:at+i+5]
        for k in range(4):
            w.append((b[k] << 2) | ((b[4] >> (2*k)) & 3))
    return w


def main(argv=()):
    chords = '--chords' in argv
    target = TARGET_CHORDS if chords else TARGET
    table = ({k: (v, (lambda n=v: mkchord.chord(mkchord.CHORDS[n])))
              for k, v in CHORDS.items()} if chords else NEW)

    d = bytearray(open(BASE, 'rb').read())
    n = d[0] & 0x0F
    print('base: %s, %d curve slots' % (BASE, n))
    if chords:
        print('filling every slot with a chord — the instrument then plays')
        print('h * f for every harmonic number h of the chord')

    for k, (name, f) in sorted(table.items()):
        if not 1 <= k <= n:
            raise SystemExit('slot %d does not exist' % k)
        raw = waveforms.as_eeprom(f())
        start = DATA + (k-1)*RECORD
        d[start:start+RECORD] = raw
        w = unpack(d, start)
        lo, hi = min(w), max(w)
        rec = 2 + k*5                        # directory entry
        # Identity byte: checksum of the 1280 curve bytes with start
        # value 55h. Without it the instrument reports Err 8 and refuses
        # the curve.
        d[rec] = (0x55 + sum(raw)) & 0xFF
        d[rec+1] = (lo << 6) >> 8;  d[rec+2] = (lo << 6) & 0xFF
        d[rec+3] = (hi << 6) >> 8;  d[rec+4] = (hi << 6) & 0xFF
        extra = ''
        if chords:
            h = mkchord.CHORDS[name]
            extra = '  = %s, so f -> %s' % (
                ':'.join(str(x) for x in h),
                ' '.join('%dx' % x for x in h))
        print('  slot %d <- %-9s from %04Xh, values %d..%d (%+d..%+d, %.2f Vpp), '
              'identity %02Xh%s'
              % (k, name, start, lo, hi, lo-512, hi-512, (hi-lo)/1022*20,
                 d[rec], extra))

    # Re-form the check byte of the directory
    length = n*5 + 5
    s = (d[0] + 0x55) & 0xFF
    for b in d[2:2+length]:
        s = (s + b) & 0xFF
    d[1] = s
    print('directory check byte: %02Xh over %d bytes from 0002h' % (s, length))

    open(target, 'wb').write(bytes(d))
    print('written: %s (%d bytes)' % (target, len(d)))


if __name__ == '__main__':
    main(sys.argv[1:])
