"""
Der Raidtermin der Übersicht - Einlesen, Restzeit, Beschriftung.

Ohne Qt und ohne Netz, wie der Rest von `core/raid_schedule.py`. Die
Uhr wird übergeben; ein Test, der die echte liest, ist am Mittwoch
abend ein anderer als am Montag.
"""

from datetime import datetime

from core.raid_schedule import (
    OWN_STATES,
    composition_text,
    count_text,
    countdown_text,
    day_text,
    open_slots,
    others_text,
    own_signup_label,
    own_signup_text,
    own_signup_variant,
    parse_schedule,
    signup_text,
)


def _moment(text: str) -> datetime:

    return datetime.fromisoformat(text)


PAYLOAD = {
    "status": "ok",
    "raid_id": 7,
    "title": "Siege of Orgrimmar",
    "raid_type": "standard",
    "signup_status": "open",
    "raid_size": 25,
    "timezone": "Europe/Berlin",
    "days": [
        {
            "key": "wednesday",
            "label": "Mittwoch",
            "date": "2026-08-12",
            "time": "20:00",
            "starts_at": "2026-08-12T20:00:00+02:00",
            "signups": {
                "active": 18,
                "tentative": 2,
                "bench": 1,
                "absent": 3,
            },
        },
        {
            "key": "thursday",
            "label": "Donnerstag",
            "date": "2026-08-13",
            "time": "20:00",
            "starts_at": "2026-08-13T20:00:00+02:00",
            "signups": {
                "active": 20,
                "tentative": 0,
                "bench": 0,
                "absent": 2,
            },
        },
    ],
}


def test_idle_is_not_a_schedule():
    """
    "Kein Raid" muss von "Raid, aber noch nichts geladen" nicht
    unterscheidbar sein - beide Male ist nichts bekannt, und die
    Übersicht sagt genau das.
    """

    schedule = parse_schedule(
        {"status": "idle", "detail": "Kein aktiver Raid."}
    )

    assert not schedule.known
    assert schedule.next_day() is None
    assert countdown_text(None) == "KEIN TERMIN BEKANNT"


def test_garbage_does_not_raise():

    for value in (None, [], "nein", {}, {"status": "ok"}):
        parse_schedule(value)


def test_the_next_day_is_the_first_one_still_ahead():

    schedule = parse_schedule(PAYLOAD)

    assert schedule.known
    assert schedule.title == "Siege of Orgrimmar"
    assert schedule.raid_size == 25

    day = schedule.next_day(_moment("2026-08-11T18:30:00+02:00"))

    assert day.key == "wednesday"

    #
    # Nach dem Mittwoch zeigt die Übersicht den Donnerstag, nicht den
    # Mittwoch der nächsten Woche - der steht so gar nicht in der
    # Antwort, und genau deshalb sortiert `next_day()` selbst.
    #

    later = schedule.next_day(_moment("2026-08-13T09:00:00+02:00"))

    assert later.key == "thursday"


def test_a_running_raid_is_the_next_one_and_says_so():

    schedule = parse_schedule(PAYLOAD)

    now = _moment("2026-08-12T21:00:00+02:00")

    day = schedule.next_day(now)

    assert day.key == "wednesday"
    assert day.is_running(now)
    assert countdown_text(day, now) == "RAID LÄUFT"


def test_every_day_behind_us_means_no_termin():
    """
    Alle Termine vorbei: der Chip fällt auf "kein Termin bekannt"
    zurück, statt eine negative Restzeit anzuzeigen.
    """

    schedule = parse_schedule(PAYLOAD)

    now = _moment("2026-08-20T12:00:00+02:00")

    assert schedule.next_day(now) is None
    assert countdown_text(schedule.next_day(now), now) == (
        "KEIN TERMIN BEKANNT"
    )


