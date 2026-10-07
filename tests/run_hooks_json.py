#!/usr/bin/env python3
"""Runs every hook in hooks/hooks.json the way Claude Code starts it, and checks the status file.

Exec form (command + args) is spawned directly without a shell, shell form goes through `sh -c`
(Claude Code docs, "Exec form and shell form"). ${CLAUDE_PLUGIN_ROOT} is replaced as plain text.
Used in CI: main's hooks.json on macOS and Linux, the windows branch's hooks.json on Windows.

Copyright (c) 2026 Simon Eckmiller. MIT License.
"""
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVENT = {"hook_event_name": "PreToolUse", "tool_name": "AskUserQuestion", "session_id": "ci",
         "tool_input": {"questions": [{"question": "CI?"}]}}


def commands(hooks):
    for groups in hooks["hooks"].values():
        for group in groups:
            for hook in group["hooks"]:
                yield hook


def run(hook, env):
    sub = lambda s: s.replace("${CLAUDE_PLUGIN_ROOT}", ROOT)
    if "args" in hook:
        argv = [sub(hook["command"])] + [sub(a) for a in hook["args"]]
    else:
        argv = ["sh", "-c", sub(hook["command"])]
    return subprocess.run(argv, input=json.dumps(EVENT), text=True, env=env, timeout=hook.get("timeout", 10))


def main():
    with open(os.path.join(ROOT, "hooks", "hooks.json"), encoding="utf-8") as f:
        hooks = json.load(f)
    failures = 0
    for hook in commands(hooks):
        state = tempfile.mkdtemp()
        env = dict(os.environ, SESSION_GUARD_STATE=state, SESSION_GUARD_SOUND="off")
        result = run(hook, env)
        path = os.path.join(state, "sessions", "ci.json")
        ok = result.returncode == 0 and os.path.exists(path)
        reason = json.load(open(path, encoding="utf-8"))["reason"] if os.path.exists(path) else None
        ok = ok and reason == "question"
        print("%s  %s %s -> exit %s, reason %s" % ("ok  " if ok else "FAIL", hook["command"],
                                                   " ".join(hook.get("args", [])), result.returncode, reason))
        failures += not ok
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
