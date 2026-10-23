<!-- 生成物。github-actions-kit の docs/design/rules.md から scripts/gen_docs.py が作る。手で編集しない -->
# GitHub Actions のワークフローのルール

GitHub Actions のワークフロー、composite アクション、`dependabot.yml` を書く・直すときのルールである。実装用スキル（`../SKILL.md`）、レビュー用スキル、検査の指摘は、ここのルールIDを参照する。

- 検査の指摘は `<ルールID> <パス>:<行> <説明>` の形で出る。外部ツールの指摘は、説明の先頭に `[ツール:規則名]` が付く
- **強制**の先頭のキーワードは、そのルールを守らせる仕組みである。`lint` と `structure` は `uv run --locked --script .gha/gha.py check` が落とし、`review` はレビュー用スキルが確かめ、`doc` は手順として守る
- **出典**と**強制**の欄のパス（`research.md`、`rules_*.py` など）は github-actions-kit のリポジトリのものである
- 「見本」と書いたファイルは `examples/` にある（`examples/workflows/ci.yml` など）

## 用語

| 用語 | 意味 |
|---|---|
| ワークフロー | `.github/workflows/<名前>.yml`。`on:` を持つファイル |
| 再利用ワークフロー | `on:` が `workflow_call` だけのワークフロー。ファイル名は `reusable-<名前>.yml` |
| composite アクション | `.github/actions/<名前>/action.yml`。`runs.using: composite` のアクション |
| 外部アクション | `uses:` が `./` で始まらないアクションと再利用ワークフロー |
| report ジョブ | `ci.yml` の最後に置く ID `report` のジョブ。全ジョブの所要時間を PR とジョブサマリーに出し、needs の結果で合否を決める（OPS-01） |
| gha | 検査の CLI。`uv run --locked --script .gha/gha.py <サブコマンド>` で起動する。サブコマンドは `check`、`pin`、`intent` |
| 作成 | まだ無いワークフローを新しく書くこと（PROC-06） |
| 保守的更新 | 既存のワークフローの書き方と意図を残し、頼まれた所だけを変えること（PROC-07） |
| 破壊的更新 | 既存のワークフローがしていることを棚卸しし、ルールどおりに書き直すこと（PROC-08） |
| 配布先 | `install.py` でキットを入れたリポジトリ |
| キット | この基盤の道具（`.gha/`、`.github/actions/run-report/`、`install.py`、`scripts/`、`tests/`） |

## 追加した軸

| 軸 | 内容 | 置く節 |
|---|---|---|
| X1 | タグとラベル（`runs-on` に書くランナーのラベル） | NAM |
| X2 | state と環境の分け方（GitHub の environment） | STR |
| X3 | 権限ポリシーの書き方（GITHUB_TOKEN の `permissions`） | OPS |
| X5 | 公開 API の互換性（composite アクションと再利用ワークフローの inputs・outputs） | PROC |
| X6 | トリガー（`on:` の選び方と、ワークフローのファイルとの対応） | STR |
| X7 | アクションの参照の固定と更新 | DEP |
| X8 | 更新の方式（作成・保守的更新・破壊的更新） | PROC |
| X9 | 処理時間の報告と必須チェック（report ジョブ） | OPS |
| X10 | キャッシュと成果物 | STATE |

X1〜X3 は iac、X4・X5 は cli-library の追加の軸で、X6〜X10 は GitHub Actions に固有の軸である。

## STR 配置と構造

### STR-01 ファイルの置き場は4種類に固定する

- 軸: A1, A6, A7
- 決定: `.github/` の下に置くファイルは次の表の4種類とし、ワークフローは `.github/workflows/` の直下、composite アクションは `.github/actions/<名前>/action.yml`、ワークフローから呼ぶスクリプトは `.github/scripts/` の直下に置く。
  | 置くもの | パス |
  |---|---|
  | ワークフロー | `.github/workflows/<名前>.yml` |
  | composite アクション | `.github/actions/<名前>/action.yml`（そのアクションだけが使うスクリプトは同じディレクトリ） |
  | ワークフローから呼ぶスクリプト | `.github/scripts/<名前>.sh` か `.github/scripts/<名前>.py` |
  | Dependabot の設定 | `.github/dependabot.yml` |
  | 検査の道具と設定（actionlint、zizmor、yamllint） | `.gha/`（`.github/` には置かない） |
- 理由: GitHub は `.github/workflows/` のサブディレクトリのファイルを実行しない。置き場が作者ごとに分かれると、検査の対象からも漏れる。
- 出典: research.md の「GitHub Actions」
- 強制: structure — `rules_str.py` の `str01_layout`（置き場の深さとファイル名）
- probe: STR-01-a
- 良い例:
  `.github/actions/setup-kit/action.yml`
- 悪い例:
  `.github/workflows/deploy/production.yml`

### STR-02 ワークフローのファイルは目的ごとに分け、トリガーとの対応を固定する

- 軸: A2, A3, X6
- 決定: ワークフローのファイル名と `on:` を、次の表の目的の行で決める。`pull_request` と `merge_group` を書けるのは `ci.yml` だけ、`workflow_call` を書けるのは `reusable-<名前>.yml` だけとし、`schedule` には `workflow_dispatch` を並べる。
  | 目的 | ファイル | `on:` |
  |---|---|---|
  | PR の検証（必須チェックにするもの全部） | `ci.yml` | `pull_request`（絞り込みを書かない）と `push.branches` に既定のブランチ1つ。マージキューを使うなら `merge_group` |
  | タグからのリリース | `release.yml` | `push.tags` |
  | デプロイ・公開 | `deploy-<先>.yml` | `push.branches` と `workflow_dispatch` |
  | 定期・手動の保守 | `<目的>.yml` | `schedule` と `workflow_dispatch` |
  | 2つ以上のワークフローから呼ぶジョブ | `reusable-<名前>.yml` | `workflow_call` だけ |
  | 上のどれでもない | `<目的>.yml` | `workflow_dispatch` |
- 理由: PR の検証を複数のワークフローに分けると、必須チェックの名前が増え、report ジョブも分かれる。トリガーの書き方が作者ごとに違うと、同じ目的のワークフローが別の時に動く。
- 出典: research.md の「GitHub Actions」
- 強制: structure — `rules_str.py` の `str02_triggers`（PR のトリガーの置き場、`reusable-*` のトリガー、`schedule` と `workflow_dispatch`、`ci.yml` の `pull_request` と `push`、表の目的の行に無いトリガー）
- probe: STR-02-a、STR-02-b、STR-02-c
- 良い例:
  見本: `.github/workflows/ci.yml`、`.github/workflows/security-audit.yml`
- 悪い例:
  ```yaml
  # docs-lint.yml（PR の検証を ci.yml と別のファイルにした）
  on:
    pull_request:
      paths:
        - docs/**
  ```

### STR-03 共有は2か所目で切り出し、ステップなら composite、ジョブなら再利用ワークフローにする

- 軸: A4, D1
- 決定: 同じものを書く2か所目が現れた時点で、次の表のとおり切り出す。1か所だけのものは、ワークフローに直接書く。
  | 同じになるもの | 切り出す先 |
  |---|---|
  | 2つ以上のステップの並び（`uses` と `with` と `run` が同じ） | composite アクション `.github/actions/<名前>/action.yml` |
  | ジョブ全体（`runs-on`、`permissions`、ステップの並び） | 再利用ワークフロー `.github/workflows/reusable-<名前>.yml` |
  | 1つのステップだけ | 切り出さない（両方に書く） |
  | 11 行以上のシェルの処理 | スクリプト（STR-04） |

  YAML のアンカーとエイリアス（`&名前`、`*名前`）では共有しない。
