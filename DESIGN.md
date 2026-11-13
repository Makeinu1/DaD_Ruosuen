# RUOSUEN Web — visual identity and release notes

Last revised: 2026-11-13

## Purpose

This is a **player-facing invitation to an unknown world**, not a lore encyclopedia or a DM rulebook. Four D&D players should feel curious enough to make their own characters after visiting on a phone. The repository's player-safe Markdown documents remain the canonical source for text; the author's confidential lore stays in Notion and must not be copied to this public repository.

## Visual direction

**The Uncharted World / 未踏の世界への招待状**. Reference: the theatrical urgency and strong character of Seikaisha's original *Red Dragon* special website, not its copyrighted artwork or layout.

- Hero: one bespoke SVG illustration (assets/ruosuen-depths.svg) of a huge underground arch, an unknown destination, and small explorers. No borrowed game artwork.
- Scale: a cinematic full-screen introduction, then chapter-like sections, and finally a practical archive.
- Palette (2026-11-13 revised by user request): **cave black** (#030810), **deep abyss navy** (#071625), **stone blue** (#173a55), **mana blue** (#80bbde), and **blue-white mana glow** (#e3f8ff). Avoid gold, copper, brown, warm cream and parchment as theme colors. The physical cave should absorb light; manastone, the deep gate, active headings and CTAs should appear softly luminous.
- Typography: Japanese literary serif (*Noto Serif JP*) and Cinzel on Latin display words. System fallbacks if fonts do not load.
- Player-safe content order: experience the setting → encounter the unknown → choose a personal motive → read lore → create a character.

## Pages and implementation

- `index.html`: public marketing/introductory homepage + original Markdown reader DOM.
- `assets/site.css`: responsive design. The document reader uses a restrained midnight-blue journal palette with high-contrast ice-white copy instead of warm parchment. The mobile navigation remains readable over the dark background.
- `assets/site.js`: existing dependency-free Markdown viewer and document navigation. Routes `#world` and `#guide` are in-page anchors, while `#/docs/...` and `#/players/...` open the Markdown reader.
- `assets/ruosuen-depths.svg`: custom original visual. Its cave artwork is color-graded **in CSS** using a cool hue shift so the warm light reads as blue-white mana. No external image dependencies. The standalone SVG used as the Open Graph social preview still has its original warm colors; it is not the live-page grade.
- `docs/**` and `players/**`: untouched canonical player guides.

## Installed project skills

- [Anthropic frontend-design](.agents/skills/frontend-design/SKILL.md) (Apache-2.0): guide for distinctive art direction.
- [Vercel-based web-interface-review](.agents/skills/web-interface-review/SKILL.md) (MIT): quality audit referencing the latest published [Vercel Web Interface Guidelines](https://github.com/vercel-labs/web-interface-guidelines).

## Quality gate

Before sharing broadly:

1. Open `https://makeinu1.github.io/DaD_Ruosuen/` in a real browser and check desktop, a narrow phone screen, and reduced-motion preference.
2. Confirm the header, hero CTAs, world/guide anchors, all six world guide links, and character-creation links work.
3. Confirm the markdown reader loads Japanese document file names, cross-document links, tables, and the bottom-next navigation.
4. Check focus visibility, text readability, horizontal overflow, loading errors, and network failure copy.
5. Check the repository's Pages deployment status for current `main`. The source-level consistency checks ran on 2026-11-13; **real-device visual verification was not available in the editing context**.

## Project decisions

A gorgeous hero is an invitation, not license to invent canon. Do not expose metaphysical truths from the author's Notion settings, assign names to currently unnamed nations, or treat D&D level 3 / official rules options as settled when they are still proposals. The player-facing site should remain source-compatible with Markdown edits, and the primary link remains character creation.
