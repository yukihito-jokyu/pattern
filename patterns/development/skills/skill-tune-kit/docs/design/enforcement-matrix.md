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
| structure | 22 |
| test | 3 |
| generator | 0 |
| review | 5 |
| doc | 4 |

## ルールごとの対応

| ルールID | 題名 | 強制 | 仕組み | probe |
|---|---|---|---|---|
| STR-01 | ファイルは表の場所に置き、表に無い場所を作らない | structure | `scripts/structure_check.py` の `LAYOUT` 表が `kit/` と `tests/` の全ファイルのパスを照合する | STR-01-a |
| STR-02 | モジュールは構造検査の表に登録し、置き場を決定表で決める | structure, review | 登録の無いモジュールは構造検査が落とす。関数の置き場はレビューで確かめる | STR-02-a |
| STR-03 | 入口は tune.py と cli.main の2つだけにする | structure | `__init__.py` の中身と `__main__` の判定を構造検査が照合する | STR-03-a |
| STR-04 | 生成物は手で編集せず make docs で作り直す | structure | `make check` の `docs-check` が再生成して差分が無いことを確かめる | STR-04-a |
| STR-05 | スキルとサブエージェントは決まった frontmatter で書く | structure | 構造検査が frontmatter と行数を照合し、エージェントの名前を `contracts.AGENTS` と突き合わせる | STR-05-a、STR-05-b |
| DEP-01 | import は許可表の組だけにし、段のモジュールどうしは import しない | structure | `scripts/structure_check.py` の `SHARED`・`STAGES`・`ENTRY` の表で import を照合する | DEP-01-a |
| DEP-02 | 他のモジュールの _ で始まる名前を使わない | structure | 構造検査が属性の参照と import を照合する | DEP-02-a |
| DEP-03 | Python 3.9 の標準ライブラリと tune_kit だけを import する | structure | 構造検査が import を `STDLIB` 表と照合する | DEP-03-a |
| DEP-04 | 副作用に触れるモジュールを表の3つに限る | lint, structure | 構造検査が書き方を照合する。`print` は ruff の `T201` でも落とす | DEP-04-a、DEP-04-b |
| NAM-01 | 名前のケースは PEP 8 に従う | lint | ruff の `N801`、`N802`、`N806`、`N815` | NAM-01-a |
| NAM-02 | 関数名は動詞表の語で始め、段の公開関数はサブコマンド名にする | structure | 構造検査が関数名の先頭の語を表と照合する | NAM-02-a |
| NAM-03 | JSON のキーは snake_case にし、dataclass のフィールド名と同じにする | structure | 構造検査が `plan.py`・`contracts.py` の `data.get("…")` と `data["…"]` のキーを照合する | NAM-03-a |
| CODE-01 | データは継承しない frozen の dataclass にし、引数を変えない | structure, review | クラスの形は構造検査が照合する。引数を書き換えないことはレビューで確かめる | CODE-01-a |
| CODE-02 | import は from tune_kit import <モジュール> にし、先頭に annotations を書く | lint, structure | 構造検査が import の形と先頭の文を照合する。相対 import は ruff の `TID252`、並びは `I001` で落とす | CODE-02-a、CODE-02-b |
| CODE-03 | 型注釈を全部に書き、mypy の strict を通す | type | `make typecheck`（mypy strict） | CODE-03-a |
| CODE-04 | 関数の大きさは ruff の上限に収める | lint | `pyproject.toml` の `[tool.ruff.lint]` の上限 | CODE-04-a |
| CODE-05 | モジュールの docstring は必須にし、コメントアウトしたコードを残さない | lint, review | ruff の `D100`、`D104`、`ERA001`。コメントが「なぜ」かはレビューで確かめる | CODE-05-a |
| CODE-06 | ファイル名・エージェント名・分割名の文字列は定数で持つ | structure | 構造検査が `layout.py` 以外の `.json`・`.md` で終わる文字列と、`contracts.py` 以外の `tune-` で始まるエージェント名の文字列を照合する | CODE-06-a |
| ERR-01 | 投げる例外は errors.py の4つだけにし、捕まえる場所を限る | lint, structure | 構造検査が `raise` と `except` を照合する。広い `except` は ruff の `BLE001` で落とす | ERR-01-a、ERR-01-b |
| ERR-02 | 外から来る JSON は workspace の load_* で検証してから使う | structure | 構造検査が `fsops.read_json` の呼び出しを `workspace` だけに、`json.loads` を `fsops` と `checks` だけに限る | ERR-02-a |
| STATE-01 | 状態はファイルだけで持ち、進み具合は workspace が求める | structure, review | 構造検査が `workspace`・`status` の `fsops` の呼び出しを照合する。状態ファイルを足していないかはレビューで確かめる | STATE-01-a |
| STATE-02 | サブエージェントとの受け渡しはひな形と決めたファイル名だけで行う | test, review | `tests/test_prompts.py` がひな形と表の一致を確かめる。プロンプトの文を Python に書いていないかはレビューで確かめる | STATE-02-a |
| STATE-03 | 学習役には学習用だけを見せ、テスト用は最後に1回だけ使う | test, review | `tests/test_splitting.py` が分割の再現性を、`tests/test_learn.py` が証拠の範囲と写しの検出を、`tests/test_status.py` がテスト用の評価の時期を確かめる | STATE-03-a |
| ASYNC-01 | 補助 CLI は並行処理を書かない | structure | 構造検査が import を照合する | ASYNC-01-a |
| OPS-01 | 結果は標準出力、エラーは標準エラーに出し、status の行は決めた書き出しだけを使う | structure, test | `tests/test_status.py` が全行の書き出しを確かめる。`logging` の import は構造検査が落とす | OPS-01-a、OPS-01-b |
| OPS-02 | 設定は plan.json だけから読み、環境変数を読まない | structure | 構造検査が `os.environ` と `os.getenv` を `proc` だけに限る | OPS-02-a |
| OPS-03 | 人に見せる文言は日本語で書き、表と率は render の関数で作る | review | レビューで確かめる | — |
| OPS-04 | 評価を進める段は、最初に承認済みの計画を読む | structure, test | 構造検査が公開関数の `load_approved` の呼び出しを照合する。`tests/test_evaluate.py` が `command` の作業ディレクトリを確かめる | OPS-04-a、OPS-04-b |
| TEST-01 | モジュールごとに tests/test_<モジュール>.py と <名前>Test クラスを置く | structure | 構造検査がファイルとクラスの有無を照合する | TEST-01-a |
| TEST-02 | モックを使わず、support.py の部品と一時ディレクトリで確かめる | structure, review | `unittest.mock` と `mock` の import は構造検査が落とす。部品の置き場はレビューで確かめる | TEST-02-a |
| TEST-03 | 検査の種類とサブコマンドを足したら、決めた名前のテストを足す | structure | 構造検査が `KINDS`・`COMMANDS` とテストの関数名を照合する | TEST-03-a |
| PROC-01 | サブコマンドを足すときは置き場から入口の順に作る | doc | AGENTS.md と実装用スキルの手順に書く | — |
| PROC-02 | 波及の対応表の組は同じ変更で変える | review | レビューで両側のファイルを突き合わせる | — |
| PROC-03 | 道具の版は Makefile で固定し、上げるときは ADR を書く | review | `Makefile` は保護ファイルなので、変更はレビューで確かめる | — |
| PROC-04 | ルールは ADR から probe の順で変える | doc | AGENTS.md の「ルールを変えたいとき」に書く | — |
| PROC-05 | 完了の条件は make check が通ること | doc | AGENTS.md の「完了の条件」と実装用スキルに書く | — |
| PROC-06 | plan.json と cases.json の形を変えたら SCHEMA_VERSION を上げる | test, review | `tests/test_plan.py` が違う版の計画を問題にすることを確かめる。版を上げたかはレビューで確かめる | PROC-06-a |
| PROC-07 | 人が決める場面はスキルに書き、AskUserQuestion で聞く | review | SKILL.md の差分をレビューで確かめる | — |
| TOOL-01 | 整形は ruff format に任せる | format | `make format-check` | TOOL-01-a |
| TOOL-02 | 編集の直後は hooks、完了の前は make check を回す | doc | AGENTS.md の「完了の条件」と `.claude/settings.json` の hooks | — |
| TOOL-03 | 抑止コメントを書かない | structure | `.foundation/bin/guard.py` が manifest の `guard.suppressions` のパターンを照合する | TOOL-03-a |
| TOOL-04 | 保護ファイルを変えない | review | hooks がエージェントの編集に確認を求め、差分はレビューで確かめる | — |
| TOOL-05 | Python 3.9 で動く書き方にし、道具は版を固定して呼ぶ | type | mypy の `python_version = "3.9"` が 3.10 以降の API を落とす | TOOL-05-a |

