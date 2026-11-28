# E01-08A 制作タスクと品質ゲート
> DM専用。各タスクは別スレッド・専用ブランチ/PR可。作者の承認なくマージしない。タスクID・素材IDは固定。担当者の実名は未割当、ここでは役割を定義。

|ID（E01-08A-）|タスク|依存|完了条件|現在|
|---|---|---|---|---|
|A00|制作ハブ・仕様・台帳・QA登録|最新main、各担当資料|本PR、27件の台帳と指示・規約・タスク・レビューが整合|レビュー待ち|
|A01|地上基準・宿・帰還|A00承認|001・002・016、昼夜連続性、原画候補001/002|未着手（001試作あり）|
|A04|街道基準と3段階|A00、001/002/023の暫定基準|005→006→025、同じ施工キット、原画候補005|未着手|
|A07|ラウル宅・机|A00、001/002/023/005の暫定基準、07|017→018、同じ小物、原画候補017|未着手|
|A08|美術ロック（監督）|A01の001/002、A03の023、A04の005、A07の017候補|5枚比較でstyle v1と環境キットを作者承認、他画の互換を確認|未着手|
|A02|任意訪問 地図院・塔・市場|A08、04|019/020、021/022、027、各訪問の見た目と情報開示の整合|未着手|
|A03|HOME・TERMINAL・GATE・大空洞|023候補はA00・001/002の暫定基準・地理台帳、残りはA08後|003→024→004→023、原画候補023、設備関係と人尺度を照合。未決機構は隠す|未着手|
|A05|洞窟3段階|A08、01|007→008→009、地形・視認条件を照合|未着手|
|A06|湖探索の差分・映像接続|A08、E01-09完成→E01-02確定、06|010/011/012/013/014/026/015、固定対2組、早遅・上映例外照合|依存待ち|
|A09|原本管理・投影用パッケージ|各素材の作者承認|原本検証、派生、台帳更新、リポジトリに登録|未着手（逐次可）|
|A10|全編投影リハーサル・引継ぎ|A09、E01-10/11と照合|実機で視認、キュー、分岐、誤表示防止、残課題の記録|未着手|

A01/A03/A04/A07では基準候補以外の最終画をA08より先に量産しない。A08後に残りを仕上げる（表のA08依存は各タスクの基準候補サブ成果のみで循環しない）。P2は効果が薄ければ作者と合意してretiredにできる。既存画は参照専用、全投影採用版を新作・差分で制作。

## 品質ゲート（アートディレクターが管理）
- QG0 設定監査：最新mainの世界・シナリオと参照画像を開く。未決・旧版・採用済みを分類、台帳のロックと表示条件を更新。
- QG1 基準：必要な形状/環境見本、style固定、先行5枚の比較。基準がロックされるまでは量産しない。
- QG2 構図：独立3案の明暗ラフ、意図・カメラ・主題・前後比較。作者が方向を選ぶ。差分画は承認された一つの母版のみ。
- QG3 原画：一枚ずつ制作。構図・形状・参照の役割を明示。変更1変数ずつ、変更したくない要素をロック。前の採用画と画風を照合。評価票でPass/Targeted fix/Regenerate/Blocked。作者が個別採用。
- QG4 連続性・技術：サムネイル/原寸/グレースケール、投影暗部、前後並列、B/C差分マスク。ネタバレ・誤った物理位置は一件でも差戻し。
- QG5 原本登録：Python転送Skill、再DLハッシュ一致、原本と派生を分離。作者のPR承認。
- QG6 卓上リハ：画像切替、任意訪問スキップ、早着・遅着・失敗・撤退、映画例外と帰還、オフライン・停電後再開。実機未実施を合格扱いしない。

