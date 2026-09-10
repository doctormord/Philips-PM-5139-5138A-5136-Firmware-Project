# PM5139 — hardware reference: strobes, bus, firmware routines

Sources: firmware disassembly V1.3 (addresses without further note) and
service manual PM 5138A (4822 872 15115, Fluke 1994), fig. 106 "Unit 2,
CPU" as well as section 6, program 4 "Strobe Test".

The PM5138A is the 10 MHz sister model of the PM5139 from the same
series; the digital part and the firmware architecture are identical.

---

## 1 Processor and memory

| Position | Type | Function |
|---|---|---|
| D301 | PCB80C652 | 8051 core with hardware I²C, 256 bytes of internal RAM |
| Crystal | 12.000 MHz | system clock |
| D304 | 74HCT573 | address latch AD0–AD7 |
| D306 | HN27512G-25 | program EPROM 64K — the dump at hand |
| D310 | HN58C256P-20 / X28C256 | EEPROM 32K×8, an 8K×8 variant is possible |
| D305 | PCF8570P | 256×8 RAM on the I²C bus, battery backed (G812) |
| D307 | 74HCT4514 | "STROBE ENCODER", 4→16 decoder |

**SFR D8h is S1CON**, not CCON. `MOV S1CON,#45h` during reset sets
ENS1=1, AA=1 and the bit rate CR=001. `CLR S1CON.6` at 622Eh and 625Ch
switches the hardware I²C block off before the firmware bit-bangs
SCL/SDA on P1.6/P1.7 itself (routine from 51A1h on).

In V1.5 both `CLR S1CON.6` are missing while the reset still sets ENS1.
To be checked.

The write access `MOV 0FBh,A` at 8E0Ah (V1.5: 9171h) hits an SFR that
does not exist on the 80C652. What was meant is the indirectly addressed
RAM 0FBh, which is written correctly one line earlier. A harmless bug,
present in both versions.

---

## 2 The external address space

`MOVX` splits cleanly at bit A15:

| DPTR | Destination |
|---|---|
| 0000h–7FFFh | EEPROM D310, A0–A14, its own /CE /OE /WE |
| 8000h–8FFFh | strobe encoder D307: **A8–A11 = strobe number** |

The size detection of the EEPROM sits at 9798h: 55h is written to 7FFFh,
5FFFh, 3FFFh and 1FFFh and read back — exactly the distinction between
the 32K and the 8K fit that the schematic lists as a variant. Result
code in R6: 00h, 86h or 8Fh.

---

## 3 The central output routine

All shift registers of the analogue units hang on one common serial line
(SBUF in shift register mode, 8051 mode 0). The strobe decides which
register takes the data.

```
0E8A  MOV   A,@R0          ; data from RAM 14h downwards, MSB first
0E8B  CLR   TI
0E8D  MOV   SBUF,A
0E8F  JNB   TI,$           ; wait for the end of the transfer
0E92  DEC   R0
0E93  DJNZ  R4,0E8A        ; R4 = number of bytes
...
0E98  ORL   DPH,#80h       ; fire the strobe
0E9B  MOVX  @DPTR,A
0E9C  MOV   DPH,#80h       ; back to idle output 0
0E9F  MOVX  @DPTR,A
```

Calling convention: DPH = strobe number, R4 = byte count, data in RAM
11h…14h. `ORL DPH,#80h` turns that into the address 8n00h.

---

## 4 Strobe assignment

The hardware assignment comes from the service manual, section 6 program
4. Entry points and call sites come from the V1.3 disassembly.

| Strobe | DPH | Hardware per manual | Entry | Bytes | Callers |
|---|---|---|---|---|---|
| STR0 | 80h | idle output / status register | 517Dh (read) | – | 36 calls |
| STR1 | 81h | RAM, unit 4, D101 | direct 43BDh, 1D2Ah | 2 | display/control word |
| STR2 | 82h | RAM, unit 4, D102, D103 | direct, 17 places | – | waveform download |
| STR3 | 83h | ampl. modulator U4 D144, pulse gen. U4 D126 | 0E78h | 2 | 0E4Ah |
| STR4 | 84h | burst logic, unit 4, D121, D122 | 0E7Fh | 2 | 0C2E 0C39 0C4E 0C54 0CBE 0CCA 0CD6 0D73 |
| STR5 | 85h | modulation oscillator, U4 D130, D138, D139 | 0E69h | 4+2 | 0BF8 0CEB 0D04 110D 111D |
| STR6 | 86h | TWS, unit 2, D331 (PCF1842P) | 0E54h | 4 | through 4321h |
| STR7 | 87h | DC generator, unit 3, D301 | 0E5Bh | 2 | 09B5 0B12 0B1E 0B2C 0B37 0B4A |
| STR8 | 88h | sweep output voltage, unit 1, D307 | direct 1D0Ch | – | sweep output |
| STR9 | 89h | amplitude controller, unit 3, D101, D102 | 0E62h | 1 | 09BB 0AFE 0B50 0BA6 10BB |

STR10–STR15 are brought out at the decoder but are never addressed by
the firmware.

---

## 5 The status register (read through STR0)

`517Dh: MOV DPH,#80h / MOVX A,@DPTR / RET` — 36 call sites.

| Bit | Meaning | Evidence |
|---|---|---|
| ACC.0 | event pending, main loop | 30 of 36 calls test exactly this bit |
| ACC.3 | second event source | 4 calls, among them 62B7h and 71ADh |
| ACC.4 | busy of the waveform RAM | 28 wait loops `JNB ACC.4,$` |

The busy loops all run with DPH=82h, that is against STR2 — which
confirms STR2 as the path to the waveform RAM on unit 4.

---

## 6 Waveform download

The tables shown in `PM5139_Waveforms.png` go into the RAM on unit 4
exclusively through STR2:

| Table | Load routine | Content |
|---|---|---|
| 44A7h | 3DABh / 4003h | quarter sine, mirrored to 1024 points |
| 46A9h | 3EFCh | haversine, 512 × 12 bit |
| 4AABh | 4425h | ten sine arcs, each step 3.33 dB smaller in amplitude (see section 34) |
| A047h / A447h / A847h | 9E37h, selected through RAM 0Dh | three built-in arbitrary curves |

The frequency goes to the TWS separately through STR6 (D331, PCF1842P) —
four bytes, set up in 4321h from the table at 4335h.

---

## 7 Self-test

The manual describes seven subprograms, reachable through the LOCAL key
while switching on. They correspond to the jump table at 5A0Bh with
eight LJMP entries:

| No. | Manual | Jump target |
|---|---|---|
| 1 | Display Test | 5A2Fh |
| 2 | Keyboard Test | 5A42h |
| 3 | Memory Register Test | 5ADBh |
| 4 | Strobe Test | 5B44h |
| 5 | Interface Test (RS-232 / IEEE-488) | 5C0Bh |
| 6 | Rotary Knob Test | 5D68h |
| 7 | EEPROM Test | 5EE9h |
| – | return to the menu | 59D1h |

The assignment follows the order in the manual and in the table; the
individual routines have not been cross-checked yet.

---

## 8 The serial C-bus

All shift registers of the analogue units are HCT4094 — serial shift
registers with their own strobe input. Exactly the type the model in
section 3 calls for.

The bus is called **C-bus** in the schematic and consists of two lines:

| Signal | Meaning | CPU pin |
|---|---|---|
| SC | serial clock | P3.1 / TXD |
| SD | serial data | P3.0 / RXD |

That matches the 8051 shift register mode (SCON mode 0), in which TXD
carries the clock and RXD the data. The bus is distributed through
HC4050 buffers (D105, D106 on unit 4); one buffered branch SC1/SD1 goes
to the amplitude modulator, the pulse generator and the modulation
oscillator, another to the burst logic.

---

## 9 Unit 4, RAM — fig. 114

This also answers the open question of STR1 against STR2:

| Strobe | Device | Label in the schematic |
|---|---|---|
| STR1 | D101-A HCT4094 → D104-A HCT367 | **page select** |
| STR2 | D102-A, D103-A HCT4094 | data and control path |

The waveform RAM itself:

| Position | Type | Label |
|---|---|---|
| D107-A | HM6716-30, 2K×8 | **RAM upper 8 bits** |
| D108-A | HM6268 | lower 4 bits |
| D112-A | HCT4094 | **load lower 4 bits** |

**The RAM is 12 bits wide.** That independently confirms what we had
derived from the ROM tables: the values are transferred as a high byte
plus a low nibble, with the nibble duplicated in the second byte
(produced at 3E27h with `MOV R6,A / SWAP A / ORL A,R6`). The haversine
table at 46A9h has only the values 00h, 44h, 88h and CCh as low bytes —
exactly the four possible duplicated nibbles.

Further signals at XB07: pin 13 "EN to TWS", pins 16–25 "10 bits from
TWS", pin 15 "C/n to DAC".

### From a 10-bit address to a 12-bit signal

The two numbers concern different quantities and do not contradict each
other:

```
TWS ──10-bit address──> RAM (1024 slots)
                        D107 HM6716   upper 8 bits
                        D108 HM6268   lower 4 bits
                              │
                        12-bit data (S1…S12)
                              ▼
                        N110 TDC1012, 12-bit DAC     clock: C/n at pin 16 (CONV)
                              │
                        OUT+ / OUT− ──> low-pass
```

So the TWS only counts through the **sample point** — 1024 of them, for
which ten bits are enough. At each sample point sits a **twelve-bit
word**, and that comes from two devices side by side: eight bits from
D107, four from D108. Fig. 115 shows the twelve lines **S1 to S12**
individually at the DAC, labelled `from RAM, TWS`.

**The converter is a TDC1012** (N110), a fast 12-bit DAC with a
differential output OUT+/OUT−, its own reference REF+/REF− and separate
analogue and digital grounds. The transfer happens with **C/n** on pin
16, `CONV` — the same line that XB07 pin 15 carries as "C/n to DAC".

*For clarity:* the **DAC08EN** from the parts list is not this
converter. DAC08 types sit in the side paths — N302 in the DC generator
(fig. 112), N127 in the pulse generator for the asymmetry (fig. 118) and
N308 at the sweep output on unit 1. The signal path itself runs through
the TDC1012.

When **loading**, the firmware goes the opposite way: the high byte
through the data path to STR2, the low nibble through D112, in the
schematic `load lower 4 bits`. That is why the nibble is duplicated in
the second byte of the ROM tables — 00h, 44h, 88h, CCh are the only
values that occur there.

---

## 10 Unit 5, keyboard and display — fig. 122

| Position | Type | Function |
|---|---|---|
| D302-A | **SAA3007** | keyboard encoder, 455 kHz resonator, matrix S0–S6 / D0–D6 |
| D304-A | **PCF8576T** | LCD driver on the I²C bus, 40 segment outputs A0–A39 |
| S405 | "BIT GENERATOR" | rotary knob, two phases A1/A2 through HCT132 Schmitt triggers |
| H401 | backlight | |

So the display hangs on the I²C bus (SCL/SDA), the keyboard on a
dedicated encoder device. The SAA3007 delivers a serial word with a
2-bit counter per key press — that explains the description of the
keyboard test in the manual: "e.g. 12-2 when key DC is pressed. This
control number is generated by the keyboard decoder and can be changed
to 0, 1, 2, or 3 by pressing this key again."

Pin assignment of XB05 between unit 2 and unit 5:

| Pin | Signal |
|---|---|
| 7 | /RES |
| 8 | INL |
| 9 | INR |
| 10 | ITG |
| 11 | SCL |
| 12 | SDA |
| 13 | SKC |

INL and INR are the two phases of the rotary knob. The firmware reads
them at 5EA1h with `MOV C,P1.4 / ANL C,/P1.3` respectively
`MOV C,P1.3 / ANL C,/P1.4` and derives the direction of rotation from
that — this is program 6 of the self-test.

---

## 11 The keyboard decoder

The SAA3007 delivers its data **pulse-width coded on a single line**
that hangs on **P3.3** (INT1). The firmware decodes it in software at
**0227h**:

```
022A  MOV   TH0,#0D7h      ; preload timer 0
022D  MOV   TL0,#46h
0230  CLR   TF0
0232  JNB   P3.3,$         ; wait for the rising edge
0235  JB    TF0,025Ah      ; timeout -> abort
0238  JB    P3.3,0235h     ; measure the pulse width
023B  MOV   A,TH0
023D  CJNE  R6,#0Bh,024Ah  ; 11 bits?
...
024A  ADD   A,#10h         ; threshold -> the carry is the bit
024C  MOV   A,R5
024D  RLC   A              ; shift the bit in
024F  INC   R6
0250  CJNE  R6,#05h,022Ah
```

Eleven bits are shifted in; the bit follows from the measured pulse
length through `ADD A,#10h` and the carry it produces. The result is
returned in R5. On a timeout before the eleventh bit the routine returns
0.

According to fig. 122 the LOCAL key (S820) as well as ADDRESS (S821) and
RESET (S822) are **not** in the encoder matrix but wired separately.
That agrees with the manual, which says explicitly for the keyboard
test: "Press any key at random, except LOCAL."

### Evidence from the strobe test

Program 4 of the self-test at **5B44h** connects both findings and at
the same time confirms the strobe table from section 4:

```
5B4D  MOV   1Fh,#01h       ; strobe number, starting at 1
5B5A  JNB   P1.4,5B8Ch     ; knob moved -> 5EA1h, 1Fh +/- 1
5B5D  JB    P1.2,5B8Ch
5B66  JB    P3.3,5B5A      ; no key -> keep waiting
5B75  MOV   R0,#14h        ; otherwise fill RAM 0Eh..14h with 00h or FFh
5B7A  JNB   22h.0,5B7Eh
5B7D  CPL   A
5B82  MOV   R4,#06h        ; six bytes
5B84  MOV   DPH,1Fh        ; strobe = knob position
5B87  LCALL 0E86h          ; send and strobe
```

Word for word what the manual describes: select the strobe line with the
rotary knob, then set all outputs of the selected register high or low
with any key.

---

## 12 Port assignment of the 80C652

Counted over the whole ROM, identical in V1.3 and V1.5. The XB05 pin
assignment was verified by the owner on the instrument.

| Pin | Direction | Signal | Use | Evidence |
|---|---|---|---|---|
| P0 | bidir. | AD0–AD7 | multiplexed bus | fig. 106, D304 HCT573 |
| P2 | out | A8–A15 | address bus, A8–A11 at the same time the strobe number | fig. 106, D307 |
| P1.0 | out (5×) | PL, XB03.8 | pen lift for an XY recorder | 1911h, 1A3Fh, 1B8Ah |
| P1.1 | out (1×) | FMO → U2 clock gen. | FM modulation on | 0C08h |
| P1.2 | in (6×) | KTG, XB05.10 | key word ready | 5B5Dh, 5C8Fh, 5D1Dh |
| P1.3 | in (8×) | IDR, XB05.9 | rotary knob direction | 25C9h, 5EA7h |
| P1.4 | in (13×) | ITG, XB05.8 | rotary knob pulse | 25CDh, 25EBh, 5EA1h |
| P1.5 | out (20×) | EN to TWS, XB07.13 | enable around every transfer | 4321h, 3DCAh |
| P1.6 | bidir. | SCL, XB05.11 | I²C clock, in software | 51A1h ff. |
| P1.7 | bidir. | SDA, XB05.12 | I²C data, in software | 51A1h ff. |
| P3.0 | – | RXD = C-bus SD | serial data, SBUF mode 0 | 0E8Dh |
| P3.1 | – | TXD = C-bus SC | serial clock | 0E8Dh |
| P3.2 | in (10×) | INT0 | interface | vector 0003h → 6279h |
| P3.3 | in (11×) | SKC, XB05.13 | serial key code | 0227h, 5A53h, 5B66h |
| P3.4 | out (1×) | T0 → PGS to TWS | waveform switching | 095Dh |
| P3.5 | out (40×) | DBK | strobe before busy polls | 3E58h, 4477h |

### The rotary knob

ITG and IDR are pulse and direction, not quadrature. At 25C2h the level
of IDR is sampled before the pulse, the edge of ITG is awaited and the
level sampled again; R3 counts the pulses.

### FMO

`MOV C,2Ch.2 / MOV P1.1,C` at 0C08h. 2Ch is the one-hot coded modulation
mode from table 740Ah, so bit 2 is FM. Through two NPN transistors the
line switches the Fmod signal onto the tuning voltage of the VCO on unit
2 — on fig. 105 the node "Fmod (FM)" at the low-pass in front of the
tuning voltage output.

### PGS

```
0953  ORL   C,2Bh.2
0955  ORL   C,2Bh.3
0957  ORL   C,2Ah.6
0959  ORL   C,2Ah.7
095B  ORL   C,2Bh.1
095D  MOV   P3.4,C
```

2Ah and 2Bh carry the one-hot coded waveform code from the table at
73F3h. The five bits that are tested are therefore unambiguous:

| Bit | Waveform |
|---|---|
| 2Ah.6 | POSSAW |
| 2Ah.7 | NEGSAW |
| 2Bh.1 | HAV |
| 2Bh.2 | SINEPULSE |
| 2Bh.3 | TRNGLPULSE |

So PGS is active for exactly those five waveforms that come out of the
waveform RAM. SINE, TRNGL, SQUARE, POSPULSE and NEGPULSE (bits 2Ah.1 to
2Ah.5) are produced by the TWS directly, ARBIT (2Bh.4) runs through a
path of its own and is not part of the expression.

### PL — pen lift

P1.0 is always switched together with timer 1: at 1911h TH1/TL1 are
loaded with FC1Bh, TR1 is set and `SETB P1.0` follows; at 1A3Fh, 1A4Bh
and 1B8Ah comes `CLR P1.0`, and likewise once in the initialisation at
0996h. The same timer constant FC1Bh sits at 1CF3h immediately before
the sweep loop, which per step outputs a new TWS frequency through STR6
and a new value for the sweep output voltage through STR8.

On unit 1, PL drives the base of V356 (BC337-25) through R626, emitter
to ground. At the collector sits R625 as a 20k5 pull-up, R634 (205R)
leads to socket X19, X20 is the ground return; V410 (BAW62) clamps
against ground. An open-collector output with current limiting, labelled
**PEN LIFT** in the schematic — the contact output for an XY recorder.

V356 inverts. So `SETB P1.0` during the ramp pulls the socket to ground
(pen down), `CLR P1.0` during the retrace releases it (pen up).

---

## 13 Power-on self-test and error codes

The order starting from the reset vector 3A9Ah. The error display is
produced by seven entry points at 3BFCh–3C14h, which all converge at
3C16h and write `E`, `r`, `r`, a space and the digit into the display
registers 3Eh–42h:

```
3C16  LCALL 396Dh        ; clear the display
3C19  MOV   42h,A        ; digit from R2 (segment pattern)
3C1C  MOV   41h,#00h     ; space
3C1F  MOV   40h,#50h     ; 'r'
3C22  MOV   3Fh,#50h     ; 'r'
3C25  MOV   3Eh,#0F1h    ; 'E'
3C28  LCALL 37DBh        ; send the display
```

| Display | Meaning per manual | Entry | Check in the ROM |
|---|---|---|---|
| `Err 1` | program memory checksum | 3BFCh | 3AABh: sum over 0000h–AC6Fh against the byte at AC70h; on failure an endless loop on 3AABh |
| `Err 2` | processor RAM fault | 3C00h | 3AD3h: CCh and 55h into every cell FFh…01h, read back; on failure an endless loop |
| `Err 3` | memory of the current settings | 3C04h | flag 22h.6, set at 3B21h; reloads defaults through 3C2Eh, 49h = 2Ch |
| `Err 4` | memory registers 1…9 | 3C08h | flag 22h.7, set at 3B07h in the loop 67h = 9…1, 49h = 2Bh |
| `Err 5` | overload protection | 3C0Ch | 3C7Ah: sets 20h.3, 49h = 1Eh, waits for a key through P3.3, returns to 3B46h |
| `Err 6` | frequency generation does not work | 3C10h | 43E4h returns carry; then `SJMP $` at 3B65h |
| `Err 8` | arbitrary memory | 3C14h | 9615h fails, 49h = 25h |
| `Err 9` | data transfer oscilloscope → generator | 92A2h | 49h = 09h, set at 8F08h |

Two remarks on this:

The manual says that only Err 1 and Err 2 prevent further operation. In
fact the firmware also hangs in an endless loop on **Err 6** (3B65h:
`SJMP 3B65h`). Whoever sees this error has a dead instrument — which
fits the reports in the forums.

Err 5 is not a pure power-on test: 3C7Ah is also jumped to during
operation and is acknowledged with any key.

---

## 14 Structure of the display

The display is a PCF8576 on unit 5 on the I²C bus. Its write slave
address byte is **70h**, and that is exactly what the transfer routine
starts with:

```
392F  MOV   A,#70h       ; slave address PCF8576
3931  LCALL 5187h        ; I²C start
3936  MOV   A,#0CEh      ; command bytes
393D  MOV   A,#80h
3944  MOV   A,#0E0h
394B  MOV   A,R3         ; parameters, from 37DBh: F8h
3951  MOV   A,R4         ;              and 70h
3957  MOV   R0,#30h      ; buffer
3959  MOV   R1,#14h      ; 20 bytes
```

**The display buffer sits in RAM 30h–43h**, 20 bytes. That is 40 nibbles
of 4 bits, i.e. exactly the 40 segment lines × 4 backplanes of the
PCF8576 — the buffer is a 1:1 image of the display RAM. 396Dh clears it
completely (display off).

Assigned so far:

| Buffer | Field |
|---|---|
| 3Eh–42h | main field, 5 digits, MSD first |
| 39h–3Ch | lower number field, 4 digits (fMOD/DEV/fSTOP/T/N/SYMMETRY/REG/ADDR) |
| 3Dh | modulation and sweep row |
| 30h–38h, 43h | remaining fields and annunciators, not yet broken down |

Evidence for 39h–3Ch: at 1829h the four BCD registers 15h–18h are copied
directly to 39h–3Ch, at 1917h all four are cleared together.

### Example: the modulation row

3812h builds the byte for 3Dh directly from the one-hot code 2Ch:

```
3812  MOV   A,2Ch
3814  ANL   A,#1Fh      ; bits 0-4 unchanged
3816  MOV   12h,A
3818  JB    2Ch.7,3831h
381B  JB    2Ch.5,3822h
381E  JB    2Ch.6,3827h
3822  ORL   12h,#60h    ; sweep linear
3827  ORL   12h,#0C0h   ; sweep logarithmic
```

It is written at 14EBh with `MOV 3Dh,12h`. The display row reads
`MOD-OFF AM FM PSK GATE LIN-SWP-LOG BURST`; so bits 0 to 4 correspond to
the order MOD-OFF, AM, FM, PSK, GATE, and the sweep indications come on
top as the bit pairs 60h respectively C0h.

The remaining annunciators can be resolved after the same pattern: the
waveform symbol row from 2Ah/2Bh, the trigger row from 2Fh. For the
final assignment bit → symbol, the segment/backplane assignment of the
PCF8576 from fig. 122 is missing.

---

## 15 Bit assignment of the display

Determined by executing the original code in the interpreter (`emu.py`):
load the defaults through 3C2Eh, set one flag or one command, run the
display build at 3381h, compare the buffer 30h–43h.

Base state after 3C2Eh:
`02 00 00 02 00 A0 28 0C 0E ED 00 00 00 00 00 0E ED ED EF 40`

### Waveform symbol row

Documented twice over: through the one-hot code in 2Ah/2Bh and,
independently of that, through the command tokens from the table at
7752h.

| Symbol | Flag | Token | Buffer bit |
|---|---|---|---|
| `═` DC | 2Ah.0 | – | 36h.1 |
| `∿` SINE | 2Ah.1 | 11h | 36h.3 |
| `∿` TRNGL | 2Ah.2 | 12h | 36h.2 |
| `⊓` SQUARE | 2Ah.3 | 13h | 36h.4 |
| `⊓` POSPULSE | 2Ah.4 | 14h | 36h.6 |
| `⊔` NEGPULSE | 2Ah.5 | 15h | 35h.0 |
| `∧` POSSAW | 2Ah.6 | 16h | 35h.2 |
| `∨` NEGSAW | 2Ah.7 | 17h | 43h.2 |
| HAV | 2Bh.1 | 18h | 43h.4 |
| SINEPULSE | 2Bh.2 | 19h | 43h.5 |
| TRNGLPULSE | 2Bh.3 | 1Ah | 43h.3 |
| `ARB` | 2Bh.4 | 1Bh | 43h.1 |

36h.5 stays set for every waveform — a fixed part of the display,
presumably the row marker `▶`.

### The digit row

Until now only the annunciators were covered in this section. The digits
of the frequency display sit in **3Eh–43h**, and specifically in the
image that is actually sent — the RAM buffer 30h–43h often shows an
intermediate state of the build when read. `core.js` carries the sent
image along in `frame`, and that is the reliable source (`display.js`,
`digits.js`).

The encoding is **different per digit position** — on the PCF8576 the
segments of one position are spread over different bits. Measured by
turning the knob with the frequency selected:

| Digit | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|---|
| Byte **42h** | 02 | 0E | 7B | 3F | 9E | B7 | F7 | 2E | FF | BF |
| Byte **41h** | ED | 0C | 79 | 3D | 9C | B5 | F5 | 2C | – | – |

For the digits 1 to 7 the two rows differ **only in bit 1** — that is
where an additional segment of the last position sits, presumably the
decimal point. The zero falls out of the pattern (02 against ED); it is
apparently driven differently in the last position.

When stepping the decade up with key 0Bh, **43h** changes from 40h to
80h, namely between decade 7 and 8:

```
decade 5 … 9, mantissa unchanged:
  00 0E ED ED 02 40     decade 5
  00 0C EF ED EF 40     decade 6
  0C ED EF ED EF 40     decade 7
  0E ED ED ED ED 80     decade 8
  0C EF ED ED ED 80     decade 9
```

**All positions share one base encoding**, 40h and 41h show it
unchanged:

| Digit | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|---|
| Segments | ED | 0C | 79 | 3D | 9C | B5 | F5 | 2C | FD | BD |

Bit 1 (02h) is an **extra segment**, the separator. So `EF = ED | 02` is
the zero with a separator — and **02h on its own is an empty position**,
not a zero. That resolves the apparent outlier of the first measurement
series: with mantissa 01000 the last position stays empty, with 01040 it
shows EFh, a real zero.

`readout.js` turns that into plain text:

```
decade 5:  00 0e ed ed 02   ->  " 1.00 "     43h = 40h
decade 6:  00 0c ef ed ef   ->  "10.00"      43h = 40h
decade 7:  0c ed ef ed ef   ->  "100.0"      43h = 40h
decade 8:  0e ed ed ed ed   ->  "1.000"      43h = 80h
decade 9:  0c ef ed ed ed   ->  "10.00"      43h = 80h
```

### The decade encoding, resolved by that

The change of 43h between decade 7 and 8 is the transition
**kHz → MHz**. With the decoded digits this gives:

| Decade | Display | Unit | Frequency |
|---|---|---|---|
| 5 | 1.00 | kHz | 1 kHz |
| 6 | 10.00 | kHz | 10 kHz |
| 7 | 100.0 | kHz | 100 kHz |
| 8 | 1.000 | MHz | 1 MHz |
| 9 | 10.00 | MHz | 10 MHz |

The mantissa stays the same, only the separator moves. As a formula:

```
f = M · 10^(D−8) kHz          M = four-digit mantissa, D = decade
```

That replaces the version in section 18 (`f = M · 0.1 Hz · 10^(D−1)`),
which was only documented over decades 1 to 5.

**Checked against the three cases read off the instrument** — the number
of steps and the final value agree in each case:

| Start | Course | End | Steps |
|---|---|---|---|
| 10 kHz (M=1000) | 100 kHz → 1 MHz → 10 MHz | 10 MHz | 3 ✓ |
| 20 kHz (M=2000) | 200 kHz → 2 MHz → 20 MHz | 20 MHz | 3 ✓ |
| 25 kHz (M=2500) | 250 kHz → 2.5 MHz | 2.5 MHz | 2 ✓ |

