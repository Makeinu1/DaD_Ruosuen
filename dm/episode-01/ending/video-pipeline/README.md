# Episode 01 Ending Video Pipeline (V7.8 — Self-Contained Blender 5.0 Cycles GPU)

**DM専用・ネタバレ注意。プレイヤーは閲覧しないこと。公開 Pages 対象外。**

第一話エンディング『空に降る雪』（90 秒 / `2,160f @ 24fps` / 全 16 カット / 1080p / 16:9 / Rec.709 / `-14 LUFS`）の自己完結型 3D 映像制作パイプライン（**V7.8: Blender 5.0.1 Cycles GPU on Google Colab NVIDIA L4 OptiX**）。

## ディレクトリ構成（GitHub 完全保存・別環境でも単体再実行可能）

- `v7_blender_cycles/v7_layout_master.json`: 90 秒・全 16 カット空間＆カメラ設計正本
- `v7_blender_cycles/v7_step4_target_table.json`: 輝度・コントラスト数値目標（±25% 検証基準）
- `v7_blender_cycles/assets/`: 3D メッシュ資産（`wh01_v20_hero.glb`, `fl01_open.glb`, `fl01_bud.glb`, `sakura_petal_3d.glb`）
- `v7_blender_cycles/textures/`: PBR テクスチャ資産（`anime_cliff_albedo.jpg`, `anime_cliff_normal.png`, `whale_skin_albedo.jpg`, `petal_rgba.png`, `moon_sky.jpg`）
- `v7_blender_cycles/scripts/`:
  - `render_step5_lookdev_cycles.py`: Step 5 540p Lookdev 5 ショット描画スクリプト（単一 `CONFIG` 管理）
  - `render_step5b_director_cuts.py`: Step 5B ディレクターズカット 4 ヒーローカメラ描画スクリプト
  - `render_step5c_extra8_cuts.py`: Step 5C 追加 8 カット描画スクリプト（全 16 カット完成用）
  - `run_step5_colab.py` / `run_step5b_colab.py` / `run_step5c_colab.py`: Google Colab NVIDIA L4 GPU 実行＆自動ランタイム削除オーケストレータ
  - `audit_step5_lookdev.py` / `measure_step4_targets.py`: ±25% 自動数値監査・ターゲット計測
  - `generate_step2_layout.py` / `build_step3_greybox.py` / `verify_90s_approach.py`: Step 2 設計図・Step 3 グレイボックス生成
  - `gen_asset_whale_wh01.py` / `gen_asset_flowers_fl01.py` / `gen_asset_pbr_textures.py`: 3D GLB メッシュ＆PBR テクスチャ生成スクリプト
- `v7_blender_cycles/out/`:
  - `v7_master_16cut_90s_sheet.png`: **全 90 秒・16 カット（4×4）完全時系列マスターシート**
  - `cuts_16_90s/cut01_*.jpg` 〜 `cut16_*.jpg`: **全 16 カット個別レンダリング画像（時系列連番）**
  - `v7_step5_lookdev_5sheet.png` / `v7_step5b_director_cuts_4sheet.png` / `v7_step5c_new8_sheet.png`: 各工程の検証コンタクトシート
  - `v7_step2_layout_plan_elevation.png` / `v7_step2_camera_whale_curves.png`: Step 2 平面図・断面図・軌道曲線
  - `step5_lookdev/step5_numeric_audit.json`: Step 5 自動数値検証ログ
