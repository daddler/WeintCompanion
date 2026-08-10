# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ["app.py"],
    pathex=[],
    binaries=[],
    datas=[
        # "assets" enthaelt auch assets/fonts - Inter und JetBrains
        # Mono liegen der App seit 2.0 bei und werden beim Start ueber
        # QFontDatabase angemeldet. Ohne sie faellt Qt wortlos auf eine
        # Systemschrift zurueck (siehe gui/theme/fonts.py).
        ("assets", "assets"),
        ("packaging/linux/updater.sh", "packaging/linux"),
        ["resources/icons", "resources/icons"],
        ("CHANGELOG.md", "."),
    ],
    hiddenimports=[
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="WeintCompanion",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets/icon.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="WeintCompanion",
)