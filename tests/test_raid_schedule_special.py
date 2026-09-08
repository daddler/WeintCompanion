"""
Der Sonderraid in der Raidübersicht - dieselbe Strecke wie ein
normaler Raid.

**Der gemeldete Fall.** Ein erstellter Sonderraid tauchte in der
Übersicht nicht auf. Die Ursache lag im Bot (`services/raid_dates.py`
drüben: das getippte Datum "17.06.2026" wurde mit `%Y-%m-%d` gelesen
und galt deshalb als unlesbar). Auf dieser Seite gab es nichts zu
reparieren - und genau deshalb steht hier ein Testlauf: er hält fest,
dass ein Sonderraid **durch denselben Datenfluss** läuft wie ein
Standardraid, damit niemand ihn später mit einem Sonderweg
"reparieren" muss.

Fünf Fragen, und alle fünf stehen so in den Abnahmekriterien:

- ein Sonderraid allein wird angezeigt,
- ein Sonderraid neben einem Standardraid wird angezeigt,
- beide zusammen erscheinen genau **einmal**,
- der Raid überlebt einen Neustart der App (Zwischenspeicher),
- und die bestehenden Filter (vorbei / bevorstehend) gelten weiter.
"""

from __future__ import annotations

import json
import types
from datetime import datetime

from core.raid_schedule import (
    day_text,
    others_text,
    parse_schedule,
)


def _moment(text: str) -> datetime:

    return datetime.fromisoformat(text)


SPECIAL_DAY = {
    "key": "special",
    "label": "Mittwoch",
    "date": "2026-06-17",
    "time": "20:00",
    "starts_at": "2026-06-17T20:00:00+02:00",
    "signups": {"active": 7, "tentative": 1, "bench": 0, "absent": 2},
    "roster": [
        {"role": "tank", "class": "WARRIOR"},
        {"role": "healer", "class": "PRIEST"},
    ],
}


SPECIAL = {
    "status": "ok",
    "raid_id": 9,
    "title": "Ordos",
    "raid_type": "special",
    "signup_status": "open",
    "raid_size": 10,
    "raid_ids": [9],
    "days": [SPECIAL_DAY],
}


def _standard_day(key, label, datum):

    return {
        "key": key,
        "label": label,
        "date": datum[:10],
        "time": "20:00",
        "starts_at": datum,
        "signups": {"active": 18, "tentative": 0, "bench": 0, "absent": 1},
    }


STANDARD_DAYS = [
    _standard_day("wednesday", "Mittwoch", "2026-06-10T20:00:00+02:00"),
    _standard_day("thursday", "Donnerstag", "2026-06-11T20:00:00+02:00"),
]


#
# --------------------------------------------------
# Ein Sonderraid allein
# --------------------------------------------------
#


def test_a_special_raid_is_drawn_like_any_other():
    """
    Kein zweiter Datentyp und kein Sonderweg: `parse_schedule()` liest
    ihn, `upcoming_days()` gibt ihn heraus, `day_text()` beschriftet
    ihn.
    """

    schedule = parse_schedule(SPECIAL)

    assert schedule.known is True
    assert schedule.raid_type == "special"
    assert schedule.title == "Ordos"

    days = schedule.upcoming_days(_moment("2026-06-10T12:00:00+02:00"))

    assert [day.key for day in days] == ["special"]

    assert days[0].active == 7
    assert len(days[0].roster) == 2

    assert "17.06." in day_text(days[0])


def test_a_special_raid_reaches_the_greeting_and_the_countdown():
    """
    `next_day()` ist die eine Stelle, aus der Kopfzeile und Countdown
    lesen. Sie muss denselben Tag nennen wie die Karte darunter.
    """

    schedule = parse_schedule(SPECIAL)

    now = _moment("2026-06-10T12:00:00+02:00")

    assert schedule.next_day(now) is schedule.upcoming_days(now)[0]

    assert schedule.next_day(now).minutes_until(now) > 0


#
# --------------------------------------------------
# Sonderraid UND Standardraid
# --------------------------------------------------
#


def _both() -> dict:
    """
    Die Antwort des Bots, wenn beide laufen: der nächste oben, der
    andere unter `others` (siehe `pick_next_schedule()` drüben).
    """

    return {
        "status": "ok",
        "raid_id": 7,
        "title": "Siege of Orgrimmar",
        "raid_type": "standard",
        "signup_status": "open",
        "raid_size": 25,
        "raid_ids": [7, 9],
        "days": list(STANDARD_DAYS),
        "others": [
            {
                "raid_id": 9,
                "title": "Ordos",
                "raid_type": "special",
                "raid_size": 10,
                "signup_status": "open",
                "days": [SPECIAL_DAY],
            }
        ],
    }


