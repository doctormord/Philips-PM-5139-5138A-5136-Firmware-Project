# BACKLOG

Open points, ordered by usefulness. Every entry names the concrete entry
point so that work can start without a run-up.

---

## ~~P1 — finish computing the sweep~~ — done

Computed and confirmed in the emulator, see section 23. Setup at 14B2h,
loop at 1932h. Step size = Δf · 2^(36 − 1Fh) / N, ramp step size =
FF000000h / N, N from 60h/61h. The arithmetic library fell out of this
along the way and is now section 24.

**What remained open from it:**

- ~~Exponential routine 2218h~~ — computed, see section 23. It
  interpolates linearly in the table at 2398h, 257 entries with
  `round((2^(i/256)−1)·65536)`, and delivers
  `X = W · 2^((13h+14h/256)/256) · 65536`. The same table serves at
  2323h, read backwards, as a logarithm.
- ~~Time constant 43h–45h~~ — settled, see section 23. It is not the
  step clock but the **retrace pause** after the end of the sweep
  (1A5Bh, 1A8Ah, 1AEDh, together with pen lift on P1.0):
  `(65536 − 44h:45h) + 43h·65536` ticks, i.e. 50·N µs, capped at a fixed
  500 ms from N = 10 000 on through 22h.4 and the constant at 1516h.
- ~~16-bit limit in 162Ch~~ — checked, see section 23. Not a bug in
  operation: the user interface produces mantissas of at most 3000, the
  limits are at 65 535 (sweep) and 32 767 (TWS telegram). It turned out
  along the way that the normal frequency path is limited too, and even
  more tightly — the earlier statement "not affected" was wrong. All
  that stays open is whether a remote command can bypass the range
  check; 29C9h does not correct a value set from outside.
- 1D62h writes F0h/F1h for STR1, the page select of the waveform RAM.
  Where the bits are taken from in 12h/13h is described, what the
  address means is not.

---

## ~~P2 — rotary knob, second direction~~ — done, was a misdiagnosis

Both directions work correctly and symmetrically, see section 19. The
direction sits in F0, set at 25CBh from the IDR level while ITG = 0. The
apparent jump to 20000 came from the non-normalised start value in the
NVRAM image, not from the direction of rotation.

**Done:** `PCF8570_image.bin` has been replaced, see section 26. The
firmware produces the factory state itself when presented with an
invalid NVRAM; exactly that state is now in the file. The old image sits
next to it as `PCF8570_image_old_synthetic.bin`. With that the rotary
knob works in both directions straight out of a cold start, without
having to set states by hand.

**Still open:**

- Limit table 2A81h has only been checked for the decades in use.
- The field layout inside a 25-byte NVRAM record and the rule behind the
  check mark are unknown.
- The chain detent count → 26ABh → 2724h has been measured but not
  computed step by step.

---

## ~~P3 — re-check the display bitmap~~ — done, the table was right

Repeated completely, in both cores with the same result: 31 flags act
immediately, 23 through a precondition, 74 not at all — exactly the
numbers from section 15. Every single assignment is confirmed, the
trigger row included. The emulator bugs had not falsified the bitmap.

Nine effects that were missing so far have been added to section 15,
among them 2Eh.4 → 35h.3 for `DIAL LOCKED`. The tool for that is
`bitmap.js`; it also does the pair search, for which `sweep3.py` in
Python was too slow.

**Open:** the 74 flags without effect are thereby confirmed as such —
they belong to P6.

---

## P4 — the 1 900 unclassified ROM bytes — largely settled

See section 25. The tool is `trace.js`, which drives the JS core through
a cold start, all 23 keys, both directions of rotation and the operating
modes, and marks every address that was executed.

**Result:**

- Exactly one area runs that `analyze2.py` does not know: 031Fh–0327h,
  the DIAL LOCK handler. It is the sixteenth entry of the jump table at
  0301h and sits there inline instead of as an `AJMP`.
- Of the 13 637 untraced bytes in the occupied ROM, 10 686 fall on five
  known table blocks, the rest on 118 small tables documented in the
  sections above.
- 9AFFh–9BB8h is real code — I²C traffic with address 5Ah, which occurs
  nowhere else. In **both** versions no jump points at it; in V1.5 the
  same code sits at B2F2h, likewise without a caller. Dead code,
  presumably for a device variant.

**What is still missing:** the trace reaches barely a quarter of the
statically known code. Sweep, modulation, self-test branches and the
interface are not in it. That is not enough for the statement "nothing
ever runs here" — but it is enough for "something unknown runs here",
and that produced exactly one hit.

**By the way:** `analyze2.py` should pick up the entry after the end of
a table when it looks like code — then the descent would find 031Fh by
itself.

---

## P5 — interface protocol — the fundamentals are there

