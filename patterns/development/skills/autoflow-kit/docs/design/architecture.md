# autoflow-kit のアーキテクチャ

この文書は、構造そのものと、その構造を選んだ理由を説明する。個々のルールの全文は [rules.md](rules.md) にある。

## 1. 前提

autoflow-kit は、任意のリポジトリに「オートフロー」を入れる道具である。オートフローとは、依頼（文章、Backlog の課題、Redmine のチケット、GitLab・GitHub の Issue）から、計画・実装・検証・AI レビュー・リスクの判定までを AI が自走し、人は決めた関所でだけ判断する流れを指す。

この構造は、次の4つの前提から決めた。

1. **AI の「できました」は証拠にならない**。記事は、Claude に実行できる検証手段を与え、「完了と言う代わりに出力を見せる」ことを最も重要とする（[research.md](research.md) の記事の節）。そこで、検査コマンドは補助 CLI が自分で実行し、結果を差分の版（git の tree id）に結び付けて記録する。AI が書いた報告は証拠として扱わない（GATE-04）
2. **順序を AI の判断に任せると、関所を飛ばしうる**。レビューを省いて報告する、検査の後に変えたまま承認を求める、といった近道を、文書だけでは止められない。そこで、実行の進み具合を追記だけの記録（`trail.jsonl`）で持ち、補助 CLI が次の段を決め、各段の入口は「今がその段の番か」を確かめてから動く（GATE-03）。スキルは `status` の指示に従うだけにする
3. **人の時間は、人にしかできない判断に使う**。記事は、人が残る場面を「作るかどうか（方向・範囲）」「リスクの高いコード」「証拠を読むこと」「結果への責任」とする。そこで、人の関所を H0〜H3 の4つに限り、条件を `policy.py` の表に置く（GATE-01）。それ以外の場面では AI は人に聞かずに進む
4. **リスクは作者ではなく変更が決める**。リスクの段は差分のパス・大きさ・種類から規則で決め、AI のリスク判定役は段を上げる方向にだけ効かせる（GATE-06）。段はレビューの深さと、最後に人がすることの重さを決める

この基盤でよく起きる変更は、関所の条件を足す、取得元を足す、レビューの観点を足す、プロンプトの文言を直す、段を足す、プロファイルに項目を足す、の6つである。どれも触るファイルが予測できるように、補助 CLI を「段のモジュール」と「共有のモジュール」に分け、段どうしの依存を禁じた。

## 2. 人の関所と機械の関所

オートフローの全体を、記事の考え方に沿って2種類の関所に分ける。

### 2.1 人の関所

| 関所 | いつ | 何を決めるか | 記事の対応 |
|---|---|---|---|
| H0 準備の承認 | リポジトリごとに1回（`autoflow-setup`） | 検査コマンド、常に人が見るパス、上限の値を承認する | 「リスクの段を書き出す。厳しめに始めて証拠に応じて緩める」 |
| H1 方向の確認 | 計画の後、実装の前。`policy.H1_RULES` の条件に当たるときだけ | 作るか、計画を直すか、やめるか | 「Deciding whether to build it」「早い段階で別の方向を出す」 |
| H2 行き詰まり | 実装の途中。`policy.H2_RULES` の条件に当たるときだけ | 続けるか、計画からやり直すか、やめるか | 「After three rounds, the reviewer asks the author to step back and reconsider the approach.」 |
| H3 最終承認 | 毎回。検証とレビューを通った後 | コミットするか、直してほしいことを伝えるか、やめるか | 「Reading the evidence」「Owning the outcome」「An approval covers one specific commit」 |

H1・H2 の条件と、H3 で人がすることの重さ（段ごと）は、`kit/.autoflow/autoflow_kit/policy.py` の表が正本である。人が読む版は `kit/claude/skills/autoflow/references/gates.md`（生成物）にある。

### 2.2 機械の関所

| 関所 | 仕組み | ルール |
|---|---|---|
| 段の順序 | `trail.next_step` が記録から次の段を決め、各段の入口の `context.begin` が番でない段を止める | GATE-03 |
| 証拠 | `verify` だけが検査コマンドを実行し、tree id 付きで記録する。検査の後に作業ツリーが変わると、次の段は `verify` に戻る | GATE-04 |
| レビュー | 観点ごとの探索役を並列に起動し、検証役の投票で閾値以上の指摘だけを残す。Important が残る間は報告に進めない。ラウンドの上限で H2 | GATE-01 |
| リスクの段 | 差分のパス・大きさ・種類から規則で段を決め、AI の判定とは大きい方を採る | GATE-06 |
| 読み取りだけの役 | 計画役・探索役・検証役・リスク判定役の前後で tree を比べ、変わっていれば止める | GATE-07 |
| 承認 | `decide` が人の回答の原文と tree id を記録し、`commit` は承認の tree と今の tree が一致するときだけ動く | GATE-05 |

