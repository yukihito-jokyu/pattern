# orch-forge-kit のアーキテクチャ

この文書は、構造そのものと、その構造を選んだ理由を説明する。個々のルールの全文は [rules.md](rules.md) にある。

## 1. 前提

orch-forge-kit は、任意のリポジトリに、開発用のオーケストレーションスキル（以下、対象スキル）を作り、良くしていくための道具である。対象スキルとは、メインのセッションで動き、Agent ツールで役ごとのサブエージェントを起動して、実装・確認・報告を進めるスキルを指す。対象スキルを作り、良くする作業は、次の4つの性質を持つ。

1. **「良い」の中身はリポジトリごとに違う**。だから、ゴールと指標は人と一緒に決め、`charter.json` に固定してから作り、評価する。決める対話は、Claude Code のメインのセッションで動くスキル（forge-goals）が受け持つ。サブエージェントは人に質問できないからである（[research.md](research.md) の「Claude Code のサブエージェント」）
2. **オーケストレーションスキルは、サブエージェントの中からは評価できない**。対象スキルは自分で Agent ツールを使ってサブエージェントを起動するので、評価の実行役もメインのセッションと同じ条件で動く必要がある。そこで、補助 CLI が評価用のコピーの中で `claude -p` を起動し、実行の記録（stream-json）から、起動したサブエージェント・編集した主体・費用・時間を測る（[ADR 0002](adr/0002-roles-and-claude-p-executor.md)、[ADR 0009](adr/0009-measure-from-documented-stream-fields.md)）
3. **作る・測る・直すの段は多く、順番を間違えやすい**。どの段にいて次に何をするかを、エージェントの判断ではなく、ファイルの有無から補助 CLI が決める。スキル（forge-build、forge-run）は補助 CLI の `status` の指示に従うだけにする
4. **生成するスキルの形は固定する**。形が自由だと、構築役と分析役が作者ごとに違う形のスキルを書き、評価の前提（採点役が手順を読めること、サブエージェントの名前で起動を数えること）が崩れる。形の決まりは `bundle.RULES` の表に置き、検査と文書を同じ表から作る（STR-06、[ADR 0008](adr/0008-fixed-bundle-shape.md)）

この基盤でよく起きる変更は、指標を足す、バンドルの決まりを足す、プロンプトの文言を直す、スキルの手順を直す、段を足す、の5つである。どれも触るファイルが予測できるように、補助 CLI を「段のモジュール」と「共有のモジュール」に分け、段どうしの依存を禁じた。

## 2. ディレクトリ構造

```text
orch-forge-kit/
├── kit/                           配布物の正本。install.py が対象のリポジトリへ写す（STR-01）
│   ├── .forge/                    → 対象のリポジトリの .forge/
│   │   ├── forge.py               補助 CLI の入口（STR-03）
│   │   ├── forge_kit/             補助 CLI のモジュール。平らに並べる（STR-01、STR-02）
│   │   └── templates/prompts/     サブエージェントと実行役へのプロンプトのひな形（STATE-02）
│   └── claude/                    → 対象のリポジトリの .claude/（先頭にドットを付けない理由は ADR 0003）
│       ├── skills/forge-goals/    人とゴール・指標・評価課題を決めるスキル（STR-05、PROC-07）
│       ├── skills/forge-build/    サブエージェントで対象スキルの初版を作るスキル
│       ├── skills/forge-run/      評価と改善を進めるスキル
│       └── agents/                設計役・構築役・採点役・分析役の定義（STR-05）
├── install.py                     配布物を対象のリポジトリに入れる
├── scripts/
│   ├── structure_check.py         構造検査（DEP-01 ほか structure の全ルール）
│   └── gen_docs.py                指標の一覧とバンドルの決まりの生成器（STR-04）
├── tests/                         テスト。test_<モジュール>.py と support.py（TEST-01、TEST-02）
│   └── fixtures/
│       ├── sample-repo/           テストで使う見本のリポジトリ
│       └── streams/               テストの偽の実行役が返す、記録した実行の記録
├── docs/design/                   設計文書
├── .foundation/                   ルールの検査の道具と probe（保護ファイル）
├── AGENTS.md、CLAUDE.md           人とエージェントの入口
└── Makefile、pyproject.toml       検査のコマンドと設定（保護ファイル）
```

