"""
Das Raid Center: ein Pull, vier Perspektiven.

Diese Datei baut Widgets - wie die anderen unter `tests/`, und aus
demselben Grund: die Fehler, um die es hier geht, sind von aussen
unsichtbar. Ein Perspektivwechsel, der den Pull verliert, ein
Charakterwechsel, der die Bewertung nicht nachzieht, ein Kopfblock, der
bei 1280 px seine Knöpfe abschneidet - keiner davon wirft eine
Ausnahme.

Geprüft wird genau die Kette, um die der Umbau gemacht wurde:

    Quelle  → ein Pull gewählt      → Analyse zeigt ihn
    Analyse → ein Spieler geklickt  → Lernen zeigt ihn, Pull bleibt
    Lernen  → ein Moment geklickt   → Wiedergabe an dieser Sekunde
    Live    ↔ Archiv                → **ein** Zustand, nicht zwei

`importorskip` und `QT_QPA_PLATFORM=offscreen` wie dort.
"""

import os
from dataclasses import replace

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

from analyzer.models import EncounterInfo
from analyzer.providers.mock import MockRaidDataProvider
from analyzer.providers.warcraftlogs_payload import FightSummary, ReportSummary

from core.config import Config
from core.raid_data_service import (
    ArchiveState,
    MODE_ARCHIVE,
    MODE_LIVE,
    MODE_REPLAY,
    ReplayState,
)
from gui.navigation import (
    RAID_VIEW_ANALYSIS,
    RAID_VIEW_KEYS,
    RAID_VIEW_LEARN,
    RAID_VIEW_LIVE,
    RAID_VIEW_SOURCE,
    RaidLink,
)
from gui.theme.theme_manager import init_theme


REPORT = ReportSummary(
    code="aBcDeF12",
    title="Mittwochsraid",
    zone="Belagerung von Orgrimmar",
    start="2026-09-02T18:30:00+02:00",
)

FIGHTS = (
    FightSummary(
        fight_id=1,
        encounter_id=1620,
        encounter_name="Immerseus",
        difficulty="25 Heroisch",
        kill=True,
        boss_percentage=0.0,
        duration=310.0,
        start="2026-09-02T18:41:00+02:00",
        size=25,
        pull_number=1,
    ),
    FightSummary(
        fight_id=3,
        encounter_id=1623,
        encounter_name="Garrosh Höllschrei",
        difficulty="25 Heroisch",
        kill=False,
        boss_percentage=42.0,
        duration=391.0,
        start="2026-09-02T21:43:00+02:00",
        size=25,
        pull_number=17,
    ),
)


