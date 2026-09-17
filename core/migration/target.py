"""
Wohin gewechselt wird - und ob ueberhaupt.

Diese Datei ist der **eine** Ort, der die naechste Generation kennt:
Repository, Generationsnummer, Kanal, Produktname. Alles andere in
`core/migration/` bekommt einen `MigrationTarget` gereicht und fragt
nie selbst nach, wohin es eigentlich geht.

WARUM DAS WICHTIG IST
---------------------

"5.0.0" darf nicht an zehn Stellen stehen. Es steht hier sogar an
*keiner*: die Zielgeneration ist die **naechste nach der eigenen**
(`next_major(VERSION)`), nicht die feste Zahl 5. Das hat zwei Folgen,
die beide gebraucht werden:

- Eine App, die selbst schon 5.x ist, bietet den Wechsel auf 5 nicht
  erneut an - sie sucht 6. Der Fall "bereits migriert" braucht dafuer
  keinen Merker, er faellt aus der Rechnung heraus.
- Derselbe Apparat traegt spaeter 5.x -> 6.x, ohne dass eine Zeile
  Fachlogik angefasst werden muss.

Wer zum Testen etwas anderes braucht, ueberschreibt es in der
Konfiguration oder ueber eine Umgebungsvariable - beides ohne
Neubau.

DER SCHALTER
------------

`MIGRATION_ENABLED_DEFAULT` ist `False`, und das bleibt so, solange
Companion-Forever nicht veroeffentlicht ist. Solange er `False` ist,
stellt diese App **keine einzige** Anfrage an das Zielrepository und
zeigt nichts davon an - `MigrationService.enabled()` ist die erste
Frage in jedem Einstiegspunkt.
"""

from __future__ import annotations

from dataclasses import dataclass
import os

from core.version import VERSION, major_of


#
# Der Schalter. Wird beim Freigeben der Migration auf True gesetzt -
# siehe docs/systems/forever-migration.md ("Was ist zu tun, wenn
# Companion-Forever 5.0.0 fertig ist").
#

MIGRATION_ENABLED_DEFAULT = False


#
# Die Konfigurationsschluessel: Einstellungen und Fortschritt stehen
# absichtlich getrennt. Was der Nutzer (oder der Entwickler) waehlt,
# und was die Migration darueber gelernt hat, sind zwei Dinge - ein
# gemeinsames Woerterbuch waere die erste Stelle, an der ein
# Zuruecksetzen des Fortschritts eine Einstellung mitnimmt.
#

SETTINGS_KEY = "forever_migration"

STATE_KEY = "forever_migration_state"


#
# Umgebungsvariablen fuer den Entwickler-Testmodus. Sie gewinnen
# gegen die Konfiguration, damit ein Test nichts hinterlaesst, was
# spaeter beim normalen Start noch gilt.
#

ENV_ENABLED = "WEINT_FOREVER_MIGRATION"

ENV_CHANNEL = "WEINT_FOREVER_CHANNEL"

ENV_DRY_RUN = "WEINT_FOREVER_DRY_RUN"

ENV_RELEASES = "WEINT_FOREVER_RELEASES"


#
# Kanaele. "stable" ist der einzige, den die normale Nutzerschaft je
# zu sehen bekommt; die anderen beiden gibt es fuer die Erprobung
# eines Releases, bevor es fertig ist.
#

STABLE = "stable"

BETA = "beta"

DEVELOPMENT = "development"

CHANNELS = (STABLE, BETA, DEVELOPMENT)


#
# Welche Vorab-Kennungen ein Kanal durchlaesst. "stable" laesst
# keine durch - ausdruecklich als leere Menge und nicht als
# Sonderfall im Code, damit die Regel an einer Stelle steht.
#

_CHANNEL_PRERELEASES = {
    STABLE: (),
    BETA: ("beta", "rc"),
    DEVELOPMENT: ("beta", "rc", "alpha", "dev", "nightly", "preview"),
}


