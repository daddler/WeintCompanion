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

echo "Starte PyInstaller..."

pyinstaller \
    --noconfirm \
    --clean \
    --windowed \
    --name WeintCompanion \
    --icon assets/icon.png \
    --add-data "assets:assets" \
    app.py

echo ""
echo "========================================"
echo " Build abgeschlossen!"
echo "========================================"
echo ""

echo "Ausgabe befindet sich unter:"
echo "dist/WeintCompanion"