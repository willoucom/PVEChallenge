"""Localisation et lecture du fichier `lockfile` du client League of Legends.

Format du fichier (une seule ligne, separateur `:`) :
    <nom du process>:<pid>:<port>:<password>:<protocol>
"""

import os
from dataclasses import dataclass
from pathlib import Path

#: Chemin d'installation par defaut du client sous Windows.
DEFAULT_INSTALL_DIR = Path(r"C:\Games\Riot Games\League of Legends")

#: Variables d'environnement acceptees pour surcharger la localisation.
ENV_LOCKFILE = "LOLBOT_LOCKFILE"
ENV_INSTALL_DIR = "LOLBOT_INSTALL_DIR"


class LockfileError(RuntimeError):
    """Le lockfile est introuvable ou illisible."""


@dataclass(frozen=True)
class Credentials:
    """Contenu du lockfile, tel que lu sur le disque."""

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
        # L'utilisateur HTTP basic est toujours "riot" cote LCU.
        return ("riot", self.password)

    def redacted(self) -> str:
        return (
            f"{self.process} pid={self.pid} port={self.port} "
            f"protocol={self.protocol} password=<{len(self.password)} caracteres>"
        )


def resolve_lockfile_path(
    lockfile: str | os.PathLike[str] | None = None,
    install_dir: str | os.PathLike[str] | None = None,
) -> Path:
    """Determine le chemin du lockfile.

    Ordre de priorite : argument `lockfile`, variable d'environnement
    `LOLBOT_LOCKFILE`, argument `install_dir`, variable d'environnement
    `LOLBOT_INSTALL_DIR`, puis chemin d'installation par defaut.
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

    return DEFAULT_INSTALL_DIR / "lockfile"


def parse_lockfile(content: str, source: Path) -> Credentials:
    """Parse le contenu brut d'un lockfile."""
    fields = content.strip().split(":")
    if len(fields) != 5:
        raise LockfileError(
            f"{source}: format inattendu, 5 champs attendus "
            f"(nom:pid:port:password:protocol), {len(fields)} trouve(s)."
        )

    process, raw_pid, raw_port, password, protocol = fields
    try:
        pid = int(raw_pid)
        port = int(raw_port)
    except ValueError as exc:
        raise LockfileError(f"{source}: pid ou port non numerique ({raw_pid!r}, {raw_port!r}).") from exc

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
    """Lit le lockfile et retourne les identifiants de connexion a la LCU."""
    path = resolve_lockfile_path(lockfile, install_dir)
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise LockfileError(
            f"Lockfile introuvable : {path}\n"
            "Le client League of Legends doit etre ouvert (le fichier est cree au "
            "demarrage et supprime a la fermeture).\n"
            f"Si le client est installe ailleurs : --lockfile <chemin> ou "
            f"--install-dir <dossier>, ou les variables {ENV_LOCKFILE} / {ENV_INSTALL_DIR}."
        ) from exc
    except OSError as exc:
        raise LockfileError(f"Lecture impossible de {path} : {exc}") from exc

    return parse_lockfile(content, path)
