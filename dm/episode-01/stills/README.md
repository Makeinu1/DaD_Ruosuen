# E01-08A 投影静止画制作ハブ
> DM専用・SPOILER WARNING。Public GitHubでありアクセス制御ではない。Pages・プレイヤー向けAIの導線には追加しない。
2026-11-28 v0.1／作者合意の制作対象を整理した設計案。今回のタスクは **E01-08A-A00（制作仕様・管理基盤の登録）**。本PRのマージ・基準原画採用は別の作者判断。新規画像制作は本PRの対象外。

## 読む順番
1. [style.md](style.md) — 変更してはいけない画風・色・構図・投影規約。
2. [asset-register.json](asset-register.json) — 素材と状態の唯一の正本（シーン指示、参照、表示条件、採用、原本とSHA-256も保持）。
3. [scene-briefs.md](scene-briefs.md) — 台帳の人間向け作画指示一覧。初期スナップショット。改訂時は台帳から同期生成する。
4. [production-tasks.md](production-tasks.md) — 依存関係、担当、品質ゲート、承認フロー。
5. [review-and-cues.md](review-and-cues.md) — 卓上キュー、レビュー票、原本移管、投影テスト。

目的は第一話の体験を強めること。紙の探索地図・戦闘マップ・動くNPC・映像・カードは別工程。画像を増やしても卓上の切替を強制しない。
参照基準: main `434b17847b78c953703fcd175d9d853f5efa307a`（2026-11-28）。[世界規約](../../../WORLD_POLICY.md)、[既存美術規約](../../../DESIGN.md)、[第一話](../README.md)、[導入](../e01-04-town-preparation-v01.md)、[街道](../road-encounters.md)、[洞窟](../cave-dungeon-v01.md)、[湖](../lake-exploration-v01.md)、[鯨](../e01-06-whale-rulings-v01.md)、[終幕](../epilogue-v01.md)、[花](../ending/flower.md)、[映像現行入口](../ending/current/README.md)、[地下地理](../../../world/underground/README.md)。

## 台帳の見方
27素材枠（既存流用候補6・映像フレーム候補1・新規18・差分2）。同じ画像を別用途で使う場合もIDは安定させる。直前の会話で合意した001〜022を維持し、補完023〜027を追番。投影順はIDでなく order。P0=体験の核、P1=場面を補強、P2=時間があれば。いずれも採用前。
湖関連010〜015および026はE01-09→E01-02の確定待ち。Cの照射前後は014/026、Bの前後は012/013。016は帰還の時刻に応じた流用。001のチャット試作は未登録・未採用。既存画像自体の公開採用と、今回の投影採用は別。
状態: planned / candidate / draft-unregistered / blocked / in-review / approved / transferred / projection-verified / retired。approvalは pending/approved/rejected。原本・派生・ハッシュが未登録の間はnull。採用後に実体を確認して更新する。
