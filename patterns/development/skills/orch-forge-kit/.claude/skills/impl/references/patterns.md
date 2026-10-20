# パターン

実装用スキル `impl` の「1. 振り分け表」の各行に対応する手順である。節の番号は振り分け表と一致させる。パスの `kit/.forge/forge_kit/` は `forge_kit/` と略す。

## 1. 指標を足す・変える

- 使う場面：指標・評価の観点を足す、指標の計算を変える
- 見本：`forge_kit/catalog.py` の `delegation`、`forge_kit/score.py` の `CALCULATORS` と `_delegation`、`tests/test_score.py` の `test_delegation`
- 作る・変えるファイル：

  | 順 | パス | 見本との対応 | 守るルール |
  |---|---|---|---|
  | 1 | `forge_kit/catalog.py` | `METRICS` に `Metric(...)` を1件足す。一致度なら `AGREEMENT_METRICS` にも足す | CODE-01、PROC-02 |
  | 2 | `forge_kit/contracts.py`、`forge_kit/collect.py` | 実行の事実が足りないときだけ、`Facts` の項目と `parse_facts`、`collect._facts` の値を足す | NAM-03、ERR-02 |
  | 3 | `forge_kit/metrics.py` | 計算の部品が要るなら純粋な関数で足す | CODE-03、CODE-04 |
  | 4 | `forge_kit/score.py` | `CALCULATORS` に `<id>` の関数を足す。`runs`（1つの課題の実行の並び）を受けて値か `None` を返す | PROC-02、CODE-04 |
  | 5 | `forge_kit/charter.py` | 前提（`requires`）があれば `_check_prerequisites` に検査を足す。採点役が判定する指標なら `grade_items` に判定の項目を足す | ERR-02、STATE-02 |
  | 6 | `tests/test_score.py` | `test_<指標の id>` を1つ足し、計算の値を確かめる。`metrics.py` に部品を足したなら `tests/test_metrics.py` に `test_<関数名>` も足す | TEST-02、TEST-03 |
  | 7 | `make docs` | `forge-goals/references/metric-catalog.md` を作り直す | STR-04 |

- 手順：
  1. 見本の `delegation` を写し、id・名前・`tells`・`computes`・`requires` を書き換える。`computes` は「何を数え、どう平均するか」を1文で書く
  2. 値は課題ごとに求め、`score.metric_scores` が課題の平均を取る。1つの課題で値が決まらない（前提の課題でない、数える編集が無い）ときは `None` を返す
  3. `make docs` を回してから `make check`
- この場面で間違えやすいこと：
  - `CALCULATORS` に足し忘れる（`tests/test_score.py` の `test_every_catalog_metric_has_calculator` で落ちる）
  - 採点役の判定の割合を自分で数え直す。採点役の判定は `_shares`（キーの接頭辞で数える）か `_is_met`（キーで数える）を使う
  - 数える事実が `contracts.Facts` に既にあるのに、`Facts`・`collect`・`trace` の形を変える。結果の無い実行の扱いは事実の形に従う（`None` になりうる項目は `_known` で除き、並びの項目は `len` で0から数える）

## 2. バンドルの決まりを足す・変える

- 使う場面：生成・改善するスキル（バンドル）の形の決まりを足す、決まりの検査を変える
- 見本：`forge_kit/bundle.py` の `RULES` の `B10` と `_no_todo`、`tests/test_bundle.py` の `test_b10`
- 作る・変えるファイル：

  | 順 | パス | 見本との対応 | 守るルール |
  |---|---|---|---|
  | 1 | `forge_kit/bundle.py` | 検査の関数 `_<名前>(ctx)` を足し、`RULES` の最後に `Rule("B<次の番号>", "<文>", _<名前>)` を足す。文の中の数と見出しは定数から作る | STR-06、CODE-04 |
  | 2 | `tests/test_bundle.py` | `test_b<番号>` を1つ足し、`self.edit` で見本のバンドルを違反させて `self.assert_rule("B<番号>")` で確かめる | STR-06、TEST-03 |
  | 3 | `kit/.forge/templates/prompts/draft-skill.md` か `draft-agent.md` | 骨組みが新しい決まりに合わないときだけ直す | STATE-02 |
  | 4 | `tests/fixtures/sample-repo/claude/` | 見本のバンドルが新しい決まりに合わないときだけ直す | TEST-02 |
  | 5 | `make docs` | `forge-build/references/bundle-rules.md` を作り直す | STR-04 |

