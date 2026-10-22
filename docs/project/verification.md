---
title: 検証とZIP配布
description: スクリプトの入力・出力・失敗時の扱いと、ZIP展開後の検証規約。
slug: /project/verification
sidebar_position: 3
---

# 検証とZIP配布

配置や操作を間違えても、不完全な成果物を完成品として扱わないようにします。構造はスクリプト、動作は個別検証、説明の妥当性は人間のレビューで確認します。

## 各スクリプトの役割

プロジェクト直下の`scripts/`は、プロジェクト全体に影響する共通処理だけを配置します。下表のZIP検証は対象IDと任意のコマンドを受け取る共通処理です。特定パターンの依存導入・検証手順をここへ組み込まず、対象パターン内のコマンドを使います。

| ファイル | 入力と確認・出力 |
| --- | --- |
| `scripts/check-dir.mjs` | 文書と実装の3階層の対応・命名・README・実ファイル |
| `scripts/check-docs.mjs` | Markdownのメタデータ・未記入欄・PNG参照・対応ZIP・一覧の紹介設定 |
| `scripts/build-downloads.mjs` | 配置確認後、必要なファイルからパターンごとのZIPを生成 |
| `scripts/verify-patterns.mjs` | ZIPを別の場所に展開し、明示された検証コマンドを実行 |
| `scripts/pattern-ci.mjs` | 各パターンの`ci.json`を検証し、Git差分に基づくCIの実行対象一覧をJSONで出力 |
| `scripts/ci-timing-report.mjs` | GitHub APIでJob・Stepの実行時間を集計し、Actions SummaryとPRの既存コメントを更新 |

IDの命名・3階層の検証と文書・実装・ZIPのパス生成は、`scripts/lib/patterns.mjs`を共通の定義として使います。個別のコマンドで正規表現やZIPのURL規則を作り直しません。トップページは`plugins/pattern-list/`が文書の紹介情報を読み、掲載対象と画像をページへ渡します。

ルートから実行します。サイトビルドは配置確認、文書確認、ZIP生成、Docusaurusビルドの順です。途中失敗は後続を止め、非0の終了コードを返します。

文書確認はZIP生成前に、リンクが生成予定パスを指すか確認します。未生成のZIPがないことだけで失敗させません。生成後はビルドとブラウザーで実際に取得できることまで確認します。

## 個別パターンの検証規約

検証方法は対象の言語・ツールに合わせます。例えばNode.jsのテストなら`node --test`、Goなら`go test ./...`を使います。テスト本体の名前や利用ツールは統一しません。必要なテスト・設定ファイルはZIPに収録し、READMEに環境・依存関係の準備、実行場所、コマンド、期待結果を書きます。準備に失敗したら後続を実行しません。単なるログ出力ではなく、具体的な期待結果を確認してください。

ZIPを別の場所へ展開し、READMEの手順で確認します。準備を含めて1つのコマンドで実行できる場合は、次の補助スクリプトも利用できます。

```sh
# Goのパターンを検証する場合の例（IDは実際の対象に置き換える）
npm run verify:patterns -- --id backend/api/error-handling -- go test ./...
```

`--id`と、`--`以降の実行コマンドは必須です。スクリプトはZIPを一時ディレクトリへ展開し、パターンのルートを作業場所にして指定コマンドを実行します。コマンドの推測や依存関係の自動導入はしません。複数の準備手順がある場合は、ZIPを自分で展開してREADMEの順に実行するか、対象ツールのタスクにまとめます。

制限時間は120秒です。変更する場合はコマンド区切りの前に`--timeout-ms 300000`などを指定します。終了コード0だけを成功とし、非0や時間切れは失敗、実行コマンドが見つからない場合は未実施として報告します。失敗・未実施のいずれも管理側は非0で終了します。環境を用意できず実行しなかった場合も、理由を明記して未実施として記録します。

実用パターンには[Docusaurusのドキュメントサイト](../web/documentation/docusaurus-basic/index.md)があります。共通CIはパターンごとに生成ZIPを展開し、そこに収録されたコマンドで依存導入・設定確認・型チェック・ビルド・テストを行います。管理処理はテスト用サンプルで別に確認し、その成功を個別実装の検証へ置き換えません。

## ZIPの収録と更新

生成先は`static/downloads/patterns/<分野>/<分類>/<パターン>.zip`です。ZIP内はパターン名のディレクトリにまとまり、README・実装・検証ファイルが入ります。

必要な隠し設定を含め、`node_modules`、`build`、`dist`、`.git`、`.cache`、`.docusaurus`、`coverage`、`test-results`、`playwright-report`、`__pycache__`、`.venv`などを除外します。必要な実ファイルをこれらの生成物用ディレクトリに置かないでください。シンボリックリンクは収録せず、実ファイルの配置を求めるエラーにします。

