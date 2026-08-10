# Design-Auftrag: WeintCompanion 2.0

Dieser Text ist so geschrieben, dass er unverändert in Claude Design
eingefügt werden kann. Alles darunter gehört in das Eingabefeld.

---

## Produkt

**WeintCompanion** ist die Desktop-Begleit-App zum World-of-Warcraft-
Addon **WeintCodex** (Mists of Pandaria Classic). Sie installiert und
aktualisiert das Addon, sichert Spieldaten, verbindet das Spiel mit
einem Discord-Bot — und enthält zwei eigene Module:

- **WeintTV** — Live-Ansicht eines Raid-Pulls: Bosslebensbalken,
  Pull-Uhr, DPS-/HPS-Ranglisten, Tode, Abklingzeiten,
  Mechanikfehler, Ereignisspur. Dazu ein Archiv vergangener Kämpfe
  und eine sekundenweise Wiedergabe.
- **WeintAcademy** — Trainingsprogramm: sechs Sternebewertungen
  (Rotation, Bewegung, Abklingzeiten, Mechaniken, Überleben,
  Leistung) und ein daraus abgeleiteter Lektionsplan.

Zielgruppe: erwachsene Raid-Spieler einer deutschen Gilde,
25 Personen, zwei feste Raidabende. Die App läuft **neben dem Spiel**,
oft auf einem zweiten Bildschirm.

**Alle Oberflächentexte sind Deutsch.**

## Auftrag

Ein vollständiges Neudesign für Version 2.0. Die heutige App ist ein
funktionierendes, aber generisches dunkles Dashboard: Karten mit Titel,
Statuszeile, Detailzeile, dazu Emoji als Statusanzeige (🟢🔴🟡). Es
soll **frischer, eigenständiger und lebendiger** werden — mit einer
echten Bewegungssprache — ohne an Übersichtlichkeit zu verlieren.

Wichtigste inhaltliche Neuausrichtung: **die Startseite zeigt heute den
Zustand der Installation** (WoW gefunden? Addon installiert? Updates?
Backups?) — ab dem zweiten Tag ist alles dauerhaft grün. Sie soll
stattdessen zeigen, **was für den Spieler heute ansteht**.

---

## Gestalterische Richtung

- **Stimmung**: dunkel, hochwertig, ruhig. Fantasy-Bezug über
  Material und Licht, nicht über Ornamente. Keine Pergament-Textur,
  keine Schnörkelrahmen, keine Drachen.
- **Referenzgefühl**: eine Mischung aus einem sehr guten
  Entwicklerwerkzeug und einer Übertragungsgrafik im Sport — sachlich,
  aber mit Anwesenheit. Datendichte ohne Enge.
- **Wichtig**: es soll nicht nach „Bootstrap-Admin-Panel im Dark Mode"
  aussehen. Schichtung, Licht und Rhythmus sollen die Arbeit machen,
  nicht Rahmen um alles.

### Farben (Ausgangspunkt, darf verfeinert werden)

Die Marke soll die beiden heute getrennten Farbwelten zusammenführen:
das Addon ist bernsteinfarben, die App violett.

```
Flächen        #0A0A0C  Grund
               #0F0F12  Karte
               #08080A  Sidebar / vertiefte Flächen
               #17171C  angehobene Fläche / Hover
Rahmen         #1E1E24  #2A2A34
Marke          #D4A24A  Bernstein  (Hauptakzent, aus dem Addon)
               #E8C96D  Bernstein hell
Fläche-Akzent  #A855F7 → #6366F1  Violett-Indigo-Verlauf
                        (nur Verläufe/Flächen, nie Bedeutungsträger)
Bedeutung      ok    #7CC06E
               warn  #D4A24A
               error #E56B6B
               live  #E56B6B (pulsierend)
               info  #8B95F5
Text           #E8E8EA  #A8A8B0  #6B6B74  #4A4A52
```

Zusätzlich mitentwerfen: **drei Akzentvarianten** (Bernstein, Arkan-
Violett, Jade), die der Nutzer wählen kann. Bitte zeigen, wie
dieselbe Ansicht in allen dreien wirkt.

### Typografie

- **Inter** für alles Fließende
- **JetBrains Mono** für Zahlen, Zeiten, Werte, Versionen und die
  kleinen Rubriklabels in Versalien mit weiter Laufweite
