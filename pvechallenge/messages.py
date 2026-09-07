"""Message catalogues, one per language.

Keys are grouped by the module that uses them. Every catalogue must hold exactly
the same keys: a test enforces it, because a missing translation is invisible
until a user hits that one path.

Placeholders use `str.format` named fields, so a translation may reorder them.
The Riot disclaimer is deliberately absent: its wording is imposed by Riot's
policy and is not ours to translate.
"""

#: Language used when the system locale matches nothing we ship.
DEFAULT_LANGUAGE = "en"


ENGLISH: dict[str, str] = {
    # -- window chrome -----------------------------------------------------
    "gui.subtitle": "Prepares a custom game lobby. Starting the game stays manual.",
    "gui.preset.frame": "Preset",
    "gui.preset.name": "Name",
    "gui.preset.source": "Source",
    "gui.preset.source.builtin": "included",
    "gui.preset.source.user": "yours",
    "gui.log.frame": "Log",
    "gui.options.frame": "Options",
    "gui.button.apply": "Apply",
    "gui.button.refresh": "Refresh",
    "gui.button.open_presets": "Open the presets folder",
    "gui.button.browse": "Browse...",
    "gui.button.save": "Save",
    "gui.options.lockfile": "Lockfile:",
    "gui.options.hint": "Empty = the client's standard install location.",
    # -- window state ------------------------------------------------------
    "gui.status.ready": "Ready.",
    "gui.status.available": "{count} preset(s) available.",
    "gui.status.unusable": "Unusable name(s): {names}. An included preset already uses them.",
    "gui.status.no_selection": "No preset selected.",
    "gui.status.applying": "Applying preset {name}...",
    "gui.status.saved": "Setting saved in {path}",
    "gui.status.lobby_ready": "Lobby ready. Start the game from the client.",
    "gui.error.presets_unreadable": "Cannot read the presets: {error}",
    "gui.error.open_folder": "Cannot open {path}: {error}",
    "gui.log.discarded": "Presets discarded, an included one already uses the name: {names}",
    "gui.log.folder": "Folder concerned: {path}",
    "gui.dialog.lockfile": "Choose the client's lockfile",
    "gui.connected_as": "Connected as: {name}",
    "gui.unknown_summoner": "<unknown>",
    "gui.error.lcu_unreachable": "Cannot reach the LCU: {error}",
    # -- presets -----------------------------------------------------------
    "preset.collision": (
        "The name {name!r} cannot be used: a preset included with the tool already "
        "uses it. Rename {path}."
    ),
    "preset.not_found": (
        "Preset not found: {name!r}. Available: {available}. Your presets: {folder}"
    ),
    "preset.file_missing": "Preset not found: {path}.",
    "preset.invalid_json": "{path} is not valid JSON: {error}",
    "preset.unknown_difficulty": "{path}: unknown difficulty {value!r}. Expected: {expected}.",
    "preset.unknown_team": "{path}: unknown team {value!r}. Expected: {expected}.",
    "preset.unknown_role": "{path}: unknown role {role!r} for {champion!r}. Expected: {expected}.",
    # -- lobby -------------------------------------------------------------
    "lobby.still_open": (
        "The existing lobby still answers {timeout} s after being closed. Check the "
        "state of the client."
    ),
    "lobby.closed_existing": "Existing lobby closed.",
    "lobby.creating": "Creating lobby {name!r} (mapId={map_id}, {mode}, queueId={queue_id})",
    "lobby.bot_added": "  + {champion} ({champion_id}) {position} {difficulty} team {team}",
    "lobby.ready": "Lobby ready: {count} bot(s) added. Start the game from the client.",
    # -- lockfile ----------------------------------------------------------
    "lockfile.lockfile_label": "Lockfile: {path}",
    "lockfile.bad_shape": (
        "{path}: unexpected format, 5 fields expected "
        "(name:pid:port:password:protocol), {count} found."
    ),
    "lockfile.bad_numbers": "{path}: pid or port is not numeric ({pid!r}, {port!r}).",
    "lockfile.not_found": (
        "Lockfile not found: {path}\n"
        "The League of Legends client must be running: the file is created when it "
        "starts and removed when it closes.\n"
        "If the client is installed elsewhere, set its path in the window's options, "
        "which saves it to {config}, or use the {env_lockfile} / {env_install_dir} "
        "environment variables."
    ),
    "lockfile.unreadable": "Cannot read {path}: {error}",
    "lockfile.redacted": (
        "{process} pid={pid} port={port} protocol={protocol} password=<{length} characters>"
    ),
    # -- configuration -----------------------------------------------------
    "config.unreadable": "Cannot read {path}: {error}",
    "config.invalid_json": "{path} is not valid JSON: {error}",
    "config.not_an_object": "{path}: a JSON object was expected, found {found}.",
    "config.lockfile_not_a_string": "{path}: 'lockfile' must be a string, found {found}.",
    "config.unwritable": "Cannot write {path}: {error}",
    # -- champions ---------------------------------------------------------
    "champion.unknown": "Champion unknown or unavailable as a bot: {name!r}.{detail}",
    "champion.near_matches": " Close matches: {names}.",
    # -- raw HTTP reporting ------------------------------------------------
    "http.failed": "{method} {path} failed (HTTP {status}).",
    "http.header": "--- LCU response ---",
    "http.request_body": "Request body:",
    "http.response_headers": "Response headers:",
    "http.response_body": "Response body:",
    "http.empty": "  <empty>",
    "http.footer": "--- end of response ---",
    # -- JSON diff ---------------------------------------------------------
    "diff.truncated": "... (truncated, {length} characters)",
    "diff.was": "(was {value})",
}


