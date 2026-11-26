# 第一話エンディング『空に降る雪』v5.0 決定版（96秒・全15カット・6クリップ）— Seedance 2.0 本番投入キット

> **DM専用・ネタバレあり。GitHub Pages / `SECTIONS` / `llms.txt` には掲載しない。**
> **共通美術参照 `@Image1`**：`unified_art_board_v5.png`（v5.0 専用 4絵統合・OKLCH/Rec.709 パレット付）
> **全クリップ25秒以下**（12s / 13s / 19s / 25s / 14s / 13s — Seedance の 29秒上限に対して安全な余裕あり）

## 本番投入対応表（そのまま Seedance 2.0 へドラッグ＆ドロップ）

| Clip | 尺 | `@Video1`（動き・カメラ・尺ロック） | `@Image1`（共通スタイル） | `@Image2`（シーン専用キーフレーム） | 出力ファイル名 |
| :--- | :---: | :--- | :--- | :--- | :--- |
| **Clip 1** | 12s | `seedance_v5_clip1_C1_C2_omen_and_shadow_12s.mp4` | `unified_art_board_v5.png` | `v5_keyframe_01_c1_shore_omen.jpg` | `final_clip1.mp4` |
| **Clip 2** | 13s | `seedance_v5_clip2_C3_C4ab_headon_nearmiss_13s.mp4` | `unified_art_board_v5.png` | `v5_keyframe_02_c3_headon_rush.jpg` | `final_clip2.mp4` |
| **Clip 3** | 19s | `seedance_v5_clip3_C5ab_C6a_bloom_to_snowstorm_19s.mp4` | `unified_art_board_v5.png` | `v5_keyframe_03_c6c_1plus3_master.jpg` | `final_clip3.mp4` |
| **Clip 4** | 25s | `seedance_v5_clip4_C6bcd_playful_abyss_arch_25s.mp4` | `unified_art_board_v5.png` | `v5_keyframe_03_c6c_1plus3_master.jpg` | `final_clip4.mp4` |
| **Clip 5** | 14s | `seedance_v5_clip5_C7ab_ascent_and_moon_dissolve_14s.mp4` | `unified_art_board_v5.png` | `v5_keyframe_04_c7b_moon_dissolve.jpg` | `final_clip5.mp4` |
| **Clip 6** | 13s | `seedance_v5_clip6_C7c_C8_true_snow_and_petal_13s.mp4` | `unified_art_board_v5.png` | `v5_keyframe_01_c1_shore_omen.jpg` | `final_clip6.mp4` |

- **最終結合＆音響合成（ワンコマンド）**：6本が揃ったら `final_clips/final_clip1.mp4`〜`final_clip6.mp4` に置いて `python3 dm/episode-01/ending/v5-pill-previs/assemble_final_screening.py` を実行すると、**1080p 24fps / Rec.709 タグ付 / -14 LUFS 音響合成済み（`kousetsuka_v5_master_audio_96s.wav`）** の 2026-12-23 上映マスターが完成します。

---

## Clip 1（0–12s｜C1 + C2：安堵と予兆 → 湖底の不穏な巨影｜12秒）
- 入力：`seedance_v5_clip1_C1_C2_omen_and_shadow_12s.mp4` + `unified_art_board_v5.png` + `v5_keyframe_01_c1_shore_omen.jpg`

