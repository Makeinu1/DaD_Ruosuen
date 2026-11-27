# 第一話エンディング『空に降る雪』— Gemini 画像生成（Nano Banana Pro / 2.1）一貫性プロンプト集

> **適用スキル**：`gemini-consistent-image`（`AntonioCardenas/generate-nanobanana` × `smixs/visual-skills` × `Square-Zero-Labs/video-prompting-skill` × `AgriciDaniel/banana-claude` 統合）
> **推奨モデル**：**Nano Banana Pro（`gemini-3-pro-image`・2K 16:9 推奨）** または **Nano Banana 2.1（`gemini-nano-banana-2.1`）**
> **最重要鉄則**：**絶対に並列でバラバラに生成しない！**
> 必ず **「Step 1：設定シート 2 枚（Sheet A / Sheet B）をロック → Step 2：3D プリビズ静止画（`previs_frames/`）＋ 設定シート ＋ 直前の承認済み画像を順番に参照連鎖させて 1 枚ずつ生成」** の順で進めてください。

---

## Step 1（必須・最初にロック）：共通アセット設定シート 2 枚

まずは本編カットを描かず、**全 9 クリップで 1 ミリもブレさせないための「三面図＆美術設定シート」を 2 枚** 作って承認・ロックします。

### Sheet A｜WH-01 蒼白の白鯨（無発光／月光発光）＋ 4人シルエット ＋ 真鍮ランタン設定シート
- **アップロードする参照画像（2枚）**：
  1. `CUT09_KEY_climax.png`（既存の採用画：白鯨の造形・ガッシュ画調の基準）
  2. `CUT03_KEY_flower.png`（既存の採用画：色彩・暗部トーンの基準）

```text
Create a clean animation production model sheet on a flat, evenly lit pale neutral grey-blue studio backdrop for consistent downstream film and video generation. Keep the exact smooth mythic baleen whale anatomy, long sweeping pectoral fins, gentle ventral throat grooves, broad crescent tail fluke, small dark calm eye, and hand-painted gouache brushwork from the first uploaded reference painting.

Arrange four clearly separated panels with generous spacing:
Top-left panel: full side profile of the 24-meter whale in its UNLIT dark state (wet dark slate-indigo back, muted pale grey-blue underside, zero glow, smooth unblemished skin with subtle ventral grooves).
Top-right panel: the exact same whale in full side profile in its MOONLIT luminous state (soft pearl-white and pale ice-blue radiance along its back and long pectoral fins, same exact proportions and markings).
Bottom-left panel: head-on front view and three-quarter front view of the same whale, plus one small detail callout of its small dark calm eye catching a single pinpoint glint of silver light.
Bottom-right panel: four anonymous dark backlit adventurer silhouettes standing side by side from behind at natural human proportions (distinct varied heights and cloak/pack outlines, no visible faces or fixed fantasy race features) beside one small weathered antique brass camping lantern casting a soft warm champagne-gold flame.

LOCKS: Keep the exact same whale proportions, fin length, smooth skin, and matte gouache paint texture across every panel. Plain neutral studio background with zero environment scenery, zero panel borders text, and zero labels.

Hand-painted 2D Japanese theatrical animation background painting in matte opaque gouache and delicate ink linework on cold-pressed paper grain, directly matching the painterly brushwork and restraint of the supplied reference painting. Deep nocturnal subterranean palette anchored strictly to midnight indigo shadows (#0A1326), dark sapphire mirror water (#183054), cool blue-silver atmospheric mist (#4A6A92), silver-blue moonlight shafts (#B2D2EE), pearl white highlights (#F2F5F8), tiny warm champagne-gold lantern and seed accents (#F4DA94), and muted grey-brown closed buds (#766C60). Visible traditional brushwork with quiet matte finishes and natural falloff into darkness; zero glossy 3D CGI sheen, zero plastic specular glare, zero neon pink or magenta tint, zero text, zero UI overlays, zero watermarks.
```

---

### Sheet B｜空雪花（5弁花・灰褐色蕾・果実付花弁）＋ 1+3融合背景（崩れた石造アーチ橋＆霧の巨岩柱）設定シート
- **アップロードする参照画像（2枚）**：
  1. `CUT03_KEY_flower.png`（既存の採用画：厳密な 5 弁白花とガッシュ質感の基準）
  2. `CUT09_KEY_climax.png`（既存の採用画：淡シャンパン金果実付きの浮遊花弁と洞窟光の基準）

