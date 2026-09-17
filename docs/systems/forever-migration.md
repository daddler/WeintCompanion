# Der Generationswechsel: 4.x → Companion-Forever 5.x

WeintCompanion 4.x ist das Ende einer Produktlinie. Die nächste
Generation entsteht als eigenständige Anwendung im Repository
`daddler/Companion-Forever` und beginnt bei **5.0.0** — sie ist kein
Update von 4.1.0, sondern ihre Nachfolgerin.

Diese Datei beschreibt die Brücke, die auf **dieser** Seite dafür
gebaut ist. Was das Zielrepository liefern muss, steht in
`../companion-forever-release-contract.md` und ist dort
massgeblich — hier wird es nicht wiederholt.

> **Der Zustand heute: abgeschaltet.**
> `MIGRATION_ENABLED_DEFAULT = False` in
> `core/migration/target.py`. Solange das so steht, stellt die App
> keine einzige Anfrage an `daddler/Companion-Forever`, zeigt nichts
> an und schreibt nichts in die Konfiguration. Sie verhält sich
> exakt wie vorher.

---

## Was ist zu tun, wenn Companion-Forever 5.0.0 fertig ist

1. Release `v5.0.0` in `daddler/Companion-Forever` veröffentlichen —
   Assets und Prüfsummen nach `../companion-forever-release-contract.md`.
2. Repository öffentlich schalten.
3. **Probelauf** auf beiden Plattformen (siehe unten). Das ist der
   Schritt, der sonst vergessen wird, und der einzige, der vor einem
   kaputten Release schützt.
4. In `core/migration/target.py`:
   `MIGRATION_ENABLED_DEFAULT = True`.
5. `core/version.py`, `packaging/installer.iss` und `CHANGELOG.md`
   auf die neue 4er-Fassung heben (Dreier-Regel, siehe
   `update-system.md`) — sie bleibt **4.x**, typischerweise die
   letzte: `4.9.x`.
6. Diesen 4er-Release veröffentlichen. Bestehende Nutzer bekommen
   ihn über den gewohnten Selbstupdate-Weg, und danach das Angebot.

