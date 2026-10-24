# skill-harness2-kit のアーキテクチャ

この文書は、構造そのものと、その構造を選んだ理由を説明する。個々のルールの全文は [rules.md](rules.md) にある。harness2 のどの仕組みをどこに移したかは [research.md](research.md) の「harness2 の仕組み」の表にある。

## 1. 前提

skill-harness2-kit は、利用者のリポジトリにある Claude Code スキル（以下、対象スキル）1つを、google-research/harness2 の方法で改善する道具である。harness2 の方法は「モデルの重みを変えずに、モデルの周り（harness）だけを、正解を使わずに直す」もので、この基盤では harness を対象スキルのディレクトリに読み替える。

方法は、1つのタスクごとに次の5段を回す。

1. **基準の実行**：今のスキルでタスクを k 回解かせる。正否は見ず、振る舞いの証拠として使う
2. **提案**：2つの次元の編集者が、証拠を読んでスキルの木を直す。INV は「どう働くか」（手順、道具、完了の確かめ方）、DOM は「実務家が何を知っているか」を受け持つ
3. **試行**：各候補で同じタスクを1回解かせ、基準の実行と比べられるようにする
4. **合成**：全候補の差分・実行・成果物を読み、根拠のある編集だけを1つにまとめる。元のまま（KEEP_BASE）も正解である
5. **選択と振り返り**：完成品の成果物を匿名で比べて1つを選び、編集ごとの効果と次のタスクへ移す教訓をライブラリに残す

この方法を動かすうえで、次の4つの性質を構造の前提にした。

1. **すべてのモデルの呼び出しは `claude -p` で、閉じ込めて動かす**。実行は使い捨ての作業場所（sandbox）に候補のスキルを入れて動かし、利用者のスキルやプラグインを混ぜない。編集者は Bash を持たず、作業場所の外を読めない。閉じ込めのフラグは `runner` だけが組み立てる（OPS-05、[ADR 0003](adr/0003-claude-p-as-the-only-channel.md)）
2. **方法は答えを見ない**。採点の基準はどのプロンプトにも無く、測定の語や採点の印は機械で拒む。事後の検査（`judge`）は選択の後にだけ動き、方法のモジュールから呼べない（STATE-04、DEP-01）
3. **費用が大きく、途中で止まる**。1タスク・1モードで実行 4k 回、編集のセッション 3k 回を使う。そのため予算を承認の前に `plan.md` で見せ、台帳で恒等式を確かめ（STATE-07）、完了の記録から続きを再開する（STATE-01）
4. **最後の判断は人が行う**。選ばれた候補を対象スキルへ書き込むのは、人が差分を見て `adopt --confirm` を実行したときだけである（PROC-07、OPS-04）

この基盤でよく起きる変更は、プロンプトの文言を直す、検証の項目を足す、`claude -p` のフラグを変える、プロファイルに項目を足す、の4つである。どれも触るファイルが予測できるように、補助 CLI を「段のモジュール」と「共有のモジュール」に分け、段どうしの依存を禁じた（DEP-01）。プロンプトの文はひな形だけに置き（STATE-02）、検証の項目は `validate` だけに置く（STATE-06）。

## 2. ディレクトリ構造

```text
skill-harness2-kit/
├── kit/                          配布物の正本。install.py が利用者のリポジトリへ写す（STR-01）
│   ├── .h2/                      → 利用者のリポジトリの .h2/
│   │   ├── h2.py                 補助 CLI の入口（STR-03）
│   │   ├── h2_kit/               補助 CLI のモジュール。平らに並べる（STR-01、STR-02）
│   │   ├── templates/prompts/    編集・合成・選択・振り返りのプロンプトのひな形（STATE-02）
│   │   └── .gitignore            実行の記録（targets/*/runs/）を git から外す
│   └── claude/                   → 利用者のリポジトリの .claude/
│       └── skills/skill-harness2/  配布するスキル。references/ にプロファイルとタスクの書き方、結果の読み方（STR-04）
├── install.py                    配布物を利用者のリポジトリに入れる
├── scripts/structure_check.py    構造検査（structure の全ルール）
├── tests/                        テスト。test_<モジュール>.py と support.py（TEST-01、TEST-02）
│   └── fixtures/                 偽の claude（fake_claude.py）と見本のスキル
├── docs/design/                  設計文書
├── .foundation/                  ルールの検査の道具と probe（保護ファイル）
├── AGENTS.md、CLAUDE.md          人とエージェントの入口
└── Makefile、pyproject.toml      検査のコマンドと設定（保護ファイル）
```

利用者のリポジトリに入れた後は、次の形になる。

