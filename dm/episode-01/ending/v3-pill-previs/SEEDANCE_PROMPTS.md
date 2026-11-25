# 第一話エンディング『空に降る雪』v3.0 — Seedance 2.5 / Flow 用プロンプトパック

> **DM専用・ネタバレあり。GitHub Pages / `SECTIONS` / `llms.txt` には掲載しない。**
> **設計準拠**：`sirioberati/ai-filmmaking-camera-control-seedance-2-5`（`docs/prompt-anatomy.md` の5ブロック構造）× 正本（`FL-01 v0.8` / `WH-01` / 2026-11-23確定事項）

---

## 使い方（4クリップ分割・全クリップ29秒未満）

全4クリップで **共通の美術基準ボード `@Image1`（`unified_art_board.png`）** と、各クリップ専用の **クリーンな Pill 動画 `@Video1`（HUD・文字なし）** を同時入力します。

| Clip | 入力動画（`@Video1`） | 入力美術ボード（`@Image1`） | 収録カット | 尺 |
|---|---|---|---|---|
| **Clip 1** | `clips/seedance_clip1_C1_C2_fear_setup_11s.mp4` | `unified_art_board.png` | C1 + C2 | **11s** |
| **Clip 2** | `clips/seedance_clip2_C3_C4_overhead_awe_12s.mp4` | `unified_art_board.png` | C3 + C4 | **12s** |
| **Clip 3** | `clips/seedance_clip3_C5_C6_bloom_and_snow_22s.mp4` | `unified_art_board.png` | C5 + C6 | **22s** |
| **Clip 4** | `clips/seedance_clip4_C7_C8_farewell_and_petal_15s.mp4` | `unified_art_board.png` | C7 + C8 | **15s** |

---

## Clip 1（0–11s｜C1 + C2：安堵と予兆 → 湖底の巨影）

```text
【Generation Goal】
Generate a theatrical 2D Japanese anime sequence with rich hand-painted gouache brushwork: first a quiet, intimate lakeside shore with a small warm lantern and one open white five-petal flower among drooping grey-brown dead-grass buds, then a hard cut to four silhouetted adventurers standing at the water's edge as an immense 24-meter dark shadow glides silently beneath the glassy subterranean lake.

【Reference Asset Roles】
@video1 is a coarse-blockout reference: a grey clay cavern set where four adventurers are represented by striped vertical pins and the giant whale is represented by a striped blue-and-black capsule. Use @video1 strictly for camera positions, lens feel, movements, framing, scale relationships, and the exact hard cut at 5.0 seconds. Never show grey clay blocks, stripes, pins, capsules, or geometric grids: rebuild every surface, cavern wall, mirror lake, lantern, plant, silhouette, and submerged giant creature in full theatrical anime painting detail.
@image1 is the unified art-direction and color palette reference: deep midnight indigo (#0A1326), dark sapphire mirror lake (#183054), silver-blue moonlight shaft (#B2D2EE), pure pearl white (#F2F5F8), faint warm champagne gold (#F4DA94), and grey-brown closed buds (#766C60). No neon pink, no plastic 3D CGI look.

【Subjects and Relationships】
- The small white glowing cylinder in @video1 corresponds to an old brass-and-iron camping lantern resting on damp cavern stone, emitting a gentle warm-gold candle glow.
- The single open five-petal white flower beside the lantern corresponds to a young Kousetsuka blossom (pure white five-fold radial symmetry on a slender stem, catching faint moonlight).
- All surrounding small drooping stalks correspond to closed Kousetsuka buds wrapped in grey-brown drooping sepals that look exactly like dry dead grass (no white petals visible yet).
- The four striped vertical pins in Shot 2 correspond to four medieval fantasy adventurers seen purely from behind in dark backlit silhouettes (anonymous cloaks and travel packs, no distinct faces or fixed race features).
- The submerged striped giant capsule in Shot 2 corresponds to the immense dark back and silent shadow of a 24-meter subterranean whale gliding just beneath the dark mirror water.

【Camera and Event Script】
The edit is fixed: exactly two shots with a hard cut at the exact frame of @video1 (5.0s).
Shot 1 (0.0s–5.0s): Slow, gentle 32mm push-in at low ground level past the warm lantern and single open white five-petal flower toward the mirror lake. Around 2.1s, a single water drop falls from the cavern ceiling onto the calm dark water beside the flower, sending crisp silvery concentric ripples outward while tiny dew on the stem trembles faintly. At the moment of the cut, the ripples fade softly across the glass-like water.
Shot 2 (5.0s–11.0s): Hard cut to a 28mm over-the-shoulder vantage behind the four silhouetted adventurers and their small lantern. The camera performs a slow, dread-filled pull-back as the immense 24-meter dark silhouette of a colossal whale glides steadily from left to center beneath the mirror surface, gently distorting the silver moonlight reflection. The four figures subtly tense and shift their weight back in awe. Silent ambient cave drip and deep sub-bass water swell; no dialogue, no music.

【Maintain Consistency】
Keep the exact cavern layout, lantern placement, four adventurers' silhouettes, deep night-blue gouache art style from @image1, and exact framing/cut timing of @video1. Closed buds remain strictly grey-brown and drooping; no pink colors; no capsules or stripes.
```

