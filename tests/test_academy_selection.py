"""
Wer ist "ich"? - die Charakterauswahl der Academy.

Diese Datei hält die Regeln fest, deren Verletzung dazu geführt hat,
dass im Spiel ein alter oder ein völlig fremder Charakter stand:

* **Die Auswahl rät nicht.** `resolve_player_name()` liefert nur, was
  gespeichert ist. Die Vermutung heißt `suggest_player_name()` und
  wird über `ensure_player_name()` festgeschrieben, bevor sie
  irgendwo wirkt - eine nur angezeigte Vermutung wäre wieder ein
  Name, den die Oberfläche kennt und die Nutzlast nicht.
* **Anzeige und Config können nicht auseinanderlaufen.**
  `reconcile_selection()` entscheidet, was die Auswahlbox zeigt, und
  schreibt genau das fest. Vorher füllte die Seite die Box neu und
  setzte die Auswahl nur, *wenn* der gespeicherte Name noch vorkam -
  fehlte er, stand die Box auf dem ersten Namen und die Config auf
  dem alten.
* **Der angemeldete Charakter gewinnt, eine Wahl von Hand gewinnt
  über ihn - aber nur für den Charakter, auf dem sie getroffen
  wurde.**

Die Auswahllogik liegt bewusst im Service und nicht in der Seite:
kein Test dieses Projekts baut ein Widget.
"""

import pytest

from analyzer.models import Actor, MetricEntry, RaidSnapshot

from core.academy_service import AcademyService
from core.paths import Paths


class _Logger:

    def __init__(self):
        self.infos = []

    def info(self, message):
        self.infos.append(message)

    def error(self, message):
        pass

    def success(self, message):
        pass

    def warning(self, message):
        pass


class _Config:

    def __init__(self):
        self.data = {
            "academy_player_name": "",
            "academy_follow_game": True,
            "academy_ingame_character": "",
            "academy_ingame_realm": "",
            "academy_player_source": "",
            "academy_manual_for": "",
        }
        self.saves = 0

    def save(self):
        self.saves += 1


class _RaidData:

    def __init__(self, snapshot):
        self.snapshot = snapshot

    def current(self):
        return self.snapshot


class _Sync:
    """
    Steht für AddonAnalysisSync. Wir zählen nur, ob zugestellt wurde -
    dass ein Auswahlwechsel SOFORT zustellt, ist der halbe Fix.
    """

    def __init__(self):
        self.published = 0

    def publish_now(self):
        self.published += 1


class _Manager:

    def __init__(self, snapshot=None):
        self.logger = _Logger()
        self.config = _Config()
        self.raid_data = _RaidData(snapshot or _snapshot())
        self.addon_analysis_sync = _Sync()


def _snapshot(*names) -> RaidSnapshot:

    names = names or ()

    return RaidSnapshot(
        captured_at=1000.0,
        source_label="Test",
        raid_size=25,
        pull_number=1,
        top_damage=tuple(
            MetricEntry(
                actor=Actor(name=name, class_name="Warrior", spec="Waffen", role="dps"),
                value=1000.0,
            )
            for name in names
        ),
    )


@pytest.fixture
def service(tmp_path, monkeypatch):

    monkeypatch.setattr(Paths, "config", staticmethod(lambda: tmp_path))

    def _make(*names):
        manager = _Manager(_snapshot(*names))
        return AcademyService(manager)

    return _make


# --------------------------------------------------
# resolve / suggest / ensure
# --------------------------------------------------


def test_resolve_raet_nicht(service):
    """
    Bis 1.6.2 kam hier der alphabetisch erste Raider heraus - bei
    jedem Snapshot neu und nie festgeschrieben. Damit ging ein Name
    ins Addon, den der Nutzer nie gewählt und nie gesehen hatte.
    """

    academy = service("Aldrin", "Bordrin")

    assert academy.resolve_player_name(academy.manager.raid_data.current()) == ""


