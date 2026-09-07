"""Builds the Windows installer, from the folder `build.py` produced.

This file is the only place the Inno Setup command exists, so a local build and
a CI build cannot drift apart -- the same reason `build.py` holds the Nuitka
call alone. It runs after `build.py`, never instead of it: it packages the
distribution folder, it does not compile anything.

    uv run python build.py
    uv run python make_installer.py
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import build

ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / "installer.iss"

#: Inno Setup's compiler. Named without a path in the workflow, and looked up
#: below when it is not on `PATH`.
COMPILER_NAME = "ISCC"

#: Where Inno Setup installs itself, per-machine. The directory carries the
#: major version, which is why it is matched rather than named: a new major
#: would otherwise silently stop being found.
COMPILER_GLOB = "Inno Setup */ISCC.exe"
PROGRAM_FILES = ("ProgramFiles(x86)", "ProgramFiles")


def compiler() -> Path:
    """Locate the Inno Setup compiler.

    Not finding it is a build failure, never a skipped step: an installer that
    silently fails to be produced is a release that ships without the file the
    README tells people to download.
    """
    found = shutil.which(COMPILER_NAME)
    if found:
        return Path(found)

    searched = []
    for variable in PROGRAM_FILES:
        root = os.environ.get(variable)
        if not root:
            continue
        searched.append(str(Path(root) / COMPILER_GLOB))
        # Highest version first, so a machine carrying two majors uses the newer.
        candidates = sorted(Path(root).glob(COMPILER_GLOB), reverse=True)
        if candidates:
            return candidates[0]

    raise FileNotFoundError(
        f"Inno Setup not found. Searched: {COMPILER_NAME} on PATH, "
        + ", ".join(searched)
    )


def installer_name(version: str) -> str:
    """Basename of the installer, without its extension.

    The Release carries the tag, so the file people download carries the tag:
    `v1.2.0-rc1` names `pvechallenge-v1.2.0-rc1-setup`. The version *inside* the
    file stays numeric, because Windows version resources hold nothing else.
    """
    return f"pvechallenge-{os.environ.get(build.ENV_VERSION) or version}-setup"


def build_command(version: str, compiler_path: Path) -> list[str]:
    """Assemble the Inno Setup call.

    Everything the installer needs comes through the command line, so
    `installer.iss` never has to be edited to publish a version.
    """
    return [
        str(compiler_path),
        f"/DAppVersion={version}",
        f"/DSourceDir={build.APP_DIR}",
        f"/DOutputDir={build.DIST}",
        f"/DOutputBaseFilename={installer_name(version)}",
        f"/DIconFile={build.ICON}",
        str(SCRIPT),
    ]


def main() -> int:
    if not build.EXE.is_file():
        print(f"{build.EXE} is missing: run build.py first.", file=sys.stderr)
        return 1

    version = build.project_version()
    command = build_command(version, compiler())
    print(" ".join(command))

    completed = subprocess.run(command, cwd=ROOT)
    if completed.returncode != 0:
        return completed.returncode

    installer = build.DIST / f"{installer_name(version)}.exe"
    if not installer.is_file():
        print(f"Inno Setup returned 0 but {installer} is missing.", file=sys.stderr)
        return 1

    print(f"{installer}: {installer.stat().st_size} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
