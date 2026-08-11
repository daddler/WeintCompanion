"""
Warum die Tiefenauswertung gerade leer ist - in Worten.

`RaidSnapshot.has_analysis` sagt nur, DASS nichts da ist. Warum,
kann drei völlig verschiedene Dinge heißen, und der Unterschied
entscheidet, ob der Nutzer etwas tun kann:

    kein Raid erkannt   -> warten, oder im Archiv einen Pull wählen
    kein Pull im Gange  -> warten
    Quelle liefert nur Summen -> auf die erweiterte Bot-Auswertung
                                 warten, nichts ist kaputt

Der Text liegt hier und nicht in den beiden Seiten, aus demselben
Grund, aus dem sich WeintTV und die Academy schon einen Snapshot und
einen ArchivePicker teilen: zwei Formulierungen desselben Sachverhalts
laufen früher oder später auseinander, und dann widersprechen sich die
beiden Seiten gegenseitig.

Die Folgesätze unterscheiden sich trotzdem, weil die Folge eine andere
ist: in WeintTV bleiben Karten leer, in der Academy bleiben Bereiche
unbewertet. Genau deshalb zwei Funktionen über einer gemeinsamen
Ursache statt eines Textbausteins für beide.
"""

from __future__ import annotations

from analyzer.models import RaidSnapshot


#
# Ursachen. Als Konstanten, damit die beiden Funktionen unten
# denselben Fall auch wirklich gleich benennen.
#

NO_RAID = "no_raid"

NO_PULL = "no_pull"

SUMS_ONLY = "sums_only"


def analysis_gap(snapshot: RaidSnapshot) -> str:
    """
    Welcher der drei Fälle vorliegt.
    """

    if not snapshot.has_data:
        return NO_RAID

    #
    # Ein erkannter Raid ohne laufende Pull-Uhr ist die
    # Vorbereitungsphase - dort fehlen die Werte nicht, es gibt sie
    # schlicht noch nicht.
    #

    if not snapshot.in_combat and snapshot.pull_seconds <= 0:
        return NO_PULL

    return SUMS_ONLY


def _sums_only_cause(snapshot: RaidSnapshot) -> str:

    return (
        f"Die Datenquelle „{snapshot.source_label}“ liefert für "
        "diesen Kampf nur Summen."
    )


def analysis_gap_text(snapshot: RaidSnapshot) -> str:
    """
    Für WeintTVs Analyse-Bereich.
    """

    gap = analysis_gap(snapshot)

    if gap == NO_RAID:

        return (
            "Es wird gerade kein Raid ausgewertet. Sobald ein Pull "
            "läuft - oder oben im Archiv ein Bericht und ein Pull "
            "gewählt sind - erscheinen hier erhaltener Schaden, "
            "Wirkungsdauern, Laufwege, Aktivzeit und "
            "Cooldown-Nutzung."
        )

    if gap == NO_PULL:

        return (
            "Der Raid steht bereit, es läuft aber gerade kein Pull. "
            "Mit dem nächsten Kampf füllt sich dieser Bereich von "
            "selbst."
        )

    return (
        _sums_only_cause(snapshot)
        + " Erhaltener Schaden je Fähigkeit, Wirkungsdauern, "
        "Laufwege, Aktivzeit und Cooldown-Nutzung kommen mit der "
        "erweiterten Auswertung des WeintCodex-Bots dazu - bis dahin "
        "bleiben die Live-Werte unverändert nutzbar."
    )


#
# --------------------------------------------------
# Einzelne Blöcke
# --------------------------------------------------
#
# `has_analysis` ist ein ODER über alle Tiefenfelder: sobald die
# Quelle *irgendetwas* davon liefert, ist es wahr und der erklärende
# Absatz über dem Bereich verschwindet. Genau dann fällt aber der
# häufigste Fall durchs Raster - die Quelle liefert einen Teil und den
# Rest nicht. Übrig bleibt der Platzhaltertext einer Karte, und
# "Keine Raid-Cooldowns erkannt." ist von "der Raid hat keine
# gezündet" nicht zu unterscheiden.
#
# Das ist derselbe Fehler, den `stars == 0` im Analyzer verhindert und
# den `spec_reference` beim Ergänzen fehlender Fähigkeiten sorgfältig
# umgeht: eine Datenlücke darf nicht wie ein Befund aussehen. Die
# Companion kann den Unterschied auch benennen, denn sie sieht, dass
# andere Tiefenfelder desselben Kampfes angekommen sind.
#

BLOCK_MOVEMENT = "movement"

BLOCK_COOLDOWN_USAGE = "cooldown_usage"

BLOCK_RAID_COOLDOWNS = "raid_cooldowns"

BLOCK_HEAL_COOLDOWNS = "heal_cooldowns"


#
# Je Block: das Feld des Snapshots und wie die Karte heißt. Die
# Beschriftung steht hier und nicht in der Seite, damit Karte und
# Erklärung nicht auseinanderlaufen.
#

BLOCK_FIELDS: dict[str, tuple[str, str]] = {
    BLOCK_MOVEMENT: ("movement", "Laufwege"),
    BLOCK_COOLDOWN_USAGE: ("cooldown_usage", "Cooldown-Nutzung"),
    BLOCK_RAID_COOLDOWNS: ("raid_cooldowns", "Raid-Cooldowns"),
    BLOCK_HEAL_COOLDOWNS: ("heal_cooldowns", "Heil-Cooldowns"),
}


def block_gap_text(snapshot: RaidSnapshot, block: str) -> str:
    """
    Warum genau dieser Block leer ist - oder leerer Text, wenn es
    nichts zu erklären gibt.

    Nichts zu erklären gibt es in zwei Fällen: der Block hat Zeilen
    (dann steht der Platzhalter ohnehin nicht da), oder die
    Tiefenauswertung fehlt komplett - dann sagt der Absatz über dem
    ganzen Bereich es bereits, und ein zweiter Satz je Karte wäre
    dieselbe Auskunft fünfmal.
    """

    field = BLOCK_FIELDS.get(block)

    if field is None:
        return ""

    name, label = field

    if getattr(snapshot, name, ()):
        return ""

    if not snapshot.has_analysis:
        return ""

    return (
        f"Die Datenquelle „{snapshot.source_label}“ hat für diesen "
        f"Kampf keine {label} geliefert - andere Tiefenwerte sind "
        f"angekommen. Das heißt „nicht übertragen“, nicht „nicht "
        f"genutzt“."
    )


def rating_gap_text(snapshot: RaidSnapshot) -> str:
    """
    Für die Bewertungskarte der Academy.

    Leerer Text heißt: nichts zu erklären. In der Vorbereitungsphase
    und ohne Raid steht auf jeder Zeile bereits "noch keine
    Auswertung" - ein zweiter Satz darunter wäre nur Wiederholung.
    Wenn dagegen ein Kampf ausgewertet wird und die Bereiche trotzdem
    unbewertet bleiben, ist das erklärungsbedürftig.
    """

    if snapshot.has_analysis:
        return ""

    if analysis_gap(snapshot) != SUMS_ONLY:
        return ""

    return (
        _sums_only_cause(snapshot)
        + " Rotation, Bewegung, Cooldowns und Überleben brauchen die "
        "erweiterte Auswertung des WeintCodex-Bots und bleiben bis "
        "dahin unbewertet - null Sterne heißen hier ausdrücklich "
        "„keine Daten“, nicht „schlecht“."
    )
