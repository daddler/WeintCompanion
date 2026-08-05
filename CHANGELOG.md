# Changelog

Alle nennenswerten Änderungen an WeintCompanion, von Version 0.7.2 bis 1.6.0.

## 1.6.0

WeintTV und die WeintAcademy kennen jetzt die Fähigkeiten jeder
Spezialisierung.

Bisher konnten beide nur wiedergeben, was die Datenquelle geschickt
hat. Kam nichts, stand dort "Keine Angaben zu DoT-Uptimes" - und zwar
wortgleich für drei völlig verschiedene Sachverhalte: der Spieler hat
seinen DoT tatsächlich nie aufgelegt, die Quelle liefert diesen Block
nicht, oder es gibt für diesen Kampf gar keine Tiefenauswertung. Wer
seine HoT-Uptimes, DoT-Uptimes oder Cooldown-Einsätze vermisst hat,
konnte an der Oberfläche nicht erkennen, welcher der drei Fälle
vorlag.

Neu ist `analyzer/data/class_abilities.py`: alle 34
Spezialisierungen von Mists of Pandaria mit ihren DoTs, HoTs,
Selbstbuffs (bei Tanks die aktive Schadensminderung) und Cooldowns -
je mit Spell-ID, englischem und deutschem Namen, Richtwert und
Abklingzeit. Die Spell-IDs stammen aus dem Raidlog-Analyzer und sind
um die Spezialisierungen ergänzt, die dort keine hatten.

Was sich dadurch ändert:

- **Erkennung in drei Sprachen.** Jede gemeldete Zeile wird über
  Spell-ID, englischen und deutschen Namen erkannt - einer genügt.
  Ein deutscher Bericht ("Verjüngung") und ein englischer
  ("Rejuvenation") landen in derselben Zeile, und in der Oberfläche
  steht durchgängig der deutsche Name.
- **Richtige Einsortierung.** Ein HoT, den die Quelle unter die Buffs
  legt, landet trotzdem in der HoT-Karte. Vorher blieb sie leer,
  obwohl die Zahl da war.
- **Fehlendes wird sichtbar.** Liefert die Quelle eine Art von
  Wirkungsdauern, erscheinen die nicht gemeldeten Fähigkeiten der
  Spezialisierung mit null Prozent und dem Hinweis "nie aufgelegt" -
  ein Befund statt einer Leerstelle. Liefert sie diese Art gar nicht,
  wird auch nichts behauptet; stattdessen nennt der Platzhaltertext,
  was für diese Spezialisierung zu sehen wäre.
- **Talentabhängiges wird nie ergänzt.** Eine Zeile "Inkarnation - nie
  genutzt" bei jemandem ohne dieses Talent wäre ein Vorwurf für
  nichts.
- **Cooldown-Quoten sind fair geworden.** Gewertet wird nur noch, was
  auf Abklingzeit gehört. Ein ungenutzter Schildwall ist kein
  verschenkter Einsatz - vorher zog genau das die Bewertung von Tanks
  und Heilern nach unten, also der Rollen mit den meisten
  Defensivcooldowns.
- **Die Simulation zeigt jede Spezialisierung.** Bisher hatten nur
  siebzehn der fünfundzwanzig simulierten Spieler überhaupt
  Wirkungsdauern; ein Elementarschamane, ein Windwandler oder ein
  Arkanmagier hatte keine einzige Zeile. Jetzt bekommt jeder Spieler
  das, was seine Spezialisierung mitbringt.

## 1.5.2

Reiner Versionssprung, kein funktionaler Unterschied zu 1.5.1: der Tag
`v1.5.1` war auf den Stand vor dem Merge des Rotationstrainer-Fixes
gesetzt worden (`core/version.py` stand dort noch auf 1.5.0), und
genau das prüft `scripts/check_version.py` vor jedem Build - der
Build brach deshalb schon im Versionsabgleich ab, bevor irgendetwas
gepackt wurde. `v1.5.1` bleibt als kaputter Tag ohne Release stehen,
dieses Release trägt den Inhalt von 1.5.1 unter der nächsten
Versionsnummer nach.

## 1.5.1

Eine Übungssitzung am Trainingsdummy zählt erst ab drei Minuten.

Bisher genügten dreißig Sekunden, und die trugen dieselbe Tage-Serie
wie eine richtige Übungseinheit: dreimal kurz auf die Puppe geschlagen
hakte die Rotationslektion im Trainingsplan ab. `MIN_SESSION_SECONDS`
in `core/academy_dummy_sync.py` verwirft Sitzungen unter drei Minuten
jetzt schon vor der Serie. Die Zahl steht bewusst doppelt - WeintCodex
1.3.2.0 meldet nichts Kürzeres mehr, aber welche Addon-Version
installiert ist, entscheidet der Spieler, und eine ältere schickt
weiterhin kurze Sitzungen.

Die 23 Lektionen "Prioritätenliste an der Trainingspuppe üben" nennen
die Mindestdauer jetzt in ihren Schritten, statt sie stillschweigend
vorauszusetzen.

## 1.5.0

WeintTV und die WeintAcademy für Tanks, Heiler und Schadensausteiler
gleichermaßen.

Drei Fehler, die alle dasselbe Symptom hatten - es passierte nichts,
und niemand konnte sehen, dass etwas fehlte.