def test_ensure_schreibt_die_vermutung_fest(service):

    academy = service("Bordrin", "Aldrin")
    snapshot = academy.manager.raid_data.current()

    assert academy.ensure_player_name(snapshot) == "Aldrin"

    # Jetzt liefert auch resolve etwas - weil es nicht mehr Vermutung ist.
    assert academy.resolve_player_name(snapshot) == "Aldrin"
    assert academy.manager.config.data["academy_player_name"] == "Aldrin"


def test_ensure_ist_idempotent_und_ueberschreibt_nichts(service):

    academy = service("Aldrin", "Bordrin")
    snapshot = academy.manager.raid_data.current()

    academy.set_player_name("Bordrin")

    assert academy.ensure_player_name(snapshot) == "Bordrin"
    assert academy.ensure_player_name(snapshot) == "Bordrin"


def test_der_angemeldete_charakter_schlaegt_die_alphabetische_reihenfolge(service):

    academy = service("Aldrin", "Bordrin")

    academy.manager.config.data["academy_ingame_character"] = "Bordrin"

    assert academy.suggest_player_name(academy.manager.raid_data.current()) == "Bordrin"


def test_ein_angemeldeter_charakter_ausserhalb_des_raids_zaehlt_nicht(service):
    """
    Sonst stünde eine Auswahl da, zu der es keine Daten gibt.
    """

    academy = service("Aldrin", "Bordrin")

    academy.manager.config.data["academy_ingame_character"] = "Cendrin"

    assert academy.suggest_player_name(academy.manager.raid_data.current()) == "Aldrin"


# --------------------------------------------------
# reconcile_selection - der eigentliche Fehler
# --------------------------------------------------


def test_eine_gueltige_auswahl_bleibt(service):

    academy = service()

    academy.set_player_name("Aldrin")

    assert academy.reconcile_selection(("Aldrin", "Bordrin")) == "Aldrin"


def test_eine_auswahl_ausserhalb_des_rosters_wird_ersetzt_UND_gespeichert(service):
    """
    Der Kern des gemeldeten Fehlers: die Auswahlbox zeigte den ersten
    Namen, die Config behielt den alten, und die Nutzlast ins Addon
    entsteht aus der Config.
    """

    academy = service()

    academy.set_player_name("Cendrin")

    assert academy.reconcile_selection(("Aldrin", "Bordrin")) == "Aldrin"
    assert academy.manager.config.data["academy_player_name"] == "Aldrin"


def test_ein_leeres_roster_leert_die_auswahl(service):

    academy = service()

    academy.set_player_name("Aldrin")

    assert academy.reconcile_selection(()) == ""
    assert academy.manager.config.data["academy_player_name"] == ""


def test_die_schreibweise_des_rosters_gewinnt(service):
    """
    Gespeichert werden muss, wie der Bericht schreibt - `find_actor()`
    sucht über genau diese Zeichenkette.
    """

    academy = service()

    academy.set_player_name("Aldrin")

    assert academy.reconcile_selection(("Aldrin-Everlook",)) == "Aldrin-Everlook"
    assert academy.manager.config.data["academy_player_name"] == "Aldrin-Everlook"


# --------------------------------------------------
# Sofortzustellung
# --------------------------------------------------


def test_ein_auswahlwechsel_stellt_sofort_zu(service):

    academy = service()

    academy.set_player_name("Aldrin")

    assert academy.manager.addon_analysis_sync.published == 1


def test_derselbe_name_stellt_nicht_erneut_zu(service):

    academy = service()

    academy.set_player_name("Aldrin")
    academy.set_player_name("Aldrin")

    assert academy.manager.addon_analysis_sync.published == 1


def test_eine_fehlende_zustellung_ist_kein_fehler(service, tmp_path, monkeypatch):
    """
    AcademyService entsteht in CompanionManager.__init__ VOR
    AddonAnalysisSync - das Attribut fehlt in diesem Fenster.
    """

    academy = service()

    del academy.manager.addon_analysis_sync

    academy.set_player_name("Aldrin")

    assert academy.player_name() == "Aldrin"
