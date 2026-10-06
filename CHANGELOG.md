# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/).

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

[0.3.0]: https://github.com/simon-says-labs/session-guard/releases/tag/v0.3.0
[0.2.0]: https://github.com/simon-says-labs/session-guard/releases/tag/v0.2.0
