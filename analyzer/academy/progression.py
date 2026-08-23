"""
Die Lernkurve: was mehrere Pulls zusammen aussagen.

**Warum es diese Datei gibt.** Die Academy bewertete bis 2.3.4
ausschliesslich den Kampf, der gerade auf dem Bildschirm stand. Ein
`PlayerProfile` entsteht aus genau einem Snapshot, lebt für die Dauer
seiner Anzeige und ist danach weg - `RaidDataService.history()` hält
zwar abgeschlossene Pulls, aber nur die der laufenden Sitzung, ohne
Sterne und ohne Bereichsaufteilung. Es gab in `core/`, `analyzer/`
und `addon/` keine einzige Stelle, die eine Bewertung über den Tag
hinaus aufhob (die Leerzustandskarte in
`gui/widgets/academy/history_card.py` sagte das ausdrücklich).

Damit fehlte der Academy genau das, wofür ein Lernzentrum da ist: die
Frage "werde ich besser?" ist über einen einzelnen Pull nicht zu
beantworten. Drei Sterne in Mechaniken sind ein Befund; drei Sterne
nach fünf und vier sind eine Entwicklung, und nur die zweite Auskunft
sagt jemandem, ob sich das Üben lohnt.

Diese Datei ist die **reine** Hälfte davon: Modell eines
aufgezeichneten Pulls, die Regeln, welcher Pull überhaupt
aufgezeichnet wird, und die Rechnung, die aus einer Reihe von
Aufzeichnungen eine Kurve macht. Kein Qt, keine Datei, kein Netz -
aus demselben Grund, aus dem der Rest von `analyzer/` keines davon
kennt. Die Ablage steht in `core/academy_history.py`.

Fünf Regeln, und jede einzelne davon zieht dieselbe Linie wie
`stars == 0` im Bewerter: **eine Kurve darf nur aus Messwerten
bestehen, die wirklich gemessen wurden.**

- **Nur beendete Pulls.** Während eines Kampfes ändern sich alle
  sechs Bewertungen im Sekundentakt - eine Aufzeichnung nach 30
  Sekunden beschriebe einen Pull, den es so nie gab. `qualifies()`
  verlangt deshalb `in_combat == False`. Das trifft alle drei Wege,
  auf denen ein Snapshot entsteht: die Live-Quelle liefert den
  beendeten Kampf weiter aus, ein Fight aus dem Archiv ist ohnehin
  vorbei, und die Wiedergabe setzt das Merkmal erst in ihrem letzten
  Bild.
- **Kein Sterne-Null in der Kurve.** `stars == 0` heisst "keine
  Daten" und ist keine schlechte Bewertung. Solche Bereiche werden
  gar nicht erst aufgezeichnet; ein Punkt bei null wäre in der Kurve
  von einem eingebrochenen Ergebnis nicht zu unterscheiden - und zwar
  genau dann, wenn die Datenquelle einen Block einmal nicht geliefert
  hat.
- **Ein Pull wird einmal aufgezeichnet.** Die Live-Quelle liefert
  denselben beendeten Kampf minutenlang weiter aus, ein Archivfight
  lässt sich beliebig oft öffnen, und die Wiedergabe endet auf
  demselben Kampf. `pull_key()` gibt allen dreien dieselbe Kennung,
  damit aus einem Pull nicht fünf Punkte werden.
- **Simulation und Ernstfall werden nicht vermischt.** Die
  Voreinstellung der Datenquelle ist die Simulation; ihre Pulls sind
  gerechnet und keine Lernkurve. Sie werden trotzdem aufgezeichnet -
  mit ihrer Quelle im Datensatz, und angezeigt wird immer nur die
  Quelle, die gerade eingestellt ist. Sie wegzulassen hiesse, die
  Karte auf der voreingestellten Quelle für immer leer zu lassen,
  und das sähe von einem Defekt nicht anders aus.
- **Die Reihenfolge kommt aus dem Kampf, nicht aus dem Klick.** Wer
  im Archiv erst Pull 5 und dann Pull 2 ansieht, hat sie in dieser
  Reihenfolge aufgezeichnet - als Kurve gelesen wäre das ein
  Rückschritt, den es nie gab. `sort_records()` ordnet deshalb nach
  Raidtag und Kampfnummer des Berichts und erst zuletzt nach dem
  Zeitpunkt der Aufzeichnung.
"""

