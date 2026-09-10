"""
Der **Sim-Lauf** - ein Vorgang, zwei Auskünfte.

WARUM ES DIESE DATEI GIBT.

Aus einem Sim-Lauf kommen zwei Dinge zurück: die **Gewichtung**
(`core/stat_weights.py`) und der **Zielzustand** (`core/target_gear.py`).
Technisch sind das zwei Auskünfte mit zwei Speichern, zwei Kanälen und
zwei Übertragungsstrings — und das bleibt auch so, aus den Gründen, die
in den beiden Verträgen stehen.

**Für den Nutzer ist es eins.** Er simmt seinen Charakter und will
danach die Empfehlungen im Spiel haben. Bis 3.2.0 verlangte das System
von ihm, die interne Trennung mitzudenken: zweimal einfügen, zweimal
übernehmen, und selbst wissen, welcher der beiden Exportknöpfe im Sim zu
welchem Teil gehört. Wer den zweiten vergaß, bekam eine Empfehlung, der
man nicht ansieht, dass ihr die Hälfte fehlt.

Diese Datei ist die Klammer darum. Sie ist ausdrücklich **kein neuer
Datenvertrag**:

* Die Ablagen bleiben (`stat_weights.json`, `target_gear.json`).
* Die Kanäle bleiben (`statweights`, `targetgear`).
* Die Strings bleiben (`WCIMPORT:SW:`, `WCIMPORT:TG:`).

Dazu kommt genau **ein** Feld auf beiden Seiten: die Kennung des Laufs.
Sie beantwortet die Frage, die vorher niemand stellen konnte —
*gehören diese Gewichtung und dieser Zielzustand zusammen?*

WAS EIN LAUF IST.

Ein Lauf gehört zu **genau einer Ausrüstung**: der, die der
WowSimsExporter gemeldet hat, als der Sim geöffnet wurde. Daraus folgt
alles Weitere:

* Die **Kennung** hängt an dieser Ausrüstung und ihrem Zeitstempel, nicht
  an der Uhr dieses Rechners. Derselbe Ausgangszustand ergibt denselben
  Lauf, auch nach einem Neustart der App - sonst hiesse jedes Einfügen
  „neuer Lauf", und die Korrelation wäre keine.
* Der **Zeitpunkt des Starts** ist der Zeitstempel des Exports. Er steht
  in der Uhr des Spiels (`time()`, vom Exporter geschrieben) und ist
  damit dieselbe Zahl, die das Addon beim *Bereitstellen* festhält. Das
  ist der ganze Handshake: kein zweiter Kanal, keine Vermutung.
* Ohne gemeldete Ausrüstung gibt es trotzdem einen Lauf - nur einen ohne
  Ausgangszustand. Er kann dann zwei Fragen nicht beantworten (wurde
  überhaupt optimiert, gilt das noch), und er **sagt das**, statt beides
  stillschweigend als „in Ordnung" zu führen.

WAS HIER NICHT PASSIERT.

**Gerechnet wird nichts.** Diese Datei stellt neben-, zählt und benennt;
die Optimierung hat der Sim getroffen. Sie ist die Fortsetzung von
`compare()` in `core/target_gear.py`, nicht eine zweite Meinung daneben.

Rein: kein Qt, keine Datei, kein Netz - wie `core/stat_weights.py` und
`core/target_gear.py`.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field, replace

from core.stat_weights import (
    class_label,
    normalize,
    parse,
    spec as spec_of,
    spec_label,
)
from core.target_gear import (
    TargetGear,
    changed_slots,
    compare,
    foreign_slots,
    parse_target,
)


#
# --------------------------------------------------
# Was für ein Text ist das?
# --------------------------------------------------
#
# EINE STELLE, DIE ES ENTSCHEIDET - UND SIE KENNT KEIN QT.
#
# Bisher wurde diese Frage im Lesen selbst beantwortet: `_read()`
# probiert die strengere Lesart zuerst und lässt die andere
# durchfallen. Das genügt, solange die Antwort nur „lies weiter"
# heisst.
#
# Seit die Seite den Text auch von sich aus aus der Zwischenablage
# nimmt, muss die Frage **gestellt werden können, ohne etwas zu tun**:
# was nicht aus dem Sim kommt, darf das Eingabefeld nicht anfassen.
# Ein Dateipfad, ein Zitat, ein halber Befehl - alles drei landet im
# Lauf eines Abends in derselben Zwischenablage, und keins davon
# gehört in dieses Feld.
#
# Zwei Fassungen derselben Reihenfolge liefen ab der ersten Änderung
# auseinander, und dann nähme die Zwischenablage ausgerechnet die
# Sorte nicht an, die das Feld gelesen hätte. Deshalb steht die
# Reihenfolge hier, und `_read()` folgt ihr.
#

NOTHING = ""

TARGET = "target"

WEIGHTS = "weights"


def recognize(text: str) -> str:
    """
    `TARGET`, `WEIGHTS` oder `NOTHING` - was dieser Text ist.

    **Die Zielausrüstung zuerst**, denn `parse_target()` ist die
    strengere der beiden Lesarten: sie erkennt nur eine Adresse, einen
    Base64-Rumpf ab 40 Zeichen oder JSON. Eine getippte Gewichtung
    („Hit 1.77") ist keins davon und fällt sicher durch - andersherum
    wäre es nicht so.

    **Erkannt heisst nicht brauchbar.** Ein Sim-Export ohne einen
    einzigen Sockelstein ist `TARGET`, und das ist Absicht: die Seite
    hat dazu einen eigenen Satz (*Include gems* fehlt), und den soll
    sie sagen dürfen. Nur was gar nicht aus dem Sim stammt, ist
    `NOTHING`.

    **Was diese App selbst in die Zwischenablage legt, ist `NOTHING`.**
    `WCIMPORT:` ist der Weg *ins Spiel*; ihn zurückzulesen hiesse, das
    eigene Ergebnis für ein neues zu halten. Die beiden Lesarten
    weisen ihn ohnehin ab - hier steht es trotzdem, weil sich das
    stillschweigend ändern kann und der Fehler dann keiner wäre, den
    man sieht.
    """

    text = (text or "").strip()

    if not text:
        return NOTHING

    if text.upper().startswith("WCIMPORT:"):
        return NOTHING

    target = parse_target(text)

    if target is not None and target.known:
        return TARGET

    parsed = parse(text)

    if parsed.problem:
        return NOTHING

    weights, _ = normalize(parsed.weights)

    return WEIGHTS if weights else NOTHING


#
# --------------------------------------------------
# Die Zustände eines Laufs
# --------------------------------------------------
#
# Sechs, und keiner davon ist ein Unterfall eines anderen: sie führen zu
# sechs verschiedenen nächsten Schritten. Ein gemeinsames „Fehler" wäre
# für fünf davon der falsche Satz.
#

EMPTY = "empty"          # nichts eingelesen - der Ausgangszustand

READY = "ready"          # vollständig, und es ändert sich etwas

UNCHANGED = "unchanged"  # vollständig, aber Stück für Stück derselbe Stand

INCOMPLETE = "incomplete"  # ein Teil des Ergebnisses fehlt noch

STALE = "stale"          # das Ergebnis gehört zu einer anderen Ausrüstung

MISMATCH = "mismatch"    # das Ergebnis gehört zu einer anderen Klasse


#
# Die Rangfolge, in der ein Zustand den anderen schlägt. Sie ist keine
# Geschmacksfrage: der obere verlangt jeweils etwas anderes als der
# untere, und wer STALE als „unvollständig" liest, fügt den fehlenden
# Teil ein und bekommt danach denselben unbrauchbaren Lauf.
#

_RANK = {
    MISMATCH: 5,
    STALE: 4,
    INCOMPLETE: 3,
    UNCHANGED: 2,
    READY: 1,
    EMPTY: 0,
}


#
# Ab wann ein Ergebnis nicht mehr zur gemeldeten Ausrüstung gehört.
#
# Ein einzelnes getauschtes Teil ist der Normalfall (ein Drop zwischen
# Simmen und Einfügen) - dafür gibt es im Spiel den Rückfall je Platz,
# und den ganzen Lauf deswegen zu verwerfen wäre die teure Antwort in
# die falsche Richtung. Wenn dagegen die HAELFTE der Plätze nicht mehr
# stimmt, wurde mit einer anderen Ausrüstung gesimmt, und das ist eine
# andere Auskunft.
#

STALE_SHARE = 0.5

STALE_MIN = 2


@dataclass(frozen=True)
class InputGear:
    """
    Der Ausgangszustand eines Laufs: was angelegt war, als der Sim
    geöffnet wurde.

    `reported_at` ist der Zeitstempel des WowSimsExporters, also eine
    Zahl aus der Uhr des **Spiels**. Genau deshalb kann das Addon sie
    gegen sein eigenes *Bereitstellen* halten.
    """

    character: str = ""

    realm: str = ""

    char_class: str = ""

    spec_key: str = ""

    items: tuple = ()

    reported_at: int = 0

    @property
    def item_count(self) -> int:

        return sum(1 for item in self.items if not item.empty)

    @property
    def fingerprint(self) -> str:
        """
        Der Ausgangszustand als kurze Zeichenkette.

        Sie geht in die Kennung des Laufs ein und macht ihn damit an
        die Ausrüstung gebunden: wer zwischendurch ein Teil wechselt und
        neu bereitstellt, hat einen anderen Lauf - und das ist richtig,
        denn ein Zielzustand gilt für genau die Ausrüstung, mit der
        gesimmt wurde.
        """

        roh = "|".join(
            "{}:{}:{}:{}".format(
                index,
                int(getattr(item, "item_id", 0) or 0),
                "-".join(
                    str(int(gem or 0))
                    for gem in getattr(item, "gems", ()) or ()
                ),
                int(getattr(item, "reforging", 0) or 0),
            )
            for index, item in enumerate(self.items)
        )

        return hashlib.sha1(roh.encode("utf-8")).hexdigest()[:12]


def input_from_export(export, reported_at: int = 0) -> InputGear | None:
    """
    Der Ausgangszustand aus einer Meldung des WowSimsExporters.

    `None`, wenn die Meldung keine Ausrüstung trägt: ein Lauf ohne
    Ausgangszustand ist etwas anderes als einer mit einem leeren, und
    nur der erste ist ehrlich.
    """

    if export is None or not getattr(export, "usable", False):
        return None

    return InputGear(
        character=str(getattr(export, "name", "") or ""),
        realm=str(getattr(export, "realm", "") or ""),
        char_class=str(getattr(export, "char_class", "") or "").upper(),
        spec_key=str(getattr(export, "spec_key", "") or ""),
        items=tuple(getattr(export, "items", ()) or ()),
        reported_at=int(reported_at or 0),
    )


def make_run_id(
    spec_key: str,
    character: str,
    realm: str,
    started_at: int,
    fingerprint: str = "",
) -> str:
    """
    Die Kennung eines Laufs: `SIM-JJJJMMTT-XXXX`.

    **Sie hängt am Lauf, nicht an der Uhr dieses Rechners.** Derselbe
    Charakter mit derselben Ausrüstung zum selben gemeldeten Zeitpunkt
    ergibt dieselbe Kennung - auch nach einem Neustart der App, auch
    beim zweiten Einfügen desselben Ergebnisses. Ohne diese Regel wäre
    die Kennung eine laufende Nummer und könnte gar nichts korrelieren:
    die Gewichtung bekäme eine andere als der Zielzustand, obwohl beide
    aus einem Lauf stammen.

    Der Datumsteil ist für Menschen da (eine Rückfrage lautet „aus
    welchem Lauf stammt das"), der Rest unterscheidet.
    """

    stamp = int(started_at or 0)

    tag = time.strftime("%Y%m%d", time.localtime(stamp)) if stamp else "00000000"

    roh = "|".join(
        [
            (spec_key or "").upper(),
            (character or "").lower(),
            (realm or "").lower(),
            str(stamp),
            fingerprint or "",
        ]
    )

    kurz = hashlib.sha1(roh.encode("utf-8")).hexdigest()[:4].upper()

    return f"SIM-{tag}-{kurz}"


@dataclass(frozen=True)
class Validation:
    """
    Was über einen Lauf zu sagen ist - in Zahlen, nicht in Sätzen.

    Die Sätze baut die Oberfläche daraus (`gui/pages/sim.py`); hier
    stehen nur die Befunde. Zwei Fassungen desselben Satzes liefen ab
    der ersten Änderung auseinander, und die falsche stünde dann
    ausgerechnet bei dem, der einen Fehler sucht.
    """

    state: str = EMPTY

    have_weights: bool = False

    have_target: bool = False

    target_expected: bool = True

    checked_slots: int = 0

    changed_slots: int = 0

    gem_changes: int = 0

    reforge_changes: int = 0

    foreign_slots: int = 0

    #
    # WELCHE Plätze sich ändern, nicht nur wieviele. Eine Zahl allein
    # ist nicht nachprüfbar: „7 Sockeländerungen" glaubt man oder nicht,
    # „Kopf, Brust, Hände" sieht man im Spiel nach. Höchstens sechs -
    # danach ist die Zeile eine Liste und kein Satz mehr.
    #

    changed_names: tuple[str, ...] = ()

    comparable: bool = False

    missing: tuple[str, ...] = ()

    notes: tuple[str, ...] = ()

    @property
    def complete(self) -> bool:
        """
        Ob alles da ist, was dieser Lauf haben kann.

        Für eine QE-Live-Spezialisierung ist das die Gewichtung allein -
        dort gibt es keinen Zielzustand zu holen, und ihn zu vermissen
        wäre eine Aufforderung ins Leere.
        """

        if not self.have_weights:
            return False

        return self.have_target or not self.target_expected

    @property
    def usable(self) -> bool:
        """
        Ob sich daraus etwas ins Spiel bringen lässt.

        Ausdrücklich schon bei einem Teil: eine Gewichtung allein ist
        eine vollwertige Auskunft, und sie zurückzuhalten, bis der
        zweite Export da ist, wäre eine Strafe für einen Zwischenstand.
        """

        return self.have_weights or self.have_target


@dataclass(frozen=True)
class SimRun:
    """
    Ein Sim-Lauf: ein Ausgangszustand, bis zu zwei Ergebnisse.

    **Er ersetzt keinen der beiden Speicher.** Was hier steht, ist die
    Klammer; abgelegt und zugestellt wird weiterhin über
    `stat_weights_store` und `target_gear_store`, die diese Kennung nur
    mitführen.
    """

    spec_key: str = ""

    character: str = ""

    realm: str = ""

    started_at: int = 0

    completed_at: int = 0

    input_gear: InputGear | None = None

    weights: dict[str, int] = field(default_factory=dict)

    weights_source: str = ""

    weights_class: str = ""

    weights_at: int = 0

    target: TargetGear | None = None

    target_at: int = 0

    @property
    def run_id(self) -> str:
        """
        Die Kennung - und `""`, solange es keinen Ausgangszustand gibt.

        EIN LAUF OHNE ANKER HAT KEINE IDENTITAET, und eine zu erfinden
        wäre schlimmer als keine: sie hinge dann an der Uhr dieses
        Rechners, wäre bei jedem Betreten der Seite eine andere, und
        die Frage „gehören diese beiden zusammen" bekäme jedes Mal ein
        falsches Nein. Ein leeres Feld ist die ehrliche Antwort -
        dieselbe Regel wie `at == -1` und `stars == 0`.
        """

        if self.input_gear is None:
            return ""

        return make_run_id(
            self.spec_key,
            self.character,
            self.realm,
            self.started_at,
            self.input_gear.fingerprint,
        )

    @property
    def have_weights(self) -> bool:

        return bool(self.weights)

    @property
    def have_target(self) -> bool:

        return self.target is not None and self.target.usable

    @property
    def source(self) -> str:
        """
        Woher das Ergebnis kam - der Zielzustand nennt seine Gestalt
        genauer als die Gewichtung, deshalb hat er hier Vorrang.
        """

        if self.target is not None and self.target.source:
            return self.target.source

        return self.weights_source or ""


def start_run(
    spec_key: str,
    export=None,
    reported_at: int = 0,
    character: str = "",
    realm: str = "",
    now: int | None = None,
) -> SimRun:
    """
    Einen Lauf eröffnen.

    Der Startzeitpunkt ist der **Zeitstempel des Exports**, nicht die
    Uhr dieses Rechners: er stammt aus dem Spiel und ist damit die
    einzige Zahl, die auf beiden Seiten dieselbe ist. Fehlt er, tritt
    die eigene Uhr ein - dann ist der Handshake im Spiel keiner, und der
    Lauf sagt das über `input_gear is None`.
    """

    gear = input_from_export(export, reported_at)

    return SimRun(
        spec_key=(spec_key or "").strip().upper(),
        character=character or (gear.character if gear else ""),
        realm=realm or (gear.realm if gear else ""),
        started_at=int(reported_at or 0)
        or int(now if now is not None else time.time()),
        input_gear=gear,
    )


def with_weights(
    run: SimRun,
    weights: dict[str, int],
    source: str = "sim",
    sim_class: str = "",
    now: int | None = None,
) -> SimRun:
    """
    Die Gewichtung in den Lauf legen - sie **ersetzt**, was dort stand.

    Ein zweites Einfügen ist immer eine Korrektur: niemand fügt
    dieselbe Auskunft zweimal ein, um beide zu behalten.
    """

    stamp = int(now if now is not None else time.time())

    return replace(
        run,
        weights=dict(weights or {}),
        weights_source=source or "sim",
        #
        # GROSSGESCHRIEBEN, weil `SpecSim.class_token` es ist
        # (`DEATHKNIGHT`) und `parse().sim_class` ebenfalls. Zwei
        # Schreibweisen für dieselbe Klasse hiessen: jede Ausgabe wäre
        # eine fremde Klasse, und die Warnung stünde immer da - nach
        # zweimal liest sie niemand mehr.
        #
        weights_class=(sim_class or "").upper(),
        weights_at=stamp,
        completed_at=stamp,
    )


def with_target(
    run: SimRun,
    target: TargetGear | None,
    now: int | None = None,
) -> SimRun:

    stamp = int(now if now is not None else time.time())

    return replace(
        run,
        target=target,
        target_at=stamp,
        completed_at=stamp,
    )


def _worse(left: str, right: str) -> str:

    return left if _RANK.get(left, 0) >= _RANK.get(right, 0) else right


def validate(
    run: SimRun | None,
    expected_spec: str = "",
    target_expected: bool = True,
) -> Validation:
    """
    Was mit diesem Lauf ist - in genau einem Zustand plus Zahlen.

    DREI DINGE, DIE HIER NICHT PASSIEREN, UND ALLE DREI SIND ABSICHT:

    * **Nichts wird verworfen.** Auch ein Lauf mit falscher Klasse
      bleibt benutzbar - vielleicht simmt jemand für seinen
      Zweitcharakter. Er wird laut benannt, und die Oberfläche verlangt
      dafür einen zweiten Blick; abgewiesen wird er nicht.
    * **Nichts wird geraten.** Fehlt der Ausgangszustand, ist
      `comparable` falsch, und die Frage „wurde überhaupt optimiert"
      bleibt **offen** statt mit „ja" beantwortet zu werden.
    * **Kein Zustand wird von einem anderen verdeckt.** `missing` und
      `notes` stehen unabhängig vom Zustand da: ein veralteter Lauf,
      dem auch noch die Gewichtung fehlt, sagt beides.
    """

    if run is None:

        return Validation(state=EMPTY, target_expected=target_expected)

    have_weights = run.have_weights

    have_target = run.have_target

    if not have_weights and not have_target:

        return Validation(
            state=EMPTY,
            target_expected=target_expected,
        )

    missing: list[str] = []

    notes: list[str] = []

    if not have_weights:
        missing.append("weights")

    if target_expected and not have_target:
        missing.append("target")

    #
    # DER VERGLEICH GEGEN DEN AUSGANGSZUSTAND. Er beantwortet die eine
    # Frage, die keine der drei Sim-Gestalten beantwortet: ob überhaupt
    # optimiert wurde. Ohne gemeldete Ausrüstung bleibt sie offen -
    # `comparable` sagt das, und die Oberfläche schreibt es hin.
    #

    checked = 0

    changed = 0

    gems = 0

    reforges = 0

    fremd = 0

    namen: tuple[str, ...] = ()

    comparable = bool(
        have_target and run.input_gear is not None and run.input_gear.items
    )

    if comparable:

        diffs = compare(run.target, run.input_gear.items)

        checked = len(diffs)

        changed = len(changed_slots(diffs))

        fremd = len(foreign_slots(diffs))

        gems = sum(diff.gem_changes for diff in diffs)

        reforges = sum(1 for diff in diffs if diff.reforge_differs)

        namen = tuple(diff.slot_name for diff in changed_slots(diffs)[:6])

    #
    # WIEVIELE PLAETZE UEBERHAUPT VERGLEICHBAR SIND. Ein Platz, auf dem
    # inzwischen ein anderes Teil steckt, ist keine Aussage ueber die
    # Optimierung - dort ist nicht die Rechnung eine andere, sondern die
    # Ausruestung. Ihn in „kein Unterschied" mitzuzaehlen hiesse, aus
    # einer fehlenden Vergleichsmoeglichkeit ein „schon optimal" zu
    # machen, und das ist der teure Irrtum in die falsche Richtung.
    #

    vergleichbar = max(checked - fremd, 0)

    state = READY if (have_weights or have_target) else EMPTY

    if missing:
        state = _worse(state, INCOMPLETE)

    if comparable and vergleichbar and changed == 0:
        state = _worse(state, UNCHANGED)

    #
    # VERALTET IST NICHT UNVOLLSTAENDIG. Ein Ergebnis, dessen Plätze zur
    # Hälfte ein anderes Teil nennen, wurde mit einer anderen Ausrüstung
    # gesimmt - den fehlenden Teil nachzuliefern hilft daran nichts.
    #

    if (
        comparable
        and checked
        and fremd >= STALE_MIN
        and fremd >= checked * STALE_SHARE
    ):
        state = _worse(state, STALE)

    #
    # Die Zahl steht in BEIDEN Faellen da, nicht nur im harmlosen. Wer
    # 15 von 15 fremden Plaetzen hat, will die 15 lesen - und wer 1 von
    # 15 hat, ebenfalls. Der Zustand sagt, wie schlimm es ist; diese
    # Zeile sagt, wie viel.
    #

    if fremd:
        notes.append("foreign")

    #
    # DIE KLASSE IST DER MASSSTAB, NICHT DIE SPEZIALISIERUNG. Die
    # Zweitspec mit laufender Ausrüstung zu simmen ist der Normalfall -
    # dieselbe Regel wie `fits_spec()` beim Weg IN den Sim.
    #

    expected = spec_of(expected_spec or run.spec_key)

    if run.weights_class and expected and run.weights_class != expected.class_token:
        state = _worse(state, MISMATCH)

    if (
        run.target is not None
        and run.target.spec_key
        and expected_spec
        and run.target.spec_key != expected_spec
    ):
        notes.append("other_spec")

        #
        # EINE ANDERE SPEZIALISIERUNG IST EIN HINWEIS, EINE ANDERE
        # KLASSE EIN MISSVERHAELTNIS. Die Zweitspec mit laufender
        # Ausruestung zu simmen ist der Normalfall (dieselbe Regel wie
        # `fits_spec()`); ein Zielzustand fuer eine fremde Klasse nennt
        # dagegen Gegenstandsnummern, die dieser Charakter nie tragen
        # wird. Abgewiesen wird auch er nicht - benannt schon.
        #

        fremde_spec = spec_of(run.target.spec_key)

        if (
            fremde_spec
            and expected
            and fremde_spec.class_token != expected.class_token
        ):
            state = _worse(state, MISMATCH)

    if have_target and not comparable:
        notes.append("unverifiable")

    return Validation(
        state=state,
        have_weights=have_weights,
        have_target=have_target,
        target_expected=target_expected,
        checked_slots=checked,
        changed_slots=changed,
        gem_changes=gems,
        reforge_changes=reforges,
        foreign_slots=fremd,
        changed_names=namen,
        comparable=comparable,
        missing=tuple(missing),
        notes=tuple(dict.fromkeys(notes)),
    )


#
# --------------------------------------------------
# Sätze für die Oberfläche
# --------------------------------------------------
#
# Sie stehen hier und nicht auf der Seite, damit der Testlauf sie ohne
# Qt prüfen kann - dieselbe Aufteilung wie `gap_text()`/`age_text()` in
# `core/wowsims_export.py`.
#


def headline(validation: Validation) -> str:
    """
    Der eine Satz, der ganz oben steht.

    Er beantwortet Frage 3 und 4 der Seite in einem: ist mein Ergebnis
    vollständig, und wurde wirklich etwas optimiert?
    """

    state = validation.state

    if state == EMPTY:
        return "Noch kein Sim-Ergebnis eingefügt."

    if state == MISMATCH:
        return "Das gehört zu einer anderen Klasse."

    if state == STALE:
        return "Das Ergebnis gehört zu einer anderen Ausrüstung."

    if state == INCOMPLETE:

        if not validation.have_weights and validation.have_target:
            return "Optimierte Ausrüstung erkannt — die Gewichtung fehlt noch."

        return "Gewichtung erkannt — die optimierte Ausrüstung fehlt noch."

    if state == UNCHANGED:
        return "Das Sim-Ergebnis entspricht deiner angelegten Ausrüstung."

    return "Sim-Ergebnis vollständig."


def parts_line(validation: Validation) -> str:
    """
    Die Häkchenzeile: was liegt vor, was fehlt.

    Sie nennt die beiden Teile in der Sprache des Nutzers und nicht in
    der des Formats - `stat_weights` und `target_gear` sind Namen aus
    dem Quelltext, und wer sie liest, muss sie erst übersetzen.
    """

    teile = ["Gewichtung " + ("✓" if validation.have_weights else "fehlt")]

    if validation.target_expected:

        teile.append(
            "Optimierte Ausrüstung "
            + ("✓" if validation.have_target else "fehlt")
        )

    return " · ".join(teile)


def change_line(validation: Validation) -> str:
    """
    Was sich ändert - in Zahlen, weil eine Zahl nachprüfbar ist und ein
    „erfolgreich" nicht.
    """

    if not validation.have_target:
        return ""

    if not validation.comparable:

        return (
            "Ob darin wirklich das Ergebnis eines Optimierungslaufs steht, "
            "lässt sich hier nicht prüfen — dafür müsste der "
            "WowSimsExporter deine angelegte Ausrüstung gemeldet haben."
        )

    vergleichbar = max(
        validation.checked_slots - validation.foreign_slots, 0
    )

    #
    # KEIN VERGLEICHBARER PLATZ IST NICHT „KEIN UNTERSCHIED". Wo überall
    # ein anderes Teil steckt, ist die Frage nach der Optimierung gar
    # nicht gestellt worden - „möglicherweise ist bereits alles optimal"
    # wäre dort schlicht falsch, und zwar in die teure Richtung.
    #

    if not vergleichbar:

        return (
            f"{validation.checked_slots} Ausrüstungsplätze geprüft — an "
            "keinem davon steckt noch das Teil, mit dem gesimmt wurde. "
            "Ob im Sim optimiert wurde, lässt sich daran nicht ablesen."
        )

    if validation.changed_slots == 0:

        return (
            f"{vergleichbar} vergleichbare Ausrüstungsplätze geprüft, "
            "kein Unterschied. Möglicherweise ist bereits alles optimal — "
            "oder im Sim wurde noch kein Optimierungslauf ausgeführt "
            "(Zahnrad neben Suggest Reforges, Include gems anhaken)."
        )

    stuecke = [f"{vergleichbar} vergleichbare Ausrüstungsplätze geprüft"]

    if validation.gem_changes:
        stuecke.append(f"{validation.gem_changes} Sockeländerungen")

    if validation.reforge_changes:
        stuecke.append(f"{validation.reforge_changes} Umschmiedungen")

    satz = " · ".join(stuecke)

    if validation.changed_names:

        satz += (
            f" — es ändert sich etwas an {validation.changed_slots} Teilen ("
            + ", ".join(validation.changed_names)
            + (", …" if validation.changed_slots > len(validation.changed_names)
               else "")
            + ")"
        )

    return satz + "."


def source_line(run: SimRun | None) -> str:
    """
    Was gelesen wurde, in Zahlen - der Beleg dafür, dass der Text
    angekommen ist.

    Er steht neben dem Befund und nicht statt seiner: „15 Teile, 12
    Sockelsteine" beantwortet, ob der richtige Export eingefügt wurde;
    ob darin optimiert wurde, beantwortet `change_line()`.
    """

    if run is None or run.target is None or not run.target.usable:
        return ""

    return "{}: {} Ausrüstungsteile, {} Sockelsteine, {} Umschmiedungen.".format(
        run.target.source_label,
        run.target.item_count,
        run.target.gem_count,
        run.target.reforge_count,
    )


def next_step(validation: Validation) -> str:
    """
    Was jetzt zu tun ist - und nichts, wenn nichts zu tun ist.

    Ein Hinweis, der immer dasteht, wird nach zweimal nicht mehr
    gelesen; dieselbe Regel wie bei der Warnzeile im
    Bestätigungsfenster drüben.
    """

    state = validation.state

    if state == INCOMPLETE:

        if "target" in validation.missing:

            #
            # Der billigere der beiden Wege: der Sim hat schon
            # gerechnet, es fehlt nur der Export daraus.
            #

            return (
                "Fehlt noch: im Sim Export → Link oder JSON kopieren. "
                "Vorher das Zahnrad neben Suggest Reforges — ohne "
                "Include gems bleiben die Sockelsteine, wie sie stecken."
            )

        #
        # WAS HIER FEHLT, KOSTET EINEN ZWEITEN SIM-LAUF - und deshalb
        # steht dabei, dass das Übernehmen darauf nicht wartet.
        #
        # *Stat Weights* rechnet im Sim von vorn und dauert Minuten. Wo
        # ein Zielzustand vorliegt, entscheidet drüben ohnehin er
        # (`../../WeintCodex/docs/systems/gearing.md`); die Gewichtung
        # ist der Rückfall für die Plätze, für die er nichts sagt - eine
        # Auskunft, die man nachreichen kann, und keine, ohne die das
        # Vorliegende nichts wert wäre.
        #
        # „Noch nicht vollständig" allein hat genau das Gegenteil
        # nahegelegt: es klang wie eine Sperre, und wer es geglaubt hat,
        # hat den Sim ein zweites Mal laufen lassen, bevor er das
        # Ergebnis des ersten ins Spiel gebracht hat.
        #

        return (
            "Übernehmen geht schon — die optimierte Ausrüstung reicht "
            "fürs Erste. Die Gewichtung dazu kostet im Sim einen "
            "zweiten Lauf unter Stat Weights; sie zählt für die Plätze, "
            "über die das Ergebnis nichts sagt, und lässt sich jederzeit "
            "nachreichen."
        )

    if state == STALE:

        return (
            "Seit dem Simmen hat sich deine Ausrüstung geändert. Im Spiel "
            "unter Charakter → Simmen neu bereitstellen und noch einmal "
            "simmen — was noch passt, gilt trotzdem weiter."
        )

    if state == MISMATCH:

        return (
            "Prüfe, ob oben der richtige Charakter steht. Übernehmen "
            "kannst du es trotzdem — gemeint ist dann diese Auswahl."
        )

    return ""


def run_label(run: SimRun | None) -> str:
    """
    Die Zeile, mit der sich ein Lauf später wiedererkennen lässt.

    Sie muss dem Nutzer nicht auffallen; sie muss dastehen, wenn er
    fragt, aus welchem Lauf eine Empfehlung stammt.
    """

    if run is None:
        return ""

    teile = [run.run_id]

    if run.spec_key:
        teile.append(spec_label(run.spec_key))

    if run.character:
        teile.append(run.character)

    if run.started_at:
        teile.append(
            time.strftime("%d.%m.%Y %H:%M", time.localtime(run.started_at))
        )

    return " · ".join(teile)


def class_note(run: SimRun | None, expected_spec: str) -> str:

    if run is None or not run.weights_class:
        return ""

    expected = spec_of(expected_spec or "")

    if not expected or run.weights_class == expected.class_token:
        return ""

    return (
        f"Diese Ausgabe ist für {class_label(run.weights_class)} gerechnet, "
        f"gewählt ist {class_label(expected.class_token)} · {expected.label}."
    )


#
# --------------------------------------------------
# Korrelation: gehört das Abgelegte zu diesem Lauf?
# --------------------------------------------------
#
# ES GIBT KEINEN DRITTEN SPEICHER, UND DAS IST DIE ENTSCHEIDUNG.
#
# Naheliegend wäre eine `sim_runs.json` neben den beiden vorhandenen
# gewesen. Sie hätte nichts gekonnt, was diese Rechnung nicht kann: die
# Kennung hängt am Lauf (Charakter, Spec, Ausgangszustand, Zeitstempel
# des Exports) und lässt sich jederzeit aus dem neu gelesenen Export
# **wieder ausrechnen**. Was übrig bliebe, wäre eine dritte Datei, die
# genau dann veraltet, wenn sie gebraucht wird - und die Sorte
# Doppelung, an der die Sockelbewertung drüben schon einmal
# auseinandergelaufen ist.
#
# Die Korrelation liegt deshalb dort, wo die Daten liegen: als ein Feld
# auf den beiden Einträgen, die es ohnehin gibt.
#


@dataclass(frozen=True)
class Stored:
    """
    Was für diese Spezialisierung abgelegt ist - und ob es zu dem Lauf
    gehört, der gerade offen ist.

    `mixed` ist der Fall, den es zu verhindern gilt: eine Gewichtung
    aus dem Lauf von gestern neben einem Zielzustand von heute. Beide
    sehen für sich in Ordnung aus, zusammen sind sie eine Auskunft über
    zwei verschiedene Ausrüstungen.
    """

    weights_run: str = ""

    target_run: str = ""

    have_weights: bool = False

    have_target: bool = False

    @property
    def mixed(self) -> bool:

        if not (self.have_weights and self.have_target):
            return False

        #
        # Ohne Kennung auf einer der beiden Seiten wird NICHTS behauptet.
        # Eine von Hand getippte Gewichtung hat keine, und jeder Eintrag
        # von vor 3.3.0 ebenfalls - „gemischt" wäre dort eine Warnung
        # über etwas, das niemand nachsehen kann.
        #

        if not self.weights_run or not self.target_run:
            return False

        return self.weights_run != self.target_run

    def belongs(self, run_id: str) -> bool:
        """
        Ob beides zum offenen Lauf gehört. Ohne Kennung: unbekannt, und
        das heisst hier `False` ohne einen Satz darüber - der Aufrufer
        fragt vorher `mixed`.
        """

        if not run_id:
            return False

        return self.weights_run == run_id and self.target_run == run_id


def stored_state(weights_entry, target_entry) -> Stored:

    return Stored(
        weights_run=str(getattr(weights_entry, "run_id", "") or ""),
        target_run=str(getattr(target_entry, "run_id", "") or ""),
        have_weights=weights_entry is not None,
        have_target=target_entry is not None,
    )


def mixed_note(stored: Stored) -> str:
    """
    Der Satz für den einen Fall, den man einer Empfehlung im Spiel nicht
    ansieht.
    """

    if not stored.mixed:
        return ""

    return (
        "Achtung: die abgelegte Gewichtung und die abgelegte "
        "Zielausrüstung stammen aus zwei verschiedenen Sim-Läufen "
        f"({stored.weights_run} und {stored.target_run}). Füge beide "
        "Ausgaben desselben Laufs ein, dann passt es wieder zusammen."
    )
