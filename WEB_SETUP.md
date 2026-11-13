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

## 参加者への共有

WebサイトのURLだけを共有すれば、GitHubにログインしていないプレイヤーもスマートフォンから閲覧できます。このリポジトリは **Public** です。未公開の冒険・DM専用情報・個人情報は公開しないでください。

## 更新方法

GitHub上のMarkdown文書を編集するだけで、Webサイトの文書は同期されます。新しいMarkdownファイルをナビゲーションにも追加したい場合は `assets/site.js` の `SECTIONS` に登録してください。

Markdownからの表示は外部ライブラリに依存しない軽量ビューアーです。複雑なMarkdown表現の一部には未対応です。スマートフォン表示の故障・リンク切れを見つけた場合はGitHubのIssueで報告してください。
