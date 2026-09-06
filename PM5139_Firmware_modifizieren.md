# PM5139 — Firmware ändern und zurückspielen

Stand des Reverse Engineering, übersetzt in eine Anleitung: was heute
schon sicher geändert werden kann, wie das Abbild wieder lauffähig wird,
und was für eine vollständige Neuimplementierung noch fehlt.

## 1 Die Prüfsumme

Beim Einschalten summiert die Firmware alle Bytes von 0000h bis zu einer
Endadresse und vergleicht das Ergebnis mit dem Byte unmittelbar danach.
Stimmt es nicht, erscheint `Err 1` und das Gerät bleibt in einer
Endlosschleife bei 3B18h stehen — kein Weiterbetrieb.

| Version | Prüfroutine | Bereich | Prüfsummenbyte | Sollwert |
|---|---|---|---|---|
| V1.3 | 3AABh | 0000h–AC6Fh | AC70h | F2h |
| V1.5 | 3B81h | 0000h–B3C9h | B3CAh | 99h |

Die Endadresse steht im ROM selbst, geladen mit `MOV 10h,#hi` und
`MOV 11h,#lo`. `romfix.py` liest sie von dort, rechnet nach und setzt
das Prüfbyte:

```
python3 romfix.py geaendert.bin            # nur prüfen
python3 romfix.py geaendert.bin fertig.bin # prüfen und korrigieren
```

Nachgewiesen: Ein Abbild mit geänderter Gerätekennung startet ohne
Korrektur mit `Err 1`, nach dem Lauf durch `romfix.py` fehlerfrei.

## 2 Freier Platz

| Version | belegt | frei |
|---|---|---|
| V1.3 | 0000h–AC70h, 44 145 Byte | AC71h–FFFFh, **21 391 Byte** |
| V1.5 | 0000h–B3CAh, 46 027 Byte | B3CBh–FFFFh, **19 509 Byte** |

Der freie Bereich liegt **außerhalb** des geprüften Bereichs. Eigener
Code dort verändert die Prüfsumme nicht; nur der Einsprung, der im
geprüften Bereich sitzt, tut es — und den fängt `romfix.py` ab.

Vorgehen für eine Erweiterung: eine vorhandene `LCALL`- oder
`LJMP`-Stelle durch einen Sprung in den freien Bereich ersetzen, dort
den eigenen Code ablegen, am Ende die ursprüngliche Routine aufrufen
und zurückspringen. Danach Prüfsumme korrigieren.

## 3 Was heute schon sicher änderbar ist

Diese Strukturen sind vollständig dekodiert und lassen sich gefahrlos
anfassen:

| Was | Ort V1.3 | Format |
|---|---|---|
| Gerätekennung `*IDN?` | AC54h | Längenbyte, dann ASCII |
| Meldungstexte | Zeiger 803Ch, 124 Einträge | Längenbyte, dann ASCII |
| Befehlstabelle | 7752h, 131 Einträge | 14 Byte Name + 2 Byte Token |
| Anzeigetexte Selbsttest | 5E11h, 24 × 5 Zeichen | Segmentmuster |
| Ziffernschrift | 5E91h, 16 Einträge | Segmentmuster |
| Tastennummern | 5AABh | Index = Tastencode |
| Vorgabewerte beim Reset | 3C2Eh | direkte Zuweisungen |
| Viertel-Sinus | 44A7h | 256 × 16 Bit |
| Haversine | 46A9h | 512 × 12 Bit |
| AM-Referenz | 4AABh | 1024 × 8 Bit |
| eingebaute Arbitrary-Kurven | A047h, A447h, A847h | je 1024 × 8 Bit |

Die Segmentkodierung für eigene Texte: Bit 0 = d, 1 = Dezimalpunkt,
2 = c, 3 = b, 4 = g, 5 = a, 6 = e, 7 = f.

## 4 Was für eine Neuimplementierung noch fehlt

**Vollständig verstanden** sind Prozessor, Speicherkarte,
Strobe-Dekodierung, C-Bus, I²C mit allen drei Teilnehmern,
Portbelegung, Tastaturkodierung, Drehknopf, Anzeigepuffer, EEPROM- und
NVRAM-Struktur, Fehlercodes, Selbsttest und der **komplette
Frequenzpfad** von der BCD-Eingabe bis zu den vier TWS-Bytes.

**Offen sind die übrigen Stellgrößen:**

| Baugruppe | Strobe | Stand |
|---|---|---|
| Amplitude | STR9, 1 Byte | Weg bekannt, Bitbelegung offen |
| Attenuator K401/K402 | über STR9, Leitungen S2/S3 | je 20 dB, Umschaltschwellen unbekannt |
| DC-Offset | STR7, 2 Byte | Format unbekannt |
| Amplitudenmodulator, Pulsgenerator | STR3, 2 Byte | Format unbekannt |
| Burst-Logik | STR4, 2 Byte | Format unbekannt |
| Modulationsoszillator | STR5, 4+2 Byte | Format unbekannt |
| Sweep-Ausgang | STR8 | Rampenschleife bei 1CF3h bekannt, Skalierung offen |

Dazu: rund 1 900 Byte des ROM sind weder als Code noch als Tabelle
klassifiziert, und von 128 Zustandsbits kennen wir bei 54 die Wirkung.
Das Protokoll zur Schnittstellenkarte auf I²C-Adresse 5Eh ist
unberührt.

## 5 Realistische Einschätzung

**Ändern und zurückspielen** ist ab sofort möglich. Texte, Tabellen,
Vorgabewerte und Kurvenformen lassen sich anpassen, eigener Code passt
in 21 KB freien Speicher, und die Prüfsumme ist ein gelöstes Problem.

**Neu schreiben** ist es noch nicht. Der Frequenzpfad zeigt, dass die
Methode trägt: Telegramm am Bus mitschneiden, Werte variieren, Formel
ableiten, im Listing gegenprüfen. Dasselbe für Amplitude, Offset,
Modulation und Burst durchzuziehen ist Fleißarbeit von überschaubarem
Umfang — sechs Baugruppen nach demselben Muster. Erst danach wäre eine
eigene Firmware mehr als ein Versprechen.
