# 第一話エンディング『空に降る雪』— Gemini 動画生成（Gemini Omni 1.2 Flash / Google Flow）全9クリップ・プロンプト集

> **適用スキル**：`gemini-previs-video`（`AntonioCardenas/generate-nanobanana` × `smixs/visual-skills` 統合）
> **対象モデル**：**`Gemini Omni 1.2 Flash`（`gemini-omni-1.2-flash`）** / Google Flow（Veo 3.1 / Omni Flash 1.2）
> **全 9 クリップすべて `8s–14s`（15秒上限内・合計ちょうど 96.0 秒）**
> **厳守事項**：
> 1. **自然言語バインド徹底**：`@Video1` や `<IMAGE_REF_0>` などのタグは一切使わず、アップロード順に自然な英語で役割指定済み。
> 2. **脱AI臭＆3ディテール監査通過済み**：`cinematic` / `epic` / `stunning` / `masterpiece` 等の禁止語ゼロ。全カットに「①環境圧・②身体的マイクロ動作・③視覚／音のモチーフ・④明確な最終フレーム」を明記。
> 3. **音響運用**：本プロジェクトにはフレーム完全同期のマスター音響（`kousetsuka_v5_master_audio_96s.wav`・`-14.21 LUFS`）がすでにあるため、最終結合時は動画生成音声をミュートしてマスター WAV へ差し替えます（プロンプト内の音指定は物理的な間のガイドとして機能します）。

---

## 全 9 クリップ投入対応表（各クリップ：参照動画 1 本 ＋ 参照画像 3〜4 枚 ≤ 6 枚上限）

| Clip | 尺 | カット構成 | アップロードする参照動画（1本） | アップロードする参照画像（順不同厳禁・この順で投入） | 出力ファイル名 |
| :---: | :---: | :--- | :--- | :--- | :--- |
| **G1** | **12s** | `C1 + C2` (0–12s) | `gemini_previs_G1_C1_C2_omen_shadow_12s.mp4` | 1. `KF-G1`（始点） / 2. `SheetA_whale_pcs.png` / 3. `SheetB_flower_arch.png` | `final_G1.mp4` |
| **G2** | **13s** | `C3 + C4a + C4b` (12–25s) | `gemini_previs_G2_C3_C4ab_headon_13s.mp4` | 1. `KF-G2`（始点） / 2. `SheetA_whale_pcs.png` / 3. `SheetB_flower_arch.png` | `final_G2.mp4` |
| **G3** | **10s** | `C5a + C5b` (25–35s) | `gemini_previs_G3_C5ab_ignite_bloom_10s.mp4` | 1. `KF-G3`（始点） / 2. `KF-G3b`（C5b地表開花） / 3. `SheetA_whale_pcs.png` / 4. `SheetB_flower_arch.png` | `final_G3.mp4` |
| **G4** | **9s** | `C6a` 単カット (35–44s) | `gemini_previs_G4_C6a_freeze_tilt_9s.mp4` | 1. `KF-G4`（始点） / 2. `SheetA_whale_pcs.png` / 3. `SheetB_flower_arch.png` | `final_G4.mp4` |
| **G5** | **8s** | `C6b` 単カット (44–52s) | `gemini_previs_G5_C6b_barrel_roll_8s.mp4` | 1. `KF-G5`（始点） / 2. `SheetA_whale_pcs.png` / 3. `SheetB_flower_arch.png` | `final_G5.mp4` |
| **G6** | **8s** | `C6c` 単カット (52–60s) | `gemini_previs_G6_C6c_abyss_1plus3_8s.mp4` | 1. `KF-G6`（始点） / 2. `SheetA_whale_pcs.png` / 3. `SheetB_flower_arch.png` | `final_G6.mp4` |
| **G7** | **9s** | `C6d` 単カット (60–69s) | `gemini_previs_G7_C6d_warm_glance_9s.mp4` | 1. `KF-G7`（始点） / 2. `SheetA_whale_pcs.png` / 3. `SheetB_flower_arch.png` | `final_G7.mp4` |
| **G8** | **14s** | `C7a + C7b` (69–83s) | `gemini_previs_G8_C7ab_moon_dissolve_14s.mp4` | 1. `KF-G8a`（C7a始点） / 2. `KF-G8b`（C7b満月溶解） / 3. `SheetA_whale_pcs.png` / 4. `SheetB_flower_arch.png` | `final_G8.mp4` |
| **G9** | **13s** | `C7c + C8` (83–96s) | `gemini_previs_G9_C7c_C8_true_snow_13s.mp4` | 1. `KF-G9`（始点） / 2. `KF-G1`（C8終点ミラー対称） / 3. `SheetA_whale_pcs.png` / 4. `SheetB_flower_arch.png` | `final_G9.mp4` |

