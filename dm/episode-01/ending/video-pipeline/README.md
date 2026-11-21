# Episode 01 Ending Video Pipeline (V7 — Blender 5.0 Cycles GPU)

**DM専用・ネタバレ注意。プレイヤーは閲覧しないこと。公開 Pages 対象外。**

第一話エンディング『空に降る雪』（90 秒 / `2,160f @ 24fps` / 1080p / 16:9 / Rec.709 / `-14 LUFS`）の現行 3D 映像制作パイプライン（**V7: Blender 5.0.1 Cycles GPU on Google Colab NVIDIA L4 OptiX**）。

## ディレクトリ構成（GitHub 管理対象）

- `v7_blender_cycles/v7_layout_master.json`: 90 秒・10 カット空間＆カメラ設計正本
- `v7_blender_cycles/v7_step4_target_table.json`: 輝度・コントラスト数値目標（±25% 検証基準）
- `v7_blender_cycles/out/v7_master_90s_storyboard_sheet.png`: 全 90 秒 8 カット時系列 Lookdev 一覧シート
- `v7_blender_cycles/out/step5_lookdev/step5_numeric_audit.json`: Step 5 自動数値検証ログ
- `v7_blender_cycles/scripts/`:
  - `render_step5_lookdev_cycles.py`: Step 5 540p Lookdev 5 ショット描画スクリプト（単一 `CONFIG` 管理）
  - `render_step5b_director_cuts.py`: Step 5B 新ディレクターズカット 4 ヒーローカメラ実証スクリプト
  - `run_step5_colab.py` / `run_step5b_colab.py`: Google Colab NVIDIA L4 GPU 実行＆自動ランタイム削除オーケストレータ
  - `audit_step5_lookdev.py`: ±25% 自動数値監査＆コンタクトシート生成

> 旧実験パイプライン（`v2`〜`v6`）、中間 `.blend`、動画ファイル（`.mp4` / `.wav`）、ローカル一時ビルド資産は `.gitignore` により GitHub から除外しています。
