#!/bin/bash

set -e

CURRENT="$1"
NEW="$2"
PID="$3"

if [ -z "$CURRENT" ] || [ -z "$NEW" ] || [ -z "$PID" ]; then
    echo "FEHLER: Parameter fehlen!"
    echo "Args: $@"
    exit 1
fi

DIR="$(dirname "$CURRENT")"

SCRIPT="$DIR/update.sh"
LOG="$DIR/update.log"

exec >>"$LOG" 2>&1

echo "========================================"
echo " WeintCompanion Linux Updater"
echo "========================================"

echo "Current : $CURRENT"
echo "New     : $NEW"
echo "PID     : $PID"

echo
echo "Warte auf Companion..."

#
# Warten bis Companion beendet wurde
#

while kill -0 "$PID" 2>/dev/null
do
    sleep 0.2
done

echo "Companion beendet."

#
# Alte Version ersetzen
#

echo "Ersetze AppImage..."

mv -f "$NEW" "$CURRENT"

chmod +x "$CURRENT"

#
# Neue Version starten
#

echo "Starte neue Version..."

nohup "$CURRENT" >/dev/null 2>&1 &
NEWPID=$!

#
# Kurz warten
#

sleep 2

#
# Prüfen ob sie wirklich läuft
#
# Bewusst NUR die direkte PID-Prüfung, kein "pgrep -f $CURRENT"
# als Fallback: dieses Skript bekommt $CURRENT selbst als
# Kommandozeilenargument übergeben (siehe oben, $1), daher matcht
# "pgrep -f $CURRENT" IMMER auch den eigenen update.sh-Prozess -
# ein Selbsttreffer, der eine fehlgeschlagene neue Version fälschlich
# als "erfolgreich gestartet" durchgehen lässt. Die PID-Prüfung
# ($NEWPID von "$!" direkt nach dem Start) ist zudem zuverlässiger:
# Bei AppImages läuft der eigentliche Prozess intern zwar oft aus
# einem gemounteten Pfad (/tmp/.mount_XXXX/...), aber genau die hier
# geprüfte äußere Runtime-PID bleibt dabei erhalten.
#

if kill -0 "$NEWPID" 2>/dev/null
then

    echo "Neue Version erfolgreich gestartet."

    #
    # Aufräumen
    #

    rm -f "$SCRIPT"
    rm -f "$LOG"

    exit 0

fi

echo
echo "FEHLER:"
echo "Neue Version konnte nicht gestartet werden."

exit 1