# PM5139 — changing the firmware and flashing it back

The state of the reverse engineering, turned into a set of
instructions: what can already be changed with confidence today, how the
image is made runnable again, and what is still missing for a complete
reimplementation.

## 1 The checksum

At power-up the firmware sums all bytes from 0000h up to an end address
and compares the result with the byte immediately after it. If it does
not match, `Err 1` appears and the instrument stays in an endless loop
at 3B18h — no further operation.

| Version | Check routine | Range | Checksum byte | Target value |
|---|---|---|---|---|
| V1.3 | 3AABh | 0000h–AC6Fh | AC70h | F2h |
| V1.5 | 3B81h | 0000h–B3C9h | B3CAh | 99h |

The end address sits in the ROM itself, loaded with `MOV 10h,#hi` and
`MOV 11h,#lo`. `romfix.py` reads it from there, recomputes and sets the
check byte:

```
python3 romfix.py changed.bin            # check only
python3 romfix.py changed.bin fixed.bin  # check and correct
```

Demonstrated: an image with a changed device identification starts with
`Err 1` without the correction, and without errors after a run through
`romfix.py`.

## 2 Free space

| Version | occupied | free |
|---|---|---|
| V1.3 | 0000h–AC70h, 44 145 bytes | AC71h–FFFFh, **21 391 bytes** |
| V1.5 | 0000h–B3CAh, 46 027 bytes | B3CBh–FFFFh, **19 509 bytes** |

The free area lies **outside** the checked range. Our own code there
does not change the checksum; only the entry point, which sits inside
the checked range, does — and `romfix.py` catches that.

Procedure for an extension: replace an existing `LCALL` or `LJMP` with a
jump into the free area, put your own code there, call the original
routine at the end and jump back. Then correct the checksum.

## 3 What can already be changed safely today

These structures are completely decoded and can be touched without risk:

| What | Location in V1.3 | Format |
|---|---|---|
| device identification `*IDN?` | AC54h | length byte, then ASCII |
| message texts | pointers at 803Ch, 124 entries | length byte, then ASCII |
| command table | 7752h, 131 entries | 14 bytes of name + 2 bytes of token |
| self-test display texts | 5E11h, 24 × 5 characters | segment patterns |
| digit font | 5E91h, 16 entries | segment patterns |
| key numbers | 5AABh | index = key code |
| default values at reset | 3C2Eh | direct assignments |
| quarter sine | 44A7h | 256 × 16 bit |
| haversine | 46A9h | 512 × 12 bit |
| level series | 4AABh | 1024 × 8 bit |
| built-in arbitrary curves | A047h, A447h, A847h | 1024 × 8 bit each |

The segment encoding for your own texts: bit 0 = d, 1 = decimal point,
2 = c, 3 = b, 4 = g, 5 = a, 6 = e, 7 = f.

## 4 What is still missing for a reimplementation

**Completely understood and measured** are the processor, the memory
map, the strobe decoding, the C-bus, I²C with all its participants, the
port assignment, the keyboard encoding, the rotary knob, the display
buffer, the EEPROM and NVRAM structures, the error codes, the self-test
— and by now **all six analogue assemblies**:

| Assembly | Strobe | State |
|---|---|---|
| frequency, TWS | STR6, 4 bytes | formula computed, section 18 |
| amplitude | STR9, 1 byte | formula computed, sections 20 and 22 |
| DC offset | STR7, 2 bytes | `1Dh = 64h ± W`, section 22 |
| amplitude modulator, pulse generator | STR3 | symmetry computed, section 22 |
| burst logic | STR4 | cycle count computed, section 22 |
| modulation oscillator | STR5 | AM depth and FM deviation computed, section 22 |
| sweep output | STR8 | scaling computed, section 23 |

On top of that the arithmetic library (section 24), the packet format of
the interface (section 28) and 75 of the 128 state bits (section 27).

**What is still missing:**

| Gap | Why it matters |
|---|---|
| **Load routines of the waveforms** — 3DABh, 4003h, 3EFCh, 4425h, 9E37h | Without them no curve points reach the 12-bit waveform RAM. The path over STR2 is known, the transfer format is not computed. |
| **Bit meanings inside the telegrams** | The formulas say *which value* is sent, not what each bit does inside the assembly. For firmware of our own that is enough as long as the same values are produced — not for different functions. |
| **Command interpreter 71BFh**, 564 bytes | Needed as soon as the remote control is to be rebuilt. |
| **The rest of the code** | Since section 29 no contiguous code block is left without a name — but a name says what a block touches, not what it computes. Most routines have not been worked through line by line. |
| attenuator switching thresholds K401/K402 | when which relay switches. Settled since section 30: they are bits in the STR9 telegram. |
| 53 state bits, remote switching, NVRAM field layout | see BACKLOG.md |

## 5 A realistic assessment

**Changing and flashing back** has been tried out. Texts, tables,
default values and waveforms can be adapted, our own code fits into 21 KB
of free memory, and the checksum is a solved problem — `patch_ok.bin`
boots in the emulator identically to the original.

**Replacing individual routines** is possible as long as they hang on
one of the computed interfaces. Anyone wanting to rewrite the frequency
computation, the amplitude, the sweep or the display has all the
formulas and telegram formats together.

**Writing it completely from scratch** is not yet within reach, and the
reason is no longer the hardware but the scale: the hardware interface
is largely worked out, but most of the original code has only been
named, not computed. You would not have to rebuild everything — but you
would have to know what you leave out. The next worthwhile steps, in
this order:

1. Compute the **waveform load routines**. Without them there is no
   output signal; that is the hardest remaining dependency.
2. Work out **5243h**, one of the most central routines with eleven
   callers.
3. The **command interpreter 71BFh**, if remote control is wanted.