**Der Lektionskatalog kam im Echtbetrieb nie an.** Katalog und
Simulation führen die Spezialisierungen deutsch ("Vergeltung",
"Braumeister"), WarcraftLogs liefert sie englisch ("Retribution",
"Brewmaster"). Beim Nachschlagen traf deshalb kein einziger Schlüssel
zu: jeder Spieler bekam nur Rollen- und Allgemeinlektionen, ohne
Fehler und ohne Warnung, und in der Oberfläche war das nicht davon zu
unterscheiden, dass für seine Spezialisierung nichts hinterlegt ist.
`analyzer/data/specs.py` führt jetzt alle vierunddreißig
Spezialisierungen in beiden Sprachen samt Rolle.

**Tanks wurden gar nicht als Tanks erkannt**, wenn der Bot die Rolle
nicht mitschickte: geraten wurde aus Schaden gegen Heilung, und dabei
kann ein Tank nur als Schadensausteiler herauskommen. Er wird dann
gegen die Schadensrangliste der Schadensausteiler gemessen und bekommt
dauerhaft einen Stern, obwohl er seine Aufgabe erfüllt. Aus
"Protection", "Blood", "Guardian" oder "Brewmaster" folgt die Rolle
jetzt unmittelbar.

**Prüfkriterien, die eine Fähigkeit nennen, blieben in deutschen
Berichten dauerhaft "keine Daten".** WarcraftLogs gibt Fähigkeiten in
der Sprache des Clients zurück, der den Bericht hochgeladen hat -
derselbe Fehler, an dem auf der Bot-Seite schon einmal sämtliche
Cooldown-Listen gescheitert sind. `analyzer/data/player_abilities.py`
gleicht beide Sprachen ab.

Dazu die Lücke, die die Tankbewertung inhaltlich unbrauchbar machte:
der Snapshot kannte nur DoTs und HoTs. Die aktive Schadensminderung
eines Tanks - Schildblock, Mischen, Schild des Rechtschaffenen,
Knochenschild - ist weder das eine noch das andere, sie liegt auf ihm
selbst. In "Rotation" blieb deshalb allein die Aktivzeit übrig, also
ausgerechnet die Zahl, die über einen Tank am wenigsten aussagt. Es
gibt jetzt eigene Buff-Uptimes: in WeintTV als eigene Karte, in der
Academy als Rotationsbewertung der Tanks und als prüfbares Kriterium
der Lektionen. Wie alle Felder der Tiefenauswertung ist der Block
optional - fehlt er, steht dort "keine Daten" und keine schlechte
Note.

Zwei weitere Bewertungen waren zu freundlich: wer der einzige Spieler
seiner Rolle im Kampf war, wurde beim Platz in der Rangliste und beim
Laufweg mit sich selbst verglichen und bekam zwangsläufig die volle
Wertung. Das trifft regelmäßig den einzigen Tank und den einzigen
Heiler - also genau die beiden, denen eine geschenkte Bestnote am
wenigsten hilft. Ohne Vergleichsgruppe gibt es dort jetzt "keine
Daten".

Der Lektionskatalog ist von 165 auf 266 Lektionen gewachsen. Jede der
vierunddreißig Spezialisierungen hat jetzt eigene Inhalte zu Rotation
und Cooldowns, jede Klasse ihre Nutzfähigkeiten (Unterbrechung,
Seelenstein, Symbiose, Handzauber), und die fünf Tank- und sechs
Heiler-Spezialisierungen sind aus ihrem Zustand von ein bis zwei
Lektionen heraus. Auf der Rollenebene sind die Bereiche
dazugekommen, die vorher auf die allgemeinen Ratschläge fielen -
Überleben, Laufwege und Leistung für Heiler und Schadensausteiler,
Rotation, Cooldowns und Leistung für Tanks.

## 1.4.6

Der Wiedergabe-Knopf und die Ladezeiten.

Die Zeitleiste eines Pulls - die mit Abstand größte Antwort des Bots -
wurde erst auf Knopfdruck angefordert. Die gesamte Wartezeit lag damit
hinter dem Klick, und wer währenddessen ein zweites Mal drückte, löste
gar nichts aus: `start_replay()` brach bei laufendem Abruf wortlos ab.
Beides ist behoben. `RaidDataService.prefetch_timeline()` holt die
Zeitleiste jetzt schon beim Wählen des Pulls, parallel zum Abruf des
Pulls selbst, sodass die Wiedergabe im Normalfall ohne Wartezeit
startet; ein Druck während des Ladens wird vorgemerkt statt verworfen
(`ReplayState.starting`). Der Zeitleisten-Endpunkt bekommt außerdem
60 statt 15 Sekunden Zeit - dieselbe Frist wie für eine dreizeilige
Berichtsliste anzusetzen, war beim teuersten Abruf die knappste, und
das Ergebnis sah aus wie ein kaputter Knopf.

Während einer laufenden Wiedergabe waren Bericht- und Pull-Auswahl
nicht mehr bedienbar: `ArchivePicker` hängt an `replayChanged`, das
viermal je Sekunde gesendet wird, und leerte seine Auswahlfelder bei
jedem Takt - ein aufgeklapptes Dropdown klappte sofort wieder zu. Die
Felder werden jetzt nur noch neu gefüllt, wenn sich ihr Inhalt
wirklich geändert hat.