```text
Create a clean animation art-direction prop and architecture sheet on a flat, evenly lit muted slate studio backdrop for consistent downstream film and video generation. Directly match the five-petal white flower geometry, translucent white petals with tiny warm champagne-gold oval seeds attached at each petal base, and matte hand-painted gouache texture of the uploaded reference paintings.

Arrange four clearly separated studies with generous spacing:
Top-left panel: botanical turnaround of the Kousetsuka plant in TWO states side by side — on the left, a drooping closed grey-brown sepal-wrapped bud on a bent stalk resembling dry dead grass (#766C60); on the right, the exact same stalk straightened upright crowned with a strictly five-fold radial pure-white five-petal blossom (#F2F5F8) with a soft pale champagne-gold center (#F4DA94).
Top-right panel: close-up study of three detached floating single white petals drifting through dark indigo air, each petal carrying one tiny 2-to-3-millimeter warm champagne-gold seed attached at its narrow base.
Bottom-left panel: weathered half-submerged old-kingdom stone aqueduct arch bridge segment showing rough chiseled dark grey-blue masonry blocks, semicircular arch opening, moss patches along the top parapet, and jagged collapsed stone end where the center span broke away; show one half bare mossy stone and the other half crowned with blooming white five-petal Kousetsuka blossoms.
Bottom-right panel: distant atmospheric study of colossal tapered natural limestone stalactite pillars heavily softened in cool blue-silver subterranean haze (#4A6A92) to sit far behind the sharper stone bridge.

LOCKS: Strictly five petals per open flower (never six or seven), tiny champagne-gold seed at the base of detached petals, weathered chiseled masonry (never pristine marble temple columns), zero text labels.

Hand-painted 2D Japanese theatrical animation background painting in matte opaque gouache and delicate ink linework on cold-pressed paper grain, directly matching the painterly brushwork and restraint of the supplied reference painting. Deep nocturnal subterranean palette anchored strictly to midnight indigo shadows (#0A1326), dark sapphire mirror water (#183054), cool blue-silver atmospheric mist (#4A6A92), silver-blue moonlight shafts (#B2D2EE), pearl white highlights (#F2F5F8), tiny warm champagne-gold lantern and seed accents (#F4DA94), and muted grey-brown closed buds (#766C60). Visible traditional brushwork with quiet matte finishes and natural falloff into darkness; zero glossy 3D CGI sheen, zero plastic specular glare, zero neon pink or magenta tint, zero text, zero UI overlays, zero watermarks.
```

> **検品ゲート（Step 1 完了チェック）**：`Sheet A` と `Sheet B` を目視確認し、① 白鯨のフォルムに違和感がないか、② 花が厳密に 5 弁か、③ 石造アーチ橋が古代神殿ではなく苔むした旧時代の石橋に見えるか、④ ネオンピンクが混ざっていないかを確認して保存してください（ファイル名：`SheetA_whale_pcs.png` / `SheetB_flower_arch.png`）。

---

## Step 2（順番どおり 1 枚ずつ連鎖生成）：全 9 クリップ始点キーフレーム（`KF-G1`〜`KF-G9`）

> **一貫性の秘密（Previs Wireframe + Sequential Reference Chaining）**：
> 各カットでは **「① `previs_frames/` の 3D プリビズ静止画（構図・カメラ角度・サイズ比を 100% 固定！）」＋「② `Sheet A`」＋「③ `Sheet B`」＋「④ 直前に承認した本番キーフレーム」** を順番にアップロードして生成します。これにより **3D プリビズの正確な構図** と **全カット統一の絵柄** が同時にロックされます！

---

### `KF-G1`｜Clip G1 始点（C1：安堵と予兆・ランタン・P0・銀の波紋）
- **アップロード順（3枚）**：
  1. `previs_G1_start.png`（3Dレイアウト・カメラ位置ロック用）
  2. `SheetA_whale_pcs.png`（真鍮ランタンの造形ロック用）
  3. `SheetB_flower_arch.png`（5弁花 P0・灰褐色蕾・遠景の崩れた石造アーチ橋ロック用）

