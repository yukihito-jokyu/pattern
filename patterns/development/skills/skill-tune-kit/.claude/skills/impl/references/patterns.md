# パターン

実装用スキル `impl` の「1. 依頼をパターンに振り分ける」の各行に対応する手順である。節の番号は振り分け表と一致させる。パスは基盤のルートからの相対パスで、`tune_kit/` は `kit/.tune/tune_kit/` を指す。

## 1. 検査の種類を足す・変える

- 使う場面：検査の種類（`kind`）を足す・変える
- 見本：`tune_kit/checks.py` の `KINDS` の `contains`（値と比べる種類）と `equals`（正解と比べる種類）、`tests/test_checks.py` の `test_kind_contains`
- 作る・変えるファイル：

  | 順 | パス | 見本との対応 | 守るルール |
  |---|---|---|---|
  | 1 | `tune_kit/checks.py` | `KINDS` に `Kind` を1つ足し、評価の関数 `evaluate_<種類>` を足す | NAM-02、CODE-03、CODE-06 |
  | 2 | `tune_kit/evaluate.py`（下の表で要るときだけ） | `_evaluate_check` の分岐 | OPS-04 |
  | 3 | `tune_kit/plan.py`（下の表で要るときだけ） | `_is_expected_used` | ERR-02 |
  | 4 | `tests/test_checks.py` | `test_kind_<種類>` を1つ足す | TEST-03 |
  | 5 | `kit/claude/skills/skill-tune/references/check-kinds.md` | `make docs` で作り直す（手で書かない） | STR-04 |

- 新しい種類の比べ方で、変える場所を決める

  | 比べ方 | 変える場所 |
  |---|---|
  | 検査の `value` の文字列と比べる | `checks.py` に `evaluate_<種類>(text, value)` を足し、`_VALUE_EVALUATORS` に登録する。`evaluate.py` は変えない |
  | 正解（`value`、`expected_file`、ケースの `expected` の順）と比べる | `checks.evaluate_text_check` の最後の分岐と、`plan._is_expected_used` の種類の組に足す |
  | 文字列以外（ファイルの有無、コマンドの終了コード） | `checks.py` に結果だけを受け取る `evaluate_<種類>` を足し、`evaluate._evaluate_check` に `if check.kind == "<種類>":` の分岐を足す。外部コマンドは `proc` を通す（DEP-04） |
  | 採点役が判定する | 実装しない。採点役のひな形と `contracts.parse_grades` も変わるので、提案として報告する |

- 手順：
  1. `Kind` の `required` と `optional` に、検査で使う項目を `plan.CHECK_KEYS` の名前で書く。`plan._check_fields` がこの2つから検証するので、`plan.py` に種類ごとの検証は書かない
  2. `summary`（合格の条件）、`expected`（正解の使い方）、`example`（plan.json に書く1行の JSON）を日本語で書く。この3つが check-kinds.md の表と例になる
  3. `test_kind_<種類>` には、合格する入力と不合格になる入力を1つずつ書く
  4. `make docs` を実行してから `make check` を回す
- この場面で間違えやすいこと：
  - `plan.CHECK_KEYS` に無い項目名を `required` に書く。項目を足すなら、先にパターン4を行う
  - check-kinds.md を手で直す。`docs-check` が落ちる

## 2. サブコマンド（段）を足す

- 使う場面：サブコマンド（段）を足す
- 見本：`tune_kit/decide.py`（最小の段）、`tune_kit/cli.py` の `COMMANDS` の `decide`、`tune_kit/status.py` の `_build_learn_steps`、`tests/test_decide.py`、`tests/test_cli.py` の `test_command_decide`
- 作る・変えるファイル（PROC-01 の順）：

  | 順 | パス | 見本との対応 | 守るルール |
  |---|---|---|---|
  | 1 | `tune_kit/layout.py` | 段が読み書きするファイル名の定数と、置き場のプロパティ | CODE-06 |
  | 2 | `tune_kit/contracts.py`（サブエージェントとの受け渡しがあるときだけ） | `DecisionRecord` と `parse_decision`、`build_decision_data` | NAM-03、ERR-02 |
  | 3 | `tune_kit/<段>.py`（既存の段に足すときはそのモジュール） | `decide.py` の全体 | STR-02、DEP-01、NAM-02、OPS-04、ERR-01 |
  | 4 | `tune_kit/status.py` | `_build_learn_steps` の、ファイルの有無で次の手を返す形 | OPS-01、STATE-01 |
  | 5 | `tune_kit/cli.py` | `COMMANDS` の `"decide": Command(...)` と、`ROUND` などの `Option` | OPS-01 |
  | 6 | `tests/test_<段>.py`、`tests/test_cli.py`、`tests/test_status.py` | `test_decide.py`、`test_command_decide` | TEST-01、TEST-02、TEST-03 |
  | 7 | `scripts/structure_check.py` と `docs/design/architecture.md` | `STAGES` に1行、許可表に1行（承認を伴う評価の段なら `APPROVED_STAGES` にも） | DEP-01、TOOL-04 |
  | 8 | `kit/claude/skills/skill-tune/SKILL.md` | 「手順 B と C：繰り返すこと」の表 | PROC-02、PROC-07 |

