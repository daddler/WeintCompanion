# WeintCompanion 2.0 — Konzept

Stand: 10.08.2026 · Grundlage: WeintCompanion 1.7.0, WeintCodex 1.3.3.0,
WeintCodex-Bot (Stand vor dem Mittwochs-Pull)

Dieses Dokument beschreibt, was 2.0 werden soll: ein Neudesign mit
eigener Bewegungssprache, eine neue Struktur der Anwendung und die
Funktionen, die aus der Companion ein eigenständiges Produkt machen
statt eines Installationshelfers mit zwei angebauten Modulen.

Es beschreibt **nicht**, wie es implementiert wird — dazu gibt es pro
Phase einen eigenen Plan. Der Design-Auftrag für Claude Design steht in
`docs/design-brief-claude-design.md` und ist so geschrieben, dass er
dort unverändert eingefügt werden kann.

---

## 1. Wo die App heute steht

1.7.0 ist funktional weit: Installer, zwei Update-Kanäle, Backups,
Discord-Anbindung, Sync in beide Richtungen, WeintTV, Academy, Archiv,
Replay. Rund 60.000 Zeilen, 40 Testdateien, saubere Schichtung
(`analyzer/` ohne einen einzigen Qt-Import). Der Unterbau ist gut.

Das Problem ist nicht die Substanz, sondern was man davon sieht.

### 1.1 Das Dashboard beantwortet die falsche Frage

Die Startseite zeigt vier Karten: *Ist WoW gefunden? Ist das Addon
installiert? Gibt es Updates? Gibt es Backups?* Am ersten Tag ist das
genau richtig. Ab dem zweiten Tag sind alle vier dauerhaft grün, und
die wertvollste Fläche der Anwendung beantwortet eine Frage, die
niemand mehr stellt.

**Das Dashboard zeigt den Zustand der Installation, wo es den Zustand
des Raiders zeigen müsste.** Das ist der eigentliche Grund, warum sich
die App „wie ein Dashboard" anfühlt — nicht die Kartenoptik.

### 1.2 Konkrete Befunde aus dem Quellcode

| Befund | Fundstelle | Wirkung |
|---|---|---|
| **Schriften sind nicht mitgeliefert.** `Typography.FONT = "Inter"`, `MONO_FONT = "JetBrains Mono"` — es existiert keine einzige `.ttf`/`.otf` im Repo und kein `QFontDatabase.addApplicationFont()` | `gui/theme/typography.py`, `app.py` | Auf den meisten Windows-Rechnern rendert die App in Segoe UI, unter Linux in irgendetwas. Das Design, das entworfen wurde, sieht kaum jemand. |
| **Status wird über Emoji im String transportiert** (`"🟢 Installation gefunden"`, `"🔴 Nicht gefunden"`, `"🟡 1 Update verfügbar"`) | `gui/widgets/dashboard_cards.py` u. a. | Emoji folgen der Systemschrift, nicht dem Theme; sie sind auf jedem OS anders groß und anders bunt, lassen sich nicht einfärben und nicht animieren. Das ist der einzelne sichtbarste Prototyp-Marker der App. |
| **Animation existiert in genau zwei Widgets** von rund fünfzig | `hero_banner.py`, `toggle_switch.py` | Es gibt keine Bewegungssprache. Seitenwechsel springen, Zahlen springen, Balken springen. |
| **Mindestgröße 1500 × 900** | `gui/theme/metrics.py` | Die App lässt sich nicht neben ein Fenster-WoW auf einen 1080p-Schirm legen — für eine *Companion*-App die härteste Einschränkung überhaupt. |
| **Native Fensterleiste über vollständig eigenem Dark-UI** | `gui/main_window.py` | Die obersten 30 px sprechen eine andere Designsprache als der Rest. |
| **Acht leere `.py`-Dateien** (`action_button.py`, `top_bar.py`, `section_title.py`, `live_log.py`, `dashboard_controller.py`, `config.py`, `updater.py`, …) plus `gui/styles_old.py` | Repo-Wurzel und `gui/` | Totes Gewicht, das jede Orientierung im Ordner kostet. |
| **Kein Ladezustand.** Seiten zeigen `-` und „Nicht geprüft", solange Daten fehlen | alle Seiten | Ein Archiv-Abruf dauert laut `warcraftlogs_archive_client.py` bis zu **180 Sekunden** — genau dort, wo ein Skelett-/Fortschrittszustand am meisten wert wäre, steht ein Strich. |
| **Zwei Farbwelten in einem Ökosystem.** Companion: Violett/Indigo („Command Deck"). Addon: Bernstein/Gold („Codex", `core/ui.lua`) | beide Repos | Zwei Produkte derselben Marke, die nichts miteinander zu tun zu haben scheinen. |