- 理由: 切り出す時期と先が作者ごとに違うと、同じ処理が composite と再利用ワークフローとコピーとアンカーの4通りで書かれる。アンカーは1つのファイルの中でしか効かず、actionlint の指摘の行も分かりにくくなる。
- 強制: structure, review — `rules_str.py` の `str03_anchors`（アンカーの禁止）、レビュー用スキルの4節（差分の中で同じステップの並びが2か所にあるか）
- probe: STR-03-a
- 良い例:
  見本: `.github/actions/setup-kit/action.yml`（`reusable-check.yml` の3つのジョブが使う）
- 悪い例:
  ```yaml
  # 3つのジョブに同じ2ステップをコピーした
  - name: Set up uv
    uses: astral-sh/setup-uv@<sha> # v10.3.2
  - name: Install dependencies
    run: uv sync --locked
  ```

### STR-04 run の本文は10行までにし、超えたらスクリプトに切り出す

- 軸: A5, D6
- 決定: `run:` の本文が11行以上になったら、処理を `.github/scripts/<名前>.sh`（composite アクションでは同じディレクトリ）に移し、`run: bash .github/scripts/<名前>.sh` で呼ぶ。
- 理由: 長いシェルを YAML に埋め込むと、shellcheck の指摘の行が読みにくく、手元で試せない。切り出す長さが作者ごとに違うと、同じ処理の置き場が分かれる。
- 強制: structure — `rules_str.py` の `str04_scripts`（`run:` の行数）
- probe: STR-04-a
- 良い例:
  ```yaml
  - name: Build kit archive
    run: bash .github/scripts/build-archive.sh
  ```
- 悪い例:
  11 行以上の `run: |` のブロック

### STR-05 デプロイと公開の書き込み権限を持つジョブには environment を付ける

- 軸: X2
- 決定: `contents`・`deployments`・`id-token`・`packages`・`pages` のどれかに `write` を付けるジョブには `environment:` を付け、名前を次の表で決める。
  | 先 | environment の名前 |
  |---|---|
  | GitHub Pages | `github-pages` |
  | タグからのリリース | `release` |
  | 本番 | `production` |
  | 本番の前の確認環境 | `staging` |
  | 上のどれでもない | 先の名前の kebab-case |
- 理由: environment に付けた保護（承認者、ブランチの制限、環境の secrets）は、environment を名乗るジョブにしか効かない。名前が作者ごとに違うと、保護を設定した環境と別の名前で動く。
- 出典: research.md の「GitHub Actions」
- 強制: structure — `rules_str.py` の `str05_environment`（書き込み権限と environment の組）
- probe: STR-05-a
- 良い例:
  見本: `.github/workflows/release.yml` の `publish` ジョブ
- 悪い例:
  ```yaml
  publish:
    permissions:
      contents: write
  ```

## DEP 境界と依存

### DEP-01 ジョブから呼ぶのは再利用ワークフロー、ステップから呼ぶのはアクションにし、入れ子にしない

- 軸: B1
- 決定: 呼び出しの向きを次の表に限る。表に無い組（再利用ワークフローから再利用ワークフロー、composite アクションからローカルのアクション）は書かない。
  | 呼ぶ側 | 呼べるもの |
  |---|---|
  | ワークフローのジョブの `uses:` | `./.github/workflows/reusable-<名前>.yml`、SHA で固定した外部の再利用ワークフロー |
  | ワークフローのステップの `uses:` | `./.github/actions/<名前>`、外部アクション |
  | 再利用ワークフローのステップの `uses:` | `./.github/actions/<名前>`、外部アクション |
  | composite アクションのステップの `uses:` | 外部アクション |
- 理由: 入れ子にすると、権限と secrets がどの段で絞られたかを追えなくなり、1つの変更で触るファイルが予測できなくなる。
- 出典: research.md の「GitHub Actions」
- 強制: structure — `rules_dep.py` の `dep01_direction`
- probe: DEP-01-a
- 良い例:
  ```yaml
  check:
    uses: ./.github/workflows/reusable-check.yml
  ```
- 悪い例:
  ```yaml
  check:
    uses: ./.github/workflows/ci.yml
  ```

### DEP-02 inputs・outputs・secrets の定義には description と required を書く

- 軸: B2, D2, D3
- 決定: 再利用ワークフロー（`workflow_call`）、手動実行（`workflow_dispatch`）、composite アクションの入力には `description` と `required` を書き、ワークフローの入力には `type` も書き、`required: false` の入力には `default` を書き、出力には `description` と `value` を書き、再利用ワークフローの secrets には `description` と `required` を書く。
  | 定義 | 必須のキー |
  |---|---|
  | `workflow_call` の入力 | `description`、`required`、`type`（`boolean`・`number`・`string`）、`required: false` なら `default` |
  | `workflow_dispatch` の入力 | `description`、`required`、`type`（`boolean`・`choice`・`environment`・`number`・`string`）、`choice` なら `options`、`required: false` なら `default` |
  | composite アクションの入力 | `description`、`required`、`required: false` なら `default` |
  | 出力（`workflow_call` と composite アクション） | `description`、`value` |
  | `workflow_call` の secrets | `description`、`required` |
- 理由: 入力の型と既定値が書かれていないと、呼ぶ側が値を推測し、作者ごとに渡し方が分かれる。
- 出典: research.md の「GitHub Actions」
- 強制: structure — `rules_dep.py` の `dep02_interface`
- probe: DEP-02-a
- 良い例:
  ```yaml
  inputs:
    needs:
      description: 呼び出し元のジョブの toJSON(needs)
      required: true
  ```
- 悪い例:
  ```yaml
  inputs:
    environment:
      default: staging
  ```

### DEP-03 ワークフロー同士は workflow_call だけでつなぐ

- 軸: B3
- 決定: ジョブの間のデータは `needs.<ジョブ>.outputs` か成果物（STATE-01）で渡し、ワークフローの間は再利用ワークフローの呼び出しでつなぎ、`workflow_run` と `repository_dispatch` をトリガーに書かない。
- 理由: `workflow_run` は既定のブランチの権限と secrets で動くため、PR の成果物を信じると権限を奪われる。つなぎ方が作者ごとに違うと、どのワークフローが何を起動するかを追えない。
- 出典: research.md の「GitHub Actions」（`pull_request_target` と `workflow_run` の節）
- 強制: structure — `rules_str.py` の `str02_triggers`（禁止のトリガー）
- probe: DEP-03-a
- 良い例:
  ```yaml
  check:
    uses: ./.github/workflows/reusable-check.yml
  ```
- 悪い例:
  ```yaml
  on:
    workflow_run:
      workflows:
        - ci
  ```

### DEP-04 外部アクションは許可表にあるものだけを使い、API の操作は gh で書く

- 軸: B4, B6
- 決定: 使ってよい外部アクションは `.gha/zizmor.yml` の `forbidden-uses.config.allow` の表にあるものだけとし、表に足すときはユーザーの承認を得てから足し、GitHub の API・リリース・PR の操作はアクションを足さずに `run:` で `gh` を使って書く。
- 理由: アクションを足すたびに、そのコードをリポジトリの権限で動かすことになる。何を足すかが作者ごとに違うと、同じ処理に別々のアクションが使われる。
- 出典: research.md の「zizmor」
- 強制: lint — zizmor の `forbidden-uses`（`.gha/zizmor.yml` の `allow`）
- probe: DEP-04-a
- 良い例:
  ```yaml
  - name: Create release
    env:
      GH_TOKEN: ${{ github.token }}
    run: gh release create "$REF_NAME" --verify-tag --generate-notes
  ```
- 悪い例:
  ```yaml
  - name: Create release
    uses: softprops/action-gh-release@<sha> # v2.0.0
  ```

### DEP-05 PR の検証のワークフローでは、report ジョブの PR コメントのほかに書き込まない