対象のリポジトリに入れた後は、次の形になる。

```text
<対象のリポジトリ>/
├── .claude/skills/forge-goals/、forge-build/、forge-run/
├── .claude/agents/forge-designer.md、forge-builder.md、forge-grader.md、forge-analyst.md
├── .claude/skills/<スキル名>/          対象スキル（install か decide --adopt が書く。OPS-04）
├── .claude/agents/<スキル名>-<役>.md   対象スキルのサブエージェント
└── .forge/
    ├── forge.py、forge_kit/、templates/
    ├── targets/<target-id>/            charter、設計、構築の記録、採点、提案、比較、決定、報告（残す。STATE-01）
    └── work/<target-id>/               実行の記録、プロンプト、採点役の出力（消してよい。.gitignore に入れる）

<OS の一時ディレクトリ>/orch-forge/<リポジトリ名>-<パスのハッシュ8桁>/<target-id>/<slot>/<run-id>/
                                        評価用のコピー（消してよい。ADR 0003）
```

## 3. 依存の許可表

`forge_kit` のモジュールごとに、import してよいモジュールを示す。表に無い組は全部禁止で、構造検査で強制する（ルールID：DEP-01）。この表は `scripts/structure_check.py` の `SHARED`・`STAGES`・`ENTRY` と1対1で対応する。モジュールが29あり行列では読めないため、行ごとに許可する相手を並べる。

### 共有のモジュール

| from | import してよいもの | 受け持つこと |
|---|---|---|
| `errors` | なし | 4つの例外 |
| `layout` | `errors` | ファイルの置き場とファイル名の定数、slot と run の id |
| `catalog` | なし | 指標の一覧（`METRICS`） |
| `metrics` | なし | 平均、一致度などの計算 |
| `render` | なし | 表、数、箇条書き、`job` の行の書き方 |
| `shape` | なし | JSON の形の検証の部品 |
| `charter` | `catalog`、`shape`、`errors` | charter の型、検証、承認のハッシュ |
| `design` | `bundle`、`shape`、`errors` | 設計の型と検証 |
| `trace` | `render` | 実行の記録を読み、起動・編集・費用を数え、採点役が読む版を作る |
| `contracts` | `shape`、`errors` | 段とサブエージェントが受け渡す JSON の型と検証、エージェント名 |
| `fsops` | `errors` | ファイルの読み書き、コピー |
| `proc` | `errors` | 外部コマンド、git、`claude -p` の起動、並行、一時ディレクトリ |
| `prompts` | `fsops`、`errors` | ひな形の表（`TEMPLATES`）と置き換え |
| `bundle` | `fsops`、`layout`、`errors` | バンドルの決まり（`RULES`）、バンドルのファイルの一覧・写し・置き換え |
| `views` | `charter`、`design`、`render` | charter と設計の人が読む版 |
| `workspace` | `charter`、`contracts`、`design`、`fsops`、`layout`、`trace`、`errors` | ファイルを読んで検証する `load_*`、承認の確認、進み具合 |

### 段のモジュール

段のモジュールは、共有のモジュールだけを import し、他の段のモジュールを import しない。

| from | import してよいもの | 受け持つサブコマンド |
|---|---|---|
| `goals` | `catalog`、`charter`、`fsops`、`layout`、`render`、`views`、`workspace`、`errors` | `targets`、`metric-catalog`、`charter-new`、`charter-check`、`charter-approve` |
| `status` | `bundle`、`charter`、`contracts`、`layout`、`render`、`workspace`、`errors` | `status` |
| `designing` | `charter`、`contracts`、`design`、`fsops`、`layout`、`prompts`、`render`、`views`、`workspace`、`errors` | `design-new`、`design-check`、`design-approve` |
| `building` | `bundle`、`charter`、`contracts`、`design`、`fsops`、`layout`、`prompts`、`render`、`views`、`workspace`、`errors` | `build`、`bundle-check`、`install` |
| `prepare` | `bundle`、`charter`、`contracts`、`fsops`、`layout`、`proc`、`prompts`、`workspace`、`errors` | `prepare` |
| `execute` | `charter`、`contracts`、`fsops`、`layout`、`proc`、`workspace`、`errors` | `execute` |
| `collect` | `bundle`、`charter`、`contracts`、`fsops`、`layout`、`proc`、`prompts`、`render`、`trace`、`workspace`、`errors` | `collect` |
| `score` | `catalog`、`charter`、`contracts`、`fsops`、`layout`、`metrics`、`render`、`workspace`、`errors` | `score` |
| `analyze` | `bundle`、`charter`、`contracts`、`fsops`、`layout`、`prompts`、`render`、`views`、`workspace`、`errors` | `analyze`、`propose` |
| `compare` | `contracts`、`fsops`、`layout`、`metrics`、`render`、`workspace`、`errors` | `compare` |
| `decide` | `bundle`、`contracts`、`fsops`、`layout`、`workspace`、`errors` | `decide` |
| `report` | `charter`、`contracts`、`fsops`、`layout`、`render`、`workspace`、`errors` | `report` |

