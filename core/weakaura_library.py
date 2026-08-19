"""
Was eine WeakAura ist, bevor sie irgendwo hingeschrieben wird.

Diese Datei ist die **reine Hälfte** der WeakAura-Brücke: Modell,
Prüfung, ID-Bildung und das Lesen der Katalogmeldung aus dem Spiel.
Kein Qt, kein `httpx`, keine Datei - aus demselben Grund wie bei
`core/raid_schedule.py`, `core/character_links.py` und
`access_roles.build_profile_payload()`: hier wird entschieden, und
Entscheidungen sind die Stelle, an der etwas falsch sein kann. Sie
soll ohne Fenster prüfbar sein.

Seit 2.2.0 gibt es dieselbe Aura in **zwei Reichweiten**: nur auf
diesem Rechner, oder über den Discord-Bot für die ganze Gilde
(`core/weakaura_guild_sync.py`). `WeakAura.scope` sagt, welche von
beiden - und ist das einzige, was diese Datei davon wissen muss: die
Prüfung ist dieselbe, die Kennung ist dieselbe, und der Weg ins Addon
ist derselbe.

Der Ablauf im Ganzen steht in `docs/weakaura-bridge.md`.

Drei Regeln, die nicht nach Geschmack sind:

* **Die ID ist der Schlüssel und wird nie neu vergeben.** Sie
  entscheidet im Addon darüber, ob eine Zustellung eine neue Aura ist
  oder eine vorhandene ersetzt (`modules/weakauras.lua`). Wird sie
  beim Umbenennen mitgezogen, entstünde aus einer korrigierten
  Schreibweise eine zweite Aura neben der alten - und niemand wüsste,
  welche der beiden die aktuelle ist.
* **Der Importstring wird von Leerraum befreit, nicht abgewiesen.**
  WeakAuras-Strings enthalten keinen; wer seinen aus Discord oder aus
  einem Forumsbeitrag kopiert, bringt trotzdem Zeilenumbrüche mit.
  Sie zu entfernen ist eindeutig, das Einfügen abzulehnen wäre nur
  lästig.
* **Ein fehlender `!WA:`-Vorspann ist ein Hinweis, keine Ablehnung.**
  Ältere WeakAuras-Versionen exportieren ohne ihn, und ob eine
  Zeichenkette wirklich importierbar ist, weiß allein WeakAuras
  selbst. Eine Prüfung, die richtige Eingaben abweist, ist schlimmer
  als eine, die eine falsche durchlässt: die eine kostet einen
  Supportfall, die andere eine Fehlermeldung im Spiel.
"""

from __future__ import annotations

import re
import time
import unicodedata
from dataclasses import dataclass


#
# Die drei Rubriken der Ingame-Seitenspalte. Sie stehen so auch in
# `modules/weakauras.lua`; eine vierte hier anzubieten hiesse, sie
# dort unter "utility" wiederzufinden.
#

CATEGORIES = ("class", "raid", "utility")

CATEGORY_LABELS = {
    "class": "Klassenaura",
    "raid": "Raidaura",
    "utility": "Utility-Aura",
}

DEFAULT_CATEGORY = "utility"


#
# Woher eine Zeile im Spiel stammt. "addon" heisst: sie kam mit dem
# Addon-ZIP und ist hier nur bekannt, weil das Spiel sie gemeldet hat.
#

ORIGIN_ADDON = "addon"

ORIGIN_COMPANION = "companion"

#
# Aus der Bibliothek der Gilde, vom Addon so zurueckgemeldet. Muss
# hier stehen, obwohl niemand danach filtert: `from_addon` fragt
# ausdruecklich nach `ORIGIN_ADDON` und nicht "alles ausser
# companion", sonst zaehlte eine Gildenaura als mitgeliefert und
# stuende in der Oberflaeche unter "mit dem Addon geliefert".
#

ORIGIN_GUILD = "guild"


