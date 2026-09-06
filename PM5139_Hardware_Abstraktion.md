# PM5139 — Hardware-Abstraktion: Strobes, Bus, Firmware-Routinen

Quellen: Firmware-Disassembly V1.3 (Adressen ohne Zusatz) und
Service Manual PM 5138A (4822 872 15115, Fluke 1994), Fig. 106 „Unit 2, CPU"
sowie Abschnitt 6, Programm 4 „Strobe Test".

Der PM5138A ist das 10-MHz-Schwestermodell des PM5139 aus derselben Baureihe;
Digitalteil und Firmware-Architektur sind identisch.

---

## 1 Prozessor und Speicher

| Position | Typ | Funktion |
|---|---|---|
| D301 | PCB80C652 | 8051-Kern mit Hardware-I²C, 256 Byte internes RAM |
| Quarz | 12,000 MHz | Systemtakt |
| D304 | 74HCT573 | Adress-Latch AD0–AD7 |
| D306 | HN27512G-25 | Programm-EPROM 64K — der vorliegende Dump |
| D310 | HN58C256P-20 / X28C256 | EEPROM 32K×8, Variante 8K×8 möglich |
| D305 | PCF8570P | 256×8 RAM am I²C-Bus, batteriegepuffert (G812) |
| D307 | 74HCT4514 | „STROBE ENCODER", 4→16-Dekoder |

**SFR D8h ist S1CON**, nicht CCON. `MOV S1CON,#45h` beim Reset setzt
ENS1=1, AA=1 und die Bitrate CR=001. `CLR S1CON.6` bei 622Eh und 625Ch
schaltet den Hardware-I²C-Block ab, bevor die Firmware SCL/SDA auf
P1.6/P1.7 selbst bitbangt (Routine ab 51A1h).

In V1.5 fehlen beide `CLR S1CON.6`, während der Reset ENS1 weiterhin
setzt. Zu prüfen.

Der Schreibzugriff `MOV 0FBh,A` bei 8E0Ah (V1.5: 9171h) trifft einen auf
dem 80C652 nicht existierenden SFR. Gemeint war das indirekt adressierte
RAM 0FBh, das eine Zeile vorher korrekt beschrieben wird. Wirkungsloser
Fehler, in beiden Versionen vorhanden.

---

## 2 Der externe Adressraum

`MOVX` teilt sich sauber am Bit A15:

| DPTR | Ziel |
|---|---|
| 0000h–7FFFh | EEPROM D310, A0–A14, eigene /CE /OE /WE |
| 8000h–8FFFh | Strobe-Encoder D307: **A8–A11 = Strobe-Nummer** |

Die Größenerkennung des EEPROMs steht bei 9798h: dort wird 55h nach
7FFFh, 5FFFh, 3FFFh und 1FFFh geschrieben und zurückgelesen — genau die
Unterscheidung zwischen der 32K- und der 8K-Bestückung, die der
Schaltplan als Variante ausweist. Ergebniscode in R6: 00h, 86h oder 8Fh.

---

## 3 Die zentrale Ausgaberoutine

Alle Schieberegister der Analogeinheiten hängen an einer gemeinsamen
seriellen Leitung (SBUF im Schieberegistermodus, 8051-Modus 0). Der
Strobe entscheidet, welches Register die Daten übernimmt.

```
0E8A  MOV   A,@R0          ; Daten aus RAM 14h abwärts, MSB zuerst
0E8B  CLR   TI
0E8D  MOV   SBUF,A
0E8F  JNB   TI,$           ; auf Übertragungsende warten
0E92  DEC   R0
0E93  DJNZ  R4,0E8A        ; R4 = Anzahl Bytes
...
0E98  ORL   DPH,#80h       ; Strobe feuern
0E9B  MOVX  @DPTR,A
0E9C  MOV   DPH,#80h       ; auf Leerausgang 0 zurückstellen
0E9F  MOVX  @DPTR,A
```

Aufrufkonvention: DPH = Strobe-Nummer, R4 = Bytezahl, Daten in RAM
11h…14h. `ORL DPH,#80h` bildet daraus die Adresse 8n00h.

---

## 4 Strobe-Belegung

Zuordnung Hardware aus dem Service Manual, Abschnitt 6 Programm 4.
Einsprungpunkte und Aufrufstellen aus dem Disassembly V1.3.

| Strobe | DPH | Hardware laut Manual | Einsprung | Bytes | Aufrufer |
|---|---|---|---|---|---|
| STR0 | 80h | Leerausgang / Statusregister | 517Dh (lesen) | – | 36 Aufrufe |
| STR1 | 81h | RAM, Unit 4, D101 | direkt 43BDh, 1D2Ah | 2 | Anzeige-/Steuerwort |
| STR2 | 82h | RAM, Unit 4, D102, D103 | direkt, 17 Stellen | – | Kurvenform-Download |
| STR3 | 83h | Ampl. Modulator U4 D144, Pulse Gen. U4 D126 | 0E78h | 2 | 0E4Ah |
| STR4 | 84h | Burst Logic, Unit 4, D121, D122 | 0E7Fh | 2 | 0C2E 0C39 0C4E 0C54 0CBE 0CCA 0CD6 0D73 |
| STR5 | 85h | Modulation Oscillator, U4 D130, D138, D139 | 0E69h | 4+2 | 0BF8 0CEB 0D04 110D 111D |
| STR6 | 86h | TWS, Unit 2, D331 (PCF1842P) | 0E54h | 4 | über 4321h |
| STR7 | 87h | DC Generator, Unit 3, D301 | 0E5Bh | 2 | 09B5 0B12 0B1E 0B2C 0B37 0B4A |
| STR8 | 88h | Sweep-Ausgangsspannung, Unit 1, D307 | direkt 1D0Ch | – | Sweep-Ausgang |
| STR9 | 89h | Amplitude Controller, Unit 3, D101, D102 | 0E62h | 1 | 09BB 0AFE 0B50 0BA6 10BB |

STR10–STR15 sind am Dekoder herausgeführt, werden von der Firmware aber
nicht angesprochen.

---

## 5 Das Statusregister (Lesen über STR0)

`517Dh: MOV DPH,#80h / MOVX A,@DPTR / RET` — 36 Aufrufstellen.

| Bit | Bedeutung | Beleg |
|---|---|---|
| ACC.0 | Ereignis anstehend, Hauptschleife | 30 von 36 Aufrufen prüfen genau dieses Bit |
| ACC.3 | zweite Ereignisquelle | 4 Aufrufe, u.a. 62B7h und 71ADh |
| ACC.4 | Busy des Wellenform-RAM | 28 Warteschleifen `JNB ACC.4,$` |

Die Busy-Schleifen laufen alle mit DPH=82h, also gegen STR2 —
das bestätigt STR2 als Pfad zum Wellenform-RAM auf Unit 4.

---

## 6 Kurvenform-Download

Die in `PM5139_Kurvenformen.png` gezeigten Tabellen gehen ausschließlich
über STR2 in das RAM auf Unit 4:

