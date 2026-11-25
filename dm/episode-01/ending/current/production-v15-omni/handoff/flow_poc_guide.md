# Google Flow × Gemini Omni 1.2 Flash｜パイロット3カット検証手順書（v14.10 基準）

> **DM専用・ネタバレあり。**
> 対象環境：Google AI Pro アカウントの **Google Flow**（ブラウザ操作・追加課金なし。日次 50 クレジット＋月 1,000 クレジット枠）。

---

## 0. 共通の準備（Google Flow の設定）

1. Google Flow で新規プロジェクト（例：`Ruosuen_v14_10_Omni_PoC`）を作成する。
2. 画面下の入力欄右側の設定を開き、以下を設定する：
   - **種別**：動画（既存動画の編集／リスタイル）
   - **モデル**：**`Omni 1.2 Flash`**
   - **アスペクト比**：`16:9`（横長）
   - **解像度**：まずは **`720p`**（検証用。合格後に 1080p アップスケール）
   - **出力数**：`1`（クレジット節約のため最初は1本ずつ）
3. 画面右上の「＋」→「アップロード」から、**該当カットのクリーン MP4**（`01_base_videos/`）と **参照画像（テキスト除去済み・`02_reference_images/`）** をアップロードする。
   - **注意**：元ファイルの `WH01_identity_sheet.png` や `R14_v15i_gold.jpg` には文字が焼き込まれているため、文字の誤転写を防ぐ目的で、**文字のない採用原画**（`CUT05_KEY_whale_emerges.png`、`CUT09_KEY_climax.png`、`CUT02_KEY_moon.png`、`style_ref_painterly.png`）および文字帯を切り落とした `02_reference_images/WH01_clean_side_oblique.png` を使用する。
4. アップロードした**プリヴィズ動画**のサムネイル右上の「︙」→「**プロンプトに追加**」を選ぶ。
5. 同様に参照画像もプロンプトへ追加し、下の英語プロンプトを貼り付けて**秒数・消費クレジットを確認**してから生成する。

---

## 1. 最優先カット：R14（8.0秒・90mm望遠・花雪の長回し）

**この1本を最初に試す理由**：Blender 本命案（`v15i`）と同じカットであり、直接比較できる。「鯨が光源（芯は白・縁は桜・ひと漕ぎで淡い金）」「手前の花吹雪（白い雪が近さで染まる）」「背景に岩壁や月光を勝手に描かない」という最重要ポイントを一度に判定できる。

- **ベース動画**：`R14_v14_10_clean.mp4`（1280×720 / 24fps / **8秒**）
- **設定秒数**：`8秒`
- **参照画像（最大3枚）**：
  1. `dm/episode-01/ending/images/adopted/CUT09_KEY_climax.png`（ガッシュ・水彩の夜景画風、花弁の透け感）
  2. `dm/episode-01/ending/images/adopted/CUT05_KEY_whale_emerges.png`（鯨の滑らかな皮膚・腹の畝・小さな暗い眼）
  3. `dm/episode-01/ending/v8/keyframe-test/refs/style_ref_painterly.png`（筆致と光の粒のニュアンス）

### Prompt R14-A（忠実リスタイル型・まずこれから試す）
```text
Restyle the attached base video into a hand-painted Japanese animated film scene (soft gouache and watercolor brushwork like Makoto Shinkai / high-craft theatrical anime background art), matching the brushwork and texture of the reference paintings.

STRICTLY KEEP UNCHANGED from the base video:
- Exact fixed telephoto camera framing, angle, timing, and 8-second pacing.
- Exact position, scale, swimming trajectory, gentle 40-degree roll, and slow tail-stroke rhythm of the giant pale whale.
- The open, deep dark indigo-violet night void of the vast underground cavern: DO NOT add rock walls, ceiling arches, mountains, water surface, moon, or diagonal moonbeams. Keep the background purely dark open cavern air with soft atmospheric depth.
- The exact flow and timing of the drifting petals (slow, readable foreground snow-like petals plus the softer trailing river of petals behind the whale).

ENHANCE visually:
- Whale appearance: smooth, majestic 24-meter white whale with subtle ventral grooves and a small dark eye (no barnacles, no horns, no scars, no ribbons). The whale itself is the luminous light source: bright pearl-white core, delicate sakura-pink luminous rim and aura, with a soft warm pale-gold wave pulsing from head to tail on each tail stroke (matching the color shifts already visible in the base video) before settling back to pearl-white and sakura.
- Flower petals: delicate translucent five-petal blossoms/single white petals with tiny warm-gold seed tips, drifting slowly like snow with gentle shallow depth-of-field bokeh in the foreground. Distant petals stay crisp white snow; only petals near the whale borrow its soft sakura-pink and pale-gold glow.
- Lighting and mood: solemn, breathtaking, quiet nocturnal wonder. Natural painterly grain, smooth motion, zero flicker.
- Audio: completely silent (no music, no speech, no sound effects). No text, no watermarks, no extra creatures, no people.
```