---

## Clip G1（12s｜`C1 + C2`：安堵と予兆 → 湖底の不穏な巨影）
- **設定**：`16:9` / `24fps` / `12s`
- **投入**：`gemini_previs_G1_C1_C2_omen_shadow_12s.mp4` ＋ `KF-G1`, `SheetA_whale_pcs.png`, `SheetB_flower_arch.png`

```text
Follow the exact camera trajectories, framing, scale, pacing, and the single hard cut at 6.0 seconds from the uploaded reference video, completely replacing all grey clay blocks, striped pins, and capsule placeholders with hand-painted 2D Japanese theatrical animation gouache matching the uploaded reference images. Use the first uploaded image as the exact starting frame. Keep the brass lantern, four anonymous backlit silhouettes, and dark submerged 24-meter whale consistent with the second reference sheet, and keep the five-petal white flower, drooping grey-brown buds, and distant half-submerged ruined stone aqueduct arches consistent with the third reference sheet.

Shot 1 (0.0s to 6.0s): Slow gentle forward push-in low across the damp dark shore rock toward the glowing brass lantern and lone five-petal white flower surrounded by drooping grey-brown closed buds. Damp cavern air holds completely still. At 2.4 seconds, one silver water droplet falls from above onto the glassy dark sapphire lake beside the flower, spreading crisp concentric silver ripples as tiny dew beads on the flower stem tremble once.

Hard cut at 6.0 seconds matching the reference video.

Shot 2 (6.0s to 12.0s): Low wide view positioned directly behind the four tiny anonymous backlit adventurer silhouettes and their small warm lantern on the shore, pulling back very slowly. Beneath the dark mirror surface of the lake, a colossal 24-meter dark shadow glides silently out of the mist near the distant sunken stone arches and curves straight onto a center approach toward the shore. The four figures' shoulders stiffen slightly and one steps half a pace back while the flame in the brass lantern flickers softly. Final frame holds on the massive dark submerged silhouette aimed dead-center at the four tiny figures.

Sound guide: quiet damp cave air, single crisp water drop at 2.4 seconds, then a deep low underwater rumble swelling slowly from 6.0 seconds; no dialogue, no music. Priorities: preserve exact layout and cut timing from the reference video, matte gouache texture with zero CGI gloss and zero neon pink.
```

---

## Clip G2（13s｜`C3 + C4a + C4b`：正面直進膨張 → ランタン脇ニアミス → 闇と眼 1.8秒無音）
- **設定**：`16:9` / `24fps` / `13s`
- **投入**：`gemini_previs_G2_C3_C4ab_headon_13s.mp4` ＋ `KF-G2`, `SheetA_whale_pcs.png`, `SheetB_flower_arch.png`

```text
Follow the exact camera trajectories, framing, overwhelming scale contrast, and exact hard cuts at 6.0 seconds and 9.5 seconds from the uploaded reference video, completely replacing every clay block, striped pin, and capsule with hand-painted 2D Japanese theatrical animation gouache matching the uploaded reference images. Use the first uploaded image as the exact starting frame. Preserve the unlit wet dark slate-indigo 24-meter whale, small dark calm eye, four tiny anonymous silhouettes, and brass lantern from the second reference sheet, and the distant dark stone arches from the third reference sheet.

Shot 1 (0.0s to 6.0s): Dead-center symmetrical low camera behind the four tiny silhouettes and warm lantern. Straight ahead along the exact center axis at eye height, the colossal unlit dark wet whale breaches low straight toward the camera with zero sideways drift, expanding steadily until its broad wet brow fills almost the entire frame while twin roaring curtains of silver spray explode outward left and right off its flanks. Water mist blows across the lantern flame, flattening it backward.

Hard cut at 6.0 seconds matching the reference video.

Shot 2 (6.0s to 9.5s): Tight low eye-level camera right beside the brass lantern on the wet rock. The towering wet dark head surges straight toward the shore until warm golden lantern light reflects visibly along the wet ventral grooves of its lower jaw inches from impact—then only in the final second pitches smoothly upward just two meters above the four ducking silhouettes, swallowing the entire shore in heavy eclipse darkness as its immense belly passes overhead.

Hard cut at 9.5 seconds matching the reference video.

Shot 3 (9.5s to 13.0s): Tight dark side-angle hold inside deep eclipse shadow. The immense smooth wet dark flank glides horizontally across the lens at close range, and the whale's small dark intelligent eye slides calmly across center frame catching a single quiet pinpoint glint of silver moonlight with zero aggression. Final frame holds on the calm eye gliding quietly out of frame into velvet darkness.

Sound guide: roaring wall of rushing water building relentlessly from 0.0 to 9.4 seconds, then cutting sharply at 9.5 seconds into complete breathless silence through 13.0 seconds; no dialogue, no music. Priorities: keep the whale unlit dark slate-indigo throughout all 13 seconds (no glow yet), preserve collision tension until 8.5 seconds, exact cuts from the reference video.
```

