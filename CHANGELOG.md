# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/).

## [0.4.0] - 2026-10-07

### Added
- Windows support in `main`: the hook keeps its state in `%LOCALAPPDATA%\session-guard` and plays the
  question sound with `winsound`; the extension reads the same folder. One VSIX now works on macOS, Linux
  and Windows.
- CI runs on Windows as well, and runs every hook from `hooks/hooks.json` the way Claude Code starts it
  (`tests/run_hooks_json.py`).
- The `windows` branch is now `main` plus one file, `hooks/hooks.json` (runs `python` without a shell).
  A CI job fails on that branch if anything else differs from `main`.

### Changed
- README (all five languages): Windows requirements, install path and why the plugin needs its own branch.

## [0.3.1] - 2026-10-06

### Added
- Extension icon, and links to the repository, the issue tracker and the README in the extension
  manifest, so the Marketplace and Open VSX pages show them.

### Fixed
- Images and links in the packaged README and CHANGELOG point to the repository. Relative paths
  were dead outside of GitHub.
- The install command in the README no longer names a fixed version.

## [0.3.0] - 2026-10-06

### Added
- French, Italian and Spanish user interface.

## [0.2.0] - 2026-10-06

First public release.

### Added
- Claude Code plugin with a hook on `Stop`, `PreToolUse` (AskUserQuestion) and `Notification`
  that writes one status file per session.
- VS Code extension that shows waiting sessions as red (approval, question) and yellow (done)
  status bar entries, with tooltip and click-to-switch.
- Sound only when you are asked a question (macOS and Linux).
- No entry for turns that continue on their own, sessions with running background tasks and
  scheduled turns.
- Click dismisses an entry; yellow entries expire after 60 minutes.
- English and German user interface.
- Plugin marketplace manifest, so the hook installs with `/plugin marketplace add`.

[0.3.1]: https://github.com/simon-says-labs/session-guard/releases/tag/v0.3.1
[0.3.0]: https://github.com/simon-says-labs/session-guard/releases/tag/v0.3.0
[0.2.0]: https://github.com/simon-says-labs/session-guard/releases/tag/v0.2.0