### Prompt R14-B（原画リッチ表現型・Aが少し地味すぎた場合の比較用）
```text
Transform the attached base video into a richly painted theatrical anime sequence in luminous gouache and watercolor, inspired by the attached reference paintings and the lyrical drifting-petal atmosphere of "5 Centimeters per Second".

Keep the EXACT camera lock, whale position, size, orientation, swimming motion, and dark open cavern space from the base video. Do NOT invent rock cliffs, cavern ceilings, lake water, a moon, or extra shafts of light.

Make the giant whale look breathtaking and painterly: smooth sculpted skin with delicate pale ventral grooves and a small dark glistening eye, glowing from within as the sole light source—brilliant pearl-white along its core, luminous sakura-blossom pink along its edges and aura, with a radiant pale-gold pulse flowing head-to-tail during each slow tail stroke.
Render the drifting petals with exquisite tactile beauty: crisp, slightly translucent milky-white petals with tiny softly glowing pale-gold seeds at their base, gently tumbling in three-dimensional depth—softly defocused foreground petals catching the whale's pink-and-gold backlight, while distant petals remain pure white snow against deep midnight indigo air.
Silent video, no music, no voices, no text, no added objects.
```

### R14 生成後の「対話的追加修正（Multi-Turn Edit）」テンプレート
Flow で最初の出力を見てズレた点だけ 1 つずつ直す場合の指示文：
- **背景に岩壁や斜めの月光柱を勝手に描いた場合**：
  > `Remove all added rock walls, cliffs, and light shafts from the background. Keep the background purely open dark midnight indigo cavern air exactly as in the original base video. Keep the whale, its motion, and the petals unchanged.`
- **鯨が白飛び／均一なピンクになった場合**：
  > `Keep the whale's core bright pearl-white with subtle smooth skin shading, gentle belly grooves, and a visible small dark eye. Limit the sakura-pink glow to the whale's rim and nearby air, with a subtle pale-gold wave during the stroke. Keep motion and petals unchanged.`
- **花弁が画面全体でピンクになりすぎた（「雪」に見えない）場合**：
  > `Make distant and outer petals pure white snow-like petals. Only the petals closest to the whale should softly pick up its sakura-pink and pale-gold light. Keep camera, whale, and motion unchanged.`

---

## 2. 2本目カット：R09（5.0秒・月光接触→淡い金の点灯＋V字の息）

**試す理由**：R14 とは全く異なる要素（暗い濡れた皮膚 → 淡い金の目覚め点灯、天井裂け目の大きな満月、柔らかい月光柱、V字の噴気霧、15°パン）を Omni が壊さず描けるか検証する。

- **ベース動画**：`R09_v14_10_clean.mp4`（1280×720 / 24fps / **5秒**）
- **設定秒数**：`5秒`
- **参照画像（3枚）**：
  1. `dm/episode-01/ending/images/adopted/CUT05_KEY_whale_emerges.png`（点灯前の濡れた濃紺〜真珠灰の鯨の質感）
  2. `dm/episode-01/ending/images/adopted/CUT02_KEY_moon.png`（裂け目の月と柔らかい月光柱の雰囲気）
  3. `dm/episode-01/ending/images/adopted/CUT09_KEY_climax.png`（全体の夜景ガッシュ画風）

### Prompt R09-A
```text
Restyle the attached base video into a hand-painted theatrical anime film shot in luminous gouache and watercolor, matching the brushwork and night atmosphere of the reference paintings.

STRICTLY KEEP UNCHANGED from the base video:
- Exact slow rightward camera pan (~15 degrees), framing, composition, and 5-second timing.
- Exact whale silhouette, glide path (gliding effortlessly without tail flapping into the moonbeam), and position relative to the moon and cavern ceiling fissure.
- The single large full moon framed cleanly inside the asymmetric cavern ceiling opening, and the soft volumetric moonbeam descending into the dark cavern.

ENHANCE visually:
- Before entering the moonbeam, the giant 24-meter whale has wet, dark slate-blue to pearl-grey smooth skin with only subtle moonlight rim highlights and a small dark eye (no self-glow yet).
- As its nose glides into the soft moonbeam, a gentle, awe-inspiring wave of warm pale-gold light awakens along its body from nose to tail, shifting toward luminous pearl-white with a pale-gold aura—never harsh neon or blown-out white.
- Shortly after entering the moonbeam, keep the delicate V-shaped exhale mist rising from its blowhole, softly illuminated by the moonlight and lingering in the air.
- Keep the distant cavern darkness deep, vast, and quiet; do not brighten far walls or add extra lights or flowers.
- Completely silent (no music, no speech, no sound effects). No text, no watermarks.
```