from __future__ import annotations

from dataclasses import dataclass

from analyzer.academy.models import (
    CATEGORY_LABELS,
    CATEGORY_ORDER,
    MAX_STARS,
    PlayerProfile,
)
from analyzer.models import PullSummary, RaidSnapshot


#
# --------------------------------------------------
# Was aufgezeichnet wird
# --------------------------------------------------
#
# Wie lange ein Kampf gedauert haben muss, um in die Kurve zu
# kommen. Ein Wipe nach zwölf Sekunden hat keine Aktivzeit, keine
# Wirkungsdauern und keine Cooldowns - was der Bewerter daraus
# rechnet, misst den Pull und nicht den Spieler. Solche Punkte
# machen aus einer Lernkurve ein Rauschen, in dem die Entwicklung
# nicht mehr zu sehen ist.
#
# Dieselbe Art Untergrenze wie `MIN_SESSION_SECONDS` bei den
# Übungssitzungen am Trainingsdummy: lieber ein Datenpunkt weniger
# als einer, der etwas anderes misst, als er behauptet.
#

MIN_PULL_SECONDS = 30.0


#
# Wie viele Pulls die Kurve zeigt. Mehr wären auf der Kartenbreite
# nicht mehr zu unterscheiden, und eine Lernkurve über ein halbes
# Jahr beantwortet die Frage "werde ich gerade besser?" nicht.
#

CURVE_LIMIT = 12


#
# Ab wie vielen Punkten überhaupt von einer Entwicklung die Rede
# sein kann. Zwei ist das Minimum, das den Namen verdient - mit
# einem einzigen Pull gibt es keine Richtung, und eine aus einem
# Punkt gezeichnete Linie wäre eine Behauptung.
#

MIN_POINTS = 2


#
# --------------------------------------------------
# Richtung
# --------------------------------------------------
#

DIRECTION_UP = "up"

DIRECTION_DOWN = "down"

DIRECTION_FLAT = "flat"


DIRECTION_LABELS = {
    DIRECTION_UP: "besser",
    DIRECTION_DOWN: "schwächer",
    DIRECTION_FLAT: "gleichbleibend",
}


#
# Unterhalb dieser Änderung heisst es "gleichbleibend". Ohne eine
# Schwelle wäre jede Kurve dauerhaft in Bewegung: ein halber Stern
# Unterschied entsteht schon dadurch, dass ein Bereich in einem Pull
# einmal nicht bewertet werden konnte. Ein Viertelstern ist die
# kleinste Änderung, die man in der Anzeige überhaupt sieht.
#

TREND_TOLERANCE = 0.25


