# Changelog

Alle nennenswerten Änderungen an WeintCompanion, von Version 0.7.2 bis 1.4.3.

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
