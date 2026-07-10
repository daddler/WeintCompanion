from __future__ import annotations

from pathlib import Path
import re

from core.lua_table import upsert_variable


class SyncReader:

    def __init__(self, wow_path: Path):

        self.wow_path = wow_path

    # --------------------------------------------------
    # SavedVariables finden
    # --------------------------------------------------

    def get_file(self):

        if self.wow_path is None:
            return None

        account_root = (
            self.wow_path
            / "WTF"
            / "Account"
        )

        if not account_root.exists():
            return None

        for account in sorted(account_root.iterdir()):

            if not account.is_dir():
                continue

            file = (
                account
                / "SavedVariables"
                / "WeintCodex.lua"
            )

            if file.is_file():
                return file

        return None

    # --------------------------------------------------

    def exists(self):

        return self.get_file() is not None

    # --------------------------------------------------

    def read(self):

        file = self.get_file()

        if file is None:
            return ""

        return file.read_text(
            encoding="utf-8",
            errors="ignore",
        )

    # --------------------------------------------------
    # Nachrichten lesen
    # --------------------------------------------------

    def get_messages(self):

        text = self.read()

        if not text:
            return []

        messages = []

        current = None

        in_queue = False

        for raw in text.splitlines():

            line = raw.strip()

            #
            # Queue gefunden
            #

            if line.startswith('["queue"]'):
                in_queue = True
                continue

            if not in_queue:
                continue

            #
            # Neue Nachricht
            #

            if line == "{":

                if current is None:
                    current = {}

                continue

            #
            # Nachricht beendet
            #

            if line == "},":

                if current:

                    if "type" in current and "payload" in current:
                        messages.append(current)

                current = None
                continue

            if current is None:
                continue

            #
            # id
            #

            if line.startswith('["id"]'):

                current["id"] = int(
                    line.split("=")[1]
                    .strip()
                    .rstrip(",")
                )

                continue

            #
            # created
            #

            if line.startswith('["created"]'):

                current["created"] = int(
                    line.split("=")[1]
                    .strip()
                    .rstrip(",")
                )

                continue

            #
            # version
            #

            if line.startswith('["version"]'):

                current["version"] = int(
                    line.split("=")[1]
                    .strip()
                    .rstrip(",")
                )

                continue

            #
            # type
            #

            if line.startswith('["type"]'):

                current["type"] = (
                    line.split("=",1)[1]
                    .strip()
                    .rstrip(",")
                    .strip('"')
                )

                continue

            #
            # payload
            #

            if line.startswith('["payload"]'):

                payload = (
                    line.split("=",1)[1]
                    .strip()
                    .rstrip(",")
                )

                if payload.startswith('"'):
                    payload = payload[1:]

                if payload.endswith('"'):
                    payload = payload[:-1]

                payload = payload.replace('\\"','"')

                current["payload"] = payload

        return messages

    # --------------------------------------------------

    def queue_size(self):

        return len(self.get_messages())

    # --------------------------------------------------
    # Nachricht entfernen
    # --------------------------------------------------

    def remove_message(self, message_id):

        file = self.get_file()

        if file is None:
            return False

        messages = self.get_messages()

        #
        # Nachricht entfernen
        #

        messages = [
            message
            for message in messages
            if message["id"] != message_id
        ]

        #
        # lastId aus der bestehenden Datei übernehmen
        #

        last_id = 0

        for line in self.read().splitlines():

            line = line.strip()

            if line.startswith('["lastId"]'):

                last_id = int(
                    line.split("=")[1]
                    .strip()
                    .rstrip(",")
                )

                break

        #
        # Nur den WeintCompanionDB-Block ersetzen - siehe
        # core/lua_table.py: die Datei enthält daneben auch
        # WeintCodex_SavedData, das hier unangetastet bleiben muss.
        #

        lines = []

        lines.append('["version"] = 1,')
        lines.append(f'["lastId"] = {last_id},')
        lines.append('["queue"] = {')

        for message in messages:

            payload = (
                message["payload"]
                .replace("\\", "\\\\")
                .replace('"', '\\"')
            )

            lines.extend([

                "{",

                f'["created"] = {message["created"]},',
                f'["type"] = "{message["type"]}",',
                f'["version"] = {message["version"]},',
                f'["payload"] = "{payload}",',
                f'["id"] = {message["id"]},',

                "},",

            ])

        lines.append("},")

        upsert_variable(
            file,
            "WeintCompanionDB",
            "\n".join(lines) + "\n",
        )

        return True