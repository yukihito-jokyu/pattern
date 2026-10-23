---
name: impl
description: skill-tune-kit で実装・変更・追加・修正を行う手順。「検査の種類を足して」「サブコマンドを追加して」「プロンプトの文言を直して」「plan.json に項目を足して」「status の表示を変えて」「採否の規則を変えて」「〜の不具合を直して」「skill-tune の手順を直して」などの依頼で使う。この基盤のコードや配布物を書く・変える依頼では、依頼の大小にかかわらず必ず使う。依頼をパターンに振り分け、決められた順序で作り、`make check` と完了前チェックリストで確かめてから報告する。
---

# skill-tune-kit の実装手順

このスキルは次の資料と一緒に使う。パスは基盤のルートからの相対パスである。

- `docs/design/rules.md`：ルールの全文。`<接頭辞>-<番号>` のルールIDで参照する
- `.claude/skills/impl/references/patterns.md`：パターンごとの手順と、作るファイルの一覧
- `docs/design/architecture.md`：依存の許可表と変更シナリオ表
- 見本（参照実装）：`kit/.tune/tune_kit/`（段は `decide.py` が最小の見本）、`tests/`（`support.py` と `test_decide.py`）

既存のコードと rules.md が食い違ったら rules.md に従い、食い違いを報告に書く。

## 1. 依頼をパターンに振り分ける

| 依頼に含まれること | patterns.md の節 |
|---|---|
| 検査の種類（`kind`）を足す・変える | 1 |
| サブコマンド（段）を足す | 2 |
| サブエージェントへのプロンプトの文言・置き換えの値を変える | 3 |
| plan.json・cases.json の項目を足す・変える | 4 |
| 既存のサブコマンドの振る舞いを直す、不具合を直す | 5 |
| 指標の計算か、候補の採否の規則を変える | 6 |
| status の行（次の手の示し方）を変える | 7 |
| 配布するスキル（skill-tune）かサブエージェントの定義を直す | 8 |

- 複数の行に当たる場合は、表の上から順に全部行う
- どの行にも当たらない場合は、実装しない。必要なパターンとルールを提案として報告する。見本に無い形をその場で発明すると、作者ごとに違う形が生まれるからである

## 2. 依頼から決まらない値

推測で決めない。聞ける状況ならユーザーに聞く。聞けない状況なら既定値で決め、報告の3に書く。

| 決めること | 何に響くか | 既定値 |
|---|---|---|
| 検査の種類の名前 | plan.json の `kind`、check-kinds.md | 小文字の英語の snake_case（比べ方を表す語。例 `starts_with`） |
| サブコマンドの名前 | cli、status、SKILL.md、段の公開関数名 | 小文字の英語の kebab-case。段の確認なら `<段>-check`、1つの段の JSON を一覧で見せるだけなら `<段>-list`（置くモジュールは patterns.md の2節の表） |
| 新しいファイルの名前 | layout の定数 | 小文字の kebab-case。サブエージェントが書くファイルの名前に `report` を含めない |
| エラーの文言 | 利用者とスキルの次の手 | 「<何が起きたか>。<次にすること>」の日本語。段の順番の誤りは「status を実行してください」で終える |
| 人に見せる新しい文言（status の行、Markdown の見出しや表の列） | 利用者とスキルの読み分け | 既存の文言にある語と並びをそのまま使い、新しい言い回しを作らない（例：率は `decide.py` の表と同じ「検証用の合格率 50.0%」「検査の通過率 75.0%」） |
| plan.json の新しい項目の既定値 | ひな形（`plan.build_skeleton`）と既存の計画 | 項目を省いたときに今までと同じ振る舞いになる値 |
| 予算の項目の上下限 | `plan.BUDGET_LIMITS` | 1〜10 |

## 3. 書く前に読む

