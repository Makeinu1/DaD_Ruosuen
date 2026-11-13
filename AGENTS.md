# Agent Guide — Ruosuen Player Portal

## First read

- **MANDATORY: read [WORLD_POLICY.md](WORLD_POLICY.md) first for world canon, GitHub ownership, Pages curation, and spoiler/security rules.**

- Read the [Agent Operating Guide](https://app.notion.com/p/40f0691fc97a81f0bd7ac9dacddfa963) before project changes where Notion is available.
- Read [DESIGN.md](DESIGN.md) for design direction and the release checklist.
- Read [DECISIONS.md](DECISIONS.md) for player-facing canon versus tentative session rules.
- **Canonical world settings live in `world/**` on GitHub.** Read `world/README.md` and relevant source files before changing world lore.
- `docs/**` and `players/**` are **player-facing adaptations** of the GitHub world canon. Pages selects only player-relevant documents; do not automatically expose everything from `world/`.
- The former extensive Notion world draft remains migration/reference material for items not yet transferred, NOT a second independently maintained canonical copy.
- **CRITICAL**: This GitHub repo is PUBLIC; excluding a file from Pages navigation does NOT make it private. Do not copy DM-only secrets/spoilers or personal data here. Use a permission-controlled store for them.

## Available project skills

- [frontend-design](.agents/skills/frontend-design/SKILL.md): apply when redesigning or extending the site. Source: Anthropic, Apache-2.0.
- [web-interface-review](.agents/skills/web-interface-review/SKILL.md): apply before publication, especially accessibility, responsive behavior and interaction. Source guidance: Vercel Web Interface Guidelines, MIT.

## Web architecture

A minimal dependency-free static GitHub Pages site:
`index.html` (intro and reader frame), `assets/site.css` (styles), `assets/site.js` (Markdown viewer/router), `assets/ruosuen-depths.svg` (original key art). `#/docs/...` and `#/players/...` open documents. `#world` and `#guide` navigate to home sections.

Changes should retain mobile-first legibility, semantic links, visible focus, reduced-motion support, and deep links. Validate on a browser and a phone when one is available; source checks alone are not evidence of a successful visual test.

## Publishing

Before adding any article to `assets/site.js` `SECTIONS`, confirm it is intended for players and does not reveal spoilers. An article living under `world/` is not automatically eligible for Pages navigation.

GitHub Pages uses the repository `main` / root when configured. The intended public URL is https://makeinu1.github.io/DaD_Ruosuen/ . Do not report live deployment or device testing as complete without evidence.