一時ディレクトリで全ZIPを生成・確認し、成功時だけ配布先を置き換えます。途中失敗で一部だけ更新せず、サイトビルドを止めます。古いZIPが残っていても今回の生成成功とは扱いません。正常な更新では削除・改名された古いZIPが消え、他の静的ファイルは残ります。

## テストとCI

プロジェクト直下の`tests/`は、管理スクリプト・掲載サイト・検索・ZIP配布などプロジェクト全体の共通機能のテストと、その補助処理・fixtureだけを配置します。個別パターン専用のテストは`patterns/<分野>/<分類>/<パターン>/`内に置き、ZIP単体で実行します。共通機能の検証を特定の実用パターンの文言・設定・収録ファイルへ依存させません。

正常なfixtureを一時ディレクトリへコピーし、欠落・配置誤り・画像形式偽装・誤リンク・収録漏れ・失敗・時間切れを作って、想定した理由で失敗するか確認します。本物の文書・実装・配布物は変更しません。

検索処理は結果を確認し、ブラウザーでは導線、PNG表示、ZIP取得と中身、検索から対象文書への移動を確認します。検証用サイトは一時環境で作り、公開サイトにサンプルを混ぜません。

共通CIは管理スクリプト・サイトを検証するジョブと、ZIPを検証する共通のmatrixジョブに分かれます。`scripts/pattern-ci.mjs`が文書と実装の対応を確認し、全パターンの`ci.json`を確認したうえで、変更された実装だけをZIP検証の対象にします。文書だけの更新や、対応済みの実行環境を使うパターンの追加では、ワークフロー本体と公開ジョブの依存先を書き換える必要はありません。対象の欠落、設定ファイルの欠落、不正な設定は一覧の作成時に失敗します。

ZIP検証の変更判定は次のとおりです。

| 変更・イベント | ZIP検証の対象 |
| --- | --- |
| PR | 比較元ブランチとの共通祖先から、PRの最新コミットまでに変更したパターンすべて。追加pushでもPR全体の差分で判定 |
| mainへのpush | push前後で変更したパターン |
| `patterns/<分野>/<分類>/<パターン>/`配下の変更 | README・テスト・設定を含め、そのパターン |
| `docs/`・`src/`・`plugins/`・ルートの`tests/`だけの変更 | ZIP検証は省略。共通のサイト検証は実行 |
| 共通のZIP生成・検証・CI・依存定義の変更 | 現在ある全パターン |
| パターンの改名 | 変更前後のパスを確認し、現在存在する対象を検証 |
| パターンの削除だけ | 削除済みの実装は実行せず、配置・文書・サイトの共通検証で確認 |

全件検証になる共通ファイルは、`scripts/pattern-ci.mjs`の`sharedVerificationFiles`で管理します。ワークフロー、ZIP生成、配置確認、ZIP検証、その共通ライブラリ、ルートの`package.json`・`package-lock.json`が対象です。共通処理のファイル構成を変えた場合は、この集合も確認します。パターン名の追加登録は不要です。

履歴を取得してGitで比較するため、ファイル一覧の件数制限で対象が欠落することはありません。比較元や共通祖先を取得できない場合はCIを失敗させ、対象0件とは扱いません。push前のコミットが存在しない初回pushでは全件を検証します。

対象が0件ならmatrixジョブを省略します。この場合もmainではサイト検証と対象判定の成功を条件に公開を進めます。選ばれたZIP検証の失敗、比較の失敗、キャンセルは公開につなげません。

手元でPR相当の対象だけを確認するには、次を実行します。

```sh
node scripts/pattern-ci.mjs --base main --head HEAD --merge-base
```

`--merge-base`を省略すると2つのコミット間の差分で判定します。`--base`を指定しなければ、従来どおり全件の実行設定を出力します。

各パターンのルートに、次の形式の`ci.json`を置きます。これはCIから呼ぶコマンドを明示するための設定です。テストの種類は各パターンで選びます。

```json
{
  "command": ["bash", "scripts/verify-ci.sh"],
  "goVersionFile": "go.mod",
  "pythonVersion": "3.12"
}
```

`command`は必須で、実行ファイルと引数を配列にします。シェルとして解釈せず、ZIP展開先を作業場所として実行します。複数の準備・検証がある場合は、この例のようにパターン内のスクリプトにまとめ、途中失敗で停止させます。GoとPythonが不要なら`goVersionFile`と`pythonVersion`は省略します。Goの定義ファイルはパターン内の実ファイルを指定し、Pythonは`3.12`のように指定します。Node.js 22とUbuntuは共通環境です。新しいOSや言語の準備が必要になったときは、共通CIにその環境への対応を追加します。未対応環境を成功とは扱いません。