| Tabelle | Laderoutine | Inhalt |
|---|---|---|
| 44A7h | 3DABh / 4003h | Viertel-Sinus, gespiegelt zu 1024 Punkten |
| 46A9h | 3EFCh | Haversine, 512 × 12 Bit |
| 4AABh | 4425h | Sinus mit 10 AM-Graden |
| A047h / A447h / A847h | 9E37h, Auswahl über RAM 0Dh | drei eingebaute Arbitrary-Kurven |

Die Frequenz geht getrennt davon über STR6 an den TWS (D331, PCF1842P) —
vier Bytes, aufgesetzt in 4321h aus der Tabelle bei 4335h.

---

## 7 Selbsttest

Das Manual beschreibt sieben Unterprogramme, erreichbar über die
LOCAL-Taste beim Einschalten. Sie entsprechen der Sprungtabelle bei
5A0Bh mit acht LJMP-Einträgen:

| Nr. | Manual | Sprungziel |
|---|---|---|
| 1 | Display Test | 5A2Fh |
| 2 | Keyboard Test | 5A42h |
| 3 | Memory Register Test | 5ADBh |
| 4 | Strobe Test | 5B44h |
| 5 | Interface Test (RS-232 / IEEE-488) | 5C0Bh |
| 6 | Rotary Knob Test | 5D68h |
| 7 | EEPROM Test | 5EE9h |
| – | Rücksprung ins Menü | 59D1h |

Die Zuordnung folgt der Reihenfolge im Manual und der Tabelle; die
Einzelroutinen sind noch nicht gegengeprüft.

---

## 8 Der serielle C-Bus

Alle Schieberegister der Analogeinheiten sind HCT4094 — serielles
Schieberegister mit eigenem Strobe-Eingang. Genau die Bauform, die das
Modell aus Abschnitt 3 verlangt.

Der Bus heißt im Schaltplan **C-Bus** und besteht aus zwei Leitungen:

| Signal | Bedeutung | CPU-Pin |
|---|---|---|
| SC | Serial Clock | P3.1 / TXD |
| SD | Serial Data | P3.0 / RXD |

Das entspricht dem 8051-Schieberegistermodus (SCON-Modus 0), in dem TXD
den Takt und RXD die Daten führt. Über HC4050-Puffer (D105, D106 auf
Unit 4) wird der Bus verteilt; ein gepufferter Zweig SC1/SD1 geht an
Amplitudenmodulator, Pulsgenerator und Modulationsoszillator, ein
weiterer an die Burst-Logik.

---

## 9 Unit 4, RAM — Fig. 114

Damit ist auch die offene Frage STR1 gegen STR2 beantwortet:

| Strobe | Baustein | Beschriftung im Plan |
|---|---|---|
| STR1 | D101-A HCT4094 → D104-A HCT367 | **page select** |
| STR2 | D102-A, D103-A HCT4094 | Daten- und Steuerpfad |

Das Wellenform-RAM selbst:

| Position | Typ | Beschriftung |
|---|---|---|
| D107-A | HM6716-30, 2K×8 | **RAM upper 8 bits** |
| D108-A | HM6268 | untere 4 Bit |
| D112-A | HCT4094 | **load lower 4 bits** |

**Das RAM ist 12 Bit breit.** Das bestätigt unabhängig, was wir aus den
ROM-Tabellen abgeleitet hatten: die Werte werden als High-Byte plus
Low-Nibble übertragen, wobei das Nibble im zweiten Byte doppelt steht
(erzeugt bei 3E27h mit `MOV R6,A / SWAP A / ORL A,R6`). Die
Haversine-Tabelle bei 46A9h hat als Low-Bytes ausschließlich die Werte
00h, 44h, 88h und CCh — exakt die vier möglichen doppelten Nibbles.

Weitere Signale an XB07: Pin 13 „EN to TWS", Pins 16–25 „10 bits from
TWS", Pin 15 „C/n to DAC".

---

## 10 Unit 5, Tastatur und Anzeige — Fig. 122

| Position | Typ | Funktion |
|---|---|---|
| D302-A | **SAA3007** | Keyboard Encoder, 455-kHz-Resonator, Matrix S0–S6 / D0–D6 |
| D304-A | **PCF8576T** | LCD-Treiber am I²C-Bus, 40 Segmentausgänge A0–A39 |
| S405 | „BIT GENERATOR" | Drehknopf, zwei Phasen A1/A2 über HCT132-Schmitt-Trigger |
| H401 | Backlight | |

Die Anzeige hängt also am I²C-Bus (SCL/SDA), die Tastatur an einem
eigenen Encoder-Baustein. Der SAA3007 liefert pro Tastendruck ein
serielles Wort mit einem 2-Bit-Zähler — das erklärt die Beschreibung im
Manual zum Tastaturtest: „e.g. 12-2 when key DC is pressed. This control
number is generated by the keyboard decoder and can be changed to 0, 1,
2, or 3 by pressing this key again."

Steckerbelegung XB05 zwischen Unit 2 und Unit 5:

| Pin | Signal |
|---|---|
| 7 | /RES |
| 8 | INL |
| 9 | INR |
| 10 | ITG |
| 11 | SCL |
| 12 | SDA |
| 13 | SKC |

INL und INR sind die beiden Phasen des Drehknopfes. Die Firmware liest
sie bei 5EA1h mit `MOV C,P1.4 / ANL C,/P1.3` beziehungsweise
`MOV C,P1.3 / ANL C,/P1.4` und leitet daraus die Drehrichtung ab — das
ist Programm 6 des Selbsttests.

---

## 11 Der Tastatur-Dekoder

Der SAA3007 liefert seine Daten **pulsweitenkodiert auf einer einzigen
Leitung**, die an **P3.3** (INT1) hängt. Die Firmware dekodiert sie in
Software bei **0227h**:

```
022A  MOV   TH0,#0D7h      ; Timer 0 vorladen
022D  MOV   TL0,#46h
0230  CLR   TF0
0232  JNB   P3.3,$         ; auf steigende Flanke warten
0235  JB    TF0,025Ah      ; Timeout -> Abbruch
0238  JB    P3.3,0235h     ; Pulsdauer messen
023B  MOV   A,TH0
023D  CJNE  R6,#0Bh,024Ah  ; 11 Bit?
...
024A  ADD   A,#10h         ; Schwelle -> Carry ist das Bit
024C  MOV   A,R5
024D  RLC   A              ; Bit einschieben
024F  INC   R6
0250  CJNE  R6,#05h,022Ah
```

Elf Bit werden eingeschoben, das Bit ergibt sich aus der gemessenen
Pulslänge über `ADD A,#10h` und das dabei entstehende Carry. Rückgabe in
R5. Bei Timeout vor dem elften Bit liefert die Routine 0 zurück.

Die LOCAL-Taste (S820) sowie ADDRESS (S821) und RESET (S822) liegen laut
Fig. 122 **nicht** in der Encoder-Matrix, sondern sind separat verdrahtet.
Das deckt sich mit dem Manual, das beim Tastaturtest ausdrücklich sagt:
„Press any key at random, except LOCAL."

