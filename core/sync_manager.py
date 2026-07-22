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

            if message.get("type") == "character":

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