@dataclass(frozen=True)
class PullRecord:
    """
    Ein aufgezeichneter Pull - so viel, wie die Kurve braucht, und
    keine Zeile mehr.

    Ausdrücklich **kein** vollständiges Profil: Begründungstexte,
    Kennzahlen und Zeitpunkte gehören zum angezeigten Kampf und
    veralten mit ihm. Was über Wochen etwas aussagt, sind die Sterne
    je Bereich und der Kampf, zu dem sie gehören.

    `ratings` ist ein Tupel von Paaren statt eines Wörterbuchs, damit
    der Datensatz eingefroren bleibt wie alles im Analyzer. Es
    enthält **nur bewertete** Bereiche; ein fehlender Bereich heisst
    "dazu lag nichts vor" und nicht "null Sterne".
    """

    key: str = ""

    #
    # Der Raidtag als "JJJJ-MM-TT". Bei einem Fight aus dem Archiv
    # der Tag des Berichts, sonst der Tag der Aufzeichnung. Er ist
    # die grobe Ordnung der Kurve und zugleich das, was unter ihr
    # steht.
    #

    day: str = ""

    #
    # Die Kampfnummer innerhalb des Berichts (WarcraftLogs' fight id),
    # 0 wenn unbekannt. Sie ordnet die Pulls **eines** Abends
    # richtig, auch wenn sie in beliebiger Reihenfolge angesehen
    # wurden - die Pull-Nummer könnte das nicht, denn sie zählt je
    # Boss und beginnt bei jedem neuen Boss wieder von vorn.
    #

    sequence: int = 0

    recorded_at: float = 0.0

    encounter: str = ""

    pull_number: int = 0

    killed: bool = False

    duration: float = 0.0

    #
    # Die Spezialisierung, mit der dieser Pull gespielt wurde. Sie
    # entscheidet mit, welche Punkte überhaupt zusammengehören: eine
    # Rotationsbewertung als Frost sagt nichts über die Rotation als
    # Feuer, und eine Kurve, die beides in eine Linie zieht, zeigt
    # einen Bruch, den nie jemand gespielt hat.
    #

    spec: str = ""

    #
    # Die Datenquelle (`raid_data_source`). Simulation und
    # WarcraftLogs stehen im selben Speicher, aber nie in derselben
    # Kurve.
    #

    source: str = ""

    ratings: tuple[tuple[str, int], ...] = ()

    # --------------------------------------------------

    def stars(self, category: str) -> int:
        """
        Die Sterne eines Bereichs - 0 heisst **nicht bewertet**.
        """

        for name, value in self.ratings:

            if name == category:
                return value

        return 0

    @property
    def average(self) -> float:
        """
        Das Mittel über die bewerteten Bereiche.

        Unbewertete Bereiche zählen nicht mit, statt als Null in den
        Durchschnitt zu gehen. Sonst fiele die Gesamtlinie genau
        dann, wenn die Datenquelle einen Block nicht geliefert hat -
        und das sähe wie ein schlechter Abend aus.
        """

        werte = [value for _, value in self.ratings if value > 0]

        if not werte:
            return 0.0

        return sum(werte) / len(werte)

    @property
    def rated(self) -> bool:

        return any(value > 0 for _, value in self.ratings)

    @property
    def sort_key(self) -> tuple:

        return (self.day, self.sequence, self.recorded_at, self.key)

    @property
    def label(self) -> str:
        """
        "Malkorok · Pull 3" - die Beschriftung eines Punktes.
        """

        boss = self.encounter or "Kampf"

        if self.pull_number:
            return f"{boss} · Pull {self.pull_number}"

        return boss

    @property
    def outcome(self) -> str:

        return "Kill" if self.killed else "Wipe"


# --------------------------------------------------
# Aufzeichnen
# --------------------------------------------------


def qualifies(snapshot: RaidSnapshot | None) -> bool:
    """
    Ob dieser Snapshot einen **beendeten, brauchbaren** Pull
    beschreibt.

    Drei Bedingungen, jede gegen einen anderen Fehlgriff:
    `in_combat` schliesst den laufenden Kampf aus (eine Bewertung aus
    der Mitte beschriebe einen Pull, den es nie gab), `has_data`
    schliesst die Pause zwischen zwei Pulls aus (die Simulation
    liefert dort ausdrücklich einen Snapshot ohne Raid), und die
    Mindestdauer schliesst den Sofort-Wipe aus.
    """

    if snapshot is None:
        return False

    if snapshot.in_combat:
        return False

    if not snapshot.has_data:
        return False

    return snapshot.pull_seconds >= MIN_PULL_SECONDS


