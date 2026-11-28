# Materials & Lookdev Reference (`arjun988/blender-skills`, MIT)

## Master Material Library & PBR Ranges

| Material | Metallic | Roughness | Notes |
|---|---|---|---|
| Polished metal | 1.0 | 0.1–0.3 | Edge wear raises roughness |
| Concrete / Stone | 0.0 | 0.8–0.95 | Add subtle noise bump + AO dirt |
| Wet Stone / Waterline | 0.0 | 0.15–0.35 | Darken albedo 40–65% near Z=water_level + gradient noise |
| Wood (raw / oiled) | 0.0 | 0.4–0.7 | Anisotropic along grain |
| Glass | 0.0 | 0.0–0.1 | Transmission 1, IOR 1.45 |
| Natural Water / Mirror Lake | 0.0 | 0.02–0.12 | Physical Fresnel (IOR 1.333), multi-scale micro-ripple normal breakup (horizontal stretch!), darker deep tint, reflection attenuation with distance/roughness |
| Fabric | 0.0 | 0.7–0.9 | Sheen 0.3 |

## Procedural Material Patterns

- **Water Staining / Submerged Transition (Critical for flooded ruins!)**:
  - `World Z height gradient + Noise → Darken albedo & lower roughness` right above the waterline (`z = 0..2.2m`) so masonry emerging from water looks genuinely wet and anchored into the lake rather than pasted onto a mirror!
  - Below `z = 0`: rapidly attenuate underwater stone into dark abyssal lake absorption rather than bright underwater geometry cutting a harsh seam.
- **Dirt & Cavity Accumulation**: `Ambient Occlusion (inverted) → multiply with dark recess tint + increase roughness` (carves flutes, steps, pediments, and roof overhangs).
- **Edge Wear / Chiseled Relief**: `Bevel / Pointiness → ColorRamp → subtle light/roughness contrast`.
- **Panel / Block Variation**: `Object Info (Random) / World Coords Noise → ±10% value variation` so stonework never looks like plastic clay blocks.

## Lookdev Loop & Checklist

```
Clay/grey pass → Base materials → Neutral light rig → Beauty light
  → Render Screenshot → Gap list → Fix 1 variable at a time (≤ 3–5 passes) → QA
```

### Mandatory Lookdev Checklist
- [ ] Greyscale value hierarchy reads clearly across all depth planes (Hero > Mid > Far > Void)
- [ ] Specular roughness and reflection physics are believable (no rigid "photocopier mirror" reflections on open water!)
- [ ] Water reflections break up horizontally via subtle dual-scale wave normals and soften/darken slightly relative to real architecture (a reflection is ALWAYS darker and more rippled than the lit structure above it!)
- [ ] Edges catch light via bevels, normals, and raking key angle
- [ ] Emissive strength stays controlled (never keyframe emissive on shared structural geometry to fake bounce)
- [ ] No unintended pure-black crush or clipped-white traps under AgX
- [ ] Before/after screenshots captured and visually compared on every iteration
