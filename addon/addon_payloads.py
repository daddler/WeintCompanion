"""
Die Auswertung in der Form, in der das Addon sie liest.

WeintTV und die Academy gibt es seit WeintCodex 1.0.1.0 auch im Spiel -
abgespeckt, für Leute mit nur einem Monitor. Beide Ingame-Seiten
rechnen bewusst nichts selbst nach: sie zeichnen nur, was hier
gebaut wird. Damit können Desktop und Addon gar nicht zu
unterschiedlichen Urteilen kommen.

Dieses Modul ist deshalb reine Umformung - keine Bewertung, keine
Schwellenwerte, kein Netzwerk. Es übersetzt die Dataclasses aus
analyzer/ in einfache Dictionaries, die core/lua_table.to_lua()
anschließend als Lua-Tabelle schreibt.

Zwei Konventionen müssen dabei erhalten bleiben, weil das Addon sie
genauso auslegt wie die Oberfläche hier:

    stars == 0      "keine Daten", NICHT "schlecht"
    at_seconds == -1  "kein Zeitpunkt bekannt", NICHT Sekunde 0

Beides wird unverändert durchgereicht, nicht auf 0 normalisiert.

Das Gegenstück im Addon ist der Kopfkommentar von
modules/companion.lua (INBOX_HANDLERS) - Feldnamen dort und hier
müssen zusammenpassen.
"""

from __future__ import annotations

from analyzer.academy.models import (
    CATEGORY_HINTS,
    CATEGORY_LABELS,
    CATEGORY_ORDER,
    PlayerProfile,
    TrainingPlan,
)
from analyzer.academy.progression import (
    build_trend,
    category_sentence,
    summary_text,
    weakest_category,
)
from analyzer.models import RaidSnapshot

#
# Der Import aus gui/ ist Absicht: analysis_gap() ist die eine Stelle,
# die entscheidet, WARUM eine Auswertung leer ist, und sie enthaelt
# bewusst kein Qt (siehe Modulkommentar dort). Genau darauf ruht er -
# ein Qt-Import in analysis_gap.py wuerde den Test-Job der CI
# lahmlegen, der nur pytest installiert und sonst nichts.
#

from gui.widgets.tv.analysis_gap import analysis_gap, rating_gap_text


#
# Schema-Version der Nutzlast. Das Addon prüft sie derzeit nicht,
# aber sie muss von Anfang an mitlaufen: ohne sie hätte eine spätere
# Formatänderung keinen Weg, sich gegenüber einem älteren Addon zu
# erkennen zu geben.
#

PAYLOAD_VERSION = 1


def _gap(snapshot: RaidSnapshot) -> str:
    """
    Warum die Tiefenauswertung leer ist - oder "" wenn sie es nicht
    ist.

    Bewusst hier berechnet und mitgeschickt, statt die Regel im Addon
    ein zweites Mal zu formulieren: analysis_gap() ist die eine
    Stelle, die diese Frage beantwortet.
    """

    if snapshot.has_analysis:
        return ""

    return analysis_gap(snapshot)


# --------------------------------------------------
# WeintTV
# --------------------------------------------------


def _ability(entry) -> dict:

    return {
        "ability": entry.ability,
        "amount": entry.amount,
        "hits": entry.hits,
        "verdict": entry.verdict,
        "note": entry.note,
        "source": entry.source_name,
    }


