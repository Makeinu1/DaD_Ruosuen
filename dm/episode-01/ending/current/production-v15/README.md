# v15 本番制作ベース（Blender）と R14 3方式比較 — ランブック

> DM資料（ネタバレ）。Pages・SECTIONS・llms.txt に載せない。
> 対象：ep.1 エンディング『空に降る雪』。判断基準（作者 2026-11-24）：**プレイヤーの感情の動きを制御して感動させること。**
> プリヴィズ v14.9b（`../previs/v14-director-rebuild/`）が **唯一の正**。尺・カメラ・鯨の動き・花弁の動きはここで作り直さない。

このフォルダは「誰が続きをやっても同じ結果になる」ための作業台。Claude・Gemini・Codex・人のどれが引き継いでもよい。

## 1. 全体の流れ

```
previs v14.9b (Python)                        ← 動き・タイミング・カメラの正
   │ bridge/export_cut.py  (カットごとに書き出し)
   ▼
cache/<cut>/cut.json + petals/f_####.npz      ← カメラ・鯨の骨格フレーム・鯨の光・花弁の位置
   │ blender/render_cut.py (Blender 5.3, EEVEE)
   ▼
renders/<cut>_<tag>/beauty/####.png  →  <cut>_guide.mp4（ガイド映像）
   ├─ 方式① post/paint.py      → paint/ + <cut>_paint.mp4   （AIなし・絵画調の後処理）
   ├─ 方式② Google Flow（Gemini Omni / Veo, video-to-video） → handoff/flow_R14.md の手順で人が操作
   └─ 方式③ wan/vid2vid.py     → wan/*.mp4                  （ローカル Wan 2.2 TI2V-5B で描き直し）
```

## 2. 状態（更新したらここを書き換える）

| 項目 | 状態 | メモ |
|---|---|---|
| PC環境（リポジトリ取得・Pillow/scipy） | 済 2026-11-24 | `C:\VideoStudio\projects\ruosuen\{repo,pylib}` |
| 書き出し R14 | 済 | 192フレーム、花弁 2万→8.5万（視野内） |
| Blenderシーン（洞窟・裂け目・地形・水・鯨・月光柱・花弁） | 済（大枠） | 月光柱はプリヴィズ `moonlit` と一致を確認 |
| R14 本描画 1280×720 | 済 | `renders/R14_a/`（EEVEE 1フレーム約0.5秒） |
| 方式① 絵画調 | 済（試作） | 追従度0.958。夜の暗さを保つ版に修正済み |
| 方式② Flow | 未（作者の操作待ち） | `handoff/flow_R14.md` |
| 方式③ Wan | 済（d45/d62/d78） | 制御モデルなしでは d62 が上限。d78 は鯨が位置から外れる |
| 3方式の比較 | 済（暫定） | `review/R14_compare_v15a.md`、シートはPC `renders/R14_a/compare_R14.png` |
| 他カット（R01〜R19） | 未 | R14で方式を決めてから |

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
```
`pc_run.py` の手順：`export`（プリヴィズ書き出し）→ `render`（EEVEE）→ `encode`（ガイドmp4）→ `paint`（方式①）→ `wan`（方式③、ComfyUIが起動していること）。

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
- 作業は `production/v15-blender-base-20261124` ブランチに小さくコミット。**マージは作者がする**（エージェントはしない）。
- 依頼をGeminiなど外部エージェントに出すときは、Notionのルオスエン配下のプロジェクト管理DBにタスクを作り、本文は依頼だけ（このREADMEへのリンク・置き場所・完了条件）。設定・プロンプト・結果はGitHubに置く。
- 成果物はPRでGitHubへ。大きな動画・連番はリポジトリに入れない（PCの `renders/` に置き、比較用の小さな画像だけ `review/` に）。
- 秘密情報（APIキー・パスワード）は書かない。リポジトリは公開。
- 確認用の画像をClaudeのサンドボックスへ持ってくるときは `post/peek.py`（PCのURLはサンドボックスから直接取れない）。

## 6. この先
1. R14で3方式を比べ、作者に選んでもらう（基準：感情が動くか・鯨が同一に見えるか・花弁の雪が美しいか・ちらつき）。
2. 選んだ方式で R13→R15→R17b→R18 の「雪の山場」を先に作る。
3. 残りのカット。4人のシルエットと最後の光はBlenderから合成で重ねる（AIに描かせない）。
