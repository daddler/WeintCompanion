"""
Die Zustellung, die ein /reload überlebt.

Der übliche Weg Richtung Addon ist die SavedVariable
WeintCompanionInboxDB (addon/inbox_writer.py). Der hat einen
Konstruktionsfehler, der erst im laufenden Spiel auffällt: WoW hält
seine SavedVariables im Arbeitsspeicher, schreibt sie bei /reload und
beim Abmelden aus dem Speicher zurück und liest sie erst DANACH
wieder ein. Alles, was wir in der Zwischenzeit in die Datei
geschrieben haben, wird von diesem Rückschreiben vernichtet - und
zwar bevor das Addon es je zu sehen bekommt.

Damit konnte "Anmeldungen abrufen" im Addon nie funktionieren: der
Knopf löst ein /reload aus, das /reload überschreibt unsere
Zustellung mit dem Stand vom Login, und übrig bleibt genau das, was
schon vorher da war. DiscordRosterSync merkt sich zudem, was zuletzt
zugestellt wurde, und schickt einen unveränderten Roster kein zweites
Mal - die Daten waren danach also nicht nur nicht angekommen,
sondern weg.

Eine Lua-Datei IM ADDON-ORDNER hat dieses Problem nicht: WoW führt
Addon-Dateien bei jedem /reload neu aus und schreibt sie niemals
zurück. Sie ist deshalb die einzige Richtung Companion -> Addon, die
während einer laufenden Sitzung überhaupt ankommen kann.

Drei Dinge daran sind nicht Geschmack:

* **Geschrieben wird die ganze Zustellung, nicht ein Zuwachs.** Das
  Addon kann die Datei nicht leeren (es schreibt keine Dateien), also
  ist ihr Inhalt immer der vollständige aktuelle Stand. Es merkt sich
  `writtenAt` und arbeitet eine unveränderte Zustellung nicht erneut
  ein.

* **Erst schreiben, dann umbenennen.** Ein /reload kann genau in
  unseren Schreibvorgang fallen; eine halb geschriebene Lua-Datei
  wäre ein Syntaxfehler im Addon-Ordner. `os.replace` ist auf beiden
  Plattformen atomar.

* **Verglichen wird gegen die Datei, nicht gegen ein Gedächtnis.**
  Ein Addon-Update entpackt den leeren Auslieferungsstand über unsere
  Zustellung. Ein reiner Speicher-Vergleich hielte sie danach für
  vorhanden und schriebe sie nie wieder - die Zustellung wäre bis zur
  nächsten inhaltlichen Änderung verschwunden.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from addon.inbox_writer import render_entries
from addon.reader import AddonReader
from core.lua_table import quote_lua_string
from core.version import VERSION

#
# Muss zu dem Dateinamen passen, den WeintCodex.toc lädt. Steht dort
# als "data/companion_live.lua".
#

BRIDGE_NAME = "companion_live.lua"
BRIDGE_DIR = "data"

HEADER = (
    "-- WeintCodex :: Companion-Zustellung (Live-Brücke)\n"
    "-- Von WeintCompanion geschrieben. Änderungen von Hand werden\n"
    "-- beim nächsten Abgleich überschrieben.\n"
    "--\n"
    "-- Warum diese Datei existiert: siehe addon/live_bridge.py der\n"
    "-- Companion und den Kopf dieser Datei im Addon-Auslieferungs-\n"
    "-- stand.\n"
)


class LiveBridgeWriter:

    def __init__(self, wow_path):

        self.wow_path = wow_path

    # --------------------------------------------------

    def path(self) -> Path | None:
        """
        Der Ablageort der Brückendatei, oder None, wenn das Addon
        nicht installiert ist. Kein Fehler - dann gibt es schlicht
        nichts zuzustellen.
        """

        if self.wow_path is None:
            return None

        reader = AddonReader(self.wow_path)

        if not reader.exists():
            return None

        return reader.addon_path / BRIDGE_DIR / BRIDGE_NAME

    # --------------------------------------------------

    def render(self, messages: list[dict], written_at: int) -> str:

        return (
            HEADER
            + "\nWeintCodex_CompanionLive = {\n"
            + f'["writtenAt"] = {written_at},\n'
            + f'["companionVersion"] = {quote_lua_string(VERSION)},\n'
            + '["queue"] = {\n'
            + render_entries(messages)
            + "},\n"
            + "}\n"
        )

    # --------------------------------------------------

    def write(self, messages: list[dict]) -> bool:
        """
        Schreibt die Zustellung, wenn sich ihr Inhalt gegenüber der
        Datei geändert hat. Gibt True zurück, wenn danach der aktuelle
        Stand dort liegt - auch dann, wenn nichts zu tun war.
        """

        target = self.path()

        if target is None:
            return False

        #
        # `writtenAt` ist der Stand, an dem das Addon erkennt, ob es
        # etwas Neues gibt. Es darf deshalb nur mitwandern, wenn sich
        # die Nachrichten wirklich geändert haben - sonst arbeitete
        # das Addon bei jedem /reload dieselbe Zustellung erneut ein
        # und meldete jeden Import ein weiteres Mal im Chat. Verglichen
        # wird darum der Teil OHNE Zeitstempel.
        #

        body = (
            f'["companionVersion"] = {quote_lua_string(VERSION)},\n'
            '["queue"] = {\n'
            + render_entries(messages)
            + "},\n"
        )

        try:
            current = target.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            current = ""

        if body in current:
            return True

        content = self.render(messages, int(time.time()))

        temporary = target.with_suffix(".lua.tmp")

        try:

            target.parent.mkdir(parents=True, exist_ok=True)

            temporary.write_text(content, encoding="utf-8")

            os.replace(temporary, target)

        except OSError:

            try:
                temporary.unlink()
            except OSError:
                pass

            return False

        return True
