# Session Guard

<p align="center"><b><a href="../README.md#deutsch">🇩🇪 Deutsch</a> · <a href="../README.md#english">🇬🇧 English</a> · <a href="README.fr.md">🇫🇷 Français</a> · <a href="README.it.md">🇮🇹 Italiano</a> · 🇪🇸 Español</b></p>

> 🇪🇸 **Ve de un vistazo qué sesión de Claude Code te necesita.** Session Guard muestra en la barra de estado de
> VS Code cada sesión que te está esperando: en rojo para una aprobación o una pregunta, en amarillo cuando una
> respuesta está lista. Un clic te lleva a la sesión, y solo suena un aviso cuando realmente se te hace una pregunta.

![Barra de estado con una entrada de Session Guard roja y una amarilla](screenshot.png)

*La barra de estado con una sesión que espera aprobación (roja) y una terminada (amarilla), aquí con la interfaz en
alemán.*

![Ilustración de los tres tipos de entrada en inglés](status-bar-illustration.png)

*Los tres tipos de entrada con la interfaz en inglés: aprobación y pregunta (rojo), respuesta terminada (amarillo).*

Trabajas con varios chats de Claude Code a la vez en VS Code. Uno hace una pregunta, otro espera una aprobación, un
tercero ha terminado, y solo te das cuenta cuando los revisas todos uno por uno. Session Guard lleva a la barra de
estado de VS Code cada sesión que te está esperando, y solo reproduce un sonido cuando realmente se te hace una
pregunta.

## Funciones

- **Una entrada por cada sesión en espera**, con el título de la sesión que aparece en la lista de sesiones de
  Claude Code.
  - 🟥 **rojo:** Claude necesita tu aprobación o te hace una pregunta
  - 🟨 **amarillo:** Claude ha terminado una respuesta que iniciaste tú
- **Clic para cambiar:** carga la sesión en la barra lateral de Claude Code y quita la entrada. Sin una segunda
  pestaña de chat.
- **Al pasar el ratón por encima** ves cuánto tiempo lleva esperando la sesión y la pregunta o la última línea.
- **Sonido solo para preguntas** (AskUserQuestion, diálogos de entrada de MCP, sesiones en segundo plano que esperan
  una entrada). Las aprobaciones y las respuestas terminadas no suenan.
- **Sin falsas alarmas** por respuestas que en realidad no han terminado:
  - Claude continúa por sí solo (por ejemplo, después de un hook Stop): la entrada desaparece.
  - Las tareas en segundo plano de la sesión siguen en ejecución: no aparece nada hasta que terminen.
  - La respuesta la inició una programación (`/loop`, cron): no aparece nada.
- Las entradas desaparecen cuando respondes, cuando Claude continúa, cuando haces clic en ellas o (solo las amarillas)
  después de 60 minutos.
- Interfaz en alemán, inglés, francés, italiano y español (sigue el idioma de visualización de VS Code).
- Todo se queda en tu equipo. Sin acceso a la red, sin telemetría.

## Cómo funciona

```
Sesión de Claude Code ──hook──▶ ~/.local/state/session-guard/sessions/<id>.json ──▶ extensión de VS Code ──▶ barra de estado
                                                                         ▲
                           historial de la sesión (~/.claude/projects/…) ┘  "¿sigue esperando?"
```

El repositorio tiene dos partes:

| Parte | Qué hace |
|---|---|
| **Plugin de Claude Code** (`hooks/`) | Un hook en `Stop`, `PreToolUse` (AskUserQuestion) y `Notification` escribe un pequeño archivo de estado JSON por sesión y reproduce el sonido de las preguntas. |
| **Extensión de VS Code** (`vscode/`) | Lee los archivos de estado cada dos segundos, comprueba en el historial de la sesión si la sesión sigue esperando y muestra las entradas en la barra de estado. |

## Requisitos