@dataclass(frozen=True)
class MigrationTarget:
    """
    Die naechste Generation, vollstaendig beschrieben.
    """

    owner: str
    repo: str
    product_name: str
    major: int
    channel: str = STABLE

    @property
    def slug(self) -> str:
        return f"{self.owner}/{self.repo}"

    @property
    def generation_label(self) -> str:
        """
        "Companion-Forever 5" - was der Nutzer liest, solange die
        genaue Fassung noch nicht feststeht.
        """

        return f"{self.product_name} {self.major}"

    def accepts(self, version) -> bool:
        """
        Gehoert diese Fassung zu dem, was dieses Ziel sucht?

        Zwei Bedingungen, und beide sind Fachregeln, keine Filter:
        die richtige Generation (eine 4.9.0 im Zielrepository ist
        kein Generationswechsel) und ein vom Kanal erlaubter
        Reifegrad.
        """

        if version is None:
            return False

        if version.major != self.major:
            return False

        return self.allows_prerelease(version)

    def allows_prerelease(self, version) -> bool:

        if not version.is_prerelease:
            return True

        allowed = _CHANNEL_PRERELEASES.get(self.channel, ())

        if not allowed:
            return False

        #
        # "beta.1" -> "beta". Verglichen wird der erste Abschnitt,
        # nicht die ganze Zeichenkette: die Nummer dahinter
        # unterscheidet zwei Vorabfassungen, nicht zwei Reifegrade.
        #

        marker = version.prerelease.split(".")[0].lower()

        return marker in allowed


#
# Das Zielrepository steht fest (Aufgabenstellung). Der Produktname
# ist der, den der Nutzer liest - nicht der Repositoryname, auch
# wenn beide hier gerade gleich lauten.
#

DEFAULT_OWNER = "daddler"

DEFAULT_REPO = "Companion-Forever"

DEFAULT_PRODUCT_NAME = "Companion-Forever"


def next_major(version: str = VERSION) -> int:
    """
    Die naechste Generation nach der laufenden Fassung.

    Eine unlesbare eigene Fassung (dazu muesste jemand
    `core/version.py` kaputtmachen) ergibt die 5 - der einzige Ort,
    an dem diese Zahl ueberhaupt vorkommt, und auch hier nur als
    Notnagel.
    """

    major = major_of(version)

    if major is None:
        return 5

    return major + 1


def _settings(config) -> dict:

    if config is None:
        return {}

    data = getattr(config, "data", None)

    if not isinstance(data, dict):
        return {}

    settings = data.get(SETTINGS_KEY)

    return settings if isinstance(settings, dict) else {}


def _env_flag(name: str) -> bool | None:
    """
    `None` heisst "nicht gesetzt" - und das ist nicht dasselbe wie
    "aus". Nur so kann die Umgebungsvariable gegen die Konfiguration
    gewinnen, ohne sie auch dann zu ueberschreiben, wenn sie gar
    nicht gesetzt ist.
    """

    raw = os.environ.get(name)

    if raw is None:
        return None

    return raw.strip().lower() in ("1", "true", "yes", "on")


def migration_enabled(config=None) -> bool:
    """
    Ob die Migration ueberhaupt stattfinden darf.

    Reihenfolge: Umgebungsvariable (Entwickler), dann Konfiguration,
    dann die Vorgabe - und die ist `False`.
    """

    from_env = _env_flag(ENV_ENABLED)

    if from_env is not None:
        return from_env

    settings = _settings(config)

    if "enabled" in settings:
        return bool(settings["enabled"])

    return MIGRATION_ENABLED_DEFAULT


def dry_run_enabled(config=None) -> bool:
    """
    Probelauf: alles ausser dem letzten Schritt. Siehe
    `MigrationService.migrate()`.
    """

    from_env = _env_flag(ENV_DRY_RUN)

    if from_env is not None:
        return from_env

    return bool(_settings(config).get("dry_run", False))


def channel(config=None) -> str:

    raw = os.environ.get(ENV_CHANNEL) or _settings(config).get("channel") or STABLE

    raw = str(raw).strip().lower()

    return raw if raw in CHANNELS else STABLE


def target_for(config=None) -> MigrationTarget:
    """
    Das Ziel, wie es diese Installation sieht.

    Alles ueberschreibbar, nichts davon muss ueberschrieben werden:
    ohne Konfiguration steht hier "daddler/Companion-Forever",
    Generation 5 (weil diese App 4.x ist), Kanal "stable".
    """

    settings = _settings(config)

    slug = str(settings.get("repository") or "").strip()

    owner, repo = DEFAULT_OWNER, DEFAULT_REPO

    if "/" in slug:

        parts = slug.split("/", 1)

        if parts[0].strip() and parts[1].strip():
            owner, repo = parts[0].strip(), parts[1].strip()

    try:
        major = int(settings.get("target_major") or 0)
    except (TypeError, ValueError):
        major = 0

    #
    # 0 heisst "automatisch" und nicht "Generation 0" - dieselbe
    # Linie wie `characters_min_level` (0 = Hoechststufe der
    # Spielversion): eine Null ist eine Frage, keine Antwort.
    #

    if major <= 0:
        major = next_major()

    return MigrationTarget(
        owner=owner,
        repo=repo,
        product_name=str(settings.get("product_name") or DEFAULT_PRODUCT_NAME),
        major=major,
        channel=channel(config),
    )
