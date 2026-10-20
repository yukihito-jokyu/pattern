---
name: impl
description: orch-forge-kit で実装・変更・追加・修正を行う手順。「指標を足して」「バンドルの決まりを足して」「サブコマンドを足して」「採点役のプロンプトを直して」「forge-run の手順を変えて」「charter に項目を足して」「claude -p の引数を変えて」「status の表示がおかしいので直して」のような、この基盤のコード・プロンプト・配布スキルを書く・変える依頼では、依頼の大小にかかわらず必ず使う。依頼をパターンに振り分け、決められた順序で作り、`make check` と完了前チェックリストで確かめてから報告する。
---

# orch-forge-kit の実装手順

このスキルは次の資料と一緒に使う。パスは基盤のルートからの相対パスである。

- `docs/design/rules.md`：ルールの全文。`<接頭辞>-<番号>` のルールIDで参照する
- `.claude/skills/impl/references/patterns.md`：パターンごとの手順と、作るファイルの一覧
- `docs/design/architecture.md`：依存の許可表、データの流れ、変更シナリオ表
- 見本（参照実装）：`kit/.forge/forge_kit/compare.py`（小さな段）、`kit/.forge/forge_kit/views.py`（共有のモジュール）、`kit/.forge/forge_kit/bundle.py` の `RULES`（決まりの表）、`tests/test_compare.py`・`tests/test_cli.py`（テスト）、`kit/.forge/templates/prompts/grader.md`（ひな形）、`kit/claude/skills/forge-run/SKILL.md`（配布スキル）

既存のコードと rules.md が食い違ったら rules.md に従い、食い違いを報告に書く。

## 1. 依頼をパターンに振り分ける

| 依頼に含まれること | patterns.md の節 |
|---|---|
| 指標・評価の観点を足す、指標の計算を変える | 1 |
| 生成・改善するスキル（バンドル）の形の決まりを足す、決まりの検査を変える | 2 |
| サブコマンド・段を足す、段の前提や出力を変える | 3 |
| サブエージェントや実行役へのプロンプトの文言、置き換えの値、サブエージェントが書く JSON の項目を変える | 4 |
| 配布するスキル（forge-goals、forge-build、forge-run）やサブエージェントの定義の手順・道具を変える | 5 |
| charter か設計（design.json）の項目を足す・意味を変える | 6 |
| `claude -p` の引数を変える、実行の記録から新しい数や項目を読む | 7 |
| 既存の関数の中だけで直る不具合を直す | 8 |

- 複数の行に当たる場合は、表の上から順に全部行う
- 道具（ruff、mypy）の版を上げる依頼は、表のどの行でもない。ADR を書いてから `Makefile` の `RUFF`・`MYPY` を変え、research.md を直し、`make check` と `violation_probe.py` を通す（PROC-03）
- どの行にも当たらない場合は、実装しない。必要なパターンとルールを提案として報告する。見本に無い形をその場で発明すると、作者ごとに違う形が生まれるからである

## 2. 依頼から決まらない値

推測で決めない。聞ける状況ならユーザーに聞く。聞けない状況なら既定値で決め、報告の3に書く。

