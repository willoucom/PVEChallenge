"""Resolving a champion name to its `championId`, read from the client.

No static table: the client is the authority.
"""

from .client import LcuClient
from .i18n import t

CHAMPION_SUMMARY = "/lol-game-data/assets/v1/champion-summary.json"
AVAILABLE_BOTS = "/lol-lobby/v2/lobby/custom/available-bots"


class ChampionError(RuntimeError):
    """Champion unknown, or unavailable as a bot."""


def load_bot_champions(client: LcuClient) -> dict[str, int]:
    """Return `champion name -> championId`, restricted to available bots.

    The client's champion catalog holds several entries sharing the same name:
    the champion and its game-mode variants, which carry different identifiers.
    Filtering on the identifiers `available-bots` declares is what singles out
    the right one; resolving on the name alone returns a variant that adding a
    bot will refuse.
    """
    available = {entry["id"] for entry in client.get_json(AVAILABLE_BOTS)}
    resolved: dict[str, int] = {}
    for champion in client.get_json(CHAMPION_SUMMARY):
        if champion["id"] in available:
            resolved.setdefault(champion["name"], champion["id"])
    return resolved


def resolve(table: dict[str, int], name: str) -> int:
    """Translate a champion name into a `championId`, or raise `ChampionError`."""
    if name in table:
        return table[name]

    lowered = name.casefold()
    matches = [known for known in table if known.casefold() == lowered]
    if len(matches) == 1:
        return table[matches[0]]

    near = sorted(known for known in table if lowered in known.casefold())
    detail = t("champion.near_matches", names=", ".join(near)) if near else ""
    raise ChampionError(t("champion.unknown", name=name, detail=detail))
