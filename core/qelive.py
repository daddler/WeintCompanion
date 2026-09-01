"""
QE Live - die Adresse für Heiler.

Gesimmt wird für Schadensausteiler auf wowsims.com/mop. Für Heiler ist
das die falsche Adresse: geplant wird dort questionablyepic.com/live,
kurz QE Live, und dessen "Classic" ist derzeit Mists of Pandaria. Alle
sechs MoP-Heiler sind vertreten.

WAS DIESES MODUL TRÄGT UND WAS AUSDRÜCKLICH NICHT
-------------------------------------------------

**QE Live gibt keine charakterbezogene Gewichtung heraus.** Das ist der
entscheidende Unterschied zu wowsims und der Grund, warum es hier keinen
Rückweg gibt: sein Top Gear rechnet mit einem vollständigen Heilmodell
und antwortet mit einem Ausrüstungssatz, nicht mit Zahlen je Wert. Was
es je Spezialisierung führt, sind Vorgabegewichte - dieselben für jeden
Spieler, aus dem Quelltext jener Seite.

Und es gibt **keine Adresse, die eine Ausrüstung trägt**. wowsims öffnet
man mit `?i=g` und den Gegenständen darin (`core/wowsims_link.py`); bei
QE Live geht die Ausrüstung nur über Kopieren und Einfügen. Den Text
dafür baut das Addon (`modules/qelive.lua`), und er wandert über die
Zwischenablage - eine zweite Fassung derselben Daten durch diese App
hindurch wäre genau die Kopie, die veraltet, wenn sie gebraucht wird.

Diese Seite übernimmt deshalb **den Weg, nicht die Rechnung** - dieselbe
Aufteilung wie bei wowsims, nur mit einem kürzeren Weg.

DIE ZAHLEN SIND DIESELBEN WIE IM ADDON
--------------------------------------

`SPECS` trägt die skalierten Gewichte, die `modules/qelive.lua` aus
`data/qelive.lua` errechnet ("größtes Gewicht = 100"). Wo die beiden
auseinanderlaufen, widersprechen sich Spiel und Desktop bei einer Frage,
die nur eine Antwort hat - dieselbe Auflage wie beim Parser der
Sim-Gewichte. `tests/test_qelive.py` und
`.github/tests/qelive_test.lua` drüben prüfen deshalb dieselben Zahlen.

Kein Qt, kein `httpx`, keine Datei - aus demselben Grund wie
`roster_target()` und `build_profile_payload()`: welcher Satz dasteht
ist genau die Stelle, an der etwas falsch sein kann, und ein Fenster
braucht man dafür nicht.
"""

from __future__ import annotations

from dataclasses import dataclass


URL = "https://questionablyepic.com/live/"


#
# Der Stand, auf den sich die Zahlen beziehen. Er steht auch in
# `data/qelive.lua` drüben und ist dort Teil der Vorschlagskennung.
#

STAND = "2026-09"


@dataclass(frozen=True)
class HealerSpec:
    """
    Eine Spezialisierung, die QE Live führt.
    """

    key: str

    label: str

    weights: dict[str, int]

    #
    # Werte, für die QE Live keine Zahl führt. Sie werden NICHT als 0
    # übernommen: eine 0 hiesse im Addon "egal", und der
    # Umschmiede-Planer schmiedete den Wert restlos weg. Beide Priester
    # führen Tempo mit 0, beim Disziplin-Priester steht drüben sogar ein
    # "TODO" daneben - das ist eine Lücke und keine Aussage, dieselbe
    # Linie wie `stars == 0`.
    #

    gaps: tuple[str, ...] = ()

    #
    # Von QE Live selbst als "Default (Beta)" geführt.
    #

    beta: bool = False