### Beleg über den Strobe-Test

Programm 4 des Selbsttests bei **5B44h** verbindet beide Erkenntnisse und
bestätigt zugleich die Strobe-Tabelle aus Abschnitt 4:

```
5B4D  MOV   1Fh,#01h       ; Strobe-Nummer, Start bei 1
5B5A  JNB   P1.4,5B8Ch     ; Drehknopf bewegt -> 5EA1h, 1Fh +/- 1
5B5D  JB    P1.2,5B8Ch
5B66  JB    P3.3,5B5A      ; keine Taste -> weiter warten
5B75  MOV   R0,#14h        ; sonst RAM 0Eh..14h mit 00h oder FFh füllen
5B7A  JNB   22h.0,5B7Eh
5B7D  CPL   A
5B82  MOV   R4,#06h        ; sechs Bytes
5B84  MOV   DPH,1Fh        ; Strobe = Knopfstellung
5B87  LCALL 0E86h          ; senden und strobe
```

Wort für Wort das, was das Manual beschreibt: mit dem Drehknopf die
Strobe-Leitung wählen, mit einer beliebigen Taste alle Ausgänge des
gewählten Registers auf high oder low setzen.

---

## 12 Portbelegung des 80C652

Zählung über das gesamte ROM, V1.3 und V1.5 identisch. Steckerbelegung
XB05 vom Anwender am Gerät verifiziert.

| Pin | Richtung | Signal | Verwendung | Beleg |
|---|---|---|---|---|
| P0 | bidir. | AD0–AD7 | Multiplexbus | Fig. 106, D304 HCT573 |
| P2 | aus | A8–A15 | Adressbus, A8–A11 zugleich Strobe-Nummer | Fig. 106, D307 |
| P1.0 | aus (5×) | PL, XB03.8 | Pen Lift für XY-Schreiber | 1911h, 1A3Fh, 1B8Ah |
| P1.1 | aus (1×) | FMO → U2 Clock Gen. | FM-Modulation ein | 0C08h |
| P1.2 | ein (6×) | KTG, XB05.10 | Tastenwort bereit | 5B5Dh, 5C8Fh, 5D1Dh |
| P1.3 | ein (8×) | IDR, XB05.9 | Drehknopf-Richtung | 25C9h, 5EA7h |
| P1.4 | ein (13×) | ITG, XB05.8 | Drehknopf-Impuls | 25CDh, 25EBh, 5EA1h |
| P1.5 | aus (20×) | EN to TWS, XB07.13 | Freigabe um jeden Transfer | 4321h, 3DCAh |
| P1.6 | bidir. | SCL, XB05.11 | I²C-Takt, per Software | 51A1h ff. |
| P1.7 | bidir. | SDA, XB05.12 | I²C-Daten, per Software | 51A1h ff. |
| P3.0 | – | RXD = C-Bus SD | serielle Daten, SBUF-Modus 0 | 0E8Dh |
| P3.1 | – | TXD = C-Bus SC | serieller Takt | 0E8Dh |
| P3.2 | ein (10×) | INT0 | Schnittstelle | Vektor 0003h → 6279h |
| P3.3 | ein (11×) | SKC, XB05.13 | serieller Tastencode | 0227h, 5A53h, 5B66h |
| P3.4 | aus (1×) | T0 → PGS to TWS | Kurvenform-Umschaltung | 095Dh |
| P3.5 | aus (40×) | DBK | Strobe vor Busy-Abfragen | 3E58h, 4477h |

### Der Drehknopf

ITG und IDR sind Impuls und Richtung, keine Quadratur. Bei 25C2h wird
der Pegel von IDR vor dem Impuls abgetastet, auf die Flanke von ITG
gewartet und danach erneut abgetastet; die Impulse zählt R3.

### FMO

`MOV C,2Ch.2 / MOV P1.1,C` bei 0C08h. 2Ch ist der One-hot-Kodierte
Modulationsmodus aus der Tabelle 740Ah, Bit 2 also FM. Die Leitung
schaltet über zwei NPN das Fmod-Signal auf die Abstimmspannung des VCO
auf Unit 2 — auf Fig. 105 der Knoten „Fmod (FM)" am Tiefpass vor dem
Tuning-Voltage-Ausgang.

### PGS

```
0953  ORL   C,2Bh.2
0955  ORL   C,2Bh.3
0957  ORL   C,2Ah.6
0959  ORL   C,2Ah.7
095B  ORL   C,2Bh.1
095D  MOV   P3.4,C
```

2Ah und 2Bh tragen den One-hot-kodierten Kurvenform-Code aus der Tabelle
bei 73F3h. Die fünf abgefragten Bits sind damit eindeutig:

| Bit | Kurvenform |
|---|---|
| 2Ah.6 | POSSAW |
| 2Ah.7 | NEGSAW |
| 2Bh.1 | HAV |
| 2Bh.2 | SINEPULSE |
| 2Bh.3 | TRNGLPULSE |

PGS ist also genau für die fünf Kurvenformen aktiv, die aus dem
Wellenform-RAM kommen. SINE, TRNGL, SQUARE, POSPULSE und NEGPULSE
(Bits 2Ah.1 bis 2Ah.5) erzeugt der TWS direkt, ARBIT (2Bh.4) läuft über
einen eigenen Pfad und ist in der Verknüpfung nicht enthalten.

### PL — Pen Lift

P1.0 wird immer zusammen mit Timer 1 geschaltet: bei 1911h wird TH1/TL1
auf FC1Bh geladen, TR1 gesetzt und danach `SETB P1.0`; bei 1A3Fh, 1A4Bh
und 1B8Ah folgt `CLR P1.0`, ebenso einmal in der Initialisierung bei
0996h. Dieselbe Timerkonstante FC1Bh steht bei 1CF3h unmittelbar vor der
Sweep-Schleife, die pro Schritt über STR6 eine neue TWS-Frequenz und
über STR8 einen neuen Wert für die Sweep-Ausgangsspannung ausgibt.

Auf Unit 1 treibt PL über R626 die Basis von V356 (BC337-25), Emitter an
Masse. Am Kollektor liegt R625 als 20k5-Pull-up, über R634 (205R) geht es
auf die Buchse X19, X20 ist die Masserückführung; V410 (BAW62) klemmt
gegen Masse. Ein Open-Collector-Ausgang mit Strombegrenzung, im Plan
beschriftet mit **PEN LIFT** — der Kontaktausgang für einen XY-Schreiber.

V356 invertiert. `SETB P1.0` während der Rampe zieht die Buchse also auf
Masse (Stift unten), `CLR P1.0` beim Rücklauf gibt sie frei
(Stift oben).

---

## 13 Einschalt-Selbsttest und Fehlercodes

Reihenfolge ab dem Reset-Vektor 3A9Ah. Die Fehleranzeige erzeugen sieben
Einsprünge bei 3BFCh–3C14h, die alle bei 3C16h zusammenlaufen und dort
`E`, `r`, `r`, Leerzeichen und die Ziffer in die Anzeigeregister
3Eh–42h schreiben:

