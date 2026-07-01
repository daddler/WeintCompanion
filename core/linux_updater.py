from pathlib import Path
import stat


class LinuxUpdater:

    def create_update_script(
        self,
        downloaded_appimage: Path,
        current_appimage: Path,
    ) -> Path:

        script = downloaded_appimage.parent / "update.sh"

        script.write_text(
f"""#!/bin/bash

set -e

LOG="{downloaded_appimage.parent}/update.log"

echo "==============================" > "$LOG"
echo "WeintCompanion Updater" >> "$LOG"
echo "$(date)" >> "$LOG"
echo "==============================" >> "$LOG"

echo "Warte auf das Beenden der Anwendung..." | tee -a "$LOG"

#
# Der Companion beendet sich selbst nach dem Start
# des Update-Skripts. Ein kurzer Puffer reicht aus.
#

sleep 2

echo "Ersetze AppImage..." | tee -a "$LOG"

mv -f "{downloaded_appimage}" "{current_appimage}"

echo "Setze Ausführungsrechte..." | tee -a "$LOG"

chmod +x "{current_appimage}"

echo "Starte neue Version..." | tee -a "$LOG"

nohup "{current_appimage}" >/dev/null 2>&1 &

echo "Update erfolgreich abgeschlossen." | tee -a "$LOG"

#
# Update-Skript entfernen
#

rm -f "$0"

""",
            encoding="utf-8",
        )

        #
        # Script ausführbar machen
        #

        mode = script.stat().st_mode

        script.chmod(
            mode
            | stat.S_IXUSR
            | stat.S_IXGRP
            | stat.S_IXOTH
        )

        return script