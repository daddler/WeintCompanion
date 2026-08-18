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
