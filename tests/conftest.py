"""Fixtures shared by the whole suite.

Three rules hold this directory together:

- no test touches the profile of the machine running it, nor its League of
  Legends client. The profile is redirected to a throwaway directory, and the
  network is replaced by a double;
- nothing is hardcoded about the contents of `pvechallenge/presets/`. Adding or
  removing a shipped preset must break no test;
- the language is pinned to English. Messages are localised and the language
  follows the system locale, so without pinning, a suite written against one
  language would pass on a French machine and fail on an English runner.
"""

import pytest

from pvechallenge.i18n import set_language

#: Language the assertions are written against.
TEST_LANGUAGE = "en"


@pytest.fixture(autouse=True)
def langue_fixee():
    """Pin the message language, then restore what the system had chosen."""
    from pvechallenge.i18n import current_language

    precedente = current_language()
    set_language(TEST_LANGUAGE)
    yield
    set_language(precedente)


@pytest.fixture(autouse=True)
def profil_isole(tmp_path, monkeypatch):
    """Redirect `%APPDATA%` to a throwaway directory and clear the overrides.

    `autouse` is deliberate: a test that forgot to request this fixture would
    write to the real configuration of the machine running it.
    """
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    monkeypatch.delenv("PVECHALLENGE_LOCKFILE", raising=False)
    monkeypatch.delenv("PVECHALLENGE_INSTALL_DIR", raising=False)
