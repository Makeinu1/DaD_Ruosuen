#!/usr/bin/env node
// Synchronize release fingerprints whenever portal HTML, JS, CSS or public
// Markdown changes. No duplicate Markdown artifacts are generated.
import fs from 'node:fs';
import path from 'node:path';
const root = path.resolve(import.meta.dirname, '..');
const read = p => fs.readFileSync(path.join(root,p),'utf8');
const write = (p,text) => fs.writeFileSync(path.join(root,p),text);
function fingerprint(text) {
  let hash = 0xcbf29ce484222325n;
  for (let i = 0; i < text.length; i++) {
    hash = BigInt.asUintN(64, (hash ^ BigInt(text.charCodeAt(i))) * 0x100000001b3n);
  }
  return hash.toString(16).padStart(16, '0');
}
const assets = ["assets/site.css","assets/concept.css","assets/journey.css","assets/site.js","assets/scroll-story.mjs","assets/scroll-effects.mjs"];
const js = read('assets/site.js');
const sections = js.slice(js.indexOf('const SECTIONS = ['), js.indexOf('const ALL ='));
const docs = Array.from(sections.matchAll(/path:\s*["']([^"']+\.md)["']/g), m=>m[1]);
if (!docs.length || docs.some(p=>!/^(docs|players|adventures)\//.test(p) || p.includes('..'))) throw new Error('Invalid public sources');
const html = read('index.html');
const assetPattern = /((?:href|src)="assets\/(?:site\.css|concept\.css|journey\.css|site\.js|scroll-story\.mjs|scroll-effects\.mjs))(?:\?[^"]*)?(")/g;
const metaPattern = /(<meta name="ruosuen-release" content=")[^"]+(")/g;
if (!html.includes('name="ruosuen-release"')) throw new Error('Missing release metadata');
const canonical = html.replace(metaPattern, (_,a,b)=>a+'0000000000000000'+b).replace(assetPattern,'$1$2');
const hashes = Object.fromEntries(docs.map(p=>[p,fingerprint(read(p))]));
const version = fingerprint(JSON.stringify([['index.html',fingerprint(canonical)],...assets.map(p=>[p,fingerprint(read(p))]),...Object.entries(hashes)]));
const nextHtml = canonical.replace(metaPattern,(_,a,b)=>a+version+b).replace(assetPattern,(_,a,b)=>a+'?v='+version+b);
const manifest = JSON.stringify({version,docs:hashes},null,2)+'\n';
if (process.argv.includes('--check')) {
  if (nextHtml!==html || read('assets/reader-release.json')!==manifest) {
    console.error('Reader release is stale; run node scripts/sync-reader-release.mjs');
    process.exitCode=1;
  }
} else {
  write('index.html',nextHtml);
  write('assets/reader-release.json',manifest);
}
console.log('Reader release: '+version);