- Claude Code con soporte para plugins, usado en la extensión de VS Code
- VS Code 1.90 o posterior
- Python 3.9 o posterior como `python3` en tu `PATH` (el hook solo usa la biblioteca estándar)
- macOS o Linux. **Windows:** usa la [rama `windows`](https://github.com/simon-says-labs/session-guard/tree/windows).

## Instalación

### 1. Plugin de Claude Code (el hook)

En una sesión de Claude Code:

```
/plugin marketplace add simon-says-labs/session-guard
/plugin install session-guard@simon-says
```

### 2. Extensión de VS Code

Descarga `session-guard-<version>.vsix` de la
[última versión publicada](https://github.com/simon-says-labs/session-guard/releases/latest) y ejecuta:

```bash
code --install-extension session-guard-0.3.0.vsix
```

Si usas [perfiles de VS Code](https://code.visualstudio.com/docs/configure/profiles), instala la extensión en cada
perfil en el que trabajes, por ejemplo con `--profile Work`. Sin `--profile`, la extensión solo se instala en el
perfil predeterminado.

Después, recarga la ventana de VS Code (**Developer: Reload Window**, disponible en la paleta de comandos). Esto
también reinicia las sesiones de Claude Code de esa ventana: Claude Code solo carga un plugin recién instalado o
actualizado al iniciar una sesión, así que hasta entonces las sesiones en curso mantienen los hooks antiguos (o
ninguno).

## Configuración

| Variable de entorno | Efecto |
|---|---|
| `SESSION_GUARD_SOUND=off` | Ningún sonido |
| `SESSION_GUARD_STATE=/ruta` | Otra carpeta de estado (configúrala para Claude Code **y** para VS Code) |

Cada evento se registra con `sound=yes|no` en `~/.local/state/session-guard/session-guard.log`, así puedes comprobar
por qué sonó o no sonó un aviso.

## Limitaciones

Léelas antes de confiar en la extensión:

- **Comandos internos.** El clic usa comandos internos de la extensión de Claude Code para VS Code
  (`claude-vscode.sidebar.open` y `claude-vscode.editor.open`), comprobados por última vez con la versión 2.1.288. No
  son una API pública y pueden cambiar. Si fallan, Session Guard recurre a la URI documentada
  `vscode://anthropic.claude-code/open?session=<id>`, que puede abrir la sesión en una pestaña nueva.
- **Formato del historial de sesión.** Si una sesión sigue esperando se lee de los historiales de sesión de
  Claude Code. Su formato no está documentado oficialmente.
- **Ajuste de la barra lateral.** Al hacer clic en una entrada, la ubicación preferida de la extensión de Claude Code
  se establece en la barra lateral (`claudeCode.preferredLocation`).
- **Windows** tiene su propia [rama `windows`](https://github.com/simon-says-labs/session-guard/tree/windows) (hook
  mediante `python`, sonido mediante `winsound`, estado en `%LOCALAPPDATA%`). Esta rama llama a `python3` y solo
  reproduce el sonido de las preguntas en macOS (`afplay`) y Linux (`paplay`).
- **Historiales grandes.** El hook lee el historial una vez por evento. Con historiales de 40 a 60 MB, esto tarda
  unos 0,75 s en un Apple M4 Pro.

## Desinstalación

```
/plugin uninstall session-guard@simon-says
code --uninstall-extension simon-says-labs.session-guard
```

Después puedes eliminar la carpeta de estado `~/.local/state/session-guard`.

## Desarrollo

```bash
python3 -m unittest discover -s tests/python   # hook
node --test tests/node/*.test.js               # extensión
python3 vscode/build_vsix.py                   # escribe dist/session-guard-<version>.vsix
claude plugin validate .                       # manifiestos del plugin y del marketplace
```

La extensión no tiene dependencias de npm y no necesita ningún paso de compilación. Consulta
[CONTRIBUTING.md](../CONTRIBUTING.md).

## Licencia

[MIT](../LICENSE) © 2026 Simon Eckmiller · publicado por [Simon Says](https://github.com/simon-says-labs)

Este es un proyecto comunitario independiente. No está afiliado a Anthropic ni cuenta con su respaldo.

<p align="right"><a href="#session-guard">↑</a></p>
