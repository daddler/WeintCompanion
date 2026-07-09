#define MyAppName "WeintCompanion"
#define MyAppVersion "0.5.5"
#define MyAppPublisher "Fabi (daddler2419)"
#define MyAppExeName "WeintCompanion.exe"

[Setup]
AppId={{F88D18D2-1D31-4D69-9E56-9EAA4E4E4F21}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\WeintCompanion
DefaultGroupName={#MyAppName}
OutputDir=..\dist
OutputBaseFilename=WeintCompanion-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=lowest

SetupIconFile=..\assets\icon.ico

; Erkennt laufende WeintCompanion-Instanzen automatisch
; (Windows Restart Manager) und fragt, ob sie geschlossen
; werden sollen, statt gesperrte Dateien stillschweigend
; zu überspringen.
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "Desktop-Verknüpfung erstellen"; GroupDescription: "Zusätzliche Aufgaben:"

[Files]
Source: "..\dist\WeintCompanion\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Weint Companion"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Weint Companion"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Weint Companion starten"; Flags: nowait postinstall skipifsilent