---

## Clip 2（11–23s｜C3 + C4：巨体の浮上 → 頭上通過と1.5秒の闇）

```text
【Generation Goal】
Generate an awe-inspiring, terrifying theatrical 2D anime sequence: first a colossal 24-meter dark wet whale rises heavily out of the subterranean lake at a shallow angle towering over four tiny silhouetted adventurers, then a hard cut to straight overhead as its massive dark belly passes directly above them, eclipsing the moonlight shaft into breathless darkness and silence.

【Reference Asset Roles】
@video1 is a coarse-blockout reference using striped pins (four 1.7m adventurers) and a giant striped capsule (24m whale). Follow @video1 strictly for camera positions, wide 24mm perspective, movements, true human-to-whale scale, shadow eclipse timing, and the exact hard cut at 7.0 seconds (18.0s master). Rebuild every element completely into hand-painted theatrical anime gouache from @image1; zero clay blocks, zero stripes, zero capsules.
@image1 defines the deep midnight indigo atmosphere, silver-blue moonlight, and painterly water curtains. Keep the whale unlit, wet dark slate-indigo to muted pearl-grey during both shots (it does NOT self-illuminate yet).

【Subjects and Relationships】
- The giant striped capsule corresponds to a 24-meter mythic subterranean whale (WH-01): sleek, majestic, smooth wet dark-indigo and muted pearl-grey skin with gentle ventral grooves and long sweeping pectoral fins, minimal tubercles or mottling, and one small dark intelligent eye. Heavy curtains of silver water cascade off its jaw and flanks as it lifts effortlessly into the cavern air.
- The four striped pins correspond to the same four anonymous backlit adventurer silhouettes standing beside their tiny warm lantern on the wet rock ledge, dwarfed by the 24-meter leviathan.

【Camera and Event Script】
The edit is fixed: exactly two shots with a hard cut at the exact frame of @video1 (7.0s into this clip).
Shot 1 (0.0s–7.0s): Low 24mm oblique three-quarter angle near the rock ledge, holding the four tiny adventurers and their lantern in the lower foreground while tilting upward and pulling back slightly as the colossal 24-meter whale breaches smoothly from the lake at a shallow, heavy angle. It shows no hostility, yet its sheer scale feels overwhelming, like an unbeatable mythic giant. Silver sheets of water pour off its massive fins back onto the mirror lake. At the moment of the cut, its huge head climbs toward the adventurers' shore.
Shot 2 (7.0s–12.0s): Hard cut to a breathless 24mm zenith tilt-up straight from ground level among the four silhouettes. The immense underside and pectoral fins of the 24-meter whale glide silently right overhead, filling almost the entire frame and physically blocking the ceiling moonlight shaft. The rock ledge and small lantern are swallowed in deep shadow. A single drop of water falls past the lens; a tiny glint of moonlight touches the whale's small dark eye during a breathless 1.5-second silence at the peak of compression.

【Maintain Consistency】
Preserve the exact whale anatomy (smooth wet skin, gentle ventral grooves, no pink glow yet), exact 1.7m-to-24m scale ratio, deep night-blue gouache look from @image1, and exact camera choreography/cut frame from @video1.
```

---

## Clip 3（23–45s｜C5 + C6：月光覚醒＆一斉開花 → 空に降る雪・空中オービット）

