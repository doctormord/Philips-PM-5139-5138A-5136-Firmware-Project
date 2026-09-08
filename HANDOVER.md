# HANDOVER — reverse engineering the Philips PM5139

State at the end of the analysis session. This document says what exists,
what it is worth, and where to continue.

## What this is about

Two EPROM dumps (M27512, 64 KiB) of a Philips PM5139 function generator,
firmware V1.3 and V1.5. Goal: understand it, change it, flash it back —
eventually a firmware of our own.

## The instrument

- **CPU:** PCB80C652, 8051 core with hardware I²C, 12 MHz
- **Program:** external EPROM 27512, V1.3 occupies 0000h–AC70h
- **EEPROM D310:** on the MOVX bus 0000h–7FFFh, arbitrary curves. The
  schematic names an X28C256 (32K), the socket held an **X28C64 (8K)**;
  the firmware only reads 0000h–1EFFh anyway
- **NVRAM D305:** PCF8570, 256 bytes on I²C (A0h), battery backed,
  current setting and nine memory registers
- **Display:** PCF8576 on I²C (70h), 20-byte buffer
- **Keyboard:** SAA3007 encoder, pulse-width coded on P3.3
- **Analogue section:** six assemblies on a serial C-bus with a strobe
  decoder (74HCT4514), strobe number = A8…A11

## What is finished

| Area | State |
|---|---|
| Disassembly V1.3 and V1.5 | complete, with XREFs, ~23 000 lines |
| Version comparison | 91.4 % structurally identical, every change named |
| Hardware abstraction | strobes, ports, buses, memory — complete |
| Command table, messages | decoded, both versions |
| Display | buffer, segment encoding, annunciator bits |
| Keyboard | encoding, matrix, all 23 keys named |
| Rotary knob | quadrature, acceleration, editing mechanics |
| Frequency path | fully computed and verified |
| Amplitude, offset, AM, FM, burst, symmetry | fully computed and verified |
| Sweep, linear and logarithmic | fully computed and verified |
| Arithmetic library | multiplication, division, normalisation verified |
| Self-test, error codes | all seven programs, all Err codes |
| Checksum | tool available, flashing back tried out |
| Emulator, Python and JavaScript | boots without errors, keyboard, knob, display |
| Browser simulator | a single HTML file, no dependencies |

## What is not finished

- **Interface:** fundamentals and packet format are documented (section
  28); the receive path still needs remote operation
- **36 of 128 state bits** still need a suitable stimulus; 75 are
  documented, 7 classified as short-lived working flags and 8 as dead
- **NVRAM field layout**: the leading fields and the check mark are
  settled (section 26); the fields from offset 0Dh on are open
- **Remote operation:** settled — INT0 in the wait loop 1B2Eh, card
  answer E3h sets 2Eh.3 (section 28)

## Added in this session

