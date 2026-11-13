"use strict";

/*
 * Ruosuen player portal.
 * Markdown in this GitHub repository is the single source of truth.
 * The reader is intentionally dependency-free and only renders a small,
 * safe Markdown subset needed by these documents.
 */
const SECTIONS = [
  {
    label: "まずはこちら",
    entries: [
      { path: "docs/01_プレイヤー向け世界観.md", label: "ルオスエンの世界", kicker: "WORLD / 01", summary: "地下へ広がる世界と冒険者たちの物語" },
      { path: "players/キャラクター作成ガイド.md", label: "キャラクター作成", kicker: "PLAYER / 01", summary: "4人の冒険に参加するためのPC作成案内" },
      { path: "players/キャラクター提出テンプレート.md", label: "キャラクター提出", kicker: "PLAYER / 02", summary: "自分のキャラクター像を書き出す" }
    ]
  },
  {
    label: "世界を知る",
    entries: [
      { path: "docs/02_迷宮と探索.md", label: "迷宮と探索", kicker: "WORLD / 02", summary: "未踏の通路、領域主、描きかけの地図" },
      { path: "docs/03_魔石と魔術.md", label: "魔石と魔術", kicker: "WORLD / 03", summary: "文明を動かすマナと魔石" },
      { path: "docs/04_自由迷宮都市と組織.md", label: "自由迷宮都市と組織", kicker: "WORLD / 04", summary: "五大国、ギルド、商人、探索者" },
      { path: "docs/08_街角の風景.md", label: "街角の風景", kicker: "ART / 01", summary: "市場、酒場、荷役場、夜の橋。四つの画風で見る自由都市" },
      { path: "docs/05_歴史と伝承.md", label: "歴史と伝承", kicker: "WORLD / 05", summary: "過去の繁栄、変わりゆく大地、不確かな噂" },
      { path: "docs/06_種族と信仰.md", label: "種族と信仰", kicker: "WORLD / 06", summary: "この世界で生きる人々と信念" }
    ]
  },
  {
    label: "冒険に参加する",
    entries: [
      { path: "docs/07_短編セッションの進め方.md", label: "冒険の進め方", kicker: "PLAY / 01", summary: "1〜2回で完結する短編の冒険" },
      { path: "players/探索パーティ結成.md", label: "パーティー結成", kicker: "PLAY / 02", summary: "4人が共に冒険する理由を作ろう" },
      { path: "players/characters/README.md", label: "PC登録について", kicker: "PLAY / 03", summary: "キャラクター設定の共有方法" },
      { path: "adventures/README.md", label: "冒険の記録", kicker: "PLAY / 04", summary: "これから増えていく冒険の足跡" }
    ]
  },
  {
    label: "参加前の確認",
    entries: [
      { path: "DECISIONS.md", label: "決定事項と未決事項", kicker: "SYSTEM / 01", summary: "開始レベルや種族など、まだ決まっていないこと" }
    ]
  }
];
const ALL = SECTIONS.flatMap(section => section.entries.map(item => ({...item, group: section.label})));
const BY_PATH = new Map(ALL.map(item => [item.path, item]));
const $ = id => document.getElementById(id);

