# github-actions-kit のアーキテクチャ

この文書は、構造そのものと、その構造を選んだ理由を説明する。個々のルールの全文は [rules.md](rules.md) にある。

## 1. 前提

この基盤は2つのものでできている。1つは、GitHub Actions のワークフローを書く・直すための**ルールと見本**（`docs/design/rules.md` の STR〜TOOL 節、`.github/` の参照実装、実装用スキル `gha-workflow`）。もう1つは、そのルールを機械で確かめる**道具**（検査の CLI `gha`、処理時間を報告する composite アクション `run-report`、配布用の `install.py`）である。

よく起きる変更は、頻度の高い順に次の4つである。

1. 配布先のリポジトリで、ワークフローを新しく書く・ジョブを足す・既存を直す（作業の大半）
2. 外部アクションの版を上げる（Dependabot が週に1回 PR を出す）
3. ルールを足す・変える（検査の関数、probe、文書を一緒に変える）
4. 検査の道具の版を上げる（actionlint、zizmor などの新しい版）

触るのは、配布先の開発者とエージェント（1）、このキットの保守者（2〜4）である。1 の作者は `.github/` だけを触り、`.gha/` には触らない。この分け方が構造の芯になる。

公式の推奨で構造に響くのは次の3点である（出典は [research.md](research.md)）。

- ワークフローは `.github/workflows/` の直下にしか置けない。サブディレクトリは実行されない
- 同じリポジトリの composite アクションは `.github/actions/<名前>/action.yml` に置くのが慣例で、`uses: ./.github/actions/<名前>` で呼ぶ
- ジョブの所要時間を PR に出す仕組みは公式に無い。REST API から取るしかない

## 2. ディレクトリ構造

```text
github-actions-kit/
├── .github/                         参照実装。このキット自身の CI であり、配布先が真似る見本（STR-01）
│   ├── workflows/
│   │   ├── ci.yml                   PR の検証と、処理時間の報告と合否（STR-02、OPS-01）
│   │   ├── reusable-check.yml       キットの全検査。2か所以上から呼ぶ検査のジョブ（STR-03）
│   │   ├── release.yml              タグからのリリース（STR-05、DEP-04）
│   │   ├── deploy-pages.yml         GitHub Pages へのデプロイ（STR-05、OPS-06）
│   │   └── security-audit.yml       定期の監査（OPS-04）
│   ├── actions/
│   │   ├── setup-kit/action.yml     uv と開発の依存を入れる composite（STR-03）
│   │   └── run-report/              処理時間の報告と合否の composite（配布する。OPS-01）
│   │       ├── action.yml
│   │       └── run_report.py        標準ライブラリだけで REST API を呼ぶ（KIT-02）
│   └── dependabot.yml               github-actions を週に1回（PROC-03）
├── .gha/                            検査の道具と設定（配布する。STR-01、TOOL-05）
│   ├── gha.py                       PEP 723 の入口。道具の版を宣言する
│   ├── gha.py.lock                  道具の版のロック
│   ├── gha_kit/                     CLI の本体（3章の表のモジュール。KIT-01）
│   ├── actionlint.yaml              セルフホストランナーのラベル（空）
│   ├── yamllint.yml                 YAML の形（TOOL-01）
│   └── zizmor.yml                   許可するアクションの表、SHA の固定の方針（DEP-04、DEP-06）
├── .claude/
│   ├── settings.json                hooks（編集後の検査、保護ファイルの確認）
│   └── skills/
│       ├── gha-workflow/            実装用スキル（配布する）
│       │   ├── SKILL.md
│       │   └── references/
│       │       ├── rules.md         生成物：rules.md の STR〜TOOL 節（KIT-06）
│       │       ├── patterns.md      依頼の種類ごとの書き方
│       │       └── examples/        生成物：.github/ の参照実装の写し（KIT-06）
│       └── gha-review/SKILL.md      レビュー用スキル（配布する）
├── scripts/
│   ├── structure_check.py           KIT 節の構造の検査（KIT-01、KIT-02、KIT-05、KIT-06）
│   └── gen_docs.py                  スキルの references/ を作る（KIT-06）
├── tests/                           キットの unittest（KIT-05）
│   ├── support.py                   偽物（REST API）とデータの組み立て
│   ├── fixtures/<題材>/              テストの YAML
│   └── test_<モジュール名>.py
├── install.py                       配布先に .gha/・run-report・dependabot.yml・スキルを写す
├── docs/design/                     設計の文書
├── .foundation/                     基盤の検査スクリプト、probe、収束テスト
├── Makefile                         make check（全検査）、make fix、make docs
├── pyproject.toml, uv.lock          キットの開発の道具の版（TOOL-05）
└── .python-version                  3.12
```

配布するのは `.gha/`、`.github/actions/run-report/`、`.github/dependabot.yml`、`.claude/skills/gha-workflow/`、`.claude/skills/gha-review/` の5つで、`install.py` が写す（[ADR 0003](adr/0003-two-distributed-skills.md)）。`dependabot.yml` は既にあれば残す。写すのは、run-report があるだけで PROC-03 が `dependabot.yml` を求め、導入した直後の `gha check` が落ちるからである。`.github/workflows/` は写さない。配布先のワークフローは配布先の作者が書くものであり、キットは見本をスキルの `references/examples/` に入れて渡す。

