# Colab GPU レンダー環境（DM専用）

**DM専用・ネタバレあり。プレイヤー閲覧禁止。公開Pages対象外。**

`ruosuen_colab_render.ipynb` は、作者の Google Colab（Google AI Pro 付帯の Colab 特典）で Blender Cycles GPU レンダーを行うための共通ノートブック。

- 開き方：Drive `マイドライブ/Ruosuen_Render/ruosuen_colab_render.ipynb` を Colab で開く（このファイルと同内容）。
- 毎回 GitHub `main` を取得して実行するので、スクリプトの正本はこのリポジトリ。
- 出力：Drive `マイドライブ/Ruosuen_Render/renders/<日時>_<スクリプト名>_<commit>/`、ログは `logs/`。
- 既定 GPU は L4（約1.7ユニット/時）。空きがなければ T4。A100/H100 は最終本番のみ。
- 最後のセルで自動切断（ユニット節約）。
- 実行するスクリプトはセル1の `RENDER_SCRIPT` で切り替える。現状あるのは旧V7（90秒/16カット）用のみで、現行 v12.5（70秒/19カット）用の Blender シーンは未作成。
- 旧 `v7_blender_cycles/scripts/run_step5*_colab.py`（colab-mcp CLI＋base64分割転送）は履歴として残す。