- 軸: B5
- 決定: `ci.yml` のジョブに付けてよい書き込み権限は、report ジョブの `pull-requests: write` だけとし、デプロイ・リリース・push・タグ付けは `release.yml`・`deploy-<先>.yml`・保守のワークフローに書く。
- 理由: PR の検証は、PR を開いた人のコードを動かす。そこで書き込みをすると、PR のコードがリポジトリを書き換えられる。
- 出典: research.md の「GitHub Actions」
- 強制: structure — `rules_dep.py` の `dep05_side_effects`
- probe: DEP-05-a
- 良い例:
  見本: `.github/workflows/ci.yml`
- 悪い例:
  ```yaml
  # ci.yml の中で
  deploy-preview:
    permissions:
      contents: write
  ```

### DEP-06 外部アクションは40桁のコミット SHA と版のコメントで固定し、SHA は gha pin で得る

- 軸: X7
- 決定: 外部アクションと外部の再利用ワークフローは `owner/repo[/path]@<40桁のコミット SHA> # vX.Y.Z` の形で書き、SHA は記憶から書かずに `gha pin <owner/repo>` の出力を写し、`docker://` のイメージは `@sha256:<digest>` で固定する。
- 理由: タグは移動できるので、タグで参照すると別のコードが動きうる。記憶の SHA は存在しないか別のコミットを指すことがある。コメントの形をそろえると、Dependabot が SHA とコメントを一緒に更新できる。
- 出典: research.md の「GitHub Actions」「Dependabot（github-actions）」
- 強制: structure, lint — `rules_dep.py` の `dep06_pinning`（形とコメント）、zizmor の `unpinned-uses`（`hash-pin` の方針）
- probe: DEP-06-a、DEP-06-b
- 良い例:
  ```yaml
  - name: Check out repository
    uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
  ```
- 悪い例:
  ```yaml
  - uses: actions/checkout@v7
  - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1
  ```

## NAM 命名

### NAM-01 ファイル名とディレクトリ名は kebab-case にし、拡張子は .yml にする

- 軸: C1
- 決定: ワークフロー、composite アクションのディレクトリ、スクリプトの名前は `^[a-z0-9]+(-[a-z0-9]+)*$` の形にし、YAML の拡張子は `.yml` にする。
- 理由: `.yml` と `.yaml`、`snake_case` と `kebab-case` が混ざると、同じ種類のファイルを glob で拾えず、名前から置き場を予測できない。
- 強制: structure — `rules_nam.py` の `nam01_files`
- probe: NAM-01-a
- 良い例:
  `.github/workflows/security-audit.yml`
- 悪い例:
  `.github/workflows/Security_Audit.yaml`

### NAM-02 ID は kebab-case、環境変数は大文字の snake_case にし、ワークフローの name はファイル名にそろえる

- 軸: C2, C6
- 決定: ジョブ・ステップ・入力・出力・matrix のキー・environment の名前は `^[a-z][a-z0-9]*(-[a-z0-9]+)*$` の形にし、環境変数と再利用ワークフローの secrets の名前は `^[A-Z][A-Z0-9_]*$` の形にし、ワークフローの `name:` はファイル名から `.yml` を除いたものにし、composite アクションの `name:` はディレクトリ名にし、ジョブには `name:` を書かない。
- 理由: ジョブの `name:` と ID が違うと、必須チェックの名前と `needs` の名前がずれる。ID のケースが混ざると、式で参照するときに作者ごとに書き方が分かれる。
- 強制: structure — `rules_nam.py` の `nam02_ids`
- probe: NAM-02-a
- 良い例:
  ```yaml
  name: ci
  jobs:
    unit-test:
  ```
- 悪い例:
  ```yaml
  name: CI
  jobs:
    unit_test:
      name: Unit Test
  ```

### NAM-03 ジョブの ID は役割の語彙表から選ぶ

- 軸: C3
- 決定: ジョブの ID は、そのジョブの役割で次の表から選ぶ。
  | 役割 | ID |
  |---|---|
  | 整形・lint・静的解析 | `lint` |
  | 型検査 | `typecheck` |
  | テスト | `test` |
  | ビルド | `build` |
  | 再利用ワークフローの呼び出し | 呼ぶファイルの `reusable-` と `.yml` を除いた名前 |
  | デプロイ | `deploy` |
  | リリースの公開 | `publish` |
  | 定期の監査・保守 | `audit` |
  | 処理時間の報告と合否（`ci.yml`） | `report` |
  | 同じ役割のジョブが2つ以上ある | 役割の ID に対象を足す（`test-unit`、`test-e2e`） |
  | 上のどれでもない | 役割を表す英語の名詞1〜2語の kebab-case |
- 理由: 同じ役割のジョブの ID が作者ごとに違うと（`tests`、`unit`、`ci`）、`needs` と必須チェックの名前がそろわない。
- 強制: review — レビュー用スキルの4節で、ジョブの中身と ID の役割が合っているかを見る
- 機械化しない理由: ジョブの役割はステップの意味から判断する必要があるため
- probe: なし
- 良い例:
  `lint`、`test`、`report`
- 悪い例:
  `run-tests`、`ci-job`、`check-all`

### NAM-04 ステップには必ず英語の name を付け、先頭の動詞を語彙表から選ぶ

- 軸: C4
- 決定: すべてのステップに `name:` を書き、名前は ASCII の英語で、先頭の語を `Attest`・`Build`・`Check`・`Comment`・`Configure`・`Create`・`Delete`・`Deploy`・`Download`・`Generate`・`Install`・`Log`・`Publish`・`Push`・`Report`・`Run`・`Set`・`Sync`・`Update`・`Upload`・`Verify` のどれかにし、末尾に `.` を付けず、次の表のアクションには表の名前を付ける。
  | uses | name |
  |---|---|
  | `actions/checkout` | `Check out repository` |
  | `actions/setup-node` | `Set up Node.js` |
  | `actions/setup-python` | `Set up Python` |
  | `actions/setup-go` | `Set up Go` |
  | `actions/setup-java` | `Set up Java` |
  | `astral-sh/setup-uv` | `Set up uv` |
  | `actions/upload-artifact` | `Upload ` の後に成果物の名前 |
  | `actions/download-artifact` | `Download ` の後に成果物の名前 |
  | `./.github/actions/run-report` | `Report run timings` |
- 理由: ステップの名前は、Actions の画面と run-report の表にそのまま出る。名前が無いステップは `Run make test` のようにコマンドが名前になり、同じ処理の名前が作者ごとに変わる。
- 強制: structure — `rules_nam.py` の `nam04_steps`
- probe: NAM-04-a
- 良い例:
  ```yaml
  - name: Run unit tests
    run: make test
  ```
- 悪い例:
  ```yaml
  - run: make test
  - name: テストを実行する
  ```

### NAM-05 式を環境変数に渡すときは、コンテキストを除いた残りを大文字の snake_case にした名前にする

- 軸: C7
- 決定: `env:` の値が式1つ（`${{ <コンテキスト>.<残り> }}`）のとき、環境変数の名前は、先頭の `github.event.`・`github.`・`inputs.`・`matrix.`・`secrets.`・`vars.`・`env.`・`runner.`・`steps.<ID>.outputs.`・`needs.<ID>.outputs.` を除いた残りの `.` と `-` を `_` にして大文字にしたものにし、トークン（`github.token`、`secrets.GITHUB_TOKEN`、`inputs.github-token`）は `GH_TOKEN` にする。
- 理由: 同じ値に作者ごとに違う名前（`PR_NUMBER`、`NUMBER`、`PULL_NUMBER`）が付くと、スクリプトを写したときに名前が合わない。`gh` は `GH_TOKEN` を読む。
- 強制: structure — `rules_nam.py` の `nam05_env_names`
- probe: NAM-05-a
- 良い例:
  ```yaml
  env:
    PULL_REQUEST_NUMBER: ${{ github.event.pull_request.number }}
    GH_TOKEN: ${{ github.token }}
  ```