---

## Clip G3（10s｜`C5a + C5b`：月光覚醒 → 地表 20cm 超低空の一斉開花ウェーブ）
- **設定**：`16:9` / `24fps` / `10s`
- **投入**：`gemini_previs_G3_C5ab_ignite_bloom_10s.mp4` ＋ `KF-G3`, `KF-G3b`, `SheetA_whale_pcs.png`, `SheetB_flower_arch.png`

```text
Follow the exact camera moves, framing, timing, and single hard cut at 5.0 seconds from the uploaded reference video, completely replacing every grey clay block, striped pin, and capsule with hand-painted 2D Japanese theatrical animation gouache matching the uploaded reference images. Use the first uploaded image as the starting frame of Shot 1 and match the second uploaded image's low shore bloom composition for Shot 2. Preserve the whale's transition from dark slate to pearl-white radiance from the third reference sheet, and the exact five-petal white flower, drooping grey-brown buds, and ruined stone aqueduct arches from the fourth reference sheet.

Shot 1 (0.0s to 5.0s): Wide upward pan from behind the four dark backlit silhouettes and brass lantern on the shore. Clearing the shore, the colossal 24-meter whale executes one broad horizontal tail stroke and glides diagonally into the towering silver-blue moonlight shaft descending from the cavern ceiling. As the moonlight touches its brow, a wave of soft pearl-white and pale ice-blue radiance travels smoothly head-to-tail across its wet body and sweeping pectoral fins, turning the dark mirror water bright silver below. The four figures slowly lower their defensive arms and tilt their heads upward.

Hard cut at 5.0 seconds matching the reference video.

Shot 2 (5.0s to 10.0s): Low ground-skimming glide just twenty centimeters above the mossy shore rock beside the warm brass lantern, looking out across the mirror lake toward the sunken ruined stone arch bridge. Touched by the whale's silver light, the drooping grey-brown sepal buds straighten upright one after another and burst open into crisp pure-white five-petal blossoms in a sweeping wave—starting right beside the foreground stones and lantern, leaping across the water, and lighting up pure-white five-petal clusters all along the mossy broken parapets of the distant stone arches. Final frame holds on the glowing shore blossoms and illuminated stone bridge arches reflected in the glassy water.

Sound guide: deep gentle wing-and-tail air rush as the whale enters moonlight, followed by delicate cascading glass-like chimes spreading left to right as the flowers bloom. Priorities: strictly five petals per flower, exact cut at 5.0 seconds, matte gouache brushwork with zero neon pink.
```

---

## Clip G4（9s｜`C6a` 単カット：花弁離陸 1 秒重力静止 → 地上から空へ連続大チルト＝3層大花吹雪）
- **設定**：`16:9` / `24fps` / `9s`（**単カット厳守！**）
- **投入**：`gemini_previs_G4_C6a_freeze_tilt_9s.mp4` ＋ `KF-G4`, `SheetA_whale_pcs.png`, `SheetB_flower_arch.png`