`.gha/` を `.github/` の外に置いたのは、`.github/` を「配布先の作者が書くもの」だけにするためである。検査の道具が `.github/` にあると、作者が設定を自分の書いたものと同じように触ってしまう。

## 3. 依存の許可表

### 3.1 gha_kit のモジュール

`.gha/gha_kit/` のモジュールは、次の表の「import してよいもの」に挙げたモジュールだけを import する。表に無い組は全部禁止で、`scripts/structure_check.py` の `check_imports` が強制する（KIT-02）。標準ライブラリは、`subprocess` を `proc.py` だけに、`urllib` と `http` をどこにも許さず、それ以外は自由に使ってよい。

| モジュール | 役割 | import してよい gha_kit のモジュール | 外部の依存 |
|---|---|---|---|
| `errors` | 例外の型（`UsageError`、`ToolError`） | なし | なし |
| `layout` | 置き場のパスの文字列 | なし | なし |
| `findings` | 指摘の型と出力の形 | なし | なし |
| `rulemap` | 外部ツールの規則名 → ルールID | なし | なし |
| `proc` | 外部コマンドの起動（唯一の場所） | `errors` | なし |
| `yamlnode` | YAML を行番号付きの木にする | なし | PyYAML |
| `targets` | 検査の対象のファイルを集める | `layout` | なし |
| `pins` | タグの一覧から SHA を解決・検証する | なし | なし |
| `gitref` | 基準の版のファイルを読む | `errors`、`proc` | なし |
| `walk` | 木を辿る補助（ジョブ、ステップ、権限） | `findings`、`layout`、`targets`、`yamlnode` | なし |
| `intent` | ワークフローの棚卸しと突き合わせ | `yamlnode` | なし |
| `tools` | yamllint・actionlint・shellcheck・zizmor の起動と出力の読み取り | `errors`、`findings`、`layout`、`proc`、`rulemap` | なし |
| `rules_str`・`rules_dep`・`rules_nam`・`rules_code`・`rules_flow`・`rules_ops` | 節ごとの構造の検査 | `findings`、`layout`、`walk`、`yamlnode` | なし |
| `policy` | 構造の検査の表（`RULES`）を回す | `findings`、`targets`、`walk`、`yamlnode`、`rules_*` | なし |
| `checks` | 構造の検査と外部ツールをまとめる | `findings`、`policy`、`proc`、`targets`、`tools`、`yamlnode` | なし |
| `ratchet` | 基準の版と指摘の件数を比べる | `checks`、`findings`、`gitref`、`layout`、`proc` | なし |
| `cli` | 引数の解釈と出力 | `checks`、`errors`、`findings`、`gitref`、`intent`、`pins`、`proc`、`ratchet`、`targets`、`yamlnode` | なし |

この表は上の行ほど下の層にあり、どの行も自分より上の行だけを import する。循環が起きないのはこの並びのためである。

`rules_*` 同士は import しない。1つのルールの検査は1つの `rules_<節>.py` の1つの関数に閉じ、共通の辿り方は `walk` に置く。こうすると、ルールを足すときに触るのは1つの `rules_<節>.py` と `policy.py` の表だけになる。

### 3.2 キットのほかの Python

| ファイル | import してよいもの |
|---|---|
| `.gha/gha.py` | `gha_kit.cli` だけ |
| `.github/actions/run-report/run_report.py` | 標準ライブラリだけ（ランナーの python3 で、依存を入れずに動かすため） |
| `install.py` | 標準ライブラリだけ（配布先の python3 で、依存を入れずに動かすため） |
| `scripts/*.py` | 標準ライブラリだけ |

### 3.3 ワークフローの呼び出し

ワークフローの側の依存の向きは DEP-01 の表で縛る。要約すると、ジョブ → 再利用ワークフロー → composite アクション → 外部アクションの一方向で、同じ段を入れ子にしない。

## 4. 公開面

| 対象 | 外から使ってよいもの | 触れなくする仕組み |
|---|---|---|
| 検査の CLI | `uv run --locked --script .gha/gha.py` の `check`・`pin`・`intent` と、その出力の形（KIT-04） | `gha_kit` のモジュールは配布先の作者が import しない前提で、`.gha/` を保護ファイルにする（TOOL-04） |
| run-report | `action.yml` の入力 `needs` と `github-token` | `run_report.py` の関数は action.yml からだけ呼ぶ。入力を変えるときは PROC-02 の互換性の決まりに従う |
| setup-kit | `action.yml` の入力 `enable-cache` と `python-version` | このキットの中だけで使う（配布しない） |
| reusable-check | `workflow_call` の入力 `enable-cache` | `.github/workflows/` のワークフローのジョブだけが呼ぶ（DEP-01） |
| スキル | `gha-workflow` と `gha-review` の SKILL.md、`references/` | `references/rules.md` と `references/examples/` は生成物で、手で変えない（KIT-06） |
| install.py | `python3 install.py <配布先のパス>` | なし（1ファイルの CLI） |

