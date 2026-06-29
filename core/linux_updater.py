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

echo "Warte bis WeintCompanion beendet wurde..."

#
# Warten bis die gestartete AppImage nicht mehr läuft
#

while pgrep -f "{current_appimage}" >/dev/null; do
    sleep 0.2
done

echo "Aktualisiere WeintCompanion..."

#
# Neue Version über die alte kopieren
#

cp -f "{downloaded_appimage}" "{current_appimage}"

if [ $? -ne 0 ]; then
    echo "Fehler beim Kopieren."
    exit 1
fi

#
# Ausführbar machen
#

chmod +x "{current_appimage}"

#
# Temporären Download löschen
#

rm -f "{downloaded_appimage}"

#
# Neue Version starten
#

"{current_appimage}" &

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