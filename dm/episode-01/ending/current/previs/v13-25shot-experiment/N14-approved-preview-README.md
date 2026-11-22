# N14（45〜51秒）作者承認済みプリヴィズ／2026-11-22

> DM専用。**N14の演技方針と「少し大きい」画角の決定を保存**。ここをマージしても、25カット全体や全演技、物理シミュレーションの完成を意味しない。公開Pagesには掲載しない。

## 今回確定してよい内容

- カメラの見せ方：**②横並走**。鯨の向き・ロールが見えなくなる過剰追尾は避ける。
- 白鯨の演技：**クジラ類に近い主に上下（dorsoventral）方向の尾びれ運動**。頭は比較的安定し、胴体後半から尾柄へ動きが伝わる。
- 6秒間の主なリズム：**ひと泳ぎ→ゆったり滑空**。完全な魚的左右尾振り案・一体回転バンク案を採らない。
- 画面の大きさ：3案の**中央「少し大きい」**を採用。全身、進行方向の余白、前・中・後景の白金色の花雪を残す。
- 見せ場：N14、世界時刻45〜51秒。次工程はN13→N14→N14.5→N15の連続性の検証。

## 再生成用ソース

- [白鯨の生体に近い上下運動と比較試作](ruosuen_whale_natural_swim_comparison.py)
- [採用画角を再生成するメインスクリプト](ruosuen_n14_approved_medium.py)
- [既存B2白金花雪描画を保った追加描画](ruosuen_flower_snow_B_vs_B2.py)
- [原本v12.5をimportする25カット比較](render_19_vs_25_from_original.py)
- [監督レビューと未採用の差分](N14-swim-strength-2026-11-22.md)

実行例（Python 3.11、`numpy Pillow`、`fonts-noto-cjk ffmpeg`）：

```bash
python ruosuen_n14_approved_medium.py --out artifacts/N14-approved-medium --fps 8
```

既存の基礎モデル`../v12-lowpoly-v12.5-cut-test/`（原本）の`STATIONS`・`MESH`・空間ジオメトリには変更を加えない。

## 動画／静止画

GitHub Actions `render-v13-n14-approved-medium.yml` は、以下の生成物を **DMフォルダ内でGitコミット**し、同時にActions artifactとして保存する。

- [作者承認画角の自然な泳ぎ・6秒動画](artifacts/N14-approved-medium/N14-natural-glide-approved-medium-45-51s.mp4)（1280×720、8fps、48フレーム）
- [旧画角／採用画角／大きい案の3画面比較](artifacts/N14-approved-medium/N14-size-comparison-45-51s.mp4)
- [採用画角48秒静止画](artifacts/N14-approved-medium/N14-natural-glide-approved-medium-48s.png)
- [サイズ比較48秒静止画](artifacts/N14-approved-medium/N14-size-comparison-48s.png)
- [再現QA](artifacts/N14-approved-medium/N14-approved-medium-QA.json)

**検証済み**：ローカルでは原本v12.5の12枚の代表フレーム完全一致を確認。現行3Dローポリの形状・うねりは**簡易リグの暫定再現**であり、WH-01完成モデルではない。

## 区別するべき未決事項

25カット構成の正式採用、花雪粒子数・形状の最終確定、N13→N14→N14.5の視線連続性、尾柄・胸びれの最終リギング、正確な空中物理の整合、N15以降の離脱演技は未決。これらを勝手に確定しない。