1. patterns.md の該当する節を最後まで読む
2. rules.md のうち、次の接頭辞の節をすべて読む

   | パターン | 読む接頭辞 |
   |---|---|
   | 1、4、6 | STR、NAM、CODE、ERR、TEST、PROC |
   | 2、5 | STR、DEP、NAM、CODE、ERR、STATE、OPS、TEST、PROC |
   | 3 | STATE、PROC |
   | 7 | OPS、STATE、PROC |
   | 8 | STR、STATE、PROC |

3. 見本の該当ファイルを開き、構成・命名・import の並び・コメントの書き方を確かめる

## 4. 作る順序

patterns.md の該当節の「作る・変えるファイル」の順に作る。検査の種類を足したら `make docs` で check-kinds.md を作り直す（STR-04）。サブコマンドを足すときは PROC-01 の順（`layout.py` → `contracts.py` → 段のモジュール → `status.py` → `cli.py` → テスト → `structure_check.py` の表と architecture.md の許可表 → SKILL.md の表）に作る。

新しい `_` で始まる関数は、それを最初に呼ぶ関数の直前に置く。テストの関数は、テストのファイルの既存のクラスの末尾に足し、既存のテストの間に挟まない。

各ファイルを保存するたびに、hooks が `make fix-file` で format と lint を走らせる（TOOL-02）。指摘が出たら、次のファイルに進む前に直す。

## 5. 検証する

1. `make check` を実行する（PROC-05）
2. 落ちたら、エラーに出たルールIDか lint のルール名を rules.md で引き、コードを直す。lint のルール名とルールIDの対応は `docs/design/enforcement-matrix.md` にある
3. 次の方法で検査を黙らせない
   - 検査の設定や保護ファイルを変える（TOOL-04）
   - 抑止コメントを書く（TOOL-03）
   - テストを skip する、または消す

   どうしても直せない場合は、その状態のまま報告する。ルールそのものを変えるべきなら、実装せずに PROC-04 の順で提案する

## 6. 完了前チェックリスト

該当するファイルを開き、1つずつ確かめる。

- [ ] PROC-02：波及の対応表の組を両側とも変えた（`checks.KINDS` ⇔ `plan.py`・check-kinds.md・`test_checks.py`、ひな形 ⇔ `prompts.TEMPLATES`・値を作る段、`contracts.AGENTS` ⇔ `kit/claude/agents/`・SKILL.md の表、status の行 ⇔ SKILL.md の「繰り返すこと」の表、plan.json の形 ⇔ `SCHEMA_VERSION`・plan-schema.md・ADR、import ⇔ `structure_check.py` の表・architecture.md の許可表）
- [ ] STR-02：2つ以上の段で使う関数は共有のモジュールに置いた
- [ ] CODE-01：関数は引数のリスト・辞書を書き換えず、新しい値を返している
- [ ] CODE-05：コメントは「なぜ」だけで、コメントアウトしたコードが無い
- [ ] STATE-01：進み具合を書いた状態ファイルを足していない
- [ ] STATE-02：プロンプトの文を Python に書かず、ひな形に書いた
- [ ] STATE-03：学習役の証拠とプロンプトに学習用以外のケースが入らない
- [ ] OPS-03：人に見せる文言は日本語で、表・率・一覧は `render` の関数で作った
- [ ] TEST-02：テストの部品は `tests/support.py` に置き、モックを使っていない
- [ ] PROC-03：ruff と mypy の版を変えていない（変えるなら ADR がある）
- [ ] PROC-06：plan.json・cases.json の形を変えたら `plan.SCHEMA_VERSION` を上げた
- [ ] PROC-07：人が決める場面を足したら SKILL.md の「人が決める場面」の表に書いた
- [ ] `make check` が通った

## 7. 報告する

次の順で書く。

1. 何を作ったか（使ったパターン）
2. 変えたファイルの一覧（作る順序の順）
3. 2 で決めた値と、その根拠（依頼文、ユーザーの回答、既定値のどれか）
4. `make check` の結果（出力の末尾）
5. 決めきれずに残したこと、ルールと既存コードの食い違い