- 手順：
  1. 決まりの文は `RULES` の1か所にだけ書く。ひな形・スキル・プロンプトに決まりの文を写さない（STR-06）
  2. 検査の関数は、問題の文の一覧を返す。問題が無ければ空の一覧を返す
- この場面で間違えやすいこと：
  - `B` と2桁の番号の文字列を `bundle.py` の外に書く（STR-06 で落ちる）
  - 既存の番号を詰め直す。番号は足すだけにする

## 3. 段を足す・変える

- 使う場面：サブコマンド・段を足す、段の前提や出力を変える
- 見本：`forge_kit/compare.py`、`forge_kit/status.py` の `_round_steps`、`forge_kit/cli.py`、`tests/test_compare.py`、`tests/test_cli.py`
- 作る・変えるファイル：

  | 順 | パス（`<stage>` は段の名前） | 見本との対応 | 守るルール |
  |---|---|---|---|
  | 1 | `forge_kit/contracts.py` | 受け渡す JSON の dataclass と `parse_<名前>` を足す | NAM-03、CODE-01、ERR-02 |
  | 2 | `forge_kit/layout.py` | ファイル名の定数と、`Layout` のパスのメソッドを足す | CODE-06、STATE-01 |
  | 3 | `forge_kit/workspace.py` | `load_<名前>` と、進み具合（`RoundProgress` など）の項目を足す | ERR-02、STATE-01 |
  | 4 | `forge_kit/<stage>.py` | `compare.py` を写す。入口の最初の文で `workspace.approved_charter` を呼ぶ | DEP-01、OPS-04、ERR-01 |
  | 5 | `forge_kit/status.py` | `_build_steps`・`_slot_steps`・`_round_steps` のどれかに、この段の `段階:` と `次:` の行を足す | OPS-01 |
  | 6 | `forge_kit/cli.py` | `make_parser` にサブコマンド、`_handlers` に呼び出し、進める段なら `ADVANCING` に足す | STR-03 |
  | 7 | `tests/test_<stage>.py`、`tests/test_cli.py` | `test_<stage>.py` に入口の関数の `test_<関数名>` と前提のエラーのテストを足し、全体の流れは `test_cli.py` の既存のメソッドに assert を足す | TEST-01、TEST-02、TEST-03 |
  | 8 | `scripts/structure_check.py`、`docs/design/architecture.md` | 許可表（`STAGES`）に行を足す。段を進める入口なら `ENTRIES` にも足す。`structure_check.py` は保護ファイルなので、依頼で明示されていなければ変えずに報告する | STR-02、DEP-01、TOOL-04 |
  | 9 | `kit/claude/skills/forge-<名前>/SKILL.md` | この段を使うスキルの「繰り返すこと」の表に、この段の `次:` の行の扱いを足す | PROC-02、PROC-07 |

- 手順：
  1. 1〜3 で受け渡しの形と置き場を先に決める（PROC-01）
  2. 段のモジュールは、共有のモジュールだけを import する。他の段の関数が欲しくなったら、共有のモジュール（`views`、`workspace` など）に移す
  3. 出力は文字列を返し、`print` は `cli` に任せる。日付が要るなら `cli` から引数で受け取る
- この場面で間違えやすいこと：
  - 段のモジュールから別の段を import する（DEP-01 で落ちる）
  - ファイル名を段のモジュールに直接書く（CODE-06 で落ちる）
  - `status` に足し忘れ、スキルがその段に辿り着けない

## 4. サブエージェント・実行役との受け渡しを変える

- 使う場面：サブエージェントや実行役へのプロンプトの文言、置き換えの値、サブエージェントが書く JSON の項目を変える
- 見本：`kit/.forge/templates/prompts/grader.md`、`forge_kit/prompts.py` の `TEMPLATES`、`forge_kit/collect.py` の `_grader_prompt`、`forge_kit/contracts.py` の `parse_grade`
- 作る・変えるファイル：

  | 順 | パス | 見本との対応 | 守るルール |
  |---|---|---|---|
  | 1 | `kit/.forge/templates/prompts/<名前>.md` | 文言を直す。置き換えは `${名前}` の形 | STATE-02、OPS-03 |
  | 2 | `forge_kit/prompts.py` | 置き換えの名前を足したら `TEMPLATES` の集合にも足す | STATE-02、PROC-02 |
  | 3 | 値を作る段のモジュール（`designing`、`building`、`prepare`、`collect`、`analyze` のどれか） | `values` の辞書に足す。値は下の「値の作り方」に従う | DEP-01、STATE-02 |
  | 4 | `forge_kit/contracts.py` か `forge_kit/design.py` | JSON の項目を変えたら dataclass と `parse_*` を変える | NAM-03、ERR-02 |
  | 5 | ひな形の JSON の例 | 4 と同じ形にそろえる | STATE-02 |
  | 6 | 値を作る段のテスト、`tests/test_prompts.py`、`tests/test_contracts.py` | 値を作る段のテストに `test_<置き換えの名前>` を足す。`test_prompts.py` の `values` を表に合わせる。JSON の項目を変えたら `test_contracts.py` の `test_parse_<名前>` に assert を足す（無ければ足す） | TEST-01、TEST-03 |

