#!/usr/bin/env python3
"""A polyphonic player in the free ROM of the PM5139.

`mkdoom.py` plays one voice: it writes a note into 50h..52h and calls
OUT_FREQ. This one puts a **chord** into the waveform RAM first, so every
note the melody plays sounds as a whole chord, transposed with it. The
polyphony costs nothing while it sounds — the TWS reads the table, the CPU
only retunes.

Why a chord fits in the table: the wavetable holds exactly one period of
the output, so a sum of harmonics is still periodic in its 1024 points
(see `mkchord.py`). A table built from 2:3:4 played at f0 sounds as root,
fifth and octave — a power chord, which is what the E1M1 riff is made of.

Why the chord does not change during the melody: a full table reload is
2048 bytes over the C-bus and costs about 32 ms measured, and the TWS is
disabled while it runs (P1.5). That is fine between phrases, not between
sixteenth notes. So the harmony lives in the table and the melody moves
by retuning, which transposes the whole chord in parallel.

The loader mirrors the firmware's own frame exactly: 4321h sets up the
TWS and sends the STR6 command, a strobe on STR2 follows, P1.5 goes low,
1024 points go out as two bytes each with a DBK pulse on P3.5 and the
RAM handshake after every point, and 4355h sends the STR1 word and puts
the RAM back into read mode.

    python3 mkpoly.py M27512_PM5139_V20.bin out.bin
    python3 mkpoly.py --chord major --midi level1.mid --channel 1 in.bin out.bin
"""
import sys
import romfix, asm51, mcs51, mkchord, mkdoom

# The firmware routines the loader borrows. Both are version independent
# in behaviour but not in address, so they are located by signature.
# The setup begins SETB P1.5 / MOV DPTR,#<table> / MOVC, but that DPTR is
# version dependent, so the signature starts after it and the entry point
# is six bytes earlier. Both are unique in V1.3, V1.5 and V2.0.
SIG_SETUP  = bytes.fromhex('f514751300751220751101')   # entry = hit - 6
SIG_SETUP_BACK = 6
SIG_FINISH = bytes.fromhex('7b00742aa25c92e6')
# The state-output dispatcher (090Ch in V1.3, 0975h in V1.5/V2.0). It is
# gated by request bits in 29h and pushes the whole analog state out. The
# signature is the MOV C,29h.0 / ORL C,29h.1 / JNC nine bytes in.
SIG_DISPATCH = bytes.fromhex('a248724950')
SIG_DISPATCH_BACK = 9
# The routine that actually outputs the amplitude (0B15h in V1.5/V2.0).
# It computes the range byte into 1Eh and the fine value into 1Ch, then
# sends STR7 and STR9 — but only if 10h differs from the new 1Eh, which is
# the "nothing changed" gate. The signature is that comparison, sixteen
# bytes into the routine. V1.3 is built differently and has no match.
SIG_AMPL = bytes.fromhex('e510f51b651e60')
SIG_AMPL_BACK = 0x10