At 25 kHz the step to decade 9 is refused because the mantissa 2500
exceeds the table limit 2001 — 25 MHz would be above the 20 MHz of the
instrument. At 2000 it does not bite. With that the display, the limit
table 12D2h and the measurement on the instrument close into one
consistent picture.

### Modulation row

| Display | Flag | Token | Buffer bit |
|---|---|---|---|
| MOD-OFF | 2Ch.0 | 21h | 33h.1 |
| AM | 2Ch.1 | 22h | 33h.5 |
| FM | 2Ch.2 | 23h | 33h.6 |
| PSK | 2Ch.3 | 24h | 32h.0 |
| GATE | 2Ch.4 | 25h | 32h.4 |
| LIN | 2Ch.5 | 26h | 31h.1 |
| SWP | 2Ch.5 and 2Ch.6 | 26h/27h | 31h.3 |
| LOG | 2Ch.6 | 27h | 31h.7 |
| BURST | 2Ch.7 | 28h | 31h.6 |

Sweep linear sets 31h to 0Ah (bits 1 and 3), logarithmic to 88h (bits 3
and 7). The middle word of the group `LIN-SWP-LOG` lights up in both
cases — exactly as printed on the front panel.

### Trigger row

The row is blocked as long as 2Ch.0 (`MOD-OFF`) is set. It only becomes
visible with sweep, burst or modulation.

| Flag | Buffer bit | Evidence |
|---|---|---|
| 2Fh.4 | 30h.2, 30h.4, 33h.4 | 6E5Ah: cleared → `TRGS INT`, set → `TRGS EXT` |
| 2Fh.5 | 33h.0 | 6DEFh: `MODSRC EXT` |
| 2Fh.0 | 31h.5 | set in all sweep and burst modes |
| 2Fh.1 | 31h.0 | ditto |
| 2Fh.2 | 32h.6 | counterpart to 2Fh.3 |
| 2Fh.3 | 32h.2 | `TRIGF CONT` / `TRIGF SING` |
| 2Fh.6 | 30h.2, 30h.4, 34h.6 | – |

With external triggering, 2Fh.4 additionally sets bit 4 in 3Bh, 3Ch and
3Dh, that is segment `g`. Three digits showing only the middle bar give
`- - -`: without internal triggering there is no cycle count to display.

### Further assignments

| Flag | Effect |
|---|---|
| 22h.3, 2Bh.5 | clear 37h and 38h — the three-digit AC/DC field |
| 2Eh.5 | fills 38h/39h — the counterpart to it |
| 2Dh.0…2Dh.6 | bits in 32h and 34h, only enabled without MOD-OFF: the parameter labels `fMOD m DEV fSTOP T N` |
| 20h.0 | only effective with 2Bh.4 (ARBIT) — an arbitrary-specific element |
| 21h.6 | digits in the lower field, REG/ADDR display |
| 27h.0…27h.2, 28h.1, 28h.2 | only effective with 2Eh.2, blank out the main and AC field |

Of 128 flags, 31 act on the display immediately, another 23 through a
precondition, the remaining 74 not at all.

### Re-checked after the emulator corrections

This whole section came into being while `ACALL` was still executed as
`AJMP` and the AC flag was missing. Both bugs are fixed, and the
measurement has been repeated completely with the corrected core — once
with `sweep.py` in Python and once with a port to `core.js`, which also
manages the expensive pair search in reasonable time.

Both cores deliver the same base state and the same numbers: **31 flags
act immediately, 23 through a precondition, 74 not at all.** Every
single assignment in the tables above is confirmed, the trigger row
included. So the emulator bugs had not falsified the bitmap.

Effects came to light that were still missing above:

| Flag | Effect | Precondition |
|---|---|---|
| 22h.1 | 42h → 02h | – |
| 2Bh.6 | 35h → 10h | – |
| 2Bh.7 | 33h.7 | – |
| 2Dh.7 | 34h.7, plus 3Ch and 3Dh | – |
| 2Eh.0 | 33h.3, plus 3Ch | – |
| 2Eh.3 | 36h.7 | – |
| 2Eh.4 | 35h.3 — this is `DIAL LOCKED`, see section 19 | – |
| 2Eh.7 | 31h.4 | – |
| 20h.1 | 3Ah, 3Bh.4 | 2Eh.0 |

Besides that, 2Ch.0 (`MOD-OFF`) sets 34h.2 in addition to 33h.1, and
2Ch.5 and 2Ch.6 set 35h.1 in addition to the sweep bits in 31h.

### Tooling

`emu.py` is a complete MCS-51 interpreter (internal RAM, SFRs, bit
addressing, MOVX onto an XRAM image, MOVC out of the ROM). Subroutines
can be stubbed by address list so that I²C and strobe accesses are
skipped. `sweep.py`, `sweep2.py`, `sweep3.py` and `cmdsweep.py` are the
four experiments the tables above come from.

---

## 16 From the key to the hardware

At the end of every executed command sits an `ORL 29h,A` at 75A7h, where
A comes from the table at 7598h, indexed through R5, the parameter
class:

```
7594  ED         MOV   A,R5
7595  04         INC   A
7596  83         MOVC  A,@A+PC
7598  01 00 04 04 08 08 08 00 08 02 0A 00 00 00 08
75A7  42 29      ORL   29h,A
75A9  D2 24      SETB  24h.4
```

RAM 29h is thus a bundle of reload requests: which analogue unit has to
be rewritten after the change. It is evaluated from 0915h on in the
cycle that starts at 090Ch:

```
0915  MOV C,29h.0 / ORL C,29h.1  -> 09BFh   frequency
091E  29h.1 with 2Ch.7 and 21h.7, or 29h.3 -> 0BA9h
092B  JNB 29h.5 -> 0EA1h                    interface
0931  JNB 29h.4 -> …
```

### Re-measured

The table below comes from `cmd16.js`: cold start, command token into
10h, command interpreter 71BFh, then 090Ch — recording every `MOVX` with
DPH = 8nh along the way. The names come from the command table at 7752h.

| Token | Command | 29h | Strobes in the wake |
|---|---|---|---|
| 11h | SINE | 06h | STR1 STR2 STR3 STR6 STR9 |
| 12h | TRNG | 06h | STR1 STR2 STR3 STR6 STR9 |
| 13h | SQR | 06h | STR1 STR2 STR3 STR6 STR9 |
| 14h | POSPULSE | 06h | STR1 STR2 STR3 STR6 **STR7** STR9 |
| 15h | NEGPULSE | 06h | STR1 STR2 STR3 STR6 **STR7** STR9 |
| 16h–17h | POS-/NEGSAWTOOTH | 06h | STR1 STR2 STR3 STR6 **STR7** STR9 |
| 18h–1Ah | HAV, SINEPULSE, TRNGLPULSE | 06h | STR1 STR2 STR3 STR6 **STR7** STR9 |
| 1Bh | ARB | 00h | – |
| 1Eh, 1Fh | #SYOFF, #SYON | 02h | STR1 STR2 STR3 STR6 STR9 |
| 20h–27h, 29h–2Fh | modulation and sweep | 08h | STR3 STR4 **STR5** STR9 |
| 28h | #BU (burst) | 0Ah | STR1 STR2 STR3 STR4 **STR5** STR6 STR9 |
| 30h–39h | OUTPUT, AC/DC, LOIMP … | 04h | – |

The 29h values agree with the table at 7598h: 02h, 04h, 08h and 0Ah
appear there; 06h arises by ORing two sources together.

### Two corrections against the first version

- **STR5 was missing.** With every change of modulation and sweep the
  modulation oscillator on unit 4 is rewritten. That is also compelling
  on the merits and was a gap in the old measurement.
- **STR7 is added, but only for the asymmetric waveforms.** Sine,
  triangle and square leave the DC generator alone; pulses, sawtooths,
  haversine and the two pulse variants readjust it. That fits the
  matter: these curves have a mean value different from zero which has
  to be compensated.

The rest of the pattern is confirmed. A new waveform means new RAM
contents, a new divider chain in the TWS and a new amplitude correction.
A changed modulation type leaves the waveform untouched. Burst is
the exception, which additionally reloads the TWS and the waveform RAM,
because a burst has to start with a defined start phase — matching
`STARTPHASE` as a command of its own (token 8Ah).

### On reliability

090Ch is not a self-contained subroutine but leads into the main cycle;
the measurement therefore runs with a step budget. Unlike in the first
version this has now been checked: from 50 000 to 2 000 000 steps every
command delivers **the same** set of strobes. So the budget is not a
source of error.

**Open:** the group 30h–39h with 29h = 04h triggers no strobe output
through 090Ch, although the AC and DC switches affect the output stage.
The path there probably runs through 29h.4 at 0931h and has not been
followed yet.

---

## 17 System emulator: start from the reset vector

`system.py` extends the interpreter with the peripherals needed for a
cold start:

- **Timers 0 and 1** as 16-bit counters with TF flags, controlled
  through TCON
- **Interrupts** INT0, TF0, INT1, TF1 and serial with the vectors
  0003h…0023h, enabled through IE, RETI resets the nesting
- **Serial interface** in shift register mode: TI is set a few clocks
  after writing to SBUF
- **I²C slave** on P1.6/P1.7 with START/STOP detection, bit counting and
  ACK over nine clocks
- **Strobe area** from 8000h: read accesses return an alternating busy
  bit so that the wait loops in the waveform download terminate
- **External EEPROM** 0000h–7FFFh as a writable image

### What the cold start shows

The checksums of both ROMs are correct: the sum over 0000h–AC6Fh gives
F2h and sits like that at AC70h; for V1.5 the sum over 0000h–B3C9h gives
the value 99h, which sits at B3CAh. So the dumps are complete and the
checksum routine has been read correctly.

The start then runs through the RAM test without errors and begins to
drive the display. The first I²C transfer reads:

```
70 CE 80 E0 F8 70  followed by 20 data bytes
```

Slave address of the PCF8576, three command bytes, two parameters and
the display buffer — exactly the order derived from the listing in
section 14, now confirmed by the running code.

With an empty EEPROM the firmware reports `Err 3` and then `Err 8`, but
keeps running and stays in the display refresh. That is the correct
behaviour for an instrument with a defective settings memory: according
to the manual both errors can be acknowledged.

Decoding the last 20 I²C bytes with the segment table from section 14
gives `Err` in the main field. With that the chain is closed once end to
end: ROM → CPU → I²C → PCF8576 → segment pattern → readable text, all
out of the original code.

### Open

- A valid EEPROM image is still missing. The header at 0000h/0001h and
  the register checksums from 0007h on can be derived from 9615h and
  95C1h, but my first attempt does not hit the structure yet.
- Key inputs are not injected yet. That would require reproducing the
  pulse-width coded data stream on P3.3 that 0227h measures — eleven
  bits, the bit value coming from the pulse length.

---

## 18 The frequency path, complete

The first functional block computed end to end: from the entered
frequency to the four bytes the TWS (D331, PCF1842P on unit 2) receives
through STR6.

### Where the frequency is stored

RAM 50h–52h, six BCD digits. The upper nibble of 50h is **not** part of
the number but the **decade index**; the remaining five digits are the
mantissa M.

```
50h = D M1     51h = M2 M3     52h = M4 M5
```

Example `11 50 10`: decade 1, mantissa 15010.

**Careful:** this example and the measurement table further down come
from the old, synthetic NVRAM image. In operation the firmware keeps the
mantissa **four digits** long — the lower nibble of 50h stays zero — and
changes the decade at 2000. The computation paths are right, but the
states cannot be set that way on the instrument; see section 23, "The
16-bit limits of the frequency representation".

### Conversion to binary

The conversion starts at 0A26h: R0 points at 50h, R3 counts three bytes,
and for each digit the 24-bit accumulator 12h:13h:14h is multiplied by
ten with 3029h and the digit is added:

```
0A5D  ANL   A,#0F0h      ; upper digit
0A5F  SWAP  A
0A63  MOV   B,#0Ah
0A66  MUL   AB
0A6C  ADD   A,R3         ; add the lower digit
0A6D  ADD   A,14h        ; 24-bit addition
0A72  ADDC  A,13h
0A77  ADDC  A,12h
```

### The decade as an exponent

The range code sits as a table directly in the code, indexed through the
decade index in R2:

```
09E5  MOV   A,R2
09E7  MOVC  A,@A+PC
09EA  A0 80 60 40 20 00 00 00 00 00
09F4  ORL   12h,A        ; exponent into the upper three bits
09F6  MOV   11h,#01h     ; TWS command "frequency"
09F9  LCALL 0E54h        ; four bytes, then STR6
```

After the conversion 12h is zero because the mantissa fits into 16 bits.
Only then is the exponent ORed in. The table values are multiples of
20h, so **E sits in bits 5 to 7**.

### The telegram

Sent from RAM 14h downwards, four bytes:

| Byte | Content |
|---|---|
| 14h | N, low part |
| 13h | N, high part |
| 12h | E in bits 5…7 |
| 11h | command code, 01h for frequency |

Further TWS commands in the same pattern: 04h together with
`ORL 12h,#20h` (09D9h), 20h (0A17h), 60h (0A20h) and C0h (0BBEh).

### The formula

Measured over five decades in the emulator:

| RAM 50h–52h | N | E | f |
|---|---|---|---|
| 11 50 10 | 30020 | 5 | 1 501 Hz |
| 21 50 10 | 30020 | 4 | 15 010 Hz |
| 31 50 10 | 30020 | 3 | 150 100 Hz |
| 41 50 10 | 30020 | 2 | 1 501 000 Hz |
| 51 50 10 | 30020 | 1 | 15 010 000 Hz |
| 10 15 01 | 3002 | 5 | 150.1 Hz |

From that:

```
N = 2 · M
f = M · 0.1 Hz · 10^(5 − E)      resp.      f = N · 0.05 Hz · 10^(5 − E)
```

So the mantissa goes into the divider **doubled**. That fits the design:
the triangle wave synthesizer counts half periods, and a triangle
oscillation needs a rising and a falling edge.

As long as the mantissa stays five digits long, a decade key only
changes the exponent — N stays constant. Only at the lower end of the
range is the mantissa itself divided; in the example from 30020 to 3002.

---

## 19 The rotary knob

Three conditions have to be met before a detent is evaluated at all:

```
004C  JB   P1.4,0062h     ; detent detected (ITG active low)
004F  JNB  24h.6,0057h    ; a parameter is selected
0054  LJMP 259Ah
25B0  MOV  C,21h.3        ; register selection with STORE/RECALL
25B2  ORL  C,21h.1
25B4  ORL  C,/2Eh.4       ; or the knob is unlocked
25B6  JC   25C2h          ; -> count detents
25B8  SETB 2Eh.2          ; otherwise only select the group
```

**2Eh.4 is DIAL LOCK.** Key code 2Ah toggles it, and the same bit drives
the `DIAL LOCKED` indication; the handler for it sits at 031Fh, see
section 25.

After a cold start with a valid NVRAM, 2Eh = 60h, so the bit is
**cleared and the knob is free**. The earlier statement that it is
locked after a cold start came from the synthetic NVRAM image and is
wrong — see section 26.

### It is a real quadrature encoder

The counting loop at 25C2h requires IDR to change **during** the ITG
edge:

```
25C9  MOV   C,P1.3        ; IDR before the edge -> F0
25D8  MOV   C,P1.3        ; IDR after the edge
25DA  ORL   C,F0          ; both 0  -> abort
25DE  MOV   C,P1.3
25E0  ANL   C,F0          ; both 1  -> abort
25E7  INC   R3            ; otherwise: count the detent
```

So ITG and IDR are two phases 90° apart, not a pulse with a direction
level. With one complete Gray cycle per detent
— (1,1) → (0,1) → (0,0) → (1,0) → (1,1) — R3 counts exactly one detent
per cycle.

### Two bugs in our own core

Two interpreter bugs came to light while working through this:

- The key injection triggered INT1 a second time through the edges of
  the data pulses. The decoder restarted and hung at 0232h in
  `JNB P3.3,$`. Every measurement taken right after a key press was
  worthless because of that.
- **The auxiliary carry flag AC was never computed.** Without AC, `DA A`
  works incorrectly, and the firmware computed in binary instead of BCD:
  turning down from 150.10 gave 150.0F instead of 150.09. With a correct
  AC the decimal arithmetic is right.

Both bugs are fixed in `emu.py` and `core.js`; the cold start stays
clean.

### The direction sits in F0

25CBh stores the IDR level present while ITG = 0 in flag F0. That flag
carries the direction of rotation through the whole evaluation: 2764h
adds when F0 = 0 and subtracts when F0 = 1, and 26DBh chooses the path
of the range check accordingly.

The model in `core.js` produces a full Gray cycle per detent out of the
rest position (ITG, IDR) = (1,1):

```
right  (0,1) -> (0,0) -> (1,0) -> (1,1)      F0 becomes 1
left   (1,0) -> (0,0) -> (0,1) -> (1,1)      F0 becomes 0
```

Because the main loop only enters at ITG = 0, the firmware reads IDR = 1
in one direction and IDR = 0 in the other. Both sequences are recognised
correctly.

### Both directions work

The earlier finding "one direction jumps to 20000" was a misdiagnosis.
The cause is the **start value**, not the direction.

The firmware keeps the frequency mantissa **four digits** long in the
range 200…2000; the limit sits in the table at 2A81h and is compared at
2A2Fh. The NVRAM image that came with the project, however, contains
decade 0 with the five-digit mantissa 15010 — a state the instrument
itself never produces. On the first turn upwards 2A16h normalises this
value, and that looked like a jump. For decade 0 the limit table also
only supplies the placeholder 00h, which is why 2A5Ah clamps at 20000.

With a normalised start value the behaviour is symmetric. Measured in
the complete simulator, cold start, DIAL LOCK off, one detent at a time:

| Start | 1× right | 2× right | 1× left | 2× left |
|---|---|---|---|---|
| D3 M1501 | 1502 | 1503 | 1500 | 1499 |
| D3 M1999 | 2000 | D4 M200 | 1998 | 1997 |
| D3 M2000 | D4 M200 | D4 M201 | 1999 | 1998 |
| D3 M0200 | 0201 | 0202 | 0199 | 0198 |
| D2 M1000 | 1001 | 1002 | 0999 | 0998 |
| D4 M1234 | 1235 | 1236 | 1233 | 1232 |

The transition 2000 → decade + 1 with mantissa 200 is equal in value.

With the corrected NVRAM from section 26 the counter-check runs without
any intervention by hand: cold start, turn the knob, done.

| Detents | 1 | 2 | 3 | 5 |
|---|---|---|---|---|
| right | 1001 | 1002 | 1003 | 1005 |
| left | 0999 | 0998 | 0997 | 0995 |

The start value is the factory state D5 M1000. Both directions are
symmetric — with that the old finding is finally refuted.

### The digit pointer

RAM 0Bh, which is R3 of register bank 1, selects the position. Its lower
nibble goes at 2685h into the table at 268Fh, from which the weight
comes through 26ABh and the BCD increment through 2724h. Measured with
the start value D3 M1501:

| 0Bh | right | left | Position |
|---|---|---|---|
| 00h, 01h | 1502 | 1500 | units |
| 02h | 1511 | 1491 | tens |
| 03h | 1601 | 1401 | hundreds |
| 04h | D4 M150 | 0501 | thousands |

Both directions act on the same position — that was unclear before as
well.

### Acceleration, measured

n detents in immediate succession, start D3 M1000:

| Detents | 1 | 2 | 3 | 4 | 5 | 8 | 12 | 16 | 24 |
|---|---|---|---|---|---|---|---|---|---|
| Change | 1 | 2 | 2 | 3 | 3 | 6 | 8 | 11 | 17 |

Turning right and left gives the same magnitude. The characteristic is
flatter than the raw table at 2622h, because between the detent count
and the increment sit the weighting at 26ABh and the increment table at
2724h; the latter is geometrically graded from 1 to 5000.

### State

The rotary knob is computed end to end: quadrature, direction through
F0, digit pointer, acceleration, range limits and decade change,
measured in both directions. What stays open is the limit table at
2A81h, of which only the entries for the decades in use are checked, and
the exact chain from the detent count through 26ABh to 2724h.

**The NVRAM image `PCF8570_image.bin` is not normalised** — it contains
decade 0 with mantissa 15010. As long as that stays so, every session in
the simulator starts in a state the instrument itself does not produce.
A value produced by the firmware, such as decade 3 with mantissa 1501,
would be right.

---

## 20 The amplitude path

### The three control quantities

| RAM | Meaning | Telegram |
|---|---|---|
| 1Ch | fine value for the amplitude controller | STR9, one byte |
| 1Dh | DC component, centred on 64h | STR7, second byte |
| 1Eh | range and relay byte | STR7, first byte |

Entry points: `MOV 14h,1Ch / LCALL 0E62h` at 0AFBh for STR9,
`LCALL 0E5Bh` at several places from 0B12h on for STR7.

### The attenuator relays

At 0AACh the range byte is formed directly from the amplitude decade:

```
0AAC  MOV   A,56h
0AAE  ANL   A,#0F0h
0AB0  SWAP  A            ; decade
0AB2  MOV   DPTR,#0B53h
0AB5  MOVC  A,@A+DPTR
0AB6  MOV   C,2Bh.7
0AB8  MOV   ACC.5,C
0ABA  MOV   1Eh,A
```

Table 0B53h: **04 1C 14 04**. The same patterns appear on the bus as the
first STR7 byte:

| Decade | Table | measured | K401 | K402 | Attenuation |
|---|---|---|---|---|---|
| 0 | 04h | A4h | – | – | 0 dB |
| 1 | 1Ch | 7Ch | on | on | 40 dB |
| 2 | 14h | B4h | – | on | 20 dB |
| 3 | 04h | A4h | – | – | 0 dB |

**Bit 4 switches K402 (20 dB), bit 3 adds K401.** That agrees with fig.
111, where K401 is labelled "20 dB (for 40 dB)". Two independent pieces
of evidence: the table in the ROM and the telegrams on the bus.

After switching, the firmware waits at 0B8Ah with timer 0 for FC1Ch,
optionally several times through R3 — the pull-in time of the relays.

### Correction per waveform

```
0B74  MOV   R0,#56h
0B77  LCALL 0F40h        ; BCD -> binary
0B7A  MOV   C,2Ah.1      ; SINE
0B7C  ORL   C,2Ah.2      ; TRNGL
0B7E  ORL   C,2Ah.3      ; SQUARE
0B80  ORL   C,2Bh.4      ; ARBIT
0B82  JC    0B86h
0B85  RLC   A            ; otherwise double
0B86  RR    A            ; and always halve
```

For sine, triangle, square and arbitrary the value is halved, for the
pulse shapes it stays as it is — the crest factor correction. It also
explains why the arbitrary EEPROM carries a minimum and a maximum per
curve.

Precondition for a fine value other than zero (0B58h): AC has to be on
and the waveform must not be DC.

---

## 21 Evaluation of the detents

### Acceleration

At 25F6h the detent count R3 is turned into a step size:

```
25F9  CJNE  A,#01h,2605h     ; one detent -> step 1
2605  ANL   A,#0F0h
2607  JZ    261Dh
261D  MOV   A,R3
261F  MOVC  A,@A+PC
2622  03 06 09 0C 0E 11 14 17 1A 1D 20 23 25 28 2B
```

Two detents give step 3, three give 6, four 9. From 16 detents on the
second table at 260Eh applies:
`2E 2E 31 34 38 3A 3B 3C 3C 3D 3D 3E 3E 3E 3E`.
So turning fast jumps in large steps.

### Parameter selection

RAM 24h, lower nibble, determines the selected group:

| Value | Group |
|---|---|
| 0 | waveform |
| 1 | frequency |
| 3 | AC amplitude |
| 4 | DC component |
| 5 | modulation parameters |

22h.3 is the AC output being switched on.

### First adjustment

```
2637  CJNE  A,#03h,264Fh
263D  JNB   22h.3,264Fh
2640  MOV   56h,#30h        ; initialise the amplitude
2647  MOV   57h,A           ; from the direction of rotation
2649  CLR   22h.3
264B  SETB  29h.0           ; request a reload
264F  CJNE  A,#04h,265Dh
2657  MOV   58h,#10h        ; initialise the DC component
```

The first detent after switching an output on sets a start value, only
the following ones adjust. The apparent jump to 3000 that I first took
for a range limit is exactly this initialisation.

### Open

The numeric formula from the entered voltage to 1Ch is still missing.
After the initialisation the amplitude does not react to further detents
in my emulator; the generic adjustment routine from 265Dh on with
`LCALL 080Bh` and the digit pointer table at 268Ch has not been computed
yet. That is the next starting point — and the same path then opens up
the DC component and the modulation parameters too, because all three
run through the same routine.

---

## 22 The remaining control quantities

All the formulas below are verified by calling the original routines
directly in the emulator, in each case over several sample points.

### Common BCD conversion

0F40h converts three BCD digits into a binary number 0…999 and returns
the decade in R2:

```
W = 100 · (first byte & 0Fh) + 10 · (second byte >> 4) + (second byte & 0Fh)
D = first byte >> 4
```

0F45h is the same entry without the decade, 0F65h with R4 = 0.

### Amplitude — STR9, one byte

```
1Ch = RR(W mod 256)              sine, triangle, square
1Ch = (W mod 256) & 7Fh          pulse and sawtooth shapes
```

`RR A` is a rotation without carry, not a division: E7h becomes F3h, not
73h. Documented at seven sample points.

Precondition (0B58h): 22h.3 has to be zero — the bit means **AC off**,
not on. Arbitrary runs through a branch of its own from 0B61h with RAM
48h and the descriptor values from the D310.

### DC component — STR7, second byte

```
1Dh = 64h + W    sign bit 58h.7 = 0
1Dh = 64h − W    sign bit 58h.7 = 1
```

Offset binary around 100, range 00h…C8h, i.e. ±100 steps. Nine sample
points checked.

### AM depth and FM deviation — STR5

The source is 5Ch/5Dh for AM, 5Eh/5Fh for FM (0BE5h/0BEAh):

```
AM:  19h = 2 · W       100 % depth -> C8h
FM:  19h = W           0…255
```

At 0C08h sits `MOV C,2Ch.2 / MOV P1.1,C` — the FM line FMO to the clock
generator, an independent confirmation of the port assignment from
section 12. Eight sample points checked.

### Burst cycles — STR4

Source 62h/63h, result as a 16-bit value in 13h:14h (0C71h):

```
decade 0:  N = W                 1…999
decade 1:  N = W + 1000          1000…1999
otherwise: N = 2000              limit
```

Without burst the default 0190h = 400 applies. Nine sample points
checked.

### Symmetry — STR3

The pulse generator uses a non-linear correction curve (0E2Fh):

```
0E2F  SUBB  A,#32h        ; symmetry minus 50 %
0E33  CPL A / INC A       ; magnitude
0E35  MOV   DPTR,#10DDh
0E38  MOVC  A,@A+DPTR
0E43  ADD   A,#80h        ; offset binary
0E48  MOV   13h,A
```

Table 10DDh, 31 entries for 0…30 % deviation:

```
0, 5, 10, 15, 20, 25, 29, 34, 39, 44, 49, 53, 58, 62, 67, 71,
76, 80, 84, 88, 92, 96, 100, 104, 107, 111, 114, 118, 121, 124, 127
```

The step size falls from 5 to 3 — a compressive characteristic, because
the duty cycle does not depend linearly on the control voltage. At 30 %
deviation 127 is reached, full drive. So the symmetry range is 20 % to
80 %.

### Summary

With that all six analogue assemblies are covered: TWS (frequency),
amplitude controller with attenuator, DC generator, modulation
oscillator, burst logic and pulse generator. The sweep over STR8 is
computed in section 23.

---

## 23 The sweep

