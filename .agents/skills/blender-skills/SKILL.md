---
name: blender-skills
description: Senior Technical Art Director & 94-skill Blender production suite (from arjun988/blender-skills v1.3.0, MIT). Orchestrates modeling, environment art, PBR/stylized materials, water/reflection shaders, lookdev loops, cinematic lighting, Cycles/EEVEE rendering, compositing, VFX, and screenshot-backed QA review directly via Blender MCP. Use whenever building, critiquing, lookdev-polishing, lighting, shading, or validating Blender scenes and assets alongside blender-python-previs.
license: MIT
metadata:
  source: https://github.com/arjun988/blender-skills
  version: "1.3.0"
  domain: blender
---

# Blender Skills (`arjun988/blender-skills` v1.3.0)

Senior Technical Art Director orchestration + specialist craft playbooks for **Blender + Blender MCP** (sourced from [arjun988/blender-skills](https://github.com/arjun988/blender-skills), MIT License, 94 specialized skills).
Complements `blender-python-previs` (which owns deterministic `bpy` clay previs scripts & Blender 4.x/5.x API guards) by adding **multi-discipline technical-art direction, PBR/procedural materials, lookdev iteration loops, cinematic lighting/volumetrics, rendering/compositing passes, environment composition, and strict screenshot-backed QA verdicts**.

## When to Use

- Planning or critiquing a multi-discipline Blender scene (environment, architecture, water, hero props, creatures)
- Lookdev & shading reviews: fixing unnatural reflections, blown highlights, flat clay, roughness/Fresnel/specular calibration, water-edge wetting/staining, mist/value separation
- Cinematic lighting & rendering: motivated lights, rim separation, volumetrics, AgX grading, Cycles bounce/glossy optimization, compositor passes
- Reference-image / art-direction matching with a mandatory screenshot-compare loop
- Running an explicit **SHIP / SHIP WITH NOTES / NO-SHIP** QA gate before full animation or export

## Director Pipeline (Always Follow in Order)

```
1. ANALYZE   → Identify asset/shot role (Hero / Midground / Background), mood, style, physical flaws
2. PLAN      → Select active specialist lanes (below) & explicit quality targets
3. BRIEF     → State structured production/fix brief before modifying Blender
4. EXECUTE   → Drive changes directly via Blender MCP / bpy (never narrate manual UI steps)
5. LOOKDEV   → Change ONE major variable per pass (material OR geometry OR light) → render screenshot → gap list (≤ 3–5 iterations)
6. QA GATE   → Screenshot-backed checklist verdict (SHIP / SHIP WITH NOTES / NO-SHIP)
```

## Core Specialist Routing (Active Lanes)

| Problem / Task | Primary Lane | Reference File |
|---|---|---|
| Full scene planning, reference match, multi-skill routing | `blender-director` | [references/skills-guide.md](references/skills-guide.md) |
| Water, stone, metal, roughness, Fresnel, wear, water-staining, master shaders | `materials` + `lookdev` | [references/materials-and-lookdev.md](references/materials-and-lookdev.md) |
| Key/fill/rim lighting, motivated fixtures, color temperature, volumetrics, Cycles/AgX, compositor | `lighting` + `rendering` + `compositing` | [references/lighting-rendering-compositing.md](references/lighting-rendering-compositing.md) |
| Architecture, sunken ruins, layer separation, scale cues, negative space, QA verdicts | `environment-artist` + `qa-review` | [references/environment-and-qa.md](references/environment-and-qa.md) |
| All 94 style / world / biome / horror / genre / export sub-skills | Full 94-skill directory | [references/skills-guide.md](references/skills-guide.md) |

## Non-Negotiable Technical Art Rules

1. **Lookdev Iteration Rule (`lookdev`)**: Always evaluate greyscale value hierarchy first (Hero > Midground > Background > Abyss), verify specular roughness & Fresnel realism, control emissives (never keyframe emission on shared structural materials to fake lighting), and compare before/after screenshots on every pass.
2. **Material Honesty (`materials`)**:
   - Use reusable master materials (`MAT_*`) with physically plausible PBR values (roughness variation, Fresnel reflection, water-line wetting/staining where architecture meets water, AO/dirt cavity contrast).
   - Never rely on a single flat mirror plane (`roughness = 0.025`, flat normal, zero wave breakup, zero waterline transition) when depicting natural submerged architecture — water reflections must obey **Fresnel angle falloff**, **micro-ripple normal breakup**, **depth/distance attenuation**, and **wet dark stone waterlines** on emerging masonry!
3. **Motivated Lighting (`lighting`)**: Every light source must have clear narrative motivation (moon, glowing creature, fixture); separate foreground/midground/background illumination cleanly without accidental light spill across depth planes; avoid flat ambient wash or pure-black crush unless intentional.
4. **AgX & Cycles Discipline (`rendering` / `compositing`)**: Use AgX color management, adjust exposure intentionally rather than blowing out lights, keep OpenImageDenoise + GPU + persistent data enabled, and verify at target camera before full-length renders.
5. **Screenshot-Backed QA Verdict (`qa-review`)**: Never rubber-stamp visual quality without inspecting actual rendered frames; classify remaining defects as **Blocker / Major / Minor / Note** and re-verify after fixes before issuing **SHIP**.

## Full Upstream Skill Pack (94 Skills, MIT)

Upstream source: `https://github.com/arjun988/blender-skills` (v1.3.0, MIT).
Categories covered in [references/skills-guide.md](references/skills-guide.md):
- **Orchestration**: `blender-director`
- **Modeling**: `blender-modeler`, `hard-surface`, `prop-artist`, `vehicle-artist`, `environment-artist`, `vegetation-artist`, `character-artist`, `creature-artist`, `character-archetypes`
- **Production**: `sculpting`, `retopology`, `uv-workflow`, `materials`, `texture-workflow`, `hair-groom`, `cloth-sim`, `lookdev`
- **Technical**: `geometry-nodes`, `lighting`, `camera-cinematography`, `rendering`, `compositing`, `animation`, `rigging`, `vfx-fx`, `physics-sim`
- **Pipeline**: `procedural-modeling`, `scene-assembly`, `set-dressing`, `asset-optimization`, `lod-pipeline`, `collision-proxy`, `export-pipeline`, `unity-export`, `unreal-export`, `godot-export`, `qa-review`, `archviz`
- **Styles / Worlds / Moods / Genres**: 55+ specialized packs (`fantasy-worlds`, `biome-worlds`, `dark-gritty-mood`, `dream-surreal-mood`, `anime-style`, `painterly-style`, `horror-style`, `genre-soulslike`, etc.).