```text
<利用者のリポジトリ>/
├── .claude/skills/skill-harness2/
└── .h2/
    ├── h2.py、h2_kit/、templates/、.gitignore
    └── targets/<target>/
        ├── profile.json                    プロファイル（人と決める）
        ├── tasks/<id>/task.md              依頼文（人と決める）
        ├── tasks/<id>/workspace/           作業の材料。実行のたびに sandbox へ写す
        ├── tasks/<id>/checks.json          事後の検査（任意。judging と planning だけが読む）
        ├── plan.md                         check が書く予算と順番
        ├── approval.json                   approve が書く（ラウンド、ハッシュ、スキルの指紋）
        ├── adopted.json                    adopt が書く採用の記録
        └── runs/r<N>/                      ラウンドの記録（git から外す）
            ├── base-skill/                 承認時のスキルの木（H0）
            ├── library/<モード>/           前のタスクの選ばれた木と教訓（INDEX.md）
            └── <task>/
                ├── base/rollouts/base<i>/  基準の実行（モードで共有）
                ├── <モード>/harnesses/<label>/   候補と完成品のスキルの木
                ├── <モード>/rollouts/<label>/    候補と完成品の実行
                ├── <モード>/sessions/<label>.a<n>/  編集のセッションの証拠と返答（監査用）
                ├── <モード>/decisions/<label>.md   段の notes（落ちた段はエラー）。後の段と show が読む
                ├── <モード>/library/       このタスクより前のタスクの分だけのライブラリの写し
                ├── <モード>/selection/、reflection/
                ├── <モード>/summary.json   モードの完了の記録（台帳、選択、編集の結果）
                └── judged.json             judge が書く
```

1つの実行のディレクトリ（`rollouts/<label>/`）には、`stream.jsonl`（`claude -p` の出力そのまま）、`stderr.txt`、`trajectory.md`（`[ACTION]`・`[OBSERVATION]`・`[ERROR]` の軌跡）、`reply.md`（最後の返答）、`deliverable.md`（返答と、材料から変わったファイル。差分は Python の difflib で作り、git は使わない）、`output/`（実行の後の作業場所）、`run.json`（完了の記録と指紋。最後に書く）を置く。

## 3. 依存の許可表

`h2_kit` のモジュールごとに、import してよいモジュールを示す。表に無い組は全部禁止で、構造検査で強制する（ルールID：DEP-01）。この表は `scripts/structure_check.py` の `SHARED`・`STAGES`・`ENTRY` と1対1で対応する。モジュールが30あり行列では読めないため、行ごとに許可する相手を並べる。

### 共有のモジュール：土台

| from | import してよいもの | 役割 |
|---|---|---|
| `errors` | なし | 利用者が直せるエラーの型（ERR-01） |
| `render` | なし | Markdown の部品（表、箇条書き、金額、囲み） |
| `parallel` | なし | 並行の実行と、入力の順での結果（ASYNC-01） |
| `contracts` | なし | モデルの返答のタグ（`<notes>`、`<why>`、`choice`、振り返りの表）の読み取り（STATE-02） |
| `transcript` | なし | `stream.jsonl` の読み取りと軌跡の Markdown |
| `layout` | `errors` | 作業場所のパス、ファイル名、ラベル、モードの定数（CODE-06） |
| `fsops` | `errors` | ファイルの読み書き・コピー・削除、一時ディレクトリ、ハッシュ（DEP-04） |
| `proc` | `errors` | 外部コマンド（`claude`、事後の検査）と環境変数（DEP-04、OPS-02） |
| `ledger` | `layout`、`errors` | 台帳と恒等式 R = 4k、P = 3k（STATE-07） |
| `skilltree` | `fsops`、`layout` | スキルの木の読み書き、編集面、frontmatter、差分、指紋、多様性 |
| `guards` | `fsops`、`skilltree`、`errors` | 測定の語、採点の印、`leak_globs` の拒否（STATE-04） |
| `profile` | `guards`、`layout`、`errors` | profile.json の型と検証（STATE-03、STATE-04、PROC-06） |
| `validate` | `guards`、`layout`、`skilltree` | 候補のスキルの木の検証と、参照の名指しの自動の直し（STATE-06） |
| `prompts` | `fsops`、`layout`、`errors` | ひな形からプロンプトを作る（STATE-02） |

### 共有のモジュール：方法

