"""How the version stamped into the executable is decided.

The build itself is not exercised here: it needs a C compiler and takes minutes.
What is exercised is the part that can quietly go wrong -- a binary announcing a
version that has nothing to do with the tag it was published under.
"""

import pytest

import build


@pytest.mark.parametrize(
    "brut, attendu",
    [
        ("1.2.3", "1.2.3"),
        ("v1.2.3", "1.2.3"),
        ("V1.2.3", "1.2.3"),
        ("v0.0.1-test", "0.0.1"),
        ("v1.0.0-rc1", "1.0.0"),
        ("2", "2"),
        ("1.2.3.4", "1.2.3.4"),
    ],
)
def test_the_leading_number_is_kept(brut, attendu):
    """Windows version resources carry numbers: a qualifier cannot be stamped."""
    assert build.numeric_version(brut) == attendu


@pytest.mark.parametrize("brut", ["nightly", "v", "", "release-candidate"])
def test_a_version_without_a_number_is_refused(brut):
    """Stamping something meaningless is worse than failing the build."""
    with pytest.raises(ValueError, match="no version number"):
        build.numeric_version(brut)


def test_without_the_variable_the_project_version_applies(monkeypatch):
    monkeypatch.delenv(build.ENV_VERSION, raising=False)

    assert build.project_version() == build.numeric_version(build.project_version())


def test_the_tag_overrides_the_project_version(monkeypatch):
    monkeypatch.setenv(build.ENV_VERSION, "v9.8.7-rc2")

    assert build.project_version() == "9.8.7"


def test_an_empty_variable_is_ignored(monkeypatch):
    """The workflow leaves it empty on a manual run, which must not break it."""
    monkeypatch.setenv(build.ENV_VERSION, "")

    assert build.project_version() == "0.1.0"


def test_the_version_reaches_the_nuitka_call(monkeypatch):
    monkeypatch.setenv(build.ENV_VERSION, "v3.4.5")
    commande = build.build_command()

    assert "--file-version=3.4.5" in commande
    assert "--product-version=3.4.5" in commande

# ------------------------------------------------------------ packaging mode


def test_the_build_is_standalone_not_onefile():
    """A single-file build unpacks itself at run time, and Defender's machine
    learning model scores that as a trojan. The same sources built standalone
    pass, so the mode is not an implementation detail: it decides whether the
    download reaches anyone at all.
    """
    commande = build.build_command()

    assert "--standalone" in commande
    assert "--onefile" not in commande


def test_the_distribution_folder_is_named_after_the_product():
    """Nuitka names it after the entry script, which would extract as `main.dist`."""
    assert build.APP_DIR.name == "pvechallenge"
    assert build.EXE.parent == build.APP_DIR
    assert build.EXE.name == "pvechallenge.exe"