- Größen (Ausgangspunkt): 28 / 18 / 15 / 14 / 13 / 12 / 11 px

Beide Schriften werden mit der App ausgeliefert — sie dürfen also
uneingeschränkt eingesetzt werden.

### Raum und Form

- Raumskala 4 / 8 / 12 / 16 / 24 / 32 / 48
- Radien 6 / 10 / 14 / 20 / Pille
- Zwei Dichten: **Komfortabel** (Standard) und **Kompakt** (etwa 15 %
  weniger Raum, für kleine Bildschirme) — beide bitte zeigen

---

## Technische Grenzen (bitte ernst nehmen)

Umgesetzt wird das in **Python mit Qt 6 (PySide6)**. Qt beherrscht
einen begrenzten Teil von CSS. Entwürfe, die das ignorieren, lassen
sich nicht bauen:

| Geht **nicht** | Umgang damit |
|---|---|
| `transition`, `@keyframes`, CSS-Animation | Jede Bewegung wird in Python programmiert. Bitte Bewegung als **Zustand A → Zustand B + Dauer + Kurve** beschreiben, nicht als CSS. |
| `box-shadow` | Schatten sind teure Einzeleffekte. Höhe bitte über **gemalte Kanten, Verläufe und Flächenhelligkeit** ausdrücken. Ein weicher Schatten pro Bildschirm ist vertretbar, nicht auf jeder Karte. |
| `backdrop-filter` / Milchglas | Nur als vorgerechnetes Bild möglich. Höchstens auf statischen Flächen (Titelleiste, Schublade). |
| Flexbox, CSS-Grid | Layouts sind Zeilen, Spalten und Raster fester Spaltenzahl. Bitte klar angeben, was fest und was dehnbar ist. |
| Beschneiden von Inhalt an runden Ecken | Runde Behälter mit farbigem Inhalt bitte vermeiden oder ausdrücklich kennzeichnen. |
| Beliebige Formen, Pfad-Masken, SVG-Filter | Symbole sind einfarbige SVGs, die in einer Themefarbe eingefärbt werden. |

**Geht dagegen gut**: lineare und radiale Verläufe, 1-px-Rahmen mit
Transparenz, Rundungen, eigengezeichnete Elemente (Punkte, Ringe,
Balken, Sparklines), Deckkraft-Übergänge, Verschiebungen, Skalierung.

---

## Bewegung

Sechs Muster, bitte jeweils Dauer und Kurve angeben:

1. **Bereichswechsel** — Überblendung plus kleiner Versatz in
   Navigationsrichtung, etwa 180 ms.
2. **Zahlen** — laufen auf ihren neuen Wert zu (~240 ms, weich
   auslaufend), springen aber bei sehr großen Sprüngen sofort.
3. **Balken** — die Breite bewegt sich, der beschriftete Wert nicht.
4. **Ladezustände** — Skelettflächen mit Schimmer. Sie erscheinen erst
   nach etwa 250 ms Wartezeit. **Das ist wichtig:** ein Archivabruf
   dauert real bis zu drei Minuten.
5. **Puls** — der LIVE-Zustand und Warnungen atmen im Sekundentakt.
   Höchstens eine Pulsquelle gleichzeitig sichtbar.
6. **Meldungen** — kurze Einblendungen unten rechts statt Dialogen.

Bitte zusätzlich eine **reduzierte Variante** mitdenken: derselbe
Bildschirm, wenn der Nutzer „Bewegung reduzieren" gewählt hat.

Grundsatz: Bewegung erklärt einen Zustandswechsel und seine Herkunft.
Was sich viermal pro Sekunde ändert (die Wiedergabe eines Kampfes),
wird **nicht** animiert.

---

## Fensteraufbau

Rahmenloses Fenster mit **eigener Titelleiste** (Ziehen, Maximieren,
eigene Fensterknöpfe). Links eine Navigationsspalte, die zwischen
232 px mit Beschriftung und 72 px nur mit Symbolen umschaltbar ist.

Zielgrößen: 1440 × 900 als Entwurfsgröße, **1120 × 720 muss
funktionieren**, 960 × 640 ist das angestrebte Minimum. Haltepunkte:

- unter 1280 px: die rechte Nebenspalte wird zu einer Schublade
- unter 1120 px: die Navigation klappt auf Symbole ein
- unter 980 px: Kartenraster einspaltig, Tabellen scrollen seitlich

