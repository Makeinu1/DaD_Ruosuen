# 第一話エンディング『空に降る雪』v6.0 — Blender Python (`bpy`) / MCP クレイ・プリビズ制作環境

> **DM専用・ネタバレあり**（GitHub Pages・`SECTIONS`・`llms.txt` には一切公開しない）
> **適用スキル**：`cinematic-previs` × `blender-python-previs` × `animation-principles`（Disney 12 原則）× `cinematic-camera-continuity` × `google-ai-pro-flow-studio`

## v5.0 Pill Previs からの 5 大刷新ポイント

1. **無彩色クレイ質感（`cinematic-previs` 準拠）**：原色の縞模様カプセルを全廃。マットグレー／オフホワイトの `Principled BSDF`（Roughness `0.78–0.88`）＋ AgX カラー管理＋ソフト照明＋リム光で、AI 動画（`Omni 1.2 Flash`）参照時に不自然な色・縞ノイズを引きずらない設計。
2. **実シルエット造形（`SheetA` / `SheetB` 比率厳守）**：
   - **白鯨 WH-01（24m）**：48×24 の滑らかな流線型ロフト胴体、体長比 30% の長い胸びれ、三日月形の水平尾びれ、自然な S 字遊泳うねり＋フォロースルー。的マーク・縞模様なし。
   - **4 人の冒険者（1.66〜1.80m）**：地面（`Z = 0.85m`）に確実に接地した自然頭身マント付きクレイシルエット（頭切れ・宙浮きなし）。
   - **背景**：Z-fighting なしの面取り済み石造アーチ橋（中央崩落口＋苔縁）、ソフトな Fresnel 月光柱（土星リングなし）、実寸比の 5 弁空雪花と蕾・ランタン。
3. **破綻構図の完全修正**：
   - `C5a` / `C7a`：4 人の頭が画面下端で切れないカメラ高・俯角へ修正。
   - `C6b`：360° バレルロールの下段 1/3 に崩れた石造アーチ橋、奥に霧岩柱が入る並走構図へ修正。
   - `C7b`：85mm 真横望遠で満月（64 分割真円）の前を白鯨が左→右へ滑空し、**尾びれ→胴体→胸びれ→最後に頭部** の順で滑らかに透過溶解する専用シェーダーへ刷新。
4. **全 14 クリップ `≤ 9 秒` 最適化（Flow クレジット節約）**：
   - 96.0 秒・15 カット・マスター音響（`kousetsuka_v5_master_audio_96s.wav`）とフレーム完全同期を維持したまま、11〜15 秒帯の 2 倍クレジット単価ペナルティを回避。全本 `1〜10 秒` 最安帯＋**無料 1080p アップスケール** 対象。
5. **ヘッドレス CLI & ライブ Blender MCP 両対応（Stills-First QA）**：
   - 段階ゲート：`--mode look`（ルック確認 1 枚）→ `--mode qa`（評価済み頂点による数値フレーミング＆接地検査）→ `--mode stills`（全 15 カット静止画＆コンタクトシート）→ `--mode clip --clip-id C1`（24fps・180° シャッター PNG 連番 → Rec.709 H.264 MP4）。

## 実行コマンド（ヘッドレス Blender CLI）

```bash
# 1. 代表ルック静止画 1 枚（C6c / C2）＋ .blend 保存（最初にユーザー承認を得る）
blender --background --factory-startup --python-exit-code 1 \
  --python dm/episode-01/ending/v6-clay-previs/build_v6_clay_previs.py -- --mode look

# 2. 全 15 カットの数値フレーミング・接地・遮蔽 QA（高速・レンダリング不要）
blender --background --factory-startup --python-exit-code 1 \
  --python dm/episode-01/ending/v6-clay-previs/build_v6_clay_previs.py -- --mode qa

# 3. 全 15 カット静止画（IN/MID/OUT）＋ one_per_shot_v6.png コンタクトシート
blender --background --factory-startup --python-exit-code 1 \
  --python dm/episode-01/ending/v6-clay-previs/build_v6_clay_previs.py -- --mode stills

# 4. 承認後に単クリップ MP4 を書き出し（例：C1 = 6秒、24fps、Rec.709）
blender --background --factory-startup --python-exit-code 1 \
  --python dm/episode-01/ending/v6-clay-previs/build_v6_clay_previs.py -- --mode clip --clip-id C1
```

## ライブ Blender MCP からの実行

接続済みセッションで `execute_blender_code` から以下を実行すると、GUI 上に完全な v6 シーンを構築して確認・カメラ微調整ができます：

```python
import sys
sys.path.insert(0, "/Users/shumpeiabe/Desktop/DnD_Rousen/dm/episode-01/ending/v6-clay-previs")
import build_v6_clay_previs as v6
v6.build_scene_in_current_blender(set_time=56.0)
```
