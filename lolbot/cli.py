"""Point d'entree en ligne de commande."""

import argparse
import sys

from .lockfile import (
    DEFAULT_INSTALL_DIR,
    ENV_INSTALL_DIR,
    ENV_LOCKFILE,
    LockfileError,
    read_credentials,
)

DIFFICULTIES = ("intro", "debutant", "intermediaire")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m lolbot",
        description=(
            "Recree un lobby de partie personnalisee League of Legends via l'API "
            "locale du client (LCU). Le client doit etre ouvert."
        ),
    )
    parser.add_argument(
        "--lockfile",
        help=f"Chemin complet du fichier lockfile (defaut : variable {ENV_LOCKFILE}, sinon <install-dir>/lockfile).",
    )
    parser.add_argument(
        "--install-dir",
        help=(
            "Dossier d'installation du client, contenant le lockfile "
            f"(defaut : variable {ENV_INSTALL_DIR}, sinon {DEFAULT_INSTALL_DIR})."
        ),
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="Timeout HTTP en secondes (defaut : 10).",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    lobby_parser = subparsers.add_parser(
        "lobby",
        help="Cree le lobby et ajoute les bots decrits par un preset.",
    )
    lobby_parser.add_argument("preset", help="Nom d'un preset de presets/ (ex : ireaz) ou chemin d'un fichier JSON.")
    lobby_parser.add_argument(
        "--difficulty",
        choices=DIFFICULTIES,
        help="Surcharge la difficulte des bots definie par le preset.",
    )

    discover_parser = subparsers.add_parser(
        "discover",
        help="Observe le lobby (GET seulement) et affiche le diff du JSON a chaque changement.",
    )
    discover_parser.add_argument(
        "--interval",
        type=float,
        default=0.5,
        help="Intervalle de polling en secondes (defaut : 0.5).",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        credentials = read_credentials(args.lockfile, args.install_dir)
    except LockfileError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"Lockfile : {credentials.source}")
    print(f"Identifiants : {credentials.redacted()}")

    # Import tardif : `requests` n'est necessaire qu'a partir d'ici.
    from .champions import ChampionError
    from .client import LcuClient, LcuError, check_connection
    from .discover import discover
    from .lobby import LobbyError, PresetError, run_lobby

    with LcuClient(credentials, timeout=args.timeout) as client:
        try:
            summoner = check_connection(client)
        except LcuError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        except Exception as exc:  # connexion refusee, TLS, timeout...
            print(f"Connexion a la LCU impossible ({client.base_url}) : {exc!r}", file=sys.stderr)
            return 1

        display_name = summoner.get("gameName") or summoner.get("displayName") or "<inconnu>"
        print(f"Connecte en tant que : {display_name}")
        print()

        if args.command == "discover":
            return discover(client, interval=args.interval)

        try:
            return run_lobby(client, args.preset, args.difficulty)
        except (PresetError, LobbyError, ChampionError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        except LcuError as exc:
            print(str(exc), file=sys.stderr)
            return 1


if __name__ == "__main__":
    raise SystemExit(main())
