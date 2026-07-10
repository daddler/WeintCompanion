import requests


class SyncClient:

    def __init__(self):

        self.url = "https://weintcodex-a1d.b.jrnm.app/sync"

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