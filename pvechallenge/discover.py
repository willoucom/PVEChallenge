"""Watching the lobby while it is being manipulated by hand in the client.

Purpose: find out which field of the lobby JSON carries a bot's position and
role, and which difficulty values the client actually sends. Nothing here changes
any state: only GET requests are issued.

This is a development tool, not part of the product. Its own output is written in
English and deliberately does not go through the message catalogue: it is read by
whoever maintains the project, never by a user.
"""

import json
import sys
import time
from datetime import datetime
from typing import Any

from .client import LcuClient, check_connection, format_response
from .config import ConfigError
from .diff import format_change, json_diff
from .lockfile import LockfileError, read_credentials

LOBBY_PATH = "/lol-lobby/v2/lobby"

#: Default polling interval, in seconds.
DEFAULT_INTERVAL = 0.5


def _timestamp() -> str:
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


def _print(message: str = "") -> None:
    print(message, flush=True)


def run_discover(client: LcuClient, interval: float = DEFAULT_INTERVAL) -> int:
    """Poll the lobby and print every change to its JSON."""
    _print(f"LCU: {client.base_url}")
    _print(f"Polling GET {LOBBY_PATH} every {interval} s. Ctrl+C to stop.")
    _print()
    _print("Now drive the client by hand:")
    _print("  1. create a custom game;")
    _print("  2. add a bot to the enemy team, with a champion, a difficulty")
    _print("     and a role or position if the interface offers one;")
    _print("  3. change its role, then its difficulty, one change at a time.")
    _print()

    previous: Any = None
    had_lobby = False
    last_error_signature: tuple[int, str] | None = None

    while True:
        response = client.request("GET", LOBBY_PATH)

        if response.status_code == 404:
            if had_lobby:
                _print(f"[{_timestamp()}] lobby closed (HTTP 404).")
                had_lobby = False
                previous = None
            elif last_error_signature != (404, ""):
                _print(f"[{_timestamp()}] no lobby yet (HTTP 404), waiting...")
                last_error_signature = (404, "")
            time.sleep(interval)
            continue

        if response.status_code >= 400:
            signature = (response.status_code, response.text)
            if signature != last_error_signature:
                _print(f"[{_timestamp()}] unexpected response:")
                _print(format_response(response))
                last_error_signature = signature
            time.sleep(interval)
            continue

        last_error_signature = None

        try:
            current = response.json()
        except ValueError:
            _print(f"[{_timestamp()}] non-JSON body:")
            _print(format_response(response))
            time.sleep(interval)
            continue

        if not had_lobby:
            had_lobby = True
            previous = current
            _print(f"[{_timestamp()}] lobby detected. Full initial state:")
            _print(json.dumps(current, indent=2, ensure_ascii=False))
            _print()
            _print("Waiting for changes...")
            time.sleep(interval)
            continue

        changes = list(json_diff(previous, current))
        if changes:
            _print(f"[{_timestamp()}] {len(changes)} change(s):")
            for change in changes:
                _print(format_change(change))
            _print()
            previous = current

        time.sleep(interval)


def discover(client: LcuClient, interval: float = DEFAULT_INTERVAL) -> int:
    try:
        return run_discover(client, interval)
    except KeyboardInterrupt:
        _print()
        _print("Stopped. Paste the output above to work out what changed.")
        return 0


def main() -> int:
    """Development entry point, with no equivalent in the interface.

    Deliberately absent from the package entry points: this tool exists to record
    the shape of the client's JSON when a patch changes it, not to be shipped. It
    therefore runs from the sources only, through
    `uv run python -m pvechallenge.discover [interval]`.
    """
    interval = DEFAULT_INTERVAL
    if len(sys.argv) > 1:
        try:
            interval = float(sys.argv[1])
        except ValueError:
            print(
                f"Invalid interval: {sys.argv[1]!r}. A number of seconds was expected.",
                file=sys.stderr,
            )
            return 1

    try:
        credentials = read_credentials()
    except (ConfigError, LockfileError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    _print(f"Lockfile: {credentials.source}")
    with LcuClient(credentials) as client:
        try:
            summoner = check_connection(client)
        except Exception as exc:  # connection refused, TLS, timeout...
            print(f"Cannot reach the LCU ({client.base_url}): {exc!r}", file=sys.stderr)
            return 1
        name = summoner.get("gameName") or summoner.get("displayName") or "<unknown>"
        _print(f"Connected as: {name}")
        _print()
        return discover(client, interval)


if __name__ == "__main__":
    sys.exit(main())
