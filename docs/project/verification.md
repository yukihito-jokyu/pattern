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
| `scripts/ci-result.mjs` | `needs`のサイト・対象判定・ZIP検証結果から合否を決め、時間レポートの取得・投稿失敗を警告として分ける |

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

全件検証になる共通ファイルは、`scripts/pattern-ci.mjs`の`sharedVerificationFiles`で管理します。ワークフロー、ZIP生成、配置確認、ZIP検証、その共通ライブラリ、ルートの`.nvmrc`・`package.json`・`package-lock.json`が対象です。`.nvmrc`は全ZIP検証に使うNode.jsのメジャー版を指定するため、変更時は全件を確認します。共通処理のファイル構成を変えた場合は、この集合も確認します。パターン名の追加登録は不要です。

履歴を取得してGitで比較するため、ファイル一覧の件数制限で対象が欠落することはありません。比較元や共通祖先を取得できない場合はCIを失敗させ、対象0件とは扱いません。push前のコミットが存在しない初回pushでは全件を検証します。

対象が0件ならmatrixジョブを省略します。合否を決める固定名の`report`とmainの公開条件は、`verify`・`discover-patterns`の成功に加え、`has-patterns == 'true'`なら`patterns`の成功、`has-patterns == 'false'`なら`patterns`のスキップを要求します。対象判定の失敗、出力欠落、不正な省略、時間切れ、キャンセルは合格・公開につなげません。`report`は通常PR・Fork・Dependabotとmainへのpushで動き、ワークフロー全体をキャンセルした場合は実行しません。判定はGitHub APIの反映待ちに依存せず、`needs`の結果を使います。

`report`は他の全ジョブを待ちますが、合否に使うのはサイト検証・対象判定・ZIP検証です。Pages公開の成否は`deploy`で別に確認します。公開は`report`の時間コメントに依存せず、同じ実行の`verify`がアップロードしたサイトだけを使います。

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

## Actionsの環境・更新・公開順序

全ジョブのrunnerは`ubuntu-24.04`、Node.jsはルートの`.nvmrc`にある`22`を`node-version-file`で読みます。外部Actionは、既存のメジャー版を維持して`gha pin`で解決した40桁SHAと`# vX.Y.Z`で固定します。新規導入した`astral-sh/setup-uv`もSHA固定し、検査に使うuvは`0.13.4`です。各checkoutは`persist-credentials: false`とし、ワークフローの権限は`permissions: {}`、各ジョブに必要な権限を明示します。

ルートの`.github/dependabot.yml`はGitHub Actionsを週次で確認し、7日間のcooldown後に更新を1つのPRへまとめます。対象は`/`と`/.github/actions/*`です。配布用の`patterns/`内にある別リポジトリ向け設定の更新とは分けて扱います。メジャー更新PRは入力や実行環境の互換性を確認してから取り込みます。

プロジェクト直下には`.claude/`と`.gha/`を置きません。ルートCIの`verify`は、一時ディレクトリへGit履歴・現在の`.github/`・キットの`.gha/`を用意し、その中で検査します。検査設定・ロックファイルはキットのものを変更せず使います。PRではbase SHA、mainへのpushではpush前のSHAと比較し、`gha check --ratchet`でファイルとルールIDの組ごとの指摘を増やさないことを確認します。比較のためcheckoutは全履歴を取得し、比較元が不明・取得不能なら検査を失敗させます。手元でもルートから次を実行します。uvとPython 3.12以上が必要で、検査ツールはロックファイルに従ってuvが用意します。

```sh
# 未コミットの変更を確認する場合。一時コピー内で検査し、終了時に削除する。
(
  set -e
  validation_root=$(mktemp -d)
  trap 'rm -rf "$validation_root"' EXIT
  git clone --shared --no-checkout . "$validation_root"
  cp -R .github "$validation_root/.github"
  cp -R patterns/development/skills/github-actions-kit/.gha "$validation_root/.gha"
  cd "$validation_root"
  uv run --locked --script .gha/gha.py check --ratchet HEAD
  uv run --locked --script .gha/gha.py pin --verify
)
```

