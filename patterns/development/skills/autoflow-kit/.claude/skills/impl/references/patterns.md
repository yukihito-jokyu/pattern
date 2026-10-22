# パターン

実装用スキル `impl` の「1. 振り分け表」の各行に対応する手順である。節の番号は振り分け表と一致させる。パスの `autoflow_kit/` は `kit/.autoflow/autoflow_kit/`、`prompts/` は `kit/.autoflow/templates/prompts/` を指す。

## 1. 関所の条件（H1・H2）

- 使う場面：H1（方向の確認）・H2（行き詰まり）を起こす条件、関所の選択肢
- 見本：`autoflow_kit/policy.py` の `H1_RULES` と `_has_new_dependency`、`H2_RULES` と `_has_too_many_failures`、`tests/test_policy.py` の `test_h1_new_dependency`・`test_h2_too_many_failures`
- 作る・変えるファイル：

  | 順 | パス | 見本との対応 | 守るルール |
  |---|---|---|---|
  | 1 | `autoflow_kit/policy.py` | 判定の関数 `_is_<状態>`・`_has_<もの>` と、`H1_RULES` か `H2_RULES` の行 | GATE-01、NAM-02 |
  | 2 | `tests/test_policy.py` | `test_<規則の id>`（当たる例と当たらない例） | GATE-01、TEST-03 |
  | 3 | `kit/claude/skills/autoflow/references/gates.md` | `make docs` で生成し直す | STR-04 |

- 手順：
  1. 計画の中身で決まる条件は `PlanRule`（引数は `contracts.Plan` と `profile.Profile`）、実行の進み具合で決まる条件は `ProgressRule`（引数は `policy.Progress` と `profile.Limits`）にする
  2. 判定の関数を、同じ表の既存の関数の直後に置き、表の最後に行を足す。規則の id は、判定の関数名から `_is_`・`_has_` を除いて `h1_`・`h2_` を付けたもの（`_has_new_dependency` → `h1_new_dependency`）。`test_rule_ids_match_functions` が確かめる
  3. 上限の値が要るなら、パターン4でプロファイルの `limits` に項目を足してから使う。数を `policy.py` に直に書かない。計画の値（受け入れ条件の確かめ方、未決の値の impact）と比べるときは、`contracts` の定数（`COMMAND`・`REVIEW`・`HUMAN`、`HIGH_IMPACT`）を使う
  4. `Progress` に無い数（例：実装の回数）が要るなら、`policy.Progress` に項目を足し、`trail.progress` で数える。テストは `tests/test_trail.py` の `test_progress_resets` に assert を足す
  5. `make docs` を回す
- この場面で間違えやすいこと：
  - 段のモジュール（`planning.py`、`building.py`）に `if` で条件を書く。条件は `policy.py` の表だけに置く（GATE-01）
  - `test_<id>` を足し忘れる。`test_rules_have_tests` が落ちる
  - 関所の選択肢（`GATES` の `Option`）を足すときは、`trail._on_decided` にその選択の行き先も足す（パターン7の4）

## 2. リスクの段とレビューの深さ

- 使う場面：リスクの段の決め方（パス、行数）、レビューの深さ・観点・投票の閾値
- 見本：`autoflow_kit/policy.py` の `tier_of_changes`・`TIERS`・`LENSES`・`DEPTHS`・`REVIEW`、`prompts/finder.md` の観点の表、`tests/test_policy.py` の `test_tier_of_changes`・`test_depths_match_lenses`
- 作る・変えるファイル：

  | 順 | パス | 見本との対応 | 守るルール |
  |---|---|---|---|
  | 1 | `autoflow_kit/policy.py` | `tier_of_changes` の理由の行、または表の行 | GATE-01、GATE-06 |
  | 2 | `prompts/finder.md` | 観点を足したときだけ、観点の表に1行 | PROC-02 |
  | 3 | `tests/test_policy.py` | 観点は `test_lens_<名前>`、段の規則は `test_tier_of_changes` に assert | TEST-03 |
  | 4 | `kit/claude/skills/autoflow/references/gates.md` | `make docs` | STR-04 |

