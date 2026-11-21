# 原画試作：一瞥（C08）と頂点の群舞（C16）— Nano Banana Pro

**DM専用・プレイヤー閲覧禁止。** 2026-11-21 作成。作者承認「1は実施しても良い」（2026-11-21）による試作の手順書。

目的は **G-B（12/01）映像方式の決定** の材料をそろえること。いちばん難しい寄り（C08 一瞥）と引き（C16 頂点の群舞。当初は大渦、2026-11-21 に渦なしへ変更）の2枚を Gemini の画像生成（Nano Banana Pro）で作り、同じ鯨に見えるか・設定を守れるか・映えるかを見る。カット内容は [v10 カット割り](../v10-shotlist.md) と [鯨の動き v10](../whale-motion-v10.md) に従う。

## 渡す画像と役割

画像ごとに役割を一つだけ与える。プロンプト内の「Image 1/2/3」は、アップロードした順番を指す。

| ファイル | 役割 | 使わせない要素 |
|---|---|---|
| [refs/WH01_identity_sheet.png](refs/WH01_identity_sheet.png) | 鯨の形（GLB の4方向。目を皮膚の外へ出した版） | 灰色の色・照明・画像内の文字 |
| [refs/style_ref_painterly.png](refs/style_ref_painterly.png) | 画風（旧採用原画 CUT09 の右端を切り出し。筆致・夜の青・細かなきらめき） | 内容・光条・構図 |
| [refs/G_C08_glance.png](refs/G_C08_glance.png) | C08 の構図（68 mm、目を右三分割線上） | CG の質感 |
| [refs/G_C16_mirror.png](refs/G_C16_mirror.png) | C16 の当初構図（湖のふちから 18 mm。月・光の柱・鯨・湖の映り込み）。渦は不採用で、現在は採用原画 C16 B を構図の参照にする | 四角い粒（花びらの代役）とその螺旋配置、右の岩壁 |
| [refs/G_C16_alt_shore_high.png](refs/G_C16_alt_shore_high.png) | C16 の別案（Cam A の高さ） | 同上 |

C16 は二案ある。v10 の指定「岸から 18 mm」を Cam A の高さで撮ると、手前の岸が湖を隠して映り込みが出ない。湖のふちまでカメラを下げた `G_C16_mirror` を本命にした。代わりに頭上の裂け目は画面上端の月だけになる。

## 手順

生成は Gemini に依頼する。依頼票は Notion のプロジェクト管理DB（ルオスエンのハブのサブアイテム）に置き、本文は依頼内容とリンクだけにする。プロンプトと合格基準の正本はこのファイル。

画像の受け渡しは当面 Google Drive で行う（2026-11-21 作者指示）。Gemini は GitHub 上の画像を取得も添付もできないため、参照画像は Drive の `refs` から取り、生成物と記録表は Drive の `results` に置く。フォルダは作者だけの非公開で、リンクは依頼票にある。Claude が Drive から [results/](results/README.md) へ登録して判定する。

生成の場所は Google Flow、Gemini アプリ、API のどれでもよい。修正のやり取りは Gemini アプリが楽で、あとで Veo に渡すなら Flow にそろえる。どれでも、画像生成のモデルに **Nano Banana Pro**（Gemini 3 Pro Image）を選び、横長（16:9）で出す。Nano Banana Pro が使えない場合は、別のモデルで代用せずに止めて作者に知らせる。

1. **鯨の清書シート（STEP 0）**：形の参照と画風の参照から、この画風の鯨を1枚作る。以降はこの清書を同一性の参照に使う。動画化（Veo の参照画像）にもそのまま使える。
2. **C08 一瞥**：構図ガイド＋清書シート＋画風の3枚で生成する。
3. **C16 頂点の群舞**：採用済み（C16 B）。直すときだけ C16 の節に従う。
4. **直す**：作り直さず、良い1枚を下の「修正の一文」で直していく（1回の修正で直すのは1点）。
5. **記録**：画像はすべて Drive の `results` に置き、1回ごとに Drive の記録表へ1行足す（消費クレジットも書く）。Claude が [results/](results/README.md) へ移し、作者と判定して判定表に記入する。

目安は清書 1–2 回、C08・C16 は各 2–4 回の生成と、修正 3 回まで。

## STEP 0：鯨の清書シート

添付順：Image 1 = `WH01_identity_sheet.png`、Image 2 = `style_ref_painterly.png`