See section 28. The tool is `iface.js`, which emulates a slave at I²C
address 5Eh and logs every transaction.

**Documented:**

- Chapter 4.12 of the service manual is present in the scan: its own
  interface processor, optically isolated I²C, INT on pin 3, RESET on
  pin 8, device address 20, RS-232 with 9600 8N1.
- I²C runs in software over P1.6 (SCL) and P1.7 (SDA), routines 5187h,
  5194h, 51A1h, 51C1h.
- Card detection through the ACK on the address, result in 25h.7.
- Initialisation measured: `E8 / EA / 80 00 / EA / E0 / C0 14 / E3`.
  The `C0 14` transfers device address 20 from RAM 68h — this agrees
  with the manual.
- Packet format: status byte with the length in bits 0…4, data block,
  then a rotating checksum `r = ror8(byte + r)`. Buffer RAM 80h–BFh,
  pointer 4Ch, counter 4Ah, status 4Bh.
- The trigger is P3.2 alias INT0, tested at 62DCh.
- Identification string `PHILIPS,PM5139,0,V1.3/0000` at AC55h, with a
  length byte 1Ah in front of it.

**The receive path is measured:** with 2Eh.3 and 26h.1 set, an injected
packet arrives completely, the payload lands at the address in 4Ch. That
confirms the checksum formula. A bug in the I²C model came to light in
the process — the address ACK when reading comes from the slave; the
correction deliberately applies only to 5Eh, because a general fix
shifted the NVRAM read.

**Remote operation is understood**, see section 28. Four links: device
address 31 (0EA5h) enables 25h.0; 29h.5 from `ORL 29h,#2Fh` (065Ah,
3B96h) kicks off 0EA1h; the card sends **E3h** for REMOTE and **E2h**
for LOCAL (6130h/6137h), which sets 26h.1; 666Ah, called from 1B37h,
then sets 2Eh.3. Measured: with address 31h and E3h, 26h.1 is set, with
E2h it is not, with address 20h nothing starts at all.

The address has to be set through the `ADDR` key. Setting 68h by hand
crashes the firmware into the command table — the same class of mistake
as with the NVRAM image.

**~~Open: 2Eh.3 stays clear.~~ Settled**, see section 28. The trigger is
**P3.2 alias INT0**, not ACC.0: in the wait loop 1B2Eh the code falls
through to 1B37h as soon as the card pulls INT0, calls 666Ah, and on the
answer **E3h** both 26h.1 **and 2Eh.3** are set (not on E2h). Measured
with `remote.js`.

Nothing happens out of the normal main loop — the state 1B0Ch (reached
from the sweep aftermath through 1A58h) is a precondition.

**The send direction is located**, see section 32: it lies in the block
8871h–9AFEh, which touches 4Ch (IFACE_POINTER) 39 times and 4Bh
(IFACE_STATUS) 34 times and sends through 5F2Eh. In front of it sit an
ASCII parser (6700h–6C00h) and the dispatcher 6A85h.

**The command groups are identified:** token 6xh = the arbitrary
waveform commands (ARB, ARBSELECT, ARBITEXECUTE, ARON, AROFF, CLARB,
BEGIN, COUNT, DATA, FILL) go to 8871h; token Cxh = the IEEE-488.2 common
commands (*CLS *ESE *ESR *OPC *RST *SRE *STB *TST *WAI) to 6B51h;
everything else to the same interpreter 71BFh that the keyboard uses.
That explains why the big block contains the EEPROM routines and touches
the interface buffers so often.

**By the way:** `PM5139_Bit_Crossreference.md` only counts individual
bit instructions and misses `ORL 29h,#imm`. That is why 29h.5 appears
there with zero setting places although it does get set. Keep that in
mind when evaluating the cross-reference.

**Carried over:** the slave at 5Eh and INT0 are now in the Python core
as well (`system2.py`, attributes `iface` and `iface_int`). Both cores
deliver the same result for the same packet.

---

## P6 — remaining state bits — from 54 to 75

See section 27. The decisive step was to stop watching only the display
and to watch the **telegrams on the C-bus** instead: `flags.js` records
what goes through SBUF to which strobe.

62 flags take effect across six operating-mode profiles; together with
those found statically, 75 of the 128 are documented. Of the remaining
53, 7 are classified as short-lived working flags and 8 as dead, 36 need
a stimulus outside the profiles.

Confirmed independently along the way: 20h.7 starts the sweep, 2Eh.4
blocks every adjustment as DIAL LOCK.

**How to continue:** the six profiles do not cover the self-test, error
cases and interface operation. The `PROFILE` table at the top of
`flags.js` is the place for more; a run over all 128 flags and six
profiles takes about ten minutes.

---

## P7 — annotated master disassembly — the tool is there