- 手順：
  1. 段の規則は `tier_of_changes` の中で、`merge_tier` で上げるか `HIGH` にするだけにする。下げる規則は `LOW` の判定（全部が低いパスかテスト）以外に書かない
  2. 観点は `LENSES` に足し、実装用スキルの2の既定値どおり `deep` の `DEPTHS` にだけ入れる
  3. 判定に使うパスは、プロファイルの `risk` の glob から読む。パスを `policy.py` に直に書かない
- この場面で間違えやすいこと：
  - AI の判定（`judgment.tier`）を規則より優先する（GATE-06）
  - `finder.md` の観点の表を直し忘れる。`tests/test_prompts.py` の `test_finder_lists_every_lens` が落ちる

## 3. 取得元

- 使う場面：取得元（課題の管理の道具）
- 見本：`autoflow_kit/layout.py` の `SOURCES`、`kit/claude/skills/autoflow/references/sources.md`、`tests/test_intake.py` の `test_origin_checks`
- 作る・変えるファイル：

  | 順 | パス | 見本との対応 | 守るルール |
  |---|---|---|---|
  | 1 | `autoflow_kit/layout.py` | `SOURCES` に `"<名前>": <ref が要るか>` | PROC-02 |
  | 2 | `kit/claude/skills/autoflow/references/sources.md` | 取り方の表に1行 | PROC-02 |
  | 3 | `tests/test_intake.py` | `test_source_<名前>`（ref が要るなら、無いと `StageError`） | TEST-03 |

- 手順：
  1. `SOURCES` の最後に足す。`cli` の `--source` の選択肢は `SOURCES` から作られるので、`cli.py` は変えない
  2. sources.md の表に、取り方（MCP のツールか CLI）と、ref・URL・題名の取り方を書く
- この場面で間違えやすいこと：補助 CLI に API を呼ぶ処理を書く。依頼の取得はスキルの仕事で、補助 CLI は `--body-file` を受け取るだけにする

## 4. プロファイルの項目

- 使う場面：プロファイル（profile.json）の項目
- 見本：`autoflow_kit/profile.py` の `Limits`・`DEFAULT_LIMITS`・`FIELDS`・`_parse_limits`、`autoflow_kit/views.py` の `render_profile`、`tests/test_profile.py` の `test_limits_order`
- 作る・変えるファイル：

  | 順 | パス | 見本との対応 | 守るルール |
  |---|---|---|---|
  | 1 | `autoflow_kit/profile.py` | dataclass の項目、既定値、`FIELDS` の行、`parse` の検証、`SCHEMA_VERSION` を1上げる | PROC-06、NAM-03 |
  | 2 | `autoflow_kit/views.py` | `render_profile` に行を足す | PROC-02 |
  | 3 | `autoflow_kit/setup.py` | リポジトリから検出できる項目だけ、検出を足す | PROC-02 |
  | 4 | 項目を使う段のモジュール | `ctx.profile.<節>.<項目>` で読む | OPS-02 |
  | 5 | `tests/test_profile.py` | `test_<項目名>`（範囲の外を落とす） | TEST-03 |
  | 6 | `kit/claude/skills/autoflow-setup/references/profile-schema.md` | `make docs` | STR-04 |
  | 7 | `docs/design/adr/<次の番号>-<名前>.md` | 古い profile.json の直し方（`setup-new --force` か、手で項目を足す） | PROC-06 |

- 手順：
  1. 既定値は、今の振る舞いを変えない値にする
  2. `SCHEMA_VERSION` を上げると、テストの見本のプロファイル（`profile.make_profile`）も新しい版になる。古い版の値で落ちることを `test_old_schema_version` が確かめる
- この場面で間違えやすいこと：
  - 段のモジュールで `.autoflow/profile.json` を読み直す（OPS-02）。実行の中では `context.begin` が返す写しだけを使う
  - `SCHEMA_VERSION` を上げ忘れる（PROC-06）

## 5. サブエージェントとの JSON と、ひな形の置き換え

