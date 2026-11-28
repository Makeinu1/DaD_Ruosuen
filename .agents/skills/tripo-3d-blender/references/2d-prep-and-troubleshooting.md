# 2D Reference Prep & Tripo Failure Diagnosis Playbook

Actionable checklist for preparing clean inputs BEFORE spending Tripo credits, plus targeted fixes inside **Blender 5.x** when raw Tripo meshes have defects.

---

## 1. Pre-Generation Reference Prep Checklist (Picture-First Rules)

If using `generate_image` (or drawing/rendering turnarounds in Blender) before sending to Tripo:

- **Backdrop**: Solid flat neutral grey/off-white (`#D5D8DC`), matte, zero gradient skies, zero cast ground shadows, zero water ripples, zero stars/dust particles.
- **Lighting**: Diffused ambient / softbox front-fill lighting only (zero rim flare, zero hard chiaroscuro shadows — shadows in 2D get carved as holes or black texture stains in 3D!).
- **Framing & Distortion**: Centered subject filling ~70–85% of frame with generous margin on all 4 edges (never crop a fluke tip, petal edge, or column cornice!). Use **50mm–85mm / Orthographic**, NEVER wide-angle 21mm distortion.
- **View Separation**:
  - Single-view best angle: **Front-3/4 (30–45° azimuth, ~10–15° slight above)** reveals width, depth, and silhouette overlap best for asymmetric props.
  - Multi-view (`front`, `left`, `right`, `back`): Keep identical eye level, horizon, and proportions across every panel (generate a 2x2 orthographic turnaround sheet first, crop cleanly into 4 separate PNGs, and verify left/right consistency before uploading).

### Asset-Specific Input Adjustments

1. **Whales / Marine Creatures**:
   - Generate from **Orthographic Lateral + Dorsal + Front** OR **clean Front-3/4 + Side** in a flat horizontal neutral glide pose.
   - Spread **pectoral fins slightly downward/outward** cleanly separated from the belly so Tripo does not weld the flippers into the ribcage.
   - Emphasize anatomical landmarks cleanly in 2D: subtle **jawline ridge, recessed eye socket contour, dorsal fluke/ridge crease, wide horizontal tail fluke edge**. (Tiny eye dots get blurred out -> model/insert the real Blender eye cleanly afterwards!)
2. **Botanical / Delicate Flowers (e.g. 5-petal blossoms & drooping buds)**:
   - Tripo struggles with paper-thin (<2mm equivalent) leaves & tightly packed petal overlaps: thin surfaces turn into Swiss-cheese holes or thick mashed lumps.
   - **Best strategy**:
     - Depict the open blossom from a **35–45° top-three-quarter angle** with slightly **sculptural/ceramics-thick petals (~2x real petal thickness)** and clear dark/gap separation between all 5 petals, AND generate the **closed bud** as its own **separate asset**!
     - OR use **H v3.1 `generate_parts=true`** / build petal-array procedural variation in Blender driven by **one crisp Tripo-generated organic calyx + hero petal sculpt**!
3. **Ruined Classical Architecture (Columns, Aqueduct Bays, Buttressed Sanctuary)**:
   - Do **NOT** generate an entire 200-meter ruin bridge in one Tripo call (it turns into mush with tiny 1px texels!).
   - Generate **one clean modular structural bay / capital / fractured pillar drum** (`2–4` reusable weathered kits: *fluted Corinthian/Romanesque column segment*, *weathered voussoir arch span*, *stepped rubble plinth*), then array/rotate/boolean-weather & dress in Blender (`bmesh` / Geometry Nodes / `blender-skills` wet shoreline shader)!
4. **Caverns, Karst Stalactites & Cliffs**:
   - Generate **2–3 rich isolated limestone spire / fractured strata rock formations** with clean sculptural overhang ridges, then instance, scale non-uniformly (within ±20%), rotate, and blend using triplanar World-Space shaders (`anime_cliff_albedo` / procedural bump) inside Blender — infinitely faster and higher-resolution than a muddy whole-cave generation.

---

## 2. Failure Diagnosis & Post-Import Fixes

| Observed Tripo Symptom | Root Cause | Fast Fix (Blender OR Next Try) |
|---|---|---|
| **Ghost lumps or dark halo crust around object** | Input image had mist, lantern glow, dark background, or floor contact shadow | Clean matte `#D8D8D8` isolated PNG cutout -> regenerate; OR in Blender Edit Mode `L` (select linked) / Volume threshold to delete detached blobs |
| **Fins / legs / petals fused with body or each other** | Insufficient negative space in 2D silhouette or P1 low resolution | Separate appendages wider in 2D ref, use **P2 (`quad=true`)** or **`generate_parts=true`**, or clean cut/bridge in Blender Sculpt/Edit mode |
| **Paper-thin petals / ears look chewed or holed** | Surface thinner than Tripo's implicit SDF voxel grid | Thicken silhouette in 2D ref OR solidify (`Solidify Modifier`, 1–3 mm equivalent) + Remesh/Smooth in Blender; best: keep Tripo stem/calyx, attach crisp quad curved petals in Blender |
| **Texture looks muddy dark on the back or has wrong shadow direction** | `delight=True` missed heavy directional shadow OR `delight=False` copied dark painterly lighting | Re-run `tripo_texture_model` with bright neutral studio ref & explicit `delight=True` (for Cycles relighting), OR run procedural Blender HSV lift + Cavity/AO relight pass in Shader Nodes |
| **Face/Eye looks like a blurry texture smudge** | Tripo models coarse eye sockets + paints pupil on 1024 UV | **Always** replace hero close-up eyes cleanly in Blender (sculpt crisp eyelid recess + layered Sphere sclera/iris/cornea glass, per `lida-avatar-workflow/references/eye-modeling.md`) |
| **Mesh won't bend cleanly / pinches when undulating** | Triangulated P1/raw mesh has poles across bending axes | Export P2 with **`quad=true` FBX** OR run Blender `QuadriFlow` + Data Transfer weights (`tripo rig-v2.5` for aquatic/quadruped; never pass `spec` on v2.5) |
| **Object imports huge (100x), sideways, or floating** | Missing metric/orientation normalization on FBX/GLB | Inspect evaluated `world_bounding_box`, rotate upright (`Ctrl+A`), scale to exact world meters, set origin to bottom/COG (`transform_apply(scale=True, rotation=True)`) |
| **GLB throws Python/Blender importer Meshopt error** | Tripo delivered compressed `_meshopt.glb` | Decode with `gltf-transform dequantize in.glb out.glb`, OR re-export Studio asset as FBX (`fbx_preset=blender`, `texture_packaging=embedded`) |