See section 29. `symbols.py` holds the symbol table, `annotate.py`
inserts it and produces `PM5139_V13_annotated.asm`.

State: 147 routines in the table, 145 with a header comment in V1.3 and
3 826 annotated lines. The listing itself stays unchanged, only
annotated on the right.

**This is how it grows:** new findings go into `symbols.py`, then
`python3 annotate.py 13`. Only take in what is documented, with the
section number as the source.

**V1.5 is connected:** `mapv15.py` maps the addresses — structural
comparison as in `seqdiff.py`, signature search as a fallback, two
addresses by hand. 130 of 147 symbols are mapped.
`python3 mapv15.py --write` produces `symbols_v15.py`, then
`python3 annotate.py 15` the listing with 128 routine headers.

**Open:** 17 routines that V1.5 changed heavily get no symbols — the
DIAL LOCK handler, both parameter loaders, the checksum routine, the
parameter limit check and several interface routines.

**Side finding, verified:** the device address in 68h is BCD in V1.3 and
binary in V1.5 — hence 31h against 1Fh. Not a bug, see section 28. Both
send `C0 14`; V1.5 brings a migration for old NVRAM contents at 3C1Fh.

---

## Section 16 — re-measured and corrected

`cmd16.js` drives every command token through 71BFh and the reload cycle
090Ch and records the strobes. Two gaps of the first version are closed:
**STR5** was missing for every change of modulation and sweep, **STR7**
for the asymmetric waveforms. The measurement is stable over step
budgets from 50 000 to 2 000 000.

**Open:** the command group 30h–39h (29h = 04h, OUTPUT, AC/DC, LOIMP)
triggers no strobe output through 090Ch. The path presumably runs
through 29h.4 at 0931h.

---

## Bit assignment of the telegrams from the schematics

See section 30. The schematics are unusable in the OCR text but very
good as images: `pdftoppm -r 400 -png`, then cut into overlapping tiles
and look at them one at a time.

**Already read off:** all strobe receivers are 74HCT4094; the DC
generator is STR7 -> 4094 -> DAC-08 with relay K301 over the line S1;
STR9 goes to D102 in the amplitude controller and supplies the lines S1
to S5, which switch K301 and the attenuator relays K401 to K404. That
makes the attenuator thresholds not a computation but bits in the STR9
telegram.

**The amplitude controller has been read off:** STR9/SC/SD come in over
X801; D101 Q1..Q8 feed the upper eight bits of the 12-bit DAC N101
(AM6012F), D102 Q1..Q3 the lower ones, and D102 Q4..Q8 (pins 7, 14, 13,
12, 11) are **S1..S5**. S1 switches K301 in the DC generator, S2..S5 the
attenuator relays K401..K404. So the attenuator thresholds are not a
computation but bits in the telegram.

**Resolved:** D101 and D102 are cascaded over **QS' (pin 10 -> pin 2)**,
only QS (pin 9) is unused; they share clock and strobe. The firmware
sends a 16-bit word as **two consecutive one-byte telegrams** — measured
as pairs about 42 000 resp. 47 000 cycles apart with millions of cycles
of silence in between. The byte sent first ends up in D102 (S1..S5 and
the lower DAC bits), the second in D101 (upper eight DAC bits). Check
the same pattern on the other assemblies with more than one shift
register.

**The attenuator has been read off** (fig. 111, page 133): S2 -> V401 ->
K401 `20 dB (for 40dB)`, S3 -> V402 -> K402 `20 dB`, S4 -> V403 -> K403
`50/600 ohms`, S5 -> V404 -> K404 (output matching, R438/C404 marked
*not mounted* in a footnote). S5 additionally drives an LED through V405
for the indication on U5. All relays TQ2 5V, drivers BC547B, series
resistor 4k64.

**The amplitude modulator has been read off** (fig. 117, page 151):
STR3 -> D144-A (HCT4094); on unit 4 the clock is called **SC1** and the
data line **E**. Q1..Q4 control internal functions, among them the
analogue multiplexer D143-A (HCT4052, ±4.9 V); Q5..Q8 are **U11, U10,
U9, U12** — the order is not ascending. Signal inputs B1 from the burst
logic and M1 from the modulation oscillator, amplifiers N145 (LF356N)
and N147 (TL072).