Mehr ist es nicht. Insbesondere muss **nichts** an der Fachlogik
angefasst werden: das Ziel ("die nächste Generation nach der
eigenen") wird gerechnet, nicht eingetippt.

### Wenn etwas schiefgeht

Schritt 4 rückgängig machen und einen weiteren 4er-Release
veröffentlichen. Wer bereits gewechselt hat, ist davon nicht
betroffen — seine 4er-Installation liegt unverändert da, und
Companion-Forever ist eine eigene Anwendung.

---

## Aufbau

Alles liegt unter `core/migration/`, jede Datei beantwortet eine
Frage:

| Datei | Frage |
|---|---|
| `target.py` | wohin, welcher Kanal, **und darf ich überhaupt** |
| `releases.py` | was liegt dort (GitHub oder Datei) |
| `discovery.py` | ist davon etwas brauchbar |
| `assets.py` | welche Datei gehört zu diesem Rechner |
| `integrity.py` | ist es wirklich diese Datei |
| `payload.py` | was nimmt der Nutzer mit |
| `handover.py` | bereitstellen und starten |
| `state.py` | wo stehen wir gerade |
| `service.py` | der Ablauf, der die anderen acht benutzt |

Dazu, ausserhalb des Pakets:

- `core/process_spawn.py` — einen Prozess starten, der das Beenden
  dieser App überlebt. Stand bis 4.1 im Selbstupdater und wird jetzt
  von beiden benutzt (die systemd-Scope-Lehre gibt es nur einmal).
- `gui/controllers/migration_runner.py` — Thread und Signale,
  gebaut wie `update_runner.py`.
- `gui/dialogs/migration_dialog.py` — der Assistent in drei Bildern.

### Warum eine eigene Schicht neben dem bestehenden Updater

Der Selbstupdater (`core/companion_updater.py` + `github_updater.py`)
beantwortet "gibt es eine neuere Fassung von **mir**" und ersetzt
dafür die laufende Datei. Beides ist hier falsch:

- Er fragt `releases/latest`. Das liefert **eine** Veröffentlichung
  nach GitHubs Regeln — eine 5.0.0 neben einer 5.1.0-beta.2 kann
  darin fehlen, und eine 4.x im Zielrepository würde als "nächste
  Generation" durchgehen.
- Seine Asset-Auswahl endet mit "sonst nimm das erste Asset". Für
  ein Update aus dem eigenen Repository ist das vertretbar, für eine
  fremde Anwendung nicht.
- Er *überschreibt* die laufende Anwendung. Der Wechsel darf das
  gerade nicht.

Wiederverwendet werden dafür `core/downloader.py` (streamt und
hasht), `core/runtime.py` (Plattform, AppImage-Erkennung),
`core/paths.py` und `core/process_spawn.py`. Neu ist nur, was
wirklich anders ist.

---

## Die Regeln, die nicht verhandelbar sind

**Ausgeschaltet heisst ausgeschaltet.** `MigrationService.enabled()`
ist die erste Zeile jedes Einstiegspunkts. Ohne Freigabe: keine
Anfrage, kein Dialog, kein Eintrag.

**Die Zielgeneration wird gerechnet.** `next_major(VERSION)` — eine
4.x sucht 5, eine 5.x sucht 6. Daraus folgt kostenlos, dass ein
abgeschlossener Wechsel sich nicht wiederholen kann, und dass
derselbe Apparat später 5 → 6 trägt.

**Nur fertige Fassungen.** Kanal `stable` nimmt keine `-beta`,
`-rc`, `-alpha`, `-nightly`, `-dev`, `-preview`. Eingeordnet wird
nach dem **Tag**, nicht nach dem `prerelease`-Häkchen.

**Ohne Prüfsumme keine Installation.** Nicht "dann eben ohne".
`verifier_for(None)` ist kein Prüfer, der nichts prüft — er ist
einer, der abbricht.

**Mehrdeutig heisst: keine Auswahl.** Zwei gleich gut passende
Installationsdateien ergeben kein Angebot, nicht die erste davon.

**Erst V5 bereitstellen, dann V4 ablösen — und "ablösen" heisst nie
"löschen".** `handover.py` fasst die bestehende Installation an
keiner Stelle an. Nach einem Fehlschlag ist der Rechner in demselben
Zustand wie vorher, abzüglich einer Datei im Download-Ordner.

**Keine Zugangsdaten in der Übergabe.** Positivliste statt
Sperrliste, plus eine Prüfung auf verdächtige Schlüssel in den
Werten (`payload.py`). Die Discord-Verknüpfung wird in V5 neu
hergestellt.

**Die Prüfung geht ins Netz und gehört deshalb nicht in eine
Seite.** Sie hängt an `CompanionManager.full_refresh()` (Start) und
an `refresh_update_status()` ("Erneut prüfen"), also demselben
Hintergrundlauf wie die beiden Update-Kanäle. Anders als diese
reitet sie **nicht** auf der Viertelstundenwache
(`core/update_watch.py`) mit: ein Generationswechsel ist ein
einmaliges Ereignis, und eine Anfrage alle fünfzehn Minuten wäre
dafür Aufwand ohne Ertrag. Wer die App tagelang offen lässt, bekommt
das Angebot beim nächsten Start oder beim nächsten "Erneut prüfen";
`tests/test_migration_visibility.py` prüft strukturell, dass keine
Datei unter `gui/` sie selbst aufruft (siehe
`../architecture/navigation.md`).

---

## Der Zustand

```
NOT_AVAILABLE → AVAILABLE → CONFIRMED → DOWNLOADING → DOWNLOADED
              → VERIFYING → INSTALLING → INSTALLED → COMPLETED
                                   ↘ FAILED ↗ (zurück zu AVAILABLE)
```

Gespeichert unter `forever_migration_state` in der bestehenden
`config.json` (atomar geschrieben, siehe
`../development/paths-and-storage.md`). Nur vorgesehene Übergänge
werden übernommen; ein unmöglicher Schritt ändert nichts und wirft
auch nicht — der Zustand ist die Buchführung über den Ablauf, nicht
sein Steuerwerk.

**Nicht** gespeichert wird der Pfad der heruntergeladenen Datei: ein
alter Pfad aus einer Datei ist der bequemste Weg, beim nächsten Mal
die falsche Datei zu starten.

Zwei Merker verhindern, dass sich das Angebot aufdrängt:
`completed` (fassungsgenau — 5.0.0 erledigt schluckt 5.1.0 nicht)
und `postponed_version` ("Später" gilt für diese Fassung, die
nächste fragt erneut). Innerhalb einer Sitzung wird der Dialog
höchstens einmal geöffnet (`MainWindow._announce_forever_migration`).

---

## Einstellungen

Unter `forever_migration` in der `config.json` — getrennt vom
Zustand, weil eine Wahl und ein Fortschritt zwei Dinge sind:

```json
"forever_migration": {
    "enabled": false,
    "channel": "stable",
    "repository": "",
    "target_major": 0,
    "dry_run": false
}
```

Leer bzw. `0` heisst "Vorgabe verwenden":
`daddler/Companion-Forever`, die nächste Generation nach der
eigenen. Dieselbe Linie wie bei `characters_min_level` — eine Null
ist eine Frage, keine Antwort.

Zum Erproben gewinnen Umgebungsvariablen gegen die Konfiguration,
damit ein Test nichts hinterlässt:

| Variable | Wirkung |
|---|---|
| `WEINT_FOREVER_MIGRATION=1` | Migration freigeben |
| `WEINT_FOREVER_CHANNEL=beta` | Kanal umstellen |
| `WEINT_FOREVER_DRY_RUN=1` | Probelauf |
| `WEINT_FOREVER_RELEASES=<datei>` | Release-Liste aus einer Datei statt von GitHub |

---

## Probelauf

Der Probelauf geht den ganzen Weg — Release finden, Asset wählen,
herunterladen, Prüfsumme vergleichen, Datei an ihren Platz legen —
und hört genau vor dem letzten Schritt auf: es wird nichts
installiert und nichts gestartet. Er schreibt ausserdem **nichts**
in die Konfiguration, weder ein Angebot noch einen abgeschlossenen
Wechsel.

Gegen das echte Release:

```bash
WEINT_FOREVER_MIGRATION=1 WEINT_FOREVER_DRY_RUN=1 python app.py
```

Ohne Netz und ohne veröffentlichtes Release, gegen eine
weggespeicherte Antwort (dasselbe Format wie die GitHub-API):

```bash
curl -s https://api.github.com/repos/daddler/Companion-Forever/releases > /tmp/r.json

WEINT_FOREVER_MIGRATION=1 WEINT_FOREVER_DRY_RUN=1 \
WEINT_FOREVER_RELEASES=/tmp/r.json python app.py
```

Was der Nutzer sieht, steht danach im Protokoll (*Protokoll*-Seite
oder `companion.log`): Prüfung, Ziel, gefundene Fassung, gewähltes
Asset, Download, Prüfung, Übergabe — ohne Zugangsdaten.

---

## Was der Nutzer sieht

Der Assistent (`gui/dialogs/migration_dialog.py`) in drei Bildern:
Angebot, Verlauf, Abschluss. Durchgehend stehen **beide**
Anwendungen mit Namen und Fassung nebeneinander —

```
WeintCompanion 4.9.0   →   Companion-Forever 5.0.0
```

— und nie ein blosses "Update 5.0.0". Ein Generationswechsel, der
wie ein Patch aussieht, erzeugt beim ersten Start der neuen
Anwendung die Frage "warum heisst das jetzt anders".

Der Dialog lässt sich im ersten und im dritten Bild schliessen, im
zweiten nicht: mitten im Download ein Fenster zuzuklappen, während
im Hintergrund ein Thread läuft, ist der Zustand, den später niemand
mehr erklären kann.

---

## Tests

| Datei | Deckt ab |
|---|---|
| `tests/test_migration_versions.py` | 4.1→5.0, 4.9→5.0, 5.0→5.0, 5.1→5.2, Kanäle, **der Schalter steht auf aus** |
| `tests/test_migration_discovery.py` | kein Release, Stable, Pre-Release, mehrere, Netzfehler, ungültiges Release, 404 |
| `tests/test_migration_assets.py` | AppImage, EXE, fremde Architektur, fehlendes Asset, Mehrdeutigkeit |
| `tests/test_migration_state.py` | Übergänge, Speicherung, "schon gewechselt", "später" |
| `tests/test_migration_integrity.py` | richtiger, falscher und fehlender Hash, Prüfsummenformate |
| `tests/test_migration_handover.py` | Ablage, Ausführbit, stille Installer-Schalter, **die bestehende Fassung bleibt unberührt** |
| `tests/test_migration_service.py` | der ganze Ablauf, Fehlschläge, Probelauf, Protokoll |
| `tests/test_migration_payload.py` | Positivliste, **keine Zugangsdaten**, Schema |
| `tests/test_migration_visibility.py` | kein Netz in `gui/`, kein Dialog ohne Freigabe |

Was diese Tests **nicht** abdecken können und was der Probelauf
deshalb leisten muss: dass ein echter Windows-Installer die
erwarteten Schalter versteht, und dass eine echte AppImage nach dem
Kopieren startet. Beides hängt an einem Release, das es noch nicht
gibt.
