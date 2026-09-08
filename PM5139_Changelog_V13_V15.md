# What changed from firmware V1.3 to V1.5

A comparison of the two EPROM dumps that were read out (M27512, 64 KiB
each) of a Philips PM5139. Everything here is documented in the code:
through structural comparison (`seqdiff.py`, `mapv15.py`), by reading out
the tables, or by measurement in the emulator. Where something is only
assumed, it says so.

An intermediate version V1.4 is not available; whether it ever existed is
unknown.

---

## Key figures

| | V1.3 | V1.5 |
|---|---|---|
| occupied ROM range | 0000h–AC70h | 0000h–B3CAh |
| size | 44 145 bytes | 46 027 bytes (**+1 882, +4.3 %**) |
| checksum | at AC70h, value F2h | at B3CAh, value 99h |
| command table | 7752h, 131 entries | 79E5h, **139** entries |
| message table | 803Ch, 124 pointers | 834Fh, **126** pointers |
| identification string | AC55h, `…,V1.3/0000` | B3AFh, `…,V1.5/0000` |

Structurally **91.4 %** of the instruction sequences are identical. So
V1.5 is not a rebuild but a further development of the same code base.

---

## Visible to the user

### Display of the output impedance

V1.5 brings two new message texts that do not exist anywhere in V1.3:

```
IMP 50
IMP 600
```

That is the switch between 50 Ω and 600 Ω which the data sheet lists for
the **PM5138A** (the PM5139 has a low-impedance position instead of
600 Ω). V1.3 has no display for it.

An obvious reading: V1.5 is a version maintained across the model range
that also serves the 600 Ω variant. What is documented is only that the
texts are present — not which instrument displays them.

### New short forms for remote control commands

Eight additional entries in the command table, all with **the same
token** as a command that already exists. So they are pure spelling
variants, not new functions:

| New in V1.5 | Token | equivalent to |
|---|---|---|
| `FMDEV`, `FMDEVTN` | 87h | `FMDEVIATION` |
| `SAW`, `SAWTH` | 16h | `SAWTOOTH` |
| `POSSAW`, `POSSAWTH` | 16h | `POSSAWTOOTH` |
| `NEGSAW`, `NEGSAWTH` | 17h | `NEGSAWTOOTH` |

On top of that, **`ARBE` was renamed to `ARBEXECUTE`** (token 68h stays).
`ARBITEXECUTE` already existed in V1.3, where the short form was called
`ARBE`.

Anyone who wrote control programs for V1.3 using `ARBE` has to adapt them
for V1.5 — that is the only change found that can break existing
programs.

---

## Under the hood

### The device address: BCD in V1.3, binary in V1.5

The most tangible internal difference. RAM cell 68h holds the
IEEE-488/RS-232 address, but in different encodings:

```
V1.3  3C38  MOV 68h,#20h        ; BCD 20, i.e. 0010 0000
V1.5  3C38  MOV 68h,#14h        ; binary 20, i.e. 0001 0100
```

Accordingly V1.3 tests against `#31h` (BCD for address 31), V1.5 against
`#1Fh`. V1.3 converts before sending to the interface card, V1.5 sends
directly.

**In exchange V1.5 brings a migration**, at 3C1Fh: on the first start
after the firmware change, an address found in the old format is
converted. A step back from V1.5 to V1.3 does not have this safeguard —
a binary stored address then lands in a BCD evaluation. In practice that
means: **set the device address again after a downgrade.**

### The I²C device is initialised differently

At two places V1.3 clears `S1CON.6`, the enable bit of the hardware I²C
controller in the PCB80C652. In V1.5 **both** clear instructions are
missing; the reset still sets ENS1.

Why is not settled. Since the firmware handles the I²C traffic in
software over P1.6/P1.7 anyway, the controller has no functional role —
it looks like the removal of dead code.

### Where things were rebuilt

The structural comparison maps 130 of 147 named routines onto V1.5
automatically. The seventeen for which that fails lie strikingly close
together:

| Area | affected routines |
|---|---|
| **interface** | `IFACE_HANDLER`, `IFACE_ADDRESS`, `IFACE_STATUSCMD`, `IFACE_COMMAND`, `IFACE_ADDR_BCD`, `IFACE_ENABLE` |
| **parameter entry** | `PARAM_LOAD`, `PARAM_DIGIT`, `TAB_PARAM_ADDR`, `PARAM_LIMIT` |
| other | `KEY_DIALLOCK`, `CHECKSUM`, `LOAD_SINE_B`, `ARG_NUMBER`, `TAB_MESSAGES`, `ARB_PART_932A`, `ARB_RECORD_LOAD` |

That `IFACE_ADDR_BCD` has no counterpart at all in V1.5 fits the address
change: the conversion is no longer needed.

So the focus of the changes lies **on the remote control and the
parameter entry**, not in the signal path.

### Shifts

The code grows in several places; the most frequent shifts against V1.3
are **+159, +142 and +135 bytes**. Addresses from V1.3 therefore cannot
be converted with a fixed offset — `mapv15.py` does it through the
structural comparison.

---

## What has stayed unchanged

Worth noting, because it bounds the reach of the change:

- **The parameter limits** (table 12D2h → 134Fh) are **byte-identical**:
  `2001 0201 0021 0011 0011 0011 0021 0101 0201 0019 0010 0101 301D`.
  So the frequency, amplitude and offset limits have stayed the same.
- **The signal path**: frequency computation, amplitude, offset, sweep,
  burst, modulation and the arithmetic library agree structurally.
- **The strobe assignment** and the number of bytes per telegram.
- **The dead code** for I²C address 5Ah (9AFFh in V1.3, B2F2h in V1.5)
  is present in both versions and without a caller in both. Presumably a
  factory diagnostic or a device variant.
- **No model byte**: neither V1.3 nor V1.5 contains the strings `5136` or
  `5138`; `PM5139` occurs exactly once, in the identification string. The
  firmware is burnt per model.

---

## Practical notes on the change

- **Checksum.** Both versions check the sum over the occupied range at
  power-up and expect it at its end. Whoever patches has to carry it
  along; `romfix.py` does that for both versions.
- **NVRAM.** The content stays in the same format (10 records, 26 bytes
  per record, the check mark being a byte sum with start value AAh). Only
  the device address at FEh/FFh is affected by the encoding change.
- **Arbitrary EEPROM.** Format and directory are unchanged; the image
  that was read out is accepted by both versions.
- **Downgrade to V1.3**: possible, but set the device address again
  afterwards (see above). Control programs using `ARBE` then work again —
  those using `ARBEXECUTE` or the new short forms do not.

---

## How to reproduce this

```bash
python3 seqdiff.py          # structural comparison, produces PM5139_Diff_V13_V15.txt
python3 mapv15.py           # address mapping V1.3 -> V1.5, shows the outliers
python3 annotate.py 15      # annotated V1.5 listing
python3 romfix.py           # check and correct the checksum
```

The command and message tables of both versions sit side by side in
`PM5139_Tables.md`.
