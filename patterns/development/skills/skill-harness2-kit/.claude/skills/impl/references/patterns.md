# パターン

実装用スキル `impl` の「1. 依頼をパターンに振り分ける」の各行に対応する手順である。節の番号は振り分け表と一致させる。パスは基盤のルートからの相対パスで、`h2_kit/` は `kit/.h2/h2_kit/`、`prompts/` は `kit/.h2/templates/prompts/`、`skill-harness2/` は `kit/claude/skills/skill-harness2/` を指す。

## 1. profile.json の項目を足す・変える

- 使う場面：profile.json の項目を足す・変える
- 見本：`h2_kit/profile.py` の `Profile`、`parse_profile`、`build_default_profile`、`_read_int`（整数）、`_read_choice`（選択肢）、`tests/test_profile.py` の `test_obs_trunc_below_ten_thousand_is_rejected`
- 作る・変えるファイル：

  | 順 | パス | 見本との対応 | 守るルール |
  |---|---|---|---|
  | 1 | `h2_kit/profile.py` | `Profile` のフィールド、`parse_profile` の1行、`build_default_profile` の1行、`SCHEMA_VERSION` を1上げる | NAM-03、CODE-03、ERR-02、STATE-04、PROC-06 |
  | 2 | `h2_kit/planning.py`（plan.md に見せる項目なら） | `_render_plan` の箇条書きか表の1行 | OPS-03 |
  | 3 | 項目を使うモジュール | `env.model.k` の読み方（`Profile` のフィールドを読む） | OPS-02 |
  | 4 | `tests/test_profile.py`、`tests/support.py`（必須の項目なら `build_profile`） | `test_obs_trunc_below_ten_thousand_is_rejected` | TEST-01、TEST-02 |
  | 5 | `skill-harness2/references/profile-guide.md` | 「人と決める項目」か「既定値のままでよい項目」の表の1行 | PROC-02 |
  | 6 | `docs/design/adr/<次の番号>-profile-schema-v<新しい版>.md` | `_template.md` を写す | PROC-06 |

- 項目の種類で、`profile.py` の書き方を決める

  | 項目の種類 | 書き方 |
  |---|---|
  | 編集・合成・選択のセッションに仕事として渡す文 | `OPTIONAL_TEXTS`（無いと方法が動かないなら `REQUIRED_TEXTS`）と `METHOD_TEXTS` に名前を足す。ひな形に入れるのはパターン5で行う |
  | 人に見せるだけの文、選択役への前置きの文 | `OPTIONAL_TEXTS` か `REQUIRED_TEXTS` だけに足す |
  | 整数 | `_read_int(data.get("<名前>"), "<名前>", (1, MAX_<名前>), problems)` と、定数 `MAX_<名前>` |
  | 決まった値のどれか | 定数のタプル（`DELIVERABLES` と同じ形）と `_read_choice` |
  | 実行か編集のセッションの `claude` の設定 | `RolloutSpec` か `ImproverSpec` のフィールドと `_parse_rollout` か `_parse_improver`。続けてパターン2を行う |
  | 正解、採点の基準、期待する出力 | 足さない（STATE-04）。事後の確かめはタスクの `checks.json` に書く |

- 手順：
  1. JSON のキーは snake_case にし、`Profile` のフィールド名と同じ綴りにする（NAM-03）。入れ子を包むだけのキーを足したら、`structure_check.py` の `WRAPPER_KEYS` に足す（TOOL-04 の例外）
  2. `build_default_profile` の値は、項目を足す前と同じ振る舞いになる値にする
  3. `SCHEMA_VERSION` を1上げる。上げると既存の profile.json は `parse_profile` で問題になるので、ADR に「既存の profile.json に足す行」を書く
  4. テストは、正しくない値が問題の一覧に入ることを1つ確かめる。名前は実装用スキルの「テストの名前の式」に従う
- この場面で間違えやすいこと：
  - 項目を `os.environ` や CLI の引数から読む。改善の設定は profile.json だけから読む（OPS-02）
  - 仕事の文を `METHOD_TEXTS` に足し忘れる。採点の語が入ってもはじかれない（STATE-04）
  - `SCHEMA_VERSION` を上げずに形を変える（PROC-06）

## 2. `claude -p` のフラグ・道具・モデルの渡し方を変える