- 使う場面：サブエージェントが書く JSON の項目、ひな形の置き換えの名前
- 見本：`autoflow_kit/contracts.py` の `Finding`・`_parse_finding`、`prompts/finder.md` の JSON の例、`tests/support.py` の `finding`、`autoflow_kit/prompts.py` の `TEMPLATES`、`autoflow_kit/reviewing.py` の `review_new` の `shared`
- 作る・変えるファイル：

  | 順 | パス | 見本との対応 | 守るルール |
  |---|---|---|---|
  | 1 | `autoflow_kit/contracts.py` | dataclass の項目と `parse_*` の検証（`unknown_keys` のキーも） | NAM-03、ERR-02 |
  | 2 | `prompts/<役>.md` | JSON の例と、項目の書き方の説明 | STATE-02、PROC-02 |
  | 3 | `tests/support.py` | `act_*` か `finding` などの見本の値に項目を足す | PROC-02 |
  | 4 | 項目を使う段のモジュールか `views.py` | 項目を読む。人に見せる表と詳細は `views.render_*`、プロンプトの一覧の1行は段のモジュールの `_<置き換えの名前>_line`（見本：`reviewing._prior_findings_line`） | DEP-01 |
  | 5 | `tests/test_contracts.py` | `test_parse_<JSON の名前>`（あれば assert を足す） | TEST-03 |

  置き換えの名前を足すときは、`autoflow_kit/prompts.py` の `TEMPLATES`、`prompts/<役>.md`、値を作る段のモジュールの `values` を一緒に変え、値を作る段のテストに `test_<置き換えの名前>` を足す。

- 手順：
  1. 項目は必須にし、無いときの値は文字列なら `""`、一覧なら `[]` にする
  2. 置き換えの値は、生の値か `render.bullets`・`render.table` の結果にする。文はひな形に書く
  3. 選べる値の一覧（`contracts.CHECKS`・`IMPACTS`・`VERDICTS` など）は、要素ごとの定数で書き、比べるときもその定数を使う（`criterion.check == contracts.HUMAN`）。値を足すときは定数と一覧の両方に足す
- この場面で間違えやすいこと：
  - サブエージェントの返答の本文を読んで判断する（STATE-02）。成果はファイルだけで受け取る
  - ひな形の例を直し忘れ、サブエージェントが古い形で書く

## 6. 既存の段の引数と振る舞い

- 使う場面：既存のサブコマンドへの引数、既存の段の振る舞い
- 見本：`autoflow_kit/cli.py` の `decide` の引数と `_run` の分岐、`autoflow_kit/deciding.py`、`tests/test_deciding.py`
- 作る・変えるファイル：

  | 順 | パス | 見本との対応 | 守るルール |
  |---|---|---|---|
  | 1 | 段のモジュール | 入口の関数に引数を足す（最初の文の `context.begin` は変えない） | GATE-03 |
  | 2 | `autoflow_kit/cli.py` | 引数を足し、そのサブコマンドを `RUN_STEPS` から外して `_run` に `decide` と同じ形の分岐を足す | OPS-01 |
  | 3 | `autoflow_kit/status.py` | スキルに引数を渡させるなら、その `次:` の行 | OPS-01 |
  | 4 | `kit/claude/skills/autoflow/SKILL.md` | 引数を使う場面を「繰り返すこと」の表に書く | PROC-02 |
  | 5 | 段のテスト | `test_<引数名>` | TEST-03 |
  | 6 | `tests/test_cli.py` | 引数を渡す流れに assert を足す（全体の流れが変わるときだけ） | TEST-03 |

- 手順：
  1. `RUN_STEPS` の関数は `(where, run_id, now)` の形だけにする。引数を足したら、その段は `_run` の明示の分岐にする
  2. 引数が状態機械の判断を変える（次の段が変わる）なら、パターン7の1から行う
- この場面で間違えやすいこと：引数で関所を飛ばせるようにする（例：`--skip-review`）。関所を緩める引数は作らず、提案として報告する

## 7. 新しい段・サブコマンド

