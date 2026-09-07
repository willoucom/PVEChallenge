"""Message translation, driven by the system locale.

The language is decided once, at import, and never changes while the application
runs: there is no selector and no saved setting. A machine that is neither French
nor English falls back to English, which is also the language of the repository
and its documentation.

Message keys are symbolic rather than English sentences. Rewording a message then
touches the catalogue only, never a call site.
"""

import locale

from .messages import CATALOGUES, DEFAULT_LANGUAGE


def detect_language() -> str:
    """Language code taken from the system locale, restricted to what we ship.

    `locale.getlocale()` is used rather than `getdefaultlocale()`, which is
    deprecated and slated for removal in Python 3.15. On Windows it returns a
    value such as `fr_FR`; only the language part matters here.
    """
    try:
        code, _encoding = locale.getlocale()
    except (TypeError, ValueError):
        return DEFAULT_LANGUAGE
    if not code:
        return DEFAULT_LANGUAGE
    language = code.replace("-", "_").split("_")[0].lower()
    return language if language in CATALOGUES else DEFAULT_LANGUAGE


#: Language in use. Module-level, resolved once at import.
_language = detect_language()


def current_language() -> str:
    """Language currently used to render messages."""
    return _language


def set_language(language: str) -> None:
    """Force the language. Exists for the tests, which need determinism.

    The application never calls it: its language follows the system, and nothing
    in the interface offers to change it.
    """
    global _language
    if language not in CATALOGUES:
        raise ValueError(f"unknown language {language!r}, expected one of {sorted(CATALOGUES)}")
    _language = language


def t(key: str, **params: object) -> str:
    """Render the message `key`, filling in `params`.

    A key missing from the active language falls back to English; a key missing
    everywhere returns the key itself. Neither case should ever happen -- a test
    asserts that every catalogue holds exactly the same keys -- but a missing
    translation must not take the window down in front of a user.
    """
    catalogue = CATALOGUES.get(_language, CATALOGUES[DEFAULT_LANGUAGE])
    template = catalogue.get(key)
    if template is None:
        template = CATALOGUES[DEFAULT_LANGUAGE].get(key)
    if template is None:
        return key
    return template.format(**params)
