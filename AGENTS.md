# Agent Guide — Ruosuen Player Portal

## First read

- **MANDATORY: read [WORLD_POLICY.md](WORLD_POLICY.md) first for world canon, GitHub ownership, Pages curation, and spoiler/security rules.**

- Read the [Agent Operating Guide](https://app.notion.com/p/40f0691fc97a81f0bd7ac9dacddfa963) before project changes where Notion is available.
- Read [DESIGN.md](DESIGN.md) for design direction and the release checklist.
- Read [DECISIONS.md](DECISIONS.md) for player-facing canon versus tentative session rules.
- Scratch work belongs in `notes/**`; proposals there are NOT canon and are NOT Pages content. See `notes/README.md`.
- **Canonical world settings live in `world/**` on GitHub.** Read `world/README.md` and relevant source files before changing world lore.
- `docs/**` and `players/**` are **player-facing adaptations** of the GitHub world canon. Pages selects only player-relevant documents; do not automatically expose everything from `world/`.
- The former extensive Notion world draft remains migration/reference material for items not yet transferred, NOT a second independently maintained canonical copy.
- **CRITICAL**: This GitHub repo is PUBLIC; excluding a file from Pages navigation does NOT make it private. Do not copy DM-only secrets/spoilers or personal data here. Use a permission-controlled store for them.

## Available project skills

- [frontend-design](.agents/skills/frontend-design/SKILL.md): apply when redesigning or extending the site. Source: Anthropic, Apache-2.0.
- [web-interface-review](.agents/skills/web-interface-review/SKILL.md): apply before publication, especially accessibility, responsive behavior and interaction. Source guidance: Vercel Web Interface Guidelines, MIT.

## Web architecture

A minimal dependency-free static GitHub Pages site:
`index.html` (intro and reader frame), `assets/site.css` (reader/shared styles), `assets/concept.css` (homepage/scenes), `assets/journey.css` (illustrated world/city and journey navigation), `assets/site.js` (Markdown viewer/router), `assets/scroll-story.mjs` (scroll-driven scene controller), `assets/ruosuen-underground-world.webp` (underground scene painting). `#/docs/...` and `#/players/...` open documents. `#world` and `#guide` navigate to home sections.

Scene anchors within the enhanced sticky stage must await `RuosuenStory.goTo` through the existing router; normal `scrollIntoView` cannot select an overlaid scene. The router keeps an in-memory snapshot for each browser-history entry. `RuosuenStory.capture` / asynchronous `restore` preserve the scene and fractional scroll position, while the router preserves article scroll and the original departure point through related articles. Every route cancels stale image-waiting selections with `cancelPending`. Do not replace the return action with a fixed opening link or a blind `history.back()`.

Keep the movie first, but retain the header navigation and character-creation link throughout it. The `.is-watching-film` state only suppresses the redundant movie-return link. Never require watching the movie to access the world/city/preparation pages. Preserve the normal-document fallback for reduced motion, small viewports, large text, unsupported browsers and JavaScript-disabled reading. Run `node --test tests/scroll-story.test.mjs` after changes to progression. With Playwright and a local server on port 8819, `node tests/navigation.browser.cjs` checks actual scroll/history restoration and the mobile grouped contents; `RUOSUEN_BASE_URL` can target Pages.

The current film has a normal-flow city-title artwork plus seven scroll-driven scenes. The second artwork is the underground panorama with この街の下には、まだ世界がある。 The introduction leaves a glimpse of the next artwork visible instead of showing a scroll instruction. All eight artworks are distinct; the brand is 自由迷宮都市ルオスエン. Derive routes and controls from the frame DOM rather than maintaining a second list of scene IDs. The intended path is movie → everyday world knowledge → a single illustrated city walk → next-session introduction (currently preparation status only) → character creation → sharing. Only five reader pages are curated; legacy public URLs resolve to their merged destinations through `ROUTE_ALIASES`. Do not restore the old 13-page menu or expose editor notes.

`assets/scroll-effects.mjs` adds native-scroll image drift and caption/section reveals across all five reader pages and the introduction. It changes transform/opacity only, refreshes after routing, and disables itself for reduced motion. Do not animate layout dimensions or interrupt native scrolling.

World and city source remains plain Markdown: heading, image, then blockquote. `composeStory` assembles these into illustrated panels. The city has six named institutions and four street scenes; preserve the approved differences in art medium. Mobile and oversized captions flow below the image. Run `node tests/navigation.browser.cjs` with the local server; `RUOSUEN_FONT_FALLBACK=1` explicitly tests fallback fonts when Google Fonts is blocked and must not be reported as external-font validation.

Changes should retain mobile-first legibility, semantic links, visible focus, reduced-motion support, and deep links. Validate on a browser and a phone when one is available; source checks alone are not evidence of a successful visual test.

## Publishing

**Do not create a second manually maintained Pages copy of a Markdown article.** The Pages reader fetches Markdown directly from repository paths; edit the source file to change published prose. After deployment, check that the rendered article matches the source in meaning.

Before adding any article to `assets/site.js` `SECTIONS`, confirm it is intended for players and does not reveal spoilers. Never register paths under `notes/` or `world/` without explicit review (default: do not register them). An article living under `world/` is not automatically eligible for Pages navigation.

GitHub Pages uses the repository `main` / root when configured. The intended public URL is https://makeinu1.github.io/DaD_Ruosuen/ . Do not report live deployment or device testing as complete without evidence.
