"""
Die Basis-URL des Bots - und warum sie sich überschreiben lässt.

Der Bot liegt bei einem Anbieter, der den Rechner bestimmt, auf dem
die Anwendung läuft, und ihn in den Hostnamen schreibt. Fällt der
Bauserver aus und die Anwendung zieht um, ändert sich die Adresse,
ohne dass am Bot etwas anders wäre. Fest verdrahtet kostete das jedes
Mal eine neue Fassung der Companion, die alle erst installieren
müssten - und bis dahin erreicht keine einzige den Bot mehr. Genau das
ist einmal passiert; diese Tests halten den Ausweg fest.
"""

from core import backend_config


def _neu_laden(monkeypatch, env=None, datei=None, tmp_path=None):
    """
    Das Modul mit gesetzter Umgebung neu einlesen - die Auflösung
    passiert beim Import, nicht bei jedem Zugriff.
    """

    if env is None:
        monkeypatch.delenv(backend_config.BOT_URL_ENV, raising=False)
    else:
        monkeypatch.setenv(backend_config.BOT_URL_ENV, env)

    if tmp_path is not None:

        monkeypatch.setattr(
            backend_config.Paths, "base", staticmethod(lambda: tmp_path)
        )

        ziel = tmp_path / "config"
        ziel.mkdir(parents=True, exist_ok=True)

        if datei is not None:
            (ziel / backend_config.BOT_URL_FILE).write_text(
                datei, encoding="utf-8"
            )

    return backend_config.resolve_bot_base_url()


# --------------------------------------------------
# Normalisierung
# --------------------------------------------------

def test_der_abschliessende_schraegstrich_faellt_weg():
    """
    Jede Aufrufstelle hängt ihren Pfad mit führendem Schrägstrich an -
    aus zweien würde sonst ein doppelter.
    """

    assert (
        backend_config.normalize_bot_url("https://x.jrnm.app/")
        == "https://x.jrnm.app"
    )


def test_unbrauchbares_wird_uebergangen():
    """
    Eine kaputte Adresse würde jeden Abruf stillschweigend scheitern
    lassen. Der eingebaute Wert ist der bessere Rateversuch.
    """

    for kaputt in ("", "   ", "unsinn", "weintcodex-bot.e.jrnm.app",
                   "https://", "ftp://x.jrnm.app", None):

        assert backend_config.normalize_bot_url(kaputt) == ""


def test_beide_schemata_zaehlen():

    assert backend_config.normalize_bot_url("http://localhost:8765")
    assert backend_config.normalize_bot_url("https://x.jrnm.app")


# --------------------------------------------------
# Die Reihenfolge
# --------------------------------------------------

def test_ohne_angabe_gilt_der_eingebaute_wert(monkeypatch, tmp_path):

    assert _neu_laden(monkeypatch, tmp_path=tmp_path) == (
        backend_config.DEFAULT_BOT_BASE_URL
    )


def test_die_umgebungsvariable_gewinnt(monkeypatch, tmp_path):
    """Der schnelle Weg, ohne eine Datei anzulegen."""

    ergebnis = _neu_laden(
        monkeypatch,
        env="https://aus-der-umgebung.example",
        datei="https://aus-der-datei.example",
        tmp_path=tmp_path,
    )

    assert ergebnis == "https://aus-der-umgebung.example"


def test_die_datei_gilt_fuer_den_dauerbetrieb(monkeypatch, tmp_path):

    ergebnis = _neu_laden(
        monkeypatch,
        datei="  https://aus-der-datei.example/\n",
        tmp_path=tmp_path,
    )

    assert ergebnis == "https://aus-der-datei.example"


def test_eine_kaputte_angabe_faellt_auf_den_eingebauten_wert_zurueck(
    monkeypatch, tmp_path
):

    ergebnis = _neu_laden(
        monkeypatch,
        env="unsinn",
        datei="auch unsinn",
        tmp_path=tmp_path,
    )

    assert ergebnis == backend_config.DEFAULT_BOT_BASE_URL


def test_das_lesen_legt_kein_verzeichnis_an(monkeypatch, tmp_path):
    """
    Ein Modulimport darf keine Verzeichnisse im Benutzerprofil
    erzeugen, nur weil eine Konstante gelesen wurde - deshalb wird
    Paths.config() hier bewusst nicht benutzt.
    """

    monkeypatch.delenv(backend_config.BOT_URL_ENV, raising=False)

    ziel = tmp_path / "unberuehrt"

    monkeypatch.setattr(
        backend_config.Paths, "base", staticmethod(lambda: ziel)
    )

    assert backend_config.resolve_bot_base_url() == (
        backend_config.DEFAULT_BOT_BASE_URL
    )

    assert not ziel.exists()