function docUrl(path) { return "#/" + encodeURIComponent(path); }
function escapeHtml(value) {
  return String(value).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")
    .replace(/"/g,"&quot;").replace(/'/g,"&#39;");
}
function safeUrl(url, sourcePath) {
  const raw = url.replace(/&amp;/g,"&").trim();
  if (/^https?:\/\//i.test(raw)) return {href: raw, external: true};
  if (/^mailto:/i.test(raw)) return {href: raw, external: true};
  if (/^#/.test(raw)) return {href: raw, external: false};
  if (/^(javascript:|data:|vbscript:|\/\/)/i.test(raw)) return null;
  try {
    const link = new URL(raw, new URL(sourcePath, document.baseURI));
    const base = new URL(".", document.baseURI);
    const file = decodeURIComponent(link.pathname).slice(decodeURIComponent(base.pathname).length);
    if (link.origin === base.origin && BY_PATH.has(file)) return {href: docUrl(file), external: false};
  } catch (_) { /* invalid URL, omit link */ }
  return null;
}
function inlineMarkdown(value, sourcePath) {
  const codeFragments = [];
  let s = escapeHtml(value);
  s = s.replace(/\`([^\`]+)\`/g, (_, code) => {
    const idx = codeFragments.push("<code>" + code + "</code>") - 1;
    return "%%CODE_" + idx + "%%";
  });
  s = s.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_, label, href) => {
    const target = safeUrl(href, sourcePath);
    if (!target) return label;
    return '<a href="' + escapeHtml(target.href) + '"' +
      (target.external ? ' target="_blank" rel="noopener noreferrer"' : "") +
      ">" + label + "</a>";
  });
  s = s.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  s = s.replace(/(?<!\*)\*([^*]+)\*(?!\*)/g, "<em>$1</em>");
  s = s.replace(/%%CODE_(\d+)%%/g, (_, i) => codeFragments[Number(i)] || "");
  return s;
}
function markdownToHtml(markdown, sourcePath) {
  const lines = markdown.replace(/\r/g,"").split("\n");
  const html = [];
  let i = 0, headingCount = 0;
  const isBlank = x => !x || !x.trim();
  const isRule = x => /^\s*[-*_]{3,}\s*$/.test(x);
  const isHeading = x => /^#{1,6}\s+/.test(x);
  const isList = x => /^\s*(?:[-*+]\s+|\d+\.\s+)/.test(x);
  const isImage = line => /^!\[[^\]]*\]\([^)]+\)\s*$/.test(line.trim());
  const isTable = (line, next) => /^\s*\|.+\|\s*$/.test(line) && /^\s*\|[\s:|\-]+\|\s*$/.test(next || "") && /---/.test(next);
  const cells = line => line.trim().replace(/^\|/,"").replace(/\|$/,"").split("|").map(x => x.trim());
  while (i < lines.length) {
    const l = lines[i];
    if (isBlank(l)) { i++; continue; }
    if (/^\s*\`\`\`/.test(l)) {
      const lang = l.trim().slice(3);
      i++; const code = [];
      while (i < lines.length && !/^\s*\`\`\`/.test(lines[i])) code.push(lines[i++]);
      if (i < lines.length) i++;
      html.push('<pre><code' + (lang ? ' class="language-' + escapeHtml(lang) + '"' : "") + '>' + escapeHtml(code.join("\n")) + '</code></pre>');
      continue;
    }
    const h = l.match(/^(#{1,6})\s+(.+?)\s*#*\s*$/);
    if (h) {
      const level = Math.min(h[1].length, 4), title = h[2];
      // The document title is already shown in the styled article header.
      if (level !== 1 || headingCount > 0) {
        const id = "section-" + (headingCount++);
        html.push("<h" + level + ' id="' + id + '">' + inlineMarkdown(title, sourcePath) + "</h" + level + ">");
      }
      i++; continue;
    }
    if (isImage(l)) {
      const match = l.trim().match(/^!\[([^\]]*)\]\(([^)]+)\)$/);
      if (match) {
        const raw = match[2].trim();
        const allowed = /^\.\.\/assets\/[a-z0-9-]+\.(?:svg|png|webp|avif|jpe?g)$/i.test(raw);
        if (allowed) {
          const img = new URL(raw, new URL(sourcePath, document.baseURI));
          if (img.origin === location.origin && img.pathname.startsWith(new URL("assets/", document.baseURI).pathname)) {
            html.push('<figure class="article-map"><a href="' + escapeHtml(img.href) + '" target="_blank" rel="noopener noreferrer" aria-label="画像を拡大表示">' +
              '<img src="' + escapeHtml(img.href) + '" alt="' + escapeHtml(match[1]) + '" loading="eager" decoding="async">' +
              '</a><figcaption>画像を選択すると別画面で拡大できます。</figcaption></figure>');
          }
        }
      }
      i++; continue;
    }
    if (isRule(l)) { html.push("<hr>"); i++; continue; }
    if (isTable(l, lines[i+1])) {
      const headings = cells(l);
      i += 2;
      const rows = [];
      while (i < lines.length && /^\s*\|.+\|\s*$/.test(lines[i])) rows.push(cells(lines[i++]));
      html.push('<div class="table-wrap"><table><thead><tr>' + headings.map(c=>"<th>" + inlineMarkdown(c,sourcePath)+"</th>").join("") + "</tr></thead><tbody>" +
        rows.map(row=>"<tr>"+headings.map((_,idx)=>"<td>"+inlineMarkdown(row[idx]||"",sourcePath)+"</td>").join("")+"</tr>").join("")+
        "</tbody></table></div>");
      continue;
    }
    if (/^\s*>\s?/.test(l)) {
      const parts = [];
      while (i < lines.length && /^\s*>\s?/.test(lines[i])) parts.push(lines[i++].replace(/^\s*>\s?/,""));
      html.push("<blockquote><p>"+inlineMarkdown(parts.join(" "),sourcePath)+"</p></blockquote>");
      continue;
    }
    if (isList(l)) {
      const ordered = /^\s*\d+\.\s+/.test(l), tag = ordered ? "ol" : "ul";
      const items = [];
      while (i < lines.length && isList(lines[i]) && /^\s*\d+\.\s+/.test(lines[i]) === ordered) {
        const text = lines[i++].replace(/^\s*(?:[-*+]\s+|\d+\.\s+)/,"");
        items.push("<li>" + inlineMarkdown(text, sourcePath) + "</li>");
      }
      html.push("<"+tag+">" + items.join("") + "</"+tag+">");
      continue;
    }
    const paragraph = [l.trim()]; i++;
    while (i < lines.length && !isBlank(lines[i]) && !isHeading(lines[i]) && !isRule(lines[i]) &&
      !isList(lines[i]) && !isImage(lines[i]) && !/^\s*>/.test(lines[i]) && !/^\s*\`\`\`/.test(lines[i]) && !isTable(lines[i],lines[i+1])) {
      paragraph.push(lines[i++].trim());
    }
    html.push("<p>" + inlineMarkdown(paragraph.join(" "),sourcePath) + "</p>");
  }
  return html.join("\n");
}

function renderNav(activePath) {
  $("sidebar").innerHTML = '<div class="sidebar-title">FIELD GUIDE / 目次</div>' +
    SECTIONS.map(section => '<div class="side-group"><div class="side-group-title">'+escapeHtml(section.label)+'</div>' +
      section.entries.map(e=>'<a class="side-link" href="'+docUrl(e.path)+'"'+(activePath===e.path?' aria-current="page"':'')+'>'+escapeHtml(e.label)+'</a>').join("") +
      '</div>').join("");
  $("mobile-categories").innerHTML = ALL.map(e => '<a href="'+docUrl(e.path)+'"'+(activePath===e.path?' aria-current="page"':'')+'>'+escapeHtml(e.label)+'</a>').join("");
  const active = $("mobile-categories").querySelector('[aria-current="page"]');
  if (active) { $("mobile-categories").scrollLeft = Math.max(0, active.offsetLeft - 35); }
}
function showHome(scrollTop = true) {
  document.title = "RUOSUEN｜ルオスエン — 地図の外側へ";
  $("home-view").classList.remove("hidden");
  $("reader-view").classList.add("hidden");
  if (scrollTop) window.scrollTo({top: 0, behavior: "instant"});
}
async function showDoc(path) {
  const meta = BY_PATH.get(path);
  if (!meta) { showHome(); return; }
  document.title = meta.label + " | ルオスエン";
  $("home-view").classList.add("hidden");
  $("reader-view").classList.remove("hidden");
  renderNav(path);
  $("article-label").textContent = meta.kicker;
  $("article-title").textContent = meta.label;
  $("article-summary").textContent = meta.summary;
  $("article-content").innerHTML = '<p class="loading" role="status">資料を読み込んでいます…</p>';
  const index = ALL.findIndex(x=>x.path===path);
  const next = ALL[(index+1) % ALL.length];
  $("reader-bottom").innerHTML = '<a href="#/">← トップへ戻る</a><a href="'+docUrl(next.path)+'">次に読む：'+escapeHtml(next.label)+' →</a>';
  window.scrollTo({top: 0, behavior: "instant"});
  try {
    const response = await fetch(new URL(path,document.baseURI), {cache:"no-cache"});
    if (!response.ok) throw new Error("HTTP " + response.status);
    const text = await response.text();
    if (currentPath() !== path) return;
    $("article-content").innerHTML = markdownToHtml(text, path);
  } catch (err) {
    $("article-content").innerHTML = '<p>資料を読み込めませんでした。接続を確認して再読み込みするか、' +
      '<a href="https://github.com/Makeinu1/DaD_Ruosuen/blob/main/'+encodeURI(path)+'" target="_blank" rel="noopener noreferrer">GitHubの元資料</a>をご覧ください。</p>';
  }
}
function currentPath() {
  try { return decodeURIComponent(location.hash.replace(/^#\/?/,"")); }
  catch (_) { return ""; }
}
function onRoute() {
  const path = currentPath();
  if (!path) showHome();
  else if (["world", "domains", "guide"].includes(path)) {
    showHome(false);
    requestAnimationFrame(() => document.getElementById(path)?.scrollIntoView({behavior:"smooth",block:"start"}));
  } else showDoc(path);
}
window.addEventListener("hashchange", onRoute);
onRoute();
