# v15 本番制作ベース（Blender）と R14 3方式比較 — ランブック

> DM資料（ネタバレ）。Pages・SECTIONS・llms.txt に載せない。
> 対象：ep.1 エンディング『空に降る雪』。判断基準（作者 2026-11-24）：**プレイヤーの感情の動きを制御して感動させること。**
> プリヴィズ **v14.10**（`../previs/v14-director-rebuild/`）が **唯一の正**。尺・カメラ・鯨の動き・花弁の動きはここで作り直さない。

このフォルダは「誰が続きをやっても同じ結果になる」ための作業台。Claude・Gemini・Codex・人のどれが引き継いでもよい。

## 1. 全体の流れ

```
previs v14.10 (Python)                        ← 動き・タイミング・カメラの正
   │ bridge/export_cut.py  (カットごとに書き出し)
   ▼
cache/<cut>/cut.json + petals/f_####.npz      ← カメラ・鯨の骨格フレーム・鯨の光・花弁の位置
   │ blender/render_cut.py (Blender 5.3, EEVEE)
   ▼
renders/<cut>_<tag>/beauty/####.png  →  <cut>_guide.mp4（ガイド映像）
   ├─【本命 v15i】render_cut.py --look sakura --set palette=source --control near / base / petals / whale_matte → post/finish.py
   │              → final/ + <cut>_final_<版>.mp4             （AIなし。層に分けて筆致・花弁の光・色を仕上げる）
   ├─ 方式① post/paint.py      → paint/ + <cut>_paint.mp4   （AIなし・絵画調の後処理。v15d で finish.py に置き換え）
   ├─ 方式② Google Flow（Gemini Omni / Veo, video-to-video） → handoff/flow_R14.md の手順で人が操作
   ├─ 方式③ wan/vid2vid.py     → wan/*.mp4                  （ローカル Wan 2.2 TI2V-5B で描き直し）
   └─ 方式③制御【保留 2026-11-25：岩壁・月光を創作する】 render_cut.py --control depth → <cut>_control_depth.mp4
                 → wan/vid2vid_control.py --clear-air（5秒ずつ）→ post/join_segments.py（重なりをクロスフェード）
                 → post/overlay_petals.py ← render_cut.py --control petals（プリヴィズの花弁だけの層）
                 → <cut>_functl_petals_<版>.mp4   （鯨・カメラ・花弁はプリヴィズどおり、絵は Fun-Control）
```

## 2. 状態（更新したらここを書き換える）