def pull_key(
    snapshot: RaidSnapshot,
    origin: str = "",
    day: str = "",
) -> str:
    """
    Die Kennung, unter der ein Pull genau einmal aufgezeichnet wird.

    **Mit `origin` ist sie exakt.** Aus dem Archiv (und aus der
    Wiedergabe, die von dort kommt) ist der Kampf durch Bericht und
    Kampfnummer eindeutig benannt - derselbe Pull morgen wieder
    geöffnet trägt dieselbe Kennung und wird nicht ein zweites Mal
    aufgezeichnet.

    **Ohne `origin` wird sie aus dem Tag gebildet.** Die Live-Quelle
    nennt keinen Bericht; sie liefert denselben beendeten Kampf aber
    minutenlang weiter aus, und innerhalb eines Raidabends ist
    "dritter Pull auf Malkorok" eindeutig. Über zwei Abende hinweg
    wiederholt sich die Pull-Nummer - deshalb steht der Tag mit in
    der Kennung, sonst verschluckte die Kurve den zweiten Abend.
    """

    if origin:
        return f"fight:{origin}"

    boss = snapshot.encounter_name or "?"

    return f"live:{day}:{boss}:{snapshot.pull_number}"


def record_from_profile(
    profile: PlayerProfile,
    snapshot: RaidSnapshot,
    *,
    key: str,
    day: str = "",
    sequence: int = 0,
    source: str = "",
    recorded_at: float = 0.0,
) -> PullRecord:
    """
    Aus einem fertigen Profil den Datensatz für die Kurve bauen.

    Nur bewertete Bereiche kommen mit (siehe `PullRecord.ratings`);
    die Reihenfolge ist die von `CATEGORY_ORDER`, damit zwei
    Datensätze desselben Pulls nicht allein durch die Reihenfolge
    verschieden aussehen.
    """

    ratings = tuple(
        (rating.category, int(rating.stars))
        for rating in sorted(
            profile.ratings,
            key=lambda entry: CATEGORY_ORDER.index(entry.category)
            if entry.category in CATEGORY_ORDER
            else len(CATEGORY_ORDER),
        )
        if rating.stars > 0
    )

    return PullRecord(
        key=key,
        day=day,
        sequence=sequence,
        recorded_at=recorded_at,
        encounter=snapshot.encounter_name,
        pull_number=snapshot.pull_number,
        #
        # Was als Kill zählt, steht genau einmal im Programm:
        # `PullSummary.KILL_THRESHOLD`. Die Zahl hier zu wiederholen
        # hiesse, dass derselbe Pull in WeintTVs Verlauf ein Kill
        # sein kann und in der Lernkurve nicht.
        #

        killed=snapshot.boss_health_percent <= PullSummary.KILL_THRESHOLD,
        duration=snapshot.pull_seconds,
        spec=profile.spec,
        source=source,
        ratings=ratings,
    )


# --------------------------------------------------
# Ablage-Form
# --------------------------------------------------
#
# Sie steht hier und nicht in der Ablage, damit Lesen und Schreiben
# in einer Datei nebeneinander stehen. Eine Form, die an zwei Stellen
# aufgeschrieben ist, läuft irgendwann auseinander - und der Schaden
# wäre still: ein Feld, das beim Lesen anders heisst als beim
# Schreiben, kommt als Vorgabewert zurück.
#


def to_dict(record: PullRecord) -> dict:

    return {
        "key": record.key,
        "day": record.day,
        "sequence": record.sequence,
        "recorded_at": record.recorded_at,
        "encounter": record.encounter,
        "pull_number": record.pull_number,
        "killed": record.killed,
        "duration": record.duration,
        "spec": record.spec,
        "source": record.source,
        "ratings": {name: value for name, value in record.ratings},
    }


