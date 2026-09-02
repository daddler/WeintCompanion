"""
Wann sagt die Anwendung, dass sich Downloads und Backups anhäufen?

Jede Addon-Aktualisierung legt zwei Dateien an, die danach niemand
mehr anfasst - das Archiv unter `downloads/` und die Sicherung unter
`backups/`. Gelöscht wird beides nie von selbst, und bis 2.7.1 wies
auch nichts darauf hin: die Zahlen standen allein unter
*Einstellungen → Backups*, wohin niemand geht, der nichts sucht.

Geprüft wird hier die Entscheidung, nicht die Anzeige - genau die
Aufteilung, aus der `core/storage_usage.py` Qt-frei ist:

- die Grenze ("mehr als fünf") und dass sie **je Ordner** gilt,
- dass ein fehlender Ordner leer ist und kein Fehler,
- dass der Bericht Änderungen meldet und nicht Zählungen
  (`StorageWatch.process()`),
- und dass die Meldung sich nicht nach jeder einzelnen neuen Datei
  wiederholt.
"""

import types

import pytest

from core import storage_usage
from core.storage_usage import WARN_COUNT


def _fill(path, count, size=1024):

    path.mkdir(parents=True, exist_ok=True)

    for index in range(count):

        (path / f"datei_{index}.zip").write_bytes(b"x" * size)

    return path


# --------------------------------------------------
# Die Grenze
# --------------------------------------------------


def test_fuenf_dateien_sind_noch_kein_befund(tmp_path):
    """
    "Mehr als fünf" heisst ab der sechsten. Eine Aktualisierung darf
    ihr Archiv und ihre Sicherung hinterlassen, ohne dass das gleich
    gemeldet wird.
    """

    report = storage_usage.scan(
        _fill(tmp_path / "d", WARN_COUNT),
        _fill(tmp_path / "b", WARN_COUNT),
    )

    assert not report.needs_cleanup

    assert report.crowded == ()


def test_ab_der_sechsten_datei_wird_gemeldet(tmp_path):

    report = storage_usage.scan(
        _fill(tmp_path / "d", WARN_COUNT + 1),
        _fill(tmp_path / "b", 0),
    )

    assert report.needs_cleanup

    assert [f.key for f in report.crowded] == [storage_usage.DOWNLOADS]


def test_die_beiden_ordner_werden_nicht_zusammengezaehlt(tmp_path):
    """
    Drei Downloads und vier Backups sind nicht sieben Dateien: es sind
    zwei verschiedene Aufräumarbeiten mit zwei verschiedenen Knöpfen.
    Ein gemeinsamer Zähler würde melden, wo in keinem der beiden
    Ordner etwas zu tun ist.
    """

    report = storage_usage.scan(
        _fill(tmp_path / "d", 3),
        _fill(tmp_path / "b", 4),
    )

    assert not report.needs_cleanup


def test_ein_fehlender_ordner_ist_leer_und_kein_fehler(tmp_path):

    report = storage_usage.scan(
        tmp_path / "gibt-es-nicht",
        None,
    )

    assert report.downloads.count == 0

    assert report.backups.count == 0

    assert not report.needs_cleanup


def test_unterordner_zaehlen_nicht_mit(tmp_path):
    """
    Dieselbe Zählweise, mit der *Einstellungen → Backups* seit jeher
    zählt und löscht - der Knopf dort räumt ausschliesslich Dateien
    weg, also darf die Zahl daneben auch nur Dateien nennen.
    """

    folder = _fill(tmp_path / "b", 2)

    (folder / "unterordner").mkdir()

    report = storage_usage.scan(None, folder)

    assert report.backups.count == 2


# --------------------------------------------------
# Was dasteht
# --------------------------------------------------


def test_die_menge_steht_neben_der_zahl(tmp_path):
    """
    Eine Zahl allein sagt nicht, worum es geht: sechs Addon-Backups
    sind wenige Megabyte, sechs Companion-Archive fast ein Gigabyte.
    """

    report = storage_usage.scan(
        None,
        _fill(tmp_path / "b", 6, size=2 * 1024 * 1024),
    )

    text = storage_usage.folder_text(report.backups)

    assert "6 Backups" in text

    assert "MB" in text


def test_ein_leerer_ordner_behauptet_keine_menge(tmp_path):

    report = storage_usage.scan(tmp_path / "leer", None)

    assert "MB" not in storage_usage.folder_text(report.downloads)


def test_der_hinweis_steht_nur_ueber_der_grenze(tmp_path):

    wenige = storage_usage.scan(None, _fill(tmp_path / "b", 2)).backups

    viele = storage_usage.scan(None, _fill(tmp_path / "c", 9)).backups

    assert storage_usage.folder_hint(wenige) == ""

    assert storage_usage.folder_hint(viele) != ""


def test_die_meldung_nennt_beide_ordner_in_einem_satz(tmp_path):
    """
    Zwei Meldungen übereinander wären zweimal derselbe Weg zu
    demselben Knopf.
    """

    report = storage_usage.scan(
        _fill(tmp_path / "d", 7),
        _fill(tmp_path / "b", 8),
    )

    text = storage_usage.cleanup_text(report)

    assert "7 Downloads" in text

    assert "8 Backups" in text