| 項目 | 状態 | メモ |
|---|---|---|
| PC環境（リポジトリ取得・Pillow/scipy） | 済 2026-11-24 | `C:\VideoStudio\projects\ruosuen\{repo,pylib}` |
| 書き出し R14 | 済 | 192フレーム、花弁 2万→8.5万（視野内） |
| Blenderシーン（洞窟・裂け目・地形・水・鯨・月光柱・花弁） | 済（大枠） | 月光柱はプリヴィズ `moonlit` と一致を確認 |
| **R14 完成版候補** | **済 v15i 2026-11-25** | `renders/R14_i/R14_final_v15i.mp4`（AIなし。**鯨が光源（芯は白、光は桜色、花弁は白い雪で近くだけ染まる）＋ひと漕ぎごとに淡い金**、少なくゆっくりした花弁、90 mm 試験）。作り方は `review/R14_visual_review_v15a.md` の v15d〜v15i 節。色の方針 B は作者承認。v15h（金なし）は `R14_h/`、v15g は `R14_g/` |
| プリヴィズ v14.10 | **済 2026-11-25（作者承認）** | 鯨は光源＋金＝目覚め・桜色＝つながり・白＝別れ、花弁は近さで色を借りる、R13〜R15 は手前の花吹雪が主役（突風が運ぶ）、R14 は 90 mm。経緯は `review/previs_proposal_near_blizzard.md`。R14 のキャッシュは v14.10 から書き出し直し済み（旧 55 mm は `cache/R14_v2_55mm`） |
| 花弁の番号（idx） | 済 v15e | `export_cut.py` が花弁ごとの番号を書き出す（遠景の花弁を増やしても飛ばない）。**他のカットは export し直すこと**。R14 の旧キャッシュは `cache/R14_v1_noid` |
| 近景の花吹雪 | 済 v15e（作者の指示）、v16 で空間に置く形も | プリヴィズ v14.10 で R13〜R15 の主役に。`NearSnow` は画面に置く形（R14、固定カメラ）と空間に置く形（`near_world=1`：首を振るカメラ、R13/R15/R17b） |
| R14 本描画 1280×720 | 済 v15c 2026-11-25 | `renders/R14_c/`：プリヴィズと照合して合わせた版（尾の位相・鯨の描き方・目・空気と花弁）。並べた動画 `R14_previs_vs_v15c.mp4`。v15b は `R14_b/`、v15a は `R14_a/` |
| 尾の打ち方の位相 | 済 v15c | プリヴィズの `PATH.retime` を Blender 側にも。**他のカットは export し直すこと**（`cut.json` に `stroke_phase0` が要る） |
| 鯨の色（尾の桃色・胸びれの黄緑） | 済 v15b | glbの `COLOR_0` はリグ用データ。`Whale._drop_vertex_tint` で Base Color から外した |
| 方式① 絵画調（控え） | 済 v15b | 鯨をマスクして筆面・雪の点を乗せないよう修正（ざらつき解消）。`renders/R14_b/paint` |
| 方式② Flow | 未（作者の操作待ち） | `handoff/flow_R14.md` |
| 方式③ Wan | 済（d45/d62/d78） | 目で見ると d62 で鯨の形が崩れ、d78 は鯨が逆向き・別の生き物。岩と月を描き足す |
| 方式③制御 Fun-Control 5B | **保留**（2026-11-25 作者の指摘で、洞窟の岩壁・月光・鯨の形がプリヴィズと違うと確認）。R14 8秒 v15b | 花弁なしで描かせ（`--clear-air`）、プリヴィズの花弁を重ねる案Bを採用。0〜120と71〜191の2本をつないだ192フレーム：`renders/R14_b/R14_functl_petals_v15b.mp4`（960×544）。残り：月光の向きはモデルの創作、鯨に陰影なし、解像度 |
| 3方式の比較 | 済（目視） | `review/R14_visual_review_v15a.md`。**本命は Blender の作り込み＋`finish.py`（v15d）** |
| **R15 本番 v16a**（最接近） | **済 2026-11-25** | `renders/R15_v16a/R15_v16a_final.mp4`。`--look r15`：手前の花吹雪を空間に置く形（`NearSnow` world mode：距離帯ごとの周期箱で密度が崩れない、シミュレーションの雪の流れに乗る、世界時間で動くのでスローで止まる、シャッターの尾）、筆致・紙の粒は首振りに乗る（`finish.py --cam-json`）、最接近で空気が明るむ（`climax`）、スローの金のきらめき。明るさの山はプリヴィズと同じ形（30→88→47） |
| **R18 本番 v16a**（月へ溶ける） | **済 2026-11-25** | `renders/R18_v16a/R18_v16a_final.mp4`。`--look r18`：開口部をプリヴィズの輪郭どおりに切る（100 mm で段差が出ない）、岩は三角の面、夜空・星（プリヴィズと同じ700個）・月（プリヴィズが開口部に置く位置と大きさ、海・縁の光・暈）、鯨は尾から月の色になり透けて溶ける。月・空・岩をプリヴィズの画と領域ごとに測って合わせた（月 212/201 など） |
| **R17b 本番 v16a**（4人が見送る白い雪） | **済 2026-11-25** | `renders/R17b_v16a/R17b_v16a_final.mp4`。`--look r17b`：4人は Blender で作ったシルエット（`Party`：プリヴィズの体格の名もない外套の人影、顔は上を向く、上からの光だけ）、白い雪はシミュレーションの落ちる雪に乗る、手前の層はホールドアウト（人影の後ろの花弁が透けない）、`--floor` で暗い洞窟を残し人影が読める |
| **R13 本番 v16a**（花畑から花弁が離れる） | **済 2026-11-25** | `renders/R13_v16a/R13_v16a_final.mp4`。`--look r13`：花の群落を本物の花で（`FlowerField`：FL-01 モデルをプリヴィズの花 6,777 株の位置に、離れた花弁の数で花びらが減る、頭は横に0.5倍）、レンズの5 m以内を通る花弁は本物の花弁の形で（`PetalsNear`）、地面は鯨の光を受けない |
| 雪の山場の通し | 済 2026-11-25 | `renders/climax_v16/climax_previs_vs_v16a.mp4`（33.0–64.5 s、R17 はプリヴィズ）。カット点の明るさの跳ね：R13→R14 +20（プリヴィズ +6）、R14→R15 −33（−12）。R14 v15i が両隣より明るい → 作者に確認中。レビュー：`review/snow_climax_v16.md` |
| 他カット（R01〜R12, R17, R19） | 未 | 雪の山場（R13〜R18）のあと |

