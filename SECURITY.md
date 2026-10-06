# Security policy

## Supported versions

Only the latest release receives fixes.

## Reporting a vulnerability

Please do **not** open a public issue for security problems. Use
[GitHub's private vulnerability reporting](https://github.com/simon-says-labs/claude-waechter/security/advisories/new)
instead.

## What the project does with your data

- The hook reads the session transcript that Claude Code passes to it and writes a small status
  file (session id, title, first line of the last message or question) to
  `~/.local/state/claude-waechter/`.
- The VS Code extension reads these status files and the transcripts they point to.
- Nothing is sent over the network. There is no telemetry.
