# 第一話エンディング『空に降る雪』v7–v9.0 — Blender Cycles / OptiX プリビズ＆ルックデブ環境

> **DM専用・ネタバレあり**（GitHub Pages・`SECTIONS`・`llms.txt` には一切公開しない）
> **適用スキル**：`blender-skills` × `blender-python-previs` × `cinematic-previs` × `animation-principles` × `cinematic-camera-continuity`

## 概要（`v9.0` 時点）

- **主スクリプト**：`build_v7_clay_previs.py`（7,365 行・決定論的 `bpy` ビルダー＋自動計測 QA）
- **構成仕様**：`spec_v7.json`（`version: "9.0"` / `24 fps` / `96.0 s` / `1280×720` / `shutter: 0.36` / `seed: 20261223` / `aurora_mode: "canon_starry_opal"`）
- **同梱テクスチャ**：`textures/`（`anime_cliff_albedo.jpg`, `anime_cliff_normal.png`, `moon_sky.jpg`, `petal_rgba.png`, `whale_skin_albedo.jpg`）
- **保存済み最終 QA 証跡**：
  - `out/review/v9_0/qa_v9_0_report.json`（`status: "PASS"`, `fails: []`, `hero_flowers: 140`, `colony_flowers: 310`, `bridge_blooms: 180`, `snow_petals_total: 2020`, `C4b_eye_centered`, `C6b_top_headroom`, `C6c_mirror_symmetry`, `C7a_zero_snow_teleport`, `C8_true_petal_shedding`, `whale_unbroken_spline`, 全 15 ショット `cam_clearance` 合格）
  - `out/review/v9_0/v9_0_one_per_shot_4x4.jpg`（全 16 枚静止画コンタクトシート）
- 注：中間レンダリング画像・`.blend`・動画ファイル群はリポジトリ肥大化防止のため `.gitignore` で除外しています。

## 主要ビルダー機能（`build_v7_clay_previs.py`）

- `build_anatomical_whale` — 白鯨 `WH-01`（流線型胴体・胸びれ・水平尾びれ・目元造作）
- `build_ruined_arch_bridge` / `build_sunken_sanctuary_city` — 破損表現付き水門石橋と沈黙聖堂建築群
- `build_cavern_roof_canopy` / `build_cavern_walls_and_headlands` / `build_cavern_stalactites` — 鍾乳洞天蓋・岸壁・岬地形
- `build_cavern_star_vault` / `build_winter_starburst_heroes` / `build_aurora_veils` — 冬の大銀河天蓋と月・亀裂表現
- 空雪花コロニー（萼・蕾・5 弁開花・実散布 `C8` 連動）

## 実行コマンド（ヘッドレス Blender CLI）

```bash
# 1. 自動計測 QA のみ（静止画レンダリングなし）
blender --background --factory-startup --python-exit-code 1 \
  --python dm/episode-01/ending/v7-clay-previs/build_v7_clay_previs.py -- --mode qa

# 2. 全ショット静止画 + コンタクトシート（Cycles / OptiX 対応 GPU）
blender --background --factory-startup --python-exit-code 1 \
  --python dm/episode-01/ending/v7-clay-previs/build_v7_clay_previs.py -- \
  --mode stills --quality cycles --samples 16 --res-scale 75

# 3. 全編レンダリング（H.264 24fps Rec.709 MP4）
blender --background --factory-startup --python-exit-code 1 \
  --python dm/episode-01/ending/v7-clay-previs/build_v7_clay_previs.py -- \
  --mode full_film --quality cycles --samples 16 --res-scale 75
```

## ライブ Blender MCP からの起動

```python
import json, sys
from pathlib import Path

root = Path("/Users/shumpeiabe/Desktop/DnD_Rousen/dm/episode-01/ending/v7-clay-previs")
sys.path.insert(0, str(root))
import build_v7_clay_previs as v7

spec = json.loads((root / "spec_v7.json").read_text(encoding="utf-8"))
v7.build_scene_in_current_blender(spec, quality="cycles", set_time=56.0)
```
