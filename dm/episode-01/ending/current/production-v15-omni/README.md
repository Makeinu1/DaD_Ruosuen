# 『空に降る雪』v15-omni｜Gemini Omni 1.2 Flash によるプリヴィズ→完成動画 PoC

> **DM専用・ネタバレあり。プレイヤー閲覧禁止。GitHub Pagesへ掲載しない。**
> 並行進行中の Blender 作り込み路線（[production-v15/](../production-v15/README.md)）とは独立した検証作業台。
> 動き・タイミング・カメラ・色の設計は **プリヴィズ v14.10**（[previs/v14-director-rebuild/](../previs/v14-director-rebuild/README.md)）を唯一の正とする。

## 目的

完成済みプリヴィズ **v14.10（18カット・70.5秒・1280×720・24fps）** から、Google の **Gemini Omni 1.2 Flash**（既存動画の編集・参照つきリスタイル機能）を用いて完成動画を作る手法の実用性を検証する。

### 検証の進め方（2段階）
1. **Phase 1（現行）：Google Flow によるパイロット検証（追加課金なし・Google AI Pro 枠）**
   - まず代表3カット（**R14 → R09 → R15**）を「左下ラベルなし」のクリーンな動画として切り出す。
   - Google Flow で `Omni 1.2 Flash` を選択し、参照原画＋設計プロンプトでリスタイル・対話修正を試す。
   - 出力を `scripts/eval_omni_output.py` でプリヴィズ v14.10 と定量・視覚比較する。
2. **Phase 2（Phase 1 の結果次第）：Gemini API（Interactions API）による全18カット自動パイプライン**
   - Google AI Pro 特典の月 \$10 API クレジット等を用い、3秒未満カット（R01/R02/R04/R08）のパディング・トリム、対話修正、1080p アップスケール、本編結合をスクリプト化する。

## ディレクトリ構成

| パス | 役割 |
|---|---|
| `handoff/flow_poc_guide.md` | **Google Flow 実作業手順書**（パイロット3カット別の参照画像・英語プロンプト・対話修正テンプレート） |
| `scripts/extract_clean_cuts.py` | v14.10 から左下文字ラベルなしのカット別 MP4 を書き出すスクリプト（`clean-render` / `fast-delogo` 両対応） |
| `scripts/eval_omni_output.py` | Omni 出力をプリヴィズ v14.10 と比較する定量評価・並列比較動画・レビュー画像生成スクリプト |
| `review/` | 比較用の小さな JPEG / 評価メモ（Git 管理対象） |
| `work/`・`outputs/` | ローカル作業用 MP4・Flow 出力（`.gitignore` により Git 管理対象外） |

## プリヴィズ v14.10 の最新ビジュアル基準（2026-11-25 作者承認）

プロンプト設計では、v14.10 / v15i で作者承認された以下の原則を厳守する：

- **空間と構図の厳守**：プリヴィズに映っていない岩壁・地形・追加の月光柱を AI に創作させない（PR #50 の Wan Fun-Control 失敗からの教訓）。
- **鯨は光源（芯＝真珠白、縁と光＝桜色、拍＝淡い金）**：
  - **金＝目覚め・いのち**：R09 の点灯、R10〜R12 の開花の拍、R14/R15 のひと漕ぎごとの光の脈。
  - **桜色＝つながり**：R13〜R15 の鯨の縁と光、R17 で強まる。
  - **白＝別れ**：R15 終盤で置いていかれた花弁が白へ戻り、R17b は白い雪のみ、R18 は月の白へ溶ける。
- **花弁は「白い雪」**：花弁自体を均一にピンク塗りしない。ふだんは白い雪で、鯨の光が届く近さに応じて桜色・淡い金を借りる（題名『空に降る雪』を守る）。
- **手前の花吹雪（R13〜R15）**：『秒速5センチメートル』のように、1枚ずつ目で追える実寸感と前ボケ・透け感。
- **鯨の造形（WH-01）**：全長24m、滑らかな皮膚・穏やかな腹の畝、小さく暗い眼、長い一対の胸びれ、小さな背びれ、水平尾びれ。突起・瘤・牙・斑・リボンは付けない。

## コマンド例

```bash
# 1. パイロット3カットをラベルなし完全再描画で書き出す（推奨・完全クリーン）
python3 dm/episode-01/ending/current/production-v15-omni/scripts/extract_clean_cuts.py \
  --cuts R14,R09,R15 \
  --mode clean-render \
  --out dm/episode-01/ending/current/production-v15-omni/work/pilot_v14_10

# 1b. 1秒で試したい場合（既存 mp4 から切り出し＋delogo）
python3 dm/episode-01/ending/current/production-v15-omni/scripts/extract_clean_cuts.py \
  --cuts R14,R09,R15 \
  --mode fast-delogo \
  --out dm/episode-01/ending/current/production-v15-omni/work/pilot_fast

# 2. Flow の出力動画を v14.10 プリヴィズと比較評価する
python3 dm/episode-01/ending/current/production-v15-omni/scripts/eval_omni_output.py \
  --guide dm/episode-01/ending/current/production-v15-omni/work/pilot_v14_10/R14_v14_10_clean.mp4 \
  --cand flowA=dm/episode-01/ending/current/production-v15-omni/outputs/R14_flow_01.mp4 \
  --times 1.0,2.5,4.5,6.8 \
  --sheet dm/episode-01/ending/current/production-v15-omni/review/R14_omni_vs_previs.jpg \
  --sbs dm/episode-01/ending/current/production-v15-omni/outputs/R14_previs_vs_flowA.mp4
```

## 運用ルール
- 作業ブランチで小さくコミットし、**`main` へのマージは作者判断**とする。
- 大きな動画ファイル（`.mp4` 等）は GitHub にコミットせず、比較用の軽量 JPEG と評価メモのみ `review/` に保存する。
- API キーや個人情報は一切リポジトリに書き込まない。