```text
【Generation Goal】
Generate a theatrical 2D Japanese anime sequence in hand-painted gouache: first an intimate subterranean lakeside with a warm brass lantern and one open white five-petal flower among drooping grey-brown dead-grass buds, then a hard cut behind four silhouetted adventurers as a colossal 24-meter dark shadow glides silently beneath the glassy mirror lake directly onto a head-on course toward them. In the far background mist across the dark lake, faint silhouettes of sunken weathered stone arch bridge ruins stand quietly half-submerged.

【Reference Asset Roles】
@video1 is a coarse-blockout reference (grey clay cavern, ruined stone arches across the lake, 4 striped vertical pins for adventurers, 1 giant striped capsule for a 24m whale). Follow @video1 strictly for camera positions, lens feel (32mm -> 28mm), scale, timing, and the exact hard cut at 6.0s. Replace every clay block, pin, capsule, and stripe completely with theatrical anime painting detail from @image1.
@image1 sets the palette: deep midnight indigo (#0A1326), dark sapphire mirror lake (#183054), silver-blue moonlight (#B2D2EE), pearl white (#F2F5F8), warm champagne gold (#F4DA94), grey-brown closed buds (#766C60). Zero neon pink, zero plastic CGI.

【Camera and Event Script】
The edit is fixed: exactly two shots with a hard cut at 6.0s matching @video1.
Shot 1 (0.0s–6.0s): Slow 32mm push-in low by the warm brass lantern and lone five-petal Kousetsuka flower (strictly five-fold radial symmetry). At 2.4s, one ceiling droplet falls onto the mirror lake beside the flower, spreading crisp silver ripples while dew on the stem trembles.
Shot 2 (6.0s–12.0s): Hard cut to a 28mm vantage directly behind the four anonymous backlit silhouettes and lantern, pulling back slowly in quiet dread as the immense 24m dark shadow curves beneath the mirror surface directly toward the center of the shore. Distant mossy sunken stone arch bridge silhouettes loom faintly across the misty dark water. Quiet cave drip and deep low sub-bass swell; no dialogue, no music.
```

---

## Clip 2（12–25s｜C3 + C4a + C4b：正面直進膨張 → ランタン脇ニアミス → 闇と『眼』1.8秒無音｜13秒）
- 入力：`seedance_v5_clip2_C3_C4ab_headon_nearmiss_13s.mp4` + `unified_art_board.png`

```text
【Generation Goal】
Generate a heart-stopping, breathless theatrical 2D anime tension sequence: first a colossal 24-meter dark wet whale breaks the water DEAD-CENTER coming straight at four tiny silhouetted adventurers like an unstoppable black wall; then a hard cut tight beside their lantern at eye-level as the giant head rushes inches from impact before lifting at the very last second to graze overhead; then a hard cut into total eclipse darkness as its huge smooth flank and one small dark intelligent eye glide silently past the lens during 1.8 seconds of total silence.

【Reference Asset Roles】
@video1 controls the exact dead-center head-on 36mm expansion (0–6s), tight eye-level 24mm last-second near-miss tilt (6–9.5s), close 40mm eye-pass hold (9.5–13s), and exact hard cuts at 6.0s and 9.5s. Replace all clay geometry, pins, capsules, and stripes with hand-painted theatrical anime gouache from @image1.
@image1 defines the wet unlit dark-indigo whale skin (smooth with gentle ventral grooves, long sweeping pectoral fins, one small dark calm eye). The whale does NOT self-illuminate yet.

【Camera and Event Script】
The edit is fixed: exactly three shots with hard cuts at 6.0s and 9.5s matching @video1.
Shot 1 (0.0s–6.0s): Dead-center symmetrical 36mm low shot behind the four tiny silhouettes and warm lantern. Straight ahead along the exact center axis, the colossal 24m dark whale breaches low at eye height coming STRAIGHT AT THE LENS—zero lateral drift, expanding relentlessly from 25% to 85% of the frame width while twin sheets of silver water explode outward from its flanks. Pure collision dread.
Shot 2 (6.0s–9.5s): Hard cut tight beside the lantern at eye level (24mm wide). The colossal dark head surges straight toward the shore until warm lantern gold flickers across its wet lower jaw—then ONLY in the final 1.1 seconds pitches smoothly upward just two meters above the four figures, swallowing them in deep eclipse shadow.
Shot 3 (9.5s–13.0s): Hard cut to a tight 40mm dark close-up in total eclipse shadow. The immense dark wet flank slides horizontally past at close range, and the whale's small dark calm eye glides gently across center frame catching one quiet pinpoint of silver moonlight during 1.8 seconds of total breathless silence.
```

---

## Clip 3（25–44s｜C5a + C5b + C6a：月光覚醒 → 地表20cm一斉開花 → 離陸1秒静止→空へ大チルト＝3層大花吹雪｜19秒）
- 入力：`seedance_v5_clip3_C5ab_C6a_bloom_to_snowstorm_19s.mp4` + `unified_art_board.png`