- 値の作り方（STATE-02）：値に文を書かない。説明・指示・値を囲む記号はひな形に書く

  | 値 | 入れるもの | ひな形に書くこと |
  |---|---|---|
  | 1つの値（パス、コマンド、名前） | 生の値。無いときは `render.MISSING`（`—`） | 値を囲む `` ` ``、「`—` なら…」の文 |
  | 長さがデータで決まる一覧 | `render.bullets(並び)`（空なら `- なし`） | 「`- なし` なら…」の文 |
  | 表 | `render.table(見出し, 行)` | 表の前の説明 |

- 触らないもの：`forge-goals` のスキルと `charter-schema.md`。charter の既存のキーの値を使うだけなら、キーの名前・形・決まりは変わらない（PROC-02）
- 手順：
  1. ひな形の中に `$` を置き換え以外で書かない（置き換えの名前と見なされる）
  2. 設計役・構築役・採点役・分析役の成果はファイルで受け取り、最後の返答は `完了: <パス>` の1行に固定する。実行役の作業は、`execute` が保存する実行の記録とコピーの差分で受け取る（STATE-02）
  3. サブエージェントが書いてよい場所は、プロンプトが示す `.forge/` の下だけにする（OPS-04）
- この場面で間違えやすいこと：
  - ひな形の JSON の例と `parse_*` の形がずれる。サブエージェントは例のとおりに書くので、検証で落ち続ける

## 5. 配布するスキル・サブエージェントを変える

- 使う場面：配布するスキル（forge-goals、forge-build、forge-run）やサブエージェントの定義の手順・道具を変える
- 見本：`kit/claude/skills/forge-run/SKILL.md`、`kit/claude/agents/forge-grader.md`
- 作る・変えるファイル：

  | 順 | パス | 見本との対応 | 守るルール |
  |---|---|---|---|
  | 1 | `kit/claude/skills/forge-<名前>/SKILL.md` | 手順・表を直す。500行以内 | STR-05、PROC-07 |
  | 2 | `kit/claude/skills/forge-<名前>/references/<ファイル>.md` | 詳細を移す。SKILL.md から1階層で参照する。生成物（`metric-catalog.md`、`bundle-rules.md`）は手で直さない | STR-05、STR-04 |
  | 3 | `kit/claude/agents/forge-<役>.md` | `tools` を列挙し、`Skill` と `Agent` を入れない。採点役と分析役は `omitClaudeMd: true` を残す | STR-05 |
  | 4 | `tests/test_install.py` | 写す先のファイルが増えたら確かめる | TEST-01 |

- 手順：
  1. スキルの手順は、補助 CLI の `status` の出力（`段階:`、`次:`、`job`、`その後:` ほか `status.LINE_KINDS` の行）の扱いとして書く。段の判断をスキルに書かない
  2. 人に決めてもらう場面は「## 人に確かめること」に足す。選ぶ値は AskUserQuestion で、あなたの案を先頭の選択肢にして `（推奨）` を付ける。人の言葉を残す値は文章で聞き、返ってきた文をそのまま使う（PROC-07）
- この場面で間違えやすいこと：
  - スキルに段の順番を独自に書き、`status` と食い違う
  - 人の言葉を残す値（`purpose`、ゴールの `statement`、評価課題、`--feedback`）を AskUserQuestion の選択肢にする

## 6. charter・設計の項目を足す・変える

- 使う場面：charter か設計（design.json）の項目を足す・意味を変える
- 見本：`forge_kit/charter.py` の `Executor` と `max_budget_usd`、`forge_kit/views.py` の `_executor_text`、`tests/test_charter.py` の `test_max_budget_usd`
- 作る・変えるファイル：

  | 順 | パス | 見本との対応 | 守るルール |
  |---|---|---|---|
  | 1 | `docs/design/adr/<番号>-<題名>.md` | 移行の手順（古い charter・設計の直し方）を書く | PROC-06 |
  | 2 | `forge_kit/charter.py` か `forge_kit/design.py` | dataclass、`shape.unknown_keys` に渡すキー（最上位は `TOP_KEYS`）、検証、`skeleton`（charter だけ）、`SCHEMA_VERSION` を1上げる | NAM-03、ERR-02、PROC-06 |
  | 3 | `forge_kit/views.py` | 人が読む版（charter.md、design.md）に項目を出す | OPS-03 |
  | 4 | 項目を使う段のモジュール | 値を使う。設計の項目なら、骨組みを作る `building._skeleton` も直す | DEP-01 |
  | 5 | `kit/claude/skills/forge-goals/references/charter-schema.md` か `kit/claude/skills/forge-build/references/design-schema.md` | 項目の表と例を直す | PROC-02 |
  | 6 | `kit/claude/skills/forge-goals/SKILL.md` か `kit/.forge/templates/prompts/designer.md` | 人と決める手順、または設計役への指示に足す | PROC-07、STATE-02 |
  | 7 | `tests/support.py`、`tests/test_charter.py` か `tests/test_design.py` | 見本の charter・設計を直し、`test_<項目の名前>` を足す。人が読む版に出したなら `tests/test_views.py` の既存のメソッドに assert を足す | TEST-02、TEST-03 |

- この場面で間違えやすいこと：
  - スキーマの文書の例を直し忘れる（`tests/test_charter.py`・`tests/test_design.py` が例を検証して落ちる）
  - `SCHEMA_VERSION` を上げ忘れる（レビューで差し戻す）

## 7. 実行役の引数か、実行の記録から読む数を変える

- 使う場面：`claude -p` の引数を変える、実行の記録（stream-json）から新しい数や項目を読む
- 見本：`forge_kit/execute.py` の `command`、`tests/test_execute.py` の `test_command`、`forge_kit/trace.py` の `_depth`、`tests/test_trace.py` の `test_spawn_depth`
- 作る・変えるファイル：

  | 順 | パス | 見本との対応 | 守るルール |
  |---|---|---|---|
  | 1 | `docs/design/research.md` | 引数や項目が公式の文書にあることを、出典付きで書く | OPS-05 |
  | 2 | `forge_kit/execute.py` | 引数は `command` の中だけで組み立てる。権限を広げる引数を足さない | OPS-05 |
  | 3 | `forge_kit/trace.py` | 記録を読む関数を `_<名前>` で足し、`Trace` に項目を足し、`parse` で埋める | ERR-02、CODE-01 |
  | 4 | `tests/fixtures/streams/<名前>.jsonl` | 新しい項目を含む記録を足すか、既存の記録に行を足す | TEST-02 |
  | 5 | `tests/test_execute.py` か `tests/test_trace.py` | `test_command` の引数の並びを直すか、`test_<項目の名前>` を足す | TEST-03 |
  | 6 | 使う指標 | 読んだ数を指標に使うなら、パターン1を続けて行う | PROC-02 |

- この場面で間違えやすいこと：
  - `"-p"` を `execute.py` の外に書く（OPS-05 で落ちる）
  - 文書に無い記録の項目を読む。項目が無いときは数えない（`None`）扱いにする

## 8. 不具合を直す

- 使う場面：既存の関数の中だけで直る不具合を直す
- 見本：直すモジュールと、その `tests/test_<モジュール>.py`
- 作る・変えるファイル：

  | 順 | パス | 見本との対応 | 守るルール |
  |---|---|---|---|
  | 1 | `tests/test_<モジュール>.py` | 不具合を再現する assert を、直す関数を確かめている既存のメソッドに先に足し、落ちることを確かめる。そのメソッドが無ければ `test_<直す関数の名前>` を足す | TEST-02、TEST-03 |
  | 2 | `forge_kit/<モジュール>.py` | 直す | 該当する節 |

- 手順：
  1. 直しが複数のモジュールにまたがるなら、このパターンではない。振り分け表で別の行に当てるか、提案として報告する
- この場面で間違えやすいこと：
  - テストで `unittest.mock` を使って再現する（TEST-02 で落ちる）。`tests/support.py` の部品で状態を作る
