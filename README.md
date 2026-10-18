# pattern

パターンの設定値や構造の意味を具体例で説明し、利用できる実装をZIPで配布するリポジトリです。現在は管理基盤を整備した段階で、実用パターンはまだありません。

説明は`docs/<分野>/<分類>/<パターン>/index.md`、実装は`patterns/`の同じ相対パスに置きます。説明用PNGは文書側の`images/`、運用文書は`docs/project/`に置きます。

## ローカルで読む

Node.js 22以上を用意し、リポジトリのルートで実行します。

```sh
npm ci
npm start
```

表示されたURLを開きます。`npm start`はZIPを生成して開発サーバーを起動します。実装を変更したら`npm run downloads:build`でZIPを更新してください。

## 全体構成

```text
docs/                           # パターンの説明と運用文書
patterns/                       # 配布する実装・README・検証用ファイル
static/downloads/patterns/      # ビルド時に生成するZIP（Git管理対象外）
src/pages/                      # サイトの入口
src/theme/SearchBar/            # 検索UI
plugins/site-search/            # 検索データ生成と検索処理
scripts/                        # 配置・文書検証、ZIP生成、個別検証
tests/scripts/                  # スクリプトと生成物のテスト
tests/search/                   # 検索処理のテスト
tests/browser/                  # 画面・画像・ZIP取得・検索のテスト
tests/fixtures/                 # 公開しない検証用サンプル
.agents/skills/pattern-maintenance/ # パターン追加・更新用スキル
.github/workflows/ci.yml        # PRとmainへのpushで検証
docusaurus.config.ts            # サイト設定
sidebars.ts                     # 自動生成サイドバー
```

## 追加・更新する

[追加・更新手順](docs/project/contributing.md)から始め、[文書テンプレート](docs/project/templates/index.md.template)と[READMEテンプレート](docs/project/templates/README.md.template)を使ってください。[AGENTS.md](AGENTS.md)に作業時のルール、[レビュー項目](docs/project/review.md)に人間が確認する内容をまとめています。支援スキルは[pattern-maintenance](.agents/skills/pattern-maintenance/SKILL.md)です。

## 検証する

ルートで実行します。

```sh
npm run check:dir
npm run check:docs
npm test
npm run typecheck
npm run build
npm run serve
```

`build`は配置・文書確認、ZIP生成、サイトビルドを順に行い、途中失敗で停止します。個別パターンはZIPを別の場所へ展開し、READMEに記載した準備・検証コマンドで確認します。共通の検証ファイル名は要求しません。ZIP展開とコマンド実行を補助する`verify:patterns`の使い方は[検証と配布](docs/project/verification.md)を参照してください。

```sh
npx playwright install chromium
npm run test:e2e
```

ブラウザー検証はサンプルを一時サイトに追加し、`/preview/`で配信します。実用サイトにサンプルは混ぜません。検証規約は[検証と配布](docs/project/verification.md)を参照してください。`build/`と`static/downloads/patterns/`は生成物なので直接編集・コミットしません。
