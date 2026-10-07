<p align="center"><img src="social-preview.png" width="100%" alt="Session Guard: see which Claude Code session needs you"></p>

# Session Guard

<p align="center"><b><a href="../README.md#deutsch">🇩🇪 Deutsch</a> · <a href="../README.md#english">🇬🇧 English</a> · 🇫🇷 Français · <a href="README.it.md">🇮🇹 Italiano</a> · <a href="README.es.md">🇪🇸 Español</a></b></p>

> 🇫🇷 **Voyez d'un coup d'œil quelle session Claude Code a besoin de vous.** Session Guard affiche dans la barre d'état
> de VS Code chaque session qui vous attend : en rouge pour une autorisation ou une question, en jaune lorsqu'une
> réponse est terminée. Un clic suffit pour passer à la session, et un son n'est émis que lorsqu'une vraie question
> vous est posée.

![Barre d'état avec une entrée Session Guard rouge et une jaune](screenshot.png)

*La barre d'état avec une session en attente d'autorisation (rouge) et une session terminée (jaune), ici avec
l'interface en allemand.*

![Illustration des trois types d'entrées en anglais](status-bar-illustration.png)

*Les trois types d'entrées avec l'interface en anglais : autorisation et question (rouge), réponse terminée (jaune).*

Vous utilisez plusieurs chats Claude Code côte à côte dans VS Code. L'un pose une question, un autre attend une
autorisation, un troisième a terminé, et vous ne vous en apercevez qu'en les parcourant tous un par un. Session Guard
affiche dans la barre d'état de VS Code chaque session qui vous attend, et n'émet un son que lorsqu'une vraie question
vous est posée.

## Fonctionnalités

- **Une entrée par session en attente**, libellée avec le titre de la session tel qu'il apparaît dans la liste des
  sessions de Claude Code.
  - 🟥 **rouge :** Claude a besoin de votre autorisation ou vous pose une question
  - 🟨 **jaune :** Claude a terminé une réponse que vous avez lancée
- **Un clic pour basculer :** charge la session dans la barre latérale de Claude Code et retire l'entrée. Pas de
  deuxième onglet de chat.
- **Au survol**, vous voyez depuis combien de temps la session attend, ainsi que la question ou la dernière ligne.
- **Un son uniquement pour les questions** (AskUserQuestion, boîtes de saisie MCP, sessions en arrière-plan qui
  attendent une saisie). Les autorisations et les réponses terminées restent silencieuses.
- **Pas de fausses alertes** pour des réponses qui ne sont pas vraiment terminées :
  - Claude continue de lui-même (par exemple après un hook Stop) : l'entrée disparaît.
  - Des tâches en arrière-plan de la session sont encore en cours : rien ne s'affiche avant qu'elles soient terminées.
  - La réponse a été lancée par une planification (`/loop`, cron) : rien ne s'affiche.
- Les entrées disparaissent lorsque vous répondez, lorsque Claude continue, lorsque vous cliquez dessus ou (jaunes
  uniquement) au bout de 60 minutes.
- Interface en allemand, anglais, français, italien et espagnol (suit la langue d'affichage de VS Code).
- Tout reste sur votre machine. Aucun accès réseau, aucune télémétrie.

## Fonctionnement

```
Session Claude Code ──hook──▶ ~/.local/state/session-guard/sessions/<id>.json ──▶ extension VS Code ──▶ barre d'état
                                                                       ▲
                          historique de session (~/.claude/projects/…) ┘  « attend-elle encore ? »
```

Le dépôt comprend deux parties :

| Partie | Rôle |
|---|---|
| **Plugin Claude Code** (`hooks/`) | Un hook sur `Stop`, `PreToolUse` (AskUserQuestion) et `Notification` écrit un petit fichier d'état JSON par session et émet le son des questions. |
| **Extension VS Code** (`vscode/`) | Lit les fichiers d'état toutes les deux secondes, vérifie dans l'historique de la session si celle-ci attend encore, et affiche les entrées dans la barre d'état. |

## Prérequis

- Claude Code avec prise en charge des plugins, utilisé dans l'extension VS Code
- VS Code 1.90 ou version ultérieure
- Python 3.9 ou version ultérieure dans votre `PATH` : sous le nom `python3` sur macOS et Linux, `python` sur
  Windows (le hook n'utilise que la bibliothèque standard)
- macOS, Linux ou Windows 10/11. **Windows :** installez le plugin depuis la [branche `windows`](https://github.com/simon-says-labs/session-guard/tree/windows)
  (voir ci-dessous) ; l'extension VS Code est la même sur tous les systèmes.

## Installation

### 1. Plugin Claude Code (le hook)

Dans une session Claude Code :

```
/plugin marketplace add simon-says-labs/session-guard
/plugin install session-guard@simon-says
```

### 2. Extension VS Code

Téléchargez `session-guard-<version>.vsix` depuis la
[dernière version publiée](https://github.com/simon-says-labs/session-guard/releases/latest) et exécutez :

```bash
code --install-extension session-guard-*.vsix
```

Si vous utilisez des [profils VS Code](https://code.visualstudio.com/docs/configure/profiles), installez l'extension
dans chaque profil dans lequel vous travaillez, par exemple avec `--profile Work`. Sans `--profile`, l'extension n'est
installée que dans le profil par défaut.

Rechargez ensuite la fenêtre VS Code (**Developer: Reload Window**, accessible via la palette de commandes). Cela
redémarre aussi les sessions Claude Code de cette fenêtre : Claude Code ne charge un plugin nouvellement installé ou
mis à jour qu'au démarrage d'une session ; jusque-là, les sessions en cours conservent les anciens hooks (ou aucun).

## Configuration

| Variable d'environnement | Effet |
|---|---|
| `SESSION_GUARD_SOUND=off` | Aucun son |
| `SESSION_GUARD_STATE=/chemin` | Autre dossier d'état (à définir pour Claude Code **et** pour VS Code) |

Chaque événement est consigné avec `sound=yes|no` dans `~/.local/state/session-guard/session-guard.log` (Windows :
`%LOCALAPPDATA%\session-guard\session-guard.log`) ; vous pouvez y vérifier pourquoi un son a été émis ou non.

## Limites

Veuillez les lire avant de vous fier à l'extension :

- **Commandes internes.** Le clic utilise des commandes internes de l'extension Claude Code pour VS Code
  (`claude-vscode.sidebar.open` et `claude-vscode.editor.open`), vérifiées pour la dernière fois avec la version
  2.1.288. Elles ne font pas partie d'une API publique et peuvent changer. Si elles échouent, Session Guard se rabat
  sur l'URI documentée `vscode://anthropic.claude-code/open?session=<id>`, qui peut ouvrir la session dans un nouvel
  onglet.
- **Format de l'historique de session.** Le fait qu'une session attende encore est déterminé à partir des historiques
  de session de Claude Code. Leur format n'est pas documenté officiellement.
- **Paramètre de barre latérale.** Un clic sur une entrée définit l'emplacement préféré de l'extension Claude Code sur
  la barre latérale (`claudeCode.preferredLocation`).
- **Sous Windows, le plugin nécessite la [branche `windows`](https://github.com/simon-says-labs/session-guard/tree/windows).** `hooks/hooks.json` vaut
  pour tous les systèmes, et aucune commande ne fonctionne partout : sous Windows, `python3` n'est souvent que
  l'espace réservé du Microsoft Store (code de sortie 49), sous macOS `python` manque généralement. La branche ne
  diffère de `main` que par ce seul fichier (elle lance `python` sans shell, Git Bash n'est pas nécessaire) ; la CI
  le vérifie. Installation : `/plugin marketplace add simon-says-labs/session-guard#windows`, puis
  `/plugin install session-guard@simon-says`. Si Python n'est pas installé, `python` n'est lui aussi que cet espace
  réservé et le hook reste muet ; installez Python depuis python.org avec « Add python.exe to PATH ». Sous Windows,
  le son passe par `winsound` et l'état se trouve dans `%LOCALAPPDATA%\session-guard`.
- **Historiques volumineux.** Le hook lit l'historique une fois par événement. Pour des historiques de 40 à 60 Mo,
  cela prend environ 0,75 s sur un Apple M4 Pro.

## Désinstallation

```
/plugin uninstall session-guard@simon-says
code --uninstall-extension simon-says-labs.session-guard
```

Vous pouvez ensuite supprimer le dossier d'état `~/.local/state/session-guard` (Windows :
`%LOCALAPPDATA%\session-guard`).

## Développement

```bash
python3 -m unittest discover -s tests/python   # hook
node --test tests/node/*.test.js               # extension
python3 vscode/build_vsix.py                   # écrit dist/session-guard-<version>.vsix
claude plugin validate .                       # manifestes du plugin et du marketplace
```

L'extension n'a aucune dépendance npm et ne nécessite aucune étape de build. Voir
[CONTRIBUTING.md](../CONTRIBUTING.md).

## Licence

[MIT](../LICENSE) © 2026 Simon Eckmiller · publié par [Simon Says](https://github.com/simon-says-labs)

Ceci est un projet communautaire indépendant. Il n'est ni affilié à Anthropic ni soutenu par Anthropic.

<p align="right"><a href="#session-guard">↑</a></p>
