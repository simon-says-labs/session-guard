# Contributing

Thanks for your interest in Session Guard. Bug reports, ideas and pull requests are welcome.

## Reporting a bug

Please open an [issue](https://github.com/simon-says-labs/session-guard/issues) and include:

- your operating system, VS Code version and Claude Code extension version
- what you expected and what happened
- the matching lines from `~/.local/state/session-guard/session-guard.log`
  (Windows: `%LOCALAPPDATA%\session-guard\session-guard.log`)

Do not paste session transcripts. They can contain your code and conversations.

## Development setup

No dependencies are needed beyond Python 3.9+ and Node.js 20+.

```bash
python3 -m unittest discover -s tests/python
node --test tests/node/*.test.js
python3 vscode/build_vsix.py
claude plugin validate .
```

To try your changes locally:

```
/plugin marketplace add /path/to/your/clone
/plugin install session-guard@simon-says
```

```bash
code --install-extension dist/session-guard-<version>.vsix
```

## Pull requests

- Keep changes focused. One topic per pull request.
- Add or update tests for every behaviour change. A test should fail without your change.
- Every user-visible string in the extension goes through `t(...)` and needs a translation in
  every `vscode/l10n/bundle.l10n.<lang>.json` (de, fr, it, es). The test suite checks this.
- The hook must never block Claude Code: it always exits with code 0 and uses the Python
  standard library only.
- Update `CHANGELOG.md` under an `Unreleased` heading.
