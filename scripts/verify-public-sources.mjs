#!/usr/bin/env node
/**
 * Ensure the static Pages reader uses one existing Markdown source per
 * player-facing document. This is a structural guard, not a live deployment
 * or browser rendering test.
 */
import fs from "node:fs";
import path from "node:path";

const fail = (message) => {
  console.error("PAGES CONTENT ERROR:", message);
  process.exitCode = 1;
};
const root = path.resolve(import.meta.dirname, "..");
const file = (p) => path.resolve(root, p);
const read = (p) => fs.readFileSync(file(p), "utf8");

for (const required of [".nojekyll", "index.html", "assets/site.css", "assets/site.js"]) {
  if (!fs.existsSync(file(required))) fail("Missing web asset: " + required);
}

const js = read("assets/site.js");
const html = read("index.html");
const starts = js.indexOf("const SECTIONS = [");
const ends = js.indexOf("const ALL =", starts);
if (starts < 0 || ends < 0 || ends <= starts) {
  fail("Cannot locate Pages navigation manifest (SECTIONS)");
  process.exit(1);
}
const section = js.slice(starts, ends);
const publicDocs = Array.from(section.matchAll(/path:\s*["']([^"']+\.md)["']/g), m => m[1]);
if (!publicDocs.length) fail("Pages navigation has no player-facing articles");

const seen = new Set();
for (const p of publicDocs) {
  if (seen.has(p)) fail("Duplicate Pages source: " + p);
  seen.add(p);
  if (!/^(docs|players|adventures)\//.test(p) && p !== "DECISIONS.md") {
    fail("Non-player document in Pages nav: " + p);
  }
  if (p.includes("..") || path.isAbsolute(p)) fail("Unsafe Pages source: " + p);
  if (!fs.existsSync(file(p))) {
    fail("Pages navigation points to missing Markdown file: " + p);
    continue;
  }
  if (!read(p).trim().startsWith("#")) fail("Markdown article missing heading: " + p);
}

if (!/fetch\(new URL\(path,\s*document\.baseURI\)/.test(js)) {
  fail("Pages reader no longer fetches the declared Markdown path directly");
}
if (!html.includes('src="assets/site.js"') || !html.includes('id="article-content"')) {
  fail("Reader not mounted in index.html");
}

if (!process.exitCode) console.log(
  "Verified " + publicDocs.length +
  " player-facing Markdown sources. Pages reads each from its original file."
);
