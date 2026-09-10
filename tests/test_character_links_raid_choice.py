"""
Tests fuer die Raidwahl der Charakterzuordnung.

Der Fehler, den sie festhalten: liefen im Discord zwei Anmeldungen
nebeneinander (25er offen, spaeter ein 10er dazu), fragte die
Companion den Bot ohne Angabe - und ohne Angabe antwortet er zum
naechsten Raid. Der 25er war damit nicht mehr zu bearbeiten, obwohl
er offen stand.

Geprueft wird deshalb beides: dass aus dem Termin ueberhaupt eine
Auswahl entsteht (`raid_choices()`, rein), und dass der Client die
Kennung als `?raid=<id>` schickt - beziehungsweise ohne Wahl eben
nicht.
"""

from core.character_links_client import CharacterLinksClient
from core.raid_schedule import RaidChoice, parse_schedule, raid_choices


# --------------------------------------------------
# Die Auswahl aus dem Termin
# --------------------------------------------------


def payload(**overrides):

    data = {
        "status": "ok",
        "raid_id": 8,
        "title": "10er Mains",
        "raid_size": 10,
        "days": [],
        "others": [
            {
                "raid_id": 7,
                "title": "25er Twinks",
                "raid_size": 25,
                "days": [],
            },
        ],
    }

    data.update(overrides)

    return data


def test_raid_id_wird_gelesen():

    schedule = parse_schedule(payload())

    assert schedule.raid_id == 8

    assert schedule.others[0].raid_id == 7


def test_beide_laufenden_raids_stehen_zur_wahl():

    choices = raid_choices(parse_schedule(payload()))

    assert [choice.raid_id for choice in choices] == [8, 7]

    assert "25er Twinks" in choices[1].label

    #
    # Die Groesse gehoert in die Beschriftung: zwei parallele Raids
    # heissen oft gleich und unterscheiden sich genau darin.
    #

    assert "25er" in choices[1].label


def test_raid_ohne_kennung_faellt_heraus():
    """
    Aeltere Bot-Fassung: kein `raid_id`. Ein Eintrag, auf den sich
    nicht zeigen laesst, waere schlimmer als ein fehlender - er wuerde
    beim Anklicken etwas anderes laden.
    """

    choices = raid_choices(parse_schedule(payload(raid_id=None)))

    assert [choice.raid_id for choice in choices] == [7]


def test_kein_termin_keine_auswahl():

    assert raid_choices(None) == ()

    assert raid_choices(parse_schedule({"status": "idle"})) == ()


def test_wahrheitswert_ist_keine_kennung():
    """
    `True` ist in Python ein `int` - und waere hier Raid 1, den es
    wirklich geben kann.
    """

    assert parse_schedule(payload(raid_id=True)).raid_id is None


def test_beschriftung_ohne_termin_nennt_wenigstens_den_namen():

    choice = RaidChoice(raid_id=4, title="Sonderraid")

    assert choice.label == "Sonderraid"


# --------------------------------------------------
# Der Client
# --------------------------------------------------


class _Recorder:
    """Faengt die Anfrage ab, statt sie zu stellen."""

    def __init__(self):

        self.calls = []

    def request(self, method, url, **kwargs):

        self.calls.append((method, kwargs.get("params")))

        raise RuntimeError("kein Netz im Test")


def _client(monkeypatch, recorder):

    import core.character_links_client as module

    monkeypatch.setattr(module.httpx, "request", recorder.request)

    client = CharacterLinksClient(
        account_store=type(
            "Store",
            (),
            {
                "load": staticmethod(lambda: {"companion_token": "t"}),
                "note_auth_rejected": staticmethod(lambda: None),
            },
        )(),
    )

    return client


def test_gewaehlter_raid_reist_als_parameter(monkeypatch):

    recorder = _Recorder()

    _client(monkeypatch, recorder).fetch(7)

    assert recorder.calls == [("GET", {"raid": 7})]


def test_ohne_wahl_wird_kein_parameter_geschickt(monkeypatch):
    """
    Ohne Angabe antwortet der Bot zum naechsten Raid - genau das
    Verhalten von vorher. Eine `0` waere dagegen eine Auswahl, die
    keinen Raid trifft.
    """

    recorder = _Recorder()

    _client(monkeypatch, recorder).fetch(None)

    assert recorder.calls == [("GET", None)]
