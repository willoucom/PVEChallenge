r"""Persisted user configuration: `%APPDATA%\pvechallenge\config.json`.

It exists for one reason only: to remember where the lockfile is when the client
is not installed at the standard location, so it does not have to be supplied on
every run. It holds nothing else.
"""

import json
from dataclasses import dataclass, replace
from pathlib import Path

from .i18n import t
from .paths import user_data_dir

#: Configuration file name, inside the user data directory.
CONFIG_FILENAME = "config.json"


class ConfigError(RuntimeError):
    """The configuration file exists but cannot be used."""


def config_path() -> Path:
    """Location of the configuration file."""
    return user_data_dir() / CONFIG_FILENAME


@dataclass(frozen=True)
class Config:
    """Settings remembered from one run to the next."""

    #: Full path to the lockfile, or None to let the other sources apply.
    lockfile: str | None = None


def load_config() -> Config:
    """Read the configuration. A missing file yields an empty configuration.

    A file that exists but cannot be read raises: staying silent would apply the
    default path while letting the user believe the saved setting is in effect.
    """
    path = config_path()
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return Config()
    except OSError as exc:
        raise ConfigError(t("config.unreadable", path=path, error=exc)) from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ConfigError(t("config.invalid_json", path=path, error=exc)) from exc

    if not isinstance(data, dict):
        raise ConfigError(t("config.not_an_object", path=path, found=type(data).__name__))

    lockfile = data.get("lockfile")
    if lockfile is not None and not isinstance(lockfile, str):
        raise ConfigError(
            t("config.lockfile_not_a_string", path=path, found=type(lockfile).__name__)
        )

    return Config(lockfile=lockfile or None)


def save_config(config: Config) -> Path:
    """Write the configuration and return its path. Creates the directory if needed."""
    path = config_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"lockfile": config.lockfile}, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise ConfigError(t("config.unwritable", path=path, error=exc)) from exc
    return path


def set_lockfile(lockfile: str | None) -> Path:
    """Save the only setting there is, preserving the rest of the file."""
    return save_config(replace(load_config(), lockfile=lockfile or None))