def build_weinttv_report(
    snapshot: RaidSnapshot,
    player_name: str = "",
) -> dict:
    """
    Der Pull-Bericht für den WeintTV-Tab im Addon.

    `player_name` ist der Charakter, auf den der Ingame-Filter
    "Nur ich" matcht. Er kommt aus der Academy-Charakterauswahl, weil
    das die einzige Stelle ist, an der der Nutzer überhaupt sagt,
    welcher Spieler im Raid er selbst ist.
    """

    encounter = snapshot.encounter

    return {
        "version": PAYLOAD_VERSION,
        "capturedAt": int(snapshot.captured_at),
        "source": snapshot.source_label,
        "me": player_name,

        "pull": snapshot.pull_number,
        "duration": snapshot.pull_seconds,
        "bossHealth": snapshot.boss_health_percent,
        "kill": snapshot.boss_health_percent <= 1.0,

        "hasAnalysis": snapshot.has_analysis,
        "gap": _gap(snapshot),

        "encounter": {
            "name": encounter.name if encounter else "",
            "instance": encounter.instance if encounter else "",
            "difficulty": encounter.difficulty if encounter else "",
            "size": encounter.raid_size if encounter else snapshot.raid_size,
        },

        "damageTaken": [
            {
                "actor": entry.actor_name,
                "total": entry.total,
                "avoidable": entry.avoidable,
                "unavoidable": entry.unavoidable,
                "hits": entry.hits,
                "avoidableHits": entry.avoidable_hits,
                "abilities": [_ability(ab) for ab in entry.abilities],
            }
            for entry in snapshot.damage_taken
        ],

        #
        # DoT, HoT und eigene Buffs landen in einer Liste,
        # unterschieden über "kind" - die Ingame-Seite zeigt alles in
        # derselben Tabelle, weil dort kein Platz für drei ist.
        #
        "uptimes": [
            {
                "actor": entry.actor_name,
                "ability": entry.ability,
                "kind": entry.kind,
                "uptime": entry.uptime_percent,
                "expected": entry.expected_percent,
                "applications": entry.applications,
                "target": entry.target,
            }
            for entry in (
                *snapshot.dot_uptimes,
                *snapshot.hot_uptimes,
                *snapshot.buff_uptimes,
            )
        ],

        "activity": [
            {
                "actor": entry.actor_name,
                "activePercent": entry.active_percent,
                "casts": entry.casts,
                "apm": entry.apm,
                "longestGap": entry.longest_gap,
            }
            for entry in snapshot.activity
        ],

        "movement": [
            {
                "actor": entry.actor_name,
                "meters": entry.meters,
                "mps": entry.meters_per_second,
                "avoidableHits": entry.avoidable_hits,
                "estimated": entry.estimated,
            }
            for entry in snapshot.movement
        ],

        "cooldowns": [
            {
                "actor": entry.actor_name,
                "ability": entry.ability,
                "uses": entry.uses,
                "possible": entry.possible,
                "inBurst": entry.in_burst,
                "efficiency": entry.efficiency,
                "castTimes": list(entry.cast_times),
                "category": entry.category,
            }
            for entry in snapshot.cooldown_usage
        ],

        #
        # Unterbrechungen und Dispels sind auf dem Desktop zwei
        # getrennte Listen, unterscheiden sich aber nur im Feld "kind" -
        # ingame stehen sie in einer Tabelle.
        #
        "support": [
            {
                "actor": entry.actor_name,
                "kind": entry.kind,
                "at": entry.at_seconds,
                "target": entry.target,
                "ability": entry.ability,
            }
            for entry in (*snapshot.interrupts, *snapshot.dispels)
        ],

        "mechanics": [
            {
                "actor": entry.actor_name,
                "mechanic": entry.mechanic,
                "count": entry.count,
                "severity": entry.severity,
                "category": entry.category,
                "at": entry.at_seconds,
            }
            for entry in snapshot.mechanics
        ],

        "consumables": [
            {
                "label": entry.label,
                "used": entry.used,
                "total": entry.total,
                "missing": list(entry.missing),
            }
            for entry in snapshot.consumables
        ],

        "warnings": list(snapshot.warnings),
    }


# --------------------------------------------------
# Academy
# --------------------------------------------------