```
3C16  LCALL 396Dh        ; Anzeige löschen
3C19  MOV   42h,A        ; Ziffer aus R2 (Segmentmuster)
3C1C  MOV   41h,#00h     ; Leerzeichen
3C1F  MOV   40h,#50h     ; 'r'
3C22  MOV   3Fh,#50h     ; 'r'
3C25  MOV   3Eh,#0F1h    ; 'E'
3C28  LCALL 37DBh        ; Anzeige senden
```

| Anzeige | Bedeutung laut Manual | Einsprung | Prüfung im ROM |
|---|---|---|---|
| `Err 1` | Prüfsumme Programmspeicher | 3BFCh | 3AABh: Summe über 0000h–AC6Fh gegen Byte AC70h; Fehler → Endlosschleife auf 3AABh |
| `Err 2` | RAM-Fehler Prozessor | 3C00h | 3AD3h: CCh und 55h in jede Zelle FFh…01h, Rücklesen; Fehler → Endlosschleife |
| `Err 3` | Speicher der aktuellen Einstellungen | 3C04h | Flag 22h.6, gesetzt bei 3B21h; lädt Vorgaben über 3C2Eh nach, 49h = 2Ch |
| `Err 4` | Speicherregister 1…9 | 3C08h | Flag 22h.7, gesetzt bei 3B07h in der Schleife 67h = 9…1, 49h = 2Bh |
| `Err 5` | Überlastschutz | 3C0Ch | 3C7Ah: setzt 20h.3, 49h = 1Eh, wartet auf Taste über P3.3, kehrt nach 3B46h zurück |
| `Err 6` | Frequenzerzeugung arbeitet nicht | 3C10h | 43E4h liefert Carry; danach `SJMP $` bei 3B65h |
| `Err 8` | Arbitrary-Speicher | 3C14h | 9615h schlägt fehl, 49h = 25h |
| `Err 9` | Datenübertragung Oszilloskop → Generator | 92A2h | 49h = 09h, gesetzt bei 8F08h |

Zwei Anmerkungen dazu:

Das Manual sagt, nur bei Err 1 und Err 2 sei kein Weiterbetrieb
möglich. Tatsächlich hängt die Firmware auch bei **Err 6** in einer
Endlosschleife (3B65h: `SJMP 3B65h`). Wer diesen Fehler sieht, hat ein
totes Gerät — was zu den Foren-Berichten passt.

Err 5 ist kein reiner Einschalttest: 3C7Ah wird auch im laufenden
Betrieb angesprungen und quittiert sich mit einer beliebigen Taste.

---

## 14 Aufbau der Anzeige

Die Anzeige ist ein PCF8576 auf Unit 5 am I²C-Bus. Sein
Schreib-Slave-Adressbyte ist **70h**, und genau damit beginnt die
Übertragungsroutine:

```
392F  MOV   A,#70h       ; Slave-Adresse PCF8576
3931  LCALL 5187h        ; I²C-Start
3936  MOV   A,#0CEh      ; Kommandobytes
393D  MOV   A,#80h
3944  MOV   A,#0E0h
394B  MOV   A,R3         ; Parameter, aus 37DBh: F8h
3951  MOV   A,R4         ;              und 70h
3957  MOV   R0,#30h      ; Puffer
3959  MOV   R1,#14h      ; 20 Bytes
```

**Der Anzeigepuffer liegt in RAM 30h–43h**, 20 Bytes. Das sind
40 Nibbles zu 4 Bit, also exakt die 40 Segmentleitungen × 4 Backplanes
des PCF8576 — der Puffer ist ein 1:1-Abbild des Display-RAM. 396Dh
löscht ihn vollständig (Anzeige aus).

Bisher zugeordnet:

| Puffer | Feld |
|---|---|
| 3Eh–42h | Hauptfeld, 5 Stellen, MSD zuerst |
| 39h–3Ch | unteres Zahlenfeld, 4 Stellen (fMOD/DEV/fSTOP/T/N/SYMMETRY/REG/ADDR) |
| 3Dh | Modulations- und Sweep-Zeile |
| 30h–38h, 43h | übrige Felder und Annunciatoren, noch nicht aufgeschlüsselt |

Beleg für 39h–3Ch: bei 1829h werden die vier BCD-Register 15h–18h
direkt nach 39h–3Ch kopiert, bei 1917h alle vier gemeinsam gelöscht.

### Beispiel: die Modulationszeile

3812h baut das Byte für 3Dh direkt aus dem One-hot-Code 2Ch:

```
3812  MOV   A,2Ch
3814  ANL   A,#1Fh      ; Bits 0-4 unverändert
3816  MOV   12h,A
3818  JB    2Ch.7,3831h
381B  JB    2Ch.5,3822h
381E  JB    2Ch.6,3827h
3822  ORL   12h,#60h    ; Sweep linear
3827  ORL   12h,#0C0h   ; Sweep logarithmisch
```

Geschrieben wird es bei 14EBh mit `MOV 3Dh,12h`. Die Anzeigezeile lautet
`MOD-OFF AM FM PSK GATE LIN-SWP-LOG BURST`; Bits 0 bis 4 entsprechen also
der Reihenfolge MOD-OFF, AM, FM, PSK, GATE, und die Sweep-Anzeigen
kommen als Bitpaare 60h beziehungsweise C0h dazu.

Nach demselben Muster lassen sich die übrigen Annunciatoren
auflösen: die Kurvenform-Symbolzeile aus 2Ah/2Bh, die Trigger-Zeile aus
2Fh. Für die endgültige Zuordnung Bit → Symbol fehlt die
Segment-/Backplane-Belegung des PCF8576 aus Fig. 122.

---

## 15 Bitbelegung der Anzeige

Ermittelt durch Ausführung des Original-Codes im Interpreter (`emu.py`):
Vorgaben über 3C2Eh laden, ein Flag oder einen Befehl setzen, den
Anzeigeaufbau bei 3381h laufen lassen, Puffer 30h–43h vergleichen.

Grundzustand nach 3C2Eh:
`02 00 00 02 00 A0 28 0C 0E ED 00 00 00 00 00 0E ED ED EF 40`

### Kurvenform-Symbolzeile

Zweifach belegt: über den One-hot-Code in 2Ah/2Bh und unabhängig davon
über die Befehlstoken aus der Tabelle bei 7752h.

| Symbol | Flag | Token | Puffer-Bit |
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

36h.5 bleibt in allen Kurvenformen gesetzt — ein fester Anzeigeteil,
vermutlich die Zeilenmarkierung `▶`.

### Modulationszeile

| Anzeige | Flag | Token | Puffer-Bit |
|---|---|---|---|
| MOD-OFF | 2Ch.0 | 21h | 33h.1 |
| AM | 2Ch.1 | 22h | 33h.5 |
| FM | 2Ch.2 | 23h | 33h.6 |
| PSK | 2Ch.3 | 24h | 32h.0 |
| GATE | 2Ch.4 | 25h | 32h.4 |
| LIN | 2Ch.5 | 26h | 31h.1 |
| SWP | 2Ch.5 und 2Ch.6 | 26h/27h | 31h.3 |
| LOG | 2Ch.6 | 27h | 31h.7 |
| BURST | 2Ch.7 | 28h | 31h.6 |

