"""The window: construction, preset sources, options, worker thread.

These tests open real Tk windows, kept off-screen. An environment with no
graphical session cannot open one: the tests are skipped there rather than
reported as failures.
"""

import gc
import json
import sys

import pytest

tk = pytest.importorskip("tkinter")

from pvechallenge.config import load_config
from pvechallenge.gui import ICON_PATH, REPO_URL, STATUS_COLORS, build
from pvechallenge.i18n import t
from pvechallenge.lobby import available_presets, builtin_presets, user_presets
from pvechallenge.paths import user_presets_dir
from pvechallenge.version import app_version

PERSO = "test-perso"


@pytest.fixture
def inclus():
    noms = sorted(builtin_presets())
    assert noms and PERSO not in noms
    return noms


@pytest.fixture(scope="session")
def racine():
    """A single Tk interpreter for the whole test session.

    Creating one per test corrupts Tcl's internal state after a few cycles: it
    loses the path to its library, and later tests fail on a missing
    `tcl_findLibrary` or `auto.tcl`. Tests therefore open child windows of a
    single root.
    """
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        pytest.skip(f"no graphical session available: {exc}")
    root.withdraw()
    yield root
    root.destroy()


@pytest.fixture
def fenetre(racine):
    """A real window, kept off-screen, destroyed at the end of the test.

    The closing `gc.collect()` is not a comfort measure. Every `App` holds
    `StringVar` objects, which become finalisable as soon as the test lets go
    of it. If the garbage collector reaches them from a worker thread, their
    `__del__` calls Tcl outside the main thread: that thread then waits for the
    Tcl lock held by the main thread, which is itself waiting for the collector
    lock held by the worker. Both block for good.

    Collecting here, in the main thread and between two tests, guarantees that
    no finalisable Tk object is left around when a worker thread starts.
    """
    fille = tk.Toplevel(racine)
    fille.withdraw()
    application = build(fille)
    fille.update()
    yield fille, application
    fille.destroy()
    gc.collect()


def couleur(widget) -> str:
    """Tk returns a Tcl object, not a string: a direct comparison would fail."""
    return str(widget.cget("foreground"))


def deposer(nom: str, contenu: dict | None = None) -> None:
    dossier = user_presets_dir()
    dossier.mkdir(parents=True, exist_ok=True)
    corps = json.dumps({"name": nom} if contenu is None else contenu)
    (dossier / f"{nom}.json").write_text(corps, encoding="utf-8")


def ordre_attendu() -> list[str]:
    """Rows as the window orders them: by source, shipped first, then file name."""
    chemins = available_presets()
    perso = set(user_presets())
    return sorted(chemins, key=lambda stem: (stem in perso, chemins[stem].name))


# ------------------------------------------------------------- construction


def test_titre_et_theme_natif(fenetre):
    root, application = fenetre

    assert root.title() == "PVE Challenge"
    assert "vista" in str(application.tk.call("ttk::style", "theme", "use"))


def test_journal_en_lecture_seule(fenetre):
    _root, application = fenetre

    assert str(application.log["state"]) == "disabled"


def textes_du_pied(application) -> list[str]:
    """Labels placed directly on the main frame, outside the framed blocks."""
    return [
        str(enfant.cget("text"))
        for enfant in application.winfo_children()
        if "text" in enfant.keys()
    ]


def test_avertissement_riot_affiche(fenetre):
    """Its presence is required by Riot's policy, it is not an ornament."""
    _root, application = fenetre

    assert any("Legal Jibber Jabber" in texte for texte in textes_du_pied(application))


def test_lien_vers_le_depot_affiche(fenetre):
    _root, application = fenetre
    pied = application.version_label.master

    assert REPO_URL in [str(e.cget("text")) for e in pied.winfo_children()]


def test_version_affichee_en_bas_a_droite(fenetre):
    """It must say what the file properties say, hence the same source."""
    _root, application = fenetre
    info = application.version_label.grid_info()

    assert str(application.version_label.cget("text")) == app_version()
    assert info["sticky"] == "e"
    assert str(application.version_label.cget("foreground")) == STATUS_COLORS["neutre"]


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific probe")
def test_icone_de_fenetre_posee(fenetre):
    """Tk cannot read an `.ico` back: ask Windows rather than Tk.

    Without that call the window carries Tk's default feather, which stays
    invisible until somebody actually looks at it.
    """
    import ctypes

    root, _application = fenetre
    assert ICON_PATH.is_file(), f"icon missing from the package: {ICON_PATH}"

    utilisateur = ctypes.windll.user32
    handle = utilisateur.GetParent(root.winfo_id()) or root.winfo_id()
    petite = utilisateur.SendMessageW(handle, 0x007F, 0, 0)
    grande = utilisateur.SendMessageW(handle, 0x007F, 1, 0)

    assert petite or grande


# ---------------------------------------------------------------- preset list