```text
Transform the first uploaded 3D grey-clay layout frame into a finished hand-painted 2D Japanese theatrical animation still while preserving its exact low shore camera angle, horizon line, composition, and object placement. Completely replace every grey block, cylinder, and primitive placeholder with painted natural detail.

On the damp dark rocky subterranean shore in the foreground, place the exact weathered brass camping lantern from the second reference sheet casting a quiet pool of warm champagne-gold light across wet stone. Directly beside the lantern stands one lone open pure-white five-petal Kousetsuka blossom from the third reference sheet, while all surrounding stalks along the rock edge remain drooping closed grey-brown dead-grass buds. Just off the rocky shore on the glassy dark sapphire mirror lake, a single ceiling water droplet has struck the surface, spreading crisp concentric silver ripples. Far across the dark misty water in the background, faint half-submerged silhouettes of the weathered stone aqueduct arch bridge with its collapsed open central gap recede into cool blue-silver haze beneath a distant shaft of silver moonlight.

LOCKS: Ignore all grey clay shading and primitive lines in the first image; use it strictly for spatial layout and perspective. Strictly five petals on the lone open flower; all other buds stay closed grey-brown. No whale visible, no people visible.

[ここに style.md の VERBATIM STYLE LOCK をそのまま貼り付け]
```

---

### `KF-G2`｜Clip G2 始点（C3：正面直進膨張・衝突寸前の暗藍巨壁）
- **アップロード順（4枚）**：
  1. `previs_G2_start.png`（完全正面対称・4人と24m鯨のサイズ比ロック用）
  2. `SheetA_whale_pcs.png`（無発光の暗藍白鯨＋4人の匿名シルエット＋ランタンロック用）
  3. `SheetB_flower_arch.png`（左右奥の暗い水没石橋シルエットロック用）
  4. `KF-G1`（承認済み 1 枚目：岸辺の岩肌・ランタン・画調を完全継承！）

```text
Transform the first uploaded 3D layout frame into a finished hand-painted 2D Japanese theatrical animation still while strictly preserving its exact dead-center symmetrical low perspective, horizon height, and overwhelming scale contrast between the tiny foreground figures and the colossal approaching beast. Completely replace every striped pin, grey block, and striped capsule with hand-painted detail matching the fourth reference image's brushwork and nocturnal cavern atmosphere.

In the lower foreground on the damp rocky shore stand the four anonymous dark backlit adventurer silhouettes from the second reference sheet beside their small glowing brass lantern. Straight ahead along the exact center axis at eye level, the colossal 24-meter UNLIT dark slate-indigo whale from the top-left and bottom-left panels of the second reference sheet breaches low straight toward the camera like an unstoppable wet black wall—zero bioluminescence, only cold silver rim light grazing its broad brow and long sweeping pectoral fins while heavy twin curtains of silver water spray burst violently outward left and right off its flanks. In the misty dark background flanks beyond the spray, the dark weathered stone arches from the third reference sheet frame the outer edges while the center behind the whale remains deep dark cavern space.

LOCKS: Ignore all striped markings and grey clay geometry from the first image. Keep the four silhouettes tiny at 1.7-meter human scale with no visible faces; keep the whale unlit wet dark slate-indigo (no glow yet). Match the rock texture, lantern glow, and gouache brushstrokes of the fourth reference image.

[ここに style.md の VERBATIM STYLE LOCK をそのまま貼り付け]
```

---

### `KF-G3`｜Clip G3 始点（C5a：月光覚醒）＋ 補助キー `KF-G3b`（C5b：地表20cm一斉開花）
- **アップロード順（4枚）**：
  1. `previs_G3_start.png`（`KF-G3b` を作る際は `previs_G3_C5b.png` に差し替え）
  2. `SheetA_whale_pcs.png`（月光発光した真珠白の白鯨＋4人シルエットロック用）
  3. `SheetB_flower_arch.png`（開花した5弁白花＋水没石橋ロック用）
  4. `KF-G2`（承認済み：同じ岸辺・同じ4人・同じ洞窟を完全継承！）

```text
Transform the first uploaded 3D layout frame into a finished hand-painted 2D Japanese theatrical animation still while strictly preserving its exact upward wide angle behind the four shore silhouettes, the distant ruined stone arch bridge, the silver skylight shaft, and the soaring whale's exact position and size. Completely replace all grey clay blocks, striped pins, and capsule placeholders.

Seen from behind the four dark backlit adventurer silhouettes and small warm brass lantern on the damp shore, the 24-meter whale from the top-right panel of the second reference sheet glides diagonally upward into the bright silver-blue moonlight shaft, its smooth back and long pectoral fins igniting head-to-tail in radiant pearl-white and pale ice-blue light. Below across the dark sapphire mirror lake, the weathered stone aqueduct arches from the third reference sheet catch crisp silver moonlight along their broken edges, while high in the rocky ceiling cleft shines the bright round silver full moon.

LOCKS: Keep the exact four silhouettes, brass lantern, and shore stone from the fourth reference image; match the luminous pearl-white whale proportions from the second reference sheet; ignore all clay blocks and stripes from the first image.

[ここに style.md の VERBATIM STYLE LOCK をそのまま貼り付け]
```

