# CLAUDE.md — PM5139 Firmware Reverse Engineering

Working instructions for Claude Code in this project directory.

## Context

Reverse engineering the firmware of a Philips PM5139 function generator,
built around 1994. The processor is a PCB80C652 (8051 core with hardware
I²C) with an external 27512 EPROM. The goal is to understand the firmware
well enough to modify it and flash it back — eventually a
reimplementation.

Read `HANDOVER.md` first for the current state and `BACKLOG.md` for the
open questions. `PM5139_Hardware_Reference.md` is the main document with
35 sections; everything documented lives there.

## Language

**Everything written or documented in this project must be in English,
without exception.** This covers, but is not limited to:

- all Markdown documents (`PM5139_*.md`, `HANDOVER.md`, `BACKLOG.md`,
  this file)
- comments and docstrings in `.py` and `.js` files
- comments and headers in generated listings (`symbols.py` feeds these,
  so its texts are English too)
- commit messages, plot titles and axis labels, console output of the
  tools
- identifiers, file names, table headings

Reason: the repository is public
(`doctormord/Philips-PM-5139-5138A-5136-Firmware-Project`), so the work
should be readable for anyone working on these instruments.

The rule is about what gets written into the repository; the
conversation with the owner continues in German. The migration of the
originally German documents is complete — every file, identifier and
comment is English now.

Note on numbers and terminology: keep the `h` suffix for hexadecimal as
the service manual does (`3A9Ah`, not `0x3A9A`), and keep the German
signal names from the schematics verbatim where they are labels on the
hardware.

## Method

**Document, do not guess.** Every statement about the firmware needs
evidence: a place in the listing, a measurement in the emulator, or the
schematic. Two independent ones are better. If something is only
assumed, say so.

**The emulator is the measuring instrument.** `emu.py` (Python) and
`core.js` (JavaScript) execute the original code. To find a formula:
call the routine directly, vary the input values, check the output
against the assumption. That worked for frequency, amplitude, offset,
AM, FM, burst and symmetry, and it is the fastest route.

**The emulator counts instructions, not machine cycles.** `core.js`
increments `cycles` once per instruction (line 105). For orderings and
instruction counts that is equivalent, for **absolute timing it is
not** — there the MCS-51 data sheet applies (at 12 MHz one machine
cycle is 1 µs, `DJNZ` needs two). See section 35.

**Rule out your own mistakes first.** Three emulator bugs caused
seemingly inexplicable behaviour in this project: `ACALL` executed as
`AJMP`, a missing AC flag (binary instead of BCD arithmetic), and a
keyboard interrupt fired twice. When the firmware behaves nonsensically,
the emulator is the first suspect.

**Do not go in circles.** If three attempts at the same spot lead
nowhere, read the listing calmly instead of experimenting further. And
the other way round: when the listing does not help, measure.

## Tools

| File | Purpose |
|---|---|
| `mcs51.py` | MCS-51 disassembler, complete opcode table |
| `analyze2.py` | code flow analysis with jump tables |
| `seqdiff.py` | structural comparison of V1.3 against V1.5 |
| `emu.py` | 8051 interpreter |
| `system.py`, `system2.py` | peripherals: timers, interrupts, I²C, strobes |
| `keys.py` | keyboard and rotary knob input |
| `core.js` | the same core in JavaScript, ~8 million instructions/s |
| `bitmap.js` | check the display bitmap, singly and in pairs |
| `trace.js` | log the ROM addresses that were executed |
| `flags.js` | effect of the state bits on the C-bus telegrams |
| `cmd16.js` | strobes in the wake of a command |
| `iface.js` | emulate the interface card at I²C 5Eh |
| `romfix.py` | check and correct the checksum |
| `mkv20.py` | builds our own version V2.0 (de-noised arbitrary curve 3) |
| `asm51.py`, `mkdoom.py` | mini assembler and melody extension in the free ROM |
| `plot_waveforms.py`, `plot_v20.py`, `plot_arb.py` | plot the waveform tables, compare versions |
| `waveforms.py`, `mkarb.py` | generate own waveforms and write them into the ARB EEPROM |
| `lines.py` | read the wires off a schematic sheet (segments instead of eyeballing) |
| `arb.js` | arbitrary EEPROM: directory check 9615h against different images |
| `xrange.js` | which EEPROM address range the firmware reads |
| `limits.js` | measure the switch-over points of the parameter limits (table 12D2h) |
| `whoruns.js` | counts whether a routine runs at all in normal operation |
| `param.js` | parameter limits through the complete handler 0663h |
| `keycodes.js` | which key code triggers which handler of table 0301h |
| `decade.js` | decade limit per parameter through real key presses |
| `remote.js` | remote entry: INT0 and card response in the wait loop 1B2Eh |
| `display.js`, `digits.js`, `digits2.js` | read the display image from `frame`, measure the digit encoding |
| `readout.js` | decode the digit row of the display into plain text |
| `nvram.js`, `nv2.js`, `nv3.js` | NVRAM field layout by differential measurement |
| `build.py` | builds `PM5139_Simulator.html` from `shell.html` and `core.js` |
| `symbols.py` | symbol table: routines, RAM, bits, strobes |
| `annotate.py` | produces the annotated disassembly |
| `mapv15.py` | maps the symbol addresses onto V1.5 |

