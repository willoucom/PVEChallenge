# LolBotChallenge

Outil en ligne de commande qui prepare un lobby de partie personnalisee League of
Legends via l'API locale du client (LCU). Il ne lance jamais la partie : il cree le
lobby et ajoute les bots, le demarrage reste manuel.

## Prerequis

- Windows, client League of Legends installe et **ouvert**.
- Python 3.11+.
- `pip install -r requirements.txt` (une seule dependance : `requests`).

## Le lockfile

Le client ecrit ses identifiants d'API dans un fichier nomme `lockfile`, a la
racine de son dossier d'installation. Chemin par defaut de cet outil :

```
C:\Games\Riot Games\League of Legends\lockfile
```

Il est cree au demarrage du client et supprime a sa fermeture. Son contenu est une
ligne unique :

```
LeagueClient:<pid>:<port>:<password>:https
```

L'outil s'en sert pour construire `https://127.0.0.1:<port>` et s'authentifier en
HTTP basic avec `riot:<password>`. Le certificat du client etant auto-signe, la
verification TLS est desactivee.

Si le client est installe ailleurs :

```bash
python -m lolbot --install-dir "D:\Jeux\League of Legends" lobby ireaz
```

```bash
python -m lolbot --lockfile "D:\Jeux\League of Legends\lockfile" lobby ireaz
```

Equivalents par variables d'environnement : `LOLBOT_LOCKFILE`, `LOLBOT_INSTALL_DIR`.

## Usage

### `lobby` — creer le lobby depuis un preset

```bash
python -m lolbot lobby ireaz
```

```bash
python -m lolbot lobby ireaz --difficulty intro
```

L'argument est un nom de preset de `presets/`, ou le chemin d'un fichier JSON.
`--difficulty` (`intro`, `debutant`, `intermediaire`) surcharge la difficulte du
preset et s'applique a tous ses bots.

Si un lobby est deja ouvert dans le client, il est ferme puis recree. Les noms de
champions sont resolus avant toute action, donc une faute de frappe dans un preset
laisse le lobby en cours intact.

### `discover` — observer le lobby

Ne fait que des `GET`, ne modifie jamais l'etat du client. Interroge
`GET /lol-lobby/v2/lobby` toutes les 500 ms, affiche l'etat initial complet du
lobby puis, a chaque changement, le diff du JSON sous forme de chemins pointes.

```bash
python -m lolbot discover
```

Sert a relever la forme exacte du JSON quand le client evolue. Intervalle
configurable : `--interval 0.25`.

## Presets

Un preset est un fichier JSON dans `presets/`. `presets/ireaz.json` decrit mon
equipe (moi seul, aucun bot) et l'equipe adverse : Warwick top, Amumu jungle,
Malphite mid, Kai'Sa bot, Lulu support.

Le bloc `lobby` porte le nom du lobby et la politique de spectateurs. La carte et
le mode n'y figurent pas : cet outil ne cree que des parties personnalisees sur la
Faille de l'invocateur en selection aveugle.

Le preset emploie son propre vocabulaire, traduit vers celui du client dans
`lolbot/lobby.py` :

| Preset | Client |
|---|---|
| `top` / `jungle` / `mid` / `bot` / `support` | `TOP` / `JUNGLE` / `MIDDLE` / `BOTTOM` / `UTILITY` |
| `intro` / `debutant` / `intermediaire` | `RSINTRO` / `RSBEGINNER` / `RSINTERMEDIATE` |
| `teams.mine` / `teams.enemy` | `teamId` `"100"` / `"200"` |

Les champions sont nommes, pas identifies par `championId` : la correspondance est
lue sur le client a chaque execution, en croisant
`/lol-game-data/assets/v1/champion-summary.json` avec
`/lol-lobby/v2/lobby/custom/available-bots`. Le catalogue de champions contient
plusieurs entrees de meme nom avec des identifiants differents ; le croisement est
ce qui designe celle qui est jouable en bot.

## Endpoints utilises

Tous verifies contre un client League of Legends ouvert.

| Appel | Reponse | Corps |
|---|---|---|
| `POST /lol-lobby/v2/lobby` | `200` | `queueId` **3100**, `customGameLobby.configuration.mutators.id` **19** ; `mapId`, `gameMode` et `spectatorPolicy` sont dans `configuration` |
| `POST /lol-lobby/v1/lobby/custom/bots` | `204` | `championId`, `botDifficulty`, `teamId` (chaine), `position`, `botUuid` (chaine vide acceptee, le client genere l'identifiant) |
| `GET /lol-lobby/v2/lobby` | `200` / `404` | 404 quand aucun lobby n'est ouvert |
| `DELETE /lol-lobby/v2/lobby` | `204` | ferme le lobby ouvert |
| `GET /lol-lobby/v2/lobby/custom/available-bots` | `200` | liste des champions jouables en bot et de leurs difficultes |
| `GET /lol-game-data/assets/v1/champion-summary.json` | `200` | catalogue des champions |

`configuration.mapId` et `configuration.gameMode` ne choisissent pas la carte ni le
mode : le client les deduit du `queueId` et ignore ce que le corps annonce. Ils
sont donc figes dans `lolbot/lobby.py` sur les valeurs de la file 3100, pour que le
corps envoye decrive le lobby reellement cree.

Recreer un lobby passe par le `DELETE`, jamais par un POST seul : poste par-dessus
un lobby existant, `POST /lol-lobby/v2/lobby` applique bien la configuration mais
conserve les membres deja presents, et un bot dont la position est deja occupee est
alors refuse en renvoyant `204` sans rien ajouter.

Le champ du role s'appelle `position` dans le corps du POST, et ressort en
`botPosition` dans l'etat lu. `teamId` est envoye en chaine (`"100"` / `"200"`)
mais ressort a `0` : c'est l'appartenance a `customTeam100` / `customTeam200` qui
fait foi.

Toute erreur HTTP affiche la requete envoyee, le statut, les en-tetes et le corps
complet de la reponse : rien n'est avale.

## Ce qui reste a verifier

- `queueId` 3100 correspond a la file « Faille — partie personnalisee aveugle » de
  ce client. Rien ne garantit que cet identifiant soit stable d'un patch a l'autre.