### 1.3 Was gut ist und bleiben muss

- `RaidSnapshot` als einziger Vertrag zwischen Datenquelle und
  Oberfläche. Jede neue Ansicht bekommt ihre Daten geschenkt.
- Die Perf-Regeln aus `CLAUDE.md`: `restyle()` statt `setStyleSheet()`
  im Sekundentakt, versteckte Seiten zeichnen nicht, Seiten entstehen
  erst beim ersten Betreten. **2.0 darf diese Narben nicht wieder
  aufreißen** — dazu unten der Bewegungsetat (Abschnitt 3.4).
- Beide Update-Kanäle (Addon über `GitHubUpdater`, Companion über
  `CompanionUpdater` mit `linux_updater.py` / `windows_updater.py`).
  Die bleiben unangetastet und bekommen in 2.0 nur eine bessere
  Oberfläche.

---

## 2. Die Leitidee von 2.0

> **Aus einem Statusbrett wird ein Raid-Begleiter.**

Drei Sätze, an denen sich jede Entscheidung messen lässt:

1. **Die Startseite zeigt, was heute ansteht** — nicht, ob die
   Installation noch da ist. Installationszustand ist eine Zeile, kein
   Raster.
2. **Die App ist auch ohne Bot vollständig.** Alles, was 2.0 an
   Funktionen dazubekommt, läuft entweder allein oder aus der
   Kombination Companion + WeintCodex. Der Bot bleibt eine
   Verstärkung, keine Voraussetzung.
3. **Bewegung erklärt Zustandswechsel** — sie schmückt nicht. Jede
   Animation beantwortet „was hat sich gerade geändert und woher kam
   es".

---

## 3. Neudesign

### 3.1 Die Marke zusammenführen

Heute laufen zwei Paletten nebeneinander her. 2.0 macht daraus ein
System mit einer gemeinsamen Markenfarbe und zwei Umgebungen:

- **Bernstein/Gold `#D4A24A` wird die Markenfarbe.** Sie steht im
  Addon schon, sie ist WoW-nah, und die Companion führt sie bereits als
  `Colors.GOLD` — nur benutzt sie sie fast nirgends.
- **Violett/Indigo bleibt der Flächenton des Desktops.** Als
  Verlaufsakzent auf Karten, Rail und Bannern — nicht mehr als
  Bedeutungsträger.
- **Bedeutung wandert in semantische Rollen**: `accent`, `live`,
  `ok`, `warn`, `error`, `muted`. Kein Widget schreibt je wieder eine
  Hexfarbe. Konsequenz: ein Akzentwechsel ist eine Zeile, nicht eine
  Suchen-und-Ersetzen-Runde.

### 3.2 Ein Token-System statt Konstantenlisten

Heute: `colors.py`, `metrics.py`, `typography.py` — flache Listen, aus
denen jedes Widget sich seinen QSS-String selbst zusammenbaut.

2.0: `gui/theme/tokens.py` als einzige Quelle mit vier Skalen —

- **Raum** (4 / 8 / 12 / 16 / 24 / 32 / 48), abhängig von der
  gewählten Dichte
- **Radius** (6 / 10 / 14 / 20 / pill)
- **Höhe/Elevation** in drei Stufen, *gemalt* statt als
  `QGraphicsDropShadowEffect` (siehe 3.6 — Schatteneffekte sind in Qt
  teuer und begrenzen die Zeichenwege)
- **Bewegung**: Dauern (`FAST 120`, `BASE 180`, `SLOW 280`) und
  Kurven (`OutCubic` für Eingänge, `InOutQuad` für Lagewechsel)

Plus `Semantic`: `Semantic.status("live")` liefert Farbe, Kontrastfarbe
und Punktzustand. Das ist die Grundlage für Akzentwahl, Dichtewahl und
später einen hellen Modus, ohne dass eine einzige Seite davon weiß.

### 3.3 Fenster und Rahmen

- **Rahmenloses Fenster mit eigener Titelleiste.** Ziehen, Maximieren
  per Doppelklick, Fensterandocken, eigene Knöpfe. Die Leiste trägt
  links das Logo, mittig den aktuellen Bereich, rechts die globalen
  Zustände (Sync-Puls, Discord-Avatar, Update-Punkt). Das verändert
  die Identität der App stärker als jede Farbwahl.
