# GitHub 原本転送 — Python版 v1.0

ChatGPT等で制作した**原本のバイナリ**を、メール経由にせず、作業環境に存在する画像ファイル・ZIPからGitHubの**PRブランチ**へ転送する。Python標準ライブラリと `git` / `gh` CLIだけを使用。再圧縮・変換・メール添付・強制プッシュ・自動マージは行わない。

## 前提

- Python 3.10以降、`git`、`gh`（GitHub CLI）をインストールし、`gh auth login` を済ませる。`git config user.name` と `git config user.email` を設定。
- **生成原画の実ファイルがこのPython環境から読めること**。これができなければ本スクリプトも転送できない。ChatGPT画面の画像参照IDや会話URLはローカルPNGに自動変換されない。原本を保存しZIP等にまとめて渡す。
- 公開リポジトリに秘匿素材、秘密鍵、参加者個人情報を入れない。PRは必ずレビューを挟む。

## 使い方

事前検査（ネット接続不要）：

```bash
python3 github_originals.py plan \
  --source /path/to/originals.zip \
  --destination dm/episode-01/ending/v8/keyframe-test/results/C11-C19-2026-11-21 \
  --report ./originals-local-audit.json
```

既存のルオスエン PR #29 に足りないPNGを補完して独立検証する（**PRはマージしない**）：

```bash
python3 github_originals.py upload \
  --source /path/to/Ruosuen_ending_C11-C19_all_trials_2026-11-21.zip \
  --repo Makeinu1/DaD_Ruosuen \
  --base main \
  --branch dm/ending-c11-c19-stills-20261121 \
  --pr 29 \
  --destination dm/episode-01/ending/v8/keyframe-test/results/C11-C19-2026-11-21 \
  --report ./pr29-originals-verified.json
```

新規原画を新ブランチに転送するときは `--branch art/xxx` とし `--pr` を省略する。GitHub CLIでDraft PRを作る。既存ファイルが原本と異なれば停止し、**確認後のみ** `--replace` を付与する。

ZIPの `manifest.json` が `{ "assets": [{"path":"selected/C11.png","bytes":123,"sha256":"..."}], "variants": [{"name":"trial.png","bytes":123,"sha256":"..."}] }` 形式なら、**全ファイル**について元サイズとSHA-256を必須検証。`manifest.json` がなければ画像を列挙して原本ハッシュを確定する。ソース内に余計な画像がある場合、manifestとの不一致として停止。ZIPが複数ルートの場合は `--source-root root/` を指定。

## 合格基準・異常系

- PNG等のバイト列を変更しない。
- 元ファイルSHA-256、Git Blob SHA-1（`git hash-object`相当）をローカル算出。
- 既存ファイルが同一ならskip。違う場合は `--replace` なしで停止。
- 転送したremoteブランチが対象コミットを指すこと、各tree内Git Blob SHA-1が一致することを照合。
- **GitHub Contents APIからrawファイルを独立再ダウンロード**し、各バイト数・SHA-256を再検証する。APIでrawダウンロードできなければ成功扱いにしない。
- 途中失敗時は再実行できる。ブランチの競合、ハッシュ不一致、権限拒否、READMEと原本の不整合は自動解決しない。
- 自動マージ、PRのReady化、READMEの「未転送」表記の書換えはしない。**検証レポートを受けて、作品の台帳更新とマージ判断を別途行う。**
- 秘密情報、Base64本文、メールMIME、トークンをログや成果物に保存しない。

## 実施した試験と制約

- `python3 -m unittest discover -s tests -v`: ZIP展開安全性、hash一致、manifest必須チェック、実際のローカル bare Gitリポジトリへのpush、別cloneからの再読み込み、同一原本の再実行、既存ファイルの差し替え拒否と明示更新、report上書き拒否を検証。
- **GitHub.com本番のPNG原本アップロードは、このPython実行環境からGitHubに接続できず、元のC11-C19 ZIPも読み込めないため未実施。** GitHub CLI + 元ZIPの両方にアクセスできる環境で上記コマンドを実行し、その出力とPRの変更ファイルを確認する必要がある。
- 旧 `ruosuen_complete_pr29.py` のように `gh pr ready` や `gh pr merge` を勝手に呼ぶ処理は設けていない。