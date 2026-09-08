#!/usr/bin/env python3
"""A minimal MIDI reader: break a file down into notes, tempo and channels.

Only as much as the conversion for the PM5139 needs: note-on/note-off,
tempo changes, program changes. SysEx and the other meta events are
skipped.
"""
import sys

def varlen(d, i):
    v = 0
    while True:
        b = d[i]; i += 1
        v = (v << 7) | (b & 0x7F)
        if not b & 0x80:
            return v, i

def read(path):
    d = open(path, 'rb').read()
    assert d[:4] == b'MThd'
    fmt = int.from_bytes(d[8:10], 'big')
    ntr = int.from_bytes(d[10:12], 'big')
    div = int.from_bytes(d[12:14], 'big')
    i = 14
    tempo = 500000                       # default: 120 BPM
    notes = []                           # (tick, channel, note, on/off, velocity)
    tempos = []
    while i < len(d):
        if d[i:i+4] != b'MTrk':
            break
        n = int.from_bytes(d[i+4:i+8], 'big')
        i += 8
        end = i + n
        t = 0
        status = 0
        while i < end:
            dt, i = varlen(d, i)
            t += dt
            if d[i] & 0x80:
                status = d[i]; i += 1
            kind, channel = status & 0xF0, status & 0x0F
            if kind in (0x80, 0x90):
                note, vel = d[i], d[i+1]; i += 2
                on = kind == 0x90 and vel > 0
                notes.append((t, channel, note, on, vel))
            elif kind in (0xA0, 0xB0, 0xE0):
                i += 2
            elif kind in (0xC0, 0xD0):
                i += 1
            elif status == 0xFF:
                typ = d[i]; i += 1
                length, i = varlen(d, i)
                if typ == 0x51:
                    tempo = int.from_bytes(d[i:i+3], 'big')
                    tempos.append((t, tempo))
                i += length
            elif status in (0xF0, 0xF7):
                length, i = varlen(d, i)
                i += length
            else:
                raise SystemExit('unknown status %02X at %d' % (status, i))
        i = end
    return {'format': fmt, 'tracks': ntr, 'division': div,
            'notes': notes, 'tempos': tempos or [(0, 500000)]}

if __name__ == '__main__':
    m = read(sys.argv[1] if len(sys.argv) > 1 else 'level1.mid')
    print('format %d, %d track(s), %d ticks per quarter'
          % (m['format'], m['tracks'], m['division']))
    for t, tp in m['tempos'][:4]:
        print('  tempo from tick %d: %d us per quarter = %.1f BPM' % (t, tp, 60e6/tp))
    on = [n for n in m['notes'] if n[3]]
    print('%d note events, of which %d are note-ons' % (len(m['notes']), len(on)))
    channels = sorted({n[1] for n in on})
    print('channels:', channels)
    for k in channels:
        kn = [n for n in on if n[1] == k]
        print('  channel %2d: %4d notes, range MIDI %d..%d'
              % (k, len(kn), min(x[2] for x in kn), max(x[2] for x in kn)))
    print('length: %d ticks' % max(n[0] for n in m['notes']))
