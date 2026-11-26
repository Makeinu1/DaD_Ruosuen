# 第一話エンディング『空に降る雪』— Gemini 動画＆画像 本番制作キット（v5.1）

> **DM専用・ネタバレあり**（GitHub Pages・`SECTIONS`・`llms.txt` には一切公開しない）
> **導入・適用済みスキル**：
> - [`gemini-consistent-image`](../../../../.agents/skills/gemini-consistent-image/SKILL.md)（`AntonioCardenas/generate-nanobanana` × `smixs/visual-skills` × `Square-Zero-Labs/video-prompting-skill` × `AgriciDaniel/banana-claude`）
> - [`gemini-previs-video`](../../../../.agents/skills/gemini-previs-video/SKILL.md)（`Gemini Omni 1.2 Flash` / `Veo 3.1` / `Google Flow` プリビズ参照動画＋マーチ演出・3ディテール物理監査）

---

## 一貫性を絶対に崩さない 4 ステップ制作手順

1. **Step 1：設定シート 2 枚を Gemini 画像（Nano Banana Pro / 2.1）で生成・ロック**
   - [01_GEMINI_IMAGE_PROMPTS.md](01_GEMINI_IMAGE_PROMPTS.md) の **Step 1** を使い、`CUT09_KEY_climax.png` と `CUT03_KEY_flower.png` を参照して **`SheetA_whale_pcs.png`** と **`SheetB_flower_arch.png`** を作成・承認する。
2. **Step 2：3D プリビズ静止画（`previs_frames/`）＋ 設定シート ＋ 直前キーフレームを順番に参照連鎖させて `KF-G1`〜`KF-G9` を 1 枚ずつ生成**
   - 並列独立生成は厳禁。必ず [style.md](style.md) の `VERBATIM STYLE LOCK` を一言一句変えずに末尾へ添付し、`KF-G1 → KF-G2 → … → KF-G9` の順で連鎖ロックする。
3. **Step 3：15秒以下へ分割済みの 9 本のプリビズ MP4（`previs_clips_gemini/`）＋ 承認済みキーフレーム ＋ 設定シートで Gemini 動画（`Gemini Omni 1.2 Flash` / Google Flow）を生成**
   - [02_GEMINI_VIDEO_PROMPTS.md](02_GEMINI_VIDEO_PROMPTS.md) の全 9 クリップ（`12 / 13 / 10 / 9 / 8 / 8 / 9 / 14 / 13s = 96.0s`）を自然言語バインドで投入し、`final_G1.mp4`〜`final_G9.mp4` を得る。
4. **Step 4：ワンコマンド最終上映マスター結合**
   - 9 本を `final_clips/` に置き `python3 dm/episode-01/ending/v5-gemini-production/assemble_gemini_final.py` を実行すると、**1080p 24fps / Rec.709 タグ付 / `-14.21 LUFS` マスター音響合成済み** の 2026-12-23 上映マスターが完成します。