The sweep does not recompute the TWS word from the BCD frequency at
every step; it carries a 40-bit frequency accumulator with a fixed step
size instead. Only shortly before the output is a TWS telegram in the
format of section 18 built from it again.

### Storage

| RAM | Content |
|---|---|
| 50h–52h | fSTART, BCD with a decade nibble, as in section 18 |
| 53h–55h | fSTOP, same format |
| 60h, 61h | sweep time, BCD with a range nibble |
| 30h–34h | fSTART in binary, unit 0.1 Hz, 5 bytes |
| 35h–38h | step size of the ramp voltage, 32 bit |
| 39h–3Ch | ramp accumulator; 39h is the byte that goes to STR8 |
| 3Dh–3Fh | N, the number of steps |
| 40h–42h | step counter |
| 15h–19h | frequency accumulator, 40 bit, relative to fSTART |
| 1Ah–1Eh | frequency step size, 40 bit |
| 1Fh | normalisation exponent |
| 43h–45h | time constant, 50·N |
| 6Ah.4 | direction, 1 = downwards |
| 2Ch.6 | logarithmic instead of linear |

The use of 35h–39h changes: during the preparation fSTOP sits there in
binary, after the swap at 15DEh the ramp step size.

### Preparation, 14B2h

The entry point is 14B2h, called from 1484h. The sequence:

```
14B2  sweep time from 60h/61h into 17h..19h, BCD
14E8  LCALL 3313h        ; BCD -> binary
14EB  3Dh..3Fh = 12h..14h ; N
14F7  17h=#32h, Z=N, LCALL 2FA0h   ; 50*N
1506  43h = 10h ; 44h:45h = -(11h:12h)  ; timer reload
151F  SETB 22h.4 / LCALL 162Ch / LCALL 1862h  ; fSTOP  -> 35h..39h
1527  CLR  22h.4 / LCALL 162Ch / LCALL 185Ch  ; fSTART -> 30h..34h
1535  LCALL 31D7h        ; 35h..39h against 30h..34h -> C
1538  6Ah.4 = C          ; direction
153D  larger value into Y, smaller into Z
1553  LCALL 32AEh        ; Y = |fSTOP - fSTART|
1556  LCALL 15FCh        ; normalise, R7 = exponent
1559  1Fh = R7
15A7  Z = N ; LCALL 3107h ; X = Y / N  -> frequency step size
15C9  LCALL 1862h        ; store away into 35h..39h
15CF  Z = N ; 16h = #0FFh ; LCALL 3107h  ; X = 0FF000000h / N
15DE  swap 35h..39h <-> 1Ah..1Eh
```

162Ch converts the BCD frequency into a binary value with the **unit
0.1 Hz**. Through the table at 167Eh the decade index selects a
multiplier from 169Bh ff. (10, 100, 1000, 10⁴, 10⁵, 10⁶, 10⁷ and
6 250 000).

| 50h–52h | 162Ch delivers | corresponds to |
|---|---|---|
| 11 50 10 | 15 010 | 1 501.0 Hz |
| 21 50 10 | 150 100 | 15 010 Hz |
| 31 50 10 | 1 501 000 | 150 100 Hz |
| 41 50 10 | 15 010 000 | 1 501 000 Hz |
| 51 50 10 | 150 100 000 | 15 010 000 Hz |

### The normalisation, 15FCh

15FCh shifts Y = 15h…19h until the top byte lies in the range 08h…0Fh,
counting the exponent in R7 along the way, starting at 24h = 36:

```
15FE  while 15h = 0: shift Y left by one byte, R7 -= 8
1614  while 15h & F0h: shift Y right by one bit, R7 += 1
1620  while 15h.3 = 0: shift Y left by one bit, R7 -= 1
```

Afterwards Y = Δf · 2^(36 − 1Fh), and Y fills exactly the upper 36 bits
of the 40-bit register.

### The two step sizes

```
frequency step size (1Ah..1Eh) = Δf · 2^(36 − 1Fh) / N
ramp step size      (35h..38h) = FF000000h / N
```

Measured by calling 14B2h directly in the emulator; Δf and N were read
out of the emulator as well, not computed:

| fSTART | fSTOP | Δf | N | 1Fh | Step size | step·N/Δf |
|---|---|---|---|---|---|---|
| 15 010 | 150 100 | 135 090 | 100 | 18 | 354 130 329 | 2¹⁸ |
| 10 000 | 100 000 | 90 000 | 100 | 17 | 471 859 200 | 2¹⁹ |
| 1 000 | 10 000 000 | 9 999 000 | 1 000 | 24 | 40 955 904 | 2¹² |
| 11 111 | 3 446 300 | 3 435 189 | 500 | 22 | 112 564 273 | 2¹⁴ |
| 123 450 | 12 345 000 | 12 221 550 | 10 000 | 24 | 5 005 946 | 2¹² |
| 500 000 | 10 000 000 | 9 500 000 | 2 000 | 24 | 19 456 000 | 2¹² |
| 100 000 000 | 344 630 000 | 244 630 000 | 100 | 28 | 626 252 800 | 2⁸ |
| 20 000 | 40 000 | 20 000 | 5 000 | 15 | 8 388 608 | 2²¹ |

In all eight cases step·N/Δf is exactly 2^(36 − 1Fh). The ramp step size
hits `FF000000h / N` exactly as well; the product N·step is FEFFFFB0h
throughout, so the ramp accumulator runs over the whole range and 39h
from 00h to FEh.

### The sweep time

60h carries the range, 61h two BCD digits. Bit 5 of 60h selects whether
61h goes to 19h or to 18h; the lower nibble of 60h supplies the leading
digit; if bit 4 of 60h is cleared, 3265h multiplies the result by ten on
top. 60h = 80h is the special case with the fixed value 0F4240h =
1 000 000.

| 60h | 61h | N |
|---|---|---|
| 30h | 10h | 10 |
| 20h | 10h | 100 |
| 20h | 25h | 250 |
| 21h | 00h | 1 000 |
| 10h | 25h | 2 500 |
| 00h | 10h | 10 000 |
| 00h | 25h | 25 000 |
| 80h | – | 1 000 000 |

With a step clock of FC1Bh, that is 997 µs, N = 1 000 corresponds to
exactly one second of sweep time.

### The retrace pause, 43h–45h

These three bytes are **not** the step clock — that comes from FC1Bh.
They form an extended waiting time for the **sweep retrace**, at three
places, 1A5Bh, 1A8Ah and 1AEDh, all in the aftermath of the sweep end at
1A0Ch:

```
1A4B  CLR   P1.0            ; pen lift, see section 12
1A4D  JNB   TF1,$
1A5B  MOV   0Dh,43h         ; number of timer overflows
1A5E  MOV   TH1,44h
1A61  MOV   TL1,45h         ; start value of timer 1
…
1A7A  wait for TF1, then count 0Dh down
1A74  MOV   39h,#00h        ; ramp to zero
1A77  LCALL 1D33h           ; send the telegrams
```

Timer 1 is loaded **only once**; inside the loop it then runs from zero.
So

```
waiting time = (65536 − 44h:45h) + 43h · 65536   timer ticks
```

and at 12 MHz one tick is one microsecond.

The value is formed at 14F7h from `50 · 65536 · N`: 43h gets the top
byte, 44h:45h the two's complement of the next two. That amounts to
**50 · N microseconds**, i.e. one twentieth of the sweep time.

| N | 43h | 44h:45h | Ticks | Time |
|---|---|---|---|---|
| 10 | 00h | FE0Ch | 500 | 0.5 ms |
| 100 | 00h | EC78h | 5 000 | 5 ms |
| 1 000 | 00h | 3CB0h | 50 000 | 50 ms |
| 2 500 | 01h | 17B8h | 125 000 | 125 ms |
| ≥ 10 000 | 07h | 5EE0h | 500 000 | 500 ms |

From 10 000 steps on the value is **fixed**. That is not an overflow but
intentional: 14E0h sets 22h.4 when the top BCD digit of the sweep time
is occupied, and 14F4h then branches with `JBC 22h.4` to the constant
`07 5E E0` at 1516h. So the retrace pause is capped at half a second.

For plotter operation that makes sense: after the run P1.0 lifts the
pen, the ramp goes back to zero, and the retrace gets a time that grows
with the sweep time — but not without limit.

**By the way:** 43h is at the same time the last byte of the display
buffer 30h–43h. The two uses exclude each other, because the sweep
repurposes the upper part of the buffer anyway.

### The loop, 1907h and 1932h

1907h sets the ramp accumulator 39h–3Ch, the frequency accumulator
15h–19h and the step counter 40h–42h to zero and starts timer 1. The
loop at 1932h does the following per pass:

```
193F  40h..42h += 1
194D  compare against 3Dh..3Fh -> on equality 1A0Ch, end of sweep
1962  39h..3Ch +/- 35h..38h     ; ramp voltage
19A4  15h..19h +/- 1Ah..1Eh     ; frequency
19E6  LCALL 1D8Eh               ; rescale and add fSTART
19E9  LCALL 2041h               ; determine the decade -> R7
19EC  LCALL 1D4Eh               ; rounding from R6.7
19EF  exponent from table 19F4h into 12h, 11h = 01h
1A03  LCALL 1CBAh               ; four bytes to the TWS
1A06  LCALL 1CD9h               ; sweep output and strobes
```

The sign at 1962h and 19A4h comes from 6Ah.5, the direction of addition
in 1E15h from 6Ah.4.

### The rescaling, 1D8Eh

1D8Eh undoes the normalisation. The index into the table at 2019h is
`25h − 1Fh`, i.e. 37 − 1Fh; the entry splits the shift into a byte part
and a bit part:

```
1D99  A = 25h - 1Fh
1D9E  DPTR = 2019h ; MOVC          ; shift code
1DA3  R5 = lower nibble            ; fine shift for 1F40h
1DAB  the upper nibble selects the byte alignment:
      0 -> 0 bits   8 -> 8 bits   4 -> 16 bits  2 -> 24 bits  1 -> 32 bits
      R6 = the next byte falling out
1E15  LCALL 1F40h                  ; fine shift
1E18  10h..14h +/- 30h..34h        ; add fSTART, 6Ah.4 chooses the sign
```

The lower nibble is a sum of four individual steps:

| Bit | Effect |
|---|---|
| 0 | one bit to the left, i.e. −1 |
| 1 | one bit to the right, +1 |
| 2 | another bit to the right, +1 |
| 3 | nibble swap, four bits to the right, +4 |

That makes byte part plus bit part = 36 − 1Fh for each of the 40 table
entries, which is the rescaling we are after. Example 1Fh = 18: index
19, entry 46h, so 16 bits from the upper nibble and +2 from the lower,
18 together.

1D4Eh then only adds the rounding carry from R6.7 — the routine does not
increase the accumulator by R6, as was assumed for a while.

### Measurement: three complete sweeps

Set up with 14B2h, then run from 1907h on and the TWS word tapped at
1A03h. fSTART = 1 501.0 Hz, fSTOP = 15 010 Hz, N = 100.

| Step | linear up | linear down | logarithmic | 39h |
|---|---|---|---|---|
| 1 | 1 636 | 14 865 | 1 536 | 02h |
| 11 | 2 985 | 13 515 | 1 933 | 1Ch |
| 21 | 4 335 | 12 165 | 2 435 | 35h |
| 31 | 5 685 | 10 815 | 3 065 | 4Fh |
| 41 | 7 035 | 9 465 | 3 855 | 68h |
| 51 | 8 385 | 8 115 | 4 855 | 82h |
| 61 | 9 735 | 6 765 | 6 110 | 9Bh |
| 71 | 11 085 | 5 415 | 7 695 | B5h |
| 81 | 12 435 | 4 065 | 9 685 | CEh |
| 91 | 13 785 | 2 715 | 12 195 | E8h |
| 99 | 14 865 | 1 636 | 14 660 | FCh |

In the linear case the frequency rises by exactly 135.09 Hz per step,
which is Δf/N. In the logarithmic sweep the ratio over each ten steps is
1.2589 — that is 10^0.1, so exactly one decade per hundred steps. The
ramp voltage 39h runs the same and linearly in all three cases; it
depends only on N, not on the frequency characteristic.

### The logarithmic sweep

If 2Ch.6 is set and 6Ah.3 cleared, 1D8Eh branches to 1E5Ch as early as
1D96h. The accumulator then carries not the frequency but its logarithm.
1E5Ch decomposes it:

```
1E5C  1Fh = (15h & FCh) >> 2          ; integer part
1E64  13h = ((15h & 03h) + (16h & FCh)) >> 2
1E72  14h = ((16h & 03h) + (17h & FCh)) >> 2
1E98  LCALL 2218h                     ; 2 to the power of the fractional part
1EDD  shift through the table 1EE7h   ; 2 to the power of 1Fh
```

So the classical decomposition `2^n = 2^integer · 2^fraction`.

### The exponential routine 2218h

2218h does **not** compute; it looks up and interpolates linearly:

```
2218  DPTR = 2398h
221B  A = 13h ; RLC A ; DPTR += A      ; two bytes per entry
222C  11h:12h = table[i+1]             ; upper sample value
2236  R3:R4   = table[i]               ; lower sample value
223D  11h:12h -= R3:R4                 ; difference
2248  difference · 14h                 ; weight it with the fractional part
2263  R3:R4 += result                  ; interpolated value
226B  X = (R3:R4 + 10000h) · W         ; multiply with 30h..34h
```

The **table at 2398h** has 257 entries of 16 bits, so 514 bytes, and
contains

```
w[i] = round((2^(i/256) − 1) · 65536)  mod 65536,   i = 0 … 256
```

255 of the 257 entries hit this formula exactly, two are off by 1. The
last entry is 0000h — that is 2^1 − 1 = 65536, the overflow is intended
and is accounted for correctly in the carry.

The subtracted one is the trick: for x ∈ [0,1), 2^x lies between 1 and 2
and would need 17 bits, while 2^x − 1 fits into 16. In the
multiplication, 226Bh brings the one back in as `+ 10000h`.
**Measured**, with the routine called directly:

| Tap | Result |
|---|---|
| at 226Bh, before the multiplication | R3:R4 = (2^((13h + 14h/256)/256) − 1) · 65536 |
| at the end | X = (R3:R4 + 10000h) · W, 40 bit |

Together therefore

```
X = W · 2^((13h + 14h/256)/256) · 65536
```

64 sample points checked for the interpolation, largest deviation 1; 36
runs of the whole routine, of which 28 exact and 8 off by the amount
that follows from the same rounding. Computed against the interpolated
table instead of the pure exponential function, every case agrees
exactly.

The table 2398h is used in the opposite direction as well: 2323h
searches it for 12h:13h and returns the index and the remainder — that
is the logarithm needed in the sweep setup at 1597h. One table for both
directions.

### The 16-bit limits of the frequency representation

At 166Bh only `1Dh = 13h` and `1Eh = 14h` go into the multiplication
with the decade factor. The third byte 12h is left behind. So as soon as
a decade factor applies, that is from decade 2 on, the sweep computes
with `M mod 65536`:

| Decade | M | 162Ch delivers | correct would be |
|---|---|---|---|
| 1 | 99 999 | 99 999 | 99 999 |
| 2 | 65 535 | 655 350 | 655 350 |
| 2 | 65 536 | 0 | 655 360 |
| 3 | 99 999 | 3 446 300 | 9 999 900 |

The **normal frequency path is limited too**, only at a different place
and even more tightly: the TWS telegram carries N = 2·M in 16 bits, so
it breaks down as early as M > 32 767. The earlier statement that 0A26h
was "not affected" was too optimistic.

| Path | largest mantissa |
|---|---|
| TWS telegram through 0A26h | 32 767 |
| sweep conversion 162Ch, from decade 2 on | 65 535 |

### Is this a firmware bug?

No — the values are unreachable through the user interface. The value
range was driven through in the complete simulator: digit position one
to the left, then forty turns upwards and eighty downwards, 106
different states.

```
mantissa  from 1 to 3000
decade    from 1 to 7
mantissa > 65535 encountered: no
```

The firmware keeps the mantissa **four digits** long and changes to the
next decade at 2000, see section 19. Values above 2000 only occur in the
top decade, where no further change is possible, and even there only up
to 3000. So both limits lie more than a factor of ten above that.

The fifth BCD position of the format — the lower nibble of 50h — stays
unused in operation. The example `11 50 10` from section 18 with the
five-digit mantissa 15010 comes from the old, synthetic NVRAM image and
is a state the instrument itself does not produce. The formula computed
there is unaffected by this.

**One path stays open:** whether a command over the interface can set a
five-digit mantissa without going through the range check. 29C9h does
not correct a value set from outside — it only applies in the adjustment
context of the rotary knob, with the registers loaded. The frequency
command of the remote control has not been followed yet.

### The telegrams per step

```
1CF3  MOV   TL1,#1Bh        ; step clock
1CF6  MOV   TH1,#0FCh
1CFB  MOV   DPH,#86h        ; trigger STR6 (the TWS takes over)
1CFF  MOV   DPH,#80h
1D03  MOV   SBUF,39h        ; one byte of sweep output voltage
1D0C  MOV   DPH,#88h        ; STR8 -> unit 1
1D14  MOV   R0,#0F0h        ; two bytes from the upper RAM
1D17  MOV   SBUF,@R0
1D22  MOV   SBUF,@R0        ; (R0 = F1h)
1D2A  MOV   DPH,#81h        ; STR1 -> page select unit 4
1D32  RET
```

So per step: let the TWS take over, one byte to the sweep output, two
bytes to the page select of the waveform RAM. The step clock comes from
timer 1 with FC1Bh — the same constant as for the pen lift.

### The step computation

1D62h forms the two bytes at RAM F0h/F1h out of the accumulator
12h:13h:

```
1D64  A = (12h & 1Fh) | (13h & E0h)
1D6E  RL A three times                ; shift the window by 3 bits
1D72  A = 13h & 1Fh
1D76  ADD A,#08h                      ; rounding
1D78  C = ACC.4 -> 22h.4              ; remember the rounding bit
1D80  @F0h = carry + shifted value
1D81  A = 18h, ACC.6 = 2Bh.4 (ARBIT), ACC.0 = rounding bit
1D8C  @F1h = A
```

1D38h does not belong here but in the normal frequency path: the routine
shifts 11h…14h left by one bit and is therefore exactly the doubling
`N = 2·M` from section 18. Its caller is 1C8Fh, and 29h.7 suppresses it.
1D4Eh only adds the rounding carry from R6.7; the earlier reading
"accumulator increased by R6" was wrong.

**State:** scaling, step sizes, sweep time, rescaling and both
characteristics are computed and confirmed in the emulator over complete
runs. With that the sweep is fully computed.

---

## 24 The arithmetic library

At 2F00h–3350h sits a fixed-point library working with four 5-byte
registers. It is used by the sweep, the frequency path and the
self-tests and is the key to all further computation paths. All
registers are big endian, the least significant byte sits at the highest
address.

| Name | RAM | Use |
|---|---|---|
| X | 10h–14h | result, at the same time the TWS telegram 11h–14h |
| Y | 15h–19h | first operand, the frequency accumulator in a sweep |
| Z | 1Ah–1Eh | second operand, the step size in a sweep |
| W | 30h–34h | scratch, fSTART in a sweep |

### The routines

| Address | Effect |
|---|---|
| 31E4h | clear X, Y and Z, 15 bytes from 10h |
| 31EEh / 31F2h / 31F6h | clear X resp. Y resp. Z |
| 3206h / 3202h | move X to Y resp. to Z, clearing the source |
| 187Eh | copy five bytes, R0 to R1 |
| 18E4h | swap Y and Z |
| 3236h | shift Y right by one bit |
| 3252h / 3256h / 324Eh | shift Y resp. Z resp. X left by one bit |
| 326Bh | shift five bytes left by one nibble, i.e. BCD times ten |
| 32AEh | Y = \|Y − Z\|, C is set if Z was larger |
| 31D7h | compare five bytes, @R0 minus @R1, result in C |
| 2FA0h | X = Y · Z |
| 3107h | X = Y / Z, integer |
| 15FCh | normalise Y, R7 = exponent |
| 3313h | six BCD digits from 17h–19h to binary in 12h–14h |
| 32DBh | binary to BCD, digits from 17h ff. accumulated in 14h |
| 1F40h | shift Y by R5 bits, encoding see section 23 |

### Evidence

All routines called directly in the emulator, operands set, result read
back.

```
2FA0h   3 276 800 · 1 000        = 3 276 800 000     exact
        65 535 · 65 535          = 4 294 836 225     exact
        16 777 215 · 255         = 4 278 189 825     exact

3107h   35 413 032 960 / 1 000 000 = 35 413          exact
        4 278 190 080 / 100        = 42 781 900      exact
        2^35 / 3                   = 11 453 246 122  exact, rounded down

32AEh   |150 100 − 15 010| = 135 090, C = 0
        |15 010 − 150 100| = 135 090, C = 1

15FCh   135 090       -> R7 = 18, Y = 083EC80000h
        90 000        -> R7 = 17, Y = 0AFC800000h
        4 294 967 295 -> R7 = 32, Y = 0FFFFFFFF0h
        throughout Y_new = Y_old · 2^(36 − R7)
```

The multiplication carries up to 40 bits without loss, the division
delivers the quotient rounded down to an integer. The normalisation
makes sure that the top byte lies in the range 08h…0Fh.

---

## 25 Code coverage: what actually runs

The static analysis in `analyze2.py` finds 30 508 code bytes by
recursive descent. That leaves 13 637 bytes in the occupied ROM up to
AC70h that are not code. The question was whether reachable code hides
in there that the descent misses through indirect jumps.

### Method

`trace.js` drives the JavaScript core through a full cold start and then
through three rounds with all 23 front panel keys, both directions of
rotation and several detent counts, plus the operating modes and
waveforms stepped through — 86 million cycles. Every executed address is
marked and afterwards held against `analyze2.py`.

The run reaches 3 694 instructions, that is barely a quarter of the
statically known code. Sweep, modulation, self-test branches and the
interface are not part of it; so the trace can only show what runs in
addition, not what is dead.

### The find: 031Fh

Exactly one area is executed that the static analysis does not know:

```
031F  B2 74      CPL   2Eh.4        ; toggle DIAL LOCK
0321  C2 3C      CLR   27h.4
0323  C2 11      CLR   22h.1
0325  D2 0C      SETB  21h.4
0327  61 D5      AJMP  X03D5h
```

Not one jump instruction in the ROM points there. The place is reached
through the jump table at 0301h: `JMP @A+DPTR` with A = 2·index lands
for index 15 at 0301h + 30 = 031Fh — and there sits not the usual
`AJMP`, but **the handler itself**. The last table entry is inline,
which saves a jump. The heuristic in `analyze2.py` correctly ends the
table after 15 entries and loses the sixteenth in doing so.

That also documents what section 19 could only assume: key code 2Ah
leads through this place and toggles 2Eh.4, the DIAL LOCK bit.

### The big gaps are tables

| Area | Bytes | Content |
|---|---|---|
| 9F47–AC46 | 3 328 | waveform tables A047h, A447h, A847h |
| 44A7–4EBD | 2 583 | waveform tables 44A7h, 46A9h, 4AABh |
| 7752–7FC1 | 2 160 | command table |
| 803C–8870 | 2 101 | message pointers and message texts |
| 2398–2599 | 514 | table belonging to 2323h |

These five blocks make up 10 686 of the 13 637 bytes. The remaining
roughly 2 950 bytes are spread over 118 small areas which are almost
without exception tables interspersed between the routines — 2019h,
26ABh, 2724h, 167Eh, 2A81h, 5AABh and their like, all documented in the
sections above.

### The dead block 9AFFh–9BB8h

186 bytes that disassemble cleanly as code and make sense in content as
well:

```
9AFF  MOV   A,0Bh
9B01  CLR   TI ; MOV SBUF,A ; JNB TI,$
9B08  MOV   DPH,#0Fh ; MOVX A,@DPTR
9B10  RET
9B11  PUSH  04h ; PUSH 02h
9B15  MOV   A,#5Ah      ; I²C address
9B17  LCALL 5187h       ; start
9B1A  two bytes 4Bh/4Ch, then ten bytes from RAM 80h
9B3F  LCALL 51C1h       ; stop
9B4A  the same with 6Ah and ten bytes from RAM 15h
9B7A  MOV   DPTR,#0000h ; table read with MOVC
```

The address 5Ah occurs nowhere else in the ROM; only 70h for the display
and A0h for the NVRAM are documented. **In both firmware versions no
jump points at this block** — in V1.5 the same code sits at B2F2h and is
likewise without a caller. So it is dead code, most likely for a device
variant or left over from development.

### State

The method is established and has uncovered a real error in the static
analysis. For a complete classification the trace would also have to run
through the sweep, the modulation and the self-test branches; that is
still outstanding.

---

## 26 The NVRAM and its factory state

The PCF8570 (D305, I²C address A0h, battery backed) holds the current
setting and nine memory registers. The `PCF8570_image.bin` that came
with the project was **synthetic**, not read out of an instrument, and
falsified several measurements.

### How that could be shown

The cold start was run with four different NVRAM contents: the supplied
image, all 00h, all FFh and a random pattern. The three invalid cases
lead to **exactly the same** result — the firmware recognises the
content as invalid and writes its factory state:

```
00: 41 01 10 61 01 50 10 00 60 10 00 10 11 80 A1 00
10: 00 00 21 00 00 01 00 50 20 02 41 01 10 61 01 50
```

Compared with the old image, exactly **20 bytes** differ, namely at the
positions 24/25, 49/50, 74/75, 99/100 and so on — a pattern with
**period 25**.

The structure follows from that: **ten records of 25 bytes each**, which
are the current setting and the nine memory registers, and the last two
bytes of each record carry a check mark. The first record gets `20 02`,
the nine registers `50 E2`.

So the payload of the old image was right — only the check marks were
not. With a wrong mark the firmware loads the record shifted by one byte
position, and that is where the unreachable state decade 0 with mantissa
15010 came from.

### Consequences

Two documented findings went back to this and have been corrected:

- The rotary knob appeared to work in one direction only, see section
  19.
- `DIAL LOCK` appeared to be set after a cold start. In fact 2Eh = 60h,
  so the knob is free.

### The factory state

`PCF8570_image.bin` now contains the content produced by the firmware
itself; the old image sits next to it as
`PCF8570_image_old_synthetic.bin`. Characteristics of the factory
state:

| Quantity | Value |
|---|---|
| frequency 50h–52h | 50 10 00, i.e. decade 5, mantissa 1000 |
| 2Eh | 60h, DIAL LOCK cleared |
| 24h | 41h |

The cold start now runs through without errors, and the NVRAM stays
**unchanged** afterwards — the firmware accepts it. That is at the same
time the proof that the content is valid.

### The field layout, measured

Differential measurement: cold start, then adjust one parameter through
keys and the rotary knob and compare the NVRAM (`nvram.js`, `nv2.js`).
The **first** record is written every time.

| Adjusted | changed NVRAM offsets |
|---|---|
| rotary knob on the frequency | 02h, 03h, **07h**, 0Bh, 0Ch, 19h |
| decade up (key 0Bh) | 02h, 03h, **05h**, 0Bh, 0Ch, 19h |
| DC offset (key 18h) | 03h, **0Dh**, 19h |
| modulation frequency (key 20h) | 02h, 03h, 0Bh, 0Ch, **0Eh, 0Fh**, 19h |

The highlighted offsets hit the prediction **NVRAM offset + 4Bh = RAM
address** exactly: 05h→50h and 07h→52h for the frequency, 0Dh→58h for
the offset, 0Fh→5Ah for the modulation frequency.

The direct comparison confirms that for a contiguous block (`nv3.js`):

| Offset | 05h…0Ch |
|---|---|
| corresponds to RAM | 50h…57h |
| content | frequency (50h–52h), stop frequency (53h–55h), amplitude (56h–57h) |

