---
name: review
description: skill-harness2-kit の変更をレビューする手順。差分、プルリクエスト、ブランチ、特定のファイルのレビューを頼まれたとき、また「この実装で問題ないか確認して」「ルールに沿っているか見て」と頼まれたときは必ず使う。機械の検査を先に回し、機械で拾えないルールをルールIDごとに確かめ、固定の形式で指摘と判定を返す。
---

# skill-harness2-kit のレビュー手順

指摘は、ルールの正本である `docs/design/rules.md` のルールIDに結び付ける。ルールに無いことを理由に差し戻さない。レビュアーごとに基準が変わるのを防ぐためである。パスは基盤のルートからの相対パスで、`h2_kit/` は `kit/.h2/h2_kit/`、`prompts/` は `kit/.h2/templates/prompts/` を指す。

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
| TOOL-04 | 保護ファイルの変更 | `.foundation/manifest.json` の `protected` に当たるファイル（`Makefile`、`pyproject.toml`、`scripts/structure_check.py`、`.claude/settings.json`、`.foundation/**`、`docs/design/rules.md`、`docs/design/enforcement-matrix.md`）が差分にあるか。`structure_check.py` は、登録の表（`SHARED`、`STAGES`、`ENTRY`、`APPROVED_STAGES`、`KEY_MODULES`、`WRAPPER_KEYS`）に要素を足すだけの差分なら指摘しない |
| TOOL-03 | 抑止コメント | manifest の `guard.suppressions` のパターン（`noqa`、`ruff: noqa`、`type: ignore`、`mypy:`、`pragma: no cover`、`fmt: off`、`unittest.skip`、`skipTest(`）が差分にあるか |
| TOOL-03 | テストの skip・削除 | `tests/` のファイルの削除、`test_` で始まる関数の削除、`assert` の削除や弱め（`assertEqual` を `assertTrue(... is not None)` にするなど） |
| DEP-03 | 依存の追加 | `structure_check.py` の `STDLIB` 表の差分、`Makefile` の `uvx` の行の差分、`requirements*.txt` の追加、`pyproject.toml` の `dependencies` の追加 |
| STATE-04 | 答えを見ない仕組みの緩め | `h2_kit/guards.py` の `MEASUREMENT_WORDS`・`GRADER_MARKERS` から語を消す差分、`prompts/_answer-free*.md` を外す差分。方法のモジュール（`execution`、`recursion`、`selection`、`reflection`、`context`、`rollout`、`library`、`prompts`、`runner`、`sandbox`）が、名前に `judg` を含まない関数を通して `judged.json` や `checks.json` を読む差分（構造検査は名前の `judg` だけを見るため） |

## 4. 機械で拾えないルールを確かめる

rules.md で強制に `review` を含むルールは、3節かこの表の1列目に全部載っている。差分に関係する行を確かめる。

| ルールID | 確認方法 | 違反の典型例 |
|---|---|---|
| STR-02 | 差分で足した関数の呼び出し元を `grep -rn '<関数名>' kit/.h2/h2_kit/` で数え、決定表の置き場と比べる | `selection.py` と `reflection.py` に同じ `_render_ids` を写す |
| CODE-01 | 差分の関数で、引数のリスト・辞書に `append`、`extend`、`update`、`pop`、`[...] =`、`del` をしていないか。例外は `_read_*` と `_parse_*` が引数の `problems` に足すことだけ | `def _add(stages: list[Stage]) -> None: stages.append(...)` |
| CODE-05 | 差分のコメントが、コードを読めば分かる「何を」ではなく「なぜ」か | `# 結果を書く` |
| STATE-01 | 差分で足したファイル名の定数（`layout.py`）が、進み具合（段階、済んだ印、番号）を書くファイルでないか | `STATE_FILE = "state.json"` に今の段を書く |
| STATE-03 | 差分のプロンプトの値（`values` の辞書）に、軌跡・成果物・スキルの本文を入れていないか。`context.py` の差分で、資料を `obs_trunc` 以外で切り詰めていないか | `values["trajectory"] = rollout.read_trajectory(view)[:2000]` |
| STATE-06 | 候補の木を作る流れ（`recursion.py`）の差分で、実行（`_run_roll`）の前に `validate.check_tree` を通しているか。差し戻しが `STAGE_ATTEMPTS` の回数までか。落ちたときに入力の木に戻して `fell_back` を記録しているか | 検証に落ちた木をそのまま実行する。差し戻しを無制限に繰り返す |
| OPS-03 | 人に見せる文言が日本語か。Markdown の表・一覧・金額を `render.render_table`・`render_bullets`・`render_usd` で作っているか。日付を段で作っていないか | `f"${cost:.2f}"`、表の行を f 文字列で手で組む |
| TEST-02 | テストの部品（リポジトリ、プロファイル、タスクを作る関数）が `tests/support.py` にあり、偽の返答が `tests/fixtures/fake_claude.py` の `behavior=` にあるか。テストのファイルに部品の関数を足していないか | `test_recursion.py` に `def _write_profile(...)` を足す |
| PROC-02 | 5節の対応表の組を、両側とも確かめる | ひな形に `${levers}` を足し、`prompts.TEMPLATES` を変えない |
| PROC-03 | `Makefile` の `RUFF`・`MYPY` の版の差分に、同じ変更の ADR があるか | `RUFF = uvx ruff@0.18.0` だけを変える |
| PROC-06 | `profile.py` の `Profile`・`parse_profile`・`build_default_profile` の差分があるとき、`SCHEMA_VERSION`・`references/profile-guide.md`・ADR の差分もあるか | `Profile` に項目を足し、版を上げない |
| PROC-07 | `skill-harness2` の SKILL.md に、人が決める場面を足したとき「人が決める場面」の表にも行があるか。`approve` と `adopt` を人の答えの前に実行する手順になっていないか。`adopt` に `--confirm` を渡しているか | 「show の後に adopt を実行する」とだけ書く |

## 5. ファイルをまたぐ対応を確かめる

PROC-02 の対応表の組ごとに、左が差分にあれば右のファイルを開いて突き合わせる。右が差分に無くても、内容が左と合っていれば指摘しない。

| 左（差分にあるもの） | 開くもの | 突き合わせること |
|---|---|---|
| `prompts/<名前>.md` | `prompts.TEMPLATES`、値を作るモジュールの `render_prompt` の呼び出し、`docs/design/research.md` の「harness2 の仕組み」の表 | ひな形の `${…}` の名前と、モジュールが渡す値の名前が同じか。先頭のコメントの harness2 のプロンプトの名前と、research.md の表の行が合っているか |
| `validate.check_tree` の検証の項目 | rules.md の STATE-06 の表、`prompts/_surface.md` の「提案ごと捨てる規則」、`tests/test_validate.py` | 項目ごとに、3つのファイルに同じ条件があるか |
| `contracts.py` の返答のタグ | `prompts/_notes-format.md`、`prompts/select.md`、`prompts/reflect.md` のうちタグを書いたもの | タグの綴りと形が同じか |
| `status.LINE_KINDS` か status の `次:` の行 | `skill-harness2` の SKILL.md の「繰り返すこと」の表 | `段階:` の値が表の1行に当たり、することが書いてあるか |
| `profile.json` の形 | `profile.SCHEMA_VERSION`、`references/profile-guide.md`、`docs/design/adr/` | 版が上がり、ガイドの表と ADR に足した項目があるか |
| `runner` のフラグ | rules.md の OPS-05 の表、research.md の「Claude Code のヘッドレス実行」 | 閉じ込めのフラグが表と同じか。確かめた Claude Code の版が書いてあるか |
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