- 悪い例:
  ```yaml
  env:
    PR: ${{ github.event.pull_request.number }}
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
  ```

### NAM-06 runs-on には版を固定したランナーのラベルを書く

- 軸: X1
- 決定: `runs-on:` には、次の表のラベルか、それらだけを値に持つ matrix のキーの式（`${{ matrix.<キー> }}`）を書き、`-latest` のラベルと、ユーザーの指示の無いセルフホストランナーを書かない。
  | OS | ラベル |
  |---|---|
  | Linux（x64） | `ubuntu-24.04` |
  | Linux（arm64） | `ubuntu-24.04-arm` |
  | macOS | `macos-26` |
  | Windows | `windows-2025` |
- 理由: `-latest` は GitHub の都合で中身が変わる（2026-10〜11 は `ubuntu-latest` が実行ごとに 24.04 か 26.04 になる）。同じワークフローの結果が日によって変わらないよう、版を固定する。
- 出典: research.md の「ランナーイメージ」
- 強制: structure — `rules_nam.py` の `nam06_runners`
- probe: NAM-06-a
- 良い例:
  `runs-on: ubuntu-24.04`
- 悪い例:
  `runs-on: ubuntu-latest`

## CODE 書き方

### CODE-01 キーの順と YAML の形を固定する

- 軸: D1
- 決定: キーは次の表の順に書き、`if:` の値は `${{ }}` で囲み、`needs:` と `branches:`・`tags:`・`paths:` は1件でもブロックの列で書き、`env:`・`with:`・`permissions:` のキーと `needs:` の要素はアルファベット順にし、1行の `run:` は1行で書き、2行以上の `run:` は `|` のブロックで書く。
  | 場所 | キーの順 |
  |---|---|
  | ワークフロー | `name`、`run-name`、`on`、`permissions`、`concurrency`、`defaults`、`env`、`jobs` |
  | `on:` のイベント | `pull_request`、`merge_group`、`push`、`schedule`、`workflow_dispatch`、`workflow_call`、表に無いイベントをアルファベット順 |
  | ジョブ | `needs`、`if`、`uses`、`runs-on`、`timeout-minutes`、`environment`、`permissions`、`strategy`、`with`、`secrets`、`container`、`services`、`env`、`outputs`、`steps` |
  | ステップ | `name`、`id`、`if`、`uses`、`with`、`working-directory`、`shell`、`env`、`run` |
  | composite アクション | `name`、`description`、`inputs`、`outputs`、`runs` |
  | 入力の定義 | `description`、`required`、`type`、`default`、`options` |
  | 出力の定義 | `description`、`value` |
- 理由: 同じ内容でも、キーの順と列の書き方が作者ごとに違うと差分が大きくなり、レビューで中身の変更が埋もれる。`if:` を `${{ }}` で囲まないと、`!` で始まる式が YAML の構文になり、外に文字列が混ざると条件が常に真になる。
- 出典: research.md の「GitHub Actions」
- 強制: structure — `rules_code.py` の `code01_shape`
- probe: CODE-01-a、CODE-01-b
- 良い例:
  ```yaml
  - name: Run unit tests
    if: ${{ github.event_name == 'push' }}
    run: make test
  ```
- 悪い例:
  ```yaml
  - run: make test
    name: Run unit tests
    if: github.event_name == 'push'
  ```

### CODE-02 matrix には fail-fast: false を書き、値が2つ以上の軸だけを作る

- 軸: D4
- 決定: `strategy.matrix` を書くジョブには `strategy.fail-fast: false` を書き、matrix の各キーの値は2つ以上の列にし、`include` と `exclude` は組を足す・除くときだけに書く。
- 理由: `fail-fast` の既定は true で、1つの組が落ちると残りが止まり、どの組が落ちるかが分からなくなる。値が1つの matrix は、ジョブの名前に `(値)` が付くだけで意味が無い。
- 強制: structure — `rules_code.py` の `code02_matrix`
- probe: CODE-02-a
- 良い例:
  見本: `.github/workflows/reusable-check.yml` の `test` ジョブ
- 悪い例:
  ```yaml
  strategy:
    matrix:
      python-version:
        - "3.12"
  ```

### CODE-03 ファイルの1行目に目的を1文で書き、ほかのコメントは「なぜ」だけにする

- 軸: D7
- 決定: ワークフロー・composite アクション・`dependabot.yml` の1行目は次の表の形の日本語1文にし、成果には途中の手順・ジョブの一覧・呼び出し元・ファイル名を書かず、1行目はトリガーか成果が変わったときだけ書き直し、それ以外のコメントは、版のコメント（DEP-06）、時間の上限の理由（ASYNC-02）、コードから読めない理由のどれかに限る。
  | ファイル | 1行目 |
  |---|---|
  | `workflow_call` 以外のトリガーを持つワークフロー | `# <トリガー>で、<成果>` |
  | 再利用ワークフロー（`reusable-*.yml`） | `# 呼ばれると、<成果>` |
  | composite アクション、`dependabot.yml` | `# <成果>` |

  成果は、最後に何がどこに残るか（公開した物、PR のコメント）か、何を確かめるか（検査の合否）である。デプロイの前に検査のジョブを足しても、成果（公開する物と先）は変わらないので、1行目は変えない。
- 理由: ファイルの目的が書かれていないと、更新するときに意図を推測するしかない（破壊的更新の棚卸しでも、目的の行が意図の手がかりになる）。呼び出し元やジョブの一覧を1行目に書くと、ほかのファイルを変えるたびに古くなり、直すかどうかで作者が分かれる。何をしているかのコメントは、コードと食い違っても検査で気づけない。
- 強制: structure, review — `rules_code.py` の `code03_header`（1行目の有無、表の形、ファイル名）、レビュー用スキルの4節（成果だけか、ほかのコメントの中身）
- probe: CODE-03-a、CODE-03-b、CODE-03-c、CODE-03-d
- 良い例:
  `# プルリクエストと main への push で、キットの全検査の合否と、全ジョブ・全ステップの処理時間を PR に出す`
- 悪い例:
  ```yaml
  # キットの全検査を3つのジョブで並べて回す。ci.yml と release.yml から呼ぶ
  name: reusable-check
  # チェックアウトする
  ```

### CODE-04 ランタイムの版はリポジトリの版のファイルから読む

- 軸: D8
- 決定: setup のアクションの版は次の表で決める。
  | リポジトリの状態 | 書き方 |
  |---|---|
  | 版のファイル（`.nvmrc`、`.node-version`、`.python-version`、`go.mod`、`.java-version`）がある | `node-version-file:`・`python-version-file:`・`go-version-file:`・`java-version-file:` にそのファイルを書く |
  | uv を使う | `astral-sh/setup-uv` だけを使い、Python は uv に `.python-version` から入れさせる |
  | 複数の版で試す | matrix に版を引用付きで並べる（OPS-03） |
  | 上のどれでもない | `with:` に版を引用付きで書き、版のファイルを作るかを報告に書く |
- 理由: 版をワークフローと版のファイルの2か所に書くと、片方だけが更新されて手元と CI の版がずれる。
- 強制: review — レビュー用スキルの4節で、版のファイルの有無と `with:` を突き合わせる
- 機械化しない理由: どのファイルが版の正本かは、配布先のリポジトリの構成によって変わり、ワークフローの字面だけでは判定できないため
- probe: なし
- 良い例:
  ```yaml
  - name: Set up Node.js
    uses: actions/setup-node@<sha> # v7.1.0
    with:
      node-version-file: .nvmrc
  ```
- 悪い例:
  ```yaml
    with:
      node-version: "22"
  ```

## ERR エラーと入力検証

### ERR-01 シェルは bash を明示し、失敗を握りつぶさない