#
# Wie weit eine Aura reicht.
#
# `local` heisst: sie liegt auf diesem Rechner und geht ins eigene
# Addon. `guild` heisst: sie liegt zusaetzlich in der Bibliothek des
# Bots, und jede verknuepfte Companion holt sie sich ab.
#
# Die Freigabe ist eine **eigene Handlung**, keine Voreinstellung.
# Alles, was jemand tippt, ungefragt an 25 Leute zu schicken, waere
# die Art Ueberraschung, die man nur einmal erlebt und danach die
# Funktion meidet.
#

SCOPE_LOCAL = "local"

SCOPE_GUILD = "guild"


#
# Unterhalb dieser Länge ist eine Zeichenkette kein Aura-Export,
# sondern ein Versehen (ein halb kopierter String, ein Name im
# falschen Feld). Der kürzeste echte Export, den WeakAuras für eine
# einzelne triviale Aura ausgibt, liegt deutlich darüber.
#

MIN_IMPORT_LENGTH = 24


def normalize_category(value: str) -> str:

    value = (value or "").strip().lower()

    return value if value in CATEGORIES else DEFAULT_CATEGORY


def clean_import_string(value: str) -> str:
    """
    Jeden Leerraum entfernen. Siehe Kopfkommentar - ein aus Discord
    kopierter String bringt Umbrüche mit, ein WeakAuras-Export
    enthält selbst keine.
    """

    return re.sub(r"\s+", "", value or "")


def looks_like_export(value: str) -> bool:
    """
    Trägt die Zeichenkette den Vorspann, den aktuelle
    WeakAuras-Versionen schreiben?

    Ausdrücklich **keine** Gültigkeitsprüfung - siehe Kopfkommentar.
    Die Oberfläche macht daraus einen Hinweis, keine Sperre.
    """

    return clean_import_string(value).startswith("!WA:")


def make_id(name: str, taken: set[str] | None = None) -> str:
    """
    Eine stabile, lesbare ID aus dem Namen.

    Lesbar, weil sie im Spiel in keiner Oberfläche steht, aber in
    jeder Fehlersuche: `WeintCodex.SavedData.weakAuraLibrary` von Hand
    zu lesen ist der Weg, auf dem eine kaputte Zustellung gefunden
    wird, und dort ist "companion-schamane-ele" eine Auskunft und ein
    Zeitstempel keine.

    Der Vorspann `companion-` hält sie aus dem Namensraum der
    mitgelieferten Auren heraus (`DRUID`, `DUNGEONPACK`, ...), damit
    ein neuer Eintrag nicht versehentlich eine mitgelieferte ersetzt.
    Wer eine mitgelieferte *absichtlich* ersetzen will, wählt in der
    Oberfläche die gemeldete Zeile aus und behält deren ID.
    """

    #
    # Umlaute zerlegen und die Zeichen ohne ASCII-Entsprechung
    # weglassen. "Mönch" wird zu "monch", nicht zu "mnch": das "ö"
    # zerfällt in "o" plus ein kombinierendes Trema, und nur das
    # Trema fällt weg.
    #

    decomposed = unicodedata.normalize("NFKD", name or "")

    ascii_only = "".join(
        char
        for char in decomposed
        if not unicodedata.combining(char)
    )

    slug = re.sub(r"[^a-z0-9]+", "-", ascii_only.lower()).strip("-")

    if not slug:
        slug = "aura"

    candidate = f"companion-{slug}"

    if not taken or candidate not in taken:
        return candidate

    #
    # Zwei Auren dürfen denselben Namen tragen (eine je Spec heisst
    # gern gleich). Die ID darf es nicht - sie ist der Schlüssel.
    #

    index = 2

    while f"{candidate}-{index}" in taken:
        index += 1

    return f"{candidate}-{index}"


