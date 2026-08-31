import threading

from addon.finder import WoWFinder
from addon.reader import AddonReader

from core.app_state import AppState
from core.backup import BackupManager
from core.config import Config
from core.downloader import Downloader
from core.github_updater import GitHubUpdater
from core.installer import Installer
from core.logger import Logger
from core.installer_workflow import InstallerWorkflow
from core.companion_updater import CompanionUpdater
from core.launcher import Launcher
from core.battlenet_launcher import BattleNetLauncher
from addon.sync_reader import SyncReader
from core.sync_manager import SyncManager
from PySide6.QtCore import QObject, QTimer, Signal
from core.discord_status import DiscordStatus
from core import discord_account
from core.discord_account import DiscordAccountStore
from core.discord_auth import DiscordAuth
from core.access_profile_sync import AccessProfileSync
from core.discord_roster_sync import DiscordRosterSync
from core.raid_schedule_sync import RaidScheduleSync
from core.update_watch import UpdateWatch
from core.last_pull_sync import LastPullSync
from addon.addon_inbox import AddonInbox
from core.addon_analysis_sync import AddonAnalysisSync
from core.raid_data_service import RaidDataService
from core.academy_service import AcademyService
from core.academy_history import day_from_iso
from core.character_store import CharacterStore
from core.stat_weights_store import StatWeightsStore
from core.stat_weights_sync import StatWeightsSync
from core.weakaura_store import WeakAuraStore
from core.weakaura_sync import WeakAuraSync
from core.weakaura_guild_sync import WeakAuraGuildSync


class _AutoSyncStarter(QObject):
    """
    Stößt start_auto_sync() garantiert im Hauptthread an, egal von
    welchem Thread aus emittiert wird.

    QTimer.singleShot(0, callback) aus einem Thread OHNE eigene
    laufende Qt-Event-Loop (wie unser InitThread - ein reiner
    threading.Thread, der nie .exec() aufruft) ist dafür nicht
    zuverlässig: der Callback braucht eine Event-Loop, die ihn
    abarbeitet, und die des aufrufenden Threads gibt es hier gar
    nicht. Eine Signal/Slot-Verbindung über Thread-Grenzen wird
    dagegen immer über die Event-Loop des EMPFÄNGER-Threads
    zugestellt (hier: der Hauptthread, der mit app.exec() läuft) -
    unabhängig davon, ob der Sender-Thread selbst eine Event-Loop hat.
    """

    requested = Signal()