```text
【Generation Goal】
Generate the emotional climax of a theatrical 2D Japanese anime film: the 24-meter whale sweeps into the ceiling moonlight shaft with one powerful tail stroke and ignites in luminous pearl-white light, instantly transforming the adventurers' grey-brown dead-grass shore into a blazing field of pure white five-petal flowers; then a hard cut into the film's sole soaring aerial camera orbit as thousands of white petals with faint champagne-gold glowing seeds suspend for one second and rise like reverse snow into the cavern sky around the gliding luminous whale.

【Reference Asset Roles】
@video1 is a coarse-blockout reference showing the exact camera sweep, bloom wave, 1.2-second petal hover-freeze, and soaring ArcAndRise + Orbit aerial trajectory around the 24m striped capsule. Follow @video1 strictly for camera path, lens feel (24mm in Shot 1, 28mm in Shot 2), timing, and the exact hard cut at 8.0 seconds (31.0s master). Replace every clay block, striped pin, and capsule with rich hand-painted theatrical anime gouache from @image1.
@image1 sets the exact palette: deep midnight indigo cavern, silver-blue moonlight shaft, luminous pearl-white whale glow, pure white five-petal blossoms, and tiny 2–3mm faint champagne-gold glowing fruits at the base of each detaching petal. Strictly NO neon pink.

【Subjects and Relationships】
- The giant capsule transforms from wet dark pearl-grey into a radiant pearl-white and ice-blue luminous whale as its nose touches the moonlight shaft; light ripples head-to-tail across its smooth flanks and gentle ventral grooves.
- The drooping grey-brown stalks around the four silhouettes and across the opposite cape visibly straighten upright and burst open into pure white five-fold radial (five-petal) Kousetsuka flowers in a sweeping wave from foreground to far shore.
- Each rising snow particle is a real translucent white petal carrying a tiny 2–3mm faint champagne-gold glowing seed at its base.

【Camera and Event Script】
The edit is fixed: exactly two shots with a hard cut at the exact frame of @video1 (8.0s into this clip).
Shot 1 (0.0s–8.0s): Wide 24mm pan-and-reveal from behind the four adventurers and lantern. Clearing their heads, the whale executes one decisive, graceful sweep of its horizontal tail fluke and surges diagonally upward into the silver moonlight shaft. On contact (~2.0s into clip), a wave of ice-blue and pearl-white radiance washes head-to-tail along its 24-meter body. Instantly as that radiance touches the shore (~2.5s–7.5s), every drooping grey-brown dead-grass bud at the adventurers' feet and across the distant cape uncurls upright and bursts into luminous white five-petal blossoms in one breathtaking wave.
Shot 2 (8.0s–22.0s): Hard cut to a 28mm vantage low above the radiant white flower field. For the first 1.2 seconds, thousands of real white petals with faint champagne-gold seeds detach simultaneously and hang completely still in mid-air—a silent magical beat. Then, as the petals stream gracefully upward like snow falling into the sky, the camera lifts off the ground for the first and only time, soaring upward through the rising floral snow in a sweeping, majestic 140-degree aerial orbit around the glowing 24-meter pearl-white whale while the dark mirror lake below reflects the inverted starfield of petals.

【Maintain Consistency】
Keep five-petal symmetry on every blossom, grey-brown-to-white transformation strictly in Shot 1, pearl-white and champagne-gold palette (zero pink), smooth whale skin with gentle grooves, and exact aerial orbit geometry of @video1.
```

---

## Clip 4（45–60s｜C7 + C8：月への別れ → 静寂と最後の一枚）

```text
【Generation Goal】
Generate the tender, lingering finale of a theatrical 2D Japanese anime film: returning to ground level behind the four silhouetted adventurers and their warm lantern as the luminous 24-meter whale ascends into the ceiling moonlight fissure while petals fall gently downward like real snow; then a hard cut to the exact locked-off lakeside framing of the opening shot where, after two seconds of stillness, one single glowing petal lands beside the young flower and sends a quiet ripple across the water before fading softly to darkness.

【Reference Asset Roles】
@video1 is a coarse-blockout reference controlling the exact wide ground-level pull-back (22mm) in Shot 1, the locked-off 32mm lakeside framing in Shot 2, and the exact hard cut at 7.0 seconds (52.0s master). Replace every clay block, striped pin, and capsule completely with hand-painted theatrical anime gouache from @image1; never show capsules, pins, or stripes.
@image1 sets the deep midnight indigo, silver moonlight, pearl-white snow, and warm champagne-gold lantern/fruit light.

【Subjects and Relationships】
- The four striped pins in Shot 1 correspond to the same four anonymous backlit adventurer silhouettes standing together beside their small warm lantern on the shore, gazing peacefully upward as a united party.
- The ascending striped capsule corresponds to the luminous pearl-white 24-meter whale gliding smoothly into the silver full-moon fissure in the cavern roof until even its tail tip dissolves into silver light.
- In Shot 2, the mature shore blossoms have dispersed their petals, leaving only the lone young intact five-petal white flower (P0) beside the warm lantern and calm mirror lake—mirroring the very first shot of the film.

【Camera and Event Script】
The edit is fixed: exactly two shots with a hard cut at the exact frame of @video1 (7.0s into this clip).
Shot 1 (0.0s–7.0s): Wide 22mm low ground-level vantage behind the four silhouettes and small glowing lantern, pulling back slowly and peacefully. Overhead, the luminous 24-meter whale rises straight into the silver ceiling fissure and merges into the moonlight around 6.2s. Released from its lift, the white floral petals drift gently downward like real snow around the four quiet figures.
Shot 2 (7.0s–15.0s): Hard cut to a completely locked-off 32mm shot identical in composition to the opening shot (lantern lower-left, lone young five-petal flower P0 beside calm mirror water). For the first 2.0 seconds, absolute stillness—"was it a dream?" Then at 9.0s into this clip, one last white petal carrying a faintly glowing champagne-gold seed drifts gently down from upper-right, settling onto the mirror water beside P0 at 12.2s and sending delicate silver ripples across the dark glass surface. Its warm golden light softly dims, lingering in quiet stillness before a gentle fade to black in the final second. No text, no end card.

【Maintain Consistency】
Match Shot 2's exact framing, lantern, and P0 placement to Clip 1 Shot 1; keep the four silhouettes anonymous and united; maintain deep night-blue hand-painted gouache from @image1 with zero CGI gloss and zero stripes or capsules.
```