- 使う場面：`claude -p` のフラグ・道具・モデルの渡し方を変える
- 見本：`h2_kit/runner.py` の `ROLLOUT_GUARD_FLAGS`、`SESSION_GUARD_FLAGS`、`build_rollout_command`、`build_session_command`、`tests/test_runner.py` の `test_session_command_is_restricted`
- 作る・変えるファイル：

  | 順 | パス | 見本との対応 | 守るルール |
  |---|---|---|---|
  | 1 | `h2_kit/profile.py`（利用者が値を決めるなら） | パターン1 | PROC-06 |
  | 2 | `h2_kit/runner.py` | `build_rollout_command` か `build_session_command` の `--<フラグ>` の行 | OPS-05、CODE-06 |
  | 3 | `tests/test_runner.py` | `test_session_command_is_restricted` の `assertIn` | TEST-02 |
  | 4 | `docs/design/research.md` | 「Claude Code のヘッドレス実行」の節の「採用するもの」に1項目。フラグ、値の形、この基盤での使い方を日本語で書き、`--help` の英語の説明を写さない。確かめた版が節の見出しの版と違えば、見出しと「確認方法」の版も変える | PROC-02 |

- 変えることで、扱いを決める

  | 変えること | 扱い |
  |---|---|
  | モデル・effort・上限など、profile.json の値を渡すフラグ | 上の表の順に作る |
  | 閉じ込めのフラグか、セッションの道具（`EDIT_TOOLS`、`READ_TOOLS`）を足す・変える | OPS-05 の表を変えるルールの変更。実装せずに提案し、承認を得たら PROC-04 の順で行う |
  | 閉じ込めのフラグを外す、`--dangerously-skip-permissions` などで緩める | 実装しない（OPS-05） |
  | 実行の道具から `Skill` を外す | 実装しない。対象スキルが呼ばれなくなる（OPS-05） |

- 手順：
  1. 入っている Claude Code で `claude --version` と `claude --help` を実行し、フラグの綴りと値の形を確かめる。記憶で書かない
  2. `--` で始まる文字列は `runner.py` だけに書く。`rollout.py` や `recursion.py` はコマンド行を受け取るだけにする（OPS-05）
  3. 偽の claude（`tests/fixtures/fake_claude.py`）は知らない引数を記録するだけなので、振る舞いを変える必要が無ければ変えない
- この場面で間違えやすいこと：
  - 段のモジュールに `["claude", "-p", ...]` を書く。構造検査が落とす（OPS-05）
  - research.md の節の見出しの版と、フラグを確かめた版が食い違ったままになる。Claude Code を上げたときに、どのフラグを確かめ直すかが分からなくなる

## 3. 候補のスキルの木の検証の項目を足す・変える

- 使う場面：候補のスキルの木の検証の項目を足す・変える
- 見本：`h2_kit/validate.py` の `check_tree`、`_list_problems`、`_check_scripts`、`prompts/_surface.md`、`tests/test_validate.py` の `test_more_injections`
- 作る・変えるファイル：

  | 順 | パス | 見本との対応 | 守るルール |
  |---|---|---|---|
  | 1 | `docs/design/adr/<次の番号>-<題>.md`、`docs/design/rules.md` の STATE-06 の表 | 承認を得てから（STATE-06 の表を変えるルールの変更） | PROC-04 |
  | 2 | `h2_kit/validate.py` | `_list_problems` に1行、長くなるなら `_check_<項目>` を足す | NAM-02、ERR-01、CODE-03 |
  | 3 | `prompts/_surface.md` | 「提案ごと捨てる規則」の段落に1文 | STATE-02、PROC-02 |
  | 4 | `tests/test_validate.py` | `test_<項目>` を1つ | TEST-01 |

- 手順：
  1. 問題の文は「<パス> が…。<直し方>」にする。この文は「前の試みは却下された」の後にそのまま編集のセッションへ返る（STATE-06）
  2. 同じ問題には同じ文を返す。`check_tree` は元の木にもある問題を文の一致で除くので、行番号や件数のように木ごとに変わる値を文に入れない
  3. 機械で直せる問題でも、`build_autolinked`（参照ファイルの名指し）の他に自動の直しを足さない。harness2 が自動で直すのは参照の名指しだけである
  4. `_surface.md` には、検証の項目と同じ条件を、編集者が読んで守れる文で書く
