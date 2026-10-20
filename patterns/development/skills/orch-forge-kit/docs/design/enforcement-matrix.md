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
| structure | 23 |
| test | 2 |
| generator | 0 |
| review | 5 |
| doc | 5 |

## ルールごとの対応

| ルールID | 題名 | 強制 | 仕組み | probe |
|---|---|---|---|---|
| STR-01 | ディレクトリは表の6か所に分けて置く | structure | `scripts/structure_check.py` の `KIT_LAYOUT` と `check_layout` が、`kit/` の下の名前とサブパッケージの有無を確かめる | STR-01-a |
| STR-02 | モジュールを足すときは許可表に行を足し、テストを作る | structure | `check_module_table` が、表に無いモジュールと、モジュールの無い表の行を落とす | STR-02-a |
| STR-03 | 入口は forge.py と cli.main の2つだけにする | structure | `check_init` が、`__init__.py` に docstring 以外の文があると落とす | STR-03-a |
| STR-04 | 生成物は手で編集せず make docs で作り直す | structure | `make docs-check` が生成し直した結果と比べ、違えば落とす | STR-04-a |
| STR-05 | この基盤のスキルとサブエージェントは決まった frontmatter で書く | structure | `check_skills` と `check_agents` が frontmatter、行数、参照、`tools` を確かめる | STR-05-a、STR-05-b |
| STR-06 | バンドルの決まりは bundle.RULES の表だけに書く | structure, test | `check_literals` が `bundle.py` の外の `B` と2桁の番号の文字列を落とし、`tests/test_bundle.py` が `RULES` の全 id に `test_<id の小文字>` があることを確かめる | STR-06-a、STR-06-b |
| DEP-01 | import は許可表の組だけにし、段のモジュールどうしは import しない | structure | `ALLOWED_IMPORTS` の表と `check_dependencies` が、表に無い import を落とす | DEP-01-a |
| DEP-02 | 他のモジュールの _ で始まる名前を使わない | structure | `check_dependencies` が `<モジュール>._<名前>` と `from forge_kit.x import _y` を落とす | DEP-02-a |
| DEP-03 | Python 3.9 の標準ライブラリだけを使う | structure | `check_stdlib` が表に無い import を落とす | DEP-03-a |
| DEP-04 | 副作用に触れるモジュールを表の3つに限る | lint, structure | `check_side_effects` がファイルの書き込み・`subprocess`・`tempfile`・時刻を、ruff の `T201` が `print` を落とす（`cli.py`、`scripts/`、`install.py` だけ `T201` を外す） | DEP-04-a、DEP-04-b |
| NAM-01 | 名前のケースは PEP 8 に従う | lint | ruff の `N` 群（`N802`、`N806` ほか pep8-naming の全ルール） | NAM-01-a |
| NAM-02 | 関数名の先頭の動詞は語彙表から選ぶ | structure, review | `scripts/structure_check.py` の `check_names` が、`SYNONYM_VERBS` の別名で始まる関数を落とす。表の動詞の使い分けと真偽値の名前はレビューで見る | NAM-02-a |
| NAM-03 | JSON のキーは snake_case にし、dataclass のフィールド名と同じにする | structure | `check_json_keys` が、`charter.py`・`design.py`・`contracts.py` の `shape` の呼び出しと `unknown_keys` のキーの綴りを確かめる | NAM-03-a |
| CODE-01 | データは継承しない frozen の dataclass にし、引数を変えない | structure, review | `check_classes` がクラスの形を確かめ、引数を変えていないかはレビューで見る | CODE-01-a |
| CODE-02 | import は forge_kit からの絶対 import にする | lint | ruff の `TID252`（`ban-relative-imports = "all"`）と `I001` | CODE-02-a |
| CODE-03 | 型注釈は全部に書き、mypy の strict を通す | type, lint | mypy の `strict`、ruff の `UP045` | CODE-03-a、CODE-03-b |
| CODE-04 | 関数の大きさは ruff の上限に収める | lint | ruff の `C901`（`max-complexity = 10`）、`PLR0913`、`PLR0912`、`PLR0911`、`PLR0915` | CODE-04-a |
| CODE-05 | モジュールの docstring は必須にし、コメントアウトしたコードを残さない | lint | ruff の `D100`、`D104`、`ERA001` | CODE-05-a、CODE-05-b |
| CODE-06 | ファイル名とエージェント名の文字列は定数で持つ | structure | `check_literals` が、持ち主のモジュール以外にあるファイル名とエージェント名の文字列を落とす。`check_paths` が、`layout.py` の外でファイル名の定数を `/` でつなぐ式を落とす | CODE-06-a、CODE-06-b |
| ERR-01 | 投げる例外は errors.py の4つだけにし、捕まえるのは cli.main だけにする | lint, structure | `check_errors` が errors.py 以外の例外の `raise` を、ruff の `BLE001` が `except Exception` を落とす | ERR-01-a、ERR-01-b |
| ERR-02 | 外から来る JSON は workspace の load_* で検証してから使う | structure | `check_errors` が、`fsops` と `workspace` の外の `fsops.read_json` を落とす | ERR-02-a |
| STATE-01 | 状態はファイルだけで持ち、進み具合はファイルの有無から求める | review | レビュー用スキルの確認項目 | — |
| STATE-02 | サブエージェントと実行役との受け渡しはひな形とファイルの契約だけで行う | test, review | `tests/test_prompts.py` が、全ひな形の置き換えの名前と表の一致を確かめ、置き換えの値に文を書いていないかはレビューで見る | STATE-02-a |
| ASYNC-01 | 並行は proc の2つの関数だけで行う | structure | `check_side_effects` が、`proc.py` 以外の並行のモジュールの import を落とす | ASYNC-01-a |
| OPS-01 | 結果は標準出力、エラーは標準エラーに出し、終了コードは 0 と 1 にする | structure, test, review | `check_side_effects` が、`cli.py` 以外の `sys.stdout`・`sys.stderr`・`sys.exit` を落とし、`tests/test_cli.py` が全体の流れの各段で `status` の行の書き出しを `status.LINE_KINDS` と突き合わせる。人が決める値の置き方はレビューで見る | OPS-01-a、OPS-01-b |
| OPS-02 | 設定は charter.json だけから読み、環境変数を読まない | structure | `check_side_effects` が、`proc.py` 以外の `os.environ`・`os.getenv`・`os.putenv` を落とす | OPS-02-a |
| OPS-03 | 人に見せる文言は日本語で書き、表と数は render の関数で書く | review | レビュー用スキルの確認項目 | — |
| OPS-04 | 評価と構築を進める段の入口は最初に承認済みの charter を読み、.claude に書くのは2つだけにする | structure | `check_entries` が `ENTRIES` の表の関数の最初の文を、`check_calls` が `bundle.place` を呼ぶモジュールを確かめる | OPS-04-a、OPS-04-b |
| OPS-05 | claude -p の引数は execute.command だけで組み立て、権限を広げない | structure, test | `check_literals` が `execute.py` の外の `"-p"` と、`kit/` の全ファイルの禁止の文字列を落とし、`tests/test_execute.py` が表の引数と順番を確かめる | OPS-05-a、OPS-05-b |
| TEST-01 | モジュールごとに tests/test_<モジュール>.py と <名前>Test クラスを置く | structure | `check_tests` が、テストのファイルとクラスの有無と、対応の無いテストを落とす | TEST-01-a |
| TEST-02 | モックを使わず、support.py の部品と本物の git で確かめる | structure | `check_tests` が `tests/` の `unittest.mock` と `mock` の import を落とす | TEST-02-a |
| TEST-03 | 新しい名前を足したら、その値を作る段のテストに test_<名前> を1つ足す | review | レビュー用スキルの確認項目 | — |
| PROC-01 | 段を足すときは契約から入口の順に作る | doc | 実装用スキルの「作る順序」 | — |
| PROC-02 | 波及の対応表の組は一緒に変える | test, review | `tests/test_score.py` が `CALCULATORS` と `catalog.METRICS` の一致を、`tests/test_charter.py` と `tests/test_design.py` がスキーマの文書の例の検証を確かめ、残りの組はレビューで見る | PROC-02-a |
| PROC-03 | 道具の版は Makefile で固定し、上げるときは ADR を書く | doc | 実装用スキルの「依頼の振り分け」 | — |
| PROC-04 | ルールは ADR から probe の順で変える | doc | AGENTS.md の「ルールを変えたいとき」 | — |
| PROC-05 | 完了の条件は make check が通ること | doc | AGENTS.md の「完了の条件」と実装用スキルのチェックリスト | — |
| PROC-06 | charter と設計の形を変えたら SCHEMA_VERSION を上げる | review | レビュー用スキルの確認項目 | — |
| PROC-07 | 人が決める場面は SKILL.md に書き、値の種類で聞き方を分ける | structure | `check_skills` が、節と AskUserQuestion の記述の有無を確かめる | PROC-07-a |
| TOOL-01 | 整形は ruff format に任せる | format | `make format-check`（`ruff format --check`） | TOOL-01-a |
| TOOL-02 | 編集の直後は hooks、完了の前は make check を回す | doc | AGENTS.md の「コマンド」と実装用スキルの完了前チェックリスト | — |
| TOOL-03 | 抑止コメントを書かない | structure | `make guard`（`.foundation/bin/guard.py`） | TOOL-03-a |
| TOOL-04 | 保護ファイルを変えない | review | レビュー用スキルの確認項目 | — |
| TOOL-05 | 配布物は Python 3.9 で動く書き方にする | type | mypy の `python_version = 3.9` | TOOL-05-a |

