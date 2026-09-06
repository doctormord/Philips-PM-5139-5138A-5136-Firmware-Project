# HANDOVER — Reverse Engineering Philips PM5139

Stand am Ende der Analysesitzung. Dieses Dokument sagt, was da ist, was
es taugt und wo man weitermacht.

## Worum es geht

Zwei EPROM-Abzüge (M27512, 64 KiB) eines Philips PM5139
Funktionsgenerators, Firmware V1.3 und V1.5. Ziel: verstehen, ändern,
zurückspielen — perspektivisch eine eigene Firmware.

## Das Gerät

- **CPU:** PCB80C652, 8051-Kern mit Hardware-I²C, 12 MHz
- **Programm:** externes EPROM 27512, V1.3 belegt 0000h–AC70h
- **EEPROM D310:** HN58C256, 32K, am MOVX-Bus 0000h–7FFFh, Arbitrary-Kurven
- **NVRAM D305:** PCF8570, 256 Byte am I²C (A0h), batteriegepuffert,
  aktuelle Einstellung und neun Speicherregister
- **Anzeige:** PCF8576 am I²C (70h), 20-Byte-Puffer
- **Tastatur:** SAA3007-Encoder, pulsweitenkodiert auf P3.3
- **Analogteil:** sechs Baugruppen über einen seriellen C-Bus mit
  Strobe-Dekoder (74HCT4514), Strobe-Nummer = A8…A11

## Was fertig ist

| Bereich | Stand |
|---|---|
| Disassembly V1.3 und V1.5 | vollständig, mit XREFs, ~23 000 Zeilen |
| Versionsvergleich | 91,4 % strukturell identisch, alle Änderungen benannt |
| Hardware-Abstraktion | Strobes, Ports, Busse, Speicher — vollständig |
| Befehlstabelle, Meldungen | dekodiert, beide Versionen |
| Anzeige | Puffer, Segmentkodierung, Annunciator-Bits |
| Tastatur | Kodierung, Matrix, alle 23 Tasten benannt |
| Drehknopf | Quadratur, Beschleunigung, Verstellmechanik |
| Frequenzpfad | vollständig gerechnet und geprüft |
| Amplitude, Offset, AM, FM, Burst, Symmetrie | vollständig gerechnet und geprüft |
| Selbsttest, Fehlercodes | alle sieben Programme, alle Err-Codes |
| Prüfsumme | Werkzeug vorhanden, Rückspielen erprobt |
| Emulator Python und JavaScript | bootet fehlerfrei, Tastatur, Knopf, Anzeige |
| Browser-Simulator | eine HTML-Datei, ohne Abhängigkeiten |

## Was nicht fertig ist

- **Sweep:** Struktur klar, Skalierung von fSTART/fSTOP auf den
  Akkumulator fehlt
- **Schnittstelle:** Protokoll zur Karte auf I²C-Adresse 5Eh unberührt
- **Rund 1 900 ROM-Bytes** weder als Code noch als Tabelle klassifiziert
- **74 von 128 Zustandsbits** ohne bekannte Bedeutung
- **Drehknopf im Emulator:** eine Richtung arbeitet, die andere löst
  eine Initialisierung aus statt einer Verstellung

## Verlässlichkeit

Alles, was als „geprüft" gekennzeichnet ist, wurde durch direkten
Aufruf der Originalroutinen im Emulator über mehrere Stützstellen
bestätigt, meist zusätzlich gegen das Listing oder den Schaltplan.

Vorsicht bei Ergebnissen aus der Mitte der Sitzung: Im Emulator waren
zeitweise drei Fehler aktiv, die später behoben wurden — `ACALL` wurde
als `AJMP` ausgeführt, das Hilfsübertrag-Flag AC fehlte, und die
Tasteneinspeisung löste INT1 doppelt aus. Die Anzeige-Bitmap aus
Abschnitt 15 und die Strobe-Zuordnung aus Abschnitt 16 sind danach nur
stichprobenweise nachgeprüft.

## Dateien

| Datei | Inhalt |
|---|---|
| `PM5139_Hardware_Abstraktion.md` | Hauptdokument, 23 Abschnitte |
| `PM5139_Firmware_modifizieren.md` | Anleitung zum Ändern und Zurückspielen |
| `PM5139_Tabellen.md` | Befehls- und Meldungstabellen beider Versionen |
| `PM5139_V13_disasm.asm`, `..._V15_...` | Disassembly |
| `PM5139_Diff_V13_V15.txt` | Blockweiser Vergleich |
| `PM5139_Kurvenformen.png` | Alle ROM-Kurventabellen geplottet |
| `PM5139_Bit_Kreuzreferenz.md` | Flags 20h–2Fh, Setz-/Lösch-/Abfragestellen |
| `PM5139_Simulator.html` | Browser-Simulator, alles inline |
| `romfix.py` | Prüfsumme prüfen und korrigieren |
| `emu.py`, `system.py`, `system2.py`, `keys.py` | Python-Emulator |
| `core.js` | JavaScript-Emulator |
| `mcs51.py`, `analyze2.py`, `seqdiff.py` | Disassembler und Analyse |
| `D310_abbild.bin`, `PCF8570_abbild.bin` | erzeugte Speicherabbilder |
| `patch_ok.bin` | Beispiel: geändertes ROM mit korrigierter Prüfsumme |

## Quellen

- Servicemanual PM 5138A (Fluke 1994) — Schwestermodell, Digitalteil
  identisch. Zwei Scans vorhanden, beiden fehlen die Seiten 4-3 bis 4-28.
- Bedienungshandbuch PM5139 (Fluke 1997) — Fehlercodes, Bedienlogik.
- Kein PM5139-Servicemanual auffindbar; seit 2010 in Foren gesucht.
