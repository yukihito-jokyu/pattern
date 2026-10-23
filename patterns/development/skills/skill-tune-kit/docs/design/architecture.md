# skill-tune-kit のアーキテクチャ

この文書は、構造そのものと、その構造を選んだ理由を説明する。個々のルールの全文は [rules.md](rules.md) にある。

## 1. 前提

skill-tune-kit は、利用者のリポジトリにある任意の Claude Code スキル（以下、対象スキル）を、評価データに基づいて改善する道具である。改善の作業は、次の4つの性質を持つ。

1. **「良い」の基準が2通りある**。入力と正解の組（正解データ）があるか作れるなら、正解との一致で測る（`reference` モード）。正解が1つに決まらないなら、人との壁打ちで決めた評価項目で測る（`criteria` モード）。どちらのモードでも、1件の評価データ（ケース）は「入力」と「満たすべき検査」の組で表す。モードの違いは、検査が正解を参照するかどうかだけになる（STATE-03）
2. **改善が評価データに合わせすぎていないかを確かめる必要がある**。そこでケースを学習用・検証用・テスト用に分ける。学習役（スキルを直すサブエージェント）には学習用だけを見せ、候補を採るかは検証用のスコアで機械的に決め、テスト用は最後に1回だけ使う（[ADR 0007](adr/0007-train-val-test-split.md)、[ADR 0008](adr/0008-mechanical-adoption.md)）
3. **評価データ自体が間違っていることがある**。正解の誤り、あいまいな評価項目、情報の足りない入力は、スキルを直しても失敗を生み続ける。そこで毎ラウンドの初めに監査役が失敗を点検し、データの直しを提案する。データを直すとゴールが変わるので、直すのは人が承認したものだけにする（PROC-07）
4. **段が多く、順番を間違えやすい**。どの段にいて次に何をするかを、エージェントの判断ではなく、ファイルの有無から補助 CLI の `status` が決める。スキル（`skill-tune`）は `status` の指示に従うだけにする（STATE-01）

この基盤でよく起きる変更は、検査の種類を足す、プロンプトの文言を直す、スキルの手順を直す、段（サブコマンド）を足す、の4つである。どれも触るファイルが予測できるように、補助 CLI を「段のモジュール」と「共有のモジュール」に分け、段どうしの依存を禁じた（DEP-01）。

## 2. ディレクトリ構造

```text
skill-tune-kit/
├── kit/                          配布物の正本。install.py が利用者のリポジトリへ写す（STR-01）
│   ├── .tune/                    → 利用者のリポジトリの .tune/
│   │   ├── tune.py               補助 CLI の入口（STR-03）
│   │   ├── tune_kit/             補助 CLI のモジュール。平らに並べる（STR-01、STR-02）
│   │   └── templates/prompts/    サブエージェントへのプロンプトのひな形（STATE-02）
│   └── claude/                   → 利用者のリポジトリの .claude/（先頭にドットを付けない理由は ADR 0003）
│       ├── skills/skill-tune/    配布するスキル。references/ に計画の作り方と形式（STR-05）
│       └── agents/               実行役・採点役・学習役・監査役の定義（STR-05）
├── install.py                    配布物を利用者のリポジトリに入れる
├── scripts/
│   ├── structure_check.py        構造検査（structure の全ルール）
│   └── gen_docs.py               検査の種類の一覧（check-kinds.md）の生成器（STR-04）
├── tests/                        テスト。test_<モジュール>.py と support.py（TEST-01、TEST-02）
│   └── fixtures/                 テストで使う見本のスキル
├── docs/design/                  設計文書
├── .foundation/                  ルールの検査の道具と probe（保護ファイル）
├── AGENTS.md、CLAUDE.md          人とエージェントの入口
└── Makefile、pyproject.toml      検査のコマンドと設定（保護ファイル）
```

利用者のリポジトリに入れた後は、次の形になる。

```text
<利用者のリポジトリ>/
├── .claude/skills/skill-tune/
├── .claude/agents/tune-executor.md、tune-grader.md、tune-learner.md、tune-auditor.md
└── .tune/
    ├── tune.py、tune_kit/、templates/
    ├── targets/<target-id>/          計画、評価データ、版、結果、ラウンドの記録、報告（残す。STATE-01）
    │   ├── plan.json                 計画（人と決める）
    │   ├── dataset/cases.json        ケース（人と決める）
    │   ├── dataset/files/<case>/     ケースの入力ファイル（input/）と正解のファイル（expected/）
    │   ├── plan.md、split.json       check-plan が書く（生成物）
    │   ├── approval.json             approve と data-fix が書く
    │   ├── versions/v<N>/            スキルの版。v0 は承認時の写し、v1 以降は学習役が直した候補
    │   ├── results/v<N>/<case>/run-<K>/  1回の実行の結果（result.json、response.md）
    │   ├── rounds/r<N>/              ラウンドごとの監査、学習、比較、決定
    │   ├── final/                    テスト用の監査（報告のみ）
    │   └── report.md、applied.json
    └── work/<target-id>/<run-key>/   実行役の作業場所（sandbox）とプロンプト。消してよい。.gitignore に入れる
```

