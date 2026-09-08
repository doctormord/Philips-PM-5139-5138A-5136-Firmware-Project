# Philips PM5139 — decoded firmware tables

CPU: MCS-51 with PCA (8xC51FA/FB class), 64 KiB of external program ROM (M27512).

## Command table

Entry format: 16 bytes = 14 bytes of name (padded with 00) + 2 bytes of
token. Token byte 1 applies when the command is followed by a parameter
or a `?`, token byte 2 when it stands alone. `00` means "not permitted in
this form". Example: `*STB` = `C4 00` -> query only; `*RST` = `00 C9` ->
standalone only; `*ESE` = `C2 C2` -> both.

Location: V1.3 from 7752h (131 entries, up to 7F81h) · V1.5 from 79E5h
(139 entries, up to 8294h)

| Command | Tok1 | Tok2 | V1.3 | V1.5 |
|---|---|---|---|---|
| `#ACOFF` | 00 | 32 | x | x |
| `#ACON` | 00 | 33 | x | x |
| `#AMLIN` | 00 | 29 | x | x |
| `#AMLOG` | 00 | 2A | x | x |
| `#AROFF` | 00 | 69 | x | x |
| `#ARON` | 00 | 68 | x | x |
| `#BU` | 00 | 28 | x | x |
| `#BUOFF` | 00 | 45 | x | x |
| `#BUON` | 00 | 47 | x | x |
| `#CLARB` | 00 | 60 | x | x |
| `#CLARBITRARY` | 00 | 60 | x | x |
| `#DCOFF` | 00 | 34 | x | x |
| `#DCON` | 00 | 35 | x | x |
| `#LOOFF` | 00 | 36 | x | x |
| `#LOON` | 00 | 37 | x | x |
| `#MOAM` | 00 | 22 | x | x |
| `#MOBURST` | 00 | 28 | x | x |
| `#MOEXTERNAL` | 00 | 2F | x | x |
| `#MOFM` | 00 | 23 | x | x |
| `#MOGATE` | 00 | 25 | x | x |
| `#MOINTERNAL` | 00 | 2E | x | x |
| `#MOOFF` | 00 | 21 | x | x |
| `#MOPSK` | 00 | 24 | x | x |
| `#SWLIN` | 00 | 26 | x | x |
| `#SWLOG` | 00 | 27 | x | x |
| `#SWOFF` | 00 | 44 | x | x |
| `#SWON` | 00 | 46 | x | x |
| `#SYOFF` | 00 | 1E | x | x |
| `#SYON` | 00 | 1F | x | x |
| `#TRCONTINUOUS` | 00 | 4F | x | x |
| `#TREXTERNAL` | 00 | 42 | x | x |
| `#TRINTERNAL` | 00 | 41 | x | x |
| `#TROFF` | 00 | 41 | x | x |
| `#TRSINGLE` | 00 | 4E | x | x |
| `*CLS` | 00 | C8 | x | x |
| `*ESE` | C2 | C2 | x | x |
| `*ESR` | C5 | 00 | x | x |
| `*IDN` | 72 | 00 | x | x |
| `*LRN` | 71 | 00 | x | x |
| `*OPC` | CB | CB | x | x |
| `*RCL` | 00 | 52 | x | x |
| `*RST` | 00 | C9 | x | x |
| `*SAV` | 00 | 51 | x | x |
| `*SRE` | C1 | C1 | x | x |
| `*STB` | C4 | 00 | x | x |
| `*TRG` | 00 | 48 | x | x |
| `*TST` | CC | 00 | x | x |
| `*WAI` | 00 | CA | x | x |
| `AC` | 00 | FF | x | x |
| `ACOFF` | 00 | 32 | x | x |
| `ACON` | 00 | 33 | x | x |
| `AM` | 00 | 22 | x | x |
| `AMDEPTH` | 86 | 86 | x | x |
| `AMPL` | 83 | 83 | x | x |
| `AMPLITUDE` | 83 | 83 | x | x |
| `AMPLT` | 83 | 83 | x | x |
| `AMSWEEP` | 00 | FF | x | x |
| `ARB` | 60 | 1B | x | x |
| `ARBE` | 68 | FF | x | — |
| `ARBEXECUTE` | 68 | FF | — | x |
| `ARBIT` | 60 | 1B | x | x |
| `ARBITEXECUTE` | 68 | FF | x | x |
| `ARBITRARY` | 60 | 1B | x | x |
| `ARBITSELECT` | 66 | 66 | x | x |
| `ARBSELECT` | 66 | 66 | x | x |
| `BEGIN` | 61 | 61 | x | x |
| `BURST` | 00 | FF | x | x |
| `CLEAR` | 00 | FF | x | x |
| `CNT` | 62 | 62 | x | x |
| `CONTINUOUS` | 00 | 4A | x | x |
| `COUNT` | 62 | 62 | x | x |
| `DATA` | 00 | 64 | x | x |
| `DC` | 00 | FF | x | x |
| `DCOFF` | 00 | 34 | x | x |
| `DCOFFSET` | 84 | 84 | x | x |
| `DCON` | 00 | 35 | x | x |
| `DUTYCYCLE` | 8B | 8B | x | x |
| `ENABLE` | 00 | 39 | x | x |
| `ERROR` | 90 | 00 | x | x |
| `FILL` | 00 | 63 | x | x |
| `FM` | 00 | 23 | x | x |
| `FMDEV` | 87 | 87 | — | x |
| `FMDEVIATION` | 87 | 87 | x | x |
| `FMDEVTN` | 87 | 87 | — | x |
| `FREQUENCY` | 81 | 81 | x | x |
| `GATE` | 00 | 25 | x | x |
| `HAV` | 00 | 18 | x | x |
| `HAVERSINE` | 00 | 18 | x | x |
| `HAVSINE` | 00 | 18 | x | x |
| `HOLD` | 00 | 4D | x | x |
| `LOIMP` | 31 | FF | x | x |
| `LOWIMPEDANCE` | 31 | FF | x | x |
| `MODFREQ` | 85 | 85 | x | x |
| `MODLN` | 20 | FF | x | x |
| `MODLNFREQ` | 85 | 85 | x | x |
| `MODOFF` | 00 | 21 | x | x |
| `MODSRC` | A0 | FF | x | x |
| `NEGPULSE` | 00 | 15 | x | x |
| `NEGSAW` | 00 | 17 | — | x |
| `NEGSAWTH` | 00 | 17 | — | x |
| `NEGSAWTOOTH` | 00 | 17 | x | x |
| `ONPERIODS` | 89 | 89 | x | x |
| `OUTPUT` | 30 | 00 | x | x |
| `POSPULSE` | 00 | 14 | x | x |
| `POSSAW` | 00 | 16 | — | x |
| `POSSAWTH` | 00 | 16 | — | x |
| `POSSAWTOOTH` | 00 | 16 | x | x |
| `PSK` | 00 | 24 | x | x |
| `PULSE` | 00 | 14 | x | x |
| `RELEASE` | 00 | 4C | x | x |
| `SAW` | 00 | 16 | — | x |
| `SAWTH` | 00 | 16 | — | x |
| `SAWTOOTH` | 00 | 16 | x | x |
| `SGLE` | 00 | 49 | x | x |
| `SINE` | 00 | 11 | x | x |
| `SINEPULSE` | 00 | 19 | x | x |
| `SINGLE` | 00 | 49 | x | x |
| `SQR` | 00 | 13 | x | x |
| `SQUARE` | 00 | 13 | x | x |
| `STARTFREQ` | 81 | 81 | x | x |
| `STARTPHASE` | 8A | 8A | x | x |
| `STFREQ` | 81 | 81 | x | x |
| `STOPFREQ` | 82 | 82 | x | x |
| `STPHASE` | 8A | 8A | x | x |
| `SWEEP` | D0 | FF | x | x |
| `SWEEPMODE` | 8C | 8C | x | x |
| `SWEEPTIME` | 88 | 88 | x | x |
| `SYMMETRY` | 32 | FF | x | x |
| `TRGFUNCTION` | 48 | FF | x | x |
| `TRGSRC` | 40 | FF | x | x |
| `TRIGFUNCTION` | 48 | FF | x | x |
| `TRIGS` | 40 | FF | x | x |
| `TRIGSOURCE` | 40 | FF | x | x |
| `TRIGSRC` | 40 | FF | x | x |
| `TRM` | 00 | C4 | x | x |
| `TRNG` | 00 | 12 | x | x |
| `TRNGL` | 00 | 12 | x | x |
| `TRNGLE` | 00 | 12 | x | x |
| `TRNGLPULSE` | 00 | 1A | x | x |
| `WAVEFORM` | 10 | 00 | x | x |

