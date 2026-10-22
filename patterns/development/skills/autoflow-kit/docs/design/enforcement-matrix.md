<!-- このファイルは rules_check.py が rules.md と probes.json から生成する。手で編集しない。 -->

# 強制の対応表

ルールごとに、どの仕組みで守らせているかを示す。段の強さは type > format > lint・structure・test > generator > review > doc の順である。
probe が実際に検査で落ちるかの結果は `.foundation/probe-results.json` にある（`violation_probe.py` が書く）。

## 集計（各ルールの最も強い段で数える）

| 段 | 件数 |
|---|---|
| type | 2 |
| format | 1 |
| lint | 6 |
| structure | 27 |
| test | 3 |
| generator | 0 |
| review | 5 |
| doc | 5 |

## ルールごとの対応

| ルールID | 題名 | 強制 | 仕組み | probe |
|---|---|---|---|---|
| STR-01 | ディレクトリは表の6か所に分けて置く | structure | `scripts/structure_check.py` の `KIT_LAYOUT` と `check_layout` が、`kit/` の下の名前とサブパッケージの有無を確かめる | STR-01-a |
| STR-02 | モジュールを足すときは許可表に行を足し、テストを作る | structure | `check_module_table` が、表に無いモジュールと、モジュールの無い表の行を落とす | STR-02-a |
| STR-03 | 入口は autoflow.py と cli.main の2つだけにする | structure | `check_init` が、`__init__.py` に docstring 以外の文があると落とす | STR-03-a |
| STR-04 | 生成物は手で編集せず make docs で作り直す | structure | `make docs-check` が生成し直した結果と比べ、違えば落とす | STR-04-a |
| STR-05 | この基盤のスキルとサブエージェントは決まった frontmatter で書く | structure | `check_skills` と `check_agents` が frontmatter、行数、参照、`tools` を確かめる | STR-05-a、STR-05-b |
| DEP-01 | import は許可表の組だけにし、段のモジュールどうしは import しない | structure | `ALLOWED_IMPORTS` の表と `check_dependencies` が、表に無い import を落とす | DEP-01-a |
| DEP-02 | 他のモジュールの _ で始まる名前を使わない | structure | `check_dependencies` が `<モジュール>._<名前>` と `from autoflow_kit.x import _y` を落とす | DEP-02-a |
| DEP-03 | Python 3.9 の標準ライブラリだけを使う | structure | `check_stdlib` が表に無い import を落とす | DEP-03-a |
| DEP-04 | 副作用に触れるモジュールを表の3つに限る | lint, structure | `check_side_effects` がファイルの書き込み・`subprocess`・`tempfile`・時刻を、ruff の `T201` が `print` を落とす（`cli.py`、`scripts/`、`install.py` だけ `T201` を外す） | DEP-04-a、DEP-04-b |
| NAM-01 | 名前のケースは PEP 8 に従う | lint | ruff の `N` 群（`N802`、`N806` ほか pep8-naming の全ルール） | NAM-01-a |
| NAM-02 | 関数名の先頭の動詞は語彙表から選ぶ | structure, review | `scripts/structure_check.py` の `check_names` が、`SYNONYM_VERBS` の別名で始まる関数を落とす。表の動詞の使い分けと真偽値の名前はレビューで見る | NAM-02-a |
| NAM-03 | JSON のキーは snake_case にし、dataclass のフィールド名と同じにする | structure | `check_json_keys` が、全モジュールの `shape` の呼び出しと `unknown_keys` のキーの綴りを確かめる | NAM-03-a |
| CODE-01 | データは継承しない frozen の dataclass にし、引数を変えない | structure, review | `check_classes` がクラスの形を確かめ、引数を変えていないかはレビューで見る | CODE-01-a |
| CODE-02 | import は autoflow_kit からの絶対 import にする | lint | ruff の `TID252`（`ban-relative-imports = "all"`）と `I001` | CODE-02-a |
| CODE-03 | 型注釈は全部に書き、mypy の strict を通す | type, lint | mypy の `strict`、ruff の `UP045` | CODE-03-a、CODE-03-b |
| CODE-04 | 関数の大きさは ruff の上限に収める | lint | ruff の `C901`（`max-complexity = 10`）、`PLR0913`、`PLR0912`、`PLR0911`、`PLR0915` | CODE-04-a |
| CODE-05 | モジュールの docstring は必須にし、コメントアウトしたコードを残さない | lint | ruff の `D100`、`D104`、`ERA001` | CODE-05-a、CODE-05-b |
| CODE-06 | ファイル名とエージェント名の文字列は定数で持つ | structure | `check_literals` が、持ち主のモジュール以外にあるファイル名とエージェント名の文字列を落とす。`check_paths` が、`layout.py` の外でファイル名の定数を `/` でつなぐ式を落とす | CODE-06-a、CODE-06-b |
| ERR-01 | 投げる例外は errors.py の4つだけにし、捕まえるのは cli.main だけにする | lint, structure | `check_errors` が errors.py 以外の例外の `raise` を、ruff の `BLE001` が `except Exception` を落とす | ERR-01-a、ERR-01-b |
| ERR-02 | 外から来る JSON は workspace の load_* で検証してから使う | structure | `check_errors` が、`fsops` と `workspace` の外の `fsops.read_json`・`fsops.read_lines` を落とす | ERR-02-a |
| STATE-01 | 進み具合は trail.jsonl だけに書き、次の段はそこから求める | review | レビュー用スキルの確認項目 | — |
| STATE-02 | サブエージェントとの受け渡しはひな形とファイルの契約だけで行う | test, review | `tests/test_prompts.py` が、全ひな形の置き換えの名前と表の一致を確かめ、置き換えの値に文を書いていないかはレビューで見る | STATE-02-a |
| ASYNC-01 | 補助 CLI は並行処理を書かない | structure | `check_side_effects` が、並行のモジュールの import を落とす | ASYNC-01-a |
| OPS-01 | 結果は標準出力、エラーは標準エラーに出し、status の行は決まった書き出しにする | structure, test | `check_side_effects` が、`cli.py` 以外の `sys.stdout`・`sys.stderr`・`sys.exit` を落とし、`tests/test_cli.py` が全体の流れの各段で `status` の行の書き出しを `status.LINE_KINDS` と突き合わせる | OPS-01-a、OPS-01-b |
| OPS-02 | 実行の設定は開始時のプロファイルの写しだけから読み、環境変数を読まない | structure | `check_side_effects` が `proc.py` 以外の `os.environ`・`os.getenv`・`os.putenv` を、`check_calls` が `setup`・`intake`・`workspace` の外の `workspace.approved_profile` を落とす | OPS-02-a、OPS-02-b |
| OPS-03 | 人に見せる文言は日本語で書き、表と数は render の関数で書く | review | レビュー用スキルの確認項目 | — |
| OPS-04 | 配布物は権限を広げず、サブエージェントの書き込み先を示す | structure | `check_forbidden` が `kit/` の全ファイルの禁止の文字列を落とす | OPS-04-a |
| OPS-05 | git への書き込みは表の関数と段だけで行い、push しない | structure | `check_calls` が表の外からの呼び出しを、`check_forbidden` が `push` の文字列を落とす | OPS-05-a |
| GATE-01 | 関所の条件と表は policy.py だけに書く | structure, test | `check_literals` が `policy.py` の外の `H0`〜`H3` の文字列を落とし、`tests/test_policy.py` の `test_rules_have_tests` が全規則の id に `test_<id>` があることを、`test_rule_ids_match_functions` が id と判定の関数名の対応を確かめる | GATE-01-a、GATE-01-b、GATE-01-c |
| GATE-02 | 配布するスキルは人の関所の節を持ち、答えが無いときは承認にしない | structure | `check_skills` が、節と AskUserQuestion の記述と決まった1文の有無を確かめる | GATE-02-a |
| GATE-03 | 段の入口は最初に context.begin を呼び、番でない段を動かさない | structure | `check_entries` が `ENTRIES` の表の関数の最初の文を確かめる | GATE-03-a |
| GATE-04 | 検査コマンドは verify だけが実行し、証拠は tree に結び付ける | structure, test | `check_calls` が `verifying` の外の `proc.shell` を落とし、`tests/test_trail.py` の `test_changed_after_verify` が、証拠の後に tree が変わると次の段が `verify` になることを確かめる | GATE-04-a、GATE-04-b |
| GATE-05 | 人の決定は decide だけが記録し、コミットは承認した tree と一致するときだけ行う | structure, test | `check_calls` が `deciding` の外の `trail.decided` を落とし、`tests/test_handoff.py` の `test_commit_requires_same_tree` が、承認の後に tree が変わるとコミットしないことを確かめる | GATE-05-a、GATE-05-b |
| GATE-06 | リスクの段は規則と AI の大きい方にし、AI は段を下げない | test | `tests/test_policy.py` の `test_merge_tier` が、全ての組で結果が両方以上であることを確かめる | GATE-06-a |
| GATE-07 | 読み取りだけの役の前後で tree を比べ、変わっていれば止める | test | `tests/test_reviewing.py` の `test_tree_changed_during_review` が、探索役の間に作業ツリーが変わると `review-collect` が止まることを確かめる | GATE-07-a |
| TEST-01 | モジュールごとに tests/test_<モジュール>.py と <名前>Test クラスを置く | structure | `check_tests` が、テストのファイルとクラスの有無と、対応の無いテストを落とす | TEST-01-a |
| TEST-02 | モックを使わず、support.py の部品と本物の git で確かめる | structure | `check_tests` が `tests/` の `unittest.mock` と `mock` の import を落とす | TEST-02-a |
| TEST-03 | 新しい名前を足したら、表の置き場に test_<名前> を1つ足す | review | レビュー用スキルの確認項目 | — |
| PROC-01 | 段を足すときは記録から入口の順に作る | doc | 実装用スキルの「作る順序」 | — |
| PROC-02 | 波及の対応表の組は一緒に変える | structure, review | `check_templates` が `prompts.TEMPLATES` とひな形のファイルの一致を、`check_agents` が `contracts.AGENTS` と定義の一致を確かめ、残りの組はレビューで見る | PROC-02-a |
| PROC-03 | 道具の版は Makefile で固定し、上げるときは ADR を書く | doc | 実装用スキルの「依頼の振り分け」 | — |
| PROC-04 | ルールは ADR から probe の順で変える | doc | AGENTS.md の「ルールを変えたいとき」 | — |
| PROC-05 | 完了の条件は make check が通ること | doc | AGENTS.md の「完了の条件」と実装用スキルのチェックリスト | — |
| PROC-06 | プロファイルの形を変えたら SCHEMA_VERSION を上げる | review | レビュー用スキルの確認項目 | — |
| TOOL-01 | 整形は ruff format に任せる | format | `make format-check`（`ruff format --check`） | TOOL-01-a |
| TOOL-02 | 編集の直後は hooks、完了の前は make check を回す | doc | AGENTS.md の「コマンド」と実装用スキルの完了前チェックリスト | — |
| TOOL-03 | 抑止コメントを書かない | structure | `make guard`（`.foundation/bin/guard.py`） | TOOL-03-a |
| TOOL-04 | 保護ファイルを変えない | review | レビュー用スキルの確認項目 | — |
| TOOL-05 | 配布物は Python 3.9 で動く書き方にする | type | mypy の `python_version = 3.9` | TOOL-05-a |