```text
Use the attached images with these roles:
- Image 1: the exact body shape of the creature, seen from four angles. Copy proportions and silhouette only. Ignore its grey colour, its studio lighting and all text in it.
- Image 2: painting style only: soft painterly brushwork, deep blue night palette, fine glittering highlights. Do not copy its whale, light rays or composition.

Create a clean character model sheet of this fantasy whale. 16:9, plain very dark navy background, no text, no labels, no frames.
Show three views side by side: left side view, three-quarter front view, view from below.
Top row - unlit state: wet, smooth skin of very deep navy blue, fading to pearl white on the belly, lit only by faint cool moonlight.
Bottom row - glowing state: the same whale glowing softly from within its skin with a pearl-opal sheen (ice cyan, white pearl, pale cherry pink, champagne gold shifting along the body), still with clear 3D shading.

Creature rules for every view:
- 24 m long whale with a smooth streamlined body, a small dorsal fin, very long smooth pectoral fins with clean edges, a two-lobed tail fluke, gentle grooves on the throat and belly only.
- Small, calm, dark eye.
- No spots, no bumps, no barnacles, no tubercles, no horns, no scales, no patterns.
- No cloth, veils, ribbons, streamers or fabric-like fins.
```

合格：形がシートと合う（頭の形・胸びれの長さ・小さな背びれ・二葉の尾）、斑と瘤なし、布なし、上段は発光していない。

## C08 一瞥（28–32 秒）

添付順：Image 1 = `G_C08_glance.png`、Image 2 = 清書シート（なければ `WH01_identity_sheet.png`）、Image 3 = `style_ref_painterly.png`

```text
Use the attached images with these roles:
- Image 1: composition guide from a 3D layout. Keep its camera angle, framing, the position of the whale's head and the eye on the right third. It is a blockout: replace its plastic CG surfaces with painting.
- Image 2: identity of the whale (head shape, eye placement, smooth skin). Use its unlit state. Ignore its background and any text.
- Image 3: painting style only.

Scene: an underground cavern at night. A giant whale floats in the air right in front of the viewer and has stopped to look straight at them. Extreme close-up of the side of its head, 68 mm telephoto look, shallow depth of field, focus on the eye.
The whale is not glowing. Wet, smooth, very deep navy skin that sinks into darkness away from the eye; only a thin cool rim of moonlight traces the top of the head.
The eye: small, calm, dark, almost black, with one tiny point of moonlight reflected in it. The expression is unreadable - neither hostile nor friendly. An animal eye: not cute, not human, no eyebrows, no tears, no smile.
Background: pure darkness. No cave walls, no rocks, no scenery.

Do not include: spots, bumps, barnacles, scars, water splashes, streams of water, sparkles, petals, glow, text, logos, borders.
Output: 16:9 cinematic still, painterly anime film key frame, low-key lighting, deep blacks with readable mid-tones.
```

合格：
- 目が右三分割線の近くにあり、焦点が目に来ている。
- 目は小さく暗く、月光は一点だけ。何を考えているか読めない（敵意も好意も出ていない）。
- 肌は濃紺で光っていない。背景は闇で、壁や景色が見えない。
- 斑・瘤・布・水しぶきがない。
- 暗部が真っ黒につぶれず、頭の丸みが読める（プロジェクターで沈みやすいため）。

## C16 頂点の群舞（57–63 秒）

**作者決定（2026-11-21）：渦は描かない。** 採用原画は [C16 B](results/C16_B_petals_dense_no_flower.png)。直すときは C16 B を元に「修正の一文」で直し、作り直すときだけ下のプロンプトを使う。当初の「大渦」プロンプトは不採用（git 履歴に残る）。

添付順：Image 1 = `results/C16_B_petals_dense_no_flower.png`、Image 2 = 清書シート（`results/sheet_t01.png`）、Image 3 = `style_ref_painterly.png`

```text
Use the attached images with these roles:
- Image 1: composition and petal density to keep: the camera at the edge of the lake looking slightly up; the full moon in a narrow ceiling rift at the top centre; a thin moonbeam; the whale swimming leftward in the middle; the mirror reflection in the lower third.
- Image 2: identity of the whale. Use its glowing state. Ignore its background and any text.
- Image 3: painting style only.

Scene: the climax inside a vast, dark underground cavern. A single shaft of moonlight falls from a narrow rift in the ceiling far above. The glowing whale glides leftward in front of the moonbeam, and the air around the beam and the whale is filled with a dense, calm swarm of drifting petals. There is no spiral and no vortex: the petals drift together as one quiet swarm, as if held by the whale's mysterious power, not by wind.
Petals: thousands of small, real white petals, soft and slightly translucent. Only loose petals fly - no whole flowers. They do not emit light; they shine only where the whale's light and the moonlight touch them. Tiny golden seeds glow softly as separate sparks.
The whale: glowing from within with a pearl-opal light (ice cyan, white pearl, pale cherry, champagne gold) with clear 3D shading; smooth skin; its small eye stays dark.
The lake: perfectly still, a black mirror reflecting the petals, the whale and the moon almost symmetrically.
Darkness: only the petals and the space around the whale are lit. The cavern walls, the far side and the ceiling around the rift fall into deep darkness; the outer edge of the swarm dissolves into the dark, suggesting a huge unseen space.

Do not include: a spiral or vortex; cave walls, cliffs, rock formations, a far shore or any scenery; chaotic wind-blown scatter; whole flowers in the air; glowing petals or comet-like trails; pink petals, cherry blossom trees, large leaf-shaped petals; spots, bumps, cloth or veils on the whale; lens flares; text; logos; borders.
Output: 16:9 cinematic wide still, 18 mm wide-angle look, painterly anime film key frame, deep blacks, high contrast for a projector.
```