## 3. 依存の許可表

`tune_kit` のモジュールごとに、import してよいモジュールを示す。表に無い組は全部禁止で、構造検査で強制する（ルールID：DEP-01）。この表は `scripts/structure_check.py` の `SHARED`・`STAGES`・`ENTRY` と1対1で対応する。モジュールが21あり行列では読めないため、行ごとに許可する相手を並べる。

### 共有のモジュール

| from | import してよいもの | 役割 |
|---|---|---|
| `errors` | なし | 利用者が直せるエラーの型 |
| `render` | なし | Markdown の部品（表、率、箇条書き、囲み、job の行） |
| `splitting` | なし | 学習用・検証用・テスト用への決定的な分割 |
| `checks` | なし | 検査の種類の一覧と、機械で判定する種類の評価 |
| `metrics` | なし | 指標の計算と採否の規則 |
| `layout` | `errors` | 作業場所のパスとファイル名の定数 |
| `plan` | `checks`、`layout` | plan.json・cases.json の型と検証 |
| `contracts` | `layout`、`plan` | 段とサブエージェントの間で受け渡す JSON の型と検証 |
| `fsops` | `errors` | ファイルの読み書き・コピー・削除とハッシュ |
| `proc` | `errors` | 外部コマンド（git、検査の `command`） |
| `prompts` | `fsops`、`layout`、`errors` | ひな形からプロンプトを作る |
| `workspace` | `contracts`、`fsops`、`layout`、`metrics`、`plan`、`splitting`、`errors` | 作業場所のファイルを読み、検証済みの型と進み具合を返す（書かない） |
| `evidence` | `contracts`、`fsops`、`layout`、`plan`、`render` | 学習役と監査役に渡す証拠（ケースと実行の結果）の Markdown |

### 段のモジュール

段のモジュールは、共有のモジュールだけを import し、他の段のモジュールを import しない。

| from | import してよいもの |
|---|---|
| `planning` | `checks`、`contracts`、`fsops`、`layout`、`plan`、`render`、`workspace`、`errors` |
| `status` | `contracts`、`layout`、`plan`、`render`、`workspace` |
| `evaluate` | `checks`、`contracts`、`fsops`、`layout`、`plan`、`proc`、`prompts`、`render`、`workspace`、`errors` |
| `learn` | `contracts`、`evidence`、`fsops`、`layout`、`plan`、`prompts`、`render`、`workspace`、`errors` |
| `decide` | `contracts`、`fsops`、`layout`、`metrics`、`plan`、`render`、`workspace`、`errors` |
| `audit` | `contracts`、`evidence`、`fsops`、`layout`、`plan`、`prompts`、`render`、`workspace`、`errors` |
| `report` | `contracts`、`fsops`、`layout`、`metrics`、`plan`、`render`、`workspace`、`errors` |

### 入口

| from | import してよいもの |
|---|---|
| `cli` | 段のモジュールの全部、`layout`、`errors` |

### 副作用の置き場

依存の向きとは別に、副作用に触れてよいモジュールを限る（DEP-04、ASYNC-01、OPS-01、OPS-02）。

| 副作用 | モジュール |
|---|---|
| ファイルの書き込み・削除・コピー、JSON の読み書き | `fsops` |
| 外部コマンド（git、検査の `command`）、環境変数 | `proc` |
| 時刻、画面への出力、終了コード | `cli` |

## 4. 公開面

| モジュール | 外から使ってよいもの | 触れなくする仕組み |
|---|---|---|
| 補助 CLI 全体 | `tune.py` のサブコマンド（`init`、`check-plan`、`approve`、`status`、`eval-prepare`、`eval-collect`、`eval-score`、`audit`、`audit-check`、`data-fix`、`learn`、`learn-check`、`decide`、`report`、`apply`） | スキルはサブコマンドだけを呼ぶ。`__init__.py` は docstring だけにする（STR-03） |
| 各モジュール | `_` で始まらない名前 | 構造検査（DEP-02） |
| サブエージェント | プロンプトのファイルと、プロンプトが示す出力のファイル | ひな形（STATE-02）と `contracts.parse_*` の検証（ERR-02） |

## 5. データの流れ

### 計画を決める（skill-tune の手順 A）

```text
人 ⇄ skill-tune（AskUserQuestion）
      → init（plan.json と cases.json のひな形）
      → 正解データがある・作れる → reference：ケースを取り込む・作る（references/dataset-guide.md）
        正解データが無い     → criteria：評価項目を壁打ちで決め、入力を作る（references/criteria-guide.md）
      → check-plan（検証、分割、plan.md）→ 人の承認 → approve（ハッシュを記録し、対象スキルを v0 に写す）
```

承認の後に plan.json か cases.json を1文字でも変えると、ハッシュが合わなくなり、評価の段は止まる（OPS-04）。データの直しは `data-fix` だけが行い、人の承認をハッシュと一緒に記録する。

### 1つの版の評価（最初の評価、候補の評価、テストで共通）