@dataclass
class WeakAura:
    """
    Ein Eintrag der Bibliothek - genau das, was im Spiel als Zeile
    erscheint.
    """

    id: str = ""

    name: str = ""

    category: str = DEFAULT_CATEGORY

    description: str = ""

    version: str = "1.0"

    author: str = ""

    #
    # Ein Icon-Pfad des Spiels ("Interface\\Icons\\..."). Leer heisst
    # "keins" und ist ein gültiger Zustand: die Zeile zeigt dann
    # nichts statt eines geratenen Symbols - dieselbe Linie wie
    # `class_icon()` in `gui/widgets/class_avatar.py`.
    #

    icon: str = ""

    #
    # Der WeakAuras-Export. Das eine Feld, ohne das der Eintrag
    # wertlos ist.
    #

    string: str = ""

    updated_at: int = 0

    #
    # Ersetzt dieser Eintrag eine mitgelieferte Aura? Wird beim
    # Anlegen aus der gemeldeten Katalogzeile übernommen und dient
    # allein der Anzeige ("ersetzt die mitgelieferte Fassung").
    #

    replaces_addon: bool = False

    #
    # `SCOPE_LOCAL` oder `SCOPE_GUILD` - siehe oben. Ein Eintrag, der
    # aus der Bibliothek des Bots stammt und hier nicht bearbeitet
    # werden darf, traegt zusätzlich `foreign = True`.
    #

    scope: str = SCOPE_LOCAL

    #
    # Wem der Eintrag in der Gildenbibliothek gehört. Leer für alles,
    # was nur hier liegt.
    #

    author_id: str = ""

    #
    # Aus der Bibliothek geholt und von jemand anderem. Solche
    # Einträge werden zugestellt, aber nicht bearbeitet - dafür ist
    # die Moderation da.
    #

    foreign: bool = False

    # --------------------------------------------------

    @property
    def shared(self) -> bool:
        return self.scope == SCOPE_GUILD

    def payload(self) -> dict:
        """
        Die Form, in der der Eintrag im Addon ankommt.

        Die Feldnamen sind hier bewusst `camelCase` und nicht die
        Python-Schreibweise: sie werden im Addon direkt gelesen
        (`modules/weakauras.lua`), und eine Umbenennung an der
        Grenze ist eine Stelle weniger, an der zwei Seiten
        auseinanderlaufen können.
        """

        data = {
            "id": self.id,
            "name": self.name,
            "category": normalize_category(self.category),
            "description": self.description,
            "version": self.version,
            "string": self.string,
            "updatedAt": int(self.updated_at or 0),
        }

        #
        # Leere Felder werden weggelassen statt als "" geschrieben.
        # Im Addon ist ein fehlendes Feld dasselbe wie ein leeres,
        # und die Nutzlast landet in einer SavedVariables-Datei, die
        # bei jedem Schreiben komplett neu geschrieben wird.
        #

        if self.author:
            data["author"] = self.author

        if self.icon:
            data["icon"] = self.icon

        #
        # Nur bei einer Gildenaura mitgeschickt. Das Addon zeichnet
        # daraus "Gilde · <Autor>" statt "Companion · <Autor>" - wer
        # eine Aura nicht selbst eingetragen hat, soll sehen, dass sie
        # aus der Bibliothek kommt und wen er zu fragen hat. Ein
        # fehlendes Feld heisst dort "vom eigenen Schreibtisch",
        # genau wie vor 2.2.0.
        #

        if self.scope == SCOPE_GUILD:
            data["scope"] = SCOPE_GUILD

        return data


def validate(aura: WeakAura, taken_ids: set[str] | None = None) -> list[str]:
    """
    Was noch fehlt, damit "Fertig" gedrückt werden darf - als Liste
    fertiger deutscher Sätze.

    Eine leere Liste heisst "vollständig". Es ist ausdrücklich keine
    Aussage darüber, ob die Aura im Spiel funktioniert; das weiss
    allein WeakAuras.
    """

    problems: list[str] = []

    if not (aura.name or "").strip():
        problems.append("Ohne Namen lässt sich die Aura im Spiel nicht ansprechen.")

    if (aura.category or "") not in CATEGORIES:
        problems.append("Es fehlt die Rubrik, unter der die Aura im Spiel steht.")

    body = clean_import_string(aura.string)

    if not body:
        problems.append("Es fehlt der WeakAuras-String.")

    elif len(body) < MIN_IMPORT_LENGTH:
        problems.append(
            "Der WeakAuras-String ist zu kurz, um ein Export zu sein - "
            "wurde er vollständig kopiert?"
        )

    if not (aura.version or "").strip():
        problems.append("Es fehlt eine Version. Sie steht im Spiel in der Zeile.")

    if taken_ids and aura.id in taken_ids:
        problems.append(
            "Diese Kennung ist schon vergeben. Beim Aktualisieren einer "
            "vorhandenen Aura ist das richtig - beim Anlegen einer neuen nicht."
        )

    return problems


