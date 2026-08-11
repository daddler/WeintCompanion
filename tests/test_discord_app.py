"""
Die Discord-Anwendung finden - statt zu hoffen, dass ein Öffner es
schon richten wird.

Der gemeldete Fehler: der Knopf "Aufstellung im Discord" öffnete
unter Linux den Browser mit `http://discord//-/channels/1311…`. Die
Ursache war kein Tippfehler in der Adresse, sondern eine Frage, die
falsch gestellt war. `xdg-open discord://…` liefert auch dann 0, wenn
für `x-scheme-handler/discord` **nichts** eingetragen ist: es reicht
die Adresse dann an den Standard-Browser weiter, und der macht aus
einem Schema, das er nicht kennt, eine http-Adresse. Der
Rückgabewert war also nie die Antwort auf "gibt es dafür ein
Programm?".

Deshalb wird hier vorher gesucht. Die Tests decken die drei Stellen
ab, an denen das schiefgehen kann: ein eingetragener Eintrag, der in
Wahrheit ein Browser ist; eine Installationsform, die niemand
bedacht hat; und die Frage, ob bei erfolgloser Suche wirklich nichts
gestartet wird (sonst wäre der Browser mit dem kaputten Link wieder
da).
"""

from pathlib import Path

import pytest

from core import discord_app


URL = "discord://-/channels/1311060525555257364/1311325324008751225"


# --------------------------------------------------
# Eine Umgebung ohne echtes System darunter
# --------------------------------------------------


@pytest.fixture
def linux(monkeypatch):

    from core.runtime import Runtime

    monkeypatch.setattr(Runtime, "is_windows", staticmethod(lambda: False))
    monkeypatch.setattr(Runtime, "is_macos", staticmethod(lambda: False))

    #
    # Kein Programm im PATH, kein flatpak, kein xdg-mime: was ein
    # Test finden soll, richtet er selbst ein. Sonst entschiede der
    # Rechner, auf dem die Testsuite läuft, über das Ergebnis.
    #

    monkeypatch.setattr(discord_app.shutil, "which", lambda name: None)

    monkeypatch.setattr(discord_app, "BINARY_PATHS", ())

    monkeypatch.setattr(discord_app, "APPIMAGE_DIRS", ())


@pytest.fixture
def applications(tmp_path, monkeypatch):
    """
    Ein Ordner für `.desktop`-Einträge, den `_data_dirs()` findet.
    """

    folder = tmp_path / "share" / "applications"

    folder.mkdir(parents=True)

    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "share"))

    monkeypatch.setenv("XDG_DATA_DIRS", "")

    return folder


def _entry(folder: Path, name: str, exec_line: str) -> Path:

    path = folder / name

    path.write_text(
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=Discord\n"
        f"Exec={exec_line}\n",
        encoding="utf-8",
    )

    return path


def _handler(monkeypatch, name: str):

    monkeypatch.setattr(discord_app, "scheme_handler", lambda: name)


# --------------------------------------------------
# Der eingetragene Programm-Eintrag
# --------------------------------------------------


def test_the_registered_client_wins(linux, applications, monkeypatch):

    _entry(applications, "discord.desktop", "/usr/bin/discord %u")

    _handler(monkeypatch, "discord.desktop")

    assert discord_app.find_launcher(URL) == ["/usr/bin/discord", URL]


def test_a_browser_registered_for_the_scheme_is_refused(
    linux, applications, monkeypatch
):
    """
    **Der gemeldete Fehler.** Firefox legt für ein einmal bestätigtes
    "Anwendung wählen" eine `userapp-Discord-XXXX.desktop` an, deren
    `Exec` auf Firefox zeigt. Wer nur auf den Namen schaut, liest
    dort "Discord" und startet den Browser - mit einer Adresse, die
    dieser in `http://discord//-/channels/…` verwandelt.
    """

    _entry(
        applications,
        "userapp-Discord-a1b2c3.desktop",
        "/usr/lib/firefox/firefox %u",
    )

    _handler(monkeypatch, "userapp-Discord-a1b2c3.desktop")

    assert discord_app.find_launcher(URL) == []


def test_a_registered_entry_whose_file_is_gone_is_no_answer(
    linux, applications, monkeypatch
):

    _handler(monkeypatch, "discord.desktop")

    assert discord_app.find_launcher(URL) == []


def test_a_third_party_client_counts_as_discord(
    linux, applications, monkeypatch
):
    """
    Wer Vesktop benutzt, hat genau den für `discord://` eingetragen.
    Ihn zu verwerfen hieße, ihn zugunsten des Browsers zu übergehen.
    """

    _entry(applications, "vesktop.desktop", "/usr/bin/vesktop %U")

    _handler(monkeypatch, "vesktop.desktop")

    assert discord_app.find_launcher(URL) == ["/usr/bin/vesktop", URL]


