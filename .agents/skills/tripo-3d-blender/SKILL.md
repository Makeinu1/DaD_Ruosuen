---
name: tripo-3d-blender
description: Produce, import, diagnose, and lookdev-finish 3D assets with Tripo AI (Blender MCP generate_3d provider="tripo", Tripo Studio Web/MCP/CLI P1/P2/H3.1) and Blender 5.x. Use when turning 2D concepts/sketches or text into reusable Tripo 3D meshes, preparing isolated neutral-lit reference views, choosing P1 vs P2 quad vs H3.1 generate_parts, switching delighting, rigging creatures vs static props, or fixing melted/baked/scaled Tripo imports inside Blender. Pair with blender-skills, 3d-asset-production, and lida-avatar-workflow.
license: MIT
metadata:
  domain: tripo-3d-blender
  synthesized_from:
    - https://github.com/ploikmjr/tripo-claude-blender-pipeline (MIT)
    - https://github.com/calesthio/generative-media-skills (MIT)
    - https://github.com/Tripo-Developer/Tripo-Studio-MCP (Official Specs)
    - https://github.com/Tripo-Developer/Tripo3D-Plugin-dsh (Official Specs)
---

# Tripo 3D to Blender Production Pipeline

End-to-end discipline for creating usable 3D assets with **Tripo AI** (via native Blender MCP `generate_3d(provider="tripo")`, Tripo Studio Web, or Tripo Studio MCP / CLI) and turning raw AI meshes into reliable, art-directed **Blender 5.x** assets.

Pair with:
- **`blender-skills`**: PBR/stylized shader tuning, waterline staining, Fresnel reflections, lighting separation, screenshot-backed lookdev loops.
- **`3d-asset-production`**: Intake triage (retopo vs decimate vs remodel), UV unwrapping, high-to-low normal/AO baking, scale/pivot contracts, glTF/FBX validation (`scripts/inspect_gltf.py`).
- **`lida-avatar-workflow`**: Japanese/EN character & creature repair, `lida_penetration_check.py`, `lida_file_check.py` (150 MB FBX check), procedural eyes, weight & bone cleanup.

---

## When to Use (and When NOT to Use)

- **Use when**:
  - Generating a standalone hero prop, creature body, flora specimen, architectural ruin fragment, or outfit piece via Tripo (`blender:generate_3d` or Tripo Studio).
  - Preparing 2D concept drawings / orthogonal turnarounds (`front` + `left`/`right`/`back`) so Tripo does not melt thin geometry or bake dark scene shadows into textures.
  - Choosing between Tripo **Smart Mesh P1 / P2** and **H v3.1** (`generate_parts`, `quad`, `delight`, credit impact).
  - Diagnosing and fixing a bad Tripo generation (missing petals/fins, fused appendages, dark baked shadows, Meshopt GLB import errors, scale/origin/axis drift, rig deformation failure).
- **Do NOT use for**:
  - Generating an entire multi-object environment or dramatic camera composition in a single Tripo call (always generate isolated objects and assemble/light in Blender).
  - Rigging **static props, stones, ruins, flora, or architectural modules** (skip rigging completely unless sub-parts actually bend or articulate).

---

## Mandatory 5-Stage Pipeline

### Stage 1: Classify the Subject Before Any Generation

Pick the exact asset class BEFORE making an image or calling Tripo:

| Class | Examples | Tripo Model & Topology | Rigging | Delighted Albedo (`delight`) |
|---|---|---|---|---|
| **Static Hero Prop / Architecture / Rock** | Ruined sanctuary column, weathered arch module, lantern, karst stalactite | **P1.0** (quick blockout) or **P2.0 / H v3.1** (detailed/clean edge); triangles OK (`quad=true` P2/v3.1 only if hand-sculpting later) | **NONE** (skip rig!) | `true` for lit stone/metal re-lighting in Cycles; `false` if keeping stylized flat-lit palette |
| **Articulated / Multi-Part Asset** | Broken arch with detachable crown moss, gate + hinges, multi-part flora, flower + removable petals | **H v3.1** with `generate_parts=true, texture=false` -> inspect parts -> chain texture pass (`texture=true`) OR generate modular pieces separately | Usually **NONE** (animate parts around explicit pivots) | Match target material (`false` for anime/gouache, `true` for PBR) |
| **Bendable Creature / Character** | Whale, quadruped beast, humanoid adventurer | **P2.0 (`Nexus-v2.0-20260801`) + `quad=true` -> FBX export** (quad edge loops deform cleanly) | Biped: `rig-v3.0` (`spec=unity\|mixamo\|unreal\|vrm`); Aquatic/Quadruped/Avian: `rig-v2.5` (**OMIT `spec`!**) | `false` for stylized painterly textures; `true` for realistic PBR |

