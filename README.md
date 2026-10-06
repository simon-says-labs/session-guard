# Session Guard

**See at a glance which Claude Code session needs you.**

You run several Claude Code chats side by side in VS Code. One asks a question, another
waits for an approval, a third has finished, and you only notice when you click through
all of them. Session Guard puts every session that is waiting for
you into the VS Code status bar, and plays a sound only when you are actually asked a
question.

![Status bar with one red and one yellow Session Guard entry](docs/screenshot.png)

*The status bar with a session waiting for approval (red) and a finished one (yellow), here with the German UI.*

![Illustration of all three entry types in English](docs/status-bar-illustration.png)

*All three entry types with the English UI: approval and question (red), finished turn (yellow).*

> **Kurz auf Deutsch:** Session Guard zeigt in der VS-Code-Statusleiste, welche
> Claude-Code-Sitzung auf dich wartet: rot bei Freigabe oder Frage, gelb, wenn eine Antwort
> fertig ist. Ein Klick wechselt in die Sitzung. Ein Ton kommt nur, wenn dir eine Frage
> gestellt wird. Die Oberfläche ist deutsch, wenn VS Code auf Deutsch läuft.

## Features

- **One entry per waiting session**, labelled with the session title from Claude Code's
  session list.
  - 🟥 **red**: Claude needs your approval or asks you a question
  - 🟨 **yellow**: Claude finished a turn you started
- **Click to switch**: loads that session into the Claude Code side bar and dismisses the
  entry. No second chat tab.
- **Hover** shows how long the session has been waiting and the question or last line.
- **Sound only for questions** (AskUserQuestion, MCP input dialogs, background sessions
  waiting for input). Approvals and finished turns stay silent.
- **No false alarms** from turns that are not really finished:
  - Claude continues on its own (for example after a Stop hook): the entry disappears.
  - Background tasks of the session are still running: nothing is shown until they finish.
  - The turn was started by a schedule (`/loop`, cron): nothing is shown.
- Entries disappear when you answer, when Claude continues, when you click them, or (yellow
  only) after 60 minutes.
- English and German UI.
- Everything stays on your machine. No network access, no telemetry.

## How it works

```
Claude Code session ──hook──▶ ~/.local/state/session-guard/sessions/<id>.json ──▶ VS Code extension ──▶ status bar
                                                                       ▲
                              session transcript (~/.claude/projects/…) ┘  "is it still waiting?"
```

The repository contains two parts:

| Part | What it does |
|---|---|
| **Claude Code plugin** (`hooks/`) | A hook on `Stop`, `PreToolUse` (AskUserQuestion) and `Notification` writes one small JSON status file per session and plays the question sound. |
| **VS Code extension** (`vscode/`) | Reads the status files every two seconds, checks the session transcript to see whether the session is still waiting, and shows the status bar entries. |

## Requirements

- Claude Code with plugin support, used in the VS Code extension
- VS Code 1.90 or later
- Python 3.9 or later as `python3` on your `PATH` (the hook uses the standard library only)
- macOS or Linux. Windows is untested (see [Limitations](#limitations)).

## Installation

### 1. Claude Code plugin (the hook)

In a Claude Code session:

```
/plugin marketplace add simon-says-labs/session-guard
/plugin install session-guard@simon-says
```

### 2. VS Code extension

Download `session-guard-<version>.vsix` from the
[latest release](https://github.com/simon-says-labs/session-guard/releases/latest) and run:

```bash
code --install-extension session-guard-0.2.0.vsix
```

If you use [VS Code profiles](https://code.visualstudio.com/docs/configure/profiles), install
it into each profile you work in, for example `--profile Work`. An extension installed without
`--profile` lands in the default profile only.

Reload the VS Code window afterwards (**Developer: Reload Window**).

## Configuration

| Environment variable | Effect |
|---|---|
| `SESSION_GUARD_SOUND=off` | No sound at all |
| `SESSION_GUARD_STATE=/path` | Different state directory (set it for Claude Code **and** VS Code) |

Every event is logged with `sound=yes|no` in `~/.local/state/session-guard/session-guard.log`,
so you can check why a sound was or was not played.

## Limitations

Please read these before you rely on the extension:

- **Internal commands.** The click uses internal commands of the Claude Code VS Code extension
  (`claude-vscode.sidebar.open` and `claude-vscode.editor.open`), last checked with version
  2.1.288. They are not a public API and may change. If they fail, Session Guard falls back to
  the documented URI `vscode://anthropic.claude-code/open?session=<id>`, which may open the
  session in a new tab instead.
- **Transcript format.** Whether a session is still waiting is read from Claude Code's session
  transcripts. Their format is not officially documented.
- **Side bar setting.** Clicking an entry sets the Claude Code extension's preferred location to
  the side bar (`claudeCode.preferredLocation`).
- **Windows** is untested. The hook calls `python3`, and the question sound is only implemented
  for macOS (`afplay`) and Linux (`paplay`).
- **Large transcripts.** The hook reads the transcript once per event. With transcripts of
  40 to 60 MB this takes about 0.75 s on an Apple M4 Pro.

## Uninstall

```
/plugin uninstall session-guard@simon-says
code --uninstall-extension simon-says-labs.session-guard
```

The state directory `~/.local/state/session-guard` can be removed afterwards.

## Development

```bash
python3 -m unittest discover -s tests/python   # hook
node --test tests/node/*.test.js                        # extension
python3 vscode/build_vsix.py                   # writes dist/session-guard-<version>.vsix
claude plugin validate .                       # plugin and marketplace manifests
```

The extension has no npm dependencies and needs no build step. See
[CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE) © 2026 Simon Eckmiller · published by [Simon Says](https://github.com/simon-says-labs)

This is an independent community project. It is not affiliated with or endorsed by Anthropic.
