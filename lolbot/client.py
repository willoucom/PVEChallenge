"""Client HTTP minimal pour l'API locale du client League of Legends (LCU).

Le client expose son API sur https://127.0.0.1:<port> avec un certificat
auto-signe : la verification TLS est desactivee volontairement.
"""

import json
from typing import Any

import requests
import urllib3

from .lockfile import Credentials

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class LcuError(RuntimeError):
    """Erreur HTTP renvoyee par la LCU. Porte la reponse complete."""

    def __init__(self, message: str, response: requests.Response) -> None:
        super().__init__(message)
        self.response = response


def format_response(response: requests.Response) -> str:
    """Rend une reponse HTTP en entier : statut, en-tetes, corps.

    Le corps n'est jamais tronque ni avale : c'est le seul moyen d'ajuster les
    payloads envoyes a des endpoints non verifies.
    """
    lines = [
        f"--- Reponse LCU ---",
        f"{response.request.method} {response.request.url}",
        f"HTTP {response.status_code} {response.reason}",
    ]

    request_body = response.request.body
    if request_body:
        if isinstance(request_body, bytes):
            request_body = request_body.decode("utf-8", errors="replace")
        lines.append("Corps envoye :")
        lines.append(request_body)

    lines.append("En-tetes de reponse :")
    for name, value in response.headers.items():
        lines.append(f"  {name}: {value}")

    lines.append("Corps de reponse :")
    text = response.text
    if not text:
        lines.append("  <vide>")
    else:
        try:
            lines.append(json.dumps(response.json(), indent=2, ensure_ascii=False))
        except ValueError:
            lines.append(text)

    lines.append("--- fin reponse ---")
    return "\n".join(lines)


class LcuClient:
    """Session HTTP authentifiee vers la LCU."""

    def __init__(self, credentials: Credentials, timeout: float = 10.0) -> None:
        self.credentials = credentials
        self.timeout = timeout
        self.session = requests.Session()
        self.session.auth = credentials.auth
        self.session.verify = False
        self.session.headers.update({"Accept": "application/json"})

    @property
    def base_url(self) -> str:
        return self.credentials.base_url

    def request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        """Envoie une requete. Ne leve pas sur un statut d'erreur HTTP."""
        url = f"{self.base_url}{path}"
        kwargs.setdefault("timeout", self.timeout)
        return self.session.request(method, url, **kwargs)

    def request_checked(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        """Comme `request`, mais leve `LcuError` (avec la reponse complete) sur 4xx/5xx."""
        response = self.request(method, path, **kwargs)
        if response.status_code >= 400:
            raise LcuError(
                f"{method} {path} a echoue (HTTP {response.status_code}).\n"
                f"{format_response(response)}",
                response,
            )
        return response

    def get_json(self, path: str, **kwargs: Any) -> Any:
        return self.request_checked("GET", path, **kwargs).json()

    def post_json(self, path: str, payload: Any, **kwargs: Any) -> requests.Response:
        return self.request_checked("POST", path, json=payload, **kwargs)

    def close(self) -> None:
        self.session.close()

    def __enter__(self) -> "LcuClient":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


def check_connection(client: LcuClient) -> dict[str, Any]:
    """Verifie que la LCU repond. Retourne le resultat de GET /lol-summoner/v1/current-summoner."""
    return client.get_json("/lol-summoner/v1/current-summoner")
