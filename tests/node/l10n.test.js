// Every user-visible string must be translated into every supported language. Run: node --test tests/node/*.test.js
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "../../vscode");
const read = (name) => fs.readFileSync(path.join(root, name), "utf8");
const LANGUAGES = ["de", "fr", "it", "es"];

function usedStrings() {
  const source = read("logic.js") + read("extension.js");
  const used = new Set();
  for (const m of source.matchAll(/\bt\("((?:[^"\\]|\\.)*)"/g)) used.add(m[1]);
  for (const m of read("logic.js").matchAll(/word: "([^"]+)"/g)) used.add(m[1]);
  return used;
}

for (const lang of LANGUAGES) {
  test(`bundle.l10n.${lang}.json translates every t(...) string and reason word`, () => {
    const bundle = JSON.parse(read(`l10n/bundle.l10n.${lang}.json`));
    const used = usedStrings();
    assert.ok(used.size >= 8, `found only ${used.size} strings`);
    assert.deepEqual([...used].filter((s) => !(s in bundle)), []);
    for (const [source, translated] of Object.entries(bundle)) {
      const placeholders = (s) => (s.match(/\{\d+\}/g) || []).sort().join();
      assert.equal(placeholders(translated), placeholders(source), `placeholders differ in "${source}"`);
      assert.notEqual(translated.trim(), "", `empty translation for "${source}"`);
    }
  });
}

test("every package.nls file has the keys package.json uses", () => {
  const keys = [...read("package.json").matchAll(/"%([^%]+)%"/g)].map((m) => m[1]).sort();
  for (const file of ["package.nls.json", ...LANGUAGES.map((l) => `package.nls.${l}.json`)]) {
    assert.deepEqual(Object.keys(JSON.parse(read(file))).sort(), keys, file);
  }
});
