# 旧原画アーカイブ v0.2｜原本転送進捗

**DM専用・プレイヤー閲覧禁止。** 2026-11-20、移植工程10。旧29枚の分類は[原画台帳](../art-manifest.md)に従う。[QG4最新原画台帳](../production/keyframes/README.md)の撮影用正本・判定を上書きしない。

転送元：Library /Ruosuen_transfer_20261119_82ed042/ の00–31.txt（Base64行分割）と [transfer-manifest.json](transfer-manifest.json)。32項目（旧原画PNG29枚＋付属3点）。各項目について取得行数・Base64文字数・復号バイト数・SHA-256・Git blob SHAを元台帳と照合し、一致したものだけコミットする。未登録の予定パスを実在ファイルとして扱わない。

## 登録済み（14/29枚）

| 番号 | ファイル | 元バイト数 | SHA-256（元台帳） | Git blob SHA（照合済み） |
|---|---|---:|---|---|
| 00 | [CUT02_KEY_moon.png](adopted/CUT02_KEY_moon.png) | 1904930 | `e6f1b185df2cd5e99c11418fcc056567d68ed4d334a91365a7d4ad20021e4d2d` | `5d6341076682c1cfd520edea5c23d4b3d3721c1f` |
| 01 | [CUT03_KEY_flower.png](adopted/CUT03_KEY_flower.png) | 1966302 | `4cc883ebf68319340826dd3322a185c55760b858d80326f278a235b744e9544c` | `64efee55a2c9297d331160038f8c63f8f85cf881` |
| 02 | [CUT04_KEY_water_shadow.png](adopted/CUT04_KEY_water_shadow.png) | 1949267 | `f71fd33090b4cff264ed1462d9aa3818b85bf719c045ab4acbc8445e96fcccfa` | `ed3cec37cdc6f0b1b6bbb5de5d5efd8a0d558c8e` |
| 03 | [CUT05_KEY_whale_emerges.png](adopted/CUT05_KEY_whale_emerges.png) | 2254754 | `6ccfd601d0595265979fb046c0cd7df3428d3756a86786117538b0547e172d25` | `6ce33ddda0f0ccbdabc41e067231f5bdf0502d71` |
| 04 | [CUT06_KEY_eye.png](adopted/CUT06_KEY_eye.png) | 2201083 | `1c97b731401f855124586d87d6e2391b3ebdafece383f26b75e1e53dd6e68699` | `c32a07c93d5ec45a95781e532ffd781c433c2f1b` |
| 05 | [CUT07_END.png](adopted/CUT07_END.png) | 2442038 | `b9b764c7a567cbd7f6adb5098be1116d64d7b6f8412b5a48670ec98d1fd56592` | `ff860d712a3aee53b0a358bdb49dacd7da69cb44` |
| 06 | [CUT07_START.png](adopted/CUT07_START.png) | 2164639 | `8848a195b1c6e60d40187edde06e9ecc73826e2f3a8a618b92f913e5c6e74676` | `2344f99cbec66feda39f53af19d9e08957be042d` |
| 07 | [CUT08_KEY_petal_release.png](adopted/CUT08_KEY_petal_release.png) | 2248781 | `f82a4c30bd7f698fbc84c0615b1337c65be5fde77272bafb71147d44c884aa64` | `c9c4c325b24195b583b39776d8aebcad4833d1ca` |
| 08 | [CUT09_KEY_climax.png](adopted/CUT09_KEY_climax.png) | 2912838 | `83cfc7e9eb4cc54651170a5b15d53e06b6069db9f02567f7c265606f47c0ca3e` | `6b6d505afb2cfa860756305bec8b59e4d63d844c` |
| 09 | [CUT10_END_moonlight_dimmed.png](adopted/CUT10_END_moonlight_dimmed.png) | 1584172 | `315614ce22160b02885e5a3229c1aa8f094df288e2b3053fc5909f44a3c23ab5` | `dd011dd8eb7e2cde1825341305f3874d3434791a` |
| 10 | [CUT01_END_matching_source_candidate.png](alternate/CUT01_END_matching_source_candidate.png) | 1752326 | `d445965cc903d9613316ffc7e99687ef12bec5cc9115fa1d5b0f07426e0e57d9` | `e808b6b466bd8a096a6e06a2d41e93b9703b5928` |
| 11 | [CUT01_ENV_opening_candidate.png](alternate/CUT01_ENV_opening_candidate.png) | 1957791 | `efd57337c6d20418315522c2e2d30477225d575d7aa7c16355d44a95045a0e67` | `e3674cb4ba22bea65516922ca32a855fce314e97` |
| 12 | [CUT10_START_departure.png](alternate/CUT10_START_departure.png) | 2389683 | `7485a1cd47533d2f4aaa05c45b348d6c361990b0b493e723927ab616d51d1f2d` | `adaa1f69fdd1aac293f98385ff08466cbdec727e` |
| 13 | [FL01_v03_young_flower_only.png](reference/FL01_v03_young_flower_only.png) | 2422169 | `ede4e40ca76a775fb8b0b90b050842e2591ed2d9dd7fec09db5738769650ae48` | `6a0bdcaf2823e245f9ad293d9b15e1b670547598` |

00.txtの全212行・2,539,908 Base64文字を取得、復号した原本のSHA-256とGitHubのBlob SHAが一致。再圧縮・再生成なし。旧原画として保存し、現行Bの採用版との同一性を断定しない。

01.txtの全219行・2,621,736 Base64文字を取得、復号した原本のSHA-256とGitHubのBlob SHAが一致。再圧縮・再生成なし。

PR #15マージ後のmainにある00〜12の13点を2026-11-20に再照合し、全Git blob SHAが元台帳と一致。進捗表の旧2枚表記を実体に合わせて修正した。

13.txtは全270行、3,229,560 Base64文字、復号2,422,169バイト、PNG 1448×1086。SHA-256とGitHub blob SHAが元台帳に一致。再生成・再圧縮なし。FL-01 v0.3の若い花の美術参照に限定し、現行v0.8の器官・散布設定には優先しない。

## 残件

14–28のPNG15枚、29–31の付属3点は未転送。元ZIP本体、後続のQG1–QG4の原本はこの転送パッケージの対象外。公開Pagesへ追加しない。公開リポジトリの注意書きはアクセス制御ではない。