| from | import してよいもの | 役割 |
|---|---|---|
| `workspace` | `fsops`、`layout`、`profile`、`skilltree`、`errors` | 作業場所のファイルを読み、検証済みの型と進み具合を返す（書かない。STATE-01、ERR-02） |
| `runner` | `fsops`、`layout`、`proc`、`profile`、`transcript`、`workspace` | `claude -p` のコマンド行と、編集のセッションの実行・キャッシュ・回収（OPS-05） |
| `sandbox` | `fsops`、`layout`、`skilltree` | 実行の作業場所を作り、スキルを入れ、後の差分を取る |
| `rollout` | `fsops`、`layout`、`profile`、`render`、`runner`、`sandbox`、`skilltree`、`transcript`、`workspace` | 1回の実行と、その完了の記録・再利用 |
| `context` | `fsops`、`guards`、`layout`、`render`、`rollout`、`skilltree` | 編集のセッションに渡す証拠の木と道案内（STATE-03） |
| `library` | `contracts`、`fsops`、`guards`、`layout`、`render`、`skilltree` | 前のタスクの選ばれた木と教訓 |
| `recursion` | `context`、`contracts`、`fsops`、`guards`、`layout`、`ledger`、`parallel`、`profile`、`prompts`、`render`、`rollout`、`runner`、`skilltree`、`validate`、`workspace`、`errors` | 提案・試行・合成の段（並列モードと逐次モード） |
| `selection` | `context`、`contracts`、`layout`、`profile`、`prompts`、`rollout`、`runner`、`errors` | 完成品の盲検の選択（STATE-05） |
| `reflection` | `context`、`contracts`、`fsops`、`layout`、`profile`、`prompts`、`rollout`、`runner`、`skilltree`、`errors` | 編集ごとの効果と教訓（ライブラリへの記録は `execution` が `library` で行う） |

### 段のモジュール

段のモジュールは、共有のモジュールだけを import し、他の段のモジュールを import しない。

| from | サブコマンド | import してよいもの |
|---|---|---|
| `planning` | `init`、`check`、`approve` | `fsops`、`guards`、`layout`、`ledger`、`profile`、`render`、`skilltree`、`validate`、`workspace`、`errors` |
| `status` | `status` | `layout`、`workspace`、`errors` |
| `execution` | `run` | `context`、`fsops`、`layout`、`library`、`recursion`、`reflection`、`render`、`rollout`、`selection`、`skilltree`、`workspace`、`errors` |
| `results` | `show` | `fsops`、`layout`、`ledger`、`render`、`skilltree`、`workspace`、`errors` |
| `adoption` | `adopt` | `fsops`、`layout`、`render`、`skilltree`、`validate`、`workspace`、`errors` |
| `judging` | `judge` | `fsops`、`layout`、`proc`、`render`、`workspace`、`errors` |

### 入口

| from | import してよいもの |
|---|---|
| `cli` | 段のモジュールの全部、`layout`、`errors` |

### 副作用の置き場

依存の向きとは別に、副作用に触れてよいモジュールを限る（DEP-04、ASYNC-01、OPS-01、OPS-02）。

| 副作用 | モジュール |
|---|---|
| ファイルの書き込み・削除・コピー、一時ディレクトリ、JSON の読み書き | `fsops` |
| 外部コマンド（`claude`、事後の検査）、環境変数 | `proc` |
| スレッド | `parallel` |
| 時刻、画面への出力、終了コード | `cli` |

## 4. 公開面

| モジュール | 外から使ってよいもの | 触れなくする仕組み |
|---|---|---|
| 補助 CLI 全体 | `h2.py` のサブコマンド（`init`、`check`、`approve`、`status`、`run`、`show`、`adopt`、`judge`） | スキルはサブコマンドだけを呼ぶ。`__init__.py` は docstring だけにする（STR-03） |
| 各モジュール | `_` で始まらない名前 | 構造検査（DEP-02） |
| 編集のセッション | `context/` の証拠（読むだけ）と `context/harness/`（編集してよい）、返答の `<notes>` | `--restricted --tools Read,Edit,Write,Glob,Grep` で作業場所に閉じ込める（OPS-05）。編集面の外のファイルは捨てる（STATE-06） |
| 選択役・振り返り役 | `context/` の証拠（読むだけ）と、返答の決まった形 | `--tools Read,Glob,Grep`（OPS-05）、`contracts.parse_*` の検証 |
| 実行（rollout） | sandbox の作業場所と、そこに入れた候補のスキル | `--setting-sources project --strict-mcp-config`、プロファイルの `rollout.tools`（OPS-05） |

## 5. データの流れ

### 準備と承認（skill-harness2 の手順 A）

```text
人 ⇄ skill-harness2（AskUserQuestion）
      → init <target> --skill <パス>（profile.json のひな形と tasks/）
      → プロファイルとタスクを書く（references/profile-guide.md、references/task-guide.md）
      → check（検証、順番、予算 → plan.md）→ 人の承認 → approve（ハッシュとスキルの指紋を記録）
```

