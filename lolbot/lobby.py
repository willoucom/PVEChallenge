"""Commande `lobby` : cree le lobby personnalise et y ajoute les bots d'un preset.

Les valeurs ci-dessous ont ete relevees sur un client League of Legends, via
`GET /help?format=Full` et `GET /lol-game-queues/v1/queues`, puis confirmees par
des appels reels.
"""

import json
import time
from pathlib import Path
from typing import Any

from .champions import ChampionError, load_bot_champions, resolve
from .client import LcuClient

LOBBY_PATH = "/lol-lobby/v2/lobby"
BOTS_PATH = "/lol-lobby/v1/lobby/custom/bots"

PRESETS_DIR = Path(__file__).resolve().parent.parent / "presets"

#: File « Faille — partie personnalisee aveugle ». `queueId: 0` fait repondre
#: `500 INVALID_LOBBY` au client, quelle que soit la configuration envoyee.
CUSTOM_QUEUE_ID = 3100

#: `gameTypeConfig.id` que le client associe a cette file, attendu dans `mutators`.
BLIND_PICK_MUTATOR_ID = 19

#: Carte et mode de cette file. Les envoyer dans `configuration` ne les choisit
#: pas : le client les deduit du `queueId` et ignore ce que le corps annonce. Ils
#: ne sont donc pas reglables par preset, et sont figes ici pour que le corps
#: envoye decrive le lobby reellement cree.
SUMMONERS_RIFT_MAP_ID = 11
CLASSIC_GAME_MODE = "CLASSIC"

#: Vocabulaire des presets -> valeurs de l'enum `LolLobbyLobbyBotDifficulty`.
DIFFICULTIES = {
    "intro": "RSINTRO",
    "debutant": "RSBEGINNER",
    "intermediaire": "RSINTERMEDIATE",
}

#: Vocabulaire des presets -> valeurs de l'enum `Position` du client.
POSITIONS = {
    "top": "TOP",
    "jungle": "JUNGLE",
    "mid": "MIDDLE",
    "bot": "BOTTOM",
    "support": "UTILITY",
}

#: `teamId` est une chaine cote API, et vaut 100 pour mon equipe, 200 pour l'autre.
TEAM_IDS = {"mine": "100", "enemy": "200"}


class PresetError(RuntimeError):
    """Preset introuvable, illisible ou incoherent."""


class LobbyError(RuntimeError):
    """Le lobby n'a pas pu etre amene dans l'etat attendu."""


def preset_path(name: str) -> Path:
    """Resout un nom de preset : chemin de fichier, ou nom court dans `presets/`."""
    candidate = Path(name)
    if candidate.suffix and candidate.exists():
        return candidate
    return PRESETS_DIR / f"{name}.json"


def load_preset(name: str) -> dict[str, Any]:
    """Charge et valide un preset."""
    path = preset_path(name)
    try:
        preset = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        available = sorted(p.stem for p in PRESETS_DIR.glob("*.json"))
        raise PresetError(
            f"Preset introuvable : {path}. Disponibles : {', '.join(available) or '<aucun>'}."
        ) from exc
    except json.JSONDecodeError as exc:
        raise PresetError(f"{path} n'est pas un JSON valide : {exc}") from exc

    difficulty = preset.get("difficulty")
    if difficulty not in DIFFICULTIES:
        raise PresetError(
            f"{path} : difficulte {difficulty!r} inconnue. Attendu : {', '.join(DIFFICULTIES)}."
        )

    teams = preset.get("teams", {})
    for side in teams:
        if side not in TEAM_IDS:
            raise PresetError(
                f"{path} : equipe {side!r} inconnue. Attendu : {', '.join(TEAM_IDS)}."
            )
        for bot in teams[side].get("bots", []):
            if bot.get("role") not in POSITIONS:
                raise PresetError(
                    f"{path} : role {bot.get('role')!r} inconnu pour {bot.get('champion')!r}. "
                    f"Attendu : {', '.join(POSITIONS)}."
                )
    return preset