---

### Stage 2: 2D Input Prep (Never Feed Raw Dark Scene Art to Tripo!)

Tripo infers 3D volume directly from contrast, silhouette boundaries, and surface shading in the input image. **Most bad Tripo outputs start with a scene illustration instead of a neutral 3D model sheet.**

Follow these strict input rules before running `image_to_model` or `multiview_to_model` — see `references/2d-prep-and-troubleshooting.md` for full repair cards:

1. **Plain Neutral Studio Backdrop (`#D8D8D8`–`#E5E5E5`)**: No dark cave sky, no glowing moon beams, no cast floor shadows, no atmospheric mist, no secondary props/particles overlapping the silhouette.
2. **Even, Shadowless Studio Lighting**: Tripo mistakes strong key shadows or rim light for physical bumps or deep black cavities (causing sunken craters or hollow backs).
3. **One Subject, Canonical Pose**:
   - **Floating / Swimming Creatures (Whale)**: Clean **horizontal neutral swim pose**, pectoral fins angled outward cleanly clear of the flanks, tail fluke flat and visible, mouth closed unless articulated separately.
   - **Flora / Thin Delicate Geometry (Blossoms, Petals, Tendrils)**: **Slight thickness exaggeration (1.5x–2x petal/stem thickness)** in 2D ref, separated calyx/petal silhouette with clear gaps between overlapping petals, photographed/drawn slightly tilted (~25–35° 3/4 view + top/side if needed) so AI does not fuse into a cabbage lump.
   - **Architecture / Ruins**: **Modular isolated section** (`left broken pier + partial arch springer`) with square orthographic elevation rather than forced ultra-wide lens perspective! Never feed a distorted 21mm wide-angle scene frame as a ruin module input.
4. **Multiview (`tripo_multiview_to_model`) Alignment Check**: Supply `front` + at least one of `left`, `right`, `back`. Verify exact height alignment, head/tail direction consistency, and silhouette match across views before spending credits.

---

### Stage 3: Execute Generation (Blender MCP vs Tripo Studio / CLI)

#### Channel A — Built-in Blender MCP `generate_3d(provider="tripo")`
- Generates a single object and imports it straight into the active Blender scene.
- Rules:
  - Keep `prompt` **short English describing ONE standalone object** (e.g., `"weathered ruined limestone sanctuary column base with chisel flutes, isolated on neutral background"`), OR supply `image` as an absolute path to a clean studio model sheet.
  - Set a semantic `name` (`TRIPO_RuinedArch_v1`) and pass the user's exact words verbatim in `user_prompt`.
  - **`job` resume rule**: If `generate_3d` times out mid-generation and returns a `job` handle, **reuse `job=...`** on the next call to retrieve the finished model **without paying credits twice**. Never start a fresh paid job for a timed-out task without checking the handle!

#### Channel B — Tripo Studio Web / MCP / CLI (Precision Controls)
- **Plan & Disclose Credits FIRST**: State planned model (`P1` / `P2` / `v3.1`), `quad`, `texture_quality` (`standard`=2K, `detailed`=4K, `extreme`=8K), and extras (`generate_parts`, `rig`) using reference credit values in `references/tripo-models-and-credits.md` BEFORE spending credits when operating CLI/MCP directly.
- **Idempotency & Recovery**: Reuse the exact `(creation_tool, idempotency_key)` when checking an ambiguous timeout (`tripo_get_model_task_by_idempotency_key`) — do NOT blindly fire a duplicate paid generation.
- **`delight` Rule (Crucial!)**:
  - Set **`delight=False`** when preserving hand-painted, anime gouache, matte stylized shading, or controlled artist colors (`CUT03`/`CUT09` palette match).
  - Set **`delight=True`** only when generating lit PBR architectural stones/metals that must react neutrally to Cycles lights without baked highlights.
