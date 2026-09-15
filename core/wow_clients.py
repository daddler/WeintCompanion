"""
Welche Spielversion diese App bedient.

Bis 4.0 gab es diese Frage nicht: "WoW" hiess Mists of Pandaria
Classic, und der Ordnername `_classic_` stand an sechs Stellen im
Quelltext - in der Ordnerprüfung, in der Suche, in der Konfiguration,
in drei Beschriftungen. Eine Spielversion war kein Gegenstand, sondern
eine Annahme.

Mit *World of Warcraft: Forever* kommt eine zweite dazu, und irgendwann
wird sie die einzige sein. Damit dieser Wechsel **eine Datenänderung
und kein Umbau** ist, steht hier eine Tabelle: jede Spielversion ein
Eintrag, und alles, was sich zwischen ihnen unterscheidet, ein Feld
darin.

WAS ÜBER FOREVER NOCH NICHT BEKANNT IST
---------------------------------------

**Der Ordnername.** Blizzard nennt die Unterordner unter
"World of Warcraft" seit jeher `_retail_`, `_classic_`,
`_classic_era_`. Wie der für Forever heisst, weiss zum Zeitpunkt
dieses Eintrags niemand ausserhalb von Blizzard - der Eintrag unten
lässt `folder_names` deshalb **leer**, und das ist kein Versehen:

- Ein *bekannter* Ordnername wird direkt unter der gewählten Wurzel
  gesucht (`_classic_` unter "World of Warcraft").
- Ein *leerer* bedeutet "Namen unbekannt": dann entscheiden allein die
  Kennzeichen einer Installation (`Interface/AddOns`, `WTF`), und
  fremde Spielversionen werden über `FOREIGN_FLAVOR_FOLDERS`
  ausgeschlossen.

Sobald der Name feststeht, ist die Vorbereitung mit **einer Zeile**
abgeschlossen: `folder_names=("_forever_",)`. Nichts anderes muss sich
ändern.

**Die Höchststufe** (`max_level`) ebenso wenig. `None` heisst nicht
"keine", sondern "noch unbekannt", und wird überall als solche
behandelt - siehe `core/character_store.default_min_level()`: solange
die Höchststufe unbekannt ist, verschwindet lieber kein Charakter aus
"Meine Charaktere", als dass eine erfundene Zahl welche ausblendet.
Dieselbe Linie wie `stars == 0` und `at == -1`: aus einer Datenlücke
wird kein Befund.

WAS HIER NICHT HINEINGEHÖRT
---------------------------

Alles, was die *Auswertung* betrifft: Encounter-Tabellen
(`analyzer/data/encounters.py`), Spezialisierungen
(`analyzer/data/specs.py`), die Sim-Adressen (`core/qelive.py`,
`core/wowsims_link.py`). Die hängen an der Spielversion, aber nicht an
ihrem *Installationsort* - sie wandern erst, wenn Forever erscheint und
man weiss, wogegen dort gespielt wird. Diese Datei beantwortet
ausschliesslich: **welche Version, und wo liegt sie.**
"""

from __future__ import annotations

from dataclasses import dataclass, field


#
# Die drei Kennzeichen einer WoW-Installation, an denen sie sich seit
# der ersten Fassung erkennen lässt. Sie stehen hier als Vorgabe und
# nicht fest verdrahtet in der Prüfung, damit eine Spielversion sie
# überschreiben kann, falls Forever den Aufbau ändert.
#

STANDARD_MARKERS: tuple[tuple[str, ...], ...] = (

    ("Interface",),
    ("Interface", "AddOns"),
    ("WTF",),

)