Eight bytes agree there byte for byte — the parameters sit in the record
**in the order of the address table 08F2h**. In total 13 of the 25 bytes
match the RAM from 4Bh on; from offset 0Dh the assignment shifts by one,
so the record is not a plain memory dump but has fields of its own.

The offsets **00h–04h** change together on almost every adjustment (02h,
03h, 0Bh, 0Ch) — those are state and status bytes, not parameters.
Offset **19h** changes on every write operation; it sits behind the 25
bytes of the first record.

### The rule behind the check mark

The routine sits at **2EA1h**:

```
2EA1  MOV R5,#19h             ; 25 bytes
2EA3  MOV A,67h / ANL A,#0Fh
2EA7  JZ  X2EAAh
2EA9  DEC R5                  ; only 24 when an arbitrary curve is selected
2EAA  MOV R0,#30h             ; source pointer
2EAC  MOV A,#0AAh             ; start value
2EAE: ADD A,@R0 / INC R0 / DJNZ R5
2EB2  RET                     ; A = check mark
```

So a **plain byte sum with start value AAh** over 25 bytes — over 24
when an arbitrary curve is selected. Computed against the image:

```
record 0, bytes 00h..18h:  AAh + sum = 02h
mark at offset 19h      =  02h            -> matches
```

That makes the record **26 bytes long**: 25 data bytes and the mark
behind them. It also explains why offset 19h changes with every
adjustment — it is not the start of the second record but the mark of
the first.

The other nine records carry no matching mark; they are unwritten in the
factory state, which fits the origin of the image (section 26 above).
Their marks could only be checked after a memory slot has actually been
used.

### The device address has a check of its own

At the top end of the NVRAM, at **FEh/FFh**, sits the device address
with a differently formed mark (2F51h):

```
2F51  MOV R1,#30h / MOV R3,#02h / MOV R4,#0FEh
2F57  MOV A,#0A0h / LCALL X5212h    ; read two bytes from FEh
2F5C  MOV A,30h / ADD A,#55h / XRL A,31h
2F62  JNZ X2F69h                    ; mark wrong -> default 20h
2F6B  MOV 68h,A                     ; device address
```

Here the mark is `value + 55h`, checked by XOR — the same pattern as
with the arbitrary directory (section 32), only with a different start
value than for the records. If it does not match, the firmware falls
back to address **20h**, which explains the figure given in the service
manual.

**What stays open:** the fields from offset 0Dh on, individually.

**Earlier version:** the field layout inside a 25-byte record is only
partly assigned — frequency, stop frequency and sweep time are
recognisable, the rest is not. The rule behind the check mark is unknown
as well. Whoever needs this should read 5F2Eh and the routines around
2F7Ah, where A0h appears as an I²C address.

---

## 27 State bits: the balance

Section 15 measures what a flag does to the **display buffer**, by
starting the build at 3381h out of a state that has been set. That
leaves 74 flags without a recognisable effect. Many of them, however, do
not control the display but the **analogue assemblies**, and those are
only visible on the serial C-bus.

### Method

`flags.js` watches both at the same time: the display buffer 30h–43h and
the telegrams. `MOV SBUF,…` collects the bytes, a `MOVX @DPTR` with
DPH = 8nh terminates the telegram and names the strobe.

At rest the firmware sends nothing, so every run needs a stimulus. And
because a flag only takes effect in the matching operating mode, every
flag runs through **six profiles**. `MODE ▶` steps 2Ch one-hot along,
which is the lever for it:

| Profile | Way there | 2Ch |
|---|---|---|
| base | one detent, `WAVE ▶`, `AC` | 01h |
| am | 2× `MODE ▶`, detent, `MODPAR ▶` | 02h |
| fm | 3× `MODE ▶`, detent, `MODPAR ▶` | 04h |
| sweep | 6× `MODE ▶`, detent | 20h |
| burst | 8× `MODE ▶`, detent | 80h |
| memory | `STORE`, `RECALL`, detent | – |

### Result

**62 flags take effect in at least one profile.** Together with those
found statically that gives:

| | Flags |
|---|---|
| display, immediately (section 15) | 31 |
| display, through a precondition | 23 |
| in running operation, six profiles | 62 |
| **union, with a documented effect** | **75** |
| without any observed effect | 53 |

The two methods overlap but do not replace each other:

- **21 flags are only seen by the operating test**: 20h.3, 20h.5, 20h.7,
  21h.0, 21h.3, 22h.0, 23h.1, 24h.0–24h.3, 24h.6, 24h.7, 26h.1,
  29h.0–29h.4, 29h.7, 2Eh.6.
- **13 flags are only seen by the static test**: 20h.0, 22h.1, 2Dh.0,
  2Dh.2–2Dh.6, 2Eh.2, 2Fh.0–2Fh.3. In running operation the firmware
  overwrites them immediately; the display build reads them anyway.

Individual effects, read off the telegrams:

| Flag | Effect |
|---|---|
| 20h.7 | **starts the sweep**: STR8 with all 256 ramp values |
| 20h.3, 2Bh.7 | suppress STR1 and STR6 |
| 20h.5, 21h.0, 29h.3, 29h.7 | trigger a full re-output: STR3, STR4, STR5, STR7, STR9 |
| 21h.3, 29h.1 | waveform download through STR1 and STR2 |
| 24h.0–24h.3, 24h.6 | suppress the output — the parameter selection nibble |
| 24h.7 | STR1 `50 19`, STR6 `D0 07 0A 01` |
| 26h.1 | remote mode, effective in all modulation profiles |
| 2Ah.0 | STR6 → `00 00 20 01`, frequency zero, i.e. DC |
| 2Bh.4 | STR1 → `00 59`, arbitrary |
| 2Ch.5, 2Ch.6 | STR8 `00`, the sweep bits |
| 2Ch.7 | STR3 → `81 01`, burst |
| 2Eh.3 | remote; opens the receive path of the interface |
| 2Eh.4 | suppresses STR1 and STR6 — `DIAL LOCK` |

Two values confirm known facts independently: 20h.7 starts the sweep,
and in the listing 14A1h sets exactly this bit; 2Eh.4 prevents every
adjustment, as befits DIAL LOCK.

### The remaining 53

"No observed effect" does not mean "unused". Held against
`PM5139_Bit_Crossreference.md`, the 53 fall into three groups.

**Short-lived working flags** — often set, often tested, but consumed
inside one routine. Flipped from outside they do not survive the next
change of state:

| Flag | set | cleared | tested |
|---|---|---|---|
| 22h.4 | 56 | 38 | 50 |
| 22h.5 | 26 | 21 | 41 |
| 22h.7 | 16 | 12 | 32 |
| 22h.6 | 12 | 14 | 21 |
| 21h.7 | 9 | 16 | 17 |
| 21h.2 | 8 | 5 | 13 |
| 2Bh.0 | 10 | 1 | 14 |

22h.4 is by far the most-used bit of the whole firmware.

**Moderately used state flags**, 36 of them, with few setting places and
a handful of tests. They need a stimulus that the six profiles do not
offer — self-test, error cases, interface operation. 29h.6 stands out
with 27 tests against only three setting places.

**Flags that lead nowhere**, eight of them — and here a closer look pays
off:

| Flag | set | cleared | tested | Interpretation |
|---|---|---|---|---|
| 23h.4 | 0 | 0 | 1 | never set, only tested: **always zero** |
| 23h.5 | 0 | 0 | 3 | ditto |
| 29h.5 | 0 | 0 | 1 | ditto |
| 25h.1 | 1 | 1 | 0 | maintained, but **never evaluated** |
| 27h.6 | 3 | 0 | 0 | ditto |
| 27h.7 | 1 | 0 | 1 | almost dead |
| 22h.2 | 1 | 1 | 1 | almost dead |
| 26h.3 | 1 | 1 | 1 | almost dead |

Three bits are tested but set nowhere — the branches belonging to them
are unreachable. Two are maintained but never read. That fits the dead
code block from section 25: remnants of a variant or of development.

### State

Of 128 flags, **75 have a documented effect**, 7 are classified as
short-lived working flags, 8 as dead or almost dead. That leaves **36**
which need a stimulus outside the six profiles. The entry point for that
is the `PROFILE` table at the top of `flags.js`; a run over all 128 flags
and six profiles takes about ten minutes.

---

## 28 The interface card on I²C address 5Eh

### What the service manual says

Chapter 4.12, page 4-29, is present in the scan and describes the
hardware:

- IEEE-488 (unit 6, figure 124) or RS-232 (unit 7, figure 126), **only
  one of the two** can be fitted.
- The card carries an **interface processor of its own**, which converts
  the parallel IEEE-488 data or the serial RS-232 data onto the internal
  I²C bus. With IEEE-488 the program sits inside the processor as a
  mask-programmed PROM, with RS-232 in an EPROM of its own.
- The I²C bus is **galvanically isolated by optocouplers**, the card has
  its own +5 VA supply from 8 V AC, fused with F852.
- When the card has a message it pulls the line **INT on the eight-pin
  socket, pin 3**. *"During running sweep, this interrupt is disabled by
  an internal software command. In this case only commands to stop the
  sweep are accepted."*
- **RESET** sits on pin 8.
- Test program 5 names the defaults: IEEE-488 device address **20**,
  RS-232 with 9600 baud, 8 data bits, no parity; identification
  `PHILIPS,PM5138A,0,Vx.x`.

### The identification string in the ROM

It sits at the end of the occupied ROM, with a length byte in front of
it:

```
AC54  1A                                 ; 26 characters
AC55  "PHILIPS,PM5139,0,V1.3/0000" 00
```

In V1.5 it sits at B3AFh with `V1.5`. It is loaded at two places, 5CAFh
and 6D46h, each time with `MOV DPTR,#AC54h`.

### The I²C layer is software

Although the PCB80C652 has a hardware I²C unit, the firmware clocks the
bus itself over two port lines:

| Address | Task |
|---|---|
| 5187h | start condition, address with R/W = 0 (write) |
| 5194h | start condition, address with R/W = 1 (read) |
| 51A1h | send one byte, MSB first, then the ACK into the carry |
| 51C1h | stop condition |

`P1.6` is SCL, `P1.7` is SDA. The same routines also serve the display
(70h) and the NVRAM (A0h).

Two entry points are aimed at the card; they check beforehand whether
the bus is free and otherwise release it through 625Ah:

```
614A  MOV C,P1.7 / ANL C,P1.6 / JC 6153h / LCALL 625Ah
6153  MOV A,#5Eh / LJMP 5187h      ; start, write
6158  … the same …
6161  MOV A,#5Eh / LJMP 5194h      ; start, read
```

### Card detection

5F74h sends a start condition with the write address. If an ACK comes
back, **25h.7** is set — so the bit means "card fitted". Without an ACK
a stop follows immediately and 26h is set to zero.

### Measured initialisation

`iface.js` hangs an emulated slave at 5Eh onto the JS core
(`cpu.iface`) and logs every transaction. After a cold start with the
card answering:

```
25h.7 = 1        card detected

W E8
W EA
W 80 00
W EA
W E0
W C0 14
W E3
```

The block repeats, after which variants with `80 80` and `81 80` follow.
The decisive part is **`C0 14`**: 14h is 20 decimal, exactly the device
address from the service manual. It comes from RAM **68h**, where it
sits as BCD and is converted to binary at 61E8h.

### The command bytes

From the handler 5F2Eh–627Eh, sent through 61A2h (start, one byte, stop)
or directly:

| Byte | Where found | Note |
|---|---|---|
| 80h + bits | 6180h | bit 4 from 0Ch.4/4Eh.7, bit 0 from 20h.3, then 69h as the second byte |
| C0h + address | 6176h | device address, measured `C0 14` |
| E0h / E1h | 6166h | E1h when the value from 61E8h equals 1Fh |
| E3h | 5FA3h | completes the initialisation |
| E6h | 5F9Ch | only when 26h.1 or 26h.7 and 4Bh.7 are cleared |
| E7h | 6095h | request output |
| E8h, EAh | 5F81h, 5F86h | introduction |
| FFh | 6145h | termination |
| C1h, C3h | 6065h, 606Ch | coming from the card, set 69h resp. 0Ch.4 |

### The receive protocol

5FA9h reads a **status byte**:

- bit 7 set → control byte without a data block, continue at 6047h
- bit 6 → additional flag
- bits 0…4 → **length** of the data block

Then follow that many data bytes and finally a checksum. The firmware
forms it running, as

```
5FF0  ADD A,R7        ; R7 = intermediate value
5FF1  RR  A           ; pure rotation, without carry
5FF2  MOV R7,A
```

that is `r ← ror8((byte + r) mod 256)` over all bytes including the
status byte, and compares at the end with `XRL A,R7`.

The payload lands in the **upper RAM from 80h on**; 6011h limits it to
BFh, so the buffer is 64 bytes. Belonging to it are **4Ch** as the write
pointer, **4Ah** as the counter and **4Bh** as the length and status
register.

### The trigger

The handler hangs on **P3.2, that is INT0** — the line INT from the
eight-pin socket, pin 3, that the manual names:

```
62DA  MOV C,25h.4
62DC  ORL C,/P3.2         ; card reports, active low
62DE  ORL C,25h.5
62E0  ORL C,24h.6
62E2  JNC 62EDh
62E4  LCALL 5F2Eh
```

This place, however, is only reached in **remote mode**: 62B1h requires
26h.1, and the entry at 0026h requires 2Eh.3.

### The device address in 68h: BCD in V1.3, binary in V1.5

The two versions store the address **differently**. It first stands out
at a constant — V1.3 tests `CJNE A,#31h`, V1.5 `CJNE A,#1Fh` — and looks
like a bug. It is not.

**The defaults:**

```
V1.3  3C6A  MOV 68h,#20h        ; BCD 20
V1.5  3C38  MOV 68h,#14h        ; binary 20
```

**Before sending:**

```
V1.3  6166  LCALL 61E8h         ; 68h from BCD to binary
      6169  MOV   R3,A
      616C  CJNE  A,#1Fh,…      ; comparison with 31, after the conversion

V1.5  633B  MOV   A,68h         ; directly, no conversion
      633D  MOV   R3,A
      6340  JNB   25h.0,…       ; a state bit instead of a value comparison
```

So V1.3 holds the address as BCD and converts it only when sending; V1.5
holds it in binary and sends it unchanged. That is why 31h appears in
V1.3 everywhere the raw content of 68h is tested, and 1Fh where it has
already been converted — and 1Fh throughout in V1.5.

**Measured**, cold start with the card answering:

| | 68h after the start | to the card |
|---|---|---|
| V1.3 | 20h | `C0 14` |
| V1.5 | 14h | `C0 14` |

Both send the same address 20. The change is not visible from outside.

In exchange V1.5 brings a **migration**, at 3C1Fh:

```
3C27  MOV A,68h / ANL A,#0E0h
3C2B  JNZ 3C44h              ; upper bits set -> an old BCD value
3C38  MOV 68h,#14h           ; move it to binary 20
```

Valid binary addresses lie between 0 and 31, so below 20h; a BCD value
such as 20h is caught by the test on `E0h` and replaced. That way an
NVRAM from a V1.3 instrument survives the version change.

The fact that 61E8h found no counterpart when mapping onto V1.5
(section 29) explains itself with that: the routine does not exist there
any more.

### The receive path, measured

The handler hangs on two conditions, both of which have to be met:

```
0026  JNB 2Eh.3,002Ch     ; remote mode
0029  LJMP 62AFh
62B1  JNB 26h.1,62C9h     ; remote flag of the interface
62DA  MOV C,25h.4
62DC  ORL C,/P3.2         ; card reports, active low
62E2  JNC 62EDh
62E4  LCALL 5F2Eh
```

There is a second path that manages without an interrupt and hangs on
the **device address**:

```
0EA1  MOV   A,68h
0EA5  CJNE  A,#31h,0EAAh   ; exactly 31h?
0EA8  SETB  25h.0
0EAA  JNB   25h.7,0EB9h    ; card present?
0EB3  LCALL 5F2Eh
```

With 2Eh.3 and 26h.1 set the handler starts up, and an injected packet
comes through completely:

| sent | RAM 11h ff. afterwards |
|---|---|
| `05 41 42 43 44 45 4E` | `41 42 43 44 45` |
| `03 11 22 33 74` | `11 22 33` |

The status byte names the length, exactly that many payload bytes
follow, and the last byte is the checksum — it is not stored. The
checksums 4Eh and 74h come from `r ← ror8((byte + r) mod 256)` over the
status byte and the payload; the firmware accepts both packets, which
confirms the formula.

The payload lands **at the address that sits in 4Ch** — 11h in the
measured case. 6011h limits the loop upwards to BFh; the firmware only
sets 4Ch = 80h in a different branch, at 6022h.

### How the instrument gets into remote mode

The receive path requires 2Eh.3 and 26h.1. The instrument sets both
itself, through a chain of four links.

**1. The device address has to be 31.** 0EA1h tests 68h and only enables
in that case:

```
0EA1  MOV   A,68h
0EA5  CJNE  A,#31h,0EAAh     ; BCD 31, 1Fh in V1.5
0EA8  SETB  25h.0
0EB3  LCALL 5F2Eh            ; handler
```

In IEEE-488, address 31 is not a valid participant address but the code
for "not addressed"; here it stands for serial operation. With address
20 the branch does not start up.

**2. A stimulus has to kick off the reload cycle.** 0EA1h hangs on
29h.5, tested at 092Bh. The bit is not set individually but in
`ORL 29h,#2Fh` at 065Ah and 3B96h — both of them restorations of the
instrument state, for instance after `RECALL`.

*Note:* `PM5139_Bit_Crossreference.md` lists 29h.5 with zero setting
places, because it only counts individual bit instructions and misses
`ORL` on the whole byte. The bit certainly is set.

**3. The card sends E3h.** In the control byte branch two commands sit
side by side:

```
6130  CJNE A,#0E2h,6137h     ; E2h -> LOCAL
6133  JB   26h.1,612Dh       ;        clear 26h.1
6137  CJNE A,#0E3h,6145h     ; E3h -> REMOTE
613A  JNB  26h.1,613Eh
613E  SETB 26h.1
```

**4. 666Ah sets 2Eh.3.** The place is called from 1B37h, reads the
status register and decides in both directions:

```
666A  LCALL 517Dh
666D  JB ACC.0,667Dh         ; an event is pending
6670  JB 26h.2,667Dh
6673  CLR 2Eh.3              ; otherwise back to LOCAL
667D  LCALL 5F2Eh
6680  MOV C,26h.1 / ANL C,/2Eh.3
6686  SETB 2Eh.3             ; enter remote
```

After that the entry at 0026h applies: `JNB 2Eh.3,002Ch` leads the main
loop to 62AFh, and the receive path is open.

**Measured** — with the address set through the `ADDR` key, not by hand:

```
after cold start    68h=20  0Bh=11  25h.0=0  26h.1=0
after ADDR          68h=20  0Bh=4A  25h.0=0  26h.1=0
after turning up    68h=31  0Bh=4A  25h.0=1  26h.1=1
```

As soon as address 31 is reached, 25h.0 enables, the handler starts up,
and the card's E3h sets 26h.1. With E2h, 26h.1 stays cleared; with
address 20 the branch does not start up at all.

**A pitfall in this:** if 68h is set to 31h *by hand* after the cold
start instead of using the key, the firmware crashes — it runs into the
command table at 7752h, 553 560 steps far in the experiment, and the
stack pointer ends up at 23h instead of 6Ah. The reason is the same as
with the NVRAM image in section 26: a state the instrument itself never
produces. Through `ADDR` everything stays clean, the command table is
not entered a single time. So a first measurement with a hand-set
address showed an apparently set 2Eh.3 — that was an artefact of the
crash, not remote mode.

**What was still missing:** 2Eh.3 stays clear. The switching place 666Ah
hangs on 1B37h, which lies in the wait loop at 1B2Eh; 1B0Ch leads there,
and according to 1A58h that is only reached out of the sweep aftermath
when
`6Ah & 3` equals 2 and 2Fh.2 is set. In the experiment 6Ah stayed at 09h
and 2Fh at 00h, 1B0Ch never started up. Which operating mode establishes
this wait state is the next step — but the way there is narrowed down.

### How 2Eh.3 is set — measured

The last open step of remote operation is settled. The decisive place is
the wait loop at 1B2Eh:

```
1B2E  LCALL X517Dh        ; read the status register
1B31  JNB   ACC.0,X1B37h  ; no event -> check for switching
1B34  JB    P3.2,X1B44h   ; P3.2 = INT0, active low from the card
                          ; falls through to 1B37h when the card reports
1B37  LCALL X666Ah        ; REMOTE_SWITCH
```

**The trigger is P3.2 alias INT0**, not ACC.0. Measured with
`remote.js`, entering at 1B0Ch, slave at 5Eh:

| Case | 1B37h | 666Ah | **2Eh.3** | 26h.1 |
|---|---|---|---|---|
| without INT0 | 0 | 0 | 0 | 0 |
| INT0 active, no card | 6272 | 6272 | 0 | 0 |
| **INT0 active, card answers E3h** | 4131 | 4131 | **1** | **1** |
| INT0 active, card answers E2h | 4486 | 4486 | 0 | 0 |

With that the complete chain stands:

1. The instrument is in the wait loop 1B2Eh — reached through 1B0Ch,
   which is jumped to from the sweep aftermath at 1A58h.
2. The interface card pulls **INT0** to ground.
3. 1B37h calls **666Ah**, which queries the card.
4. If it answers **E3h** (REMOTE), **26h.1 and 2Eh.3** are set; with
   **E2h** (LOCAL) neither happens.
5. After that the remote operation runs through 62B1h, which first tests
   26h.1 and is reached from 1BBAh, 3C8Dh, 63D7h and 6454h.

**Out of the normal main loop nothing happens**: over eight million
steps with INT0 permanently active, neither 62DCh nor 62AFh nor 1B37h is
reached. The state 1B0Ch is a precondition — which confirms the earlier
assumption that the entry hangs on the sweep aftermath.

**Model limit of the emulator:** `CPU.prototype.xr` always returns 11h
or 01h for the status register, so bit 0 is always set. The branch
through `JNB ACC.0` at 1B31h is therefore never reachable in the
emulator; only the path over P3.2 was measured. On the instrument ACC.0
means "event pending" according to section 5 and is zero at rest — so
that branch should apply there as well.

### A bug in the I²C model

That nothing arrived at first was down to the emulator, not the
firmware. The ACK directly after the **read address** comes from the
slave; `core.js` instead evaluated the level the master leaves on the
line and derived `mack = false` from it — after which no byte was ever
fetched. With the NVRAM this never showed, because `mack` was still set
there from an earlier transaction.

The correction applies **only to the interface card**. The display and
the NVRAM keep their previous behaviour so that the earlier measurements
stay valid; a general fix shifted the NVRAM pointer by one byte and
changed the display buffer. Counter-check after the change: cold start,
display buffer and bitmap balance unchanged, the NVRAM is not touched
after the start.

### State

Hardware, addressing, card detection, initialisation sequence, command
set, packet format, checksum and the **receive path** are documented and
measured, the device address additionally checked against the service
manual.

**What is missing:** how the instrument gets into remote mode by itself
— 2Eh.3 is set at 2DAAh, 6298h, 6686h and 6B30h, and which path applies
in operation is open. Likewise the meaning of the individual command
bytes and of the send direction from 60A8h on.

**Emulator:** `core.js` knows an optional slave at 5Eh (`cpu.iface`) and
INT0 on P3.2 (`cpu.ifaceInt`). Without both, the core behaves as before.
**This has not been carried over into the Python core.**

---

## 29 The annotated disassembly

The raw listing from `analyze2.py` has 23 000 lines without a single
name. Everything in this document, however, can be carried back into the
listing as a symbol. Two files do that:

| File | Content |
|---|---|
| `symbols.py` | the symbol table: routines, RAM, bits, strobes, I²C addresses |
| `annotate.py` | inserts it into the listing, produces `PM5139_V13_annotated.asm` |

### Principle

Only what is documented is taken in — through the listing, a measurement
in the emulator or the service manual. Every routine entry names the
section where the evidence sits. Assumptions get no name.

The listing itself is **not changed**: addresses, bytes and mnemonics
stay character for character, the explanation is added on the right.
That keeps the file diffable against the original. The check belongs to
the tool: 17 491 code lines, not a single one changed in the original
part.

### What is inserted

```
;----------------------------------------------------------------------------
; DIV_XYZ
; X = Y / Z, integer, rounded down
; see PM5139_Hardware_Reference.md, section 24
;----------------------------------------------------------------------------
3107  7815       MOV   R0,#15h              ; 15h = Y0
3109  123338     LCALL X3338h               ; BIT_LENGTH
310C  504E       JNC   X315Ch
310E  EC         MOV   A,R4
3110  781A       MOV   R0,#1Ah              ; 1Ah = Z0
…
311A  F510       MOV   10h,A                ; 10h = X0
```

and for the interface:

```
5F74  12614A     LCALL X614Ah               ; IFACE_START_W
5F77  5003       JNC   X5F7Ch
5F79  0251C1     LJMP  X51C1h               ; I2C_STOP

L5F7C:
5F7C  D22F       SETB  25h.7                ; 25h.7 = IFACE_PRESENT
```

What gets annotated: jump targets with a known name, direct RAM
addresses, named bits, `MOV DPH,#8nh` with the corresponding strobe and
its assembly, and the three I²C addresses. The file header carries the
register convention and the RAM ranges.

### Size

The symbol table currently holds 147 routines, 34 RAM symbols, five RAM
ranges, 31 named bits, ten strobes and three I²C addresses. That gives
145 routines with a header comment and 3 826 annotated lines in the V1.3
listing.

### Taking V1.5 along

`mapv15.py` maps the addresses measured on V1.3 onto V1.5, in two
stages:

1. **Structural comparison** as in `seqdiff.py`: disassemble both ROMs,
   reduce the instruction sequences to tokens — relative jump distances
   instead of absolute targets — and compare them with
   `SequenceMatcher`. The mapping falls out of the matching blocks
   directly; 13 937 instructions are assigned this way.
2. **Signature search** as a fallback for tables and data the
   disassembler does not recognise as code. Only what occurs exactly
   once is adopted.

Two addresses are filled in by hand because neither method applies: the
checksum at B3CAh and the identification string at B3AEh.

**130 of the 147 symbols** can be mapped this way. The most frequent
shifts are +159, +142 and +135 bytes — V1.5 inserted at several places
rather than shifting uniformly. Seventeen routines stay unmapped because
V1.5 changed them so heavily that the comparison does not bite: the DIAL
LOCK handler, both parameter loaders, the checksum routine, the
parameter limit check and several interface routines.

The table is produced with `python3 mapv15.py --write` into
`symbols_v15.py`, after which `python3 annotate.py 15` delivers the
annotated V1.5 listing with 128 routine headers.

### A find from the comparison

`DISPLAY_BUILD` differs in one constant:

```
V1.3  338A  MOV   A,68h        V1.5  3429  MOV   A,68h
      338C  CJNE  A,#31h,…           342B  CJNE  A,#1Fh,…
```

Both are the check of the device address in 68h — the same place the
receive path of the interface hangs on at 0EA5h. Verified in section 28:
this is **not a bug fix but a change of format**, and both versions are
correct in themselves.

### Complete coverage

After adding the self-tests (section 7), the load routines (section 6)
and the remote control parts worked out most recently, the V1.3 ROM
contains **no contiguous code block without a name any more**. The last
five were:

| Area | Bytes | What it is |
|---|---|---|
| 4EBEh–4FF5h | 312 | checks which parameter the digit pointer 0Bh selects; five entry points from the user interface |
| 2157h–21FFh | 169 | helper for the table access at 2200h in the arithmetic library |
| 1032h–10C7h | 150 | **bit reversal**: ACC.0 against ACC.7 and so on, then STR9 |
| 3029h–3050h | 40 | multiply X by the byte in R6, carry into R3 |
| AC47h–AC53h | 13 | set two display cells and send them, in the reset sequence at 3AA8h |

