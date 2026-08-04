"""
Zuordnung Discord-Rolle -> Rang -> Freigaben.

Diese Tabelle ist die Companion-Haelfte des Zugriffsprofils, das das
Addon ab WeintCodex 1.2.0.0 auswertet (siehe core/access.lua dort). Sie
liegt hier und nicht im Bot, weil eine Rollenumbenennung im Discord so
ohne Bot-Deploy nachgezogen werden kann.

WICHTIG, damit niemand mehr darin sieht als drin ist: diese Datei liegt
auf dem Rechner des Spielers und ist editierbar, genauso wie die
SavedVariables des Addons. Das Ganze ist DATENHYGIENE UND UX, KEINE
SICHERHEITSGRENZE:

  - die Community-Bindung im Addon verhindert, dass sich die Daten
    zweier Gilden in einer SavedVariables-Datei vermischen,
  - die Freigaben halten die Oberflaeche ehrlich: niemand sieht eine
    Seite voller Zahlen, die ihn nichts angehen.

Vertraulichkeit leistet das nicht. Dafuer muesste der Bot eine
unberechtigte Nutzlast gar nicht erst ausliefern.

TIER_FEATURES unten muss mit TIER_FEATURES in WeintCodex'
core/access.lua uebereinstimmen. Das Addon fuehrt dieselbe Tabelle als
Rueckfall fuer Schluessel, die wir nicht mitschicken - wir schicken
aber immer alle mit (siehe features_for), damit ein Auseinanderlaufen
der beiden Tabellen gar nicht auffallen kann.
"""

from __future__ import annotations


#
# Raenge, aufsteigend. Der hoechste gewinnt, wenn ein Nutzer mehrere
# zugeordnete Rollen hat - sonst wuerde ein Offizier, der zusaetzlich
# die Rolle "Raidgast" traegt, auf Gast zurueckfallen.
#

TIER_ORDER = (
    "gast",
    "extern",
    "mitglied",
    "offizier",
)


TIER_LABELS = {
    "gast": "Gast",
    "extern": "Extern",
    "mitglied": "Mitglied",
    "offizier": "Offizier",
}


#
# Die neun Freigaben. Reihenfolge nur der Lesbarkeit wegen.
#
# ACHTUNG: calendar.view niemals ohne raids.view gewaehren - die
# Kalenderseite des Addons liest die Anmeldungen fuer die
# Einladungsvorschau.
#

FEATURE_KEYS = (
    "raids.view",
    "raids.edit",
    "calendar.view",
    "calendar.invite",
    "materials.view",
    "materials.scan",
    "bossguides.tips",
    "weinttv.raid",
    "loot.report",
)


TIER_FEATURES = {

    "gast": set(),

    #
    # Extern bekommt genau das, was man zum Mitraiden braucht: Roster,
    # Termine, Taktiken. Nicht: eine fremde Gildenbank in unsere
    # Auswertung scannen, Auswertungen des ganzen Raids, oder
    # Loot-Meldungen in unseren Discord.
    #

    "extern": {
        "raids.view",
        "calendar.view",
        "bossguides.tips",
    },

    "mitglied": {
        "raids.view",
        "calendar.view",
        "bossguides.tips",
        "materials.view",
        "materials.scan",
        "weinttv.raid",
        "loot.report",
    },

    "offizier": {
        "raids.view",
        "raids.edit",
        "calendar.view",
        "calendar.invite",
        "materials.view",
        "materials.scan",
        "bossguides.tips",
        "weinttv.raid",
        "loot.report",
    },

}


#
# Standard-Zuordnung Discord-Rollenname -> Rang. Wird beim Laden der
# Konfiguration eingesetzt und ist dort ueberschreibbar
# (config.data["access_role_map"]), damit umbenannte oder zusaetzliche
# Rollen ohne neue Companion-Version nachgezogen werden koennen.
#
# Verglichen wird kleingeschrieben und ohne Rand-Leerzeichen, sonst
# waere "Raider " eine andere Rolle als "Raider".
#

DEFAULT_ROLE_MAP = {

    "gildenmeister": "offizier",
    "offizier": "offizier",
    "raidlead": "offizier",
    "raidleitung": "offizier",

    "mitglied": "mitglied",
    "gildenmitglied": "mitglied",
    "trial": "mitglied",

    "raidgast": "extern",
    "gast": "extern",
    "extern": "extern",
    "twink": "extern",

    #
    # Tatsaechliche Discord-Rollennamen von "Bis Einer Weint": Admin,
    # Gildenleitung, Klassen-Support und Member sind gildenintern und
    # sollen den vollen Funktionsumfang bekommen. Raider und Friends
    # sind gildenexterne Rollen fuer Mitraidende ohne Gildenmitgliedschaft
    # - deshalb "extern" statt "mitglied", obwohl "Raider" andernorts oft
    # ein Gildenmitglied waere.
    #

    "admin": "offizier",
    "gildenleitung": "offizier",
    "klassen-support": "offizier",
    "member": "offizier",

    "raider": "extern",
    "friends": "extern",

}


def normalize_role(name) -> str:

    if not isinstance(name, str):
        return ""

    return name.strip().lower()


