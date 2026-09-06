"""Resolution d'un nom de champion vers son `championId`, depuis le client.

Aucune table statique : le client fait foi.
"""

from .client import LcuClient

CHAMPION_SUMMARY = "/lol-game-data/assets/v1/champion-summary.json"
AVAILABLE_BOTS = "/lol-lobby/v2/lobby/custom/available-bots"


class ChampionError(RuntimeError):
    """Champion inconnu ou indisponible en bot."""


def load_bot_champions(client: LcuClient) -> dict[str, int]:
    """Retourne `nom du champion -> championId`, restreint aux bots disponibles.

    Le catalogue de champions du client contient plusieurs entrees portant le meme
    nom : le champion et ses variantes de mode de jeu, qui ont des identifiants
    differents. Filtrer sur les identifiants que `available-bots` declare est ce
    qui distingue le bon du reste ; resoudre sur le nom seul renvoie une variante
    que l'ajout de bot refusera.
    """
    available = {entry["id"] for entry in client.get_json(AVAILABLE_BOTS)}
    resolved: dict[str, int] = {}
    for champion in client.get_json(CHAMPION_SUMMARY):
        if champion["id"] in available:
            resolved.setdefault(champion["name"], champion["id"])
    return resolved


def resolve(table: dict[str, int], name: str) -> int:
    """Traduit un nom de champion en `championId`, ou leve `ChampionError`."""
    if name in table:
        return table[name]

    lowered = name.casefold()
    matches = [known for known in table if known.casefold() == lowered]
    if len(matches) == 1:
        return table[matches[0]]

    near = sorted(known for known in table if lowered in known.casefold())
    detail = f" Proches : {', '.join(near)}." if near else ""
    raise ChampionError(
        f"Champion inconnu ou indisponible en bot : {name!r}.{detail}"
    )