Dazu drei Ursachen für spürbare Trägheit, alle gemessen:

- `setStyleSheet()` verwirft in Qt die Stilberechnung eines Widgets
  und zeichnet neu, auch bei unverändertem Inhalt. Beim Zeichnen eines
  WeintTV-Snapshots kamen rund 280 solcher Aufrufe zusammen, drei
  Viertel der Rechenzeit eines Bildes. `gui/theme/restyle.py` setzt
  nur noch, was sich geändert hat: ein Bild kostet statt 25 nun 3,5 ms.
- WeintTV und die Academy hängen am selben `snapshotChanged` und
  zeichneten sich auch dann neu, wenn die jeweils andere Seite im
  Vordergrund war - bei laufender Wiedergabe dauerhaft doppelte
  Arbeit für ein Bild, das niemand sieht.
- Der Programmstart baute alle sieben Seiten im Voraus, obwohl meist
  nur eine angesehen wird; allein WeintTV und die Academy legen dabei
  ihre Listenzeilen auf Vorrat an. Seiten entstehen jetzt beim ersten
  Betreten (`MainWindow._ensure_page()`), der Start dauert statt rund
  vier nur noch knapp eine Sekunde.

## 1.4.5

Für niemanden in der Gilde kam ein Zugriffsprofil an: Discord-Rollen wie
"Admin", "Gildenleitung", "Klassen-Support" oder "Member" fehlten in der
Standard-Zuordnung Rolle → Rang, sodass `resolve_tier()` nie einen Rang
fand und im Addon (bewusst fail-open) immer alles offen blieb, statt echte
Freigaben zuzustellen. `core/access_roles.py`s `DEFAULT_ROLE_MAP` kennt jetzt
die tatsächlichen Rollennamen: Admin/Gildenleitung/Klassen-Support/Member als
gildeninterne Rollen bekommen "offizier", Raider/Friends als gildenexterne
Rollen "extern". Letzteres korrigiert nebenbei einen zu großzügigen
Alt-Stand, in dem "raider" fälschlich auf "mitglied" abgebildet war und
externen Mitraidern damit `materials.scan`/`loot.report`/`weinttv.raid`
freigegeben hätte.

## 1.4.4

Der Discord-Verknüpfungshinweis aus 1.4.3 hat seinen zweiten Absatz
abgeschnitten: Titel und Fließtext lagen direkt im Root-Layout, und
das wortumbrechende `QLabel` hat seine Höhe nicht zuverlässig an den
vollen Text angepasst, sodass der Hinweis auf die lokale Speicherung
der Anmeldedaten nicht mehr lesbar war. `gui/dialogs/discord_link_prompt.py`
packt Titel und Text jetzt - wie schon der "Was ist neu"-Dialog - in
eine `QScrollArea`, damit der Inhalt unabhängig von Schriftgröße oder
Zeilenzahl immer vollständig sichtbar bleibt.

## 1.4.3

Reiner Versionssprung wie schon bei 1.4.1: der Tag `v1.4.2` war
versehentlich auf einen veralteten Stand (`Version 1.2.6`, weit vor
der 1.4.2-Versionserhöhung) gesetzt worden, wodurch
`scripts/check_version.py` den Build zu Recht abgebrochen hat. Da
GitHub das Verschieben eines bereits veröffentlichten Tags per
Tag-Protection blockiert, gibt es statt eines korrigierten `v1.4.2`
diesen Patch-Tag - diesmal zusammen mit einer echten Änderung.

- Neu: Popup beim Programmstart, solange kein Discord-Account
  verknüpft ist (`gui/dialogs/discord_link_prompt.py`). Es weist
  darauf hin, dass der volle Funktionsumfang erst mit verknüpftem
  Discord-Account zur Verfügung steht und dass die Anmeldedaten
  ausschließlich lokal und temporär auf dem eigenen Rechner liegen.
  Schließbar wie jeder andere Dialog, erscheint aber - anders als das
  "Was ist neu"-Popup - bei jedem Start erneut, solange nicht
  verknüpft ist.

## 1.4.2

WeintCodex 1.3.0.0 bringt einen Rotationstrainer - ein kleines Fenster
im Addon, das live an einer Trainingspuppe die Prioritätenliste der
eigenen Spec abhakt. Diese Version verzahnt das mit dem Trainingsplan.

- Neu: Der Lektionskatalog bekommt pro DPS-Spec (alle 23) eine
  Rotations-Lektion "Prioritätenliste an der Trainingspuppe üben"
  (`analyzer/academy/lessons/classes/<klasse>.py`).
- Neu: `core/academy_dummy_sync.py` verarbeitet die vom Addon gemeldeten
  Übungssitzungen (`dummy_practice_session`, siehe
  `core/sync_manager.py`) und führt pro Charakter und Spec eine
  Tage-Serie. Drei aufeinanderfolgende Tage mit mindestens 80 %
  Trefferquote haken die zugehörige Lektion automatisch ab - über
  dieselbe Persistenz wie das manuell gesetzte Häkchen.
- `core/academy_service.py` speichert diese Serien jetzt zusätzlich
  unter `dummy_practice` in `academy_progress.json`.

## 1.4.1

