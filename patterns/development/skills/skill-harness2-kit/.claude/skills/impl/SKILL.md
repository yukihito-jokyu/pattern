---
name: impl
description: skill-harness2-kit で実装・変更・追加・修正を行う手順。「プロンプトの文言を直して」「候補の検証の項目を足して」「claude のフラグを変えて」「profile.json に項目を足して」「証拠の木に資料を足して」「サブコマンドを追加して」「status の表示を変えて」「〜の不具合を直して」「skill-harness2 の手順を直して」「モードを足して」などの依頼で使う。この基盤のコードや配布物を書く・変える依頼では、依頼の大小にかかわらず必ず使う。依頼をパターンに振り分け、決められた順序で作り、`make check` と完了前チェックリストで確かめてから報告する。
---

# skill-harness2-kit の実装手順

このスキルは次の資料と一緒に使う。パスは基盤のルートからの相対パスである。

- `docs/design/rules.md`：ルールの全文。`<接頭辞>-<番号>` のルールIDで参照する
- `.claude/skills/impl/references/patterns.md`：パターンごとの手順と、作るファイルの一覧
- `docs/design/architecture.md`：依存の許可表、データの流れ、変更シナリオ表
- `docs/design/research.md`：harness2 のどの仕組みを、この基盤のどこに移したかの表
- 見本（参照実装）：`kit/.h2/h2_kit/`（段は `adoption.py` が最小の見本）、`kit/.h2/templates/prompts/`、`tests/`（`support.py`、`fixtures/fake_claude.py`、`test_adoption.py`）

既存のコードと rules.md が食い違ったら rules.md に従い、食い違いを報告に書く。

## 1. 依頼をパターンに振り分ける

| 依頼に含まれること | patterns.md の節 |
|---|---|
| profile.json の項目を足す・変える | 1 |
| `claude -p` のフラグ・道具・モデルの渡し方を変える | 2 |
| 候補のスキルの木の検証の項目を足す・変える | 3 |
| 編集のセッションに渡す証拠の木（`context/`）に資料を足す・変える | 4 |
| 編集・合成・選択・振り返りのプロンプトの文言・置き換えの値を変える | 5 |
| サブコマンド（段）を足す | 6 |
| 既存のサブコマンドの振る舞いを直す、不具合を直す | 7 |
| status の行、show・plan.md の表示を変える | 8 |
| 配布するスキル（skill-harness2）の手順か参照ファイルを直す | 9 |
| モードを足す、予算の恒等式（R = 4k、P = 3k）・選択の規則・段の順番など方法の骨組みを変える | 10 |

- 複数の行に当たる場合は、表の上から順に全部行う（上の行が作るものを下の行が使うため）
- 10 の行に当たる場合は、他の行も含めて実装せず、patterns.md の10節に従って提案だけを報告する
- どの行にも当たらない場合は、実装しない。必要なパターンとルールを提案として報告する。見本に無い形をその場で発明すると、作者ごとに違う形が生まれるからである

## 2. 依頼から決まらない値

推測で決めない。聞ける状況ならユーザーに聞く。聞けない状況なら既定値で決め、報告の3に書く。

| 決めること | 何に響くか | 既定値 |
|---|---|---|
| サブコマンドの名前 | `cli.COMMANDS`、段の公開関数名（同じ綴り。`-` と `_` は使えない）、status の `次:` の行、SKILL.md | ファイルを書くサブコマンドは小文字の英語の動詞1語（既存の `init`、`check`、`approve`、`run`、`adopt`、`judge`）。ファイルを書かずに見せるだけのサブコマンドは、見せるものを表す小文字の英語の名詞1語（既存の `status`） |
| ADR のファイル名 | `docs/design/adr/` | `<次の4桁の番号>-<決めたことを表す英語の kebab-case>.md`。profile.json の形を変えた ADR は `<番号>-profile-schema-v<新しい SCHEMA_VERSION>.md` |
| 段のモジュールの名前 | `structure_check.py` の `STAGES`、architecture.md | 段がすることを表す英語の名詞1語（既存の `planning`、`execution`、`results`、`adoption`、`judging` と同じ形） |
| 新しいファイルの名前 | `layout.py` の `<名前>_FILE` か `<名前>_DIR` の定数 | harness2 に同じ役割のファイルがあればその名前（`INDEX.md`、`EXPERIENCE.md` と同じ扱い）、無ければ小文字の英語1語と拡張子 |
| profile.json の新しい項目の名前 | キー、`Profile` のフィールド、profile-guide.md | 小文字の英語の snake_case。harness2 の profile に同じ役割の項目があればその名前 |
| profile.json の新しい項目の既定値 | `profile.build_default_profile` | 項目を足す前と同じ振る舞いになる値 |
| 整数の項目の上下限 | `profile._read_int` の `bounds` | 下限は 1。上限は `profile.py` に `MAX_<名前>` の定数で置き、harness2 に上限があればその値、無ければ `MAX_K` と同じ 5 |
| プロンプトの新しい文 | ひな形 | harness2 のプロンプトに同じ働きの文があれば、その文の日本語訳（ADR-0005）。無ければ既存のひな形にある語と並びを使い、新しい言い回しを作らない |
| 置き換えの名前 | `prompts.TEMPLATES`、ひな形の `${…}` | 値が profile.json の項目なら項目名と同じ綴り。それ以外は小文字の英語の snake_case |
| エラーと検証の問題の文 | 利用者、編集のセッション（差し戻しの文になる） | 「<何が起きたか>。<次にすること>」の日本語（例：`SKILL.md がありません。消さずに編集してください`） |
| 人に見せる新しい文言（status の行、show・plan.md の見出しや表の列） | 利用者とスキルの読み分け | 既存の文言にある語と並びをそのまま使う（例：「落ちて入力の木に戻った段」「選ばれた候補」） |
| テストの関数名 | `tests/test_<モジュール>.py` | 下の「テストの名前の式」の表の式。式に当てはめた後の語の選び方も、表の例に合わせる |

