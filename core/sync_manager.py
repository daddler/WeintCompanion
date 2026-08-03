from addon.sync_reader import SyncReader
from discord.sync_client import SyncClient
from core.character_sync_client import CharacterSyncClient


class SyncManager:

    def __init__(self, manager):

        self.manager = manager

        self.reader = SyncReader(
            manager.state.wow_path
        )

        self.client = SyncClient()
        self.character_client = CharacterSyncClient()

    # --------------------------------------------------

    def process(self):

        #
        # Aktuellen WoW-Pfad übernehmen
        #

        self.reader.wow_path = (
            self.manager.state.wow_path
        )

        #
        # SavedVariables vorhanden?
        #

        if not self.reader.exists():

            return

        #
        # Nachrichten lesen
        #

        messages = self.reader.get_messages()
        print(messages)

        if not messages:

            return

        self.manager.logger.info(
            f"{len(messages)} Nachricht(en) werden verarbeitet."
        )

        #
        # Alle Nachrichten senden
        #

        for message in messages:

            #
            # Charakter-Meldungen (Companion-Discord-Login -> Bot) laufen
            # über einen eigenen, tokenbasierten Client statt über den
            # anonymen Material-SyncClient. Ist kein Discord-Account
            # verknüpft, wird die Nachricht ohne Fehlermeldung verworfen -
            # das ist der normale Zustand für jeden nicht verknüpften
            # Spieler, kein Fehler.
            #

            #
            # Academy-Fortschritt kommt aus dem Addon zurueck (ingame
            # gesetzte Haken und abgewaehlte Lektionen) und bleibt hier
            # auf dem Rechner - der Bot hat damit nichts zu tun. Die
            # Nachricht wird deshalb lokal verarbeitet und danach
            # entfernt, ohne SyncClient.
            #

            if message.get("type") == "academy":

                self._apply_academy_progress(
                    message.get("payload") or ""
                )

                self.reader.remove_message(
                    message["id"]
                )

                continue

            if message.get("type") == "character":

                #
                # Bridge-Karte "Charakter-Roster": meldet die in der
                # Twinkverwaltung ausgewählten Charaktere an den Bot
                # (Grundlage für den Klassen-Abgleich beim Kalender-Invite,
                # siehe services/companion_characters.py im Bot). Ist die
                # Bridge ausgeschaltet, wird die Nachricht nur verworfen -
                # das Addon erfasst sie unabhängig davon immer.
                #

                if not self.manager.config.data.get(
                    "character_roster_sync_enabled",
                    True,
                ):

                    self.reader.remove_message(
                        message["id"]
                    )
                    continue

                if not self.character_client.is_linked():

                    self.reader.remove_message(
                        message["id"]
                    )
                    continue

                success = self.character_client.send(
                    message["payload"]
                )

            #
            # Loot-Meldungen sind ein neues, standardmäßig deaktiviertes
            # Feature (Bridge-Karte "Loot-Verteilung"). Das Addon erfasst
            # sie unabhängig davon immer - ist die Bridge hier ausgeschaltet,
            # wird die Nachricht nur verworfen statt an den Bot gesendet.
            #

            elif message.get("type") == "loot" and not self.manager.config.data.get(
                "loot_sync_enabled",
                False,
            ):

                self.reader.remove_message(
                    message["id"]
                )
                continue

            else:

                success = self.client.send(
                    message
                )

            if success:

                self.reader.remove_message(
                    message["id"]
                )
                print(self.reader.read())

                self.manager.logger.success(
                    f"Nachricht #{message['id']} verarbeitet."
                )

            else:

                self.manager.logger.error(
                    f"Nachricht #{message['id']} konnte nicht gesendet werden."
                )
    # --------------------------------------------------
    # Academy-Fortschritt aus dem Addon
    # --------------------------------------------------

    def _apply_academy_progress(self, payload: str):
        """
        Format (siehe SendAcademyProgress in modules/companion.lua):

            <Charakter>|<erledigt,...>|<abgewaehlt,...>;<Charakter2>|...

        Lektions-IDs sind ASCII-Bezeichner ohne Komma, Pipe oder
        Semikolon - das Format ist damit eindeutig.

        Die Listen des Addons ERSETZEN die hiesigen. Das Addon hat
        beim Login den Desktop-Stand erhalten und seitdem nur
        ergaenzt; es ist fuer diesen Charakter also die juengere
        Quelle. Ein Zusammenfuehren statt Ersetzen wuerde bedeuten,
        dass ingame abgehakte Lektionen nie wieder geoeffnet werden
        koennten.
        """

        academy = getattr(self.manager, "academy", None)

        if academy is None or not payload:
            return

        changed = False

        for block in payload.split(";"):

            parts = block.split("|")

            if len(parts) != 3:
                continue

            name = parts[0].strip()

            if not name:
                continue

            completed = [
                entry
                for entry in parts[1].split(",")
                if entry
            ]

            excluded = [
                entry
                for entry in parts[2].split(",")
                if entry
            ]

            if academy.data["completed"].get(name) != completed:

                academy.data["completed"][name] = completed
                changed = True

            if academy.data["excluded"].get(name) != excluded:

                academy.data["excluded"][name] = excluded
                changed = True

        if not changed:
            return

        academy.save()

        self.manager.logger.info(
            "Academy: Fortschritt aus dem Addon uebernommen."
        )