Sweep linear setzt 31h auf 0Ah (Bits 1 und 3), logarithmisch auf 88h
(Bits 3 und 7). Das mittlere Wort der Gruppe `LIN-SWP-LOG` leuchtet in
beiden Fällen — genau wie auf der Frontplatte gedruckt.

### Triggerzeile

Die Zeile ist gesperrt, solange 2Ch.0 (`MOD-OFF`) gesetzt ist. Erst mit
Sweep, Burst oder Modulation wird sie sichtbar.

| Flag | Puffer-Bit | Beleg |
|---|---|---|
| 2Fh.4 | 30h.2, 30h.4, 33h.4 | 6E5Ah: gelöscht → `TRGS INT`, gesetzt → `TRGS EXT` |
| 2Fh.5 | 33h.0 | 6DEFh: `MODSRC EXT` |
| 2Fh.0 | 31h.5 | in allen Sweep- und Burstmodi gesetzt |
| 2Fh.1 | 31h.0 | dito |
| 2Fh.2 | 32h.6 | Gegenstück zu 2Fh.3 |
| 2Fh.3 | 32h.2 | `TRIGF CONT` / `TRIGF SING` |
| 2Fh.6 | 30h.2, 30h.4, 34h.6 | – |

Bei externer Triggerung setzt 2Fh.4 zusätzlich in 3Bh, 3Ch und 3Dh
jeweils Bit 4, also das Segment `g`. Drei Ziffern mit nur Mittelbalken
ergeben `- - -`: ohne interne Triggerung gibt es keine Zyklenzahl
anzuzeigen.

### Weitere Zuordnungen

| Flag | Wirkung |
|---|---|
| 22h.3, 2Bh.5 | löschen 37h und 38h — das dreistellige AC/DC-Feld |
| 2Eh.5 | füllt 38h/39h — Gegenstück dazu |
| 2Dh.0…2Dh.6 | Bits in 32h und 34h, freigeschaltet erst ohne MOD-OFF: die Parameterbezeichner `fMOD m DEV fSTOP T N` |
| 20h.0 | nur mit 2Bh.4 (ARBIT) wirksam — Arbitrary-spezifisches Element |
| 21h.6 | Ziffern im unteren Feld, REG/ADDR-Anzeige |
| 27h.0…27h.2, 28h.1, 28h.2 | nur mit 2Eh.2 wirksam, blenden Haupt- und AC-Feld aus |

Von 128 Flags wirken 31 unmittelbar auf die Anzeige, 23 weitere über
eine Vorbedingung, die übrigen 74 gar nicht.

### Werkzeug

`emu.py` ist ein vollständiger MCS-51-Interpreter (interner RAM, SFR,
Bitadressierung, MOVX auf ein XRAM-Abbild, MOVC aus dem ROM). Unterprogramme
lassen sich per Adressliste stubben, damit I²C- und Strobe-Zugriffe
übersprungen werden. `sweep.py`, `sweep2.py`, `sweep3.py` und
`cmdsweep.py` sind die vier Experimente, aus denen die Tabellen oben
stammen.

---

## 16 Von der Taste zur Hardware

Am Ende jedes ausgeführten Befehls steht bei 75A7h ein `ORL 29h,A`, wobei
A aus der Tabelle bei 7598h kommt, indiziert nach Parameterklasse
(`01 00 04 04 08 08 08 00 08 02 0A 00 00 00 08`). RAM 29h ist damit ein
Bündel von Nachlade-Anforderungen: welche Analogeinheit nach der
Änderung neu beschrieben werden muss. Ausgewertet wird es ab 0915h im
Zyklus, der bei 090Ch beginnt.

Ermittelt im Interpreter: Vorgaben laden, Befehlstoken in 10h setzen,
Befehlsinterpreter 71BFh ausführen, dann 090Ch laufen lassen und alle
`MOVX`-Schreibzugriffe oberhalb 8000h mitschreiben. Das untere Nibble
von DPH ist die Strobe-Nummer aus Abschnitt 4.

| Befehlsgruppe | Token | nachgeladene Einheiten |
|---|---|---|
| Kurvenformen | 11h–1Ah | STR1 + STR2 (Wellenform-RAM), STR6 (TWS), STR3 (Ampl.Mod./Pulsgen.), STR9 (Ampl. Controller) |
| Symmetrie `#SYON`/`#SYOFF` | 1Eh, 1Fh | dieselben fünf |
| Modulation, Sweep | 20h–2Ah, 2Eh, 2Fh | STR3, STR4 (Burst-Logik), STR9 |
| Burst `#BU` | 28h | STR3, STR4, STR9 **und zusätzlich** STR1, STR2, STR6 |

Das Muster ist in sich schlüssig. Eine neue Kurvenform bedeutet neuen
RAM-Inhalt, neue Teilerkette im TWS und eine neue Amplitudenkorrektur —
fünf Einheiten. Eine geänderte Modulationsart lässt die Kurvenform
unberührt und beschreibt nur Modulator, Burst-Logik und
Amplitudensteller.

Die eine Ausnahme ist Burst: dort werden zusätzlich TWS und
Wellenform-RAM neu geladen, weil ein Burst mit definierter Startphase
beginnen muss und die Kurve dafür neu abgelegt wird. Das deckt sich mit
`STARTPHASE` als eigenem Befehl (Token 8Ah) und mit der
Anzeigebezeichnung `T` in der Parameterzeile.

**Einschränkung:** 090Ch ist kein abgeschlossenes Unterprogramm, sondern
mündet in den Hauptzyklus. Der Interpreter läuft deshalb mit einem
Schrittbudget und bricht ab, sobald der Programmzähler in einen
Datenbereich läuft. Die Tabelle zeigt also, welche Strobes im
unmittelbaren Nachlauf eines Befehls angesprochen werden — für den
Vergleich zwischen Befehlen ist das aussagekräftig, eine vollständige
Ablaufspur ist es nicht.

---

## 17 Systememulator: Start ab Reset-Vektor

`system.py` erweitert den Interpreter um die Peripherie, die für einen
Kaltstart nötig ist:

- **Timer 0 und 1** als 16-Bit-Zähler mit TF-Flags, gesteuert über TCON
- **Interrupts** INT0, TF0, INT1, TF1 und seriell mit Vektoren 0003h…0023h,
  Freigabe über IE, RETI setzt die Verschachtelung zurück
- **Serielle Schnittstelle** im Schieberegistermodus: TI wird einige Takte
  nach dem Schreiben auf SBUF gesetzt
- **I²C-Slave** an P1.6/P1.7 mit START-/STOP-Erkennung, Bitzählung und
  ACK über neun Takte
- **Strobe-Bereich** ab 8000h: Lesezugriffe liefern ein wechselndes
  Busy-Bit, damit die Warteschleifen im Wellenform-Download terminieren