def from_dict(data) -> PullRecord | None:
    """
    Einen Datensatz einlesen - `None`, wenn er unbrauchbar ist.

    Defensiv wie `snapshot_from_payload()`: eine von Hand
    verunstaltete Datei darf die Academy nicht unbenutzbar machen.
    Ein Datensatz ohne Kennung oder ohne eine einzige Bewertung wird
    verworfen, denn beides macht ihn für die Kurve wertlos.
    """

    if not isinstance(data, dict):
        return None

    key = str(data.get("key") or "").strip()

    if not key:
        return None

    roh = data.get("ratings")

    if not isinstance(roh, dict):
        return None

    ratings = []

    for name in CATEGORY_ORDER:

        try:
            wert = int(roh.get(name) or 0)

        except (TypeError, ValueError):
            continue

        if wert > 0:
            ratings.append((name, min(MAX_STARS, wert)))

    if not ratings:
        return None

    def _zahl(feld, vorgabe=0.0):

        try:
            return float(data.get(feld) or vorgabe)

        except (TypeError, ValueError):
            return vorgabe

    return PullRecord(
        key=key,
        day=str(data.get("day") or ""),
        sequence=int(_zahl("sequence")),
        recorded_at=_zahl("recorded_at"),
        encounter=str(data.get("encounter") or ""),
        pull_number=int(_zahl("pull_number")),
        killed=bool(data.get("killed")),
        duration=_zahl("duration"),
        spec=str(data.get("spec") or ""),
        source=str(data.get("source") or ""),
        ratings=tuple(ratings),
    )


# --------------------------------------------------
# Auswählen und ordnen
# --------------------------------------------------


def sort_records(records) -> tuple[PullRecord, ...]:
    """
    Die Pulls in der Reihenfolge, in der sie **gespielt** wurden.

    Nicht in der, in der sie angesehen wurden: wer im Archiv erst
    Pull 5 und dann Pull 2 öffnet, hätte sonst eine Kurve, die einen
    Rückschritt zeigt, den es nie gab.
    """

    return tuple(sorted(records, key=lambda record: record.sort_key))


def select(
    records,
    source: str = "",
    spec: str = "",
    limit: int = CURVE_LIMIT,
) -> tuple[PullRecord, ...]:
    """
    Die Punkte einer Kurve: gleiche Quelle, gleiche Spezialisierung,
    die letzten `limit`.

    Beide Filter greifen nur, wenn die Frage überhaupt beantwortbar
    ist. Ohne bekannte Spezialisierung wird nicht gefiltert - sonst
    bliebe die Kurve für jede Quelle leer, die keine meldet, und das
    sähe von "es gibt keine Pulls" nicht anders aus.
    """

    passend = [
        record
        for record in records
        if record.rated
        and (not source or record.source == source)
        and (not spec or not record.spec or record.spec == spec)
    ]

    geordnet = sort_records(passend)

    return geordnet[-limit:] if limit > 0 else geordnet


# --------------------------------------------------
# Die Kurve
# --------------------------------------------------


@dataclass(frozen=True)
class Trend:
    """
    Eine Linie der Lernkurve.

    `category` ist "" für die Gesamtlinie (das Mittel über alle
    bewerteten Bereiche) und sonst einer der sechs Bereiche.

    `points` sind die Sterne je Pull. Für einen Bereich sind das
    ganze Zahlen, für die Gesamtlinie ein Mittelwert - beides in
    derselben Einheit, damit die Karte zwei Linien in ein Koordinaten-
    system zeichnen kann, ohne umzurechnen.
    """

    category: str = ""

    points: tuple[float, ...] = ()

    # --------------------------------------------------

    @property
    def label(self) -> str:

        if not self.category:
            return "Gesamt"

        return CATEGORY_LABELS.get(self.category, self.category)

    @property
    def first(self) -> float:

        return self.points[0] if self.points else 0.0

    @property
    def last(self) -> float:

        return self.points[-1] if self.points else 0.0

    @property
    def delta(self) -> float:

        return self.last - self.first

    @property
    def direction(self) -> str:

        if self.delta > TREND_TOLERANCE:
            return DIRECTION_UP

        if self.delta < -TREND_TOLERANCE:
            return DIRECTION_DOWN

        return DIRECTION_FLAT

    @property
    def direction_label(self) -> str:

        return DIRECTION_LABELS[self.direction]

    @property
    def best(self) -> float:

        return max(self.points) if self.points else 0.0

    @property
    def text(self) -> str:
        """
        "Rotation 2,7 → 3,8" - die Legende einer Linie.
        """

        return f"{self.label} {stars_text(self.first)} → {stars_text(self.last)}"