def test_liste_les_presets_inclus_avec_leur_source(fenetre, inclus):
    _root, application = fenetre
    attendus = ordre_attendu()

    assert sorted(attendus) == inclus
    assert list(application.tree.get_children()) == attendus
    assert application.tree.item(attendus[0], "values") == (
        f"{attendus[0]}.json",
        t("gui.preset.source.builtin"),
    )
    assert application.tree.selection() == (attendus[0],)
    assert couleur(application.status) == STATUS_COLORS["neutre"]


def test_inventaire_compte_les_presets_disponibles(fenetre, inclus):
    """The count gets its own line: the status bar keeps what is happening."""
    _root, application = fenetre

    assert application.inventaire_var.get() == t("gui.status.available", count=len(inclus))
    assert application.status_var.get() == t("gui.status.ready")


def test_preset_utilisateur_apparait_marque_perso(fenetre, inclus):
    root, application = fenetre
    deposer(PERSO)

    application.refresh_presets()
    root.update()

    assert sorted(application.tree.get_children()) == sorted(inclus + [PERSO])
    assert list(application.tree.get_children()) == ordre_attendu()
    assert application.tree.item(PERSO, "values") == (
        f"{PERSO}.json",
        t("gui.preset.source.user"),
    )


def test_le_libelle_vient_du_champ_name_et_le_fichier_garde_sa_colonne(fenetre, inclus):
    root, application = fenetre
    deposer(PERSO, {"name": "5 Warwick (intro)"})

    application.refresh_presets()
    root.update()

    assert application.tree.item(PERSO, "text") == "5 Warwick (intro)"
    assert application.tree.item(PERSO, "values")[0] == f"{PERSO}.json"


def test_le_libelle_retombe_sur_le_nom_de_fichier_si_le_json_est_casse(fenetre, inclus):
    """A broken preset must not take the list down with it."""
    root, application = fenetre
    dossier = user_presets_dir()
    dossier.mkdir(parents=True, exist_ok=True)
    (dossier / f"{PERSO}.json").write_text("{ ceci n'est pas du json", encoding="utf-8")

    application.refresh_presets()
    root.update()

    assert application.tree.item(PERSO, "text") == PERSO


def test_collision_retire_le_nom_et_le_signale_en_rouge(fenetre, inclus):
    root, application = fenetre
    deposer(inclus[0])

    application.refresh_presets()
    root.update()

    assert inclus[0] not in application.tree.get_children()
    assert couleur(application.status) == STATUS_COLORS["erreur"]
    assert repr(inclus[0]) in application.status_var.get()


# ---------------------------------------------------------------- options


def test_reglage_du_lockfile_enregistre_et_relu(fenetre):
    root, application = fenetre
    application.lockfile_var.set("D:\\Jeux\\LoL\\lockfile")

    application.save_lockfile()
    root.update()

    assert load_config().lockfile == "D:\\Jeux\\LoL\\lockfile"
    assert couleur(application.status) == STATUS_COLORS["succes"]

    # This second window is destroyed explicitly: leaving it alive would leave
    # behind Tk variables the collector may finalise later from another thread,
    # which calls Tcl outside the main thread.
    seconde = tk.Toplevel(root)
    try:
        assert build(seconde).lockfile_var.get() == "D:\\Jeux\\LoL\\lockfile"
    finally:
        seconde.destroy()


def test_champ_vide_efface_le_reglage(fenetre):
    _root, application = fenetre
    application.lockfile_var.set("D:\\Jeux\\LoL\\lockfile")
    application.save_lockfile()

    application.lockfile_var.set("   ")
    application.save_lockfile()

    assert load_config().lockfile is None


# ------------------------------------------------------------ worker thread


def test_application_sans_client_echoue_sans_figer_l_interface(fenetre, inclus):
    """No client is listening: the error must come back through the queue, not block."""
    root, application = fenetre
    application.tree.selection_set(inclus[0])

    # Clear the Tk garbage now, in the main thread, rather than leaving it to the
    # worker thread's collector: their finalisers call Tcl, and would do so from
    # the wrong thread.
    gc.collect()

    application.apply_selected()
    assert "disabled" in application.apply_button.state()

    application._worker.join(timeout=30)
    if application._worker.is_alive():
        # A thread still alive here is either a real deadlock or a slow machine.
        # Without the stacks there is no telling which, and a failure nobody can
        # diagnose keeps coming back.
        import faulthandler
        import tempfile

        # `dump_traceback` writes to a real descriptor: an in-memory buffer has
        # none, and the call would fail on `fileno`.
        with tempfile.TemporaryFile("w+") as fichier:
            faulthandler.dump_traceback(file=fichier, all_threads=True)
            fichier.seek(0)
            piles = fichier.read()
        pytest.fail("the worker thread did not finish within 30 s.\n" + piles)

    application._drain()
    root.update()

    assert couleur(application.status) == STATUS_COLORS["erreur"]
    assert "disabled" not in application.apply_button.state()
    assert f"--- {inclus[0]} ---" in application.log.get("1.0", "end")
