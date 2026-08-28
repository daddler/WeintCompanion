import os
from pathlib import Path

from core.paths import Paths


#
# Basis-URL des WeintCodex-Bot-Backends. Zentral an dieser einen
# Stelle gepflegt, damit ein künftiger Umzug des Bots (neue Domain,
# neues Hosting) nicht an einer von mehreren duplizierten Stellen
# vergessen werden kann - acht Module lesen sie.
#
# **Warum sie sich überschreiben lässt.** Der Bot liegt bei einem
# Anbieter, der den Rechner bestimmt, auf dem die Anwendung läuft, und
# den Rechner in den Hostnamen schreibt. Ein Umzug - erzwungen etwa
# durch einen ausgefallenen Bauserver - ändert die Adresse also, ohne
# dass am Bot selbst irgendetwas anders wäre. Stünde sie hier nur fest
# verdrahtet, kostete jeder solche Umzug eine neue Fassung der
# Companion, die alle erst installieren müssten - und bis dahin
# erreicht keine einzige den Bot mehr. Genau das ist einmal passiert.
#
# Zwei Wege, in dieser Reihenfolge:
#
#   1. die Umgebungsvariable WEINTCODEX_BOT_URL - für einen schnellen
#      Versuch, ohne eine Datei anzulegen;
#   2. eine Datei `bot_url.txt` im Konfigurationsverzeichnis, die nur
#      die Adresse enthält - das ist der Weg für den Dauerbetrieb,
#      und er lässt sich per Anleitung weitergeben.
#
# Ohne beides gilt der eingebaute Wert. Eine unbrauchbare Angabe wird
# **übergangen**, nicht übernommen: eine kaputte Adresse würde jeden
# einzelnen Abruf stillschweigend scheitern lassen, und der eingebaute
# Wert ist immer noch der bessere Rateversuch.
#

#
# Der Bot ist inzwischen zweimal umgezogen, und beim zweiten Mal
# wechselte nicht nur der Rechnername, sondern die ganze Domain:
#
#   weintcodex-a1d.b.jrnm.app  ->  weintcodex-bot.e.jrnm.app
#                              ->  weintcodex-bot.e.onjrnm.co.uk
#
# `jrnm.app` löst seitdem überhaupt nicht mehr auf (NXDOMAIN für die
# ganze Zone), nicht nur der alte Hostname. Jeder Abruf scheiterte
# danach mit "Der Name oder der Dienst ist nicht bekannt" - die
# Discord-Anmeldung eingeschlossen, obwohl an ihr nichts fehlte.
# Genau der Fall, für den die Überschreibung unten existiert.
#

DEFAULT_BOT_BASE_URL = "https://weintcodex-bot.e.onjrnm.co.uk"

BOT_URL_ENV = "WEINTCODEX_BOT_URL"

BOT_URL_FILE = "bot_url.txt"


def normalize_bot_url(value) -> str:
    """
    Eine brauchbare Basis-URL - oder "".

    Verlangt wird ein Schema (http/https) und ein Rest dahinter; der
    abschließende Schrägstrich fällt weg, weil jede Aufrufstelle ihren
    Pfad mit führendem Schrägstrich anhängt und daraus sonst ein
    doppelter würde.
    """

    text = str(value or "").strip().rstrip("/")

    if not text:
        return ""

    for schema in ("https://", "http://"):

        if text.lower().startswith(schema) and len(text) > len(schema):
            return text

    return ""


def bot_url_override_path() -> Path:
    """
    Wo die Datei mit der abweichenden Adresse liegt.

    Bewusst über `Paths.base()` zusammengesetzt und nicht über
    `Paths.config()`: jene Funktion legt das Verzeichnis an, und ein
    Modulimport darf keine Verzeichnisse erzeugen - schon gar nicht im
    Benutzerprofil, nur weil irgendwo eine Konstante gelesen wurde.
    """

    return Paths.base() / "config" / BOT_URL_FILE


def resolve_bot_base_url() -> str:

    aus_umgebung = normalize_bot_url(os.environ.get(BOT_URL_ENV))

    if aus_umgebung:
        return aus_umgebung

    try:
        pfad = bot_url_override_path()

        if pfad.is_file():

            aus_datei = normalize_bot_url(
                pfad.read_text(encoding="utf-8")
            )

            if aus_datei:
                return aus_datei

    except OSError:

        #
        # Nicht lesbar, falsche Rechte, Datenträger weg: kein Grund,
        # den Start abzubrechen. Der eingebaute Wert trägt weiter.
        #

        pass

    return DEFAULT_BOT_BASE_URL


