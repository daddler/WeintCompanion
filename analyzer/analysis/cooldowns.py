"""
Cooldown-Nutzung: eine Rechnung je Frage.

Diese Datei ist die Antwort auf vier Fehler, die alle dieselbe
Ursache hatten - die Cooldown-Bewertung wurde an drei Stellen
unabhängig voneinander gerechnet (im Bot-Payload, in der
Spec-Anreicherung, in der Academy), und die drei Rechnungen waren
nicht dieselbe:

1. **Ein möglicher Einsatz zu viel.** `int(dauer // abklingzeit) + 1`
   ergibt für einen Sechs-Minuten-Kampf und einen Drei-Minuten-Cooldown
   drei mögliche Einsätze. Möglich sind zwei (bei 0:00 und bei 3:00);
   der dritte läge genau auf dem Schlussgong. Wer alles richtig
   gemacht hatte, las deshalb "2 von 3 möglichen Einsätzen" und
   "1 Einsatz verschenkt".
2. **Defensives in der Nutzungsquote.** Die Kategorie wurde im Payload
   aus einer kurzen englischen Namensliste geraten, die *keine*
   Defensivcooldowns kannte. Alles, was nicht "rallying cry" oder
   "tranquility" hiess - also auch jeder Schildwall, jedes
   Gottesschild, jede Eisblock - galt als "geht auf Abklingzeit" und
   zählte als verschenkt, wenn er nicht gedrückt wurde. Getroffen hat
   das ausgerechnet Tanks: sie haben die meisten Defensivcooldowns.
   Und weil die Liste englisch war, fiel bei einem deutschen Bericht
   zusätzlich jeder Raid-Cooldown durchs Raster.
3. **Häufige Cooldowns durch das Heldentum-Fenster bestraft.** Der
   Anteil "Einsätze im Heldentum / alle Einsätze" wird umso kleiner,
   je öfter man einen Cooldown korrekt nutzt. Ein Ein-Minuten-Cooldown,
   in einem Sechs-Minuten-Kampf sechsmal gedrückt und einmal davon im
   Heldentum, ergab 17 % und damit einen Stern - für perfektes Spiel.
   Die Frage ist nicht, welcher *Anteil* der Einsätze im Fenster lag,
   sondern ob die **grossen** Cooldowns dort waren, wo sie hingehören.
4. **Kein Zeitbezug.** "4 von 6" sagt nicht, *wann* die Lücke war.
   `ready_gaps()` liefert die Strecken, auf denen ein Cooldown bereit
   war und nicht kam - die Grundlage des Cooldown-Zeitstrahls in
   WeintTV.

Alles hier ist rein: Zahlen rein, Zahlen raus, kein Qt, kein Snapshot
im Zugriff.
"""

from __future__ import annotations

from dataclasses import dataclass

from analyzer.data import class_abilities
from analyzer.models import (
    CD_DEFENSIVE,
    CD_HEAL,
    CD_PERSONAL,
    CD_RAID,
    CooldownUsage,
    HeroismWindow,
)


#
# Wie viel Restzeit ein Einsatz mindestens braucht, um noch als
# möglich zu gelten.
#
# Ein Cooldown, der rechnerisch zwei Sekunden vor dem letzten Schlag
# noch einmal bereit geworden wäre, ist keine verpasste Nutzung - er
# hätte nichts mehr geändert. Ohne diese Karenz erzeugt jede
# Kampfdauer, die knapp über einem Vielfachen der Abklingzeit liegt,
# genau einen erfundenen Vorwurf.
#

MIN_TAIL_SECONDS = 10.0


#
# Ab welcher Abklingzeit ein Cooldown als "gross" gilt - also als
# einer, den man für ein Burstfenster aufhebt.
#
# Zwei Minuten ist die Grenze, ab der Aufheben überhaupt sinnvoll ist:
# ein Ein-Minuten-Cooldown gehört auf Abklingzeit, und ihn für das
# Heldentum zu parken kostet mehr, als die Ausrichtung einbringt.
#

MAJOR_COOLDOWN_SECONDS = 120.0


#
# Ab welcher Länge eine ungenutzte Bereitschaft im Zeitstrahl
# überhaupt gezeigt wird. Alles darunter ist Rauschen: kein Mensch
# drückt auf die Sekunde.
#

MIN_GAP_SECONDS = 15.0


#
# Kategorien, die auf Abklingzeit gehören. Als Menge und nicht als
# `== CD_PERSONAL`, damit die Frage "zählt das in die Nutzungsquote"
# an einer Stelle beantwortet wird.
#

ON_COOLDOWN_CATEGORIES = frozenset({CD_PERSONAL})


def counts_towards_usage(category: str) -> bool:
    """
    Ob ein Cooldown in die Quote "genutzt von möglich" gehört.

    Nur Cooldowns, die auf Abklingzeit gehören. Ein Schildwall, ein
    Gottesschild, eine Aura der Hingabe warten auf ihren Moment -
    sie mitzuzählen hiesse, Umsicht als verschenkten Einsatz zu
    werten.
    """

    return category in ON_COOLDOWN_CATEGORIES