def test_countdown_is_coarse_by_design():

    schedule = parse_schedule(PAYLOAD)

    day = schedule.days[0]

    cases = {
        "2026-08-12T19:45:00+02:00": "IN 15 MIN",
        "2026-08-12T17:00:00+02:00": "IN 3 STD",
        "2026-08-12T16:30:00+02:00": "IN 3 STD 30 MIN",
        "2026-08-11T20:00:00+02:00": "IN 1 T",
        "2026-08-10T18:00:00+02:00": "IN 2 T 2 STD",
    }

    for stamp, expected in cases.items():
        assert countdown_text(day, _moment(stamp)) == expected


def test_labels_read_like_a_sentence():

    schedule = parse_schedule(PAYLOAD)

    day = schedule.days[0]

    assert day_text(day) == "Mittwoch, 12.08. um 20:00 Uhr"

    assert signup_text(day, 25) == (
        "18 von 25 zugesagt · 2 vielleicht · 1 Ersatzbank"
    )

    #
    # Ohne bekannte Raidgröße kein "von 25" - eine erfundene
    # Obergrenze ließe die Zusagen knapp oder üppig aussehen.
    #

    assert signup_text(day, 0) == (
        "18 zugesagt · 2 vielleicht · 1 Ersatzbank"
    )

    assert signup_text(schedule.days[1], 25) == "20 von 25 zugesagt"


def test_a_day_without_a_timestamp_is_not_a_day():
    """
    Ein Termin ohne lesbaren Zeitpunkt zählt nicht als der nächste -
    sonst stünde in der Übersicht ein Titel ohne Datum, und der Chip
    rechnete gegen nichts.
    """

    schedule = parse_schedule({
        "status": "ok",
        "title": "Ordos",
        "raid_size": 10,
        "days": [
            {
                "key": "special",
                "label": "Samstag",
                "starts_at": "",
                "signups": {"active": 4},
            }
        ],
    })

    assert schedule.known
    assert schedule.next_day() is None
    assert schedule.days[0].active == 4


# --------------------------------------------------
# Wo die Anmeldung steht
# --------------------------------------------------


def test_the_signup_location_is_read_as_strings():
    """
    Der `discord`-Block nennt Gilde, Kanal und Nachricht der
    Anmeldung. Jede Kennung als Zeichenkette - aus `1.23e+18` wird
    nie wieder ein Link.
    """

    schedule = parse_schedule({
        **PAYLOAD,
        "discord": {
            "guild_id": 1311060525555257364,
            "channel_id": "1311325324008751225",
            "message_id": "  1400000000000000000  ",
        },
    })

    assert schedule.signup == {
        "guild_id": "1311060525555257364",
        "channel_id": "1311325324008751225",
        "message_id": "1400000000000000000",
    }


def test_an_older_bot_reports_no_location():
    """
    Kein Block, kein Fundort - und nichts Zusammengesetztes, das wie
    eine Adresse aussieht. Die Übersicht hat dafür ihren eigenen
    Rückfall.
    """

    assert parse_schedule(PAYLOAD).signup == {}

    for broken in ("", [], {"channel_id": ""}, {"channel_id": None}):

        assert parse_schedule({**PAYLOAD, "discord": broken}).signup == {}


# --------------------------------------------------
# Die Aufstellung
# --------------------------------------------------


def _with_roster(**extra):

    day = dict(PAYLOAD["days"][0])

    day["roster"] = (
        [{"role": "tank", "class": "Warrior"}] * 2
        + [{"role": "healer", "class": "Priest"}] * 5
        + [{"role": "dps", "class": "Mage"}] * 14
    )

    day["signups"] = {"active": 21, "tentative": 2, "bench": 1}

    return parse_schedule({
        **PAYLOAD,
        "days": [day],
        **extra,
    })


def test_the_roster_carries_roles_and_classes_but_no_names():
    """
    Die Grenze des Vertrags: Rolle und Klasse ja, Name nein. Ein
    Namensfeld hier würde eine rollengeschützte Auskunft in eine
    ungeschützte verschieben.
    """

    day = _with_roster().days[0]

    assert day.has_roles()

    assert day.role_counts() == {"tank": 2, "healer": 5, "dps": 14}

    assert day.roster[0].class_name == "Warrior"

    assert not hasattr(day.roster[0], "name")


