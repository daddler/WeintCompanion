from pathlib import Path

import httpx


class Downloader:

    # --------------------------------------------------

    def download(
        self,
        url: str,
        destination: Path,
    ):

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

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