## 3. ディレクトリ構造

```text
autoflow-kit/
├── kit/                              配布物の正本。install.py が対象のリポジトリへ写す（STR-01）
│   ├── .autoflow/                    → 対象のリポジトリの .autoflow/
│   │   ├── autoflow.py               補助 CLI の入口（STR-03）
│   │   ├── autoflow_kit/             補助 CLI のモジュール。平らに並べる（STR-01、STR-02）
│   │   └── templates/prompts/        サブエージェントへのプロンプトのひな形（STATE-02）
│   └── claude/                       → 対象のリポジトリの .claude/（先頭にドットを付けない理由は ADR 0003）
│       ├── skills/autoflow-setup/    プロファイルを作り、人の承認を得るスキル（H0）
│       ├── skills/autoflow/          依頼から最終承認までを自走させるスキル（H1〜H3）
│       ├── skills/autoflow-learn/    記録を集計し、発生源を直す提案をするスキル
│       └── agents/                   計画役・実装役・探索役・検証役・リスク判定役の定義（STR-05）
├── install.py                        配布物を対象のリポジトリに入れる
├── scripts/
│   ├── structure_check.py            構造検査（structure の全ルール）
│   └── gen_docs.py                   関所の表（gates.md）とプロファイルの表の生成器（STR-04）
├── tests/                            テスト。test_<モジュール>.py と support.py（TEST-01、TEST-02）
│   └── fixtures/sample-repo/         テストと通しの実行で使う見本のリポジトリ
├── docs/design/                      設計文書
├── .foundation/                      ルールの検査の道具と probe（保護ファイル）
├── AGENTS.md、CLAUDE.md              人とエージェントの入口
└── Makefile、pyproject.toml          検査のコマンドと設定（保護ファイル）
```

対象のリポジトリに入れた後は、次の形になる。

```text
<対象のリポジトリ>/
├── .claude/skills/autoflow-setup/、autoflow/、autoflow-learn/
├── .claude/agents/autoflow-planner.md、autoflow-builder.md、autoflow-finder.md、autoflow-verifier.md、autoflow-risk.md
└── .autoflow/
    ├── autoflow.py、autoflow_kit/、templates/
    ├── profile.json                      検査コマンド・パスの分類・上限（setup が作り、人が承認する。コミットする）
    ├── profile-approval.json             プロファイルの sha256 と承認の記録（コミットする）
    └── runs/                             実行の記録（.gitignore に入れる。STATE-01）
        ├── intake.md                     スキルが取得元から取った依頼の本文（start に渡す）
        └── <run-id>/
            ├── trail.jsonl                   実行の記録（追記だけ。依頼の出所と作業ブランチは最初の出来事が持つ）
            ├── task.md、guide.md             依頼と、開始時のレビューの指示（REVIEW.md など）の写し
            ├── profile.json                  開始時のプロファイルの写し（OPS-02）
            ├── plan/<n>/                     計画役のプロンプト、plan.json、plan.md、flow.json
            ├── build/<n>/                    実装役のプロンプトと report.json
            ├── evidence/                     検査の結果（<n>.json と、検査ごとのログ <n>-<検査>.log）
            ├── risk/<n>/                     差分、リスク判定役のプロンプト、judgment.json
            ├── review/round-<n>/             差分、探索役・検証役のプロンプトと出力、candidates.json、result.json、result.md
            ├── gates/                        H2 の理由（h2-<n>.md）
            └── handoff-<n>.md                H3 で人が読む報告書
```

段の成果は、段の番号（計画・実装・リスクの判定は何回目か、証拠は何件目か、レビューは何ラウンド目か）の置き場に書き、前の成果を上書きしない。段の結果の要約（リスクの段、レビューの件数、コミットの id）は、別のファイルではなく `trail.jsonl` の出来事に書く（STATE-01）。

## 4. 依存の許可表

`autoflow_kit` のモジュールごとに、import してよいモジュールを示す。表に無い組は全部禁止で、構造検査で強制する（ルールID：DEP-01）。この表は `scripts/structure_check.py` の `SHARED`・`STAGES`・`ENTRY` と1対1で対応する。モジュールが28（`__init__` を除く）あり行列では読めないため、行ごとに許可する相手を並べる。

### 共有のモジュール