def test_an_older_bot_reports_no_roles_and_nothing_is_guessed():
    """
    Ohne den Block bleibt die Zusammensetzung unbekannt - und wird
    nicht aus der Gesamtzahl geschätzt. Drei geraten Reihen wären in
    der Anzeige von drei gemeldeten nicht zu unterscheiden.
    """

    day = parse_schedule(PAYLOAD).days[0]

    assert day.roster == ()

    assert not day.has_roles()

    assert day.role_counts() == {"tank": 0, "healer": 0, "dps": 0}


def test_bare_role_counts_are_enough_for_the_bars():
    """
    Die billigere der beiden Formen: nur Zahlen je Rolle, keine
    Klassen. Die Aufstellung stimmt dann, nur die Farbe fehlt.
    """

    day = dict(PAYLOAD["days"][0])

    day["signups"] = {
        "active": 21,
        "roles": {"tank": 2, "heiler": 5, "damage": 14},
    }

    parsed = parse_schedule({**PAYLOAD, "days": [day]}).days[0]

    assert parsed.role_counts() == {"tank": 2, "healer": 5, "dps": 14}

    assert all(not slot.class_name for slot in parsed.roster)


def test_an_unknown_role_is_dropped_rather_than_filed_as_damage():
    """
    Eine falsche Rolle ist schlechter als eine fehlende: sie gibt sich
    nicht als Lücke zu erkennen.
    """

    day = dict(PAYLOAD["days"][0])

    day["roster"] = [
        {"role": "tank", "class": "Warrior"},
        {"role": "Buffbot", "class": "Mage"},
        {"role": "", "class": "Mage"},
    ]

    parsed = parse_schedule({**PAYLOAD, "days": [day]}).days[0]

    assert parsed.role_counts() == {"tank": 1, "healer": 0, "dps": 0}


def test_what_is_missing_needs_a_target_to_compare_against():
    """
    Ohne gemeldete Sollstärke bleibt es bei "vier offene Plätze" -
    welche es sind, weiß nur, wer das Soll kennt. Ein geratenes Soll
    (2 Tanks, 5 Heiler) wäre für die halbe Gilde falsch.
    """

    schedule = _with_roster()

    day = schedule.days[0]

    total, missing, free = open_slots(schedule, day)

    assert (total, missing, free) == (4, {}, 4)

    assert composition_text(schedule, day) == "Vier offene Plätze"

    #
    # Mit Soll wird daraus eine Ansage.
    #

    schedule = _with_roster(
        composition={"tank": 2, "healer": 6, "dps": 17},
    )

    day = schedule.days[0]

    total, missing, free = open_slots(schedule, day)

    assert total == 4

    assert missing == {"healer": 1, "dps": 3}

    assert free == 0

    assert composition_text(schedule, day) == (
        "Vier offene Plätze · 1 Heiler, 3 Schaden"
    )


def test_the_rest_is_free_rather_than_forced_into_a_role():
    """
    Die Sollstärke sagt, wie viele Heiler gebraucht werden, nicht wie
    der letzte Platz zu besetzen ist.
    """

    schedule = _with_roster(
        composition={"tank": 2, "healer": 6, "dps": 15},
    )

    day = schedule.days[0]

    total, missing, free = open_slots(schedule, day)

    assert (total, missing, free) == (4, {"healer": 1, "dps": 1}, 2)

    assert composition_text(schedule, day) == (
        "Vier offene Plätze · 1 Heiler, 1 Schaden, 2 frei wählbar"
    )


def test_a_full_raid_says_so_and_a_single_slot_is_singular():

    day = dict(PAYLOAD["days"][0])

    day["signups"] = {"active": 25}

    schedule = parse_schedule({**PAYLOAD, "days": [day]})

    assert composition_text(schedule, schedule.days[0]) == (
        "Die Aufstellung ist vollständig."
    )

    day["signups"] = {"active": 24}

    schedule = parse_schedule({**PAYLOAD, "days": [day]})

    assert composition_text(schedule, schedule.days[0]) == (
        "Ein offener Platz"
    )