Reiner Versionssprung: der Tag `v1.4.0` war versehentlich auf einen
Stand vor der 1.4.0-Versionserhöhung gesetzt worden, wodurch
`scripts/check_version.py` den Build zu Recht abbrach. Da GitHub das
Verschieben eines bereits veröffentlichten Tags per Tag-Protection
blockiert, gibt es statt eines korrigierten `v1.4.0` diesen Patch-Tag
auf demselben Funktionsstand. Kein Code hat sich gegenüber 1.4.0
geändert.

## 1.4.0

Wer mitraidet, aber nicht in der Gilde ist, kann WeintCompanion jetzt
gefahrlos bekommen: die App fragt die Discord-Rolle ab und stellt dem
Addon daraus ein Zugriffsprofil zu. WeintCodex 1.2.0.0 richtet danach
aus, welche Bereiche offenstehen - und verknüpft sich mit genau einer
Community, sodass sich die Daten zweier Gilden nicht mehr in derselben
SavedVariables-Datei vermischen können.

- Neu: Zugriffsprofil-Zustellung. Die Rollennamen kommen vom Bot
  (`GET /companion/access-profile`), die Zuordnung auf Rang und
  Freigaben passiert hier in `core/access_roles.py` - eine im Discord
  umbenannte Rolle lässt sich damit ohne neue Companion-Version
  nachziehen.
- Neu: Einstellung `access_role_map`, um die Zuordnung
  Rollenname → Rang zu überschreiben, und
  `access_profile_sync_enabled`, um die Zustellung abzuschalten.
- Neu: Nachrichten an das Addon tragen die Discord-Guild-ID. Das Addon
  verwirft damit Daten, die zu einer anderen Community gehören, statt
  sie einzuarbeiten - relevant, wenn in der App der verknüpfte
  Discord-Account gewechselt wird.
- Behoben: `SyncReader.remove_message()` baute die verbleibenden
  Nachrichten aus einer festen Feldliste neu auf und verlor dabei
  Felder, die es noch nicht kannte. Eine Nachricht, die auf den
  nächsten Zyklus wartete, verlor so still ihre Herkunftsangabe.
- Wichtig: Solange der Bot den Endpunkt nicht bereitstellt, wird kein
  Profil zugestellt und im Addon bleibt alles offen - genau wie vor
  WeintCodex 1.2.0.0. Der Vertrag steht in
  `docs/access-profile-bridge.md`.
- Wichtig: Das ist **keine Sicherheitsgrenze.** Die Zuordnungstabelle
  liegt wie die SavedVariables des Addons auf dem Rechner des Spielers.
  Der Nutzen ist zweierlei: die Community-Bindung verhindert das
  Vermischen zweier Gilden, und die Freigaben halten die Oberfläche
  ehrlich. Vertraulichkeit leistet das nicht - dafür müsste der Bot
  eine unberechtigte Nutzlast gar nicht erst ausliefern.

## 1.3.0

WeintTV und die Academy gibt es jetzt auch im Spiel - abgespeckt, für
alle, die nur einen Monitor haben und im Raid nicht dauernd aus WoW
heraus wollen. Diese Version stellt die Auswertung dem Addon zu; die
Anzeige selbst bringt WeintCodex 1.0.1.0 mit.

- Neu: Die zuletzt ausgewertete Analyse wird ins Addon gestellt -
  erhaltener und vermeidbarer Schaden samt "Was tun"-Hinweis,
  Wirkungsdauern, Aktivzeit, Laufwege, Cooldown-Nutzung,
  Unterbrechungen und Mechanikfehler. Dazu Sternebewertung,
  Trainingsplan und Lektionskatalog des gewählten Charakters.
- Neu: Bridge-Karte "WeintTV & Academy ingame" auf der Sync-Seite,
  mit der sich die Zustellung abschalten lässt.
- Neu: Ingame abgehakte Lektionen und abgewählte Katalogeinträge
  kommen zurück auf den Desktop - der Lernpfad ist damit auf beiden
  Seiten derselbe.
- Wichtig: Zugestellt wird, was WeintTV oder die Academy zuletzt
  ausgewertet haben. Der Raid-Datendienst wird dafür bewusst nicht
  dauerhaft gestartet, damit die Anwendung nicht im Hintergrund
  pollt, wenn niemand die beiden Seiten benutzt.
- Wichtig: Das Addon liest die Zustellung beim Login bzw. nach
  /reload - dieselbe Bedingung wie beim Raid-Roster-Import. Ein
  Live-Bild im Spiel ist technisch nicht möglich, WoW liest seine
  SavedVariables nur beim Laden ein.
- Intern: Die Inbox Richtung Addon hat jetzt Kanäle. Vorher hat jeder
  Absender die komplette Warteschlange ersetzt - mit zwei Absendern
  im selben Sync-Durchlauf hätte der zweite die Nachrichten des
  ersten gelöscht.
- Intern: Nutzlasten Richtung Addon dürfen verschachtelte Tabellen
  sein und werden als echtes Lua geschrieben. Ein Trennzeichen-Format
  wäre für Lektionstexte und Schadenshinweise nicht eindeutig
  gewesen - genau die Zeichen, die als Trenner taugen, kommen darin
  vor.

## 1.2.6

