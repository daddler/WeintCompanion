import requests


class DiscordStatus:

    def __init__(self):

        self.url = "https://weintcodex-a1d.b.jrnm.app/status"

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