- **Externes EEPROM** 0000h–7FFFh als beschreibbares Abbild

### Was der Kaltstart zeigt

Die Prüfsummen beider ROMs stimmen: Summe über 0000h–AC6Fh ergibt F2h und
steht so bei AC70h; für V1.5 ergibt die Summe über 0000h–B3C9h den Wert
99h, der bei B3CAh steht. Die Dumps sind also vollständig, und die
Prüfsummenroutine ist richtig gelesen.

Der Start durchläuft anschließend den RAM-Test fehlerfrei und beginnt,
die Anzeige zu bedienen. Die erste I²C-Übertragung lautet:

```
70 CE 80 E0 F8 70  gefolgt von 20 Datenbytes
```

Slave-Adresse des PCF8576, drei Kommandobytes, zwei Parameter und der
Anzeigepuffer — genau die Reihenfolge, die in Abschnitt 14 aus dem
Listing abgeleitet wurde, jetzt vom laufenden Code bestätigt.

Mit leerem EEPROM meldet die Firmware `Err 3` und danach `Err 8`, läuft
aber weiter und bleibt im Anzeige-Refresh. Das ist das korrekte
Verhalten für ein Gerät mit defektem Einstellungsspeicher: beide Fehler
sind laut Manual quittierbar.

Dekodiert man die letzten 20 I²C-Bytes mit der Segmenttabelle aus
Abschnitt 14, steht im Hauptfeld `Err`. Damit ist die Kette einmal
vollständig geschlossen: ROM → CPU → I²C → PCF8576 → Segmentmuster →
lesbarer Text, alles aus dem Originalcode heraus.

### Offen

- Ein gültiges EEPROM-Abbild fehlt noch. Der Kopf bei 0000h/0001h und
  die Registerprüfsummen ab 0007h lassen sich aus 9615h und 95C1h
  ableiten, mein erster Versuch trifft die Struktur aber noch nicht.
- Tasteneingaben werden bisher nicht eingespeist. Dafür müsste der
  pulsweitenkodierte Datenstrom auf P3.3 nachgebildet werden, den 0227h
  ausmisst — elf Bit, Bitwert über die Pulslänge.

---

## 18 Der Frequenzpfad, vollständig

Der erste durchgerechnete Funktionsblock: von der eingegebenen Frequenz
bis zu den vier Bytes, die der TWS (D331, PCF1842P auf Unit 2) über
STR6 bekommt.

### Ablage der Frequenz

RAM 50h–52h, sechs BCD-Ziffern. Das obere Nibble von 50h ist **nicht**
Teil der Zahl, sondern der **Dekadenindex**; die restlichen fünf Ziffern
sind die Mantisse M.

```
50h = D M1     51h = M2 M3     52h = M4 M5
```

Beispiel `11 50 10`: Dekade 1, Mantisse 15010.

### Umrechnung nach binär

Bei 0A26h beginnt die Wandlung: R0 zeigt auf 50h, R3 zählt drei Bytes,
und je Ziffer wird der 24-Bit-Akkumulator 12h:13h:14h mit 3029h mal
zehn genommen und die Ziffer addiert:

```
0A5D  ANL   A,#0F0h      ; obere Ziffer
0A5F  SWAP  A
0A63  MOV   B,#0Ah
0A66  MUL   AB
0A6C  ADD   A,R3         ; untere Ziffer dazu
0A6D  ADD   A,14h        ; 24-Bit-Addition
0A72  ADDC  A,13h
0A77  ADDC  A,12h
```

### Dekade als Exponent

Der Bereichscode steht als Tabelle unmittelbar im Code, indiziert über
den Dekadenindex in R2:

```
09E5  MOV   A,R2
09E7  MOVC  A,@A+PC
09EA  A0 80 60 40 20 00 00 00 00 00
09F4  ORL   12h,A        ; Exponent in die oberen drei Bits
09F6  MOV   11h,#01h     ; TWS-Befehl "Frequenz"
09F9  LCALL 0E54h        ; vier Bytes, dann STR6
```

Nach der Wandlung ist 12h null, weil die Mantisse in 16 Bit passt. Erst
danach wird der Exponent hineinodert. Die Tabellenwerte sind Vielfache
von 20h, also **E in den Bits 5 bis 7**.

### Das Telegramm

Gesendet wird aus RAM 14h abwärts, vier Bytes:

| Byte | Inhalt |
|---|---|
| 14h | N, niederwertig |
| 13h | N, höherwertig |
| 12h | E in Bit 5…7 |
| 11h | Befehlscode, 01h für Frequenz |

Weitere TWS-Befehle im selben Muster: 04h zusammen mit `ORL 12h,#20h`
(09D9h), 20h (0A17h), 60h (0A20h) und C0h (0BBEh).

### Die Formel

Gemessen über fünf Dekaden im Emulator:

| RAM 50h–52h | N | E | f |
|---|---|---|---|
| 11 50 10 | 30020 | 5 | 1 501 Hz |
| 21 50 10 | 30020 | 4 | 15 010 Hz |
| 31 50 10 | 30020 | 3 | 150 100 Hz |
| 41 50 10 | 30020 | 2 | 1 501 000 Hz |
| 51 50 10 | 30020 | 1 | 15 010 000 Hz |
| 10 15 01 | 3002 | 5 | 150,1 Hz |

Daraus:

```
N = 2 · M
f = M · 0,1 Hz · 10^(5 − E)      bzw.      f = N · 0,05 Hz · 10^(5 − E)
```

Die Mantisse geht also **verdoppelt** in den Teiler. Das passt zur
Bauart: der Triangle Wave Synthesizer zählt Halbperioden, für eine
Dreieckschwingung braucht es aufsteigende und absteigende Flanke.

Solange die Mantisse fünfstellig bleibt, ändert eine Dekadentaste nur
den Exponenten — N bleibt konstant. Erst am unteren Anschlag des
Bereichs wird die Mantisse selbst geteilt; im Beispiel von 30020 auf
3002.

---

## 19 Der Drehknopf

Drei Bedingungen müssen erfüllt sein, bevor eine Raste überhaupt
ausgewertet wird:

```
004C  JB   P1.4,0062h     ; Raste erkannt (ITG aktiv-low)
004F  JNB  24h.6,0057h    ; Parameter angewählt
0054  LJMP 259Ah
25B0  MOV  C,21h.3        ; Registerwahl bei STORE/RECALL
25B2  ORL  C,21h.1
25B4  ORL  C,/2Eh.4       ; oder Knopf entsperrt
25B6  JC   25C2h          ; -> Rasten zählen
25B8  SETB 2Eh.2          ; sonst nur Gruppe anwählen
```

**2Eh.4 ist DIAL LOCK.** Beim Kaltstart ist das Bit gesetzt, der Knopf
also gesperrt; Tastencode 2Ah schaltet es um, und dasselbe Bit steuert
die Anzeige `DIAL LOCKED`.

### Es ist ein echter Quadraturgeber

Die Zählschleife bei 25C2h verlangt, dass IDR sich **während** der
ITG-Flanke ändert:

