Write-Host ""
Write-Host "========================================"
Write-Host " WeintCompanion Windows Builder"
Write-Host "========================================"
Write-Host ""

Write-Host "Bereinige alte Builds..."

if (Test-Path build) {
    Remove-Item build -Recurse -Force
}

if (Test-Path dist) {
    Remove-Item dist -Recurse -Force
}

Write-Host "Starte PyInstaller..."

pyinstaller WeintCompanion.spec

Write-Host "Erstelle Installer..."

iscc packaging\installer.iss

Write-Host ""
Write-Host "========================================"
Write-Host " Build abgeschlossen!"
Write-Host "========================================"