## 機械で縛っていないルール

| ルールID | 題名 | 強制 | 機械化しない理由 |
|---|---|---|---|
| OPS-03 | 人に見せる文言は日本語で書き、表と率は render の関数で作る | review | 文言が日本語として自然か、人に見せる文言かどうかは意味の判断が要るため |
| PROC-01 | サブコマンドを足すときは置き場から入口の順に作る | doc | 作った順番は差分に残らないため |
| PROC-02 | 波及の対応表の組は同じ変更で変える | review | 組の一部（ひな形と表、KINDS と文書、AGENTS と定義）は他のルールの検査で縛るが、status の行と SKILL.md の手順の対応は意味の判断が要るため |
| PROC-03 | 道具の版は Makefile で固定し、上げるときは ADR を書く | review | 版を上げてよいかは互換性の判断が要るため |
| PROC-04 | ルールは ADR から probe の順で変える | doc | 変えた順番は差分に残らないため |
| PROC-05 | 完了の条件は make check が通ること | doc | 報告の時点で check を回したかは差分に残らないため |
| PROC-07 | 人が決める場面はスキルに書き、AskUserQuestion で聞く | review | スキルの手順が人に聞いてから実行する形になっているかは、文の意味の判断が要るため |
| TOOL-02 | 編集の直後は hooks、完了の前は make check を回す | doc | いつ検査を回したかは差分に残らないため |
| TOOL-04 | 保護ファイルを変えない | review | hooks はエージェントの編集にだけ確認を求め、人の編集は止められないため、差分のレビューで確かめる |

## 対象外とした軸

| 軸 | 理由 |
|---|---|