- 置くモジュールを決める

  | 新しいサブコマンドがすること | 置くモジュール | 名前の例 |
  |---|---|---|
  | 既存の段の間に入る新しい処理で、ファイルを書く | 新しい段のモジュール `tune_kit/<段>.py` を足す | `<段>` |
  | 既存の段の出力を検査する | その出力を書く段のモジュール | `<段>-check` |
  | ファイルを書かず、1つの段が書いた JSON を一覧で見せる | その JSON を書く段のモジュール（decision.json なら `decide.py`） | `<段>-list`（`decide-list`） |
  | ファイルを書かず、2つ以上の段の JSON をまとめて見せる | `report.py` | `report-<何を>` |

  `status.py` には次の手を示すことだけを置き、表示だけのサブコマンドを足さない。

- 手順：
  1. 段の公開関数は、サブコマンド名の `-` を `_` にした名前にし、引数は `where: layout.Layout` を先頭に、戻り値は人に見せる文字列にする
  2. 評価を進める段なら、公開関数の最初の文で `workspace.load_approved(where)` を呼ぶ（OPS-04）
  3. 段の順番を確かめる関数は `_require_<何を>` と名付け、順番の誤りは `StageError` で「…。status を実行してください」と投げる
  4. 書くファイルは `fsops.write_*` で書き、完了の印になるファイルを最後に書く（途中で止まっても status が同じ段を示すため）
  5. status の行は `LINE_KINDS` の書き出しで始め、コマンドは `_build_command` で作る
  6. `structure_check.py` は保護ファイルである。hooks が確認を求めたら、変更が登録の表に要素を足すだけであることを示して承認を得る（TOOL-04）
- この場面で間違えやすいこと：
  - 2つ以上の段で使う関数を、片方の段に置いてもう一方から import する。共有のモジュールに置く（STR-02、DEP-01）
  - 進み具合を書いたファイル（`state.json` の類）を足す。進み具合はファイルの有無から `workspace` が求める（STATE-01）
  - `print` や `sys.exit` を段に書く。段は文字列を返し、出力は `cli` が行う（DEP-04）

## 3. プロンプトの文言・置き換えの値を変える

- 使う場面：サブエージェントへのプロンプトの文言・置き換えの値を変える
- 見本：`kit/.tune/templates/prompts/learner.md`、`tune_kit/prompts.py` の `TEMPLATES`、`tune_kit/learn.py` の `_write_prompt`
- 作る・変えるファイル：

  | 順 | パス | 見本との対応 | 守るルール |
  |---|---|---|---|
  | 1 | `kit/.tune/templates/prompts/<名前>.md` | 文言と `${置き換えの名前}` | STATE-02 |
  | 2 | `tune_kit/prompts.py`（置き換えの名前を足す・消すときだけ） | `TEMPLATES` の組 | STATE-02 |
  | 3 | 値を作る段（`executor`・`grader` は `evaluate.py`、`learner` は `learn.py`、`auditor` は `audit.py`） | `_write_prompt` の `prompts.render_prompt` の引数 | STATE-02、STATE-03 |
  | 4 | `tests/test_prompts.py`、値を作る段のテスト | `test_templates_match_table` | TEST-02 |

- 手順：
  1. 文言だけを変えるなら、ひな形だけを変える。Python のコードは変えない
  2. 置き換えの値を足すなら、ひな形・`TEMPLATES`・段の `render_prompt` の引数を同じ変更で変える
  3. 値に入れる文は段で組み立てず、ケースや結果の値だけを渡す。説明の文はひな形に書く
