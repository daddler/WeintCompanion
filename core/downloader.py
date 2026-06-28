from pathlib import Path

import httpx


class Downloader:

    def __init__(self):

        self.download_dir = Path("cache/downloads")
        self.download_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

    # --------------------------------------------------

    def download(self, url: str, filename: str):

        destination = self.download_dir / filename

        with httpx.stream(
            "GET",
            url,
            follow_redirects=True,
            timeout=60,
        ) as response:

            response.raise_for_status()

            with open(destination, "wb") as file:

                for chunk in response.iter_bytes():

                    file.write(chunk)

        return destination