### テストの名前の式

| 確かめること | 関数名の式 | 例 |
|---|---|---|
| 足した・移した公開関数（共有のモジュール） | `test_<関数名>`。条件で2つ以上に分けるときだけ `test_<関数名>_<条件>` | `test_render_usd`、`test_build_confirm_code` |
| profile.json の項目が問題になること | `test_<項目名>_<条件>_is_rejected`。条件は、型の違いなら `of_wrong_type`、上下限の外なら `out_of_range`、選択肢の外なら `not_in_choices`。入れ子の項目は葉の名前だけを使い、全部の置き場を1つのテストで確かめる | `test_timeout_sec_out_of_range_is_rejected`（`rollout` と `improver` の両方を確かめる） |
| コマンド行のフラグ | `test_<フラグの英語の snake_case>_is_passed_only_when_set`。全部の置き場（実行とセッション）を1つのテストで確かめる | `test_effort_is_passed_only_when_set` |
| ひな形に置き換えの値が入ること | `test_<ひな形の名前の snake_case>_prompts_include_<置き換えの名前>`（同じ値を2つ以上のひな形に入れたら、ひな形の名前の共通の接頭辞だけを使う） | `test_select_prompts_include_ids`、`test_compose_prompts_include_k`（`compose` と `compose-round`） |
| 検証の項目 | `test_<項目の英語名>` | `test_more_injections` |
| サブコマンドの出力の一部 | `test_<サブコマンド>_shows_<出すものの英語名>`。条件で出し分けるなら `_only_after_<条件の英語>` を付ける | `test_show_shows_diversity`、`test_status_shows_pending_only_after_run` |
| 不具合の再現 | `test_<サブコマンドか関数>_<正しい振る舞いを表す英語の動詞句>` | `test_run_resumes_without_new_calls` |

## 3. 書く前に読む

1. patterns.md の該当する節を最後まで読む
2. rules.md のうち、次の接頭辞の節をすべて読む

   | パターン | 読む接頭辞 |
   |---|---|
   | 1 | STR、NAM、CODE、ERR、STATE、OPS、TEST、PROC |
   | 2 | DEP、STATE、OPS、TEST、PROC |
   | 3 | CODE、ERR、STATE、TEST、PROC |
   | 4 | CODE、STATE、TEST、PROC |
   | 5 | STATE、PROC |
   | 6、7 | STR、DEP、NAM、CODE、ERR、STATE、ASYNC、OPS、TEST、PROC |
   | 8 | OPS、STATE、PROC |
   | 9 | STR、STATE、PROC |
   | 10 | 全部 |

3. 見本の該当ファイルを開き、構成・命名・import の並び・コメントの書き方を確かめる
4. プロンプトや方法の振る舞いに触れるなら、research.md の「harness2 の仕組み」の表で、その振る舞いの元になった harness2 の仕組みを確かめる。方法の流れ（段の順番、実行やセッションの回数、合成・選択・振り返りの規則）を harness2 と違うものにする変更は、10 と同じく提案にする。プロンプトに文を足すことは、この項目に当たらず、patterns.md の5節に従う

## 4. 作る順序

