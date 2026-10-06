// Every user-visible string must have a German translation. Run: node --test tests/node/
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "../../vscode");
const read = (name) => fs.readFileSync(path.join(root, name), "utf8");

test("all t(...) strings and reason words exist in bundle.l10n.de.json", () => {
  const german = JSON.parse(read("l10n/bundle.l10n.de.json"));
  const source = read("logic.js") + read("extension.js");
  const used = new Set();
  for (const m of source.matchAll(/\bt\("((?:[^"\\]|\\.)*)"/g)) used.add(m[1]);
  for (const m of read("logic.js").matchAll(/word: "([^"]+)"/g)) used.add(m[1]);
  assert.ok(used.size >= 8, `found only ${used.size} strings`);
  const missing = [...used].filter((s) => !(s in german));
  assert.deepEqual(missing, []);
});

test("package.nls.json and package.nls.de.json have the same keys as package.json uses", () => {
  const pkg = read("package.json");
  const keys = [...pkg.matchAll(/"%([^%]+)%"/g)].map((m) => m[1]).sort();
  for (const file of ["package.nls.json", "package.nls.de.json"]) {
    assert.deepEqual(Object.keys(JSON.parse(read(file))).sort(), keys, file);
  }
});
