---
name: review
description: orch-forge-kit の変更をレビューする手順。差分、プルリクエスト、ブランチ、特定のファイルのレビューを頼まれたとき、また「この実装で問題ないか確認して」「ルールに沿っているか見て」と頼まれたときは必ず使う。機械の検査を先に回し、機械で拾えないルールをルールIDごとに確かめ、固定の形式で指摘と判定を返す。
---

# orch-forge-kit のレビュー手順

指摘は、ルールの正本である `docs/design/rules.md` のルールIDに結び付ける。ルールに無いことを理由に差し戻さない。レビュアーごとに基準が変わるのを防ぐためである。

## 1. 対象を決める

- 指定があれば、それを対象にする
- 指定が無ければ、未コミットの変更（`git diff HEAD` と未追跡のファイル）を対象にする
- 未コミットの変更も無ければ、現在のブランチと基準のブランチの差分を対象にする

対象のファイル一覧を、出力の「対象」節に書く。

## 2. 機械の検査を回す

`make check` を実行する。落ちたら、出力の要点を「機械の検査」節に載せる。機械が拾った違反を、人手の指摘として重複して書かない。

## 3. 抜け道を確かめる

| ルールID | 確認 | 見るもの |
|---|---|---|
| TOOL-04 | 保護ファイルの変更 | `.foundation/manifest.json` の `protected` に当たるファイル（`Makefile`、`pyproject.toml`、`scripts/structure_check.py`、`.claude/settings.json`、`.foundation/**`、`docs/design/rules.md`、`docs/design/enforcement-matrix.md`）が差分にあり、依頼で明示されていない |
| TOOL-03 | 抑止コメント | manifest の `guard.suppressions` のパターン（`noqa`、`type: ignore`、`pragma: no cover` ほか）が差分にある |
| TEST-01 | テストの skip・削除 | `tests/test_*.py` の削除、テストのメソッドの削除、skip の追加 |
| DEP-03 | 依存の追加 | `structure_check.py` の `STDLIB` の表の変更、標準ライブラリでない import |
| OPS-05 | 実行役の権限を広げる | `execute.command` の引数の増減、`kit/` の下の `bypassPermissions`・`--dangerously-skip-permissions`・`--bare`、`kit/claude/agents/` の `permissionMode` |

## 4. 機械で拾えないルールを確かめる

rules.md で強制に `review` を含むルールは、3節かこの表の1列目に全部載っている。差分に関係する行を確かめる。