```text
In a single unbroken scene, no scene cuts. Follow the exact continuous low-to-high camera lift and upward tilt trajectory and timing from the uploaded reference video, completely replacing all clay meshes and primitive flowers with hand-painted 2D Japanese theatrical animation gouache matching the uploaded reference images. Use the first uploaded image as the exact starting frame. Keep the pearl-white 24-meter whale identical to the second reference sheet, and keep the five-petal blossoms, detached white petals with tiny warm champagne-gold seeds, mossy sunken stone arch bridge, and mist-softened far outer stalactite pillars identical to the third reference sheet.

From 0.0 to 1.6 seconds, the low wide camera holds steady above the blooming shore and dark mirror lake as hundreds of translucent pure-white single petals—each carrying a tiny warm champagne-gold seed at its base—detach softly from the shore blossoms and mossy stone bridge, rising one to two meters into the air and FREEZING completely motionless in mid-air for one silent suspended second (0.6s to 1.6s). At 1.6 seconds, the stillness breaks: the suspended petals billow gracefully skyward in every direction, filling the entire 220-meter subterranean cathedral volume in three natural depth layers (fine far mist sparks, mid swirling white-and-gold petals filling the whole space, and a few larger softly blurred foreground petals). In one smooth continuous upward lift and tilt matching the reference video (1.8s to 9.0s), the camera rises off the shore and tilts skyward to reveal the luminous pearl-white whale gliding serenely over the wide collapsed central gap of the ruined stone arch bridge while heavily mist-softened giant stalactite pillars frame only the extreme outer flanks. Final frame holds on the vast open cathedral sky filled edge-to-edge with drifting floral snow and the glowing whale soaring above the symmetrical reflected arches.

Sound guide: one hushed crystal breath during the 1-second mid-air freeze, swelling into a warm airy upward rush of snow and distant cathedral resonance as the camera tilts skyward. Priorities: strictly one unbroken take with zero cuts, true 1-second visible petal freeze before rising, space-filling three-layer snowstorm, matte gouache look.
```

---

## Clip G5（8s｜`C6b` 単カット：360°緩やかバレルロール × 崩れた石造アーチ橋くぐり並走）
- **設定**：`16:9` / `24fps` / `8s`（**単カット厳守！**）
- **投入**：`gemini_previs_G5_C6b_barrel_roll_8s.mp4` ＋ `KF-G5`, `SheetA_whale_pcs.png`, `SheetB_flower_arch.png`

```text
In a single unbroken scene, no scene cuts. Follow the exact parallel aerial tracking glide, whale barrel-roll rotation, double parallax, and pacing from the uploaded reference video, completely replacing all striped capsules and clay blocks with hand-painted 2D Japanese theatrical animation gouache matching the uploaded reference images. Use the first uploaded image as the exact starting frame. Keep the pearl-white 24-meter whale identical to the second reference sheet, and keep the midground ruined stone aqueduct arch bridge (with blooming white parapet flowers), atmospheric blue-silver mist veil, far outer-flank blurred stalactite pillars, and three-layer white-and-gold floral snowstorm identical to the third reference sheet.

Gliding sideways in smooth parallel motion beside the luminous 24-meter whale, the camera tracks the creature as it executes one unhurried, weightless, playful 360-degree barrel roll directly above the wide collapsed central breach of the sunken ruined stone arch bridge spanning the lower third of the frame. Its long sweeping pectoral fins rotate cleanly up through the drifting petals and back around with calm aquatic grace, stirring nearby white-and-champagne-gold petals gently without pulling them into rigid ropes. As the camera tracks laterally, the sharper silver-rimmed stone arches in the midground stream past steadily while the heavily mist-blurred colossal natural stalactite pillars far behind the mist veil drift much more slowly, creating deep subterranean parallax while leaving the central air behind the whale completely open. Final frame completes the full 360-degree roll cleanly with the whale leveling out peacefully inside the drifting three-layer snowstorm.

Sound guide: soft weightless rushing air and one distant resonant gentle whale song echoing softly through the cathedral space. Priorities: strictly one unbroken shot with zero cuts, clean complete 360-degree slow barrel roll matching the reference video, crisp midground stone arches cleanly separated by mist from blurred far stalactites.
```

---

## Clip G6（8s｜`C6c` 単カット：1+3融合・220m大空洞決定画・40°遊びバンク＆鏡面対称）
- **設定**：`16:9` / `24fps` / `8s`（**単カット厳守！**）
- **投入**：`gemini_previs_G6_C6c_abyss_1plus3_8s.mp4` ＋ `KF-G6`, `SheetA_whale_pcs.png`, `SheetB_flower_arch.png`

