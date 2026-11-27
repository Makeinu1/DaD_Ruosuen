# ローカル版 Antigravity 引き継ぎガイド（Google AI Pro 0円制作環境）

このファイルは、クラウド側で構築・`main` マージ済みの **第一話エンディング『空に降る雪』v5.1（Gemini 画像＋Gemini 動画・追加課金 0 円環境）** を、**公式ブラウザ操作ツールが使えるローカル版 Antigravity IDE** へシームレスに引き継ぐためのガイドです。

## 1. すでに `main` に入っている資産（`git pull origin main` で取得可能）

- **導入済み Skills（3 本）**：
  - `.agents/skills/google-ai-pro-flow-studio/SKILL.md`（追加課金 0 円・Google Flow 公式ブラウザ運用・クォータ上限ガード・自動ログ）
  - `.agents/skills/gemini-consistent-image/SKILL.md`（Nano Banana Pro / 2.1 一貫性・設定シート先行・連鎖参照・脱AI臭）
  - `.agents/skills/gemini-previs-video/SKILL.md`（Gemini Omni 1.2 Flash / Veo 3.1・15秒以下分割・自然言語メディアバインド・マーチ演出）
- **承認済みモデルシート（ローカル保存＆記録済み）**：
  - `dm/episode-01/ending/v5-gemini-production/studio/images/SheetA_whale_pcs.jpg`（WH-01 白鯨2状態・4人シルエット・真鍮ランタン）
  - `dm/episode-01/ending/v5-gemini-production/studio/images/SheetB_flower_arch.jpg`（5弁空雪花・灰褐色蕾・淡金果実付花弁・崩れた石造アーチ橋＆霧の巨岩柱）
- **レイアウト静止画 16 枚**：`dm/episode-01/ending/v5-gemini-production/previs_frames/`
- **プロンプト一式**：`style.md` / `01_GEMINI_IMAGE_PROMPTS.md` / `02_GEMINI_VIDEO_PROMPTS.md`
- **自動ログ＆上限ガード**：`dm/episode-01/ending/v5-gemini-production/studio/studio_log.py`（`generation_log.jsonl` + `.meta.json` + `quota_budget.json`）
- **最終 1080p Rec.709＋`-14.21 LUFS` 音響結合スクリプト**：`dm/episode-01/ending/v5-gemini-production/assemble_gemini_final.py`

## 2. Google Drive からローカルへダウンロードする動画・音声素材（大容量のため Git 外）

- **Google Drive フォルダ**：`https://drive.google.com/drive/folders/1s1RW5XqC9cBIXhERJEDJn0HY0Y8YKKPT`（`ending_v5_gemini_production_20261126`）
  - `02_previs_videos_for_Gemini_Video/*.mp4`（9本・すべて 8〜14秒）→ `dm/episode-01/ending/v5-gemini-production/previs_clips_gemini/` へ配置
  - `kousetsuka_v5_master_audio_96s.wav` → `dm/episode-01/ending/v5-pill-previs/audio/` へ配置
