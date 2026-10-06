// Session Guard: one coloured status bar entry per Claude Code session that is waiting for you.
// Red = approval or question, yellow = turn finished. A click opens the session and dismisses the entry.
//
// Copyright (c) 2026 Simon Eckmiller. MIT License.
"use strict";
const vscode = require("vscode");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { waitingSessions, markSeen, label, waitTime, stateRoot } = require("./logic");

const FOLDER = path.join(stateRoot(process.platform, process.env, os.homedir()), "sessions");
const POLL_MS = 2000;
const t = (message, ...args) => vscode.l10n.t(message, ...args);

let items = []; // status bar items in display order
let signature = "";

function tooltip(s) {
  const md = new vscode.MarkdownString();
  md.appendMarkdown("**");
  md.appendText(s.title);
  md.appendMarkdown("**  \n");
  md.appendText(`${label(s, t).word} · ${waitTime(s, Date.now(), t)}`);
  if (s.text) {
    md.appendMarkdown("\n\n> ");
    md.appendText(s.text);
  }
  md.appendMarkdown("\n\n_");
  md.appendText(t("Click: switch to this chat and dismiss"));
  md.appendMarkdown("_");
  return md;
}

function refresh() {
  const list = waitingSessions(FOLDER);
  const next = list.map((s) => s.session_id + ":" + s.reason).join("|");
  if (next !== signature) {
    // An item's priority cannot change after creation, so a new order means new items.
    items.forEach((item) => item.dispose());
    items = list.map((s, i) =>
      vscode.window.createStatusBarItem("sessionGuard." + i, vscode.StatusBarAlignment.Left, 1000 - i)
    );
    signature = next;
  }
  list.forEach((s, i) => {
    const item = items[i];
    const l = label(s, t);
    item.name = "Session Guard";
    item.text = l.text;
    item.backgroundColor = new vscode.ThemeColor(l.color);
    item.tooltip = tooltip(s);
    item.command = { command: "sessionGuard.open", title: t("Open chat"), arguments: [s.session_id] };
    item.show();
  });
}

async function openSession(sessionId) {
  markSeen(FOLDER, sessionId);
  refresh();
  // Load the session into the Claude Code side bar instead of opening a second chat tab.
  // These are internal commands of the Claude Code extension (read in version 2.1.288):
  // `sidebar.open` makes the side bar the preferred location, `editor.open` with
  // `programmatic: "honor-preferred-location"` then loads the session there. If they are
  // missing, fall back to the documented URI handler.
  try {
    await vscode.commands.executeCommand("claude-vscode.sidebar.open");
    await vscode.commands.executeCommand("claude-vscode.editor.open", sessionId, undefined, undefined, undefined,
      undefined, { programmatic: "honor-preferred-location" });
  } catch {
    await vscode.env.openExternal(
      vscode.Uri.parse("vscode://anthropic.claude-code/open?session=" + encodeURIComponent(sessionId))
    );
  }
}

function safeRefresh() {
  try {
    refresh();
  } catch (error) {
    console.error("Session Guard:", error);
  }
}

function activate(context) {
  context.subscriptions.push(vscode.commands.registerCommand("sessionGuard.open", openSession));
  const timer = setInterval(safeRefresh, POLL_MS);
  context.subscriptions.push({ dispose: () => clearInterval(timer) });
  try {
    fs.mkdirSync(FOLDER, { recursive: true });
    const watcher = fs.watch(FOLDER, safeRefresh);
    context.subscriptions.push({ dispose: () => watcher.close() });
  } catch {
    // polling is enough without fs.watch
  }
  context.subscriptions.push({ dispose: () => items.forEach((item) => item.dispose()) });
  safeRefresh();
}

function deactivate() {}

module.exports = { activate, deactivate };
