"""Catalogue integrity, and how the language is chosen.

These tests do not check wording. They check the two things that break silently:
a key that exists in one language and not the other, and a translation whose
placeholders no longer match the call site.
"""

from string import Formatter

import pytest

from pvechallenge import i18n
from pvechallenge.messages import CATALOGUES, DEFAULT_LANGUAGE


def placeholders(template: str) -> set[str]:
    """Named fields a template expects, ignoring literal text."""
    return {name for _text, name, _spec, _conv in Formatter().parse(template) if name}


def test_default_language_is_shipped():
    assert DEFAULT_LANGUAGE in CATALOGUES


def test_several_languages_are_shipped():
    """A single catalogue would make every other test here vacuous."""
    assert len(CATALOGUES) >= 2


@pytest.mark.parametrize("language", sorted(CATALOGUES))
def test_every_catalogue_holds_the_same_keys(language):
    """A key missing from one language is invisible until a user hits that path."""
    reference = set(CATALOGUES[DEFAULT_LANGUAGE])
    manquantes = reference - set(CATALOGUES[language])
    en_trop = set(CATALOGUES[language]) - reference

    assert not manquantes, f"{language}: missing keys {sorted(manquantes)}"
    assert not en_trop, f"{language}: unknown keys {sorted(en_trop)}"


@pytest.mark.parametrize("language", sorted(CATALOGUES))
def test_every_translation_expects_the_same_placeholders(language):
    """A translation naming a field the caller does not pass raises at runtime."""
    ecarts = {
        key: (placeholders(CATALOGUES[DEFAULT_LANGUAGE][key]), placeholders(template))
        for key, template in CATALOGUES[language].items()
        if key in CATALOGUES[DEFAULT_LANGUAGE]
        and placeholders(CATALOGUES[DEFAULT_LANGUAGE][key]) != placeholders(template)
    }

    assert not ecarts, f"{language}: placeholders differ for {sorted(ecarts)}"


def test_no_template_is_empty():
    for language, catalogue in CATALOGUES.items():
        vides = sorted(key for key, template in catalogue.items() if not template.strip())
        assert not vides, f"{language}: empty messages {vides}"


# ------------------------------------------------------------ language choice


def test_unknown_locale_falls_back_to_the_default(monkeypatch):
    monkeypatch.setattr(i18n.locale, "getlocale", lambda *_: ("xx_XX", "UTF-8"))
    assert i18n.detect_language() == DEFAULT_LANGUAGE


def test_absent_locale_falls_back_to_the_default(monkeypatch):
    monkeypatch.setattr(i18n.locale, "getlocale", lambda *_: (None, None))
    assert i18n.detect_language() == DEFAULT_LANGUAGE


@pytest.mark.parametrize("code", ["fr_FR", "fr-CA", "FR"])
def test_a_known_language_is_recognised_whatever_its_shape(code, monkeypatch):
    monkeypatch.setattr(i18n.locale, "getlocale", lambda *_: (code, "UTF-8"))
    assert i18n.detect_language() == "fr"


def test_unknown_language_is_refused():
    with pytest.raises(ValueError, match="unknown language"):
        i18n.set_language("xx")


# ----------------------------------------------------------------- rendering


def test_a_key_missing_everywhere_returns_itself():
    """Better a visible key than a window that dies on a forgotten message."""
    assert i18n.t("nothing.at.all") == "nothing.at.all"


def test_a_key_missing_in_the_active_language_falls_back(monkeypatch):
    monkeypatch.setitem(CATALOGUES, "zz", {})
    i18n.set_language("zz")

    assert i18n.t("gui.status.ready") == CATALOGUES[DEFAULT_LANGUAGE]["gui.status.ready"]


@pytest.mark.parametrize("language", sorted(CATALOGUES))
def test_parameters_are_filled_in_every_language(language):
    i18n.set_language(language)
    rendu = i18n.t("gui.status.available", count=3)

    assert "3" in rendu
    assert "{" not in rendu
