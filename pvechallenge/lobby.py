"""Creating the custom lobby and filling it with the bots of a preset.

The values below were read from a running League of Legends client, through
`GET /help?format=Full` and `GET /lol-game-queues/v1/queues`, then confirmed by
real calls.
"""

import json
import time
from pathlib import Path
from typing import Any, Callable

from .champions import ChampionError, load_bot_champions, resolve
from .client import LcuClient
from .i18n import t
from .paths import user_presets_dir

#: Where progress messages go. The window wires its log here; a call from the
#: sources may wire `print`. Errors do not travel this way: they are raised, and
#: reported by the caller.
Report = Callable[[str], None]

LOBBY_PATH = "/lol-lobby/v2/lobby"
BOTS_PATH = "/lol-lobby/v1/lobby/custom/bots"

#: Presets shipped with the tool. They live in the package, so they travel with
#: the wheel and with the executable, and they are read-only.
BUILTIN_PRESETS_DIR = Path(__file__).resolve().parent / "presets"

#: File « Faille — partie personnalisee aveugle ». `queueId: 0` fait repondre
#: `500 INVALID_LOBBY` au client, quelle que soit la configuration envoyee.
CUSTOM_QUEUE_ID = 3100

#: `gameTypeConfig.id` the client ties to this queue, expected inside `mutators`.
BLIND_PICK_MUTATOR_ID = 19

#: Map and mode of this queue. Sending them in `configuration` does not select
#: them: the client derives them from `queueId` and ignores what the body claims.
#: They are therefore not preset-configurable, and are pinned here so that the
#: body sent describes the lobby actually created.
SUMMONERS_RIFT_MAP_ID = 11
CLASSIC_GAME_MODE = "CLASSIC"

#: Preset vocabulary -> values of the client's `LolLobbyLobbyBotDifficulty` enum.
DIFFICULTIES = {
    "intro": "RSINTRO",
    "debutant": "RSBEGINNER",
    "intermediaire": "RSINTERMEDIATE",
}

#: Preset vocabulary -> values of the client's `Position` enum.
POSITIONS = {
    "top": "TOP",
    "jungle": "JUNGLE",
    "mid": "MIDDLE",
    "bot": "BOTTOM",
    "support": "UTILITY",
}

#: `teamId` is a string on the API side: 100 for my team, 200 for the other one.
TEAM_IDS = {"mine": "100", "enemy": "200"}


class PresetError(RuntimeError):
    """Preset missing, unreadable or inconsistent."""


class LobbyError(RuntimeError):
    """The lobby could not be brought into the expected state."""


def _json_files(directory: Path) -> dict[str, Path]:
    """Short name -> path, for the JSON files of a directory. Missing directory: empty."""
    if not directory.is_dir():
        return {}
    return {path.stem: path for path in sorted(directory.glob("*.json"))}


def builtin_presets() -> dict[str, Path]:
    """Presets shipped with the tool."""
    return _json_files(BUILTIN_PRESETS_DIR)


def user_presets() -> dict[str, Path]:
    """Presets the user dropped into their profile."""
    return _json_files(user_presets_dir())


def available_presets() -> dict[str, Path]:
    """Usable presets, both sources merged.

    A name carried by both sources is usable through neither: it is excluded
    here, and `preset_path` refuses it explicitly.
    """
    builtin = builtin_presets()
    user = user_presets()
    collisions = builtin.keys() & user.keys()
    return {name: path for name, path in (builtin | user).items() if name not in collisions}


def preset_label(path: Path) -> str:
    """Displayable name of a preset: its `name` field, falling back to the file name.

    Listing the presets must never fail on the contents of one of them: a file
    whose JSON is broken, or whose `name` is absent or is not usable text, still
    appears, under the only name certain to exist. The failure surfaces when the
    preset is applied, where `load_preset` reports it in full.
    """
    try:
        preset = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return path.stem

    label = preset.get("name") if isinstance(preset, dict) else None
    if isinstance(label, str) and label.strip():
        return label
    return path.stem


def preset_path(name: str) -> Path:
    """Resolve a preset name: file path, user preset, or shipped preset."""
    candidate = Path(name)
    if candidate.suffix and candidate.exists():
        return candidate

    builtin = builtin_presets()
    user = user_presets()

    if name in builtin and name in user:
        raise PresetError(t("preset.collision", name=name, path=user[name]))
    if name in user:
        return user[name]
    if name in builtin:
        return builtin[name]

    available = ", ".join(sorted(available_presets())) or "<none>"
    raise PresetError(
        t("preset.not_found", name=name, available=available, folder=user_presets_dir())
    )


