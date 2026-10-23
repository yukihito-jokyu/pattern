---
name: review
description: skill-tune-kit の変更をレビューする手順。差分、プルリクエスト、ブランチ、特定のファイルのレビューを頼まれたとき、また「この実装で問題ないか確認して」「ルールに沿っているか見て」と頼まれたときは必ず使う。機械の検査を先に回し、機械で拾えないルールをルールIDごとに確かめ、固定の形式で指摘と判定を返す。
---

# skill-tune-kit のレビュー手順

指摘は、ルールの正本である `docs/design/rules.md` のルールIDに結び付ける。ルールに無いことを理由に差し戻さない。レビュアーごとに基準が変わるのを防ぐためである。

## 1. 対象を決める

- 指定があれば、それを対象にする
- 指定が無ければ、未コミットの変更（`git diff HEAD` と未追跡のファイル）を対象にする
- 未コミットの変更も無ければ、現在のブランチと基準のブランチの差分を対象にする
- git のリポジトリでなければ、依頼で渡された差分かファイルを対象にする

対象のファイル一覧を、出力の「対象」節に書く。

## 2. 機械の検査を回す

`make check` を実行する。落ちたら、出力の要点を「機械の検査」節に載せる。機械が拾った違反を、人手の指摘として重複して書かない。

## 3. 抜け道を確かめる

| ルールID | 確認 | 見るもの |
|---|---|---|
| TOOL-04 | 保護ファイルの変更 | `.foundation/manifest.json` の `protected` に当たるファイル（`Makefile`、`pyproject.toml`、`scripts/structure_check.py`、`.claude/settings.json`、`.foundation/**`、`docs/design/rules.md`、`docs/design/enforcement-matrix.md`）が差分にあるか。`structure_check.py` は、登録の表（`SHARED`、`STAGES`、`ENTRY`、`APPROVED_STAGES`、`KEY_READERS`、`WRAPPER_KEYS`）に要素を足すだけの差分なら指摘しない |
| TOOL-03 | 抑止コメント | manifest の `guard.suppressions` のパターン（`noqa`、`type: ignore`、`pragma: no cover`、`fmt: off`、`unittest.skip`）が差分にあるか |
| TOOL-03 | テストの skip・削除 | `tests/` のファイルの削除、`test_` で始まる関数の削除、`skipTest` の追加 |
| DEP-03 | 依存の追加 | `structure_check.py` の `STDLIB` 表の差分、`Makefile` の `uvx` の行の差分、`requirements*.txt`・`pyproject.toml` の `dependencies` の追加 |

## 4. 機械で拾えないルールを確かめる

rules.md で強制に `review` を含むルールは、3節かこの表の1列目に全部載っている。差分に関係する行を確かめる。

| ルールID | 確認方法 | 違反の典型例 |
|---|---|---|
| STR-02 | 差分で足した関数の呼び出し元を `grep -rn '<関数名>' kit/.tune/tune_kit/` で数え、決定表の置き場と比べる | `learn.py` と `audit.py` に同じ `_render_json` を写す |
| CODE-01 | 差分の関数で、引数のリスト・辞書に `append`、`extend`、`update`、`pop`、`[...] =`、`del` をしていないか | `def _add(rows: list[str]) -> None: rows.append(...)` |
| CODE-05 | 差分のコメントが、コードを読めば分かる「何を」ではなく「なぜ」か | `# 結果を書く` |
| STATE-01 | 差分で足したファイル名の定数（`layout.py`）が、進み具合（段階、済んだ印、番号）を書くファイルでないか | `STATE_FILE = "state.json"` に今の段を書く |
| STATE-02 | `kit/.tune/tune_kit/` の差分に、サブエージェントへの指示の文（「〜してください」「〜を読み」）が無いか。出力ファイルの名前に `report` が無いか | `values["rules"] = "採点は厳しくしてください"` |
| STATE-03 | `learn.py` と `evidence.py` の差分で、証拠とプロンプトに入るケースが `plan.TRAIN` だけか。`status.py` の差分で、テスト用の評価が止める条件の後だけか | `approved.list_cases(plan.VAL)` を学習役の証拠に足す |
| OPS-03 | 人に見せる文言が日本語か。Markdown の表・率・一覧を `render.render_table`・`render_rate`・`render_bullets` で作っているか。日付を段で作っていないか | `f"{rate * 100:.1f}%"`、表の行を f 文字列で手で組む |
| TEST-02 | テストの部品（計画、ケース、サブエージェントの出力を作る関数）が `tests/support.py` にあり、テストのファイルに部品の関数を足していないか | `test_learn.py` に `def _write_plan(...)` を足す |
| PROC-02 | 5節の対応表の組を、両側とも確かめる | `checks.KINDS` に種類を足し、`make docs` をしていない |
| PROC-03 | `Makefile` の `RUFF`・`MYPY` の版の差分に、同じ変更の ADR があるか | `RUFF = uvx ruff@0.18.0` だけを変える |
| PROC-06 | `plan.py` の `*_KEYS`・dataclass・`_parse_*` の差分があるとき、`SCHEMA_VERSION`・`references/plan-schema.md`・ADR の差分もあるか | `Budget` に項目を足し、版を上げない |
| PROC-07 | `skill-tune` の SKILL.md か `status.py` に、人が決める場面（AskUserQuestion）を足したとき、SKILL.md の「人が決める場面」の表にも行があるか | status に「人に聞く」の行を足し、表に足さない |

## 5. ファイルをまたぐ対応を確かめる

PROC-02 の対応表の組ごとに、左が差分にあれば右のファイルを開いて突き合わせる。右が差分に無くても、内容が左と合っていれば指摘しない。

| 左（差分にあるもの） | 開くもの | 突き合わせること |
|---|---|---|
| `checks.KINDS` | `kit/claude/skills/skill-tune/references/check-kinds.md`、`tests/test_checks.py` | `make check` の `docs-check` と構造検査が通っていれば済み。`Kind` の `required`・`optional` の名前が `plan.CHECK_KEYS` にあるか |
| `templates/prompts/<名前>.md` | `prompts.TEMPLATES`、値を作る段の `render_prompt` の呼び出し | ひな形の `${…}` の名前と、段が渡す値の名前が同じか |
| `contracts.AGENTS` | `kit/claude/agents/`、`skill-tune` の SKILL.md の「サブエージェント」の表 | 役の名前が3か所で同じか |
| `status.LINE_KINDS` か status の `次:` の行 | `skill-tune` の SKILL.md の「手順 B と C：繰り返すこと」の表 | 足した行の書き出しと文言の形が表の1行に当たり、することが書いてあるか |
| plan.json・cases.json の形 | `plan.SCHEMA_VERSION`、`references/plan-schema.md`、`docs/design/adr/` | 版が上がり、項目の表と ADR に足した項目があるか |
| モジュールの追加・import の変更 | `structure_check.py` の表、`docs/design/architecture.md` の依存の許可表 | 2つの表の組が同じか |

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
