---
name: review
description: autoflow-kit の変更をレビューする手順。差分、プルリクエスト、ブランチ、特定のファイルのレビューを頼まれたとき、また「この実装で問題ないか確認して」「ルールに沿っているか見て」と頼まれたときは必ず使う。機械の検査を先に回し、機械で拾えないルールをルールIDごとに確かめ、固定の形式で指摘と判定を返す。
---

# autoflow-kit のレビュー手順

指摘は、ルールの正本である `docs/design/rules.md` のルールIDに結び付ける。ルールに無いことを理由に差し戻さない。レビュアーごとに基準が変わるのを防ぐためである。

## 1. 対象を決める

- 指定があれば、それを対象にする
- 指定が無ければ、未コミットの変更（`git diff HEAD` と未追跡のファイル）を対象にする
- 未コミットの変更も無ければ、現在のブランチと基準のブランチの差分を対象にする

対象のファイル一覧を、出力の「対象」節に書く。

## 2. 機械の検査を回す

`make check` を実行する。落ちたら、落ちた検査の名前と、出力に出たルールIDを「機械の検査」節に載せる。ルールIDは、構造検査と guard では行頭の ID をそのまま写し、lint・型のエラーは `docs/design/enforcement-matrix.md` でルール名からルールIDを引く。機械が拾った違反を、人手の指摘として重複して書かない。

## 3. 抜け道を確かめる

| ルールID | 確認 | 見るもの |
|---|---|---|
| TOOL-04 | 保護ファイルの変更 | `.foundation/manifest.json` の `protected`（`Makefile`、`pyproject.toml`、`scripts/structure_check.py`、`.claude/settings.json`、`.foundation/**`、`docs/design/rules.md`、`docs/design/enforcement-matrix.md`）に当たるファイルが差分にあり、依頼で明示されていない。段・モジュールを足す依頼の `structure_check.py` の表の行の追加だけは除く |
| TOOL-03 | 抑止コメントとテストの skip | 差分に `noqa`、`type: ignore`、`pragma: no cover`、`fmt: off`、`unittest.skip`、`skipTest(` がある |
| TEST-01 | テストの削除 | `tests/test_*.py` のファイルかメソッドが消えている、assert が弱められている |
| DEP-03 | 依存の追加 | `scripts/structure_check.py` の `STDLIB` の表の変更、標準ライブラリでない import |

## 4. 機械で拾えないルールを確かめる

rules.md で強制に `review` を含むルールは、3節かこの表の1列目に全部載っている。差分に関係する行を確かめる。

| ルールID | 確認方法 | 違反の典型例 |
|---|---|---|
| NAM-02 | 足した関数名の先頭の動詞を、rules.md の NAM-02 の語彙表と突き合わせる。真偽値を返す関数が `is_`・`has_` で始まるか | `load_` なのに検証しない関数、`def touches_scope(...) -> bool` |
| CODE-01 | 足した関数が、引数の `dict`・`list`（`problems` を除く）に代入・`append`・`update` していないか | `def add(items: list[str]) -> None: items.append(x)` |
| STATE-01 | 新しく書くファイルが、段の進み具合（何回目か、どの段か、通ったか）を持たないか。段の判断が `trail.jsonl` 以外のファイルを読んでいないか | `fsops.write_json(where.run_dir(run_id) / ..., {"round": 2})`、次の段が `<段>.json` を読んで分岐する |
| STATE-02 | プロンプトの文が段のモジュールに無いか。置き換えの値が生の値か `render.bullets`・`render.table` の結果だけか。返答の本文を読んで判断していないか | `"findings": f"あなたは…{lens}…"`、返答の「完了」以外の文を解析する |
| OPS-03 | 人に見せる文言が日本語か。表が `render.table`、数が `render.number`、一覧が `render.bullets` で書かれているか | `f"| {cmd} | {code} |"` を段のモジュールに書く、英語のエラー文 |
| TEST-03 | 足した名前（規則の id、観点、置き換えの名前、引数、プロファイルの項目、取得元、JSON の項目、出来事、公開の関数）ごとに、rules.md の TEST-03 の表の置き場に `test_<足した名前>` が1つあるか | `test_repro_fails_before_fix` のような文の名前、置き場の違うテストファイル |
| PROC-02 | 下の5節で確かめる | 表だけ変えてひな形を変えない |
| PROC-06 | `profile.py` のキー・意味が変わったとき、`SCHEMA_VERSION` が上がり、ADR に移行の手順があるか | キーを足して `SCHEMA_VERSION = 1` のまま |
| TOOL-04 | 3節の1行目と同じ | `pyproject.toml` の `ignore` に足す |

## 5. ファイルをまたぐ対応を確かめる

rules.md の PROC-02 の表の組ごとに、差分に左の列のファイルがあれば、右の列のファイルを開いて突き合わせる。

1. `policy.py` の表が変わった → `kit/claude/skills/autoflow/references/gates.md` が `make docs` の結果と一致するか（`make docs-check` が通るか）。規則が増えたら `tests/test_policy.py` に `test_<id>` があるか
2. `policy.LENSES` が変わった → `kit/.autoflow/templates/prompts/finder.md` の観点の表に同じ名前があるか
3. `contracts.py` の項目が変わった → その JSON を書かせるひな形の JSON の例と、`tests/support.py` の見本の値に同じ項目があるか
4. `profile.py` のキーが変わった → `views.render_profile`、`setup.py` の検出、`profile-schema.md`（`make docs`）
5. `layout.SOURCES` が変わった → `kit/claude/skills/autoflow/references/sources.md` の表
6. `trail.py` の段・出来事が変わった → `status.py` の `STEP_LABELS` と `_steps`、`kit/claude/skills/autoflow/SKILL.md` の「繰り返すこと」の表、architecture.md の6章
7. `autoflow_kit` のモジュールが増減した → `scripts/structure_check.py` の表と architecture.md の4章の許可表

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