def resolve_tier(roles, role_map=None):
    """
    Bestimmt aus den Discord-Rollennamen den Rang.

    Gibt (tier, matched_roles) zurueck. Passt keine Rolle, ist tier
    None - der Aufrufer entscheidet dann, ob er ueberhaupt ein Profil
    zustellt. Ein stiller Rueckfall auf "gast" waere hier falsch: er
    wuerde einen Konfigurationsfehler (Rolle im Discord umbenannt, Map
    nicht nachgezogen) in eine Sperre verwandeln, die aussieht wie eine
    Absicht.
    """

    if role_map is None:
        role_map = DEFAULT_ROLE_MAP

    lookup = {
        normalize_role(key): value
        for key, value in role_map.items()
    }

    best = None
    matched = []

    for role in roles or []:

        tier = lookup.get(normalize_role(role))

        if tier is None:
            continue

        if tier not in TIER_ORDER:
            continue

        matched.append(role)

        if best is None or TIER_ORDER.index(tier) > TIER_ORDER.index(best):
            best = tier

    return best, matched


def features_for(tier) -> dict:
    """
    Vollstaendige Freigabetabelle als {Schluessel: bool}.

    Bewusst vollstaendig und nicht nur die erlaubten: das Addon nimmt
    ausdrueckliche Booleans immer vorrangig und braucht seine eigene
    Rangtabelle dann gar nicht mehr. Damit koennen die beiden Tabellen
    nicht auseinanderlaufen, ohne dass es auffaellt.

    Nicht-Booleans gelten im Addon absichtlich als "nicht gesetzt" -
    hier entstehen deshalb nur echte True/False-Werte.
    """

    allowed = TIER_FEATURES.get(tier, set())

    return {
        key: (key in allowed)
        for key in FEATURE_KEYS
    }


def label_for(tier) -> str:

    return TIER_LABELS.get(tier, tier or "")


#
# Antwort des Bots -> Nutzlast fuer das Addon
#
# Bewusst hier und nicht in core/access_profile_sync.py: dieser Teil
# ist reine Abbildung ohne Netzzugriff und laesst sich damit ohne httpx
# und ohne laufende App testen - dieselbe Trennung wie bei
# analyzer/providers/warcraftlogs_payload.py gegenueber
# core/warcraftlogs_client.py.
#


def build_profile_payload(
    data,
    role_map=None,
    version="",
    now=0,
):
    """
    Baut die access_profile-Nutzlast aus der Bot-Antwort.

    Gibt (payload, matched_roles, error) zurueck. Ist payload None, war
    die Antwort unbrauchbar oder keine Rolle zugeordnet - dann wird
    nichts zugestellt und im Addon bleibt alles offen. Ein stiller
    Rueckfall auf "gast" waere hier falsch: er wuerde einen
    Konfigurationsfehler (Rolle im Discord umbenannt, Zuordnung nicht
    nachgezogen) in eine Sperre verwandeln, die aussieht wie Absicht.
    """

    if not isinstance(data, dict):
        return None, [], "Antwort ist keine Tabelle."

    community = data.get("community")

    if not isinstance(community, dict):
        return None, [], "Antwort enthaelt keine Community."

    community_id = community.get("id")

    if community_id is None:
        return None, [], "Antwort enthaelt keine Community-ID."

    #
    # WICHTIG: als Zeichenkette. Eine Discord-Snowflake ist zu gross
    # fuer Luas 5.1-Zahlen - sie wuerde beim Schreiben zu "1.23e+18"
    # und im Addon nie gegen die Dezimaldarstellung passen, womit jede
    # Nachricht dort als "fremde Community" gaelte.
    #

    community_id = str(community_id).strip()

    if not community_id:
        return None, [], "Community-ID ist leer."

    roles = data.get("roles")

    if not isinstance(roles, list):
        roles = []

    #
    # Der Bot darf den Rang auch selbst mitschicken. Dann gewinnt er -
    # so laesst sich die Zuordnung spaeter in den Bot ziehen, ohne dass
    # die Companion dafuer neu ausgeliefert werden muss.
    #

    given = data.get("tier")

    if isinstance(given, str) and given.strip().lower() in TIER_ORDER:

        tier = given.strip().lower()
        matched = [str(role) for role in roles if role]

    else:

        tier, matched = resolve_tier(roles, role_map)

    if tier is None:

        listed = ", ".join(str(role) for role in roles) or "keine"

        return None, [], (
            f"Keine der Discord-Rollen ({listed}) ist einem Rang "
            f"zugeordnet. Zuordnung in den Einstellungen pruefen."
        )

    identity = data.get("identity")

    if not isinstance(identity, dict):
        identity = {}

    try:
        expires_at = int(data.get("expiresAt"))
    except (TypeError, ValueError):
        expires_at = 0

    payload = {
        "community": {
            "id": community_id,
            "name": str(community.get("name") or ""),
        },
        "identity": {
            "discordId": str(identity.get("discordId") or ""),
            "discordName": str(identity.get("discordName") or ""),
        },
        "tier": tier,
        "tierLabel": label_for(tier),
        "roles": [str(role) for role in roles if role],
        "features": features_for(tier),
        "issuedAt": int(now),
        "expiresAt": expires_at,
        "companionVersion": str(version or ""),
    }

    notice = data.get("notice")

    if isinstance(notice, str) and notice.strip():
        payload["notice"] = notice.strip()

    return payload, matched, None
