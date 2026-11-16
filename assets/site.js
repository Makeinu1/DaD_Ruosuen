"use strict";

/*
 * Ruosuen player portal.
 * Markdown in this GitHub repository is the single source of truth.
 * The reader is intentionally dependency-free and only renders a small,
 * safe Markdown subset needed by these documents.
 */
const SECTIONS = [
  {label:"この街から", entries:[
    {path:"docs/01_プレイヤー向け世界観.md",label:"レウナの世界",kicker:"この街を支える世界",summary:"人々は、なぜ地下へ向かうのか。",layout:"story"},
    {path:"docs/04_自由迷宮都市と組織.md",label:"ルオスエンを歩く",kicker:"六つの施設と街角",summary:"訪ねたい場所を、見つけに。",layout:"story",chapters:true},
    {path:"adventures/次の冒険.md",label:"次の冒険の始まり",kicker:"次は、君たちの話を",summary:"導入と開始条件は、準備中です。",layout:"story"}
  ]},
  {label:"冒険の準備",entries:[
    {path:"players/キャラクター作成ガイド.md",label:"この世界で冒険する",kicker:"君は、何を求めてルオスエンへ？",summary:"人物像から、四人で歩き出す準備へ。"},
    {path:"players/キャラクター提出テンプレート.md",label:"キャラクターを共有する",kicker:"君の人物を、DMへ",summary:"未定のところは、相談しながら。"}
  ]}
];
// Public bookmarks survive the consolidation; editor-only pages stay unregistered.
const ROUTE_ALIASES = {
  "docs/02_迷宮と探索.md":"docs/01_プレイヤー向け世界観.md",
  "docs/03_魔石と魔術.md":"docs/01_プレイヤー向け世界観.md",
  "docs/05_歴史と伝承.md":"docs/04_自由迷宮都市と組織.md",
  "docs/06_種族と信仰.md":"players/キャラクター作成ガイド.md",
  "docs/07_短編セッションの進め方.md":"players/キャラクター作成ガイド.md",
  "docs/08_街角の風景.md":"docs/04_自由迷宮都市と組織.md",
  "players/探索パーティ結成.md":"players/キャラクター作成ガイド.md",
  "players/characters/README.md":"players/キャラクター提出テンプレート.md",
  "adventures/README.md":"adventures/次の冒険.md",
  overture:"world", domains:"territory", manastone:"cargo", map:"depths", characters:"guide"
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
              '<img src="' + escapeHtml(img.href) + '" alt="' + escapeHtml(match[1]) + '" width="' + (/ruosuen-(underground-world|street-night-oil)\.webp$/.test(raw) ? 1672 : 1536) + '" height="' + (/ruosuen-(underground-world|street-night-oil)\.webp$/.test(raw) ? 941 : 1024) + '" loading="lazy" decoding="async">' +
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
  const groups = SECTIONS.map(section => '<div class="side-group"><div class="side-group-title">'+escapeHtml(section.label)+'</div>' +
    section.entries.map(e => '<a class="side-link" href="'+docUrl(e.path)+'"'+(activePath===e.path?' aria-current="page"':'')+'>'+escapeHtml(e.label)+'</a>').join("") + '</div>').join("");
  $("sidebar").innerHTML = '<div class="sidebar-title">FIELD GUIDE / 目次</div>' + groups;
  $("mobile-categories").innerHTML = groups;
  document.querySelector('.reader-toc').open = false;
}

// Deliberate neighbors rather than a circular tour of every document.
const RELATED = {
  "docs/01_プレイヤー向け世界観.md":["docs/04_自由迷宮都市と組織.md"],
  "docs/04_自由迷宮都市と組織.md":["adventures/次の冒険.md"],
  "adventures/次の冒険.md":["players/キャラクター作成ガイド.md"],
  "players/キャラクター作成ガイド.md":["players/キャラクター提出テンプレート.md"],
  "players/キャラクター提出テンプレート.md":["players/キャラクター作成ガイド.md"]
};

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
  if (meta.layout === 'story') {
    for (const heading of [...article.children]) {
      if (!/^H[23]$/.test(heading.tagName)) continue;
      const figure = heading.nextElementSibling;
      const quote = figure?.nextElementSibling;
      if (!figure?.matches('figure.article-map') || quote?.tagName !== 'BLOCKQUOTE') continue;
      const panel = document.createElement('section');
      panel.className = 'story-panel' + (heading.tagName === 'H3' ? ' story-corner' : '');
      panel.setAttribute('aria-labelledby', heading.id);
      heading.before(panel);
      const caption = document.createElement('div');
      caption.className = 'story-caption';
      figure.className = 'story-art';
      figure.querySelector('figcaption')?.remove();
      panel.append(figure, caption);
      caption.append(heading);
      // The optional opening emphasis is the short hook, before the explanation.
      const paragraph = quote.querySelector('p');
      const lead = paragraph?.firstChild;
      if (lead?.nodeType === Node.ELEMENT_NODE && lead.tagName === 'STRONG') {
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
  const chapters = $("story-chapters");
  chapters.replaceChildren();
  chapters.hidden = !meta.chapters;
  if (meta.chapters) {
    for (const heading of article.querySelectorAll('.story-panel h2')) {
      const link = document.createElement('a');
      link.href = '#' + heading.id;
      link.textContent = heading.textContent;
      chapters.append(link);
    }
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
function renderRelated(path) {
  const prep = BY_PATH.get(path).group === '冒険の準備' || path === 'docs/07_短編セッションの進め方.md';
  const links = (RELATED[path] || []).map(p => '<a href="'+docUrl(p)+'">'+escapeHtml(BY_PATH.get(p).label)+' <span aria-hidden="true">→</span></a>').join('');
  $("reader-bottom").innerHTML = '<div class="reader-related"><p>'+(prep?'冒険の準備を進める':'この先へ')+'</p>'+links+'</div>' +
    '<a class="reader-return" data-return-to-story href="#/">物語を見る</a>' +
    '<a class="reader-return" href="#guide">街から冒険へ <span aria-hidden="true">→</span></a>';
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
  $("journey-nav").innerHTML = ALL.map(e => '<a href="'+docUrl(e.path)+'"'+(e.path===path?' aria-current="page"':'')+'>'+escapeHtml(e.label)+'</a>').join('');
  $("story-chapters").hidden = true;
  document.body.classList.remove('is-watching-film');
  $("home-view").classList.add('hidden');
  $("reader-view").classList.remove('hidden');
  renderNav(path);
  $("article-label").textContent = meta.kicker;
  $("article-title").textContent = meta.label;
  $("article-summary").textContent = meta.summary;
  $("article-content").setAttribute('aria-busy','true');
  delete $("article-content").dataset.source;
  $("article-content").innerHTML = '<p class="loading" role="status">資料を読み込んでいます…</p>';
  renderRelated(path);
  updateReturnLinks(entry);
  window.scrollTo({top:0,behavior:'instant'});
  try {
    const response = await fetch(new URL(path,document.baseURI), {cache:'no-cache'});
    if (!response.ok) throw new Error('HTTP ' + response.status);
    const text = await response.text();
    if (token !== routing) return;
    $("article-content").innerHTML = markdownToHtml(text, path);
    composeStory(meta);
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
