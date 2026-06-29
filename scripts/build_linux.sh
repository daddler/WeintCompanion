#!/bin/bash

set -e

echo ""
echo "========================================"
echo " WeintCompanion Linux Builder"
echo "========================================"
echo ""

echo "Bereinige alte Builds..."

rm -rf build
rm -rf dist
rm -rf AppDir

echo "Starte PyInstaller..."

pyinstaller WeintCompanion.spec

echo ""
echo "========================================"
echo " PyInstaller erfolgreich"
echo "========================================"
echo ""

if command -v linuxdeploy >/dev/null 2>&1; then

    echo "linuxdeploy gefunden."

else

    echo "linuxdeploy nicht installiert."
    echo "AppImage wird übersprungen."

fi

echo ""
echo "Ausgabe befindet sich unter:"
echo "dist/WeintCompanion"