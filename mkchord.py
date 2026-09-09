#!/usr/bin/env python3
"""Chord wavetables for the waveform RAM of the PM5139.

The instrument is a wavetable DDS: the TWS (Triangle Wave Synthesizer,
D331 on unit 2) generates read addresses 0..1023 for a RAM on unit 4, and
that RAM is filled by the CPU over the C-bus. The table holds exactly one
period of the output signal.

That is what makes polyphony possible without any modulation. A table
holding a *sum of harmonics* is still periodic in those 1024 points, so
it plays as a chord — several notes at once, at full output level, and
the CPU does no work at all while it sounds. Since the notes must be
integer multiples of the table frequency, the intervals come out in just
intonation, which for a sustained chord is the better tuning anyway.

Set the instrument to the fundamental f0; the chord then sounds at
h * f0 for every harmonic number h in the set. A power chord 2:3:4 at
f0 = 41.205 Hz gives E2 (82.41 Hz), B2 and E3.

Wire format, established on the instrument (section 36.8): two bytes per
point, **high byte first**. The first byte carries the upper eight bits,
the second the two least significant, in the pattern 00h/44h/88h/CCh —
the bit pair duplicated into both nibbles. So the bus delivers **10 bits
per point**, 1..1023 with 512 as the zero line, the range the arbitrary
EEPROM stores as well (section 32).

The order was the other way round here at first, inferred from decoding
the firmware's own download, and it was wrong: the instrument played the
table as noise. The test suite of section 36.8 settled it — a ramp with
the bytes exchanged came out as a clean sawtooth. The converter output is
inverted as well, so a rising table gives a falling ramp; that is left
alone, because for a chord it makes no audible difference.

    python3 mkchord.py                 # list the chords and their tables
    python3 mkchord.py power out.bin   # write one table as a raw stream
"""
import sys
import waveforms

N = waveforms.N                     # 1024 points


# Harmonic numbers over the fundamental, in just intonation. The chord
# sounds one octave and a fifth above f0 for the sets starting at 2, and
# two octaves above for those starting at 4 — the ratios are what matter.
CHORDS = {
    'octave': (1, 2),               # root and its octave
    'fifth':  (2, 3),               # bare fifth
    'power':  (2, 3, 4),            # root, fifth, octave — the rock power chord
    'major':  (4, 5, 6),            # major triad
    'minor':  (10, 12, 15),         # minor triad
    'sus4':   (6, 8, 9),            # suspended fourth
    'dom7':   (4, 5, 6, 7),         # dominant seventh, harmonic (septimal) 7th
    'maj7':   (8, 10, 12, 15),      # major seventh
    'min7':   (10, 12, 15, 18),     # minor seventh
}


def chord(harmonics, rolloff=1.0, phase_spread=True):
    """One period of the sum of the given harmonics.

    `rolloff` damps the higher partials with 1/h**rolloff, which keeps the
    chord from being dominated by its top note. `phase_spread` staggers
    the starting phases so the partials do not all peak at once — that
    lowers the crest factor and leaves more room for each note after
    quantisation.
    """
    import math
    out = []
    for i in range(N):
        x = 2 * math.pi * i / N
        s = 0.0
        for k, h in enumerate(harmonics):
            ph = (math.pi * k * k / len(harmonics)) if phase_spread else 0.0
            s += math.sin(h * x + ph) / (h ** rolloff)
        out.append(s)
    return out


def pack(values):
    """The 2048-byte stream for the waveform RAM, low byte first.

    `values` are the 1024 points as 10-bit numbers, 1..1023.
    """
    if len(values) != N:
        raise SystemExit('%d points, expected %d' % (len(values), N))
    b = bytearray()
    for v in values:
        v = max(1, min(1023, int(v)))
        b.append(v >> 2)                # the eight high bits go first
        b.append((v & 3) * 0x44)        # then the two low bits, both nibbles
    return bytes(b)


def unpack(stream):
    """The inverse of pack(), for checking a captured bus stream."""
    return [((stream[i] << 2) | (stream[i + 1] >> 6)) for i in range(0, 2 * N, 2)]


def table(name, rolloff=1.0):
    """A named chord, quantised and packed, ready for the bus."""
    if name not in CHORDS:
        raise SystemExit('unknown chord %r, known: %s'
                         % (name, ' '.join(sorted(CHORDS))))
    v = waveforms._quantise(chord(CHORDS[name], rolloff), 1, 1023)
    return pack(v)


def _describe(name):
    h = CHORDS[name]
    v = waveforms._quantise(chord(h, 1.0), 1, 1023)
    peak = max(max(v) - 512, 512 - min(v))
    # the interval of each partial above the fundamental, in cents
    import math
    cents = ['%+d' % round(1200 * math.log2(x / h[0])) for x in h]
    return ('  %-7s %-14s %-5s peak %+4d  span %4d..%4d'
            % (name, ':'.join(str(x) for x in h),
               'x%d' % (max(h) // h[0]), peak, min(v), max(v)),
            '           intervals over the lowest note: %s cents' % ' '.join(cents))


def main(argv):
    if len(argv) > 1:
        name = argv[1]
        data = table(name)
        if len(argv) > 2:
            open(argv[2], 'wb').write(data)
            print('written: %s  (%d bytes, %d points)' % (argv[2], len(data), N))
        else:
            print(data.hex(' '))
        return
    print('chord wavetables, 1024 points, 10 bit, 512 = zero line')
    print('the instrument plays h * f0 for every harmonic number h\n')
    for name in CHORDS:
        a, b = _describe(name)
        print(a); print(b)
    print('\n  2048 bytes each; %d fit in the free ROM of V2.0 (19509 bytes)'
          % (19509 // 2048))


if __name__ == '__main__':
    main(sys.argv)