- この場面で間違えやすいこと：
  - 指示の文を Python の文字列に書いて値として渡す（STATE-02）
  - 学習役（`learner`）の値に、検証用・テスト用のケースの依頼文や正解を入れる（STATE-03）
  - サブエージェントの最後のメッセージの形（`完了: <path>` の1行）を変える。スキルの手順が読めなくなる

## 4. plan.json・cases.json の項目を足す・変える

- 使う場面：plan.json・cases.json の項目を足す・変える
- 見本：`tune_kit/plan.py` の `Budget` と `_parse_budget`、`build_plan_data`、`build_skeleton`
- 作る・変えるファイル：

  | 順 | パス | 見本との対応 | 守るルール |
  |---|---|---|---|
  | 1 | `tune_kit/plan.py` | `*_KEYS`、dataclass のフィールド、`_parse_*`、`build_*_data`、`build_skeleton`、`SCHEMA_VERSION` | NAM-03、CODE-03、ERR-02、PROC-06 |
  | 2 | `tune_kit/planning.py`（plan.md に見せる項目なら） | `_render_plan_md` | OPS-03 |
  | 3 | 項目を使う段のモジュール | `approved.model.budget.parallel` の読み方 | OPS-02 |
  | 4 | `tests/test_plan.py`、`tests/support.py` の `build_plan` | `test_case_data_round_trips` | TEST-02 |
  | 5 | `kit/claude/skills/skill-tune/references/plan-schema.md` | 項目の表 | PROC-02 |
  | 6 | `docs/design/adr/<次の番号>-<題>.md` | `_template.md` を写す | PROC-06 |

- 手順：
  1. JSON のキーは snake_case にし、dataclass のフィールド名と同じ綴りにする（NAM-03）
  2. 項目を省いたときの値は、今までと同じ振る舞いになる値にする
  3. `SCHEMA_VERSION` を1上げる。上げると既存の計画は `parse_plan` で問題になるので、ADR に移し方を書く
  4. 配列や入れ子を包むだけのキーを足したら、`structure_check.py` の `WRAPPER_KEYS` に足す（TOOL-04 の例外）
- この場面で間違えやすいこと：
  - 項目を `os.environ` や CLI の引数から読む。評価の設定は plan.json だけから読む（OPS-02）
  - 予算の項目を足して `BUDGET_LIMITS` に上下限を書かない

## 5. 既存のサブコマンドの振る舞いを直す、不具合を直す

- 使う場面：既存のサブコマンドの振る舞いを直す、不具合を直す
- 見本：直す段のモジュールと、`tests/test_<段>.py` の同じ段のテスト
- 作る・変えるファイル：

  | 順 | パス | 見本との対応 | 守るルール |
  |---|---|---|---|
  | 1 | `tests/test_<段>.py` | 同じファイルの既存のテスト | TEST-01、TEST-02 |
  | 2 | `tune_kit/<段>.py`（関数が2つ以上の段で使われていれば共有のモジュール） | 同じモジュールの既存の関数 | STR-02、CODE-01 |
  | 3 | `tune_kit/status.py`（次の手が変わるときだけ） | パターン7 | OPS-01 |

- 手順：
  1. 不具合を再現するテストを先に書き、落ちることを `make test` で確かめる
  2. 直す。段の順番の条件を変えるときは `_require_*` と `status.py` の両方を変える（片方だけだと、status が示したコマンドが落ちる）
  3. テストの部品が要るなら `tests/support.py` に足し、テストのファイルに部品を書かない（TEST-02）
- この場面で間違えやすいこと：
  - 直したい段とは別の段のモジュールを import して関数を借りる（DEP-01）
  - 落ちているテストを消す、skip する（TOOL-03）

## 6. 指標の計算か、候補の採否の規則を変える

