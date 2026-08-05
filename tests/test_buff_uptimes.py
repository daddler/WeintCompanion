"""
Eigene Buffs - die Kennzahl, an der die Tankbewertung hing.

Vorher gab es im Snapshot nur DoTs und HoTs. Ein Tank hat weder das
eine noch das andere: seine aktive Schadensminderung (Schildblock,
Mischen, Schild des Rechtschaffenen, Knochenschild) liegt auf ihm
selbst. In "Rotation" blieb deshalb nur die Aktivzeit übrig - also
ausgerechnet die Zahl, die über einen Tank am wenigsten aussagt.

Diese Datei sichert den ganzen Weg ab: Modell, Bot-Antwort,
Simulation, Prüfkriterium und Bewertung.
"""

from analyzer.academy.checks import resolve
from analyzer.academy.evaluator import build_profile
from analyzer.academy.models import CATEGORY_ROTATION, LessonCheck
from analyzer.models import (
    ROLE_TANK,
    UPTIME_BUFF,
    UPTIME_DOT,
    UPTIME_HOT,
    Actor,
    RaidSnapshot,
    TankEntry,
    UptimeEntry,
)
from analyzer.providers.mock import MockRaidDataProvider
from analyzer.providers.warcraftlogs_payload import snapshot_from_payload


def _tank(name="Bramborn"):

    return Actor(
        name=name,
        class_name="Warrior",
        spec="Schutz",
        role=ROLE_TANK,
    )


def _snapshot(**overrides):

    base = dict(
        raid_size=25,
        buff_uptimes=(
            UptimeEntry(
                actor_name="Bramborn",
                ability="Shield Block",
                uptime_percent=74.0,
                kind=UPTIME_BUFF,
                expected_percent=70.0,
            ),
        ),
    )

    base.update(overrides)

    return RaidSnapshot(**base)


def test_buff_uptimes_are_their_own_list():
    """
    Bei den HoTs abgelegt würden sie nur für Heiler ausgewertet, bei
    den DoTs stünden sie in WeintTV in der falschen Karte.
    """

    snapshot = _snapshot()

    assert snapshot.uptimes_of("Bramborn", UPTIME_BUFF)

    assert snapshot.uptimes_of("Bramborn", UPTIME_DOT) == ()

    assert snapshot.uptimes_of("Bramborn", UPTIME_HOT) == ()


def test_buff_uptimes_count_as_deep_analysis():
    """
    `has_analysis` ist der einzige Schalter, mit dem die Oberfläche
    eine ganze Karte auf "keine Daten" stellt - eine Quelle, die nur
    Buffs liefert, darf davon nicht ausgeschlossen sein.
    """

    assert _snapshot().has_analysis is True


def test_the_check_resolves_the_ability_in_both_languages():

    snapshot = _snapshot(
        buff_uptimes=(
            UptimeEntry(
                actor_name="Bramborn",
                ability="Schildblock",
                uptime_percent=62.0,
                kind=UPTIME_BUFF,
            ),
        ),
    )

    check = LessonCheck(metric="buff_uptime", subject="Shield Block")

    assert resolve(snapshot, _tank(), check) == 62.0


def test_a_missing_buff_is_no_data_and_not_zero():

    check = LessonCheck(metric="buff_uptime", subject="Shield Barrier")

    assert resolve(_snapshot(), _tank(), check) is None


def test_the_bot_payload_carries_the_block():
    """
    Additiv wie alle v2-Felder: eine Antwort ohne `buffs` ist kein
    Fehler, sondern schlicht ohne diese Zeilen.
    """

    payload = {
        "status": "ok",
        "fight": {"name": "Horridon", "duration": 180.0, "in_progress": False},
        "players": [
            {
                "name": "Bramborn",
                "class": "Warrior",
                "spec": "Protection",
                "damage_total": 100.0,
                "buffs": [
                    {"aura": "Shield Block", "uptime_percent": 74.0},
                ],
            },
        ],
    }

    snapshot = snapshot_from_payload(payload, "WarcraftLogs")

    abilities = [entry.ability for entry in snapshot.buff_uptimes]

    #
    # Gemeldet ist nur der Schildblock. Die Schildbarriere gehört aber
    # zur aktiven Minderung eines Schutzkriegers, und weil die Quelle
    # eigene Buffs nachweislich liefert, ist ihr Fehlen eine Null und
    # keine Datenlücke - siehe analyzer/analysis/spec_reference.py.
    #

    assert abilities == ["Schildblock", "Schildbarriere"]

    assert snapshot.buff_uptimes[0].kind == UPTIME_BUFF

    assert snapshot.buff_uptimes[0].uptime_percent == 74.0

    assert snapshot.buff_uptimes[1].uptime_percent == 0.0

    #
    # Und der Richtwert kommt aus der Spec-Tabelle, auch für die
    # gemeldete Zeile - sonst hätten WeintTV und die Academy für
    # denselben Effekt zwei Maßstäbe.
    #

    assert snapshot.buff_uptimes[0].expected_percent > 0.0

    del payload["players"][0]["buffs"]

    assert snapshot_from_payload(payload, "WarcraftLogs").buff_uptimes == ()


def test_the_simulation_gives_its_tanks_active_mitigation():
    """
    Ohne diese Zeilen wäre die Simulation kein Beweis mehr für den
    Vertrag: sie soll zeigen, was der Bot liefern soll.
    """

    snapshot = MockRaidDataProvider()._combat_snapshot(1, 150.0)

    names = {entry.actor_name for entry in snapshot.buff_uptimes}

    assert {"Bramborn", "Sigmara"} <= names


def test_a_tanks_rotation_is_rated_on_his_mitigation():
    """
    Der Kern: dieselbe Aktivzeit, einmal mit guter und einmal mit
    schlechter Abdeckung der aktiven Minderung - die Bewertung muss
    sich unterscheiden.
    """

    def rating(percent):

        #
        # Der Spieler muss im Snapshot auffindbar sein, sonst gibt es
        # gar kein Profil - die Tankübersicht genügt dafür.
        #

        snapshot = _snapshot(
            buff_uptimes=(
                UptimeEntry(
                    actor_name="Bramborn",
                    ability="Shield Block",
                    uptime_percent=percent,
                    kind=UPTIME_BUFF,
                    expected_percent=70.0,
                ),
            ),
            tanks=(TankEntry(actor=_tank(), health_percent=100.0),),
        )

        return build_profile(snapshot, "Bramborn").rating(CATEGORY_ROTATION)

    good = rating(70.0)

    bad = rating(20.0)

    assert good.stars > bad.stars

    assert "Aktive Minderung" in good.detail