- この場面で間違えやすいこと：
  - 検証を `recursion.py` に書く。差し戻しと採用（`adoption.adopt`）の両方で同じ検証を使うため、`validate.py` に置く
  - `_surface.md` を変え忘れ、編集者が知らない理由で木が捨てられる（PROC-02）
  - 採点の印の一覧（`guards.GRADER_MARKERS`）を検証の項目として広げる。印の一覧を変えるのは STATE-04 の変更である

## 4. 証拠の木（`context/`）に資料を足す・変える

- 使う場面：編集のセッションに渡す証拠の木（`context/`）に資料を足す・変える
- 見本：`h2_kit/context.py` の `Evidence`、`write_context`、`_write_named`、`h2_kit/recursion.py` の `_build_evidence`、`prompts/_layout-legend.md`、`tests/test_context.py` の `test_all_evidence_is_written_as_files`
- 作る・変えるファイル：

  | 順 | パス | 見本との対応 | 守るルール |
  |---|---|---|---|
  | 1 | `h2_kit/layout.py` | `DECISIONS_DIR` と同じ形の定数 | CODE-06 |
  | 2 | `h2_kit/context.py` | `Evidence` のフィールド（既定値は空）と、`write_context` の `lines +=` の1行 | STATE-03、CODE-01 |
  | 3 | 資料を渡すモジュール（`recursion.py` の `_build_evidence`、`selection.py`、`reflection.py` のどれか） | `Evidence(...)` の引数 | STATE-03、STATE-05 |
  | 4 | `prompts/_layout-legend.md` | パスと中身の説明の1行 | STATE-02 |
  | 5 | `tests/test_context.py` | `test_all_evidence_is_written_as_files` の `assertIn` | TEST-02 |

- 手順：
  1. 資料は `fsops` で書き、全文を書く。切り詰めるのは軌跡の1つの観測を `obs_trunc` で切るときだけにする（STATE-03）
  2. 空の資料は書かず、道案内（`Built.layout`）にも載せない（`_write_named` は空の一覧なら何も返さない）
  3. 書いた後の `guards.require_clean_directory` を消さない。新しい資料に採点の印があれば、セッションを起動する前に止まる（STATE-04）
- この場面で間違えやすいこと：
  - 資料をプロンプトの文に埋め込む。プロンプトは道案内だけにする（STATE-03）
  - 選択役の証拠にスキルの木・差分・ラベルを入れる（STATE-05）
  - タスクの `checks.json` や事後の検査の結果（`judged.json`）を資料にする（STATE-04）

## 5. プロンプトの文言・置き換えの値を変える

- 使う場面：編集・合成・選択・振り返りのプロンプトの文言・置き換えの値を変える
- 見本：`prompts/propose-inv.md`、`prompts/_yardstick.md`（条件で入る部品）、`h2_kit/prompts.py` の `TEMPLATES`、`h2_kit/recursion.py` の `_build_proposal`、`tests/test_prompts.py` の `test_placeholders_match_the_table`
- 作る・変えるファイル：

  | 順 | パス | 見本との対応 | 守るルール |
  |---|---|---|---|
  | 1 | `prompts/<名前>.md` | 文言と `${置き換えの名前}`、部品なら `${block_<名前>}` | STATE-02、STATE-04 |
  | 2 | `h2_kit/prompts.py`（置き換えの名前を足す・消すときだけ） | `TEMPLATES` の組 | STATE-02 |
  | 3 | 値を作るモジュール（`propose-*`・`mission`・`compose*`・`_rejected` は `recursion.py`、`select` は `selection.py`、`reflect` は `reflection.py`） | `_build_proposal` の `values` | STATE-02、STATE-03 |
  | 4 | `tests/test_prompts.py`、値を作るモジュールのテスト | `test_placeholders_match_the_table` | TEST-02 |
  | 5 | `docs/design/research.md` | 「harness2 の仕組み」の表の「この基盤での形」 | PROC-02 |

- 手順：
  1. 文言だけを変えるなら、ひな形だけを変える。Python のコードは変えない
  2. 先頭の `<!-- … -->` のコメントに、元にした harness2 のプロンプトの名前を書く。harness2 に無い文を足すなら、その理由を同じコメントに書く（ADR-0005）
  3. 条件で入る文は部品（`_<名前>.md`）にし、値を作るモジュールで `prompts.render_part(..., when)` を使う。条件を Python の文字列の連結で作らない
  4. 置き換えの値には profile.json の値やラベルなどの値だけを渡し、説明の文はひな形に書く
