"""
Die Aufstellungskarte der Übersicht - beide Raidtage.

Der Standardraid läuft Mittwoch **und** Donnerstag, und das sind zwei
Anmeldungen: wer am Mittwoch zusagt, muss am Donnerstag nicht können.
Die Karte zeigte bis 2.3.3 nur den nächsten Termin, also am Dienstag
den Mittwoch - ob der Donnerstag überhaupt Leute hatte, war in der
App nicht zu sehen, obwohl der Bot beide Tage in derselben Antwort
schickt.

Sie baut Widgets und braucht deshalb Qt. Geprüft wird, was auf dem
Bildschirm steht: welche Zeilen sichtbar sind und welche Zahl bei
welchem Tag - eine gemeinsame Zahl für beide Tage wäre der Fehler,
den es hier zu verhindern gilt.
"""

import os

import pytest

pytest.importorskip("PySide6")


def _app():

    from PySide6.QtWidgets import QApplication

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    app = QApplication.instance()

    if app is None:
        app = QApplication([])

    return app


class _Config:

    def __init__(self):
        self.data = {}

    def save(self):
        pass


@pytest.fixture(autouse=True)
def _theme():

    _app()

    from gui.theme.theme_manager import init_theme

    init_theme(_Config())


def _tag(key, label, starts_at, active, roster=None):

    entry = {
        "key": key,
        "label": label,
        "starts_at": starts_at,
        "signups": {
            "active": active,
            "tentative": 0,
            "bench": 0,
            "absent": 0,
        },
    }

    if roster is not None:
        entry["roster"] = roster

    return entry


STANDARD = {
    "status": "ok",
    "raid_id": 7,
    "title": "Siege of Orgrimmar",
    "raid_type": "standard",
    "signup_status": "open",
    "raid_size": 25,
    "days": [
        _tag(
            "wednesday",
            "Mittwoch",
            "2026-08-12T20:00:00+02:00",
            3,
            [
                {"role": "tank", "class": "WARRIOR"},
                {"role": "healer", "class": "PRIEST"},
                {"role": "dps", "class": "MAGE"},
            ],
        ),
        _tag(
            "thursday",
            "Donnerstag",
            "2026-08-13T20:00:00+02:00",
            1,
            [{"role": "tank", "class": "MONK"}],
        ),
    ],
}


def _card(payload, now="2026-08-11T18:30:00+02:00"):

    from datetime import datetime

    from core.raid_schedule import parse_schedule

    from gui.pages.overview import RosterCard

    schedule = parse_schedule(payload)

    card = RosterCard()

    card.resize(900, card.height())

    card.apply(schedule, schedule.upcoming_days(datetime.fromisoformat(now)))

    return card


def _visible(card):

    return [block for block in card._blocks if block.isVisibleTo(card)]


# --------------------------------------------------


def test_both_days_stand_below_each_other():

    card = _card(STANDARD)

    blocks = _visible(card)

    assert len(blocks) == 2

    assert blocks[0].when.text().startswith("Mittwoch")

    assert blocks[1].when.text().startswith("Donnerstag")


def test_every_day_carries_its_own_number_and_its_own_strip():
    """
    Der eigentliche Punkt. Eine gemeinsame Zahl im Kopf der Karte
    liesse den Donnerstag hinter dem Mittwoch verschwinden - und genau
    dessen leere Plätze sind der Grund, überhaupt nachzusehen.
    """

    card = _card(STANDARD)

    mittwoch, donnerstag = _visible(card)

    assert mittwoch.count.text() == "3 / 25 zugesagt"

    assert donnerstag.count.text() == "1 / 25 zugesagt"

    assert [len(group.filled) for group in mittwoch.strip.groups()] == [
        1, 1, 1, 0,
    ]

    assert [len(group.filled) for group in donnerstag.strip.groups()] == [
        1, 0,
    ]

    #
    # Und die Zahl steht nicht mehr im Kopf: dort gehört sie nur hin,
    # solange es einen einzigen Termin gibt.
    #

    assert not hasattr(card, "count")


def test_a_special_raid_shows_the_one_block_it_has():

    card = _card({
        "status": "ok",
        "raid_id": 9,
        "title": "Ordos",
        "raid_type": "special",
        "signup_status": "open",
        "raid_size": 10,
        "days": [_tag("special", "Samstag", "2026-08-15T19:30:00+02:00", 7)],
    })

    blocks = _visible(card)

    assert len(blocks) == 1

    assert blocks[0].when.text().startswith("Samstag")


def test_a_closed_signup_is_said_once_and_not_per_day():
    """
    Die Anmeldung wird für den **Raid** geschlossen, nicht für einen
    seiner Tage. Zweimal untereinander gelesen sähe es aus wie zwei
    verschiedene Auskünfte.
    """

    payload = dict(STANDARD, signup_status="locked")

    card = _card(payload)

    assert card.status.isVisibleTo(card)

    assert card.status.text() == "Anmeldung geschlossen"

    for block in _visible(card):
        assert "geschlossen" not in block.note.text()


def test_without_a_raid_the_card_says_so_instead_of_showing_zero_days():

    card = _card({"status": "idle", "detail": "Kein aktiver Raid."})

    assert _visible(card) == []

    assert not card.title.isVisibleTo(card)

    assert card.explanation.isVisibleTo(card)

    assert not card.status.isVisibleTo(card)


def test_the_blocks_are_reused_rather_than_rebuilt():
    """
    `refresh()` läuft bei jedem Seitenwechsel und bei jeder
    abgeschlossenen Hintergrundprüfung. Ein Widget je Durchgang neu zu
    bauen kostet Layout für ein Bild, das gleich bleibt - dieselbe
    Regel wie bei den Zeilen unter `gui/widgets/tv/`.
    """

    from datetime import datetime

    from core.raid_schedule import parse_schedule

    card = _card(STANDARD)

    zuerst = list(card._blocks)

    schedule = parse_schedule(STANDARD)

    for _ in range(3):

        card.apply(
            schedule,
            schedule.upcoming_days(
                datetime.fromisoformat("2026-08-11T18:30:00+02:00")
            ),
        )

    assert card._blocks == zuerst


def test_a_shorter_answer_hides_the_leftover_block():
    """
    Nach dem Mittwoch bleibt ein Tag übrig. Der zweite Block wird
    versteckt und nicht weggeworfen - stehen bleiben darf er nicht,
    sonst zeigte die Karte einen Termin, den es nicht mehr gibt.
    """

    from datetime import datetime

    from core.raid_schedule import parse_schedule

    card = _card(STANDARD)

    assert len(_visible(card)) == 2

    schedule = parse_schedule(STANDARD)

    card.apply(
        schedule,
        schedule.upcoming_days(
            datetime.fromisoformat("2026-08-13T09:00:00+02:00")
        ),
    )

    blocks = _visible(card)

    assert len(blocks) == 1

    assert blocks[0].when.text().startswith("Donnerstag")

    assert len(card._blocks) == 2
