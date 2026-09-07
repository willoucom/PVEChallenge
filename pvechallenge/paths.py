"""Locations of user-owned data, kept outside the package.

The package is read-only: it may be installed in a protected directory, or frozen
into an executable whose extraction directory is temporary. Everything the user
adds or configures therefore lives next to it, in their profile.
"""

import os
from pathlib import Path

#: Application directory name, shared by every location below.
APP_DIR_NAME = "pvechallenge"


def user_data_dir() -> Path:
    r"""User data directory: `%APPDATA%\pvechallenge` on Windows.

    Windows defines `APPDATA` for every interactive session. Falling back to the
    home directory covers environments where it is not set, rather than failing
    on a missing variable.
    """
    appdata = os.environ.get("APPDATA")
    base = Path(appdata) if appdata else Path.home()
    return base / APP_DIR_NAME


def user_presets_dir() -> Path:
    """Directory where the user drops their own presets."""
    return user_data_dir() / "presets"