- この場面で間違えやすいこと：
  - 指示の文を Python の文字列に書いて値として渡す（STATE-02）
  - 返答のタグ（`<notes>`、`<why>`、`choice` の囲み、`KEEP_BASE`、`NO_ENTRY`）の綴りをひな形だけで変える。`contracts.py` と同じ変更で変える（PROC-02）
  - 「採点基準は無い」の部品（`_answer-free.md`、`_answer-free-select.md`）を外す（STATE-04）

## 6. サブコマンド（段）を足す

- 使う場面：サブコマンド（段）を足す
- 見本：`h2_kit/adoption.py`（最小の段）、`h2_kit/cli.py` の `COMMANDS`・`_build_parser`・`HANDLERS`・`_run_adopt`、`h2_kit/status.py` の `_render_approved`、`tests/test_adoption.py`、`tests/test_cli.py` の `test_command_adopt`
- 作る・変えるファイル（PROC-01 の順）：

  | 順 | パス | 見本との対応 | 守るルール |
  |---|---|---|---|
  | 1 | `h2_kit/layout.py` | 段が書くファイル名の定数（`ADOPTED_FILE`）と、置き場のプロパティ（`adopted_path`） | CODE-06 |
  | 2 | `h2_kit/workspace.py` | 書いたファイルの型（`Adoption`）、`load_<名前>`、`_parse_<名前>`、`build_json` の引数の型 | NAM-03、ERR-02、STATE-01 |
  | 3 | `h2_kit/<段>.py` | `adoption.py` の全体 | STR-02、DEP-01、NAM-02、OPS-04、ERR-01 |
  | 4 | `h2_kit/status.py` | `_render_approved` の、ファイルの有無で `段階:` と `次:` を返す形 | OPS-01、STATE-01 |
  | 5 | `h2_kit/cli.py` | `COMMANDS` に1語、`_build_parser` の引数、`_run_<名前>`、`HANDLERS` に1行 | OPS-01、DEP-04 |
  | 6 | `tests/test_<段>.py`、`tests/test_cli.py`、`tests/test_status.py` | `test_adoption.py`、`test_command_adopt` | TEST-01、TEST-02、TEST-03 |
  | 7 | `scripts/structure_check.py` と `docs/design/architecture.md` | `STAGES` に1行と許可表に1行（承認済みのプロファイルを読む段なら `APPROVED_STAGES` にも）。architecture.md は「データの流れ」にサブコマンドの行、「公開面」のサブコマンドの一覧にも足す | DEP-01、TOOL-04 |
  | 8 | `skill-harness2/SKILL.md` | 「手順」の該当の手順と「繰り返すこと」の表（人が決める場面なら「人が決める場面」の表も） | PROC-02、PROC-07 |

- 置くモジュールを決める

  | 新しいサブコマンドがすること | 置くモジュール |
  |---|---|
  | 新しいファイルを書く処理で、既存の段の間に入る | 新しい段のモジュール `h2_kit/<段>.py` |
  | ファイルを書かず、記録（`summary.json`、`adopted.json`、`judged.json` など）を見せるだけ | `results.py`（見せる段）。記録は `workspace` の `load_*` で読む |
  | 事後の検査（`checks.json` を使う） | `judging.py`。方法のモジュールから呼ばない（STATE-04） |

  `status.py` には次の手を示すことだけを置き、表示だけのサブコマンドを `status.py` に足さない。

- 手順：
  1. 段の公開関数はサブコマンド名にし、引数は `where: layout.Layout` を先頭に、戻り値は人に見せる文字列にする（NAM-02）。日付が要るなら `cli` から `today` を渡す（DEP-04）
  2. 承認済みのプロファイルを使う段なら、公開関数の最初の文で `workspace.load_approved(where)` を呼ぶ（OPS-04）
  3. 段の順番の誤りは `StageError` で「…。status で進みを確かめてください」と投げる
  4. 書くファイルは `fsops.write_*` で書き、完了の印になるファイルを最後に書く（途中で止まっても status が同じ段を示すため。STATE-01）
  5. `structure_check.py` は保護ファイルである。hooks が確認を求めたら、変更が登録の表に要素を足すだけであることを示して承認を得る（TOOL-04）