Der Wiedergabe-Knopf meldete für jeden Pull "Für diesen Pull liefert
der Bot keine Zeitleiste", und die Analyse blieb bei DoT-/HoT-Uptimes,
Laufwegen, Unterbrechungen und Cooldowns leer. Beides lag am Bot, der
die Daten nie geliefert hat - diese Version wertet aus, was er ab
sofort schickt.

- Wichtig: Diese Version wertet Daten aus, die erst ein
  aktualisierter WeintCodex-Bot liefert. Solange der Bot noch nicht
  aktualisiert ist, ändert sich in WeintTV und der Academy nichts.
- Fix: Die Wiedergabe hat nie funktionieren können - den Endpunkt für
  die Zeitleiste gab es im Bot schlicht nicht, und seine Antwort
  "nicht gefunden" erschien als "Für diesen Pull liefert der Bot keine
  Zeitleiste". Er ist jetzt umgesetzt.
- Fix: DoT-/HoT-Uptimes, Laufwege, Unterbrechungen und Dispels sowie
  Raid- und Heil-Cooldowns blieben leer, weil der Bot Fähigkeiten über
  ihren englischen Namen suchte. WarcraftLogs liefert die Namen aber
  in der Sprache des Berichts - in einem deutschen Log passte kein
  einziger. Erkannt wird jetzt über die Zauber-ID sowie den deutschen
  und den englischen Namen.
- Neu: Laufwege werden geliefert. Der Wert ist eine Schätzung aus den
  Positionsangaben der Kampfereignisse und ist als solche
  beschriftet - als Vergleich innerhalb eines Pulls belastbar, als
  absolute Zahl nicht.
- Die Bewertung, ob ein Treffer vermeidbar war, liegt wieder
  ausschließlich in der App. Der Bot schickt nur noch Treffer mit
  Zeitpunkt. Fähigkeiten ohne hinterlegte Regel erzeugen weiterhin
  keinen Eintrag - lieber eine Lücke als ein Vorwurf an jemanden, der
  nichts falsch gemacht hat.

## 1.2.5

Enthält alles aus 1.2.4 - dieses Release kam nie bei euch an: sein Tag
zeigte auf den Stand von 1.2.3, das Update installierte deshalb wieder
1.2.3 und bot sich danach erneut selbst an.

- Fix: Der Build bricht jetzt ab, wenn ein Tag nicht zu der im Code
  hinterlegten Version passt, statt ein Release mit falscher
  Versionsnummer zu veröffentlichen. Genau das hatte zuvor schon
  v1.2.0 und v1.2.1 getroffen.

## 1.2.4

- Fix: Der Wiedergabe-Knopf in WeintTV und der Academy funktioniert
  jetzt wirklich. Er blieb im Live-Modus unsichtbar, weil die
  Verfügbarkeit geprüft wurde, bevor die Datenquelle überhaupt
  bestand. Und selbst wenn eine Wiedergabe startete, stand sie
  danach still: die Uhr wurde aus dem Ladethread heraus gestartet,
  was Qt stillschweigend ablehnt.
- Fix: Ein Wechsel des Berichts, des Pulls oder der Datenquelle
  verwarf die bereits geladene Zeitleiste nicht - der nächste Druck
  auf Wiedergabe spielte deshalb den vorherigen Kampf ab, eingefroren
  bei 00:00.
- Fix: Ein Klick in die Zeitleiste (statt Ziehen am Regler) sprang
  nicht an die gewählte Stelle.
- Fix: Die Wiedergabe wird nicht mehr im Klick-Moment berechnet -
  die Oberfläche bleibt beim Start bedienbar.
- WeintTV: "Kampfereignisse" zeigt jetzt den ganzen Verlauf eines
  Pulls - zusätzlich zu Toden, Kampf-Rezz und Heldentum auch
  Unterbrechungen, Dispels, Mechanikfehler mit Zeitpunkt sowie
  Phasenwechsel und angesagte Bossfähigkeiten der Datenquelle.
- WeintTV: Liefert die Datenquelle keine Tiefenauswertung, steht dort
  jetzt ein erklärender Hinweis statt zehn leerer Karten - mit dem
  Unterschied zwischen "kein Raid", "kein Pull läuft" und "diese
  Quelle liefert nur Summen".
- WeintAcademy: Derselbe Hinweis erscheint bei der Bewertung, damit
  unbewertete Bereiche nicht wie ein Defekt aussehen.
- WeintTV: Aktivzeit nennt zusätzlich die längste Pause, Uptimes die
  Zahl der Anwendungen.

## 1.2.3

- Vorbereitung der WarcraftLogs-Anbindung für die Tiefenanalyse: der
  Vertrag mit dem WeintCodex Bot ist um DoT-/HoT-Uptimes,
  Cooldown-Nutzung sowie Unterbrechungen und Dispels ergänzt. Sobald der
  Bot diese Daten liefert, füllen sich die entsprechenden Karten in
  WeintTVs Analyse automatisch - bis dahin bleiben sie unverändert
  "keine Daten".

## 1.2.2

- Fix: Das Companion-Update blieb manchmal mit "Keine Prüfsumme für das
  Companion-Update verfügbar" stehen, obwohl der Release ganz normal eine
  Prüfsumme hatte. Ursache war eine Teilstring-Suche bei der Asset-Auswahl,
  die unter bestimmten Bedingungen die von der CI veröffentlichte
  ".sha256"-Datei selbst statt der eigentlichen Installationsdatei als "das
  Asset" erkennen konnte - danach lief die Suche nach deren eigener
  Prüfsumme zwangsläufig ins Leere und das Update wurde aus
  Sicherheitsgründen abgebrochen.

