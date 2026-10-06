#!/usr/bin/env python3
"""Session Guard hook: records which Claude Code session is waiting for you.

Registered by hooks/hooks.json for these events:

    Stop                         -> the turn ended; the session waits for input ("done")
    PreToolUse AskUserQuestion   -> Claude asks you a question ("question")
    Notification                 -> permission_prompt ("approval"), elicitation_* and
                                    agent_needs_input ("question")

For every session it writes <state>/sessions/<session_id>.json, which the VS Code
extension in vscode/ turns into a status bar entry. The extension decides from the
session transcript whether the session is still waiting.

A sound is played only when you are asked a question. Approvals and finished turns
show up silently in the status bar. A finished turn is not reported at all when it
was started by a schedule (turnOrigin "scheduled") or when background tasks of the
session are still running.

The hook must never block Claude Code: every error ends with exit code 0.
Works with Python 3.9+, standard library only.

Environment:
    SESSION_GUARD_STATE   state directory (default: ~/.local/state/session-guard)
    SESSION_GUARD_SOUND   "off" disables the sound

Copyright (c) 2026 Simon Eckmiller. MIT License.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time

# event type -> (reason shown in the status bar, sound)
EVENTS = {
    "Stop": ("done", None),
    "AskUserQuestion": ("question", "question"),
    "permission_prompt": ("approval", None),
    "elicitation_dialog": ("question", "question"),
    "elicitation_url_dialog": ("question", "question"),
    "agent_needs_input": ("question", "question"),
}

# At most one sound per session within this many seconds. VS Code sends a
# permission_prompt about six seconds after an AskUserQuestion dialog opens.
DEDUP_SECONDS = 20

# Background tasks: started according to a tool result, finished according to a
# <task-notification> or a TaskStop result.
STARTED = [re.compile(r"running in background with ID: ([A-Za-z0-9_-]+)"),
           re.compile(r"moved to the background \(ID: ([A-Za-z0-9_-]+)\)")]
FINISHED = [re.compile(r"<task-id>([A-Za-z0-9_-]+)</task-id>"),
            re.compile(r"stopped task: ([A-Za-z0-9_-]+)")]

SOUNDS = {
    "darwin": ["afplay", "/System/Library/Sounds/Funk.aiff"],
    "linux": ["paplay", "/usr/share/sounds/freedesktop/stereo/message.oga"],
}


def state_dir():
    return os.environ.get("SESSION_GUARD_STATE") or os.path.expanduser("~/.local/state/session-guard")


def safe_id(session_id):
    return re.sub(r"[^A-Za-z0-9-]", "", session_id or "") or "no-id"


def session_title(transcript, cwd):
    """The title shown in Claude Code's session list, else the folder name."""
    ai_title = custom_title = ""
    try:
        with open(transcript, encoding="utf-8", errors="replace") as f:
            for line in f:
                if '"title' not in line and 'Title"' not in line:
                    continue
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if entry.get("type") == "custom-title" and entry.get("customTitle"):
                    custom_title = entry["customTitle"]
                elif entry.get("type") == "ai-title" and entry.get("aiTitle"):
                    ai_title = entry["aiTitle"]
    except (OSError, TypeError):
        pass
    return custom_title or ai_title or os.path.basename((cwd or "").rstrip("/")) or "Claude"


def first_line(text):
    for line in (text or "").splitlines():
        line = re.sub(r"[#*`>|_]+", "", line).strip()
        if line:
            return line[:140]
    return ""


def transcript_state(transcript):
    """(open background task ids, origin of the last turn) in a single pass.

    The origin is the turnOrigin of the last prompt: human, scheduled, task_notification or peer.
    """
    started, finished, origin = set(), set(), ""
    try:
        with open(transcript, encoding="utf-8", errors="replace") as f:
            for line in f:
                if "background" in line:
                    for pattern in STARTED:
                        started.update(pattern.findall(line))
                if "<task-id>" in line or "stopped task" in line:
                    for pattern in FINISHED:
                        finished.update(pattern.findall(line))
                if '"turnOrigin"' in line:
                    try:
                        origin = json.loads(line).get("turnOrigin") or origin
                    except ValueError:
                        pass
    except (OSError, TypeError):
        return set(), ""
    return started - finished, origin