| from | import してよいもの | 受け持つこと |
|---|---|---|
| `errors` | なし | 4つの例外 |
| `layout` | `errors` | ファイルの置き場とファイル名の定数、実行の id、取得元の表（`SOURCES`） |
| `shape` | なし | JSON の形の検証の部品と、dataclass を JSON の値にする `to_data` |
| `render` | なし | 表、箇条書き、数、コードの囲み、`job` の行の書き方 |
| `fsops` | `errors` | ファイルの読み書き、追記、写し |
| `proc` | `errors` | 外部コマンド（検査コマンド、git）の起動と出力 |
| `profile` | `shape`、`errors` | プロファイルの型、既定値、検証、sha256 |
| `contracts` | `shape`、`errors` | サブエージェントと受け渡す JSON（計画、実装の報告、指摘、投票、リスクの判定）と、段どうしで受け渡す JSON（証拠、レビューの候補と結果）の型と検証、エージェント名 |
| `policy` | `contracts`、`profile`、`shape` | 関所とリスクの段とレビューの深さの表（`TIERS`、`LENSES`、`DEPTHS`、`KINDS`、`H1_RULES`、`H2_RULES`、`GATES`、`REVIEW`）と、それを当てはめる関数。手順（`Flow`）を組み立てる |
| `changes` | `proc`、`errors` | 作業ツリーの tree id、変更ファイル、差分の文、行数 |
| `trail` | `policy`、`shape`、`errors` | 実行の記録（`trail.jsonl`）の出来事の型と、次の段を決める状態機械（`next_step`）、H2 の数え方（`progress`） |
| `prompts` | `fsops`、`errors` | ひな形の表（`TEMPLATES`）と置き換え |
| `views` | `contracts`、`policy`、`profile`、`render` | 人とサブエージェントが読む版（計画、プロファイル、レビューの結果、関所の理由、種類と段の表） |
| `workspace` | `contracts`、`fsops`、`layout`、`policy`、`profile`、`shape`、`trail`、`errors` | ファイルを読んで検証する `load_*`、承認済みのプロファイル、実行の一覧 |
| `context` | `changes`、`layout`、`profile`、`trail`、`workspace`、`errors` | 段の入口。実行の状態と今の tree を読み、今がその段の番かを確かめる（`begin`）。読み取りだけの役の前後の tree を比べる（`require_same_tree`） |
| `escalation` | `fsops`、`layout`、`policy`、`profile`、`trail`、`views` | H2 の条件を確かめ、当たれば関所の理由を書いて記録に足す（`build-check`・`verify`・`review-tally` が使う） |

### 段のモジュール

段のモジュールは、共有のモジュールだけを import し、他の段のモジュールを import しない。

| from | import してよいもの | 受け持つサブコマンド |
|---|---|---|
| `setup` | `fsops`、`layout`、`proc`、`profile`、`render`、`shape`、`views`、`workspace`、`errors` | `setup-new`、`setup-check`、`setup-approve` |
| `intake` | `changes`、`fsops`、`layout`、`proc`、`profile`、`trail`、`workspace`、`errors` | `start` |
| `planning` | `context`、`fsops`、`layout`、`policy`、`prompts`、`render`、`shape`、`trail`、`views`、`workspace`、`errors` | `plan-new`、`plan-check` |
| `deciding` | `context`、`fsops`、`layout`、`policy`、`proc`、`trail`、`errors` | `decide` |
| `building` | `changes`、`context`、`contracts`、`escalation`、`fsops`、`layout`、`policy`、`prompts`、`render`、`trail`、`views`、`workspace`、`errors` | `build-new`、`build-check` |
| `verifying` | `changes`、`context`、`contracts`、`escalation`、`fsops`、`layout`、`proc`、`profile`、`render`、`shape`、`trail`、`workspace`、`errors` | `verify` |
| `risking` | `changes`、`context`、`fsops`、`layout`、`policy`、`prompts`、`render`、`trail`、`views`、`workspace`、`errors` | `risk-new`、`risk-check` |
| `reviewing` | `changes`、`context`、`contracts`、`escalation`、`fsops`、`layout`、`policy`、`prompts`、`render`、`shape`、`trail`、`views`、`workspace`、`errors` | `review-new`、`review-collect`、`review-tally` |
| `handoff` | `changes`、`context`、`contracts`、`fsops`、`layout`、`policy`、`proc`、`render`、`trail`、`views`、`workspace`、`errors` | `handoff`、`commit` |
| `status` | `context`、`contracts`、`layout`、`policy`、`render`、`trail`、`workspace`、`errors` | `status` |
| `learning` | `contracts`、`fsops`、`layout`、`policy`、`render`、`trail`、`workspace`、`errors` | `metrics`、`incident`、`learn` |