## 1.2.0

WeintTV und die WeintAcademy sind vollständig ausgebaut.

- WeintTV: Wiedergabe. Ein abgeschlossener Pull lässt sich Sekunde für
  Sekunde abspielen - mit Schieberegler, Pause und 1x bis 8x. WeintTV und
  die Academy zeigen dabei immer denselben Moment.
- WeintTV: Neue Karte "Kampfereignisse" im Live-Bereich. Tode,
  Kampf-Wiederbelebungen und Heldentum auf einer gemeinsamen Zeitachse -
  endlich ist ablesbar, WANN Heldentum lief und AUF WEN ein Rezz ging.
- WeintTV: Die Analyse ist von vier auf zehn Karten gewachsen - erhaltener
  Schaden mit Vermeidbarkeitsanteil, vermeidbarer Schaden je Fähigkeit samt
  Hinweis was zu tun war, DoT- und HoT-Uptimes, Laufwege, Aktivzeit,
  Cooldown-Nutzung über den ganzen Kampf sowie Unterbrechungen und Dispels.
- WeintTV: Spielerfilter in der Analyse. Ohne ihn wären 25 Spieler mal sechs
  Tabellen unlesbar.
- WeintTV: Ein Klick auf eine Analysezeile öffnet diesen Spieler in der
  Academy.
- Academy: "Rotation" bewertete bisher nur den Platz in der Schadensliste -
  das ist eine Ausrüstungsbewertung, keine Aussage über die Spielweise.
  Rotation misst jetzt Aktivzeit, Aktionen pro Minute und die
  Wirkungsdauern der eigenen Effekte. Der Rang bleibt sichtbar, aber als
  eigener Bereich "Leistung".
- Academy: Neuer Bereich "Überleben" - erhaltener Schaden und sein
  vermeidbarer Anteil, gemessen gegen die eigene Rolle. Ein Tank bekommt
  zwangsläufig den meisten Schaden ab; nach Summe zu bewerten hieße, ihn für
  seine Aufgabe zu bestrafen.
- Academy: Cooldowns werden jetzt tatsächlich bewertet - genutzte gegen
  mögliche Einsätze und der Anteil, der im Heldentum lag.
- Academy: Der Trainingsplan erkennt selbst, ob eine Lektion im gewählten Log
  eingehalten wurde: erfüllt, nicht erfüllt oder keine Daten, jeweils mit dem
  gemessenen Wert gegen das Ziel. Der eigene Haken bleibt daneben bestehen.
- Academy: Aus einem Befund springt man an die Sekunde der Wiedergabe, an
  der er entstanden ist.
- Academy: Der Katalog ist von 23 auf über 100 Lektionen gewachsen -
  allgemein, nach Rolle, je Klasse und Spezialisierung sowie bossbezogen.
  Jede lässt sich abwählen; standardmäßig sind alle aktiv, und neu
  hinzukommende Lektionen erscheinen automatisch.
- Academy: Fehlt einer Bewertung die Datengrundlage, zeigt sie das
  ausdrücklich an, statt eine Note zu erfinden.
- Die Einordnung "war dieser Treffer vermeidbar" liegt jetzt im Companion und
  nicht im Bot. Sie ist dreiwertig: was nicht hinterlegt ist, bleibt "nicht
  eingeordnet" - sonst bekäme jeder Boss ohne Referenzdaten automatisch eine
  tadellose Bewertung.
- Referenzdaten für alle vierzehn Bosse der Schlacht um Orgrimmar: welcher
  Schaden vermeidbar war, welcher zum Kampf gehört, was stattdessen zu tun
  gewesen wäre. Dazu Lektionen zu jedem dieser Kämpfe, die der Trainingsplan
  selbst gegen das Log prüft.
- Die Simulation liefert alle neuen Auswertungen mit, sodass sich beides auch
  außerhalb der Raidzeit ansehen lässt.
- Fix: Kampf-Wiederbelebungsladungen werden von den tatsächlich gewirkten
  Rezzes verbraucht, nicht von Todesfällen.
- Fix: Der Live/Archiv-Umschalter blieb während der Wiedergabe auf seinem
  alten Stand stehen.

## 1.1.5

- Neu: Die Bot-Anbindung liefert jetzt echte Daten für den "Analyse"-Bereich
  von WeintTV/WeintAcademy (Live und Archiv) - Heldentum, Verbrauchsgüter
  (Flask/Nahrung, Näherung) sowie genutzte Raid-/Heil-Cooldowns. Ein erster
  bossspezifischer Mechanikfehler (Immerseus) ist ebenfalls hinterlegt,
  weitere Bosse folgen schrittweise.

## 1.1.4

- Fix: Das Report-Dropdown des Archiv-Modus (WeintTV/WeintAcademy) zeigte bei
  mehreren gleichnamigen Berichten (z.B. wiederholt
  "Siege of Orgrimmar · Siege of Orgrimmar") keine Möglichkeit, sie
  auseinanderzuhalten. Zeigt jetzt Datum und Uhrzeit (lokal umgerechnet) vor
  Titel/Zone an.

## 1.1.3