- この場面で間違えやすいこと：
  - 2つ以上の段で使う関数を片方の段に置き、もう一方から import する。共有のモジュールに置く（STR-02、DEP-01）
  - 進み具合を書いたファイル（`state.json` の類）を足す。進み具合は記録の有無から `workspace.compute_progress` が求める（STATE-01）
  - `print` や `sys.exit` を段に書く。段は文字列を返し、出力は `cli` が行う（DEP-04）
  - `test_command_<名前>` を足し忘れる。構造検査が落とす（TEST-03）

## 7. 既存のサブコマンドの振る舞いを直す、不具合を直す

- 使う場面：既存のサブコマンドの振る舞いを直す、不具合を直す
- 見本：直すモジュールと、`tests/test_<モジュール>.py` の同じ関数のテスト。偽の claude の振る舞いは `tests/fixtures/fake_claude.py` の `invalid-once`（差し戻しの再現）
- 作る・変えるファイル：

  | 順 | パス | 見本との対応 | 守るルール |
  |---|---|---|---|
  | 1 | `tests/fixtures/fake_claude.py`（不具合の再現に新しい返答が要るときだけ） | `_run_propose` の `if "<振る舞い>" in behaviors:` | TEST-02 |
  | 2 | `tests/test_<モジュール>.py` | 同じファイルの既存のテスト | TEST-01、TEST-02 |
  | 3 | `h2_kit/<モジュール>.py`（関数が2つ以上のモジュールで使われていれば共有のモジュール） | 同じモジュールの既存の関数 | STR-02、CODE-01、ERR-01 |
  | 4 | `h2_kit/status.py`（次の手が変わるときだけ） | パターン8 | OPS-01 |

- 手順：
  1. 不具合を再現するテストを先に書き、落ちることを `make test` で確かめる
  2. 偽の claude に返答を足すときは、`behavior=` の新しい名前（小文字の kebab-case）を1つ足し、テストでは `support.build_profile(behaviors=["<名前>"])` で選ぶ。`unittest.mock` を使わない（TEST-02）
  3. 直す。段の順番の条件を変えるときは、段のモジュールと `status.py` の両方を変える（片方だけだと、status が示したコマンドが落ちる）
  4. 失敗の扱いを変えるときは ERR-01 の表に従う。段の失敗は入力の木に戻して `fell_back` を記録し、投げない
- この場面で間違えやすいこと：
  - 直したいモジュールとは別の段のモジュールを import して関数を借りる（DEP-01）
  - 落ちているテストを消す、skip する（TOOL-03）
  - 台帳（`ledger`）に記録しない実行やセッションを足す。R = 4k、P = 3k が合わずに run が止まる（STATE-07）

## 8. status の行、show・plan.md の表示を変える

- 使う場面：status の行、show・plan.md の表示を変える
- 見本：`h2_kit/status.py` の `LINE_KINDS`、`STAGES`、`_render_approved`、`h2_kit/results.py` の `_render_section`、`h2_kit/planning.py` の `_render_plan`、`tests/test_status.py` の `test_line_kinds_are_fixed`
- 作る・変えるファイル：

  | 順 | パス | 見本との対応 | 守るルール |
  |---|---|---|---|
  | 1 | `h2_kit/status.py`、`h2_kit/results.py`、`h2_kit/planning.py` のどれか | `_render_*` の関数 | OPS-01、OPS-03 |
  | 2 | `tests/test_status.py`、`tests/test_results.py`、`tests/test_planning.py` のどれか | 同じファイルの既存のテスト | TEST-02 |
  | 3 | `skill-harness2/SKILL.md`（status の `段階:` か `次:` を変えたら） | 「繰り返すこと」の表 | PROC-02 |
  | 4 | `skill-harness2/references/reading-results.md`（show の見出しや行を変えたら） | 「節の中身」の表 | PROC-02 |
  | 5 | `docs/design/architecture.md`（サブコマンドが出すものを足す・消すとき） | 「データの流れ」の「結果を見て採用する」の、そのサブコマンドの行 | PROC-02 |