def build_academy_catalog(lessons) -> dict:
    """
    Der Lektionskatalog dieses Charakters.

    Übergeben wird bewusst das Ergebnis von
    AcademyService.active_lessons() bzw. lessons_for_actor() und nicht
    der Gesamtkatalog: die 143 Lektionen aller Klassen und Bosse in
    die SavedVariables zu schreiben wäre Verschwendung, das Addon
    könnte mit den fremden ohnehin nichts anfangen.
    """

    return {
        "version": PAYLOAD_VERSION,

        "categories": [
            {
                "id": category,
                "label": CATEGORY_LABELS.get(category, category),
                "hint": CATEGORY_HINTS.get(category, ""),
            }
            for category in CATEGORY_ORDER
        ],

        "lessons": [
            {
                "id": lesson.lesson_id,
                "title": lesson.title,
                "category": lesson.category,
                "summary": lesson.summary,
                "steps": list(lesson.steps),
                "class": lesson.class_name,
                "spec": lesson.spec,
                "encounter": lesson.encounter,
                "roles": list(lesson.roles),
            }
            for lesson in lessons
        ],
    }


def _identity(profile: PlayerProfile, character: str) -> str:
    """
    Der Name, unter dem diese Auswertung im Addon abgelegt wird.

    `PlayerProfile.name` liefert wörtlich `"-"`, wenn der gewählte
    Spieler im Snapshot nicht gefunden wurde. Genau dieser Wert ging
    bis 1.6.2 als `character` ins Addon - während `weinttv_report.me`
    im selben Atemzug den echten Namen trug. Zwei Identitäten aus
    einer Zustellung, und das Addon musste raten, welche gilt.

    Deshalb gewinnt hier der von außen aufgelöste Name; das Profil
    ist nur noch Rückfall, und `"-"` erreicht die Leitung nie.
    """

    if character:
        return character

    if profile.actor is not None:
        return profile.actor.name

    return ""


def _line(trend) -> list[float]:
    """
    Eine Linie als Zahlenreihe - gerundet, weil zwei Nachkommastellen
    schon mehr sind, als fünf Sterne hergeben.
    """

    if trend is None:
        return []

    return [round(value, 2) for value in trend.points]


def _progress(records) -> dict:
    """
    Die Lernkurve in der Form, in der das Addon sie zeichnet.

    **Gerechnet wird hier nichts.** Punkte, Richtung und die beiden
    Sätze entstehen in `analyzer/academy/progression.py` - derselben
    Stelle, aus der die Verlaufskarte auf dem Desktop liest. Eine
    zweite Rechnung für dieselbe Kurve wäre die Doppelung, an der
    Spiel und Desktop irgendwann verschiedene Entwicklungen zeigen.

    Ohne aufgezeichnete Pulls bleibt `points` leer und `text` sagt
    genau das - eine erfundene Linie aus einem Punkt wäre die
    schlechtere Antwort.
    """

    records = tuple(records or ())

    overall = build_trend(records)

    category = weakest_category(records)

    area = build_trend(records, category) if category else None

    return {
        "pulls": len(records),

        "text": summary_text(records, overall),

        "points": _line(overall),

        "first": round(overall.first, 2) if overall else 0.0,
        "last": round(overall.last, 2) if overall else 0.0,
        "direction": overall.direction if overall else "",

        #
        # Der Bereich, der über die aufgezeichneten Pulls im Mittel am
        # schwächsten steht - nicht der des letzten Kampfes, sonst
        # spränge er von Pull zu Pull auf einen anderen.
        #
        # Seine Punkte reisen bewusst **nicht** mit: die Ingame-Karte
        # zeichnet eine Reihe, und zwei Reihen unterschiedlicher Länge
        # (ein Pull ohne Bewertung dieses Bereichs ist dort kein Punkt)
        # nebeneinanderzustellen hiesse, Pulls zu vergleichen, die
        # nicht dieselben sind. Der Satz sagt dasselbe und kann dabei
        # nicht falsch ausgerichtet sein.
        #
        "area": {
            "category": category,
            "label": CATEGORY_LABELS.get(category, category),
            "text": category_sentence(area),
        },
    }


