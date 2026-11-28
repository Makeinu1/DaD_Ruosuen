# Lighting, Rendering & Compositing Reference (`arjun988/blender-skills`, MIT)

## Lighting Workflow & Rules

```
Art Direction → Motivated Key Light → Fill / Shadow Floor → Rim Separation
  → Depth-Plane Accents → Volumetrics / Mist → AgX Grade → Validation Renders
```

- **Motivate every light**: visible fixture, moon shaft, or bioluminescent hero creature.
- **Color Temperature Separation**:
  - Moonlight / subterranean mist: `7500K–9000K` cool blue-silver
  - Practical warm / candle / lantern: `1800K–3200K`
- **Depth-Plane Light Control**:
  - Never allow a background accent light to spill backward onto midground architecture (position behind midground or narrow spread/angle).
  - Never allow artificial fill/accent area lamps to produce fake white rectangular specular reflections in glossy water (`visible_glossy = False`, `visible_camera = False`).
  - Keep reflection energy strictly lower than direct sky/architecture luminance (Fresnel + dark water absorption + subtle wave-normal scatter).

## Cycles & Color Management Rules

- **Engine**: Cycles + GPU (OptiX/Metal) + OpenImageDenoise + Adaptive Sampling + `use_persistent_data = True` for sequences.
- **Bounces**: Preview 6–8, Production 8–12 (ensure glossy bounce ≥ 2 for clean water reflection without fireflies; clamp indirect glossy if needed).
- **Color Management**: `AgX` View Transform (`Base Contrast` or `Medium Contrast`), tune exposure rather than clipping lights to pure white.
- **Preview vs Final**: Fast low-sample Stills-First QA renders (16–32 samples) before launching multi-hundred-frame renders.

## Compositor Beauty Stack (Optional Post)

```
Combined → Exposure / Color Balance (AgX-aware) → Subtle Glare (Fog Glow sparingly) → Subtle Vignette → Output
```
- Never crush blacks in comp to hide lighting issues; fix the light/shader first.