- **Aufklappbare Sidebar statt reiner Icon-Rail.** 232 px mit
  Beschriftung und Gruppen, per Klick auf 72 px eingeklappt (der
  heutige Zustand). Die Einstellung wird gemerkt.
- **Neue Untergrenze: 1120 × 720**, Ziel 960 × 640. Drei
  Haltepunkte:
  - `< 1280`: Aktivitätsspalte wird zur Schublade über dem Inhalt
  - `< 1120`: Sidebar klappt automatisch auf Icons ein
  - `< 980`: Kartenraster einspaltig, Tabellen horizontal scrollend

### 3.4 Bewegung — mit ausdrücklichem Etat

Sechs Bausteine, alle in `gui/motion/`:

| Baustein | Wo | Regel |
|---|---|---|
| **Seitenwechsel** | `MainWindow.change_page()` | 180 ms Überblendung + 8 px Versatz in Navigationsrichtung. Nie beim ersten Aufbau einer Seite. |
| **`AnimatedNumber`** | DPS/HPS, Prozente, Zähler | `QVariantAnimation` über den Wert, 240 ms `OutCubic`. Springt bei Sprüngen > 40 % sofort (sonst „zählt" die Zahl beim Pull-Wechsel sichtbar hoch). |
| **`AnimatedMeter`** | Ranking-Balken, Bosslebensbalken | Es animiert die Breite, nie der Text. |
| **`Skeleton`** | Archiv-Abruf, Update-Prüfung, Bericht laden | Schimmer-Verlauf, erst nach 250 ms Wartezeit sichtbar — kurze Abrufe sollen nicht flackern. |
| **`Pulse`** | LIVE-Chip, Sync-Punkt, Warnzustände | 1 Hz Atmen. Genau eine gleichzeitig sichtbare Pulsquelle pro Bildschirm. |
| **`Toast`** | Erfolg/Fehler statt Logzeile | Unten rechts, 4 s, mit „Rückgängig" wo sinnvoll (Backup gelöscht, Auswahl geändert). |

**Der Etat — und warum er in diesem Repo nicht verhandelbar ist.**
`CLAUDE.md` hält fest, dass ein Replay mit 4 Hz tickt und dass genau
dort schon einmal drei Viertel der Bildzeit in überflüssigen
`setStyleSheet()`-Aufrufen verschwanden (25 ms → 3,5 ms nach dem Fix),
und dass unsichtbare Animationen im Academy-Katalog dutzendfach pro
Bild liefen. Deshalb:

1. Animiert wird **nur bei nutzerausgelösten Zustandswechseln** und
   bei Daten mit höchstens 1 Hz.
2. Alles, was aus `snapshotChanged` oder `replayChanged` kommt, setzt
   Werte **direkt** — `AnimatedNumber` und `AnimatedMeter` haben dafür
   ein `set_immediate()`.
3. Eine Animation, deren Ziel bereits erreicht ist, startet nicht neu
   (dieselbe Regel, die `ToggleSwitch` schon durchgesetzt bekommen hat).
4. **„Bewegung reduzieren"** als Schalter in den Einstellungen, und die
   Systemeinstellung wird respektiert. Dann bleiben nur Zustandswechsel
   ohne Zeitverlauf.

### 3.5 Komponenten, die neu entstehen

`StatusDot` (gemalt, gefärbt, optional pulsierend — ersetzt sämtliche
Status-Emoji) · `Chip` (Rolle, Schwierigkeit, Zustand) ·
`StatCard` (Kennzahl + Verlauf + Vergleich) · `Sparkline` (kleiner
Verlaufsgraph für Trends) · `Timeline` (senkrechte Ereignisspur) ·
`SkeletonBlock` · `Toast` · `EmptyState` (Symbol + Satz + genau ein
Knopf) · `SegmentedControl` (existiert, wird auf Tokens gehoben) ·
`AnimatedNumber` / `AnimatedMeter` / `Pulse`.

### 3.6 Was Qt hier *nicht* kann (und wie 2.0 damit umgeht)

Damit die Entwürfe umsetzbar bleiben — das gehört auch in den
Design-Auftrag:

- **Kein `transition`, kein `@keyframes` in QSS.** Jede Bewegung ist
  Python (`QPropertyAnimation`).
- **Kein `box-shadow`.** Nur `QGraphicsDropShadowEffect`, einer pro
  Widget, teuer und in Zusammenspiel mit anderen Effekten heikel.
  → Höhe wird als gemalter Rahmen + Verlaufskante gelöst.
- **Kein `backdrop-filter`.** Milchglas gibt es nur als vorgerechnetes
  Pixmap. → Sparsam und nur auf statischen Flächen (Titelleiste,
  Schublade).
- **`border-radius` beschneidet keine Kindwidgets.** Runde Container
  mit Inhalt brauchen eine Maske oder eigenes Zeichnen.
- **SVG-Symbole färben sich nicht von selbst um.** 2.0 braucht einen
  Icon-Cache, der eine SVG in der Tokenfarbe rendert und zwischenlegt.
- **`qlineargradient`/`qradialgradient` funktionieren** — Verläufe sind
  also erlaubt, aber nur als Flächenfüllung.

---

## 4. Neue Struktur

Aus sieben gleichrangigen Bereichen werden drei Gruppen:

```
RAID
  Übersicht        ← neue Startseite, ersetzt das Dashboard
  WeintTV
  Academy
  Archiv           ← eigener Bereich statt Ausklappmenü in zwei Seiten

CHARAKTER
  Meine Charaktere ← neu
  Vorbereitung     ← neu

SYSTEM
  Addon & Updates  ← heutige Seite "Software"
  Verbindungen     ← heutige Seite "Synchronisation"
  Einstellungen
  Protokoll
```

**Kein Bereich verschwindet, keine Funktion entfällt.** Die
Registry-Architektur aus `gui/navigation.py` trägt das unverändert: ein
Bereich ist weiterhin ein Enum-Eintrag plus ein `PageSpec`, die Gruppen
sind ein zusätzliches Feld. Der Grundsatz „nie eine nackte Zahl als
Navigationsziel" bleibt.

### 4.1 Die neue Übersicht

Statt vier Statuskarten:

- **„Heute"** — der nächste Raid aus dem bereits synchronisierten
  Roster (Mittwoch/Donnerstag), mit Countdown, Aufstellung und der
  eigenen Zusage. Diese Daten liegen schon in der App, sie werden nur
  nirgends gezeigt.
- **„Dein letzter Pull"** — schwächster Bereich aus dem Academy-Profil,
  eine konkrete Lektion, ein Knopf dorthin.
- **„Vorbereitung"** — Verzauberungen/Sockel/Verbrauchsgüter über
  *alle* Charaktere (siehe 5.2), als ein Fortschrittsring.
- **„Systemzeile"** — Addon, Companion, Sync, Backup als **eine**
  Zeile mit vier Punkten. Grün heißt: hier gibt es nichts zu tun. Bei
  Handlungsbedarf klappt genau die betroffene Zeile auf.

Der `PriorityBanner` bleibt im Prinzip erhalten — er ist heute schon
die beste Idee auf der Seite — nur nicht mehr als einziger Inhalt mit
Rang.

---

## 5. Neue Funktionen

Alle Vorschläge laufen **ohne Bot**. Sortiert nach Wirkung; die
Aufwandsangabe ist grob (S ≤ 2 Tage, M ≤ 1 Woche, L = mehrere Wochen).

### 5.1 Live-Combatlog als Datenquelle — *das Kernstück* · L

`analyzer/combatlog/` enthält heute nur `locator.py`; der
Provider-Vertrag (`analyzer/providers/base.py`) steht seit Anfang an
bereit. Fehlen: Tailer, Ereignis-Parser, Aggregatoren.

Warum das der wichtigste Punkt der Liste ist:

- **Die App wird eigenständig.** WeintTV und Academy laufen ohne Bot,
  ohne WarcraftLogs, ohne Internet.
- **Echtzeit statt Verzug.** Die WarcraftLogs-Strecke hängt laut
  Provider bis zu 45 Sekunden hinterher und rechnet die Pull-Uhr
  zwischenzeitlich selbst hoch. Der lokale Log liegt millisekundenaktuell.
- **Die teuersten Fehlerquellen der Bot-Strecke verschwinden.** Die
  ganze Geschichte um lokalisierte Fähigkeitsnamen (Seelenruhe ≠
  Tranquility) und um `auras` statt `entries` existiert lokal nicht:
  der Combatlog liefert Spell-IDs.
- **Es gilt auch außerhalb des Raids** — Dungeons, LFR, Solo, und vor
  allem die Trainingspuppe, an der der Rotationshelfer des Addons
  ohnehin schon misst.

Zu bedenken: Positionsdaten (für Bewegung) und mehrere Zusatzfelder
brauchen `advancedCombatLogging 1`. 2.0 erkennt das am Log-Format
selbst und sagt es in der Oberfläche, statt still weniger zu zeigen.

Aufteilung: `tailer.py` (Datei folgen, Rotation überstehen, ~200
Zeilen), `parser.py` (Zeile → typisiertes Ereignis, ~400), `aggregate.py`
(Ereignisse → `RaidSnapshot`, nutzt `analyzer/analysis/` unverändert
weiter). Danach ist es ein Eintrag in `PROVIDER_FACTORIES` — der Rest
der App merkt nichts.

### 5.2 Vorbereitungs-Check über alle Charaktere · M

Das Addon bewertet in `modules/charakter.lua` bereits jeden Slot auf
Verzauberung, Sockel und Statverteilung (0–100 Punkte pro Prüfung) und
kennt über `twinks` die Zweitcharaktere; `modules/bis.lua` kennt die
Lücken zur BiS-Liste. **Das alles existiert nur im Spiel, nur für den
gerade angemeldeten Charakter.**

Neue ausgehende Zustandsnachricht `character_gear` (dieselbe Bauart
wie `character_report` aus 1.7.0: lokal behandelt, geht nie zum Bot) →
die Companion zeigt vor dem Raid **alle** Charaktere nebeneinander:
fehlende Verzauberungen, leere Sockel, offene BiS-Slots, mit Sprung in
die Academy-Lektion, wo es eine gibt.

Das ist die Funktion mit dem besten Verhältnis aus Aufwand und
spürbarem Nutzen, weil beide Seiten die Daten schon haben.

### 5.3 Verbrauchsgüter- und Materialplaner · M

Das Addon führt `materialData` und `guildBankCache`, die Companion
kennt das Roster des nächsten Raids. Daraus:

> „Mittwoch, 25 Mann: 50 Fläschchen, 75 Mahlzeiten, 50 Tränke
> gebraucht — Gildenbank deckt 32/60/50 — es fehlen 18 Fläschchen und
> 15 Mahlzeiten."

Reine Rechnung auf vorhandenen Daten, ohne Bot. Für die Raidleitung
das, was heute in einer Tabelle nebenher läuft.

### 5.4 Pull-Journal und Raid-Rückblick · M

`PullSummary`/`history()` stirbt heute mit der Sitzung. 2.0 schreibt
Pulls nach `Paths.config()/pulls/` und baut daraus einen
**Abend-Rückblick**: Pull für Pull, Bestwerte, wo die Fehler weniger
wurden, wer sich verbessert hat. Ausgabe als Bild oder HTML, das die
Raidleitung von Hand in den Discord hängt — kein Bot nötig.

### 5.5 Fortschritt über Zeit · M

Die Academy bewertet heute **einen** Snapshot. Werden die sechs
Sternebewertungen je Charakter und Pull mitgeschrieben, entsteht der
Verlauf: „Mechaniken 2★ → 4★ über drei Raidabende". Das ist es, was
aus einer Momentaufnahme ein Trainingsprogramm macht — und es liefert
dem Neudesign gleichzeitig echte Diagramme statt weiterer Karten.

Wichtig, weil sonst der Sinn kippt: `stars == 0` heißt weiterhin
**keine Daten** und darf nie als Nullpunkt in eine Kurve eingehen.

### 5.6 Overlay-Modus · M

Ein rahmenloses Fenster (~380 × 220), immer im Vordergrund, mit
Pull-Uhr, Boss-Prozent, eigenem Rang, nächster Abklingzeit. Genau das,
was „Companion" bedeutet, und es kostet keine neuen Daten — es liest
denselben `RaidSnapshot`.

### 5.7 Benachrichtigungen · S

Das Tray-Icon ist da, `showMessage()` funktioniert auf beiden
Plattformen. Fehlen nur die Anlässe: Addon-Update verfügbar, Raid
beginnt in 30 Minuten (aus dem Roster), Pull beendet mit
Kurzbewertung, Sync seit X Minuten fehlgeschlagen.

### 5.8 WeakAura-Verwaltung auf dem Desktop · M

Das Addon führt `data/weakauras/*.lua` je Klasse. Die Companion kann
den Katalog zeigen, den Importstring direkt in die Zwischenablage
legen (ohne laufendes Spiel) und durch Lesen der WeakAuras-eigenen
`SavedVariables` beantworten, welche davon installiert und aktuell
sind. Eigenständig, ohne Bot.

### 5.9 Profile und Sicherungen · M

Backups existieren, sind aber unsichtbar. 2.0: benannte Schnappschüsse
von `WTF` + `Interface/AddOns`, Wiederherstellen mit Vorschau,
„Sicherung vor dem Raid", automatische Aufbewahrungsregel. Dazu
**mehrere WoW-Installationen** (heute genau ein `classic_path`).

### 5.10 Diagnose und Erste Hilfe · S

`faulthandler` schreibt `crash.log`, `app.py` trägt eine ganze Reihe
von Qt-Notlösungen mit `WEINT_FORCE_*`-Schaltern. Nichts davon hat
eine Oberfläche. Eine Diagnoseseite sammelt Version, Betriebssystem,
Qt-Plattform, Pfade, Addon-Version und die letzten Fehler in einen
kopierbaren Block — plus einen Schalter je Notlösung.

### 5.11 Einrichtung als geführter Weg · S

Der heutige Erstkontakt ist ein Dashboard voller roter Karten. 2.0
führt in vier Schritten durch: WoW finden → Addon installieren →
Discord verknüpfen (überspringbar) → Datenquelle wählen. Die
vorhandene `TOUR_PAGES`-Mechanik aus `whats_new_dialog.py` wird dazu
umgebaut, nicht ersetzt.

### 5.12 Auto-Update — bleibt, wird sichtbar · S

Ausdrücklich unverändert in der Sache: beide Kanäle, AppImage unter
Linux, Inno-Setup unter Windows, dieselben Runner. Was 2.0 ergänzt:

- **Fortschrittsbalken** statt eines Wartezustands ohne Rückmeldung
- **Herunterladen im Hintergrund**, danach „Zum Anwenden neu starten" —
  statt sofortigem Beenden mitten in der Arbeit
- **Kanalwahl** stabil/beta, damit Testversionen nicht an alle gehen
- **Fortsetzbarer Download**, denn eine abgebrochene Leitung fängt
  heute von vorn an

---

## 6. Reihenfolge

Drei Etappen, jede für sich auslieferbar. Die Seiten sind voneinander
unabhängig, deshalb wandert jede einzeln auf das neue Fundament — es
gibt keinen Stichtag, an dem alles gleichzeitig umgestellt sein muss.

**Etappe 1 — Fundament (keine Funktionsänderung).**
Schriften mitliefern · `tokens.py` + `Semantic` · Bewegungsmodul ·
`StatusDot` und Ende der Emoji · rahmenloses Fenster + Titelleiste ·
Haltepunkte und neue Mindestgröße · tote Dateien raus. Ergebnis: die
App sieht überall gleich und neu aus, kann aber exakt dasselbe.

**Etappe 2 — Struktur.**
Gruppierte Sidebar · neue Übersicht · Archiv als eigener Bereich ·
Ladezustände und Leerzustände · Toasts · geführte Einrichtung ·
Update-Oberfläche mit Fortschritt.

**Etappe 3 — Fähigkeiten.**
Live-Combatlog-Provider · Vorbereitungs-Check · Fortschritt über Zeit ·
Pull-Journal · Overlay · Materialplaner · Benachrichtigungen.

Was 5.2 und 5.3 betrifft: die Addon-Seite (eine neue ausgehende
Zustandsnachricht) ist klein und kann früh in WeintCodex landen, damit
zum Zeitpunkt der Companion-Umsetzung schon Daten fließen.

---

## 7. Was 2.0 nicht anfassen darf

- **Der `RaidSnapshot`-Vertrag.** Neue Ansichten lesen ihn, sie
  erweitern ihn nicht ohne Not.
- **Die Nutzlasten Richtung Addon** (`academy_catalog`,
  `academy_state`, `weinttv_report`, `access_profile`) — App und Addon
  aktualisieren unabhängig voneinander. Erweiterungen bleiben
  additiv und optional.
- **Die beiden Konventionen**: `stars == 0` heißt *keine Daten*,
  `at_seconds == -1` heißt *kein Zeitpunkt bekannt*.
- **`companionVersion` in jedem Inbox-Schreibvorgang**, auch im leeren.
- **Die Qt-Notlösungen in `app.py`** und ihre Reihenfolge vor dem
  PySide6-Import.
- **Die Perf-Regeln**: `restyle()` statt `setStyleSheet()`, versteckte
  Seiten zeichnen nicht, Seiten entstehen erst beim Betreten.
- **Beide Update-Kanäle** und der Aufbau-Weg (`WeintCompanion.spec`,
  Build-Skripte, CI auf `v*`-Tags).
