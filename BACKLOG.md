# BACKLOG

Offene Punkte, nach Nutzen geordnet. Jeder Eintrag nennt den konkreten
Einstieg, damit man ohne Anlauf loslegen kann.

---

## P1 — Sweep zu Ende rechnen

**Ziel:** Ableitung des Akkumulator-Startwerts und der Schrittweite aus
fSTART und fSTOP.

**Bekannt:** Rampenschleife 1CFBh, Schrittrechnung 1D62h, Akkumulator
11h…14h, Verdopplung 1D38h, Addition 1D4Eh. Je Schritt gehen ein Byte
an STR8 und zwei Byte an STR1.

**Einstieg:** Wer schreibt 11h…14h und R6 vor dem Sweepstart? Aufrufer
von 1D38h ist 1C8Fh, von 1D4Eh ist 19ECh. Dort ansetzen.

**Methode:** Wie beim Frequenzpfad — Startwerte setzen, 1D62h direkt
aufrufen, Ausgabe gegen die Formel prüfen.

---

## P2 — Drehknopf, zweite Richtung

**Ziel:** Beide Drehrichtungen verstellen den Parameter.

**Bekannt:** Quadratur bei 25C2h funktioniert, R3 zählt korrekt,
Beschleunigungstabellen 2622h und 260Eh, Gewichte 26ABh,
Zuwachstabelle 2724h.

**Problem:** Eine Richtung läuft in die Initialisierung bei 2640h
(Amplitude) beziehungsweise 2657h (Offset) statt in die Verstellung.

**Einstieg:** 265Dh mit `LCALL 080Bh` und die Zeigerlogik bei
269Ch/26A0h einzeln durchspielen. Vermutlich muss ein Zustandsbit
gesetzt sein, das mein Ruhepegel nach dem Gray-Zyklus nicht erzeugt.

---

## P3 — Anzeige-Bitmap nachprüfen

**Ziel:** Die Zuordnung Annunciator zu Puffer-Bit aus Abschnitt 15 nach
den Emulatorkorrekturen bestätigen.

**Grund:** Die Tabelle entstand, als `ACALL` noch falsch ausgeführt
wurde. Kurvenform- und Modulationszeile sind seither nachgeprüft, die
übrigen Bits nicht.

**Methode:** `sweep.py` und `sweep3.py` mit dem korrigierten Kern
erneut laufen lassen und die Ergebnisse vergleichen.

---

## P4 — Die 1 900 unklassifizierten ROM-Bytes

**Ziel:** Feststellen, ob dort erreichbarer Code liegt.

**Bekannt:** 44 145 Byte belegt, 30 518 als Code getract, rund 11 700
als Tabellen identifiziert.

**Verdacht:** Indirekte Aufrufe über Funktionszeigertabellen, die der
rekursive Abstieg nicht findet. Auch der Block 9AFFh–9BB8h, 186 Byte,
disassembliert sauber, wird aber von nirgends erreicht.

**Methode:** Im Emulator während längerer Läufe alle ausgeführten
Adressen protokollieren und mit der statischen Analyse vergleichen.

---

## P5 — Schnittstellenprotokoll

**Ziel:** Die Kommunikation zur IEEE-488- beziehungsweise
RS-232-Karte auf I²C-Adresse 5Eh.

**Bekannt:** Handler 5F2Eh–627Eh, Zustandsbits in 26h, 25h.7 zeigt an,
ob eine Karte bestückt ist. Ohne Karte wird der Arbitrary-Test
übersprungen.

**Nutzen:** Erst damit ließe sich der Fernsteuerbetrieb im Simulator
nachbilden.

---

## P6 — Restliche Zustandsbits

**Ziel:** Von 128 Flags in 20h–2Fh sind 54 zugeordnet.

**Material:** `PM5139_Bit_Kreuzreferenz.md` listet für jedes Bit alle
Setz-, Lösch- und Abfragestellen.

**Methode:** Wie bei der Anzeige — Flag kippen, Wirkung beobachten,
im Listing gegenprüfen.

---

## P7 — Kommentiertes Master-Disassembly

**Ziel:** Aus dem automatisch erzeugten Listing eine lesbare Fassung
mit Funktionsnamen, RAM-Symbolen und Kopfkommentaren machen.

**Voraussetzung:** Sinnvoll erst, wenn P1 bis P4 abgearbeitet sind,
sonst kommentiert man Vermutungen.

---

## Kleinkram

- Simulator: Anzeigefelder für AC/DC und das untere Zahlenfeld sind nur
  teilweise gerendert; die Einheitenanzeige (MHz/kHz/V/ms) fehlt.
- Simulator: LOCAL, ADDR und RESET fehlen als Tasten (sie laufen nicht
  über den Encoder, brauchen also eigene Leitungen im Modell).
- `analyze2.py`: Sprungtabellen werden heuristisch erkannt. Für andere
  ROMs wäre eine Datenflussanalyse robuster.
- V1.5 ist bisher kaum im Emulator gelaufen; alle Messungen stammen aus
  V1.3.