- 軸: E1
- 決定: ワークフローには `defaults.run.shell: bash` を書き、ワークフローのステップには `shell:` を書かず、composite アクションの `run` のステップには `shell: bash` を書き、`continue-on-error` をジョブにもステップにも書かず、`run:` に `|| true`・`|| :`・`set +e` を書かない。
- 理由: `shell` を省くと `bash -e` で動き、`-o pipefail` が付かないので、パイプの途中の失敗が成功に見える。`continue-on-error`、`|| true`、`set +e` を書くと、失敗したステップが成功として報告され、本当の原因が後のステップの失敗に隠れる。
- 出典: research.md の「GitHub Actions」
- 強制: structure — `rules_flow.py` の `err01_shell`（shell、`continue-on-error`、`run:` の `|| true`・`|| :`・`set +e`）
- probe: ERR-01-a、ERR-01-b、ERR-01-c
- 良い例:
  ```yaml
  defaults:
    run:
      shell: bash
  ```
- 悪い例:
  ```yaml
  - name: Run unit tests
    continue-on-error: true
    run: make test | tee test.log
  ```

### ERR-02 run と script には式を書かず、値はすべて env で渡す

- 軸: E2
- 決定: `run:` の本文と `actions/github-script` の `script:` には `${{` を書かず、使う値は同じステップの `env:` に式で入れて、本文では `"$NAME"` と引用付きで読む。
- 理由: 式は、シェルが解釈する前に文字列として埋め込まれる。PR の題名やブランチ名を埋め込むと、その中のコマンドが動く。信頼できる値かどうかの判断を作者に任せると判断が分かれるので、すべての値を env で渡す。
- 出典: research.md の「GitHub Actions」（Script injections）
- 強制: structure, lint — `rules_flow.py` の `err02_expressions`、actionlint の `[expression]`（potentially untrusted）と zizmor の `template-injection`
- probe: ERR-02-a、ERR-02-b
- 良い例:
  ```yaml
  - name: Run tests
    env:
      PYTHON_VERSION: ${{ matrix.python-version }}
    run: uv run --python "$PYTHON_VERSION" make test
  ```
- 悪い例:
  ```yaml
  - name: Run tests
    run: uv run --python ${{ matrix.python-version }} make test
  ```

## STATE 状態とデータの流れ

### STATE-01 データの受け渡しの方法を、渡す範囲で決める

- 軸: E3
- 決定: 値とファイルの受け渡しは次の表の方法で行い、`$GITHUB_ENV` には書かない。
  | 渡す範囲 | 方法 |
  |---|---|
  | 同じジョブのステップの間の値 | `echo "<名前>=<値>" >> "$GITHUB_OUTPUT"` と `steps.<ID>.outputs.<名前>` |
  | 同じジョブのステップの間のファイル | 作業ディレクトリのファイル |
  | ジョブの間の値 | ジョブの `outputs:` と `needs.<ジョブ>.outputs.<名前>` |
  | ジョブの間のファイル | `actions/upload-artifact` と `actions/download-artifact`（STATE-02） |
  | ステップの環境変数 | そのステップの `env:` |
  | 上のどれでもない | 実装せずに、新しいパターンの提案として報告する |
- 理由: `$GITHUB_ENV` に書いた値は、後のすべてのステップの環境に入り、どこで使われるかを追えない。危険なトリガーでは、その値で別のステップの動きを変えられる。
- 出典: research.md の「zizmor」（`github-env`）
- 強制: structure — `rules_flow.py` の `state01_env_file`
- probe: STATE-01-a
- 良い例:
  ```yaml
  - name: Generate version
    id: version
    run: echo "value=$(git describe --tags)" >> "$GITHUB_OUTPUT"
  ```
- 悪い例:
  `run: echo "VERSION=$(git describe --tags)" >> "$GITHUB_ENV"`

### STATE-02 キャッシュは setup のアクションの機能を使い、成果物には保存日数と空のときの扱いを書く

- 軸: X10
- 決定: 依存のキャッシュは次の表の setup のアクションの機能で行い、`actions/cache` は表のアクションで扱えないものだけに使い、`release.yml` と `deploy-<先>.yml` では `actions/cache` を使わずに表の右の列の書き方でキャッシュを切り、`actions/upload-artifact` には `retention-days` と `if-no-files-found: error` を書く。
  | アクション | キャッシュを使う書き方 | `release.yml`・`deploy-<先>.yml` での書き方 |
  |---|---|---|
  | `astral-sh/setup-uv` | 何も書かない（既定で有効） | `enable-cache: false` |
  | `actions/setup-go` | 何も書かない（既定で有効） | `cache: false` |
  | `actions/setup-node` | `cache: <npm・yarn・pnpm>` | `package-manager-cache: false` を書き、`cache` を書かない |
  | `actions/setup-python` | `cache: <pip・pipenv・poetry>` | `cache` を書かない |
- 理由: キャッシュのキーを手で組むと、作者ごとにキーが違い、無効化の条件も違う。リリースでキャッシュを読むと、PR で汚したキャッシュが成果物に入る。setup-uv・setup-go・setup-node は何も書かなくてもキャッシュを使うので、切るときは明示する。成果物の保存日数を書かないと既定の 90 日残り、空の成果物は警告だけで通る。
- 出典: research.md の「GitHub Actions」（キャッシュ）、「zizmor」（`cache-poisoning`）
- 強制: structure, lint — `rules_flow.py` の `state02_artifacts`、zizmor の `cache-poisoning`
- probe: STATE-02-a、STATE-02-b
- 良い例:
  ```yaml
  - name: Upload dist
    uses: actions/upload-artifact@<sha> # v7.0.2
    with:
      if-no-files-found: error
      name: dist
  ```
  （`retention-days: 1` も書く。見本: `.github/workflows/deploy-pages.yml`）
- 悪い例:
  ```yaml
  - uses: actions/upload-artifact@<sha> # v7.0.2
    with:
      name: dist
      path: dist
  ```

## ASYNC 非同期と並行

### ASYNC-01 concurrency はワークフローの種類ごとに決まった値を書く

- 軸: E4
- 決定: ワークフローの `concurrency:` を次の表の値にし、ジョブには `concurrency:` を書かない。
  | ワークフロー | `group` | `cancel-in-progress` |
  |---|---|---|
  | `ci.yml` | `${{ github.workflow }}-${{ github.event.pull_request.number \|\| github.ref }}` | `${{ github.event_name == 'pull_request' }}` |
  | `reusable-<名前>.yml` | 書かない（呼ぶ側の値に従う） | 書かない |
  | 上のどれでもない | `${{ github.workflow }}` | `false` |
- 理由: PR に push するたびに古い実行を止めないと、ランナーを無駄に使い、古い結果の報告が新しい結果を上書きする。リリースとデプロイは途中で止めると半端な状態が残るので、止めずに順番に並べる。
- 出典: research.md の「GitHub Actions」（concurrency）
- 強制: structure — `rules_flow.py` の `async01_concurrency`
- probe: ASYNC-01-a
- 良い例:
  ```yaml
  concurrency:
    group: ${{ github.workflow }}
    cancel-in-progress: false
  ```
- 悪い例:
  ```yaml
  concurrency:
    group: release-${{ github.ref }}
    cancel-in-progress: true
  ```

### ASYNC-02 runs-on を持つジョブには timeout-minutes を書き、値は10分にする

- 軸: E4
- 決定: `runs-on:` を持つすべてのジョブに `timeout-minutes:` を書き、値は report ジョブを `5`、それ以外を `10` にし、10 以外の値にするときは同じ行の末尾に `# <その長さが要る理由>` を書き、ステップには `timeout-minutes:` を書かない。
- 理由: 既定の上限は 360 分で、止まったジョブが6時間ランナーを使い続ける。値が作者ごとに違うと、どの値に根拠があるのか分からない。
- 出典: research.md の「GitHub Actions」（timeout-minutes）
- 強制: structure — `rules_flow.py` の `async02_timeout`
- probe: ASYNC-02-a
- 良い例:
  ```yaml
  runs-on: ubuntu-24.04
  timeout-minutes: 30 # E2E テストがブラウザを3つ起動するため
  ```
