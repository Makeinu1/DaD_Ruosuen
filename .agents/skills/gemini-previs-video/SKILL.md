---
name: gemini-previs-video
description: Previs-referenced video directing and prompting for Google Gemini video models (Gemini Omni 1.2 Flash / gemini-omni-1.2-flash, Veo 3.1, and Google Flow). Combines 3D previs MP4 reference videos (<=15s) + locked Gemini reference keyframes (up to 6 images) using natural-language media binding, Walter Murch dramaturgy, 3-detail physical audit, and strict cross-clip visual consistency.
---

# Gemini Previs-to-Video Directing (`Gemini Omni 1.2 Flash` / `Veo 3.1` / `Google Flow`)

Use this skill whenever turning a **3D Previs / Animatic MP4** plus **consistent reference keyframes & asset sheets** into finished video clips in **Google Gemini Video** (`Gemini Omni 1.2 Flash` / `gemini-omni-1.2-flash`, `Veo 3.1`, or `Google Flow`).

> **Upstream Attributions (required by licenses):**
> - **Serge Shima — [github.com/smixs/visual-skills](https://github.com/smixs/visual-skills)** (CC BY 4.0): `references/dramaturgy.md`, `references/universal-rules.md`, `references/veo.md`, `references/animatic-keyframes.md`
> - **Antonio Cárdenas — [github.com/AntonioCardenas/generate-nanobanana](https://github.com/AntonioCardenas/generate-nanobanana)** (MIT): `references/gemini-omni-flash.md`

---

## Hard Technical Rules for Gemini Video (`Gemini Omni 1.2 Flash` / `Google Flow`)

1. **Strict Clip Duration Discipline (`<= 15s`)**:
   - `Gemini Omni 1.2 Flash`: **3s–15s** per generation (`720p / 1080p / 4K @ 24fps`, native audio, extension up to `30s`).
   - **First & Last Frame interpolation**: **3s–10s**.
   - **Reference Video + Reference Image Limits**:
     - `3s–10s` clips: up to **3 reference videos** + up to **6 reference images**.
     - `11s–15s` clips: **1 reference video (the 3D Previs MP4)** + up to **6 reference images**.
   - **Action**: Always slice long previs sequences (e.g., 19s–25s Seedance blocks) cleanly at cut boundaries into **`8s–14s` clips** BEFORE prompting Gemini Video.
2. **Natural-Language Media Binding (CRITICAL!)**:
   - **NEVER** use Seedance tags (`@Video1`, `@Image1`) or deprecated Gemini tokens (`<FIRST_FRAME>`, `<LAST_FRAME>`, `<IMAGE_REF_0>`, `<VIDEO_REF_0>`).
   - Bind EVERY uploaded asset by its upload order in plain natural language, stating BOTH **what to inherit** AND **what to ignore**:
     - Example: *"Follow the exact camera trajectory, lens feel, subject scale, timing, and cut point of the uploaded reference video; completely replace all grey clay blocks, striped pins, and capsule placeholders. Use the first uploaded image as the exact starting frame. Keep the creature anatomy, ruined stone aqueduct arches, white five-petal flowers, and hand-painted gouache brushwork identical to the second and third reference sheets."*
3. **Single-Shot vs Multi-Shot Protection**:
   - By default, `Gemini Omni 1.2 Flash` inserts narrative cuts.
   - For a continuous single-take clip, explicitly include: **`"In a single unbroken scene, no scene cuts."`**
   - For a 2-to-3 shot clip matching a previs cut, state the **exact cut timestamp** matching the uploaded previs video (e.g., `"Exact hard cut at 6.0s matching the uploaded reference video"`).
4. **Motion-Delta Prompting (Do NOT Fight the Reference Images)**:
   - When the start keyframe + asset sheets already lock subject appearance, setting, and style, spend 70% of the prompt directing **what moves, how the camera moves, physical consequences (spray, ripples, drifting petals, light shifts), and the exact ending frame** — do not bloat or contradict the locked stills.

---

## Mandatory 6-Point Dramaturgy & 3-Detail Audit (Before Shipping ANY Prompt)

Read `references/dramaturgy.md` and `references/universal-rules.md`. Every prompt MUST pass ALL checks before delivery:

1. **Banned Adjectives Stripped (`0` tolerance)**: NEVER write `cinematic`, `epic`, `stunning`, `masterpiece`, `beautiful lighting`, `dynamic camera`, `powerful scene`, or naked emotion labels (`he is afraid`). Replace with observable physical facts.
2. **One Primary Camera Move per Shot**: State one motivated move answering *"what changed?"* — otherwise lock the camera still.
3. **Three Concrete Physical Details per Shot**:
   - **Environmental pressure** (e.g., cold blue-silver moonlight shaft, damp shore mist, warm brass lantern light flickering across wet stone)
   - **Physical micro-action** (e.g., shoulders stiffen, dorsal ridge breaks glass water, pectoral wing tilts 22° downward)
   - **Recurring visual/sound motif** (e.g., concentric silver ripples, white petal with tiny pale-gold seed, total breathless silence)
4. **Consequence Prompting**: Describe physical consequences of motion (twin curtains of silver spray exploding outward off the brow; petals stirring gently in wake air; tail dissolving into silver mist before the head).
5. **Mandatory Final Image Rule**: Every clip explicitly states its exact visible final frame so the model lands cleanly at the cut boundary.
6. **Priority Declaration**: On dense clips, declare what MUST survive (1. subject identity & scale, 2. camera path from previs video, 3. palette & brushwork from sheets, 4. exact end frame).

## Bundled References

Read the targeted reference before writing prompts:
- `references/gemini-omni-flash.md` — Current GA `gemini-omni-1.2-flash` specs, 15s limit, R2V + reference video rules, natural-language binding, stateful continuation
- `references/veo.md` — Google Veo 3 / 3.1 syntax, First/Last frame, Ingredients to Video, audio/SFX control, failure fixes
- `references/dramaturgy.md` — Walter Murch's Rule of Six, staging, rhythm staircase, five anchors
- `references/universal-rules.md` — 14 universal video rules, three-detail audit, reference role discipline, priority declaration
- `references/animatic-keyframes.md` — Animatic-to-video motion handoff & keyframe discipline