## 3. PCでの実行（VideoStudio PC：RTX 3060 12GB、Blender 5.3、Windows）

置き場所：`ROOT = C:\VideoStudio\projects\ruosuen`（`repo/` `pylib/` `cache/` `renders/`）。gitへは書き戻さない（PCにGitHubの認証はない）。

### 3.1 MCP `blender_run` から（Claude）
MCPの応答は約230秒で切れるが、Blender側の処理は続く。長い処理は投げたあと `list_outputs` で進み具合を見る。

```python
import os, subprocess, runpy
ROOT = os.path.join(PROJECTS_DIR, 'ruosuen'); REPO = os.path.join(ROOT, 'repo')
BR = 'production/v15-blender-base-20261124'
subprocess.run(['git','-C',REPO,'fetch','--depth','1','origin',BR]); subprocess.run(['git','-C',REPO,'checkout','-B',BR,'FETCH_HEAD'])
runpy.run_path(os.path.join(REPO,'dm','episode-01','ending','current','production-v15','pc_run.py'),
               init_globals={'ARGS': ['--cut','R14','--steps','export,render,encode,paint','--tag','a']}, run_name='__main__')
```

### 3.2 PCのターミナルから（Gemini CLI / Codex CLI / 人）
```bat
cd C:\VideoStudio\projects\ruosuen\repo
git fetch origin production/v15-blender-base-20261124 && git checkout production/v15-blender-base-20261124
"C:\Program Files\Blender Foundation\Blender 5.3\blender.exe" -b -P dm\episode-01\ending\current\production-v15\pc_run.py -- --cut R14 --steps export,render,encode,paint --tag a
"C:\Program Files\Blender Foundation\Blender 5.3\5.3\python\bin\python.exe" dm\episode-01\ending\current\production-v15\wan\vid2vid.py --video C:\VideoStudio\projects\ruosuen\renders\R14_a\R14_guide.mp4 --out C:\VideoStudio\projects\ruosuen\renders\R14_a\wan --denoise 0.55
rem 本命 v15i：層を描く → 仕上げ（PYTHONPATH=pylib）
"C:\Program Files\Blender Foundation\Blender 5.3\blender.exe" -b -P dm\episode-01\ending\current\production-v15\blender\render_cut.py -- --cache C:\VideoStudio\projects\ruosuen\cache\R14 --out C:\VideoStudio\projects\ruosuen\renders\R14_i --res 1280 --look sakura --set palette=source --control near
"C:\Program Files\Blender Foundation\Blender 5.3\blender.exe" -b -P dm\episode-01\ending\current\production-v15\blender\render_cut.py -- --cache C:\VideoStudio\projects\ruosuen\cache\R14 --out C:\VideoStudio\projects\ruosuen\renders\R14_i --res 1280 --look sakura --set palette=source --control base
"C:\Program Files\Blender Foundation\Blender 5.3\blender.exe" -b -P dm\episode-01\ending\current\production-v15\blender\render_cut.py -- --cache C:\VideoStudio\projects\ruosuen\cache\R14 --out C:\VideoStudio\projects\ruosuen\renders\R14_i --res 1280 --look sakura --set palette=source --control petals
"C:\Program Files\Blender Foundation\Blender 5.3\blender.exe" -b -P dm\episode-01\ending\current\production-v15\blender\render_cut.py -- --cache C:\VideoStudio\projects\ruosuen\cache\R14 --out C:\VideoStudio\projects\ruosuen\renders\R14_i --res 1280 --look sakura --set palette=source --control whale_matte
"C:\Program Files\Blender Foundation\Blender 5.3\5.3\python\bin\python.exe" dm\episode-01\ending\current\production-v15\post\finish.py --layers C:\VideoStudio\projects\ruosuen\renders\R14_i --dst C:\VideoStudio\projects\ruosuen\renders\R14_i\final --dab 0.3 --fine 0.12 --mist 0.25 --gain 1.1 --ring 0.15 --bloom 0.7 --near-tint 1.0,0.55,0.75 --near-tint-gold 1.0,0.82,0.48 --mp4 C:\VideoStudio\projects\ruosuen\renders\R14_i\R14_final_v15i.mp4
rem 方式③制御：奥行きの制御映像 → Fun-Control（models/diffusion_models/wan2.2_fun_control_5B_bf16.safetensors が要る）
"C:\Program Files\Blender Foundation\Blender 5.3\blender.exe" -b -P dm\episode-01\ending\current\production-v15\blender\render_cut.py -- --cache C:\VideoStudio\projects\ruosuen\cache\R14 --out C:\VideoStudio\projects\ruosuen\renders\R14_b --res 960 --control depth
"C:\Program Files\Blender Foundation\Blender 5.3\blender.exe" -b -P dm\episode-01\ending\current\production-v15\blender\render_cut.py -- --cache C:\VideoStudio\projects\ruosuen\cache\R14 --out C:\VideoStudio\projects\ruosuen\renders\R14_b --res 1280 --control petals
"C:\ffmpeg\bin\ffmpeg.exe" -framerate 24 -i C:\VideoStudio\projects\ruosuen\renders\R14_b\control_depth\%04d.png -c:v libx264 -crf 14 -pix_fmt yuv420p C:\VideoStudio\projects\ruosuen\renders\R14_b\R14_control_depth.mp4
set PY="C:\Program Files\Blender Foundation\Blender 5.3\5.3\python\bin\python.exe"
set W=C:\VideoStudio\projects\ruosuen\renders\R14_b\wanctl
rem 1本目 0〜120（約8分半）
%PY% dm\episode-01\ending\current\production-v15\wan\vid2vid_control.py --control C:\VideoStudio\projects\ruosuen\renders\R14_b\R14_control_depth.mp4 --no-ref --clear-air --out %W%
rem 2本目 71〜191：初めの絵＝1本目の71フレーム目
"C:\ffmpeg\bin\ffmpeg.exe" -i %W%\R14_control_depth_functl_none_clear_s7_f0.mp4 -vf "select=eq(n\,71)" -frames:v 1 %W%\seg1_clear_f71.png
%PY% dm\episode-01\ending\current\production-v15\wan\vid2vid_control.py --control C:\VideoStudio\projects\ruosuen\renders\R14_b\R14_control_depth.mp4 --start 71 --ref %W%\seg1_clear_f71.png --clear-air --out %W%
rem つなぐ → プリヴィズの花弁を重ねる（PYTHONPATH=pylib が要る）
%PY% dm\episode-01\ending\current\production-v15\post\join_segments.py --a %W%\R14_control_depth_functl_none_clear_s7_f0.mp4 --b %W%\R14_control_depth_functl_img_clear_s7_f71.mp4 --start2 71 --out %W%\R14_clear_join.mp4
%PY% dm\episode-01\ending\current\production-v15\post\overlay_petals.py --paint %W%\R14_clear_join.mp4 --petals C:\VideoStudio\projects\ruosuen\renders\R14_b\control_petals --start 0 --out C:\VideoStudio\projects\ruosuen\renders\R14_b\R14_functl_petals_v15b.mp4
```
`pc_run.py` の手順：`export`（プリヴィズ書き出し）→ `render`（EEVEE）→ `encode`（ガイドmp4）→ `paint`（方式①）→ `wan`（方式③、ComfyUIが起動していること）。