def test_ohne_befund_gibt_es_keinen_satz(tmp_path):

    report = storage_usage.scan(_fill(tmp_path / "d", 1), None)

    assert storage_usage.cleanup_text(report) == ""


# --------------------------------------------------
# Der Wächter meldet Änderungen, nicht Zählungen
# --------------------------------------------------


def _watch(monkeypatch, tmp_path):

    from core import storage_watch as module

    downloads = tmp_path / "downloads"
    backups = tmp_path / "backups"

    downloads.mkdir(parents=True, exist_ok=True)
    backups.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        module.Paths,
        "downloads",
        staticmethod(lambda: downloads),
    )

    monkeypatch.setattr(
        module.Paths,
        "backups",
        staticmethod(lambda: backups),
    )

    return module.StorageWatch(), downloads, backups


def test_der_erste_durchgang_zaehlt_und_meldet_nichts(monkeypatch, tmp_path):
    """
    Nichts da, nichts geändert - `process()` darf die sichtbare Seite
    nicht neu zeichnen lassen, nur weil zum ersten Mal gezählt wurde.
    """

    watch, _, _ = _watch(monkeypatch, tmp_path)

    assert watch.process() is False

    assert watch.report.needs_cleanup is False


def test_eine_neue_datei_wird_gemeldet(monkeypatch, tmp_path):

    watch, downloads, _ = _watch(monkeypatch, tmp_path)

    watch.process()

    _fill(downloads, 3)

    #
    # Der träge Takt läuft noch: ohne invalidate() wird nicht neu
    # gezählt, und genau das ist der Sinn - die Ordner ändern sich
    # durch eine Installation oder durch das Aufräumen, und beide
    # melden sich selbst.
    #

    assert watch.process() is False

    watch.invalidate()

    assert watch.process() is True

    assert watch.report.downloads.count == 3


def test_derselbe_stand_wird_kein_zweites_mal_gemeldet(monkeypatch, tmp_path):

    watch, downloads, _ = _watch(monkeypatch, tmp_path)

    _fill(downloads, 9)

    assert watch.refresh() is True

    assert watch.refresh() is False


def test_der_bericht_ist_nie_none(monkeypatch, tmp_path):
    """
    Vor der ersten Zählung steht der leere Bericht da. Sonst müsste
    jede lesende Stelle "noch nicht gezählt" von "nichts da"
    unterscheiden - und beide verlangen dasselbe, nämlich keine
    Meldung.
    """

    from core.storage_watch import StorageWatch

    assert StorageWatch().report.needs_cleanup is False


# --------------------------------------------------
# Die Meldung: einmal, und nicht nach jeder neuen Datei
# --------------------------------------------------


def _announce(state, downloads=0, backups=0, memo=None):
    """
    Ruft das echte `MainWindow._announce_storage()` auf einem
    Platzhalter auf - ohne ein Fenster zu bauen, wie
    `tests/test_live_updates.py` es mit `_run_sync_worker()` tut.

    `state` ist der Merker, der zwischen zwei Aufrufen stehenbleibt.
    Zurück kommt die Liste der Meldungstexte dieses Aufrufs.
    """

    pytest.importorskip("PySide6")

    from gui.main_window import MainWindow

    posted = []

    report = storage_usage.StorageReport(
        downloads=storage_usage.FolderUsage(
            storage_usage.DOWNLOADS, downloads, downloads * 1024,
        ),
        backups=storage_usage.FolderUsage(
            storage_usage.BACKUPS, backups, backups * 1024,
        ),
    )

    fake = types.SimpleNamespace(
        manager=types.SimpleNamespace(
            storage_watch=types.SimpleNamespace(report=report),
        ),
        _announced_storage=state,
        notify=lambda text, variant, action: posted.append(text),
        _announce_in_tray=lambda text: None,
        _open_storage_section=lambda: None,
    )

    MainWindow._announce_storage(fake)

    return posted


def test_unter_der_grenze_wird_nichts_gemeldet():

    assert _announce({}, downloads=WARN_COUNT) == []


def test_gemeldet_wird_einmal_und_nicht_bei_jedem_durchgang():
    """
    `state_changed` kommt beim Start, bei jedem "Erneut prüfen" und aus
    dem Hintergrundtakt. Eine Meldung je Durchgang wäre eine, die man
    wegklickt, ohne sie zu lesen.
    """

    state = {}

    assert len(_announce(state, downloads=6)) == 1

    assert _announce(state, downloads=6) == []


def test_eine_einzelne_neue_datei_meldet_sich_nicht_erneut():

    state = {}

    _announce(state, backups=6)

    assert _announce(state, backups=7) == []


def test_nach_fuenf_weiteren_dateien_wird_wieder_gemeldet():

    state = {}

    _announce(state, backups=6)

    assert len(_announce(state, backups=6 + WARN_COUNT)) == 1


def test_nach_dem_aufraeumen_zaehlt_der_naechste_ueberlauf_wieder():
    """
    Wer aufgeräumt hat, soll beim nächsten Volllaufen wieder etwas
    hören - sonst bliebe die einmal gegebene Meldung für immer die
    letzte.
    """

    state = {}

    _announce(state, downloads=6)

    _announce(state, downloads=0)

    assert len(_announce(state, downloads=6)) == 1