- **Meshopt GLB Decode**: If a Studio GLB fails to import into Blender due to Meshopt/quantization (`_meshopt.glb`), decode cleanly with:
  ```bash
  gltf-transform dequantize model_meshopt.glb model_for_blender.glb
  ```
  Or request FBX with `fbx_preset=blender, texture_packaging=embedded`.

---

### Stage 4: Mandatory Post-Import Blender 5.x Normalization

Immediately after ANY Tripo model enters Blender (via `generate_3d` or manual `.fbx`/`.glb` import):

1. **Inspect Geometry & Metrics via `bpy`**:
   - Print evaluated `world_bounding_box` dimensions (`X × Y × Z`), vertex/polygon/quad-ratio counts, material count, image resolutions, and non-manifold edge check.
2. **Fix Scale, Rotation, and Origin**:
   - Scale uniformly to real project meters (e.g. adult adventurer height `1.70 m`, hero blossom `0.35 m`, hero whale `24.0 m`, arch bay width `24.0 m`).
   - Apply transforms (`bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)`) so `scale == (1, 1, 1)` everywhere!
   - Set **Origin** cleanly: bottom-center (`min_z = 0`) for props/ruins/flowers; chest/COG or nose tip for swimming creatures; hinge pivot for articulated wings/gates.
3. **Render Orthographic Lookdev Sheet (`front` / `side` / `back` / `3-4`) + Wireframe Overlay**:
   - Use Blender MCP `look()` / Cycles preview strip BEFORE placing into hero shots. Never approve an asset from Tripo's tiny thumbnail alone.

---

### Stage 5: Targeted Blender Cleanup & Hybrid Upgrade

Tripo gives you **rapid 80% organic silhouette mass** that hand-coded `bmesh` lofts struggle to match, while Blender gives you **100% precision on optics, details, and shading**. Combine both:

- **Mesh Cleanup**: Remove loose island debris (<1% volume), weld doubles (`merge_by_distance`), `normals_make_consistent(inside=False)`, `WeightedNormal` or clean `Shade Auto Smooth` (`30°–45°`).
- **Remesh / Retopo Triage** (see `3d-asset-production` for details):
  - *Hero silhouette OK but messy triangles?* -> Use `QuadriFlow` / `Remesh` + **Shrinkwrap + High-to-Low Normal/AO Bake**, OR Tripo `smart_low_poly` (`v3.0`, `quad=True`, ≤ 10k quads).
  - *Thin parts melted or missing?* -> Keep Tripo's organic main torso / column drum / calyx core, and replace or layer clean parametric/sculpted Blender petals, baleen grooves, fluted ribs, or glowing eyes on top!
- **Eye Rule for Characters/Creatures**: NEVER keep flat painted/melted Tripo eyeballs in closeups. Boolean/carve clean eye sockets and insert crisp multi-layer Blender sphere eyes (sclera + concave iris + specular cornea, per `lida-avatar-workflow/references/eye-modeling.md`).
- **Shader / Palette Discipline**: Avoid plastic `Roughness = 0.5` defaults. Calibrate stone, skin, and organic translucency (`Principled BSDF` `Subsurface Weight`, `IOR`, wetness gradient near lake Z=0) using `blender-skills`.

---

## Bundled References

- `references/tripo-models-and-credits.md` — Verified Tripo model family matrix (`Smart Mesh P1/P2`, `H v3.1`), limits, rig compatibility (`v3.0` vs `v2.5`), Meshopt GLB handling, and reference credit rules (`Tripo-Developer` + `ploikmjr` MIT).
- `references/2d-prep-and-troubleshooting.md` — Step-by-step 2D turnaround prep checklist + symptom-to-fix diagnostic table for Tripo failures (flora, marine creatures, weathered classical ruins, karst cliffs).
