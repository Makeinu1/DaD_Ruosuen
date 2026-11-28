# Environment Art & QA Review Reference (`arjun988/blender-skills`, MIT)

## Environment Composition Layers

| Layer | Content | Detail & Value Role |
|---|---|---|
| Foreground | Framing boulders, shore, flora | Medium detail, dark framing silhouette or intimate focus |
| Midground | Hero architecture / viaduct / interaction zone | Hero sculpted detail, mid-bright lit stone (`50–65%`) |
| Background | Distant sunken sanctuary / mist silhouettes | Lower contrast, cooler atmospheric haze (`25–40%`), never brighter than midground |
| Reflection Plane | Water surface tying sky + architecture | Always darker, softer, and slightly ripple-broken vs the real structure above; distinct waterline wetting on emerging masonry |

## Architecture & Storytelling Checklist
- **Waterline Integration**: Structures rising from water MUST have a wet dark base band (`0..2m` above lake Z), slight mist/foam softness or ripple disturbance at contact, and natural perspective alignment — never look like a dry floating cutout glued onto a chrome mirror.
- **Depth & Scale Cues**: Stepped staircases, columns, gables, arches, and negative space (dark breathing water between midground piers and background landmarks).
- **3-Tier Geometry Discipline**: Tier 1 Silhouette → Tier 2 Panel/Structural Breaks (recesses, ribs, bevels) → Tier 3 Narrative Details.

## QA Review Gate & Verdict Template

Severity levels:
- **Blocker**: Broken normals, wrong scale, glaring visual/physical artifact (e.g., chrome-mirror water sticker, clipped white blowout, floating geometry)
- **Major**: Weak silhouette separation, flat depth planes, bad reflection alignment/brightness
- **Minor**: Small shading polish, subtle ripple tuning, naming cleanup
- **Note**: Optional enhancement

```markdown
## QA Verdict: [Scene / Shot]
- Result: SHIP / SHIP WITH NOTES / NO-SHIP
- Blockers: ...
- Majors: ...
- Minors: ...
- Verified Screenshots: [file paths]
```
- **MUST NOT** issue `SHIP` without actually inspecting the post-fix rendered screenshot.
