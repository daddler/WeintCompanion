import json
import os
from pathlib import Path

from core.paths import Paths


class Config:

    def __init__(self):

        self.file = (
            Paths.config()
            / "config.json"
        )

        self.data = {

            "classic_path": "",

            #
            # Allgemeine Einstellungen
            #

            "check_updates": True,

            "auto_sync": True,

            "sync_interval": 5,

            "roster_sync_enabled": True,

            "character_roster_sync_enabled": True,

            #
            # Zugriffsprofil: holt die Discord-Rollen beim Bot ab und
            # stellt dem Addon daraus Rang und Freigaben zu
            # (core/access_profile_sync.py). Ohne zugestelltes Profil
            # bleiben im Addon alle Bereiche offen.
            #

            "access_profile_sync_enabled": True,

            #
            # Zuordnung Discord-Rollenname -> Rang
            # ("gast"/"extern"/"mitglied"/"offizier"). Leer bedeutet:
            # die Standardzuordnung aus core/access_roles.py verwenden.
            # Hier eintragen, wenn Rollen im Discord anders heissen.
            #

            "access_role_map": {},

            #
            # Stellt die zuletzt ausgewertete WeintTV-/Academy-Analyse
            # ins Addon (core/addon_analysis_sync.py).
            #

            "addon_analysis_sync_enabled": True,

            "start_on_boot": False,

            "minimize_to_tray": False,

            #
            # Battle.net-Start (Linux)
            #

            "linux_launcher_type": "custom",

            "linux_launcher_value": "",

            #
            # "Was ist neu"-Popup (gui/dialogs/whats_new_dialog.py)
            #

            "whats_new_enabled": True,

            "onboarding_seen_version": "",

            #
            # Module (WeintTV / WeintAcademy)
            #

            "weinttv_enabled": True,

            "academy_enabled": True,

            "raid_data_source": "mock",

            "combatlog_path": "",

            "academy_player_name": "",

        }

        self.load()

    # --------------------------------------------------

    def load(self):

        if not self.file.exists():

            self.save()

            return

        try:

            with open(
                self.file,
                "r",
                encoding="utf-8",
            ) as f:

                self.data.update(
                    json.load(f)
                )
                #
                # Fehlende Einstellungen ergänzen
                #

                changed = False

                defaults = {

                    "check_updates": True,
                    "auto_sync": True,
                    "sync_interval": 5,
                    "roster_sync_enabled": True,
                    "character_roster_sync_enabled": True,
                    "addon_analysis_sync_enabled": True,
                    "start_on_boot": False,
                    "minimize_to_tray": False,
                    "linux_launcher_type": "custom",
                    "linux_launcher_value": "",
                    "whats_new_enabled": True,
                    "onboarding_seen_version": "",
                    "weinttv_enabled": True,
                    "academy_enabled": True,
                    "raid_data_source": "mock",
                    "combatlog_path": "",
                    "academy_player_name": "",

                }

                for key, value in defaults.items():

                    if key not in self.data:

                        self.data[key] = value
                        changed = True

                if changed:

                    self.save()

        except Exception:

            #
            # Eine kaputte config.json (z. B. durch einen Absturz
            # mitten im Schreiben) wird NICHT stillschweigend mit
            # den In-Memory-Defaults überschrieben - das würde
            # sämtliche Nutzereinstellungen kommentarlos löschen.
            # Stattdessen wird die kaputte Datei beiseite gelegt,
            # damit der Verlust sichtbar/nachvollziehbar bleibt.
            #

            backup_path = self.file.with_suffix(
                self.file.suffix + ".bak"
            )

            try:

                self.file.replace(backup_path)

                print(
                    f"config.json war beschädigt und wurde nach "
                    f"{backup_path.name} verschoben - Einstellungen "
                    f"wurden auf Standardwerte zurückgesetzt."
                )

            except OSError as exc:

                print(
                    f"config.json war beschädigt und konnte nicht "
                    f"gesichert werden ({exc}) - Einstellungen werden "
                    f"auf Standardwerte zurückgesetzt."
                )

            self.save()

    # --------------------------------------------------

    def save(self):
        """
        Schreibt zuerst in eine temporäre Datei im selben Verzeichnis
        und ersetzt config.json danach atomar (os.replace) - ein
        Absturz/Stromausfall mitten im Schreiben kann so nie eine
        halbgeschriebene, kaputte config.json hinterlassen.
        """

        self.file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        tmp_path = self.file.with_suffix(
            self.file.suffix + ".tmp"
        )

        with open(
            tmp_path,
            "w",
            encoding="utf-8",
        ) as f:

            json.dump(
                self.data,
                f,
                indent=4,
                ensure_ascii=False,
            )

        os.replace(tmp_path, self.file)

    # --------------------------------------------------
    # Classic-Pfad
    # --------------------------------------------------

    def get_classic_path(self):

        path = self.data.get(
            "classic_path",
            "",
        )

        if not path:
            return None

        path = Path(path)

        if path.exists():
            return path

        return None

    # --------------------------------------------------

    def set_classic_path(self, path):

        self.data["classic_path"] = str(path)

        self.save()

    # --------------------------------------------------
    # Battle.net-Start (Linux)
    # --------------------------------------------------

    def get_linux_launcher_type(self):

        return self.data.get(
            "linux_launcher_type",
            "custom",
        )

    def get_linux_launcher_value(self):

        return self.data.get(
            "linux_launcher_value",
            "",
        )

    def set_linux_launcher(self, launcher_type, value):

        self.data["linux_launcher_type"] = launcher_type
        self.data["linux_launcher_value"] = value.strip()

        self.save()

    def get_linux_launch_command(self):
        """
        Baut aus Launcher-Typ + Wert den tatsächlich auszuführenden
        Befehl. "lutris"/"steam"/"faugus" kennen eine feste
        CLI-Syntax, bei "custom" (z. B. Bottles, Heroic, ...) ist
        der Wert bereits der vollständige Befehl.
        """

        launcher_type = self.get_linux_launcher_type()
        value = self.get_linux_launcher_value()

        if not value:
            return ""

        if launcher_type == "lutris":
            return f"lutris lutris:rungame/{value}"

        if launcher_type == "steam":
            return f"steam steam://rungameid/{value}"

        if launcher_type == "faugus":
            return f"faugus-launcher --game {value}"

        return value