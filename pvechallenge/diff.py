"""Recursive diff between two JSON documents, rendered as dotted paths."""

from typing import Any, Iterator, Literal

from .i18n import t

Kind = Literal["added", "removed", "changed"]
Change = tuple[Kind, str, Any, Any]

_MISSING = object()


def json_diff(old: Any, new: Any, path: str = "$") -> Iterator[Change]:
    """Yield the differences between `old` and `new`.

    Each difference is a `(kind, path, old_value, new_value)` tuple. Lists are
    compared by index: a bot inserted in the middle shifts every following index
    and therefore produces several lines. That is deliberate -- the point is to
    see the document's raw shape, not to tidy it up.
    """
    if isinstance(old, dict) and isinstance(new, dict):
        for key in old.keys() | new.keys():
            child = f"{path}.{key}"
            old_value = old.get(key, _MISSING)
            new_value = new.get(key, _MISSING)
            if old_value is _MISSING:
                yield ("added", child, None, new_value)
            elif new_value is _MISSING:
                yield ("removed", child, old_value, None)
            else:
                yield from json_diff(old_value, new_value, child)
        return

    if isinstance(old, list) and isinstance(new, list):
        for index in range(max(len(old), len(new))):
            child = f"{path}[{index}]"
            if index >= len(old):
                yield ("added", child, None, new[index])
            elif index >= len(new):
                yield ("removed", child, old[index], None)
            else:
                yield from json_diff(old[index], new[index], child)
        return

    if old != new:
        yield ("changed", path, old, new)


def format_change(change: Change, max_len: int = 2000) -> str:
    """Render one difference on a line, or several if the value is long."""
    import json

    kind, path, old_value, new_value = change

    def render(value: Any) -> str:
        text = json.dumps(value, ensure_ascii=False, indent=2)
        if len(text) > max_len:
            text = text[:max_len] + t("diff.truncated", length=len(text))
        return text

    if kind == "added":
        return f"  + {path} = {render(new_value)}"
    if kind == "removed":
        return f"  - {path} " + t("diff.was", value=render(old_value))
    return f"  ~ {path} : {render(old_value)} -> {render(new_value)}"
