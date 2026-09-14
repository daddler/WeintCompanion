"""
Zustandswerte des Raid-Kontexts: die drei Modi (live, archive, replay)
und die reinen Datenklassen `ArchiveState`/`ReplayState`.

Eine eigene, Qt-freie Datei aus demselben Grund wie
`core/raid_context.py`: diese Werte sind reine Daten, keine
Qt-Objekte, und werden auch von Stellen gebraucht, die kein PySide6
laden dürfen (`core/raid_context.py`, `gui/widgets/tv/encounter_meta.py`,
`addon/addon_payloads.py`, und Tests, die ausdrücklich Qt-frei bleiben
wollen wie `tests/test_raid_context.py`). Bis sie hierher zogen, kamen
sie aus `core/raid_data_service.py` - einer Datei, die mit
`QObject`/`Signal` unweigerlich PySide6 mit sich zieht, und riss damit
die "Qt-frei"-Kette jeder Datei ab, die diese Werte nur lesen wollte.

`core/raid_data_service.py` selbst importiert sie von hier und reicht
sie unverändert weiter, damit bestehender Code
(`from core.raid_data_service import MODE_LIVE, ArchiveState, …`)
unangetastet bleibt - nur Code, der PySide6 gerade nicht laden darf,
muss von hier importieren statt von dort.
"""

from __future__ import annotations

from dataclasses import dataclass

from analyzer.providers.warcraftlogs_payload import FightSummary, ReportSummary


#
# Zusätzlich zum Live-Feed kann WeintTV/die Academy einen einzelnen,
# längst abgeschlossenen WarcraftLogs-Fight ansehen (Report wählen ->
# Pull darin wählen). "Verlauf" ist als Name bewusst vermieden - das
# bezeichnet in WeintTV bereits die abgeschlossenen Pulls DIESER
# Live-Sitzung (siehe history()/PullSummary in raid_data_service.py);
# ein zweites "Verlauf" für etwas völlig anderes (ein beliebiger
# vergangener Report) wäre verwirrend.
#
# Der Modus ist bewusst global im Service verankert statt in einer
# einzelnen Seite: WeintTV und die Academy sollen beim Blick ins
# Archiv denselben Pull sehen, aus demselben Grund, aus dem sie schon
# denselben Live-Snapshot teilen.
#

MODE_LIVE = "live"

MODE_ARCHIVE = "archive"


#
# Wiedergabe: ein archivierter Pull wird Sekunde für Sekunde
# abgespielt. Bewusst ein weiterer Wert desselben `mode`-Feldes und
# kein zweites Flag - sonst gäbe es zwei Antworten auf die Frage
# "darf der Live-Poll gerade veröffentlichen?", und irgendwann
# überschreibt der Poll ein Wiedergabebild.
#

MODE_REPLAY = "replay"


@dataclass(frozen=True)
class ArchiveState:
    """
    Zustand der Archiv-Auswahl - ein Wert, den die Quellenansicht und
    der Kopfblock des Raid Centers unverändert übernehmen.

    Getrennte *_loading/*_error-Felder pro Schritt (Reports laden,
    Fights eines Reports laden, einen Fight laden), weil jeder Schritt
    unabhängig fehlschlagen oder noch laufen kann - ein einzelnes
    "loading"-Flag könnte nicht ausdrücken, dass z. B. die Reportliste
    längst da ist, aber gerade ein Fight nachlädt.
    """

    mode: str = MODE_LIVE

    reports: tuple[ReportSummary, ...] = ()

    reports_loading: bool = False

    reports_error: str = ""

    selected_report: str = ""

    fights: tuple[FightSummary, ...] = ()

    fights_loading: bool = False

    fights_error: str = ""

    selected_fight: int | None = None

    fight_loading: bool = False

    fight_error: str = ""

    #
    # Seit 3.6.0: woran die Oberfläche einen Fortschritt zeigen kann.
    #
    # `fight_started_at` ist eine Monotonzeit (`time.monotonic()`), 0.0
    # heisst "läuft gerade keiner" - keine Uhrzeit, weil eine
    # Systemuhr während des Wartens gestellt werden kann und der
    # Balken dann rückwärts liefe. `fight_expected` ist die Schätzung
    # aus core/loading_progress.py; 0.0 heisst dort ausdrücklich
    # "nicht abschätzbar" und nie "sofort fertig". `fight_label`
    # benennt, worauf gewartet wird - ohne ihn steht auf der Seite ein
    # Balken ohne Gegenstand.
    #

    fight_started_at: float = 0.0

    fight_expected: float = 0.0

    fight_label: str = ""

    # --------------------------------------------------

    def elapsed(self, now: float) -> float:
        """
        Wie lange der laufende Abruf schon dauert. 0.0, wenn keiner
        läuft.
        """

        if not self.fight_loading or self.fight_started_at <= 0:
            return 0.0

        return max(0.0, now - self.fight_started_at)

    # --------------------------------------------------

    @property
    def is_live(self) -> bool:

        return self.mode == MODE_LIVE

    @property
    def browsing(self) -> bool:
        """
        Ob gerade etwas anderes als der Live-Feed gezeigt wird - der
        eine Schalter, an dem der Live-Poll erkennt, dass er sein
        Ergebnis verwerfen muss.
        """

        return self.mode != MODE_LIVE


@dataclass(frozen=True)
class ReplayState:
    """
    Zustand der Wiedergabe - der Wert, den `ReplayBar` unverändert
    übernimmt.

    Getrennt von `ArchiveState`, obwohl der Modus in dessen `mode`
    steckt: die Archiv-Auswahl (welcher Bericht, welcher Pull) bleibt
    während der Wiedergabe unverändert bestehen, damit das Beenden
    der Wiedergabe wieder genau dort landet, wo man war.
    """

    #
    # `loading` heißt "eine Zeitleiste wird gerade geholt", `starting`
    # zusätzlich "und danach soll sofort abgespielt werden".
    #
    # Die Trennung ist nötig, seit die Zeitleiste bereits mit der Wahl
    # des Pulls im Hintergrund geladen wird (siehe
    # RaidDataService.select_archive_fight): währenddessen ist
    # `loading` wahr, ohne dass der Nutzer irgendetwas gedrückt hätte.
    # Der Wiedergabe-Knopf darf dann weder ausgegraut sein noch "Wird
    # geladen …" behaupten - er soll drückbar bleiben und den Start
    # eben vormerken.
    #

    loading: bool = False

    starting: bool = False

    error: str = ""

    duration: float = 0.0

    position: float = 0.0

    playing: bool = False

    speed: float = 1.0

    label: str = ""

    report_code: str = ""

    fight_id: int | None = None

    #
    # Modus, aus dem die Wiedergabe gestartet wurde - dorthin führt
    # das Beenden zurück.
    #

    origin: str = MODE_ARCHIVE

    # --------------------------------------------------

    @property
    def available(self) -> bool:

        return self.duration > 0

    @property
    def progress(self) -> float:

        if self.duration <= 0:
            return 0.0

        return max(0.0, min(1.0, self.position / self.duration))

    @property
    def clock(self) -> str:

        return _clock(self.position)

    @property
    def total_clock(self) -> str:

        return _clock(self.duration)


def _clock(value: float) -> str:

    total = max(0, int(value))

    return f"{total // 60:02d}:{total % 60:02d}"
