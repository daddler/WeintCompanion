"""
Ist das wirklich die Datei, die es sein soll?

Der Generationswechsel laedt eine ausfuehrbare Datei herunter und
startet sie. Das ist der gefaehrlichste Vorgang, den diese App
kennt - gefaehrlicher als das Selbstupdate, denn dort ist wenigstens
das Repository dasselbe. Deshalb gilt dieselbe Regel wie beim
Companion-Update, nur schaerfer formuliert:

**OHNE PRUEFSUMME KEINE INSTALLATION.**

Nicht "dann eben ohne" und nicht "mit Warnung trotzdem". Ein Release
ohne `<asset>.sha256` ist entweder aelter als der Release-Vertrag
(dann gehoert es nicht in eine Migration) oder veraendert worden
(dann erst recht nicht). Der Vertrag steht in
`docs/companion-forever-release-contract.md`.

WARUM EINE PRUEFERSCHNITTSTELLE UND NICHT NUR EIN HASH
------------------------------------------------------

SHA-256 beweist, dass die Datei unterwegs nicht kaputtgegangen ist,
und mehr nicht: wer die Pruefsummendatei aendern kann, kann auch die
Binaerdatei aendern. Der naechste Schritt ist eine Signatur - dann
beweist die Pruefung, **wer** die Datei gebaut hat. Damit das keine
Umbauaktion wird, laeuft die Pruefung schon heute ueber `Verifier`
mit einer Methode: ein `SignatureVerifier` tritt spaeter neben den
`Sha256Verifier`, der Rest der Migration merkt davon nichts.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import re


CHUNK = 1024 * 1024

_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class IntegrityError(Exception):
    """
    Die Datei ist nicht die erwartete - oder es laesst sich nicht
    feststellen. Beides bricht den Wechsel ab.
    """

    def __init__(self, code: str, message: str):

        super().__init__(message)

        self.code = code
        self.message = message


def sha256_of_file(path) -> str:

    hasher = hashlib.sha256()

    with open(path, "rb") as file:

        for chunk in iter(lambda: file.read(CHUNK), b""):
            hasher.update(chunk)

    return hasher.hexdigest().lower()


def parse_checksum(text: str, asset_name: str = "") -> str | None:
    """
    Liest den Digest aus dem Inhalt einer `.sha256`-Datei.

    Drei Schreibweisen kommen in freier Wildbahn vor, alle drei
    werden verstanden:

        <hash>
        <hash>  dateiname
        <hash> *dateiname          (Binaermodus von sha256sum)

    Enthaelt die Datei mehrere Zeilen (eine Pruefsummendatei fuer
    ein ganzes Release), entscheidet der Dateiname - und wenn er
    nicht vorkommt, ist die Antwort `None` statt der ersten besten
    Zeile.
    """

    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]

    if not lines:
        return None

    wanted = (asset_name or "").strip().lower()

    for line in lines:

        parts = line.split()

        digest = parts[0].lower()

        if not _HEX64.match(digest):
            continue

        if len(parts) == 1:

            #
            # Nur ein Digest: gilt fuer die Datei, zu der diese
            # Pruefsummendatei gehoert - aber nur, wenn es die
            # einzige Zeile ist. Alles andere waere geraten.
            #

            if len(lines) == 1:
                return digest

            continue

        name = " ".join(parts[1:]).lstrip("*").strip().lower()

        if not wanted or Path(name).name == Path(wanted).name:
            return digest

    return None


class Verifier:
    """
    Der Vertrag: pruefe diese Datei, wirf bei Zweifel.
    """

    name = "verifier"

    def verify(self, path: Path) -> None:
        raise NotImplementedError


@dataclass
class Sha256Verifier(Verifier):

    expected: str
    name: str = "sha256"

    def verify(self, path: Path) -> None:

        expected = (self.expected or "").strip().lower()

        if not _HEX64.match(expected):

            raise IntegrityError(
                "MISSING_CHECKSUM",
                "Zu dieser Datei gibt es keine gueltige Pruefsumme - "
                "der Wechsel wird aus Sicherheitsgruenden abgebrochen.",
            )

        actual = sha256_of_file(path)

        if actual != expected:

            raise IntegrityError(
                "CHECKSUM_MISMATCH",
                f"Pruefsumme von {Path(path).name} stimmt nicht "
                f"(erwartet {expected}, erhalten {actual}).",
            )


def verifier_for(expected: str | None) -> Verifier:
    """
    Der Pruefer zu dem, was das Release mitliefert.

    Ein fehlender Hash ergibt **keinen** "Pruefer, der nichts
    prueft": er ergibt einen, der beim Pruefen abbricht. Der
    Unterschied ist der zwischen "wir haben nicht geprueft" und "wir
    haben festgestellt, dass wir nicht pruefen koennen" - und nur
    das zweite laesst sich melden.
    """

    return Sha256Verifier(expected or "")
