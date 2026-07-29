# Changelog

Alle nennenswerten Änderungen an WeintCompanion, von Version 0.7.2 bis 1.1.1.

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
