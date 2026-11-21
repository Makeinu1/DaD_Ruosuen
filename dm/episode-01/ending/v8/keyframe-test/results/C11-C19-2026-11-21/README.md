# 第一話エンディング C11–C19 原画・採用台帳（2026-11-21）
**DM専用・プレイヤー閲覧禁止。** 公開GitHubにあるため、この警告はアクセス制御ではない。

> **PNG転送・照合完了（2026-11-21）**：選定8枚、C14候補1枚、比較試作34枚を無改変のままGitHubへ登録済み。旧C16の2枚も`Old/`に保全。転送当初はGit blob SHA-1・原本サイズで照合し、同日後続のGitHub Actions監査で選定・候補9点は原本台帳のSHA-256との一致を追加確認。比較試作34点は原本SHA-256を保存していないため、外部原本との独立一致は未証明。

## 現在の判定

| Cut | 対象原本 | 判定 |
|---|---|---|
| C11 | `C11.png` | provisional |
| C11.5 | `C11_5.png` | provisional |
| C12 | `C12.png` | provisional |
| C13 | `C13.png` | approved |
| C14 | `C14_latest_test.png` | unconfirmed |
| C15 | `C15.png` | approved |
| C17 | `C17.png` | approved |
| C18 | `C18.png` | approved |
| C19 | `C19.png` | approved_final |
| C16（旧） | [旧Bパターン](../Old/C16_B_petals_dense_no_flower.png) / [旧初稿](../Old/C16_t01.png) | **Old（過去版）** |

- C11〜C12の「暫定採用」は最終形態の手直し余地を残す。C11.5は余剰胸びれの修正後、作者が一旦採用とした版。
- C13は鯨を画面外にし、花びらの静止を描く採用版。
- C14は新しい銀白の波案を生成したが、**作者による明示的な採用は未確認**。採用原画として扱わない。
- C15は花畑が画面に写らない、湖上高空の鯨の修正版を採用。
- C17は自然で高密度な花吹雪と強い上昇角度の最終版を採用。C18は遠景の鯨を小さくした版を採用。
- C19は月を小さく修正した最後の**2枚目**を最終採用。画中の最後の花びらが湖面にある点は、旧演出「若い花のそばへ着地」と食い違うので動画化時に確認する。

## GitHub登録済み
- [`selected/`](selected/)：C11, C11.5, C12, C13, C15, C17, C18, C19、合計8 PNG。無加工、Git blob照合済み。
- [`candidate/`](candidate/)：C14最新試作、1 PNG。**未承認のまま**Git blob照合済み。
- [`variants/`](variants/)：制作中の比較原画34 PNG。生成時の無加工原本、Git blob照合済み。採用版に上書きしない。
- [manifest.json](manifest.json)：画像サイズとSHA-256。`github_binary_status` は登録・Git blob照合済み。
- 現行動線と演出の正本：[v10カット割り](../../../v10-shotlist.md)、[鯨の動線 v10](../../../whale-motion-v10.md)。

## 完了したバイナリ照合

- 登録対象：選定8枚、C14候補1枚、比較試作34枚、Old/C16の2枚＝計45 PNG。
- GitHub作業ブランチのtreeに全45枚のPNGが実在。Git blob SHA-1とbyte数をローカル原本からの計算値と照合して一致。
- 原本のSHA-256とGit blob SHAは[manifest.json](manifest.json)に記録（原本SHA-256は選定8枚＋C14候補）。転送当初はGitHubからの独立SHA-256照合が未実施だったが、後続のGitHub Actionsで選定・候補9点のSHA-256を原本台帳に照合して成功。比較試作34点は現物SHA-256を算出したのみ。
- C14は採否未確定。C16の新規採用画像はこのスレッドでは制作していないため、旧C16をOldに格納しており、新規C16の確定を意味しない。

**原画が表現した建造物・洞窟構造・水晶等は、世界設定の追加確定ではない。**

## C16の扱い（2026-11-21 作者指定）

- 従来の `C16_B_petals_dense_no_flower.png` と `C16_t01.png` は **Old / 過去版** として扱う。いずれも [Old/](../Old/) に **Gitオブジェクト同一SHAのままアーカイブコピー済み**。
- 過去の参照URLが壊れないよう、従来の場所も一時的に残す。今後の映像制作では従来のC16を新しい採用正本と誤認しない。
- **今回の会話では新しいC16原画は生成されていない。** 新C16の原本やハッシュは未確定。存在しない画像を代替・捏造して登録しない。
- 本PRには **Old/C16の2枚**に加え、**新規PNG43枚**（選定8枚＋C14候補1枚＋比較原画34枚）が含まれる。いずれもGit blob SHA-1とサイズを原本照合済み。

## 2026-11-21 追加監査：GitHub Actionsでの原本照合

- [原画監査の実行結果（PASS）](https://github.com/Makeinu1/DaD_Ruosuen/actions/runs/44916353650)、[監査スクリプト](https://github.com/Makeinu1/DaD_Ruosuen/blob/main/tools/github-original-transfer/audit_repository_media.py)。
- GitHub Actionsのcheckoutで取得した実ファイル45点をPythonで読込み、選定・候補9点は元のSHA-256・サイズ・Git blob SHA-1のすべてに一致。
- 旧C16アーカイブ2点はGit blob SHA-1と残置された元ファイルの同一バイト列を照合。比較試作34点は存在・PNGシグネチャ・現物SHA-256を記録。
- 比較試作34点の外部原本SHA-256は保存されていないため、GitHubにある試作原画が外部原本と完全一致するとの独立検証は未完了。原本ZIPのmanifestが入手できた場合に追加照合する。
- 自動検証は `.github/workflows/verify-original-media.yml` に保存。結果JSONはActions Artifactから取得できる。