- 使う場面：指標の計算か、候補の採否の規則を変える
- 見本：`tune_kit/metrics.py` の `compute_decision`、`tests/test_metrics.py`、`docs/design/adr/0008-mechanical-adoption.md`
- 作る・変えるファイル：

  | 順 | パス | 見本との対応 | 守るルール |
  |---|---|---|---|
  | 1 | `docs/design/adr/<次の番号>-<題>.md` | 0008 を置き換える ADR | PROC-02 |
  | 2 | `tune_kit/metrics.py` | `compute_summary`、`compute_decision` | CODE-01、CODE-03 |
  | 3 | `tests/test_metrics.py` | 同じファイルの既存のテスト | TEST-02 |
  | 4 | `tune_kit/decide.py`、`tune_kit/report.py`（表の列が変わるときだけ） | `_render_rates`、`_render_rounds` | OPS-03 |
  | 5 | `kit/claude/skills/skill-tune/SKILL.md`（人への説明が変わるときだけ） | 「全体の流れ」の表 | PROC-02 |

- 手順：
  1. 率は `fractions.Fraction` で計算し、表示は `render.render_rate` に任せる（浮動小数の誤差で採否が揺れないため）
  2. 採否は検証用の結果だけで決め、テスト用の結果を採否に使わない（STATE-03）
- この場面で間違えやすいこと：
  - 判定に学習用の結果を使う。学習用は過学習の印（`overfit`）にだけ使う
  - `metrics.py` に `tune_kit` の他のモジュールを import する。`metrics` は依存を持たない（DEP-01）

## 7. status の行（次の手の示し方）を変える

- 使う場面：status の行（次の手の示し方）を変える
- 見本：`tune_kit/status.py` の `_build_fix_steps`（人が決める場面）と `_build_learn_steps`（サブエージェントを起動する場面）
- 作る・変えるファイル：

  | 順 | パス | 見本との対応 | 守るルール |
  |---|---|---|---|
  | 1 | `tune_kit/status.py` | `_build_*_steps` と、書き出しを足すなら `LINE_KINDS` | OPS-01、STATE-01 |
  | 2 | `tests/test_status.py` | `test_every_stage_uses_line_kinds` | OPS-01 |
  | 3 | `kit/claude/skills/skill-tune/SKILL.md` | 「手順 B と C：繰り返すこと」の表 | PROC-02 |

- 手順：
  1. 行の書き出しは `LINE_KINDS` のどれかにする。新しい書き出しが要るなら `LINE_KINDS` と SKILL.md の表に同じ変更で足す
  2. サブエージェントの起動は `LAUNCH` の行と `render.render_job` の行で示し、続けて `その後:` の行を出す
  3. 人が決める場面は「`次: <ファイル> を人に見せ、… AskUserQuestion で聞く`」と、答えごとのコマンドの行で示し、SKILL.md の「人が決める場面」の表にも足す（PROC-07）
- この場面で間違えやすいこと：
  - status でファイルを書く。status は `workspace` の読む関数だけを使う（STATE-01）
  - 行の文言を変えて SKILL.md の表を変えない。スキルが行を読み分けられなくなる

## 8. 配布するスキル（skill-tune）かサブエージェントの定義を直す

- 使う場面：配布するスキル（skill-tune）かサブエージェントの定義を直す
- 見本：`kit/claude/skills/skill-tune/SKILL.md`、`kit/claude/agents/tune-grader.md`
- 作る・変えるファイル：

  | 順 | パス | 見本との対応 | 守るルール |
  |---|---|---|---|
  | 1 | `kit/claude/skills/skill-tune/SKILL.md` か `references/<名前>.md` | 同じファイルの既存の節 | STR-05、PROC-07 |
  | 2 | `kit/claude/agents/tune-<役>.md` | `tune-grader.md` の frontmatter | STR-05 |
  | 3 | `tune_kit/contracts.py`（役を足すときだけ） | `AGENTS` | CODE-06、PROC-02 |

- 手順：
  1. frontmatter は STR-05 の表のとおりにする。SKILL.md は500行以内、`references/` はサブディレクトリを作らない
  2. スキルが実行するのは `python3 .tune/tune.py` のサブコマンドだけにする（`allowed-tools` がそれだけを許す）
  3. 役を足すときは、`AGENTS`・`kit/claude/agents/`・SKILL.md のサブエージェントの表・ひな形（パターン3）を同じ変更で足す
- この場面で間違えやすいこと：
  - 採点役・学習役・監査役の `tools` に `Bash` を足す。正解やテスト用のデータを読める経路が増える
  - SKILL.md に補助 CLI の内部（ファイルの置き場や JSON の形）を書く。スキルは status の行に従うだけにする
