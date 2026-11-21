# GitHub Actions による原本画像の事後検査

この監査は、GitHub `main` からActions Runnerが取得したPNG実体をPythonで読み、`manifest.json` に登録した原本のSHA-256・Git Blob SHA-1と照合します。**元画像の再生成や上書きは行いません。**

対象はC11–C19の選定・候補9枚（原本サイズ／SHA-256／Git Blob SHA-1を照合）、比較試作34枚（存在・PNGシグネチャ・サイズ・現在のSHA-256をレポートに記録）、旧C16アーカイブ2枚（登録Git Blob SHA-1と、残置された旧版ファイルの内容一致を確認）です。

比較試作34枚は、プロジェクトmanifestに元ファイル個別のSHA-256が保存されていません。**監査時に算出したSHA-256はGitHub内の現物を示すもので、外部原本との独立一致証明ではありません。** もし元ZIPの完全なmanifestが見つかれば比較試作34枚の原本SHA-256も別途照合してください。

GitHub Actionsのワークフロー `Verify original PNG records` により、Pull Request、関連ファイルの`main`更新、手動実行で検査します。結果は`original-media-audit.json`をActions Artifactとして保存します。Pythonだけで動かす場合：

```bash
python3 tools/github-original-transfer/audit_repository_media.py \
  --repo-root . \
  --manifest dm/episode-01/ending/v8/keyframe-test/results/C11-C19-2026-11-21/manifest.json \
  --output original-media-audit.json
```

このチェックはGitHubからRunnerが取得したバイト列の検査です。GitHub REST Contents APIによる全45枚の独立再ダウンロード検査、採用判断、外部原本ZIP照合は含みません。