今回は保守的更新のため、書式・名前の既存指摘とCI内の公開構造は残します。`gha check`単独は指摘0件を保証しません。標準形の`run-report`はスキップ全般を合格と扱うため、ルートでは既存の時間レポートと`ci-result.mjs`の厳密な判定を使います。公開のファイル分離、コメントの直列化を含むジョブの`concurrency`、標準形のreportとの差は、全面再構成時に検討します。

ワークフローの`concurrency`はPR番号またはブランチを単位にし、追加pushで実行中の古いPRだけをキャンセルします。mainへのpushは実行中の検証・公開を止めません。`deploy`も`github-pages`グループで直列化し、ロック取得後、Pagesの設定・公開より先にAPIから現在のmain先頭を取得します。実行の`GITHUB_SHA`と一致しない場合は公開を省略し、Summaryに理由を残します。照合APIが失敗した場合も公開しません。

公開対象は「公開直前の照合時点でmain先頭と一致し、同じ実行で検証済みのサイト」です。照合後にmainが進むと、その次の検証・公開までは直前の版が表示されます。`cancel-in-progress: false`でも待機中の実行は置換されるため、全pushの実行や、最新コミットが必ず最後に公開されることは保証しません。最新のmain実行が失敗・キャンセルされた場合は、Actionsで先頭コミットの実行を再実行し、`deploy`のSummaryと公開結果を確認します。古いコミットの再実行では先頭との照合で公開を止めます。この順序方針の実際の動作は、下記のGitHub上の確認で検証します。

## PRのCI実行時間レポート

同一リポジトリのブランチから作成した通常のPRでは、`report`ジョブが合否と時間レポートをSummaryに出し、時間レポートをPRコメントへ反映します。品質検証が失敗した場合や、変更対象がなくZIP検証を省略した場合も集計します。Fork・DependabotのPRとmainへのpushでは、合否とそのSummaryだけを作り、時間レポートのAPIを呼びません。全体をキャンセルした実行は対象外です。

`scripts/ci-timing-report.mjs`は、現在の実行IDを使ってGitHub APIのJob一覧を全ページ取得します。`filter=latest`により再実行前の古い一覧を混ぜず、matrixはパターンごとのJobとして表示します。集計ジョブ自身と、PRでは実行しない`deploy`は除外します。依存Jobの終了後も一覧APIへの反映が遅れる場合があるため、未完了のJobは詳細APIで再確認します。詳細APIも未反映なら10秒間隔で最大6回待って再取得し、それでも未完了なら最終結果を投稿せず、時間レポートの作成失敗を返します。`report`はこの失敗を警告として表示し、品質検証の合否は維持します。

レポートにはJobの時間・結果、全Jobを横断した遅いStep TOP 10、Job別に折りたためる全Stepの時間・結果を載せます。全Stepの詳細は実行順です。準備や終了処理のStepも含み、スキップや時刻欠落は「—」、実測0秒は「0秒」と区別します。時間は開始から終了までの差で、実行前の待ち時間や課金時間ではありません。並列Jobの時間を合計してPRの待ち時間として扱いません。

計測単位はGitHub ActionsのJob・Stepです。`Verify standalone ZIP`内の依存導入・ビルド・テストや、`npm run build`内部の各コマンドは、それぞれのStep全体に含まれます。内部コマンドごとの計測は行いません。

同じ内容をActions Summaryへ保存し、PRでは`github-actions[bot]`が投稿した`<!-- ci-timing-report -->`で始まるコメントを更新します。初回だけ新規投稿するため、追加pushや再実行でコメントが増えません。文字数上限を超える場合は、コメントの詳細を省略してその理由とSummaryへのリンクを載せ、全StepはSummaryに残します。

