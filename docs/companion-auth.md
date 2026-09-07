# Companion-Authentifizierung: Vertrag zwischen Bot und Companion

Diese Datei beschreibt, wie ein Discord-Konto mit Companion verknüpft wird
und warum diese Verknüpfung einen Bot-Neustart überlebt. Bot-Seite:
`services/companion_token.py`, `services/companion_auth.py`. Companion-Seite:
`core/discord_auth.py`, `core/discord_account.py`.

## Login-Fluss

`/companion/auth/exchange` tauscht einen Discord-OAuth2-Code (den Companion
über den Systembrowser besorgt, lokaler Callback-Server) gegen ein
Bot-ausgestelltes, undurchsichtiges Pairing-Token — der echte Discord-Zugriffs-
Token verlässt den Bot nie. `DiscordAuth.login()` (Companion) führt den
OAuth2-Ablauf; `DiscordAuth.parse_exchange_response()` ist **rein** (kein
Netzwerk) und weist eine Antwort ohne Token zurück, ebenso wie
`DiscordAccountStore.save()` ohne Token eine `DiscordAccountError` wirft —
beide Login-Aufrufstellen behandeln einen fehlgeschlagenen `save()` als
fehlgeschlagenen Login (früher stand `save()` ungeschützt im Erfolgszweig,
eine Exception flog aus einem Qt-Slot und die Seite blieb bei „Browser
öffnet sich …" stehen).

**Ein Login, der keinen Browser öffnen kann, muss sofort scheitern.**
`open_url()`s Rückgabewert wird geprüft; ohne registrierten Browser wirft
`login()` sofort mit der Adresse, die man von Hand öffnen könnte, statt erst
nach 120 s mit „Zeitüberschreitung" zu antworten. Ein belegter Port 53682
(ein vorheriger Versuch hält ihn noch) wird als deutscher Satz übersetzt
statt als `Address already in use`.

## Das Pairing-Token muss den Deploy überleben

Der meistgemeldete Companion-Fehler war „ich muss Discord immer wieder neu
verbinden". Kein Companion-Bug: das Token war nur ein Schlüssel in
`companion_links`, und `data/raid.db` ist nach jedem Neustart leer (der Host
hat kein persistentes Volume). Jeder Deploy entwertete damit jede
Verknüpfung gleichzeitig — für die App nicht von einem echten Widerruf zu
unterscheiden: Companion löscht sein gespeichertes Konto bei einem 401
(`core/character_sync_client.py`).

**Nicht gelöst über eine vierte Discord-Snapshot-Kopie** — ein Token ist
ein Credential und gehört nicht als Anhang in einen Kanal, den jeder
künftige Leser erbt. `services/companion_token.py` lässt das Token stattdessen
seine eigene Identität tragen, mit einem HMAC-Schlüssel signiert — Prüfung
braucht keinen Lookup, keine Zeile, keine Host-Abhängigkeit.

Vier Regeln:

- **Der Schlüssel kommt aus der Umgebung, `DISCORD_CLIENT_SECRET` ist der
  Rückfall.** Das ist der eine Wert, der für den Login ohnehin gesetzt sein
  muss und über Deploys stabil ist — die Behebung wirkt ohne neue
  Konfiguration. `COMPANION_TOKEN_SECRET` überschreibt ihn; beide werden pro
  Aufruf gelesen, nie beim Import eingefroren.
- **„Ungültig" und „ich kann nicht prüfen" sind verschiedene Antworten.**
  Ohne jeden Schlüssel bekommt ein signiertes Token `TokenKeyMissing` →
  `CompanionAuthError` → **HTTP 503**, nie ein 401. Ein 401 würde jede
  Companion eine gute Verknüpfung wegen einer fehlenden Umgebungsvariable
  löschen lassen — derselbe Fehler in anderer Verkleidung.
  `_require_companion_link()` ist die einzige Stelle in `sync_server.py`, die
  ein Token auflöst.
- **Widerruf ist ehrlich über das, was er kann.** Ohne persistenten Speicher
  lässt sich ein einzelnes Token nicht über einen Neustart hinaus
  widerrufen; `revoke()` hält Fingerabdrücke nur im Prozessspeicher, der
  dauerhafte Weg für „alles entwerten" ist ein neuer
  `COMPANION_TOKEN_SECRET`. Das Token liegt auf der Maschine des Nutzers,
  und „Trennen" löscht es genau dort.
- **Eine zweite Maschine loggt die erste nicht mehr aus.** Signierte Tokens
  sind unabhängig voneinander (vorher: eine Zeile pro Discord-Konto, ein
  zweites Gerät entwertete das erste lautlos).

`companion_links` wird weiterhin geschrieben, ist aber kein Credential-Store
mehr — nur noch das Verzeichnis „wer hat wann verknüpft" plus Rückfallpfad
für einen Bot ohne Signaturschlüssel (dann wie vorher: Verlust bei jedem
Neustart, einmal geloggt).

## Eine einzelne 401 darf nicht entlinken (Companion-seitige Regel)

Ein 401 ist kein Beweis — er kann ein neu startender Bot sein, ein Proxy
dazwischen oder ein als „Token ungültig" verkleideter Serverfehler.
`DiscordAccountStore.note_auth_rejected()` (Companion) ist die eine Stelle,
die entscheidet, und entlinkt erst nach `AUTH_REJECTIONS_BEFORE_UNLINK`
Ablehnungen innerhalb von `AUTH_REJECTION_WINDOW`. Der Zähler lebt **auf der
Klasse**, weil mehrere Clients dieselbe Frage stellen und die Schwelle sonst
fünfmal einzeln erreicht werden müsste; `clear()` setzt ihn zurück, sonst
erbt eine frisch neu verlinkte Verknüpfung die alten Ablehnungen.

**Eine Retry-Schleife ist ein Vorfall, nicht drei.** Eine fehlgeschlagene
Nachricht bleibt in der Warteschlange des Addons und wird beim nächsten
Sync-Takt erneut versucht — ein abgelehntes Token erzeugte so drei
Ablehnungen in drei Zyklen in 15 Sekunden. `AUTH_REJECTION_COOLDOWN` (60 s)
zählt eine Ablehnung innerhalb des Cooldowns als denselben Vorfall; drei
gezählte Ablehnungen brauchen damit mindestens zwei Minuten — ein neu
startender Bot ist dann längst zurück, ein wirklich totes Token wird in
zwei Minuten statt fünfzehn Sekunden erkannt.

**Und das Entlinken sagt es.** `discord_account.set_logger()` wird einmal in
`CompanionManager.__init__` verdrahtet — die Nachricht gehört zur
Funktion, die entscheidet, nicht zu ihren fünf Aufrufstellen.

## Atomares Schreiben

`open(..., "w")` leert die Datei vor dem Schreiben; ein Absturz dazwischen
hinterlässt eine leere Datei, die `load()` nicht von „nie verknüpft"
unterscheiden konnte. `_write_atomic()` schreibt eine Nebendatei, `fsync`t
sie, ersetzt dann atomar (`os.replace()`) und fsynct das Verzeichnis;
`save()` hält zusätzlich `discord_account.json.bak`, `load()` fällt darauf
zurück, wenn die Hauptdatei fehlt oder unlesbar ist. `clear()` entfernt
beide.

**„Ist verknüpft?" hat genau eine Antwort: `is_usable()`.** Ein Eintrag ohne
`companion_token` erfüllte früher „es gibt einen Eintrag", aber keiner der
sieben Clients konnte damit etwas anfangen — die UI zeigte „Verbunden als …"
und kein einziger Abruf lief. `is_usable()` prüft das Token, nicht nur die
Existenz eines Eintrags.
