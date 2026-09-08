#!/usr/bin/env python3
"""Converts a MIDI file into the note table of the PM5139.

The generator is **monophonic**: one output, one frequency at a time.
Polyphonic material therefore has to be reduced to a single voice. Time
multiplexing between several voices is out of the question — a note needs
a few full oscillations to become audible (about 73 ms at 41 Hz), so four
voices would end up with a switching rate of 5 to 12 Hz and would sound
like a sequence of notes, not like a chord.

Selection rules (`--voice`):
    high      the highest sounding note at any time (melody)
    low       the lowest (bass line)
    channel N this MIDI channel only

Channel 9 (GM drums) is always skipped.

Table format, as in section 35: three bytes of frequency per entry
(decade 3 and the frequency in 0.01 Hz as BCD) and one byte of duration
in units of 1.006 ms. A zero byte terminates the table.
"""
import sys, midi

UNIT_US  = 1006
REST_HZ  = 1.0          # practically inaudible; the output cannot be silent
KICK_HZ  = 60.0         # kick frequency: a good one period in KICK_MS
KICK_MS  = 22           # short enough not to chop up the melody

def frequency(note):
    return 440.0 * 2 ** ((note - 69) / 12.0)

def bcd(hz):
    """Decade 3 plus five BCD digits of the frequency in 0.01 Hz"""
    hz = max(0.5, min(hz, 99999 / 100.0))
    z = '%05d' % round(hz * 100)
    return [(3 << 4) | int(z[0]), (int(z[1]) << 4) | int(z[2]),
            (int(z[3]) << 4) | int(z[4])]

def pick_voice(m, rule, channel=None):
    """Break the time axis into sections of equal pitch"""
    div = m['division']
    tempo = m['tempos'][0][1]
    us_per_tick = tempo / div
    events = sorted(m['notes'], key=lambda n: n[0])
    active = set()
    sections = []            # (start_tick, note or None)
    last = None
    for t, k, note, on, vel in events:
        if k == 9:
            continue
        if channel is not None and k != channel:
            continue
        if on:
            active.add((k, note))
        else:
            active.discard((k, note))
        if not active:
            chosen = None
        elif rule == 'low':
            chosen = min(n for _, n in active)
        else:
            chosen = max(n for _, n in active)
        if chosen != last:
            sections.append((t, chosen))
            last = chosen
    return sections, us_per_tick

def smooth(sections, us_per_tick, min_note_ms=25, min_rest_ms=30):
    """Remove sections that are too short.

    Two cases disturb the playback: very short rests between two notes
    only produce a click, and notes under about 25 ms do not manage a
    full oscillation at low frequencies. Both are merged with the
    preceding section."""
    if not sections:
        return sections
    out = [list(sections[0])]
    for i in range(1, len(sections)):
        t, note = sections[i]
        until = sections[i+1][0] if i+1 < len(sections) else t
        duration_ms = (until - t) * us_per_tick / 1000
        if isinstance(note, tuple):
            out.append([t, note]); continue          # never smooth kick stages
        limit = min_rest_ms if note is None else min_note_ms
        if duration_ms < limit:
            continue                  # too short: the previous section runs on
        if note == out[-1][1]:
            continue                  # same pitch: merge
        out.append([t, note])
    return [tuple(x) for x in out]


