# PVE Challenge

Windows application that prepares a League of Legends custom game lobby through
the client's local API (LCU). It never starts the game: it creates the lobby and
adds the bots, launching stays manual.

> PVE Challenge was created under Riot Games' "Legal Jibber Jabber" policy using
> assets owned by Riot Games. Riot Games does not endorse or sponsor this project.

## Requirements

- Windows, League of Legends client installed and **running**.

The release carries an installer: download `pvechallenge-<tag>-setup.exe` and run
it. The application installs for the current user alone, under
`%LOCALAPPDATA%\Programs\PVE Challenge`, so Windows asks for no administrator
approval, and it is removed from the usual list of installed applications.

Updating means running the new installer over the installed version: it empties
the application folder before copying, so nothing of the version it replaces
survives. Presets and settings live elsewhere and are untouched.

A zip of the application folder is published beside it, for whoever prefers to
run it without installing anything. Extract it anywhere and run
`pvechallenge.exe` from inside it, and keep the folder together: the executable
needs what sits next to it.

Neither file is code-signed, so Windows SmartScreen warns the first time one runs.
With the installer it warns once and never again. Windows marks a downloaded file
as coming from the Internet; Explorer carries that mark over to the files it
extracts from a zip, while a file written by a running program carries no mark at
all. The zip therefore hands SmartScreen a marked executable on every extraction,
where the installer takes the warning once, for itself, and the application it
writes starts unremarked.