**The pulse generator has been read off** (fig. 118, page 154): D126-A
(HCT4094) on STR3/SC1/**SD1**, eight outputs to N127 (DAC-08EN),
labelled `Duty Cycle for fc > 20 kHz` and `Asymmetry` — that is the
symmetry quantity from section 22.

**The STR3 cascade is resolved:** the line **E** runs from the pulse
generator to the amplitude modulator and is the data input of D144
there. So the registers are in series after all, only across the
assembly boundary: `SD1 -> D126 -> E -> D144`. The byte sent first lands
in D144, the second in D126. The earlier conclusion "no uniform cascade
pattern" was wrong.

Further inputs of the pulse generator: **B4** = TWS MSB (agrees with
chapter 3), A2 from the frequency multiplier, PGS from the CPU, B5 from
the burst logic; **U9** switches relay K810 through V172. Output B3
`fc > 20 kHz` to the burst logic.

**The signal path is settled** (fig. 115, page 145): the TWS supplies 10
bits of **address** for 1024 sample points; at each of them sits a
**12-bit word** from two devices (D107 HM6716 upper 8 bits, D108 HM6268
lower 4). The twelve lines S1..S12 go in parallel into **N110 = TDC1012**,
a 12-bit DAC with a differential output; the transfer clock is **C/n**
on pin 16 (CONV). The DAC08 types sit only in the side paths (DC
generator, asymmetry, sweep output), not in the signal path.

**The burst logic has been read off** (fig. 120, page 160): STR4 ->
D121-A and D122-A (both HCT4094) load an **11-bit down counter** made of
cascaded HCT191 (D117, D118, ...). Eleven bits hold 2048 values — that
confirms the limit N = 2000 from section 22 and chapter 3 **in
hardware**, and the two bytes measured per STR4 telegram match the two
registers. Inputs B3 (`fc > 20 kHz` from the pulse generator) and B4
(RAM MSB).

**The modulation oscillator has been read** (fig. 119, page 157). Three
serial receivers, and according to the assembly strip that is all of
them: TWS D130-A (LIC016A = PCF1842P) with its own inputs SCI/SDI/STRI
plus the HCT4094s D138-A and D139-A. The chain runs over QS' (pin 10),
pin 9 stays free:

```
SD1 --> D139 --> D138 --> D130 (SDI);  SC1 and STR5 go to all three
```

According to the listing (`L0E69`, two send operations under one strobe)
the six bytes go out in the order **14h, 13h, 12h, 11h, 19h, 18h**. The
byte sent first travels furthest:

| Byte | Destination | Meaning |
|---|---|---|
| 14h…11h | D130, TWS | 32-bit frequency word, LSB first |
| 19h | D138 | eight bits to the DAC N135 (AD7523JN) |
| 18h | D139 | eight control bits to the multiplexers D140/D141 |

Documented through three independent points: the TWS on STR6 likewise
gets exactly four bytes (`L0E54`); 19h is loaded as a number, 18h bit by
bit (`ORL 18h,#08h`, `ANL 18h,#0F7h`); 18h comes from the operating-mode
table at 0F83h through `X0F69h`. See section 30.

The **entry table 0E54h–0E84h** falls out along the way; it documents the
byte count of each strobe from the listing (STR6 4, STR7 2, STR9 1, STR5
4+2, STR3 2, STR4 2) — congruent with the measurements.

Also on that sheet: the second sine chain **TWS D130 → SinePROM D131-A
(27C64) → latch D132-A (HCT574) → DAC N133 (DAC-08EN) → low-pass**. This
is where the "SINUS 1.1" that was read out sits — **confirmed**, removed
as the SinePROM from unit 4 (page 158). The widths fit: 10 bits of
address from the TWS = 1024 entries, 8 bits of value for the DAC-08,
exactly the dump. It is the only 27C64 in the schematics.

**Measured telegram lengths** (cold start and four keys): STR1 2, STR2
2, STR3 2, STR4 2, STR5 6, STR6 4, STR7 2, STR8 1, STR9 1.

**On the X24C16 (D312):** it is *not* the device at 5Ah — its slave
address is fixed 1010 plus three bank bits, it occupies A0h..AEh and
thereby rules out the PCF8570. The "OPTIONAL" in the schematic is an
alternative fit, EEPROM instead of buffered RAM.

**On 5Ah:** it lies in the same device type block 0101 as the interface
card at 5Eh, only with different bank bits. The dead code sends ten
bytes twice (receive buffer from 80h, arithmetic registers from 15h) —
this looks like a factory diagnostic. See section 30.

---

## The two devices that were read out

See sections 31 and 32. `D27C64-2_PM5139_SINUS11_V15.HEX` and
`X28C64_PM5139_V15.HEX`, both placed next to them as .bin. Since the
switch-over the X28C64 is at the same time `D310_image.bin`, that is,
the image the emulator works with.

**Settled:** the D27C64 is a plain 8-bit sine, 1024 points, one full
period from the zero crossing; block marks 55h at 400h and 00h at 800h.
The X28C64 holds **10-bit values, four packed into five bytes** (four
bytes of upper eight bits, the fifth holding the four pairs of lower
bits). The block from 1500h is a half sine arc, `1023*sin(pi*i/512)`,
deviation 0.21 %.

**Open:**

- ~~Delimit the remaining blocks of the X28C64.~~ **Settled**, see
  section 32. Curve k lies at `0100h + (k-1)*1280`, six of them up to
  1EFFh — exactly the measured read range. The directory names the
  minimum and maximum of each curve as a 10-bit value left-aligned by
  six bits; all six checked against the unpacked data. 512 is the zero
  point (manual: value range −511..+511 = 20 Vpp). Curve 5 from 1500h
  is a full-wave rectified sine, curves 2 and 6 are erased with
  `FILL 0`.
- ~~Which device in the instrument is the X28C64?~~ **Settled:** it is
  the arbitrary EEPROM **D310**. The firmware checks the directory at
  9615h, and the dump passes the check; a single flipped bit makes it
  fail. The 8 KB variant was fitted instead of the X28C256 named in the
  schematic. See section 32.
- Where does the firmware use 10-bit curves? According to section 9 the
  waveform RAM is twelve bits wide. The TWS supplies *addresses* with 10
  bits (that explains the 1024 points in the 27C64), but in the X28C64
  the *values* are 10 bits wide — a different path. Candidate: the value
  is stretched to twelve bits, or only the upper eight go to a DAC-08.

---

## Upper frequency limit and model differences — settled

See section 33. The limit sits as a **ROM table at 12D2h** (V1.5: 134Fh,
byte-identical), 13 entries of 16 bits, indexed by parameter, checked at
11CCh. Patchable with `romfix.py`.

**Above 20 MHz nothing works anyway:** the clock is fixed at
10 × 2^21 Hz = 20.97152 MHz (PLL on crystal G800), so at 20 MHz the
instrument runs with about two sample points per period, practically at
Nyquist. A patch would only make the display count higher, the output
would be aliasing. 40 MHz would only be possible with a second analogue
squaring stage.

**No model byte:** `5136` and `5138` occur zero times in both ROMs,
`PM5139` exactly once (identification string AC55h). The firmware is
burnt per model. The models also differ demonstrably in the power supply
(TAB. 1: PM5136 ±16.5 V, PM5138A ±26 V).

**Open:**

- ~~The scaling in Hz.~~ **Settled**, see section 33. Table 12D2h is
  indexed by **parameter**, not by waveform — that was a mistake in the
  first version. The index is `24h & 0Fh`, the same number as in the
  lower nibble of the 8xh tokens. The values are BCD and name the
  smallest impermissible digit sequence: amplitude 21 (20 Vpp), offset
  11 (10 V), FM deviation 21 (2 %), phase 19 (180 degrees), burst 201
  (2000), frequency 2001 (20 MHz) — five of them agree directly with the
  data sheet.

  Counter-check made through the full handler 0663h (`param.js`):
  Z0..Z2 are zero, only Z3/Z4 come from the table, carry = 1 means
  "rejected", and an error is **not** reported in the process. The
  parameter addresses sit in table 08F2h.
  **The real operating path is established:** key **0Bh** raises the
  decade and triggers the check in doing so, 0Ah lowers it. That makes
  the measurement work without touching RAM (`keycodes.js`, `decade.js`).
  For FREQUENCY the decade ends at **9**.

  **Confirmed on the instrument:** 10 kHz -> 10 MHz, 20 kHz -> 20 MHz,
  25 kHz -> only 2.5 MHz. The third case documents the table value 2001
  as the smallest impermissible mantissa and the upper limit **20 MHz**.
  ~~Open: the encoding of decade and mantissa above decade 5.~~
  **Settled**, see section 15: the digit row lies in 3Eh–43h of the image
  that is sent (`c.frame`), all positions share one segment encoding, and
  43h switches from kHz to MHz at decade 7->8. From that
  **f = M * 10^(D-8) kHz**; all three cases read off the instrument are
  reproduced exactly (`readout.js`).

  Side finding: **11CCh never runs in keyboard and rotary knob
  operation** (measured, `whoruns.js`); it is reached through handler 0663h,
  the ninth entry of jump table 0301h, and only for parameters carrying
  bit 7 or 6 in the flag table 069Dh.
- Whether a remote command bypasses the check at 11CCh. Since section 32
  it is known where the remote control part sits.
- How the PM5139 makes 20 MHz out of the same clock — its low-pass has
  to sit at 10 MHz instead of 5 MHz, which can only be documented with a
  PM5139 manual.

---

## Our own version V2.0

Built with `mkv20.py` from V1.5, see section 34. It contains exactly one
change of substance: the built-in arbitrary curve 3 was a noisy sampling
of the same waveform that already sits in the ROM as a computed table
(563 direction changes against 13, sigma 4 LSB). On top of that the
version identification in the display and in `*IDN?`, and the checksum
carried over.

In addition, arbitrary curve 2 in the ROM now carries a logarithmic
chirp (it was identical to curve 1 except for two bytes), and
`D310_image_V20.bin` fills all six arbitrary slots with curves of our
own: sinc, ringing, ECG, staircase, rectified sine, multi-tone.

The melody hangs on **menu number 8** of the diagnostic program (LOCAL
while switching on). Two bytes are changed for it: the eighth table
entry at 5B94h, which was unreachable and redundant in the original, and
the count limit at 5B62h. **To check on the instrument:** whether the
menu really counts up to 8 and the display is right — in the emulator
the menu key press cannot be triggered because ACC.0 of the status
register is always set there.

**Not yet tried on the instrument.** In the emulator the cold start runs
without errors and produces the same state as V1.5; the EEPROM image
passes the directory check, a flipped bit does not.

**Open:** whether the noisy curve was intentional. Against that speaks
the fact that the basic shape matches the computed table exactly and the
mean of the deviation is zero.

---

## Odds and ends

- Simulator: the display fields for AC/DC and the lower number field are
  only partly rendered; the unit indication (MHz/kHz/V/ms) is missing.
- Simulator: LOCAL, ADDR and RESET are missing as keys (they do not run
  through the encoder, so they need their own lines in the model).
- `analyze2.py`: jump tables are recognised heuristically. For other
  ROMs a data flow analysis would be more robust.
- V1.5 has barely run in the emulator so far; all measurements come from
  V1.3.

## Sound: what is left besides MIDI

Reassessed after the polyphonic player ran on the instrument. The numbers
below are measured, not estimated (sections 36.8 and 36.9).

**1. Chord wavetables through the ARB EEPROM — buildable now, no EPROM.**
The owner confirmed the arbitrary function works on this instrument: six
curves out of the fitted X28C64, selectable from the front panel. So this
is polyphony **without touching the firmware at all** — write the EEPROM,
pick a slot, set the frequency by hand, and the instrument sounds h · f
for every harmonic number h in the table.

`python3 mkarb.py --chords` builds it. Six slots, six chords, chosen to
be usable together:

| Slot | Chord | Harmonics | at f = 100 Hz |
|---|---|---|---|
| 1 | fifth | 2:3 | 200, 300 |
| 2 | power | 2:3:4 | 200, 300, 400 |
| 3 | major | 4:5:6 | 400, 500, 600 |
| 4 | minor | 10:12:15 | 1000, 1200, 1500 |
| 5 | dom7 | 4:5:6:7 | 400, 500, 600, 700 |
| 6 | min7 | 10:12:15:18 | 1000, 1200, 1500, 1800 |

The identity byte per curve is computed, and `arb.js` now checks our own
images against the firmware's own directory routine at 9615h — both
`D310_image_V20.bin` and `D310_image_chords.bin` come back **rejected: 0x**,
so no Err 8.

What is left is to burn it and listen, which is the one thing that cannot
be done here: whether a just-intonation triad through the analogue chain
sounds the way the arithmetic says. Note the intervals are **just, not
equal-tempered** — the major third is 386 cents against 400, which is
audibly different and, for a sustained chord, better.

**2. Sample playback — through STR9, not the DC generator.**
The earlier plan was to write the DC generator (STR7 -> D301 -> N302
DAC-08). That is the worse of the two paths now that both are measured:

| | STR7, DC generator | **STR9, amplitude** |
|---|---|---|
| Telegram | 2 bytes | **1 byte** |
| Firmware routine | 79 us | **49 us** |
| Hand-written loop | ~30 us | **~22 us -> 45 kSa/s** |
| Side effects | first byte carries the attenuator relays | none |
| Resolution | 8 bit | 7 bit (it wraps at 80h) |

STR9 feeds the AM6012, which multiplies the waveform coming out of the
RAM. Load the wavetable with a constant and the output becomes the DAC
value alone — a plain PCM converter on the main output, at up to 11.6 Vpp.
This is not speculation: the amplitude matrix of section 36.8 scaled a
triangle smoothly with that byte, which is multiplying behaviour.

**The ceiling is ROM, not speed.** One byte per sample:

| Rate | With the poly player in ROM (13 492 bytes) | Whole free area (19 509) |
|---|---|---|
| 8 kSa/s | 1.7 s | 2.4 s |
| 16 kSa/s | 0.84 s | 1.2 s |
| 44.1 kSa/s | 0.31 s | 0.44 s |

So this is a **sound effect, not a music route** — one drum hit, one
sampled shout, a second at most. The arbitrary EEPROM adds 8 KB over
MOVX, which buys another second at 8 kSa/s and costs a second read per
sample. Worth doing for what it is; not worth doing expecting a song.
Note this is the "class-D" idea without the PWM: the resolution is
already in the converter, so modulating a pulse width would only throw it
away.

**3. A second, independent channel on the pen lift line.**
P1.0 drives V356 (BC337-25) to a 0/+5 V BNC on the rear panel. It is the
only genuinely CPU-wiggled single bit that leaves the instrument, and
`SETB P1.0` / `CLR P1.0` is one machine cycle each.

As a way of making the main output louder this is pointless now — STR9
gives seven real bits. What makes it interesting is that it is a
**separate output**. The wavetable chord on the front BNC needs no CPU
time at all once the table is loaded; the TWS reads it out by itself and
the CPU only sets the frequency, a few hundred microseconds per note. So
the CPU is idle almost all the time, and that idle time could drive a
one-bit stream on the rear connector. Chord and melody in front,
percussion behind, from one 8051 and no added hardware. Nobody has tried
it.

Rough budget, from the measured figures: a bit period of two machine
cycles is 2 µs, so 500 kbit/s. Noise-shaped, that is a comfortable
several hundred kHz of oversampling for a few kHz of audio bandwidth —
easily enough for drums. An RC into a small speaker is the whole
reconstruction filter. What has to be worked out is the interleaving: the
melody loop has to keep the bit stream fed while it waits out a note, so
the note timing would move from a `DJNZ` delay into the sample counter.
That is a rewrite of the player loop, not a new discovery.

Two things to check before believing any of it: whether P1.0 is free
while the diagnostic menu entry runs (the firmware toggles it with
timer 1 during sweeps, at 1911h and 1A3Fh — section 12), and how much
drive the open-collector stage really has into a speaker load.

**Still open from section 36.**

* The STR1 control word is understood as far as `RAM_PAGE` at 1D62h
  builds it (frequency-derived, plus bit 6 from 2Bh.4 and bit 0 from
  22h.4), but the values 2Eh and 20h seen during a cold start come from
  the continuation of the finish routine at 4360h and were not traced.
* There is no second RAM buffer, so a chord change costs a full 32–40 ms
  reload with the output silent. The player avoids it by keeping the
  harmony in the table and moving only the frequency. If a piece needs
  changing chords, put the reload on a rest.
* Section 12 says PGS is active for exactly the five waveforms that come
  out of the waveform RAM, and section 36.5 built on that. The instrument
  then showed a SINE command loading a 2050-byte table as well, with the
  same STR3 word as HAV. **What PGS actually distinguishes is open
  again.**
* Bit 5 of the STR7 relay byte clicks but costs no level. Most likely
  K403, the 50/600 Ω relay, which a high-impedance probe cannot see —
  unverified.
* The waveform-dependent setup index (table at 4335h, values
  `1E 24 24 25 2C 34 13 1A`) is mapped for SINE, TRNGL/TRNGLPULSE, HAV
  and the ROM ARB curves. Indices 4, 5, 6 and 7 belong to call sites that
  were not identified.

## The holy grail — the instrument as a synthesizer

Not a DX7. The comparison that holds is a **PPG Wave or a Prophet VS**:
a monophonic wavetable synth with two-operator FM. Every building block
is already in the instrument and already documented.

| Function | What provides it | Evidence |
|---|---|---|
| Oscillator | TWS + the 1024-point wavetable, 10 bit, any single-cycle waveform | section 36 |
| Second operator | modulation oscillator (TWS D130 + SinePROM D131 + DAC-08 N133) onto the VCO over M1, 10 Hz…100 kHz, deviation over the AD7523 | section 30, fig. 119 |
| Envelope | AM6012, 12-bit multiplying DAC, two STR9 telegrams | section 30, fig. 109 |
| Note change | a precomputed 4-byte TWS word on STR6 | section 18 |

Two operators with an **arbitrary carrier waveform** is something the DX7
precisely cannot do — its operators are sines.

**Measured cost** (machine cycles, section 36.5, on V2.0 after a cold
start; call the routine, count to the RET):

| Routine | Instructions | Machine cycles | Real time |
|---|---|---|---|
| `OUT_FREQ` 0A28h, a whole note change | 385 | 588 | **0.588 ms** |
| of which `FREQ_BCD2BIN` 0A8Fh | 228 | 324 | 0.324 ms |
| `SEND_STR6` 0EDBh, the 4-byte TWS word | 79 | 139 | **0.139 ms** |
| `SEND_STR7` 0EE2h, 2 bytes | 45 | 79 | 0.079 ms |
| `SEND_STR9` 0EE9h, 1 byte | 28 | 49 | **0.049 ms** |

So a note change that skips the BCD conversion — 128 ready-made TWS words
in a 512-byte ROM table, indexed by MIDI note number — costs **139 µs**,
not the 100 µs first estimated, and going through `OUT_FREQ` costs 588 µs
because more than half of it is BCD arithmetic. An envelope step is two
STR9 telegrams, **98 µs**, so a 1 kHz envelope rate is about **10 % of the
CPU** (the first estimate of 66 µs and 7 % was too optimistic). The CPU is
not the bottleneck either way.

### The two walls

**There is exactly one main TWS.** One oscillator, one wavetable. No
firmware can duplicate a phase accumulator, so there is no real polyphony
with independent pitches and independent envelopes. That is a hardware
fact, not a budget problem.

**The chord trick does not scale to arbitrary music.** Every partial has
to be an integer multiple of f0, and a partial needs roughly eight points
per period, so h ≤ 128. The pitch grid is therefore f0 and the highest
available note is 128·f0. To tune to ±5 cents at 82 Hz you need
f0 ≲ 0.5 Hz — which puts the highest note at 64 Hz, below the note you
were tuning. The two requirements contradict each other. For **parallel
harmony at fixed intervals** it works beautifully (that is what `mkpoly.py`
does), for arbitrary chords in equal temperament it cannot.

The route to arbitrary chords is therefore not the table but the
**arpeggio**: retuning costs 139 µs against 32–40 ms for a reload, so
switching between three notes at 1 kHz costs about 14 % of the CPU and
fuses into a chord — the classic SID trick, and here with no constraint
on tuning at all.

### The lucky accident, and the catch

**12 MHz gives exactly the MIDI baud rate.** 12 000 000 / 384 = 31 250,
exactly, with timer 1 in mode 2, `TH1 = FFh` and `SMOD = 0`. Crystal G816
could not be better chosen for MIDI.

The catch: the UART sits in **mode 0** and drives the C-bus with it
(section 8). One UART, two jobs, and not at the same time. So MIDI in has
to arrive either through the interface card on I²C 5Eh (section 28) or be
bit-banged on an interrupt pin — 32 µs per bit is 32 machine cycles,
doable but it eats the timing everywhere else. **That is the open
question, not the synthesis.**

A second output channel is available for free: the **MOD output** on the
back carries the modulation oscillator's signal outside. Two BNCs, mixed
externally. And since the SinePROM D131 is a socketed 27C64 that we have
read out (section 31), its waveform can be replaced too.

**The table is the patch, not the note** (section 36.3, measured). A
wavetable reload is 16.4 ms at the absolute floor — 2048 bytes at the
C-bus rate of f_osc/12 — 32 ms with the firmware's own fastest loop,
39.5 ms from a ready-made ROM table, and 55.7 ms for an ARB slot out of
the EEPROM, where the unpacking costs the difference. There is no second
RAM page to swap. So no amount of firmware work changes the waveform at
note rate, and the design has to put the table on the program-change
level, exactly as a PPG Wave does. Note on is a retune (139 µs), velocity
and envelope are one STR9 byte (49 µs).

### Groundwork before anyone starts

* a table of 128 ready-made TWS frequency words, one per MIDI note
  (512 bytes) — derivable from the formula in section 18 and checkable
  against `notefreq.js`;
* measure the achievable envelope rate against `mcyc` rather than
  estimating it;
* check on the real instrument at what rate an arpeggio actually fuses
  into a chord — that is an ear question, not an arithmetic one;
* decide the MIDI input path before anything else is built.

**Amplitude control is solved** (section 36.9): the second byte of the
STR9 telegram pair is a monotonic amplitude DAC — one pair, no relays, no
range switching, which is exactly what an envelope needs. The first STR9
byte has no level effect, and the attenuator relays are bits 3, 4 and 5
of the first STR7 byte, so STR7 is best left alone. A single STR9
telegram is enough — measured at 49 us, so a 1 kHz envelope costs about
5 % of the CPU. What is still open is which of the eight relay
combinations is the 0 dB setting; `mkpoly.py --relays` builds an image
that walks all eight.

The paragraph below is the state before that measurement, kept because it
records how the wrong reading came about:

**(superseded) Amplitude control is NOT solved** (section 36.9) and it blocks the
envelope. The routine at 0B15h can be made to emit — write 56h/57h, poison
10h to defeat the "nothing changed" gate, call it — but on the instrument
every path that writes STR7 collapses the output, from 8.3 Vpp down to
100 mV or less, including the `04h` the table gives for the 20 V range.
The byte is masked with 27h at 0B01h before sending, and 04h/14h/1Ch all
mask to the same value, so that telegram cannot be the attenuator. Find
where the attenuator actually is before building an envelope on it. Fig.
109 (amplitude controller) and fig. 111 were read for section 30; the
amplifier sheet, fig. 110, never was, and the summing node for the DC
path is unknown — that is where to look.

Realistically not a weekend. But there is nothing unknown left in it —
display, keyboard, C-bus, TWS word and the envelope path are all
documented. The jump is diligence, not research.