```text
【Generation Goal】
Generate the joyous turning point and breathtaking floral-snowstorm eruption of a theatrical 2D Japanese anime film: first the 24m whale surges into the silver moonlight shaft and ignites in radiant pearl-white light; then a hard cut down to a poetic 20cm ground-level lens watching dry grey-brown dead-grass buds burst open in a luminous wave of pure white five-petal flowers from underfoot all the way across the mossy parapets of the sunken ruined stone arch bridge; then a hard cut to a 21mm low vantage where thousands of white petals with faint champagne-gold seeds lift off the blossoms, FREEZE completely motionless in mid-air for 1.0 silent second, and then billow skyward as the camera tilts seamlessly from ground level up into a vast 220-meter subterranean cathedral filled edge-to-edge with a three-layer floral snowstorm!

【Reference Asset Roles】
@video1 strictly controls the 24mm moonlit ignition pan (0–5s), 35mm ultra-low 20cm ground-level bloom wave (5–10s), 21mm 1.0s gravity-freeze lift-off followed by continuous ground-to-sky tilt reveal (10–19s), and exact hard cuts at 5.0s and 10.0s. Replace every clay block, pin, arch mesh, and capsule with lush hand-painted theatrical anime gouache from @image1.
CRITICAL BACKGROUND LAYERING (Depth-Stratified 1+3 Fusion):
- Midground (crisp silhouette with cool silver moonlight rim & lake reflection): Sunken old-era ruined stone aqueduct arch bridge with a wide broken central span and blooming white five-petal Kousetsuka crowning its mossy stone parapets.
- Atmospheric mist separator: Soft cool blue-silver haze band along the horizon separating midground stone arches from deep cavern rock.
- Far outer flanks ONLY (heavily blurred into misty midnight blue, low contrast, ZERO pillars in center sky or behind the whale/moon): Colossal natural limestone stalactite columns framing the extreme left and right distance.

【Camera and Event Script】
The edit is fixed: exactly three shots with hard cuts at 5.0s and 10.0s matching @video1.
Shot 1 (0.0s–5.0s): 24mm back-of-party pan-up. Clearing the shore, the 24m whale sweeps its tail once and glides into the silver skylight beam, igniting head-to-tail in pearl-white and ice-blue radiance.
Shot 2 (5.0s–10.0s): Hard cut to a 35mm camera skimming just 20cm above the mossy ground. Drooping grey-brown sepal buds straighten upright and burst open into crisp five-fold white flowers in a cascading wave from the foreground pebbles out across the dark water to ignite white blossoms along the top of the ruined stone arch bridge!
Shot 3 (10.0s–19.0s): Hard cut to a 21mm ultra-wide low vantage. From 10.6s to 11.6s, thousands of translucent white petals (each bearing a tiny 2–3mm faint champagne-gold seed) detach and FREEZE completely still in mid-air for one breathless silent second above the shore and dark mirror lake. At 11.6s, gravity releases—the petals burst upward into a space-filling three-layer snowstorm (far glowing mist dots, mid swirling five-petal snowflakes filling the entire cavern volume, and subtle soft bokeh foreground petals) as the camera smoothly rises and tilts skyward to reveal the luminous white whale gliding into the vast 220m abyss above the ruined stone arches!
```

---

## Clip 4（44–69s｜C6b + C6c + C6d：360°ロール×石橋くぐり → 220m大空洞×1+3融合・40°バンク大旋回 → 22°優しい一瞥0.6xスロー｜25秒）
- 入力：`seedance_v5_clip4_C6bcd_playful_abyss_arch_25s.mp4` + `unified_art_board.png`

