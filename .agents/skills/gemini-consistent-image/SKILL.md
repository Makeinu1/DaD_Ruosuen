---
name: gemini-consistent-image
description: Consistent multi-shot image art direction and prompting for Google Gemini image models (Nano Banana Pro / gemini-3-pro-image and Nano Banana 2.1 / gemini-nano-banana-2.1). Enforces Asset/Character Sheet FIRST, verbatim style.md locks, 3D previs wireframe-to-painting handoff, sequential reference chaining (up to 14 refs), de-slop rules, and pixel QA review before downstream Gemini video generation.
---

# Gemini Consistent Image Direction (`Nano Banana Pro` / `Nano Banana 2.1`)

Use this skill whenever generating a multi-shot series of paintings, keyframes, or turnaround sheets in **Google Gemini Image** (`Nano Banana Pro` / `gemini-3-pro-image` or `Nano Banana 2.1` / `gemini-nano-banana-2.1`) where **character, creature, prop, architecture, lighting, and brushwork consistency** across shots is critical.

> **Upstream Attributions (required by licenses):**
> - **Serge Shima — [github.com/smixs/visual-skills](https://github.com/smixs/visual-skills)** (CC BY 4.0): `references/nano-banana-rules.md`, `references/characters.md`, `references/de-slop.md`
> - **Antonio Cárdenas — [github.com/AntonioCardenas/generate-nanobanana](https://github.com/AntonioCardenas/generate-nanobanana)** (MIT): `references/nano-banana-pro.md`, `references/nano-banana-2.md`
> - **Square-Zero-Labs — [github.com/Square-Zero-Labs/video-prompting-skill](https://github.com/Square-Zero-Labs/video-prompting-skill)** (Apache-2.0): `references/character-sheets.md`
> - **AgriciDaniel — [github.com/AgriciDaniel/banana-claude](https://github.com/AgriciDaniel/banana-claude)** (MIT): `references/banana-brief-contract.md`

---

## Core Consistency Workflow (NEVER Skip or Parallelize Shots!)

1. **Freeze `style.md` FIRST**: Define one short verbatim style block (medium, brushwork, exact Hex/OKLCH palette, lighting direction, forbidden elements). Prepend this exact block verbatim to EVERY prompt in the series so wording never drifts.
2. **Phase A — Master Asset / Turnaround Sheets FIRST** (see `references/character-sheets.md`):
   - NEVER jump straight into generating final scene shots from text alone.
   - Generate clean, evenly lit neutral-backdrop **Model / Asset Turnaround Sheets** FIRST (one sheet per major subject/creature or cohesive environment kit: front, 3/4, side profile, detail callouts).
   - Inspect pixels and lock the approved sheets before touching any scene shot.
3. **Phase B — Sequential Previs-Guided Reference Chaining** (see `references/nano-banana-pro.md`, `references/characters.md`):
   - **NEVER generate a multi-shot series independently in parallel!** Each unchained run drifts in proportions, masonry, and texture.
   - Use **Nano Banana Pro (`gemini-3-pro-image`, 2K default — same token cost as 1K)** when combining up to **14 reference images** (`5 characters + 6 objects + 3 dedicated style refs`) or converting an uploaded **3D Pill Previs still frame / wireframe** into a finished painting.
   - For every Shot `N`, upload references in an explicit, consistent order and bind each role in plain natural language:
     1. **Exact 3D Previs still frame** for Shot `N` ("Follow the exact camera angle, composition, subject placement, and scale from the first uploaded layout reference; replace every grey clay block, stripe, and capsule completely...")
     2. **Approved Master Asset Sheet(s)** ("Keep the creature anatomy, markings, architecture, and props identical to the second and third reference sheets...")
     3. **Approved Style Anchor + Previous Approved Shot (`N-1`)** ("Match the exact hand-painted brushwork, palette, and atmospheric depth of the fourth reference image...")
4. **Pixel Review & Delta Iteration** (see `references/banana-brief-contract.md`, `references/de-slop.md`):
   - Treat every mismatch as an under-specified variable, not a bad roll.
   - Change **one variable per iteration** via an explicit `EDIT DELTA` or return to the locked references with tightened `LOCKS:` lines.

---

## Mandatory Prompt Rules for Gemini Image (`Nano Banana`)

- **Prose, not tag soup**: Write 1–2 cohesive director-grade paragraphs (`Subject + Action + Location/Context + Composition + Medium/Style`), followed by short labeled `LOCKS:` lines for hard invariants.
- **No numerical lens/camera jargon**: Nano Banana ignores `35mm`, `85mm`, `f/2.8`, `ISO 400`. Describe the optical effect instead (`"wide cathedral perspective"`, `"compressed telephoto perspective"`, `"shallow depth of field"`).
- **Zero banned AI-slop boosters**: NEVER use `4K`, `8K`, `masterpiece`, `ultra-detailed`, `hyper-detailed`, `best quality`, `stunning`, `cinematic`, `epic`, `perfect`, `flawless`. State concrete physical surfaces, brushwork, and light behavior instead.
- **Explicit Role Binding**: Never attach an unexplained image. State clearly what each reference defines AND what to ignore (e.g., `"Ignore the grey clay texture and striped markers of Image 1; use it strictly for spatial layout and framing"`).
- **Ratio & Size are API/UI parameters**: Keep aspect ratio and resolution out of prose unless framing requires it.

## Bundled References

Read the targeted reference before drafting prompts:
- `references/nano-banana-pro.md` — Nano Banana Pro (`gemini-3-pro-image`) limits, 14-ref fusion, wireframe-to-art strength, `previous_interaction_id` chaining
- `references/nano-banana-2.md` — Nano Banana 2.1 (`gemini-nano-banana-2.1`) fast/standard tier & panoramic ratios
- `references/nano-banana-rules.md` — Nano Banana prompt quirks, multi-ref tier table, thinking levels
- `references/character-sheets.md` — Turnaround & prop/asset sheet construction before scene stills
- `references/characters.md` — Identity locking patterns across multi-shot series
- `references/de-slop.md` — Eliminating generic AI sheen, located imperfections, escalating reference deviations
- `references/banana-brief-contract.md` — Frozen visual brief (`LOCKS`, `EDIT DELTA`, P0/P1 pixel QA)