def warnings(aura: WeakAura) -> list[str]:
    """
    Was auffällt, ohne das Speichern zu verhindern.

    Getrennt von `validate()`, weil beides sonst dasselbe Gewicht
    hätte: ein Hinweis, der wie ein Fehler aussieht, wird entweder
    fälschlich ernst genommen oder lehrt, Fehler zu übersehen.
    """

    notes: list[str] = []

    if aura.string and not looks_like_export(aura.string):
        notes.append(
            "Der String beginnt nicht mit \"!WA:\". Ältere "
            "WeakAuras-Versionen exportieren so - ob er sich "
            "importieren lässt, zeigt sich erst im Spiel."
        )

    if not (aura.description or "").strip():
        notes.append(
            "Ohne Beschreibung steht im Spiel nur der Name. "
            "Wer die Aura nicht selbst eingetragen hat, sieht dann "
            "nicht, was sie kann."
        )

    return notes


#
# Die Katalogmeldung aus dem Spiel
#
# Format (siehe `WeintCodex.Companion.ReportWeakAuraCatalog` im
# Addon):
#
#     <id>|<name>|<category>|<version>|<origin>;<id>|...
#
# Fehlende Felder werden hingenommen, zusätzliche ignoriert - das
# Addon darf das Format erweitern, ohne diese Seite zu brechen.
#


@dataclass
class CatalogEntry:
    """
    Eine Aura, die das Addon kennt.
    """

    id: str = ""

    name: str = ""

    category: str = DEFAULT_CATEGORY

    version: str = ""

    origin: str = ORIGIN_ADDON

    @property
    def from_addon(self) -> bool:
        """
        Kam die Zeile mit dem Addon-ZIP?

        Ausdruecklich ein Vergleich auf `ORIGIN_ADDON` und nicht
        "alles ausser companion": seit es Gildenauren gibt, meldet das
        Addon einen dritten Wert, und der ist keine mitgelieferte
        Aura. Ein fehlendes Feld gilt weiterhin als mitgeliefert -
        so meldete eine aeltere Addon-Version.
        """

        return self.origin == ORIGIN_ADDON


def parse_catalog(payload: str) -> list[CatalogEntry]:

    if not isinstance(payload, str) or not payload.strip():
        return []

    entries: list[CatalogEntry] = []

    for record in payload.split(";"):

        if not record.strip():
            continue

        fields = record.split("|")

        identifier = fields[0].strip()

        if not identifier:
            continue

        def field_at(index: int) -> str:
            return fields[index].strip() if index < len(fields) else ""

        entries.append(
            CatalogEntry(
                id=identifier,
                name=field_at(1) or identifier,
                category=normalize_category(field_at(2)),
                version=field_at(3),
                origin=field_at(4) or ORIGIN_ADDON,
            )
        )

    return entries


def aura_from_catalog(entry: CatalogEntry) -> WeakAura:
    """
    Eine gemeldete Zeile als Ausgangspunkt zum Aktualisieren.

    Der Importstring bleibt **leer**: das Addon meldet ihn nicht mit
    (er wäre ein Vielfaches der übrigen Nutzlast), und wer eine Aura
    aktualisiert, bringt ohnehin eine neue Zeichenkette mit. Ein
    geratener oder alter String wäre hier das Gegenteil einer
    Aktualisierung.
    """

    return WeakAura(
        id=entry.id,
        name=entry.name,
        category=normalize_category(entry.category),
        version=entry.version or "1.0",
        replaces_addon=entry.from_addon,
    )


def now() -> int:
    return int(time.time())