### 入口

| from | import してよいもの |
|---|---|
| `cli` | 段のモジュールの全部、`layout`、`proc`、`errors` |

### 副作用の置き場

依存の向きとは別に、副作用に触れてよいモジュールを限る（DEP-04、ASYNC-01、OPS-01、OPS-02）。

| 副作用 | モジュール |
|---|---|
| ファイルの書き込み・削除・コピー | `fsops` |
| 外部コマンド（git、検査コマンド、`claude -p`）、並行、環境変数、一時ディレクトリ | `proc` |
| 時刻、画面への出力、終了コード | `cli` |
| 対象のリポジトリの `.claude/` への書き込み（`bundle.place`） | `building`（`install`）、`decide`（`--adopt`） |

## 4. 公開面

| モジュール | 外から使ってよいもの | 触れなくする仕組み |
|---|---|---|
| 補助 CLI 全体 | `forge.py` のサブコマンド（`targets`、`metric-catalog`、`charter-new`、`charter-check`、`charter-approve`、`status`、`design-new`、`design-check`、`design-approve`、`build`、`bundle-check`、`install`、`prepare`、`execute`、`collect`、`score`、`analyze`、`propose`、`compare`、`decide`、`report`） | スキルはサブコマンドだけを呼ぶ。`__init__.py` は何も公開しない（STR-03） |
| 各モジュール | `_` で始まらない名前 | 構造検査（DEP-02） |
| サブエージェント | プロンプトのファイルと、プロンプトが示す出力のファイル | ひな形（STATE-02）と `contracts.parse_*`・`design.parse`・`bundle.check` の検証（ERR-02、STR-06） |
| 実行役（`claude -p`） | `execute.command` が組み立てる引数 | 構造検査とテスト（OPS-05） |

## 5. データの流れ

### 人とゴールを決める（forge-goals）

```text
人 ⇄ forge-goals（AskUserQuestion と文章の質問）
      → charter-new（ひな形）→ charter.json を書く → charter-check（検証、charter.md）
      → 人の承認 → charter-approve（approval に sha256 を書く）
```

承認の後に charter を1文字でも変えると、`approval.sha256` と中身のハッシュが合わなくなり、設計・構築・評価の段は止まる（OPS-04）。

### 初版を作る（forge-build）

対象のリポジトリに `.claude/skills/<スキル名>/SKILL.md` が無いときに通る。

```text
design-new     → ホールドアウトを除いた charter（visible-charter.md）と設計役のプロンプトを書く。job の行を出す
設計役         → リポジトリの決まりを読み、build/design.json を書く
design-check   → 設計の形を検査し、design.md を書く
人             → 設計を承認するか、直してほしいことを答える（直すなら design-new --feedback で設計役をもう一度）
design-approve → design-approval.json に設計の sha256 を書く
build          → 設計から下書きのバンドルの骨組み（build/draft/）を作り、構築役のプロンプトを書く。job の行を出す
構築役         → 骨組みの TODO(forge) を埋める。書くのは build/draft/ の下だけ
bundle-check   → バンドルの決まりと、設計との一致を検査し、bundle-check.md を書く
人             → 下書きを入れるか、直してほしいことを答える（直すなら build --feedback で構築役をもう一度）
install        → 下書きを .claude/skills/<スキル名>/ と .claude/agents/ に写し、install.json を書く
```