def test_both_raids_are_visible_at_once():

    schedule = parse_schedule(_both())

    assert schedule.title == "Siege of Orgrimmar"

    assert [other.title for other in schedule.others] == ["Ordos"]

    assert schedule.others[0].raid_type == "special"

    #
    # Der zweite Raid wird durch dieselbe Funktion gelesen und rechnet
    # deshalb dieselbe Restzeit - kein zweiter Datentyp daneben.
    #

    tag = schedule.others[0].next_day(_moment("2026-06-10T12:00:00+02:00"))

    assert tag is not None
    assert tag.key == "special"

    zeile = others_text(schedule, _moment("2026-06-10T12:00:00+02:00"))

    assert "Ordos" in zeile
    assert "17.06." in zeile


def test_neither_raid_appears_twice():
    """
    `all_raids()` ist die Liste, aus der die Übersicht zählt. Ein Raid,
    der zweimal darin steht, stünde auch zweimal auf der Karte.
    """

    schedule = parse_schedule(_both())

    ids = [raid.title for raid in schedule.all_raids()]

    assert ids == ["Siege of Orgrimmar", "Ordos"]
    assert len(ids) == len(set(ids))

    #
    # Und der Sonderraid trägt seinen eigenen Tag genau einmal, nicht
    # zusätzlich die Tage des Standardraids.
    #

    assert len(schedule.others[0].days) == 1


def test_the_nested_entry_carries_no_others_of_its_own():
    """
    Sonst bestimmte die Antwort des Bots, wie tief eingelesen wird -
    und ein Sonderraid stünde in jeder Ebene noch einmal.
    """

    verschachtelt = _both()

    verschachtelt["others"][0]["others"] = [dict(SPECIAL)]

    schedule = parse_schedule(verschachtelt)

    assert schedule.others[0].others == ()


#
# --------------------------------------------------
# Die bestehenden Filter
# --------------------------------------------------
#


def test_a_past_special_raid_falls_out_of_the_upcoming_days():
    """
    Der Filter "vorbei / bevorstehend" gilt für den Sonderraid genauso.
    Die Karte sagt dann, dass nichts bekannt ist - und das ist richtig:
    es gibt keinen Termin mehr zu zeigen.
    """

    schedule = parse_schedule(SPECIAL)

    assert schedule.upcoming_days(_moment("2026-06-20T12:00:00+02:00")) == ()

    assert schedule.next_day(_moment("2026-06-20T12:00:00+02:00")) is None


def test_a_running_special_raid_still_counts_as_upcoming():
    """
    Vier Stunden Nachlauf, dieselbe Regel wie beim Standardraid.
    """

    schedule = parse_schedule(SPECIAL)

    laeuft = _moment("2026-06-17T21:30:00+02:00")

    assert [day.key for day in schedule.upcoming_days(laeuft)] == ["special"]

    assert schedule.next_day(laeuft).is_running(laeuft) is True


#
# --------------------------------------------------
# Neustart der App
# --------------------------------------------------
#


class _Logger:

    def info(self, *_):
        pass

    def warning(self, *_):
        pass

    def error(self, *_):
        pass

    def success(self, *_):
        pass


class _Response:

    status_code = 200

    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def test_a_special_raid_survives_a_restart(monkeypatch, tmp_path):
    """
    Der Abruf braucht ein verknüpftes Konto und einen erreichbaren Bot.
    Ohne Zwischenspeicher stünde nach jedem Start ein paar Sekunden
    lang "kein Termin bekannt" - und offline dauerhaft.

    Geprüft wird der ganze Weg: abrufen, ablegen, ein **zweiter**
    `RaidScheduleSync` (das ist der Neustart) liest die Datei wieder
    ein und kennt denselben Sonderraid.
    """

    from core import raid_schedule_sync as module

    monkeypatch.setattr(module.Paths, "cache", staticmethod(lambda: tmp_path))

    monkeypatch.setattr(
        module.DiscordAccountStore,
        "load",
        lambda self: {"companion_token": "t"},
    )

    monkeypatch.setattr(
        module.httpx,
        "get",
        lambda url, **kwargs: _Response(_both()),
    )

    manager = types.SimpleNamespace(logger=_Logger())

    erst = module.RaidScheduleSync(manager)

    assert erst.process() is True

    assert erst.schedule.others[0].title == "Ordos"

    #
    # Was auf der Platte liegt, ist die Antwort des Bots - unverändert,
    # also auch mit dem Sonderraid darin.
    #

    abgelegt = json.loads(
        (tmp_path / module.CACHE_FILE).read_text(encoding="utf-8")
    )

    assert [o["title"] for o in abgelegt["others"]] == ["Ordos"]

    #
    # Der Neustart: dieselbe Datei, ein frisches Objekt, kein Netz.
    #

    monkeypatch.setattr(
        module.httpx,
        "get",
        lambda url, **kwargs: (_ for _ in ()).throw(
            AssertionError("beim Start darf nicht abgerufen werden")
        ),
    )

    danach = module.RaidScheduleSync(manager)

    assert danach.schedule.known is True
    assert [o.title for o in danach.schedule.others] == ["Ordos"]

    tag = danach.schedule.others[0].next_day(
        _moment("2026-06-10T12:00:00+02:00")
    )

    assert tag.key == "special"