SPECS: tuple[HealerSpec, ...] = (

    HealerSpec(
        "DRUID_RESTORATION", "Restoration Druid",
        {"intellect": 100, "spirit": 84, "crit": 56, "haste": 58,
         "mastery": 73},
    ),

    HealerSpec(
        "PALADIN_HOLY", "Holy Paladin",
        {"intellect": 100, "spirit": 59, "crit": 55, "haste": 44,
         "mastery": 90},
        beta=True,
    ),

    HealerSpec(
        "PRIEST_DISCIPLINE", "Discipline Priest",
        {"intellect": 100, "spirit": 34, "crit": 71, "mastery": 72},
        gaps=("haste",),
    ),

    HealerSpec(
        "PRIEST_HOLY", "Holy Priest",
        {"intellect": 100, "spirit": 66, "crit": 56, "mastery": 68},
        gaps=("haste",),
    ),

    HealerSpec(
        "SHAMAN_RESTORATION", "Restoration Shaman",
        {"intellect": 100, "spirit": 36, "crit": 69, "haste": 54,
         "mastery": 57},
        beta=True,
    ),

    HealerSpec(
        "MONK_MISTWEAVER", "Mistweaver Monk",
        {"intellect": 100, "spirit": 30, "crit": 64, "haste": 24,
         "mastery": 34},
    ),

)


SPEC_BY_KEY: dict[str, HealerSpec] = {entry.key: entry for entry in SPECS}


def spec(key: str) -> HealerSpec | None:
    """
    Die Spezialisierung zu einem Profilschlüssel, oder `None`.

    Gefragt wird damit nicht "ist das ein Heiler", sondern "führt QE
    Live diese Spezialisierung". Das ist die genauere Frage und
    dieselbe Zurückhaltung wie bei `sim_url()`: ein unbekannter
    Schlüssel wird nicht geraten.
    """

    return SPEC_BY_KEY.get((key or "").strip().upper())


def is_healer(key: str) -> bool:

    return spec(key) is not None


def gap_labels(entry: HealerSpec | None) -> list[str]:
    """
    Die deutschen Namen der Werte, für die QE Live keine Zahl führt.
    """

    if entry is None:

        return []

    names = {
        "haste": "Tempowertung",
        "crit": "Kritische Trefferwertung",
        "mastery": "Meisterschaftswertung",
        "spirit": "Willenskraft",
        "hit": "Trefferwertung",
        "expertise": "Waffenkunde",
    }

    return [names.get(key, key) for key in entry.gaps]


def guidance(entry: HealerSpec | None) -> str:
    """
    Was der Spieler tun muss - in der Reihenfolge, in der er es tut.

    Der Weg ist ein anderer als bei wowsims, und der Unterschied ist
    keine Feinheit: dort öffnet ein Knopf den Sim mitsamt Ausrüstung,
    hier trägt die Zwischenablage sie. Wer das nicht weiss, sucht auf
    dieser Seite einen Knopf, den es nicht geben kann.
    """

    if entry is None:

        return ""

    return (
        "QE Live nimmt die Ausrüstung nur als eingefügten Text an - eine "
        "Adresse, die sie mitbringt, gibt es dort nicht. Im Spiel steht "
        "sie unter Charakter → Simmen zum Kopieren bereit (auch über "
        "/wc qe). Danach hier die Seite öffnen, einen Charakter dieser "
        "Spezialisierung anlegen und den Text unter Import einfügen."
    )


def weights_note(entry: HealerSpec | None) -> str:
    """
    Warum aus QE Live nichts zurückkommt - und was stattdessen gilt.

    Der Satz muss dastehen. Wer von den Schadensausteilern kommt,
    erwartet nach dem Sim eine Gewichtung und hält ihr Ausbleiben sonst
    für einen Fehler dieser App.
    """

    if entry is None:

        return ""

    text = (
        "Zurück ins Spiel kommt von dort nichts: QE Live rechnet keine "
        "Gewichtung je Charakter, sein Top Gear antwortet mit einem "
        "Ausrüstungssatz. Was es für diese Spezialisierung an Gewichten "
        "führt, liegt im Spiel unter Priorisierung als Vorschlag bereit."
    )

    labels = gap_labels(entry)

    if labels:

        text += (
            f" Für {' und '.join(labels)} führt QE Live keine Zahl - dort "
            f"bleibt es beim Wert der Spezialisierung."
        )

    if entry.beta:

        text += " Diese Spezialisierung führt QE Live selbst noch als Beta."

    return text
