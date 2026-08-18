import requests

from core.backend_config import BOT_BASE_URL


class SyncClient:

    def __init__(self):

        #
        # Über BOT_BASE_URL statt fest verdrahtet: die Adresse des
        # Bots ändert sich bei einem Serverumzug, und sie stand hier
        # als zweite Kopie neben der zentralen - genau der Fall, vor
        # dem der Kommentar in core/backend_config.py warnt. Beim
        # Umzug auf weintcodex-bot.e.jrnm.app blieben diese beiden
        # Stellen prompt auf der alten Adresse stehen.
        #

        self.url = f"{BOT_BASE_URL}/sync"

    # --------------------------------------------------

    def send(self, message):

        try:

            response = requests.post(

                self.url,

                json=message,

                #
                # Der Bot wartet serverseitig bis zu 15s auf die
                # Discord-Bestätigung (Kanal/Nachricht holen + editieren).
                # Ein knapperes Client-Timeout hier würde sonst genau in
                # diesem - eigentlich noch erfolgreichen - Fall vorzeitig
                # abbrechen.
                #

                timeout=25,

            )

            #
            # WICHTIG: Nicht nur den HTTP-Status prüfen. Der Bot
            # antwortet bei "veraltet"/"nicht konfiguriert" ebenfalls
            # mit 200 und einem abweichenden "status"-Feld - wurde das
            # hier ignoriert, hat Companion die Nachricht aus der
            # Warteschlange des Addons gelöscht, OBWOHL das Discord-
            # Embed nie aktualisiert wurde (der eigentliche Bug hinter
            # den unvollständigen Gildenbank-Syncs).
            #

            if response.status_code != 200:
                return False

            try:

                body = response.json()

            except ValueError:

                return False

            return body.get("status") == "ok"

        except Exception as e:

            print(f"Sync-Fehler: {e}")

            return False