def build_academy_state(
    profile: PlayerProfile,
    plan: TrainingPlan,
    snapshot: RaidSnapshot,
    completed,
    excluded,
    character: str = "",
    records=(),
    practice=(),
) -> dict:
    """
    Bewertung, Trainingsplan und Fortschritt eines Charakters.

    `plan` liefert die Reihenfolge - sie entsteht in
    evaluator.build_plan() aus den schwächsten Bereichen und darf im
    Addon nicht neu sortiert werden, sonst stünde dort eine andere
    "nächste Lektion" als auf dem Desktop.
    """

    actor = profile.actor

    results = {}

    for item in plan.items:

        result = item.result

        if result is None:
            continue

        results[item.lesson_id] = {
            "status": result.status,
            "at": result.at_seconds,
            "checks": [
                {
                    "status": check.status,
                    "detail": check.detail,
                }
                for check in result.checks
            ],
        }

    identity = _identity(profile, character)

    return {
        "version": PAYLOAD_VERSION,
        "character": identity,
        "capturedAt": int(snapshot.captured_at),
        "source": snapshot.source_label,

        "encounter": profile.encounter_name,
        "pull": profile.sample_size,
        "gap": _gap(snapshot),

        #
        # Derselbe Sachverhalt in Worten - und zwar in den Worten der
        # Academy, nicht denen von WeintTV: hier bleiben Bereiche
        # unbewertet, dort bleiben Karten leer. `gap` allein ist ein
        # Schlüssel, den das Addon selbst hätte ausformulieren müssen,
        # also eine zweite Formulierung desselben Befundes.
        #
        # Leer bleibt er absichtlich, wo jede Zeile ohnehin schon
        # "noch keine Daten" sagt (kein Raid, kein Pull) - ein zweiter
        # Satz darunter wäre Wiederholung.
        #
        "gapText": rating_gap_text(snapshot),

        #
        # Stand dieser Charakter überhaupt im ausgewerteten Pull? Ohne
        # die Angabe zeigt das Addon fünf Null-Stern-Zeilen und kann
        # nicht sagen, ob die Bewertung fehlt oder schlecht ist.
        # Additiv - ein älteres Addon ignoriert den Schlüssel.
        #
        "hasActor": actor is not None,

        "actor": {
            "name": actor.name if actor else identity,
            "class": actor.class_name if actor else "",
            "spec": actor.spec if actor else "",
            "role": actor.role if actor else "",
        },

        #
        # stars == 0 bleibt 0: das heißt "keine Daten". Würde man es
        # hier auf 1 anheben oder die Zeile weglassen, läse das Addon
        # eine schlechte Bewertung bzw. gar keine, wo in Wahrheit nur
        # die Datengrundlage fehlt.
        #
        "ratings": [
            {
                "category": rating.category,
                "stars": rating.stars,
                "detail": rating.detail,
                "metric": rating.metric_text,
                "at": rating.at_seconds,
            }
            for rating in profile.ratings
        ],

        "plan": [item.lesson_id for item in plan.items],
        "results": results,

        #
        # Warum der Plan so sortiert ist. Er folgt der Lernkurve,
        # sobald sie genug Pulls kennt - und dann kann seine
        # Reihenfolge den Sternen daneben widersprechen, die zu
        # *diesem* Kampf gehören. Ohne diesen Satz sieht das im Spiel
        # nach einem Fehler aus; auf dem Desktop steht er seit 2.3.5
        # über dem Plan. Leer heisst: es zählt allein der gezeigte
        # Kampf, also wie eh und je.
        #
        "planNote": plan.note,

        #
        # Der Satz zum Profil selbst (etwa: gegen wen hier verglichen
        # wird). Ebenfalls fertig formuliert.
        #
        "note": profile.note,

        #
        # "Werde ich besser?" - die Frage, die ein einzelner Pull
        # nicht beantwortet. Der Desktop zeichnet die Kurve seit
        # 2.3.5 auf; im Spiel gab es sie bis 2.8.0 nicht.
        #
        "progress": _progress(records),

        #
        # Die Übungsserie am Trainingsdummy, je Spec-Schlüssel des
        # Addons. Sie entsteht aus den Sitzungen, die das Addon
        # selbst meldet - und war dort bis 2.8.0 unsichtbar: erst am
        # dritten Tag erschien wortlos ein Haken.
        #
        "practice": list(practice or ()),

        "completed": sorted(completed),
        "excluded": sorted(excluded),
    }
