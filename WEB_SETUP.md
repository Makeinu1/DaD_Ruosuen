# ルオスエン Web版 — GitHub Pages の公開設定

このリポジトリには、スマートフォン・タブレット・PCに対応した静的Webサイトが含まれています。

- サイト用HTML: `index.html`
- デザイン: `assets/site.css`
- 資料閲覧機能: `assets/site.js`
- 元の資料: `docs/**/*.md`、`players/**/*.md`、その他のMarkdown
- Jekyllビルドを無効化: `.nojekyll`

## 公開までに必要な最初の設定（管理者）

1. [リポジトリのPages設定](https://github.com/Makeinu1/DaD_Ruosuen/settings/pages) を開きます。
2. **Build and deployment → Source** を **Deploy from a branch** にします。
3. **Branch:** `main`、**Folder:** `/(root)` を選んで **Save** します。
4. GitHubのデプロイが成功すると、次のURLでサイトを見られます。

   **https://makeinu1.github.io/DaD_Ruosuen/**

※ サイトURLはGitHub Pagesの規則から導かれる予定URLです。公開されるまでは404の場合があります。設定後にPages画面の `Visit site` で確認してください。

## 設定の正本と公開する内容

- 自由な草案は [`notes/`](notes/README.md) に書きます（未採用のメモ帳）。
- 世界設定の正本は [`world/`](world/README.md) です。
- プレイヤーに読ませたい情報は `docs/` や `players/` に整理し、Web側の `assets/site.js` にある `SECTIONS` で**掲載文書を選別**します。
- PagesはMarkdown原稿を**同じリポジトリから直接読み込んで表示**します。Pages用に本文をもう一度コピーしないこと。GitHubの更新直後はデプロイの時間差があるため、Pages公開の成功を確認してください。
- このリポジトリは**Public**です。Pagesの案内から外れた `world/` のファイルもGitHub上や公開された静的ファイルのURL経由で閲覧され得ます。**Pagesの選別は情報秘匿ではありません**。
- DM専用の創作上の未公開情報は `dm/` に集約し、SECTIONS・llms.txt・公開記事・公開用素材から参照しません。Public GitHubおよびルート配信の直接URLからは閲覧可能です。実際に秘匿が必要な情報は別のアクセス制限された保存先で保管します。

詳細なルールは [WORLD_POLICY.md](WORLD_POLICY.md) を参照してください。

## 参加者への共有

WebサイトのURLだけを共有すれば、GitHubにログインしていないプレイヤーもスマートフォンから閲覧できます。このリポジトリは **Public** です。未公開の冒険・DM専用資料は `dm/` のみに整理し、プレイヤー向け導線へ掲載しないでください。個人情報や認証情報はコミットしないでください。

## 更新方法

GitHub上のMarkdown文書を編集するだけで、Webサイトの文書は同期されます。新しいMarkdownファイルをナビゲーションにも追加したい場合は、プレイヤー向けの公開内容を確認したうえで `assets/site.js` の `SECTIONS` に登録してください。本文のコピーを作らず元Markdownのパスを使ってください。**`world/` のすべてをPagesへ自動掲載しないでください。**

Markdownからの表示は外部ライブラリに依存しない軽量ビューアーです。複雑なMarkdown表現の一部には未対応です。スマートフォン表示の故障・リンク切れを見つけた場合はGitHubのIssueで報告してください。