patterns.md の該当節の「作る・変えるファイル」の順に作る。サブコマンドを足すときは PROC-01 の順（`layout.py` → `workspace.py` → 段のモジュール → `status.py` → `cli.py` → テスト → `structure_check.py` の表と architecture.md の許可表 → SKILL.md の表）に作る。

新しい `_` で始まる関数は、それを最初に呼ぶ関数より後ろに、呼ばれる順に置く（見本：`execution.run` の後の `_render_overview`、`_run_task`、`_run_mode`）。テストの関数は、テストのファイルの既存のクラスの末尾に足し、既存のテストの間に挟まない。

足した公開関数と、別のモジュールへ移した公開関数には、そのモジュールの `tests/test_<モジュール>.py` にテストを1つずつ足す（名前は2節の「テストの名前の式」）。振る舞いを変えたサブコマンドには、その段のテストのファイルにテストを1つ足す。偽の claude の振る舞いを足すときは `tests/fixtures/fake_claude.py` の `behavior=` の値を1つ足し、テストからはプロファイルの `claude` で選ぶ（TEST-02）。

各ファイルを保存するたびに、hooks が `make fix-file` で format と lint を走らせる（TOOL-02）。指摘が出たら、次のファイルに進む前に直す。

## 5. 検証する

1. `make check` を実行する（PROC-05）
2. 落ちたら、エラーに出たルールIDか lint のルール名を rules.md で引き、コードを直す。lint のルール名とルールIDの対応は `docs/design/enforcement-matrix.md` にある
3. 次の方法で検査を黙らせない
   - 検査の設定や保護ファイルを変える（TOOL-04）
   - 抑止コメントを書く（TOOL-03）
   - テストを skip する、または消す
   - `guards.MEASUREMENT_WORDS` や `guards.GRADER_MARKERS` から語を消す（STATE-04）

   どうしても直せない場合は、その状態のまま報告する。ルールそのものを変えるべきなら、実装せずに PROC-04 の順で提案する

## 6. 完了前チェックリスト

該当するファイルを開き、1つずつ確かめる。

- [ ] PROC-02：波及の対応表の組を両側とも変えた（ひな形 ⇔ `prompts.TEMPLATES`・値を作るモジュール・research.md の表、`validate.check_tree` の項目 ⇔ STATE-06 の表・`_surface.md`・`test_validate.py`、`contracts.py` のタグ ⇔ 返答の形を書いたひな形、`status.LINE_KINDS` か `次:` の行 ⇔ SKILL.md の「繰り返すこと」の表、profile.json の形 ⇔ `SCHEMA_VERSION`・profile-guide.md・ADR、`runner` のフラグ ⇔ OPS-05 の表・research.md、import ⇔ `structure_check.py` の表・architecture.md の許可表）
- [ ] STR-02：2つ以上のモジュールで使う関数は共有のモジュールに置いた
- [ ] CODE-01：関数は引数のリスト・辞書を書き換えず、新しい値を返している（例外は `_read_*` と `_parse_*` が引数の `problems` に足すことだけ）
- [ ] CODE-05：コメントは「なぜ」だけで、コメントアウトしたコードが無い
- [ ] STATE-01：進み具合を書いた状態ファイルを足していない
- [ ] STATE-03：証拠をプロンプトの文に埋め込まず、`context/` のファイルとして置いた。軌跡を `obs_trunc` 以外で切り詰めていない
- [ ] STATE-06：候補の木を実行する前に `validate.check_tree` を通している（候補を作る流れを変えたとき）
- [ ] OPS-03：人に見せる文言は日本語で、表・一覧・金額は `render` の関数で作った
- [ ] TEST-02：テストの部品は `tests/support.py` に、偽の振る舞いは `fake_claude.py` に置き、モックを使っていない
- [ ] 足した・移した公開関数ごとにテストがあり、テストの名前が2節の式に合っている
- [ ] PROC-03：ruff と mypy の版を変えていない（変えるなら ADR がある）
- [ ] PROC-06：profile.json の形を変えたら `profile.SCHEMA_VERSION` を上げた
- [ ] PROC-07：人が決める場面を足したら SKILL.md の「人が決める場面」の表に書いた
- [ ] TOOL-04：保護ファイルは、`structure_check.py` の登録の表に要素を足した以外に変えていない
- [ ] `make check` が通った

## 7. 報告する

次の順で書く。

1. 何を作ったか（使ったパターン）
2. 変えたファイルの一覧（作る順序の順）
3. 2 で決めた値と、その根拠（依頼文、ユーザーの回答、既定値のどれか）
4. `make check` の結果（出力の末尾）
5. 決めきれずに残したこと、ルールと既存コードの食い違い、harness2 と振る舞いが違ってしまう点