- 使う場面：新しい段・サブコマンド
- 見本：`autoflow_kit/risking.py`（プロンプトを書く段と確かめる段の組）、`autoflow_kit/trail.py` の `RISK`・`RISKED`・`risked`・`_on_risked`、`autoflow_kit/status.py` の `_steps`、`tests/test_risking.py`
- 作る・変えるファイル（PROC-01 の順）：

  | 順 | パス | 見本との対応 | 守るルール |
  |---|---|---|---|
  | 1 | `autoflow_kit/trail.py` | 段の定数と `STEPS`、出来事の定数と `EVENTS`、出来事を作る関数、`TRANSITIONS` の行と前の段からの行き先、`_number` | STATE-01、PROC-01 |
  | 2 | `autoflow_kit/contracts.py`、`autoflow_kit/layout.py` | 受け渡す JSON の型と、置き場のメソッド | CODE-06、ERR-02 |
  | 3 | `autoflow_kit/<段>.py` | 入口の関数（最初の文で `context.begin`） | GATE-03、DEP-01 |
  | 4 | `scripts/structure_check.py`、`docs/design/architecture.md` | `STAGES` と `ENTRIES` の行、許可表の行（保護ファイル。段を足す依頼はこの変更を含む） | STR-02 |
  | 5 | `autoflow_kit/status.py` | `STEP_LABELS` と `_steps` | OPS-01 |
  | 6 | `autoflow_kit/cli.py` | `RUN_STEPS` と `HELP` | STR-03 |
  | 7 | `tests/test_<段>.py`、`tests/test_trail.py` | `<段>Test` と、`test_<段>` | TEST-01、TEST-03 |
  | 8 | `kit/claude/skills/autoflow/SKILL.md`、architecture.md の6章 | 「繰り返すこと」の表と、データの流れ | PROC-02 |

- 手順：
  1. サブエージェントを起動する段は、プロンプトを書く `<段>-new` と、出力を確かめる `<段>-check` の組にする。読み取りだけの役なら、`-check` で `context.require_same_tree` を呼ぶ（GATE-07）
  2. 新しいサブエージェントを足すときは、`contracts.AGENTS`、`kit/claude/agents/autoflow-<役>.md`、`prompts/<役>.md`、`prompts.TEMPLATES` を一緒に足す
- この場面で間違えやすいこと：
  - 段の結果を別のファイル（`<段>.json`）に書き、次の段がそれを読んで判断する（STATE-01）。判断に使う値は出来事に持たせる
  - 段のモジュールから別の段のモジュールを呼ぶ（DEP-01）。2つの段が使う処理は共有のモジュールに置く

## 8. 文言・配布するスキル・サブエージェント

- 使う場面：プロンプトの文言、配布するスキルの手順、サブエージェントの定義
- 見本：`prompts/finder.md`、`kit/claude/skills/autoflow/SKILL.md`、`kit/claude/agents/autoflow-finder.md`
- 作る・変えるファイル：

  | 順 | パス | 見本との対応 | 守るルール |
  |---|---|---|---|
  | 1 | `prompts/<役>.md` | 置き換えの名前（`${名前}`）を変えずに文を直す | STATE-02 |
  | 2 | `kit/claude/skills/<スキル>/SKILL.md` | frontmatter を変えず、500行以内 | STR-05、GATE-02 |
  | 3 | `kit/claude/agents/autoflow-<役>.md` | `tools` を列挙し、`Skill`・`Agent` を入れない | STR-05、OPS-04 |

- 手順：
  1. スキルの「人に確かめること」の節と、決まった1文は消さない（GATE-02）
  2. 置き換えの名前を変えるなら、パターン5の置き換えの手順で行う
- この場面で間違えやすいこと：スキルに「推奨が承認なら、そのまま decide を実行する」のような、人の答えを AI が埋める手順を書く（GATE-02）

## 9. 不具合の修正

- 使う場面：不具合の修正（振る舞いを変えずに直す）
- 見本：直す関数のモジュールと、そのテスト（`tests/test_<モジュール>.py`）
- 作る・変えるファイル：

  | 順 | パス | 見本との対応 | 守るルール |
  |---|---|---|---|
  | 1 | `tests/test_<モジュール>.py` | 直す関数を確かめている既存のメソッドに、落ちる assert を足す。無ければ `test_<直した関数の名前>` | TEST-03 |
  | 2 | 直すモジュール | 関数の中だけを直す | CODE-04 |

- 手順：
  1. 先にテストを足し、`PYTHONPATH=kit/.autoflow python3 -B -m unittest tests.test_<モジュール>` で落ちることを確かめる
  2. 直して、同じテストが通ることを確かめ、`make check` を回す
- この場面で間違えやすいこと：直すついでに名前や構造を変える。依頼に無い整理は提案として報告する