def test_full_and_wrongly_composed_is_not_called_complete():
    """
    Fünfundzwanzig Zusagen, darunter kein zweiter Tank:
    "vollständig" wäre die bequeme Antwort und die einzige, die der
    Raidleitung nichts nützt.
    """

    day = dict(PAYLOAD["days"][0])

    day["signups"] = {"active": 25}

    day["roster"] = (
        [{"role": "tank", "class": "Warrior"}]
        + [{"role": "healer", "class": "Priest"}] * 6
        + [{"role": "dps", "class": "Mage"}] * 18
    )

    schedule = parse_schedule({
        **PAYLOAD,
        "days": [day],
        "composition": {"tank": 2, "healer": 6, "dps": 17},
    })

    assert composition_text(schedule, schedule.days[0]) == (
        "Voll besetzt · 1 Tank fehlt noch"
    )


def test_without_a_raid_size_nothing_is_said_about_open_slots():
    """
    Dieselbe Regel wie bei `signup_text()`: eine erfundene Obergrenze
    ließe die Zusagen knapp oder üppig aussehen.
    """

    schedule = parse_schedule({
        **PAYLOAD,
        "raid_size": 0,
    })

    day = schedule.days[0]

    assert open_slots(schedule, day) == (0, {}, 0)

    assert composition_text(schedule, day) == ""

    assert count_text(day, 0) == "18 zugesagt"

    assert count_text(day, 25) == "18 / 25 zugesagt"


def test_a_broken_composition_costs_nothing():

    for broken in (None, [], "nein", {"tank": "zwei"}, {"buffbot": 3}):

        schedule = parse_schedule({**PAYLOAD, "composition": broken})

        assert schedule.composition == {}


def test_a_signup_that_is_gone_is_not_a_raid():
    """
    Der Bot antwortet "idle", sobald die Anmeldenachricht im Kanal
    fehlt - bis 2.0.2 nannte die Übersicht einen längst gelöschten
    Testraid nach jedem Neustart wieder als nächsten Termin.
    """

    schedule = parse_schedule({
        "status": "idle",
        "detail": "Zu diesem Raid gibt es im Anmelde-Kanal keine Nachricht mehr.",
    })

    assert not schedule.known

    assert schedule.next_day() is None

    assert "Anmelde-Kanal" in schedule.detail


# --------------------------------------------------
# Mehrere Raids gleichzeitig
# --------------------------------------------------
#
# Im Discord dürfen seit Bot-Seite 2.0.11 mehrere Anmeldungen
# nebeneinander laufen. Die Übersicht hat genau einen Termin-Platz -
# dort steht weiter der nächste, die übrigen kommen als `others`
# hinterher. Ohne diese Zeile wäre ein zweiter Raid in der App
# unsichtbar: man sähe nicht, dass man sich noch woanders eintragen
# kann.


WEITERER = {
    "raid_id": 8,
    "title": "25er Twinks",
    "raid_type": "standard",
    "signup_status": "locked",
    "raid_size": 25,
    "days": [
        {
            "key": "thursday",
            "label": "Donnerstag",
            "starts_at": "2026-08-13T20:00:00+02:00",
            "signups": {"active": 20, "tentative": 0, "bench": 0, "absent": 2},
        }
    ],
}


def test_ein_einzelner_raid_hat_keine_weiteren():
    """Der Normalfall - und der Zustand bei einer älteren Bot-Fassung."""

    schedule = parse_schedule(PAYLOAD)

    assert schedule.others == ()

    assert others_text(schedule) == ""

    assert [r.title for r in schedule.all_raids()] == ["Siege of Orgrimmar"]


