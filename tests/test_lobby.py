"""Two-source presets, and lobby creation with progress reporting."""

import json

import pytest

from pvechallenge.lobby import (
    BOTS_PATH,
    LOBBY_PATH,
    PresetError,
    available_presets,
    builtin_presets,
    load_preset,
    preset_path,
    run_lobby,
    user_presets,
)
from pvechallenge.paths import user_presets_dir

from .doubles import ClientFactice, champions_du_preset

#: Test name, chosen so it can collide with no shipped preset.
PERSO = "test-perso"


@pytest.fixture
def inclus():
    """Names of the presets shipped in the package, read at run time."""
    noms = sorted(builtin_presets())
    assert noms, "le paquet ne contient aucun preset : rien a exercer"
    assert PERSO not in noms
    return noms


def deposer(nom: str) -> None:
    """Write a minimal preset into the user directory."""
    dossier = user_presets_dir()
    dossier.mkdir(parents=True, exist_ok=True)
    (dossier / f"{nom}.json").write_text(json.dumps({"name": nom}), encoding="utf-8")


# --------------------------------------------------------------- two sources


def test_sans_preset_utilisateur_seuls_les_inclus_sont_disponibles(inclus):
    assert user_presets() == {}
    assert sorted(available_presets()) == inclus


def test_preset_inclu_resolu_vers_le_paquet(inclus):
    nom = inclus[0]
    assert preset_path(nom) == builtin_presets()[nom]


def test_preset_utilisateur_sajoute_aux_inclus(inclus):
    deposer(PERSO)
    assert sorted(available_presets()) == sorted(inclus + [PERSO])
    assert preset_path(PERSO) == user_presets_dir() / f"{PERSO}.json"


def test_nom_porte_par_les_deux_sources_est_refuse(inclus):
    nom = inclus[0]
    deposer(nom)

    assert nom not in available_presets()
    with pytest.raises(PresetError, match="cannot be used"):
        preset_path(nom)


def test_nom_inconnu_leve_et_liste_les_disponibles(inclus):
    with pytest.raises(PresetError, match="not found"):
        preset_path("nexistepas")


def test_chemin_de_fichier_explicite_est_prioritaire(inclus):
    chemin = builtin_presets()[inclus[0]]
    assert preset_path(str(chemin)) == chemin


def test_preset_json_invalide_leve():
    dossier = user_presets_dir()
    dossier.mkdir(parents=True, exist_ok=True)
    (dossier / f"{PERSO}.json").write_text("{ pas du json", encoding="utf-8")

    with pytest.raises(PresetError, match="not valid JSON"):
        load_preset(PERSO)


@pytest.mark.parametrize("champ, valeur", [("difficulty", "impossible"), ("teams", {"voisins": {}})])
def test_preset_incoherent_leve(champ, valeur, inclus):
    preset = json.loads(builtin_presets()[inclus[0]].read_text(encoding="utf-8"))
    preset[champ] = valeur
    dossier = user_presets_dir()
    dossier.mkdir(parents=True, exist_ok=True)
    (dossier / f"{PERSO}.json").write_text(json.dumps(preset), encoding="utf-8")

    with pytest.raises(PresetError):
        load_preset(PERSO)


# ---------------------------------------------------- creation and reporting


@pytest.fixture
def preset_et_client(inclus):
    """A shipped preset, and a client double able to resolve its champions."""
    preset = load_preset(inclus[0])
    return inclus[0], preset, ClientFactice(champions_du_preset(preset))


def test_run_lobby_poste_le_lobby_puis_chaque_bot(preset_et_client):
    nom, preset, client = preset_et_client
    attendus = sum(len(equipe.get("bots", [])) for equipe in preset["teams"].values())

    assert run_lobby(client, nom, report=lambda _message: None) == 0

    assert client.posts[0][0] == LOBBY_PATH
    assert client.posts[0][1]["queueId"] == 3100
    assert len(client.bots_postes) == attendus
    assert all(corps["botUuid"] == "" for corps in client.bots_postes)


def test_run_lobby_rapporte_chaque_etape_par_le_callback(preset_et_client):
    nom, preset, client = preset_et_client
    lignes = []

    run_lobby(client, nom, report=lignes.append)

    assert any("Creating lobby" in ligne for ligne in lignes)
    assert sum(ligne.startswith("  + ") for ligne in lignes) == len(client.bots_postes)
    assert lignes[-1].startswith("Lobby ready")


def test_run_lobby_necrit_rien_sur_la_sortie_standard(preset_et_client, capsys):
    """The decoupling exists for the window: nothing may leak to stdout."""
    nom, _preset, client = preset_et_client

    run_lobby(client, nom, report=lambda _message: None)

    assert capsys.readouterr().out == ""


def test_lobby_existant_est_ferme_avant_recreation(preset_et_client):
    nom, _preset, client = preset_et_client
    client.lobby_ouvert = True
    lignes = []

    run_lobby(client, nom, report=lignes.append)

    assert client.supprime == 1
    assert "Existing lobby closed." in lignes


def test_aucun_lobby_ouvert_aucune_suppression(preset_et_client):
    nom, _preset, client = preset_et_client

    run_lobby(client, nom, report=lambda _message: None)

    assert client.supprime == 0


def test_difficulte_surchargee_sapplique_a_tous_les_bots(preset_et_client):
    nom, _preset, client = preset_et_client

    run_lobby(client, nom, difficulty="intro", report=lambda _message: None)

    assert {corps["botDifficulty"] for corps in client.bots_postes} == {"RSINTRO"}


def test_champion_inconnu_laisse_le_lobby_intact(preset_et_client):
    """Champions are resolved before any action: nothing must have moved."""
    from pvechallenge.champions import ChampionError

    nom, _preset, client = preset_et_client
    client.champions = {"Personne": 1}
    client.lobby_ouvert = True

    with pytest.raises(ChampionError):
        run_lobby(client, nom, report=lambda _message: None)

    assert client.posts == []
    assert client.supprime == 0