To run from source you also need Python 3.14+ and
[uv](https://docs.astral.sh/uv/) (a single dependency, `requests`):

```bash
uv sync
uv run pvechallenge
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

If the client is installed elsewhere, set the path in the window's **Options**
panel: pick the file with *Parcourir...*, then *Enregistrer*. The setting is kept
in `%APPDATA%\pvechallenge\config.json` and reused on every run:

```json
{
  "lockfile": "D:\\Games\\League of Legends\\lockfile"
}
```

Leaving the field empty clears the setting and restores the default path above.

For a one-off override, two environment variables are read as well. The lockfile
path is resolved in this order, first match wins:

1. `PVECHALLENGE_LOCKFILE`
2. `PVECHALLENGE_INSTALL_DIR`
3. `lockfile` in `%APPDATA%\pvechallenge\config.json`
4. the default path above

An environment variable is a deliberate, one-off override, so it comes before the
saved setting, which in turn comes before the hardcoded default. The path
actually used is written to the log on every run. A config file that exists but
cannot be read is an error, never silently ignored.

## Usage

Start the application, pick a preset in the list, and click **Creer le lobby**. The log
pane shows every step: which lockfile was read, which account is connected, the
lobby being created, and each bot as it is added. The status line at the bottom
carries the outcome, and its colour carries the state: amber while working, green
on success, red on failure with the reason.

If a lobby is already open in the client, it is closed and recreated. Champion
names are only resolved once the new lobby exists, because that is when the
client lists the champions playable as bots; a typo in a preset therefore closes
that lobby again and says so in the log.

The **Options** panel holds the lockfile path and a button that opens your own
presets folder in Explorer.

The version sits at the bottom right. It reads `dev` when running from the
sources: a source tree has no version. A released build stamps the tag it was
published under into the package, so the window and the file properties can never
disagree.

Bot difficulty is not settable from the window: it is the `difficulty` field of
the preset.

## Language

The interface follows the system locale. English and French are shipped; any
other locale falls back to English. There is no setting and no selector: the
language is decided once, at start-up.

Messages live in `pvechallenge/messages.py`, one catalogue per language, keyed by
symbolic names rather than by English sentences, so rewording a message touches
the catalogue only. Adding a language means adding a catalogue: a test checks
that every catalogue holds the same keys and expects the same placeholders, so a
forgotten message fails the build instead of reaching a user.

The Riot notice is not translated. Its wording is imposed by their policy.

## Presets

A preset is a JSON file, and presets come from two sources:

- **Shipped presets**, inside the package under `pvechallenge/presets/`. They are
  read-only and travel with the wheel and with the executable.
- **Your own presets**, in `%APPDATA%\pvechallenge\presets\`. Drop a JSON file there and
  it appears in the list. That folder is yours: updates, reinstalls and
  uninstalls never touch it.

A file name carried by both sources is usable by neither. The tool refuses it and
names the file to rename, so that a shipped preset can never be silently replaced
by another one of the same name.

In the list, a preset is shown under its `name` field, and identified by its file
name, which has its own column: the file name is what resolves the preset, and it
is what tells two presets apart when they carry the same `name`. A preset whose
JSON is unreadable, or whose `name` is absent or is not usable text, is shown
under its file name; the error itself is reported when the preset is applied.

The list is grouped by source, the shipped presets first, then your own, and each
group is ordered by file name.

`pvechallenge/presets/ireaz.json` is the shipped example: it describes my team (me alone,
no bots) and the enemy team: Warwick top, Amumu jungle, Malphite mid, Kai'Sa bot,
Lulu support.

The `lobby` block carries the lobby name and the spectator policy. Map and game
mode are not part of it: this tool only creates custom games on Summoner's Rift in
blind pick.

Presets use their own vocabulary, translated to the client's in `pvechallenge/lobby.py`:

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
| `GET /lol-lobby/v2/lobby/custom/available-bots` | `200` | champions playable as bots and their difficulties; empty list when no custom lobby is open |
| `GET /lol-game-data/assets/v1/champion-summary.json` | `200` | champion catalog |

`configuration.mapId` and `configuration.gameMode` do not select the map or the
mode: the client derives them from `queueId` and ignores what the body claims.
They are therefore hardcoded in `pvechallenge/lobby.py` to the values of queue 3100, so
that the body sent describes the lobby actually created.

Recreating a lobby goes through the `DELETE`, never a bare POST: posted on top of
an existing lobby, `POST /lol-lobby/v2/lobby` does apply the configuration but
keeps the members already present, and a bot whose position is already taken is
then rejected with a `204` that adds nothing.

The role field is named `position` in the POST body, and comes back as
`botPosition` in the state that is read. `teamId` is sent as a string (`"100"` /
`"200"`) but comes back as `0`: membership in `customTeam100` / `customTeam200` is
what counts.

Any HTTP error is reported whole: the request sent, the status, the headers and
the full response body. Nothing is swallowed, and nothing is truncated.

## Development

### Watching the lobby

`discover` watches the lobby and reports what changes in its JSON. It only issues
`GET` requests and never modifies the client's state: it polls
`GET /lol-lobby/v2/lobby`, prints the full initial lobby state, then prints the
diff as dotted paths on every change.

```bash
uv run python -m pvechallenge.discover
uv run python -m pvechallenge.discover 0.25   # polling interval, in seconds
```

It exists to record the exact shape of the JSON when a client patch changes it.
It is deliberately absent from the packaged application, and runs from the
sources only.

### Running the tests

```bash
uv run python -m pytest
```

The suite exercises the real code with no network and no game client: the LCU is
replaced by a double, and `%APPDATA%` is redirected to a throwaway folder, so no
test can write to the configuration of the machine running it. The interface
tests open real Tk windows, kept off-screen.

Nothing is hardcoded about the contents of `pvechallenge/presets/`: adding or
removing a shipped preset breaks no test.

### Regenerating the icon

`pvechallenge/icon.ico` is versioned, and derived from `assets/logo.png`. Run this
after changing the logo, never otherwise:

```bash
uv run python make_icon.py
```

It writes six sizes, from 16 to 128. There is no 256: the source is 128 wide, and
enlarging it would invent detail. The two smallest get a one-pixel steel rim and
livelier colours, because below 32 pixels the dark shield otherwise dissolves into
a dark taskbar.

### Building the executable

```bash
uv sync
uv run python build.py
```

`build.py` is the only place the Nuitka invocation exists, so a local build and a
CI build cannot drift apart. It compiles `main.py`, not `pvechallenge/gui.py`: a package
module compiled as a script loses its relative imports.

The result is `dist/pvechallenge/`, a folder holding the executable, Python, the
package, its presets and its icon.

It is deliberately not a single file. Nuitka can produce one, but such a binary
unpacks itself into a temporary directory and runs from there, and Windows
Defender's machine learning model scores that behaviour as a trojan -- browsers
then refuse the download outright. The same sources built as a folder pass
cleanly. A test asserts the mode, so an accidental return to a single file would
not go unnoticed until a release stopped reaching anyone.

Building needs a C compiler: GitHub's Windows runners carry MSVC, and Nuitka
picks up a local Visual Studio installation on its own. Without one, it downloads
MinGW-w64 on first use.

### Building the installer

```bash
uv run python make_installer.py
```

It compiles `installer.iss` with Inno Setup, from the folder `build.py` produced,
and writes `dist/pvechallenge-<version>-setup.exe`. It packages, it does not
build: run before `build.py`, it reports the missing executable rather than
producing an empty installer. `make_installer.py` is the only place the Inno
Setup invocation exists, for the same reason `build.py` holds the Nuitka call
alone.

The wizard asks nothing whose answer is always the same -- no directory, no
program group, no confirmation page -- and picks English or French from the
system locale without a selector, as the application does. The one thing it asks
is whether to add a desktop shortcut, unchecked by default.

Inno Setup is looked up as `ISCC` on `PATH`, then in the per-machine installation
directories. Not finding it fails the build: a release that silently shipped
without its installer would point people at a file that is not there.

The installer empties its destination before copying anything. Inno Setup removes
only what it is told to, and the names a Nuitka distribution carries are not
stable from one version to the next, so an update would otherwise keep whatever
the new version no longer ships. Presets make that more than untidiness: the
package enumerates them at run time, so one left behind would go on being listed,
and collide with a preset of the same name the user later writes.

The sweep is guarded. Its `Check` function requires the destination to already
hold `pvechallenge.exe`, so a directory that is not an installation of this
application -- `/DIR=` accepts any path -- is never emptied, and a first
installation deletes nothing.

### Releasing

Pushing a `v*` tag runs `.github/workflows/release.yml`, which runs the tests,
builds on `windows-2025`, then attaches the executable to the matching GitHub
Release. A failing test stops the run before anything is built.

The tag decides the version: it is what people download, so it is what the file
announces and what the window shows. Windows version resources hold numbers only,
so `v1.2.0-rc1` is stamped as `1.2.0`; a tag holding no number at all fails the
build rather than producing a binary labelled with nothing. Publishing is
repeatable: a Release that already exists is updated instead of refused.

A Release carries two files, both named after the tag: the installer, which is
what the top of this README sends people to, and a zip of the application folder
for the portable case -- a Release cannot carry a folder as such. Neither is
signed, so SmartScreen still has its say, as described under *Requirements*.

The same workflow can be started by hand, which tests and builds, then uploads
the binary as a workflow artifact without publishing anything. Artifacts need no
zipping of their own: GitHub already serves them that way.

## Still to verify

- `queueId` 3100 maps to this client's "Summoner's Rift — custom blind pick"
  queue. Nothing guarantees that this identifier is stable across patches.