> **※ C5b（地表 20cm 開花）用キーフレーム `KF-G3b`** を追加生成する場合は、`Image 1` を `previs_G3_C5b.png`・`Image 4` を `KF-G1` に差し替え、本文を **「カメラが地表 20cm の超低空から岸辺の石とランタン越しに、手前の灰褐色蕾が純白の 5 弁花へ一斉に開花し、その開花の波が鏡面湖の対岸にある崩れた石造アーチ橋の苔の上まで連なって白い花を灯す瞬間」** に差し替えて生成します。

---

### `KF-G4`｜Clip G4 始点（C6a：花弁離陸 1 秒静止 → 3層大花吹雪の幕開け）
- **アップロード順（4枚）**：
  1. `previs_G4_start.png`（地表低空・花弁浮遊・遠景の石造アーチ橋＆白鯨レイアウト）
  2. `SheetB_flower_arch.png`（5弁花・淡シャンパン金果実付花弁・苔上開花した石橋）
  3. `SheetA_whale_pcs.png`（月光発光の白鯨）
  4. `KF-G3`（承認済み：同じ洞窟光とガッシュ画調を継承！）

```text
Transform the first uploaded 3D layout frame into a finished hand-painted 2D Japanese theatrical animation still preserving its exact low wide perspective skimming above the blooming rocky shore toward the wide dark mirror lake, ruined stone arch bridge, and distant soaring white whale. Completely replace every clay block and primitive flower disc.

Across the foreground rocky shore and hovering silently one to two meters above the glassy dark sapphire water, hundreds of translucent pure-white single petals—each carrying a tiny warm champagne-gold seed at its base exactly as in the second reference sheet—hang completely motionless in mid-air like suspended snow after detaching from the blooming five-petal flowers. Across the wide mirror lake stand the weathered sunken stone aqueduct arches with white five-petal flowers blooming along their mossy parapets and reflecting cleanly in the dark water. Above the open collapsed central gap of the bridge glides the luminous pearl-white whale from the third reference sheet under the silver moonlight shaft, while heavily mist-softened giant natural stalactite pillars frame only the far outer left and right edges.

LOCKS: Keep petals pure white with tiny champagne-gold seeds (zero pink); keep center sky around the whale completely free of rock columns; match the exact gouache texture and palette of the fourth reference image.

[ここに style.md の VERBATIM STYLE LOCK をそのまま貼り付け]
```

---

### `KF-G5`｜Clip G5 始点（C6b：360°緩やかバレルロール × 崩れた石造アーチ橋くぐり）
- **アップロード順（4枚）**：
  1. `previs_G5_start.png`（並走アングル・下段に崩れた石造アーチ橋・奥に霧の巨岩柱）
  2. `SheetA_whale_pcs.png`（月光発光の白鯨の正確な造形）
  3. `SheetB_flower_arch.png`（中景の石造アーチ橋・最遠景の霧岩柱・花雪）
  4. `KF-G4`（承認済み：直前カットの 3 層大花吹雪と石橋の質感を完全継承！）

```text
Transform the first uploaded 3D layout frame into a finished hand-painted 2D Japanese theatrical animation still preserving its exact elevated parallel tracking angle beside the swimming whale, with the broken stone arch bridge spanning the lower third below and far misty stalactite pillars framing the outer distance. Completely replace all striped capsules and grey blocks.

Floating effortlessly across the center of the vast midnight-indigo cavern, the luminous pearl-white 24-meter whale from the second reference sheet glides gracefully over the wide collapsed central opening of the weathered sunken stone aqueduct arch bridge below, its long pectoral fins beginning a gentle weightless barrel roll. The entire vast subterranean space is filled naturally with a three-layer luminous floral snowstorm matching the third and fourth reference images—tiny distant mist sparks far back, drifting white five-petal snowflakes and champagne-gold seeded petals filling the mid air around the whale, and a few larger softly blurred translucent petals drifting near the foreground edge. Behind a cool blue-silver mist veil far behind the sharper stone bridge, colossal blurred natural limestone stalactite pillars stand only along the outer flanks, leaving the central air behind the whale completely open.

LOCKS: Preserve exact whale anatomy and smooth ventral grooves from the second sheet; keep midground stone bridge crisp with mossy parapet blossoms and far stalactites heavily mist-softened so the background never feels cluttered; match the fourth image's brushwork.

[ここに style.md の VERBATIM STYLE LOCK をそのまま貼り付け]
```

