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

pyinstaller WeintCompanion.spec

echo ""
echo "========================================"
echo " Build abgeschlossen!"
echo "========================================"
echo ""

echo "Ausgabe befindet sich unter:"
echo "dist/WeintCompanion"