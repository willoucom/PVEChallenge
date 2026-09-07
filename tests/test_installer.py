"""How the installer is assembled.

Inno Setup itself is not run here: it is a Windows compiler the suite cannot
assume. What is exercised is what can quietly go wrong -- an installer named
after something other than the tag, or built from a folder the build never
produced.
"""

from pathlib import Path

import pytest

import build
import make_installer

#: Stands in for the compiler, which the suite never runs.
ISCC = Path("C:/Inno Setup/ISCC.exe")


def test_the_installer_is_named_after_the_tag(monkeypatch):
    """The Release carries the tag, so the file people download carries it too."""
    monkeypatch.setenv(build.ENV_VERSION, "v1.2.0-rc1")

    assert make_installer.installer_name("1.2.0") == "pvechallenge-v1.2.0-rc1-setup"


def test_without_a_tag_the_numeric_version_names_it(monkeypatch):
    """A local build has no tag, and must still produce a named file."""
    monkeypatch.delenv(build.ENV_VERSION, raising=False)

    assert make_installer.installer_name("1.2.0") == "pvechallenge-1.2.0-setup"


def test_an_empty_variable_is_ignored(monkeypatch):
    """The workflow leaves it empty on a manual run, which must not name a file
    `pvechallenge--setup`."""
    monkeypatch.setenv(build.ENV_VERSION, "")

    assert make_installer.installer_name("1.2.0") == "pvechallenge-1.2.0-setup"


def test_the_version_reaches_the_inno_setup_call(monkeypatch):
    monkeypatch.delenv(build.ENV_VERSION, raising=False)
    commande = make_installer.build_command("3.4.5", ISCC)

    assert "/DAppVersion=3.4.5" in commande
    assert "/DOutputBaseFilename=pvechallenge-3.4.5-setup" in commande


def test_the_installer_packages_what_the_build_produced(monkeypatch):
    """The two scripts must name the same folder: `build.py` renames Nuitka's
    output, and an installer built from `main.dist` would package nothing."""
    monkeypatch.delenv(build.ENV_VERSION, raising=False)
    commande = make_installer.build_command("3.4.5", ISCC)

    assert f"/DSourceDir={build.APP_DIR}" in commande
    assert f"/DOutputDir={build.DIST}" in commande
    assert commande[-1] == str(make_installer.SCRIPT)


def test_the_script_installs_the_executable_the_build_names():
    """`installer.iss` names the executable in its shortcuts and its uninstall
    entry. Renaming it in `build.py` alone would ship shortcuts pointing at a
    file that is not there."""
    script = make_installer.SCRIPT.read_text(encoding="utf-8")

    assert build.EXE.name in script


def test_a_missing_compiler_is_an_error(monkeypatch):
    """Producing no installer must fail the build, never pass quietly: the README
    tells people to download a file that would then not exist."""
    monkeypatch.setattr(make_installer.shutil, "which", lambda _: None)
    for variable in make_installer.PROGRAM_FILES:
        monkeypatch.setenv(variable, str(Path("nowhere")))

    with pytest.raises(FileNotFoundError, match="Inno Setup not found"):
        make_installer.compiler()


def test_the_destination_is_emptied_before_an_update():
    """Inno Setup removes only what it is told to, and a Nuitka distribution does
    not carry a stable set of names. Without the sweep, an update would silt up
    with what the new version no longer ships -- presets included, which the
    package enumerates at run time and would therefore keep listing."""
    script = make_installer.SCRIPT.read_text(encoding="utf-8")

    assert "[InstallDelete]" in script
    assert r'Type: filesandordirs; Name: "{app}\*"' in script


def test_the_sweep_only_touches_our_own_installation():
    """`/DIR=` accepts any path, and emptying a directory that is not ours is what
    the Inno Setup documentation warns about. The guard names the executable the
    build produces, so it recognises an installation by what is in it."""
    script = make_installer.SCRIPT.read_text(encoding="utf-8")

    assert "Check: OurOwnInstall" in script
    garde = script[script.index("function OurOwnInstall") :]
    assert build.EXE.name in garde
