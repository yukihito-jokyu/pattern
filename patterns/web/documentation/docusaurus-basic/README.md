# Docusaurusの日本語ドキュメントサイト

ホーム、記事、自動サイドバー、日本語の静的検索、設定台帳とsetupスキルを含む雛形です。サイト名や公開先はサンプルです。利用者の回答で設定してください。

## 環境と導入

Node.js 22以上とnpm、ブラウザーテストにはChromiumを使用します。CIの基準はUbuntu・Node.js 22です。Docusaurusは3.10.2、TypeScriptは6.0.3、Playwrightは1.64.1に固定しています。依存関係全体はpackage-lock.jsonで固定します。

ZIPを新しい空ディレクトリへ展開し、以降は展開された `docusaurus-basic/` を作業場所にします。既存サイトへファイルを一括上書きする手順ではありません。このZIPだけで依存関係を導入できます。

```sh
node --version
npm ci
npm run setup -- check
```

準備が失敗した場合は停止し、原因を解消してから再開します。checkのokがtrueなら、配布設定・OSSの版・設定台帳・管理ファイルが整合しています。

## 自分のサイトを設定する

Codexなど `.agents/skills/` を認識するスキル対応環境では、この展開先をプロジェクトとして開き、`$setup` を指定します。スキル本体は `.agents/skills/setup/SKILL.md` です。最初に質問範囲を「重要のみ（推奨）」「重要＋普通」「すべて」から選びます。範囲外は現在値・未設定時の既定動作を維持し、個別に確認した回答と区別して記録します。独自の権限や外部サービスは必要ありません。

スキルを使わない場合も、次のCLIと回答ファイルで同じ設定を生成できます。

```sh
npm run setup -- init --level important --out setup-answers.json
npm run setup -- list --answers setup-answers.json --group site
```

listは区分別の設定パス、現在値、未設定、既定値、型、条件、出典と質問を出力します。`--group` を省略すると選択した質問範囲の全区分です。`--level important`は重要のみ、`--level normal`は重要＋普通、`--level advanced`はすべてです。initの既定はimportantで、listは回答ファイルのquestionLevelに従います。回答ファイルを指定しないlistの既定もimportantです。全台帳を見る場合は`npm run setup -- list --level advanced`を使います。分岐・配列・辞書を含む設定台帳の詳細は `setup/settings.catalog.json`、対象版と出典は `setup/sources.md` と `setup/coverage.json` にあります。

回答ファイルのsettingsに最終設定を記入し、reviewsへ各項目の確認結果を記録します。initは選択範囲内をunanswered、範囲外をretainedで作ります。confirmedはその最終値を確認した状態、not-applicableは理由付き非該当、retainedは質問範囲の選択に従って元の値や未設定を維持する状態です。範囲外を変更する場合は、その項目を個別確認してconfirmedへ更新します。valuesにはlistingが抽出する値の配列を保存します。未設定の値は[]です。確認後の値の変更と未回答はvalidateで検出します。形式と質問の扱いは `.agents/skills/setup/references/questions.md` を参照してください。

```sh
npm run setup -- validate --answers setup-answers.json
npm run setup -- plan --answers setup-answers.json
npm run setup -- apply --answers setup-answers.json
npm run setup -- check
```

planにはファイルごとの変更前と変更後、質問範囲、維持した台帳項目数が出ます。内容を確認してからapplyしてください。applyのchangedに変更したファイルが表示されます。再実行する場合はinitで現在値から回答を作り直し、同じ最終値なら変更は増えません。回答ファイルは上書きせず、新しい名前で作ってください。

主要な変更箇所はsite.title、site.tagline、site.url、site.baseUrl、theme.navbar、custom.home、custom.searchです。例えば `https://example.com/manual/` に置く場合、urlは `https://example.com`、baseUrlは `/manual/` です。`SITE_BASE_URL` 環境変数があるとbaseUrlを一時上書きし、checkは保存値と実効値を表示します。