Node is available and is much faster than Python for measurement series.
A cold start takes about 9 million steps.

## Important addresses

```
V1.3, ROM occupies 0000h–AC70h, checksum at AC70h
Reset            3A9Ah        checksum routine   3AABh
Command table    7752h        message pointers   803Ch
Waveform tables  44A7h 46A9h 4AABh A047h A447h A847h
Display buffer   RAM 30h–43h  output             37DBh / 392Fh
Key decoder      0227h        key numbers        5AABh
Rotary knob      25C2h        acceleration       2622h / 260Eh
Frequency        50h–52h      computation        0A26h / 09E5h
Amplitude        56h/57h      computation        0B57h / 0AACh
Offset           58h/59h      computation        0A90h
Strobe output    0E54h ff.    status read        517Dh
```

The strobe number sits in the lower nibble of DPH: `MOV DPH,#8nh`
followed by `MOVX @DPTR,A` triggers STRn, 80h is the idle output.

## Conventions

- Numbers in the text with the `h` suffix, as in the service manual:
  `3A9Ah`, not `0x3A9A`.
- Differences between V1.3 and V1.5 belong in
  `PM5139_Changelog_V13_V15.md`.
- New findings belong in `PM5139_Hardware_Reference.md`, with a code
  excerpt and a measurement table.
- Strike finished backlog items, add new questions.
- Always carry emulator changes through both cores, Python and
  JavaScript, otherwise the results drift apart.
- After every change to `core.js`: `python3 build.py` and check the cold
  start — it has to run through without errors.

## Caution

Results from the middle phase of the project were partly produced with
the emulator bugs named above. All three affected places have since been
re-measured: section 15 was right, the strobe assignment in section 4
agrees with the service manual, and section 16 has been corrected —
STR5 was missing for every modulation and STR7 for the asymmetric
waveforms.

Second pitfall: **hand-set states**. Setting a RAM byte after the fact
easily produces a state the device itself never takes — that has led to
wrong conclusions twice already (rotary knob, device address) and once
to a crash into the command table. Where possible, establish the state
through keys and the rotary knob, then check that the firmware is still
running inside the code.

Third pitfall: synthetic test images. `PCF8570_image.bin` was wrong and
spoiled two findings, see section 26. So with inexplicable behaviour, do
not only suspect the emulator, but the images as well.

**Both images are real by now.** `PCF8570_image.bin` is the factory
state produced by the firmware itself, `D310_image.bin` the X28C64 as
read out — the firmware accepts its directory (section 32). The earlier
synthetic versions sit next to them as `*_synthetisch.bin` and only
serve as a counter-check; `mk_eeprom.py` has been writing there since.

Three sources sit in the folder: the **PM5139 user manual**
(`PM5139_User_Manual_FLUKE.pdf`, a pure scan without a text layer — the
English part has been OCRed as `PM5139_User_Manual_OCR_ENG.txt` and is
searchable), the **data sheet of all three models**
(`PM5136_PM5138A_PM5139_Specsheet.pdf`, real text) and the service
manual.

`pm5138A_service_manual.pdf` is the primary source for the hardware: 176
pages, OCR, running text readable with `pdftotext -layout`. Pages 4-3 to
4-28 are missing, but chapter 3 with the block diagram description is
complete. PM5136, PM5138A and PM5139 are internally almost identical.

**The schematics are worthless in OCR — but excellent as images:**
`pdftoppm -f N -l N -r 400 -png`, then cut into overlapping tiles and
look at them one at a time. Which page shows which schematic is listed
in section 30.