class FakeService(QObject):
    """
    Der Datendienst, so weit das Raid Center ihn anspricht.

    Er **hält den Zustand selbst** - genau wie der echte. Das ist hier
    nicht nur Bequemlichkeit: die Prüfung, dass es keinen zweiten
    Archiv- und keinen zweiten Wiedergabezustand gibt, lässt sich nur
    an einer Attrappe führen, die der einzige Halter ist.
    """

    snapshotChanged = Signal(object)
    archiveChanged = Signal()
    replayChanged = Signal()
    sourceChanged = Signal()

    def __init__(self):

        super().__init__()

        self.calls = []

        self.attached = 0

        self._snapshot = MockRaidDataProvider()._combat_snapshot(3, 200.0)

        self.state = ArchiveState(mode=MODE_LIVE)

        self.replay = ReplayState()

    # -------------------------------------------------- Lesen

    def current(self):
        return self._snapshot

    def archive_state(self):
        return self.state

    def replay_state(self):
        return self.replay

    def replay_available(self):
        return self.replay.duration > 0

    def history(self):
        return ()

    def configured_source(self):
        return "mock"

    def active_source(self):
        return "mock"

    def set_source(self, source):
        self.calls.append(("source", source))
        return False

    # -------------------------------------------------- Anmelden

    def attach(self):
        self.attached += 1

    def detach(self):
        self.attached -= 1

    # -------------------------------------------------- Archiv

    def ensure_reports(self):

        self.calls.append("reports")

        self.state = replace(self.state, reports=(REPORT,))

        self.archiveChanged.emit()

    def enter_archive_mode(self):

        self.calls.append("enter")

        self.state = replace(self.state, mode=MODE_ARCHIVE, reports=(REPORT,))

        self.archiveChanged.emit()

    def show_live(self):

        self.calls.append("live")

        self.state = replace(self.state, mode=MODE_LIVE)

        self.archiveChanged.emit()

    def select_archive_report(self, code):

        self.calls.append(("report", code))

        self.state = replace(
            self.state,
            mode=MODE_ARCHIVE,
            selected_report=code,
            fights=FIGHTS,
        )

        self.archiveChanged.emit()

    def select_archive_fight(self, code, fight_id):

        self.calls.append(("fight", code, fight_id))

        self.state = replace(
            self.state,
            mode=MODE_ARCHIVE,
            reports=(REPORT,),
            fights=FIGHTS,
            selected_report=code,
            selected_fight=fight_id,
        )

        #
        # Der echte Dienst veröffentlicht den geholten Pull als Snapshot
        # (`_publish(..., track=False)`), und genau daraus liest der
        # Kopfblock Boss, Pullnummer und Bossanteil. Eine Attrappe, die
        # das unterlässt, würde dem Kontext genau die Hälfte
        # unterschlagen, auf die es hier ankommt.
        #

        fight = next(
            (entry for entry in FIGHTS if entry.fight_id == fight_id),
            None,
        )

        if fight is not None:

            self._snapshot = replace(
                self._snapshot,
                live=False,
                in_combat=False,
                encounter=EncounterInfo(
                    encounter_id=fight.encounter_id,
                    name=fight.encounter_name,
                    instance=REPORT.zone,
                    difficulty=fight.difficulty,
                    raid_size=fight.size,
                ),
                pull_number=fight.pull_number,
                pull_seconds=fight.duration,
                boss_health_percent=fight.boss_percentage,
            )

        self.archiveChanged.emit()

        self.snapshotChanged.emit(self._snapshot)

    # -------------------------------------------------- Wiedergabe

    def start_replay(self):

        self.calls.append("start_replay")

        #
        # Wie beim echten Dienst: die Zeitleiste ist noch nicht da, der
        # Start ist nur vorgemerkt.
        #

        self.replay = replace(self.replay, loading=True, starting=True)

        self.replayChanged.emit()

    def finish_timeline(self, duration=391.0):
        """
        Die Zeitleiste ist angekommen - der Schritt, auf den ein
        vorgemerkter Sprung wartet.
        """

        self.state = replace(self.state, mode=MODE_REPLAY)

        self.replay = replace(
            self.replay,
            loading=False,
            starting=False,
            duration=duration,
            playing=True,
        )

        self.replayChanged.emit()

    def seek_replay(self, seconds):
        self.calls.append(("seek", round(float(seconds), 3)))

    def set_replay_playing(self, playing):
        self.calls.append(("playing", bool(playing)))

    def stop_replay(self):
        self.calls.append("stop")

    def toggle_replay(self):
        self.calls.append("toggle")

    def set_replay_speed(self, speed):
        self.calls.append(("speed", speed))


class _Logger:

    def __getattr__(self, name):
        return lambda *args, **kwargs: None


@pytest.fixture(scope="module")
def qt_app():

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    app = QApplication.instance() or QApplication([])

    init_theme(Config())

    return app


@pytest.fixture
def page(qt_app):

    from core.academy_service import AcademyService
    from gui.pages.raid_center import RaidCenterPage

    class _Manager:

        def __init__(self):

            self.config = Config()

            self.logger = _Logger()

            self.raid_data = FakeService()

            self.academy = AcademyService(self)

    built = RaidCenterPage(_Manager())

    #
    # `on_enter()` ist der Weg, den `MainWindow.change_page()` nimmt -
    # ohne ihn wäre die Seite nicht angemeldet und zeichnete nicht.
    #

    built.on_enter()

    return built


def _service(page):

    return page.manager.raid_data


# --------------------------------------------------
# Ein Bereich, vier Perspektiven
# --------------------------------------------------


def test_all_four_perspectives_exist_and_can_be_shown(page):

    for key in RAID_VIEW_KEYS:

        page.show_view(key)

        assert page._view == key

        assert page._views[key] is not None