@dataclass(frozen=True)
class WowClient:
    """
    Eine Spielversion und das, was diese App über sie wissen muss.
    """

    id: str

    #
    # Der volle Name für Überschriften und Dateidialoge, die Kurzform
    # für Statuszeilen ("MoP Classic · _classic_").
    #

    name: str

    short_name: str

    #
    # Die möglichen Namen des Installationsordners unter der
    # Battle.net-Wurzel. **Leer heisst "noch unbekannt"**, nicht
    # "keiner" - siehe Modulkommentar.
    #

    folder_names: tuple[str, ...] = ()

    #
    # Höchststufe, oder None solange unbekannt.
    #

    max_level: int | None = None

    #
    # Erschienen? Eine nicht erschienene Version lässt sich bereits
    # auswählen (darum geht es bei dieser Vorbereitung), wird aber in
    # der Einrichtung nicht angeboten - dort wäre sie nur eine Frage,
    # die niemand beantworten kann.
    #

    released: bool = True

    #
    # Einzeiler unter der Auswahl. Trägt, was der Nutzer über diese
    # Version wissen muss, bevor er sie wählt.
    #

    hint: str = ""

    markers: tuple[tuple[str, ...], ...] = field(
        default=STANDARD_MARKERS,
    )

    # --------------------------------------------------

    @property
    def folder_known(self) -> bool:
        """
        Ist der Name des Installationsordners bekannt?
        """

        return bool(self.folder_names)


# --------------------------------------------------
# Die Tabelle
# --------------------------------------------------


MOP_CLASSIC = WowClient(

    id="mop_classic",

    name="World of Warcraft: Mists of Pandaria Classic",

    short_name="MoP Classic",

    folder_names=("_classic_",),

    max_level=90,

    released=True,

)


FOREVER = WowClient(

    id="forever",

    name="World of Warcraft: Forever",

    short_name="Forever",

    #
    # Absichtlich leer - siehe Modulkommentar. Sobald Blizzard den
    # Ordnernamen nennt, steht er hier und sonst nirgends.
    #

    folder_names=(),

    max_level=None,

    released=False,

    hint=(
        "Forever ist angekündigt, aber noch nicht erschienen. Der "
        "Name des Installationsordners steht noch nicht fest - wähle "
        "den Ordner deiner Installation deshalb selbst aus, sobald "
        "es sie gibt."
    ),

)


CLIENTS: tuple[WowClient, ...] = (

    MOP_CLASSIC,
    FOREVER,

)


DEFAULT_CLIENT_ID = MOP_CLASSIC.id


#
# Alle Unterordnernamen, die Blizzard für Spielversionen vergibt -
# einschliesslich Testumgebungen. Für eine Spielversion mit *bekanntem*
# Ordnernamen spielt die Liste keine Rolle; für eine mit unbekanntem
# ist sie der Unterschied zwischen "irgendeine Installation" und "die
# gesuchte": ohne sie würde eine Suche nach Forever im Zweifel
# `_retail_` finden und als Forever ausgeben.
#

FOREIGN_FLAVOR_FOLDERS: tuple[str, ...] = (

    "_retail_",
    "_classic_",
    "_classic_era_",
    "_ptr_",
    "_xptr_",
    "_beta_",
    "_classic_ptr_",
    "_classic_beta_",
    "_classic_era_ptr_",

)


# --------------------------------------------------
# Zugriff
# --------------------------------------------------


def all_clients() -> tuple[WowClient, ...]:

    return CLIENTS


def client(client_id) -> WowClient:
    """
    Die Spielversion zu einer Kennung.

    **Eine unbekannte Kennung fällt auf die Vorgabe zurück und wirft
    nicht.** Der Wert kommt aus der `config.json` und damit aus einer
    Datei, die ein Nutzer von Hand ändern kann; eine Ausnahme beim
    Start wäre die härteste denkbare Antwort auf einen Tippfehler.
    """

    for candidate in CLIENTS:

        if candidate.id == client_id:
            return candidate

    return default_client()


def default_client() -> WowClient:

    for candidate in CLIENTS:

        if candidate.id == DEFAULT_CLIENT_ID:
            return candidate

    return CLIENTS[0]


def released_clients() -> tuple[WowClient, ...]:
    """
    Die Spielversionen, die es tatsächlich schon gibt.

    Die Einrichtung fragt nur dann nach der Version, wenn es hier mehr
    als eine gibt - solange Forever nicht erschienen ist, bleibt der
    erste Schritt so kurz wie bisher, und er wird von selbst zu einer
    Frage, sobald `released=True` gesetzt wird.
    """

    return tuple(
        candidate
        for candidate in CLIENTS
        if candidate.released
    )


def foreign_flavor_folders(target: WowClient) -> tuple[str, ...]:
    """
    Die Ordnernamen anderer Spielversionen - also alle bekannten ausser
    denen der übergebenen.
    """

    own = set(target.folder_names)

    return tuple(
        name
        for name in FOREIGN_FLAVOR_FOLDERS
        if name not in own
    )