The most interesting of these is **1032h**. The routine reverses the bit
order in the accumulator before the byte goes out through SEND_STR9 —
the shift registers expect the bits in reverse order. Anyone rebuilding
the C-bus telegrams has to take that into account.

**AC47h** runs immediately before the checksum routine 3AABh and sets
two display cells; it is the display shown during the self-check at
power-up.

### Limits

- Names exist only where something is documented. Large parts of the
  listing stay unnamed — that is deliberate, not an omission.
- For V1.5 the names only hold as far as both versions agree; for the
  routines that differ in content the name is a hint, not a guarantee.
- Additions are not made in the listing but in `symbols.py`; after that
  run `mapv15.py --write` and `annotate.py` again.

---

## 30 Reading the schematics

The OCR text of the service manual reproduces the running text well, but
the **schematics** only as disconnected fragments of signal names. The
schematics have to be looked at as images.

### How

```
pdftoppm -f <page> -l <page> -r 400 -png pm5138A_service_manual.pdf out
```

400 dpi gives about 3200 × 4300 to 5800 × 4300 pixels. That is too large
to take in at a glance, so cut it into overlapping tiles — two columns,
three rows, 80 to 90 pixels of overlap each — and look at the tiles one
at a time. At this resolution part numbers, pin numbers and signal names
are reliably legible.

### Which page shows what

Determined through the signal names the OCR picks up despite everything:

| PDF page | Content | Marker |
|---|---|---|
| 121 | unit 2, CPU (fig. 106) | PCB80C652, address latch, EPROM, EEPROM |
| 122, 123 | unit 2, TWS (fig. 107) | STR1, STR6, STR7, STR2, STR3 |
| 127, 128 | unit 3, amplitude controller (fig. 109) | STR9, D101/D102, signals S1…S5 |
| 133, 134 | unit 3, attenuator (fig. 111) | relays K401…K404, S2…S5 |
| 136, 137 | unit 3, DC generator (fig. 112) | STR7, D301, DAC-08, relay K301 |
| 142, 143 | unit 4, RAM and pulse generator | STR1, STR2, STR3, STR5 |
| 151, 152 | unit 4, amplitude modulator | STR3 |
| 157 | unit 4, modulation oscillator | STR2 |

### What is already established from them

**All strobe receivers are 74HCT4094** — an 8-bit shift register with an
output latch of its own. The parts list carries them as D101–103, D126,
D301 and D307. That confirms the bus model from section 3 in hardware:
SD shifts the bits, SC clocks, and the strobe transfers them into the
outputs simultaneously.

**The DC generator, fig. 112:**

```
STR7 ──> D301 (74HCT4094) ──8 bits──> N302 (DAC-08EN) ──> N301 (TL072) ──> output
                                      ±VREF, adjustment R302/R303/R304
S1 (from the amplitude controller) ──> V314 ──> relay K301, two changeover contacts
```

So the DC component is an **8-bit DAC value**, and the range position is
switched by a relay that the DC generator does not drive itself — the
amplitude controller does, over the line S1. That fits the measured
formula `1Dh = 64h ± W` from section 22: 64h lies in the middle of the
eight-bit range.

**The amplitude controller, fig. 109:** STR9 goes to D102, a 74HCT4094P;
the manual additionally names D101. The control lines **S1 to S5** come
from here — S1 switches the DC relay K301, S2 to S5 the attenuator
relays K401 to K404 on fig. 111. That also makes the open question of
the attenuator thresholds addressable: they are bits in the STR9
telegram, not a computation.

**The CPU, fig. 106:** confirms independently what section 28 derived
from the listing — the line **INT** of the interface (X809 pin 3) sits
on **INT0, pin 12** of the processor. Also visible: D306 = 27C512 as the
program EPROM, D310 = X28C256 as the arbitrary EEPROM, D307 = HCT4514 as
the strobe decoder, and an **optional** device
D312 = X24C16P, a 2K EEPROM on the I²C — a section of its own on that
below.

The table in fig. 106 also names the difference between the series:
the PM5136 works with ±16.5 V, the PM5138A with ±26 V.

### The optional X24C16 — and what it is not

Clearly visible in the detail: at D312, **A0, A1 and A2 all sit on
ground**, SCL and SDA hang on the same bus as the display and the NVRAM,
and the jumper X13 sits next to it.

According to the data sheet the slave address of the X24C16 is fixed
`1010` plus **three bank bits**, with which the device switches between
its eight 256-byte banks; the pins A0…A2 are unused and have to go to
VSS. So the device occupies **the whole address block A0h…AEh**.

Two things follow from that:

- **The X24C16 cannot be the device at 5Ah.** An earlier assumption in
  that direction was wrong.
- **The X24C16 and the PCF8570 exclude each other.** The NVRAM answers
  on A0h, and the X24C16 would cover the same block completely. So the
  "OPTIONAL" in the schematic is not an extension but an **alternative
  fit** — an EEPROM instead of battery-backed RAM.

### Who sits on 5Ah, then?

Looking at the address allocation puts the dead block from section 25
into a new light:

| Address | Device type | Bank | Device |
|---|---|---|---|
| 70h | 0111 | 000 | PCF8576, display |
| A0h | 1010 | 000 | PCF8570, NVRAM |
| **5Eh** | **0101** | **111** | interface card |
| **5Ah** | **0101** | **101** | dead code at 9AFFh |

5Ah and 5Eh lie in the **same device type block**, differing only in the
bank bits. So the dead code very probably talks to **the same type of
device as the interface card**, only addressed differently — a second
card, another variant or a factory instrument.

What it does fits that: two short telegrams, ten payload bytes each,
once from the receive buffer at RAM 80h, once from the arithmetic
register at RAM 15h. That is not a useful function but looks like a
**diagnostic output** — send the buffer and the register contents to a
device that is not connected in the production configuration.

### The amplitude controller, fig. 109 in detail

Three lines come in from unit 2 through X801: **pin 7 = SC**,
**pin 8 = SD**, **pin 9 = STR9**. They go to two shift registers D101
and D102, both 74HCT4094P, and to a converter **N101 = AM6012F, a 12-bit
DAC**.

Read off the tiles:

| Device | Pin | Q | goes to |
|---|---|---|---|
| D101 | 4, 5, 6, 7, 14, 13, 12, 11 | Q1…Q8 | DAC bits 12…5, the upper eight |
| D102 | 4, 5, 6 | Q1…Q3 | the lower DAC bits |
| D102 | 7 | Q4 | **S1** |
| D102 | 14 | Q5 | **S2** |
| D102 | 13 | Q6 | **S3** |
| D102 | 12 | Q7 | **S4** |
| D102 | 11 | Q8 | **S5** |

