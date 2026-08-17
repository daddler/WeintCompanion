"""
Zuordnung Discord-Account -> WoW-Charakter: die reine Hälfte.

Der Kalender-Invite ingame braucht echte Charakternamen. Der Bot kennt
sie nur, wenn der Spieler selbst die Companion verknüpft **und** seine
Twinkverwaltung gepflegt hat - für Gildenfremde und Nachzügler blieb
nur der Discord-Anzeigename, den es ingame nicht gibt. Der Bot hat
dafür seit Kurzem eine zweite Quelle: eine von Hand gesetzte Zuordnung
(`services/character_links.py` drüben, `/weintcharakter` in Discord).

Diese Datei übersetzt die Antwort des Bots in Zeilen, die die Seite
zeichnen kann. Ohne Qt und ohne `httpx` - aus demselben Grund wie bei
`roster_target()` und `build_profile_payload()`: die Entscheidung, was
als Lücke gilt, ist die Stelle, an der etwas falsch sein kann, und sie
soll ohne Fenster prüfbar bleiben.

**Der Bot entscheidet, diese Seite zeigt an.** Welcher Name gewinnt,
wenn Meldung und Handeintrag sich widersprechen, steht ausschliesslich
im Bot - dieselbe Aufteilung wie beim Ausrüstungsbogen, wo das Addon
urteilt und die Companion zeichnet. Auch das Zerlegen von
"Njiah-OokOok" in Name und Realm passiert dort: die Antwort auf ein
POST nennt den gespeicherten Stand, und genau der wird angezeigt.
Zwei Zerlegungen derselben Eingabe würden auseinanderlaufen, und der
Unterschied fiele erst am Kalender auf.
"""

from __future__ import annotations

from dataclasses import dataclass, field


#
# Herkunft eines Namens, wie der Bot sie meldet. `DISCORD` ist die
# Lücke: dort steht kein Charakter, sondern der Anzeigename.
#

SOURCE_RAIDLEAD = "raidlead"

SOURCE_COMPANION = "companion"

SOURCE_DISCORD = "discord"


SOURCE_LABELS = {
    SOURCE_RAIDLEAD: "Von Hand gesetzt",
    SOURCE_COMPANION: "Vom Spieler gemeldet",
    SOURCE_DISCORD: "Kein Charakter bekannt",
}


#
# Englischer Klassen-Token -> deutsche Beschriftung. Dieselben Token,
# die der Bot in CLASS_MAP führt und in der Anmeldung ablegt.
#

CLASS_LABELS = {
    "WARRIOR": "Krieger",
    "PALADIN": "Paladin",
    "PRIEST": "Priester",
    "DRUID": "Druide",
    "MONK": "Mönch",
    "HUNTER": "Jäger",
    "MAGE": "Magier",
    "WARLOCK": "Hexenmeister",
    "ROGUE": "Schurke",
    "SHAMAN": "Schamane",
    "DEATHKNIGHT": "Todesritter",
}


ANY_CLASS = ""


ANY_CLASS_LABEL = "Jede Klasse"


def class_label(token: str | None) -> str:
    """
    Beschriftung eines Klassen-Tokens.

    Ein unbekannter Token wird unverändert durchgereicht, nicht durch
    einen geratenen ersetzt - dieselbe Regel wie bei den Klassennamen
    im Analyzer. "UNKNOWN" ist der Token einer Anmeldung ohne gesetzte
    Klasse und bekommt deshalb einen eigenen, ehrlichen Text.
    """

    token = (token or "").strip().upper()

    if not token:
        return ANY_CLASS_LABEL

    if token == "UNKNOWN":
        return "Klasse unbekannt"

    return CLASS_LABELS.get(token, token)


def format_character(name: str | None, realm: str | None) -> str:
    """
    "Njiah" oder "Njiah-OokOok" - so, wie die Einladung ingame
    adressiert wird.
    """

    name = (name or "").strip()
    realm = (realm or "").strip()

    if not name:
        return ""

    return f"{name}-{realm}" if realm else name


@dataclass(frozen=True)
class SignupRow:
    """Eine Anmeldung des laufenden Raids samt aufgelöstem Namen."""

    discord_id: str

    discord_name: str

    name: str

    realm: str = ""

    class_token: str = ""

    role: str = "DPS"

    source: str = SOURCE_DISCORD

    resolved: bool = False

    @property
    def character(self) -> str:
        return format_character(self.name, self.realm)

    @property
    def source_label(self) -> str:
        return SOURCE_LABELS.get(self.source, self.source)

    @property
    def class_name(self) -> str:
        return class_label(self.class_token)


