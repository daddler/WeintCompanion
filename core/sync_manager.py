from addon.sync_reader import SyncReader
from discord.sync_client import SyncClient
from core.character_sync_client import CharacterSyncClient
from core.academy_progress_sync import apply_addon_progress
from core.academy_dummy_sync import apply_dummy_practice_session
from core.character_report_sync import apply_character_report


#
# Nachrichtenarten, die auf diesem Rechner bleiben. Der Bot hat mit
# ihnen nichts zu tun: eigener Lernfortschritt, eigene Übungsdaten,
# der eigene angemeldete Charakter. Die drei Zweige unten sind
# dieselbe Form dreimal; die Menge ist die Naht, an der die nächste
# lokale Art dazukommt.
#
LOCAL_MESSAGE_TYPES = {
    "academy",
    "dummy_practice_session",
    "character_report",
    "character_sheet",
    "weakaura_catalog",
}


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

            #
            # Rotationstrainer-Sitzung am Trainingsdummy (siehe
            # modules/rotationtrainer.lua im Addon). Genau wie
            # "academy" persönliche Übungsdaten, die hier auf dem
            # Rechner bleiben und den Bot nichts angehen - deshalb
            # ebenfalls lokal verarbeitet statt über den SyncClient.
            #

            if message.get("type") == "dummy_practice_session":

                apply_dummy_practice_session(
                    getattr(self.manager, "academy", None),
                    message.get("payload") or "",
                )

                self.reader.remove_message(
                    message["id"]
                )

                continue

            #
            # Wer ist ingame angemeldet? Seit WeintCodex 1.3.3.0.
            # Bleibt lokal - er beantwortet ausschliesslich die Frage,
            # fuer welchen Charakter Academy und WeintTV gelten, und
            # die wurde vorher geraten (siehe
            # core/character_report_sync.py).
            #

            if message.get("type") == "character_report":

                report = apply_character_report(
                    getattr(self.manager, "academy", None),
                    message.get("payload") or "",
                )

                if report is not None:

                    self.manager.logger.info(
                        "Ingame angemeldet: "
                        f"{report['name']}"
                        + (f"-{report['realm']}" if report["realm"] else "")
                    )

                self.reader.remove_message(
                    message["id"]
                )

                continue

            #
            # Der Ausrüstungsstand des angemeldeten Charakters, seit
            # WeintCodex 1.3.3.1. Bleibt aus demselben Grund lokal wie
            # die Meldung darüber: es ist die eigene Ausrüstung, kein
            # Gildenwissen - und die Seiten "Meine Charaktere" und
            # "Vorbereitung" sind die einzigen Leser.
            #

            if message.get("type") == "character_sheet":

                store = getattr(self.manager, "characters", None)

                sheet = store.apply(message.get("payload") or "") if store else None

                if sheet is not None:

                    self.manager.logger.info(
                        "Ausrüstung übernommen: "
                        f"{sheet['name']}"
                        + (f"-{sheet['realm']}" if sheet["realm"] else "")
                        + (f" ({sheet['spec']})" if sheet["spec"] else "")
                    )

                self.reader.remove_message(
                    message["id"]
                )

                continue

            #
            # Welche WeakAuras kennt das Addon? Seit WeintCodex
            # 2.1.0.0. Bleibt lokal: es ist eine Auskunft ueber die
            # eigene Installation, kein Gildenwissen - und die Seite
            # "WeakAuras" ist die einzige Leserin. Ohne sie koennte
            # sie nur die Auren auflisten, die sie selbst angelegt
            # hat, und "eine vorhandene aktualisieren" waere genau
            # darauf beschraenkt.
            #

            if message.get("type") == "weakaura_catalog":

                store = getattr(self.manager, "weakauras", None)

                changed = (
                    store.apply_catalog(message.get("payload") or "")
                    if store else False
                )

                #
                # Nur bei einer Aenderung protokollieren. Der Katalog
                # ist ueber eine Spielsitzung hinweg konstant; eine
                # Zeile bei jeder Anmeldung waere Rauschen.
                #

                if changed:

                    self.manager.logger.info(
                        f"WeakAuras im Addon: "
                        f"{len(store.catalog())} bekannt."
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

            elif message.get("type") in LOCAL_MESSAGE_TYPES:

                #
                # Sollte oben schon behandelt worden sein. Kommt eine
                # lokale Art trotzdem hier an (neuer Typ eingeführt,
                # Zweig vergessen), darf sie NICHT an den Bot gehen -
                # sie ist persönlich und der Bot antwortet ohnehin
                # nicht mit Erfolg, sodass sie liegen bliebe und im
                # Sync-Takt Fehler erzeugte.
                #

                self.manager.logger.warning(
                    f"Lokale Nachricht \"{message.get('type')}\" ohne "
                    "Verarbeitung - verworfen."
                )

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
        Der ingame gesetzte Stand ersetzt den hiesigen - Format und
        Begruendung siehe core/academy_progress_sync.py.
        """

        academy = getattr(self.manager, "academy", None)

        if apply_addon_progress(academy, payload):

            self.manager.logger.info(
                "Academy: Fortschritt aus dem Addon uebernommen."
            )