def test_the_flatpak_field_codes_do_not_end_up_as_arguments(
    linux, applications, monkeypatch
):
    """
    Flatpaks `Exec` trägt die Markierungen des Dateiweiterreichens
    (`@@u … @@`). Als Argumente übergeben wären sie für Discord eine
    Adresse, die es nicht gibt.
    """

    _entry(
        applications,
        "com.discordapp.Discord.desktop",
        "/usr/bin/flatpak run --branch=stable --arch=x86_64 "
        "--file-forwarding com.discordapp.Discord @@u %u @@",
    )

    _handler(monkeypatch, "com.discordapp.Discord.desktop")

    argv = discord_app.find_launcher(URL)

    assert argv[-1] == URL

    assert "@@" not in argv

    assert "@@u" not in argv

    assert "com.discordapp.Discord" in argv


def test_an_exec_without_a_placeholder_still_carries_the_address(
    linux, applications, monkeypatch
):
    """
    Ein Eintrag ohne `%u` ist kein Grund, die Adresse fallenzulassen -
    sonst öffnete sich Discord auf dem zuletzt gesehenen Kanal, und
    der Knopf hätte scheinbar funktioniert.
    """

    _entry(applications, "discord.desktop", "/usr/bin/discord")

    _handler(monkeypatch, "discord.desktop")

    assert discord_app.find_launcher(URL) == ["/usr/bin/discord", URL]


def test_only_the_desktop_entry_section_is_read(applications):
    """
    Die `[Desktop Action …]`-Blöcke darunter haben eigene
    `Exec`-Zeilen ("Neues Fenster"), die keine Adresse annehmen.
    """

    path = applications / "discord.desktop"

    path.write_text(
        "[Desktop Entry]\n"
        "Exec=/usr/bin/discord %u\n"
        "Actions=new-window;\n"
        "\n"
        "[Desktop Action new-window]\n"
        "Exec=/usr/bin/discord --new-window\n",
        encoding="utf-8",
    )

    assert discord_app.exec_line(path) == "/usr/bin/discord %u"


# --------------------------------------------------
# Die übrigen Installationsformen
# --------------------------------------------------


def test_a_program_in_the_path_is_found(linux, applications, monkeypatch):

    _handler(monkeypatch, "")

    monkeypatch.setattr(
        discord_app.shutil,
        "which",
        lambda name: "/usr/bin/discord" if name == "discord" else None,
    )

    assert discord_app.find_launcher(URL) == ["/usr/bin/discord", URL]


def test_an_installed_flatpak_is_found(linux, applications, monkeypatch):

    _handler(monkeypatch, "")

    monkeypatch.setattr(
        discord_app.shutil,
        "which",
        lambda name: "/usr/bin/flatpak" if name == "flatpak" else None,
    )

    monkeypatch.setattr(
        discord_app,
        "_query",
        lambda command: _Answer(
            0, "org.gimp.GIMP\ncom.discordapp.Discord\n"
        ),
    )

    assert discord_app.find_launcher(URL) == [
        "flatpak",
        "run",
        "com.discordapp.Discord",
        URL,
    ]


class _Answer:

    def __init__(self, returncode, stdout=""):

        self.returncode = returncode

        self.stdout = stdout


def test_an_appimage_lying_around_is_found(
    linux, applications, monkeypatch, tmp_path
):
    """
    Der Fall, nach dem gefragt wurde: eine heruntergeladene AppImage
    ohne Installation, ohne PATH-Eintrag und ohne Schema-Zuordnung.
    """

    _handler(monkeypatch, "")

    folder = tmp_path / "Downloads"

    folder.mkdir()

    appimage = folder / "Discord-0.0.75-x86_64.AppImage"

    appimage.write_text("", encoding="utf-8")

    appimage.chmod(0o755)

    monkeypatch.setattr(discord_app, "APPIMAGE_DIRS", (str(folder),))

    assert discord_app.find_launcher(URL) == [str(appimage), URL]


def test_a_foreign_appimage_is_not_mistaken_for_discord(
    linux, applications, monkeypatch, tmp_path
):

    _handler(monkeypatch, "")

    folder = tmp_path / "Downloads"

    folder.mkdir()

    other = folder / "WeintCompanion-x86_64.AppImage"

    other.write_text("", encoding="utf-8")

    other.chmod(0o755)

    monkeypatch.setattr(discord_app, "APPIMAGE_DIRS", (str(folder),))

    assert discord_app.find_launcher(URL) == []