### 3.2b v16：カットごとのジョブ（`renders/job_cut.py`、PC 上）
環境変数で指定して Blender で走らせる（層を描いて `finish.py` まで）。`--python-exit-code 1` を付けるとスクリプトの失敗が戻り値に出る。
```bat
set CUT=R15& set TAG=R15_v16a& set LOOK=r15& set LAYERS=base,near,petals,whale_matte& set CAMJSON=1& set MP4=1
set FIN=--stroke 0.025 --hue 0.1 --dab 0.12 --mist 0.18 --bloom 0.5 --gain 1.0 --whale-detail 0.3
"C:\Program Files\Blender Foundation\Blender 5.3\blender.exe" -b --python-exit-code 1 -P C:\VideoStudio\projects\ruosuen\renders\job_cut.py
```
| カット | LOOK | LAYERS | FIN（`finish.py` の追加引数） |
|---|---|---|---|
| R15 | r15 | base,near,petals,whale_matte（CAMJSON=1） | `--stroke 0.025 --hue 0.1 --dab 0.12 --mist 0.18 --bloom 0.5 --gain 1.0 --whale-detail 0.3` |
| R18 | r18 | base,petals,whale_matte | `--dab 0.3 --fine 0.12 --mist 0.25 --gain 1.1 --ring 0.15 --bloom 0.5 --stroke 0.0 --sat 1.0` |
| R17b | r17b | base,near,petals,whale_matte | `--dab 0.3 --fine 0.12 --mist 0.4 --gain 1.2 --ring 0.15 --bloom 0.5 --stroke 0.05 --sat 1.0 --floor 0.03,0.04,0.06` |
| R13 | r13 | base,near,petals,whale_matte（CAMJSON=1） | `--dab 0.3 --fine 0.12 --mist 0.15 --gain 1.0 --ring 0.15 --bloom 0.6 --stroke 0.1 --sat 1.1` |

