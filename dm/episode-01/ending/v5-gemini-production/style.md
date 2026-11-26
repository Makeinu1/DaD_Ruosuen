# `style.md` — 第一話エンディング『空に降る雪』Gemini 画像生成 共通スタイル・ロック定義

> **運用ルール（`gemini-consistent-image` スキル準拠）**：
> 下記の **【VERBATIM STYLE LOCK】** ブロックは、**一言一句変えずに（verbatim）** すべての Gemini 画像プロンプト（Sheet A / Sheet B / KF-G1〜KF-G9）の末尾に貼り付けてください。表現を毎回言い換えると、画調と色温度がカットごとに少しずつドリフトします。

---

## 【VERBATIM STYLE LOCK】（そのままコピーして全プロンプトに添付）

```text
Hand-painted 2D Japanese theatrical animation background painting in matte opaque gouache and delicate ink linework on cold-pressed paper grain, directly matching the painterly brushwork and restraint of the supplied reference painting. Deep nocturnal subterranean palette anchored strictly to midnight indigo shadows (#0A1326), dark sapphire mirror water (#183054), cool blue-silver atmospheric mist (#4A6A92), silver-blue moonlight shafts (#B2D2EE), pearl white highlights (#F2F5F8), tiny warm champagne-gold lantern and seed accents (#F4DA94), and muted grey-brown closed buds (#766C60). Visible traditional brushwork with quiet matte finishes and natural falloff into darkness; zero glossy 3D CGI sheen, zero plastic specular glare, zero neon pink or magenta tint, zero text, zero UI overlays, zero watermarks.
```

---

## 禁止ワード（`de-slop` 監査済み・絶対に混ぜない）

- **AI臭ブースター禁止**：`4K`, `8K`, `ultra-detailed`, `hyper-detailed`, `masterpiece`, `best quality`, `stunning`, `cinematic`, `epic`, `perfect`, `flawless`, `sharp focus`
- **数値レンズ表記禁止（Nano Banana は無視するため自然語を使う）**：`21mm`, `35mm`, `50mm`, `85mm`, `f/2.8`, `ISO 400` は書かず、`wide cathedral expanse`, `low shore perspective`, `compressed telephoto perspective`, `shallow depth of field` 等で記述する。
