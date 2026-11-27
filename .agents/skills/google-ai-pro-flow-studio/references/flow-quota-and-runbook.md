# Google AI Pro × Google Flow クォータ・クレジット＆ブラウザ運用ランブック（2026年11月確認）

## 1. Google AI Pro 契約内の上限（追加課金 0 円の範囲）

- **公式URL**：`https://flow.google.com/`（旧 `labs.google/fx/tools/flow` はここへリダイレクト）
- **画像生成（Flow クレジット消費 0！）**：
  - **Nano Banana Pro**：1日最大 **100 枚**（初回生成から 24 時間でリセット・失敗時は消費なし）
  - **Nano Banana 2.1 / 2 Lite 合算**：1日最大 **1,000 枚**
  - **2K アップスケール**：1日最大 **200 枚**
- **動画生成（月間 1,000 クレジット ＋ 毎日 50 クレジット、繰越なし）**：
  - **Omni Flash 1.2（360p ドラフト）**：`1〜10秒 = 1 cr/秒`、`11〜15秒 = 2 cr/秒`（例：8秒＝8 cr、12秒＝14 cr）
  - **Omni Flash 1.2（720p 本番）**：`1〜10秒 = 3 cr/秒`、`11〜15秒 = 6 cr/秒`（例：8秒＝24 cr、10秒＝30 cr、12秒＝42 cr、14秒＝54 cr）
  - **720p → 1080p アップスケール**：`1〜10秒 = 0 cr`、`11〜15秒 = 追加1秒あたり 1 cr`
  - **Veo 3.1 Lite（720p・4/6/8秒）**：`10 cr / 回`（固定）
  - ※ 上限到達時は **即停止** し、翌日リセット（＋50 cr）または翌月リセット（＋1,000 cr）を待つ。追加クレジット購入（Top-up）は一切実行しない。

## 2. ブラウザ操作チェックリスト（公式ブラウザツール／手動引き継ぎ共通）

1. **`https://flow.google.com/` を開く**
2. **ログイン確認**：未ログイン・2FA・規約同意画面が出たら **即座にユーザーへ引き継ぐ**。
3. **残高確認**：画面右上の残クレジット表示を確認し、生成予定コストを下回っていたら **生成せず停止** する。
4. **画像生成（Nano Banana Pro）**：
   - モデル選択で **Nano Banana Pro**（アスペクト比 `16:9`）を選択。
   - 参照画像（`SheetA_whale_pcs.jpg`, `SheetB_flower_arch.jpg`, プリビズ静止画等）をアップロード。
   - プロンプトを貼り付けて生成 → 目視検品 → PNG/JPG をダウンロード → `studio_log.py record --media-type image ...` で記録。
5. **動画生成（参照画像＋プリビズ動画 → MP4）**：
   - モデル選択で **Omni Flash 1.2**（または **Veo 3.1 Lite**）を選択。
   - まずは **360p** で動きと一貫性を確認（8秒＝8 cr）→ OK なら **720p** 生成＋**0 cr 1080p アップスケール**。
   - 参照動画（15秒以下のプリビズ MP4）と承認済みキーフレーム＆設定シート（最大6枚）をアップロードし、自然言語プロンプトを貼り付けて生成。
   - 生成完了後、MP4 をダウンロード → `studio_log.py record --media-type video ...` で `studio/videos/` へ保存＆記録。

## 3. 記録されるメタデータ項目（`generation_log.jsonl` & `.meta.json`）

- `timestamp_utc`（実行時刻）
- `surface`（`antigravity-generate-image` または `google-flow-browser`）
- `model`（使用モデル名）
- `prompt`（投入プロンプト全文）
- `references`（参照素材のパスおよび SHA-256 ハッシュ一覧）
- `output_path` / `output_sha256` / `output_bytes` / `media_meta`（解像度・fps・秒数・コーデック・音声有無）
- `flow_credits_spent` / `extra_spend_jpy`（常に `0`）
- `qa_status`（`needs_review` / `approved` / `rejected`）