def weave_kicks(sections, m, us_per_tick, notes=(35, 36)):
    """Weave drum kicks into the monophonic sequence of notes.

    The generator is monophonic, so a kick sounds *instead of* the
    melody. The stages are encoded as ('KICK', Hz) so that they stay
    distinguishable from real MIDI notes.

    A single frequency, no stages.

    A falling frequency would have no audible effect here: with a total
    duration of 20 to 30 ms every stage stays below one full oscillation,
    and the ear only perceives pitch from about four to eight periods on.
    What arrives is a click whose timbre depends on the frequency — not
    on its course. That is how monophonic chiptunes do it as well:
    percussion there is a short impulse that stands in for the melody for
    a few milliseconds.

    60 Hz at 22 ms gives a good one full period: low enough for a bass
    impression, short enough not to chop up the melody.
    """
    stages = [(KICK_HZ, KICK_MS)]
    times = sorted(t for t, k, note, on, vel in m['notes']
                   if k == 9 and on and note in notes)
    if not times or not sections:
        return sections

    # look up the pitch at any point in time
    def note_at(t):
        chosen = None
        for st, n in sections:
            if st <= t:
                chosen = n
            else:
                break
        return chosen

    merged = list(sections)
    for kt in times:
        onward = note_at(kt)
        pos = kt
        for hz, ms in stages:
            merged.append((pos, ('KICK', hz)))
            pos += round(ms * 1000 / us_per_tick)
        merged.append((pos, onward))                 # the melody runs on
    merged.sort(key=lambda x: x[0])

    # duplicate points in time: the kick inserted later wins
    out = []
    for t, note in merged:
        if out and out[-1][0] == t:
            if isinstance(note, tuple):
                out[-1] = (t, note)
            continue
        if out and out[-1][1] == note:
            continue
        out.append((t, note))
    return out


def table(sections, us_per_tick, tempo_factor=1.0, end_tick=None, rest_ms=0):
    """Write the sections into the table.

    `end_tick` says how long the **last** section sounds — without it the
    section would get a duration of zero and drop out, so the closing
    note would be missing. `rest_ms` appends a pause so that the jump
    back to the beginning does not happen in the middle of a note.
    """
    b = bytearray()
    n = 0
    for i, (t, note) in enumerate(sections):
        if i+1 < len(sections):
            until = sections[i+1][0]
        elif end_tick is not None and end_tick > t:
            until = end_tick
        else:
            until = t
        duration_us = (until - t) * us_per_tick / tempo_factor
        units = round(duration_us / UNIT_US)
        if units <= 0:
            continue
        if isinstance(note, tuple) and note[0] == 'KICK':
            f = note[1]
        elif note is None:
            f = REST_HZ
        else:
            f = frequency(note)
        while units > 0:                     # the duration fits into one byte
            part = min(units, 255)
            b += bytes(bcd(f) + [part])
            units -= part
            n += 1
    if rest_ms > 0:
        units = max(1, min(255, round(rest_ms * 1000 / UNIT_US)))
        b += bytes(bcd(REST_HZ) + [units])
        n += 1
    b.append(0)
    return bytes(b), n

def main(argv):
    path = 'level1.mid'
    rule, channel, factor, kicks = 'high', None, 1.0, False
    i = 1
    while i < len(argv):
        if argv[i] == '--voice':     rule = argv[i+1]; i += 2
        elif argv[i] == '--channel': channel = int(argv[i+1]); rule = 'channel'; i += 2
        elif argv[i] == '--tempo':   factor = float(argv[i+1]); i += 2
        elif argv[i] == '--kicks':   kicks = True; i += 1
        else: path = argv[i]; i += 1
    m = midi.read(path)
    sections, us = pick_voice(m, rule, channel)
    raw = len(sections)
    sections = smooth(sections, us)
    if kicks:
        sections = weave_kicks(sections, m, us)
    end = max(x[0] for x in m['notes'])
    tab, n = table(sections, us, factor, end_tick=end, rest_ms=250)
    duration = sum(tab[i+3] for i in range(0, len(tab)-1, 4)) * UNIT_US / 1e6
    print('%s, rule %s%s%s' % (path, rule,
          '' if channel is None else ' %d' % channel, ', with kicks' if kicks else ''))
    print('  %d sections, after smoothing %d -> %d entries, %d bytes'
          % (raw, len(sections), n, len(tab)))
    print('  playing time %.1f s at tempo factor %.2f' % (duration, factor))
    return tab

if __name__ == '__main__':
    main(sys.argv)
