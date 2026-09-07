"""Lockfile priority chain, and persisted configuration."""

import json
from pathlib import Path

import pytest

from pvechallenge.config import Config, ConfigError, config_path, load_config, set_lockfile
from pvechallenge.lockfile import (
    DEFAULT_INSTALL_DIR,
    LockfileError,
    parse_lockfile,
    read_credentials,
    resolve_lockfile_path,
)

DEFAUT = DEFAULT_INSTALL_DIR / "lockfile"


# ------------------------------------------------------------- configuration


def test_configuration_absente_donne_une_config_vide():
    assert not config_path().exists()
    assert load_config() == Config(lockfile=None)


def test_reglage_ecrit_puis_relu():
    chemin = set_lockfile("D:\\Jeux\\LoL\\lockfile")

    assert chemin == config_path()
    assert json.loads(chemin.read_text(encoding="utf-8")) == {"lockfile": "D:\\Jeux\\LoL\\lockfile"}
    assert load_config().lockfile == "D:\\Jeux\\LoL\\lockfile"


def test_reglage_vide_efface_le_chemin():
    set_lockfile("D:\\Jeux\\LoL\\lockfile")
    set_lockfile(None)

    assert load_config().lockfile is None


@pytest.mark.parametrize(
    "contenu, motif",
    [
        ("{ pas du json", "not valid JSON"),
        ('["une", "liste"]', "JSON object"),
        ('{"lockfile": 42}', "must be a string"),
    ],
)
def test_configuration_illisible_leve_plutot_que_de_se_taire(contenu, motif):
    """Ignoring a broken file would apply the default while implying the setting held."""
    config_path().parent.mkdir(parents=True, exist_ok=True)
    config_path().write_text(contenu, encoding="utf-8")

    with pytest.raises(ConfigError, match=motif):
        load_config()


def test_configuration_illisible_remonte_jusqu_a_la_resolution():
    config_path().parent.mkdir(parents=True, exist_ok=True)
    config_path().write_text("{ pas du json", encoding="utf-8")

    with pytest.raises(ConfigError):
        resolve_lockfile_path()


# ------------------------------------------------------------ priority chain


def test_sans_rien_le_defaut_fige_sapplique():
    assert resolve_lockfile_path() == DEFAUT


def test_configuration_bat_le_defaut():
    set_lockfile("D:\\Config\\lockfile")

    assert resolve_lockfile_path() == Path("D:\\Config\\lockfile")


def test_environnement_bat_la_configuration(monkeypatch):
    set_lockfile("D:\\Config\\lockfile")
    monkeypatch.setenv("PVECHALLENGE_INSTALL_DIR", "E:\\EnvDir")

    assert resolve_lockfile_path() == Path("E:\\EnvDir\\lockfile")


def test_variable_de_lockfile_bat_celle_de_dossier(monkeypatch):
    monkeypatch.setenv("PVECHALLENGE_INSTALL_DIR", "E:\\EnvDir")
    monkeypatch.setenv("PVECHALLENGE_LOCKFILE", "E:\\EnvFile\\lockfile")

    assert resolve_lockfile_path() == Path("E:\\EnvFile\\lockfile")


def test_argument_lockfile_bat_tout(monkeypatch):
    set_lockfile("D:\\Config\\lockfile")
    monkeypatch.setenv("PVECHALLENGE_LOCKFILE", "E:\\EnvFile\\lockfile")

    assert resolve_lockfile_path(lockfile="F:\\Arg\\lockfile") == Path("F:\\Arg\\lockfile")


def test_variable_de_lockfile_bat_l_argument_de_dossier(monkeypatch):
    """The documented order: the file variable comes before the directory argument."""
    monkeypatch.setenv("PVECHALLENGE_LOCKFILE", "E:\\EnvFile\\lockfile")

    assert resolve_lockfile_path(install_dir="F:\\ArgDir") == Path("E:\\EnvFile\\lockfile")


def test_argument_de_dossier_bat_sa_variable(monkeypatch):
    monkeypatch.setenv("PVECHALLENGE_INSTALL_DIR", "E:\\EnvDir")

    assert resolve_lockfile_path(install_dir="F:\\ArgDir") == Path("F:\\ArgDir\\lockfile")


# --------------------------------------------------------------- real reads


def test_lockfile_absent_nomme_le_chemin_et_les_recours():
    with pytest.raises(LockfileError) as erreur:
        read_credentials()

    message = str(erreur.value)
    assert str(DEFAUT) in message
    assert "PVECHALLENGE_LOCKFILE" in message


def test_lockfile_lu_et_decompose(tmp_path):
    fichier = tmp_path / "lockfile"
    fichier.write_text("LeagueClient:1234:54321:motdepasse:https", encoding="utf-8")

    identifiants = read_credentials(lockfile=fichier)

    assert identifiants.pid == 1234
    assert identifiants.port == 54321
    assert identifiants.base_url == "https://127.0.0.1:54321"
    assert identifiants.auth == ("riot", "motdepasse")


def test_mot_de_passe_absent_de_la_forme_lisible(tmp_path):
    """The lockfile carries a secret: it must not end up in a log."""
    fichier = tmp_path / "lockfile"
    fichier.write_text("LeagueClient:1:2:motdepasse:https", encoding="utf-8")

    lisible = read_credentials(lockfile=fichier).redacted()

    assert "motdepasse" not in lisible


@pytest.mark.parametrize(
    "contenu, motif",
    [
        ("trop:peu:de:champs", "5 fields expected"),
        ("LeagueClient:abc:54321:mdp:https", "not numeric"),
    ],
)
def test_lockfile_malforme_leve(contenu, motif, tmp_path):
    with pytest.raises(LockfileError, match=motif):
        parse_lockfile(contenu, tmp_path / "lockfile")
