import hashlib
from pathlib import Path

import httpx


class ChecksumError(Exception):
    pass


class Downloader:

    # --------------------------------------------------

    def download(
        self,
        url: str,
        destination: Path,
        expected_sha256: str | None = None,
    ):
        """
        Lädt "url" nach "destination". Ist "expected_sha256" gesetzt,
        wird die Datei während des Streamens gehasht und der Digest
        danach mit dem erwarteten Wert verglichen - bei Abweichung
        wird die (potenziell manipulierte oder beschädigte) Datei
        gelöscht und ChecksumError geworfen, statt sie an den
        Aufrufer zurückzugeben.
        """

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        hasher = hashlib.sha256()

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
                    hasher.update(chunk)

        if expected_sha256:

            actual = hasher.hexdigest().lower()
            expected = expected_sha256.strip().lower()

            if actual != expected:

                destination.unlink(missing_ok=True)

                raise ChecksumError(
                    f"Prüfsumme stimmt nicht überein für {destination.name} "
                    f"(erwartet {expected}, erhalten {actual})."
                )

        return destination