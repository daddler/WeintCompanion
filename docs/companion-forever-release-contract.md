# Companion-Forever: Release-Vertrag

**Wer das hier liest:** wer im Repository `daddler/Companion-Forever`
den Build oder die Veröffentlichung baut. Diese Datei beschreibt
*ausschliesslich*, wie ein Release aussehen muss, damit die
bestehende WeintCompanion-4.x-Anwendung es findet, prüfen und
installieren kann. Sie schreibt nichts über den Inhalt, die
Architektur oder die Oberfläche der neuen Anwendung vor.

Umgekehrt gilt dasselbe: WeintCompanion greift **nie** auf Quelltext,
Dateien oder Projektstruktur von Companion-Forever zu. Die einzige
Verbindung zwischen beiden Anwendungen ist das, was hier steht.

Die Umsetzung auf der 4.x-Seite: `core/migration/`, beschrieben in
`systems/forever-migration.md`.

---

## 1. Repository und Verteilung

| | |
|---|---|
| Repository | `daddler/Companion-Forever` |
| Verteilung | GitHub Releases (`GET /repos/daddler/Companion-Forever/releases`) |
| Sichtbarkeit | öffentlich, **spätestens** wenn die Migration freigegeben wird |

Solange das Repository privat ist, antwortet GitHub jedem Nutzer mit
`404`. Das wird auf der 4.x-Seite als "noch nichts veröffentlicht"
gelesen und **nicht** als Fehler — es darf also gefahrlos schon
gesucht werden, bevor es etwas zu finden gibt.

Die Abfrage läuft gegen die **Liste** der Releases, nicht gegen
`releases/latest`. Das ist Absicht: `latest` folgt GitHubs eigenen
Regeln und kann eine gültige 5.0.0 verschweigen, wenn daneben eine
neuere Vorabfassung liegt.

Es wird **keine** bestimmte Build-Pipeline vorausgesetzt. GitHub
Actions ist der naheliegende Weg, aber nichts in der 4.x-Anwendung
hängt daran; was zählt, ist das fertige Release.

---

## 2. Versionierung

- **Semantisch**, drei Teile: `MAJOR.MINOR.PATCH`.
- Tag-Format: `vX.Y.Z` (das `v` ist optional, wird aber erwartet —
  beide Schreibweisen gelten als dieselbe Fassung).
- Die erste Fassung ist **`v5.0.0`**. Nicht 1.0.0, nicht 4.2.0: die
  bestehende Produktlinie steht bei 4.x, und die neue Generation
  setzt sie fort.
- Vorabfassungen nach SemVer mit Bindestrich: `v5.0.0-beta.1`,
  `v5.0.0-rc.2`.
- Ein Tag, der sich nicht so lesen lässt (`latest`, `nightly`,
  `release-5`), wird von der 4.x-Anwendung **ignoriert**, nicht
  geraten.

Was die 4.x-Anwendung sucht, ist die höchste Fassung mit
`major == 5`. Eine `4.9.0` im Zielrepository ist kein
Generationswechsel; eine `6.0.0` gehört einem späteren Wechsel, der
von einer 5.x aus angeboten wird.

---

## 3. Kanäle

| Kanal | Nimmt | Wer |
|---|---|---|
| `stable` | nur fertige Fassungen | alle Nutzer (Vorgabe) |
| `beta` | zusätzlich `-beta.*`, `-rc.*` | Erprobung |
| `development` | zusätzlich `-alpha.*`, `-dev.*`, `-nightly.*`, `-preview.*` | Entwicklung |

Ein Release wird über seinen **Tag** eingeordnet, nicht über das
`prerelease`-Häkchen auf GitHub. Beides kann auseinanderlaufen, und
der Tag ist das, was der Nutzer später als Fassung sieht. Das
Häkchen zu setzen ist trotzdem richtig — es steuert, was GitHub
selbst als `latest` anzeigt.

`draft`-Releases werden nie berücksichtigt.

---

## 4. Assets: Benennung

Jedes 5.x-Release **muss** für beide Plattformen je eine
Installationsdatei und je eine Prüfsumme enthalten:

```
Companion-Forever-<version>-x86_64.AppImage
Companion-Forever-<version>-x86_64.AppImage.sha256
Companion-Forever-Setup-<version>-x64.exe
Companion-Forever-Setup-<version>-x64.exe.sha256
```