- Fix: Der Release-Build von 1.1.2 schlug im Test-Schritt gelegentlich fehl
  (Race Condition beim schnellen Neustart der WarcraftLogs-Datenquelle -
  ein Hintergrund-Thread konnte unter ungünstigem Timing bis zu 60 Sekunden
  als Karteileiche stehen bleiben, statt sich sofort zu beenden). Reiner
  Build-/Interna-Fix, keine Auswirkung auf sichtbares App-Verhalten.

## 1.1.2

- Neu: **Archiv-Modus** für WeintTV und die WeintAcademy - zusätzlich zum
  Live-Feed lässt sich jetzt ein vergangener WarcraftLogs-Bericht auswählen
  und ein bestimmter Pull daraus ansehen (Bericht wählen, Pull darin wählen).
  Der Umschalter ist geteilt: ein Wechsel wirkt auf beiden Seiten gleich,
  damit WeintTV und Academy immer denselben Log betrachten. Setzt eine
  Discord-Verknüpfung voraus und wird erst nutzbar, sobald die
  entsprechende Bot-Anbindung live ist.

## 1.1.1

- Fix: Der Release-Build von 1.1.0 schlug im Test-Schritt fehl, weil zwei
  neu hinzugekommene Tests `core/raid_data_service.py` importierten, das auf
  Modulebene PySide6 lädt - die CI installiert für die Testsuite aber
  bewusst nur pytest, keine GUI-Abhängigkeiten. Reiner Build-/Test-Fix,
  keine Auswirkung auf die App selbst.

## 1.1.0

- Neu: **WeintTV** - ein Live-Dashboard für den Raid mit Bossleben,
  Pull-Timer, Schadens-/Heilrangliste, Tank-Übersicht, Cooldown- und
  Verbrauchsgüter-Status sowie erkannten Mechanikfehlern. Ein-/Ausschaltbar
  über Einstellungen → Module.
- Neu: **WeintAcademy** - leitet aus denselben Raiddaten ein persönliches
  Lernprofil ab (Sternebewertung für Rotation, Bewegung, Cooldowns und
  Mechaniken, relativ zur eigenen Rolle) und daraus einen Trainingsplan mit
  den nächsten sinnvollen Lektionen. Ebenfalls über Einstellungen → Module
  steuerbar.
- Neu: WeintTV und die Academy teilen sich eine gemeinsame Datenquelle, die
  sich in Einstellungen → Module umschalten lässt:
  - **Simulation** - ein deterministischer Beispiel-Pull, mit dem sich
    beide Ansichten jederzeit prüfen lassen, auch ohne laufenden Raid.
  - **WarcraftLogs** - liest den laufenden Livelog-Bericht über den
    WeintCodex-Bot (die App verbindet sich nicht selbst mit WarcraftLogs).
    Gilt für den gesamten Raid, unabhängig davon, ob dieser Rechner selbst
    mitloggt; die Werte sind durch die Art der Übertragung einige Sekunden
    im Verzug, was in der Oberfläche offen ausgewiesen wird. Setzt eine
    Discord-Verknüpfung voraus und wird erst nutzbar, sobald die
    entsprechende Bot-Anbindung live ist.
- Neu: Erkennung des WoW-Combat-Logs (Einstellungen → Module) als
  Grundlage für eine spätere Live-Auswertung direkt aus dem Kampfprotokoll.
- Aufräumen: Die Seitennavigation wurde auf eine einzige, zentrale Liste
  (`gui/navigation.py`) umgestellt - Sidebar und Seitenstapel können damit
  strukturell nicht mehr auseinanderlaufen.

## 1.0.1

- Neu: "Was ist neu"-Popup - erscheint einmalig nach dem Start und zeigt bei
  einer Neuinstallation eine kurze Tour durch Dashboard, Addon-Verwaltung,
  Sync/Discord-Bridges und Einstellungen. Bei einem Update auf eine neue
  Version werden stattdessen die Änderungen aus genau diesem Changelog
  angezeigt. Über die Checkbox im Dialog oder den Schalter in
  Einstellungen → Allgemein lässt sich das Popup dauerhaft abschalten bzw.
  die Tour jederzeit erneut aufrufen.
- Fix: Der Windows-Installer zeigte im Setup-Assistenten und unter "Apps &
  Features" weiterhin Version 0.9.1 an, obwohl die App selbst bereits auf
  1.0.0 stand.

## 1.0.0

Erster offizieller Release. Neben allgemeiner Politur enthält dieser Release
mehrere Härtungen, die vor einem offiziellen 1.0-Release notwendig waren:

- Sicherheit: Downloads (Companion-Self-Update und WeintCodex-Addon-Update)
  werden jetzt per SHA-256-Prüfsumme verifiziert, bevor sie ausgeführt bzw.
  installiert werden. Für das Companion-Self-Update ist eine gültige
  Prüfsumme jetzt zwingend erforderlich - ohne sie wird kein Update mehr
  heruntergeladen.
- Fix: Die Addon-Installation (core/installer.py) ersetzte die bestehende
  Version bisher per "erst löschen, dann kopieren" - ein Absturz mitten
  im Update konnte den Nutzer komplett ohne installiertes Addon
  zurücklassen. Die Installation läuft jetzt über einen atomaren Swap
  (neue Version erst vollständig danebenbauen, dann in einem Schritt
  tauschen); schlägt selbst das fehl, wird automatisch versucht, aus dem
  zuvor erstellten Backup wiederherzustellen.
