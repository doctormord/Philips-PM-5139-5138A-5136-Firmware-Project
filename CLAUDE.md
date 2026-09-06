# CLAUDE.md — PM5139 Firmware Reverse Engineering

Arbeitsanweisung für Claude Code in diesem Projektverzeichnis.

## Kontext

Reverse Engineering der Firmware eines Philips PM5139 Funktions­generators,
Baujahr um 1994. Prozessor ist ein PCB80C652 (8051-Kern mit Hardware-I²C)
mit externem 27512-EPROM. Ziel ist, die Firmware so weit zu verstehen,
dass sie geändert und zurückgespielt werden kann — perspektivisch eine
Neuimplementierung.

Lies zuerst `HANDOVER.md` für den Stand und `BACKLOG.md` für die offenen
Punkte. `PM5139_Hardware_Abstraktion.md` ist das Hauptdokument mit 23
Abschnitten; dort steht alles Belegte.

## Sprache

Der Anwender arbeitet auf Deutsch. Antworte auf Deutsch. Kommentare in
Code und Dokumenten ebenfalls auf Deutsch. Bezeichner im Code dürfen
englisch bleiben, wo das üblich ist.

## Arbeitsweise

**Belegen, nicht vermuten.** Jede Aussage über die Firmware braucht
einen Beleg: eine Stelle im Listing, eine Messung im Emulator oder den
Schaltplan. Am besten zwei unabhängige. Wenn etwas nur vermutet ist,
schreib das dazu.

**Der Emulator ist das Messgerät.** `emu.py` (Python) und `core.js`
(JavaScript) führen den Originalcode aus. Für eine Formel: Routine
direkt aufrufen, Eingangswerte variieren, Ausgabe gegen die Vermutung
prüfen. Das hat bei Frequenz, Amplitude, Offset, AM, FM, Burst und
Symmetrie funktioniert und ist der schnellste Weg.

**Eigene Fehler zuerst ausschließen.** In dieser Sitzung waren drei
Emulatorfehler die Ursache für scheinbar unerklärliches Verhalten:
`ACALL` als `AJMP` ausgeführt, fehlendes AC-Flag (dadurch binäre statt
BCD-Arithmetik), doppelt ausgelöster Tastaturinterrupt. Wenn die
Firmware sich unsinnig verhält, ist der Emulator der erste Verdächtige.

**Nicht im Kreis laufen.** Wenn drei Anläufe an derselben Stelle nichts
bringen, das Listing ruhig lesen statt weiter zu probieren. Umgekehrt:
wenn das Listing nicht weiterhilft, messen.

## Werkzeuge

| Datei | Zweck |
|---|---|
| `mcs51.py` | MCS-51-Disassembler, vollständige Opcode-Tabelle |
| `analyze2.py` | Code-Flow-Analyse mit Sprungtabellen |
| `seqdiff.py` | Strukturvergleich V1.3 gegen V1.5 |
| `emu.py` | 8051-Interpreter |
| `system.py`, `system2.py` | Peripherie: Timer, Interrupts, I²C, Strobes |
| `keys.py` | Tastatur- und Drehknopfeinspeisung |
| `core.js` | derselbe Kern in JavaScript, ~8 Mio. Befehle/s |
| `romfix.py` | Prüfsumme prüfen und korrigieren |
| `build.py` | baut `PM5139_Simulator.html` aus `shell.html` und `core.js` |

Node steht zur Verfügung und ist für Messreihen deutlich schneller als
Python. Ein Kaltstart braucht etwa 9 Millionen Schritte.

## Wichtige Adressen

```
V1.3, ROM belegt 0000h–AC70h, Prüfsumme bei AC70h
Reset            3A9Ah        Prüfsummenroutine  3AABh
Befehlstabelle   7752h        Meldungszeiger     803Ch
Kurventabellen   44A7h 46A9h 4AABh A047h A447h A847h
Anzeigepuffer    RAM 30h–43h  Ausgabe            37DBh / 392Fh
Tastendekoder    0227h        Tastennummern      5AABh
Drehknopf        25C2h        Beschleunigung     2622h / 260Eh
Frequenz         50h–52h      Rechnung           0A26h / 09E5h
Amplitude        56h/57h      Rechnung           0B57h / 0AACh
Offset           58h/59h      Rechnung           0A90h
Strobe-Ausgabe   0E54h ff.    Statuslesen        517Dh
```

Strobe-Nummer steht im unteren Nibble von DPH: `MOV DPH,#8nh` gefolgt
von `MOVX @DPTR,A` löst STRn aus, 80h ist der Leerausgang.

## Konventionen

- Zahlen im Text mit `h`-Suffix, wie im Servicemanual: `3A9Ah`, nicht `0x3A9A`.
- Neue Erkenntnisse gehören in `PM5139_Hardware_Abstraktion.md`, mit
  Codeausschnitt und Messtabelle.
- Abgearbeitete Backlog-Punkte streichen, neue Fragen ergänzen.
- Emulatoränderungen immer in beiden Kernen nachziehen, Python und
  JavaScript, sonst driften die Ergebnisse auseinander.
- Nach jeder Änderung an `core.js`: `python3 build.py` und den
  Kaltstart prüfen — er muss fehlerfrei durchlaufen.

## Vorsicht

Ergebnisse aus der mittleren Projektphase sind teilweise mit den oben
genannten Emulatorfehlern entstanden. Betroffen sind die
Anzeige-Bitmap in Abschnitt 15 und die Strobe-Zuordnung in
Abschnitt 16. Vor dem Weiterbauen darauf: nachmessen.