def status_path(session_id):
    return os.path.join(state_dir(), "sessions", safe_id(session_id) + ".json")


def write_status(event, reason, title, text):
    path = status_path(event.get("session_id"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        size = os.path.getsize(event.get("transcript_path") or "")
    except OSError:
        size = 0
    data = {
        "session_id": event.get("session_id") or "no-id",
        "reason": reason,
        "title": title,
        "text": text,
        "time": time.time(),
        "cwd": event.get("cwd") or "",
        "transcript_path": event.get("transcript_path") or "",
        "transcript_size": size,
    }
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    os.replace(tmp, path)


def duplicate_approval(event, kind):
    """permission_prompt that VS Code sends after an AskUserQuestion dialog.

    It must not overwrite the question, otherwise the status bar would show the generic
    "Claude needs your permission" instead of the actual question.
    """
    if kind != "permission_prompt":
        return False
    try:
        with open(status_path(event.get("session_id")), encoding="utf-8") as f:
            old = json.load(f)
    except (OSError, ValueError):
        return False
    return old.get("reason") == "question" and time.time() - old.get("time", 0) < DEDUP_SECONDS


def recently_sounded(session_id):
    folder = os.path.join(state_dir(), "dedup")
    os.makedirs(folder, exist_ok=True)
    marker = os.path.join(folder, safe_id(session_id))
    now = time.time()
    try:
        if now - os.path.getmtime(marker) < DEDUP_SECONDS:
            return True
    except OSError:
        pass
    with open(marker, "w") as f:
        f.write(str(now))
    return False


def play_sound():
    if os.environ.get("SESSION_GUARD_SOUND", "").lower() == "off":
        return
    command = SOUNDS.get(sys.platform)
    if not command or not shutil.which(command[0]) or not os.path.exists(command[1]):
        return
    subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def log(kind, line, sound):
    """One line per event, so you can check whether the hook fired and whether it played a sound."""
    folder = state_dir()
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, "session-guard.log"), "a", encoding="utf-8") as f:
        f.write("%s\t%s\t%s\tsound=%s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), kind, line,
                                            "yes" if sound else "no"))


def main():
    event = json.load(sys.stdin)
    name = event.get("hook_event_name", "")
    if name == "Stop":
        kind, text = "Stop", first_line(event.get("last_assistant_message"))
    elif name == "PreToolUse":
        kind = event.get("tool_name", "")
        questions = (event.get("tool_input") or {}).get("questions") or [{}]
        text = first_line(questions[0].get("question", ""))
    else:
        kind, text = event.get("notification_type", ""), first_line(event.get("message"))
    if kind not in EVENTS:
        return
    reason, sound = EVENTS[kind]
    title = session_title(event.get("transcript_path"), event.get("cwd"))

    if kind == "Stop":
        open_tasks, origin = transcript_state(event.get("transcript_path"))
        if origin == "scheduled":
            write_status(event, "scheduled", title, text)
            log(kind, "%s · scheduled run" % title, False)
        elif open_tasks:
            write_status(event, "working", title, text)
            log(kind, "%s · background tasks running (%s)" % (title, ", ".join(sorted(open_tasks))), False)
        else:
            write_status(event, reason, title, text)
            log(kind, "%s · %s · %s" % (title, reason, text), False)
        return

    if duplicate_approval(event, kind):
        return
    write_status(event, reason, title, text)
    if recently_sounded(event.get("session_id")):
        return
    if sound:
        play_sound()
    log(kind, "%s · %s · %s" % (title, reason, text), bool(sound))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