## 使用Skillと今回の具体的な反映
- [桜井式 企画](../../../.agents/skills/sakurai/references/planning.md)・[グラフィック](../../../.agents/skills/sakurai/references/graphics.md)：プレイ時間を優先、主役・光・尺度、不要な絵は表示しない、低品質画面でも検証。Notion [桜井式](https://app.notion.com/p/4230691fc97a81bcb907d5ea44f7056a)は非公式要約であり本人の個別判断と称さない。
- [illustration-composition](../../../.agents/skills/illustration-composition/SKILL.md)：目的→独立3案→明暗と視線→個別承認。
- [gemini-consistent-image](../../../.agents/skills/gemini-consistent-image/SKILL.md)・[brief contract](../../../.agents/skills/gemini-consistent-image/references/banana-brief-contract.md)：style固定、環境キット、役割付き参照、逐次制作、変更差分レビュー。モデル固有の制限は使用時のツール仕様に従う。外部エージェント依頼票はGuide例外に従う。
- [cinematic-camera-continuity](../../../.agents/skills/cinematic-camera-continuity/SKILL.md)：前後のカメラ・空間・進行方向、同構図比較。静止画に不要な動画仕様は適用しない。
- [原本転送](../../../tools/github-original-transfer/SKILL.md)：実体取得、SHA-256とGit Blob検証、Draft PR。画像未取得時に転送済みとしない。

## スレッド起動テンプレート
「E01-08A-Axxを担当。Notion Agent Operating Guideと最新mainの dm/episode-01/stills/README.md、style.md、asset-register.json、担当のシーン指示、関連する世界・シナリオ正本、上記Skillを読む。既存素材を実際に見て、QG0/QG1を確認し、まず構図とロックを言語化。承認後に一枚ずつ制作・比較・修正し、採用前に登録しない。成果は台帳に更新し専用PR、作者指示なくマージしない。未決は担当へ連絡。プレイヤーPagesには掲載しない。」

## 2026-11-28 Skill棚卸し・適用ルーティング
Notion登録済みSkillとGitHub内の既存Skillを照合。新規インストール不要。手順の重複を増やさず以下を工程に組み込む。Notion Skillは登録済み本文を参照し、付属スクリプトや未取得の参考ファイルは必要時に検査して取得。外部コードの自動実行はしない。

|工程|主Skill|補助Skill|成果|
|---|---|---|---|
|QG0・QG1|[style-cinematography-director](https://app.notion.com/p/41c0691fc97a8191b7c0e8c128660aff)|sakurai、[character-location-prop-bible](https://app.notion.com/p/41c0691fc97a81cf933eeb2eb7118173)|style、場所・部品の安定IDと設定画、時刻・状態の可変条件を分離|
|QG2|illustration-composition|[shotlist-and-visual-breakdown](https://app.notion.com/p/41c0691fc97a81e1ad39d95f5e85a7c9)、cinematic-camera-continuity|3案の構図比較、主題、前後と空間の整合|
|QG3|[cinematic-image-prompting](https://app.notion.com/p/41c0691fc97a811cb42bd31d41030646)|gemini-consistent-image（Gemini使用時・他モデルは適応）、character-location-prop-bible|役割付き参照・固定style・一枚ずつ制作|
|QG4|[prompt-iteration-and-diagnostics](https://app.notion.com/p/41c0691fc97a81958dc0ffde34c66458)|sakurai、cinematic-camera-continuity|意図/結果/原因/変更一つ/維持する条件/次の検査の修正記録|
|QG5・6|原本転送Skill|sakurai|原本検証、投影実機での階調・視認性・切替検証|

補足：director-skillsは全体のルーター、Blender/previs系はHOME/GATE/湖など空間の連続性が必要な場合だけ利用。ai-image-prompts-skillは探索用の補助であり今回の固定美術ラインの代わりにしない。実機投影は汎用の新Skillよりこのプロジェクト固有のチェックリストで管理する。基準候補5枚の順は001→002→023→005→017。各キットについて安定ID、固定形状・材質・人尺度、可変の時刻・小物位置・物語状態、参照元と採否、変更履歴を記録する。