@dataclass(frozen=True)
class LinkRow:
    """Ein von Hand gesetzter Eintrag."""

    discord_id: str

    name: str

    realm: str = ""

    class_token: str = ANY_CLASS

    @property
    def character(self) -> str:
        return format_character(self.name, self.realm)

    @property
    def class_name(self) -> str:
        return class_label(self.class_token)

    @property
    def is_placeholder(self) -> bool:
        return not self.class_token


@dataclass(frozen=True)
class Overview:
    """Was der Bot zur Charakterzuordnung zu sagen hat."""

    signups: tuple[SignupRow, ...] = ()

    links: tuple[LinkRow, ...] = ()

    raid_id: int | None = None

    #
    # Leerer Text heißt: alles in Ordnung. Sonst steht hier die
    # Erklärung des Bots (oder die eigene), unverändert anzeigbar.
    #

    reason: str = ""

    #
    # Fehlt die Rolle, ist das kein Fehler, sondern eine Antwort - die
    # Seite sagt dann, wofür sie da wäre, statt eine Störung zu melden.
    #

    forbidden: bool = False

    @property
    def ok(self) -> bool:
        return not self.reason and not self.forbidden

    @property
    def has_raid(self) -> bool:
        return self.raid_id is not None

    @property
    def open_rows(self) -> tuple[SignupRow, ...]:
        return tuple(row for row in self.signups if not row.resolved)

    @property
    def resolved_count(self) -> int:
        return sum(1 for row in self.signups if row.resolved)

    def links_for(self, discord_id: str) -> tuple[LinkRow, ...]:
        return tuple(row for row in self.links if row.discord_id == discord_id)


def parse_overview(body: dict | None) -> Overview:
    """
    Antwort von GET /companion/character-links in Zeilen übersetzen.

    Defensiv gelesen wie jeder Bot-Payload: eine unvollständige Antwort
    ist kein Fehler, sondern führt zu weniger Zeilen. Ein Eintrag ohne
    `discord_id` wird verworfen - er wäre weder zuzuordnen noch zu
    löschen.
    """

    if not isinstance(body, dict):
        return Overview(reason="Die Antwort des Bots hatte ein unerwartetes Format.")

    raid_id = body.get("raid_id")

    signups = []

    for raw in body.get("signups") or ():

        if not isinstance(raw, dict):
            continue

        discord_id = str(raw.get("discord_id") or "").strip()

        if not discord_id:
            continue

        signups.append(SignupRow(
            discord_id=discord_id,
            #
            # Kein Anzeigename heißt, dass der Bot den Account im
            # Server nicht mehr findet (ausgetreten). Die ID ist dann
            # das Einzige, was ihn noch benennt - besser als ein
            # leeres Feld, das wie ein Zeichenfehler aussieht.
            #
            discord_name=str(raw.get("discord_name") or "").strip() or discord_id,
            name=str(raw.get("name") or "").strip(),
            realm=str(raw.get("realm") or "").strip(),
            class_token=str(raw.get("class") or "").strip().upper(),
            role=str(raw.get("role") or "DPS").strip().upper(),
            source=str(raw.get("source") or SOURCE_DISCORD).strip().lower(),
            resolved=bool(raw.get("resolved")),
        ))

    links = []

    for raw in body.get("links") or ():

        if not isinstance(raw, dict):
            continue

        discord_id = str(raw.get("discord_id") or "").strip()
        name = str(raw.get("name") or "").strip()

        if not discord_id or not name:
            continue

        links.append(LinkRow(
            discord_id=discord_id,
            name=name,
            realm=str(raw.get("realm") or "").strip(),
            class_token=str(raw.get("class") or "").strip().upper(),
        ))

    return Overview(
        signups=tuple(signups),
        links=tuple(links),
        raid_id=raid_id if isinstance(raid_id, int) else None,
    )


def summary_text(overview: Overview) -> str:
    """
    Der Satz über der Liste.

    Er nennt die offenen Zuordnungen zuerst, denn das ist die Frage,
    mit der man diese Seite öffnet. "0 offen" wird nie behauptet, wo
    gar keine Anmeldung vorliegt - eine Zahl, die nichts gezählt hat,
    ist die falscheste aller Antworten.
    """

    if not overview.has_raid:
        return "Zurzeit läuft keine Anmeldung."

    total = len(overview.signups)

    if not total:
        return "Zur laufenden Anmeldung hat sich noch niemand gemeldet."

    open_count = len(overview.open_rows)

    if not open_count:
        return (
            f"Für alle {total} Anmeldungen ist ein Charaktername bekannt. "
            f"Der Kalender-Invite erreicht jeden."
        )

    return (
        f"{open_count} von {total} Anmeldungen haben noch keinen "
        f"Charakternamen - der Kalender-Invite erreicht sie nicht."
    )