At D101 **pin 9 (QS) is unused**, while **pin 10 (QS')** carries on to
D102 — more on that below.

Where the five lines lead is settled with that:

| Line | Destination | Effect |
|---|---|---|
| S1 | V314 → relay K301, fig. 112 | range position of the DC generator |
| S2…S5 | relays K401…K404, fig. 111 | attenuator, 0/20/40 dB and Zo 50 Ω / 600 Ω |

That answers the old question about the "attenuator switching
thresholds": they are **no thresholds and no computation, but five bits
in the STR9 telegram** that switch relays directly.

### The attenuator, fig. 111

The four lines arrive as a bundle "from U3, Amplitude Controller" and
each switches a transistor that pulls a relay. All relays are of type
**TQ2, 5 V**, the drivers **BC547B**.

| Line | Driver | Series resistor | Relay | Label in the schematic |
|---|---|---|---|---|
| **S2** | V401 | R442, 4k64 | **K401** | `20 dB (for 40dB)` |
| **S3** | V402 | R443, 4k64 | **K402** | `20 dB` |
| **S4** | V403 | R444, 4k64 | **K403** | `50/600 ohms` |
| **S5** | V404 | R447, 4k64 | **K404** | output matching |

So the attenuation is a pure bit combination: 0 dB with both relays at
rest, 20 dB through one, 40 dB through both in series — the label
`20 dB (for 40dB)` at K401 says exactly that. The output impedance
depends on S4 alone.

Two observations on the side:

- **S5 additionally drives an indicator.** Next to V404 sits **V405**,
  designated `LED driver` in the schematic; through R446 it feeds the
  connection X810 pin 1 to `to U5, Display`. So the position of this
  relay is shown on the front panel.
- Attached to K404 are **R438 (46E4) and C404 (33p)**, both marked with
  `*` and listed in the footnote as **`not mounted`** — a matching
  network that was foreseen but not fitted.

That closes the chain from the firmware to the relay: the first of the
two STR9 bytes lands in D102, whose outputs Q4…Q8 are S1…S5, and S2…S5
switch K401…K404 directly.

### The amplitude modulator, fig. 117

On unit 4 the bus lines are named differently than on unit 3: the clock
is **SC1**, the data run on **E**. The strobe stays STR3.

```
STR3 ──> D144-A (HCT4094) pin 1  (C2)
SC1  ──> D144-A pin 3  (C1)
E    ──> D144-A pin 2  (1D)
+5V  ──> D144-A pin 15 (EN3)
```

| D144 pin | Q | goes to |
|---|---|---|
| 4, 5, 6, 7 | Q1…Q4 | control inside the modulator, among other things the analogue multiplexer **D143-A (HCT4052)** |
| 14 | Q5 | **U11** |
| 13 | Q6 | **U10** |
| 12 | Q7 | **U9** |
| 11 | Q8 | **U12** |

So the output designations do **not** run in ascending order: U11, U10,
U9, U12. They are the counterpart of S1…S5 on unit 3 — control lines to
other assemblies.

The two signal inputs come from the neighbouring assemblies:
**B1 "from U4, Burst Logic"** and **M1 "from U4, Ampl. Mod."**. The
HCT4052 selects between them; it runs on ±4.9 V, which limits the
analogue signals cleanly. The amplification is done with **N145
(LF356N)** and **N147 (TL072)**.

### The pulse generator, fig. 118 — and the resolution for STR3

The second device on STR3 sits here: **D126-A, likewise an HCT4094.**
Its inputs come as a bundle "from U4, RAM":

```
STR3 ──> D126-A pin 1  (C2)
SC1  ──> D126-A pin 3  (C1)
SD1  ──> D126-A pin 2  (1D)
+5V  ──> D126-A pin 15 (EN3)
```

The eight outputs feed **N127, a DAC-08EN**, and the branch is labelled
in the schematic with **`Duty Cycle for fc > 20 kHz`** and
**`Asymmetry`**. That is exactly the quantity section 22 computed for
STR3 as symmetry — here as an 8-bit DAC value.

**The cascade runs across the assembly boundary.** A line **E** leads
from the pulse generator `to U4, Amplitude Modulator` — and **E** is the
data input of D144 there. So the two registers on STR3 are in series
after all, just across two parts of the circuit:

```
SD1 ──> D126 (pulse generator, asymmetry)  ──E──>  D144 (amplitude modulator)
STR3 and SC1 go to both in parallel
```

So the same pattern holds as with STR9: the byte sent **first** travels
through and ends up in **D144**, the one sent **last** stays in
**D126**. An earlier conclusion in this document — that the two
registers on STR3 were not chained because they sit on different
assemblies — was therefore wrong.

The differing line names explain themselves with that: **SD** is the
data line from the bus, **SD1** its branch to the pulse generator, **E**
the pass-on branch to the modulator. **SC1** is the shared clock on unit
4.

### Further inputs of the pulse generator

| Signal | Origin |
|---|---|
| **B4** | "from U2, TWS (MSB)" — the most significant bit of the TWS |
| **A2** | "from U4, fig. 116", the frequency multiplier |
| **PGS** | "from U2, CPU" |
| **B5** | "from U4, Burst Logic" |
| **U9** | from the amplitude modulator; switches relay **K810** through V172 |
| **B3** | output to the burst logic, labelled `fc > 20 kHz` |

So the schematic confirms what chapter 3 describes: the pulse generator
forms its square wave from **B4, the MSB of the TWS**, and takes over
setting the duty cycle above 20 kHz. The U lines from the amplitude
modulator switch relays in the pulse generator in the process — K810
through U9, others through the neighbouring branches.

### The burst logic, fig. 120

The core is labelled in the schematic: an **`11 bit down counter`**,
made of cascaded **HCT191** — D117-A, D118-A and a third one for the
remaining bits. It is loaded from two shift registers:

```
STR4 ──> D121-A (HCT4094)  and  D122-A (HCT4094)
SC   ──> both, clock
```

Both come "from U4, RAM". Two registers of eight bits give 16, of which
**eleven** go into the counter.

**That confirms the measured burst formula independently.** Section 22
derived from the emulator that the cycle count is limited at **2000**,
and chapter 3 of the manual gives `N = 1 ... 2000`. An eleven-bit
counter holds 2048 values — so the limit is given by the hardware and
the firmware stays just below it. The measured **two bytes per STR4
telegram** match the two registers as well.

The inputs are **B3** "from U4, Pulse Gen." — the line `fc > 20 kHz`
from fig. 118 — and **B4** "from U4, RAM (MSB)".

### The modulation oscillator, fig. 119

This is where the most registers hang on one strobe: **STR5 transfers
six bytes**. The assembly strip at the bottom edge of the sheet names
all devices of the page exhaustively:

```
D130-P LIC016A (24)   D131-P 27C64 (28)    D132-P HCT574 (20)
D138-P HCT4094 (16)   D139-P HCT4094 (16)
D140-P HCT4052 (16)   D141-P HCT4052 (16)
```

So there are **exactly three serial receivers**: the TWS D130-A
(designated PCF1842P in the symbol, LIC016A in the strip — a Philips
house number for the same chip) with its own inputs SCI/SDI/STRI, and
the two HCT4094s D138-A and D139-A. No further HCT4094 is fitted on the
sheet.

The second sine chain also sits on the same sheet, labelled explicitly
that way in the schematic: **TWS** D130-A → **SinePROM** D131-A (27C64,
8K×8) → **latch** D132-A (HCT574) → **DAC** N133 (DAC-08EN) →
**low-pass**.

This is where the EPROM "SINUS 1.1" that was read out sits. That is
**confirmed**: the device was removed as the "SinePROM" from **unit 4**,
page 158 in the PDF (the same drawing as 157, with the assembly strip).
The widths fit: the TWS puts out a 10-bit address, the DAC-08 takes 8
bits — and the dump contains 1024 bytes of sine over one full period, 8
bits wide, the rest unerased (section 31). It is also the only 27C64 in
the entire set of schematics; `pdftotext` finds "SinePROM" only on pages
157 and 158.

That also disposes of the earlier note "DAC board, unit 3" — the
assembly is indeed called a DAC chain, but it belongs to unit 4,
modulation oscillator.

**The wiring, traced point by point in the 800 dpi rendering** (the
segments were extracted from the image with `lines.py` instead of being
eyeballed — with five parallel lines 90 pixels apart that is necessary):

```
SC1   ──> D130 pin 6 (SCI)   and  D138 pin 3 (C1)   and  D139 pin 3 (C1)
STR5  ──> D130 pin 7 (STRI)  and  D138 pin 1 (C2)   and  D139 pin 1 (C2)
SD1   ──> D139 pin 2 (1D)
D139 pin 10 (QS') ──> D138 pin 2 (1D)
D138 pin 10 (QS') ──> D130 pin 8 (SDI)
```

On both HCT4094s **pin 9 (QS) ends free**, the data are passed on
through **pin 10 (QS')** — the same pattern as with D101/D102 on STR9
and with D126/D144 on STR3. So the chain is

```
SD1 ──> D139 ──> D138 ──> D130 (TWS)
```

**The six bytes, from the listing.** The central output routine has its
own entry point for every strobe; STR5 is the only one that sends twice,
because the six bytes come from two different registers:

```
L0E69:  MOV R4,#04h        ; four bytes
        SETB F0            ; marker: do not terminate yet
        ACALL X0E88h       ; R0=14h -> sends 14h,13h,12h,11h, then RET through JBC F0
        MOV DPH,#05h       ; strobe 5
        MOV R0,#19h
        MOV R4,#02h        ; two more bytes
        SJMP X0E8Ah        ; sends 19h,18h; F0 is now 0 -> strobe
0E98:   ORL DPH,#80h  /  MOVX @DPTR,A     ; DPH=85h, STR5
        MOV DPH,#80h  /  MOVX @DPTR,A     ; idle output
```

They are sent in the order **14h, 13h, 12h, 11h, 19h, 18h**. In a shift
register chain the byte sent first travels furthest, so:
| Send order | Byte | ends up in | Meaning |
|---|---|---|---|
| 1st–4th | 14h, 13h, 12h, 11h | **D130**, TWS | 32-bit frequency word, LSB first |
| 5th | 19h | **D138** | eight bits to the DAC N135 (AD7523JN) |
| 6th | 18h | **D139** | eight control bits to the multiplexers D140/D141 |

Three independent pieces of evidence support the assignment:

1. **The amount sent matches the chain length.** 4 bytes TWS + 8 bits +
   8 bits = 48 bits = six bytes. That the TWS is 32 bits deep is
   confirmed by the entry point of the *other* TWS: `L0E54` likewise
   sends exactly four bytes from 14h…11h for **STR6** (D331 in unit 2).
2. **19h is a numeric value, 18h a bit pattern.** Before every call of
   0E69h, 19h is loaded from a table conversion (`X0F45h` with R0=5Ch
   resp. 5Eh, partly `RL A`), while 18h is handled bit by bit:
   `ORL 18h,#08h`, `ANL 18h,#0F7h`, `MOV 18h,#14h`. A DAC value and a
   switch register — exactly the roles of D138 and D139.
3. **18h comes from an operating-mode table.** `X0F69h` reads 2Ch
   (operating mode, one-hot), forms the bit number, adds 8 if 2Fh.5 or
   2Fh.4 is set, and fetches the byte from the 16-byte table at
   **0F83h**: `D0 90 90 14 14 D0 D0 E4 D0 50 50 50 50 F0 F0 C0`. It then
   sets bit 1 from `29h.7 ∧ 2Ch.2`. That is what a register looks like
   that drives analogue switches, not one that carries an amplitude.

The outputs confirm this in the schematic: **D138 Q1…Q8 (pins 4,5,6,7,
14,13,12,11)** go directly to **N135 AD7523JN pins 4…11**, whose VREF
comes from the amplifier N134-A "Mod.freq. amplitude"; **D139** feeds the
two HCT4052s D140/D141, which switch between "~ for AM/FM" and "TTL for
Burst/Gate/PSK".

Further signals: **2 MHz** "from U2, Clock Gen." on D130 pin 11 (FCI) as
the time base — matching chapter 3, which assigns the 2 MHz explicitly
to the modulation oscillator — and **M0** "from U4, Burst Logic" on
D140. D130 pin 9 (STI) hangs on the fifth conductor of the bundle, pin
10 (ETI) is open.

### The entry table 0E54h–0E84h: byte count per strobe

The complete table fell out while following STR5. Every strobe has an
entry point of its own that only sets `R4` (number of bytes) and `DPH`
(strobe number); the data are always sent from the X register downwards
starting at 14h:

| Entry | Strobe | Bytes | Source | Receiver per schematic |
|---|---|---|---|---|
| 0E54h | STR6 | 4 | 14h…11h | TWS D331, unit 2 |
| 0E5Bh | STR7 | 2 | 14h, 13h | |
| 0E62h | STR9 | 1 | 14h | D101/D102, one of two per telegram |
| 0E69h | STR5 | 4+2 | 14h…11h, 19h, 18h | D130 / D138 / D139 |
| 0E78h | STR3 | 2 | 14h, 13h | D126/D144, pulse generator |
| 0E7Fh | STR4 | 2 | 14h, 13h | D121-A/D122-A, 11-bit burst counter |

The two bytes to STR4 fit the **11-bit down counter** of the burst logic
read off the schematic, the two to STR3 the cascade across the sheet
boundary. With that the byte count of every strobe is documented from
the listing, not only from measurement.

### How STR9 transfers sixteen bits

The hardware offers two shift registers on STR9, but the firmware sends
only **one** byte per telegram. The contradiction resolves in two steps.

**First, the wiring.** At D101 only **pin 9 (QS) is unused**; **pin 10
(QS')** carries a line to the right, around underneath the device and
back to the left to **D102 pin 2**, the data input. So the two are
**cascaded** through the second serial output. They share clock and
strobe:

```
X801 pin 7  SC    ──> D101 pin 3   and  D102 pin 3
X801 pin 8  SD    ──> D101 pin 2
X801 pin 9  STR9  ──> D101 pin 1   and  D102 pin 1
D101 pin 10 (QS') ──> D102 pin 2
```

**Second, the measurement.** The telegrams come in pairs. Over a cold
start and three key presses:

| Telegram | Distance to the previous one |
|---|---|
| `80` | – |
| `00` | 2 053 538 cycles |
| `37` | **41 587 cycles** |
| `00` | 3 353 288 cycles |
| `37` | **46 924 cycles** |

Two bytes close together, then a long silence. So a 16-bit word is
transferred in **two consecutive one-byte telegrams**. Because both
registers hang on the same strobe, the second telegram pushes the first
byte on into D102: **the byte sent first ends up in D102, the one sent
last in D101.**

That fixes the bit assignment:

| Byte | Register | Content |
|---|---|---|
| first | D102 | Q1…Q3 the lower DAC bits, **Q4…Q8 = S1…S5** |
| second | D101 | Q1…Q8, the upper eight DAC bits |

The statement "STR9, one byte" in section 4 is correct per telegram, but
as a description of the process it is incomplete — there are always two.

The same pattern is to be expected on every assembly with more than one
shift register and should be checked when reading the remaining
schematics.

### State

The series of sheets is done: amplitude controller (fig. 109),
attenuator (fig. 111), amplitude modulator (fig. 117), pulse generator
(fig. 118), burst logic (fig. 120) and modulation oscillator (fig. 119).
The cascade pattern has been confirmed everywhere: several shift
registers on one strobe, connected through **QS' (pin 10)**, pin 9 stays
free — with D101/D102 (STR9), D126/D144 (STR3), D121/D122 (STR4) and
D139/D138/D130 (STR5).

For the byte split, the route through the **entry table 0E54h–0E84h** is
shorter than any measurement: it names the strobe number and the byte
count in plain form. The schematic then supplies which receiver keeps
which byte.

---

## 31 Two devices that were read out: the ARB EPROM and the X28C64

Both dumps are available as Intel HEX and were read out several times.

### D27C64, labelled "SINUS 1.1" — the SinePROM D131-A

Its location is confirmed: **unit 4, modulation oscillator**, labelled
"SinePROM" in the schematic (fig. 119, pages 157/158). It sits between
the TWS D130-A and the latch D132-A in front of the DAC N133; see
section 30.


| Area | Content |
|---|---|
| 0000h–03FFh | 1024 bytes of curve |
| 0400h | a single byte 55h |
| 0800h | a single byte 00h |
| otherwise | FFh, unerased |

The curve is a **plain 8-bit sine over one full period**:

```
w[i] = 127.5 + 127.5 · sin(2π·i/1024)
```

Largest deviation 1.5 out of 255, 0.55 on average — that is pure
rounding. Sample points: w[0] = 127, w[256] = 254, w[512] = 127,
w[768] = 0. So the sine starts at the zero crossing and rises.

The two single bytes at 0400h and 0800h sit exactly on the kilobyte
boundaries and look like block marks.

**The sine is not inside the firmware ROM.** Neither V1.3 nor V1.5
contains the byte sequence, and none of the built-in waveform tables
matches it — A047h and A447h do correlate at −0.92 but are not sine
curves, they are piecewise linear shapes.

### X28C64

Unlike the EPROM, this device is **written throughout**, 0000h to 1FFFh,
with only 298 bytes carrying FFh.

**The data are packed, not interspersed with metadata.** Every five
bytes contain **four values of ten bits**: four bytes supply the upper
eight bits, the fifth byte the four pairs of lower two bits, the least
significant pair first.

```
value k (k = 0…3) = (byte[k] << 2) | ((byte[4] >> 2k) & 3)
```

4 · 10 bits = 40 bits = exactly 5 bytes, without loss. The value range
runs cleanly from 1 to 1023, and the unpacked series is smooth.

The block from **1500h** is unambiguous with that:

```
w[i] = 1023 · sin(π·i/512)        i = 0 … 511
```

a half sine arc over 512 points. **Addendum:** that was only half the
curve. Since section 32 the record length is known — 1024 points in 1280
bytes — and the second 512 points carry the same arc once more. So it is
a **full-wave rectified sine** over the whole curve length, and the
block is **arbitrary curve 5**, because 1500h = 0100h + 4·1280. Largest
deviation 2.2 out of 1023, i.e. 0.21 %. Sample points: w[0] = 1,
w[128] = 723, w[256] = 1023, w[384] = 723 — and 723/1023 is 0.707, the
sine of 45°.

### Two corrections to somebody else's preliminary analysis

An analysis of these dumps was available that is misleading on two
points:

- The fifth byte was said to be a **metadata byte** with timing or
  flags. It is not: it carries the lower two bits of four ten-bit
  values. The proof is the packing itself — 40 bits go into 5 bytes
  without a remainder, the value range exhausts 1…1023, and the unpacked
  curve is smoother than the discarded eight-bit values.
- The curve at 1500h was said to be a **full cycle**, mathematically an
  inverted cosine. It is a half arc over 512 points; a full-sine model
  deviates by 25 %, the half-arc model by 0.21 %.

The observation of the group-of-five structure and the classification of
the D27C64 as a plain wavetable were right.

### The X28C64 is the arbitrary EEPROM D310

The question of where it is fitted is answered, see section 32: the
firmware checks the directory of this device, and the dump that was read
out passes the check. At D310 the schematic carries an X28C256 with
32 KB — what was fitted here was the smaller 8 KB variant. On the MOVX
bus that makes no difference, the firmware only uses the beginning
anyway.

### Open

The grouping of the **curve data** in fives does not sit on round
addresses, and the blocks beyond the directory are not delimited yet —
for that, the starting offset that makes the unpacked series smooth has
to be found per block. The directory from 0002h on now says, however,
how many curves there are at all (six) and which parameters belong to
each; see section 32.

---

## 32 The remote control part: parser, dispatcher and the block 8871h–9AFEh

With 4749 bytes and 13 entry points, 8871h–9AFEh was the largest
contiguous code area without any name at all. The way in was not found
inside the block itself but at its only external caller.

### The dispatcher 6A85h

```
6A85  JBC   24h.5,X6AA5h
6A88  MOV   A,10h          ; command code, not a computed value
6A8C  ANL   A,#0F0h
6A8E  CJNE  A,#60h,X6A94h
6A91  LJMP  X8871h         ; group 60h  -> the big block
6A94  CJNE  A,#0C0h,X6A9Fh
6A99  JB    ACC.3,X6ABDh
6A9C  LJMP  X6B51h         ; group C0h
6A9F  LCALL X71BFh         ; otherwise the shared command interpreter
```

The last line is remarkable: **remote commands end up in the same
command table as key presses** (71BFh, section 16). Only the groups 60h
and C0h have execution parts of their own — those are the commands that
do not exist on the front panel.

### An ASCII parser sits in front of it

The area 6700h–6C00h compares against characters throughout, not against
numbers. All the comparisons at a glance:

| Character | Role |
|---|---|
| `0Ah` LF | end of line, tested at 13 places |
| `3Bh` `;` | command separator |
| `2Ch` `,` | argument separator |
| `3Fh` `?` | query |
| `20h` ` ` | skip the space |
| `22h` `"` | character string |
| `2Bh` `+`, `2Dh` `-` | sign; they set 22h.4 |
| `2Eh` `.` | decimal point; sets 22h.7 |
| `45h` `E` | exponent |
| `23h` `#` | increments 10h and calls 5F4Dh |
| `53h` `S`, `50h` `P`, `64h` `d` | keywords |

That is a text command set typical of IEEE-488. From it the parser
assembles the command code in 10h and hands over to 6A85h.

### What the block touches

An evaluation of the 2457 instructions shows the role immediately:

| RAM | Frequency | Meaning |
|---|---|---|
| 4Ch | 39× | IFACE_POINTER |
| 4Bh | 34× | IFACE_STATUS |
| 10h–14h, 15h–1Eh | 20–57× each | arithmetic registers X, Y, Z |

Plus calls of `5F2Eh` (IFACE_HANDLER), `517Dh` (STATUS_READ, 7×),
`3381h`/`37DBh` (build and send the display). The block **formats values
and sends them back over the interface** — so the send direction left
open in section 28 hangs on it.

Contrary to what was assumed, it contains **no texts**: of 4750 bytes,
1397 are printable, but only as random opcodes, in 16 runs of at most
eight characters each.

### Structured into thirteen parts — all named

| Area | Bytes | called from |
|---|---|---|
| 8871h–8A1Bh | 427 | 6A91h (the dispatcher) |
| 8A1Ch–8CB8h | 669 | 6804h, 8991h, 899Eh, 8C19h |
| 8CB9h–8DE2h | 298 | 63FDh |
| 8DE3h–8E1Bh | 57 | 6B4Dh and five places inside the block |
| 8E1Ch–8E31h | 22 | 6EC5h |
| 8E32h–8E54h | 35 | 3CEDh |
| 8E55h–8F02h | 174 | 6896h |
| 8F03h–9329h | 1063 | 68A2h and four places inside the block |
| 932Ah–9614h | 747 | 687Ah |
| 9615h–97D8h | 452 | 3B6Ch, 5EEEh, 71A2h |
| 97D9h–98B2h | 218 | 3B74h, 3D08h and three places inside the block |
| 98B3h–991Eh | 108 | 5F01h, 966Bh |
| 991Fh–9AFEh | 480 | 1345h, 1394h |

All thirteen now carry a name. Two are settled in substance — 9615h
checks the directory, 991Fh loads a curve record. For the others what is
documented is **what they touch**, not what they stand for in substance;
their names are therefore given after where they were found:

| Part | documented property |
|---|---|
| 8871h | entry of group 60h from the dispatcher 6A91h |
| 8A1Ch | computes in Z and Y, reports errors through 645Ah |
| 8CB9h | stores 34h/35h in the upper RAM buffer at FBh…FDh, uses 4Bh/4Ch |
| 8DE3h, 8E1Ch, 8E32h | short helpers, some called from the initialisation |
| 8E55h | display cells 32h/33h/3Eh, reads the status register |
| 8F03h | largest part: build the display, status register, interface pointer 4Ch |
| 932Ah | status register, pointers 4Bh/4Ch, arithmetic register X |
| 97D9h | output sequence with fixed constants through 43ADh and 10B5h |
| 98B3h | sets Y to 0200h and masks, uses the curve number 67h |

The assignment of *which arbitrary command triggers which part* is
therefore not made yet: the block contains only four direct token
comparisons (60h ARB, 61h BEGIN, 62h CNT, 66h ARBSELECT), the rest
branches on bit tests of 10h. That could be measured cleanly over the
remote control path as soon as a command can be injected completely.

### The learn query: table 6CECh

In front of the reply generator 6D1Eh sit 50 bytes that read as
**command tokens** — eight groups separated by 00h, in exactly the order
of the operating modes from 2Ch (one-hot):

| Operating mode | commands emitted |
|---|---|
| MOD OFF | B0h, STFREQ, WAVEFORM, AMPL, DCOFFSET, DUTYCYCLE, OUTPUT, LOIMP, ACOFF, DCOFF |
| AM | MODLN, MODFREQ, AMDEPTH, MODSRC |
| FM | MODLN, MODFREQ, FMDEVIATION, MODSRC |
| PSK | MODLN, MODFREQ, MODSRC |
| GATE | MODLN, MODFREQ, MODSRC |
| SWEEP LIN | MODLN, STOPFREQ, SWEEPTIME, SWEEPMODE, TRIGS |
| SWEEP LOG | MODLN, STOPFREQ, SWEEPTIME, MODFREQ, AMDEPTH, SWEEPMODE, MODSRC, TRIGS |
| BURST | MODLN, MODFREQ, ONPERIODS, STPHASE, TRIGS |

This is the template for **`*LRN?`**, the learn query: with it the
instrument returns its complete setting as a sequence of commands, and
only those parameters that have any meaning in the current operating
mode. One token, **B0h**, does not appear in the command table —
presumably a control mark for the beginning.

**6D1Eh** builds the reply from it: it touches 4Fh 29 times, the buffer
`MSG_APPEND` (8014h) hangs the texts onto.

### The argument evaluation 7415h

The execution part of group C0h is short and delegates:

```
6B51  LCALL X7415h        ; evaluate the argument
6B54  JNC   X6B5Dh
6B56  DEC   4Ch  /  INC 4Bh   ; pointer back, count the error
6B5D  ...
6B62  MOV   A,10h  /  CJNE A,#0C4h,X6B82h   ; C4h = TRM
```

7415h (480 bytes) is also called from 71C7h in the shared interpreter
and relies on 7693h for the numeric part, which reports range errors
through `ERROR_REPORT`.

### The error report 645Ah

Twelve of the calls out of the block go to the same short routine:

```
645A  MOV  49h,A          ; remember the error number
645C  MOV  DPTR,#6465h
645F  MOVC A,@A+DPTR      ; class mask from the table
6460  ORL  69h,A          ; collect the class in 69h
6462  SETB 24h.3          ; an error is pending
6464  RET
```

The table at 6465h has **56 entries** — error numbers 00h to 37h — and
supplies one mask each out of 00h, 04h, 08h, 10h or 20h. The numbers the
block reports are 01h, 03h, 20h, 21h, 22h, 25h and 80h. The routine
649Dh in front of it picks the number matching the operating mode.

### The arbitrary EEPROM: directory and checksum

The most productive part is 9615h. It works on the MOVX bus, that is on
the EEPROM D310, and computes in groups of five:

```
9615  CLR   F0  /  CLR 22h.7
9619  MOV   DPTR,#0000h
961C  MOVX  A,@DPTR   /  MOV R6,A
961E  ADD   A,#55h    /  MOV R4,A     ; the checksum starts at header + 55h
9623  MOVX  A,@DPTR   /  MOV R1,A     ; 0001h = target value
9627  MOV   A,R6  /  ANL A,#0Fh       ; lower nibble = count n
962B  MOV   B,#05h  /  MUL AB
962F  ADD   A,#05h  /  MOV R3,A       ; to be checked: n*5 + 5 bytes
9632  MOVX  A,@DPTR / INC DPTR / ADD A,R4 / MOV R4,A / DJNZ R3
9638  XRL   A,R1
9639  JZ    X9645h                    ; matches
963B  SETB  22h.7  /  SETB F0  /  LCALL X9798h   ; rejected
```

Recomputed against the **actually read out** X28C64:

```
header 0000h = 06h  ->  n = 6, 6*5+5 = 35 bytes from 0002h are checked
sum = 55h + 06h + sum(d[2..36]) = 35h
target value 0001h = 35h                                -> matches
```

So the dump is a valid directory. The counter-check in the emulator
confirms it and at the same time shows that the check is sharp — the
number of times the error branch 963Bh is taken was counted:

| Image | Error branch |
|---|---|
| the X28C64 as read out | **0×** |
| the same, one data bit flipped | 1× |
| the same, check byte flipped | 1× |
| `D310_image.bin` (synthetic) | 0× |
| empty, all FFh | 1× |

That documents that the X28C64 read out is **the arbitrary EEPROM
D310**. Incidentally, 9615h does not run during the cold start — the
routine had to be called directly, otherwise the result stays the same
for every image.

### The record layout

991Fh loads the record of the selected curve:

```
991F  JB    20h.1,X9946h        ; alternatively from the RAM buffer at E0h
9922  MOV   DPTR,#0003h         ; default: record 0
9925  MOV   R0,#11h  /  MOV R3,#04h
9929  MOV   C,2Bh.4  /  ANL C,29h.1    ; only if arbitrary is selected
992F  MOV   A,67h / ANL A,#0F0h / SWAP A   ; k = curve number
9934  DEC   A  /  MOV B,#05h  /  MUL AB
9939  ADD   A,#08h  /  MOV DPL,A    ; 0008h + (k-1)*5 = 0003h + k*5
993D  MOVX  A,@DPTR / MOV @R0,A / INC R0 / INC DPL / DJNZ R3
```

Four bytes land in X1…X4. So the directory consists of **n+1 records of
five bytes each** from 0002h on, one identity byte and four data bytes:

| Record | Address | Identity | Data | as 16 bit |
|---|---|---|---|---|
| 0 | 0002h | 01h | 80 00 FF C0 | 8000h FFC0h |
| 1 | 0007h | FFh | 80 00 FF C0 | 8000h FFC0h |
| 2 | 000Ch | 55h | 80 00 80 00 | 8000h 8000h |
| 3 | 0011h | 27h | 7F 40 87 C0 | 7F40h 87C0h |
| 4 | 0016h | F6h | 80 00 B3 00 | 8000h B300h |
| 5 | 001Bh | 5Dh | 00 40 FF C0 | 0040h FFC0h |
| 6 | 0020h | 55h | 80 00 80 00 | 8000h 8000h |

Calling 991Fh directly in the emulator delivers exactly `80 00 FF C0` in
X1…X4 with the real dump — record 0, as derived from the listing. With
the synthetic image `00 00 00 00` comes back, with an empty one
`FF FF FF FF`.

**The two values are the minimum and maximum of the curve**, as a 10-bit
value left-aligned by six bits. For arbitrary, the data sheet gives
"Memory length 1024 (10 bits), Vertical resolution 1023 (10 bits)" —
dividing the directory values by 64 gives exactly such numbers. Checked
against the unpacked curve data, with six sample points:

| Record | Directory | ÷64 | actually in the data |
|---|---|---|---|
| 1 | 8000h FFC0h | 512 1023 | min 512, max 1023 ✓ |
| 2 | 8000h 8000h | 512 512 | min 512, max 512 ✓ |
| 3 | 7F40h 87C0h | 509 543 | min 509, max 543 ✓ |
| 4 | 8000h B300h | 512 716 | min 512, max 716 ✓ |
| 5 | 0040h FFC0h | 1 1023 | min 1, max 1023 ✓ |
| 6 | 8000h 8000h | 512 512 | min 512, max 512 ✓ |

Record 0 is identical with record 1 and serves as the default — 991Fh
reads it without a curve selection.

### Why six curves and not twenty-four

The data sheet gives **24 waveform memories** for all three models. The
directory says n = 6. The arithmetic explains the difference completely:

```
1024 points of 10 bits, packed 4 values per 5 bytes  ->  1280 bytes per curve

 6 curves x 1280 =  7 680 bytes, from 0100h to 1EFFh   (X28C64,  8 KB)
24 curves x 1280 = 30 720 bytes, from 0100h to 78FFh   (X28C256, 32 KB)
```

The measured read range of the firmware is **0100h–1EFFh**, that is six
curves to the byte. The instrument is fitted with the small device and
therefore has **six instead of twenty-four** curve memories; `n` in the
header byte is exactly that number. The full fit with the X28C256 named
in the schematic would give 24 — exactly the data sheet figure.

So the curves sit at fixed addresses:

```
curve k starts at 0100h + (k-1) * 1280      k = 1 … n
      1: 0100h   2: 0600h   3: 0B00h   4: 1000h   5: 1500h   6: 1A00h
```

Unpacking them gives, for the instrument at hand:

| Curve | from | Content |
|---|---|---|
| 1 | 0100h | min 512, max 1023 — only the upper half driven |
| 2 | 0600h | empty, constant 512 |
| 3 | 0B00h | min 509, max 543 — very small drive |
| 4 | 1000h | min 512, max 716 |
| 5 | 1500h | **full-wave rectified sine**, two half arcs over 1024 points, `1 + 1022·sin(π·i/512)`, deviation ≤ 1 |
| 6 | 1A00h | empty, constant 512 |

### What the user manual says about it

The PM5139 user manual (chapter 3.7.4.6) describes the commands of group
60h from the user's point of view — they match the tokens from the
command table one to one:

| Command | Value range | Effect |
|---|---|---|
| `ARBSELECT` | 1…24 | select a memory slot |
| `ARBITRARY` / `ARB` | 1…24 | activate a stored curve |
| `BEGIN` | 0…1023 | start address on the X axis |
| `COUNT` / `CNT` | 1…255 | address step size |
| `DATA` | `yy,xx,xx,…` | yy values, each −511…+511 |
| `FILL` | −511…+511 | set all 1024 addresses to one value |
| `CLEAR ARBIT` | — | erase the curve, equivalent to `FILL 0` |
| `ARBITEXECUTE` | ON/OFF | output immediately or wait for `ARB` |

The decisive part is the value range **−511 … 0 … +511**, which
according to the manual corresponds to 20 Vpp. So the 10-bit values
stored internally are **offset by 512**: 512 is the zero. That explains
the measurement above completely:

| Curve | raw | as Y | Amplitude `(Ymax−Ymin)/1022 · 20 V` |
|---|---|---|---|
| 1 | 512…1023 | 0…+511 | 10.000 V |
| 2 | 512…512 | 0…0 | 0 V — erased, i.e. `FILL 0` |
| 3 | 509…543 | −3…+31 | 0.665 V |
| 4 | 512…716 | 0…+204 | 3.992 V |
| 5 | 1…1023 | −511…+511 | 20.000 V |
| 6 | 512…512 | 0…0 | 0 V — erased |

The conversion formula is in the manual verbatim. That also makes the
**purpose** of the two directory values clear: the firmware needs the
minimum and the maximum to determine the output amplitude of a curve —
which is why they sit in the directory and do not have to be searched
for in 1280 bytes on every output. The error messages 138 `AMPLITUDE OF
ARBITRARY OUT OF RANGE` and 139 `AMPLITUDE CORRECTED` fit that.

The OCR version of the English part of the manual sits in the project as
`PM5139_User_Manual_OCR_ENG.txt`.

The **curve number k sits in the upper nibble of 67h**. If it does not
match the count in the directory, 9650h resets it to 1:

```
9645  MOV  A,67h / ANL A,#0F0h / SWAP A / MOV R3,A
964B  MOV  A,R6  / CLR C / SUBB A,R3
964E  JNC  X9656h
9650  ANL  67h,#0Fh  /  ORL 67h,#10h
```

### Which address range the firmware reads at all

Before switching over the emulator image, it had to be settled whether
an 8 KB device is enough. An X28C64 in a socket meant for the X28C256
gets no connection on A13 and A14, so its content is mirrored four times
over 0000h–7FFFh. The measurement was made with a hook in
`CPU.prototype.xr`, over a cold start, twelve keys and the direct call of
the EEPROM routines:

```
addresses read:    7717 different ones, 0000h to 1EFFh
of those >= 2000h: 0
ranges:            0000h-0024h   and   0100h-1EFFh
during the cold start alone: not a single one
```

So the mirroring never becomes visible — the 8 KB are exactly enough.
And the
directory ends at **0024h**, exactly the computed length
`2 + (6·5+5) − 1 = 36 = 24h`. A third independent piece of evidence for
the structure of the header.

So the curve data sit from **0100h** on, not immediately behind the
directory.

### The emulator image is the real dump now

`D310_image.bin` had been generated up to this point, not read out —
one of the three pitfalls named in CLAUDE.md. Since the real dump passes
the check, it has taken its place; the old version sits next to it as
`D310_image_synthetic.bin`, and `mk_eeprom.py` has been writing there
since, so that it does not overwrite the real image.

The exchange changes nothing about the earlier measurements. A cold
start followed by four keys delivers the same state with both images:

```
PC=0071  display 16 00 A2 02 2B A0 08 0C 0E ED 00 0E ED ED 00 0E ED ED EF 40
22h.7=0  67h=11h  2Bh=40h
```

In the *base* profile `flags.js` delivers `STR1{00 19}` and
`STR6{D2 07 20 01}` unchanged. That is to be expected because the cold
start does not read the EEPROM at all — but it confirms that no earlier
measurement has to be redone.

### Open

- The meaning of the two 16-bit values per record. The obvious thought
  that the identity byte is a checksum over the four data bytes with
  start value 55h does **not** hold: it only fits for the two records
  whose data sum happens to be zero.
- The nine remaining sub-areas of the block, individually.

### What the groups 60h and C0h are

The command table at 7752h has long been decoded in `PM5139_Tables.md` —
131 entries of 16 bytes, 14 bytes of name and two tokens each (one for
the form with a parameter or `?`, one for the command standing alone).
Grouping all tokens by the upper nibble, that is by exactly what the
dispatcher tests, the answer falls out:

| Nibble | Commands | Destination |
|---|---|---|
| **6xh** | ARB, ARBIT, ARBITRARY, ARBSELECT, ARBITSELECT, ARBITEXECUTE, ARON, AROFF, CLARB, CLARBITRARY, BEGIN, CNT, COUNT, DATA, FILL | **8871h** |
| **Cxh** | `*CLS`, `*ESE`, `*ESR`, `*OPC`, `*RST`, `*SRE`, `*STB`, `*TST`, `*WAI`, TRM | **6B51h** |
| all the rest | waveform (1xh), modulation (2xh), output (3xh), trigger (4xh), memory (5xh), values (8xh) … | 71BFh |

**Group 60h are the arbitrary waveform commands.** That explains
everything else about the block by itself: why it contains the EEPROM
routines 9615h and 991Fh, why it touches 4Ch and 4Bh so often (`DATA`
and `FILL` take in sample points over the interface) and why it is as
large as 4749 bytes — loading, checking, selecting and executing curves
is the most elaborate single function of the instrument.

**Group C0h are the IEEE-488.2 common commands.** That confirms the
classification of the parser from its character set independently: it is
an instrument with the usual `*` command set, only over RS-232 instead
of GPIB.

Only the prefixes without a meaning of their own carry FFh — `AC`, `DC`,
`SWEEP`, `BURST`, `MODSRC`, `TRIGSRC` and others that only become
complete with an additional word.

The message table closes the circle: index 100 holds `CHECKSUM ERROR`,
index 99 `NO ARBITRARY DATA` — the texts belonging to exactly the error
branch in 9615h that was measured above.

---

## 33 The upper frequency limit: what is software and what is not

The question was whether the PM5136, PM5138A and PM5139 differ only in
firmware and whether anything above 20 MHz would be possible. The answer
is split: the limit really does sit in the ROM as a patchable table, but
the clock puts a hard physical barrier above it.

### The table at 12D2h

The check happens at 11CCh, indexed by **parameter** (not by waveform —
see the correction further down):

```
11CF  MOV  A,24h
11D1  ANL  A,#0Fh
11D3  DEC  A
11D4  RL   A            ; R3 = (parameter index - 1) * 2
11D6  JNZ  X11E0h
11D8  MOV  A,50h        ; frequency, decade in the upper nibble
11DA  ADD  A,#90h       ; carry from 50h >= 70h on, i.e. decade >= 7
11DC  JC   X1216h
...
1216  MOV  A,R3
1217  MOV  DPTR,#12D2h
121A  MOVC A,@A+DPTR  /  MOV 1Dh,A     ; Z3 = limit, high part
121F  MOVC A,@A+DPTR  /  MOV 1Eh,A     ; Z4 = limit, low part
1222  LCALL X31C7h                     ; COMPARE_YZ
1225  JNC  X1228h                      ; limit exceeded -> correct
1227  RET
```

Thirteen entries of 16 bits each:

```
2001  0201  0021  0011  0011  0011  0021  0101  0201  0019  0010  0101  301D
```

The values are **BCD**, not binary: read as hex digits they give 2001,
201, 21, 11, 101, 19, 10. That is measured, see below.

This table is **not** the one from section 19: 2A81h holds the limits
per decade for the rotary knob, 12D2h the upper limit per parameter. Two
separate checks.

In V1.5 the same table sits at **134Fh** and is byte-identical. So a
patch would be trivial, and `romfix.py` carries the checksum along.

### There is no model byte

Both ROMs searched:

| String | V1.3 | V1.5 |
|---|---|---|
| `5136` | 0× | 0× |
| `5138` | 0× | 0× |
| `PM5139` | 1× | 1× |

The one occurrence is the identification string at AC55h. The firmware
is burnt per model; there is no configuration switch that could be
flipped.

### What the hardware fixes

From the service manual, chapter 3 (page 10) and the chapter on the
clock (page 13), verbatim:

> The CLOCK GENERATOR produces the clock frequency 10 × 2²¹ Hz =
> 20.97 MHz for the Triangle Wave Synthesizer (TWS) and the 2 MHz clock
> frequency for the Modulation Oscillator. The Voltage Controlled
> Oscillator (VCO) for the 20.97 MHz in the Phase-Locked Loop (PLL) is
> an LC oscillator …

> The 5 MHz Lowpass Filter (LPF) smooths the staircase sine wave signal
> of the DAC. … The FREQUENCY MULTIPLIER doubles the frequency above
> 5 MHz by analog squaring.

> Above f_char the number of elements decreases linearly with
> increasing frequency, whereby the rate by which the elements are
> generated is still the clock frequency 20.97 MHz.

The clock hangs on the 10 MHz crystal **G800** and cannot be changed
without a hardware modification. And the models also differ in the
analogue part, documented: the power supply schematic carries a fitting
table **TAB. 1** with PM5136 ±16.5 V against PM5138A ±26 V — that is the
Vpp difference, and it cannot be patched away.

### Why 20 MHz is the end

```
20.97152 MHz / 2  =  10.49 MHz digital        (Nyquist)
             × 2  =  20.97 MHz after the analogue doubler
the PM5139 uses      20.00 MHz
```

So the instrument already runs practically at the limit. At 20 MHz about
**two sample points per period** remain — the number falls linearly with
frequency from 1024 at f_char = 20.48 kHz, because the TWS word is the
step size through the waveform, not the output rate. A patch of the
table would make the display count higher and let the computation keep
running (up to the known 16-bit truncation in 162Ch, section 23), but
the output would be aliasing instead of a sine.

The thought of halving the time resolution therefore leads nowhere — the
firmware does that automatically anyway, and with one point per period
there is no oscillation left. 40 MHz would only be reachable through a
**second analogue squaring stage**, that is additional hardware, with
the level halved and the distortion doubled per stage.

### The target figures from the data sheet

The specsheet `PM5136_PM5138A_PM5139_Specsheet.pdf` gives the operating
limits of all three models side by side — exactly the table the service
manual was missing:

| Waveform | PM5136 | PM5138A | PM5139 |
|---|---|---|---|
| nominal range | 0.1 mHz – 5 MHz | 0.1 mHz – 10 MHz | 0.1 mHz – 20 MHz |
| sine, pos./neg. pulse | 5 MHz | 10 MHz | 20 MHz |
| square | 5 MHz | 10 MHz | 20 MHz |
| triangle | 500 kHz | 500 kHz | 500 kHz |
| pos./neg. sawtooth | 50 kHz | 50 kHz | 50 kHz |
| sine pulse, triangle pulse, haversine | — | — | 50 kHz |
| **arbitrary** | 0.1 mHz – 20 kHz | | |

That documents the model differences as well: the PM5138A delivers
40 Vpp against 20 Vpp on the other two — matching the fitting table
TAB. 1 in the power supply schematic (±26 V against ±16.5 V). Sine
pulse, triangle pulse and haversine exist **only** on the PM5139.

The figure **max. 20.48 MS/s** for arbitrary matches the clock, i.e.
20.97152 MHz minus overhead — the same time base as in the service
manual.

### Correction: the table is indexed by parameter, not by waveform

The first version of this section said "indexed by waveform". That is
wrong. The path there clears it up:

**11CCh does not run at all in keyboard and rotary knob operation.**
Measured over a cold start, a single detent, twenty detents and four key
sequences — zero passes. When turning, the range check from section 19
applies instead.

11CCh is reached through the handler **0663h**, the ninth entry of the
keyboard jump table at 0301h. It first loads the parameter and then
decides on the basis of a flag table:

```
0663  MOV   A,24h
066F  LCALL X08EAh
0672  MOV   R4,#15h
0674  LCALL X080Bh        ; PARAM_LOAD -> Y = parameter as BCD
0678  MOV   A,24h  /  ANL A,#0Fh
067C  MOV   DPTR,#069Dh  /  MOVC A,@A+DPTR
0680  JB    ACC.7,X0688h
0683  JB    ACC.6,X0688h  ; only then checked
0688  LCALL X1121h        ; -> 11CCh
```

The flag table at 069Dh reads
`00 90 91 A2 40 A3 40 40 84 40 40 40 00 00 00 E5`; bit 7 or 6 set means
"this parameter is checked". The index is `24h & 0Fh`, that is the
**selected parameter** — and exactly the same index forms the table
pointer in 11CFh.

Which index is which parameter is stated by the command table: the
tokens of group 8xh carry the parameter index in the lower nibble.

| Index | Parameter | Table | as BCD | Data sheet |
|---|---|---|---|---|
| 1 | FREQUENCY, STARTFREQ | 2001h | 2001 | 20 MHz |
| 2 | STOPFREQ | 0201h | 201 | |
| 3 | AMPLITUDE | 0021h | 21 | **0–20 Vpp** ✓ |
| 4 | DCOFFSET | 0011h | 11 | **±10 V** ✓ |
| 5 | MODFREQ | 0011h | 11 | 10 Hz–100 kHz |
| 6 | AMDEPTH | 0011h | 11 | 0–100 % |
| 7 | FMDEVIATION | 0021h | 21 | **0–2 %** ✓ |
| 8 | SWEEPTIME | 0101h | 101 | |
| 9 | ONPERIODS | 0201h | 201 | **1–2000** ✓ |
| 10 | STARTPHASE | 0019h | 19 | **±180°** ✓ |
| 11 | DUTYCYCLE | 0010h | 10 | 1–99 % |
| 12 | SWEEPMODE | 0101h | 101 | |

The table value is the **smallest impermissible digit sequence**: 21 for
20 Vpp, 11 for 10 V, 19 for 180°, 21 for 2 %, 2001 for 20 MHz. Five of
them agree directly with the data sheet — which documents the reading
and refutes the earlier assignment "per waveform". The number of entries
fits as well: it is twelve parameters plus one reserve entry, not
thirteen waveforms.

**Confirmed independently by the PM5136 manual.** Its error list
numbers the range errors through, in exactly the same order:

| Index | Parameter (ROM) | Limit | ERROR no. | Message in the PM5136 manual |
|---|---|---|---|---|
| 1 | FREQUENCY | 2001 | 107 | FREQUENCY OUT OF RANGE |
| 2 | STOPFREQ | 201 | 108 | STOP FREQUENCY OUT OF RANGE |
| 3 | AMPLITUDE | 21 | 109 | AMPLITUDE OUT OF RANGE |
| 4 | DCOFFSET | 11 | 110 | DC OFFSET OUT OF RANGE |
| 5 | MODFREQ | 11 | *111* | **missing** |
| 6 | AMDEPTH | 11 | 112 | AM DEPTH OUT OF RANGE |
| 7 | FMDEVIATION | 21 | 113 | FM DEVIATION OUT OF RANGE |
| 8 | SWEEPTIME | 101 | 114 | SWEEP TIME OUT OF RANGE |
| 9 | ONPERIODS | 201 | 115 | BURST PERIOD OUT OF RANGE |
| 10 | STARTPHASE | 19 | *116* | **missing** |
| 11 | DUTYCYCLE | 10 | 117 | DUTY CYCLE OUT OF RANGE |
| 12 | SWEEPMODE | 101 | 118 | ILLEGAL SWEEP MODE |

So **error number = parameter index + 106**. And the only two gaps, 111
and 116, are exactly the two parameters the PM5136 does not have: its
modulation frequency is fixed at 1 kHz according to the data sheet, and
its start/stop phase is fixed at 0°. The same two are missing from its
command list. That confirms the order of table 12D2h from a completely
independent source — and at the same time pins index 12 down as
SWEEPMODE.

### What else the model comparison shows

Of the 131 entries in the ROM command table, **48** are missing from the
PM5136 manual, and they group cleanly by the hardware differences:

| Group | missing commands | Reason |
|---|---|---|
| arbitrary | ARB, ARBIT, ARBITRARY, ARBSELECT, ARBITSELECT, ARBITEXECUTE, ARON, AROFF, CLARB, CLARBITRARY, CNT, FILL | the PM5136 has no curve memories |
| modulation | PSK, MOPSK, MOGATE | PM5138A/5139 only |
| waveforms | HAVERSINE, HAVSINE, SINEPULSE, TRNGLPULSE | PM5139 only |
| output | LOIMP, LOWIMPEDANCE, LOON, LOOFF | the PM5136 only has 50 Ω |
| parameters | MODFREQ, MODLNFREQ, STARTPHASE, STPHASE | see above |

So the PM5139 ROM contains the full command set. A PM5136 with this
firmware would have commands for assemblies it does not own — which
supports the observation from section 33 that the firmware is burnt per
model and that there is no model byte.

### The table values are BCD — measured

Y does not carry the computed frequency but the **entered parameter as
BCD**; it is filled by `PARAM_LOAD` (080Bh, "into 15h..19h"). A first
attempt to measure through `FREQ_BCD2BIN` (0A26h) therefore came to
nothing — the result lands in X there, and Y stays empty.

With Y as BCD and bisection over the switch-over point of 11CCh
(`limits.js`):

| Parameter (index) | decade < 7 | decade ≥ 7 |
|---|---|---|
| FREQUENCY (1) | 201 | **2001** |
| STOPFREQ (2) | 201 | 201 |
| AMPLITUDE (3) | 21 | 21 |
| DCOFFSET (4) | 11 | 11 |
| MODFREQ (5) | 11 | 11 |
| AMDEPTH (6) | 11 | 11 |
| FMDEVIATION (7) | 21 | 21 |
| SWEEPTIME (8) | 101 | 101 |
| ONPERIODS (9) | 201 | 201 |
| STARTPHASE (10) | 19 | 19 |
| DUTYCYCLE (11) | 10 | 10 |

The switch-over points are **exactly the table entries, read as BCD** —
`2001h` → 2001, `0201h` → 201, `0021h` → 21, `0011h` → 11, `0101h` →
101, `0019h` → 19, `0010h` → 10. That documents the reading of the
table, and the special path for the frequency too: only for parameter 1
does the decade threshold at 11D8h switch to a different entry — below
decade 7, 201 applies, above it 2001.

### Where the parameters sit in RAM

`PARAM_LOAD` fetches the address from a table at **08F2h**, indexed with
the same `24h & 0Fh`:

```
08EA  MOV  A,24h / ANL A,#0Fh / INC A / MOVC A,@A+PC
08F2  50 53 56 58 5A 5C 5E 60 62 64 66 68 67 6A 67
0901  MOV  R0,A                      ; pointer to the parameter
0903  JB   24h.7,X090Ah
0906  MOV  A,@R0 / ANL A,#0F0h / SWAP A   ; R2 = decade
```

Four of them are known independently and confirm the assignment: **50h**
frequency, **56h** amplitude, **58h** offset, **60h** sweep time. Index
1 and 2 occupy three bytes, from index 3 on it is two (081Bh:
`ADD A,#0FDh`, below it `DEC R3`).

### Counter-check through the complete handler

Calling 0663h directly instead of 11CCh starts up the whole chain —
1121h, 11CCh, 1216h and 1222h once each. Watching Z in the process:

```
parameter 3 (amplitude):   Z = 00 00 00 00 21     <- table value 0021h
Y with mantissa 999:       Y = 00 00 00 09 99
```

That removes the earlier reservation: **Z0…Z2 are zero**, only Z3/Z4
come from the table, and the comparison runs against exactly the BCD
value. The meaning of the carry is documented as well — with Y ≥ Z,
11CCh ends through 1227h with the carry set, and the caller then
discards (`0688h: JC X0686h`). With Y < Z it runs through 1228h to
123Eh, `CLR C`.

Remarkable: **no error is reported through 645Ah**; 49h stays unchanged.
The handler discards the input silently.

### The real operating path — key 0Bh

The detour over hand-set RAM cells was unnecessary. Trying all 256 key
codes and counting which handler of the jump table 0301h starts up
(`keycodes.js`), the answer falls out:

| Handler | Key codes |
|---|---|
| 8 (0663h), **without** 11CCh | 0Ah, 4Ah, 8Ah, CAh |
| 8 (0663h), **with** 11CCh | **0Bh**, 4Bh, 8Bh, CBh |

The upper bits are repeat and status bits, what counts is the lower
nibble. And the two keys do the obvious thing: **0Ah lowers the decade,
0Bh raises it** — after a press on 0Ah, 50h no longer holds 50h but 40h,
after 0Bh 60h. When stepping up, the firmware checks the upper limit;
when stepping down it does not.

So the measurement runs without touching RAM at all: select the
parameter, then press 0Bh repeatedly (`decade.js`).

```
FREQUENCY (parameter 1, RAM 50h), decade|mantissa:
  5|01000 -> 6|01000 -> 7|10000 -> 8|10000 -> 9|10000 -> 9|10000 ...
```

The decade runs up to **9** and stops there; further key presses change
nothing. At decade 7 the firmware shifts the mantissa from 01000 to
10000. That is the upper limit, measured through real operating steps
and reproducible.

The selection keys fell out along the way: **08h** selects FREQUENCY,
**18h** DCOFFSET, **20h** MODFREQ, **1Ah** DUTYCYCLE.

### Read off the instrument: the limit is 20 MHz

Three cases, stepped up on the real PM5139 with the decade key:

| Start value | End value | Steps | Mantissa | Reason for stopping |
|---|---|---|---|---|
| 10 kHz | 10 MHz | 3 | 1000 | end of the decade range |
| 20 kHz | 20 MHz | 3 | 2000 | end of the decade range |
| **25 kHz** | **2.5 MHz** | **2** | 2500 | **mantissa too large** |

The third case is the telling one: with mantissa 2500 the instrument
refuses the step that would give 25 MHz and stops one decade earlier.
With 2000 the same step goes through and ends at 20 MHz.

That documents the table value **2001h → BCD 2001** as the *smallest
impermissible mantissa*, and the upper limit of **20 MHz** is measured
instead of inferred. The reading of the whole table 12D2h stands on firm
ground with that: they are BCD limits per parameter, each of them the
first forbidden value.

Two limits act side by side, by the way — the end of the decade range
(decade 9 in the emulator measurement) and the mantissa limit from the
table. At 10 kHz and 20 kHz the range end bites, at 25 kHz the table.

### Open

- **The encoding of decade and mantissa above decade 5.** The formula
  from section 18 (`f = M · 0.1 Hz · 10^(D−1)`) is only documented over
  decades 1 to 5 and does not fit the measured end state "decade 9,
  mantissa 10000". That the firmware shifts the mantissa at decade 7
  (01000 → 10000) and switches to the second table entry there belongs
  to this. An attempt to counter-check that in the emulator by setting
  the mantissa failed — set mantissas lead to states the instrument does
  not take. The clean way would be to set the value through the rotary
  knob.
- With DCOFFSET and DUTYCYCLE, 0Bh does not move the decade; there
  either the end of the range is already reached or the key has no
  effect.
- Whether a remote command bypasses the check at 11CCh. For 29C9h it is
  already noted that values set from outside are not corrected; since
  section 32 it is known where the remote control part sits.
- How the PM5139 makes 20 MHz out of the same clock. All hardware
  figures come from the PM5138A manual, which ends at 10 MHz. From the
  chain it follows that its low-pass has to sit at 10 MHz instead of
  5 MHz — that is not documented, we are missing the PM5139 manual.


---

## 34 The built-in arbitrary curves and a version V2.0

The ROM holds three waveform tables of 1024 bytes each that are loaded
as arbitrary waveforms (9E37h, selected through RAM 0Dh). In the
waveform plot they compare badly with the computed tables. Measuring
them shows two very different causes.

### A047h and A447h are not a defect

| | Segments | different values |
|---|---|---|
| A047h | 108 | 52 |
| A447h | 110 | 52 |

The structure is a **pulse train**: a falling edge, then a baseline at
value 3, a plateau at 253 over 463 points, and in between **narrow
needle pulses** at value 79, two points wide each, 50 points apart.
A047h has four of them, A447h five — the two tables differ at exactly
**two** places.

That is a test pattern for trigger and interference investigations, not
a botched curve. There is nothing to repair here.

### A847h is a noisy copy

The third curve is different. It has the same shape as the computed
table 4AABh (ten sine arcs with staggered amplitude), but:

| | 4AABh | A847h |
|---|---|---|
| different values | – | 222 |
| **direction changes** | **13** | **563** |
| deviation from 4AABh | – | mean −0.13, σ = 4.11 |

The basic shape is right — the mean of the deviation is zero, and only
two of 1024 points differ by more than 10. What distinguishes it from
the computed version is **noise** of about ±4 LSB, recognisable in the
563 direction changes against 13. The curve was apparently sampled from
an analogue source instead of being computed.

### The fix

`mkv20.py` builds a version **V2.0** from it, optionally from V1.5 (the
default) or V1.3. The addresses are found by signature, not entered as
constants:

1. **Replace arbitrary curve 3** with the clean content of the AM table.
   Both are 1024 bytes of 8 bits, the replacement is neutral in size and
   touches no code — 863 bytes change.
2. **Identification string** to `PHILIPS,PM5139,0,V2.0/0000`, so that
   `*IDN?` reports the version. The length stays the same.
3. **Version indication in the display.** The reset sequence sets two
   display cells and sends them (AC47h in V1.3, B3A4h in V1.5):

   | | 3Fh | 40h | Display |
   |---|---|---|---|
   | V1.3 | 0Eh = "1." | 3Dh = "3" | 1.3 |
   | V1.5 | 0Eh = "1." | B5h = "5" | 1.5 |
   | **V2.0** | **7Bh = "2."** | **EDh = "0"** | **2.0** |

   The bytes follow the segment encoding measured in section 15.
4. **Checksum** re-formed over 0000h…B3C9h and stored at B3CAh.

Counter-checked in the emulator: a cold start and four key presses
deliver the same display buffer and the same flags 20h–2Fh as V1.5, the
error flag stays clear, and `romfix.py` confirms the checksum.
`showversion.js` reads the version indication back out of all three
versions — 1.3, 1.5 and 2.0.

### What the table 4AABh really is

In this document it used to be called "sine with ten AM depths". That
designation came from the appearance of the plot, **not from the code** —
4425h merely loads the table into the waveform RAM through STR2, without
any hint at its meaning. Computed through, it is something else:

The 1024 points fall into **ten segments** at the jump points, each of
them a sine arc — alternately from the zero line upwards and from full
scale downwards. Their spans are

```
255  171  120  80  56  38  26  17  12  8
```

so a geometric series with the ratio **0.681 per step**. That is
10^(−1/6), hence **3.33 dB per step** and **30.1 dB over the whole
series** (a factor of 31.9). A model `255 · 10^(−k/6)` hits the values to
within at most 3 out of 255; a halving model deviates by up to 56, a
3 dB model by 10.

So it is a **logarithmically staggered level series** — which fits an
amplitude or attenuation test, but not modulation depths. What the
firmware loads it for is not said by this; only the content is
documented.

### What else would present itself

Three further peculiarities were documented while going through, which
could be fixed but bring **no practical benefit**:

| Where found | Kind | Effect |
|---|---|---|
| `MOV 0FBh,A` at 8E0Ah (V1.5: 9171h) | a write access to an SFR the 80C652 does not have; what was meant is the indirectly addressed RAM 0FBh, which is written correctly one line earlier | harmless, in both versions |
| 9AFFh–9BB8h (V1.5: B2F2h) | I²C traffic with address 5Ah, without any caller in both versions | dead code, 186 bytes |
| 27h.7, 22h.2, 26h.3 | are tested but set nowhere | unreachable branches |

An intervention there does not change the behaviour and only increases
the risk. That is why V2.0 contains only the curve correction.

### Waveforms of our own

`waveforms.py` generates waveforms in both formats of the instrument: as
a **ROM table** (1024 points of 8 bits, raw) and as an **EEPROM record**
(1024 points of 10 bits, four values packed into five bytes, 512 being
the zero).

Two pitfalls that came up in the process:

- **Cyclic continuity.** With the logarithmic chirp the total phase has
  to be a whole multiple of 2π, otherwise the curve jumps when
  repeating. The phase is therefore stretched afterwards so that it
  works out; the remaining jump of 32 out of 255 is the pure sampling
  limit at 40 periods over 1024 points. With the ringing, on the other
  hand, the jump is **intended** — it is the step edge.
- **Drive level against the DC reference.** Two ways are available:
  stretch the curve over the full value range, or scale it so that its
  natural zero sits on the zero of the converter. `waveforms.py` does
  the second, for a reason that only becomes visible when looking at the
  hardware.

  The DC offset of the instrument comes **through STR7 from the DC
  generator D301**, an analogue path of its own, and adds a **fixed**
  voltage. The DC content of a stretched curve, on the other hand,
  scales **with the amplitude**. So anyone stretching an asymmetric
  curve has to readjust the offset on every change of amplitude:

  | Curve | baseline after stretching | offset needed |
  |---|---|---|
  | sinc | −329 steps | +6.44 V |
  | ECG | −287 steps | +5.62 V |
  | rectified sine | −511 steps | +10.00 V |
  | ringing | −63 steps | +1.23 V |
  | staircase, multi-tone, chirp | ±0 | 0 V |

  A zero-centred curve, in contrast, carries its DC reference within
  itself and stays right at every amplitude. What that costs:

  | Curve | steps used | loss |
  |---|---|---|
  | sinc | 622 of 1022 | 0.72 bit |
  | ECG | 654 of 1022 | 0.64 bit |
  | ringing | 910 of 1022 | 0.17 bit |
  | rectified sine | 511 of 1022 | 1.00 bit |
  | staircase, multi-tone, chirp | 1022 of 1022 | – |

  A loss of 0.7 bit corresponds to about 1.6 quantisation steps. The
  noise of the analogue path already amounted to **16 steps** in the
  original that was read out (σ = 4.1 LSB at 8 bits). So the zero
  centring costs about a tenth of what the signal path contributes in
  noise anyway — and it saves having to readjust the offset.

  For symmetric curves both ways are identical; `strecken=True` remains
  available for special cases.

  What matters in both cases is the **order**: the scaling is done in
  floating point, the rounding only once afterwards. That keeps the
  error at half a quantisation step, the optimum; rounding first and
  stretching afterwards would give 1.0 to 1.5 steps.

**In the ROM in V2.0:** arbitrary curve 2 now carries a logarithmic
chirp (1 to 40 periods). It was the natural place for it, because it
differed from curve 1 in exactly **two** bytes — one needle pulse — and
was therefore practically redundant.

**In the arbitrary EEPROM** (`mkarb.py` → `D310_image_V20.bin`) all six
slots are occupied:

| Slot | Curve | Drive level | What for |
|---|---|---|---|
| 1 | sinc, 8 lobes | 12.17 Vpp | band limiting, overshoot |
| 2 | ringing, Q≈6 | 17.81 Vpp | settling behaviour |
| 3 | ECG | 12.80 Vpp | demo, medical electronics |
| 4 | staircase, 16 steps bipolar | 20.00 Vpp | linearity, resolution |
| 5 | rectified sine | 10.00 Vpp | as in the original, but computed |
| 6 | multi-tone, 5 tones | 20.00 Vpp | intermodulation |

All six sit with their natural zero on the zero of the converter. That
is why the Vpp figure is smaller than 20 for the asymmetric shapes — the
rest stays as headroom for the opposite direction, and the baseline is
right at every amplitude setting without readjusting the offset.

The directory entries (minimum and maximum per record) and the check
byte are computed along with them. Counter-check in the emulator: the
firmware accepts the image, and a single flipped bit makes it reject it.

### Plots

`plot_waveforms.py` produces the overall plot from an arbitrary image
(`PM5139_Waveforms_V15.png`, `..._V20.png`), `plot_v20.py` the
before/after of the changed curve
(`PM5139_Waveform3_V15_vs_V20.png`). Both find the tables by signature
and therefore run on all three versions.


---

## 35 Our own code in the ROM: a melody on ARB curve 3

### Why no exploit is needed — and why there cannot be one

The obvious thought of putting code into an arbitrary memory slot and
executing it from there fails on the architecture: the 8051 fetches
instructions through **/PSEN** and data through **/RD** and **/WR**. The
program EPROM **D306** hangs on the former, the arbitrary EEPROM **D310**
on the latter with "its own /CE /OE /WE" according to section 2. The
processor cannot fetch an instruction from the MOVX space — not because
it is blocked, but because the line is missing. Nothing about that can
be changed in software.

Nor is it necessary. Behind the checksum lie **19 509 bytes of
continuous FFh** in the program EPROM, and code runs there.

### The trigger: menu item 8 of the diagnostic program

A first attempt hooked the routine onto the built-in ROM curve 3. That
was a wrong choice: measured over all 256 key codes, the curve
dispatcher is **never** reached from the user interface, 67h stays at
01 — the firmware uses the three ROM curves internally only. A dead
trigger.

The usable point of attachment is the diagnostic menu (LOCAL while
switching on, section 7). Its jump table at 5B7Fh has eight entries, but
the menu loop counts 0Bh only from **1 to 7**:

```
5B5D  INC   0Bh
5B5F  MOV   A,0Bh
5B61  CJNE  A,#08h,X5B45h    ; at 8 back to 1
```

So the eighth entry — index 7, an `LJMP` to the start of the menu at
5B45h — is **never reachable** through the counting, and it is redundant
on top: 5B45h is jumped to from 5B61h and 5B67h anyway. It is exactly
this dead entry that takes the melody:

| Place | Change |
|---|---|
| 5B94h | table entry 8: `LJMP 5B45h` → `LJMP` to the melody |
| 5B62h | count limit `08h` → `09h`, the menu now counts 1…8 |

Two bytes in total. No self-test is lost, no table has to be relocated,
and no menu item without a function is created.

**Operation:** hold LOCAL down and switch on, let the menu count
through, press a key at **8**.

### The old trampoline on ARB curve 3

The routine that loads one of the three built-in curves selects it
through DPTR at the end:

```
AE4D  MOV   A,0Dh
AE50  MOV   DPTR,#9FA9h     ; curve 1
AE53  DEC   A  /  JZ ...
AE56  MOV   DPTR,#A3A9h     ; curve 2
AE59  DEC   A  /  JZ ...
AE5C  MOV   DPTR,#A7A9h     ; curve 3
AE5E  LJMP  XAEBEh          <- here
```

The `LJMP` at AE5Eh would technically be a clean point of attachment —
three bytes pointing at our own code, which afterwards jumps on to the
original target. Only there is no operating step that leads there, which
is why the entry runs through the diagnostic menu. The place stays
unchanged and is documented here in case the ROM curves should ever
become reachable over the remote control.

### The tone output

Tones are produced through the regular frequency path. The encoding is
pleasantly direct — decade 3, then the frequency in 0.01 Hz as BCD:

| Note | Hz | 50h 51h 52h |
|---|---|---|
| E2 | 82.41 | `30 82 41` |
| D2 | 73.42 | `30 73 42` |
| C2 | 65.41 | `30 65 41` |
| B1 | 61.74 | `30 61 74` |
| A#1 | 58.27 | `30 58 27` |
| G1 | 49.00 | `30 49 00` |

So the note table needs four bytes per note: three for the frequency,
one for the duration. A zero byte terminates it.

### The routine

163 bytes at B3CBh, of which 113 bytes are notes. Built with `asm51.py`,
a small assembler that only knows the instructions needed here; the
result was cross-checked with the existing disassembler `mcs51.py`:

```
B3CB  MOV   DPTR,#B3FDh          ; note table
B3CE  CLR   A  / MOVC A,@A+DPTR
B3D0  JZ    XB3FAh               ; zero byte = end
B3D2  MOV   50h,A / INC DPTR     ; three bytes of frequency
      …
B3E1  MOV   R5,A  / INC DPTR     ; duration
B3E3  PUSH  DPH / PUSH DPL
B3E7  LCALL X0A28h               ; OUT_FREQ
B3EA  POP   DPL / POP DPH
B3EE  MOV   R6,#40h              ; wait loop
B3F0  MOV   R7,#0FAh
B3F2  DJNZ  R7,XB3F2h
B3F4  DJNZ  R6,XB3F0h
B3F6  DJNZ  R5,XB3EEh
B3F8  SJMP  XB3CEh
B3FA  LJMP  XAEBEh               ; back into the normal flow
```

### Measured

Calling the curve selection with A = 3 in the emulator, recording every
call of OUT_FREQ:

```
28 notes, clean return into the trampoline target
 1  82.41 Hz  E2
 2  82.41 Hz  E2   97.2 ms
 3  82.41 Hz  E2   97.2 ms
 4  73.42 Hz  D2   97.2 ms
 …
```

The sequence is the bass line of *At Doom's Gate*: four times seven E,
each with a turning note D, C, A♯, B. After the last note the routine
jumps back to the beginning — it **runs endlessly** until the instrument
is switched off and on again.

### The tempo — and why the emulator does not count here

E1M1 runs at about **140 BPM**, the bass line in sixteenths, so **107 ms**
per note. The wait loop is designed for that:

```
w3:  DJNZ R7  with R7 = 250   ->  250 x 2 = 500 us
w2:  MOV R7 (1) + 500 + DJNZ R6 (2) = 503 us,  R6 = 2  ->  1006 us
     R5 = 107  ->  107.6 ms per note   (target 107.1, deviation 0.4 %)
```

The timings come from the MCS-51 data sheet: at 12 MHz one machine cycle
is 1 µs, `DJNZ` needs two, `MOV Rn,#data` one.

**The emulator reports only 54.5 ms for it.** The reason is in `core.js`
line 105: there `this.cycles++` increments the counter **once per
instruction**, regardless of how many machine cycles the instruction
really needs. For instruction counts and orderings that makes no
difference, for absolute timings it does. Where milliseconds matter, the
data sheet applies, not the emulator — the measured 54.5 ms correspond
exactly to the 504 instructions per unit that the loop executes.

**Normal operation is untouched:** a cold start and four key presses
deliver the same display content and the same program counter with and
without the melody.

### Practical notes

The output delivers up to 20 Vpp — on a loudspeaker it needs a series
resistor or a small amplitude setting. One phrase lasts 3.44 seconds and
repeats endlessly; while it runs the firmware is blocked. It is ended by
switching off and on. The exit to the original target is still in the
code (the `LJMP` behind the loop) and can be reactivated with three
bytes should the melody be meant to run only once.

Build order:

```bash
python3 mkv20.py     # curves and version identification
python3 mkdoom.py    # append the melody, recompute the checksum
python3 romfix.py M27512_PM5139_V20.bin
```

## 36 Polyphony: the instrument is a wavetable DDS

The melody of section 35 is one voice. It need not be, and the reason is
in the service manual, chapter 3, page 3-1:

> The TWS generates the read addresses 0 to 1023 for the subsequent RAM.
> Up to the characteristic frequency fchar = 20.48 kHz, all 1024 amplitude
> samples are generated per output signal period.

> During signal generation, the distinct signal amplitude samples are read
> out from the RAM. If the basic signal waveform is altered or the duty
> cycle in the frequency range ≤ 20 kHz is altered, the corresponding
> amplitude samples are loaded into the RAM by the CPU, then the CPU
> switches the RAM to read mode again.

So the PM5139 is a 1024-point wavetable synthesiser whose table the CPU
writes, and the table holds exactly **one period of the output**. A table
built from a sum of harmonics is therefore still periodic in those 1024
points — it plays as a chord. Several notes sound at once, at full output
level, and the CPU does nothing at all while they sound.

Because the partials have to be integer multiples of the table frequency,
the intervals come out in just intonation. For a sustained chord that is
the better tuning anyway.

### 36.1 The download format — ten bits per point

Two bytes per point, **high byte first**:

| Byte | Content |
|---|---|
| 1 | the upper eight bits |
| 2 | the two least significant bits, as 00h, 44h, 88h or CCh — the bit pair duplicated into both nibbles |

so `value = (byte1 << 2) | (byte2 >> 6)`, giving **1 … 1023 with 512 as
the zero line** — the range the arbitrary EEPROM stores as well
(section 32). The waveform RAM is twelve bits wide (D107 the upper eight,
D108 the lower four) but the bus drives only ten of them, so the 10-bit
ARB format wastes nothing; it matches the wire.

> The order was inferred the other way round at first, from decoding the
> firmware's own download off the bus. It was wrong, and the instrument
> played the table as noise until it was corrected. Section 36.7 has the
> test that settled it. The counts below still hold — they say nothing
> about which byte comes first.

Measured over one complete sine download:

| Quantity | Value |
|---|---|
| Distinct low bytes in 1024 points | 4 — `00h 44h 88h CCh`, nothing else |
| Distinct high bytes | 256 |
| Reconstructed points modulo 4 | 1024 of 1024 are ≡ 0 |
| Value range | 4 … 4092 |

Every reconstructed point is a multiple of four and only four distinct
values ever appear in the low-bit byte, which is what fixes the depth at
ten bits regardless of the byte order.

### 36.2 The loader frame

`LOAD_SINE` at 3DABh (V1.3) shows the sequence, and it is the same for
every waveform:

```
3DAB  MOV C,2Ah.2 / ORL C,2Bh.3 / CLR A / ADDC A,#00h   ; index 0 or 1
3DB2  LCALL 4321h        ; SETB P1.5, then a 4-byte TWS command on STR6
3DB5  MOV DPH,#82h / MOVX @DPTR,A     ; a bare strobe on STR2
3DB9  MOV DPTR,#44A7h    ; the source table
3DCA  CLR P1.5           ; EN low — the TWS stops reading
      ... 1024 points, two bytes each ...
3E01  LJMP 4355h         ; the STR1 word, RAM back into read mode
```

The setup routine builds the TWS command from a table at 4335h:

```
4321  SETB  P1.5
4323  MOV   DPTR,#4335h
4326  MOVC  A,@A+DPTR
4327  MOV   14h,A        ; 1Eh for index 0 — the full-table case
4329  MOV   13h,#00h
432C  MOV   12h,#20h     ; TWS command 20h
432F  MOV   11h,#01h
4332  LJMP  0E54h        ; SEND_STR6
```

and the finish sends `(00h, 2Ah)` to STR1 through 43ADh — which is
exactly the two-byte word that closes every waveform download on the bus.

The inner loop at 3D80h shows the timing. The two SBUF writes of a point
are **hand-padded to exactly eight machine cycles apart** and TI is never
polled:

```
3D80  MOV SBUF,R6        2      ; low byte
3D82  MOV A,R3           1  \
3D83  NOP x 7            7  /   eight machine cycles = one byte at fosc/12
3D8A  MOV SBUF,A         1      ; high byte
...
3D9D  CLR P3.5 / SETB P3.5      ; DBK clocks the point into the RAM
3DA1  MOVX A,@DPTR              ; STR0 status, ACC.4 = busy
3DA2  JB 22h.7,3DA6 / CPL A     ; the expected polarity alternates with
3DA6  JNB ACC.4,3DA1            ; the point number (22h.7 from R5 bit 0)
```

That the padding is exactly eight cycles is independent evidence that
serial mode 0 clocks at f_osc/12 — one bit per machine cycle, 8 µs per
byte at 12 MHz. The data sheet says so; the firmware bets its timing on it.

### 36.3 Measured cost of a reload

With the machine-cycle counter (section 36.9), taken over a cold start:

| Download | Bytes | Machine cycles | Real time | Per byte |
|---|---|---|---|---|
| Fill, all points 2048 (loop 3D80h) | 2050 | 32 342 | **32.3 ms** | 15.8 |
| Sine (computed, with interpolation) | 2050 | 56 850 | **56.9 ms** | 27.7 |
| Our loader, straight from a ROM table | 2050 | 39 490 | **39.5 ms** | 19.3 |

And the same measurement for a curve coming out of the arbitrary EEPROM,
which is what selecting an ARB slot does (`ARB_OUTPUT`, 990Bh in V2.0):

| Source | Bytes on the bus | Machine cycles | Real time | MOVX reads |
|---|---|---|---|---|
| **ARB slot from the EEPROM** | 2074 | 55 681 | **55.7 ms** | 2345 |

Identical for every slot. The extra 16 ms over our own loader is the
unpacking: 1280 packed bytes have to be read over MOVX and expanded from
four values per five bytes into the two-byte wire format.

**16.4 ms is a hard floor**, set by the C-bus at f_osc/12 and 2048 bytes,
and there is no second RAM page to swap (36.5). So the wavetable cannot
be exchanged at note rate by any amount of firmware work. At 55.7 ms an
ARB slot change is 18 per second: fine on a chord change at 120 BPM,
where it costs a tenth of a quarter note, and impossible per note — a
sixteenth at 140 BPM is 107 ms and half of it would be silence.

That is what fixes the shape of any synthesizer built on this: the table
is the **patch**, not the note. The same constraint a PPG Wave had.

| Time scale | Mechanism | Cost | Role |
|---|---|---|---|
| per note | retune, ready-made TWS word on STR6 | 139 µs | note on |
| per note | one STR9 byte | 49 µs | envelope, velocity |
| per patch | reload the table | 32–56 ms | timbre, program change |

The bus itself would need only 2048 × 8 µs = 16.4 ms; the rest is the
per-point handshake and the pointer arithmetic. Ours sits between the two
firmware loops: no interpolation to do, but `PUSH DPL/DPH` around the
status read, because DPH is needed for the strobe address while DPTR
holds the source pointer.

**There is no second buffer page.** `RAM_PAGE` at 1D62h, whose name
suggested one, builds the STR1 word out of the *frequency* word 12h/13h
plus two mode bits — it selects how the TWS reads the table above f_char,
not which of two buffers is live:

```
1D62  MOV R0,#0F0h
1D64  A = (13h & E0h) | (12h & 1Fh), rotated left three times
1D72  A = (13h & 1Fh) + 08h ; ACC.4 -> 22h.4 ; + E0h ; carry into F0h
1D81  F1h = 18h, bit 6 from 2Bh.4, bit 0 from 22h.4
```

So a chord change costs a full reload with the output silent for the
duration. At 32–40 ms that is fine between phrases and wrong between
sixteenth notes, which is what shapes the player below.

### 36.4 A polyphonic player: `mkchord.py` and `mkpoly.py`

`mkchord.py` builds the tables. Harmonic numbers over the fundamental,
in just intonation, summed with a 1/h roll-off and staggered starting
phases to keep the crest factor down:

| Name | Harmonics | Intervals over the lowest note |
|---|---|---|
| `octave` | 1:2 | +1200 ¢ |
| `fifth` | 2:3 | +702 ¢ |
| `power` | 2:3:4 | +702, +1200 ¢ |
| `major` | 4:5:6 | +386, +702 ¢ |
| `minor` | 10:12:15 | +316, +702 ¢ |
| `sus4` | 6:8:9 | +498, +702 ¢ |
| `dom7` | 4:5:6:7 | +386, +702, +969 ¢ |
| `maj7` | 8:10:12:15 | +386, +702, +1088 ¢ |
| `min7` | 10:12:15:18 | +316, +702, +1018 ¢ |

`mkpoly.py` puts a table and a melody into the free ROM behind the
checksum and hooks the same dead self-test entry as `mkdoom.py`. It loads
the chord once, then plays the melody by retuning only — which transposes
the whole chord in parallel. The harmony lives in the table, the melody
in the frequency word, and nothing is reloaded while the music runs.

Every note frequency is divided by the lowest harmonic, so the chord
lands on the pitch the score asks for: for `power` (2:3:4) an E2 at
82.41 Hz becomes f0 = 41.205 Hz, and the instrument sounds E2, B2 and E3
together.

Verification is by construction, because the emulator models no waveform
RAM: `polytest.js` boots, enters the player, records the telegrams and
compares the 1024 points arriving on the bus with what `mkchord.py`
generated.

```
telegrams emitted by the loader:
  STR6     4 byte(s)     122 machine cycles  1E 00 20 01
  STR2     0 byte(s)     132 machine cycles
  STR1  2050 byte(s)   39490 machine cycles  CC 89 88 8A 44 8B 44 8C ...

  distinct low bytes: 00 44 88 CC
  points: 1024, range 125..1023, 597 distinct values
  direction changes: 6
  -> all 1024 points identical to the table mkchord.py built

the melody, as the player sets it:
  note  1   f0 = 41.20 Hz   chord 2:3:4 = 82.4 / 123.6 / 164.8 Hz   root E2
  ...
  note  8   f0 = 36.71 Hz   chord 2:3:4 = 73.4 / 110.1 / 146.8 Hz   root D2
```

The riff of section 35 with the same note pattern, but every note now a
power chord — which is what that riff is made of in the original.

### 36.4.1 Two players

Both live in the free ROM behind the checksum and both hook the same dead
entry of the self-test jump table (section 35), so an image carries one or
the other, never both.

| | `mkdoom.py` | `mkpoly.py` |
|---|---|---|
| Voices | one | one table, several notes at once |
| Waveform | whatever is loaded | its own 1024-point chord table |
| Per note | 50h..52h, then `OUT_FREQ` | the same, and the chord transposes with it |
| Output level | as the front panel left it | set explicitly, measured 11.6 Vpp |
| Footprint, built-in tune | 182 bytes | 2617 bytes |
| Footprint, full MIDI track | about 3.7 KB of notes | **6185 bytes** of the 19509 free |
| In the repository | built by `mkdoom.py` | `M27512_PM5139_V20_chords.bin` |

The polyphonic one costs 272 bytes of code; the rest is 2048 bytes of
chord table and 3697 bytes of notes. Two thirds of the free area is still
empty.

Build order:

```bash
python3 mkv20.py                       # curves and version identification

# monophonic
python3 mkdoom.py M27512_PM5139_V20.bin mono.bin

# polyphonic, built-in short version
python3 mkpoly.py --chord power M27512_PM5139_V20.bin poly.bin

# polyphonic, from a MIDI file, upper guitar channel
python3 mkpoly.py --chord power --midi level1.mid --channel 1 \
        M27512_PM5139_V20.bin poly.bin

python3 romfix.py poly.bin              # verify the checksum
node polytest.js poly.bin               # verify on the bus
```

The same tables also fit the arbitrary EEPROM, which needs no firmware
change at all: `python3 mkarb.py --chords` fills the six slots with
chords, and the curves are then selected from the front panel like any
other arbitrary waveform. `arb.js` verifies the directory against the
firmware's own check at 9615h.

### 36.4.2 The envelope

Until the amplitude path was understood (36.8) every note was a flat tone
and the result sounded like an organ. The note loop simply burned its
duration in a `DJNZ` delay. That delay is where the envelope belongs: one
STR9 byte per step, at one step per delay unit, so about 1 kHz.

```
env[i] = 7Fh · e^(−i/40),  floor 06h,  128 entries
```

128 steps cover 129 ms and the last value is held for anything longer.
Measured in the emulator over the first notes, the DAC runs
127 → 109 → 94 → 81 → 70 → 60 → 52 … and jumps back to 127 on the next
note, which is the plucked shape.

Cost: one telegram of 49 µs against a 1009 µs unit, so under 5 % of the
CPU, and it needs no reload and no relay. A single byte is enough — the
first byte of an STR9 pair has no effect on the level, so the previous
value simply shifts on into the register that does not matter.

`--decay` sets the time constant, `--no-envelope` returns to the flat
tone.

The chord tables gained two fuller voicings at no cost in space or load
time, since the number of harmonics does not change the table size:

| Name | Harmonics | Direction changes | Crest factor |
|---|---|---|---|
| `power` | 2:3:4 | 6 | 2.07 |
| `crunch` | 2:3:4:6:8 | 10 | 2.25 |
| `crunch5` | 2:3:4:6:8:12:16 | 16 | 2.33 |

Useful switches: `--chord` picks the harmony, `--waveform` the RAM
waveform to route through, `--relay` and `--dac` the output level
(section 36.8), `--leadin` prepends three seconds of a plain ramp as a
scope check, and `--matrix`, `--relays`, `--ampmatrix` build the
diagnostic images described in 36.7 and 36.8.

### 36.5 What the first burn taught us — telegrams, not just bytes

> **Read this together with 36.6.** The explanation reached here — that
> the waveform RAM feeds the output for only five of the twelve waveforms
> — did not survive the next measurement: a SINE command loads a
> 2050-byte table as well, and its STR3 word is identical to HAV's. What
> stands from this burn is the method and the frequency figures, not the
> conclusion.

The first EPROM built by `mkpoly.py` ran, but produced no melody: a
motorboating putt-putt, and on the scope a square-ish fundamental
chopped at a higher rate. The bus told us the player itself was right —

```
melody (works):  STR6[62 40 60 01]   N = 4062h = 16482
poly:            STR6[30 20 60 01]   N = 2030h =  8240   exactly half
```

— the frequency word is exactly the factor two the chord `power` (2:3:4)
requires. So what was audible was not our table.

The reason is in section 12, in a sentence written long before any of
this: **PGS is active for exactly those five waveforms that come out of
the waveform RAM** — POSSAW, NEGSAW, HAV, SINEPULSE, TRNGLPULSE.

> SINE, TRNGL, SQUARE, POSPULSE and NEGPULSE (bits 2Ah.1 to 2Ah.5) are
> produced by the TWS directly, ARBIT (2Bh.4) runs through a path of its
> own and is not part of the expression.

So the waveform RAM feeds the output for **five of the twelve waveforms**,
not for all of them. After a cold start the selected waveform is SINE
(2Ah = 02h), which the TWS makes directly — the chord was written into a
memory nothing was reading, and the instrument played its TWS waveform at
f0, one octave below the melody. A ~41 Hz tone changing every 107 ms is
exactly what motorboating sounds like.

This is worth stating plainly because it contradicts the natural reading
of the service manual quote at the top of this section: the CPU does load
every waveform into the RAM, but only some waveforms are then *read* from
it. Loading the table is necessary and not sufficient.

`mkpoly.py` therefore selects the waveform itself before loading:

```
MOV 2Ah,#00h        ; DC, SINE, TRNGL, SQUARE, both pulses, both sawtooths
CLR 2Bh.2 / 2Bh.3   ; SINEPULSE, TRNGLPULSE
CLR 2Bh.4           ; not ARBIT — that would reload from the EEPROM
CLR 2Bh.1 / SETB 2Bh.1   ; HAV, one of the five
SETB P3.4           ; PGS, because the expression at 0953h does not run
                    ; from inside the diagnostic menu
```

2Bh.6 is deliberately left alone; it is not part of the one-hot waveform
code. Measured before and after entering menu item 8:

| | 2Ah | 2Bh | selected |
|---|---|---|---|
| after cold start | 02h | 40h | SINE — TWS direct |
| after the selection | 00h | 42h | HAV — reads the RAM |

**Open, to be settled on the instrument:** whether HAV is the best of the
five for this. All five read the RAM, but they differ in what else the
firmware does for them (amplitude correction per waveform, the asymmetry
byte on STR3), and none of that dependent state is set up by the player.

### 36.6 The second burn — a waveform is nineteen telegrams

Selecting a RAM waveform by setting 2Ah/2Bh was still not enough: on the
instrument the five probe stages produced their five frequencies
correctly and the shape never changed. Setting those bits is only
firmware state; the analog routing lives in shift registers.

`cmd16.js` says what a real waveform command costs — 29h = 06h and

```
token 18h HAV   STR1 STR2 STR3 STR6 STR7 STR9
```

and recorded in order (V1.3, token 18h) it is **nineteen telegrams**:

| # | | # | | # | |
|---|---|---|---|---|---|
| 1 | STR6 `D0 07 20 01` | 8 | STR6 `25 00 20 01` | 15 | STR7 `57 64` |
| 2 | STR3 `80 01` | 9 | STR2 (bare) | 16 | STR7 `14 64` |
| 3 | STR9 `00` | 10 | STR1 2050 bytes | 17 | STR7 `14 64` |
| 4 | STR6 `00 00 00 60` | 11 | STR6 `00 00 00 60` | 18 | STR7 `14 64` |
| 5 | **STR2 `00 80`** | 12 | STR1 `00 20` | 19 | STR9 `6E` |
| 6 | STR1 `00 20` | 13 | STR1 `00 19` | | |
| 7 | STR1 `00 2E` | 14 | STR6 `D0 07 20 01` | | |

The first player sent **three** of these — 8, 9 and 10. Entry 5 is the
one that hurts: `STR2 00 80` is what puts the waveform RAM into write
mode. Without it the 2048 bytes go out on the bus and land nowhere,
which is precisely what the instrument showed.

Two more corrections fell out of the same recording. The setup index is
waveform specific — the byte comes from the table at 4335h
(`1E 24 24 25 2C 34 13 1A`) and becomes 14h of a frequency-format TWS
command, so index 0 (1Eh) is the SINE case, 1 is TRNGL/TRNGLPULSE and
**3 (25h) is HAV**; the player had hardcoded 0. And the state dispatcher
at 090Ch/0975h **cannot be called as a subroutine** from the diagnostic
menu — measured, it never returns and ends in the main loop at 526Eh.

`mkpoly.py` therefore replays the recorded list from a table in ROM with
its own send routine, substituting our chord for entry 10. Entries 11–14
are left out because the firmware's finish routine, which the loader
tail-jumps to, emits them itself. Verified against the recording:

```
16 of 19 telegrams identical, the rest being one duplicated STR1 00 19
```

Note also that this recording contradicts the reading in section 12 that
SINE is produced by the TWS directly: **SINE loads a 2050-byte table
too**, and its STR3 word (`80 01`) is the same as HAV's. Whatever PGS
distinguishes, it is not "reads the RAM or not". That question is open
again.

### 36.7 The wire format, settled on the instrument

The emulator models no waveform RAM, so three burns went by on inference
alone. The fourth carried a **test suite**: six tables, three seconds
each at one fixed frequency, each designed so that one glance at a scope
answers one question. What came back:

| # | Table | Expected if right | Observed |
|---|---|---|---|
| 1 | every point 512 | flat line | **flat** |
| 2 | rising ramp, low byte first | clean sawtooth | noise |
| 3 | the same ramp, bytes exchanged | noise | **clean falling ramp** |
| 4 | ramp with the low bit pair zeroed | clean sawtooth | noise |
| 5 | ramp over 512 points, then flat | ramp then flat | square, low part noisy |
| 6 | the chord | smooth, six turns | noise, larger amplitude |

Stage 1 proves the bytes reach the converter at all. Stages 3 and 4 settle
the format between them: in stage 3 the **first** byte carries the ramp
and the output is clean, in stage 4 the **second** byte carries it and the
output is noise. So

> the high eight bits go on the bus **first**, the two low bits second.

This is the format section 36.1 now states. It was inferred the other way round from decoding
the firmware's own download, and the instrument outranks the inference.
`mkchord.pack()` has been corrected; `polytest.js` decodes accordingly.

Stage 5 is consistent: its first half was a ramp in the wrong order
(noise) and its second half a constant (flat), which is exactly the
"square with a noisy low part" that came back. Stage 1 cannot distinguish
the two orders — a constant is a constant either way — which is why it
was put first, as a start-of-cycle marker.

The ramp came out **falling** for a rising table, so the converter output
is inverted. That is left as it is: for a chord it makes no audible
difference, and inverting the table would only hide the fact.

Why the earlier inference was wrong is still open. Decoding the boot
download with the low byte first yields a clean 12-bit sine, which is a
strong-looking result and was accepted too readily; with the byte order
now established the other way, that decode needs redoing. Section 36.1
and this section disagree, and the instrument is right.

### 36.8 Setting the amplitude, and where the attenuator really sits

The first working player produced only about 1 Vpp whatever the front
panel said, because the replayed telegram list carried the amplitude
bytes recorded from a HAV command, and its first STR7 byte was `14h`.

Driving the output routine over the whole range settles both the encoding
and a contradiction the documents had carried unresolved (section 20 put
the attenuator in the first STR7 byte, section 30 on S2..S5 of STR9).
Measured on V2.0, with 10h poisoned to defeat the "nothing changed" gate:

| 56h | 57h | Nominal | 1Ch | 1Eh | Telegrams |
|---|---|---|---|---|---|
| 32h | 00h | 20 V | 64h | 04h | STR7 `04 64`, STR9 `64` |
| 31h | 00h | 10 V | 32h | 04h | STR7 `04 64`, STR9 `32` |
| 30h | 50h | 5 V | 19h | 04h | STR7 `04 64`, STR9 `19` |
| 22h | 00h | 2 V | 64h | 14h | STR7 `14 64`, STR9 `64` |
| 12h | 00h | 0.2 V | 64h | 1Ch | STR7 `1C 64`, STR9 `64` |

**That reading did not survive the instrument.** Measured on hardware,
with the front panel at 20 Vpp and the player driven from the diagnostic
menu:

| What the player sends | Output |
|---|---|
| neither STR7 nor STR9 | **8.3 Vpp** |
| the recorded STR7 block (first byte 14h) | 1 Vpp |
| STR7 `04 64`, any STR9 | 100 mVpp |
| the amplitude routine at 0B15h | 50 mVpp |

Every configuration that writes STR7 collapses the output, `04h` included
— which is the value the table gives for decade 3, the 20 V range. So the
first STR7 byte is **not** simply the attenuator, and the mapping below is
recorded as what the table contains, not as an established meaning. Note
also that at 0B01h the byte is masked with 27h before it is sent, and
04h, 14h and 1Ch all mask down to the same 04h — so this telegram cannot
be carrying the range at all. The attenuator is somewhere else.

The relays hold their state, so a wrong write is sticky: after the sweep
above, going back to the stage that sends nothing restored the frequency
but not the level.

**What works, and is what `mkpoly.py` does:** send neither STR7 nor STR9
and leave the amplitude chain exactly as the front panel set it before
the diagnostic menu was entered. Also measured: our own chord tables have
a mean of exactly 512.0, i.e. no DC content at all, so the one-sided trace
seen on the scope comes from the DC generator's state and not from the
table.

**Settled with a frequency-keyed matrix.** A burn is expensive, so the
next image packed 31 tests into one and used the *frequency as the test
number* — test n at 100 + n·10 Hz — so the scope's own read-out says which
combination is live and nothing has to be counted. A plain triangle was
used as the waveform because its Vpp is easy to read. Since the relays
hold their state, the question was not "which is loud" but "where does it
become loud again". Observed:

| Test | Result | Conclusion |
|---|---|---|
| 110 Hz, first STR7 write | **clicks** | STR7's first byte drives relays |
| 190 Hz, `07h` → `20h` | **clicks** | the relay is **bit 5** |
| 220 Hz (`23h`) vs 180 Hz (`07h`) | quieter | bit 5 set = attenuated |
| 220…260 Hz (`23h`…`27h`) | all equal | bits 0…2 have no level effect |
| 330 Hz (`00 C0`) vs 340 Hz (`00 FF`) | rises | **STR9's second byte is a monotonic amplitude DAC** |
| 350/360/370 Hz (`80/F8/07` + `FF`) | all equal | STR9's **first** byte has no level effect |
| 390 Hz (`FF` single) vs 400 Hz (`37` single) | rises | a **single** STR9 telegram already sets the level — the pair is not needed |
| the whole 300 range | no relay clicks | STR9 is a pure DAC, nothing mechanical |
| 270/280/290 Hz (`18h`, `20h`, `14h`) | **all click** | the relay field is **bits 3, 4 and 5**, not bit 5 alone |

So the model is:

* **STR9, second byte** — the amplitude DAC, monotonic over 00h…FFh. One
  telegram — a single one is enough, the pair is not required — with no
  relays and no range switching. At the measured 49 µs for a one-byte STR9
  telegram, a 1 kHz envelope costs about 5 % of the CPU. **This is the
  envelope primitive.**
* **STR9, first byte** — no audible effect. Section 30's reading, that
  S1..S5 and the low DAC bits sit here, does not hold for the level.
**Measured completely, 30 s per step, DAC at full scale:**

| bits 5-4-3 | STR7 | Vpp | |
|---|---|---|---|
| 000 | `04h` | 120 mV | both attenuators in, −40 dB |
| 001 | `0Ch` | 1.2 V | one bypassed |
| 010 | `14h` | 1.2 V | the other bypassed |
| **011** | **`1Ch`** | **11.6 V** | **both bypassed, 0 dB** |
| 1xx | +20h | unchanged | bit 5 costs no level (it clicks — most likely K403, the 50/600 Ω relay, invisible to a high-impedance probe) |

So bits 3 and 4 are **two separate 20 dB stages**, which is why 001 and
010 measure the same and switching between them clicks. And the ROM table
`04 1C 14 04` reads the opposite way from what section 20 recorded:
**04h is the most attenuated value and 1Ch the least** — they are bypass
bits, not enable bits. 11.6 V is also more than the 8.2 V the front panel
was giving, so the instrument can be driven harder from here than through
the panel.

**The DAC is effectively seven bits.** Same run, relays fixed:

| DAC | 00h | 20h | 40h | 60h | 80h | A0h | C0h | FFh |
|---|---|---|---|---|---|---|---|---|
| Vpp | 0 | 40 mV | 66 mV | 100 mV | **0** | 40 mV | 62 mV | 120 mV |

It wraps at 80h and starts over, so the usable range is 00h…7Fh and it is
roughly linear inside it. The firmware never leaves that range — it
computes 1Ch = 64h for a full 20 Vpp — which is why the wrap had never
shown up. Writing FFh, as an earlier build did, folds back to 7Fh.

* **STR7, first byte, bits 3, 4 and 5** — the relay field, three bits,
  which fits K401…K404. Bits 0…2 do nothing to the level. The first pass
  of the matrix only covered `00h`…`07h` and `20h`…`27h`, which never set
  bits 3 or 4, and the absence of clicks there was briefly mistaken for
  "bit 5 alone" — the boot values `18h`, `20h` and `14h` at 270/280/290 Hz
  clicked and corrected it.
* This also explains the 27h mask at 0B01h: `27h` does not pass bits 3
  and 4, so that telegram cannot set the attenuator at all.
* Writing STR7 at all is therefore best avoided unless the relay state is
  meant to change; `mkpoly.py` leaves it alone and sets the level with a
  single STR9 pair.

The table below is retained as raw data for whoever picks this up:

| Decade | 1Eh | Attenuation |
|---|---|---|
| 3 | 04h | 0 dB |
| 2 | 14h | 20 dB |
| 1 | 1Ch | 40 dB |

and the amplitude in volts is `W · 10^(decade−4)` with W the three BCD
digits spread over 56h (hundreds) and 57h (tens, units). STR9 carries the
fine value 1Ch, which is `W / 2` before the per-waveform correction of
AMPL_CORRECT — for HAV it comes out at 48h rather than 64h.

**The gate.** Writing 56h/57h and calling the routine does nothing on its
own. At 0B25h (V2.0) it does

```
0B25  MOV A,10h / MOV 1Bh,A / XRL A,1Eh / JZ 0B9Eh
```

— 10h holds the range byte last sent, and if it matches the newly
computed one the routine returns silently. Poisoning 10h with any other
value forces the output. That is the whole recipe:

```
MOV 56h,#<decade and hundreds>
MOV 57h,#<tens and units>
MOV 10h,#0AAh          ; defeat the "nothing changed" gate
LCALL 0B15h            ; V1.5/V2.0; V1.3 is built differently
```

`encode_volts()` in `mkpoly.py` reproduces the firmware's own byte pairs
(20 V → 32h 00h, 10 V → 31h 00h, 5 V → 30h 50h) and the routine does emit
telegrams once the gate is defeated — but on the instrument the result is
50 mVpp, so something in the sequence is still wrong. **The amplitude
question is therefore open, not closed**, and the synthesizer backlog
entry still needs it: an envelope cannot be built on a call whose effect
is not understood.

Note the routine at 0B15h is version specific: V1.3 has the whole thing
inline at 0AACh, while V1.5 and V2.0 split the range-byte computation out
into 0BBAh, which on its own only returns a value and sends nothing —
which is why calling *that* looked like a dead end at first.

### 36.9 The emulators know the analogue side now

Five EPROMs went into the polyphonic player, and the reason was always
the same: the emulator modelled the CPU and the bus but nothing behind
them, so it could only confirm that the right bytes went out. Everything
downstream had to be checked on a scope. That gap is closed for the parts
whose behaviour was measured.

**Modelled**

| | |
|---|---|
| Waveform RAM | 1024 points in `wram`. Two bytes per point out of SBUF, high byte first, latched by the rising edge of DBK on P3.5; a strobe on STR2 resets the address. `wcount` counts the points. |
| STR6 | the main TWS word: N, exponent and command, and the resulting frequency in `afe.hz` |
| STR7 | the relay field (bits 3 and 4, 20 dB each) and the DC offset, 64h being the zero line |
| STR8 | the sweep output DAC |
| STR9 | the amplitude DAC, seven bits, wrapping above 7Fh |
| STR1 | the control word, stored raw |

`c.afeState()` prints one line: frequency, how much of full scale the
table uses, the DAC value, the attenuation and the offset.

**Not modelled, deliberately**

STR3 (pulse generator and amplitude-modulator mux), STR4 (burst counter)
and STR5 (modulation oscillator) are counted in `afe.seen` but their
contents are not interpreted. Their telegram layouts were never pinned
down, and a model that guesses is worse than none — it would agree with
itself and disagree with the instrument, which is exactly the failure
mode this whole section is about.

Nor is there a signal path: nothing computes an output waveform from the
table and the frequency. `polytest.js` now checks the RAM contents
against what `mkchord.py` generated, which is the check that was missing,
but whether that table *sounds* right is still a question for a scope.

**Validation.** The model is anchored on the one case known to be right
on hardware: after the player loads its chord, `wram` holds exactly the
1024 points `mkchord.py` produced, zero differences. The frequency
formula reproduces 41.20 Hz and 82.40 Hz, the two values the player is
known to set.

One thing this brought up. Decoding the *firmware's own* boot download
with the established byte order gives a repeating four-value staircase,
not the smooth sine that the opposite order suggested early on. Either
the firmware's loaders do not all use the same order, or the table loaded
at boot is not what was assumed in 36.1. **Open**, and worth settling,
because it is the last place where our reading of the format and the
firmware's behaviour disagree.

### 36.10 Machine cycles in the emulators

All the times above are measurable only because both emulators now count
machine cycles as well as instructions. `mcs51.CYCLES` holds the table
from the MCS-51 data sheet (162 opcodes at one cycle, 92 at two, `MUL`
and `DIV` at four); `core.js` carries the same 256 entries as a string
and `cyclecheck.py` refuses to let the two drift apart.

The counter is `mcyc` in both cores and is **purely observational** — it
drives no timer and no serial model, so every measurement taken before it
existed still reproduces exactly.

Anchor: stepping the wait loop of `mkdoom.py` reports

| Address | Executions | Cycles |
|---|---|---|
| `MOV R6,#02h` | 1 | 1 |
| `MOV R7,#0FAh` | 2 | 2 |
| `DJNZ R7` | 500 | 1000 |
| `DJNZ R6` | 2 | 4 |
| `DJNZ R5` | 1 | 2 |
| | | **1009** |

so one unit is **1009 µs**, not the 1006 the source assumed — that figure
dropped the `MOV R6` and the `DJNZ R5`. `mkdoom.py` and `mid2ton.py` have
been corrected. Over a whole cold start the ratio comes out at **1.862
machine cycles per instruction**, which is the factor by which every
instruction-count timing in this document was short.
