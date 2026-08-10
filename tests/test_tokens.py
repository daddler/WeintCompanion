"""
Die Design-Tokens sind die einzige Stelle, an der ein Farbwert steht -
und damit die Stelle, an der eine Lücke am unauffälligsten wäre.

Alles hier prüfbare kommt ohne Qt aus: `gui/theme/tokens.py` importiert
bewusst kein PySide6, damit genau das möglich bleibt (dieselbe Trennung
wie bei `analyzer/`).
"""

from gui.theme import tokens


def test_every_accent_is_complete():
    """
    Eine Akzentvariante ohne `onBase` färbt den Text auf dem
    Hauptknopf nicht - er stünde in der Vordergrundfarbe auf einer
    hellen Fläche und wäre unlesbar.
    """

    for name, accent in tokens.ACCENTS.items():

        assert set(accent) == {"base", "light", "onBase"}, name

        for key, value in accent.items():

            assert value.startswith("#"), (name, key)

            tokens.rgb(value)


def test_every_accent_has_a_pressed_and_hover_state():

    for name in tokens.ACCENTS:

        assert name in tokens.ACCENT_PRESSED

        assert name in tokens.ACCENT_HOVER

        assert len(tokens.ACCENT_HOVER[name]) == 2


def test_default_accent_exists():

    assert tokens.ACCENT_DEFAULT in tokens.ACCENTS


def test_unknown_accent_falls_back_instead_of_failing():
    """
    `config.json` ist eine Datei, die von Hand bearbeitet werden kann.
    Ein Tippfehler darf die Oberfläche nicht farblos machen.
    """

    assert tokens.accent("gibtsnicht") == tokens.ACCENTS[tokens.ACCENT_DEFAULT]

    assert tokens.accent(None) == tokens.ACCENTS[tokens.ACCENT_DEFAULT]


def test_both_densities_carry_the_same_keys():
    """
    Ein Schlüssel, den nur eine der beiden Dichten kennt, fällt erst
    auf, wenn jemand umschaltet - und dann als KeyError mitten im
    Aufbau einer Seite.
    """

    comfortable = set(tokens.DENSITY["comfortable"])

    compact = set(tokens.DENSITY["compact"])

    assert comfortable == compact


def test_compact_is_never_larger_than_comfortable():

    for key, value in tokens.DENSITY["comfortable"].items():

        assert tokens.DENSITY["compact"][key] <= value, key


def test_state_colors_are_complete_and_empty_is_none():
    """
    `empty` ist absichtlich None: ein leerer Statuspunkt wird nur als
    Kontur gezeichnet. Ein grauer gefüllter Punkt sähe aus wie ein
    eigener Zustand - gemeint ist aber "keine Angabe".
    """

    assert tokens.STATE["empty"] is None

    for key in ("ok", "warn", "error", "live", "info"):

        assert tokens.STATE[key].startswith("#")


def test_tinted_colors_use_fractional_alpha():
    """
    Qt liest in `rgba()` eine Ganzzahl als 0-255 und eine
    Fließkommazahl als Anteil. `tint()` muss deshalb immer einen
    Dezimalpunkt schreiben - "rgba(255,255,255,0)" wäre unsichtbar
    statt zu 0 % gedeckt, und schlimmer: "rgba(255,255,255,1)" wäre
    fast unsichtbar statt deckend.
    """

    value = tokens.tint("#FFFFFF", 1.0)

    assert value == "rgba(255,255,255,1.000)"

    assert "." in tokens.tint("#D4A24A", tokens.TINT_BORDER)


def test_rgb_accepts_short_form_and_rejects_nonsense():

    assert tokens.rgb("#FFF") == (255, 255, 255)

    assert tokens.rgb("0A0A0C") == (10, 10, 12)

    for bad in ("#12345", "", "#GGGGGG"):

        try:
            tokens.rgb(bad)

        except ValueError:
            continue

        raise AssertionError(f"{bad!r} haette abgelehnt werden muessen")


def test_mix_stays_within_the_two_colors():

    assert tokens.mix("#FFFFFF", "#000000", 0.0) == "#000000"

    assert tokens.mix("#FFFFFF", "#000000", 1.0) == "#FFFFFF"

    assert tokens.mix("#FFFFFF", "#000000", 0.5) == "#808080"


def test_typography_covers_every_role_used_by_the_design():

    for name in (
        "title",
        "section",
        "card",
        "body",
        "small",
        "mono",
        "monoBig",
        "eyebrow",
        "micro",
    ):

        assert name in tokens.TYPE


def test_only_the_small_mono_roles_are_letterspaced():
    """
    Die weite Laufweite ist das Kennzeichen der Rubriklabels. Sie
    versehentlich auf den Fließtext zu setzen, würde die ganze
    Oberfläche auseinanderziehen.
    """

    spaced = {
        name
        for name, token in tokens.TYPE.items()
        if token.letter_spacing > 0
    }

    assert spaced == {"eyebrow", "micro"}


def test_the_window_minimum_is_not_larger_than_the_design_size():

    assert tokens.WINDOW_MIN[0] <= tokens.WINDOW_DEFAULT[0]

    assert tokens.WINDOW_MIN[1] <= tokens.WINDOW_DEFAULT[1]