- Fix: config.json und die WoW-SavedVariables-Datei werden jetzt
  atomar geschrieben (write-temp-then-rename) statt direkt überschrieben -
  ein Absturz mitten im Schreiben kann keine der beiden Dateien mehr
  beschädigen. Eine dennoch beschädigte config.json wird beim nächsten
  Start nach "config.json.bak" verschoben statt stillschweigend mit
  Standardwerten überschrieben zu werden.
- Fix: Ein einzelner fehlerhafter/abgeschnittener Eintrag in der
  Sync-Warteschlange des Addons (z. B. durch einen Lesezugriff mitten in
  einem Schreibvorgang von WoWs Lua-VM) bricht nicht mehr den kompletten
  Sync-Zyklus ab, sondern wird übersprungen.
- Aufräumen: totes, nicht mehr funktionierendes Auth-Scaffolding
  (core/auth/) entfernt - die tatsächliche Discord-Verknüpfung läuft
  bereits vollständig über core/discord_auth.py.
- macOS wird für 1.0 nicht offiziell unterstützt (kein Build/CI-Ziel,
  bestehende Codepfade sind ungetestet).

## 0.9.1

- Neu: Bridge "Charakter-Roster" ist jetzt aktiv. Wer in der Twinkverwaltung
  (WeintCodex-Addon) einen Charakter auswählt, wird automatisch an die
  Charakter-Datenbank des Bots gemeldet (Grundlage für den Klassen-Abgleich
  beim Gilden-Kalender-Invite). Standardmäßig aktiviert, Umschaltung über
  die Sync-Seite. Erfordert WeintCodex ab v0.9.9.26 (Auswahl wird sofort statt
  erst beim nächsten Login gemeldet).

## 0.9.0

- Fix: Die Bridge-Karten "Charakter-Roster" und "Gilden-Kalender" auf der
  Sync-Seite waren vertauscht - die als "Charakter-Roster" aktiv markierte
  Bridge trieb tatsächlich schon den Export der Raid-Anmeldung in den
  Ingame-Kalender an (Gilden-Kalender), während "Charakter-Roster" als
  Feature (Online-Status je Charakter) noch gar nicht existiert. Jetzt
  korrekt beschriftet: "Gilden-Kalender" ist aktiv, "Charakter-Roster"
  ist als geplant markiert.

## 0.8.9

- Neu: Bridge "Loot-Verteilung" - vom Addon erfasste Item-Zuteilungen
  (Episch+, per Würfel oder Meisterlooter vergeben) werden bei aktivierter
  Bridge automatisch an einen Discord-Kanal gemeldet. Standardmäßig
  deaktiviert, Umschaltung über die Sync-Seite.

## 0.8.8

- Fix: "Addon-Ordner öffnen" konnte auf KDE-Systemen (z. B. Nobara) lautlos
  fehlschlagen bzw. mit einem Absturz von "kde-open" enden. Ursache: von
  PyInstaller gesetzte Variablen wie QT_PLUGIN_PATH wurden an den
  gestarteten "xdg-open"-Prozess vererbt, wodurch dessen "kde-open" die
  Qt-Plattform-Plugins aus dem WeintCompanion-Bundle statt aus dem System
  zu laden versuchte und abstürzte. Diese Variablen werden jetzt zusätzlich
  aus der Umgebung externer Prozesse entfernt.

## 0.8.7

- Neu: Auf der Seite "Deine Installationen" wird jetzt neben WeintCodex auch
  WeintCompanion selbst gelistet - mit Versions-Diff (installiert → neueste),
  Changelog der installierten Version und einem Update-Button.

## 0.8.6

- Fix: Toggle-Schalter in den Einstellungen zeigten nach einem Neustart der
  App teils den falschen Zustand an.
- Installer-Version mit der App-Version synchronisiert.

## 0.8.5

- Neu: Autostart (App startet mit dem System) und "In den Tray minimieren"
  in den Allgemein-Einstellungen.

## 0.8.4

- Fix: Die "Über"-Buttons öffneten beim Klick lautlos keinen Browser mehr.

## 0.8.3

- Dashboard-UX: Der "WoW starten"-Button hebt sich stärker vom Hintergrund
  ab, leitet bei fehlendem Start-Befehl direkt zu den passenden
  Einstellungen weiter, gibt beim Speichern sichtbares Feedback und zeigt
  den Discord-Namen im Fenstertitel an.

## 0.8.2

- Dashboard: Die Seite kommt jetzt ohne Scrollen aus, der Zuschnitt des
  About-Banners wurde korrigiert.

## 0.8.1

- Fix: Der Versionsvergleich behandelte "v0.8" fälschlich als andere
  Version als "0.8.0" und löste dadurch unnötig "Update verfügbar" aus.

## 0.8.0

- Neu: Changelog-Panel im Dashboard, das die Änderungen der aktuell
  installierten Companion-Version anzeigt.

## 0.7.4

- Fix: Der Faugus-Start nutzte einen erfundenen `--start`-Flag statt der
  korrekten CLI und schlug dadurch fehl.

## 0.7.3

- Neu: "WoW starten"-Button, der Battle.net direkt aus dem Dashboard startet.