def build_lobby_payload(preset: dict[str, Any]) -> dict[str, Any]:
    """Construit le corps du POST de creation de lobby."""
    lobby = preset.get("lobby", {})
    return {
        "queueId": CUSTOM_QUEUE_ID,
        "customGameLobby": {
            "lobbyName": lobby.get("lobbyName", preset.get("name", "")),
            "lobbyPassword": "",
            "configuration": {
                "mapId": SUMMONERS_RIFT_MAP_ID,
                "gameMode": CLASSIC_GAME_MODE,
                "mutators": {"id": BLIND_PICK_MUTATOR_ID},
                "spectatorPolicy": lobby.get("spectatorPolicy", "AllAllowed"),
                "teamSize": 5,
            },
        },
    }


def build_bot_payload(champion_id: int, difficulty: str, side: str, role: str) -> dict[str, Any]:
    """Construit le corps du POST d'ajout de bot.

    `botUuid` est declare obligatoire par le client mais accepte une chaine vide :
    c'est le client qui genere l'identifiant.
    """
    return {
        "championId": champion_id,
        "botDifficulty": DIFFICULTIES[difficulty],
        "teamId": TEAM_IDS[side],
        "position": POSITIONS[role],
        "botUuid": "",
    }


def close_existing_lobby(client: LcuClient, timeout: float = 5.0) -> bool:
    """Ferme le lobby ouvert s'il y en a un. Retourne True si un lobby a ete ferme.

    Creer par-dessus un lobby existant ne suffit pas : le POST applique bien la
    configuration, mais conserve les membres deja presents, et un bot dont la
    position est deja occupee est refuse sans erreur. Sans fermeture prealable, la
    commande afficherait un succes en laissant les anciens bots en place.
    """
    if client.request("GET", LOBBY_PATH).status_code != 200:
        return False

    client.request_checked("DELETE", LOBBY_PATH)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if client.request("GET", LOBBY_PATH).status_code == 404:
            return True
        time.sleep(0.2)

    raise LobbyError(
        f"Le lobby existant repond encore {timeout} s apres sa fermeture. "
        "Verifie l'etat du client."
    )


def run_lobby(client: LcuClient, preset_name: str, difficulty: str | None = None) -> int:
    """Cree le lobby du preset et y ajoute tous ses bots."""
    preset = load_preset(preset_name)
    if difficulty is not None:
        preset["difficulty"] = difficulty
    chosen = preset["difficulty"]

    # Resoudre tous les champions avant de toucher au client : un nom errone doit
    # faire echouer la commande sans avoir ferme le lobby en cours ni laisser
    # derriere elle un lobby a moitie rempli.
    champions = load_bot_champions(client)
    planned = [
        (side, bot["champion"], resolve(champions, bot["champion"]), bot["role"])
        for side, team in preset.get("teams", {}).items()
        for bot in team.get("bots", [])
    ]

    if close_existing_lobby(client):
        print("Lobby existant ferme.")

    payload = build_lobby_payload(preset)
    configuration = payload["customGameLobby"]["configuration"]
    print(
        f"Creation du lobby {payload['customGameLobby']['lobbyName']!r} "
        f"(mapId={configuration['mapId']}, {configuration['gameMode']}, "
        f"queueId={payload['queueId']})"
    )
    client.post_json(LOBBY_PATH, payload)

    for side, champion, champion_id, role in planned:
        client.post_json(BOTS_PATH, build_bot_payload(champion_id, chosen, side, role))
        print(
            f"  + {champion} ({champion_id}) {POSITIONS[role]} "
            f"{DIFFICULTIES[chosen]} equipe {TEAM_IDS[side]}"
        )

    print()
    print(f"Lobby pret : {len(planned)} bot(s) ajoute(s). Lance la partie depuis le client.")
    return 0
