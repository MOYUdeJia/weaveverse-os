; Weaveverse OS installer. User data in %APPDATA%\WeaveverseOS is not removed on uninstall.

#define MyAppName "Weaveverse OS"
#define MyAppExe "WeaveverseOS.exe"
#define MyAppVersion "10.1"

[Setup]
AppId={{8C4E2A71-6B0E-4C3A-9F1D-7A2B6E5D10A4}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\WeaveverseOS
DefaultGroupName=Weaveverse OS
DisableProgramGroupPage=yes
OutputDir=dist
OutputBaseFilename=WeaveverseOS-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExe}
PrivilegesRequired=admin

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加图标:"; Flags: unchecked

[Files]
Source: "dist\WeaveverseOS\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Weaveverse OS"; Filename: "{app}\{#MyAppExe}"
Name: "{autodesktop}\Weaveverse OS"; Filename: "{app}\{#MyAppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExe}"; Description: "启动 Weaveverse OS"; Flags: nowait postinstall skipifsilent