- 悪い例:
  ```yaml
  runs-on: ubuntu-24.04
  steps:
  ```

## OPS ログ・設定・セキュリティ・表示

### OPS-01 ci.yml の最後に report ジョブを置き、処理時間の報告と合否を任せる

- 軸: E5, X9
- 決定: `ci.yml` の最後のジョブを次の形の `report` にし、`ci.yml` 以外のワークフローには report ジョブを置かず、`./.github/actions/run-report` は `ci.yml` の report ジョブだけで使う。
  | キー | 値 |
  |---|---|
  | `if` | `${{ !cancelled() }}` |
  | `needs` | `ci.yml` の `report` 以外の全ジョブの ID（PROC-02） |
  | `runs-on` | `ubuntu-24.04` |
  | `timeout-minutes` | `5` |
  | `permissions` | `actions: read`、`contents: read`、`pull-requests: write` |
  | 1つ目のステップ | `actions/checkout`（`persist-credentials: false`、`sparse-checkout: .github/actions/run-report`） |
  | 2つ目のステップ | `./.github/actions/run-report`（`needs: ${{ toJSON(needs) }}`） |
- 理由: 全ジョブ・全ステップの所要時間は、全ジョブが終わった後に REST API から1回で取るのが確実である。報告と合否を1つのジョブにまとめると、ブランチ保護の必須チェックを `report` の1つにでき、ジョブを足しても保護の設定を変えずに済む。
- 出典: research.md の「GitHub REST API」
- 強制: structure — `rules_ops.py` の `ops01_report`
- probe: OPS-01-a
- 良い例:
  見本: `.github/workflows/ci.yml` の `report` ジョブ
- 悪い例:
  ```yaml
  report:
    if: ${{ always() }}
    needs:
      - lint
  ```

### OPS-02 secrets はそれを使うステップの env か with にだけ書き、クラウドは OIDC で認証する

- 軸: E6
- 決定: `secrets.<名前>` はそれを使うステップの `env:` か `with:` にだけ書き、ワークフローとジョブの `env:` には書かず、`secrets: inherit` を書かず、AWS・Google Cloud・Azure への認証は `id-token: write` と各社の公式アクションの OIDC で行い、長期の鍵を secrets に置かない。
- 理由: ワークフローやジョブの env に置いた secrets は、そのジョブの全ステップ（外部アクションを含む）から読める。`secrets: inherit` は呼ぶ先に全部の secrets を渡す。長期の鍵は漏れたときに失効させるまで使われ続ける。
- 出典: research.md の「GitHub Actions」（OIDC・secrets）
- 強制: structure, lint, review — `rules_ops.py` の `ops02_secrets`、zizmor の `secrets-inherit` と `overprovisioned-secrets`、レビュー用スキルの4節（OIDC を使えるのに鍵を使っていないか）
- probe: OPS-02-a、OPS-02-b
- 良い例:
  ```yaml
  - name: Publish package
    env:
      NPM_TOKEN: ${{ secrets.NPM_TOKEN }}
    run: npm publish
  ```
- 悪い例:
  ```yaml
  env:
    NPM_TOKEN: ${{ secrets.NPM_TOKEN }}
  jobs:
  ```

### OPS-03 版の数値は引用して文字列にする

- 軸: E7
- 決定: `with:` の `-version` で終わるキーの値と、matrix の値のうち数字と `.` だけでできたものは `"3.12"` のように二重引用符で囲む。
- 理由: YAML では引用しない `3.10` は数値の `3.1` になり、`20` は整数になる。版の指定が作者ごとに引用の有無で分かれると、`3.10` を指定したつもりで `3.1` が入る。
- 強制: structure — `rules_ops.py` の `ops03_versions`
- probe: OPS-03-a
- 良い例:
  ```yaml
  python-version:
    - "3.12"
    - "3.13"
  ```
- 悪い例:
  `python-version: 3.10`

### OPS-04 schedule には timezone を書き、分を0にしない

- 軸: E7
- 決定: `schedule:` の各要素には `cron:` と `timezone:`（IANA の名前。既定は `Asia/Tokyo`）を書き、cron の分は `1`〜`59` の数字1つにする。
- 理由: timezone を書かないと UTC で動き、作者ごとに時差の換算を間違える。毎時0分は GitHub の負荷が高く、実行が遅れたり破棄されたりする。
- 出典: research.md の「GitHub Actions」（schedule）
- 強制: structure — `rules_ops.py` の `ops04_schedule`
- probe: OPS-04-a
- 良い例:
  ```yaml
  schedule:
    - cron: 17 9 * * 1
      timezone: Asia/Tokyo
  ```
- 悪い例:
  `- cron: "0 0 * * 1"`

### OPS-05 zizmor の指摘を0件にし、checkout は資格情報を残さない

- 軸: E8
- 決定: ワークフロー・composite アクション・`dependabot.yml` を zizmor（`--offline`、persona は regular、設定は `.gha/zizmor.yml`）にかけて指摘を0件にし、`actions/checkout` には `persist-credentials: false` を書き、`pull_request_target` をトリガーに書かない。
- 理由: セキュリティの定型（資格情報の残り、危険なトリガー、権限、式の埋め込み）を作者の知識に任せると、知らない作者の書いたものに穴が残る。
- 出典: research.md の「zizmor」「GitHub Actions」（`pull_request_target`）
- 強制: lint — zizmor（`artipacked`、`dangerous-triggers` ほか、regular の全監査。`self-repository` だけは ADR 0006 で止める）
- probe: OPS-05-a
- 良い例:
  ```yaml
  - name: Check out repository
    uses: actions/checkout@<sha> # v7.0.1
    with:
      persist-credentials: false
  ```
- 悪い例:
  ```yaml
  - name: Check out repository
    uses: actions/checkout@<sha> # v7.0.1
  ```

### OPS-06 ワークフローの permissions は空にし、全ジョブに要る権限だけを書く

- 軸: X3
- 決定: ワークフローの先頭に `permissions: {}` を書き、`runs-on` を持つジョブと `uses` で再利用ワークフローを呼ぶジョブの両方に `permissions:` を書き、付ける権限を次の表で決め、何も要らないジョブには `permissions: {}` を書く。
  | ジョブがすること | 権限 |
  |---|---|
  | リポジトリを checkout する | `contents: read` |
  | 実行のジョブの情報を読む（report） | `actions: read` |
  | PR にコメントする（report） | `pull-requests: write` |
  | Release を作る・タグを push する | `contents: write` |
  | OIDC でクラウドに認証する | `id-token: write` |
  | 成果物の来歴を証明する | `attestations: write`、`id-token: write` |
  | GitHub Pages にデプロイする | `pages: write`、`id-token: write` |
  | GitHub Packages（GHCR）に push する | `packages: write` |
  | code scanning に結果を上げる | `security-events: write` |
  | Issue を作る・変える | `issues: write` |
  | 上のどれでもない | 呼ぶ REST API の文書の「Fine-grained access tokens」の節に書かれた権限 |
- 理由: `permissions` を書かないと、リポジトリの既定（書き込みを含むことがある）がそのまま付く。ワークフローに書いた権限は全ジョブに付くので、ジョブごとに書く。
- 出典: research.md の「GitHub Actions」（permissions）
- 強制: structure, lint, review — `rules_ops.py` の `ops06_permissions`（空のワークフローの権限、全ジョブの permissions、キーの値）、zizmor の `excessive-permissions`、レビュー用スキルの4節（表に照らして余分な権限が無いか）
- probe: OPS-06-a、OPS-06-b
- 良い例:
  ```yaml
  permissions: {}
  jobs:
    lint:
      permissions:
        contents: read
  ```
