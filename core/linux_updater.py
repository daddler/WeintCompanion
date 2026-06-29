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

#
# Kurz warten bis Companion beendet wurde
#

sleep 2

echo "Aktualisiere WeintCompanion..."

#
# Neue Version über die alte kopieren
#

cp -f "{downloaded_appimage}" "{current_appimage}"

#
# Ausführbar machen
#

chmod +x "{current_appimage}"

#
# Download löschen
#

rm -f "{downloaded_appimage}"

#
# Neue Version starten
#

"{current_appimage}" &

#
# Script löschen
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