# RUOSUEN Web — visual identity and release notes

Last revised: 2026-11-14

## Purpose

This is a **player-facing invitation to an unknown world**, not a lore encyclopedia or a DM rulebook. Four D&D players should feel curious enough to make their own characters after visiting on a phone. GitHub `world/` is the canonical source for world rules; `docs/` and `players/` are the **player-facing edition** derived from it. The author's confidential lore must not be copied to this public repository, regardless of where it is stored. See `WORLD_POLICY.md`.

## Visual direction

**The Uncharted World / 未踏の世界への招待状**. Reference: the theatrical urgency and strong character of Seikaisha's original *Red Dragon* special website, not its copyrighted artwork or layout.

- Hero: one bespoke SVG illustration (assets/ruosuen-depths.svg) of a huge underground arch, an unknown destination, and small explorers. No borrowed game artwork.
- Scale: a cinematic full-screen introduction, then chapter-like sections, and finally a practical archive.
- Palette (2026-11-13 revised by user request): **cave black** (#030810), **deep abyss navy** (#071625), **stone blue** (#173a55), **mana blue** (#80bbde), and **blue-white mana glow** (#e3f8ff). Avoid gold, copper, brown, warm cream and parchment as theme colors. The physical cave should absorb light; manastone, the deep gate, active headings and CTAs should appear softly luminous.
- Typography: Japanese literary serif (*Noto Serif JP*) and Cinzel on Latin display words. System fallbacks if fonts do not load.
- Player-safe content order: experience the setting → encounter the unknown → choose a personal motive → read lore → create a character.

## Four core illustration styles (adopted 2026-11-14)

The following **four art directions are the default options for future Ruosuen concept art**. These are not four separate canonical worlds: an illustrator may use different media to portray the same city, preserving geography, history, and social logic.

| Style | Primary use | Art direction |
|---|---|---|
| **1. Watercolor / 水彩画風** | Arrival scenes, hills, city panoramas and travel | Light washes and pencil/pen linework; paper-white breathing room; distant aerial perspective, asymmetry, lived-in architecture and natural light. |
| **2. Copperplate etching / 銅版画風** | City maps, historical surveys, engraved records and guide illustrations | Mostly white paper, precise but uneven ink hatching and limited stains; reduce the size and contrast of labels so the **image** is primary. Keep monochrome as part of the artwork, not a site-wide image filter. |
| **3. Nocturne fantasy painting / 夜景・幻想画風** | Evening city, abyss and underground world, faint mana light | Painterly shadow and restrained blue-white light against dark stone; isolated sources of illumination and a true sense of the unknown, without excessive glowing crystals. |
| **4. Gouache / ガッシュ・不透明水彩画風** | Markets, alleys, workshops, people at work and daily life | Opaque pigment, confident brush shapes, selective detail, tactile masonry and ordinary human activity; an illustration, not an overly polished fantasy render. |

### Image publication and anti-generic-art direction

- **Preserve the original colors for styles 1, 3 and 4 on GitHub Pages.** Do **not** automatically grayscale, desaturate or recolor concept-art images in the Markdown article reader. Full-color gouache, watercolor and nocturnes should stay in color; authors can explicitly choose a monochrome work on a case-by-case basis.
- For **style 2 (copperplate)**, keep the pale monochrome artwork, white page and subtle physical wear that the author approved. Do not force other images into that style. The article interface may be deep navy while the artwork itself remains white or colorful: these are complementary layers, not a contradiction.
- Favor visual hierarchy and credible world-building over generic AI fantasy: avoid repetitive identical towers, random ornaments, perfectly symmetrical concentric cities, huge royal castles without political rationale, and excessive magic glow. Include working logistics, regional history, imperfect repairs, people and spacious areas where the eye can rest.
- The four style names are production guidelines, **not an instruction to make every illustration into a four-panel comparison board**. After exploring styles, prefer a strong standalone image for Pages unless a comparative sheet is explicitly desired.
- Each art asset is a depiction or proposal, not an automatic canon decision. National names, architectural styles and maps still require explicit approval under `WORLD_POLICY.md`.

## Pages and implementation

- `index.html`: public marketing/introductory homepage + original Markdown reader DOM.
- `assets/site.css`: responsive design. The document reader uses a restrained midnight-blue journal palette with high-contrast ice-white copy instead of warm parchment. The mobile navigation remains readable over the dark background.
- `assets/site.js`: existing dependency-free Markdown viewer and document navigation. Routes `#world` and `#guide` are in-page anchors, while `#/docs/...` and `#/players/...` open the Markdown reader.
- `assets/ruosuen-depths.svg`: custom original visual. Its cave artwork is color-graded **in CSS** using a cool hue shift so the warm light reads as blue-white mana. No external image dependencies. The standalone SVG used as the Open Graph social preview still has its original warm colors; it is not the live-page grade.
- `world/**`: maintained world-setting canon (not automatically displayed on Pages).
- `docs/**` and `players/**`: public player guides curated for Pages.

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

A gorgeous hero is an invitation, not license to invent canon. Do not expose author-only metaphysical truths or spoilers in the player-facing website, assign names to currently unnamed nations, or treat D&D level 3 / official rules options as settled when they are still proposals. The player-facing site should remain source-compatible with Markdown edits, and the primary link remains character creation.
