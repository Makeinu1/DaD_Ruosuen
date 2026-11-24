# 方式② Google Flow（Gemini Omni / Veo）で R14 を描き直す手順

> DM資料。Flow は作者の Google AI Pro アカウントで、ブラウザから操作する（APIキーは使わない・書かない）。
> 操作する人：作者、または作者のChromeにつながった Claude / Gemini。

## 目的
Blenderのガイド映像（動き・構図・タイミングはプリヴィズ v14.9b と同一）を、原画カットと同じ「夜の絵画」の見た目に描き直せるかを確かめる。**動きと構図が変わったら失敗**（鯨の位置・向き・花弁の流れはガイドどおりであること）。

## 入れるもの
| 種類 | ファイル | 入手先 |
|---|---|---|
| ガイド映像 | `R14_guide.mp4`（1280×720・24fps・8秒） | PC `C:\VideoStudio\projects\ruosuen\renders\R14_a\`（VideoStudio の `list_outputs` のURLでも取れる） |
| 画風の参考 | `images/adopted/CUT05_KEY_whale_emerges.png`、`CUT09_KEY_climax.png` | このリポジトリ（`dm/episode-01/ending/images/adopted/`） |
| 鯨の同一性 | `v8/keyframe-test/refs/WH01_identity_sheet.png` | 同上 |

Flowで動画→動画（video-to-video / 参照つき編集）を選ぶ。長さの上限が8秒未満なら、先頭から上限いっぱいで切る（例：0〜5秒）。

## 指示文（英語のまま貼る）
```
Restyle this video, keeping exactly the same camera, composition, timing and motion.
Style: hand-painted animated film background art, gouache and watercolour on paper, soft visible brush strokes,
matching the reference paintings. A vast dark underground cavern at night. The giant pale pearl-white whale
(same design as the reference sheet) keeps its exact position, size, direction and swimming motion, with a soft
inner glow. The countless tiny white flower petals around and behind it drift like snow, glinting faint gold,
following the same flow as in the video. A faint cold moonbeam slants down from above. Deep blue-violet night
palette, quiet and solemn. No text, no people, no extra creatures, no camera shake.
```

## 保存と報告
- 出てきた動画を `R14_flow_<連番>.mp4` として PC の `renders\R14_a\flow\` に置く（GitHubには動画を入れない）。
- 比較用に、2秒・4秒・6秒のフレームを小さなjpg（横640）で `production-v15/review/` に置き、PRで出す。
- 使った設定（モデル名・長さ・何回目の生成か）を `review/flow_R14_notes.md` に1行ずつ。

## 合否の見方
1. 鯨の位置・大きさ・向き・泳ぎ方がガイドと同じか（重ねて見てずれがないか）
2. 鯨が原画の鯨と同じ生き物に見えるか
3. 花弁の雪が「流れ」として保たれ、ちらつかないか
4. 絵として美しいか（原画カットと並べて違和感がないか）
