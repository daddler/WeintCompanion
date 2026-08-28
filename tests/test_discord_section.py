"""
Einstellungen -> Discord: der Ausweg, wenn der Bot umgezogen ist.

Der Fehlerbericht: "Weiterhin kein Login-Erfolg", dazu ein
Bildschirmfoto dieses Abschnitts mit

    Der letzte Versuch ist fehlgeschlagen: [Errno -2] Der Name oder
    der Dienst ist nicht bekannt

Der Name des Bots existierte im DNS nicht mehr - sein Anbieter
schreibt den Rechner in den Hostnamen, ein Umzug benennt ihn also um.
Die Adresse liess sich seit 2.0.12 überschreiben, aber nur über eine
von Hand angelegte Datei in einem Verzeichnis, das niemand auswendig
kennt: ein Ausweg, den man erst finden muss, ist im Ernstfall keiner.

Diese Datei hält fest, dass die Bedienelemente da sind **und wirken** -
aus demselben Grund, aus dem es `tests/test_appearance_section.py`
gibt: dass ein Bedienelement schlicht fehlt, sieht kein einziger der
übrigen Tests.
"""

import os

import pytest

pytest.importorskip("PySide6")

from core import backend_config


def _app():

    from PySide6.QtWidgets import QApplication

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    app = QApplication.instance()

    if app is None:
        app = QApplication([])

    return app


class _Protokoll:

    def __init__(self):
        self.zeilen = []

    def _merken(self, text):
        self.zeilen.append(text)

    error = info = warning = success = _merken


class _Konten:

    def load(self):
        return {}


class _Manager:

    def __init__(self):
        self.logger = _Protokoll()
        self.discord_account = _Konten()


def _abschnitt(monkeypatch, tmp_path):

    _app()

    monkeypatch.setattr(
        backend_config.Paths, "base", staticmethod(lambda: tmp_path)
    )

    monkeypatch.delenv(backend_config.BOT_URL_ENV, raising=False)

    from gui.pages.settings_sections.discord import DiscordSection

    return DiscordSection(_Manager())


# --------------------------------------------------

def test_die_adresse_laesst_sich_ueberhaupt_eintragen(monkeypatch, tmp_path):
    """
    Ohne dieses Feld ist ein Umzug des Bots für jeden Nutzer das
    Ende jeder Verbindung - bis eine neue Fassung der Companion
    erscheint und alle sie installiert haben.
    """

    abschnitt = _abschnitt(monkeypatch, tmp_path)

    abschnitt.address_input.setText("https://neu.example.app")

    abschnitt.save_address()

    assert backend_config.resolve_bot_base_url() == (
        "https://neu.example.app"
    )


def test_die_eingabe_wird_bereinigt_statt_abgewiesen(monkeypatch, tmp_path):
    """
    Eine kopierte Adresse bringt gern einen abschliessenden
    Schrägstrich mit; jede Aufrufstelle hängt ihren Pfad mit
    führendem an.
    """

    abschnitt = _abschnitt(monkeypatch, tmp_path)

    abschnitt.address_input.setText("  https://neu.example.app/  ")

    abschnitt.save_address()

    assert backend_config.resolve_bot_base_url() == (
        "https://neu.example.app"
    )


def test_eine_kaputte_adresse_wird_benannt_und_nicht_abgelegt(monkeypatch, tmp_path):
    """
    Sie stillschweigend zu übernehmen hiesse, den einzigen Ausweg
    mit dem zu verstopfen, wogegen er hilft.
    """

    abschnitt = _abschnitt(monkeypatch, tmp_path)

    abschnitt.address_input.setText("weintcodex-bot.example.app")

    abschnitt.save_address()

    assert backend_config.resolve_bot_base_url() == (
        backend_config.DEFAULT_BOT_BASE_URL
    )

    assert abschnitt.address_hint.text().startswith("Nicht gespeichert")


def test_leeren_fuehrt_zur_eingebauten_adresse_zurueck(monkeypatch, tmp_path):

    abschnitt = _abschnitt(monkeypatch, tmp_path)

    abschnitt.address_input.setText("https://neu.example.app")
    abschnitt.save_address()

    abschnitt.address_input.setText("")
    abschnitt.save_address()

    assert backend_config.resolve_bot_base_url() == (
        backend_config.DEFAULT_BOT_BASE_URL
    )


def test_der_neustart_wird_verlangt(monkeypatch, tmp_path):
    """
    Die acht lesenden Module holen die Adresse beim Import ab. Ohne
    diesen Satz probierte man es sofort erneut, scheiterte genauso -
    und hielte den Ausweg für kaputt.
    """

    abschnitt = _abschnitt(monkeypatch, tmp_path)

    abschnitt.address_input.setText("https://neu.example.app")
    abschnitt.save_address()

    assert "neu starten" in abschnitt.address_hint.text()


def test_die_umgebungsvariable_sperrt_das_feld(monkeypatch, tmp_path):
    """
    Sie gewinnt über die Datei. Ein Feld, dessen Eingabe folgenlos
    bleibt, ist von einem kaputten Knopf nicht zu unterscheiden.
    """

    _app()

    monkeypatch.setattr(
        backend_config.Paths, "base", staticmethod(lambda: tmp_path)
    )

    monkeypatch.setenv(
        backend_config.BOT_URL_ENV, "https://aus-der-umgebung.example"
    )

    from gui.pages.settings_sections.discord import DiscordSection

    abschnitt = DiscordSection(_Manager())

    assert not abschnitt.address_input.isEnabled()
    assert not abschnitt.address_save_button.isEnabled()
    assert backend_config.BOT_URL_ENV in abschnitt.address_hint.text()


def test_refresh_ueberschreibt_keine_halb_getippte_adresse(monkeypatch, tmp_path):
    """
    `refresh()` läuft bei jedem Betreten des Abschnitts und bei jeder
    `state_changed` - dieselbe Falle wie beim `ArchivePicker`.
    """

    abschnitt = _abschnitt(monkeypatch, tmp_path)

    abschnitt.address_input.setText("https://halb-getippt")

    abschnitt.refresh()

    assert abschnitt.address_input.text() == "https://halb-getippt"
