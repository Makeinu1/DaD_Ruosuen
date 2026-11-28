# 投影美術デザインライン v0.1
> 作者承認待ち。世界設定を新たに決定しない。既存DESIGN.mdの古典的幻想画と11/17街歩きシリーズを卓用に適用する。色値は作画用目安で世界設定や測光値ではない。

## 1. 美術の核
「人々が暮らす、未知に満ちた世界」。人間の生活と尺度のある巨大自然、地下への期待、静寂、帰還の幸福。主題は一枚一つ。静止画のために行動を止めない。
### 固定スタイルブロック（全プロンプトの冒頭に同文で挿入、v0.1）
> Classical hand-painted fantasy environment illustration, opaque gouache and restrained ink-like brushwork, believable stone, timber, fabric and organic forms, selective detail, atmospheric depth with clear foreground, middle ground and distant masses. Human-scale eye-level staging unless the approved shot requires otherwise. Muted earth and slate tones, warm amber practical lights against cool natural shadows; source-motivated illumination, readable midtones, no crushed blacks. Full-bleed landscape 16:9, no captions, UI, logos, decorative border, excessive bloom, generic floating particles, glossy CGI or photoreal finish. Preserve the approved reference identities and scene-specific locks; do not invent new canon.

日本語補足：画面全体を均一に精密にせず、面の筆致と主題の選択的描写。人・建築・動植物の構造と接地は自然に。既存の淡彩・夜景の特性を尊重し、既存画を無理に再生成しない。スタイルブロック変更は版を上げ、全採用素材への影響を確認。

## 2. 基準原画・参照階層
- 画風候補：assets/ruosuen-walk-mole-inn-20261117.webp（温暖室内、筆致）、assets/ruosuen-walk-labyrinth-panorama-20261117.webp（地下の尺度、空気遠近）、assets/reuna-turn-10.webp（地上、都市構造）、assets/ruosuen-street-night-oil.webp（同一都市の昼夜対）、assets/ruosuen-first-adventure-b.webp（年末の生活とガッシュ/インク）。
- A01/A04/A07で001・005・017を順次基準原画候補にし、三枚を並べて作者が画風をロックする（生成前の暫定規約と最終承認を分ける）。既存の基準を優先して1枚ずつ進める。
- 参照画像は「画風」「形状・空間」「構図」「編集母版」の役割を明示する。画像名だけでなくリポジトリ相対パス、コミット、必要ならハッシュを記録。古い原画の採用歴は現行カメラ・地形の承認と同一ではない。
- 環境キット（A01〜A07で必要なものだけ先行承認）：街の石壁・屋根・橋・灯具、地図院の机と器具、塔のアーチ・標本棚、HOME/GATE/TERMINALの共通工法、街道の路面・光苔・補助灯、洞窟の岩質、湖の岩/葉/FL-01、ラウルの製本道具と机。反復する建築は簡単な形状図・材質見本・人尺度をセットにする。未知の機構は描かず隠す。地図・映像が必要な場合はその担当の形状を参照し、こちらで公式化しない。

## 3. カラースクリプト（sRGB HEXの目安）
|場面|暗部・中間・暖色/主光|狙い|
|---|---|---|
|地上|#6F777D #C6CFD1 #D8C6A5 #B78E59|親近感、時刻に依存しない日常|
|室内|#544033 #8C6846 #B68A52 #E7B777|暖灯、食卓・仕事|
|地下文明|#293C50 #506878 #7995A4 #DBB77B|冷気と人工灯、巨大さ|
|街道|#303C40 #4E605D #77877B #8A9774|自然と灯守の植栽|
|洞窟|#303238 #4A4944 #857662 #BD9B63|閉塞、光源に応じた暖冷|
|湖|#242E42 #46556C #697E92 #DFE3DD|静寂、淡い月光と白五弁|
|映画（参照のみ）|白・淡桜・淡金＋暗い岩壁|強い光と花雪を静止画で先取りしない|
|ラウル宅|#635343 #927353 #BE9B6E #F1E8D8|紙・木の温もり|
光は物体の色だけでなく光源色・反射・遮蔽で描写。地下を一律に青くしない。色だけで重要な手掛かりを伝えない。

## 4. 構図・空間のロック
各新規母版につき独立した3案の明暗サムネイル（3〜5階調）→主題・視点・最も明るい領域・進行方向・前中遠景・余白を比較→一案承認。新規画は独立案、修正は選択済み母版を参照。前後シーンを並べ、同じ方向・ランドマーク・人尺度を検査。必要な施設・湖だけ簡易3D/平面ブロックアウトを参照し、独自座標を確定しない。視点は実際にPCが立てる場所、接写は調査が成立したとき。地上昼夜、B、C、工房の対は背景配置を保持。湖の対は固定カメラと変化マスクを記録、同じ岩/葉/根元/画角/水位を維持。差分の外はピクセル比較を行い、物理的に必要な光・影以外の変化は不合格。

## 5. 画像の禁止事項・技術仕様
文字・透かし・ロゴ・UI・枠・誤認しやすい文字地図なし。既存の紋章は既存参照の範囲のみ。未承認の祭礼・降雪・鉄道網・機構・地形・NPC/PC外見・敵の位置・未発見の手掛かり・鯨/花雪の先出しは禁止。描いたものを新設定として扱わない。
原則16:9、原本は生成時の解像度・形式・バイトを保持。投影版は1920×1080 sRGB PNGを目標（機材に応じた派生は別ファイル、アップスケールを原本と呼ばない）。既存3:2の無理な切抜き禁止、必要なら構図を確認し余白処理または新作。プロジェクターの実機で暗部、色、階調、文字なしの状態、客席から主題が判別できるか検査。画面に余分な光源・粒子を入れず映画との差を作る。