```text
【Generation Goal】
Generate the joyous, mythic, feature-film-grade centerpiece of a theatrical 2D Japanese anime ending inside a vast 220-meter subterranean cathedral filled with a three-layer luminous floral snowstorm: first a 35mm parallel aerial glide watching the pearl-white 24-meter whale perform a graceful, unhurried 360-degree barrel roll above the broken central breach of a sunken ruined stone arch bridge with double parallax against misty far stalactite pillars; then a hard cut to the iconic 21mm ultra-wide cathedral tableau as the whale banks playfully at 40 degrees across the vast dark mirror lake, mirrored upside-down alongside the symmetrical reflections of the ruined stone arches; then a hard cut to an intimate 42mm gentle hold as the whale glides close toward the shore, dips its long pectoral fin, and turns a warm 22-degree downward glance toward the four adventurers in a tender 0.6x slow-motion breath before curving gently skyward.

【Reference Asset Roles】
@video1 strictly controls the 35mm barrel-roll parallel track (0–8s), 21mm grand abyss 1+3 fusion orbit (8–16s), 42mm intimate warm-glance 0.6x slow-mo hold (16–25s), exact whale roll/bank/glance acting, double parallax between midground ruined stone arches and far-flank misty stalactites, and exact hard cuts at 8.0s and 16.0s. Replace every clay block, arch mesh, stalactite, and capsule completely with theatrical Ghibli/Makoto-Shinkai-caliber hand-painted gouache from @image1.
CRITICAL SPACE-FILLING FLORAL SNOWSTORM: Petals fill the ENTIRE 220-meter space naturally in three depth layers (far delicate mist sparks, mid luminous white-and-champagne-gold five-petal snowflakes gently swirled by the whale's passing wings without collapsing into narrow ropes, and occasional large soft-focus foreground bokeh petals). Zero neon pink.
CRITICAL DEPTH-STRATIFIED 1+3 BACKGROUND: Crisp silver-rimmed ruined stone aqueduct arches (with blooming white flowers on mossy parapets and symmetrical lake reflections) in midground; soft blue-silver atmospheric mist separating them from colossal blurred natural limestone stalactite pillars strictly along the extreme outer flanks; center sky and full moon completely open and uncluttered.

【Camera and Event Script】
The edit is fixed: exactly three shots with hard cuts at 8.0s and 16.0s matching @video1.
Shot 1 (0.0s–8.0s): 35mm parallel aerial glide tracking the luminous 24m whale as it executes one joyous, slow, weightless 360-degree barrel roll right over the wide collapsed central span of the sunken stone arch bridge. Midground stone arches stream past smoothly while distant misty stalactite pillars drift slowly behind them (cinematic double parallax), surrounded by swirling three-layer floral snow.
Shot 2 (8.0s–16.0s): Hard cut to a sweeping 21mm ultra-wide grand tableau of the 220m subterranean ocean. Framed between the weathered stone arch spans (mirrored symmetrically in the glassy black water) and the far misty rock columns on the flanks, the glowing whale sweeps gracefully across the center in a playful 40-degree bank while its luminous upside-down twin glides beneath the mirror surface through a sky-and-lake ocean of floral snow.
Shot 3 (16.0s–25.0s): Hard cut to a warm, intimate 42mm vantage near the shore. Cruising effortlessly closer through drifting white-and-gold snow, the luminous whale slows smoothly into a tender 0.6x slow-motion breath (18.5s–21.5s), tilts its sweeping pectoral fin, and turns its head gently 22 degrees downward to cast one serene, affectionate glance with its small dark eye toward the four adventurers—before softly lifting its nose and beginning its slow ascent toward the moonlit ceiling.
```

---

## Clip 5（69–83s｜C7a + C7b：背中越し見送り＆残された雪 → 85mm真横望遠・尾びれから頭へ満月へ溶け還る｜14秒）
- 入力：`seedance_v5_clip5_C7ab_ascent_and_moon_dissolve_14s.mp4` + `unified_art_board.png`

