// Tests for vscode/extension.js with a fake vscode module. Run: node --test tests/node/
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const Module = require("node:module");
const { format } = require("../../vscode/logic");

const state = fs.mkdtempSync(path.join(os.tmpdir(), "waechter-ext-"));
process.env.CLAUDE_WAECHTER_STATE = state;
const sessions = path.join(state, "sessions");
fs.mkdirSync(sessions, { recursive: true });

const german = JSON.parse(fs.readFileSync(path.join(__dirname, "../../vscode/l10n/bundle.l10n.de.json"), "utf8"));
let bundle = {}; // {} = English (source strings), german = German UI

const items = [];
const commands = {};
const calls = [];
const fakeVscode = {
  StatusBarAlignment: { Left: 1, Right: 2 },
  ThemeColor: class { constructor(id) { this.id = id; } },
  MarkdownString: class {
    constructor() { this.value = ""; }
    appendMarkdown(t) { this.value += t; return this; }
    appendText(t) { this.value += t.replace(/[*_>`\\[\]]/g, "\\$&"); return this; }
  },
  l10n: { t: (message, ...args) => format(bundle[message] ?? message, ...args) },
  Uri: { parse: (u) => ({ u }) },
  env: { openExternal: async (u) => calls.push(["external", u.u]) },
  window: {
    createStatusBarItem(id, alignment, priority) {
      const item = { id, alignment, priority, visible: false, disposed: false,
        show() { this.visible = true; }, dispose() { this.disposed = true; } };
      items.push(item);
      return item;
    },
  },
  commands: {
    registerCommand(name, fn) { commands[name] = fn; return { dispose() {} }; },
    async executeCommand(name, ...args) { calls.push([name, ...args]); },
  },
};
const originalLoad = Module._load;
Module._load = function (request, ...rest) {
  return request === "vscode" ? fakeVscode : originalLoad.call(this, request, ...rest);
};
const extension = require("../../vscode/extension");

function writeStatus(id, reason, title, text) {
  fs.writeFileSync(path.join(sessions, id + ".json"), JSON.stringify({
    session_id: id, reason, title, text, time: Date.now() / 1000 - 120,
    cwd: "/x", transcript_path: "", transcript_size: 0 }));
}

const visible = () => items.filter((item) => !item.disposed && item.visible);

test("two waiting sessions give two entries, red before yellow; click loads the side bar and dismisses", async (t) => {
  writeStatus("s-yellow", "done", "Write release notes", "Notes are ready");
  writeStatus("s-red", "approval", "Refactor billing", "May I run *deploy.sh*?");
  const context = { subscriptions: [] };
  extension.activate(context);
  t.after(() => context.subscriptions.forEach((s) => s.dispose())); // stop the timer even on failure

  const shown = visible();
  assert.equal(shown.length, 2);
  assert.equal(shown[0].text, "$(alert) Refactor billing · needs approval");
  assert.equal(shown[0].backgroundColor.id, "statusBarItem.errorBackground");
  assert.ok(shown[0].priority > shown[1].priority, "red is further left");
  assert.equal(shown[1].text, "$(check) Write release notes · done");
  assert.match(shown[0].tooltip.value, /2 min ago/);
  assert.match(shown[0].tooltip.value, /\\\*deploy\.sh\\\*/, "user text is not rendered as markdown");

  await commands[shown[0].command.command](...shown[0].command.arguments);
  assert.deepEqual(calls.slice(-2), [
    ["claude-vscode.sidebar.open"],
    ["claude-vscode.editor.open", "s-red", undefined, undefined, undefined, undefined, { programmatic: "honor-preferred-location" }],
  ]);
  assert.equal(typeof JSON.parse(fs.readFileSync(path.join(sessions, "s-red.json"), "utf8")).seen, "number");
  assert.deepEqual(visible().map((item) => item.text), ["$(check) Write release notes · done"]);
});

test("German UI when VS Code runs in German", (t) => {
  bundle = german;
  t.after(() => { bundle = {}; });
  writeStatus("s-de", "question", "Frage", "C520 oder C620?");
  const context = { subscriptions: [] };
  extension.activate(context);
  t.after(() => context.subscriptions.forEach((s) => s.dispose()));
  const texts = visible().map((item) => item.text);
  assert.ok(texts.includes("$(question) Frage · fragt dich"), texts.join(" | "));
  assert.ok(texts.includes("$(check) Write release notes · fertig"), texts.join(" | "));
  assert.match(visible()[0].tooltip.value, /seit 2 min/);
});

test("click falls back to the documented URI when the internal command is missing", async () => {
  const real = fakeVscode.commands.executeCommand;
  fakeVscode.commands.executeCommand = async () => { throw new Error("command not found"); };
  await commands["claudeWaechter.open"]("abc-123");
  fakeVscode.commands.executeCommand = real;
  assert.deepEqual(calls.at(-1), ["external", "vscode://anthropic.claude-code/open?session=abc-123"]);
});