## 5. データの流れ

### 5.1 gha check

1. `cli.main` が引数を読み、`checks.run` を呼ぶ
2. `targets.discover` が `.github/` の下のワークフロー・composite アクション・`dependabot.yml`・スクリプトを集め、`targets.select` が指定のパスに絞る
3. `yamlnode.load` が全部の YAML を行番号付きの木にする。構造の検査はファイルをまたいで見る（report の `needs` と ci のジョブなど）ので、絞る前の全ファイルを読む
4. `policy.check` が `RULES` の表の検査関数を順に回す。各関数は `walk` で木を辿り、`Finding` を返す。指定のファイルの指摘だけを残す
5. `tools` が yamllint・actionlint（shellcheck を含む）・shellcheck（スクリプト）・zizmor を `proc.run` で起動し、出力を `Finding` に変える。ルールIDは `rulemap` で付ける
6. 全部を並べ、重複を除いて返す。`cli` が1行ずつ出し、件数の行を出し、終了コードを返す

### 5.2 gha check --ratchet と gha intent

`--ratchet <版>` は、`gitref` で基準の版の `.github/` を一時ディレクトリに写し、今の `.gha/` を写して同じ検査を回す。(パス, ルールID) ごとの件数を比べ、増えた組だけを返す。保守的更新で「既存の違反は残してよいが増やさない」を機械で見るための仕組みである（PROC-07）。

`intent <パス>` は、ワークフローがしている事実（トリガー、入力、権限、secrets、ジョブ、使うアクション、成果物など12種類）を表にする。`--compare-ref <版>` を付けると、基準の版にあって今の版に無い事実を出す。作り直しでファイル名が変わったときは `--from <古いパス>` で基準の側のパスを指定する。破壊的更新で、黙って消えたものを拾うための仕組みである（PROC-08）。

### 5.3 run-report（CI の実行時）

1. `ci.yml` の report ジョブが、全ジョブの終了後に `./.github/actions/run-report` を `needs: ${{ toJSON(needs) }}` で呼ぶ
2. `run_report.py` が `GET /repos/{o}/{r}/actions/runs/{id}/attempts/{n}/jobs` を全ページ取り、終わったジョブとステップの開始・終了の時刻から、待ち時間と所要時間を出す
3. 判定、ジョブの表、遅いステップの上位5件、mermaid のガントチャート、ジョブごとのステップの内訳を Markdown にする
4. ジョブサマリーに書き、PR なら `<!-- run-report:<ワークフロー名> -->` で始まるコメントを作るか更新する。フォークの PR で書けないときは通知だけにする
5. `needs` に失敗か取り消しのジョブがあれば、エラーを出して失敗で終わる。ブランチ保護の必須チェックは report の1つにする

## 6. 変更シナリオ表

| 変更 | 触るファイル | 触らないもの |
|---|---|---|
| 配布先でワークフローを足す | `.github/workflows/<名前>.yml`（`ci.yml` に足すなら report の `needs` も） | `.gha/`、run-report |
| 配布先で既存のワークフローを直す（保守的更新） | 対象のワークフローの、依頼に要る行だけ | ほかの行、ほかのファイル |
| 外部アクションの版を上げる | Dependabot の PR が `uses:` の行を変える。その後 `make docs` で `references/examples/` を作り直す | rules.md、`.gha/` |
| 許可するアクションを足す | `.gha/zizmor.yml` の `allow`（承認が要る） | ワークフロー以外のキットのファイル |
| 構造の検査のルールを足す | ADR、rules.md、`rules_<節>.py` の関数1つ、`policy.py` の `RULES`、`.foundation/probes.json` | `checks`、`cli`、`tools`、ほかの `rules_*` |
| 外部ツールの規則にルールIDを割り当てる | `rulemap.py` の `RULES`、rules.md、probes.json | `tools`、`policy` |
| 検査の道具の版を上げる | `.gha/gha.py` の依存、`uv lock --script .gha/gha.py`、research.md、manifest の `tools` | `gha_kit` のコード（出力の形が変わらない限り） |
| PyYAML の版を上げる | `.gha/gha.py`、`pyproject.toml`、`uv.lock`、`.gha/gha.py.lock`（KIT-06 が版の一致を見る） | `gha_kit` のコード |
| 置き場の名前を変える | `layout.py`、rules.md の STR-01、参照実装 | `rules_*`（`layout` の定数を使うので変わらない） |
| run-report の表示を変える | `run_report.py`、`tests/test_run_report.py` | `action.yml`（入力が変わらない限り）、ワークフロー |
| CLI にサブコマンドを足す | `cli.py`、`tests/test_cli.py`、実装用スキル | `checks`、`rules_*` |
| 配布するファイルを足す | `install.py`、`tests/test_install.py`、この文書の2章 | 配布しないファイル |
| キットの参照実装（`.github/`）のジョブやステップを変える | 対象のファイル。その後 `make docs` で `references/examples/` を作り直す | `docs/design/`（2章と4章はファイルの役割だけを書き、ジョブ・呼び出し元を列挙しないので、変えない。KIT-06） |
