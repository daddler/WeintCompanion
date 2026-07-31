# Changelog

Alle nennenswerten Änderungen an WeintCompanion, von Version 0.7.2 bis 1.2.3.

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