Beispiel für `v5.0.0`:

```
Companion-Forever-5.0.0-x86_64.AppImage
Companion-Forever-5.0.0-x86_64.AppImage.sha256
Companion-Forever-Setup-5.0.0-x64.exe
Companion-Forever-Setup-5.0.0-x64.exe.sha256
```

Die Auswahl (`core/migration/assets.py`) arbeitet nach Endung und
Architektur, nicht nach dem vollen Namen — der Produktname im
Dateinamen darf sich also ändern. Verbindlich sind:

- **Endung.** Linux `.AppImage`, Windows `.exe` (ersatzweise
  `.msi`). Gross-/Kleinschreibung egal.
- **Architektur im Namen**, sobald es mehr als eine gibt:
  `x86_64`/`amd64`/`x64` bzw. `aarch64`/`arm64`. Eine Datei **ohne**
  Architekturangabe gilt als "für alle" und wird genommen, wenn
  keine passendere daliegt. Eine Datei mit *fremder* Architektur
  wird nie genommen — lieber kein Wechsel als ein Wechsel auf ein
  Programm, das nicht startet.
- **Genau eine** gleichwertige Datei je Plattform. Liegen zwei
  gleich gut passende AppImages im Release, wird **keine** gewählt,
  das Release gilt als unvollständig und der Nutzer bekommt kein
  Angebot.

Nie als Installationsdatei erkannt werden: `.sha256`, `.sha512`,
`.md5`, `.sig`, `.asc`, `.pem`, `.txt`, `.json`, `.yml`/`.yaml`
sowie alles, dessen Name "Source code" enthält.

---

## 5. Integrität

Zu **jeder** Installationsdatei gehört eine Datei
`<dateiname>.sha256`. Ohne sie wird der Wechsel abgebrochen — nicht
mit Warnung fortgesetzt.

Inhalt, eine dieser drei Formen:

```
<64 Hex-Zeichen>
<64 Hex-Zeichen>  <dateiname>
<64 Hex-Zeichen> *<dateiname>
```

Die zweite Form ist die Ausgabe von `sha256sum` und die empfohlene.
Enthält die Datei mehrere Zeilen, entscheidet der Dateiname; kommt er
nicht vor, gilt die Prüfsumme als nicht vorhanden.

**Signaturen** sind noch nicht vorgesehen, aber vorbereitet: die
Prüfung läuft über eine Schnittstelle mit einer Methode
(`core/migration/integrity.Verifier`). Ein Signaturprüfer tritt
später neben den SHA-256-Prüfer, ohne dass sich am Ablauf etwas
ändert. Wer in Companion-Forever bereits Signaturen veröffentlicht,
legt sie als `<dateiname>.sig` daneben — sie werden dann von der
4.x-Seite ignoriert, stören aber nicht.

---

## 6. Was die Installationsdateien können müssen

### Linux (AppImage)

- Ausführbar, ohne Installation lauffähig.
- Die 4.x-Anwendung legt sie **neben die laufende AppImage** (oder,
  wenn sie aus dem Quelltext läuft, unter
  `~/.local/share/WeintCompanion/forever/`), setzt das Ausführbit und
  startet sie.
- Sie darf die bestehende `WeintCompanion*.AppImage` **nicht**
  überschreiben — dafür genügt der eigene Dateiname.

### Windows (Installer)

- Muss `/VERYSILENT /SUPPRESSMSGBOXES /NORESTART` verstehen.
- Muss die Anwendung nach der Installation **selbst starten**. Bei
  Inno Setup heisst das: `[Run]` **ohne** `skipifsilent` (genau wie
  `packaging/installer.iss` dieser App).
- Rückgabewert `0` heisst erfolgreich; alles andere gilt als
  Fehlschlag, und der Wechsel wird abgebrochen.
- Muss in ein **eigenes** Verzeichnis installieren und darf eine
  vorhandene WeintCompanion-4.x-Installation weder entfernen noch
  verändern. Die alte Fassung ist der Rückfallweg.

---

## 7. Datenübernahme (Migration Payload)

Vor dem Start der neuen Anwendung legt die 4.x-Seite eine
Übergabedatei ab:

| | |
|---|---|
| Linux | `~/.local/share/WeintCompanion/handover/migration.json` |
| Windows | `%LOCALAPPDATA%\WeintCompanion\handover\migration.json` |

Companion-Forever darf sie lesen, muss es aber nicht. Aufbau:

```json
{
    "schema_version": 1,
    "created_at": "2026-09-17T20:15:00",
    "source": {
        "product": "WeintCompanion",
        "version": "4.9.0",
        "platform": "Linux",
        "config_dir": "/home/…/.local/share/WeintCompanion/config",
        "data_dir": "/home/…/.local/share/WeintCompanion"
    },
    "target": {
        "product": "Companion-Forever",
        "repository": "daddler/Companion-Forever",
        "major": 5,
        "channel": "stable",
        "version": "5.0.0"
    },
    "settings": { "wow_client": "forever", "wow_paths": {"forever": "…"}, "…": "…" },
    "data_files": [
        {"role": "characters", "path": "…/characters.json", "exists": true, "migrate": true, "note": ""},
        {"role": "discord_account", "path": "…/discord_account.json", "exists": true,
         "migrate": false, "note": "enthaelt Zugangsdaten - nicht uebernehmen"}
    ],
    "discord": {"linked": true, "relink_required": true}
}
```

Regeln, die für beide Seiten gelten:

- **`schema_version` wird gelesen, bevor irgendetwas anderes gelesen
  wird.** Eine höhere Zahl als die bekannte heisst: nicht
  interpretieren.
- **`settings` ist ein Vorschlag, keine Struktur.** Die Schlüssel
  sind die der 4.x-Konfiguration; Companion-Forever ordnet sie so
  ein, wie es sie selbst braucht. Es ist ausdrücklich **nicht**
  gewollt, dass V5 die 4er-Konfigurationsstruktur übernimmt.
- **`data_files` trägt Pfade, keine Inhalte.** Beide Anwendungen
  laufen auf demselben Rechner.
- **Ein Eintrag mit `migrate: false` wird nicht eingelesen.**
  Zurzeit ist das `discord_account.json` — sie enthält das
  Companion-Token.
- **Es stehen keine Zugangsdaten in dieser Datei.** Keine Tokens,
  keine Passwörter, keine API-Schlüssel. Die Discord-Verknüpfung
  wird in V5 neu hergestellt (`relink_required`).
- Die Datei wird atomar geschrieben (erst `.tmp`, dann ersetzt) —
  eine halb geschriebene Übergabe kann es nicht geben.

Wächst der Payload später, steigt `schema_version`. Felder werden
**hinzugefügt**, nicht umbenannt.

---

## 8. Checkliste für v5.0.0

- [ ] Tag `v5.0.0`, Release kein Entwurf, kein Pre-Release-Häkchen
- [ ] `Companion-Forever-5.0.0-x86_64.AppImage` + `.sha256`
- [ ] `Companion-Forever-Setup-5.0.0-x64.exe` + `.sha256`
- [ ] AppImage startet auf einem System ohne vorinstalliertes Qt
- [ ] Installer versteht `/VERYSILENT /SUPPRESSMSGBOXES /NORESTART`
      und startet die Anwendung danach selbst
- [ ] Installer legt ein eigenes Verzeichnis an und fasst eine
      vorhandene WeintCompanion-Installation nicht an
- [ ] Release-Text vorhanden (er wird auf der 4.x-Seite zurzeit nicht
      angezeigt, gehört aber zu einem vollständigen Release)
- [ ] Probelauf gegen das echte Release bestanden (siehe
      `systems/forever-migration.md`, Abschnitt "Probelauf")

## 9. Checkliste für jedes weitere 5.x-Release

- [ ] Tag `vX.Y.Z`, semantisch grösser als der vorherige
- [ ] Beide Plattform-Assets, beide Prüfsummen, gleiche Benennung
- [ ] Genau **eine** Installationsdatei je Plattform und Architektur
- [ ] Vorabfassungen tragen `-beta.N`/`-rc.N` im Tag **und** das
      Pre-Release-Häkchen

Fehlt eines davon, bekommt niemand ein Angebot — die 4.x-Seite
meldet das Release im Protokoll als unvollständig und bleibt, wo sie
ist.