| 決めること | 何に響くか | 既定値 |
|---|---|---|
| 新しい指標の id | charter、`metric-catalog.md`、テストの名前 | 数える事実（`contracts.Facts` の項目）があれば、その項目の名前と同じ（`cost_usd`、`duration_sec`、`launches` の形）。無ければ、測るものを表す英小文字の語を `_` でつなぐ |
| 新しい指標の測り方 | 採点役の起動回数 | 差分・事実（facts.json）・実行の記録だけで数えられるなら `machine`、それ以外は `grader` |
| 新しい指標の向きと既定の閾値 | charter のひな形、合否 | 割合は `higher` と `1.0`、上限の無い量は `lower` と、費用なら `2.0`、秒なら `900.0`、回数なら `10.0`（既存の `cost_usd`、`duration_sec`、`launches` と同じ値） |
| 新しい指標を推奨（ひな形に入れる）にするか | `charter-new` のひな形 | 推奨にしない（`recommended=False`） |
| 新しいバンドルの決まりの番号 | `bundle-rules.md`、テストの名前 | `RULES` の最後の番号の次（`B14` の形）。既存の番号を詰めない |
| 新しいサブコマンドの名前 | スキルの表、`status` の出力 | 英小文字の動詞1語（`compare` の形）。2語なら `-` でつなぐ（`bundle-check` の形） |
| 新しいエラーの種類 | 終了コードは同じ。文言の書き方 | 前の段が済んでいない → `StageError`、ファイルの形 → `InvalidFileError`、外部コマンド → `CommandError`、それ以外 → `KitError` |
| 新しいファイルの置き場 | 消してよいか（STATE-01） | 記録として残すものは `.forge/targets/<id>/`、作り直せるものは `.forge/work/<id>/` |
| 人に見せる文言 | スキルが読む行の形 | `status` の行は `status.LINE_KINDS` の書き出しだけを使う（OPS-01）。他の出力は既存の段の言い回し（`段階: …`、`次: …`、`その後: …`、`WARN …`）にそろえる |
| 人が決める値をコマンドに渡すときの書き方 | `status` の行、配布するスキルの手順 | `status` の関数の中で、`_command` に渡す文字列に `--<引数の名前> '<日本語の名前>'` を直接書く（OPS-01）。新しい種類の行、定数、変数を足さない |
| 新しい置き換えの名前 | ひな形、`prompts.TEMPLATES`、テストの名前 | 値の元になる項目か引数の名前と同じにする（引数 `--feedback` → `${feedback}`、`target.skill_name` → `${skill_name}`）。前に持ち主の名前を足さない |
| 置き換えの値が無いときの書き方 | ひな形の文 | `<値> or render.MISSING` の形で、空文字だけを無い値として `render.MISSING` を入れ、「`—` なら…」をひな形に書く（STATE-02）。値を `strip` しない（`feedback or render.MISSING` と同じ） |
| 新しい CLI の引数を必須にするか | 呼び出し方 | 人が省ける値は任意にし、既定値は空文字か charter の値にする |
| 段の入口の関数に足す引数の位置 | 呼び出し方、テスト | `where`（と `slot`・`round_no`）の後、`today` の前に置く（`design_new(where, feedback)`、`install(where, today)` の形） |
| 人の言葉を受け取る引数の値 | 記録とプロンプトに入る文 | 受け取ったまま記録して渡す。`strip` などで変えない（`--feedback` と同じ） |
| `.forge/targets/` に残る記録の JSON に項目を足したときの古い記録 | 前の版で書いた記録が読めるか | 項目の無い記録を既定値で読む（PROC-06） |
| 項目が取りうる値の一覧の定数の名前 | 定数の名前、テスト | 項目の名前の複数形を大文字にする（`priority` → `PRIORITIES`、`method` → `METHODS`、`direction` → `DIRECTIONS`）。文書の言い方（`effort level` など）から名前を作らない |
| ADR のファイル名 | `docs/design/adr/` | `<4桁の番号>-<足す・変える charter のキー、CLI の引数、決まりの名前を kebab-case にしたもの>.md`（`executor.effort` → `<番号>-executor-effort.md`）。そうした名前の無い決定は、決めたことを3語以内の kebab-case にする |
| 新しいテストのメソッドの位置 | テストのファイルの差分 | テストのクラスの最後のメソッドの後に足す。既存のメソッドの並びは変えない |
| 人に聞く場面の聞き方 | 配布するスキルの「## 人に確かめること」 | 選ぶ値は AskUserQuestion（案を先頭にして `（推奨）`）、人の言葉を残す値は文章で聞く（PROC-07） |

## 3. 書く前に読む

