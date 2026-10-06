// Tests for vscode/logic.js. Run: node --test tests/node/
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { waitingSessions, markSeen, label, waitTime, format, MAX_AGE_HOURS, DONE_MAX_AGE_MINUTES } = require("../../vscode/logic");

const NOW = Date.parse("2026-10-05T15:00:00Z");
const EVENT_S = (NOW - 60_000) / 1000; // event one minute ago

function folder() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "waechter-"));
}

function line(type, timeMs) {
  return JSON.stringify({ type, timestamp: new Date(timeMs).toISOString() }) + "\n";
}

// Writes transcript + status file. `after` are entries written AFTER the event.
function session(dir, id, reason, timeS, before, after, extra = {}) {
  const transcript = path.join(dir, id + ".jsonl");
  fs.writeFileSync(transcript, before.join(""));
  const size = fs.statSync(transcript).size;
  fs.appendFileSync(transcript, after.join(""));
  const status = { session_id: id, reason, title: "Title " + id, text: "Text " + id, time: timeS,
    cwd: "/x", transcript_path: transcript, transcript_size: size, ...extra };
  fs.writeFileSync(path.join(dir, id + ".json"), JSON.stringify(status));
  return status;
}

const ids = (list) => list.map((s) => s.session_id);

test("Stop followed only by a system entry: still waiting", () => {
  const d = folder();
  session(d, "a", "done", EVENT_S, [line("assistant", NOW - 61_000)], [line("system", NOW - 59_900)]);
  assert.deepEqual(ids(waitingSessions(d, NOW)), ["a"]);
});

test("new user entry after the event: no longer waiting", () => {
  const d = folder();
  session(d, "b", "done", EVENT_S, [], [line("user", NOW - 30_000)]);
  assert.deepEqual(waitingSessions(d, NOW), []);
});

test("Claude continues after an approval: no longer waiting", () => {
  const d = folder();
  session(d, "c", "approval", EVENT_S, [], [line("assistant", NOW - 20_000)]);
  assert.deepEqual(waitingSessions(d, NOW), []);
});

test("last answer written late but timestamped before the event: still waiting", () => {
  const d = folder();
  session(d, "e", "done", EVENT_S, [], [line("assistant", NOW - 60_500)]);
  assert.equal(waitingSessions(d, NOW).length, 1);
});

test("older than MAX_AGE_HOURS: hidden", () => {
  const d = folder();
  session(d, "f", "approval", (NOW - (MAX_AGE_HOURS + 1) * 3600_000) / 1000, [], []);
  assert.deepEqual(waitingSessions(d, NOW), []);
});

test("done entries disappear after DONE_MAX_AGE_MINUTES, red ones stay", () => {
  const d = folder();
  const old = (NOW - (DONE_MAX_AGE_MINUTES + 1) * 60_000) / 1000;
  session(d, "done-old", "done", old, [], []);
  session(d, "red-old", "approval", old, [], []);
  assert.deepEqual(ids(waitingSessions(d, NOW)), ["red-old"]);
});

test("transcript grew by more than the read window: no longer waiting", () => {
  const d = folder();
  const huge = JSON.stringify({ type: "user", timestamp: new Date(NOW).toISOString(), x: "y".repeat(600_000) }) + "\n";
  session(d, "g", "question", EVENT_S, [], [huge]);
  assert.deepEqual(waitingSessions(d, NOW), []);
});

test("missing transcript: still shown", () => {
  const d = folder();
  fs.writeFileSync(path.join(d, "h.json"), JSON.stringify({ session_id: "h", reason: "question", title: "T", text: "",
    time: EVENT_S, transcript_path: "/does/not/exist", transcript_size: 0 }));
  assert.equal(waitingSessions(d, NOW).length, 1);
});

test("unreadable transcript (a directory) does not break the list", () => {
  const d = folder();
  fs.writeFileSync(path.join(d, "k.json"), JSON.stringify({ session_id: "k", reason: "question", title: "K", text: "",
    time: EVENT_S, transcript_path: folder(), transcript_size: 0 }));
  session(d, "ok", "done", EVENT_S, [], []);
  assert.deepEqual(ids(waitingSessions(d, NOW)).sort(), ["k", "ok"]);
});

test("broken status files and foreign files are ignored", () => {
  const d = folder();
  fs.writeFileSync(path.join(d, "broken.json"), "{not json");
  fs.writeFileSync(path.join(d, "x.json.tmp"), "{}");
  session(d, "i", "done", EVENT_S, [], []);
  assert.deepEqual(ids(waitingSessions(d, NOW)), ["i"]);
});

test("reasons 'working' and 'scheduled' are not shown", () => {
  const d = folder();
  session(d, "bg", "working", EVENT_S, [], []);
  session(d, "cron", "scheduled", EVENT_S, [], []);
  assert.deepEqual(waitingSessions(d, NOW), []);
});

test("missing folder: empty list", () => {
  assert.deepEqual(waitingSessions("/does/not/exist/sessions", NOW), []);
});

test("order: red (approval/question) before yellow, oldest first", () => {
  const d = folder();
  session(d, "yellow", "done", EVENT_S - 100, [], []);
  session(d, "red-new", "question", EVENT_S, [], []);
  session(d, "red-old", "approval", EVENT_S - 50, [], []);
  assert.deepEqual(ids(waitingSessions(d, NOW)), ["red-old", "red-new", "yellow"]);
});

test("seen after the event: hidden; seen before a newer event: shown again", () => {
  const d = folder();
  session(d, "s1", "done", EVENT_S, [], [], { seen: EVENT_S + 10 });
  session(d, "s2", "question", EVENT_S, [], [], { seen: EVENT_S - 100 });
  assert.deepEqual(ids(waitingSessions(d, NOW)), ["s2"]);
});

test("markSeen writes the field and hides the entry", () => {
  const d = folder();
  session(d, "mk", "done", EVENT_S, [], []);
  markSeen(d, "mk", NOW);
  assert.equal(JSON.parse(fs.readFileSync(path.join(d, "mk.json"), "utf8")).seen, NOW / 1000);
  assert.deepEqual(waitingSessions(d, NOW), []);
});

test("label: icon, shortened title, reason, colour", () => {
  const l = label({ reason: "approval", title: "Migrate the billing service to v2" });
  assert.equal(l.text, "$(alert) Migrate the billing servic… · needs approval");
  assert.equal(l.color, "statusBarItem.errorBackground");
  assert.equal(label({ reason: "question", title: "Short" }).text, "$(question) Short · asks you");
  assert.equal(label({ reason: "done", title: "Short" }).color, "statusBarItem.warningBackground");
});

test("waitTime formats minutes and hours", () => {
  assert.equal(waitTime({ time: NOW / 1000 }, NOW), "just now");
  assert.equal(waitTime({ time: (NOW - 5 * 60_000) / 1000 }, NOW), "5 min ago");
  assert.equal(waitTime({ time: (NOW - 125 * 60_000) / 1000 }, NOW), "2 h 5 min ago");
});

test("format replaces placeholders like vscode.l10n.t", () => {
  assert.equal(format("{0} h {1} min ago", 2, 5), "2 h 5 min ago");
});