---

### `KF-G6`｜Clip G6 始点（C6c：1+3融合・220m大空洞決定画・40°遊びバンク＆鏡面対称）
- **アップロード順（4枚）**：
  1. `previs_G6_start.png`（21mm超広角・石造アーチ橋＋鏡面反射＋最遠景霧岩柱＋白鯨＆逆さ鯨の決定構図）
  2. `SheetA_whale_pcs.png`（白鯨の正確な造形）
  3. `SheetB_flower_arch.png`（中景石橋・苔上開花・最遠景霧岩柱・果実付花弁）
  4. `KF-G5`（承認済み：直前カットと 100% 同じ白鯨・石橋・花雪密度を継承！）

```text
Transform the first uploaded 3D layout frame into the signature grand wide centerpiece painting of a hand-painted 2D Japanese theatrical animation film, strictly preserving its exact wide cathedral expanse, horizon line, ruined stone arch placement, symmetrical lake reflection, and banking whale position. Completely replace every clay mesh and stripe.

Across the vast 220-meter midnight-indigo subterranean ocean, the weathered sunken stone aqueduct arches from the third reference sheet extend from left and right with a wide open collapsed gap in the center; crisp silver moonlight rims the semicircular stone arches, pure-white five-petal Kousetsuka bloom along the mossy broken parapets, and the entire bridge casts a quiet dark symmetrical inverted reflection across the glassy sapphire mirror lake. A soft cool blue-silver atmospheric mist band separates the midground bridge from colossal, heavily mist-softened natural limestone stalactite pillars standing strictly along the extreme outer left and right flanks, keeping the center sky and towering silver moonlight shaft completely clear. Gliding joyously through the open central sky above the collapsed breach in a graceful 40-degree bank is the luminous pearl-white 24-meter whale from the second reference sheet, mirrored upside-down in the calm dark water below. Filling the entire vast volume organically in three depth layers is the same luminous floral snowstorm of white petals with tiny champagne-gold seeds from the fourth reference image.

LOCKS: Depth-stratified 1+3 fusion strictly obeyed (sharp silver-rimmed midground stone bridge, mist band separator, soft blurred far-flank stalactites only, zero columns behind the whale or moon shaft). Match the whale, masonry, flowers, and gouache brushstrokes of the fourth reference image identically.

[ここに style.md の VERBATIM STYLE LOCK をそのまま貼り付け]
```

---

### `KF-G7`｜Clip G7 始点（C6d：22°優しい一瞥＆0.6xスローの間）
- **アップロード順（4枚）**：
  1. `previs_G7_start.png`（中望遠の寄り添いアングル・白鯨の穏やかな横顔と静かな眼）
  2. `SheetA_whale_pcs.png`（白鯨の側面＆静かな眼のディテール）
  3. `SheetB_flower_arch.png`（花雪・背景霧）
  4. `KF-G6`（承認済み：同じ白鯨の質感と花雪の色調を継承！）

```text
Transform the first uploaded 3D layout frame into an intimate, warm hand-painted 2D Japanese theatrical animation still preserving its exact close three-quarter framing of the luminous whale gliding gently past the viewer's side. Completely replace every clay capsule and stripe.

Cruising close through the quiet midnight-indigo cavern air filled with gently drifting white petals and tiny warm champagne-gold seeds, the luminous pearl-white 24-meter whale from the second reference sheet tilts its long sweeping pectoral fin softly downward and turns its head gently toward the viewer—showing its small dark intelligent eye catching a tender pinpoint of silver moonlight. The whale's smooth pearl skin glows softly without harsh glare, illuminating nearby drifting petals in cool silver-white while the vast misty cavern background and distant moonlight column fall into soft painterly depth of field.

LOCKS: Exact same smooth pearl-white whale proportions and small calm dark eye from the second and fourth reference images; soft drifting three-layer floral snow matching the fourth image; zero cartoonish exaggerated eye size.

[ここに style.md の VERBATIM STYLE LOCK をそのまま貼り付け]
```

---

