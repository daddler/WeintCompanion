#
# Basis-URL des WeintCodex-Bot-Backends. Zentral an dieser einen
# Stelle gepflegt, damit ein künftiger Umzug des Bots (neue Domain,
# neues Hosting) nicht an einer von mehreren duplizierten Stellen
# vergessen werden kann.
#

BOT_BASE_URL = "https://weintcodex-a1d.b.jrnm.app"

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
