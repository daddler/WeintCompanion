# Changelog

Alle nennenswerten Änderungen an WeintCompanion, von Version 0.7.2 bis 0.9.1.

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