def test_die_adresse_zeigt_auf_den_bot(monkeypatch):
    """
    Der eingebaute Wert muss die Adresse sein, unter der der Bot
    tatsächlich läuft - acht Module hängen daran.
    """

    assert backend_config.DEFAULT_BOT_BASE_URL == (
        "https://weintcodex-bot.e.jrnm.app"
    )

    assert not backend_config.DEFAULT_BOT_BASE_URL.endswith("/")


# --------------------------------------------------
# Die Adresse von Hand setzen
# --------------------------------------------------
# Seit 2.4.4 nicht mehr nur lesbar, sondern auch schreibbar - und
# damit aus den Einstellungen heraus bedienbar. Der Grund steht oben:
# verschwindet der Name des Bots aus dem DNS, scheitert jeder Abruf,
# und der einzige Ausweg führte über eine von Hand angelegte Datei in
# einem Verzeichnis, das niemand auswendig kennt.

import pytest


def _ablage(monkeypatch, tmp_path):

    monkeypatch.setattr(
        backend_config.Paths, "base", staticmethod(lambda: tmp_path)
    )

    monkeypatch.delenv(backend_config.BOT_URL_ENV, raising=False)

    return tmp_path / "config" / backend_config.BOT_URL_FILE


def test_die_geschriebene_adresse_wird_danach_gelesen(monkeypatch, tmp_path):

    _ablage(monkeypatch, tmp_path)

    backend_config.write_bot_url_override("https://neu.example.app")

    assert backend_config.resolve_bot_base_url() == (
        "https://neu.example.app"
    )


def test_das_verzeichnis_wird_bei_bedarf_angelegt(monkeypatch, tmp_path):
    """
    `bot_url_override_path()` setzt den Pfad bewusst ohne
    `Paths.config()` zusammen, damit ein Modulimport keine
    Verzeichnisse erzeugt - beim Schreiben muss es dann aber
    entstehen dürfen.
    """

    pfad = _ablage(monkeypatch, tmp_path)

    assert not pfad.parent.exists()

    backend_config.write_bot_url_override("https://neu.example.app")

    assert pfad.is_file()


def test_eine_kaputte_adresse_wird_gar_nicht_erst_abgelegt(monkeypatch, tmp_path):
    """
    Dieselbe Linie wie beim Lesen, nur eine Stufe früher: eine
    unbrauchbare Angabe abzulegen hiesse, den einzigen Ausweg mit dem
    zu verstopfen, wogegen er hilft.
    """

    pfad = _ablage(monkeypatch, tmp_path)

    with pytest.raises(ValueError):
        backend_config.write_bot_url_override("weintcodex-bot.example.app")

    assert not pfad.exists()


def test_leer_raeumt_die_ablage(monkeypatch, tmp_path):
    """
    Der Weg zurück zur eingebauten Adresse - ohne ihn müsste man
    wissen, wie sie lautet, um sie wiederherzustellen.
    """

    pfad = _ablage(monkeypatch, tmp_path)

    backend_config.write_bot_url_override("https://neu.example.app")

    assert backend_config.write_bot_url_override("") == ""

    assert not pfad.exists()

    assert backend_config.resolve_bot_base_url() == (
        backend_config.DEFAULT_BOT_BASE_URL
    )


def test_raeumen_ohne_vorhandene_datei_ist_kein_fehler(monkeypatch, tmp_path):

    _ablage(monkeypatch, tmp_path)

    assert backend_config.write_bot_url_override("") == ""


def test_die_quelle_wird_benannt(monkeypatch, tmp_path):
    """
    Die Einstellungsseite zeigt sie an. Stünde dort eine Adresse aus
    der Umgebungsvariable, bliebe eine Eingabe im Feld folgenlos -
    von aussen nicht von einem kaputten Knopf zu unterscheiden.
    """

    _ablage(monkeypatch, tmp_path)

    assert backend_config.bot_url_source() == "default"

    backend_config.write_bot_url_override("https://aus-der-datei.example")

    assert backend_config.bot_url_source() == backend_config.BOT_URL_FILE

    monkeypatch.setenv(
        backend_config.BOT_URL_ENV, "https://aus-der-umgebung.example"
    )

    assert backend_config.bot_url_source() == backend_config.BOT_URL_ENV