```text
eval-prepare → 足りない実行（版 × ケース × 回）ごとに、作業場所（sandbox）を作って git の基準を置き、
               版のスキルを写し、実行役のプロンプトを書く
実行役       → sandbox の中で、写したスキルに従ってケースの依頼をこなし、返答を response.md に書く
eval-collect → 機械の検査（contains、equals、command など）を回し、judge の検査があれば
               採点役のプロンプトを書く
採点役       → 版を知らされずに、judge の検査ごとに合否と根拠を grade.json に書く
eval-score   → 機械の検査と採点を合わせて results/<版>/<ケース>/run-<K>/result.json に書き、作業場所を消す
```

作業場所を消すのは、採点役のプロンプトに正解があり、後で別の版を解く実行役に読ませないためである。結果には、そのケースの中身のハッシュ（入力、正解、検査、sandbox の形）を記録する。データが直されてハッシュが変わったケースの結果は古いものとして扱い、`status` が評価のやり直しを指示する（STATE-01）。

### 改善のラウンド（r1 から max_rounds まで）

```text
audit       → 今の版の学習用・検証用の失敗を集め、監査役のプロンプトを書く（失敗が無ければ監査を省く）
監査役      → 失敗ごとに原因（skill、expected、check、input）を分類し、データの直しを audit.json に書く
audit-check → 直しの形を検査し、audit.md を書く
人          → 適用する直しを選ぶ（skill-tune が AskUserQuestion で聞く）
data-fix    → 選ばれた直しを cases.json・plan.json に適用し、承認を記録し直す
（直したケースは今の版で評価し直す）
learn       → 今の版を versions/v<N>/ に写し、学習用だけの証拠（evidence.md）と学習役のプロンプトを書く
学習役      → 証拠を読み、v<N>/ を直し、proposal.json を書く
learn-check → 提案の形、name の不変、500行、検証用・テスト用の文の写しを検査し、proposal.md を書く
（候補 v<N> を学習用・検証用で評価する）
decide      → 検証用のスコアで候補を採るかを機械的に決め、compare.md と decision.json を書く
```

次のどれかに当たったら、ラウンドを止めて最後の評価へ進む（STATE-03）。

| 条件 | 理由 |
|---|---|
| 今の版が検証用で全ケース・全検査に合格した | 直す余地が無い |
| 決定したラウンドの数が `budget.max_rounds` に達した | 予算 |
| 直近の `budget.patience` 回が続けて不採用だった | 改善が頭打ち |

### 最後の評価と報告

```text
（元の版 v0 と最良の版を、テスト用で評価する）
audit --final → 最良の版のテスト用の失敗を監査役が点検する（報告のみ。データは直さない）
report        → 指標の推移、採った変更、データの直し、テストの結果を report.md に書く
人            → 最良の版を対象スキルに適用するかを決める
apply         → 対象スキルを最良の版で置き換える（applied.json を書く）
```

## 6. 変更シナリオ表

| 変更 | 触るファイル | 触らないもの |
|---|---|---|
| 検査の種類を1つ足す | `checks.py`（KINDS と評価の関数）、`plan.py`（種類ごとの必須項目）、`make docs` で check-kinds.md、`tests/test_checks.py` | 段のモジュール（`command` のように外部コマンドが要る種類だけ `evaluate.py` も） |
| プロンプトの文言を直す | `templates/prompts/<名前>.md` | Python のコード（置き換えの名前を変えるなら `prompts.py` の表も） |
| 置き換えの値を1つ足す | `templates/prompts/<名前>.md`、`prompts.py`（TEMPLATES）、値を作る段のモジュール、`tests/test_prompts.py` | 他の段のモジュール |
| plan.json に項目を足す | `plan.py`（型と parse）、`plan.SCHEMA_VERSION`、`planning.py`（plan.md）、`references/plan-schema.md`、ADR | 項目を使わない段のモジュール |
| 段（サブコマンド）を1つ足す | 新しい段のモジュール、`layout.py`（置き場）、`contracts.py`（受け渡しがあれば）、`status.py`、`cli.py`、`tests/test_<段>.py`、`structure_check.py` と本書の許可表、skill-tune の SKILL.md の表 | 既存の段のモジュール |
| 1つの段の JSON を一覧で見せるだけのサブコマンドを足す | その JSON を書く段のモジュール（例：`decide.py` に `decide_list`）、`cli.py`、`tests/test_<段>.py`、`tests/test_cli.py`、使う場面があれば skill-tune の SKILL.md | `status.py`、他の段のモジュール、`layout.py`（新しいファイルを書かないため） |
| スキルの手順を直す | `kit/claude/skills/skill-tune/SKILL.md` か `references/` | 補助 CLI |
| サブエージェントの道具を変える | `kit/claude/agents/<役>.md` | 補助 CLI、ひな形 |
| 指標の計算か採否の規則を変える | `metrics.py`、`tests/test_metrics.py`、ADR 0008 | 段のモジュール（表示の列が変わるなら `decide.py`・`report.py` も） |