def write_bot_url_override(value) -> str:
    """
    Die abweichende Adresse ablegen - oder die Ablage räumen.

    Liefert die abgelegte Adresse, oder "", wenn die Datei entfernt
    wurde. Eine unbrauchbare Angabe wird **nicht** geschrieben,
    sondern gemeldet: dieselbe Linie wie beim Lesen, nur eine Stufe
    früher. Eine kaputte Adresse hier abzulegen hiesse, den einzigen
    Ausweg mit dem zu verstopfen, wogegen er hilft.

    Warum das überhaupt bedienbar sein muss: verschwindet der Name
    des Bots aus dem DNS - der wahrscheinlichste Ausfall dieser
    Anwendung, siehe oben -, scheitert jeder Abruf, und der einzige
    Weg zurück führte bis 2.4.4 über eine von Hand angelegte Datei
    in einem Verzeichnis, das niemand auswendig kennt. Ein Ausweg,
    den man erst finden muss, ist im Ernstfall keiner.
    """

    text = str(value or "").strip()

    pfad = bot_url_override_path()

    if not text:

        try:
            pfad.unlink()
        except FileNotFoundError:
            pass

        return ""

    adresse = normalize_bot_url(text)

    if not adresse:

        raise ValueError(
            "Das ist keine brauchbare Adresse. Erwartet wird eine "
            "vollständige Angabe mit http:// oder https:// davor, "
            "zum Beispiel https://weintcodex-bot.example.app"
        )

    pfad.parent.mkdir(parents=True, exist_ok=True)

    pfad.write_text(adresse + "\n", encoding="utf-8")

    return adresse


def bot_url_source() -> str:
    """
    Woher die gerade gültige Adresse stammt.

    Für die Anzeige in den Einstellungen: steht dort eine Adresse,
    die von einer Umgebungsvariable kommt, hilft es nicht, das
    Eingabefeld zu ändern - jene gewinnt.
    """

    if normalize_bot_url(os.environ.get(BOT_URL_ENV)):
        return BOT_URL_ENV

    try:
        pfad = bot_url_override_path()

        if pfad.is_file() and normalize_bot_url(
            pfad.read_text(encoding="utf-8")
        ):
            return BOT_URL_FILE

    except OSError:
        pass

    return "default"


#
# Einmal beim Import bestimmt. Die acht lesenden Module holen sich den
# Wert selbst beim Import ab; eine spätere Änderung greift deshalb
# nach einem Neustart der Companion, nicht mitten im Betrieb - was für
# einen Serverumzug genau die richtige Körnung ist.
#

BOT_BASE_URL = resolve_bot_base_url()

#
# Die Discord-Gilde des Projekts, als ZEICHENKETTE - eine Snowflake
# sprengt die Zahlengenauigkeit (dieselbe Regel wie bei
# `community.id` in core/access_roles.py).
#
# Sie steht hier und nicht in der Seite, weil zwei Stellen sie
# brauchen: der Feedback-Link in Einstellungen -> Über und der
# "Aufstellung im Discord"-Knopf der Übersicht. Als bloßer Rückfall
# gedacht: nennt der Bot im Zugriffsprofil eine Gilde, gilt jene
# (`config["discord_community_id"]`), denn nur sie gehört
# nachweislich zu diesem Nutzer.
#

DISCORD_GUILD_ID = "1311060525555257364"

#
# Der Feedback-Channel innerhalb dieser Gilde. Deep-Link statt der
# reinen Invite-URL, damit Mitglieder direkt im richtigen Channel
# landen statt auf dem Server-Standardkanal.
#

DISCORD_FEEDBACK_CHANNEL_ID = "1519466082362982410"

#
# Der Kanal, in dem die Raids eröffnet werden. Er gilt nur innerhalb
# der Projektgilde - eine fremde Gilde hat andere Kanäle, und eine
# dorthin übernommene Kanal-ID führte auf einen Link ins Nichts.
#
# Nur ein Rückfall: nennt der Bot in `/companion/raid-schedule` den
# Fundort der Anmeldung, gilt jener, denn der zeigt auf den Beitrag
# selbst statt bloß auf den Kanal.
#

DISCORD_RAID_CHANNEL_ID = "1311325324008751225"