def category_of(
    name: str = "",
    spell_id: int = 0,
    given: str = "",
) -> str:
    """
    Welche Schublade ein gemeldeter Cooldown bekommt.

    Die Quelle gewinnt, wenn sie eine brauchbare Angabe macht -
    danach entscheidet die Fähigkeitstabelle, die Spell-ID, den
    englischen **und** den deutschen Namen kennt. Erst wenn beides
    schweigt, bleibt `CD_PERSONAL` als Annahme.
    """

    if given in (CD_RAID, CD_HEAL, CD_PERSONAL, CD_DEFENSIVE):
        return given

    found = class_abilities.cooldown_info(name, spell_id)

    if found is not None:

        #
        # Die Tabelle ist hier spec-unabhängig befragt: steht dieselbe
        # Fähigkeit bei zwei Spezialisierungen in verschiedenen
        # Schubladen (Seelenruhe ist beim Wiederherstellungsdruiden
        # ein Heil-, bei den übrigen ein Raid-Cooldown), gewinnt der
        # erste Eintrag. Für die Frage, die diese Datei stellt - zählt
        # das in die Nutzungsquote - sind beide dasselbe; die
        # spec-genaue Einordnung holt `spec_reference` je Spieler
        # nach.
        #

        return found.category

    return CD_PERSONAL


def known_cooldown_seconds(name: str = "", spell_id: int = 0) -> float:
    """
    Die Abklingzeit aus der Fähigkeitstabelle, oder 0.0.

    0.0 heisst "unbekannt" und nie "keine Abklingzeit" - dieselbe
    Regel wie `stars == 0`.
    """

    found = class_abilities.cooldown_info(name, spell_id)

    return float(found.cooldown) if found is not None else 0.0


def possible_uses(duration: float, cooldown: float) -> int:
    """
    Wie oft ein Cooldown in dieser Kampfdauer hätte kommen können.

    Gezählt werden die Zeitpunkte 0, `cooldown`, 2 × `cooldown` …,
    die noch mindestens `MIN_TAIL_SECONDS` vor dem Kampfende liegen.
    Ohne bekannte Abklingzeit gibt es keine Obergrenze - dann 0,
    damit daraus keine erfundene Quote entsteht.
    """

    if cooldown <= 0 or duration <= 0:
        return 0

    usable = duration - MIN_TAIL_SECONDS

    if usable <= 0:

        #
        # Ein Kampf, der kürzer ist als die Karenz: der erste Einsatz
        # bei 0:00 war trotzdem möglich.
        #

        return 1

    return int(usable // cooldown) + 1


def is_major(cooldown: float) -> bool:
    """
    Ob ein Cooldown gross genug ist, um ihn für ein Burstfenster
    aufzuheben.
    """

    return cooldown >= MAJOR_COOLDOWN_SECONDS


@dataclass(frozen=True)
class ReadyGap:
    """
    Eine Strecke, auf der ein Cooldown bereit war und nicht kam.

    `until` ist das Ende der Strecke - entweder der nächste Einsatz
    oder das Kampfende. Wofür das da ist: eine Quote sagt *wie viel*
    fehlte, diese Strecke sagt *wann*. Nur die zweite Auskunft kann
    man sich beim nächsten Pull vornehmen.
    """

    start: float

    until: float

    @property
    def seconds(self) -> float:

        return max(0.0, self.until - self.start)


def ready_gaps(
    cast_times: tuple[float, ...],
    cooldown: float,
    duration: float,
    min_seconds: float = MIN_GAP_SECONDS,
) -> tuple[ReadyGap, ...]:
    """
    Die Strecken, auf denen der Cooldown bereit war und nicht kam.

    Ohne bekannte Abklingzeit gibt es keine Aussage - dann eine leere
    Liste statt einer geratenen Lücke. Die letzte Strecke endet
    `MIN_TAIL_SECONDS` vor dem Kampfende: was danach bereit wird,
    hätte nichts mehr geändert (dieselbe Karenz wie in
    `possible_uses()`).
    """

    if cooldown <= 0 or duration <= 0:
        return ()

    horizon = duration - MIN_TAIL_SECONDS

    if horizon <= 0:
        return ()

    gaps: list[ReadyGap] = []

    ready_at = 0.0

    for cast in sorted(cast_times):

        if cast > horizon:
            break

        if cast - ready_at >= min_seconds:
            gaps.append(ReadyGap(ready_at, cast))

        ready_at = max(ready_at, cast + cooldown)

    if horizon - ready_at >= min_seconds:
        gaps.append(ReadyGap(ready_at, horizon))

    return tuple(gaps)


def burst_alignment(
    usage: CooldownUsage,
    windows: tuple[HeroismWindow, ...],
) -> tuple[int, int]:
    """
    (getroffen, Gelegenheiten) für **einen** Cooldown.

    Eine Gelegenheit ist ein Burstfenster, in dem dieser Cooldown
    bereit war oder während des Fensters bereit geworden wäre.
    Getroffen ist sie, wenn im Fenster tatsächlich ein Einsatz lag.

    Genau dieser Zuschnitt ist der Unterschied zur früheren Fassung:
    gezählt werden Gelegenheiten, nicht Einsätze. Wer einen
    Ein-Minuten-Cooldown sechsmal richtig drückt, hatte eine
    Gelegenheit und hat sie genutzt - und nicht "eine von sechs".
    """

    if not windows or not is_major(usage.cooldown):
        return 0, 0

    hits = 0

    chances = 0

    for window in windows:

        before = [at for at in usage.cast_times if at < window.start]

        ready_at = (max(before) + usage.cooldown) if before else 0.0

        if ready_at > window.end:

            #
            # Der Cooldown war das ganze Fenster über unten - das ist
            # keine verpasste Gelegenheit, sondern der Preis eines
            # früheren, ebenfalls richtigen Einsatzes.
            #

            continue

        chances += 1

        if any(window.contains(at) for at in usage.cast_times):
            hits += 1

    return hits, chances


def alignment_of(
    rows: tuple[CooldownUsage, ...],
    windows: tuple[HeroismWindow, ...],
) -> tuple[int, int]:
    """
    Dasselbe über mehrere Cooldowns eines Spielers.
    """

    hits = 0

    chances = 0

    for usage in rows:

        row_hits, row_chances = burst_alignment(usage, windows)

        hits += row_hits

        chances += row_chances

    return hits, chances
