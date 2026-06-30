import requests


class SyncClient:

    def __init__(self):

        self.url = "http://127.0.0.1:8765/sync"

    # --------------------------------------------------

    def send(self, message):

        try:

            response = requests.post(

                self.url,

                json=message,

                timeout=5,

            )

            return response.status_code == 200

        except Exception as e:

            print(f"Sync-Fehler: {e}")

            return False