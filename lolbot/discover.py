"""Commande `discover` : observe le lobby pendant que l'utilisateur le manipule a la main.

But : identifier quel champ du JSON de lobby porte la position/le role d'un bot,
et quelles valeurs de difficulte le client envoie reellement. Aucun appel qui
modifie l'etat n'est fait ici : uniquement des GET.
"""

import json
import sys
import time
from datetime import datetime
from typing import Any

from .client import LcuClient, format_response
from .diff import format_change, json_diff

LOBBY_PATH = "/lol-lobby/v2/lobby"


def _timestamp() -> str:
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


def _print(message: str = "") -> None:
    print(message, flush=True)


def run_discover(client: LcuClient, interval: float = 0.5) -> int:
    """Boucle de polling sur le lobby, affiche chaque changement du JSON."""
    _print(f"LCU : {client.base_url}")
    _print(f"Polling GET {LOBBY_PATH} toutes les {interval} s. Ctrl+C pour arreter.")
    _print()
    _print("Manipule maintenant le client :")
    _print("  1. cree une partie personnalisee ;")
    _print("  2. ajoute un bot dans l'equipe adverse, avec un champion, une difficulte")
    _print("     et un role/une position si l'interface le propose ;")
    _print("  3. change son role, puis sa difficulte, un changement a la fois.")
    _print()

    previous: Any = None
    had_lobby = False
    last_error_signature: tuple[int, str] | None = None

    while True:
        response = client.request("GET", LOBBY_PATH)

        if response.status_code == 404:
            if had_lobby:
                _print(f"[{_timestamp()}] lobby ferme (HTTP 404).")
                had_lobby = False
                previous = None
            elif last_error_signature != (404, ""):
                _print(f"[{_timestamp()}] aucun lobby pour l'instant (HTTP 404), en attente...")
                last_error_signature = (404, "")
            time.sleep(interval)
            continue

        if response.status_code >= 400:
            signature = (response.status_code, response.text)
            if signature != last_error_signature:
                _print(f"[{_timestamp()}] reponse inattendue :")
                _print(format_response(response))
                last_error_signature = signature
            time.sleep(interval)
            continue

        last_error_signature = None

        try:
            current = response.json()
        except ValueError:
            _print(f"[{_timestamp()}] corps non-JSON :")
            _print(format_response(response))
            time.sleep(interval)
            continue

        if not had_lobby:
            had_lobby = True
            previous = current
            _print(f"[{_timestamp()}] lobby detecte. Etat initial complet :")
            _print(json.dumps(current, indent=2, ensure_ascii=False))
            _print()
            _print("En attente de changements...")
            time.sleep(interval)
            continue

        changes = list(json_diff(previous, current))
        if changes:
            _print(f"[{_timestamp()}] {len(changes)} changement(s) :")
            for change in changes:
                _print(format_change(change))
            _print()
            previous = current

        time.sleep(interval)


def discover(client: LcuClient, interval: float = 0.5) -> int:
    try:
        return run_discover(client, interval)
    except KeyboardInterrupt:
        _print()
        _print("Arret demande. Colle la sortie ci-dessus pour qu'on identifie le champ de role.")
        return 0