---

## 3. 3本目カット：R15（6.0秒・最接近スロー＋押し寄せる花雪→置いていかれる雪）

**試す理由**：全編の感情的・視覚的ピーク。近距離の巨大な鯨（目線の傾き・0.6倍スロー）と、手前へ押し寄せた花弁が終盤に鯨から離れて白へ戻る演出を検証する。

- **ベース動画**：`R15_v14_10_clean.mp4`（1280×720 / 24fps / **6秒**）
- **設定秒数**：`6秒`
- **参照画像（3枚）**：
  1. `dm/episode-01/ending/images/adopted/CUT05_KEY_whale_emerges.png`（近距離の鯨の皮膚・腹の畝・胸びれ・瞳）
  2. `dm/episode-01/ending/images/adopted/CUT09_KEY_climax.png`（花吹雪と光の表現）
  3. `dm/episode-01/ending/v8/keyframe-test/refs/style_ref_painterly.png`（筆致）

### Prompt R15-A
```text
Restyle the attached base video into the breathtaking visual climax of a hand-painted theatrical Japanese animated film, using luminous gouache and watercolor brushwork matching the reference paintings.

STRICTLY KEEP UNCHANGED from the base video:
- Exact camera pan-and-tilt tracking as the giant whale sweeps past from right to left and climbs away into the upper distance.
- Exact 6-second pacing, including the brief dreamlike slow-motion moment at closest approach (~3 seconds in) as the whale subtly tilts toward the camera.
- Exact open dark cavern space—do not invent cavern walls, ocean surface, or extra moons.

ENHANCE visually:
- Close-up whale detail: monumental 24-meter smooth white whale with delicate ventral grooves, long graceful pectoral fins, and a small, calm, dark glistening eye that briefly meets the viewer's gaze without aggression or smile. The whale glows from within as a living light source—bright pearl-white core, rich luminous sakura-pink rim and aura, pulsing warm pale-gold at closest approach (brightest peak of the film, without harsh overexposure).
- Flower-petal blizzard: lush, tactile milky-white petals with tiny glowing pale-gold seeds rushing past the camera in deep 3D parallax, with large softly blurred foreground bokeh petals shimmering gold during the slow-motion peak. In the final second as the whale pulls away, the left-behind petals lose their pink-gold warmth and drift softly as quiet white snow.
- Completely silent (no music, no speech, no sound effects). No text, no watermarks.
```

---

## 4. 検証後の持ち帰り・評価手順

1. Flow で生成した MP4 をダウンロードし、ファイル名を以下のように揃える：
   - 例：`R14_flow_A1.mp4`、`R14_flow_A2_edit1.mp4`、`R09_flow_A1.mp4`
2. このセッションへ動画ファイルを共有（または `outputs/` に配置）すれば、`scripts/eval_omni_output.py` で以下を一括検証する：
   - **追従度（`adherence`）**：プリヴィズ v14.10 と鯨・花弁の位置がどれだけ一致しているか
   - **創作物検知（`invented_bright_ratio`）**：暗い領域に岩壁や余計な光を描き足していないか
   - **ちらつき（`flicker`）**：フレーム間の破綻がないか
   - **並列比較動画＆コンタクトシート**：左＝v14.10 プリヴィズ／右＝Omni 1.2 Flash で目視確認

### 合否チェック（4項目）
1. **構図・動き**：プリヴィズと重ねて鯨の軌道・尺・カメラが破綻していないか
2. **余計な創作なし**：存在しない岩壁・月光柱・文字・人物を描き足していないか
3. **v14.10 の色と質感**：鯨が光源（白芯＋桜縁＋金の拍）、花弁が「白い雪（近さで染まる）」として美しいか
4. **感情が動くか**：Blender 本命案（`v15i`）と比べて、初見の観客の心を動かせる品質か