def test_weitere_raids_werden_vollstaendig_gelesen():

    schedule = parse_schedule({**PAYLOAD, "others": [WEITERER]})

    assert len(schedule.others) == 1

    weiterer = schedule.others[0]

    #
    # Derselbe Datentyp wie der Hauptraid, also auch dieselben
    # Rechnungen - ein zweiter Typ würde irgendwann anders rechnen.
    #

    assert weiterer.known

    assert weiterer.title == "25er Twinks"

    assert weiterer.raid_size == 25

    assert weiterer.signup_status == "locked"

    # Die Uhr wird übergeben - sonst hinge der Test am Kalender.
    jetzt = _moment("2026-08-10T12:00:00+02:00")

    assert weiterer.next_day(jetzt) is not None

    assert weiterer.next_day(jetzt).active == 20


def test_der_hauptraid_bleibt_unberuehrt():
    """
    Die übrigen Raids dürfen an der Auskunft über den nächsten nichts
    ändern - sie stehen daneben, nicht darin.
    """

    ohne = parse_schedule(PAYLOAD)

    mit = parse_schedule({**PAYLOAD, "others": [WEITERER]})

    assert mit.title == ohne.title

    assert mit.raid_size == ohne.raid_size

    assert mit.days == ohne.days

    assert mit.next_day(_moment("2026-08-10T12:00:00+02:00")) == ohne.next_day(
        _moment("2026-08-10T12:00:00+02:00")
    )


def test_die_zeile_nennt_namen_und_termin():

    schedule = parse_schedule({**PAYLOAD, "others": [WEITERER]})

    zeile = others_text(schedule, _moment("2026-08-10T12:00:00+02:00"))

    assert zeile.startswith("Außerdem offen:")

    assert "25er Twinks" in zeile

    assert "Donnerstag" in zeile


def test_ein_raid_ohne_lesbaren_termin_steht_trotzdem_da():
    """
    Der Bot sortiert ihn ans Ende, weil sein Datum unlesbar ist - den
    Raid gibt es aber. "Es läuft noch etwas, dessen Termin ich nicht
    kenne" ist eine bessere Auskunft als Schweigen.
    """

    schedule = parse_schedule({
        **PAYLOAD,
        "others": [{"raid_id": 9, "title": "Sonderraid", "days": []}],
    })

    assert len(schedule.others) == 1

    zeile = others_text(schedule, _moment("2026-08-10T12:00:00+02:00"))

    assert "Sonderraid" in zeile


def test_kaputte_eintraege_kosten_nur_sich_selbst():

    for kaputt in (None, "nein", 5, {}, [1, 2]):

        schedule = parse_schedule({**PAYLOAD, "others": kaputt})

        assert schedule.title == "Siege of Orgrimmar"

        assert schedule.others == ()


def test_ohne_raid_gibt_es_auch_keine_weiteren():

    schedule = parse_schedule({"status": "idle", "detail": "Kein aktiver Raid."})

    assert schedule.others == ()

    assert schedule.all_raids() == ()

    assert others_text(schedule) == ""


def test_eine_verschachtelte_antwort_wird_nicht_weiterverfolgt():
    """
    Der Bot schickt `others` im verschachtelten Eintrag nicht. Läse die
    Companion es trotzdem, bestimmte die Antwort die Rekursionstiefe.
    """

    schedule = parse_schedule({
        **PAYLOAD,
        "others": [{**WEITERER, "others": [WEITERER, WEITERER]}],
    })

    assert len(schedule.others) == 1

    assert schedule.others[0].others == ()


#
# =========================
# Beide Raidtage
# =========================
#


def test_both_raid_days_are_upcoming_before_the_raid():
    """
    Mittwoch **und** Donnerstag sind zwei Anmeldungen: wer am Mittwoch
    zusagt, muss am Donnerstag nicht können. Die Übersicht zeigt
    deshalb beide - vorher nannte sie am Dienstag nur den Mittwoch,
    und ob der Donnerstag überhaupt Leute hatte, war in der App nicht
    zu sehen, obwohl es in derselben Antwort stand.
    """

    schedule = parse_schedule(PAYLOAD)

    days = schedule.upcoming_days(_moment("2026-08-11T18:30:00+02:00"))

    assert [day.key for day in days] == ["wednesday", "thursday"]

    #
    # Jeder Tag trägt seine eigenen Zahlen - genau das ist der Grund,
    # sie überhaupt getrennt zu zeigen.
    #

    assert [day.active for day in days] == [18, 20]