- 悪い例:
  ```yaml
  permissions:
    contents: write
    pull-requests: write
  ```

## TEST テスト

### TEST-01 ワークフローの正しさは gha check で確かめ、GitHub 上で動かしていないことを報告する

- 軸: F1
- 決定: ワークフローと composite アクションは `gha check` の actionlint と shellcheck（設定は `.gha/actionlint.yaml`）で指摘を0件にし、GitHub 上で実行して確かめていないものは報告に「GitHub 上では未実行」と書く。
- 理由: ワークフローは手元で実行できず、式の型の誤り、存在しない入力、シェルの誤りは、push して初めて落ちる。静的な検査で落とせるものを先に落とし、確かめていないことを確かめたと言わない。
- 出典: research.md の「actionlint」「shellcheck」
- 強制: lint, doc — actionlint と shellcheck（`gha check`。ワークフローの run と `.github/scripts/*.sh`）。報告の書き方は実装用スキルの7節
- probe: TEST-01-a、TEST-01-b
- 良い例:
  ```bash
  uv run --locked --script .gha/gha.py check
  ```
- 悪い例:
  検査を回さずに「ワークフローを作成しました。動作します」と報告する

## PROC 作業手順

### PROC-01 ワークフローは決まった順で作る

- 軸: G1
- 決定: 作成と破壊的更新では、次の順で作る。
  | 順 | すること |
  |---|---|
  | 1 | 依頼から、目的・トリガー・ジョブ・使う secrets を表にする（実装用スキルの2節の値を決める） |
  | 2 | STR-02 の表でファイル名と `on:` を決める |
  | 3 | 見本のファイルを写し、`permissions`・`concurrency`・`defaults` を書く |
  | 4 | ジョブとステップを書く |
  | 5 | `ci.yml` なら report ジョブの `needs` を更新する（PROC-02） |
  | 6 | 外部アクションの SHA を `gha pin` で得て書く |
  | 7 | `gha check` を通す |
- 理由: 順が作者ごとに違うと、途中の形（SHA を後から入れる、権限を最後に足す）が違い、足し忘れが起きる。
- 強制: doc — 実装用スキルの4節
- 機械化しない理由: 作業の順は結果の差分に残らないため
- probe: なし
- 良い例:
  実装用スキルの4節の順に作り、報告の2に順に並べる
- 悪い例:
  ステップを書いてから permissions を最後に足す

### PROC-02 一緒に変えるファイルの組を同じ変更で変える

- 軸: G2, X5
- 決定: 次の表の左の変更をしたら、右も同じ変更で変える。composite アクションと再利用ワークフローの入力を足すときは `required: false` と `default` を付けて足し、入力の名前を変える・消すときは呼んでいる全ファイルを同じ変更で直す。
  | 変更 | 一緒に変えるもの |
  |---|---|
  | `ci.yml` のジョブを足す・消す・名前を変える | report ジョブの `needs` |
  | 外部アクションを新しく使う | `.gha/zizmor.yml` の許可表（ユーザーの承認が要る。DEP-04） |
  | composite アクション・再利用ワークフローの入力を変える | それを呼ぶ全ワークフローの `with:` |
  | 再利用ワークフローの出力を変える | それを読む `needs.<ジョブ>.outputs` |
  | 新しい secrets を使う | 報告の「ユーザーが設定すること」 |
  | 新しい environment を使う | 報告の「ユーザーが設定すること」（保護の規則） |
- 理由: 片側だけを変えると、report ジョブが終わっていないジョブを待たずに動いたり、呼ぶ側が存在しない入力を渡したりする。
- 強制: structure, lint, review — `rules_ops.py` の `ops01_report`（report の `needs`）、actionlint の `workflow-call` と `job-needs`、レビュー用スキルの5節（secrets と environment）
- probe: PROC-02-a、PROC-02-b
- 良い例:
  `test-e2e` ジョブを足し、同じ変更で report の `needs` に `test-e2e` を足す
- 悪い例:
  ジョブを足したが report の `needs` は `- lint` のまま

### PROC-03 アクションの更新は Dependabot に任せ、手で上げるときは gha pin を使う

- 軸: G3
- 決定: `.github/dependabot.yml` に `package-ecosystem: github-actions` の項目を置き、`directories` に `/` と `/.github/actions/*`、`schedule.interval` に `weekly`、`cooldown.default-days` に `7`、`groups` に全部を1つにまとめるグループを書き、手で版を上げるときは `gha pin <owner/repo>` の出力で `uses:` の行を置き換える。
- 理由: SHA で固定しただけでは古い版に留まり続ける。更新の頻度と待つ日数を決めないと、出たばかりの版（乗っ取られた版を含む）がすぐに入る。
- 出典: research.md の「Dependabot（github-actions）」「zizmor」（`dependabot-cooldown`）
- 強制: structure, lint — `rules_ops.py` の `proc03_dependabot`、zizmor の `dependabot-cooldown`
- probe: PROC-03-a、PROC-03-b
- 良い例:
  見本: `.github/dependabot.yml`
- 悪い例:
  ```yaml
  - package-ecosystem: github-actions
    directory: /
    schedule:
      interval: daily
  ```

### PROC-04 ルールは決まった順で変える

- 軸: G4
- 決定: ルールを変えるときは、ユーザーの承認を得てから、ADR → `docs/design/rules.md` → 検査の設定と `.foundation/probes.json` → 参照実装 → `make docs` の順に変え、`rules_check.py` と `violation_probe.py` を通す。
- 理由: 順を飛ばすと、ルールと検査と見本が食い違い、作者がどれに従うかで揺れる。
- 強制: doc — AGENTS.md の「ルールを変えたいとき」
- 機械化しない理由: 変更の順と承認の有無は差分に残らないため
- probe: なし
- 良い例:
  ADR を書いてから rules.md を変える
- 悪い例:
  検査が通らないので `.gha/zizmor.yml` だけを変える

### PROC-05 完了の条件はモードごとの検査で決める

- 軸: G5
- 決定: 次の表の検査が通ったときだけ完了と報告する。
  | 状況 | 通す検査 |
  |---|---|
  | 作成・破壊的更新 | `gha check`（指摘0件） |
  | 保守的更新 | `gha check --ratchet HEAD`（基準の版より指摘が増えていない） |
  | 外部アクションの参照を足した・変えた | 上に加えて `gha pin --verify` |
  | このキットを開発した | `make check` |
- 理由: 完了の基準が作者ごとに違うと、検査を回さずに終える作者が出る。保守的更新で既存の指摘まで0件を求めると、頼まれていない所を書き換えることになる。
- 強制: doc — 実装用スキルの5節と7節
- 機械化しない理由: どの検査を回したかは差分に残らないため（結果は報告に貼らせる）
- probe: なし
- 良い例:
  報告の4に `gha check: 指摘 0 件` を貼る
- 悪い例:
  検査の結果を貼らずに「問題ありません」と書く

### PROC-06 既存のワークフローを変えるときは、保守的更新か破壊的更新かをユーザーに選んでもらう

- 軸: X8
- 決定: モードを次の表で決め、既存のワークフローを変える依頼で依頼文にモードの指定が無いときはユーザーに選んでもらい、聞けない状況では保守的更新にして報告に書く。
  | 状況 | モード |
  |---|---|
  | 対象のワークフローがまだ無い | 作成 |
  | 既存を変える依頼で、「今の書き方は変えずに」「最小限で」「この部分だけ」と指定がある | 保守的更新 |
  | 既存を変える依頼で、「作り直して」「全面的に」「ベストな書き方で」と指定がある | 破壊的更新 |
  | 既存を変える依頼で、指定が無い | ユーザーに選んでもらう。聞けないなら保守的更新 |