### 1回の評価（baseline、candidate、final で共通）

```text
prepare  → 評価に使うバンドルを work/<id>/<slot>/bundle/ に写し、課題 × 実行役の人数ぶん、リポジトリを
           OS の一時ディレクトリに写す。コピーから forge-* のスキルとエージェントと .forge/ を除き、
           バンドルを重ね、git の基準を作り、実行役のプロンプト（prompt.md、system.md）と plan.json を書く
execute  → コピーごとに claude -p を起動し（並行の数は charter の executor.parallel）、stream.jsonl、
           stderr.txt、exec.json を書く。exec.json がある run は飛ばすので、止まっても続きから回せる
collect  → コピーの差分・検査コマンドの結果・実行の記録の集計を facts.json に、採点役が読む版を
           trace.md と result.md に書き、採点役のプロンプト（grader-prompt.md）を書く。job の行を出す
採点役   → 受け入れ条件、手順の各項目、報告の形、独自の指標の判定を grade.json に書く
score    → 事実と判定から指標を計算し、scores.json と scores.md を書く
```

### 改善のラウンド

```text
analyze  → 今のバンドルを rounds/<N>/proposed/ に写し、ホールドアウトを除いた charter と、
           分析役のプロンプトを書く
分析役   → 証拠（採点、実行の記録の集計、差分）を読み、原因を分類して proposed/ を直し、proposal.json を書く
propose  → 提案の形、バンドルの決まり、スキル名の不変、差分との対応、評価課題の文の写しを検査し、
           proposal.md を書く
候補の評価 → 上の「1回の評価」を proposed/ のバンドルで行う
compare  → 今のバンドルと候補の指標を比べ、推奨（採用・不採用）を compare.md に書く
人       → 採否を決める（forge-run が AskUserQuestion で聞く）
decide   → 採用なら、今のバンドルを rounds/<N>/previous/ に退避し、proposed/ を .claude/ へ写す
```

must の指標を全部満たすか、ラウンドが上限に達したら、ホールドアウトを含めて最後の評価を行い、`report` が報告を書く。

## 6. 変更シナリオ表

| 変更 | 触るファイル | 触らないもの |
|---|---|---|
| 指標を1つ足す | `catalog.py`（METRICS）、`score.py`（CALCULATORS）、`make docs` で metric-catalog.md、`tests/test_score.py` | 他の段のモジュール、スキル |
| バンドルの決まりを1つ足す | `bundle.py`（RULES と検査の関数）、`make docs` で bundle-rules.md、`tests/test_bundle.py` | 段のモジュール、ひな形、スキル |
| プロンプトの文言を直す | `templates/prompts/<名前>.md` | Python のコード（置き換えの名前を変えるなら `prompts.py` の表も） |
| 置き換えの値を1つ足す | `templates/prompts/<名前>.md`、`prompts.py`（TEMPLATES）、値を作る段のモジュール（designing、building、prepare、collect、analyze のどれか） | 他の段のモジュール |
| charter に項目を足す | `charter.py`（型と parse）、`charter.SCHEMA_VERSION`、`views.py`（人が読む版）、`charter-schema.md`、ADR | 段のモジュール（項目を使う段だけ変える） |
| 設計に項目を足す | `design.py`（型と parse）、`design.SCHEMA_VERSION`、`views.py`、`design-schema.md`、骨組みを作る `building.py`、ADR | 評価の段のモジュール |
| 実行役の引数を変える | `execute.py`（command）、`tests/test_execute.py`、research.md の「ヘッドレス実行」 | 他の段のモジュール |
| 実行の記録から新しい数を読む | `trace.py`、`tests/test_trace.py`、`tests/fixtures/streams/`、使う指標（`catalog.py`、`score.py`） | 実行と準備の段 |
| 段を1つ足す | 新しい段のモジュール、`contracts.py`・`layout.py`（受け渡しと置き場）、`status.py`、`cli.py`、`tests/test_<段>.py`、`structure_check.py` と本書の許可表、段を使うスキルの表 | 既存の段のモジュール |
| スキルの手順を直す | `kit/claude/skills/forge-*/SKILL.md` か `references/` | 補助 CLI |
| サブエージェントの道具を変える | `kit/claude/agents/<役>.md` | 補助 CLI、ひな形 |