```text
In a single unbroken scene, no scene cuts. Follow the exact slow sweeping ultra-wide orbital arc, horizon placement, whale banking curve, and mirrored lake symmetry from the uploaded reference video, completely replacing every clay mesh and stripe with hand-painted 2D Japanese theatrical animation gouache matching the uploaded reference images. Use the first uploaded image as the exact starting frame. Keep the pearl-white 24-meter whale identical to the second reference sheet, and keep the depth-stratified 1+3 subterranean architecture and three-layer floral snowstorm identical to the third reference sheet.

Sweeping slowly in a stately wide arc across the vast 220-meter midnight-indigo subterranean ocean, the camera reveals the entire cathedral space at once: weathered sunken stone aqueduct arches extending from left and right with white five-petal Kousetsuka blooming along their mossy parapets and casting a crisp dark symmetrical reflection in the glassy sapphire lake; a soft cool blue-silver mist veil separating the midground bridge from heavily blurred giant limestone stalactite pillars strictly along the extreme left and right outer edges; and the towering silver moonlight shaft shining cleanly behind the right arches. Through the wide open central sky above the collapsed bridge gap, the luminous pearl-white 24-meter whale banks playfully at 40 degrees in an unhurried horizontal curve, mirrored upside-down in the calm dark mirror ocean below, while three natural depth layers of white petals with tiny pale-gold seeds drift across the entire cathedral air and skim just above the mirror water. Final frame holds on the majestic symmetrical tableau of sky whale, reflected lake whale, glowing stone arches, and endless falling snow.

Sound guide: swelling warm cathedral resonance, soft drifting crystalline shimmer, and one gentle distant whale call. Priorities: strictly one unbroken take with zero cuts, crisp depth separation between midground stone arches and far misty stalactites, zero pillars behind the whale or moon shaft, matte gouache look.
```

---

## Clip G7（9s｜`C6d` 単カット：22°優しい一瞥＆0.6xスローの静かな間 → 上空への針路）
- **設定**：`16:9` / `24fps` / `9s`（**単カット厳守！**）
- **投入**：`gemini_previs_G7_C6d_warm_glance_9s.mp4` ＋ `KF-G7`, `SheetA_whale_pcs.png`, `SheetB_flower_arch.png`

```text
In a single unbroken scene, no scene cuts. Follow the exact intimate tracking hold, whale deceleration, gentle downward glance, and final upward curve from the uploaded reference video, completely replacing every clay capsule and stripe with hand-painted 2D Japanese theatrical animation gouache matching the uploaded reference images. Use the first uploaded image as the exact starting frame. Keep the pearl-white 24-meter whale's smooth skin, long sweeping pectoral fins, and small dark calm eye identical to the second reference sheet, and the drifting three-layer white-and-gold petals identical to the third reference sheet.

Cruising unhurriedly closer through the quiet midnight-indigo air filled with drifting white petals and tiny warm champagne-gold seeds, the luminous pearl-white whale slows smoothly into a tender 0.6x slow-motion breath between 2.5 and 5.5 seconds. Its long pectoral fin tilts gently downward, its slow S-wave tail undulation eases almost to a glide, and its head turns subtly 22 degrees toward the camera—its small dark intelligent eye catching a soft pinpoint of silver moonlight in one quiet, affectionate glance toward the adventurers below. Between 6.0 and 9.0 seconds, normal calm pace resumes as the whale gently levels its wings, sweeps its tail fluke once with soft grace, and curves its nose upward toward the high moonlit ceiling. Final frame shows the luminous whale ascending away into the drifting snow toward the distant silver light above.

Sound guide: full ambience eases back into intimate quiet breath and four soft delicate celesta notes during the 2.5–5.5 second slow-motion glance. Priorities: strictly one unbroken take with zero cuts, subtle restrained 22-degree warm eye glance (never cartoonish), exact whale identity and matte gouache brushwork.
```

---

## Clip G8（14s｜`C7a + C7b`：背中越し見送り＆残された雪 → 85mm真横望遠・尾から頭へ満月溶解）
- **設定**：`16:9` / `24fps` / `14s`
- **投入**：`gemini_previs_G8_C7ab_moon_dissolve_14s.mp4` ＋ `KF-G8a`, `KF-G8b`, `SheetA_whale_pcs.png`, `SheetB_flower_arch.png`

