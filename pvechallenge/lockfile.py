"""Locating and reading the League of Legends client's `lockfile`.

File format (a single line, `:` separated):
    <process name>:<pid>:<port>:<password>:<protocol>
"""

import os
from dataclasses import dataclass
from pathlib import Path

from .config import config_path, load_config
from .i18n import t

#: Default install path of the client on Windows.
DEFAULT_INSTALL_DIR = Path(r"C:\Riot Games\League of Legends")

#: Environment variables accepted to override the location.
ENV_LOCKFILE = "PVECHALLENGE_LOCKFILE"
ENV_INSTALL_DIR = "PVECHALLENGE_INSTALL_DIR"


class LockfileError(RuntimeError):
    """The lockfile is missing or unreadable."""


@dataclass(frozen=True)
class Credentials:
    """Contents of the lockfile, as read from disk."""

    process: str
    pid: int
    port: int
    password: str
    protocol: str
    source: Path

    @property
    def base_url(self) -> str:
        return f"{self.protocol.lower()}://127.0.0.1:{self.port}"

    @property
    def auth(self) -> tuple[str, str]:
        # The HTTP basic user is always "riot" on the LCU side.
        return ("riot", self.password)

    def redacted(self) -> str:
        """Readable form, safe to log: the password is replaced by its length."""
        return t(
            "lockfile.redacted",
            process=self.process,
            pid=self.pid,
            port=self.port,
            protocol=self.protocol,
            length=len(self.password),
        )


def resolve_lockfile_path(
    lockfile: str | os.PathLike[str] | None = None,
    install_dir: str | os.PathLike[str] | None = None,
) -> Path:
    """Work out the path to the lockfile.

    Priority order: the `lockfile` argument, the `PVECHALLENGE_LOCKFILE`
    environment variable, the `install_dir` argument, the
    `PVECHALLENGE_INSTALL_DIR` environment variable, the saved setting, then the
    default install path.

    An argument or an environment variable is a deliberate, one-off override, so
    it comes before the saved setting, which itself comes before the hardcoded
    default.
    """
    if lockfile is not None:
        return Path(lockfile)

    env_lockfile = os.environ.get(ENV_LOCKFILE)
    if env_lockfile:
        return Path(env_lockfile)

    if install_dir is not None:
        return Path(install_dir) / "lockfile"

    env_install_dir = os.environ.get(ENV_INSTALL_DIR)
    if env_install_dir:
        return Path(env_install_dir) / "lockfile"

    configured = load_config().lockfile
    if configured:
        return Path(configured)

    return DEFAULT_INSTALL_DIR / "lockfile"


def parse_lockfile(content: str, source: Path) -> Credentials:
    """Parse the raw contents of a lockfile."""
    fields = content.strip().split(":")
    if len(fields) != 5:
        raise LockfileError(t("lockfile.bad_shape", path=source, count=len(fields)))

    process, raw_pid, raw_port, password, protocol = fields
    try:
        pid = int(raw_pid)
        port = int(raw_port)
    except ValueError as exc:
        raise LockfileError(
            t("lockfile.bad_numbers", path=source, pid=raw_pid, port=raw_port)
        ) from exc

    return Credentials(
        process=process,
        pid=pid,
        port=port,
        password=password,
        protocol=protocol,
        source=source,
    )


def read_credentials(
    lockfile: str | os.PathLike[str] | None = None,
    install_dir: str | os.PathLike[str] | None = None,
) -> Credentials:
    """Read the lockfile and return the credentials used to reach the LCU."""
    path = resolve_lockfile_path(lockfile, install_dir)
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise LockfileError(
            t(
                "lockfile.not_found",
                path=path,
                config=config_path(),
                env_lockfile=ENV_LOCKFILE,
                env_install_dir=ENV_INSTALL_DIR,
            )
        ) from exc
    except OSError as exc:
        raise LockfileError(t("lockfile.unreadable", path=path, error=exc)) from exc

    return parse_lockfile(content, path)