def load_preset(name: str) -> dict[str, Any]:
    """Load and validate a preset."""
    path = preset_path(name)
    try:
        preset = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PresetError(t("preset.file_missing", path=path)) from exc
    except json.JSONDecodeError as exc:
        raise PresetError(t("preset.invalid_json", path=path, error=exc)) from exc

    difficulty = preset.get("difficulty")
    if difficulty not in DIFFICULTIES:
        raise PresetError(
            t("preset.unknown_difficulty", path=path, value=difficulty,
              expected=", ".join(DIFFICULTIES))
        )

    teams = preset.get("teams", {})
    for side in teams:
        if side not in TEAM_IDS:
            raise PresetError(
                t("preset.unknown_team", path=path, value=side, expected=", ".join(TEAM_IDS))
            )
        for bot in teams[side].get("bots", []):
            if bot.get("role") not in POSITIONS:
                raise PresetError(
                    t("preset.unknown_role", path=path, role=bot.get("role"),
                      champion=bot.get("champion"), expected=", ".join(POSITIONS))
                )
    return preset


def build_lobby_payload(preset: dict[str, Any]) -> dict[str, Any]:
    """Build the body of the lobby creation POST."""
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
    """Build the body of the bot addition POST.

    The client declares `botUuid` mandatory but accepts an empty string: it is
    the client that generates the identifier.
    """
    return {
        "championId": champion_id,
        "botDifficulty": DIFFICULTIES[difficulty],
        "teamId": TEAM_IDS[side],
        "position": POSITIONS[role],
        "botUuid": "",
    }


def close_existing_lobby(client: LcuClient, timeout: float = 5.0) -> bool:
    """Close the open lobby if there is one. Returns True if one was closed.

    Creating on top of an existing lobby is not enough: the POST does apply the
    configuration, but keeps the members already present, and a bot whose
    position is already taken is refused without an error. Without closing first,
    the run would report success while leaving the old bots in place.
    """
    if client.request("GET", LOBBY_PATH).status_code != 200:
        return False

    client.request_checked("DELETE", LOBBY_PATH)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if client.request("GET", LOBBY_PATH).status_code == 404:
            return True
        time.sleep(0.2)

    raise LobbyError(t("lobby.still_open", timeout=timeout))


def run_lobby(
    client: LcuClient,
    preset_name: str,
    difficulty: str | None = None,
    *,
    report: Report = print,
) -> int:
    """Create the preset's lobby and add every one of its bots.

    `report` receives each progress message, one line at a time.
    """
    preset = load_preset(preset_name)
    if difficulty is not None:
        preset["difficulty"] = difficulty
    chosen = preset["difficulty"]

    if close_existing_lobby(client):
        report(t("lobby.closed_existing"))

    payload = build_lobby_payload(preset)
    configuration = payload["customGameLobby"]["configuration"]
    report(
        t(
            "lobby.creating",
            name=payload["customGameLobby"]["lobbyName"],
            map_id=configuration["mapId"],
            mode=configuration["gameMode"],
            queue_id=payload["queueId"],
        )
    )
    client.post_json(LOBBY_PATH, payload)

    # The champions can only be resolved from here: the client leaves
    # `available-bots` empty as long as no custom lobby exists. A name it does
    # not know therefore fails with the lobby already created, so that lobby is
    # closed again rather than left behind empty.
    try:
        champions = load_bot_champions(client)
        planned = [
            (side, bot["champion"], resolve(champions, bot["champion"]), bot["role"])
            for side, team in preset.get("teams", {}).items()
            for bot in team.get("bots", [])
        ]
    except ChampionError:
        close_existing_lobby(client)
        report(t("lobby.closed_after_failure"))
        raise

    for side, champion, champion_id, role in planned:
        client.post_json(BOTS_PATH, build_bot_payload(champion_id, chosen, side, role))
        report(
            t(
                "lobby.bot_added",
                champion=champion,
                champion_id=champion_id,
                position=POSITIONS[role],
                difficulty=DIFFICULTIES[chosen],
                team=TEAM_IDS[side],
            )
        )

    report("")
    report(t("lobby.ready", count=len(planned)))
    return 0