def test_the_running_day_stays_in_the_list():
    """
    Mittwoch 21:00: der Raid läuft. Er verschwindet nicht aus der
    Liste, sonst stünde mitten im Raid nur noch der Donnerstag da.
    """

    schedule = parse_schedule(PAYLOAD)

    days = schedule.upcoming_days(_moment("2026-08-12T21:00:00+02:00"))

    assert [day.key for day in days] == ["wednesday", "thursday"]


def test_a_day_already_behind_us_does_not_come_back_a_week_later():
    """
    Die Falle an dieser Stelle. Der Bot nennt zu jedem Wochentag
    dessen **nächstes Vorkommen**; am Donnerstag steht der Mittwoch
    derselben Antwort deshalb bereits auf der kommenden Woche - mit
    den Zusagen der vergangenen, denn die Anmeldung ist dieselbe.

    Neben dem heutigen Donnerstag wäre das eine Aufstellung zu einem
    Datum, zu dem sie nicht gehört. Solange nur der nächste Termin
    angezeigt wurde, fiel es nicht auf; untereinander schon.
    """

    payload = dict(PAYLOAD)

    payload["days"] = [
        dict(
            PAYLOAD["days"][1],
        ),
        #
        # Der Mittwoch, wie der Bot ihn am Donnerstag schickt: eine
        # Woche weiter, die Zahlen unverändert.
        #
        dict(
            PAYLOAD["days"][0],
            date="2026-08-19",
            starts_at="2026-08-19T20:00:00+02:00",
        ),
    ]

    schedule = parse_schedule(payload)

    days = schedule.upcoming_days(_moment("2026-08-13T09:00:00+02:00"))

    assert [day.key for day in days] == ["thursday"]


def test_after_the_raid_week_both_days_are_ahead_again():
    """
    Freitag: beide Termine liegen wieder vor uns, einen Tag
    auseinander - der Schnitt aus dem Test darüber darf hier nichts
    wegnehmen.
    """

    payload = dict(PAYLOAD)

    payload["days"] = [
        dict(
            PAYLOAD["days"][0],
            date="2026-08-19",
            starts_at="2026-08-19T20:00:00+02:00",
        ),
        dict(
            PAYLOAD["days"][1],
            date="2026-08-20",
            starts_at="2026-08-20T20:00:00+02:00",
        ),
    ]

    schedule = parse_schedule(payload)

    days = schedule.upcoming_days(_moment("2026-08-14T12:00:00+02:00"))

    assert [day.key for day in days] == ["wednesday", "thursday"]


def test_the_next_day_is_the_first_of_the_upcoming_ones():
    """
    Countdown und Begrüßung haben genau einen Platz. Sie dürfen einen
    anderen Tag nennen als die Karte darunter zeigt - deshalb rechnet
    `next_day()` nicht selbst, sondern nimmt den ersten.
    """

    schedule = parse_schedule(PAYLOAD)

    for text in (
        "2026-08-11T18:30:00+02:00",
        "2026-08-12T21:00:00+02:00",
        "2026-08-13T09:00:00+02:00",
        "2026-08-20T12:00:00+02:00",
    ):

        now = _moment(text)

        days = schedule.upcoming_days(now)

        assert schedule.next_day(now) == (days[0] if days else None)


def test_a_special_raid_has_exactly_one_day():

    schedule = parse_schedule({
        "status": "ok",
        "raid_id": 9,
        "title": "Ordos",
        "raid_type": "special",
        "signup_status": "open",
        "raid_size": 10,
        "days": [{
            "key": "special",
            "label": "Samstag",
            "starts_at": "2026-08-15T19:30:00+02:00",
            "signups": {"active": 7, "tentative": 1, "bench": 0, "absent": 2},
        }],
    })

    days = schedule.upcoming_days(_moment("2026-08-11T12:00:00+02:00"))

    assert [day.key for day in days] == ["special"]


