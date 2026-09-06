#!/usr/bin/env python3
"""PM5139/PM5138A: Prüfsumme eines EPROM-Abbilds prüfen und korrigieren.

Die Firmware summiert beim Einschalten alle Bytes von 0000h bis zu einer
Endadresse und vergleicht mit dem Byte unmittelbar danach. Stimmt es nicht,
zeigt sie Err 1 und bleibt in einer Endlosschleife stehen.

Die Endadresse steht im ROM selbst: die Prüfroutine lädt sie mit
    MOV 10h,#hi   (75 10 hi)
    MOV 11h,#lo   (75 11 lo)
"""
import sys, re

def endadresse(rom):
    """Endadresse aus der Prüfroutine lesen."""
    treffer = []
    for m in re.finditer(rb'\x75\x10(.)\x75\x11(.)', rom):
        adr = (m.group(1)[0] << 8) | m.group(2)[0]
        if 0x8000 <= adr < 0x10000:          # plausibler ROM-Umfang
            treffer.append((m.start(), adr))
    if not treffer:
        raise SystemExit('Prüfroutine nicht gefunden')
    return treffer[-1]

def summe(rom, ende):
    s = 0
    for i in range(0, ende + 1):
        s = (s + rom[i]) & 0xFF
    return s

def pruefen(rom):
    stelle, ende = endadresse(rom)
    ist = summe(rom, ende)
    soll = rom[ende + 1]
    return stelle, ende, ist, soll

def main(argv):
    if len(argv) < 2:
        print(__doc__)
        print('Aufruf:  romfix.py <abbild.bin> [ausgabe.bin]')
        return 1
    rom = bytearray(open(argv[1], 'rb').read())
    stelle, ende, ist, soll = pruefen(rom)
    print('Prüfroutine bei %04Xh, Bereich 0000h–%04Xh' % (stelle, ende))
    print('Prüfsummenbyte liegt bei %04Xh' % (ende + 1))
    print('  gespeichert: %02Xh' % soll)
    print('  berechnet  : %02Xh' % ist)
    if ist == soll:
        print('  -> stimmt, das Abbild startet fehlerfrei')
    else:
        print('  -> falsch, das Gerät würde Err 1 zeigen')
    if len(argv) > 2:
        rom[ende + 1] = ist
        open(argv[2], 'wb').write(bytes(rom))
        print('korrigiert geschrieben nach %s' % argv[2])
        _, _, i2, s2 = pruefen(rom)
        print('Gegenprobe: berechnet %02Xh, gespeichert %02Xh -> %s'
              % (i2, s2, 'ok' if i2 == s2 else 'FEHLER'))
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
