# Windows PC（VideoStudio）の Claude Code に渡すプロンプト

PCで `C:\VideoStudio\projects\ruosuen\repo` を開いて Claude Code を起動し、下の枠の中をそのまま貼る。

```text
あなたはD&Dキャンペーン「ルオスエン」第1話エンディング映像『空に降る雪』の本番制作を、クラウド側のClaudeから引き継ぐ。作業場所はこのPC（VideoStudio PC：Windows、RTX 3060 12GB）。

■ 最初に読むもの（この順で）
1. リポジトリの AGENTS.md と WORLD_POLICY.md（公開リポジトリ・ネタバレ・置き場所のきまり）
2. dm/episode-01/ending/current/production-v15/README.md（手順・状態・引き継ぎのきまり）
3. dm/episode-01/ending/current/production-v15/review/R14_compare_v15a.md（前回の比較。数値だけで判断している）
4. 判断基準（作者）：「プレイヤーの感情の動きを制御して感動させること」。動き・タイミング・カメラはプリヴィズ v14.9b（dm/episode-01/ending/current/previs/v14-director-rebuild/）が唯一の正。

■ 環境（確認済み）
- リポジトリ：C:\VideoStudio\projects\ruosuen\repo（ブランチ production/v15-blender-base-20261124、PR #50 はドラフト）
- Blender 5.3："C:\Program Files\Blender Foundation\Blender 5.3\blender.exe"
- Python：Blender内蔵 "C:\Program Files\Blender Foundation\Blender 5.3\5.3\python\bin\python.exe"、環境変数 PYTHONPATH=C:\VideoStudio\projects\ruosuen\pylib（Pillow・scipy入り）
- ffmpeg：C:\ffmpeg\bin\ffmpeg.exe
- ComfyUI：C:\VideoStudio\ComfyUI_windows_portable、API http://127.0.0.1:8188。入っている動画モデルは Wan 2.2 TI2V-5B だけ（WanVaceToVideo / Wan22FunControlToVideo のノードはあるがモデルなし）
- 成果物：C:\VideoStudio\projects\ruosuen\renders\R14_a\（beauty\、paint\、R14_guide.mp4、R14_paint.mp4、wan\R14_guide_wan_d45_s7.mp4・d62・d78、compare_R14.png）

■ やること
1. 【目で見る評価】前回はクラウド側から画像が見られず数値だけで判断した。今回は実際に見る。
   - compare_R14.png と、各動画の 0.5・2・3.5・4.5秒のフレーム（ffmpegで書き出す）を見る。
   - 参考：原画 dm/episode-01/ending/images/adopted/CUT05_KEY_whale_emerges.png、CUT09_KEY_climax.png、鯨の設定 dm/episode-01/ending/v8/keyframe-test/refs/WH01_identity_sheet.png
   - 見る観点：(a) 鯨の位置・大きさ・向きがガイドと同じか (b) 鯨が原画の鯨と同じ生き物に見えるか (c) 花弁の雪が「流れ」として美しいか、ちらつかないか (d) 絵として原画と並べて違和感がないか (e) 夜の暗さと月光柱が保たれているか
   - 結果を review/R14_visual_review_v15a.md に書く（版ごとに良い点・悪い点、どれを本命にするかの推薦と理由）。比較用の小さなjpg（横640程度、合計300KB以内）を review/ に置いてよい。動画や連番はリポジトリに入れない。
2. 【方式①の改善案】paint 版の弱点を1つ選んで直し、R14 の数フレームで前後比較する（blender/render_cut.py の LOOK、post/paint.py）。全192フレームの再描画は、改善が見た目で確かめられたときだけ。
3. 【方式③の強化は作者に確認してから】動きを固定したまま強く描き直すために、制御つきモデル（Wan 2.2 Fun-Control 5B、または VACE）を入れる案がある。ダウンロード（約10GB）の前に必ず作者に聞く。許可が出たら、ComfyUI で使える現行のファイル名と置き場所を公式の配布元で確かめ、12GBで動く設定を選び、Blender から奥行き（または輪郭）の制御映像を出して wan/ に制御版スクリプトを作る。既存の wan/vid2vid.py とワークフローファイルは壊さない。
4. 【記録】README.md の「状態」表を更新し、小さくコミットして production/v15-blender-base-20261124 に push する。
   - このPCには GitHub の認証が入っていない。push で認証を求められたら作者に「Git Credential Manager のブラウザ画面でサインインしてほしい」と頼む。トークンやパスワードをファイル・コマンド履歴・リポジトリに書かない。
   - コミットメッセージの最後に Co-Authored-By 行を付ける。PR #50 への説明の追加はよいが、マージはしない（作者が判断する）。

■ きまり
- リポジトリは公開。DM資料は dm/** の外に出さない。Pages・SECTIONS・llms.txt に何も足さない。
- プリヴィズのタイミング・カメラ・鯨の経路・花弁のシミュレーションを手で作り直さない。直したいときは理由を書いて作者に提案する。
- 曲は作らない。4人のシルエットと最後の光は AI に描かせず、Blender から合成する方針。
- Google Flow（方式②）は作者のアカウントで動かすもの。作者が頼まない限り操作しない。手順は handoff/flow_R14.md。
- 迷ったら、取り返しのつかない操作（大きなダウンロード、既存ファイルの削除、設定の変更）の前に作者に聞く。

■ 終わったら作者への報告（日本語で短く）
- 目で見て、どの方式がよかったか（理由つき）
- 直したこと、push したコミット
- 作者に決めてほしいこと
```