合格：
- 月・光の柱・鯨・湖の映り込みがそろう。花びらは柱と鯨のまわりを満たし、螺旋や渦になっていない（鯨に全部の花びらがまとわりついていない）。
- 壁・奥・遠い岸が見えない。群れの外縁が闇に溶けている。
- 花びらは白く小さく、それ自体は光っていない。金の種子だけが光っている。花が丸ごと舞っていない。
- 群れは風で散らかっておらず、静かに漂っている。
- 鯨が清書シートと同じ個体に見える（斑・瘤・布なし、オパールの発光）。
- 一目で「映え」がある。

## 修正の一文（編集で直す）

作り直さず、直したい点だけを英語の一文で頼む。先頭に `Keep everything else exactly the same.` を付ける。

| 症状 | 修正の一文 |
|---|---|
| 斑・瘤・模様が出た | `Make the whale's skin completely smooth: remove all spots, bumps, barnacles and patterns.` |
| 布・ベール・リボン | `Remove any cloth, veil, ribbon or streamer; the fins must be smooth, solid whale fins.` |
| 壁や奥が見える | `Darken every cave wall and rock until it disappears into black; only the petals and the whale stay lit.` |
| 花びらが光る・ピンク | `Make the petals white and not self-luminous, lit only by the whale and the moon. Keep the small glowing golden seeds.` |
| 花びらが風で散らかる | `Make the petals drift as one calm, dense swarm around the moonbeam and the whale, as if held by an invisible force; no spiral.` |
| 花が丸ごと舞う | `Replace every whole flower in the air with loose single white petals.` |
| 手前の花びらが光る・尾を引く | `Make the large blurred foreground petals plain white and not glowing, with no trails; keep the golden seeds as separate tiny sparks.` |
| 目が人間的・かわいい | `Make the eye smaller, darker and calmer: an animal eye with a single tiny moon reflection, no expression.` |
| 目に月光が入らない | `Add one tiny point of moonlight reflected in the whale's eye, nowhere else.` |
| 湖の映り込みがない | `Make the lake a perfectly still black mirror that reflects the petals, the whale and the moon.` |
| 鯨の大きさが違う | `Resize the whale to match its size in Image 1.` |
| 暗すぎて形が読めない | `Lift the mid-tones slightly so the whale's form reads, while keeping deep blacks.` |

同じ症状が修正3回で直らないときは、その症状をこの表に書き足し、次のプロンプトに反映する。

## G-B（12/01）の判定

| 結果 | 方式 |
|---|---|
| 両カット合格（修正3回以内） | Gemini 路線で全カットの原画を作る。次に C16 を Veo 3.1 の Frames to Video で8秒動かす試験へ |
| 片方だけ合格 | 合格した側（寄り／引き）の種類は Gemini、残りは Blender で仕上げる |
| 両方不合格 | Blender 本線。V7 の修正（光源の照らし分け・オパール発光・目の露出）を全カットに入れる |

C08 と C16 で同じ鯨に見えない場合は、清書シートを作り直してから再判定する。

## ガイドの作り方（再現用）

- `scripts/whale_sheet.py`：`wh01_v20_hero.glb` の目を法線方向へ 0.20 m 出し、4方向を 800×450 でレンダーする。4枚を並べて文字を入れたものが `WH01_identity_sheet.png`。
- `scripts/guide_shots.py`：V7 Step 5C のシーン（`video-pipeline/v7_blender_cycles/`）を組む作業用ハーネスに読み込ませる撮影定義。C08（目の露出・68 mm）、C16 別案（Cam A 高）、C16 本命（湖のふち、`ONLY16B=1`）。花びらの渦は二本腕の螺旋に並べた発光板で、本番の花びらではない（渦は 2026-11-21 に不採用）。960×540・24 サンプル、CPU で1枚約80秒。
- 修正関数は [../diagnosis/v7_probe_test_shots.py](../diagnosis/v7_probe_test_shots.py)。
- `style_ref_painterly.png` は旧採用原画 `images/adopted/CUT09_KEY_climax.png` の右上を切り出したもの。旧原画の斑のある鯨・4弁の花・水しぶきを避けるため、鯨の写っていない部分だけを使う。