```
25C9  MOV   C,P1.3        ; IDR vor der Flanke -> F0
25D8  MOV   C,P1.3        ; IDR nach der Flanke
25DA  ORL   C,F0          ; beide 0  -> Abbruch
25DE  MOV   C,P1.3
25E0  ANL   C,F0          ; beide 1  -> Abbruch
25E7  INC   R3            ; sonst: Raste zählen
```

ITG und IDR sind also zwei um 90° versetzte Phasen, kein Impuls mit
Richtungspegel. Mit einem vollständigen Gray-Zyklus je Raste
— (1,1) → (0,1) → (0,0) → (1,0) → (1,1) — zählt R3 exakt eine Raste
pro Zyklus.

### Zwei Fehler im eigenen Kern

Beim Nachvollziehen kamen zwei Interpreterfehler ans Licht:

- Die Tasteneinspeisung löste über die Flanken der Datenpulse ein
  zweites Mal INT1 aus. Der Dekoder startete erneut und hing bei 0232h
  in `JNB P3.3,$`. Alle Messungen unmittelbar nach einem Tastendruck
  waren dadurch wertlos.
- **Das Hilfsübertrag-Flag AC wurde nie berechnet.** Ohne AC arbeitet
  `DA A` falsch, und die Firmware rechnete binär statt BCD: aus 150.10
  wurde beim Herunterdrehen 150.0F statt 150.09. Mit korrektem AC
  stimmt die Dezimalarithmetik.

Beide Fehler sind in `emu.py` und `core.js` behoben; der Kaltstart
bleibt fehlerfrei.

### Stand

Eine Drehrichtung arbeitet sauber und dekrementiert die angewählte
Ziffer in BCD, mit korrektem Übertrag über die Stellen. Die
Gegenrichtung springt unabhängig vom Ausgangswert auf 20000 und bleibt
dort — offenbar die Bereichsgrenze des Geräts, 20 MHz. Warum eine
einzelne Raste dorthin führt, ist noch offen; R3 ist in beiden
Richtungen 1, die Ursache liegt also in der Auswertung ab 25F6h.

---

## 20 Der Amplitudenpfad

### Die drei Stellgrößen

| RAM | Bedeutung | Telegramm |
|---|---|---|
| 1Ch | Feinwert Amplitude Controller | STR9, ein Byte |
| 1Dh | Gleichanteil, um 64h zentriert | STR7, zweites Byte |
| 1Eh | Bereichs- und Relaisbyte | STR7, erstes Byte |

Einsprünge: `MOV 14h,1Ch / LCALL 0E62h` bei 0AFBh für STR9,
`LCALL 0E5Bh` an mehreren Stellen ab 0B12h für STR7.

### Die Attenuator-Relais

Bei 0AACh wird das Bereichsbyte direkt aus der Amplitudendekade
gebildet:

```
0AAC  MOV   A,56h
0AAE  ANL   A,#0F0h
0AB0  SWAP  A            ; Dekade
0AB2  MOV   DPTR,#0B53h
0AB5  MOVC  A,@A+DPTR
0AB6  MOV   C,2Bh.7
0AB8  MOV   ACC.5,C
0ABA  MOV   1Eh,A
```

Tabelle 0B53h: **04 1C 14 04**. Dieselben Muster erscheinen am Bus als
erstes STR7-Byte:

| Dekade | Tabelle | gemessen | K401 | K402 | Dämpfung |
|---|---|---|---|---|---|
| 0 | 04h | A4h | – | – | 0 dB |
| 1 | 1Ch | 7Ch | ein | ein | 40 dB |
| 2 | 14h | B4h | – | ein | 20 dB |
| 3 | 04h | A4h | – | – | 0 dB |

**Bit 4 schaltet K402 (20 dB), Bit 3 zusätzlich K401.** Das deckt sich
mit Fig. 111, wo K401 als „20 dB (for 40 dB)" beschriftet ist. Zwei
unabhängige Belege: die Tabelle im ROM und die Telegramme am Bus.

Nach dem Umschalten wartet die Firmware bei 0B8Ah mit Timer 0 auf
FC1Ch, wahlweise mehrfach über R3 — die Anzugszeit der Relais.

### Korrektur je Kurvenform

```
0B74  MOV   R0,#56h
0B77  LCALL 0F40h        ; BCD -> binaer
0B7A  MOV   C,2Ah.1      ; SINE
0B7C  ORL   C,2Ah.2      ; TRNGL
0B7E  ORL   C,2Ah.3      ; SQUARE
0B80  ORL   C,2Bh.4      ; ARBIT
0B82  JC    0B86h
0B85  RLC   A            ; sonst verdoppeln
0B86  RR    A            ; und immer halbieren
```

Für Sinus, Dreieck, Rechteck und Arbitrary wird der Wert halbiert, für
die Pulsformen bleibt er stehen — die Scheitelfaktorkorrektur. Sie
erklärt auch, warum das Arbitrary-EEPROM Minimum und Maximum je Kurve
mitführt.

Vorbedingung für einen Feinwert ungleich null (0B58h): AC muss ein sein
und die Kurvenform darf nicht DC sein.

---

## 21 Auswertung der Rasten

### Beschleunigung

Bei 25F6h wird die Rastenzahl R3 in eine Schrittweite umgesetzt:

```
25F9  CJNE  A,#01h,2605h     ; eine Raste -> Schritt 1
2605  ANL   A,#0F0h
2607  JZ    261Dh
261D  MOV   A,R3
261F  MOVC  A,@A+PC
2622  03 06 09 0C 0E 11 14 17 1A 1D 20 23 25 28 2B
```

Zwei Rasten ergeben Schritt 3, drei ergeben 6, vier 9. Ab 16 Rasten
greift die zweite Tabelle bei 260Eh:
`2E 2E 31 34 38 3A 3B 3C 3C 3D 3D 3E 3E 3E 3E`.
Schnelles Drehen springt also in großen Schritten.

### Parameterwahl

RAM 24h, unteres Nibble, bestimmt die angewählte Gruppe:

| Wert | Gruppe |
|---|---|
| 0 | Kurvenform |
| 1 | Frequenz |
| 3 | Wechselamplitude |
| 4 | Gleichanteil |
| 5 | Modulationsparameter |

22h.3 ist der eingeschaltete AC-Ausgang.

### Erstverstellung

```
2637  CJNE  A,#03h,264Fh
263D  JNB   22h.3,264Fh
2640  MOV   56h,#30h        ; Amplitude initialisieren
2647  MOV   57h,A           ; aus der Drehrichtung
2649  CLR   22h.3
264B  SETB  29h.0           ; Nachladen anfordern
264F  CJNE  A,#04h,265Dh
2657  MOV   58h,#10h        ; Gleichanteil initialisieren
```

Die erste Rastung nach dem Einschalten eines Ausgangs setzt einen
Startwert, erst die folgenden verstellen. Der scheinbare Sprung auf
3000, den ich zunächst für eine Bereichsgrenze hielt, ist genau diese
Initialisierung.

### Offen