### 入口

| from | import してよいもの |
|---|---|
| `cli` | 段のモジュールの全部、`layout`、`trail`、`errors` |

### 副作用の置き場

依存の向きとは別に、副作用に触れてよいモジュールを限る（DEP-04、OPS-01、OPS-02、OPS-05）。

| 副作用 | モジュール |
|---|---|
| ファイルの書き込み・追記・写し | `fsops` |
| 外部コマンド（検査コマンド、git）、環境変数 | `proc` |
| 時刻、画面への出力、終了コード | `cli` |
| git のブランチの作成（`proc.git_switch_new`） | `intake` |
| git の index への全変更の追加（`proc.git_stage_all`。tree id を得るため） | `changes` |
| git のコミット（`proc.git_commit`） | `handoff` |
| 検査コマンドの実行（`proc.shell`） | `verifying` |
| 対象のリポジトリの `.claude/settings.local.json` への書き込み | `setup`（`setup-approve --allow`） |

## 5. 公開面

| モジュール | 外から使ってよいもの | 触れなくする仕組み |
|---|---|---|
| 補助 CLI 全体 | `autoflow.py` のサブコマンド（`setup-new`、`setup-check`、`setup-approve`、`start`、`status`、`plan-new`、`plan-check`、`decide`、`build-new`、`build-check`、`verify`、`risk-new`、`risk-check`、`review-new`、`review-collect`、`review-tally`、`handoff`、`commit`、`metrics`、`incident`、`learn`） | スキルはサブコマンドだけを呼ぶ。`__init__.py` は何も公開しない（STR-03） |
| 各モジュール | `_` で始まらない名前 | 構造検査（DEP-02） |
| サブエージェント | プロンプトのファイルと、プロンプトが示す出力のファイル | ひな形（STATE-02）と `contracts.parse_*` の検証（ERR-02） |
| プロファイル | `profile.json` のキー（`profile.SCHEMA_VERSION` で版を持つ） | `profile.parse` の検証と、`setup-approve` の sha256（PROC-06） |

## 6. データの流れ

### 準備（autoflow-setup、H0）

```text
setup-new     → リポジトリのファイル（package.json、Makefile、go.mod、pyproject.toml、Cargo.toml、CI の設定）から、
                検査コマンド・テストのパス・常に人が見るパスの案を作り、.autoflow/profile.json を書く
setup-check   → プロファイルを検証し、人が読む版を出す
人            → 承認するか、直してほしいことを答える（AskUserQuestion）
setup-approve → profile-approval.json に sha256・承認した人・回答の原文を書く。--allow なら検査コマンドの
                許可の規則を .claude/settings.local.json に足す
```

### 1件の依頼（autoflow、H1〜H3）

各段の後、スキルは `status` を実行し、出力の `次:`・`job`・`人:` の行に従って次の段に進む。

```text
スキル        → 取得元の表で依頼の本文を取り、.autoflow/runs/intake.md に書く
start         → 承認済みのプロファイルと、きれいな作業ツリーを確かめ、作業ブランチ autoflow/<run-id> を作り、
                依頼とレビューの指示とプロファイルを写して、実行の記録を始める（trail: started）
verify        → 作業の前に、プロファイルの検査コマンドが通るかを確かめる（baseline。trail: verified）
              → 落ちれば止める（検査コマンドを直して setup からやり直す）
plan-new      → 計画役のプロンプトを書く（trail: prompted。tree を控える）
計画役        → コードを読み、plan/<n>/plan.json を書く（項目は contracts.Plan）
plan-check    → tree が変わっていないかと計画を検証し、手順と予測の段（flow.json）を組み、H1 の要否を決める
                （trail: planned）
（H1）        → 条件に当たれば人が決める（decide --gate H1）
build-new     → 実装役のプロンプトを書く（理由：first、repro、failed、findings、human）
実装役        → コードを変え、build/<n>/report.json を書く（項目は contracts.BuildReport）
build-check   → 報告を検証し（回答の要る指摘に全部答えたか、再現の段でテストの外を変えていないか）、
                止まった理由があれば H2 を起こす（trail: built）
verify        → 種類が fix で再現がまだなら、計画の再現のコマンドだけを実行し、落ちることを確かめる（repro）
              → それ以外は、プロファイルの検査コマンド・受け入れ条件のコマンド・再現のコマンドを実行し、
                tree id 付きで記録する（check。trail: verified）。失敗が上限に達すれば H2
risk-new      → 作業の前の tree からの差分で規則の段を求め、リスク判定役のプロンプトを書く
リスク判定役  → risk/<n>/judgment.json を書く
risk-check    → 段 = max(規則, AI)、人の要否を決める（trail: risked）
review-new    → 段からレビューの深さを決め、差分（2ラウンド目からは前のラウンドの tree からの差分）と
                既出の指摘と回答を添えて、観点ごとの探索役のプロンプトを書く
探索役（並列）→ 指摘を書く（項目は contracts.Finding）
review-collect→ tree を比べ、指摘しないパスと退けた既出の指摘を除き、同じ場所の指摘をまとめて候補にし、
                検証役のプロンプトを書く（候補が無ければ書かない）
検証役（並列）→ 候補ごとに本物かと重大度を投票する
review-tally  → 閾値以上の票の候補だけを残し、Important・Nit・Pre-existing に分ける（trail: reviewed）
              → Important が残れば build-new（findings）へ戻る。ラウンドの上限なら H2
handoff       → H3 で人が読む報告書を handoff-<n>.md に書く（中身は handoff.py。trail: handed_off）
（H3）        → 人が承認・修正の依頼・中止を決める（decide --gate H3）。承認は tree id に結び付く
commit        → 承認の tree と今の tree が一致するときだけ、作業ブランチにコミットする（trail: committed）。
                リモートには送らない
```

