# 王立地図院 — 地下地理台帳 v0.3

> 2026-11-25 作者依頼による初期実装。PR承認後に運用開始する。既存の [世界設定・公開運用規約](../../WORLD_POLICY.md) を優先。プレイヤーはリポジトリを閲覧せず公式Pagesのみ利用すること（Publicリポジトリでありアクセス制御ではない）。

## 原則

地図院の地理管理体系をそのままGitHubで運用する。既存の正式名称・番号を参照キーとして共用し、別の制作管理番号を作らない。未確定の地理は空白にする。地図院が知らないことと、作者がまだ設定していないことを区別する。地図は台帳から派生する。シナリオの都合による過去の事実の無断改変は禁止する。

- [地理台帳](atlas.json)：ネタバレを含まない採用・暫定採用地理の構造化正本（Pages未掲載）。
- [DM補完台帳](../../dm/underground/atlas.json)：DM専用の創作上の地理、報告。実際の秘密や個人情報は保存禁止。
- [設計・模擬検証の履歴](../../notes/地下世界地理台帳_管理規約案.md)：v0.1からの来歴。現行運用は本書を優先。
- [検証コード](../../scripts/verify-underground.mjs)／[回帰テスト](../../tests/underground.test.mjs)。

## 台帳の初期値

地上・HOME・TERMINAL・PORTの模式接続を維持し、AREA 1の初回正式採番を追加した。設計・採番・作図の正本は[AREA設計ガイド](area-design-guide.md)。登録版はPR承認後に運用開始。地理の細部は概算・未決を維持。

AREAは発見・確認順、番号と隣接関係は独立。地下地図は方位を表示しない。GATEはAREA 1のR3/R7共通端点。PORTもAREA 1内の別高度（詳細未決）。TERMINALは活動圏であり既存代表NODEは模式接続にのみ使用。地下と地上の方向・距離は対応しない。局所座標とAREA間接続を分離する。

## データ仕様（JSON v0.3）

ルートオブジェクトには version（"0.3"）と areas / nodes / segments / routes / facilities / reports の配列が必要。IDは配列内の id。地図院とGitHubで同じ登録識別子を使う。種別付きキー（NODE:TERMINAL、FACILITY:HOME、例 NODE:34）は記法の実装案で、作中の番号割当規則や道標の表記を確定しない。

共通フィールド：
- id：種別付きの正式名または番号（registration=named/numbered）。未採番のみ tmp:スコープ:対象（registration=pending）。例 tmp:session-01:opening-a。正式登録時は暫定レコードを失効させ後継へ対応付ける。
- name：道名・正式名・顕彰名。無名はnull。番号と道路名は共存できる。実在する異称だけを任意追加する。道名は複数区間にまたがり得る。
- approval：accepted / provisional。未採用案はnotesまたはDM草案。source：承認・観測の出典（ファイルと見出し等）。lifecycle：active / retired。history：変更履歴配列。
- historyの各項目：kind（world_change / correction / registration / survey / reorganization / knowledge）、at（作中時点、未定ならセッション・場面）、reason、source。既存レコードを変更する場合は追記必須。Gitの時刻とは別。
- retiredの場合 retirement={at,reason,successors}。旧番号を削除・再利用しない。SEGMENTの後継は方向付きの順序配列、その他はID配列。旧報告・旧地図は原文を残す。

| 種別 | 固有フィールド |
|---|---|
| AREA | datum、geometry、outline_xy_m、terrain、ceiling_height_m（未設定null）。局所座標・地形レイヤー。 |
| NODE | kind、position（null または datum / x / y / z、単位m）。分岐・乗降場・入口等、測量や案内に有用な地点のみ。巨大空洞は必要に応じ入口・湖岸などを追加 |
| SEGMENT | from / to（未知終端のみnull）、geometry（schematic/surveyed/approximate/unknown）、length_m、elevation_change_m（符号付き・from→to、未知はnull）、methods配列 |
| ROUTE | steps=[{segment,direction}]（forward/reverse）。現行路線は現行区間の連続列。閉鎖しても指定自体は消さない |
| FACILITY | kind、nodes / segmentsの参照配列、state（operational/failed/closed/unknown/building）。昇降機や橋等。設備参照と区間の相互対応を確認 |
| REPORT | subjects（対象ID配列）、observer、observed_at、reported_at（未報告null）、knowledge_holders、certainty（observed/surveyed/reported/inferred）、claim、source。原報告は不変。追加報告・訂正報告で更新する |

v0.3追加：area は AREA 参照。NODE.position は同一AREAのdatum。SEGMENT.plan_xy_m は局所平面形状、horizontal_length_m は投影長（length_mとは別）。maintenance は maintained / unmaintained / local / unknown、通行可否はmethods.state。terminal_kind は observed_opening または known_area_connection、後者は destination_area を指定し相手NODE未設定ならto:null。AREA間に絶対高低差を仮定しない。publication=regional_map は地域図への出力候補であり、発行時点・地図院の知識の確認は別。terrain の key はAREA内の地形レイヤーキーで正式識別番号ではない。v0.2履歴との互換検査を残す。

