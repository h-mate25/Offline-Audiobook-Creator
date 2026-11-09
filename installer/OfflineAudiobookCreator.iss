#define MyAppName "Offline Audiobook Creator"
#define MyAppPublisher "h-mate25"
#ifndef MyAppVersion
  #define MyAppVersion "1.0.1"
#endif
#define MyAppExeName "Offline-Audiobook-Creator-Launcher.exe"

[Setup]
AppId={{B4D9B9F7-DC16-4F19-A86E-4BB8C5C3C62B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL=https://github.com/h-mate25/Offline-Audiobook-Creator
AppSupportURL=https://github.com/h-mate25/Offline-Audiobook-Creator
DefaultDirName={autopf}\Offline Audiobook Creator
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\release
OutputBaseFilename=Offline-Audiobook-Creator-Setup-{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}
SetupLogging=yes
VersionInfoVersion={#MyAppVersion}.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} Windows telepítő
VersionInfoCopyright=Copyright (c) 2026 {#MyAppPublisher}

[Languages]
Name: "hungarian"; MessagesFile: "compiler:Languages\Hungarian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Asztali parancsikon létrehozása"; GroupDescription: "Parancsikonok:"
Name: "dependencies"; Description: "Docker Desktop és WSL2 ellenőrzése/telepítése"; GroupDescription: "Első indítási előkészítés:"; Flags: checkedonce

[Files]
Source: "..\release\Offline-Audiobook-Creator-Launcher.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\docker-compose.yml"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\Dockerfile"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\.dockerignore"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\CHANGELOG.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\src\*"; DestDir: "{app}\src"; Excludes: "__pycache__\*;*.pyc;*.egg-info\*"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "..\docs\*"; DestDir: "{app}\docs"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "..\models\*"; DestDir: "{app}\models"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "install-dependencies.ps1"; DestDir: "{app}\installer"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\installer\install-dependencies.ps1"" -InstallDocker -InstallWsl"; Tasks: dependencies; StatusMsg: "Docker Desktop és WSL2 ellenőrzése..."; Flags: waituntilterminated
Filename: "{app}\{#MyAppExeName}"; Description: "Az Offline Audiobook Creator elindítása"; Flags: nowait postinstall skipifsilent