- 理由: 保守的更新と破壊的更新では、変えてよい範囲がまるで違う。作者が推測で選ぶと、頼んでいない書き換えか、頼んだ改善の不足のどちらかが起きる。
- 強制: doc — 実装用スキルの1節と2節
- 機械化しない理由: モードはユーザーの意思で決まり、ファイルからは判定できないため
- probe: なし
- 良い例:
  「既存の書き方を残す保守的更新と、ルールどおりに書き直す破壊的更新のどちらにしますか」と聞く
- 悪い例:
  指定の無い依頼で、ファイル全体をルールどおりに書き直す

### PROC-07 保守的更新では頼まれた所だけを変え、指摘を増やさない

- 軸: X8
- 決定: 保守的更新では、依頼に必要な行だけを足し・変え、それ以外の行は ID・名前・キーの順・コメント・引用の書き方のどれも1文字も変えず、足した行・変えた行はルールどおりに書き、`gha check --ratchet HEAD` で指摘を増やさず、既存の行の違反は直さずに報告の「提案」に書く。
- 理由: 既存の書き方と意図を残すと頼まれたのに書き換えると、レビューの差分が大きくなり、気づかないうちに動きが変わる。足す行をルールどおりにすれば、ファイルが少しずつルールに近づく。
- 強制: review — レビュー用スキルの5節で、差分が依頼の範囲に収まっているかを見る
- 機械化しない理由: どの行が依頼に必要かは、依頼の意味から判断する必要があるため（指摘の増減は `gha check --ratchet` が機械で見る）
- probe: なし
- 良い例:
  依頼された `test` ジョブだけを足し、既存の `build` ジョブの `actions/checkout@v4` は提案として報告する
- 悪い例:
  ジョブを1つ足す依頼で、既存の全ステップに `name:` を足す

### PROC-08 破壊的更新では、していることを棚卸しして確かめてから書き直す

- 軸: X8
- 決定: 破壊的更新では、`gha intent <パス>` の棚卸しの表の「意図」の列を埋めてユーザーに確かめ、ルールどおりに書き直し、`gha intent <パス> --compare-ref HEAD`（ファイル名を変えたときは `--from <古いパス>` を足す）に出た事実を1件ずつ「移した先」か「落とした理由」で報告の対応表に書き、`gha check` の指摘を0件にする。
- 理由: 書き直すと、既存のワークフローがしていたこと（secrets の利用、成果物、通知）が黙って消えやすい。機械で棚卸しした事実を1件ずつ確かめると、何を残し何を落としたかを作者ごとに同じ粒度で示せる。
- 強制: review, doc — レビュー用スキルの5節（対応表と `--compare-ref` の出力の突き合わせ）、実装用スキルの4節（手順）
- 機械化しない理由: 事実が新しいファイルのどこに移ったか、落としてよいかは、意図の判断が要るため
- probe: なし
- 良い例:
  対応表に「`secrets.DEPLOY_TOKEN` → OIDC（`id-token: write`）に置き換えたので落とした」と書く
- 悪い例:
  棚卸しをせずに書き直し、古いワークフローの Slack 通知が消えた

## TOOL 道具と自動化

### TOOL-01 YAML の整形は yamllint の設定で縛り、formatter は使わない

- 軸: H1
- 決定: `.github/` の YAML は `.gha/yamllint.yml`（2字下げ、列も字下げ、空でない `{}` と `[]` の禁止、必要なときだけ二重引用符、120 字まで、真偽値は `true` と `false`）で指摘を0件にし、YAML の formatter を足さない。
- 理由: YAML の formatter はコメントと引用を崩すものが多く、足すと作者ごとに使うものが分かれる。lint の設定で形を1つに決めれば、手で直すだけで同じ形になる。
- 出典: research.md の「yamllint」
- 強制: lint — yamllint（`gha check`）
- probe: TOOL-01-a
- 良い例:
  ```yaml
  branches:
    - main
  ```
- 悪い例:
  `branches: [main]`

### TOOL-02 検査は編集の直後と完了の前に回す

- 軸: H2
- 決定: このキットでは編集の直後に hooks が `make fix-file` を回し、完了の前に `make check` を回し、配布先ではワークフローを保存するたびに `gha check <パス>` を回し、完了の前に PROC-05 の検査を回す。
- 理由: 検査を最後にまとめて回すと、どの編集で壊れたかが分からず、直す範囲が広がる。
- 強制: doc — 実装用スキルの4節と5節、`.claude/settings.json` の hooks
- 機械化しない理由: いつ検査を回したかは差分に残らないため
- probe: なし
- 良い例:
  ワークフローを書くたびに `gha check .github/workflows/ci.yml` を回す
- 悪い例:
  全ファイルを書き終えてから初めて検査を回す

### TOOL-03 抑止コメントで検査を黙らせない

- 軸: H3
- 決定: `# zizmor: ignore`、`# yamllint disable`、`# shellcheck disable`、`# noqa`、`# ruff:`、`# type: ignore`、`# mypy:`、`# pragma: no cover`、`# fmt: off`、`# fmt: skip`、テストの skip（`unittest.skip`、`skipTest(`）を書かない。
- 理由: 抑止コメントで検査を通せるなら、そのルールは無いのと同じである。抑止が要るほどの例外は、ルールの変更（PROC-04）として扱う。
- 強制: structure — `rules_ops.py` の `tool03_suppressions`（配布先の `.github/` を含む）と `.foundation/bin/guard.py`（このキットの Python）
- probe: TOOL-03-a、TOOL-03-b
- 良い例:
  指摘の原因を直す（`"$FOO"` と引用する）
- 悪い例:
  `# shellcheck disable=SC2086`

### TOOL-04 検査の設定と保護ファイルを、検査を通すために変えない

- 軸: H3
- 決定: `.foundation/manifest.json` の `protected` に列挙したファイル（配布先では `.gha/` の全ファイル）は、ユーザーの承認なしに変えない。
- 理由: 設定を緩めれば、どの検査も通る。
- 強制: review — レビュー用スキルの3節で、差分に保護ファイルがあるかを見る
- 機械化しない理由: hooks はエージェントの編集にだけ確認を求め、人の編集は止められないため、差分のレビューで確かめる
- probe: なし
- 良い例:
  許可表に無いアクションが要るとき、`.gha/zizmor.yml` を変えずにユーザーに承認を求める
- 悪い例:
  `forbidden-uses` の `allow` に `*/*` を足す

### TOOL-05 検査の道具の版はスクリプトの依存とロックファイルで固定する

- 軸: H4
- 決定: 検査の道具（actionlint、shellcheck、zizmor、yamllint、PyYAML）の版は `.gha/gha.py` の先頭の依存の宣言と `.gha/gha.py.lock` で固定し、`uv run --locked --script .gha/gha.py` で起動し、キットの開発の道具の版は `pyproject.toml` と `uv.lock`、Python の版は `.python-version` で固定する。
- 理由: 道具の版が作者ごとに違うと、同じワークフローへの指摘が変わる。
- 出典: research.md の「uv 0.13.4、CPython 3.12」
- 強制: structure — `uv run --locked`（ロックファイルと宣言が食い違うと起動しない）
- probe: TOOL-05-a
- 良い例:
  `uv run --locked --script .gha/gha.py check`
- 悪い例:
  `uvx zizmor .github/`

## 対象外とした軸

| 軸 | 理由 |
|---|---|
| C5 | YAML の値には型を名前で表す慣習が無く、入力の型は `type:` で明示する（DEP-02）。キットの Python の名前は ruff の命名規則（KIT-03）で縛る |
| D5 | 対象外（宣言的に書くため。ワークフローで状態を書き換えるのは `$GITHUB_OUTPUT` だけで、STATE-01 で扱う） |
