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

// The AI reading guide is deliberately limited to the same curated Markdown
// as the visible player menu, not every file served by the public repository.
const guidePath = "llms.txt";
if (!fs.existsSync(file(guidePath))) {
  fail("Missing player-facing AI guide");
} else {
  const guide = read(guidePath);
  const guideRoot = "https://makeinu1.github.io/DaD_Ruosuen/";
  const urls = Array.from(guide.matchAll(/^\s*- \[[^\]]+\]\(([^)]+)\)/gm), m => m[1]);
  const expected = [guideRoot, ...publicDocs.map(p => guideRoot + p.split("/").map(encodeURIComponent).join("/"))];
  if (JSON.stringify(urls) !== JSON.stringify(expected)) fail("llms.txt links must match the current Pages homepage and curated Markdown in order");
  if (!html.includes('name="ai-content-policy"') || !html.includes('href="llms.txt"')) fail("Pages is missing the AI guide discovery metadata");
}

// Story artwork is part of the published source, not a separately maintained copy.
for (const p of publicDocs) {
  if (!fs.existsSync(file(p))) continue;
  for (const match of read(p).matchAll(/!\[[^\]]*\]\(([^)]+)\)/g)) {
    const imagePath = path.resolve(path.dirname(file(p)), match[1]);
    if (!imagePath.startsWith(file("assets") + path.sep) || !fs.existsSync(imagePath)) {
      fail("Missing or unsafe article artwork in " + p + ": " + match[1]);
    }
  }
}
for (const match of html.matchAll(/<img[^>]+src="(assets\/[^"?#]+)"/g)) {
  if (!fs.existsSync(file(match[1]))) fail("Missing film artwork: " + match[1]);
}

// Verify that both responsive derivatives exist, retain their original
// counterpart, and actually reduce the bytes served.
const manifestPath = "assets/responsive/manifest.json";
if (fs.existsSync(file(manifestPath))) {
  const manifest = JSON.parse(read(manifestPath));
  const declared = js.match(/const RESPONSIVE_ART = (\{[\s\S]*?\});/);
  if (!declared || JSON.stringify(JSON.parse(declared[1])) !== JSON.stringify(manifest)) fail("Responsive artwork metadata diverges from the manifest");
  for (const name of Object.keys(manifest)) {
    const original = file("assets/" + name);
    if (!fs.existsSync(original)) { fail("Responsive artwork missing its original: " + name); continue; }
    for (const width of [800, 1200].filter(w => w < manifest[name][0])) {
      const derivative = file("assets/responsive/" + name.replace(/\.webp$/, "-" + width + ".webp"));
      if (!fs.existsSync(derivative)) fail("Missing responsive artwork: " + derivative);
      else if (fs.statSync(derivative).size >= fs.statSync(original).size) fail("Responsive artwork is not smaller: " + derivative);
    }
  }
  for (const match of html.matchAll(/(?:imagesrcset|srcset)="([^"]+)"/g)) {
    for (const candidate of match[1].split(",")) {
      const source = candidate.trim().split(/\s+/)[0];
      if (!fs.existsSync(file(source))) fail("Responsive HTML references a missing asset: " + source);
    }
  }
  for (const width of [800, 1200, 1672]) {
    if (!fs.existsSync(file("assets/ruosuen-first-adventure-" + width + ".webp"))) fail("Missing first adventure art: " + width);
  }
}
if (!/fetch\(new URL\(path,\s*document\.baseURI\)/.test(js)) {
  fail("Pages reader no longer fetches the declared Markdown path directly");
}
if (!/src="assets\/site\.js(?:\?[^"]*)?"/.test(html) || !html.includes('id="article-content"')) {
  fail("Reader not mounted in index.html");
}

if (!process.exitCode) console.log(
  "Verified " + publicDocs.length +
  " player-facing Markdown sources. Pages reads each from its original file."
);