class CompanionManager(QObject):

    #
    # Wird ausgelöst, wenn die "In Tray minimieren"-Einstellung
    # geändert wird - MainWindow hält das eigentliche
    # QSystemTrayIcon und reagiert live darauf, ohne dass ein
    # Neustart nötig ist.
    #

    tray_settings_changed = Signal(bool)

    #
    # Ausgelöst, sobald eine Prüfung den AppState verändert haben kann
    # (full_refresh, refresh_update_status). Die Oberfläche zeichnet
    # daraufhin die aktuelle Seite und die Navigationsspalte neu.
    #
    # Ohne dieses Signal war ein gefundenes Update auf der Übersicht
    # praktisch nie zu sehen: `full_refresh()` läuft in einem
    # Hintergrund-Thread und ist rund eine Sekunde NACH dem Zeichnen
    # der Übersicht fertig, und nichts fragte danach noch einmal nach.
    # Die Systemzeile zeigte deshalb den Stand von vor der Prüfung, bis
    # der Nutzer die Seite verließ und erneut betrat - `refresh()` hängt
    # ausschließlich am Seitenwechsel.
    #
    # Es wird bewusst aus dem Arbeits-Thread emittiert: der
    # CompanionManager entsteht im Hauptthread, seine Thread-Affinität
    # ist also richtig, und eine Signalverbindung über Thread-Grenzen
    # wird immer über die Event-Loop des EMPFÄNGERS zugestellt (siehe
    # den Docstring von _AutoSyncStarter). Ein direkter Aufruf von
    # `page.refresh()` aus dem Thread heraus würde dagegen Widgets aus
    # dem falschen Thread anfassen.
    #

    state_changed = Signal()

    def __init__(self):

        super().__init__()

        self.state = AppState()

        self.config = Config()

        self.logger = Logger()

        self.github = GitHubUpdater(
            owner="daddler",
            repo="WeintCodex",
            asset_filter=".zip",
        )
        self.downloader = Downloader()
        self.backup = BackupManager()
        self.installer = Installer()
        self.workflow = InstallerWorkflow(self)
        self.companion_updater = CompanionUpdater(self)
        self.launcher = Launcher()
        self.battlenet_launcher = BattleNetLauncher(self.config)
        self.sync = SyncManager(self)
        self.discord = DiscordStatus()
        self.discord_account = DiscordAccountStore()

        #
        # Damit die Ablage selbst sagen kann, wenn sie die Verknüpfung
        # aufhebt oder aus der Sicherung wiederherstellt. Vorher hat
        # das eine von fünf Stellen mit `print()` getan - also an
        # keiner Stelle, die ein Nutzer je zu sehen bekommt.
        #

        discord_account.set_logger(self.logger)
        self.discord_auth = DiscordAuth()
        #
        # Alles, was Richtung Addon zugestellt wird, laeuft ueber eine
        # gemeinsame Inbox - sonst wuerde der zuletzt schreibende
        # Absender die Nachrichten der uebrigen ueberschreiben.
        #

        self.addon_inbox = AddonInbox(self)

        self.discord_roster_sync = DiscordRosterSync(self, self.addon_inbox)

        #
        # Holt die Discord-Rollen beim Bot ab und stellt dem Addon
        # daraus Rang und Freigaben zu. Eigener Kanal in der Inbox, wie
        # die uebrigen Absender.
        #

        self.access_profile_sync = AccessProfileSync(self, self.addon_inbox)

        #
        # Der Raidtermin für die Übersicht. Kein Absender Richtung
        # Addon - das Addon bekommt den Kalender bereits über
        # DiscordRosterSync; hier geht es allein um die Frage "wann ist
        # der nächste Raid", die die Übersicht bis 2.0.1 gar nicht
        # stellen konnte.
        #

        self.raid_schedule_sync = RaidScheduleSync(self)

        #
        # Sieht im Hintergrund nach, ob eine neue Fassung bereitliegt.
        # Bis 2.3.2 geschah das genau zweimal - beim Start und auf
        # Knopfdruck -, und damit erfuhr niemand von einer Fassung, die
        # nach dem Öffnen der Anwendung erschien. Siehe
        # core/update_watch.py.
        #

        self.update_watch = UpdateWatch(self)

        #
        # Der letzte Pull für die Übersicht. Ebenfalls kein Absender
        # Richtung Addon: er beantwortet allein die Frage "was war
        # mein letzter Kampf", die die Übersicht bis 2.0.6 nur für die
        # laufende Sitzung stellen konnte - nach einem Neustart stand
        # dort auch am Tag nach dem Raid "Noch kein Pull".
        #

        self.last_pull_sync = LastPullSync(self)

        #
        # WeintTV und WeintAcademy hängen beide am selben
        # RaidDataService - er ist die einzige Stelle, an der Raid-
        # Daten beschafft werden. Beide Dienste arbeiten träge: sie
        # starten weder einen Thread noch einen Netzwerkzugriff,
        # solange keine Seite sie anfordert, und verlängern damit
        # den Anwendungsstart nicht.
        #

        self.raid_data = RaidDataService(self)
        self.academy = AcademyService(self)

        #
        # Die Lernkurve wird **hier** mitgeschrieben und nicht auf der
        # Academy-Seite.
        #
        # Der Grund ist der Nutzungsablauf: wer den Abend über WeintTV
        # laufen lässt und erst danach in die Academy sieht, hätte
        # sonst genau einen Punkt in der Kurve - den letzten Pull. Der
        # Snapshot-Strom läuft aber, sobald **irgendeine** der beiden
        # Seiten angemeldet ist, und diese Stelle sieht ihn ganz.
        #
        # Ein gebundener Slot und keine Lambda: das Signal gehört
        # einem Dienst, der so lange lebt wie das Programm (dieselbe
        # Regel wie bei den Theme-Signalen, siehe CLAUDE.md).
        #

        self.raid_data.snapshotChanged.connect(self._note_academy_pull)

        #
        # Die Charakterliste sammelt die "character_sheet"-Meldungen
        # mehrerer Anmeldungen ein - das Addon meldet immer nur den
        # gerade gespielten Charakter. Sie liest beim Erzeugen ihre
        # Datei und macht sonst nichts, verlängert den Start also
        # nicht.
        #

        self.characters = CharacterStore(self)

        #
        # Die WeakAura-Bibliothek: was auf der Seite "WeakAuras"
        # eingetragen wurde, plus der zuletzt gemeldete Katalog des
        # Addons. Liest beim Erzeugen ihre Datei und macht sonst
        # nichts.
        #

        self.weakauras = WeakAuraStore(self)

        #
        # Und ihre Zustellung ins Addon. Eigener Kanal in der Inbox
        # wie jeder andere Absender.
        #

        self.weakaura_sync = WeakAuraSync(
            self,
            self.addon_inbox,
            self.weakauras,
        )

        #
        # Und die Gegenrichtung: die gemeinsame Bibliothek des Bots.
        # Was jemand freigegeben hat, bekommen alle - der Bot ist
        # dafuer das, was er in diesem Verbund ohnehin ist: die eine
        # Stelle, an der Gildenwissen liegt.
        #

        self.weakaura_guild_sync = WeakAuraGuildSync(
            self,
            self.weakauras,
        )

        #
        # Die Wertegewichte aus einem Sim: was auf der Seite "Simmen"
        # eingelesen wurde, plus ihre Zustellung ins Addon. Liest beim
        # Erzeugen ihre Datei und macht sonst nichts.
        #

        self.stat_weights = StatWeightsStore(self)

        self.stat_weights_sync = StatWeightsSync(
            self,
            self.addon_inbox,
            self.stat_weights,
        )

        #
        # Stellt die zuletzt ausgewertete Auswertung samt Lernpfad ins
        # Addon (WeintTV/Academy ingame). Meldet den RaidDataService
        # bewusst nicht an, siehe core/addon_analysis_sync.py.
        #

        self.addon_analysis_sync = AddonAnalysisSync(self, self.addon_inbox)

        self.sync_timer = QTimer()

        self.sync_timer.timeout.connect(
            self.run_auto_sync
        )

        #
        # _AutoSyncStarter wird hier im Hauptthread erzeugt (Companion-
        # Manager selbst lebt im Hauptthread) - seine Thread-Affinität
        # ist damit korrekt gesetzt, bevor _initialize_worker im
        # Hintergrund-Thread emit() darauf aufruft.
        #

        self._auto_sync_starter = _AutoSyncStarter()

        self._auto_sync_starter.requested.connect(
            self.start_auto_sync
        )

        self._sync_busy = False
        self._sync_lock = threading.Lock()

    # --------------------------------------------------
    # Initialisierung
    # --------------------------------------------------

    def initialize(self):

        #
        # full_refresh verzögert starten, damit das Fenster
        # zuerst gerendert wird und der Qt-Hauptthread frei bleibt
        #

        QTimer.singleShot(
            100,
            self._initialize_async,
        )

    def _initialize_async(self):

        thread = threading.Thread(
            target=self._initialize_worker,
            daemon=True,
            name="InitThread",
        )

        thread.start()

    def _initialize_worker(self):

        #
        # full_refresh() darf den Start von Auto-Sync niemals verhindern:
        # Ohne dieses try/except würde eine einzelne fehlgeschlagene
        # Anfrage (Netzwerk-Hänger, Discord/GitHub down, defekte
        # SavedVariables, ...) diesen Thread lautlos beenden - in einer
        # AppImage/EXE ohne sichtbares Terminal sieht das für Nutzer wie
        # ein Absturz aus, obwohl nur dieser Hintergrund-Thread stirbt
        # und Auto-Sync danach nie mehr anläuft.
        #

        try:

            self.full_refresh()

        except Exception as exc:

            self.logger.error(
                f"Initialisierung fehlgeschlagen: {exc}"
            )

        finally:

            #
            # Siehe _AutoSyncStarter-Docstring: garantiert im
            # Hauptthread zugestellt, unabhängig von der (fehlenden)
            # Event-Loop dieses Threads.
            #

            self._auto_sync_starter.requested.emit()

    # --------------------------------------------------
    # Automatische Synchronisation
    # --------------------------------------------------

    def start_auto_sync(self):

        if not self.config.data.get(
            "auto_sync",
            True,
        ):

            self.logger.info(
                "Automatische Synchronisation deaktiviert."
            )

            return

        interval = self.config.data.get(
            "sync_interval",
            5,
        )

        #
        # Sekunden -> Millisekunden
        #

        self.sync_timer.start(
            interval * 1000
        )

        self.logger.success(
            f"Automatische Synchronisation aktiviert ({interval} Sekunde(n))."
        )

    def run_auto_sync(self):

        #
        # Verhindert, dass ein neuer Sync startet,
        # während der vorherige noch läuft
        #

        with self._sync_lock:

            if self._sync_busy:
                return

            self._sync_busy = True

        thread = threading.Thread(
            target=self._run_sync_worker,
            daemon=True,
            name="SyncThread",
        )

        thread.start()

    def _run_sync_worker(self):

        #
        # Ob dieser Durchgang etwas geändert hat, das auf dem Bildschirm
        # steht. Nur dann wird am Ende `state_changed` gemeldet - eine
        # Meldung je Takt hiesse, die sichtbare Seite alle fünf Sekunden
        # neu zu zeichnen und `MainWindow._announce_updates()` ebenso oft
        # zu durchlaufen.
        #
        # Ohne diesen Weg blieb alles, was hier abgeholt wird, bis zum
        # nächsten Seitenwechsel unsichtbar: `refresh()` einer Seite
        # hängt am Wechsel und an `state_changed`, und das kam nach dem
        # Start nur noch auf Knopfdruck ("Erneut prüfen").
        #

        dirty = False

        try:

            self.sync.process()

        except Exception as exc:

            self.logger.error(
                f"Sync fehlgeschlagen: {exc}"
            )

        #
        # Zugriffsprofil zuerst: es entscheidet im Addon darüber, was
        # von den nachfolgend zugestellten Daten überhaupt angezeigt
        # wird. Die Reihenfolge in der Inbox ist dem Addon zwar egal (es
        # zieht Profile in einem eigenen ersten Durchgang vor), aber so
        # steht das Profil auch in der Datei vor den Daten, auf die es
        # sich bezieht.
        #

        try:

            if self.config.data.get(
                "access_profile_sync_enabled",
                True,
            ):

                self.access_profile_sync.process()

        except Exception as exc:

            self.logger.error(
                f"Zugriffsprofil-Zustellung fehlgeschlagen: {exc}"
            )

        #
        # Eigener try/except: ein Fehler beim Raid-Roster-Abruf
        # (z. B. Bot nicht erreichbar) darf den Material-Sync oben
        # nicht mit runterreißen und umgekehrt.
        #

        try:

            if self.config.data.get(
                "roster_sync_enabled",
                True,
            ):

                self.discord_roster_sync.process()

        except Exception as exc:

            self.logger.error(
                f"Gilden-Kalender-Sync fehlgeschlagen: {exc}"
            )

        #
        # Nach einer neuen Fassung sehen. Traege (alle 15 Minuten,
        # siehe update_watch.REFRESH_SECONDS) und mit eigenem
        # try/except wie jeder Schritt - ein nicht erreichbares GitHub
        # darf weder den Material-Sync noch die Zustellung ans Addon
        # mitreissen.
        #

        try:

            if self.update_watch.process():
                dirty = True

        except Exception as exc:

            self.logger.error(
                f"Update-Pruefung fehlgeschlagen: {exc}"
            )

        #
        # Der Raidtermin der Uebersicht. Eigener try/except wie alle
        # anderen Schritte - eine nicht erreichbare Terminauskunft darf
        # weder den Material-Sync noch die Zustellung ans Addon
        # mitreissen.
        #

        try:

            if self.raid_schedule_sync.process():
                dirty = True

        except Exception as exc:

            self.logger.error(
                f"Raidtermin-Abruf fehlgeschlagen: {exc}"
            )

        #
        # Der letzte Pull der Uebersicht. Eigener try/except wie jeder
        # andere Schritt - und bewusst nach dem Termin, weil er die
        # teureren beiden Abrufe traegt (Bericht- und Pull-Liste).
        #

        try:

            self.last_pull_sync.process()

        except Exception as exc:

            self.logger.error(
                f"Abruf des letzten Pulls fehlgeschlagen: {exc}"
            )

        #
        # Die gemeinsame WeakAura-Bibliothek beim Bot abholen. Traege
        # (alle zehn Minuten, siehe REFRESH_SECONDS) und vor der
        # Zustellung, damit eine neu freigegebene Aura im selben
        # Durchgang beim Addon landet statt erst im naechsten.
        #

        try:

            self.weakaura_guild_sync.process()

        except Exception as exc:

            self.logger.error(
                f"Abruf der WeakAura-Bibliothek fehlgeschlagen: {exc}"
            )

        #
        # Die WeakAura-Bibliothek ins Addon. Eigener try/except wie
        # jeder Schritt; sie ist rein lokal (keine Netzrunde) und
        # schreibt nur, wenn sich etwas geaendert hat.
        #

        try:

            self.weakaura_sync.process()

        except Exception as exc:

            self.logger.error(
                f"WeakAura-Zustellung fehlgeschlagen: {exc}"
            )

        #
        # Die Sim-Gewichte ins Addon. Rein lokal wie die Zustellung
        # darüber und mit eigenem try/except; sie schreibt nur, wenn
        # sich etwas geändert hat.
        #

        try:

            self.stat_weights_sync.process()

        except Exception as exc:

            self.logger.error(
                f"Zustellung der Sim-Gewichte fehlgeschlagen: {exc}"
            )

        #
        # Wieder eigener try/except: eine fehlerhafte Auswertung darf
        # weder den Material-Sync noch den Roster-Abruf mitreissen.
        #

        try:

            if self.config.data.get(
                "addon_analysis_sync_enabled",
                True,
            ):

                self.addon_analysis_sync.process()

        except Exception as exc:

            self.logger.error(
                f"WeintTV/Academy-Zustellung fehlgeschlagen: {exc}"
            )

        #
        # Zum Schluss die Zustellung im Addon-Ordner nachziehen. Fast
        # immer ein Vergleich ohne Schreibvorgang - noetig ist sie fuer
        # den einen Fall, in dem uns die Datei aus der Hand genommen
        # wird: ein Addon-Update entpackt den leeren
        # Auslieferungsstand darueber. Ohne diesen Schritt bliebe die
        # Zustellung danach verschwunden, bis sich beim Bot inhaltlich
        # etwas aendert - die Absender oben schicken einen
        # unveraenderten Stand kein zweites Mal.
        #

        try:

            self.addon_inbox.reassert()

        except Exception as exc:

            self.logger.error(
                f"Nachziehen der Addon-Zustellung fehlgeschlagen: {exc}"
            )

        finally:

            with self._sync_lock:

                self._sync_busy = False

        #
        # Erst hier, und nur bei tatsaechlicher Aenderung: die
        # Oberflaeche zieht daraufhin die sichtbare Seite und die
        # Navigationsspalte nach (MainWindow._on_state_changed).
        #
        # Bewusst NACH dem Freigeben von `_sync_busy`, damit dieser
        # Durchgang zum Zeitpunkt der Meldung wirklich beendet ist -
        # zugestellt wird der Slot ohnehin ueber die Event-Loop des
        # Hauptthreads (siehe den Docstring von `state_changed`).
        #

        if dirty:

            self.state_changed.emit()

    # --------------------------------------------------
    # Automatische Synchronisation stoppen
    # --------------------------------------------------

    def stop_auto_sync(self):

        if self.sync_timer.isActive():

            self.sync_timer.stop()

            self.logger.info(
                "Automatische Synchronisation gestoppt."
            )

    # --------------------------------------------------
    # Classic Installation
    # --------------------------------------------------

    def detect_wow(self):

        classic_path = self.config.get_classic_path()

        if classic_path is None:

            finder = WoWFinder()
            classic_path = finder.find()

            if classic_path:
                self.config.set_classic_path(classic_path)

        #
        # Ein anderer Pfad heißt eine andere SavedVariables-Datei, in
        # der noch gar nichts steht. Der Merker in AddonAnalysisSync
        # kennt nur den Inhalt, nicht das Ziel - ohne dieses
        # Verwerfen würde die erste Zustellung dorthin als
        # "unverändert" unterdrückt und käme nie an.
        #
        if classic_path != self.state.wow_path:

            for attribute in (
                "addon_analysis_sync",
                "weakaura_sync",
                "stat_weights_sync",
            ):

                sync = getattr(self, attribute, None)

                if sync is not None:
                    sync.invalidate()

        self.state.wow_path = classic_path
        self.state.wow_found = classic_path is not None

        if self.state.wow_found:

            self.state.addons_path = (
                classic_path
                / "Interface"
                / "AddOns"
            )

        else:

            self.state.addons_path = None

    # --------------------------------------------------
    # Addon
    # --------------------------------------------------

    def detect_addon(self):

        self.state.addon_found = False
        self.state.addon_version = "-"

        if not self.state.addons_path:
            self.state.addon_path = None
            return

        self.state.addon_path = (
            self.state.addons_path
            / "WeintCodex"
        )

        reader = AddonReader(self.state.wow_path)

        if not reader.exists():
            return

        self.state.addon_found = True
        self.state.addon_version = (
            reader.get_version() or "-"
        )

        #
        # Companion Queue prüfen
        #

        sync = SyncReader(
            self.state.wow_path
        )

        if sync.exists():

            count = sync.queue_size()

            if count:

                self.logger.info(
                    f"Companion: {count} Nachricht(en) in der Warteschlange."
                )

            else:

                self.logger.success(
                    "Companion: Warteschlange leer."
                )

        else:

            self.logger.info(
                "Companion: Keine SavedVariables gefunden."
            )

    # --------------------------------------------------
    # GitHub
    # --------------------------------------------------

    def normalize_version(self, version):

        if not version:
            return ""

        return (
            version
            .strip()
            .lower()
            .removeprefix("v")
        )

    def check_github(self, quiet: bool = False):
        """
        `quiet` ist der Modus der Hintergrundwache (siehe
        core/update_watch.py): dieselbe Prüfung, aber ohne die beiden
        Zeilen, die nur den *Vollzug* melden. Alle fünfzehn Minuten
        "WeintCodex ist aktuell." ins Protokoll zu schreiben, macht
        aus der Protokollseite eine Liste von Nichtereignissen - und
        ein nicht erreichbares GitHub ist im Hintergrund keine
        Störung, sondern der Normalfall eines Rechners, der gerade
        offline ist. Der Fund einer neuen Fassung wird auch leise
        gemeldet: das ist ein Ereignis.
        """

        release = self.github.get_latest_release()

        if release is None:

            self.state.github_version = "-"
            self.state.github_release_name = ""
            self.state.github_changelog = ""
            self.state.github_download_url = ""
            self.state.github_asset_name = ""
            self.state.github_published = ""
            self.state.github_sha256 = ""
            self.state.update_available = False

            if quiet:

                self.logger.info(
                    "GitHub konnte nicht erreicht werden."
                )

            else:

                self.logger.error(
                    "GitHub konnte nicht erreicht werden."
                )

            return

        self.state.github_version = release.version
        self.state.github_release_name = release.name
        self.state.github_changelog = release.changelog
        self.state.github_download_url = release.download_url
        self.state.github_asset_name = release.asset_name
        self.state.github_published = release.published_at
        self.state.github_sha256 = release.sha256 or ""

        github = self.normalize_version(
            self.state.github_version
        )

        addon = self.normalize_version(
            self.state.addon_version
        )

        self.state.update_available = (
            github != addon
        )

        if self.state.update_available:

            self.logger.info(
                f"Neue Version gefunden ({release.version})."
            )

        elif not quiet:

            self.logger.success(
                "WeintCodex ist aktuell."
            )

    # --------------------------------------------------
    # Discord
    # --------------------------------------------------

    def check_discord(self):

        data = self.discord.fetch()

        if data is None:

            self.state.discord_connected = False
            self.state.discord_name = "-"
            self.state.discord_guilds = 0
            self.state.discord_latency = None

            return

        if not data.get("online", False):

            self.state.discord_connected = False
            self.state.discord_name = "-"
            self.state.discord_guilds = 0
            self.state.discord_latency = None

            return

        bot = data.get("bot", {})

        self.state.discord_connected = True
        self.state.discord_name = bot.get("name", "-")
        self.state.discord_guilds = bot.get("guilds", 0)
        self.state.discord_latency = bot.get("latency")

    # --------------------------------------------------
    # Installation / Update
    # --------------------------------------------------

    def install_or_update(self):

        return self.workflow.run()

    # --------------------------------------------------
    # WoW starten (Battle.net)
    # --------------------------------------------------

    def start_wow(self):

        try:

            self.battlenet_launcher.launch(
                self.state.wow_path
            )

            self.logger.success(
                "Battle.net wird gestartet..."
            )

        except Exception as exc:

            self.logger.error(
                f"Battle.net konnte nicht gestartet werden: {exc}"
            )

    # --------------------------------------------------
    # Status
    # --------------------------------------------------

    def has_wow(self):

        return self.state.wow_found

    def has_addon(self):

        return self.state.addon_found

    # --------------------------------------------------
    # Refresh
    # --------------------------------------------------

    def refresh(self):

        self.detect_wow()
        self.detect_addon()

    # --------------------------------------------------
    # Lernkurve
    # --------------------------------------------------

    def _note_academy_pull(self, snapshot):
        """
        Jeden beendeten Pull für die Lernkurve der Academy anbieten.

        Hängt am `snapshotChanged` des Datendienstes und läuft damit
        im Sekundentakt (in einer Wiedergabe viermal so oft). Die
        Entscheidung, ob daraus ein Punkt wird, trifft
        `AcademyService.note_snapshot()`; die billigen Prüfungen
        stehen dort ganz vorn.

        Was diese Stelle beisteuert, ist die **Herkunft**: aus welchem
        Bericht und welchem Kampf der Snapshot stammt. Ohne sie wäre
        derselbe archivierte Pull, zweimal geöffnet, zweimal in der
        Kurve - und die Reihenfolge käme aus der Klickfolge statt aus
        dem Raidabend.

        Der ganze Aufruf steht unter `try/except`: er hängt am
        Datenstrom von WeintTV, und eine Aufzeichnung, die scheitert,
        darf niemals den laufenden Kampf mitnehmen.
        """

        try:

            state = self.raid_data.archive_state()

            origin = ""

            day = ""

            sequence = 0

            #
            # `browsing` und nicht bloss "ist ein Bericht gewählt":
            # `show_live()` lässt die Archiv-Auswahl ausdrücklich
            # stehen, damit ein Rücksprung ins Archiv wieder dort
            # landet, wo man war. Ohne diese Bedingung bekäme der
            # nächste **Live**-Pull die Kennung des zuletzt
            # angesehenen Archivkampfes - und würde als dessen
            # Doppelgänger verworfen. Der Punkt fehlte dann in der
            # Kurve, ohne dass irgendetwas fehlschlägt.
            #

            if (
                state.browsing
                and state.selected_report
                and state.selected_fight is not None
            ):

                origin = f"{state.selected_report}#{state.selected_fight}"

                sequence = int(state.selected_fight)

                day = self._report_day(state)

            self.academy.note_snapshot(
                snapshot,
                origin=origin,
                day=day,
                sequence=sequence,
                source=self.config.data.get("raid_data_source", ""),
            )

        except Exception as exc:

            self.logger.warning(
                f"Academy-Verlauf konnte nicht fortgeschrieben "
                f"werden: {exc}"
            )

    def _report_day(self, state) -> str:
        """
        Der Raidtag des gewählten Berichts, aus seiner Liste.

        Leer, wenn der Bericht nicht (mehr) in der Liste steht oder
        keinen lesbaren Zeitstempel trägt - dann fällt die
        Aufzeichnung auf den heutigen Tag zurück, was für einen
        gerade gespielten Pull ohnehin stimmt.
        """

        for report in state.reports:

            if report.code == state.selected_report:
                return day_from_iso(report.start)

        return ""

    # --------------------------------------------------
    # Vollständige Aktualisierung
    # --------------------------------------------------

    def _note_update_check(self):
        """
        Der Hintergrundwache sagen, dass ihre beiden Endpunkte gerade
        abgefragt wurden - ohne diesen Vermerk zoege sie fuenf Sekunden
        nach dem Start ein zweites Mal los (siehe core/update_watch.py).

        Ueber `getattr`, und das ist hier keine Vorsicht auf Verdacht:
        der Aufruf steht im `finally` von `full_refresh()`, und dieses
        `finally` hat genau eine Aufgabe - die Meldung an die
        Oberflaeche darf unter keinen Umstaenden ausbleiben. Was dort
        steht, darf also selbst nichts werfen koennen, auch nicht auf
        einem nur teilweise aufgebauten Manager (so ruft
        `tests/test_update_visibility.py` full_refresh() auf).
        """

        watch = getattr(self, "update_watch", None)

        if watch is not None:
            watch.note_checked()

    def full_refresh(self):

        try:

            self.detect_wow()
            self.detect_addon()
            self.check_github()
            self.check_discord()
            self.companion_updater.check_for_update()
            self.sync.process()

        finally:

            self._note_update_check()

            #
            # Auch dann melden, wenn ein Schritt gescheitert ist: die
            # vorherigen haben den Zustand bereits verändert, und eine
            # halb aktualisierte Anzeige ist besser als eine, die auf
            # dem Stand von vor der Prüfung stehen bleibt.
            #

            self.state_changed.emit()

    # --------------------------------------------------
    # Manuelle Update-Prüfung (Button im Dashboard)
    # --------------------------------------------------

    def refresh_update_status(self):
        """
        Prüft erneut gegen GitHub, ob ein Addon- oder Companion-Update
        verfügbar ist - ohne die App neu zu starten. Macht dieselben
        Anfragen wie full_refresh(), aber ohne Discord-Status/Sync,
        die für eine reine "nach Updates suchen"-Aktion irrelevant sind.

        Beide Zwischenspeicher werden vorher verworfen: hier steht
        immer ein Nutzer hinter der Prüfung, der von einer neuen
        Fassung gehört hat. Eine Antwort aus dem Speicher von vor
        zehn Minuten wäre für ihn nicht von einem kaputten Knopf zu
        unterscheiden.
        """

        self.github.invalidate_cache()

        self.companion_updater.github.invalidate_cache()

        #
        # Auch der Raidtermin wird wieder freigegeben. Der Knopf sitzt
        # auf der Uebersicht direkt neben der Aufstellung, und "erneut
        # pruefen" heisst dort alles, was die Seite zeigt - abgeholt
        # wird er im naechsten Sync-Takt (hoechstens fuenf Sekunden),
        # denn eine Netzrunde gehoert nicht in diesen Aufruf.
        #

        self.raid_schedule_sync.invalidate()

        try:

            self.detect_addon()
            self.check_github()
            self.companion_updater.check_for_update()

        finally:

            self._note_update_check()

            self.state_changed.emit()