どの段の後でも、検査の後に作業ツリーが変わっていれば、次の段は `verify` に戻る（GATE-04）。H3 の承認の後に変わったときも同じである（GATE-05）。

この図は段の順序だけを書く。JSON の項目は `contracts.py`、報告書の中身は `handoff.py`・`views.py`、関所の条件は `policy.py` が正本である。項目・条件・観点を足しても、この図は変えない。段を足したときだけ変える（PROC-02）。

### 学ぶ（autoflow-learn）

```text
metrics  → 全実行の trail から、人の介入の回数、1回で承認された割合、レビューのラウンド、差し戻しと中止と
           インシデント（ガードレール）を数える
incident → コミットした実行に、後で見つかった問題を記録する（trail: incident）
learn    → 繰り返したバグの種類、退けた指摘、人の修正の依頼、H2 の理由、インシデントを並べる
スキル   → 発生源（CLAUDE.md、REVIEW.md、プロファイル、検査）を直す案を作り、人の承認を得て直す
```

## 7. 変更シナリオ表

| 変更 | 触るファイル | 触らないもの |
|---|---|---|
| H1・H2 の条件を1つ足す | `policy.py`（`H1_RULES` か `H2_RULES` と判定の関数）、`make docs` で gates.md、`tests/test_policy.py` | 段のモジュール、スキル |
| リスクの段の規則を足す | `policy.py`（`tier_of_changes`）、`tests/test_policy.py`、`make docs` | 段のモジュール |
| レビューの観点を足す | `policy.py`（`LENSES`、`DEPTHS`）、`templates/prompts/finder.md` の観点の節、`tests/test_policy.py` | 段のモジュール、スキル |
| 取得元を足す | `layout.py`（`SOURCES`）、`autoflow/references/sources.md`、`tests/test_intake.py` | 他の段 |
| プロンプトの文言を直す | `templates/prompts/<名前>.md` | Python のコード（置き換えの名前を変えるなら `prompts.py` の表も） |
| プロファイルに項目を足す | `profile.py`（型、既定値、parse、`SCHEMA_VERSION`）、`views.py`、`setup.py`（検出）、`make docs` で profile-schema.md、ADR | 段のモジュール（項目を使う段だけ変える） |
| サブエージェントとの JSON に項目を足す | `contracts.py`、ひな形、`tests/test_contracts.py` と `tests/support.py` | 他の段 |
| 段を1つ足す | `trail.py`（出来事と状態機械）、新しい段のモジュール、`layout.py`、`cli.py`、`status.py`、`tests/test_<段>.py`、`structure_check.py` と本書の許可表、`autoflow/SKILL.md` の表 | 既存の段のモジュール |
| 依頼の種類を足す | `policy.py`（`KINDS` と `check_plan`）、`make docs`、`tests/test_policy.py` | 段のモジュール、ひな形（種類の表は `views.render_kinds` が埋める） |
| スキルの手順を直す | `kit/claude/skills/autoflow*/SKILL.md` か `references/` | 補助 CLI |
| サブエージェントの道具を変える | `kit/claude/agents/<役>.md` | 補助 CLI、ひな形 |
