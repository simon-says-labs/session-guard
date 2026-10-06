// Session Guard: pure logic without a vscode dependency, so it can be tested with `node --test`.
//
// Reads the status files written by hooks/session_guard_hook.py and decides from the session
// transcript whether a session is still waiting: as soon as a user or assistant entry appears
// after the event, you have answered or Claude is working again. After a Stop, Claude Code only
// appends a `system` entry (stop_hook_summary), so a quiet transcript means "still waiting".
//
// Copyright (c) 2026 Simon Eckmiller. MIT License.
"use strict";
const fs = require("node:fs");
const path = require("node:path");

const MAX_AGE_HOURS = 12; // older entries belong to forgotten sessions
const DONE_MAX_AGE_MINUTES = 60; // yellow "done" entries disappear after this time
const READ_WINDOW = 512 * 1024; // bytes of transcript read after the event
const GRACE_MS = 1500; // entries up to 1.5 s after the event still belong to it
const TITLE_MAX = 26;

const REASONS = {
  approval: { icon: "$(alert)", word: "needs approval", color: "statusBarItem.errorBackground", rank: 0 },
  question: { icon: "$(question)", word: "asks you", color: "statusBarItem.errorBackground", rank: 0 },
  done: { icon: "$(check)", word: "done", color: "statusBarItem.warningBackground", rank: 1 },
};

// Same placeholder syntax as vscode.l10n.t: "{0} min ago".
function format(message, ...args) {
  return message.replace(/\{(\d+)\}/g, (match, i) => (i < args.length ? String(args[i]) : match));
}

function stillWaiting(status) {
  const transcript = status.transcript_path;
  if (!transcript) return true;
  let size;
  try {
    size = fs.statSync(transcript).size;
  } catch {
    return true; // nothing to decide from; MAX_AGE_HOURS cleans up
  }
  const from = Math.max(0, (status.transcript_size || 0) - 4096);
  if (size - from > READ_WINDOW) return false; // that much new content means the session moved on
  if (size <= from) return true;
  const buffer = Buffer.alloc(size - from);
  const fd = fs.openSync(transcript, "r");
  try {
    fs.readSync(fd, buffer, 0, buffer.length, from);
  } finally {
    fs.closeSync(fd);
  }
  const limit = status.time * 1000 + GRACE_MS;
  for (const line of buffer.toString("utf8").split("\n")) {
    if (!line.includes('"timestamp"')) continue;
    let entry;
    try {
      entry = JSON.parse(line);
    } catch {
      continue; // first line may be cut off
    }
    if ((entry.type === "user" || entry.type === "assistant") && Date.parse(entry.timestamp) > limit) return false;
  }
  return true;
}

function waitingSessions(folder, nowMs = Date.now()) {
  let names;
  try {
    names = fs.readdirSync(folder);
  } catch {
    return [];
  }
  const list = [];
  for (const name of names) {
    if (!name.endsWith(".json")) continue;
    let s;
    try {
      s = JSON.parse(fs.readFileSync(path.join(folder, name), "utf8"));
    } catch {
      continue;
    }
    if (!REASONS[s.reason] || typeof s.time !== "number") continue;
    const ageMs = nowMs - s.time * 1000;
    if (ageMs > MAX_AGE_HOURS * 3600_000) continue;
    if (s.reason === "done" && ageMs > DONE_MAX_AGE_MINUTES * 60_000) continue;
    if (typeof s.seen === "number" && s.seen >= s.time) continue; // dismissed by a click
    let waiting = true; // unreadable transcript: better show the entry than lose the whole list
    try {
      waiting = stillWaiting(s);
    } catch {}
    if (waiting) list.push(s);
  }
  return list.sort((a, b) => REASONS[a.reason].rank - REASONS[b.reason].rank || a.time - b.time);
}

// Same file naming as safe_id() in hooks/session_guard_hook.py.
function statusFile(folder, sessionId) {
  return path.join(folder, (String(sessionId).replace(/[^A-Za-z0-9-]/g, "") || "no-id") + ".json");
}

// A click marks the entry as seen. A newer event of the same session shows it again.
function markSeen(folder, sessionId, nowMs = Date.now()) {
  const file = statusFile(folder, sessionId);
  try {
    const s = JSON.parse(fs.readFileSync(file, "utf8"));
    s.seen = nowMs / 1000;
    fs.writeFileSync(file + ".tmp", JSON.stringify(s));
    fs.renameSync(file + ".tmp", file);
  } catch {
    // file gone or broken: nothing to show either
  }
}

function label(s, t = format) {
  const reason = REASONS[s.reason];
  const title = s.title.length > TITLE_MAX ? s.title.slice(0, TITLE_MAX) + "…" : s.title;
  return { text: `${reason.icon} ${title} · ${t(reason.word)}`, color: reason.color, word: t(reason.word) };
}

function waitTime(s, nowMs = Date.now(), t = format) {
  const minutes = Math.max(0, Math.round((nowMs - s.time * 1000) / 60000));
  if (minutes < 1) return t("just now");
  if (minutes < 60) return t("{0} min ago", minutes);
  return t("{0} h {1} min ago", Math.floor(minutes / 60), minutes % 60);
}

module.exports = { waitingSessions, stillWaiting, markSeen, label, waitTime, format, MAX_AGE_HOURS, DONE_MAX_AGE_MINUTES };