FRENCH: dict[str, str] = {
    # -- habillage de la fenetre -------------------------------------------
    "gui.subtitle": "Prepare un lobby de partie personnalisee. Le lancement de la partie reste manuel.",
    "gui.preset.frame": "Preset",
    "gui.preset.name": "Nom",
    "gui.preset.source": "Source",
    "gui.preset.source.builtin": "inclu",
    "gui.preset.source.user": "perso",
    "gui.log.frame": "Journal",
    "gui.options.frame": "Options",
    "gui.button.apply": "Appliquer",
    "gui.button.refresh": "Rafraichir",
    "gui.button.open_presets": "Ouvrir le dossier des presets",
    "gui.button.browse": "Parcourir...",
    "gui.button.save": "Enregistrer",
    "gui.options.lockfile": "Lockfile :",
    "gui.options.hint": "Vide = emplacement d'installation standard du client.",
    # -- etat de la fenetre -------------------------------------------------
    "gui.status.ready": "Pret.",
    "gui.status.available": "{count} preset(s) disponible(s).",
    "gui.status.unusable": "Nom(s) inutilisable(s) : {names}. Un preset inclu les porte deja.",
    "gui.status.no_selection": "Aucun preset selectionne.",
    "gui.status.applying": "Application du preset {name}...",
    "gui.status.saved": "Reglage enregistre dans {path}",
    "gui.status.lobby_ready": "Lobby pret. Lance la partie depuis le client.",
    "gui.error.presets_unreadable": "Lecture des presets impossible : {error}",
    "gui.error.open_folder": "Ouverture impossible de {path} : {error}",
    "gui.log.discarded": "Presets ecartes, nom deja inclu dans l'outil : {names}",
    "gui.log.folder": "Dossier concerne : {path}",
    "gui.dialog.lockfile": "Choisir le fichier lockfile du client",
    "gui.connected_as": "Connecte en tant que : {name}",
    "gui.unknown_summoner": "<inconnu>",
    "gui.error.lcu_unreachable": "Connexion a la LCU impossible : {error}",
    # -- presets ------------------------------------------------------------
    "preset.collision": (
        "Le nom {name!r} ne peut pas etre utilise : un preset inclu dans l'outil "
        "le porte deja. Renomme {path}."
    ),
    "preset.not_found": (
        "Preset introuvable : {name!r}. Disponibles : {available}. "
        "Presets utilisateur : {folder}"
    ),
    "preset.file_missing": "Preset introuvable : {path}.",
    "preset.invalid_json": "{path} n'est pas un JSON valide : {error}",
    "preset.unknown_difficulty": "{path} : difficulte {value!r} inconnue. Attendu : {expected}.",
    "preset.unknown_team": "{path} : equipe {value!r} inconnue. Attendu : {expected}.",
    "preset.unknown_role": "{path} : role {role!r} inconnu pour {champion!r}. Attendu : {expected}.",
    # -- lobby --------------------------------------------------------------
    "lobby.still_open": (
        "Le lobby existant repond encore {timeout} s apres sa fermeture. "
        "Verifie l'etat du client."
    ),
    "lobby.closed_existing": "Lobby existant ferme.",
    "lobby.creating": "Creation du lobby {name!r} (mapId={map_id}, {mode}, queueId={queue_id})",
    "lobby.bot_added": "  + {champion} ({champion_id}) {position} {difficulty} equipe {team}",
    "lobby.ready": "Lobby pret : {count} bot(s) ajoute(s). Lance la partie depuis le client.",
    # -- lockfile -----------------------------------------------------------
    "lockfile.lockfile_label": "Lockfile : {path}",
    "lockfile.bad_shape": (
        "{path} : format inattendu, 5 champs attendus "
        "(nom:pid:port:password:protocol), {count} trouve(s)."
    ),
    "lockfile.bad_numbers": "{path} : pid ou port non numerique ({pid!r}, {port!r}).",
    "lockfile.not_found": (
        "Lockfile introuvable : {path}\n"
        "Le client League of Legends doit etre ouvert : le fichier est cree au "
        "demarrage et supprime a la fermeture.\n"
        "Si le client est installe ailleurs, renseigne son chemin dans les options "
        "de la fenetre, qui l'enregistre dans {config}, ou passe par les variables "
        "{env_lockfile} / {env_install_dir}."
    ),
    "lockfile.unreadable": "Lecture impossible de {path} : {error}",
    "lockfile.redacted": (
        "{process} pid={pid} port={port} protocol={protocol} password=<{length} caracteres>"
    ),
    # -- configuration ------------------------------------------------------
    "config.unreadable": "Lecture impossible de {path} : {error}",
    "config.invalid_json": "{path} n'est pas un JSON valide : {error}",
    "config.not_an_object": "{path} : un objet JSON est attendu, {found} trouve.",
    "config.lockfile_not_a_string": "{path} : 'lockfile' doit etre une chaine, {found} trouve.",
    "config.unwritable": "Ecriture impossible de {path} : {error}",
    # -- champions ----------------------------------------------------------
    "champion.unknown": "Champion inconnu ou indisponible en bot : {name!r}.{detail}",
    "champion.near_matches": " Proches : {names}.",
    # -- restitution HTTP brute ---------------------------------------------
    "http.failed": "{method} {path} a echoue (HTTP {status}).",
    "http.header": "--- Reponse LCU ---",
    "http.request_body": "Corps envoye :",
    "http.response_headers": "En-tetes de reponse :",
    "http.response_body": "Corps de reponse :",
    "http.empty": "  <vide>",
    "http.footer": "--- fin reponse ---",
    # -- diff JSON ----------------------------------------------------------
    "diff.truncated": "... (tronque, {length} caracteres)",
    "diff.was": "(etait {value})",
}


#: Every language we ship, by code.
CATALOGUES: dict[str, dict[str, str]] = {"en": ENGLISH, "fr": FRENCH}