承認の後に profile.json か tasks を1文字でも変えると、ハッシュが合わなくなり、`run`・`adopt`・`judge` は止まる（OPS-04）。対象スキルを承認の後に変えた場合も、`run` と `adopt` は止まる。

### 1つのタスクの改善（run の中。タスクはプロファイルの種で決めた順に流す）

```text
基準の実行   base1..k を H0 で実行する（モードで共有）
並列モード   inv1..k と dom1..k が H0 と基準の実行を読んで提案する
             → 検証（落ちたら1回だけ差し戻し、それでも落ちたら H0 に戻す）→ 2k 個の候補を1回ずつ実行
             → agg1..k がそれぞれ独立に全候補を読んで合成する → 検証 → k 個の完成品を1回ずつ実行
逐次モード   t = 1..k の順に、inv<t> と dom<t> が今の版 c<t-1>（c0 = H0）と、それまでの全候補・全版を読んで提案
             → 検証 → 2 個の候補を実行 → c<t> が合成する（前に捨てた候補の採り直しや前の版の再現も許す）
             → 検証 → c<t> を実行し、次の段の入力にする
台帳         実行 4k、編集のセッション 3k を確かめる（STATE-07）
選択         成果物を出した完成品だけを、匿名の ID で比べて1つを選ぶ（k = 1 なら選択役を起動しない）
振り返り     選ばれた木の編集ごとに helped / hurt / no observed effect / confounded を付け、
             教訓を最大1つ書く → ライブラリに木と教訓を残す（後のタスクが読む）
要約         summary.json を書く（モードの完了の記録）
```

各タスクは H0 から始め、前のタスクで分かったことはライブラリを通してだけ伝わる（harness2 の `run_domain` と同じ）。ライブラリの中身は後のタスクにとって「確かめ直す仮説」であり、プロンプトにもそう書く。

### 結果を見て採用する（skill-harness2 の手順 C）

```text
show    → タスク・モードごとに、選ばれた候補、選んだ理由、元との差分、合成の notes、振り返り、台帳、多様性、
          確認の符号と採用のコマンドを出す
人      → 採用する候補か「採用しない」かを決める（skill-harness2 が AskUserQuestion で聞く）
adopt   → 承認時のスキルから変わっていないこと、確認の符号が一致することを確かめ、対象スキルを書き換える
judge   → （任意）checks.json のコマンドを、選ばれた完成品と基準の実行の成果物で動かし、結果を並べる
```

## 6. 変更シナリオ表

| 変更 | 触るファイル | 触らないもの |
|---|---|---|
| プロンプトの文言を直す | `templates/prompts/<名前>.md` | Python のコード（置き換えの名前を変えるなら `prompts.py` の表も） |
| ひな形の置き換えの値を1つ足す | `templates/prompts/<名前>.md`、`prompts.py`（TEMPLATES）、値を作るモジュール、`tests/test_prompts.py` | 他の段のモジュール |
| 候補の検証の項目を1つ足す | `validate.py`、`tests/test_validate.py`、`templates/prompts/_surface.md`、rules.md の STATE-06（ルールの変更） | `recursion.py`（`check_tree` の問題の一覧をそのまま差し戻すため） |
| `claude -p` のフラグを変える | `runner.py`、`tests/test_runner.py`、research.md、rules.md の OPS-05 | 段のモジュール、`rollout.py` |
| profile.json に項目を足す | `profile.py`（型と parse）、`profile.SCHEMA_VERSION`、`planning.py`（plan.md）、`references/profile-guide.md`、`tests/test_profile.py`、ADR | 項目を使わないモジュール |
| 新しいモードを足す | `layout.py`（モード名とラベル）、`recursion.py`、`selection.py`（候補の集め方）、`tests/test_recursion.py`、ADR | `runner.py`、`rollout.py`、`context.py` |
| 段（サブコマンド）を1つ足す | 新しい段のモジュール、`layout.py`（置き場）、`workspace.py`（読み込み）、`status.py`、`cli.py`、`tests/test_<段>.py`、`tests/test_cli.py`、`structure_check.py` と本書の許可表、skill-harness2 の SKILL.md の表 | 既存の段のモジュール |
| スキルの手順を直す | `kit/claude/skills/skill-harness2/SKILL.md` か `references/` | 補助 CLI |
| 証拠の木に1種類の資料を足す | `context.py`、`layout.py`（ファイル名）、`templates/prompts/` の道案内、`tests/test_context.py` | 段のモジュール |