def test_an_appimage_without_the_executable_bit_is_no_answer(
    linux, applications, monkeypatch, tmp_path
):
    """
    Eine frisch heruntergeladene AppImage ist nicht ausführbar. Sie
    zu starten schlüge fehl - und der Knopf hätte wieder nichts
    getan, statt in den Browser auszuweichen.
    """

    _handler(monkeypatch, "")

    folder = tmp_path / "Downloads"

    folder.mkdir()

    appimage = folder / "Discord.AppImage"

    appimage.write_text("", encoding="utf-8")

    appimage.chmod(0o644)

    monkeypatch.setattr(discord_app, "APPIMAGE_DIRS", (str(folder),))

    assert discord_app.find_launcher(URL) == []


def test_a_real_installation_beats_a_downloaded_appimage(
    linux, applications, monkeypatch, tmp_path
):

    _entry(applications, "discord.desktop", "/usr/bin/discord %u")

    _handler(monkeypatch, "discord.desktop")

    folder = tmp_path / "Downloads"

    folder.mkdir()

    appimage = folder / "Discord.AppImage"

    appimage.write_text("", encoding="utf-8")

    appimage.chmod(0o755)

    monkeypatch.setattr(discord_app, "APPIMAGE_DIRS", (str(folder),))

    assert discord_app.find_launcher(URL) == ["/usr/bin/discord", URL]


# --------------------------------------------------
# Wenn nichts gefunden wird
# --------------------------------------------------


def test_nothing_found_means_nothing_started(linux, applications, monkeypatch):
    """
    Der Kern des gemeldeten Fehlers: lieber `False` melden und den
    Browser mit der https-Adresse übernehmen lassen, als irgendetwas
    zu starten und Erfolg zu behaupten.
    """

    _handler(monkeypatch, "")

    monkeypatch.setattr(
        discord_app.subprocess,
        "Popen",
        lambda argv, **kw: pytest.fail(f"nichts zu starten: {argv}"),
    )

    assert discord_app.open_link(URL) is False


def test_an_empty_address_is_no_search(linux):

    assert discord_app.find_launcher("") == []

    assert discord_app.find_launcher("   ") == []

    assert discord_app.open_link("") is False


def test_a_failing_source_does_not_end_the_search(
    linux, applications, monkeypatch
):
    """
    Eine unlesbare Datei, ein kaputtes `xdg-mime`, ein Ordner ohne
    Rechte: keiner dieser Fälle darf die Suche beenden, denn die
    nächste Fundstelle kennt die Anwendung vielleicht.
    """

    def boom(url):
        raise OSError("kaputt")

    monkeypatch.setattr(discord_app, "_from_scheme_handler", boom)

    monkeypatch.setattr(
        discord_app.shutil,
        "which",
        lambda name: "/usr/bin/discord" if name == "discord" else None,
    )

    assert discord_app.find_launcher(URL) == ["/usr/bin/discord", URL]


def test_the_launch_does_not_wait_for_discord_to_close(
    linux, applications, monkeypatch
):
    """
    Discord ist ein Fenster, kein Befehl: `subprocess.run()` würde
    warten, bis der Nutzer es wieder schließt - im Hauptthread, also
    mit eingefrorener Oberfläche.
    """

    seen = {}

    monkeypatch.setattr(
        discord_app,
        "find_launcher",
        lambda url: ["/usr/bin/discord", url],
    )

    monkeypatch.setattr(
        discord_app.subprocess,
        "run",
        lambda *a, **kw: pytest.fail("run() statt Popen()"),
    )

    monkeypatch.setattr(
        discord_app.subprocess,
        "Popen",
        lambda argv, **kw: seen.update(argv=argv, kw=kw),
    )

    assert discord_app.open_link(URL) is True

    assert seen["argv"] == ["/usr/bin/discord", URL]

    #
    # Ohne eigene Sitzung nähme ein beendetes WeintCompanion Discord
    # mit.
    #

    assert seen["kw"]["start_new_session"] is True


# --------------------------------------------------
# Windows
# --------------------------------------------------


def test_windows_finds_the_newest_installed_version(monkeypatch, tmp_path):
    """
    Discord legt neben der neuen die alte Fassung ab. Die
    Sortierung muss die Versionsnummer lesen: `app-1.0.9200` ist
    neuer als `app-1.0.9051`, als Zeichenkette aber kleiner.
    """

    from core.runtime import Runtime

    monkeypatch.setattr(Runtime, "is_windows", staticmethod(lambda: True))
    monkeypatch.setattr(Runtime, "is_macos", staticmethod(lambda: False))

    base = tmp_path / "Discord"

    for version in ("1.0.9051", "1.0.9200"):

        folder = base / f"app-{version}"

        folder.mkdir(parents=True)

        (folder / "Discord.exe").write_text("", encoding="utf-8")

    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    argv = discord_app.find_launcher(URL)

    assert argv == [str(base / "app-1.0.9200" / "Discord.exe"), URL]
