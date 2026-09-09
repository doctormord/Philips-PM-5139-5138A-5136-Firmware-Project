#!/usr/bin/env python3
"""Places a melody in the free ROM area and hooks it to the diagnostic menu.

Not an exploit — the 8051 cannot fetch code out of the arbitrary EEPROM
anyway (Harvard architecture: code through /PSEN from D306, data through
/RD from D310). Instead the code sits in the program EPROM, where about
19.5 KB are unused behind the checksum, and it is reached through menu
item 8 of the diagnostic program (section 35).

Notes are set through 50h..52h and put out with OUT_FREQ. The encoding is
direct: decade 3, then the frequency in 0.01 Hz as BCD — so 82.41 Hz is
30 82 41.

    python3 mkdoom.py [source.bin] [target.bin]
    python3 mkdoom.py --midi level1.mid --channel 1 M27512_PM5139_V20.bin
"""
import sys
import romfix, asm51, mcs51

# --- notes ------------------------------------------------------------
# The bass line of "At Doom's Gate" (E1M1) runs in sixteenths at about
# 140 BPM. One unit of the wait loop equals 1.006 ms, so the duration is
# given directly in milliseconds.
E2, D2, C2, B1, As1 = 82.41, 73.42, 65.41, 61.74, 58.27
BPM = 140
# One unit of the wait loop takes 1009 us on real hardware:
#   MOV R6 = 1, then twice ( MOV R7 = 1 + 250 times DJNZ = 500 + DJNZ R6
#   = 2 ), then DJNZ R5 = 2 machine cycles; at the 12 MHz of crystal G816
#   one machine cycle is 1 us (MCS-51 data sheet).
# This used to read 1006, which dropped the MOV R6 and the DJNZ R5. The
# figure is now measured: mcs51.CYCLES gives both emulators a machine-cycle
# counter, and stepping this very loop reports 1009 (see section 35).
UNIT_US = 1 + 2 * (1 + 250*2 + 2) + 2        # = 1009
S = round(60000 / BPM / 4 * 1000 / UNIT_US)   # a sixteenth, in units
def bar(last):                       # seven E, then the turning note
    return [(E2, S)]*7 + [(last, S)]
MELODY = bar(D2) + bar(C2) + bar(As1) + bar(B1)

def note_table(midi_file=None, rule='high', channel=None, tempo=1.0, kicks=False):
    """Build the note table — either from the built-in short version or
    from a MIDI file through mid2ton.py."""
    if midi_file:
        import mid2ton, midi as midilib
        m = midilib.read(midi_file)
        sections, us = mid2ton.pick_voice(m, rule, channel)
        sections = mid2ton.smooth(sections, us)
        if kicks:
            sections = mid2ton.weave_kicks(sections, m, us)
        end = max(x[0] for x in m['notes'])
        tab, n = mid2ton.table(sections, us, tempo, end_tick=end, rest_ms=250)
        return tab
    b = bytearray()
    for hz, duration in MELODY:
        z = '%05d' % round(hz * 100)      # five digits in 0.01 Hz
        b += bytes([(3 << 4) | int(z[0]),
                    (int(z[1]) << 4) | int(z[2]),
                    (int(z[3]) << 4) | int(z[4]),
                    duration])
    b.append(0x00)                        # end marker
    return bytes(b)

def find(rom, sig, what):
    p = rom.find(sig)
    if p < 0 or rom.find(sig, p+1) >= 0:
        raise SystemExit('%s: not found unambiguously' % what)
    return p