```text
【Generation Goal】
Generate the poignant, tear-jerking moonlight farewell of a theatrical 2D Japanese anime film: first a 21mm ultra-wide ground return behind four tiny silhouetted adventurers and their warm lantern watching the luminous 24m whale ascend above the ruined stone arch bridge toward the ceiling moon while the "left-behind" floral snow slows and begins drifting gently downward; then a hard cut to a poetic 85mm telephoto SIDE-PROFILE view of the whale gliding serenely across the radiant giant Full Moon, smoothly dissolving FROM TAIL TIP TO HEAD (tail fluke first -> smooth flanks -> sweeping pectoral fins -> and finally its calm forward-looking head last) into pure silver-white moonlight, leaving 1.5 seconds of breathless stillness on the luminous Full Moon.

【Reference Asset Roles】
@video1 strictly controls the 21mm ground-level ascent tilt behind the 4 pins and ruined stone arches (0–6s), the 85mm telephoto side-profile framing across the giant Full Moon (6–14s), the EXACT tail-to-head progressive dissolution timing (7.0s tail tip -> 12.4s head fades completely -> 12.4s–14.0s pure Full Moon hold), and the exact hard cut at 6.0s. Rebuild every block, pin, arch, and capsule into luminous theatrical anime gouache from @image1.

【Camera and Event Script】
The edit is fixed: exactly two shots with a hard cut at 6.0s matching @video1.
Shot 1 (0.0s–6.0s): 21mm ultra-wide low vantage behind the four anonymous backlit silhouettes and tiny warm lantern, with the blooming ruined stone arch bridge mirrored across the dark lake ahead. Having completed its great swim, the luminous pearl-white whale curves skyward toward the bright ceiling fissure and full moon. Left behind in the cathedral air, the space-filling floral snow loses its upward pull and begins to drift downward like gentle winter snow.
Shot 2 (6.0s–14.0s): Hard cut to a breathtaking 85mm telephoto side-profile view framing the giant glowing silver Full Moon framed by dark cavern fissure rock. The luminous 24-meter whale glides horizontally and serenely across the moon's face in crisp side profile. Returning its borrowed moonlight without haste, the whale dissolves smoothly FROM TAIL TO HEAD: at 7.2s the tail fluke turns to incandescent silver mist and vanishes; at 8.8s the rear torso melts into pure white glow; at 10.2s the long pectoral wings dissolve; and at 11.5s–12.4s its calm forward-looking head fades last into the moon's pure light, leaving 1.6 seconds of radiant, serene Full Moon with a few drifting white snowflakes.
```

---

## Clip 6（83–96s｜C7c + C8：本物の雪の祝福 → C1完全同一構図・最後の一枚と波紋｜13秒）
- 入力：`seedance_v5_clip6_C7c_C8_true_snow_and_petal_13s.mp4` + `unified_art_board.png`

```text
【Generation Goal】
Generate the quiet, warm, deeply moving epilogue of a theatrical 2D Japanese anime film: first a 24mm low wide shot behind four silhouetted adventurers beside their warm lantern as thousands of released white petals drift down like real gentle winter snow across them, the glassy lake, and the distant ruined stone arch bridge; then a hard cut to a completely locked-off 32mm shot mirroring Shot 1 of the entire film (lantern, lone five-petal flower P0, calm mirror water), where after two seconds of stillness one final glowing white petal settles gently onto the water beside P0, spreads a single silver ripple, and lets its faint champagne-gold glow fade softly to black.

【Reference Asset Roles】
@video1 strictly controls the 24mm gentle pull-back snowfall (0–6s), the exact locked-off 32mm C1 mirror-symmetry composition (6–13s), the final petal landing at 9.0s (t=92.0s master) with silver ripple, the fade to black from 11.6s to 13.0s, and the exact hard cut at 6.0s. Match @image1's midnight-indigo, warm lantern gold, silver moonlight, and hand-painted gouache texture with zero neon pink.

【Camera and Event Script】
The edit is fixed: exactly two shots with a hard cut at 6.0s matching @video1.
Shot 1 (0.0s–6.0s): Gentle 24mm pull-back behind the four anonymous backlit silhouettes and glowing brass lantern. With the whale returned to the moon, the suspended white petals drift steadily downward like true quiet winter snow, dusting their shoulders, drifting across the dark mirror lake, and settling along the distant sunken stone arch bridge. Warm, grateful quiet.
Shot 2 (6.0s–13.0s): Hard cut to a completely locked-off 32mm camera matching the exact framing of the opening shot (warm brass lantern, lone five-petal white flower P0, glassy dark water). After two serene seconds, one last glowing white petal drifts down onto the mirror water beside P0 at 9.0s, spreading crisp silver ripples across the dark reflection. The faint champagne-gold seed glow diminishes gently to stillness, fading smoothly to black at 13.0s.
```
