# LolBotChallenge

Command-line tool that prepares a League of Legends custom game lobby through the
client's local API (LCU). It never starts the game: it creates the lobby and adds
the bots, launching stays manual.

## Requirements

- Windows, League of Legends client installed and **running**.
- Python 3.14+.
- [uv](https://docs.astral.sh/uv/) for dependency management (a single dependency:
  `requests`).

```bash
uv sync
```

## The lockfile

The client writes its API credentials to a file named `lockfile`, at the root of
its installation directory. This tool's default path:

```
C:\Riot Games\League of Legends\lockfile
```

It is created when the client starts and removed when it closes. Its content is a
single line:

```
LeagueClient:<pid>:<port>:<password>:https
```

The tool uses it to build `https://127.0.0.1:<port>` and authenticate with HTTP
basic auth as `riot:<password>`. The client's certificate is self-signed, so TLS
verification is disabled.

If the client is installed elsewhere:

```bash
uv run lolbot --install-dir "D:\Games\League of Legends" lobby ireaz
```

```bash
uv run lolbot --lockfile "D:\Games\League of Legends\lockfile" lobby ireaz
```

Environment variable equivalents: `LOLBOT_LOCKFILE`, `LOLBOT_INSTALL_DIR`.

## Usage

### `lobby` — create the lobby from a preset

```bash
uv run lolbot lobby ireaz
```

```bash
uv run lolbot lobby ireaz --difficulty intro
```

The argument is the name of a preset from `presets/`, or the path to a JSON file.
`--difficulty` (`intro`, `debutant`, `intermediaire`) overrides the preset's
difficulty and applies to all of its bots.

If a lobby is already open in the client, it is closed and recreated. Champion
names are resolved before any action is taken, so a typo in a preset leaves the
current lobby untouched.

### `discover` — watch the lobby

Only issues `GET` requests, never modifies the client's state. Polls
`GET /lol-lobby/v2/lobby` every 500 ms, prints the full initial lobby state, then
prints the JSON diff as dotted paths on every change.

```bash
uv run lolbot discover
```

Used to record the exact shape of the JSON as the client evolves. Configurable
interval: `--interval 0.25`.

## Presets

A preset is a JSON file in `presets/`. `presets/ireaz.json` describes my team (me
alone, no bots) and the enemy team: Warwick top, Amumu jungle, Malphite mid,
Kai'Sa bot, Lulu support.

The `lobby` block carries the lobby name and the spectator policy. Map and game
mode are not part of it: this tool only creates custom games on Summoner's Rift in
blind pick.

Presets use their own vocabulary, translated to the client's in `lolbot/lobby.py`:

| Preset | Client |
|---|---|
| `top` / `jungle` / `mid` / `bot` / `support` | `TOP` / `JUNGLE` / `MIDDLE` / `BOTTOM` / `UTILITY` |
| `intro` / `debutant` / `intermediaire` | `RSINTRO` / `RSBEGINNER` / `RSINTERMEDIATE` |
| `teams.mine` / `teams.enemy` | `teamId` `"100"` / `"200"` |

Champions are named, not identified by `championId`: the mapping is read from the
client on every run, by intersecting
`/lol-game-data/assets/v1/champion-summary.json` with
`/lol-lobby/v2/lobby/custom/available-bots`. The champion catalog holds several
entries sharing the same name under different identifiers; the intersection is
what designates the one that is playable as a bot.

## Endpoints used

All verified against a running League of Legends client.

| Call | Response | Body |
|---|---|---|
| `POST /lol-lobby/v2/lobby` | `200` | `queueId` **3100**, `customGameLobby.configuration.mutators.id` **19**; `mapId`, `gameMode` and `spectatorPolicy` live in `configuration` |
| `POST /lol-lobby/v1/lobby/custom/bots` | `204` | `championId`, `botDifficulty`, `teamId` (string), `position`, `botUuid` (empty string accepted, the client generates the identifier) |
| `GET /lol-lobby/v2/lobby` | `200` / `404` | 404 when no lobby is open |
| `DELETE /lol-lobby/v2/lobby` | `204` | closes the open lobby |
| `GET /lol-lobby/v2/lobby/custom/available-bots` | `200` | champions playable as bots and their difficulties |
| `GET /lol-game-data/assets/v1/champion-summary.json` | `200` | champion catalog |

`configuration.mapId` and `configuration.gameMode` do not select the map or the
mode: the client derives them from `queueId` and ignores what the body claims.
They are therefore hardcoded in `lolbot/lobby.py` to the values of queue 3100, so
that the body sent describes the lobby actually created.

Recreating a lobby goes through the `DELETE`, never a bare POST: posted on top of
an existing lobby, `POST /lol-lobby/v2/lobby` does apply the configuration but
keeps the members already present, and a bot whose position is already taken is
then rejected with a `204` that adds nothing.

The role field is named `position` in the POST body, and comes back as
`botPosition` in the state that is read. `teamId` is sent as a string (`"100"` /
`"200"`) but comes back as `0`: membership in `customTeam100` / `customTeam200` is
what counts.

Any HTTP error prints the request sent, the status, the headers and the full
response body: nothing is swallowed.

## Still to verify

- `queueId` 3100 maps to this client's "Summoner's Rift — custom blind pick"
  queue. Nothing guarantees that this identifier is stable across patches.
