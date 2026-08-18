import requests

from core.backend_config import BOT_BASE_URL


class DiscordStatus:

    def __init__(self):

        #
        # Über BOT_BASE_URL statt fest verdrahtet: die Adresse des
        # Bots ändert sich bei einem Serverumzug, und sie stand hier
        # als zweite Kopie neben der zentralen - genau der Fall, vor
        # dem der Kommentar in core/backend_config.py warnt. Beim
        # Umzug auf weintcodex-bot.e.jrnm.app blieben diese beiden
        # Stellen prompt auf der alten Adresse stehen.
        #

        self.url = f"{BOT_BASE_URL}/status"

    # --------------------------------------------------

    def fetch(self):

        try:

            response = requests.get(
                self.url,
                timeout=3,
            )

            if response.status_code != 200:
                return None

            return response.json()

        except Exception:

            return None