### Navigation

```
RAID        Übersicht · WeintTV · Academy · Archiv
CHARAKTER   Meine Charaktere · Vorbereitung
SYSTEM      Addon & Updates · Verbindungen · Einstellungen · Protokoll
```

---

## Zu entwerfende Bildschirme

**Vorrangig (1–5):**

1. **Übersicht** — die neue Startseite. Enthält: „Heute" (nächster
   Raidtermin mit Countdown und Aufstellung), „Dein letzter Pull"
   (schwächster Bewertungsbereich + eine konkrete Lektion),
   „Vorbereitung" (ein Fortschrittsring über alle Charaktere) und eine
   **einzelne Systemzeile** mit vier Punkten für Addon, App, Sync und
   Sicherung — die sich nur bei Handlungsbedarf aufklappt.

2. **WeintTV, live** — die datendichteste Ansicht der App. Oben Boss,
   Lebensbalken, Pull-Uhr, LIVE-Zeichen. Darunter DPS- und
   HPS-Rangliste (bis 25 Zeilen, mit Klassenfarben und Balken), Tank-
   Kacheln, Tode, Raid-Abklingzeiten, eine Ereignisspur.
   **Die eigentliche Aufgabe: 25 Zeilen lesbar unterbringen, ohne dass
   es eng wird.**

3. **Academy, Profil** — sechs Sternebewertungen als Hauptbild, der
   schwächste Bereich hervorgehoben, darunter der Lektionsplan mit
   Prüfergebnissen (bestanden / nicht bestanden / **keine Daten** —
   dieser dritte Zustand ist wichtig und darf nie wie „schlecht"
   aussehen). Dazu neu: ein **Verlauf über mehrere Raidabende**.

4. **Addon & Updates** — zwei Komponenten (Addon und App) mit
   installierter Version, verfügbarer Version, Änderungsnotizen und
   Aktionsknopf. Bitte den Zustand „Update wird gerade heruntergeladen"
   mit Fortschritt mitentwerfen.

5. **Leer- und Ladezustände** — mindestens drei: „kein Raid aktiv",
   „Archiv wird geladen" (das dauert Minuten), „keine Verbindung zum
   Bot". Jeder mit genau einem sinnvollen nächsten Schritt.

**Nachrangig (6–9):**

6. **Archiv** — Bericht wählen, Pull wählen, abspielen, mit
   Wiedergabeleiste (Uhr, Regler, Geschwindigkeit bis 8×).
7. **Vorbereitung** — alle Charaktere nebeneinander: fehlende
   Verzauberungen, leere Sockel, offene BiS-Slots.
8. **Overlay** — ein sehr kleines, immer sichtbares Fenster
   (etwa 380 × 220) mit Pull-Uhr, Boss-Prozent, eigenem Rang.
9. **Einrichtung** — vier geführte Schritte für den ersten Start.

## Bausteine, die durchgängig gebraucht werden

Statuspunkt (gemalt, optional pulsierend — **er ersetzt alle
Status-Emoji**) · Chip · Kennzahlkachel mit Verlauf · Sparkline ·
Fortschrittsring · Balkenzeile mit Klassenfarbe · Datentabelle
(dicht, 25 Zeilen) · Sternebewertung mit Nullzustand „keine Daten" ·
senkrechte Ereignisspur · Skelettfläche · Meldungsstreifen ·
Leerzustand · segmentierter Umschalter · Umschaltknopf · Auswahlfeld ·
Wiedergabeleiste.

## Was nicht passieren soll

- Emoji als Bedeutungsträger
- ein Rahmen um jedes Element (Schichtung statt Kästen)
- reines Violett als Markenfarbe — Bernstein soll gleichberechtigt sein
- Dekoration, die keine Information trägt
- ein heller Modus (die App läuft neben einem Vollbildspiel im Dunkeln)
- Bewegung um der Bewegung willen

## Gewünschte Lieferform

Für jeden Bildschirm eine Ansicht in 1440 × 900 und, wo es einen
Unterschied macht, dieselbe in 1120 × 720. Dazu die Bausteinübersicht
mit allen Zuständen (Ruhe, Überfahren, Gedrückt, Aktiv, Deaktiviert,
Ladend, Fehler) und die Farb-/Raum-/Schrift-Skalen als benannte Werte —
diese Namen werden anschließend eins zu eins zu den Design-Tokens im
Code.