| ルールID | 確認方法 | 違反の典型例 |
|---|---|---|
| NAM-02 | 足した・名前を変えた関数の先頭の動詞を、語彙表（`read_`、`load_`、`parse_`、`write_`、`render_`、`make_`、`check_`、段の名前）の意味と突き合わせる。表に無い意味の関数は、名詞か表に無い動詞で始めてよい。真偽値を返す関数が `is_`・`has_` で始まるかを見る | `load_` なのに検証しない。`render_` なのに Markdown でない値を返す。真偽値を返す `grade_ok` を足す |
| CODE-01 | 関数の中で、引数の `dict`・`list` に代入・`append`・`pop`・`update`・`sort` していないかを見る。検証の関数が受け取る `problems` に問題の文を足すのは違反ではない | `data.pop("verdict")` を引数の辞書に対して行う。受け取った一覧を `sort()` で並べ替える |
| OPS-01 | `status.py` に人が決める値を足していれば、`_command` に渡す文字列に `--<引数の名前> '<日本語の名前>'` を直接書いているか（定数、変数、新しい種類の行を足していないか）を見る | `FEEDBACK = "'<…>'"` を定数に置く。`…を残すなら:` の行を足す |
| STATE-01 | 新しいファイルの置き場が `.forge/targets/`（残す）か `.forge/work/`（消してよい）の表に合い、進み具合を表すファイルを足していないかを見る | `state.json` に段の名前を書き、`status` がそれを読む |
| STATE-02 | `prompts.render` に渡す `values` の各値が、生の値・`render.MISSING`・`render.bullets`・`render.table` のどれかで、文（説明や指示）を含まないかを見る。サブエージェントの成果を返答の本文から読んでいないかを見る | `items or "- （判定する項目はありません）"` のように、無いときの文を値に入れる |
| OPS-03 | 人に見せる表・数・判定を `render.table`・`render.number`・`render.usd`・`render.mark` で書き、長さがデータで決まる一覧を `render.bullets` で書いているかを見る | 段のモジュールで `f"{value:.2f}"` や手書きの `|` の表を作る |
| TEST-03 | 差分で足した名前（指標の id、バンドルの決まりの id、置き換えの名前、引数、charter・設計の項目、実行の記録の項目、`contracts` の JSON の項目、公開の関数）ごとに、rules.md の表の置き場に `test_<名前>` があるかを見る | `test_parallel_runs_checks_concurrently` のような文の名前。同じ確認を2つのテストのファイルに書く |
| PROC-02 | 差分に波及の対応表の左側があれば、右側のファイルも差分にあるかを見る | `contracts.AGENTS` の名前を変え、`kit/claude/agents/` とスキルの表を変えていない |
| PROC-06 | `charter.py`・`design.py` のキーや意味が変わっていれば、`SCHEMA_VERSION` の変更と ADR があるかを見る。`.forge/targets/` に残る記録の JSON（`contracts` の `parse_design_approval`、`parse_decision` ほか）に項目を足していれば、項目の無い古い記録を既定値で読むかを見る | `executor` に項目を足し、`SCHEMA_VERSION` を変えない。decision.json に必須の項目を足し、前の版の記録が読めなくなる |
| TOOL-04 | 3節の保護ファイルの確認と同じ | `pyproject.toml` の `ignore` に足す |

## 5. ファイルをまたぐ対応を確かめる

rules.md の PROC-02 の表の各組について、差分に左側のファイルがあれば、両側のファイルを開いて突き合わせる。

1. `catalog.METRICS` の id の集合と `score.CALCULATORS` のキーの集合が同じか。`metric-catalog.md` が `make docs` の結果と同じか（`make docs-check` が通っていればよい）
2. `bundle.RULES` の id ごとに `tests/test_bundle.py` に `test_<id の小文字>` があるか（`make test` が通っていればよい）。`bundle-rules.md` が `make docs` の結果と同じか
3. `prompts.TEMPLATES` の置き換えの名前と、ひな形の `${名前}` が同じか（`make test` が通っていればよい）。ひな形の JSON の例が `contracts.parse_*`・`design.parse` の形と同じか
4. `contracts.AGENTS` の値と `kit/claude/agents/` のファイル名、そのエージェントを起動するスキルの表が同じか
5. charter のキーと `forge-goals/references/charter-schema.md` の表、設計のキーと `forge-build/references/design-schema.md` の表が同じか。人が決める charter のキーを足したなら、`forge-goals/SKILL.md` の、そのキーを決める手順の表（手順7の環境、手順8の実行の条件と予算）に行があるか
6. `layout` に足した置き場が、architecture.md の「データの流れ」に載っているか
7. `status` の `次:` の行の形と、段を使うスキルの「繰り返すこと」の表が対応しているか
8. `forge_kit` のモジュールの増減と、`structure_check.py` と `architecture.md` の許可表が同じか

## 6. 出力の形式

必ず次の形で出す。

```
# レビュー結果

## 判定
承認 または 差し戻し

## 対象
- <ファイルの一覧>

## 機械の検査
<check の結果。通った、または落ちた（要点）>

## 指摘
| # | ルールID | 場所 | 根拠（実際の記述） | 直し方 |
|---|---|---|---|---|
| 1 | <ID> | <パス>:<行> | `<該当の記述>` | <直し方> |

指摘が無ければ「なし」と書く。

## ルール追加の提案
<ルールには無いが、揺れや問題になりうる点。指摘とは分けて書く。無ければ「なし」>
```

- 判定は機械的に決める。check が通り、かつ指摘が0件なら「承認」、それ以外は「差し戻し」
- 指摘は場所の順に並べる
- 同じ違反が複数の箇所にあれば、箇所ごとに1行ずつ書く
