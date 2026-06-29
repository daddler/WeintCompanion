#!/bin/bash

set -e

echo ""
echo "========================================"
echo " WeintCompanion AppImage Builder"
echo "========================================"
echo ""

APPDIR="AppDir"

rm -rf "$APPDIR"

mkdir -p "$APPDIR/usr/bin"

echo "Kopiere Programm..."

cp -r dist/WeintCompanion/* "$APPDIR/usr/bin/"

echo "Kopiere AppRun..."

cp packaging/linux/AppRun "$APPDIR/"

chmod +x "$APPDIR/AppRun"

echo "Kopiere Desktop-Datei..."

cp packaging/linux/WeintCompanion.desktop "$APPDIR/"

echo "Kopiere Icon..."

cp assets/icon.png "$APPDIR/icon.png"

echo "Erzeuge AppImage..."

linuxdeploy \
    --appdir "$APPDIR" \
    --desktop-file "$APPDIR/WeintCompanion.desktop" \
    --icon-file "$APPDIR/icon.png" \
    --output appimage

echo ""
echo "========================================"
echo " AppImage erfolgreich erstellt!"
echo "========================================"
echo ""

ls -lh *.AppImage