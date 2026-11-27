# 第一話エンディング『空に降る雪』v3.0 — Seedance 2.5 Pill カメラプリヴィズ一式

> **DM専用・ネタバレあり。GitHub Pages / `SECTIONS` / `llms.txt` には掲載しない。**

## 収録ファイル

- **[scene_spec.json](scene_spec.json)**：全8カット（60秒・24fps）の3D座標・24m白鯨スプライン・4人PC配置・レンズ・カメラ軌道の単一正本。
- **[pill_engine.html](pill_engine.html)**：外部依存ゼロの WebGL2 3D Pill プリヴィズエンジン（実シャドウマップ・斜め縞ストライプ stand-in・鏡面湖波紋・灰褐色蕾→5弁開花・花雪・最後の一枚）。
- **[render_and_qa.py](render_and_qa.py)**：Playwright + PyAV（H.264）によるカメラ連続性QA・コンタクトシート生成・MP4書き出しスクリプト。
- **[QA_CAMERA_CONTINUITY.md](QA_CAMERA_CONTINUITY.md)**：0.5秒刻み全121サンプルによるカメラ衝突・180度ルール・画面速度・クリップ長（<29秒）検証レポート。
- **[sheets/one_per_shot.png](sheets/one_per_shot.png)**：全8カットのヒーローフレーム一覧（4×2）。
- **[sheets/in_mid_out_part1.png](sheets/in_mid_out_part1.png)** / **[sheets/in_mid_out_part2.png](sheets/in_mid_out_part2.png)**：全8カットの In / Mid / Out 連続性検査シート。
- **[unified_art_board.png](unified_art_board.png)**：採用済み初期原画6点＋v3.0正本カラーパレット＆設定整合ロックを統合した `@Image1` 統一美術ボード。
- **[SEEDANCE_PROMPTS.md](SEEDANCE_PROMPTS.md)**：4クリップ分割（11s / 12s / 22s / 15s）それぞれの Seedance 2.5 / Flow 用本番プロンプト。

## 動画ファイル（Google Drive に配置）

Git リポジトリ肥大化を避けるため、MP4 動画5本は Google Drive の `Ruosuen_Render/ending_v3_pill_previs_20261125` フォルダに配置しています：

1. `master_60s_preview.mp4` — 全8カット60秒・通し確認用（上部/下部スレートバー付き）
2. `seedance_clip1_C1_C2_fear_setup_11s.mp4` — Seedance 入力用クリーン動画（C1+C2・11s・HUDなし）
3. `seedance_clip2_C3_C4_overhead_awe_12s.mp4` — Seedance 入力用クリーン動画（C3+C4・12s・HUDなし）
4. `seedance_clip3_C5_C6_bloom_and_snow_22s.mp4` — Seedance 入力用クリーン動画（C5+C6・22s・HUDなし）
5. `seedance_clip4_C7_C8_farewell_and_petal_15s.mp4` — Seedance 入力用クリーン動画（C7+C8・15s・HUDなし）

## 再現コマンド

```bash
# コンタクトシート + カメラ連続性QA のみ
python3 dm/episode-01/ending/v3-pill-previs/render_and_qa.py --mode sheets

# 動画5本（60秒マスター + 4本のSeedanceクリーン動画）を書き出し
python3 dm/episode-01/ending/v3-pill-previs/render_and_qa.py --mode video
```
