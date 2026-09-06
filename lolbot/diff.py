"""Diff recursif entre deux documents JSON, rendu en chemins pointes."""

from typing import Any, Iterator, Literal

Kind = Literal["ajoute", "retire", "modifie"]
Change = tuple[Kind, str, Any, Any]

_MISSING = object()


def json_diff(old: Any, new: Any, path: str = "$") -> Iterator[Change]:
    """Produit les differences entre `old` et `new`.

    Chaque difference est un tuple `(kind, chemin, ancienne_valeur, nouvelle_valeur)`.
    Les listes sont comparees par index : un bot insere au milieu decale les
    index suivants et produit donc plusieurs lignes. C'est voulu, le but est de
    voir la forme brute du document, pas de la simplifier.
    """
    if isinstance(old, dict) and isinstance(new, dict):
        for key in old.keys() | new.keys():
            child = f"{path}.{key}"
            old_value = old.get(key, _MISSING)
            new_value = new.get(key, _MISSING)
            if old_value is _MISSING:
                yield ("ajoute", child, None, new_value)
            elif new_value is _MISSING:
                yield ("retire", child, old_value, None)
            else:
                yield from json_diff(old_value, new_value, child)
        return

    if isinstance(old, list) and isinstance(new, list):
        for index in range(max(len(old), len(new))):
            child = f"{path}[{index}]"
            if index >= len(old):
                yield ("ajoute", child, None, new[index])
            elif index >= len(new):
                yield ("retire", child, old[index], None)
            else:
                yield from json_diff(old[index], new[index], child)
        return

    if old != new:
        yield ("modifie", path, old, new)


def format_change(change: Change, max_len: int = 2000) -> str:
    """Rend une difference sur une ligne (ou plusieurs si la valeur est longue)."""
    import json

    kind, path, old_value, new_value = change

    def render(value: Any) -> str:
        text = json.dumps(value, ensure_ascii=False, indent=2)
        if len(text) > max_len:
            text = text[:max_len] + f"... (tronque, {len(text)} caracteres)"
        return text

    if kind == "ajoute":
        return f"  + {path} = {render(new_value)}"
    if kind == "retire":
        return f"  - {path} (etait {render(old_value)})"
    return f"  ~ {path} : {render(old_value)} -> {render(new_value)}"