書き出し（`EXPORT=1`）は v16 から `near_k`・`near_flow`・`slow`・`climax`（フレームごと）、`moon`（開口部の月）、R10〜R13 は `flowers.npz` も書く。**v16 の見た目を使うカットは書き出し直すこと。**

### 3.3 Linux / Colab で見た目を試す
`pip install bpy==5.3.0 numpy pillow scipy` で同じ `render_cut.py` が動く（GPUなしでもEEVEEがソフト描画で1枚40〜80秒）。
```
python bridge/export_cut.py --cut R14 --out cache/R14 --every 48
python blender/render_cut.py -- --cache cache/R14 --out out/R14 --res 640 --frames 96:97
python post/paint.py --src out/R14/beauty --dst out/R14/paint
```

## 4. 見た目の調整点（`blender/render_cut.py` の `LOOK['guide']`、または `--set key=value`）

| キー | 意味 | 現在 |
|---|---|---|
| `vol_density` | 洞窟の空気の濃さ（月光柱・鯨の光のにじみ） | 0.00035 |
| `moon_strength` / `moon_color` | 月光 | 4.0 / 青白 |
| `whale_light_w` / `whale_light_vol` | 鯨の光の強さ / 空気へのにじみ | 1.5e5 / 0.5 |
| `whale_emit` | 鯨の体の発光（点火の進み・ひと掻きごとの光の波はプリヴィズと同じ式） | 0.8 |
| `petal_emit` / `fruit_emit` | 花弁の白 / 金の実りの光 | 1.3 / 1.0 |
| `petal_min_px` | 遠くの花弁の最小の大きさ（画素） | 0.8 |

### 注意（ハマりどころ）
- **空気をワールドの霧にしないこと**。無限遠の霧が月光（太陽ライト）を全部吸収し、光柱が出なくなる。空気は `CaveAir` の箱（体積オブジェクト）で持つ。
- 鯨の光は体の中心にあるので影を切っている（`use_shadow=False`）。
- 本番モデル `wh01_v20_hero.glb` はプリヴィズの鯨と同じ寸法・向き（頭が+x、上が+z）。左右対称なので横向きの符号は形に影響しない。変形は `v14_world.deform` を本番モデルの頂点にそのままかけている。
- 花弁は毎フレーム作り直す板ポリ（カメラ向き）。加算合成なので重なり順の問題がない。

## 5. 引き継ぎのきまり（Notion Agent Operating Guide v0.0.9 に従う）
- 作業はブランチに小さくコミット（v15：`production/v15-blender-base-20261124`、PR #50 で main へマージ済み。v16：`production/v16-snow-climax-20261125`）。**マージは作者の指示があるときだけ**。
- 依頼をGeminiなど外部エージェントに出すときは、Notionのルオスエン配下のプロジェクト管理DBにタスクを作り、本文は依頼だけ（このREADMEへのリンク・置き場所・完了条件）。設定・プロンプト・結果はGitHubに置く。
- 成果物はPRでGitHubへ。大きな動画・連番はリポジトリに入れない（PCの `renders/` に置き、比較用の小さな画像だけ `review/` に）。
- 秘密情報（APIキー・パスワード）は書かない。リポジトリは公開。
- 確認用の画像をClaudeのサンドボックスへ持ってくるときは `post/peek.py`（PCのURLはサンドボックスから直接取れない）。

## 6. この先
1. R14で3方式を比べ、作者に選んでもらう（基準：感情が動くか・鯨が同一に見えるか・花弁の雪が美しいか・ちらつき）。
2. 選んだ方式で R13→R15→R17b→R18 の「雪の山場」を先に作る。
3. 残りのカット。4人のシルエットと最後の光はBlenderから合成で重ねる（AIに描かせない）。