def test_a_view_is_built_on_first_use_and_not_at_startup(page):
    """
    Dieselbe Überlegung wie bei `MainWindow._ensure_page()`: alle vier
    im Voraus zu bauen kostete rund zwei Sekunden in dem Moment, in dem
    jemand das Raid Center zum ersten Mal öffnet - für drei Ansichten,
    die er dabei nicht sieht.
    """

    assert set(page._views) == {RAID_VIEW_LIVE}

    page.show_view(RAID_VIEW_LEARN)

    assert set(page._views) == {RAID_VIEW_LIVE, RAID_VIEW_LEARN}


def test_switching_the_perspective_keeps_the_pull(page):
    """
    Der Kern des Umbaus. Der Kopfblock steht ausserhalb des Stapels; ein
    Wechsel darf an Boss, Pull, Ausgang und Zeitpunkt nichts ändern.
    """

    _service(page).select_archive_fight("aBcDeF12", 3)

    before = (
        page.header.boss.text(),
        page.header.facts.text(),
        page.header.when.text(),
    )

    for key in RAID_VIEW_KEYS:

        page.show_view(key)

        assert (
            page.header.boss.text(),
            page.header.facts.text(),
            page.header.when.text(),
        ) == before


def test_only_the_visible_view_is_drawn(page):
    """
    Die Lernansicht baut je Bild ein vollständiges Profil und einen
    Trainingsplan, die Analyse sechs Tabellen. Das für drei Ansichten zu
    tun, die niemand ansieht, war schon zwischen WeintTV und der Academy
    die Doppelarbeit, gegen die dort `_attached` stand.
    """

    page.show_view(RAID_VIEW_LEARN)

    drawn = []

    for key, view in page._views.items():

        original = view.apply

        def record(snapshot, key=key, original=original):
            drawn.append(key)
            original(snapshot)

        view.apply = record

    page._on_snapshot(_service(page).current())

    assert drawn == [RAID_VIEW_LEARN]


def test_a_hidden_page_does_not_draw_at_all(page):
    """
    Der Dienst veröffentlicht weiter, während eine andere Seite im
    Vordergrund ist - bei einer laufenden Wiedergabe viermal je
    Sekunde.
    """

    page.on_leave()

    drawn = []

    view = page._views[RAID_VIEW_LIVE]

    view.apply = lambda snapshot: drawn.append(True)

    page._on_snapshot(_service(page).current())

    assert drawn == []


# --------------------------------------------------
# Quelle → Analyse
# --------------------------------------------------


def test_choosing_a_pull_in_the_source_view_shows_its_analysis(page):
    """
    Der Schritt, der bis 3.6.0 fehlte: die Archiv-Seite wählte aus und
    schrieb daneben "die Zahlen erscheinen in WeintTV" - richtig, und
    trotzdem ein Seitenwechsel von Hand.
    """

    page.show_view(RAID_VIEW_SOURCE)

    _service(page).select_archive_fight("aBcDeF12", 3)

    assert page._view == RAID_VIEW_ANALYSIS

    assert "Garrosh" in page.header.boss.text()


def test_a_pull_loaded_from_another_view_does_not_move_the_user(page):
    """
    Wer in der Analyse sitzt und dort einen Pull nachlädt, will dort
    bleiben. Umgeschaltet wird nur aus der Quellenansicht heraus.
    """

    page.show_view(RAID_VIEW_LEARN)

    _service(page).select_archive_fight("aBcDeF12", 3)

    assert page._view == RAID_VIEW_LEARN


def test_the_same_pull_arriving_twice_does_not_switch_again(page):
    """
    `archiveChanged` kommt während eines Ladevorgangs mehrfach. Ein
    Wechsel je Meldung riss den Nutzer aus der Ansicht, in der er
    gerade liest.
    """

    page.show_view(RAID_VIEW_SOURCE)

    _service(page).select_archive_fight("aBcDeF12", 3)

    assert page._view == RAID_VIEW_ANALYSIS

    page.show_view(RAID_VIEW_SOURCE)

    _service(page).archiveChanged.emit()

    assert page._view == RAID_VIEW_SOURCE


# --------------------------------------------------
# Analyse → Lernen
# --------------------------------------------------