New in V1.5: `SAW`, `SAWTH`, `POSSAW`, `POSSAWTH`, `NEGSAW`, `NEGSAWTH`,
`FMDEV`, `FMDEVTN`, `ARBEXECUTE`. Gone: `ARBE` (renamed to `ARBEXECUTE`).
Not a single token has changed.

## Message table

A pointer table with 16-bit big-endian pointers; the strings are
length-prefixed (first byte = number of characters). Output routine:
V1.3 8014h, V1.5 8327h (index in R4, appends the text to the buffer at
4Fh).

Location: V1.3 803Ch (124 entries) · V1.5 834Fh (126 entries)

| Idx V1.3 | Idx V1.5 | Text |
|---|---|---|
| 0 | 0 | ` ` |
| 1 | 1 | `ACON;` |
| 2 | 2 | `ACOFF;` |
| 3 | 3 | `DCON` |
| 4 | 4 | `DCOFF` |
| 5 | 5 | `SYM ON` |
| 6 | 6 | `SYM OFF` |
| 7 | 7 | `SINE` |
| 8 | 8 | `TRNG` |
| 9 | 9 | `SQUA` |
| 10 | 10 | `POSPUL` |
| 11 | 11 | `NEGPUL` |
| 12 | 12 | `SAW` |
| 13 | 13 | `NEGSAW` |
| 14 | 14 | `HAVER` |
| 15 | 15 | `SINEP` |
| 16 | 16 | `TRNGLP` |
| 17 | 17 | `ARBIT` |
| 18 | 18 | `STARTF` |
| 19 | 19 | `FREQ` |
| 20 | 20 | `STOPF` |
| 21 | 21 | `AMPLT` |
| 22 | 22 | `DCOFFS` |
| 23 | 23 | `MODFRE` |
| 24 | 24 | `AMDEP` |
| 25 | 25 | `FMDEV` |
| 26 | 26 | `SWEEPT` |
| 27 | 27 | `ONPER` |
| 28 | 28 | `STARTP` |
| 29 | 29 | `DUTYC` |
| 30 | 30 | `SWEEPM` |
| 31 | 31 | `MODOFF` |
| 32 | 32 | `MODLN AM` |
| 33 | 33 | `MODLN FM` |
| 34 | 34 | `MODLN PSK` |
| 35 | 35 | `MODLN GATE` |
| 36 | 36 | `SWEEP LIN` |
| 37 | 37 | `SWEEP LOG` |
| 38 | 38 | `MODLN BUR` |
| 39 | 39 | `MODSRC INT` |
| 40 | 40 | `MODSRC EXT` |
| 41 | 41 | `TRGS INT` |
| 42 | 42 | `TRGS EXT` |
| 43 | 43 | `TRIGF SING` |
| 44 | 44 | `TRIGF CONT` |
| 45 | 45 | `HOLD` |
| 46 | 46 | `BEGIN` |
| 47 | 47 | `COUNT` |
| 48 | 48 | `DATA` |
| 98 | 49 | `OUTPUT OVERLOADED` |
| 50 | 50 | `TRIGF` |
| 51 | 51 | `ON` |
| 52 | 52 | `OFF` |
| 53 | 53 | `*TRG` |
| 109 | 54 | `NO SWEEP SELECTED` |
| 55 | 55 | `TRIGF OFF` |
| 56 | 56 | `LOIMP OFF` |
| 57 | 57 | `LOIMP ON` |
| 58 | 58 | `AMSWE LIN` |
| 59 | 59 | `AMSWE LOG` |
| 60 | 60 | `ARBE ON` |
| 61 | 61 | `ARBE OFF` |
| 62 | 62 | `BEG ` |
| 63 | 63 | `CNT ` |
| 64 | 64 | `ARB ` |
| 65 | 65 | `ARBSEL ` |
| 66 | 66 | `NO ARBITRARY AVAILABLE` |
| 67 | 67 | `TRIGS OFF` |
| **—** | 68 | `IMP 600` |
| **—** | 69 | `IMP 50` |
| 68 | 70 | `NO ERROR` |
| 69 | 71 | `SYNTAX ERROR` |
| 70 | 72 | `ILLEGAL HEADER` |
| 71 | 73 | `BODY SYNTAX ERROR` |
| 72 | 74 | `DATA OUT OF RANGE` |
| 73 | 75 | `NO QUERY HEADER` |
| 99 | 76 | `NO ARBITRARY DATA` |
| 75 | 77 | `FREQUENCY OUT OF RANGE` |
| 76 | 78 | `STOP FREQUENCY OUT OF RANGE` |
| 77 | 79 | `AMPLITUDE OUT OF RANGE` |
| 78 | 80 | `DC OFFSET OUT OF RANGE` |
| 79 | 81 | `MOD.FREQUENCY OUT OF RANGE` |
| 80 | 82 | `AM DEPTH OUT OF RANGE` |
| 81 | 83 | `FM DEVIATION OUT OF RANGE` |
| 82 | 84 | `SWEEP TIME OUT OF RANGE` |
| 83 | 85 | `BURST PERIOD OUT OF RANGE` |
| 84 | 86 | `BURST PHASE OUT OF RANGE` |
| 85 | 87 | `DUTY CYCLE OUT OF RANGE` |
| 86 | 88 | `ILLEGAL SWEEP MODE` |
| 87 | 89 | `AMPLITUDE+DC OFFSET OUT OF RANGE` |
| 88 | 90 | `INCOMPATIBLE FREQUENCY / WAVEFORM` |
| 89 | 91 | `INCOMPATIBLE AMPLITUDE / WAVEFORM` |
| 90 | 92 | `INCOMPATIBLE DUTY CYCLE / WAVEFORM` |
| 91 | 93 | `INCOMPATIBLE DUTY CYCLE / FREQUENCY` |
| 92 | 94 | `INCOMPATIBLE FREQUENCY / BURST PARAMETERS` |
| 93 | 95 | `NO EXTERNAL MODULATION POSSIBLE` |
| 94 | 96 | `NO SWEEP OR BURST SELECTED` |
| 95 | 97 | `NO EXTERNAL TRIGGER POSSIBLE` |
| 96 | 98 | `ILLEGAL REGISTER ADDRESS` |
| 97 | 99 | `NO DATA STORED` |
| 98 | 100 | `OUTPUT OVERLOADED` |
| 99 | 101 | `NO ARBITRARY DATA` |
| 100 | 102 | `CHECKSUM ERROR` |
| 101 | 103 | `VALUE OUT OF RANGE` |
| 102 | 104 | `ADDRESS OUT OF RANGE` |
| 103 | 105 | `TIME OUT` |
| 104 | 106 | `STOP SWEEP FIRST` |
| 105 | 107 | `EEPROM ERROR` |
| 106 | 108 | `AMPLITUDE OF ARBITRARY OUT OF RANGE` |
| 107 | 109 | `AMPLITUDE CORRECTED` |
| 108 | 110 | `HOLD NOT POSSIBLE` |
| 109 | 111 | `NO SWEEP SELECTED` |
| 110 | 112 | `NO BURST SELECTED` |
| 111 | 113 | `EXTERNAL RAM ERROR` |
| 112 | 114 | `BACKUP ERROR` |
| 113 | 115 | `NO TRIGGER POSSIBLE` |
| 114 | 116 | `NO OUTPUT DATA AVAILABLE` |
| 115 | 117 | `OUTPUT DATA DESTROYED` |
| 116 | 118 | `INCOMPATIBLE WAVEFORM / MODULATION` |
| 117 | 119 | `INCOMPATIBLE MOD.FREQUENCY / MODULATION` |
| 118 | 120 | `INCOMPATIBLE STOP FREQUENCY / WAVEFORM` |
| 119 | 121 | `INCOMPATIBLE FREQUENCY / FM-DEVIATION` |
| 120 | 122 | `INCOMPATIBLE FREQUENCY / STOP FREQUENCY` |
| 121 | 123 | `ILLEGAL MEMORY ADDRESS` |
| 122 | 124 | `INCOMPATIBLE AMPLITUDE / LOW IMPEDANCE` |
| 123 | 125 | `UNKNOWN ERROR` |

