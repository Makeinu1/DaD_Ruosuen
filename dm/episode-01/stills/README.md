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

## 素材台帳（初期スナップショット）
正本JSONに変更を加えたらこの表とscene-briefs.mdを同期。順番は実際のプレイによって省略・再表示可。

|ID|順|場面|優先|制作種別|状態|採用|
|---|---:|---|---|---|---|---|
|E01-ST-001|10|年の瀬のルオスエン|P0|new|draft-unregistered|pending|
|E01-ST-002|20|モグラの寝床 内観|P0|reuse|candidate|pending|
|E01-ST-019|30|王立地図院 内部全景|P1|new|planned|pending|
|E01-ST-020|31|地図院 閲覧・作業空間|P1|reuse|candidate|pending|
|E01-ST-021|40|伽藍の塔 導入景|P1|reuse|candidate|pending|
|E01-ST-022|41|伽藍の塔 研究・閲覧室|P1|new|planned|pending|
|E01-ST-027|50|年末市場|P2|reuse|candidate|pending|
|E01-ST-003|60|HOME 地下への降下|P0|new|planned|pending|
|E01-ST-024|70|ターミナル 活動圏|P1|new|planned|pending|
|E01-ST-004|80|GATE 探索の出入口|P0|new|planned|pending|
|E01-ST-023|90|ファーストライト大空洞|P0|reuse|candidate|pending|
|E01-ST-005|100|アルデン大街道 R3|P0|new|planned|pending|
|E01-ST-006|110|R65 前半 人通りの減少|P0|new|planned|pending|
|E01-ST-025|120|R65 後半 文明の外縁|P0|new|planned|pending|
|E01-ST-007|130|未整備横道の先の洞窟入口|P0|new|planned|pending|
|E01-ST-008|140|洞窟内の狭い接近通路|P0|new|planned|pending|
|E01-ST-009|150|はぐれ狼の棲む広間|P1|new|planned|pending|
|E01-ST-010|160|地底湖 到着時全景|P0|new|blocked|pending|
|E01-ST-011|170|A 最初の一輪|P0|new|blocked|pending|
|E01-ST-012|180|B 閉じた蕾|P0|new|blocked|pending|
|E01-ST-013|190|B 同構図の開花後|P0|delta|blocked|pending|
|E01-ST-014|200|C 月光が届く直前|P0|new|blocked|pending|
|E01-ST-026|210|C 月光で開いた若齢花|P0|delta|blocked|pending|
|E01-ST-015|220|鯨が去った後の湖|P0|frame|blocked|pending|
|E01-ST-016|230|地上への帰還|P1|reuse|candidate|pending|
|E01-ST-017|240|ラウルの製本工房兼自宅|P0|new|planned|pending|
|E01-ST-018|250|花便りの作業机|P2|new|planned|pending|