- 手順：
  1. status の各行は `LINE_KINDS` の書き出しで始める。新しい書き出しを足すのは OPS-01 の変更なので、実装せずに提案する
  2. 表は `render.render_table`、一覧は `render.render_bullets`、金額は `render.render_usd` で作る（OPS-03）
  3. `次:` の行には、そのまま実行できるサブコマンドを書く（対象の名前を含める）
- この場面で間違えやすいこと：
  - 表を f 文字列の `|` で組み立てる（OPS-03）
  - 段のモジュールの記録を、その段のモジュールを import して読む。記録は `workspace` の `load_*` で読む（DEP-01、ERR-02）
  - `次:` の行に、対象の名前の無いコマンドを書く。スキルがそのまま実行できなくなる（OPS-01）

## 9. 配布するスキル（skill-harness2）の手順か参照ファイルを直す

- 使う場面：配布するスキル（skill-harness2）の手順か参照ファイルを直す
- 見本：`skill-harness2/SKILL.md`（「人が決める場面」と「繰り返すこと」の表）、`skill-harness2/references/troubleshooting.md`（エラーの文の言葉で引く表）
- 作る・変えるファイル：

  | 順 | パス | 見本との対応 | 守るルール |
  |---|---|---|---|
  | 1 | `skill-harness2/references/<名前>.md` | 同じディレクトリの既存の参照ファイル | STR-04 |
  | 2 | `skill-harness2/SKILL.md` | 本文の `references/<名前>.md` の名指し、表の行 | STR-04、PROC-07 |

- 手順：
  1. 補助 CLI の振る舞いを変えずに済むなら、スキルの文だけを変える。CLI の出力の文言を変える必要があるならパターン8を先に行う
  2. 詳しい説明は参照ファイルに置き、SKILL.md は500行以内に収め、参照ファイルは本文で `references/<名前>.md` の形で名指しする（STR-04）
  3. frontmatter は5つのキー（`name`、`description`、`disable-model-invocation`、`allowed-tools`、`argument-hint`）のままにする。`allowed-tools` を広げない
  4. 人に聞く場面を足すなら「人が決める場面」の表に行を足し、AskUserQuestion で聞くと書く（PROC-07）
- この場面で間違えやすいこと：
  - 補助 CLI を通さずにファイルを直接書く手順を足す。状態は CLI だけが書く（STATE-01）
  - `adopt` を人の答えの前に実行する手順にする（PROC-07）
  - エラーの文を troubleshooting.md に足すとき、CLI の実際の文と違う言葉で書く。表はエラーの文の言葉で引かれる

## 10. 方法の骨組みを変える（モード、予算の恒等式、選択の規則、段の順番）

- 使う場面：モードを足す、予算の恒等式（R = 4k、P = 3k）・選択の規則・段の順番など方法の骨組みを変える
- 見本：`docs/design/adr/0007-per-task-h0-and-human-adoption.md`（方法の骨組みを決めた ADR）、`docs/design/research.md` の「harness2 の仕組み」の表
- 作る・変えるファイル：実装しない。次の提案を報告する

  | 順 | 提案に書くこと | 確かめるもの |
  |---|---|---|
  | 1 | 変えたい振る舞いと、harness2 の同じ仕組みとの違い | research.md の「harness2 の仕組み」の表 |
  | 2 | ADR の案（`docs/design/adr/_template.md` の形） | — |
  | 3 | 変わるルール（CODE-06 のラベル・モード名、STATE-05、STATE-07 など）と、構造検査・probe の変更 | rules.md、`.foundation/probes.json` |
  | 4 | 触るファイルの一覧 | architecture.md の変更シナリオ表の「新しいモードを足す」の行 |

- 手順：
  1. 提案を報告し、承認を待つ。承認されたら PROC-04 の順（ADR → rules.md → 検査の設定と probe → 見本）で行う
  2. 承認の後にモードを足すときは、`layout.py`（モード名とラベル）→ `recursion.py` → `selection.py`（候補の集め方）→ `tests/test_recursion.py` の順に作る
- この場面で間違えやすいこと：
  - harness2 に無い工夫（候補を2回ずつ実行する、事後の検査で選ぶ）を骨組みに足す。harness2 の方法から外れ、この基盤の目的（harness2 の模倣）を壊す
  - `ledger.ROLLOUTS_PER_K` か `ledger.SESSIONS_PER_K` だけを変えて恒等式を合わせる。probe（STATE-07-a）が落ちるのは正しい振る舞いである