CIと同じコマンドは、環境を準備したうえでルートから実行できます。

```sh
npm run verify:patterns -- --id backend/architecture/go-clean --ci --timeout-ms 1200000
```

`--ci`は`ci.json`のコマンドを選びます。手動のコマンド指定とは併用できません。従来の`--`以降にコマンドを書く方法も使えます。CIの検証時間は20分、準備を含むジョブ全体は25分です。各パターンを別のrunnerで実行し、1件が失敗しても他の検証を続けます。選ばれたパターンの成功を確認してから公開します。失敗ログを成果物として保存し、ブラウザーの結果など追加資料は`CI_ARTIFACTS_DIR`へ保存できます。Goの検証では通常の失敗時にもAPIと検証DBを終了します。時間切れやrunnerの強制停止時は終了処理が走らない場合があるため、使い捨てのCI環境で実行してください。

## PRのCI実行時間レポート

同一リポジトリのブランチから作成した通常のPRでは、`CI Timing Report`ジョブが`verify`・`discover-patterns`・`patterns`の終了後に実行されます。品質検証が失敗した場合や、変更対象がなくZIP検証を省略した場合も集計します。Fork・DependabotのPR、mainへのpush、キャンセルされた実行は対象外です。公開ジョブはレポートに依存しません。

`scripts/ci-timing-report.mjs`は、現在の実行IDを使ってGitHub APIのJob一覧を全ページ取得します。`filter=latest`により再実行前の古い一覧を混ぜず、matrixはパターンごとのJobとして表示します。集計ジョブ自身と、PRでは実行しない`deploy`は除外します。取得時点で未完了のJobがあれば、最終結果として投稿せず失敗させます。

レポートにはJobの時間・結果、全Jobを横断した遅いStep TOP 10、Job別に折りたためる全Stepの時間・結果を載せます。全Stepの詳細は実行順です。準備や終了処理のStepも含み、スキップや時刻欠落は「—」、実測0秒は「0秒」と区別します。時間は開始から終了までの差で、実行前の待ち時間や課金時間ではありません。並列Jobの時間を合計してPRの待ち時間として扱いません。

計測単位はGitHub ActionsのJob・Stepです。`Verify standalone ZIP`内の依存導入・ビルド・テストや、`npm run build`内部の各コマンドは、それぞれのStep全体に含まれます。内部コマンドごとの計測は行いません。

同じ内容をActions Summaryへ保存し、PRでは`github-actions[bot]`が投稿した`<!-- ci-timing-report -->`で始まるコメントを更新します。初回だけ新規投稿するため、追加pushや再実行でコメントが増えません。文字数上限を超える場合は、コメントの詳細を省略してその理由とSummaryへのリンクを載せ、全StepはSummaryに残します。

コメント更新の競合を避けるため、集計ジョブだけをPR番号ごとの`concurrency`で直列化します。投稿前にPRが開いていることと最新コミットの一致を確認し、同じコミットの新しいCI実行や新しい試行のレポートがあれば古い結果を投稿しません。古い実行のSummaryは、その実行の記録として残ります。

集計ジョブだけに`contents: read`・`actions: read`・`pull-requests: write`を付けます。認証は`GITHUB_TOKEN`を使い、追加のPATやnpm依存関係は不要です。投稿権限不足などAPIで失敗した場合は集計ジョブを失敗させます。集計済みのSummaryは残るため、`403 Resource not accessible by integration`などの原因をActionsのログとリポジトリの権限設定で確認してください。

変更時には`node --test tests/scripts/ci-timing-report.test.mjs`を実行します。実際のPRでも、初回のコメント投稿、追加push後の同じコメントIDの更新、再実行時の試行番号更新を確認します。失敗・ZIP検証なし・Fork・Dependabot・古い実行の抑止はAPIの応答を使う共通テストでも検証します。

仕様は[GitHub ActionsのJob・Step取得API](https://docs.github.com/en/rest/actions/workflow-jobs#list-jobs-for-a-workflow-run)と[PRコメントの作成・更新API](https://docs.github.com/en/rest/issues/comments)で確認できます。

サイト、個別実装、人間の確認結果は分けて記録します。関連仕様は[DocusaurusのDocs設定](https://docusaurus.io/docs/api/plugins/@docusaurus/plugin-content-docs)、[画像・ファイルの扱い](https://docusaurus.io/docs/markdown-features/assets)、[Playwrightのサーバー起動](https://playwright.dev/docs/test-webserver)、[GitHub Actionsのmatrix](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/run-job-variations)で確認できます。