def test_clicking_a_player_in_the_analysis_opens_learning_for_him(page):
    """
    Der Weg, der vorher über die Seitenleiste ging - und dort begann die
    Arbeit von vorn: Charakter wählen, Pull wiederfinden, Lektion
    suchen.
    """

    _service(page).select_archive_fight("aBcDeF12", 3)

    page.show_view(RAID_VIEW_ANALYSIS)

    name = _service(page).current().actor_names[2]

    page._views[RAID_VIEW_ANALYSIS].playerRequested.emit(name)

    assert page._view == RAID_VIEW_LEARN

    assert page.manager.academy.player_name() == name

    #
    # Und der Pull ist derselbe geblieben.
    #

    assert "Garrosh" in page.header.boss.text()


def test_the_analysis_filter_does_not_change_the_identity(page):
    """
    Die Raidansicht ist dazu da, sich auch andere anzusehen. Ein Blick
    auf den Kollegen darf die Ingame-Identität nicht umstellen (siehe
    `analyzer/names.py`).
    """

    page.show_view(RAID_VIEW_ANALYSIS)

    view = page._views[RAID_VIEW_ANALYSIS]

    before = page.manager.academy.player_name()

    index = view.player_filter.findData(
        _service(page).current().actor_names[1]
    )

    view.player_filter.setCurrentIndex(index)

    assert page.manager.academy.player_name() == before


def test_a_character_change_redraws_the_rating(page):
    """
    Ein Charakterwechsel im Kopfblock wechselt den ganzen Lernstand,
    ohne dass eine einzelne Lektion anders aussieht - die Signatur des
    Plans sieht das nicht, deshalb muss sie verworfen werden.
    """

    page.show_view(RAID_VIEW_LEARN)

    learn = page._views[RAID_VIEW_LEARN]

    names = _service(page).current().actor_names

    page.header.show_player(names[0])

    page._on_character_changed(names[0])

    first = learn.profile_name.text()

    page.header.show_player(names[1])

    page._on_character_changed(names[1])

    assert learn.profile_name.text() != first

    assert learn.profile_name.text() == names[1]


# --------------------------------------------------
# Lernen → Wiedergabe
# --------------------------------------------------


def test_a_moment_starts_the_replay_and_jumps_once_it_is_loaded(page):
    """
    Der Sprung kann erst ausgeführt werden, wenn die Zeitleiste da ist -
    bis dahin wartet er vorgemerkt. Ohne diese Reihenfolge landete
    `seek_replay()` auf einer Wiedergabe der Länge 0.
    """

    service = _service(page)

    service.select_archive_fight("aBcDeF12", 3)

    page.show_view(RAID_VIEW_LEARN)

    page._views[RAID_VIEW_LEARN].momentRequested.emit(221.0)

    assert "start_replay" in service.calls

    assert page._pending_seek == 221.0

    #
    # Angesehen wird der Moment in der Live-Ansicht: sie ist die, die
    # den Kampf zeigt.
    #

    assert page._view == RAID_VIEW_LIVE

    #
    # Noch kein Sprung - die Zeitleiste fehlt.
    #

    assert ("seek", 221.0) not in service.calls

    service.finish_timeline()

    assert ("seek", 221.0) in service.calls

    #
    # Und angehalten: man will den Moment ansehen, nicht ab ihm
    # weiterlaufen.
    #

    assert ("playing", False) in service.calls

    assert page._pending_seek is None


def test_a_moment_during_a_running_replay_jumps_straight_away(page):

    service = _service(page)

    service.select_archive_fight("aBcDeF12", 3)

    service.finish_timeline()

    page.show_view(RAID_VIEW_LEARN)

    page._views[RAID_VIEW_LEARN].momentRequested.emit(64.0)

    assert ("seek", 64.0) in service.calls

    assert page._pending_seek is None


def test_a_replay_notice_without_a_pending_jump_does_nothing(page):
    """
    `replayChanged` kommt bei jedem Takt der Wiedergabe. Ein Sprung je
    Meldung hielte sie dauerhaft an derselben Sekunde fest.
    """

    service = _service(page)

    service.finish_timeline()

    service.calls.clear()

    service.replayChanged.emit()

    assert not [call for call in service.calls if call and call[0] == "seek"]


# --------------------------------------------------
# Ein Zustand, nicht zwei
# --------------------------------------------------


