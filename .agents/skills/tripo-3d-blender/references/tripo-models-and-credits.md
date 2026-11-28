# Tripo Model Families, Options & Reference Credits

> Verified against `Tripo-Developer/Tripo-Studio-MCP`, `Tripo-Developer/Tripo3D-Plugin-dsh`, and `ploikmjr/tripo-claude-blender-pipeline` (MIT). Check live Studio schemas before quoting final account balances or plan limits.

## 1. Model Family Selection Matrix

| Product Name | Studio MCP `family` / `model_version` | CLI / API Model ID | Poly Limits | Native Quads (`quad=true`) | Supported Exclusives & Best Use |
|---|---|---|---|---|---|
| **Smart Mesh P1 (Fast)** | `smart_mesh` / `Nexus-v1.0-20260214` | `tripo-p1` | 500 – 20,000 tris | No (Triangles only) | Fast silhouettes, steady static props, boulders, cheap exploration (lower credits) |
| **Smart Mesh P2** | `smart_mesh` / `Nexus-v2.0-20260801` | `tripo-p2` / `P2-20260801` | 48 – 50,000 tris / 48 – 25,000 quads | **Yes** (forces FBX) | **First choice for bending characters, creatures, clean quad hero meshes**; supports `symmetry` |
| **HD v3.1** | `hd` / `v3.1-20260211` (up to `v3.5-20260815` where available) | `tripo-v3.1` | 500 – 1M std / 2M detailed tris; 50,000 quads | Yes (+5cr addon) | Dense sculpt source for normal baking, **explicit `generate_parts=true`**, `negative_prompt`, `geometry_quality` |

### Critical Parameter Traps (Avoid Silent Rejections)

1. **`texture: false` constraint**: When `texture=false` (e.g., generating geometry first or using `generate_parts=true`), **OMIT `pbr`, `texture_quality`, and `delight` completely** — passing `false` to them is still rejected!
2. **`generate_parts: true` (HD v3.1 only)**: Requires `texture=false` and explicit `segmentation_granularity` (`simple | balanced | detailed`). Run `texture` as a second chained step (`--then texture:pbr=...`) on `@last` or the resulting `model_id`.
3. **Quads force FBX**: Setting `quad=true` on P2 or H v3.1 exports **FBX** (NOT GLB — GLB conversion of native quads is rejected or triangulates them). Use `--format FBX` (`fbx_preset=blender`, `texture_packaging=embedded`).
4. **Rigging Model & Species Split**:
   - **Biped ONLY**: `rig-v3.0` supports `spec` (`unity`, `mixamo`, `unreal`, `vrm`, `actorcore`) and preset motions (`idle`, `walk`, `run`, `jump`, `climb`, `dive`, `slash`, `shoot`, `hurt`, `fall`, `turn`) + Text2Motion.
   - **Non-Biped Creatures**: MUST use **`rig-v2.5`** with `topology`/`rig_type` in `{quadruped, aquatic, serpentine, hexapod, octopod, avian}` and **OMIT `spec` completely** (sending `spec` fails on v2.5!). Note: presets are limited (`preset:quadruped:walk`, `preset:aquatic:march`, `preset:serpentine:march`, none for avian).
   - **Static Props / Architecture / Plants**: **Never auto-rig**.
5. **`texture_quality` Tiers**: `standard` = 2K, `detailed` = 4K (+10cr), `extreme` = 8K (+20cr, Max/tier restricted). Check `delight=False` (preserve painterly colors) vs `delight=True` (neutral PBR albedo).

---

## 2. Reference Credit Guide (`Tripo-Developer` Documentation)

> Reference estimates only — MCP cannot inspect Studio trial allowances or final plan pricing directly. Always disclose estimated credits and wait for confirmation on paid CLI/API batches.

### Modeling Base Credits

| Operation | Base Credits | Notes |
|---|---:|---|
| Text / Single-Image **HD v2.5 / v3.0 / v3.1** | **15** | Multi-view HD also 15 (Paid plans) |
| Text / Single-Image **Smart Mesh P1** | **35** | Multi-view P1 also 35 (Paid plans) |
| Text / Image / Multiview **Smart Mesh P2** | **100** | P2 gives clean topology/quads (up to 4 generation tries when UI option enabled) |

### Common Add-ons & Post-Processing Credits

| Operation / Option | Extra Credits | Notes |
|---|---:|---|
| `texture_quality: standard` (2K) | **+10** | Base texture component |
| `texture_quality: detailed` (4K) | **+20 total** | +10 on top of 2K texture |
| `pbr: true` | **+5** | Metallic/Roughness PBR maps (turn `pbr=false` for stylized/painted if unrequested) |
| `generate_parts: true` | **+20 to +30** | HD v3.1 only; requires `texture=false` initially |
| `segment` (split existing mesh) | **+40** | Use `complete` (no credits on paid plans) to cap cut holes |
| `decimate` / `smart_low_poly` | **30 – 40** | `decimate:v3.0` takes `smart_uv=true` (retopologizes 500–20k faces) |
| `rig` (auto-rig) | **20** | Preceded by **free** `rig-check` compatibility gate! |
| `convert` (simple vs complex FBX) | **5 – 10** | `scale_factor`, `pivot_to_center_bottom`, `texture_format=PNG`, `texture_size`, `quad` trigger complex convert (10) |
| `image multiview` / `ai completion` / `motion retarget` | **0 credits** (tier-gated) | Requires Starter/Pro/Max/Member plan entitlement |

---

## 3. Blender MCP `generate_3d` vs Studio Web/MCP Decision

| Scenario | Recommended Tool | Why |
|---|---|---|
| Quick single prop / organic base straight into Blender scene | `blender:generate_3d(provider="tripo")` | Zero file-download friction; immediate import into Blender; resume timed-out tasks via `job=...` without paying twice |
| Multi-view 4-angle precision creature (`quad=true` FBX), `generate_parts=true`, `delight=False`, `smart_low_poly`, or P2 retries | **Tripo Studio Web (`studio.tripo3d.ai`) or Tripo Studio MCP / CLI -> import `.fbx`/`.glb` into Blender** | Exposes explicit `P2-20260801` + `quad=true`, `delight`, `generate_parts`, `fbx_preset=blender`, `segmentation` and credit controls |
| Meshopt `.glb` won't import cleanly in local Blender | `gltf-transform dequantize in.glb out.glb` | Decodes Meshopt buffer compression + unquantizes attributes before Blender import |