SEGMENT.methodsの項目：mode（walk/rope/lift/ship 等、必要なものだけ）、direction（forward/reverse/both）、state（passable/restricted/blocked/unknown）、facility（必要ならID）、condition（任意）。設備故障は該当移動手段だけに影響し得る。飛行や魔法は条件別に扱い、一律の不可能を設定しない。模式区間は経路計算の対象外。昇降機はFACILITYでありNODEやSEGMENTとは別。

標高の厳密値に限って elevation_precision="exact" と elevation_datum を指定。検査は同一基準の閉ループに対して実施。概算・誤差範囲・基準間の変換は未実装のためDMが確認する。直線距離・経路長・天井高・地表からの深度は混同しない。

## 地図院の知識とDMの知識

地理の事実と観測記録は別管理。登録番号があることは記録の正しさを保証しない。PCの発見、地図院への報告、地図院による測量・登録、作者採用は別イベント。相反する証言は別REPORTとして併存させる。未報告から報告済みに移る際は元REPORTを書き換えず、受領REPORTを追加し元記録にsource等で結びつける。

worldからdmへの直接参照を禁止する。秘匿された行き先はworld側でto:nullとし、DM側の別SEGMENTでrefinesにworld側IDを指定して終端を記録できる。DM専用情報を公開用出力に自動混入させない。公開可能になった事実は同一IDを維持して移す。worldは一般市民やPCが知っている情報の意味ではなく、制作上の置き場所である。配布地図は対象の知識・時点・Git版を固定し、作者が内容を確認する（自動生成は未実装）。

## 冒険者向け地図の表示方針（2026-11-25 作者承認）

ゲート周辺は案内図としての視認性・機能美を優先し、開拓区域の外縁では地形や高低差など探索に必要な情報を充実させる。測量用の正本と携行用地図を分け、同一台帳から目的に応じて表示を変える。地図の簡略化は未測量を意味しない。逆に未整備と未測量も別の状態である。第一話の配布地図は目的地専用ではなく、今後の冒険にも再利用できる地図院の標準的な案内図を目指す。オフライン卓で使用できる印刷物をChatGPTで制作する。

以下は次段階の設計候補であり、個別仕様の承認ではない。
- ゲート周辺：路線番号、主要分岐、主要施設、整備区間を優先する模式的な路線図。岩壁などは省略可能。縮尺の有無を明示し、交差と接続を区別する。
- 開拓外縁：地域測量図・必要な断面図で、実際に判明している空洞・道・高低差を表す。未確認の先は描かない。
- 第一話は広域案内図と対象地域の拡大図を候補とする。地図内の文字は英語を基本とする。具体的な路線数・番号・施設・地理・配色・印刷サイズ・凡例・地図の発行範囲は未決。過去の例示番号は正式採番しない。

## セッション運用（必須）

準備前に本台帳・DM補完・関連セッション・採用済み自然法則を読む。既知の接続を再利用し、未確定値を補完しない。新規シナリオ草案は正本と分離。
プレイ中は自然文で十分。最低限、セッションID/日付、作中時点、出発点・通った道・分岐、上下/目印/所要時間、観測と伝聞、何を誰に伝えたか、地理の変化を残す。過去の原記録を上書きしない。実在の参加者の秘匿情報は登録しない。
終了後、エージェントが既存台帳と照合し、新規登録・変更・未解決事項のPRを作る。採用済みの地理だけ正本へ。DMが確認後マージ。原記録には基準版と更新版（マージコミット）を紐づける。未訪問の草案は観測済みにしない。
分岐追加は既存SEGMENTをretiredにし、後継区間を順番付きで登録。正方向・逆方向・共有路線と設備参照を一括更新する。古い戦闘位置等の帰属が分からなければ未決。
地図院が知らない実在地点には暫定キーを用い、正式採番まで保持する。採番は最新mainを確認してから決める。競合時は告知済み番号を黙って変えない。

## 検証

リポジトリルートで Node.js 20+（CIは22）：
```sh
node scripts/verify-underground.mjs
node tests/underground.test.mjs
```
PR時は対象ブランチ最新のSHA、PR head、共通祖先を指定し、マージ結果上で実行する：
```sh
node scripts/verify-underground.mjs --target TARGET_SHA --head HEAD_SHA --merge-base MERGE_BASE_SHA
```
参照・ID重複・路線の連続性/方向・失効番号・履歴追記・報告の変更・world→dm参照・同一基準の厳密高低差閉ループ・並行変更競合等を検査。未知は許容。正式採番の細則、地名重複の意味的判定、誤差区間、時間依存の自動経路検索、過去版の自動再構築、会員ランク別の地図生成は未実装。ソースの内容が実際の承認を証明するか、自然描写、漏洩防止の全ては自動化できない。PRレビュー必須。GitHubの公開範囲は変更しない。