def encode_volts(v):
    """The two RAM bytes 56h/57h for an output amplitude in volts.

    Measured by driving the routine over the whole range: 56h holds the
    decade in the upper nibble and the hundreds digit in the lower, 57h
    the tens and units, and the amplitude is W * 10^(decade-4) volts with
    W the three BCD digits. The decade also picks the attenuator through
    the table at 0BE0h — `04 1C 14 04`, i.e. 0, 40, 20, 0 dB — so the
    largest usable decade is chosen, which is the least attenuation.
    """
    for d in (3, 2, 1, 0):
        w = round(v * 10 ** (4 - d))
        if 10 <= w <= 999:
            return (d << 4) | (w // 100), ((w // 10) % 10 << 4) | (w % 10), d, w
    raise SystemExit('%.3f V cannot be encoded' % v)


def find(rom, sig, what):
    p = rom.find(sig)
    if p < 0:
        raise SystemExit('%s: signature not found' % what)
    if rom.find(sig, p + 1) >= 0:
        raise SystemExit('%s: signature not unique' % what)
    return p


# The waveform RAM is not always in the signal path. Section 12: PGS is
# active for exactly five waveforms, and those are the ones that come out
# of the RAM. SINE, TRNGL, SQUARE, POSPULSE and NEGPULSE are made by the
# TWS directly and ignore the table completely; ARBIT has a path of its
# own and would pull a curve out of the EEPROM. So the player has to put
# the instrument into one of the five first — otherwise the chord sits in
# a memory nobody reads and what you hear is the TWS at f0, an octave
# below the melody. That is what the first burn did.
# The third column is the index the firmware's own loader passes to the
# setup routine. It selects a byte from the table at 4335h
# (1E 24 24 25 2C 34 13 1A) which becomes 14h of a frequency-format TWS
# command — so it is not a mode byte but a TWS setting, and it is not the
# same for every waveform. Known from the call sites of 4321h:
# index 1 = TRNGL/TRNGLPULSE (3DB0h), index 3 = HAV (3EFCh) and
# LOAD_ARB_ROM (9E4Ch). The rest are unmapped, so 0 is a guess there and
# is flagged as such.
RAM_WAVEFORMS = {           # bit, display name, setup index, index known?
    'hav':        ('2Bh.1', 'HAV',        3, True),
    'sinepulse':  ('2Bh.2', 'SINEPULSE',  0, False),
    'trnglpulse': ('2Bh.3', 'TRNGLPULSE', 1, True),
    'possaw':     ('2Ah.6', 'POSSAW',     0, False),
    'negsaw':     ('2Ah.7', 'NEGSAW',     0, False),
}


# The complete telegram sequence the firmware sends for a waveform
# command, recorded with cmd16.js on V1.3 (token 18h = HAV) and shown in
# section 36.7. The first player sent only entries 8..10 of these and the
# instrument accordingly never changed its waveform: the frequency
# followed, the shape did not. Entry 5 in particular, STR2 `00 80`, is
# what puts the waveform RAM into write mode; without it the table lands
# nowhere.
#
# Entries 8..10 are the load itself and are replaced by our own table, so
# the replay is split into a part before and a part after.
HAV_BEFORE = [
    (6, [0xD0, 0x07, 0x20, 0x01]),
    (3, [0x80, 0x01]),
    (9, [0x00]),
    (6, [0x00, 0x00, 0x00, 0x60]),
    (2, [0x00, 0x80]),
    (1, [0x00, 0x20]),
    (1, [0x00, 0x2E]),
]
# Entries 11..14 of the recorded sequence — STR6 `00 00 00 60`, STR1
# `00 20`, STR1 `00 19`, STR6 `D0 07 20 01` — are emitted by the
# firmware's finish routine, which our loader already tail-jumps to. Only
# the amplitude and offset block behind them has to be replayed.
# The last entry is the amplitude. STR9 carries twelve bits as two
# one-byte telegrams through the QS' cascade, so the byte sent *last*
# ends up in D101 as the upper eight bits of the AM6012. The recording
# had 6Eh — about 43 % of full scale, which is why the first working
# build only produced about 1 Vpp. LEVEL replaces it.
HAV_AFTER = [
    (7, [0x57, 0x64]),
    (7, [0x14, 0x64]),
    (7, [0x14, 0x64]),
    (7, [0x14, 0x64]),
    (9, [0x6E]),          # patched from `level`
]


def test_suite(chord_name):
    """Six tables, each answering one question, in one burn.

    They run in this order at one fixed frequency, three seconds each, so
    the shapes are directly comparable on a scope. The flat one comes
    first because a straight line is an unmistakable start-of-cycle mark.
    """
    N = mkchord.N
    ramp = [1 + (i * 1022) // (N - 1) for i in range(N)]

    def swapped(values):
        b = bytearray(mkchord.pack(values))
        for i in range(0, len(b), 2):
            b[i], b[i + 1] = b[i + 1], b[i]
        return bytes(b)

    return [
        ('flat',   mkchord.pack([512] * N),
         'every point 512 — the output must go flat. If it does, our bytes '
         'reach the converter; if a waveform is still there, the RAM is not '
         'being read at all'),
        ('ramp',   mkchord.pack(ramp),
         'a rising sawtooth over the full range. Clean ramp = the streaming '
         'and the byte order are right'),
        ('swap',   swapped(ramp),
         'the same ramp with the two bytes of every point exchanged. If THIS '
         'is the clean one, our byte order is inverted'),
        ('coarse', mkchord.pack([(v // 4) * 4 for v in ramp]),
         'the ramp with the two low bits forced to zero, so the first byte of '
         'every point is 00h. Clean here but noisy at "ramp" means the low '
         'bit pair is packed wrongly'),
        ('half',   mkchord.pack([1 + (i * 1022) // 511 if i < 512 else 512
                                 for i in range(N)]),
         'a ramp over the first 512 points, flat over the rest. Two ramps per '
         'period would mean only 512 points are read'),
        ('chord',  mkchord.table(chord_name),
         'the real thing — the chord'),
    ]


def ramp_table():
    """A plain rising ramp over the full range, as a scope test pattern.

    A chord is hard to judge by eye; a sawtooth is not. If this comes out
    of the instrument as a clean ramp, the streaming into the waveform
    RAM works and only the chord data is in question. If it comes out as
    noise, the streaming is wrong and the chord is irrelevant.
    """
    return mkchord.pack([1 + (i * 1022) // (mkchord.N - 1) for i in range(mkchord.N)])


def telegram_table(entries):
    """strobe, count, bytes ... terminated by a strobe of 0."""
    out = bytearray()
    for strobe, data in entries:
        out.append(strobe)
        out.append(len(data))
        out += bytes(data)
    out.append(0x00)
    return bytes(out)


# Candidate amplitude settings, to be judged on the instrument. STR9
# carries twelve bits as two telegrams through the QS' cascade, so a
# single byte leaves the pair half-updated and the previous contents
# shift into the second register — which may be exactly what went wrong.
# The second STR7 byte is the DC offset 1Dh, 64h being the zero line.
AMP_TRIALS = [
    ('baseline, nothing sent — the reference', 150.0, []),
    ('offset only: STR7 04 64 (1Dh = 64h, zero line)', 200.0,
     [(7, [0x04, 0x64])]),
    ('offset + STR9 pair 00 64', 250.0,
     [(7, [0x04, 0x64]), (9, [0x00]), (9, [0x64])]),
    ('offset + STR9 pair 00 FF', 300.0,
     [(7, [0x04, 0x64]), (9, [0x00]), (9, [0xFF])]),
    ('offset + STR9 pair 80 FF', 350.0,
     [(7, [0x04, 0x64]), (9, [0x80]), (9, [0xFF])]),
    ('offset + STR9 single FF (as before)', 400.0,
     [(7, [0x04, 0x64]), (9, [0xFF])]),
]


def triangle_table():
    """A symmetric triangle — the easiest thing to read a Vpp off."""
    N = mkchord.N
    v = []
    for i in range(N):
        x = i / N
        v.append(1 + round(2044 * (x * 2 if x < 0.5 else 2 - x * 2)) // 2)
    return mkchord.pack([min(1023, max(1, y)) for y in v])


# The amplitude matrix. One test per entry, and the *frequency identifies
# the test*: test n runs at MATRIX_BASE + n*10 Hz, so the scope's own
# frequency read-out says which combination is active and no counting is
# needed. The attenuator relays hold their state, so a test is affected by
# the one before it — which is exactly why the useful question is not
# "which is loud" but **"at which frequency does it become loud again"**.
MATRIX_BASE = 100.0


def full_amp_matrix():
    """The complete amplitude picture: relays and DAC, in one run.

    Every test writes both the STR7 relay byte and the STR9 DAC, so each
    step stands on its own and the sticky relay state cannot carry over.
    The relay byte uses 04h as its base, because that is what the
    firmware's own table at 0BE0h contains — with the field in bits 3..5
    the values come out as 04h, 0Ch, 14h, 1Ch..., and 04h/14h/1Ch are
    exactly the three entries of that table.

    Block A varies the relays at full DAC, block B varies the DAC at a
    fixed relay setting, so attenuation and fine control can be told
    apart.
    """
    t = [('nothing — reference', [],
          'the front-panel state, about 8.3 Vpp. Everything else is relative to this')]
    for f in range(8):
        b = (f << 3) | 0x04
        note = {0x04: '  = table entry "0 dB"',
                0x14: '  = table entry "20 dB"',
                0x1C: '  = table entry "40 dB"'}.get(b, '')
        t.append(('STR7 %02X + DAC FF' % b,
                  [(7, [b, 0x64]), (9, [0x00]), (9, [0xFF])],
                  'relays 5-4-3 = %d%d%d%s' % ((f >> 2) & 1, (f >> 1) & 1, f & 1, note)))
    for d in (0x00, 0x20, 0x40, 0x60, 0x80, 0xA0, 0xC0, 0xFF):
        t.append(('STR7 04 + DAC %02X' % d,
                  [(7, [0x04, 0x64]), (9, [0x00]), (9, [d])],
                  'DAC %3d of 255 — should be %d %% of the 110 Hz step if linear'
                  % (d, round(d * 100 / 255))))
    return t


def relay_matrix():
    """The eight combinations of the relay field in the first STR7 byte.

    Bits 3, 4 and 5 click; bits 0..2 do nothing to the level. Eight
    combinations, each with the STR9 DAC at full scale so the fine value
    cannot confuse the reading, plus a reference that sends nothing.
    """
    t = [('nothing — reference', [],
          'about 8.3 Vpp, the front-panel state')]
    for f in range(8):
        b = f << 3
        t.append(('STR7 %02X 64 + DAC FF' % b,
                  [(7, [b, 0x64]), (9, [0x00]), (9, [0xFF])],
                  'relay bits 5-4-3 = %d%d%d%s'
                  % ((f >> 2) & 1, (f >> 1) & 1, f & 1,
                     '   (14h family: the boot/1.1 V state)' if b == 0x10 else
                     '   (1Ch family: the 40 dB table entry)' if b == 0x18 else '')))
    return t


def amp_matrix():
    """(label, telegrams, what to expect) per test."""
    t = [('nothing — reference', [], 'about 8.3 Vpp. If not, the run did '
          'not start from the front-panel state — power up normally first')]
    # the first STR7 byte is masked with 27h before sending, so these are
    # all the distinct values that byte can carry
    for x in (0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
              0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27):
        why = ('04h is known quiet (100 mV)' if x == 0x04 else
               'loud here = the attenuator is this byte')
        t.append(('STR7 %02X 64' % x, [(7, [x, 0x64])], why))
    # the values the firmware itself sends on STR7 during a cold boot
    for pair, why in (((0x18, 0x80), 'second byte 80h instead of 64h — watch '
                       'the vertical POSITION, not the height'),
                      ((0x20, 0x64), 'a value the firmware itself sends'),
                      ((0x14, 0x64), 'the boot value, which belongs to the '
                       '1.1 V state — quiet would fit that')):
        t.append(('STR7 %02X %02X (boot)' % pair, [(7, list(pair))], why))
    # STR9 as a pair, without touching STR7
    ladder = 'THE KEY GROUP: 00/40/80/C0/FF should climb steadily if STR9 is the DAC'
    for a2, b2, why in ((0x00, 0x00, ladder + ' — this one silent or minimum'),
                        (0x00, 0x40, 'a quarter of the way up'),
                        (0x00, 0x80, 'half'),
                        (0x00, 0xC0, 'three quarters'),
                        (0x00, 0xFF, 'maximum of the ladder'),
                        (0x80, 0xFF, 'first byte varied — a BIG jump here means '
                         'the relays sit in it'),
                        (0xF8, 0xFF, 'all relay bits set'),
                        (0x07, 0xFF, 'only the low DAC bits set'),
                        (0x00, 0x37, 'the value the firmware sends at boot')):
        t.append(('STR9 pair %02X %02X' % (a2, b2), [(9, [a2]), (9, [b2])], why))
    t.append(('STR9 single FF', [(9, [0xFF])],
              'differs from the 00 FF pair = a single telegram desynchronises '
              'the cascade'))
    t.append(('STR9 single 37', [(9, [0x37])], 'the same question, boot value'))
    return t


def run_matrix(a, freq, tests, seconds=2.0):
    a.label('mxloop')
    for n, (_, tel, _w) in enumerate(tests):
        if tel:
            a.op('MOV DPTR,#mx%d' % n)
            a.op('LCALL rep')
        b = bcd_freq(MATRIX_BASE + n * 10)
        a.op('MOV 50h,#%02Xh' % b[0])
        a.op('MOV 51h,#%02Xh' % b[1])
        a.op('MOV 52h,#%02Xh' % b[2])
        a.op('LCALL %04Xh' % freq)
        hold(a, 'm%d' % n, seconds)
    a.op('LJMP mxloop')


def amp_sweep(a, freq, seconds=3.0):
    """Try each candidate in turn at its own pitch, so the loudest one can
    be named without any measurement — just listen for which step jumps."""
    a.label('amploop')
    for n, (_, hz, tel) in enumerate(AMP_TRIALS):
        if tel:
            a.op('MOV DPTR,#amp%d' % n)
            a.op('LCALL rep')
        b = bcd_freq(hz)
        a.op('MOV 50h,#%02Xh' % b[0])
        a.op('MOV 51h,#%02Xh' % b[1])
        a.op('MOV 52h,#%02Xh' % b[2])
        a.op('LCALL %04Xh' % freq)
        hold(a, 'a%d' % n, seconds)
    a.op('LJMP amploop')


def set_level(a, value):
    """Set the output level through STR9 and the attenuator through STR7.

    Measured over the full matrix, 30 s per step:

      relay field, bits 3..5 of the first STR7 byte, DAC at full scale
        000 (04h) 120 mV   both attenuators in, -40 dB
        001 (0Ch) 1.2 V    one out
        010 (14h) 1.2 V    the other out
        011 (1Ch) 11.6 V   both out, 0 dB   <- the loud one
        bit 5 adds nothing to the level (it clicks; most likely K403,
        the 50/600 ohm relay, which a high-impedance probe does not see)

      DAC, second STR9 byte, relays fixed
        00h 0 mV   20h 40 mV   40h 66 mV   60h 100 mV
        80h 0 mV   A0h 40 mV   C0h 62 mV   FFh 120 mV

    So bits 3 and 4 are two separate 20 dB stages — which is why 001 and
    010 give the same level and switching between them clicks — and the
    ROM table `04 1C 14 04` reads the other way round from what section 20
    recorded: 04h is *most* attenuated, 1Ch is *least*. They are bypass
    bits.

    The DAC wraps at 80h, so it is effectively seven bits; the firmware
    stays well inside that, computing 64h for a full 20 Vpp. Values above
    7Fh fold back to nothing.

    One STR9 telegram sets the level, with no relay involved — that is the
    envelope primitive.
    """
    a.op('MOV DPTR,#lvl')
    a.op('LCALL rep')


def set_amplitude(a, ampl, volts):
    """Let the firmware set the output amplitude.

    Writing 56h/57h alone does nothing — the routine compares 10h with the
    range byte it computes and returns silently when they match, so 10h is
    poisoned first to force the output.
    """
    b56, b57, d, w = encode_volts(volts)
    # The DC offset has to be set too. STR7 pushes two bytes into a single
    # 8-bit register (D301), so only the byte sent *last* survives, and
    # that one is 1Dh — the offset, in offset binary with 64h as the zero
    # line. The player never wrote 1Dh, so the routine sent whatever was
    # in RAM: the output sat hard on one side and the ac swing collapsed
    # with it. 58h/59h are the BCD source OFFSET_CALC computes 1Dh from.
    a.op('MOV 58h,#00h')
    a.op('MOV 59h,#00h')
    a.op('MOV 1Dh,#64h')                # zero offset
    a.op('MOV 56h,#%02Xh' % b56)
    a.op('MOV 57h,#%02Xh' % b57)
    a.op('MOV 10h,#0AAh')               # defeat the "nothing changed" gate
    a.op('LCALL %04Xh' % ampl)
    return d, w


def replay(a):
    """Send the telegram list at DPTR. Own code, so it does not depend on
    the addresses of the firmware's send stubs."""
    a.label('rep')
    a.op('CLR A'); a.op('MOVC A,@A+DPTR')
    a.op('JZ repdone')
    a.op('MOV R1,A')                    # strobe number
    a.op('INC DPTR')
    a.op('CLR A'); a.op('MOVC A,@A+DPTR')
    a.op('MOV R2,A')                    # byte count
    a.op('INC DPTR')
    a.label('repbyte')
    a.op('CLR A'); a.op('MOVC A,@A+DPTR')
    a.op('MOV SBUF,A')
    a.op('CLR TI')
    a.label('repwait'); a.op('JNB TI,repwait')
    a.op('INC DPTR')
    a.op('DJNZ R2,repbyte')
    a.op('PUSH DPL'); a.op('PUSH DPH')  # DPH is the strobe address now
    a.op('MOV DPL,#00h')
    a.op('MOV A,R1'); a.op('ORL A,#80h')
    a.op('MOV DPH,A')
    a.op('MOVX @DPTR,A')
    a.op('MOV DPH,#80h')
    a.op('MOVX @DPTR,A')
    a.op('POP DPH'); a.op('POP DPL')
    a.op('SJMP rep')
    a.label('repdone')
    a.op('RET')


def select_waveform(a, which, dispatch):
    """Put the instrument on a waveform that reads the waveform RAM.

    Setting the bits in 2Ah/2Bh is not enough — that is only firmware
    state. The analog routing sits in shift registers, and the mux that
    picks the waveform hangs on **STR3** (D144 on unit 4). Measured with
    `cmd16.js`: a waveform command sets 29h = 06h and produces

        STR1 STR2 STR3 STR6 STR7 STR9

    while the first version of this player sent only STR6, STR2 and STR1.
    That is exactly why the frequency followed but the shape never
    changed on the instrument.

    So the bits are set and then the firmware's own dispatcher is asked
    to output the lot. It also reloads its own table for that waveform —
    harmless, because our loader runs afterwards and overwrites it.
    """
    bit = RAM_WAVEFORMS[which][0]
    a.op('MOV 2Ah,#00h')                # clears DC, SINE, TRNGL, SQUARE,
    a.op('CLR 2Bh.2')                   # the two pulses and both sawtooths
    a.op('CLR 2Bh.3')
    a.op('CLR 2Bh.4')                   # not ARBIT: that reloads from EEPROM
    a.op('CLR 2Bh.1')
    a.op('SETB %s' % bit)
    a.op('SETB P3.4')                   # PGS: the RAM feeds the output
    # The dispatcher at 090Ch/0975h cannot be called from here — it does
    # not return, it ends in the main loop (measured). So the telegrams
    # are replayed from the recorded list instead.
    a.op('MOV DPTR,#before')
    a.op('LCALL rep')


def loader(a, setup, finish, table_label, tag=''):
    """Streams 1024 points from ROM into the waveform RAM.

    The two SBUF writes of a point must sit at least eight machine cycles
    apart, one byte time at the mode-0 shift clock of fosc/12. The
    firmware pads with seven NOPs; here the pointer arithmetic fills the
    gap and a single NOP tops it up — see the cycle count in the test.
    """
    # A already holds the index into the table at 4335h
    a.op('LCALL %04Xh' % setup)         # -> SETB P1.5 and the STR6 command
    a.op('MOV DPH,#82h')
    a.op('MOVX @DPTR,A')                # STR2: the mode byte 4321h returned
    a.op('CLR P1.5')                    # EN low, the TWS stops reading
    a.op('MOV DPTR,#%s' % table_label)
    a.op('MOV R2,#04h')                 # four passes of 256 points
    a.op('MOV R5,#00h')
    a.label('point%s' % tag)
    a.op('CLR A'); a.op('MOVC A,@A+DPTR')
    a.op('MOV SBUF,A')                  # low byte: the two least bits
    a.op('INC DPTR')                    # -- 7 cycles of byte time --
    a.op('CLR A'); a.op('MOVC A,@A+DPTR')
    a.op('INC DPTR')
    a.op('NOP')                         # -- the eighth --
    a.op('MOV SBUF,A')                  # high byte: the upper eight bits
    a.op('CLR P3.5'); a.op('SETB P3.5')  # DBK clocks the point into the RAM
    a.op('PUSH DPL'); a.op('PUSH DPH')   # DPH is needed for the status read
    a.op('MOV DPH,#80h')
    a.op('INC R5')                      # the handshake polarity alternates
    a.op('MOV A,R5')                    # with the point number, exactly as
    a.op('RRC A')                       # the firmware does at 3D8Dh
    a.op('MOV 22h.7,C')
    a.label('wait%s' % tag)
    a.op('MOVX A,@DPTR')                # STR0 status, ACC.4 = RAM busy
    a.op('JB 22h.7,ready%s' % tag)
    a.op('CPL A')
    a.label('ready%s' % tag)
    a.op('JNB ACC.4,wait%s' % tag)
    a.op('POP DPH'); a.op('POP DPL')
    a.op('CJNE R5,#00h,point%s' % tag)          # 256 points per pass
    a.op('DJNZ R2,point%s' % tag)
    a.op('LJMP %04Xh' % finish)         # STR1 word, RAM back to read mode;
    #                                     its RET returns to our LCALL


def player(a, freq, notes_label, envel=False):
    """The melody loop, as in mkdoom.py: three bytes of frequency, one of
    duration, terminated by a zero byte, then round again."""
    a.label('loop')
    a.op('CLR A'); a.op('MOVC A,@A+DPTR'); a.op('JZ done')
    a.op('MOV 50h,A'); a.op('INC DPTR')
    a.op('CLR A'); a.op('MOVC A,@A+DPTR'); a.op('MOV 51h,A'); a.op('INC DPTR')
    a.op('CLR A'); a.op('MOVC A,@A+DPTR'); a.op('MOV 52h,A'); a.op('INC DPTR')
    a.op('CLR A'); a.op('MOVC A,@A+DPTR'); a.op('MOV R5,A');  a.op('INC DPTR')
    a.op('PUSH DPH'); a.op('PUSH DPL')
    a.op('LCALL %04Xh' % freq)
    a.op('POP DPL'); a.op('POP DPH')
    if envel:
        a.op('MOV R3,#00h')             # restart the envelope on every note
    a.label('hold')                     # one unit = 1009 us, measured
    if envel:
        envelope_step(a, 'n')           # about 45 us of the 1009
    a.op('MOV R6,#02h')
    a.label('h2'); a.op('MOV R7,#0FAh')
    a.label('h3'); a.op('DJNZ R7,h3')
    a.op('DJNZ R6,h2')
    a.op('DJNZ R5,hold')
    a.op('SJMP loop')
    a.label('done')
    a.op('MOV DPTR,#%s' % notes_label)  # start the melody again
    a.op('SJMP loop')


def envelope_table(peak=0x7F, floor=0x06, tau=40.0, n=128):
    """A plucked shape for the amplitude DAC.

    One byte per step, and a step is one unit of the wait loop, so about
    1009 us — roughly a 1 kHz envelope rate. 128 entries cover 129 ms and
    the last value is held for anything longer.

    Without this every note is a flat tone and the whole thing sounds like
    an organ. The DAC is seven bits (section 36.8), so the values stay
    inside 00h..7Fh.
    """
    import math
    out = bytearray()
    for i in range(n):
        v = peak * math.exp(-i / tau)
        out.append(max(floor, min(peak, int(round(v)))))
    return bytes(out)


def envelope_step(a, tag):
    """Send one envelope value to STR9 and advance the index in R3.

    R3 is the step counter, clamped at 7Fh so a long note holds the tail.
    DPTR belongs to the note table, so it is saved across the lookup, and
    the value is stashed in R1 because R6 and R7 are the delay counters.
    """
    a.op('PUSH DPL'); a.op('PUSH DPH')
    a.op('MOV DPTR,#envtab')
    a.op('MOV A,R3')
    a.op('CLR C')                       # MOVC needs a clean carry-free A
    a.op('MOVC A,@A+DPTR')
    # One byte is enough: measured, a single STR9 telegram changes the
    # level, and the first byte of a pair has no effect on it anyway
    # (section 36.8). So the previous value simply shifts on into the
    # register that does not matter.
    a.op('MOV SBUF,A')
    a.op('CLR TI')
    a.label('ew1%s' % tag); a.op('JNB TI,ew1%s' % tag)
    a.op('MOV DPH,#89h')                # fire STR9
    a.op('MOV DPL,#00h')
    a.op('MOVX @DPTR,A')
    a.op('MOV DPH,#80h')
    a.op('MOVX @DPTR,A')
    a.op('POP DPH'); a.op('POP DPL')
    a.op('INC R3')                      # advance, clamp at 7Fh
    a.op('MOV A,R3')
    a.op('JNB ACC.7,eok%s' % tag)
    a.op('DEC R3')
    a.label('eok%s' % tag)


def hold(a, tag, seconds):
    """Busy-wait roughly `seconds`, in units of the 1009 us wait loop."""
    outer = max(1, min(255, round(seconds / (255 * 0.001009))))
    a.op('MOV R4,#%02Xh' % outer)
    a.label('ho%s' % tag)
    a.op('MOV R5,#0FFh')
    a.label('hu%s' % tag)
    a.op('MOV R6,#02h')
    a.label('hv%s' % tag); a.op('MOV R7,#0FAh')
    a.label('hw%s' % tag); a.op('DJNZ R7,hw%s' % tag)
    a.op('DJNZ R6,hv%s' % tag)
    a.op('DJNZ R5,hu%s' % tag)
    a.op('DJNZ R4,ho%s' % tag)


def bcd_freq(hz):
    """The three bytes for 50h..52h: decade 3, frequency in 0.01 Hz."""
    z = '%05d' % round(hz * 100)
    if len(z) > 5:
        raise SystemExit('%.2f Hz does not fit decade 3' % hz)
    return ((3 << 4) | int(z[0]), (int(z[1]) << 4) | int(z[2]),
            (int(z[3]) << 4) | int(z[4]))


def probe(a, freq, order, dispatch, seconds=3.0):
    """Diagnostic: no melody at all.

    Cycles through the waveforms that read the waveform RAM, loading the
    chord table for each and then holding one frequency, so the question
    "does our table reach the output" can be answered on a scope instead
    of by ear. Each stage gets its own pitch so it can be told apart:
    100, 150, 200, 250, 300 Hz for f0.
    """
    a.label('probeloop')
    for n, (which, hz) in enumerate(order):
        select_waveform(a, which, dispatch)
        a.op('MOV A,#%02Xh' % RAM_WAVEFORMS[which][2])
        a.op('LCALL loadidx')
        a.op('MOV DPTR,#after')
        a.op('LCALL rep')
        b = bcd_freq(hz)
        a.op('MOV 50h,#%02Xh' % b[0])
        a.op('MOV 51h,#%02Xh' % b[1])
        a.op('MOV 52h,#%02Xh' % b[2])
        a.op('LCALL %04Xh' % freq)
        hold(a, 'p%d' % n, seconds)
    a.op('LJMP probeloop')


def hold_suite(a, freq, hz, index, names, seconds=3.0):
    """Load each test table in turn and hold one frequency after it."""
    a.label('suiteloop')
    for n in names:
        a.op('MOV DPTR,#before')
        a.op('LCALL rep')
        a.op('MOV A,#%02Xh' % index)
        a.op('LCALL ld_%s' % n)
        a.op('MOV DPTR,#after')
        a.op('LCALL rep')
        b = bcd_freq(hz)
        a.op('MOV 50h,#%02Xh' % b[0])
        a.op('MOV 51h,#%02Xh' % b[1])
        a.op('MOV 52h,#%02Xh' % b[2])
        a.op('LCALL %04Xh' % freq)
        hold(a, 's_%s' % n, seconds)
    a.op('LJMP suiteloop')


def hold_two(a, freq, finish, setup, hz, index, seconds=3.0):
    """Alternate two tables at one fixed frequency.

    A burn is expensive, so this shows both in one go: first the ramp,
    then the chord, three seconds each, for ever. On a scope the ramp is
    unmistakable, so it says whether the streaming into the waveform RAM
    works at all, and the chord right after it says whether the chord
    data is right — two answers, one EPROM.
    """
    a.label('twoloop')
    for n, label in (('r', 'table'), ('c', 'table2')):
        a.op('MOV DPTR,#before')
        a.op('LCALL rep')
        a.op('MOV A,#%02Xh' % index)
        a.op('LCALL load_%s' % n)
        a.op('MOV DPTR,#after')
        a.op('LCALL rep')
        b = bcd_freq(hz)
        a.op('MOV 50h,#%02Xh' % b[0])
        a.op('MOV 51h,#%02Xh' % b[1])
        a.op('MOV 52h,#%02Xh' % b[2])
        a.op('LCALL %04Xh' % freq)
        hold(a, 't%s' % n, seconds)
    a.op('LJMP twoloop')


def scale(a, freq, hz_list, seconds=1.0):
    """A slow, unmistakable sequence: a handful of chords, one second each.

    The built-in riff is seven identical notes and one turning note, all
    between 82 and 165 Hz — a register in which a small speaker gives
    almost nothing and in which seven repeats of the same pitch do not
    sound like a melody at all. This plays widely spaced chords in a
    comfortable register instead, so it is immediately obvious whether
    the notes advance.
    """
    a.label('scaleloop')
    for n, hz in enumerate(hz_list):
        b = bcd_freq(hz)
        a.op('MOV 50h,#%02Xh' % b[0])
        a.op('MOV 51h,#%02Xh' % b[1])
        a.op('MOV 52h,#%02Xh' % b[2])
        a.op('LCALL %04Xh' % freq)
        hold(a, 'sc%d' % n, seconds)
    a.op('LJMP scaleloop')


def hold_one(a, freq, hz):
    """Set one frequency and stay there. No melody, no cycling — so what
    is on the output is nothing but the table."""
    b = bcd_freq(hz)
    a.op('MOV 50h,#%02Xh' % b[0])
    a.op('MOV 51h,#%02Xh' % b[1])
    a.op('MOV 52h,#%02Xh' % b[2])
    a.op('LCALL %04Xh' % freq)
    a.label('forever')
    a.op('SJMP forever')


def notes(chord_name, midi_file=None, rule='high', channel=None, tempo=1.0):
    """The note table, with every frequency divided by the lowest harmonic
    so the chord lands on the pitch the melody asks for."""
    h0 = min(mkchord.CHORDS[chord_name])
    raw = mkdoom.note_table(midi_file, rule, channel, tempo)
    out = bytearray()
    for i in range(0, len(raw) - 1, 4):
        hz = (((raw[i] & 0x0F) * 10000) + (raw[i+1] >> 4) * 1000 +
              (raw[i+1] & 0x0F) * 100 + (raw[i+2] >> 4) * 10 +
              (raw[i+2] & 0x0F)) / 100.0
        f0 = hz / h0
        z = '%05d' % round(f0 * 100)
        if len(z) > 5:
            raise SystemExit('f0 = %.2f Hz does not fit the decade' % f0)
        out += bytes([(3 << 4) | int(z[0]),
                      (int(z[1]) << 4) | int(z[2]),
                      (int(z[3]) << 4) | int(z[4]), raw[i+3]])
    out.append(0x00)
    return bytes(out)


def main(argv):
    chord_name, midi_file, rule, channel, tempo = 'power', None, 'high', None, 1.0
    waveform = 'hav'
    mode = 'play'
    # The ramp lead-in was a diagnostic: a clean sawtooth on a scope said
    # the table reached the converter. It has done its job, and at full
    # output it is unpleasantly loud, so it is off unless asked for.
    leadin = False
    # None = do not touch STR9 at all, so the amplitude stays exactly as the
    # front panel left it before the diagnostic menu was entered. A number
    # sends that byte as the upper eight bits of the AM6012 instead.
    level = None
    volts = 20.0                 # amplitude the player sets for itself
    dac = 0x7F                   # STR9 amplitude DAC; it wraps above 7Fh
    envel = True                 # pluck the notes with the STR9 DAC
    decay = 40.0                 # envelope time constant, in units of 1009 us
    relay = 0x1C                 # STR7 relay byte: bits 3+4 set = both
                                 # attenuators bypassed, measured 11.6 Vpp
    step_s = 30.0                # seconds per matrix step
    volts = 20.0                 # output amplitude the player sets for itself
    hold_hz = 200.0
    pattern = 'chord'
    rest, i = [], 1
    while i < len(argv):
        if argv[i] == '--chord':     chord_name = argv[i+1]; i += 2
        elif argv[i] == '--probe': mode = 'probe'; i += 1
        elif argv[i] == '--leadin': leadin = True; i += 1
        elif argv[i] == '--level':
            level = None if argv[i+1] == 'keep' else int(argv[i+1], 0)
            i += 2
        elif argv[i] == '--volts': volts = float(argv[i+1]); i += 2
        elif argv[i] == '--dac': dac = int(argv[i+1], 0); i += 2
        elif argv[i] == '--relay': relay = int(argv[i+1], 0); i += 2
        elif argv[i] == '--no-envelope': envel = False; i += 1
        elif argv[i] == '--decay': decay = float(argv[i+1]); i += 2
        elif argv[i] == '--ampsweep': mode = 'amp'; i += 1
        elif argv[i] == '--matrix': mode = 'matrix'; i += 1
        elif argv[i] == '--relays': mode = 'relays'; i += 1
        elif argv[i] == '--ampmatrix': mode = 'ampmatrix'; i += 1
        elif argv[i] == '--step': step_s = float(argv[i+1]); i += 2
        elif argv[i] == '--scale': mode = 'scale'; i += 1
        elif argv[i] == '--hold':  mode = 'hold'; hold_hz = float(argv[i+1]); i += 2
        elif argv[i] == '--pattern': pattern = argv[i+1]; i += 2
        elif argv[i] == '--waveform':
            waveform = argv[i+1]
            if waveform != 'none' and waveform not in RAM_WAVEFORMS:
                raise SystemExit('waveform must be "none" or one of: %s'
                                 % ' '.join(RAM_WAVEFORMS))
            i += 2
        elif argv[i] == '--midi':    midi_file = argv[i+1]; i += 2
        elif argv[i] == '--voice':   rule = argv[i+1]; i += 2
        elif argv[i] == '--channel': channel = int(argv[i+1]); rule = 'channel'; i += 2
        elif argv[i] == '--tempo':   tempo = float(argv[i+1]); i += 2
        else: rest.append(argv[i]); i += 1
    source = rest[0] if rest else 'M27512_PM5139_V20.bin'
    target = rest[1] if len(rest) > 1 else source
    rom = bytearray(open(source, 'rb').read())
    SUITE = test_suite(chord_name) if pattern == 'suite' else []
    MATRIX = (amp_matrix() if mode == 'matrix'
              else relay_matrix() if mode == 'relays'
              else full_amp_matrix() if mode == 'ampmatrix' else [])

    setup = find(bytes(rom), SIG_SETUP, 'the loader setup (4321h in V1.3)') - SIG_SETUP_BACK
    finish = find(bytes(rom), SIG_FINISH, 'the loader finish (4355h in V1.3)')
    dispatch = find(bytes(rom), SIG_DISPATCH,
                    'the state dispatcher (090Ch in V1.3)') - SIG_DISPATCH_BACK
    p = bytes(rom).find(SIG_AMPL)
    ampl = (p - SIG_AMPL_BACK) if p >= 0 else None
    print('loader frame: setup at %04Xh, finish at %04Xh, dispatcher at %04Xh'
          % (setup, finish, dispatch))

    _, end_probe = romfix.endadresse(bytes(rom))
    tab = __import__('symbols_v15' if end_probe > 0xB000 else 'symbols')
    freq = [a for a, (n, _, _) in tab.ROUTINES.items() if n == 'OUT_FREQ']
    if len(freq) != 1:
        raise SystemExit('OUT_FREQ not unambiguous in the symbol table')
    freq = freq[0]
    print('OUT_FREQ at %04Xh (from %s)' % (freq, tab.__name__))

    _, end = romfix.endadresse(bytes(rom))
    base = end + 2
    a = asm51.Asm(base)
    # The loader has to be a subroutine: it ends by tail-jumping into the
    # firmware's finish routine, whose RET then returns here — jumping to
    # it inline would return past the melody to our own caller.
    ORDER = [('hav', 100.0), ('possaw', 150.0), ('negsaw', 200.0),
             ('sinepulse', 250.0), ('trnglpulse', 300.0)]
    if mode == 'probe':
        probe(a, freq, ORDER, dispatch)
    elif mode in ('matrix', 'relays', 'ampmatrix'):
        select_waveform(a, waveform, dispatch)
        a.op('MOV A,#%02Xh' % RAM_WAVEFORMS[waveform][2])
        a.op('LCALL loadidx')
        a.op('MOV DPTR,#after')
        a.op('LCALL rep')
        run_matrix(a, freq, MATRIX, step_s)
    elif mode == 'amp':
        select_waveform(a, waveform, dispatch)
        a.op('MOV A,#%02Xh' % RAM_WAVEFORMS[waveform][2])
        a.op('LCALL loadidx')
        a.op('MOV DPTR,#after')
        a.op('LCALL rep')
        amp_sweep(a, freq)
    elif mode == 'scale':
        # roots at 200, 250, 300, 400, 500, 600, 800 Hz — f0 is half of each
        SCALE = [100.0, 125.0, 150.0, 200.0, 250.0, 300.0, 400.0]
        select_waveform(a, waveform, dispatch)
        a.op('MOV A,#%02Xh' % RAM_WAVEFORMS[waveform][2])
        a.op('LCALL loadidx')
        a.op('MOV DPTR,#after')
        a.op('LCALL rep')
        scale(a, freq, SCALE)
    elif mode == 'hold' and pattern == 'suite':
        select_waveform(a, waveform, dispatch)
        hold_suite(a, freq, hold_hz, RAM_WAVEFORMS[waveform][2],
                   [n for n, _, _ in SUITE])
    elif mode == 'hold' and pattern == 'both':
        select_waveform(a, waveform, dispatch)
        hold_two(a, freq, finish, setup, hold_hz, RAM_WAVEFORMS[waveform][2])
    elif mode == 'hold':
        select_waveform(a, waveform, dispatch)
        a.op('MOV A,#%02Xh' % RAM_WAVEFORMS[waveform][2])
        a.op('LCALL loadidx')
        a.op('MOV DPTR,#after')
        a.op('LCALL rep')
        hold_one(a, freq, hold_hz)
    else:
        if waveform != 'none':
            select_waveform(a, waveform, dispatch)
        idx = RAM_WAVEFORMS[waveform][2] if waveform != 'none' else 0
        if leadin:
            # Three seconds of a plain ramp before the music: on a scope a
            # clean sawtooth confirms in one glance that the table reaches
            # the converter, without needing a separate burn for it.
            a.op('MOV DPTR,#before'); a.op('LCALL rep')
            a.op('MOV A,#%02Xh' % idx)
            a.op('LCALL ld_lead')
            a.op('MOV DPTR,#after'); a.op('LCALL rep')
            b = bcd_freq(200.0)
            a.op('MOV 50h,#%02Xh' % b[0])
            a.op('MOV 51h,#%02Xh' % b[1])
            a.op('MOV 52h,#%02Xh' % b[2])
            a.op('LCALL %04Xh' % freq)
            hold(a, 'lead', 3.0)
            a.op('MOV DPTR,#before'); a.op('LCALL rep')
        a.op('MOV A,#%02Xh' % idx)
        a.op('LCALL loadidx')
        a.op('MOV DPTR,#after')
        a.op('LCALL rep')
        set_level(a, dac)
        a.op('MOV DPTR,#notes')
        player(a, freq, 'notes', envel)
    # the loader, entered with the setup index in A
    if pattern == 'suite':
        for n, _, _ in SUITE:
            a.label('ld_%s' % n)
            loader(a, setup, finish, 'tb_%s' % n, tag='_%s' % n)
    if mode in ('play',) and leadin:
        a.label('ld_lead')
        loader(a, setup, finish, 'tb_lead', tag='_lead')
    # loadidx must alias the loader for the *main* table, so it has to sit
    # after any extra loaders emitted above — otherwise LCALL loadidx ends
    # up in the lead-in ramp instead of the chord.
    a.label('loadidx')
    a.label('load_r')
    loader(a, setup, finish, 'table')
    if mode == 'hold' and pattern == 'both':
        a.label('load_c')
        loader(a, setup, finish, 'table2', tag='_c')
    replay(a)
    a.label('before'); a.db(*telegram_table(HAV_BEFORE))
    # STR9 carries the amplitude as two telegrams through the QS' cascade.
    # Sending only part of a pair would desynchronise it, so either both
    # entries stay or both go.
    before = [(s_, list(d)) for s_, d in HAV_BEFORE]
    after = [(s_, list(d)) for s_, d in HAV_AFTER]
    if mode in ('amp', 'matrix', 'relays', 'ampmatrix'):
        before = [e for e in before if e[0] not in (7, 9)]
        after = [e for e in after if e[0] not in (7, 9)]
    elif ampl is not None:
        # the amplitude routine sends its own STR7 and STR9; the recorded
        # ones carried 14h in the first STR7 byte, which is the 20 dB
        # attenuator — that was the missing factor of ten
        before = [e for e in before if e[0] != 9]
        after = [e for e in after if e[0] not in (7, 9)]
    elif level is None:
        # Measured on the instrument: sending nothing at all is the loudest
        # configuration (8.3 Vpp), the recorded STR7 bytes carry 14h in the
        # first position — the 20 dB attenuator — and cost a factor of
        # eight. So drop the whole amplitude and offset block and leave the
        # analog chain exactly as the front panel set it.
        before = [e for e in before if e[0] not in (7, 9)]
        after = [e for e in after if e[0] not in (7, 9)]
    else:
        after[-1] = (9, [level])
    a.label('before'); a.db(*telegram_table(before))
    a.label('after');  a.db(*telegram_table(after))
    a.label('lvl'); a.db(*telegram_table(
        ([(7, [relay, 0x64])] if relay is not None else [])
        + [(9, [0x00]), (9, [dac])]))
    if mode == 'amp':
        for n, (_, _, tel) in enumerate(AMP_TRIALS):
            if tel:
                a.label('amp%d' % n); a.db(*telegram_table(tel))
    if mode in ('matrix', 'relays', 'ampmatrix'):
        for n, (_, tel, _w) in enumerate(MATRIX):
            if tel:
                a.label('mx%d' % n); a.db(*telegram_table(tel))
    wave = (triangle_table() if mode in ('matrix', 'relays', 'ampmatrix')
            else ramp_table() if pattern in ('ramp', 'both')
            else mkchord.table(chord_name))
    tune = notes(chord_name, midi_file, rule, channel, tempo)
    if pattern == 'suite':
        for n, data, _ in SUITE:
            a.label('tb_%s' % n); a.db(*data)
    if mode == 'play' and leadin:
        a.label('tb_lead'); a.db(*ramp_table())
    a.label('table'); a.db(*wave)
    if mode == 'hold' and pattern == 'both':
        a.label('table2'); a.db(*mkchord.table(chord_name))
    if mode == 'play' and envel:
        a.label('envtab'); a.db(*envelope_table(peak=dac, tau=decay))
    a.label('notes'); a.db(*tune)
    code = a.finish()

    if base + len(code) >= len(rom):
        raise SystemExit('the player no longer fits into the ROM')
    rom[base:base+len(code)] = code
    h = mkchord.CHORDS[chord_name]
    print('player at %04Xh, %d bytes: %d of code, %d of chord table, %d of notes'
          % (base, len(code), len(code) - len(wave) - len(tune), len(wave), len(tune)))
    print('chord "%s" = harmonics %s, the melody is divided by %d'
          % (chord_name, ':'.join(str(x) for x in h), min(h)))
    if mode == 'play' and envel:
        e = envelope_table(peak=dac, tau=decay)
        print('envelope: %d steps of ~1.009 ms, %02Xh down to %02Xh, tau %.0f ms'
              % (len(e), e[0], e[-1], decay * 1.009))
    if mode == 'play':
        if dac > 0x7F:
            print('WARNING: the DAC wraps above 7Fh — %02Xh acts as %02Xh'
                  % (dac, dac & 0x7F))
        att = {0x00: 40, 0x08: 20, 0x10: 20, 0x18: 0}.get(relay & 0x18, None)
        print('level: STR7 %02Xh (attenuator %s) + STR9 DAC %02Xh of 7Fh'
              % (relay, ('%d dB' % att) if att is not None else '?', dac))
        print('       bits 3 and 4 are two 20 dB stages, both bypassed at 1Ch;')
        print('       measured 11.6 Vpp, more than the front panel gave.')
    if mode == 'ampmatrix':
        import textwrap
        print('AMPLITUDE MATRIX: %d steps, %.0f s each, triangle waveform.'
              % (len(MATRIX), step_s))
        print('   The frequency is the test number: %.0f + n*10 Hz.'
              % MATRIX_BASE)
        print('   Every step sets BOTH the relay byte and the DAC, so no state')
        print('   carries over from the step before.')
        print()
        print('   BLOCK A — the relays, DAC at full scale:')
        for n, (what, _, expect) in enumerate(MATRIX):
            if n == 9:
                print()
                print('   BLOCK B — the DAC, relays fixed at 04h:')
            head = '   %4.0f Hz  %-20s ' % (MATRIX_BASE + n * 10, what)
            print(textwrap.fill(expect, 94, initial_indent=head,
                                subsequent_indent=' ' * len(head)))
        print()
        print('   Note the Vpp at every step. Two questions get answered:')
        print('   A: how many distinct levels do the eight relay settings give,')
        print('      and are the steps 20 dB (factor 10) apart?')
        print('   B: is the DAC linear? 20h should be an eighth of FFh.')
    elif mode == 'relays':
        print('RELAY MATRIX: %d tests, the frequency is the test number'
              % len(MATRIX))
        import textwrap
        for n, (what, _, expect) in enumerate(MATRIX):
            head = '   %4.0f Hz  %-22s ' % (MATRIX_BASE + n * 10, what)
            print(textwrap.fill(expect, 92, initial_indent=head,
                                subsequent_indent=' ' * len(head)))
        print()
        print('   Look for the ONE combination that is as loud as 100 Hz.')
        print('   That is the 0 dB setting, and with it the level can finally')
        print('   be set deliberately instead of only left alone.')
    elif mode == 'matrix':
        print('AMPLITUDE MATRIX: %d tests, %.0f s each, triangle waveform.'
              % (len(MATRIX), 2.0))
        print('   The FREQUENCY is the test number: test n runs at %.0f + n*10 Hz.'
              % MATRIX_BASE)
        print('   Read the frequency off the scope, note the Vpp. The relays')
        print('   hold their state, so watch for where it becomes LOUD again.')
        print()
        import textwrap
        for n, (what, _, expect) in enumerate(MATRIX):
            head = '   %4.0f Hz  %-18s ' % (MATRIX_BASE + n * 10, what)
            print(textwrap.fill('expect: ' + expect, 96,
                                initial_indent=head,
                                subsequent_indent=' ' * len(head)))
        print()
        print('   WHAT TO LOOK FOR, in order of value:')
        print('   1. does any of 110-260 Hz come back to ~8 V?  -> the attenuator')
        print('      is that byte. If none does, it is provably somewhere else.')
        print('   2. do 300/310/320/330/340 Hz climb steadily?  -> STR9 is the')
        print('      amplitude DAC, and that is the envelope primitive.')
        print('   3. do 350/360/370 Hz jump in big steps (20 or 40 dB) rather')
        print('      than small ones?  -> the relays are in the first STR9 byte.')
        print('   4. at 270 Hz the second STR7 byte is 80h instead of 64h:')
        print('      watch whether the trace moves up or down, not its height.')
    elif mode == 'amp':
        print('AMPLITUDE SWEEP: six settings, 3 s each, each at its own pitch.')
        print('   Report which step is loudest.')
        for n, (why, hz, _) in enumerate(AMP_TRIALS, 1):
            print('   %d. %4.0f Hz   %s' % (n, hz, why))
    elif ampl is not None:
        b56, b57, d, w = encode_volts(volts)
        att = {3: 0, 2: 20, 1: 40, 0: 0}[d]
        print('amplitude: %.3g Vpp — 56h=%02Xh 57h=%02Xh (decade %d, W=%d),'
              % (volts, b56, b57, d, w))
        print('           attenuator %d dB, set through the routine at %04Xh'
              % (att, ampl))
    elif level is None:
        print('amplitude: STR9 left alone — the level stays as the front')
        print('           panel had it before the diagnostic menu')
    else:
        print('amplitude byte on STR9: %02Xh (%d %% of full scale)'
              % (level, round(level * 100 / 255)))
    if mode == 'scale':
        print('SCALE build: seven chords, 1 s each, then round again.')
        print('   f0 = 100 125 150 200 250 300 400 Hz')
        print('   -> chord roots at 200 250 300 400 500 600 800 Hz.')
        print('   If these seven steps are audible, the note engine works')
        print('   and only the piece and its register are wrong.')
    if mode == 'play' and leadin:
        print('lead-in: 3 s of a plain ramp at 200 Hz before the music —')
        print('         a clean falling sawtooth on a scope means the table')
        print('         reaches the converter.')
    if mode == 'hold' and pattern == 'suite':
        print('SUITE build: six tables, %.0f s each, f0 = %.2f Hz throughout,'
              % (3.0, hold_hz))
        print('   waveform %s, no melody. In this order:'
              % RAM_WAVEFORMS[waveform][1])
        for i, (n, _, why) in enumerate(SUITE, 1):
            import textwrap
            head = '   %d. %-7s ' % (i, n)
            print(textwrap.fill(why, 74, initial_indent=head,
                                subsequent_indent=' ' * len(head)))
    elif mode == 'hold' and pattern == 'both':
        print('HOLD build: alternates a ramp and the chord "%s" every 3 s'
              % chord_name)
        print('   waveform %s, f0 = %.2f Hz throughout, no melody.'
              % (RAM_WAVEFORMS[waveform][1], hold_hz))
        print('   On a scope: a clean sawtooth means the streaming works.')
    elif mode == 'hold':
        print('HOLD build: pattern "%s", waveform %s, one fixed frequency'
              % (pattern, RAM_WAVEFORMS[waveform][1]))
        print('   f0 = %.2f Hz, no melody and no cycling — whatever is on the'
              % hold_hz)
        print('   output is the table and nothing else.')
    elif mode == 'probe':
        print('PROBE build: no melody. Cycles the five RAM waveforms,')
        for w, hz in ORDER:
            b, name, idx, known = RAM_WAVEFORMS[w]
            print('   %-11s f0 = %5.0f Hz -> chord %.0f/%.0f/%.0f Hz, setup index %d%s'
                  % (name, hz, 2*hz, 3*hz, 4*hz, idx, '' if known else ' (guessed)'))
        print('   about 3 s each, then round again')
    elif waveform == 'none':
        print('waveform: left as the instrument had it — the chord is only')
        print('          audible if a RAM waveform happens to be selected')
    else:
        print('waveform set to %s (%s), one of the five that read the RAM'
              % (RAM_WAVEFORMS[waveform][1], RAM_WAVEFORMS[waveform][0]))

    # the same hook as mkdoom.py: the dead eighth entry of the self test
    selftest = [a2 for a2, (n, _, _) in tab.ROUTINES.items() if n == 'TAB_SELFTEST']
    if selftest:
        entry = selftest[0] + 7*3
        if rom[entry] != 0x02:
            raise SystemExit('the eighth table entry is not an LJMP')
        rom[entry+1] = (base >> 8) & 0xFF
        rom[entry+2] = base & 0xFF
        limit = bytes(rom).find(bytes([0xE5, 0x0B, 0xB4, 0x08]))
        if limit < 0:
            if bytes(rom).find(bytes([0xE5, 0x0B, 0xB4, 0x09])) >= 0:
                raise SystemExit('this image already carries the menu patch — '
                                 'build a fresh V2.0 with mkv20.py first')
            raise SystemExit('count limit of the menu not found')
        rom[limit+3] = 0x09
        print('self-test entry 8 -> %04Xh, count limit 08h -> 09h' % base)
        print('  ==> menu number 8 starts the polyphonic player')

    rom[end+1] = romfix.summe(bytes(rom), end)
    print('checksum over 0000h..%04Xh: %02Xh' % (end, rom[end+1]))
    open(target, 'wb').write(bytes(rom))
    print('written:', target)


if __name__ == '__main__':
    main(sys.argv)
