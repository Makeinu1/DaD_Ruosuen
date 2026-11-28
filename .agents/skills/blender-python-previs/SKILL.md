---
name: blender-python-previs
description: Build deterministic clay 3D previs scenes, anatomical blockout meshes, real-optics cameras, smooth animations, and stills-first QA contact sheets in Blender via Python (bpy) headless CLI or Blender MCP. Use when creating or rebuilding 3D previs, clay animatics, camera blocking, Blender 4.x/5.x scripts, or AI-video camera references alongside cinematic-previs and animation-principles.
---

# Blender Python & MCP Clay Previs (`bpy` / MCP)

Use this skill to construct, verify, and render clean, reproducible **clay 3D previs** in **Blender (4.x / 5.x)** through **Python (`bpy`)** — running identically via **headless CLI (`blender --background --factory-startup --python ...`)** or a **live Blender MCP bridge** (`execute_blender_code`). Pair with `cinematic-previs` (camera/cut rulebook & clay look), `animation-principles` (Disney's 12 principles for motion & staging), and `cinematic-camera-continuity` (180° rule & shot-pair QA).

> **Upstream Attributions (MIT License):**
> - **RobLe3 — [github.com/RobLe3/cc-blender-skill](https://github.com/RobLe3/cc-blender-skill)** (MIT): `references/blender-cameras.md`, `references/blender-modeling.md`, `references/blender-lighting.md`, `references/blender-animation.md`, `references/blender-rendering.md`, animation quality gate patterns.
> - **starryark — [github.com/starryark/3d-assisted-illustration](https://github.com/starryark/3d-assisted-illustration)** (MIT): `references/blender-api-lessons.md` (headless stage-gated Python pipeline, numeric placement/visibility asserts, verified Blender 5.x API traps).
> - **Siddharth Ahuja — [github.com/ahujasid/blender-mcp](https://github.com/ahujasid/blender-mcp)** (MIT): Live MCP execution channel compatibility (`execute_blender_code`, viewport inspection).

---

## Dual Execution Channel (Headless Python + Live Blender MCP)

1. **Always write clean, deterministic Python (`bpy`) modules** seeded with an explicit `random.Random(seed)` so the exact same scene builds reproducibly via:
   - **Headless CLI**: `blender --background --factory-startup --python-exit-code 1 --python build_scene.py -- --mode look`
   - **Live Blender MCP**: Execute the module in the connected Blender session (`execute_blender_code`) and save a `.blend` file for interactive inspection/tweaking.
2. **Verify availability before claiming execution**: Never claim Blender or Blender MCP ran unless `blender --version` or a live MCP tool response confirmed it.

---

## Stage-Gated Previs Pipeline (Stills-First QA)

1. **Stage 1 — Look Still (`--mode look`)**:
   - Build clean clay materials (matte grey/off-white `Principled BSDF`, `Roughness 0.78–0.88`, zero neon stripes, muted value separation per subject), AgX color management, and soft directional + fill + rim lighting.
   - Render ONE hero medium/wide still and get user approval on the clay look and proportions before rendering all cuts.
2. **Stage 2 — Measured Framing & Contact Pass (`--mode qa`)**:
   - Use **evaluated world-space mesh vertices** (`depsgraph` + `to_mesh()`), NEVER raw `obj.bound_box` (which lies for rotated meshes).
   - Check every shot (in, middle, out): subject inside 90% action-safe area, zero head/joint crops at frame edges, grounded feet/bases (`contact_offset`), camera distance & clear line of sight (`ray_cast`), pan/tilt angular speed within RED 7-second rule.
3. **Stage 3 — All-Cuts Stills & Contact Sheet (`--mode stills`)**:
   - Render clean 16:9 stills for every cut (in/mid/out) and assemble a `one_per_shot` contact sheet (slate/HUD outside picture or in letterbox bar only).
   - Run the eye pass (`cinematic-previs` + `animation-quality-gate`) and get user approval BEFORE rendering full animations.
4. **Stage 4 — PNG Sequence → H.264 24fps Rec.709 MP4 (`--mode clip`)**:
   - Render **24 fps** with **180° shutter (`motion_blur_shutter = 0.5`)** to a PNG sequence (resilient on crash, `use_persistent_data = True`), then encode with `ffmpeg` (`-c:v libx264 -pix_fmt yuv420p -color_primaries bt709 -color_trc bt709 -colorspace bt709 -crf 18 -movflags +faststart`).
   - For Google Flow / Gemini Omni 1.2 Flash downstream video generation, keep every clip **`≤ 10s`** whenever possible to stay in the lowest credit tier + 0-credit 1080p upscale band.

---

## Mandatory Blender 4.x / 5.x Cross-Version Rules

- **EEVEE Engine Name**: Try `'BLENDER_EEVEE_NEXT'` (4.2–4.x), fall back to `'BLENDER_EEVEE'` (5.0+ / ≤4.1); guard legacy EEVEE attributes with `hasattr()`. For hero clay stills or Apple Silicon Metal GPU, `'CYCLES'` with adaptive sampling + OpenImageDenoise (`OPENIMAGEDENOISE`) gives ultra-clean soft shadows.
- **Layered Actions (Blender 5.x+)**: Never assume `action.fcurves` exists — always use `get_fcurves_compat(action)` traversing `action.layers[].strips[].channelbags[].fcurves` when present.
- **Camera Optics**: Always set `cam.data.sensor_fit = 'HORIZONTAL'` and explicit `sensor_width` (`36.0` Full Frame or `24.89` Super 35). Aim cameras via `TRACK_TO` constraint on a target Empty (`TRACK_NEGATIVE_Z`, `UP_Y`) or `obj.location` (never stale `matrix_world` on a freshly created camera without `view_layer.update()`).
- **Camera Guard**: Always verify `scene.camera is not None` before calling `bpy.ops.render.render()`.
- **Image Output (Blender 5.2+)**: Set `image_settings.media_type = 'IMAGE'` (if attribute exists) BEFORE `image_settings.file_format = 'PNG'`.
- **Clean Geometry**: Name every object with `GEO-`, `CAM-`, `LGT-`, `EMPTY-` prefixes; overlap multi-part joins by 5–15 mm (no hairline seams); apply `Bevel` BEFORE `Subdivision Surface`; call `normals_make_consistent(inside=False)` and smooth shading on organic curved parts.

## Bundled References

- `references/blender-cameras.md` — Bounding-box framer, Track-To rig, focal lengths, DoF, orbit/dolly recipes (`cc-blender-skill`, MIT)
- `references/blender-modeling.md` — Clean multi-part joins, Bevel→SubSurf order, boolean/cleanup (`cc-blender-skill`, MIT)
- `references/blender-lighting.md` — Studio/cinematic three-point, rim, atmospheric lighting (`cc-blender-skill`, MIT)
- `references/blender-animation.md` — Bezier easing, Blender 5.x `get_fcurves_compat`, shape keys, drivers (`cc-blender-skill`, MIT)
- `references/blender-rendering.md` — Cycles/EEVEE 4.x/5.x presets, AgX, Metal GPU, PNG sequence→ffmpeg (`cc-blender-skill`, MIT)
- `references/blender-api-lessons.md` — Verified Blender 5.x API traps, headless CLI flags, numeric verification rules (`3d-assisted-illustration`, MIT)
