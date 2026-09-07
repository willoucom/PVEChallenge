"""Doubles of external objects, to exercise the code with no network and no game client."""

from typing import Any

from pvechallenge.lobby import BOTS_PATH, LOBBY_PATH


class ReponseFactice:
    """The bare minimum of the HTTP response interface the code actually uses."""

    def __init__(self, status_code: int) -> None:
        self.status_code = status_code


class ClientFactice:
    """Double of the LCU client: answers with no network, and keeps what is posted.

    It mimics only the methods actually called. A missing method fails the test
    with an explicit `AttributeError`, which beats an accommodating double that
    would let an unexpected call through.
    """

    def __init__(self, champions: dict[str, int], lobby_ouvert: bool = False) -> None:
        self.champions = champions
        self.lobby_ouvert = lobby_ouvert
        self.posts: list[tuple[str, Any]] = []
        self.supprime = 0

    def request(self, method: str, path: str, **kwargs: Any) -> ReponseFactice:
        if path == LOBBY_PATH:
            if method == "DELETE":
                self.lobby_ouvert = False
                self.supprime += 1
                return ReponseFactice(204)
            return ReponseFactice(200 if self.lobby_ouvert else 404)
        return ReponseFactice(204)

    def request_checked(self, method: str, path: str, **kwargs: Any) -> ReponseFactice:
        return self.request(method, path, **kwargs)

    def get_json(self, path: str, **kwargs: Any) -> Any:
        if path.endswith("available-bots"):
            return [{"id": identifiant} for identifiant in self.champions.values()]
        return [{"id": identifiant, "name": nom} for nom, identifiant in self.champions.items()]

    def post_json(self, path: str, payload: Any, **kwargs: Any) -> ReponseFactice:
        self.posts.append((path, payload))
        return ReponseFactice(200)

    @property
    def bots_postes(self) -> list[Any]:
        return [corps for chemin, corps in self.posts if chemin == BOTS_PATH]


def champions_du_preset(preset: Any) -> dict[str, int]:
    """`name -> championId` table covering exactly the champions of a preset.

    The identifiers are arbitrary: the code does not interpret them, it copies
    them into the body sent to the client.
    """
    noms = [
        bot["champion"]
        for equipe in preset.get("teams", {}).values()
        for bot in equipe.get("bots", [])
    ]
    return {nom: 1000 + index for index, nom in enumerate(sorted(set(noms)))}