| Area | Result |
|---|---|
| Sweep, complete | scaling, step sizes, sweep time, both characteristics computed and confirmed over full runs — section 23 |
| Arithmetic library | four 5-byte registers, multiplication, division, normalisation — section 24 |
| Rotary knob | both directions work; the earlier finding was a misdiagnosis of the start value — section 19 |
| Display bitmap | fully re-checked, the table was right, nine effects added — section 15 |
| Code coverage | dynamic trace, one overlooked handler found, dead block documented — section 25 |
| NVRAM | the image was synthetic and falsified two findings; had the firmware produce the factory state — section 26 |
| State bits | from 54 to 75 documented flags via the C-bus telegrams — section 27 |
| Interface | I²C 5Eh, card detection, initialisation measured, packet format documented — section 28 |
| Annotated listing | symbol table and tool, 147 routines named — section 29 |
| Section 16 | re-measured and corrected: STR5 and STR7 were missing |
| Exponential routine | 2218h computed: table interpolation over 2398h — section 23 |
| Time constant 43h–45h | retrace pause after the sweep, 50·N µs, capped — section 23 |
| 16-bit limits | unreachable in operation; 0A26h is limited as well — section 23 |
| Python core | interface slave carried over, both cores deliver the same |
| V1.5 symbols | 130 of 147 mapped, annotated V1.5 listing — section 29 |
| Device address | 68h is BCD in V1.3 and binary in V1.5; not a bug — section 28 |
| Schematics | six sheets read, the cascade pattern over QS' confirmed everywhere — section 30 |
| STR5 broken down | chain D139→D138→D130, bytes 14h…11h TWS, 19h DAC, 18h multiplexer — section 30 |
| Byte count per strobe | documented from the entry table 0E54h–0E84h, not only measured — section 30 |
| SINUS 1.1 EPROM | is the SinePROM D131-A in unit 4, between the TWS and the latch — section 30/31 |
| Remote control part | ASCII parser, dispatcher 6A85h, the 4749-byte block structured — section 32 |
| X28C64 | is the arbitrary EEPROM D310; directory and checksum documented — section 32 |
| D310 image | switched to the real dump; cold start and telegrams unchanged — section 32 |
| Parameter limits | table 12D2h indexed per **parameter** (not per waveform), BCD, measured — section 33 |
| Command groups | 6xh = arbitrary commands, Cxh = IEEE-488.2 common commands — section 32 |
| Remote entry | INT0 in the wait loop 1B2Eh, answer E3h sets 2Eh.3 — section 28 |
| Parameter order | confirmed through the error numbers of the PM5136 manual: no. = index + 106 — section 33 |
| Learn query *LRN? | table 6CECh: command tokens per operating mode, eight groups — section 32 |
| Code coverage | **no unnamed code block left**, including the 13 parts of 8871h; 145 routine headers — section 29/32 |
| Display digit row | segment encoding of every position, unit in 43h — section 15 |
| Frequency encoding | f = M * 10^(D-8) kHz; the three measurements on the device reproduced exactly — section 15 |
| NVRAM field layout | offset + 4Bh = RAM address; frequency, stop frequency, amplitude, offset documented — section 26 |
| NVRAM check mark | byte sum with start value AAh over 25 bytes (2EA1h), record length 26 — section 26 |
| Changelog V1.3/V1.5 | IMP 50/600 display, eight command short forms, address BCD -> binary — its own document |
| Version V2.0 | curve 3 de-noised, curve 2 = chirp, display and *IDN? show 2.0; plus six arbitrary curves of our own — section 34 |
| Arbitrary format | 1024 points of 10 bit, 1280 bytes per curve from 0100h, min/max in the directory — section 32 |
| Six curves instead of 24 | 8 KB device instead of 32 KB; the arithmetic works out to the byte — section 32 |

## Reliability

Everything marked as "verified" was confirmed by calling the original
routines directly in the emulator over several sample points, usually in
addition checked against the listing or the schematic.

Three bugs were active in the emulator for a while and were fixed later —
`ACALL` was executed as `AJMP`, the auxiliary carry flag AC was missing,
and the key injection triggered INT1 twice. The places affected by that
have since been re-measured: the display bitmap in section 15 completely,
with an unchanged result, the strobe assignment in section 4 against the
service manual, likewise without deviation, and section 16, where two
strobes were missing — STR5 for every modulation, STR7 for the
asymmetric waveforms.

The second pitfall was not an emulator bug but a synthetic test image:
see section 26. With unexpected behaviour it is worth checking whether an
image and not the firmware is the cause.

## Files