キーを省略するとOSSの既定動作を使います。false、null、空文字、空配列は省略と異なり、対象のスキーマが許可する場合だけ使用できます。独自検索の省略可能な値はパターンの既定値が適用されます。関数などは `{"$module":"./local-options.cjs","export":"handler"}` で、利用者が選んだサイト内の信頼できるモジュールを参照します。このモジュールは検証・起動時にNode.jsで読み込まれます。

site.settings.json、tsconfig.json、docusaurus.config.ts、sidebars.ts、playwright.config.tsとsetupが変更した記事・カテゴリは管理対象です。管理対象の手編集は競合として止め、無言で上書きしません。変更したい値は回答へ記入してください。記事本文、画像、ホームや検索の実装は通常の編集対象です。setupは記事の本文を保持してfront matterを変更します。既存の手編集は差分を保存・比較して取り込むか、管理対象を変更前に戻してから進めてください。`.setup-state.json` を消して競合を隠す手順は使用しません。

ブログや多言語などを新たに有効にした場合は、必要なコンテンツ・設定モジュールを用意してから検証します。全機能の組み合わせを動作保証するものではありません。未導入pluginの設定、依存ライブラリ内部の全APIは設定台帳の範囲外です。

## 使用方法

```sh
npm start
```

表示されたURLを開きます。ホームから「ドキュメントを読む」で入門記事へ移動できます。「文書を検索」を開いて「設定」などを入力するとタイトルと本文を検索できます。複数語は空白で区切るAND検索です。検索は部分一致であり、形態素解析や誤字補正は行いません。外部サービスへ検索語を送信しません。

記事はdocs/へ追加します。表示順はsidebar_position、カテゴリ表示名は_category_.jsonです。記事追加後は本番ビルドでサイドバーと検索データが更新されます。検索対象のinclude/excludeはdocs/guide/writing.mdなどサイトルートからのパスに対するglobです。draft・unlistedは検索から除外しますが、unlistedはアクセス制御ではありません。

## 検証

作業場所は引き続き `docusaurus-basic/` です。

```sh
npm run setup -- check
npm run typecheck
npm run build
npx playwright install chromium
npm test
```

Linuxでブラウザー用のOSライブラリも必要な場合は `npx playwright install --with-deps chromium` を使います。導入が失敗したらブラウザーテストは実行しません。

期待結果はcheckのokがtrue、型チェックと通常ビルドの終了コード0、setup・検索・ビルド検証・ブラウザーの全テスト成功です。不正な記事リンクを作るテストは「ビルド失敗を確認したらテスト成功」になります。テストは一時コピーを使用し、本物の記事へ異常例を追加しません。

setupテストは未回答・台帳欠落・不正値・古い回答・手編集・失敗時復元・本文保持・再適用に加え、質問範囲の選択・省略項目の維持・未確認の変更の拒否を確認します。ブラウザーは `/preview/` で配信して文書導線、日本語検索、記事追加、検索除外、画像、キー操作、モバイルとダーク表示を確認します。テスト用の追加記事は配布サイトへ混ぜません。

```sh
npm run serve
```

通常ビルド後にserveし、ホーム、サイドバー、記事、画像、検索を目視してください。検証用の既定ポートは4186です。使用中ならplaywright.use.baseURLなどをsetupで変更し、テストサーバー設定もそろえてください。独自のwebServerを設定しない場合は一時コピーを起動する補助処理を使用します。

## 画面PNGを撮影する

ビルド済みサイトをChromiumで開き、ホーム・記事・検索結果・モバイル記事の4枚を保存します。出力先は実行場所からの相対パス、または絶対パスで指定します。同名のPNGは更新されるため、保存したい画像がある場合は別の出力先を選びます。

```sh
npm run build
npx playwright install chromium
node scripts/capture.mjs --output screenshots
```

作業場所は展開先の`docusaurus-basic/`です。既定のサンプル内容・ライト表示を撮影し、ホームと記事の表示内容、検索語「設定」の結果を確認します。サンプルの文言や画像を変更した場合は、撮影スクリプトの対象要素も合わせて変更してください。ローカル配信にはポート4188を使用します。撮影は検証テストとは別の操作で、指定した出力先にだけPNGを書き込みます。
