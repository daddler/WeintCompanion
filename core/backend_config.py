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


def guild_url(guild_id: str = "") -> str:
    """
    Der Link auf eine Discord-Gilde.

    Ohne Angabe die Gilde des Projekts.
    """

    return (
        "https://discord.com/channels/"
        f"{str(guild_id).strip() or DISCORD_GUILD_ID}"
    )


def feedback_url() -> str:

    return f"{guild_url()}/{DISCORD_FEEDBACK_CHANNEL_ID}"


#
# Die Ziele, die `roster_target()` nennen kann.
#

TARGET_URL = "url"

TARGET_SETTINGS = "settings"


def roster_target(
    community_id: str = "",
    has_account: bool = False,
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

    1. Nennt das Zugriffsprofil eine Gilde, gilt jene - nur sie
       gehört nachweislich zu diesem Nutzer.
    2. Ist ein Konto verknüpft, der Bot hat aber keine Gilde gemeldet
       (das Endpunkt existiert noch nicht), führt der Weg in die Gilde
       des Projekts.
    3. Ohne verknüpftes Konto ist die Einstellung der richtige Ort.
       Ein Discord-Link würde hier auf einen Server zeigen, zu dem die
       Anwendung nie eine Verbindung hergestellt hat.
    """

    stored = str(community_id or "").strip()

    if stored:
        return TARGET_URL, guild_url(stored)

    if has_account:
        return TARGET_URL, guild_url()

    return TARGET_SETTINGS, "discord"