# --------------------------------------------------
# Die eigene Anmeldung
# --------------------------------------------------
#
# "21 von 25 zugesagt" beantwortet nicht, ob man selbst dabei ist -
# die Antwort des Bots nennt keine Namen, es ist aus ihr also gar
# nicht zu erkennen, wer von den 21 man ist. Der Bot schickt es
# deshalb je Tag als `days[].me`.
#


def _with_me(*states):

    tage = []

    for index, state in enumerate(states):

        tag = dict(PAYLOAD["days"][index])

        if state is not None:
            tag["me"] = state

        tage.append(tag)

    return parse_schedule({**PAYLOAD, "days": tage})


def test_the_own_state_is_read_per_day():

    schedule = _with_me("active", "none")

    mittwoch, donnerstag = schedule.days

    assert mittwoch.me == "active"

    assert donnerstag.me == "none"

    assert own_signup_label(mittwoch) == "ANGEMELDET"

    assert own_signup_label(donnerstag) == "NICHT ANGEMELDET"


def test_a_missing_field_says_nothing_at_all():
    """
    Eine ältere Bot-Fassung kennt das Feld nicht. Daraus "nicht
    angemeldet" zu machen wäre von einer echten fehlenden Anmeldung
    nicht zu unterscheiden - und das ist ein Satz, auf den jemand hin
    handelt. Die leere Beschriftung blendet den Chip aus.
    """

    schedule = _with_me(None, None)

    assert schedule.days[0].me == ""

    assert own_signup_label(schedule.days[0]) == ""

    assert own_signup_text(schedule.days[0]) == ""


def test_an_unknown_value_is_treated_as_no_answer_at_all():
    """
    Additiv gedacht wie `normalize_role()`: ein Wert, den diese
    Fassung nicht kennt, kostet die Auskunft - er erfindet keine.
    """

    schedule = _with_me("angemeldet")

    assert schedule.days[0].me == ""


def test_a_cancellation_is_an_answer_and_is_not_a_warning():
    """
    Der eigentliche Punkt: "abgesagt" heisst, der Raidlead weiss
    Bescheid; "nicht geantwortet" heisst, er wartet. Nur das zweite
    ist eine Aufforderung, und nur das zweite trägt deshalb die
    Warnfarbe. Rot hiesse "hier stimmt etwas nicht", und abgesagt zu
    haben ist kein Fehler.
    """

    abgesagt, offen = _with_me("absent", "none").days

    assert own_signup_variant(abgesagt) == "neutral"

    assert own_signup_variant(offen) == "warn"

    assert own_signup_variant(_with_me("active").days[0]) == "ok"


def test_every_state_carries_a_label_and_a_sentence():
    """
    Sonst bliebe ein Chip ohne Beschriftung stehen - und der wäre von
    "nicht gemeldet" nicht zu unterscheiden, weil genau das den Chip
    ausblendet.
    """

    for state in OWN_STATES:

        tag = _with_me(state).days[0]

        assert own_signup_label(tag)

        assert own_signup_text(tag)

        assert own_signup_variant(tag)


def test_the_own_state_survives_the_parallel_raids():
    """
    `others` läuft durch dasselbe `parse_schedule()` - beim zweiten
    Raid, an den man eher nicht denkt, ist die Frage sogar die
    wichtigere.
    """

    weiterer = {
        "title": "Twinkraid",
        "raid_size": 10,
        "days": [{**PAYLOAD["days"][0], "me": "none"}],
    }

    schedule = parse_schedule({**PAYLOAD, "others": [weiterer]})

    assert schedule.others[0].days[0].me == "none"


def test_the_state_reaches_the_comparison_the_card_redraws_on():
    """
    `RaidScheduleSync.process()` vergleicht den **ganzen** eingefrorenen
    Stand und macht daraus ein `state_changed`. Trüge `me` nicht dazu
    bei, bliebe der Chip auf "nicht angemeldet" stehen, nachdem man
    sich im Discord gerade eingetragen hat - und das ist genau der
    Augenblick, in dem jemand hinsieht.
    """

    assert _with_me("none") != _with_me("active")