| File | Content |
|---|---|
| `PM5139_Hardware_Reference.md` | main document, 35 sections |
| `PM5139_Firmware_Modification.md` | how to change the firmware and flash it back |
| `PM5139_Tables.md` | command and message tables of both versions |
| `PM5139_Changelog_V13_V15.md` | what changed from V1.3 to V1.5, in prose |
| `M27512_PM5139_V20.bin` | our own version V2.0: arbitrary curve 3 de-noised, built from V1.5 |
| `mkv20.py` | builds V2.0 from V1.5 or V1.3, finds the addresses by signature |
| `asm51.py` | tiny MCS-51 assembler for ROM extensions |
| `mkdoom.py` | places a melody in the free ROM and hooks it to the diagnostic menu |
| `doomtest.js`, `notefreq.js` | record the note sequence, check the frequency encoding |
| `plot_waveforms.py` | plots all waveform tables of an arbitrary image |
| `plot_v20.py` | comparison plot of arbitrary curve 3, V1.5 against V2.0 |
| `waveforms.py` | generates waveforms in both formats (ROM 8 bit, EEPROM 10 bit) |
| `mkarb.py` | fills the six arbitrary slots -> `D310_image_V20.bin` |
| `plot_arb.py` | plots the six curves of an EEPROM image |
| `D310_image_V20.bin` | arbitrary EEPROM with six curves of our own, ready to burn |
| `PM5139_ARB_V20.png` | the six curves plotted |
| `PM5139_Waveforms_V15.png`, `..._V20.png` | overall plot per version |
| `PM5139_Waveform3_V15_vs_V20.png` | before/after of the corrected curve |
| `PM5139_User_Manual_OCR_ENG.txt` | OCR of the English manual part, searchable |
| `PM5139_V13_disasm.asm`, `..._V15_...` | disassembly |
| `PM5139_Diff_V13_V15.txt` | block-by-block comparison |
| `PM5139_Waveforms.png` | all ROM waveform tables plotted |
| `PM5139_Bit_Crossreference.md` | flags 20h–2Fh, where they are set, cleared and tested |
| `PM5139_Simulator.html` | browser simulator, everything inline |
| `romfix.py` | check and correct the checksum |
| `emu.py`, `system.py`, `system2.py`, `keys.py` | Python emulator |
| `core.js` | JavaScript emulator |
| `bitmap.js` | check the display bitmap, singly and in pairs |
| `trace.js` | log the ROM addresses that were executed |
| `flags.js` | effect of the state bits on the C-bus telegrams |
| `cmd16.js` | strobes in the wake of a command |
| `iface.js` | emulate the interface card at I²C 5Eh |
| `arb.js` | arbitrary EEPROM: directory check 9615h against different images |
| `mcs51.py`, `analyze2.py`, `seqdiff.py` | disassembler and analysis |
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
| `lines.py` | read wire segments off a rendered schematic sheet |
| `symbols.py`, `annotate.py`, `mapv15.py` | symbol table, annotated listing, V1.5 mapping |
| `PM5139_V13_annotated.asm`, `..._V15_...` | disassembly with names and header comments |
| `D310_image.bin` | **really read out** arbitrary EEPROM D310 (X28C64, 8 KB) |
| `D310_image_synthetic.bin` | the old generated version, only a counter-check now |
| `PCF8570_image.bin` | NVRAM in the factory state, produced by the firmware |
| `PCF8570_image_old_synthetic.bin` | the old, faulty image |
| `patch_ok.bin` | example: modified ROM with a corrected checksum |

## Sources

- **`PM5139_User_Manual_FLUKE.pdf`** — user manual PM5139, 354 pages,
  trilingual (GB/D/F). **No text layer**, a pure scan; the English part
  (PDF pages 13–145) sits next to it OCRed as
  `PM5139_User_Manual_OCR_ENG.txt`. Describes the remote control
  commands completely, chapter 3.7.4.6 the arbitrary waveforms.
- **`PM5136_User_Manual_FLUKE.pdf`** — user manual PM5136, 278 pages,
  **with a text layer**, directly readable with `pdftotext -layout`.
  Useful as a counter-check: its error numbers and its command list show
  which parameters and assemblies the smallest model does not have.
- **`PM5136_PM5138A_PM5139_Specsheet.pdf`** — data sheet of all three
  models side by side, with real text. Operating limits per waveform,
  arbitrary data (1024 points, 10 bit, 24 memories).
- **`pm5138A_service_manual.pdf`** — service manual PM 5138A, 176 pages,
  OCRed, text cleanly readable with `pdftotext -layout`. Primary source
  with schematics, parts list and alignment instructions. Pages 4-3 to
  4-28 are missing here as well, chapter 4.12 on the interface from 4-29
  on is present. PM5136, PM5138A and PM5139 are internally almost
  identical and differ only in the figures for Vpp and frequency.
- Operating manual PM5139 (Fluke 1997) — error codes, operating logic.
- No PM5139 service manual could be found; people have been looking in
  forums since 2010.
