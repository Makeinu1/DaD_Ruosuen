# Agent Guide — Ruosuen Player Portal

## First read

- Read the [Agent Operating Guide](https://app.notion.com/p/40f0691fc97a81f0bd7ac9dacddfa963) before project changes where Notion is available.
- Read [DESIGN.md](DESIGN.md) for design direction and the release checklist.
- Read [DECISIONS.md](DECISIONS.md) for player-facing canon versus tentative session rules.
- For world descriptions, read `docs/**` and `players/**`. They are the **public** player source of truth; do not copy author-only/spoiler Notion settings into this public repository.

## Available project skills

- [frontend-design](.agents/skills/frontend-design/SKILL.md): apply when redesigning or extending the site. Source: Anthropic, Apache-2.0.
- [web-interface-review](.agents/skills/web-interface-review/SKILL.md): apply before publication, especially accessibility, responsive behavior and interaction. Source guidance: Vercel Web Interface Guidelines, MIT.

## Web architecture

A minimal dependency-free static GitHub Pages site:
`index.html` (intro and reader frame), `assets/site.css` (styles), `assets/site.js` (Markdown viewer/router), `assets/ruosuen-depths.svg` (original key art). `#/docs/...` and `#/players/...` open documents. `#world` and `#guide` navigate to home sections.

Changes should retain mobile-first legibility, semantic links, visible focus, reduced-motion support, and deep links. Validate on a browser and a phone when one is available; source checks alone are not evidence of a successful visual test.

## Publishing

GitHub Pages uses the repository `main` / root when configured. The intended public URL is https://makeinu1.github.io/DaD_Ruosuen/ . Do not report live deployment or device testing as complete without evidence.