def test_the_page_holds_no_archive_and_no_replay_state(page):
    """
    Die wichtigste Prüfung dieser Datei. `RaidDataService` ist und
    bleibt die einzige Wahrheit über Modus, Archivauswahl und
    Wiedergabe; ein zweiter Halter daneben wären zwei Wahrheiten über
    denselben Pull.

    Geprüft wird über die Attribute: was die Seite nicht speichert, kann
    auch nicht veralten.
    """

    _service(page).select_archive_fight("aBcDeF12", 3)

    for key in RAID_VIEW_KEYS:
        page.show_view(key)

    held = {
        name
        for name in vars(page)
        if isinstance(getattr(page, name), (ArchiveState, ReplayState))
    }

    assert not held

    for view in page._views.values():

        held = {
            name
            for name in vars(view)
            if isinstance(getattr(view, name), (ArchiveState, ReplayState))
        }

        assert not held, type(view).__name__


def test_the_mode_comes_from_the_service_in_every_view(page):

    service = _service(page)

    service.select_archive_fight("aBcDeF12", 3)

    for key in RAID_VIEW_KEYS:

        page.show_view(key)

        assert page.header.mode.label.text() == "ARCHIV"

    service.show_live()

    for key in RAID_VIEW_KEYS:

        page.show_view(key)

        assert page.header.mode.label.text() != "ARCHIV"


def test_the_way_back_to_the_running_raid_is_one_button(page):

    service = _service(page)

    service.select_archive_fight("aBcDeF12", 3)

    page.header.live_button.click()

    assert "live" in service.calls

    assert service.archive_state().mode == MODE_LIVE


# --------------------------------------------------
# Tiefenverweise von aussen
# --------------------------------------------------


def test_a_deep_link_loads_the_pull_then_the_character_then_the_view(page):
    """
    Die Reihenfolge ist die Aussage. Andersherum stünde für einen
    Moment der alte Pull mit dem neuen Charakter da.
    """

    service = _service(page)

    name = service.current().actor_names[1]

    page.open(
        RaidLink(
            view=RAID_VIEW_LEARN,
            report_code="aBcDeF12",
            fight_id=3,
            player=name,
        )
    )

    assert ("fight", "aBcDeF12", 3) in service.calls

    assert page.manager.academy.player_name() == name

    assert page._view == RAID_VIEW_LEARN


def test_a_deep_link_without_a_pull_keeps_the_loaded_one(page):
    """
    `RaidLink(view=…)` heisst "derselbe Kampf, anderer Blick". Eine
    halbe Kennung darf die bestehende Auswahl nicht verwerfen.
    """

    service = _service(page)

    service.select_archive_fight("aBcDeF12", 3)

    service.calls.clear()

    page.open(RaidLink(view=RAID_VIEW_LEARN))

    assert not [call for call in service.calls if call and call[0] == "fight"]

    assert service.archive_state().selected_fight == 3


def test_a_deep_link_does_not_refetch_a_pull_that_is_already_loaded(page):
    """
    Ein archivierter Pull kostet den Bot Minuten. Ein erneuter Abruf
    desselben wäre reine Wartezeit.
    """

    service = _service(page)

    service.select_archive_fight("aBcDeF12", 3)

    service.calls.clear()

    page.open(RaidLink(view=RAID_VIEW_ANALYSIS, report_code="aBcDeF12", fight_id=3))

    assert not [call for call in service.calls if call and call[0] == "fight"]


def test_a_deep_link_with_a_second_jumps_into_the_replay(page):

    service = _service(page)

    page.open(
        RaidLink(report_code="aBcDeF12", fight_id=3, seconds=120.0)
    )

    assert page._pending_seek == 120.0

    service.finish_timeline()

    assert ("seek", 120.0) in service.calls


# --------------------------------------------------
# Module
# --------------------------------------------------


def test_a_disabled_module_costs_one_perspective_not_the_area(page):
    """
    Bis 3.6.0 leerte derselbe Schalter einen ganzen Navigationspunkt.
    Jetzt bleibt der Bereich nutzbar: wer die Academy abgeschaltet hat,
    sieht Live, Analyse und Quelle unverändert.
    """

    page.manager.config.data["academy_enabled"] = False

    page.show_view(RAID_VIEW_LEARN)

    assert page.disabled_notice.isVisibleTo(page)

    assert "WeintAcademy" in page.disabled_title.text()

    page.show_view(RAID_VIEW_SOURCE)

    assert not page.disabled_notice.isVisibleTo(page)

    page.manager.config.data["academy_enabled"] = True