1. patterns.md の該当する節を最後まで読む
2. rules.md のうち、パターンに対応する接頭辞の節をすべて読む

   | パターン | 読む節 |
   |---|---|
   | 1 指標 | STR、CODE、PROC、TEST |
   | 2 バンドルの決まり | STR（STR-06）、CODE、TEST |
   | 3 段 | STR、DEP、ERR、STATE、OPS、TEST、PROC |
   | 4 受け渡し | STATE、ERR、NAM、TEST |
   | 5 配布スキル | STR（STR-05）、PROC（PROC-07） |
   | 6 charter・設計 | NAM、ERR、PROC（PROC-06） |
   | 7 実行役の引数・実行の記録 | OPS（OPS-05）、ERR、TEST |
   | 8 不具合 | 直すモジュールに関係する節と TEST |

3. 見本の該当ファイルを開き、構成・命名・import の並び・コメントの書き方を確かめる

## 4. 作る順序

patterns.md の該当節の「作る・変えるファイル」の順に作る。段を足すときは、契約（`contracts`・`layout`）→ 段のモジュール → `status` → `cli` → テスト → スキルの表の順にする（PROC-01）。生成物（`metric-catalog.md`、`bundle-rules.md`）は手で書かず、`make docs` で作る。

各ファイルを保存するたびに、hooks が `make fix-file` で整形と lint を走らせる（TOOL-02）。指摘が出たら、次のファイルに進む前に直す。

## 5. 検証する

1. `make check` を実行する
2. 落ちたら、エラーに出たルールIDか lint のルール名を rules.md で引き、コードを直す。lint のルール名とルールIDの対応は `docs/design/enforcement-matrix.md` にある
3. 次の方法で検査を黙らせない
   - 検査の設定や保護ファイルを変える
   - 抑止コメントを書く
   - テストを skip する、または消す

   どうしても直せない場合は、その状態のまま報告する

## 6. 完了前チェックリスト

該当するファイルを開き、1つずつ確かめる。

- [ ] PROC-02：波及の対応表の組を、両側のファイルを開いて突き合わせた（`catalog.METRICS` ⇔ `score.CALCULATORS` ⇔ `make docs`、`bundle.RULES` ⇔ `tests/test_bundle.py` の `test_b<番号>` ⇔ `make docs`、`prompts.TEMPLATES` ⇔ ひな形、`contracts.AGENTS` ⇔ `kit/claude/agents/` ⇔ 起動するスキルの表、charter のキー ⇔ `charter-schema.md`、設計のキー ⇔ `design-schema.md`、`layout` の置き場 ⇔ architecture.md のデータの流れ、`status` の次の手 ⇔ スキルの「繰り返すこと」の表、モジュールの増減 ⇔ `structure_check.py` と architecture.md の許可表）
- [ ] NAM-02：足した関数の先頭の動詞が、語彙表（`read_`、`load_`、`parse_`、`write_`、`render_`、`make_`、`check_`、段の名前）の意味どおりで、同じ意味の別名を使っていない。真偽値を返す関数は `is_`・`has_` で始まる
- [ ] CODE-01：引数の `dict` と `list` を変えていない（検証の関数が受け取る `problems` に問題を足すのは除く）
- [ ] STATE-02：`prompts.render` に渡す値に文を書いていない（生の値、`render.MISSING`、`render.bullets`、`render.table` のどれか）
- [ ] OPS-01：`status` に人が決める値を足したなら、`_command` に渡す文字列に `'<日本語の名前>'` を直接書いた
- [ ] TEST-03：足した名前ごとに `test_<名前>` を、rules.md の表の置き場に1つ足した
- [ ] STATE-01：進み具合を新しい状態ファイルに書いていない。新しいファイルは置き場の表に合っている
- [ ] OPS-03：人に見せる表と数を `render` の関数で書いた
- [ ] PROC-06：charter か設計の形を変えたなら `SCHEMA_VERSION` を上げ、ADR を書いた
- [ ] TOOL-04：保護ファイルを変えていない（変えたなら依頼で明示されている）
- [ ] TOOL-02、PROC-05：`make check` が通った

## 7. 報告する

次の順で書く。

1. 何を作ったか（使ったパターン）
2. 変えたファイルの一覧（作る順序の順）
3. 2 で決めた値と、その根拠（依頼文、ユーザーの回答、既定値のどれか）
4. `make check` の結果（出力の末尾）
5. 決めきれずに残したこと、ルールと既存コードの食い違い