### `KF-G8`｜Clip G8 始点（C7a：見送り）＋ 重要キー `KF-G8b`（C7b：85mm真横望遠・尾から頭へ満月溶解）
- **`KF-G8b`（C7b 満月溶解の決定画）アップロード順（4枚）**：
  1. `previs_G8_C7b_mid.png`（真横の満月＆尾から溶け始めた白鯨の厳密なレイアウト！）
  2. `SheetA_whale_pcs.png`（白鯨の正確な真横シルエット）
  3. `SheetB_flower_arch.png`（淡金果実付きの白い花弁）
  4. `KF-G7`（承認済み：同じ白鯨の質感と画調を完全継承！）

```text
Transform the first uploaded 3D layout frame into a poignant hand-painted 2D Japanese theatrical animation farewell still, strictly preserving its exact compressed telephoto side-profile framing of the giant radiant silver-white full moon framed by dark cavern ceiling rock and the whale gliding horizontally across the moon's face. Completely replace every clay mesh and stripe.

Filling the center of the frame against deep midnight-indigo darkness shines the giant, perfectly round luminous silver-white full moon with subtle crater texture, framed only at the far dark corners by rough cavern fissure rock with nothing cutting across the moon's disc. Gliding serenely from left to right directly across the moon in crisp side profile is the exact pearl-white 24-meter whale from the second and fourth reference images, smoothly dissolving FROM TAIL TO HEAD back into pure moonlight: its crescent tail fluke and rear half on the left have already dissolved into shimmering incandescent silver-white mist, vapor, and delicate light dust merging seamlessly into the moon's glow, while its long sweeping pectoral fins and calm, gentle forward-looking head on the right still hold soft pearlescent form as they fade peacefully into light. A few delicate white petals with tiny champagne-gold seeds drift slowly across the quiet moonlit air.

LOCKS: Tail dissolves FIRST on the left while the calm head remains visible LAST on the right; completely clean unobstructed full moon (no dark bands or rings crossing the moon); exact same whale anatomy and matte gouache brushwork as the fourth reference image.

[ここに style.md の VERBATIM STYLE LOCK をそのまま貼り付け]
```

> **※ C7a（4人の背中越し見送り）用キーフレーム `KF-G8a`** も作る場合は、`Image 1` を `previs_G8_start.png`・`Image 4` を `KF-G6` に差し替え、4人の背中とランタン・奥の崩れた石造アーチ橋・空へ昇る白鯨・降り始める花雪を描いてロックします。

---

### `KF-G9`｜Clip G9 始点（C7c：本物の雪が4人と石橋を包む祝福）
- **アップロード順（4枚）**：
  1. `previs_G9_start.png`（4人の背中越し＋ランタン＋奥の石造アーチ橋レイアウト）
  2. `SheetA_whale_pcs.png`（4人の匿名シルエット＋真鍮ランタン）
  3. `SheetB_flower_arch.png`（崩れた石造アーチ橋＋舞い降りる白い花弁）
  4. `KF-G1`（承認済み 1 枚目：導入と完全に同じ岸辺・同じランタン・同じ石橋へ還る！）

```text
Transform the first uploaded 3D layout frame into a serene, grateful hand-painted 2D Japanese theatrical animation epilogue still preserving its exact low wide angle behind the four shore figures looking out across the calm dark mirror lake toward the distant sunken stone arch bridge. Completely replace every clay pin and block.

Standing peacefully beside their small warm brass lantern on the exact same damp rocky shore from the fourth reference image, the four anonymous dark backlit adventurer silhouettes from the second reference sheet look quietly out over the dark sapphire mirror lake. With the whale gone, hundreds of released pure-white petals with tiny fading champagne-gold seeds drift softly downward like gentle real winter snow, dusting the rocky shore, floating silently over the glassy water, and settling along the mossy ruined stone aqueduct arches across the misty lake. Soft silver moonlight descends calmly from high above.

LOCKS: Match the exact shore stones, brass lantern, water palette, and distant stone arches of the fourth reference image (KF-G1) so the opening and ending feel unmistakably in the exact same place; four anonymous silhouettes with no visible faces; gentle downward winter snowfall mood.

[ここに style.md の VERBATIM STYLE LOCK をそのまま貼り付け]
```

> **※ Clip G9 後半（C8：最後の一枚と波紋）** は **`KF-G1` と完全同一構図（ミラー対称）** のため、動画生成時に **`KF-G1` をそのまま終点側リファレンスとして再投入** することで、最初と最後が 1 ミリもズレない完璧な額縁構造が完成します！