def main(argv):
    # --midi FILE [--voice high|low] [--channel N] [--tempo F] [--kicks]
    midi_file, rule, channel, tempo, kicks = None, 'high', None, 1.0, False
    rest = []
    i = 1
    while i < len(argv):
        if argv[i] == '--midi':      midi_file = argv[i+1]; i += 2
        elif argv[i] == '--voice':   rule = argv[i+1]; i += 2
        elif argv[i] == '--channel': channel = int(argv[i+1]); rule = 'channel'; i += 2
        elif argv[i] == '--tempo':   tempo = float(argv[i+1]); i += 2
        elif argv[i] == '--kicks':   kicks = True; i += 1
        else: rest.append(argv[i]); i += 1
    source = rest[0] if rest else 'M27512_PM5139_V20.bin'
    target = rest[1] if len(rest) > 1 else source
    rom = bytearray(open(source, 'rb').read())

    # 1. The point of attachment: the place that selects curve 3.
    #    In V1.3: 9E67 MOV DPTR,#A847h / 9E6A LJMP 9ECAh
    #    It is searched for through its surroundings, because the
    #    addresses differ between versions.
    sig = bytes.fromhex('e50d90')          # MOV A,0Dh / MOV DPTR,#..
    p = find(bytes(rom), sig, 'curve selection')
    # from there look for the third MOV DPTR and the LJMP after it
    i = p
    hits = []
    while len(hits) < 3 and i < p + 64:
        if rom[i] == 0x90:
            hits.append(i); i += 3
        else:
            i += 1
    if len(hits) < 3 or rom[hits[2]+3] != 0x02:
        raise SystemExit('the curve selection pattern is not as expected')
    trampoline = hits[2] + 3               # the LJMP behind the third curve
    onward = (rom[trampoline+1] << 8) | rom[trampoline+2]
    print('curve selection at %04Xh, trampoline on the LJMP at %04Xh '
          '(led to %04Xh)' % (p, trampoline, onward))

    # 2. Fetch OUT_FREQ from the symbol table. In V1.5 the routine was not
    #    only moved but changed — a signature from V1.3 does not find it
    #    there. Which table applies is decided by the end address of the
    #    checksum.
    _, end_probe = romfix.endadresse(bytes(rom))
    tab = __import__('symbols_v15' if end_probe > 0xB000 else 'symbols')
    freq = [a for a, (n, _, _) in tab.ROUTINES.items() if n == 'OUT_FREQ']
    if len(freq) != 1:
        raise SystemExit('OUT_FREQ not unambiguous in the symbol table')
    freq = freq[0]
    print('OUT_FREQ at %04Xh (from %s)' % (freq, tab.__name__))

    # 3. Put the routine behind the checksum
    _, end = romfix.endadresse(bytes(rom))
    base = end + 2                              # one byte of air behind the sum
    a = asm51.Asm(base)
    a.op('MOV DPTR,#table')
    a.label('loop')
    a.op('CLR A');  a.op('MOVC A,@A+DPTR');  a.op('JZ done')
    a.op('MOV 50h,A'); a.op('INC DPTR')
    a.op('CLR A');  a.op('MOVC A,@A+DPTR');  a.op('MOV 51h,A'); a.op('INC DPTR')
    a.op('CLR A');  a.op('MOVC A,@A+DPTR');  a.op('MOV 52h,A'); a.op('INC DPTR')
    a.op('CLR A');  a.op('MOVC A,@A+DPTR');  a.op('MOV R5,A');  a.op('INC DPTR')
    a.op('PUSH DPH'); a.op('PUSH DPL')
    a.op('LCALL %04Xh' % freq)
    a.op('POP DPL');  a.op('POP DPH')
    a.label('wait')                        # one unit = 1.006 ms
    a.op('MOV R6,#02h')
    a.label('w2'); a.op('MOV R7,#0FAh')
    a.label('w3'); a.op('DJNZ R7,w3')
    a.op('DJNZ R6,w2')
    a.op('DJNZ R5,wait')
    a.op('SJMP loop')
    a.label('done')                        # end of the table: start over
    a.op('LJMP %04Xh' % 0)                 # placeholder, set below
    a.label('after')
    a.op('LJMP %04Xh' % onward)
    a.label('table')
    code = bytearray(a.finish())
    # The LJMP at the end of the table points back to the beginning: the
    # melody runs endlessly until the instrument is switched off and on
    # again. The exit behind it (an LJMP to the original target) stays in
    # the code so that the place is documented and easy to change.
    pos = code.find(bytes([0x02, 0x00, 0x00]))
    if pos < 0:
        raise SystemExit('placeholder for the loop not found')
    code[pos+1] = (base >> 8) & 0xFF
    code[pos+2] = base & 0xFF
    notes = note_table(midi_file, rule, channel, tempo, kicks)
    code += notes

    if base + len(code) >= len(rom):
        raise SystemExit('the routine no longer fits into the ROM')
    rom[base:base+len(code)] = code
    entries = (len(notes) - 1) // 4
    playtime = sum(notes[i+3] for i in range(0, len(notes)-1, 4)) * UNIT_US / 1e6
    print('melody routine at %04Xh, %d bytes (of which %d bytes of notes)'
          % (base, len(code), len(notes)))
    print('%d entries, playing time %.1f s, endless loop%s'
          % (entries, playtime, '' if not midi_file else
             '  (from %s, voice %s%s)' % (midi_file, rule,
                                          ', with kicks' if kicks else '')))

    # 3b. Hook the melody onto the diagnostic menu.
    #
    #     The jump table has eight entries, but the menu loop counts 0Bh
    #     only from 1 to 7 (CJNE A,#08h). The eighth entry — index 7, an
    #     LJMP to the start of the menu at 5B45h — is **never reachable**
    #     through the counting and redundant on top: 5B45h is jumped to
    #     from 5B61h and 5B67h anyway.
    #
    #     So it is enough to bend this dead entry onto the melody and
    #     raise the count limit by one. No test is lost, no table has to
    #     be relocated, and no menu item without a function is created.
    selftest = [a for a, (n, _, _) in tab.ROUTINES.items() if n == 'TAB_SELFTEST']
    if selftest:
        selftest = selftest[0]
        entry = selftest + 7*3                      # index 7
        if rom[entry] != 0x02:
            raise SystemExit('the eighth table entry is not an LJMP')
        before = (rom[entry+1] << 8) | rom[entry+2]
        rom[entry+1] = (base >> 8) & 0xFF
        rom[entry+2] = base & 0xFF
        print('self-test table %04Xh, entry 8 (index 7) at %04Xh: '
              '%04Xh -> %04Xh' % (selftest, entry, before, base))
        limit = bytes(rom).find(bytes([0xE5, 0x0B, 0xB4, 0x08]))
        if limit < 0:
            if bytes(rom).find(bytes([0xE5, 0x0B, 0xB4, 0x09])) >= 0:
                raise SystemExit('this image already carries the menu patch — '
                                 'build a fresh V2.0 with mkv20.py first')
            raise SystemExit('count limit of the menu not found')
        rom[limit+3] = 0x09
        print('  count limit at %04Xh: 08h -> 09h, the menu now counts 1..8'
              % (limit+3))
        print('  ==> menu number 8 starts the melody')

    # 4. The old trampoline on ROM curve 3 stays untouched: no operating
    #    step leads there (measured), so it would be a dead trigger. The
    #    entry runs through the diagnostic menu.

    # 5. Checksum
    rom[end+1] = romfix.summe(bytes(rom), end)
    print('checksum over 0000h..%04Xh: %02Xh' % (end, rom[end+1]))
    open(target, 'wb').write(bytes(rom))
    print('written:', target)

if __name__ == '__main__':
    main(sys.argv)