Only `IMP 600` (44h) and `IMP 50` (45h) are new; all the other texts are
identical character for character, but shifted by 2 from index 68 on.

## Jump tables (JMP @A+DPTR)

| V1.3 | V1.5 | Entries | Stride |
|---|---|---|---|
| 0301h | 0570h | 15 | 2 (AJMP/SJMP) |
| 0421h | 02D2h | 5 | 2 |
| 29DBh | 2A8Ah | 15 | 4 |
| 5A0Bh | 5B7Fh | 8 | 3 (LJMP) |
| 6C06h | 6E86h | 16 | 2 |
| 9BCAh | ABBAh | 10 | 2 |
| 9C7Dh | AC70h | 9 | 2 |
| 9CF6h | ACF1h | 9 | 2 |
| — | B027h | 6 | 2 (V1.5 only, a new menu) |

## Configuration code in RAM 68h (only evaluated by V1.5)

    68h = 24h + (d1-1) + (d2-1)*9 + b1*27 + b2*54 + b3*108
          d1 = 1..9, d2 = 1..3, b1/b2/b3 = 0/1   -> 216 Kombinationen

Decoding: B21Fh (d1), B286h (d2), B267h (b1), B2B8h (b2), B2A3h (b3).
b1 drives bit 25h.0, which the new messages `IMP 50`/`IMP 600` hang on.
Input through the state machine AF3Bh/B0BAh, called on key code 0Ch (only
when 68h & E0h != 0). Reset defaults: 2Bh resp. 14h.