```text
Follow the exact camera moves, framing, progressive tail-to-head dissolution timing, and single hard cut at 6.0 seconds from the uploaded reference video, completely replacing all grey clay blocks, striped pins, and capsule placeholders with hand-painted 2D Japanese theatrical animation gouache matching the uploaded reference images. Use the first uploaded image as the starting frame of Shot 1 and match the second uploaded image's exact telephoto full-moon side-profile framing and dissolution aesthetic for Shot 2. Preserve the whale anatomy and four shore silhouettes from the third reference sheet, and the ruined stone aqueduct arches and golden-seeded white petals from the fourth reference sheet.

Shot 1 (0.0s to 6.0s): Low wide view positioned behind the four tiny anonymous backlit silhouettes and small glowing brass lantern on the rocky shore, tilting slowly upward across the dark mirror lake and mossy blooming stone arch bridge. Having finished its swim, the luminous pearl-white whale ascends smoothly into the towering silver moonlight column toward the distant full moon high in the cavern fissure. Left behind in the wide cavern air, the floating white floral snow loses its upward lift and begins drifting softly downward around the stone bridge and shore.

Hard cut at 6.0 seconds matching the reference video.

Shot 2 (6.0s to 14.0s): Compressed telephoto side-profile view framing the giant, perfectly round luminous silver-white full moon framed only at the dark corners by rough cavern fissure rock with nothing cutting across the moon's face. Gliding serenely horizontally from left to right directly across the face of the moon, the luminous pearl-white 24-meter whale returns its borrowed moonlight by dissolving smoothly FROM TAIL TO HEAD: at 7.4 seconds the crescent tail fluke turns into shimmering incandescent silver-white mist and disappears; by 9.8 seconds the rear torso melts cleanly into pure moonlit vapor; by 11.2 seconds the long sweeping pectoral fins dissolve into light dust; and by 12.3 seconds its calm, gentle forward-looking head fades last into the pure white radiance of the full moon. Final 1.7 seconds (12.3s to 14.0s) hold quietly on the lone radiant full moon with a few delicate white petals drifting slowly past.

Sound guide: bittersweet ascending shimmer softening gradually as the tail-to-head dissolve completes, ending in pure quiet moonlit stillness. Priorities: exact cut at 6.0 seconds, unobstructed full moon, unmistakable TAIL-TO-HEAD dissolution order (head disappears LAST), matte gouache look.
```

---

## Clip G9（13s｜`C7c + C8`：本物の雪の祝福 → C1完全同一構図・最後の一枚と波紋）
- **設定**：`16:9` / `24fps` / `13s`
- **投入**：`gemini_previs_G9_C7c_C8_true_snow_13s.mp4` ＋ `KF-G9`, `KF-G1`, `SheetA_whale_pcs.png`, `SheetB_flower_arch.png`

```text
Follow the exact camera motion, locked-off final framing, final petal landing timing at 9.0 seconds, and single hard cut at 6.0 seconds from the uploaded reference video, completely replacing all clay pins and blocks with hand-painted 2D Japanese theatrical animation gouache matching the uploaded reference images. Use the first uploaded image as the exact starting frame of Shot 1, and lock Shot 2 to the EXACT camera composition, damp shore rock, weathered brass lantern, lone five-petal white flower, and distant misty stone arches of the second uploaded image (KF-G1) for perfect opening-to-ending mirror symmetry.

Shot 1 (0.0s to 6.0s): Gentle slow pull-back low behind the four tiny anonymous backlit silhouettes and their warm brass lantern on the rocky shore. With the whale gone, hundreds of pure-white petals drift steadily downward like quiet real winter snow—brushing softly past the four figures' shoulders, dusting the wet shore stones, and floating down across the glassy dark sapphire lake and distant weathered stone aqueduct arches. Warm, grateful calm; one figure quietly lets out a visible breath in the cool cavern air.

Hard cut at 6.0 seconds matching the reference video.

Shot 2 (6.0s to 13.0s): Completely locked-off, motionless camera mirroring the exact composition of the second uploaded image (warm brass lantern, lone open five-petal white flower on the wet rock, calm dark sapphire mirror water, faint sunken stone arches in the far mist). Two serene seconds pass in stillness. At 8.5 seconds, one final glowing translucent white petal carrying a tiny warm champagne-gold seed drifts gently down from above and lands softly on the glassy mirror lake beside the lone flower at exactly 9.0 seconds, spreading crisp concentric silver ripples across the water. Its faint golden seed glow softens and fades peacefully as the entire frame fades smoothly to black from 11.6 to 13.0 seconds.

Sound guide: soft gentle winter snowfall air fading into quiet damp cave stillness, then one crisp tender silver water-droplet chime at 9.0 seconds mirroring the opening drop before fading into silence. Priorities: exact locked-off mirror match to the second uploaded image (KF-G1) in Shot 2, exact petal landing and ripple at 9.0 seconds, smooth fade to black at 13.0 seconds, matte gouache texture with zero neon pink.
```