コメント更新の競合を避けるため、集計ジョブだけをPR番号ごとの`concurrency`で直列化します。投稿前にPRが開いていることと最新コミットの一致を確認し、同じコミットの新しいCI実行や新しい試行のレポートがあれば古い結果を投稿しません。古い実行のSummaryは、その実行の記録として残ります。

`report`だけにコメント用の`actions: read`・`pull-requests: write`を付け、checkout用の`contents: read`も指定します。認証は`GITHUB_TOKEN`を使い、追加のPATやnpm依存関係は不要です。従来は投稿権限不足などのAPI失敗で集計ジョブを失敗させていましたが、今回は必須チェックを品質検証に使うため、取得・投稿失敗をActionsの警告とSummaryに分けます。品質検証が成功なら`report`は成功、品質検証が失敗なら時間レポートの成否によらず失敗です。`403 Resource not accessible by integration`などの原因はログとリポジトリの権限設定で確認してください。構文不正や品質判定用の入力欠落を警告へ変えることはありません。

変更時には`node --test tests/scripts/ci-result.test.mjs tests/scripts/ci-timing-report.test.mjs`を実行します。共通テストでは品質結果の組合せ、ZIP省略条件、Fork・Dependabotの判定、API失敗と品質失敗の分離、古いコメントの抑止、公開前の先頭照合を確認します。ローカルのテストはGitHubのスケジューラーや権限設定の実行確認を代替しません。実際のPR・mainでは次の順で確認します。

1. 通常PRでCIを完了させ、botのコメントにJob一覧・TOP 10・Job別の全Step詳細があることを確認します。コメントのパーマリンク末尾にある`issuecomment-`以降のIDを控えます。
2. 同じPRへ追加pushし、対象コミットが更新され、コメントIDが変わらないことを確認します。
3. Actionsで同じ実行の「Re-run all jobs」を実行し、コメントIDを維持したまま試行番号が増えることを確認します。
4. 同じPRへ短い間隔で追加pushし、古い実行がキャンセルされ、最新の`report`と同じIDのコメントが残ることを確認します。Fork・Dependabotでは`report`が品質を判定し、コメントAPIを呼ばないことを確認します。
5. ZIP対象0件、対象ありの成功・失敗、対象判定の失敗、不正なスキップで`report`と公開条件が一致することを確認します。mainへのpushでは、同じ実行の検証済みサイトだけが公開されること、連続push中も実行中の公開が停止されないこと、古いmainコミットの再実行が公開前の照合で省略されることを確認します。
6. 上記をGitHub上で確認してから、既存のmainブランチ保護とrulesetの必須チェック名・提供元アプリを調べます。Settings → BranchesとSettings → Rules → Rulesetsで、該当ブランチへの適用範囲も確認します。現在の設定を控え、`report`をGitHub Actions提供の必須チェックに追加し、認識されることを確認してから、置き換え対象の検証チェックを外します。ほかの保護条件と公開用チェックを一括削除しません。この変更には保護設定を編集できる権限と別途の操作承認が必要です。

古い実行などで投稿を省略した場合は、集計Stepのログに`posted: false`と理由を出力します。投稿に成功した場合は`posted: true`とコメントのURLを出力します。

仕様は[GitHub ActionsのJob・Step取得API](https://docs.github.com/en/rest/actions/workflow-jobs#list-jobs-for-a-workflow-run)と[PRコメントの作成・更新API](https://docs.github.com/en/rest/issues/comments)で確認できます。

サイト、個別実装、人間の確認結果は分けて記録します。関連仕様は[DocusaurusのDocs設定](https://docusaurus.io/docs/api/plugins/@docusaurus/plugin-content-docs)、[画像・ファイルの扱い](https://docusaurus.io/docs/markdown-features/assets)、[Playwrightのサーバー起動](https://playwright.dev/docs/test-webserver)、[GitHub Actionsのmatrix](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/run-job-variations)で確認できます。