def guild_url(guild_id: str = "") -> str:
    """
    Der Link auf eine Discord-Gilde.

    Ohne Angabe die Gilde des Projekts.
    """

    return (
        "https://discord.com/channels/"
        f"{str(guild_id).strip() or DISCORD_GUILD_ID}"
    )


def channel_url(
    guild_id: str = "",
    channel_id: str = "",
    message_id: str = "",
) -> str:
    """
    Der Link auf einen Kanal - und, wenn bekannt, auf eine bestimmte
    Nachricht darin.

    Ohne Kanal bleibt es beim Gildenlink: `/channels/<gilde>` öffnet
    den Standardkanal, `/channels/<gilde>//<nachricht>` dagegen gar
    nichts.
    """

    parts = [
        str(part).strip()
        for part in (channel_id, message_id)
    ]

    if not parts[0]:
        return guild_url(guild_id)

    if not parts[1]:
        parts = parts[:1]

    return "/".join([guild_url(guild_id), *parts])


def feedback_url() -> str:

    return f"{guild_url()}/{DISCORD_FEEDBACK_CHANNEL_ID}"


#
# Das Präfix, unter dem die Discord-Anwendung selbst erreichbar ist.
# Derselbe Pfad wie im Web, nur mit eigenem Schema - `-` steht für
# "die laufende Anmeldung", Discord erwartet dort einen Platzhalter.
#

DISCORD_APP_PREFIX = "discord://-/channels/"

DISCORD_WEB_PREFIX = "https://discord.com/channels/"


def app_url(url: str) -> str:
    """
    Dieselbe Adresse für die Discord-Anwendung statt für den Browser.

    Der Knopf "Aufstellung im Discord" landete bis 2.0.2 im Browser,
    also in einer zweiten, abgemeldeten Ansicht desselben Servers -
    während die Anwendung daneben offen stand. Leer für alles, was
    kein Discord-Link ist; der Aufrufer bleibt dann beim Browser.
    """

    address = str(url or "").strip()

    if not address.startswith(DISCORD_WEB_PREFIX):
        return ""

    return DISCORD_APP_PREFIX + address[len(DISCORD_WEB_PREFIX):]


#
# Die Ziele, die `roster_target()` nennen kann.
#

TARGET_URL = "url"

TARGET_SETTINGS = "settings"


def roster_target(
    community_id: str = "",
    has_account: bool = False,
    signup: dict | None = None,
) -> tuple[str, str]:
    """
    Wohin der Knopf "Aufstellung im Discord" führt.

    Rein und ohne Qt - aus demselben Grund, aus dem
    `access_roles.build_profile_payload()` von `httpx` getrennt ist:
    die Entscheidung ist die Stelle, an der etwas falsch sein kann,
    und sie soll ohne Fenster prüfbar bleiben.

    Liefert `(TARGET_URL, adresse)` oder
    `(TARGET_SETTINGS, abschnitt)`.

    Die Reihenfolge trägt die eigentliche Aussage:

    0. Nennt der Bot den Fundort der Anmeldung (`signup`, aus
       `/companion/raid-schedule`), gilt der. Das ist die einzige
       Auskunft, die auf den **Beitrag** zeigt statt auf einen Server -
       und sie stammt aus derselben Antwort wie der Termin daneben,
       kann also nicht auf einen anderen Raid verweisen.
    1. Sonst: nennt das Zugriffsprofil eine Gilde, gilt jene - nur sie
       gehört nachweislich zu diesem Nutzer. Der Anmelde-Kanal des
       Projekts kommt dabei **nicht** mit; eine fremde Gilde hat
       eigene Kanäle.
    2. Ist ein Konto verknüpft, der Bot hat aber keine Gilde gemeldet
       (das Endpunkt existiert noch nicht), führt der Weg in den
       Anmelde-Kanal der Projektgilde.
    3. Ohne verknüpftes Konto ist die Einstellung der richtige Ort.
       Ein Discord-Link würde hier auf einen Server zeigen, zu dem die
       Anwendung nie eine Verbindung hergestellt hat.
    """

    found = signup or {}

    if found.get("channel_id"):

        return TARGET_URL, channel_url(
            found.get("guild_id", ""),
            found.get("channel_id", ""),
            found.get("message_id", ""),
        )

    stored = str(community_id or "").strip()

    if stored:
        return TARGET_URL, guild_url(stored)

    if has_account:

        return TARGET_URL, channel_url(
            "",
            DISCORD_RAID_CHANNEL_ID,
        )

    return TARGET_SETTINGS, "discord"