Die Zahlenformel von der eingegebenen Spannung zu 1Ch fehlt noch. Nach
der Initialisierung reagiert die Amplitude in meinem Emulator auf
weitere Rasten nicht; die generische Verstellroutine ab 265Dh mit
`LCALL 080Bh` und der Ziffernzeiger-Tabelle bei 268Ch ist noch nicht
durchgerechnet. Das ist der nächste Ansatzpunkt — und derselbe Weg
öffnet dann auch Gleichanteil und Modulationsparameter, weil alle drei
über dieselbe Routine laufen.

---

## 22 Die übrigen Stellgrößen

Alle folgenden Formeln sind durch direkten Aufruf der Originalroutinen
im Emulator geprüft, jeweils über mehrere Stützstellen.

### Gemeinsame BCD-Wandlung

0F40h wandelt drei BCD-Ziffern in eine Binärzahl 0…999 und liefert die
Dekade in R2:

```
W = 100 · (erstes Byte & 0Fh) + 10 · (zweites Byte >> 4) + (zweites Byte & 0Fh)
D = erstes Byte >> 4
```

0F45h ist derselbe Einsprung ohne Dekade, 0F65h mit R4 = 0.

### Amplitude — STR9, ein Byte

```
1Ch = RR(W mod 256)              Sinus, Dreieck, Rechteck
1Ch = (W mod 256) & 7Fh          Puls- und Sägezahnformen
```

`RR A` ist eine Rotation ohne Carry, keine Division: aus E7h wird F3h,
nicht 73h. Belegt an sieben Stützstellen.

Vorbedingung (0B58h): 22h.3 muss null sein — das Bit bedeutet **AC
aus**, nicht ein. Arbitrary läuft über einen eigenen Zweig ab 0B61h mit
RAM 48h und den Deskriptorwerten aus dem D310.

### Gleichanteil — STR7, zweites Byte

```
1Dh = 64h + W    Vorzeichenbit 58h.7 = 0
1Dh = 64h − W    Vorzeichenbit 58h.7 = 1
```

Offset-Binär um 100, Bereich 00h…C8h, also ±100 Stufen. Neun
Stützstellen geprüft.

### AM-Grad und FM-Hub — STR5

Quelle ist 5Ch/5Dh bei AM, 5Eh/5Fh bei FM (0BE5h/0BEAh):

```
AM:  19h = 2 · W       100 % Grad -> C8h
FM:  19h = W           0…255
```

Bei 0C08h steht `MOV C,2Ch.2 / MOV P1.1,C` — die FM-Leitung FMO zum
Taktgenerator, unabhängige Bestätigung der Portzuordnung aus
Abschnitt 12. Acht Stützstellen geprüft.

### Burst-Zyklen — STR4

Quelle 62h/63h, Ergebnis als 16-Bit-Wert in 13h:14h (0C71h):

```
Dekade 0:  N = W                 1…999
Dekade 1:  N = W + 1000          1000…1999
sonst:     N = 2000              Begrenzung
```

Ohne Burst steht die Vorgabe 0190h = 400. Neun Stützstellen geprüft.

### Symmetrie — STR3

Der Pulsgenerator benutzt eine nichtlineare Korrekturkurve (0E2Fh):

```
0E2F  SUBB  A,#32h        ; Symmetrie minus 50 %
0E33  CPL A / INC A       ; Betrag
0E35  MOV   DPTR,#10DDh
0E38  MOVC  A,@A+DPTR
0E43  ADD   A,#80h        ; Offset-Binär
0E48  MOV   13h,A
```

Tabelle 10DDh, 31 Einträge für 0…30 % Abweichung:

```
0, 5, 10, 15, 20, 25, 29, 34, 39, 44, 49, 53, 58, 62, 67, 71,
76, 80, 84, 88, 92, 96, 100, 104, 107, 111, 114, 118, 121, 124, 127
```

Die Schrittweite fällt von 5 auf 3 — eine kompressive Kennlinie, weil
das Tastverhältnis nicht linear von der Steuerspannung abhängt. Bei
30 % Abweichung ist 127 erreicht, die volle Aussteuerung. Der
Symmetriebereich ist damit 20 % bis 80 %.

### Bilanz

Damit sind alle sechs Analogbaugruppen erschlossen: TWS (Frequenz),
Amplitude Controller mit Attenuator, DC-Generator, Modulationsoszillator,
Burst-Logik und Pulsgenerator. Offen bleibt der Sweep über STR8, dessen
Rampenschleife bei 1CF3h bekannt, dessen Skalierung aber noch nicht
gerechnet ist.

---

## 23 Der Sweep

Der Sweep läuft nicht über eine Neuberechnung des TWS-Worts, sondern
über einen Akkumulator und eine daraus abgeleitete Adresse.

### Die Rampenschleife

```
1CF3  MOV   TL1,#1Bh        ; Schritttakt
1CF6  MOV   TH1,#0FCh
1CFB  MOV   DPH,#86h        ; STR6 auslösen (TWS übernimmt)
1CFF  MOV   DPH,#80h
1D03  MOV   SBUF,39h        ; ein Byte Sweep-Ausgangsspannung
1D0C  MOV   DPH,#88h        ; STR8 -> Unit 1
1D14  MOV   R0,#0F0h        ; zwei Byte aus dem oberen RAM
1D17  MOV   SBUF,@R0
1D22  MOV   SBUF,@R0        ; (R0 = F1h)
1D2A  MOV   DPH,#81h        ; STR1 -> Seitenauswahl Unit 4
1D32  RET
```

Je Schritt also: TWS übernehmen, ein Byte an den Sweep-Ausgang, zwei
Byte an die Seitenauswahl des Wellenform-RAM. Der Schritttakt kommt
aus Timer 1 mit FC1Bh — derselben Konstante wie beim Pen-Lift.

### Die Schrittrechnung

1D62h bildet die beiden Bytes bei RAM F0h/F1h aus dem Akkumulator
12h:13h:

```
1D64  A = (12h & 1Fh) | (13h & E0h)
1D6E  RL A dreimal                    ; Fenster um 3 Bit verschieben
1D72  A = 13h & 1Fh
1D76  ADD A,#08h                      ; Rundung
1D78  C = ACC.4 -> 22h.4              ; Rundungsbit merken
1D80  @F0h = Übertrag + verschobener Wert
1D81  A = 18h, ACC.6 = 2Bh.4 (ARBIT), ACC.0 = Rundungsbit
1D8C  @F1h = A
```

Der Akkumulator selbst wird bei 1D38h um ein Bit nach links geschoben
(Verdopplung über alle vier Bytes 11h…14h) beziehungsweise bei 1D4Eh
um R6 erhöht. Start- und Stoppfrequenz bestimmen den Anfangswert und
die Schrittweite; die Umrechnung dorthin ist noch nicht gerechnet.

**Stand:** Struktur, Telegramme, Schritttakt und Bitentnahme sind
geklärt. Was fehlt, ist die Ableitung des Akkumulator-Startwerts und
der Schrittweite aus fSTART und fSTOP.
