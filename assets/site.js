"use strict";

/*
 * Ruosuen player portal.
 * Markdown in this GitHub repository is the single source of truth.
 * The reader is intentionally dependency-free and only renders a small,
 * safe Markdown subset needed by these documents.
 */
// Dimensions from the original artwork. Variants are derived without replacing it.
const RESPONSIVE_ART = {
  "reuna-turn-01.webp": [
    1672,
    941
  ],
  "reuna-turn-02.webp": [
    1672,
    941
  ],
  "reuna-turn-03.webp": [
    1672,
    941
  ],
  "reuna-turn-04.webp": [
    1672,
    941
  ],
  "reuna-turn-05.webp": [
    1672,
    941
  ],
  "reuna-turn-06.webp": [
    1672,
    941
  ],
  "reuna-turn-07.webp": [
    1672,
    941
  ],
  "reuna-turn-08.webp": [
    1672,
    941
  ],
  "reuna-turn-09.webp": [
    1672,
    941
  ],
  "reuna-turn-10.webp": [
    1672,
    941
  ],
  "ruosuen-film-airfleet.webp": [
    1672,
    941
  ],
  "ruosuen-film-departure.webp": [
    1536,
    1024
  ],
  "ruosuen-film-manastones.webp": [
    1672,
    941
  ],
  "ruosuen-film-possibility.webp": [
    1672,
    941
  ],
  "ruosuen-film-survey.webp": [
    1536,
    1024
  ],
  "ruosuen-film-vista.webp": [
    1536,
    1024
  ],
  "ruosuen-street-night-oil.webp": [
    1672,
    941
  ],
  "ruosuen-street-tavern-watercolor.webp": [
    1536,
    1024
  ],
  "ruosuen-underground-world.webp": [
    1672,
    941
  ],
  "ruosuen-walk-church-20261117.webp": [
    1672,
    941
  ],
  "ruosuen-walk-labyrinth-battle-v2.webp": [
    1672,
    941
  ],
  "ruosuen-walk-labyrinth-exploration-v3.webp": [
    1670,
    941
  ],
  "ruosuen-walk-labyrinth-ruins-v2.webp": [
    1672,
    941
  ],
  "ruosuen-walk-maps-20261117.webp": [
    1672,
    941
  ],
  "ruosuen-walk-matenrou-20261117.webp": [
    1672,
    941
  ],
  "ruosuen-walk-mole-inn-20261117.webp": [
    1672,
    941
  ],
  "ruosuen-walk-mole-trading-20261117.webp": [
    1672,
    941
  ],
  "ruosuen-walk-quentha-20261117.webp": [
    1672,
    941
  ],
  "ruosuen-walk-shipyard-20261117.webp": [
    1672,
    941
  ],
  "ruosuen-walk-tower-20261117.webp": [
    1672,
    941
  ]
};
const SECTIONS = [
  {label:"街から冒険へ",entries:[
    {path:"docs/04_自由迷宮都市と組織.md",label:"ルオスエンを歩く",kicker:"人と仕事と、その先の迷宮",summary:"地下の三つの景色から、街の表と裏に生きる人々へ。",layout:"story",book:true,walk:true},
    {path:"adventures/次の冒険.md",label:"この街で冒険する",kicker:"君たちは、何を探しに行く？",summary:"救助、探索、護衛、採集。四人から始まる小さな冒険の可能性。",layout:"story",book:true},
    {path:"adventures/最初の冒険.md",label:"最初の冒険",kicker:"第一話",summary:"年の瀬、自由迷宮都市ルオスエン。",book:true,prologue:true},
    {path:"players/キャラクター作成ガイド.md",label:"キャラクターを考える",kicker:"君は、この街で何者になる？",summary:"人物像の種と、四人で冒険するための準備。"}
  ]},
  {label:"もっと知る",entries:[
    {path:"docs/01_プレイヤー向け世界観.md",label:"世界を知る",kicker:"魔石から、ルオスエンへ",summary:"なぜ船は地下を飛ぶのか。レウナの歴史から、街の始まりをたどる。",layout:"story",book:true,history:true}
  ]}
];
// Public bookmarks survive the consolidation; editor-only pages stay unregistered.
const ROUTE_ALIASES = {
  "docs/02_迷宮と探索.md":"docs/01_プレイヤー向け世界観.md",
  "docs/03_魔石と魔術.md":"docs/01_プレイヤー向け世界観.md",
  "docs/05_歴史と伝承.md":"docs/01_プレイヤー向け世界観.md",
  "docs/06_種族と信仰.md":"players/キャラクター作成ガイド.md",
  "docs/07_短編セッションの進め方.md":"players/キャラクター作成ガイド.md",
  "docs/08_街角の風景.md":"docs/04_自由迷宮都市と組織.md",
  "players/探索パーティ結成.md":"players/キャラクター作成ガイド.md",
  "players/characters/README.md":"players/キャラクター作成ガイド.md",
  "players/キャラクター提出テンプレート.md":"players/キャラクター作成ガイド.md",
  "adventures/README.md":"adventures/次の冒険.md",
  overture:"vista", world:"vista", domains:"territory", manastone:"cargo", map:"depths", characters:"guide"
};
const resolvePath = path => ROUTE_ALIASES[path] || path;
const ALL = SECTIONS.flatMap(section => section.entries.map(item => ({...item, group: section.label})));
const BY_PATH = new Map(ALL.map(item => [item.path, item]));
const $ = id => document.getElementById(id);

