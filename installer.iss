; Turns the folder `build.py` produces into a single downloadable installer.
;
; Compiled by `make_installer.py`, which is the only place the Inno Setup
; invocation exists: a local build and a CI build therefore cannot drift apart.
; Everything that changes from one release to the next is defined on the command
; line, so publishing a version never means editing this file.

#ifndef AppVersion
  #error AppVersion is defined by make_installer.py
#endif
#ifndef SourceDir
  #error SourceDir is defined by make_installer.py
#endif
#ifndef OutputDir
  #error OutputDir is defined by make_installer.py
#endif
#ifndef OutputBaseFilename
  #error OutputBaseFilename is defined by make_installer.py
#endif
#ifndef IconFile
  #error IconFile is defined by make_installer.py
#endif

[Setup]
; Identifies the application across versions, so installing replaces the
; previous version instead of sitting beside it. It must never change.
AppId={{39744D93-7D18-435C-9B5D-7EB2268EEA23}
AppName=PVE Challenge
AppVersion={#AppVersion}
AppPublisher=Wilfried Jeanniard
DefaultDirName={autopf}\PVE Challenge
DefaultGroupName=PVE Challenge
OutputDir={#OutputDir}
OutputBaseFilename={#OutputBaseFilename}
SetupIconFile={#IconFile}
UninstallDisplayIcon={app}\pvechallenge.exe
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern

; Installs for the current user alone, under `%LOCALAPPDATA%\Programs`. Nothing
; is written outside their profile, so Windows raises no administrator prompt:
; one less obstacle between the download and the running application.
PrivilegesRequired=lowest

; The application is compiled by the 64-bit toolchain, and the game it drives
; runs nowhere else.
ArchitecturesAllowed=x64compatible

; Every page whose answer is always the same is removed. The installer exists to
; shorten the path between downloading and running, not to ask questions.
DisableDirPage=yes
DisableProgramGroupPage=yes
DisableReadyPage=yes
; The application picks its language from the system without asking, and so
; does its installer: with this off, Inno Setup uses the locale's language and
; falls back to the first one listed.
ShowLanguageDialog=no

; Metadata visible in the file's properties. Their absence is one of the signals
; that make an executable look dubious, and the installer is the file people
; actually download.
VersionInfoVersion={#AppVersion}
VersionInfoCompany=Wilfried Jeanniard
VersionInfoProductName=PVE Challenge
; Riot's trademark has no place in the installer's metadata either: the « Legal
; Jibber Jabber » policy forbids using it in naming.
VersionInfoDescription=Installeur de PVE Challenge

[Languages]
; Same rule as the application: the language follows the system locale, English
; and French are shipped, and there is no selector. English is listed first, so
; it is what an unmatched locale falls back to.
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[InstallDelete]
; Emptied before anything is copied, so an update leaves nothing of the version
; it replaces. Inno Setup removes only what it is told to remove, and the names
; the build produces are not stable: `python314.dll` becomes `python315.dll`, a
; dropped dependency takes its `.pyd` with it. A shipped preset left behind would
; be worse than dead weight -- the package enumerates its presets at run time, so
; it would keep appearing in the list, and collide with a preset of the same name
; the user later writes.
;
; The documentation warns against this wildcard, on two grounds: `{app}` may hold
; files the user owns, and it may point somewhere critical. Neither holds here.
; Everything the user owns lives under `%APPDATA%`, and the entry is skipped
; unless the directory already holds this application.
Type: filesandordirs; Name: "{app}\*"; Check: OurOwnInstall

[Files]
; The whole distribution folder. The executable needs what sits next to it, so
; nothing here is optional.
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; Flags: unchecked

[Icons]
Name: "{autoprograms}\PVE Challenge"; Filename: "{app}\pvechallenge.exe"
Name: "{autodesktop}\PVE Challenge"; Filename: "{app}\pvechallenge.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\pvechallenge.exe"; Description: "{cm:LaunchProgram,PVE Challenge}"; Flags: nowait postinstall skipifsilent

[Code]
function OurOwnInstall: Boolean;
// True when the destination already holds this application. `/DIR=` can point an
// installation anywhere, and a directory that is not ours is one we must not
// empty. A first installation finds nothing to delete either way.
begin
  Result := FileExists(ExpandConstant('{app}\pvechallenge.exe'));
end;