## 機械で縛っていないルール

| ルールID | 題名 | 強制 | 機械化しない理由 |
|---|---|---|---|
| STATE-01 | 状態はファイルだけで持ち、進み具合はファイルの有無から求める | review | 新しいファイルが状態を表すかどうかは、ファイルの意味の判断が要る |
| OPS-03 | 人に見せる文言は日本語で書き、表と数は render の関数で書く | review | 文言が人に見せるものか、内部の値かは、字面では見分けられない |
| TEST-03 | 新しい名前を足したら、その値を作る段のテストに test_<名前> を1つ足す | review | どの名前が依頼で足したものかは、差分の意味の判断が要る |
| PROC-01 | 段を足すときは契約から入口の順に作る | doc | 作る順序は、出来上がった差分に痕跡が残らない |
| PROC-03 | 道具の版は Makefile で固定し、上げるときは ADR を書く | doc | 版を上げる手順は、出来上がった差分では `Makefile` の1行にしか現れない |
| PROC-04 | ルールは ADR から probe の順で変える | doc | 変えた順序は差分に残らない |
| PROC-05 | 完了の条件は make check が通ること | doc | 報告の中身は差分に残らない |
| PROC-06 | charter と設計の形を変えたら SCHEMA_VERSION を上げる | review | キーの意味が変わったかどうかは、字面では判定できない |
| TOOL-02 | 編集の直後は hooks、完了の前は make check を回す | doc | hooks の設定は `.claude/settings.json`（保護ファイル）にあり、回したかどうかは差分に残らない |
| TOOL-04 | 保護ファイルを変えない | review | hooks はエージェントの編集にだけ確認を求め、人の編集は止められないため、差分のレビューで確かめる |

## 対象外とした軸

| 軸 | 理由 |
|---|---|
