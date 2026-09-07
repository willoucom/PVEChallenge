"""Builds the distributed Windows executable, through Nuitka.

This file is the only place the build command exists. The release workflow
calls it as-is, exactly as a developer would locally: a CI build and a local
build therefore cannot drift apart.

Nuitka compiles `main.py`, not `pvechallenge/gui.py`: a package module compiled
as a script loses its relative imports.
"""

import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENTRY = ROOT / "main.py"
DIST = ROOT / "dist"

#: Executable icon. It lives in the package, which is also where the window
#: reads it from: one file serves both the executable and the title bar.
ICON = ROOT / "pvechallenge" / "icon.ico"

COMPANY_NAME = "Wilfried Jeanniard"
PRODUCT_NAME = "PVE Challenge"
#: Riot's trademark has no place in the binary's metadata: the « Legal Jibber
#: Jabber » policy forbids using it in naming.
FILE_DESCRIPTION = "Prepare une partie personnalisee contre des adversaires informatiques"


#: Set by the release workflow from the tag being built. The tag is what a user
#: downloads, so it is the tag the binary must announce.
ENV_VERSION = "PVECHALLENGE_VERSION"

#: Written by the build so the window can show the same version as the file
#: properties. Not tracked: a source tree has no version, and the interface
#: says `dev` when this module is absent.
STAMP = ROOT / "pvechallenge" / "_version.py"


def numeric_version(raw: str) -> str:
    """Keep the leading dotted-numeric part of a version.

    Windows version resources hold numbers and nothing else, and Nuitka refuses
    anything they cannot express. A tag may carry a leading `v` and a trailing
    qualifier -- `v1.2.3-rc1` -- so both are stripped rather than failing a build
    over a pre-release name.

    A version with no number at all is another matter: it would silently stamp
    the binary with something meaningless, so it raises.
    """
    match = re.match(r"\d+(?:\.\d+)*", raw.lstrip("vV"))
    if match is None:
        raise ValueError(f"{raw!r} holds no version number Windows could carry")
    return match.group(0)


def project_version() -> str:
    """Version stamped into the executable.

    The release workflow sets `PVECHALLENGE_VERSION` from the tag, so a published
    binary announces the version it was published under. A local build has no
    tag, and falls back to what pyproject.toml declares.
    """
    override = os.environ.get(ENV_VERSION)
    if override:
        return numeric_version(override)

    with (ROOT / "pyproject.toml").open("rb") as handle:
        return numeric_version(tomllib.load(handle)["project"]["version"])


def build_command() -> list[str]:
    """Assemble the Nuitka call."""
    version = project_version()
    command = [
        sys.executable,
        "-m",
        "nuitka",
        "--onefile",
        # No console: the application is a window, not a command.
        "--windows-console-mode=disable",
        # tkinter is not picked up by import analysis alone.
        "--enable-plugin=tk-inter",
        # Embeds pvechallenge/presets/*.json, which Nuitka does not see as code.
        "--include-package-data=pvechallenge",
        # The stamped version is imported inside a `try`, which static analysis
        # does not follow: without this, the executable would report `dev`.
        "--include-module=pvechallenge._version",
        f"--output-dir={DIST}",
        "--output-filename=pvechallenge.exe",
        "--remove-output",
        # The CI runner has nobody to answer a prompt.
        "--assume-yes-for-downloads",
        # Metadata visible in the file's properties: their absence is one of the
        # signals that make an executable look dubious.
        f"--company-name={COMPANY_NAME}",
        f"--product-name={PRODUCT_NAME}",
        f"--file-description={FILE_DESCRIPTION}",
        f"--file-version={version}",
        f"--product-version={version}",
    ]
    if ICON.is_file():
        command.append(f"--windows-icon-from-ico={ICON}")
    command.append(str(ENTRY))
    return command


def stamp_version(version: str) -> Path:
    """Write the version into the package, for the interface to read back."""
    contenu = [
        '"""Generated at build time. Absent from a source tree, by design."""',
        "",
        f'VERSION = "{version}"',
        "",
    ]
    STAMP.write_text("\n".join(contenu), encoding="utf-8")
    return STAMP


def main() -> int:
    if not ICON.is_file():
        print(f"Icone absente ({ICON}) : build avec l'icone par defaut.", file=sys.stderr)

    version = project_version()
    print(f"{stamp_version(version)} : VERSION = {version!r}")

    command = build_command()
    print(" ".join(command))
    completed = subprocess.run(command, cwd=ROOT)
    if completed.returncode != 0:
        return completed.returncode

    produced = DIST / "pvechallenge.exe"
    if not produced.is_file():
        print(f"Nuitka a rendu 0 mais {produced} est absent.", file=sys.stderr)
        return 1
    print(f"{produced} ({produced.stat().st_size} octets)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