## 機械で縛っていないルール

| ルールID | 題名 | 強制 | 機械化しない理由 |
|---|---|---|---|
| STATE-01 | 進み具合は trail.jsonl だけに書き、次の段はそこから求める | review | 新しいファイルが進み具合を表すかどうかは、ファイルの意味の判断が要る |
| OPS-03 | 人に見せる文言は日本語で書き、表と数は render の関数で書く | review | 文言が人に見せるものか、内部の値かは、字面では見分けられない |
| TEST-03 | 新しい名前を足したら、表の置き場に test_<名前> を1つ足す | review | どの名前が依頼で足したものかは、差分の意味の判断が要る |
| PROC-01 | 段を足すときは記録から入口の順に作る | doc | 作る順序は、出来上がった差分に痕跡が残らない |
| PROC-03 | 道具の版は Makefile で固定し、上げるときは ADR を書く | doc | 版を上げる手順は、出来上がった差分では `Makefile` の1行にしか現れない |
| PROC-04 | ルールは ADR から probe の順で変える | doc | 変えた順序は差分に残らない |
| PROC-05 | 完了の条件は make check が通ること | doc | 報告の中身は差分に残らない |
| PROC-06 | プロファイルの形を変えたら SCHEMA_VERSION を上げる | review | キーの意味が変わったかどうかは、字面では判定できない |
| TOOL-02 | 編集の直後は hooks、完了の前は make check を回す | doc | hooks の設定は `.claude/settings.json`（保護ファイル）にあり、回したかどうかは差分に残らない |
| TOOL-04 | 保護ファイルを変えない | review | hooks はエージェントの編集にだけ確認を求め、人の編集は止められないため、差分のレビューで確かめる |

## 対象外とした軸

| 軸 | 理由 |
|---|---|