function docUrl(path) { return "#/" + encodeURIComponent(resolvePath(path)); }
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
    if (link.origin === base.origin && BY_PATH.has(resolvePath(file))) return {href: docUrl(file), external: false};
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
// Standard Markdown hard breaks (two trailing spaces or a backslash).
// Ordinary soft-wrapped prose still becomes a single paragraph.
function paragraphHtml(lines, sourcePath) {
  const groups = [];
  let group = [];
  lines.forEach((line, index) => {
    const hard = index < lines.length - 1 && /(?: {2,}|\\)$/.test(line);
    group.push((hard ? line.replace(/(?: {2,}|\\)$/, "") : line).trim());
    if (hard || index === lines.length - 1) {
      groups.push(inlineMarkdown(group.join(" "), sourcePath));
      group = [];
    }
  });
  return groups.join("<br>");
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
        // The city chapter divider gets its own ID without renumbering
        // any of the existing article navigation targets.
        const isCityDivider = sourcePath === "docs/04_自由迷宮都市と組織.md" &&
          level === 2 && title === "この街に生きる人々";
        const id = isCityDivider ? "walk-people" : "section-" + (headingCount++);
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
            const name = img.pathname.split('/').pop();
            const firstAdventure = name === 'ruosuen-first-adventure-1672.webp';
            const dimensions = firstAdventure ? [1672, 941] : RESPONSIVE_ART[name];
            const [width, height] = dimensions || [1536, 1024];
            const portrait = height > width;
            const sizes = portrait ? '(max-width: 480px) 400px, (max-width: 740px) calc(100vw - 40px), 700px' : BY_PATH.get(sourcePath)?.layout === 'story'
              ? '(max-width: 480px) 400px, (max-width: 700px) 100vw, (max-width: 1500px) 92vw, 1392px'
              : '(max-width: 700px) calc(100vw - 48px), 880px';
            const candidates = firstAdventure
              ? [img.href.replace('-1672.webp', '-800.webp') + ' 800w', img.href.replace('-1672.webp', '-1200.webp') + ' 1200w']
              : dimensions ? [800, 1200].filter(w => w < width).map(w => new URL('responsive/' + name.replace('.webp', '-' + w + '.webp'), img).href + ' ' + w + 'w') : [];
            const responsive = candidates.length
              ? ' srcset="' + escapeHtml([...candidates, img.href + ' ' + width + 'w'].join(', ')) + '" sizes="' + sizes + '"'
              : '';
            html.push('<figure class="article-map"><a href="' + escapeHtml(img.href) + '" target="_blank" rel="noopener noreferrer" aria-label="画像を拡大表示">' +
              '<img src="' + escapeHtml(img.href) + '"' + responsive + ' alt="' + escapeHtml(match[1]) + '" width="' + width + '" height="' + height + '" loading="lazy" decoding="async">' +
              '</a></figure>');
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
      html.push("<blockquote>"+parts.join("\n").split(/\n\s*\n/).filter(p=>p.trim()).map(p=>"<p>"+paragraphHtml(p.split("\n"),sourcePath)+"</p>").join("")+"</blockquote>");
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
    const paragraph = [l]; i++;
    while (i < lines.length && !isBlank(lines[i]) && !isHeading(lines[i]) && !isRule(lines[i]) &&
      !isList(lines[i]) && !isImage(lines[i]) && !/^\s*>/.test(lines[i]) && !/^\s*\`\`\`/.test(lines[i]) && !isTable(lines[i],lines[i+1])) {
      paragraph.push(lines[i++]);
    }
    html.push("<p>" + paragraphHtml(paragraph,sourcePath) + "</p>");
  }
  return html.join("\n");
}

// One global navigation, with mutually exclusive desktop/mobile links.
function updateHeaderCurrent(path) {
  for (const link of document.querySelectorAll('.top-nav a[href^="#/"]')) {
    const target = resolvePath(decodeURIComponent(link.getAttribute('href').slice(2)));
    if (path && target === path) link.setAttribute('aria-current','page');
    else link.removeAttribute('aria-current');
  }
}

// Keep the Markdown source readable on GitHub: heading + image + quotation.
// Only curated story pages opt into the scenic presentation.
let captionObserver;
function fitStoryCaptions() {
  for (const panel of document.querySelectorAll('.story-panel')) {
    const caption = panel.querySelector('.story-caption');
    const image = panel.querySelector('img');
    panel.classList.toggle('caption-below', caption.scrollHeight > image.clientHeight * 0.6);
  }
}
function composeStory(meta) {
  captionObserver?.disconnect();
  const article = $("article-content");
  article.classList.toggle("storybook",Boolean(meta.book));
  article.classList.toggle("storybook-walk",Boolean(meta.walk));
  article.classList.toggle("world-history",Boolean(meta.history));
  article.classList.toggle("prologue",Boolean(meta.prologue));
  if (meta.layout === 'story') {
    for (const heading of [...article.children]) {
      if (!/^H[23]$/.test(heading.tagName)) continue;
      const figure = heading.nextElementSibling;
      const quote = figure?.nextElementSibling;
      if (!figure?.matches('figure.article-map') || quote?.tagName !== 'BLOCKQUOTE') continue;
      const panel = document.createElement('section');
      panel.className = 'story-panel' + (!meta.history && heading.tagName === 'H3' ? ' story-corner' : '');
      panel.setAttribute('aria-labelledby', heading.id);
      heading.before(panel);
      const caption = document.createElement('div');
      caption.className = 'story-caption';
      figure.className = 'story-art';
      const artwork = figure.querySelector('img');
      if (Number(artwork?.getAttribute('height')) > Number(artwork?.getAttribute('width'))) figure.classList.add('portrait-art');
      panel.append(figure, caption);
      caption.append(heading);
      // The optional opening emphasis is the short hook, before the explanation.
      const paragraph = quote.querySelector('p');
      const lead = paragraph?.firstChild;
      if (!meta.book && lead?.nodeType === Node.ELEMENT_NODE && lead.tagName === 'STRONG') {
        const hook = document.createElement('p');
        hook.className = 'story-hook';
        hook.append(lead);
        caption.append(hook);
      }
      // Blockquotes remain normal readable Markdown outside the Pages viewer.
      quote.querySelectorAll('p').forEach(p => caption.append(p));
      quote.remove();
    }
  }
  if (meta.walk) {
    const heading = article.querySelector('#walk-people');
    const kicker = heading?.nextElementSibling;
    const copy = kicker?.nextElementSibling;
    if (heading && kicker?.tagName === 'P' && copy?.tagName === 'P') {
      const divider = document.createElement('section');
      divider.className = 'walk-chapter-divider';
      divider.setAttribute('aria-labelledby', heading.id);
      heading.before(divider);
      kicker.classList.add('walk-divider-kicker');
      copy.classList.add('walk-divider-copy');
      divider.append(heading, kicker, copy);
    }
  }
  if (meta.history) {
    const phases = ['rise','fall','renewal','city'];
    let chapter;
    let index = 0;
    for (const child of [...article.children]) {
      if (child.tagName === 'H2') {
        chapter = document.createElement('section');
        chapter.className = 'history-chapter';
        chapter.dataset.historyPhase = phases[index++];
        chapter.setAttribute('aria-labelledby',child.id);
        child.before(chapter);
        chapter.append(child);
      } else if (chapter && child.matches('.story-panel')) {
        chapter.append(child);
      } else if (chapter && child.tagName === 'P' && !chapter.querySelector('.story-panel')) {
        child.classList.add('history-era');
        chapter.append(child);
      } else {
        // The concluding question and onward link stay outside the chapters.
        chapter = null;
      }
    }
  }
  if (meta.prologue) {
    const heading = article.querySelector('h2');
    const image = heading?.nextElementSibling;
    if (image?.matches('figure.article-map')) heading.before(image);
  }
  if (meta.layout !== 'story') {
    // Animate coherent reading sections rather than each line of body text.
    let section;
    for (const child of [...article.children]) {
      if (child.tagName === 'H2') {
        section = document.createElement('section');
        section.className = 'reading-section';
        section.setAttribute('aria-labelledby',child.id);
        child.before(section);
      }
      if (section) section.append(child);
    }
  }
  if (meta.layout === 'story' && window.ResizeObserver) {
    captionObserver = new ResizeObserver(fitStoryCaptions);
    article.querySelectorAll('.story-caption, .story-art img').forEach(e => captionObserver.observe(e));
  }

}
const HOME_ANCHORS = new Set([...document.querySelectorAll('[data-film-scene]')].map(frame => frame.id).concat('characters','guide'));
const visits = new Map();
let entrySequence = 0;
let activeKey = '';
let activeHash = '';
let routing = 0;
let restoring = false;
let pendingRoute = 0;
let pendingScroll = 0;
history.scrollRestoration = 'manual';

function currentPath() {
  try { return resolvePath(decodeURIComponent(location.hash.replace(/^#\/?/,''))); }
  catch (_) { return ''; }
}
function newKey() { return Date.now().toString(36) + '-' + (++entrySequence); }
function ensureEntry() {
  let key = history.state?.ruosuenEntry;
  if (!key) {
    key = newKey();
    history.replaceState({...history.state, ruosuenEntry:key}, '');
  }
  if (!visits.has(key)) visits.set(key, {kind:BY_PATH.has(currentPath())?'doc':'home', path:currentPath(), y:0});
  return key;
}
function savePlace() {
  if (restoring || location.hash !== activeHash) return;
  const entry = visits.get(activeKey);
  if (!entry) return;
  entry.y = window.scrollY;
  if (entry.kind === 'home') {
    entry.story = window.RuosuenStory?.capture() || null;
    entry.archiveOpen = document.querySelector('.film-archive-disclosure').open;
  }
}
function originOf(entry) {
  return entry?.kind === 'doc' ? visits.get(entry.originKey) : null;
}
function updateReturnLinks(entry) {
  const origin = originOf(entry);
  const label = origin?.story ? '物語の続きへ' : origin ? '元の場所へ戻る' : '物語を見る';
  document.querySelectorAll('[data-return-to-story]').forEach(link => { link.textContent = label; });
}
// Promote the original Markdown's final standalone internal link to the
// single onward action. No second list of page destinations is maintained.
function renderOnward(path) {
  const nav = $("reader-bottom");
  const article = $("article-content");
  nav.replaceChildren();
  nav.hidden = true;
  const last = article.lastElementChild;
  // Reading pages may wrap their final paragraph in a reading section.
  const paragraph = last?.matches('.reading-section') ? last.lastElementChild : last;
  if (!paragraph?.matches('p') || paragraph.childNodes.length !== 1 ||
      !paragraph.firstElementChild?.matches('a[href^="#/"]')) return;
  const link = paragraph.firstElementChild;
  const target = resolvePath(decodeURIComponent(link.getAttribute('href').slice(2)));
  if (!BY_PATH.has(target)) return;
  const optional = path === 'players/キャラクター作成ガイド.md';
  const kicker = document.createElement('span');
  kicker.className = 'reader-onward-kicker';
  kicker.textContent = optional ? 'OPTIONAL READING' : path === 'adventures/最初の冒険.md' ? 'YOUR STORY BEGINS' : 'THE NEXT CHAPTER';
  const arrow = document.createElement('span');
  arrow.className = 'reader-onward-arrow';
  arrow.textContent = '→';
  arrow.setAttribute('aria-hidden','true');
  link.className = 'reader-onward-link';
  link.prepend(kicker);
  link.append(arrow);
  nav.append(link);
  paragraph.remove();
  nav.classList.toggle('optional-onward',optional);
  nav.hidden = false;
}
const nextPaint = () => new Promise(resolve => requestAnimationFrame(resolve));

async function showHome(entry, token) {
  document.title = '自由迷宮都市ルオスエン — この街の下には、まだ世界がある。';
  document.body.classList.remove('story-layout','reading-layout');
  captionObserver?.disconnect();
  $("home-view").classList.remove('hidden');
  $("reader-view").classList.add('hidden');
  const archive = document.querySelector('.film-archive-disclosure');
  if (entry.saved) archive.open = Boolean(entry.archiveOpen);
  else if (entry.path === 'guide') archive.open = true;
  window.RuosuenStory?.refresh();
  await nextPaint();
  if (token !== routing) return;
  if (entry.saved) {
    if (!await window.RuosuenStory?.restore(entry.story)) window.scrollTo({top:entry.y,behavior:'instant'});
  } else if (!entry.path) {
    window.scrollTo({top:0,behavior:'instant'});
  } else if (!await window.RuosuenStory?.goTo(entry.path)) {
    if (token !== routing) return;
    document.getElementById(entry.path)?.scrollIntoView({behavior:'instant',block:'start'});
  }
  if (token !== routing) return;
  window.RuosuenScroll?.refresh();
  // Raw scroll restoration outside the film still needs to update its header.
  window.RuosuenStory?.refresh();
}

async function showDoc(path, entry, token) {
  const meta = BY_PATH.get(path);
  document.title = meta.label + ' | ルオスエン';
  document.body.classList.toggle('story-layout',meta.layout === 'story');
  document.body.classList.toggle('reading-layout',meta.layout !== 'story');
  document.body.classList.remove('is-watching-film');
  $("home-view").classList.add('hidden');
  $("reader-view").classList.remove('hidden');
  $("article-label").textContent = meta.kicker;
  $("article-title").textContent = meta.label;
  $("article-summary").textContent = meta.summary;
  $("article-content").setAttribute('aria-busy','true');
  delete $("article-content").dataset.source;
  $("article-content").innerHTML = '<p class="loading" role="status">資料を読み込んでいます…</p>';
  $("reader-bottom").replaceChildren();
  $("reader-bottom").hidden = true;
  updateReturnLinks(entry);
  window.scrollTo({top:0,behavior:'instant'});
  try {
    const response = await fetch(new URL(path,document.baseURI), {cache:'no-cache'});
    if (!response.ok) throw new Error('HTTP ' + response.status);
    const text = await response.text();
    if (token !== routing) return;
    $("article-content").innerHTML = markdownToHtml(text, path);
    composeStory(meta);
    renderOnward(path);
    $("article-content").dataset.source = path;
    // Dimensions reserve the artwork's space. Decode only the opening image and
    // images above a restored position; the rest load as the visitor approaches.
    const images = [...$("article-content").querySelectorAll('img')];
    await Promise.all(images.filter((image,index) => index === 0 ||
      (entry.saved && image.getBoundingClientRect().top + scrollY <= entry.y + innerHeight))
      .map(image => { image.loading = 'eager'; return image.decode().catch(() => {}); }));
  } catch (_) {
    if (token !== routing) return;
    $("article-content").innerHTML = '<p>資料を読み込めませんでした。接続を確認して再読み込みするか、' +
      '<a href="'+docUrl(path)+'">もう一度読み込む</a>。</p>';
  }
  await nextPaint();
  if (token !== routing) return;
  fitStoryCaptions();
  if (entry.saved) window.scrollTo({top:entry.y,behavior:'instant'});
  $("article-title").setAttribute('tabindex','-1');
  $("article-title").focus({preventScroll:true});
  $("article-content").setAttribute('aria-busy','false');
  window.RuosuenScroll?.refresh();
}

async function onRoute() {
  const token = ++routing;
  window.RuosuenStory?.cancelPending();
  restoring = true;
  const key = ensureEntry();
  const entry = visits.get(key);
  activeKey = key;
  activeHash = location.hash;
  document.querySelectorAll('.header-menu').forEach(menu => { menu.open = false; });
  updateReturnLinks(entry);
  updateHeaderCurrent(entry.kind === 'doc' ? entry.path : null);
  if (entry.kind === 'doc') await showDoc(entry.path, entry, token);
  else await showHome(entry, token);
  if (token !== routing) return;
  restoring = false;
  entry.saved = true;
  savePlace();
}

function navigate(hash, snapshot) {
  savePlace();
  const previous = visits.get(activeKey);
  const path = resolvePath(decodeURIComponent(hash.replace(/^#\/?/,'')));
  const key = newKey();
  const entry = snapshot ? {...snapshot} : {
    kind:BY_PATH.has(path)?'doc':'home', path, y:0,
    originKey:previous?.kind === 'doc' ? previous.originKey : activeKey
  };
  visits.set(key, entry);
  history.pushState({...history.state,ruosuenEntry:key},'',hash);
  onRoute();
}

document.addEventListener('click', event => {
  if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.altKey || event.shiftKey) return;
  const link = event.target.closest('a[href^="#"]');
  if (!link || link.target || link.hasAttribute('download')) return;
  const hash = link.getAttribute('href');
  let path;
  try { path = resolvePath(decodeURIComponent(hash.replace(/^#\/?/,''))); } catch (_) { return; }
  if (path && !BY_PATH.has(path) && !HOME_ANCHORS.has(path)) {
    const target = document.getElementById(path);
    if (target && !target.closest('.hidden')) {
      event.preventDefault();
      target.scrollIntoView({behavior:'instant',block:'start'});
      target.setAttribute('tabindex','-1');
      target.focus({preventScroll:true});
    }
    return;
  }
  event.preventDefault();
  if (link.hasAttribute('data-return-to-story')) {
    const entry = visits.get(activeKey);
    const origin = originOf(entry);
    navigate(origin?.path ? '#'+origin.path : '#/', origin);
  } else navigate(hash);
});

function scheduleRoute() {
  if (!pendingRoute) pendingRoute = requestAnimationFrame(() => { pendingRoute = 0; onRoute(); });
}
window.addEventListener('popstate', scheduleRoute);
window.addEventListener('hashchange', scheduleRoute);
window.addEventListener('scroll', () => {
  if (!pendingScroll) pendingScroll = requestAnimationFrame(() => { pendingScroll = 0; savePlace(); });
}, {passive:true});
window.addEventListener('ruosuen:story-ready', () => {
  const entry = visits.get(activeKey);
  // If the module arrived after the reader, remeasure direct scene URLs.
  if (entry?.kind === 'home') { entry.saved = false; onRoute(); }
});
onRoute();