def stars_text(value: float) -> str:
    """
    Sterne als Zahl: ganze ohne Nachkomma, gemittelte mit einer
    Stelle und Komma - "3" bzw. "3,4".
    """

    if abs(value - round(value)) < 0.05:
        return str(int(round(value)))

    return f"{value:.1f}".replace(".", ",")


def build_trend(records, category: str = "") -> Trend | None:
    """
    Die Linie eines Bereichs - `None`, wenn es keine gibt.

    Ein Pull, in dem dieser Bereich nicht bewertet wurde, ist **kein
    Punkt** und keine Null: er fällt aus der Linie heraus, die
    übrigen rücken zusammen. Eine Lücke als Nullpunkt zu zeichnen
    wäre die eine Sorte Fehler, gegen die dieses ganze Modul
    geschrieben ist.
    """

    punkte = []

    for record in records:

        wert = record.average if not category else float(
            record.stars(category)
        )

        if wert > 0:
            punkte.append(wert)

    if len(punkte) < MIN_POINTS:
        return None

    return Trend(category=category, points=tuple(punkte))


def weakest_category(records) -> str:
    """
    Der Bereich, der über die aufgezeichneten Pulls im Mittel am
    schwächsten steht - die zweite Linie der Karte.

    Bewusst über **alle** Punkte gemittelt und nicht am letzten Pull
    abgelesen: ein einzelner schlechter Kampf entscheidet sonst, was
    die Kurve zeigt, und die Linie sprünge von Pull zu Pull auf einen
    anderen Bereich.

    Nur Bereiche mit mindestens `MIN_POINTS` Punkten kommen infrage -
    sonst stünde dort eine gestrichelte Linie aus einem einzigen
    Wert.
    """

    bester_schnitt = None

    gewaehlt = ""

    for category in CATEGORY_ORDER:

        werte = [
            record.stars(category)
            for record in records
            if record.stars(category) > 0
        ]

        if len(werte) < MIN_POINTS:
            continue

        schnitt = sum(werte) / len(werte)

        if bester_schnitt is None or schnitt < bester_schnitt:

            bester_schnitt = schnitt

            gewaehlt = category

    return gewaehlt


def summary_text(records, trend: Trend | None) -> str:
    """
    Der Satz über der Kurve.

    Er nennt zuerst die Menge - "über 7 Pulls" - denn eine Richtung
    ohne ihre Grundlage ist nicht einzuordnen. Ohne Entwicklung sagt
    er das und behauptet keine.
    """

    anzahl = len(records)

    if anzahl < MIN_POINTS or trend is None:

        if anzahl == 1:
            return "Ein Pull aufgezeichnet - für eine Entwicklung fehlt der zweite."

        return "Noch keine Entwicklung erkennbar."

    if trend.direction == DIRECTION_FLAT:

        return (
            f"Über {anzahl} Pulls gleichbleibend bei "
            f"{stars_text(trend.last)} Sternen."
        )

    richtung = "besser" if trend.direction == DIRECTION_UP else "schwächer"

    return (
        f"Über {anzahl} Pulls {richtung}: "
        f"{stars_text(trend.first)} → {stars_text(trend.last)} Sterne."
    )


def category_sentence(trend: Trend | None) -> str:
    """
    Der Satz zur zweiten Linie - was sich in diesem einen Bereich
    getan hat.
    """

    if trend is None or not trend.category:
        return ""

    if trend.direction == DIRECTION_FLAT:

        return (
            f"{trend.label} bleibt bei {stars_text(trend.last)} "
            f"{'Stern' if trend.last == 1 else 'Sternen'}."
        )

    richtung = "steigt" if trend.direction == DIRECTION_UP else "fällt"

    return (
        f"{trend.label} {richtung} von {stars_text(trend.first)} "
        f"auf {stars_text(trend.last)}."
    )