def test_a_disabled_module_is_not_evaluated_either(page):
    """
    Ein abgeschaltetes Modul darf auch nicht im Hintergrund rechnen -
    sonst kostet es weiter, was es sparen soll.
    """

    page.show_view(RAID_VIEW_LEARN)

    page.manager.config.data["academy_enabled"] = False

    drawn = []

    page._views[RAID_VIEW_LEARN].apply = lambda snapshot: drawn.append(True)

    page._draw(_service(page).current())

    assert drawn == []

    page.manager.config.data["academy_enabled"] = True


# --------------------------------------------------
# Kleine Fenstergrößen (§14)
# --------------------------------------------------


@pytest.mark.parametrize("width,height", [
    (1440, 900),
    (1366, 768),
    (1280, 720),
    (960, 640),
])
def test_the_header_keeps_its_primary_actions_at_every_size(
    page,
    width,
    height,
):
    """
    Keine abgeschnittenen Primary Actions (§14). Geprüft wird die
    **gerechnete** Mindestbreite gegen die verfügbare: ein Kopfblock,
    dessen Inhalt breiter ist als sein Platz, schneidet rechts ab, und
    rechts stehen genau die beiden Knöpfe.
    """

    from gui.layout.breakpoints import resolve

    _service(page).select_archive_fight("aBcDeF12", 3)

    page.on_layout_changed(resolve(width))

    #
    # Die Seite bekommt die Fensterbreite abzüglich der eingeklappten
    # Navigationsspalte (das Raid Center klappt sie immer ein).
    #

    page.resize(width - 72, height - 40)

    page.layout().activate()

    for key in RAID_VIEW_KEYS:

        page.show_view(key)

        page.layout().activate()

        assert page.header.minimumSizeHint().width() <= page.header.width(), key

        assert page.hint.width() > 0, key


def test_the_header_stacks_instead_of_clipping_on_a_narrow_window(page):
    """
    Nebeneinander bräuchten Kennung und Bedienelemente zusammen rund
    900 px - und die Knöpfe wären die Hälfte, die abgeschnitten wird.
    Umgehängt und nicht neu gebaut: ein Neubau je Fenstergrösse verlöre
    den Stand der Auswahlbox.
    """

    from gui.layout.breakpoints import resolve

    box = page.header.character_box

    page.on_layout_changed(resolve(1440))

    assert not page.header._stacked

    page.on_layout_changed(resolve(900))

    assert page.header._stacked

    assert page.header.character_box is box

    #
    # Und zurück: die Wahl des Nutzers bleibt unberührt.
    #

    page.on_layout_changed(resolve(1440))

    assert not page.header._stacked


def test_every_view_scrolls_for_itself_so_the_header_stays(page):
    """
    Ein Scrollbereich um die *Seite* würde den Kopfblock beim ersten
    Rollen mitnehmen - und damit genau das aufgeben, worum es hier geht.
    """

    from PySide6.QtWidgets import QScrollArea

    for key in RAID_VIEW_KEYS:
        page.show_view(key)

    scrolled = {
        key
        for key, container in page._containers.items()
        if isinstance(container, QScrollArea)
    }

    assert scrolled == set(RAID_VIEW_KEYS)

    #
    # Der Kopfblock hängt nicht im Stapel - deshalb bleibt er stehen.
    #

    assert page.stack.indexOf(page.header) == -1


def test_the_source_view_needs_no_outer_scrollbar_at_1280x720(page):
    """
    Die Quellenansicht rollt schon in zwei eigenen Spalten. Ein
    äusserer Balken wäre ein Rad in einem Rad, sobald er regelmässig
    erschiene - er ist nur das Netz für die Mindestgrösse.
    """

    from gui.layout.breakpoints import resolve

    page.on_layout_changed(resolve(1280))

    page.resize(1280 - 72, 720 - 40)

    page.show_view(RAID_VIEW_SOURCE)

    page.layout().activate()

    area = page._containers[RAID_VIEW_SOURCE]

    view = page._views[RAID_VIEW_SOURCE]

    assert view.minimumSizeHint().height() <= area.viewport().height()
