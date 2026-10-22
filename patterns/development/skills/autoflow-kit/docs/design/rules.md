# autoflow-kit のルール

このファイルは autoflow-kit のルールの正本である。AGENTS.md・スキル・レビューの指摘・検査のエラーは、ここのルールIDを参照する。ルールの変更手順は AGENTS.md の「ルールを変えたいとき」に従う。

## 読み方

- ルールIDは `<接頭辞>-<連番>` である。廃止したルールも ID を再利用せず、`- 状態: 廃止` と書いて残す
- 接頭辞は次のとおりである。`GATE` はこの基盤で足した接頭辞で、オートフローの正しさを守る関所（人の関所と機械の関所）のルールに使う

  | 接頭辞 | 軸のグループ |
  |---|---|
  | `STR` | A 配置と構造、X3 |
  | `DEP` | B 境界と依存 |
  | `NAM` | C 命名 |
  | `CODE` | D 書き方 |
  | `ERR` | E1〜E2 エラー・入力検証 |
  | `STATE` | E3 状態とデータの流れ、X4 |
  | `ASYNC` | E4 非同期・並行 |
  | `OPS` | E5〜E8 ログ・設定・セキュリティ・表示、X1、X7 |
  | `GATE` | X5 人の関所、X6 機械の関所 |
  | `TEST` | F テスト |
  | `PROC` | G 作業手順、X2 |
  | `TOOL` | H 道具・自動化 |

- **強制**の先頭のキーワードは、そのルールを守らせる仕組みを表す

  | キーワード | 仕組み |
  |---|---|
  | `type` | 型・可視性で書けなくする |
  | `format` | formatter |
  | `lint` | linter |
  | `structure` | 構造検査 |
  | `test` | テスト |
  | `generator` | 生成器 |
  | `review` | レビュー用スキル |
  | `doc` | 文書のみ |

  ルールと仕組みの対応表は `enforcement-matrix.md`（生成物）にある
- `type`・`format`・`lint`・`structure`・`test` のルールには、違反例（probe）が `.foundation/probes.json` にあり、検査で落ちることを確かめてある

## ルールの書式

`rules_check.py` がこの書式を読む。項目名と順番を変えない。

```markdown
### <接頭辞>-<2桁の番号> <決定を1行で要約した題名>

- 軸: <答えている軸の記号。複数ならカンマ区切り>
- 決定: <読んだ2人が同じ判定をできる1文。条件で答えが変わるなら、次の行から2字下げで決定表を書く>
- 理由: <何が揺れ、何が壊れるのを防ぐか>
- 出典: <research.md の該当節、または公式ドキュメントの URL。無ければ行ごと省く>
- 強制: <キーワード。複数ならカンマ区切り> — <仕組みの説明：どの設定・スクリプトのどこで縛るか>
- probe: <この強制を証明する probe の ID。機械の段ごとに1件以上>
- 良い例:
  <5行以内のコード。長くなるなら「見本: <参照実装のパス>」と書く>
- 悪い例:
  <実際に書かれがちな違反。5行以内>
```

- 機械の段（`type`・`format`・`lint`・`structure`・`test`）を含まないルールには、`- 機械化しない理由:` を**強制**の次の行に足し、`probe` の値は `なし` にする
- 軸の記号は範囲で書いてもよい（`D1〜D3` は D1、D2、D3 と読まれる）
- 番号は節ごとに 01 から、カタログの軸の順（同じ軸の中では決定の順）に振る
- ルールが0件の節は、見出しごと消し、その節の軸を「対象外とした軸」表に書く
- 決定の中のコード片（`` ` `` で囲んだ部分）は、あいまいな語の検査から除かれる

## 用語

| 用語 | 意味 |
|---|---|
| オートフロー | 依頼から、計画・実装・検証・AI レビュー・リスクの判定・最終承認・コミットまでを、補助 CLI の指示で AI が自走し、人は関所でだけ判断する流れ |
| 補助 CLI | `kit/.autoflow/autoflow.py` と `autoflow_kit` パッケージ。配布先では `.autoflow/autoflow.py` |
| 段 | 補助 CLI の1つ以上のサブコマンドが受け持つ、オートフローの1区切り（`trail.STEPS` の値） |
| 段のモジュール | 1つ以上のサブコマンドを実装するモジュール（`setup`、`intake`、`planning`、`deciding`、`building`、`verifying`、`risking`、`reviewing`、`handoff`、`status`、`learning`） |
| 共有のモジュール | 2つ以上の段が使うモジュール（`errors`、`layout`、`shape`、`render`、`fsops`、`proc`、`profile`、`contracts`、`policy`、`changes`、`trail`、`prompts`、`views`、`workspace`、`context`、`escalation`） |
| 実行 | 1件の依頼についてのオートフロー。`.autoflow/runs/<run-id>/` に記録が残る |
| 実行の記録 | 実行ごとの追記だけのファイル `trail.jsonl`。1行が1つの出来事（`trail.Event`）で、次の段はこれだけから決まる |
| プロファイル | 対象のリポジトリの検査コマンド、テストのパス、リスクのパスの分類、上限を書いた `.autoflow/profile.json`。H0 で人が承認する |
| tree | `git add -A` の後に `git write-tree` で得る id。作業ツリーの中身だけで決まり、差分の版として、証拠・レビュー・承認を結び付ける |
| 人の関所 | 人が決める場面。H0（準備の承認）、H1（方向の確認）、H2（行き詰まり）、H3（最終承認）の4つ |
| 機械の関所 | 補助 CLI が決める場面。段の順序、証拠、レビューの投票、リスクの段、読み取りだけの役の確認、承認の結び付け |
| リスクの段 | `low`・`medium`・`high` のどれか。変更（差分）から規則で決め、AI の判定は上げる方向にだけ効く |
| 計画役・実装役・探索役・検証役・リスク判定役 | 配布するサブエージェントの `autoflow-planner`、`autoflow-builder`、`autoflow-finder`、`autoflow-verifier`、`autoflow-risk` |
| 読み取りだけの役 | 計画役・探索役・検証役・リスク判定役。作業ツリーを変えてはならない |

## 追加した軸

カタログに無い、この分野に固有の軸を定義する。X1 と X2 は domain-profiles の cli-library が定める軸である。

| 軸 | 内容 | 置く節 |
|---|---|---|
| X1 | 終了コードと出力の形式（標準出力と標準エラーの使い分け、警告と `status` の行の書き方） | OPS |
| X2 | 公開 API の互換性（profile.json の形を変えるときの手順） | PROC |
| X3 | この基盤のスキル・サブエージェントの定義の書式（frontmatter、行数、参照ファイル） | STR |
| X4 | サブエージェントとの受け渡し（プロンプトのひな形と、サブエージェントが書くファイル） | STATE |
| X5 | 人の関所（人が決める場面、その条件の置き場、聞き方、答えが無いときの扱い） | GATE |
| X6 | 機械の関所（段の順序、証拠、承認の結び付け、リスクの段、読み取りだけの役） | GATE |
| X7 | git への書き込み（ブランチの作成、index、コミット）を行う場所 | OPS |

## STR 配置と構造

### STR-01 ディレクトリは表の6か所に分けて置く

- 軸: A1, A5
- 決定: ファイルは次の表の置き場に置き、`kit/.autoflow/autoflow_kit/` にはサブパッケージを作らない。
  | 置くもの | 置き場 |
  |---|---|
  | 補助 CLI のモジュール | `kit/.autoflow/autoflow_kit/<モジュール>.py`（平らに並べる） |
  | サブエージェントへのプロンプトのひな形 | `kit/.autoflow/templates/prompts/<名前>.md` |
  | 配布するスキル | `kit/claude/skills/autoflow<-名前>/` |
  | 配布するサブエージェント | `kit/claude/agents/autoflow-<役>.md` |
  | 開発用のスクリプト（構造検査、生成器） | `scripts/` |
  | テストと見本のリポジトリ | `tests/test_<モジュール>.py`、`tests/support.py`、`tests/fixtures/sample-repo/` |
- 理由: 置き場が分かれると、配布物（`kit/`）と開発の道具が混ざり、`install.py` が写す範囲が作者ごとに変わる
- 強制: structure — `scripts/structure_check.py` の `KIT_LAYOUT` と `check_layout` が、`kit/` の下の名前とサブパッケージの有無を確かめる
- probe: STR-01-a
- 良い例:
  `kit/.autoflow/autoflow_kit/changes.py`
- 悪い例:
  `kit/.autoflow/autoflow_kit/stages/verifying.py`

### STR-02 モジュールを足すときは許可表に行を足し、テストを作る

- 軸: A2, A3
- 決定: `autoflow_kit` にモジュールを1つ足すときは、`scripts/structure_check.py` の `SHARED` か `STAGES` と `docs/design/architecture.md` の許可表に行を足し、`tests/test_<モジュール>.py` を作る。1つのモジュールが受け持つのは、用語の表の段のモジュールの1つの段か、共有のモジュールの1つの関心だけにする。
- 理由: 表に無いモジュールは依存の向きを検査できず、どこに何があるかが作者ごとに変わる
- 強制: structure — `check_module_table` が、表に無いモジュールと、モジュールの無い表の行を落とす
- probe: STR-02-a
- 良い例:
  `SHARED` に `"changes": {"proc", "errors"}` を足し、`tests/test_changes.py` を作る
- 悪い例:
  表に足さずに `autoflow_kit/cache.py` を置く

### STR-03 入口は autoflow.py と cli.main の2つだけにする

- 軸: A7
- 決定: `autoflow_kit/__init__.py` には docstring だけを書き、コマンドの入口は `kit/.autoflow/autoflow.py` から呼ぶ `cli.main(argv, default_root)` だけにする。
- 理由: `__init__.py` で再 export すると、`from autoflow_kit import main` と `from autoflow_kit.cli import main` の2通りの書き方が生まれる
- 強制: structure — `check_init` が、`__init__.py` に docstring 以外の文があると落とす
- probe: STR-03-a
- 良い例:
  `"""autoflow の補助 CLI。"""`
- 悪い例:
  `__all__ = ["cli"]`

### STR-04 生成物は手で編集せず make docs で作り直す

- 軸: A6
- 決定: 次の表の生成物は手で編集せず、入力を直してから生成し直す。
  | 生成物 | 入力 | 生成するもの |
  |---|---|---|
  | `kit/claude/skills/autoflow/references/gates.md` | `policy` の表（`TIERS`、`DEPTHS`、`KINDS`、`H1_RULES`、`H2_RULES`、`GATES`、`REVIEW`） | `make docs`（`scripts/gen_docs.py`） |
  | `kit/claude/skills/autoflow-setup/references/profile-schema.md` | `profile.FIELDS` と既定値（`profile.make_profile`） | `make docs`（`scripts/gen_docs.py`） |
  | `docs/design/enforcement-matrix.md` | `docs/design/rules.md`、`.foundation/probes.json` | `rules_check.py` |
- 理由: 手で直した生成物は、次の生成で消えるか、コードと食い違ったまま残る。関所の条件の文書がコードと食い違うと、人とスキルが別の条件を信じる
- 強制: structure — `make docs-check` が生成し直した結果と比べ、違えば落とす
- probe: STR-04-a
- 良い例:
  `policy.py` を直してから `make docs`
- 悪い例:
  `gates.md` の文言だけを直す

### STR-05 この基盤のスキルとサブエージェントは決まった frontmatter で書く

- 軸: X3
- 決定: 配布するスキルとサブエージェントは次の形にする。
  | 対象 | 形 |
  |---|---|
  | スキル | ディレクトリ名と `name` を `autoflow` か `autoflow-<名前>` で同じにし、`description`、`argument-hint`、`disable-model-invocation: true`、`allowed-tools: Bash(python3 .autoflow/autoflow.py *)` を書き、`context` を書かない。SKILL.md は500行以内にし、参照は `references/<ファイル>` の1階層で、`references/` の全ファイルを SKILL.md から参照する |
  | サブエージェント | ファイル名と `name` を同じにし、`contracts.AGENTS` の値とそろえる。`description` を書き、`tools` を列挙し、`Skill` と `Agent` を入れない |
- 理由: `Agent` を持つサブエージェントは、さらにサブエージェントを起動して関所の外で作業を広げる。`Skill` を持つと、オートフローのスキルを入れ子で呼びうる。自動で呼ばれるスキルは、人の知らない間に作業ブランチを作りうる
- 出典: research.md の「Claude Code のスキル」「Claude Code のサブエージェント」
- 強制: structure — `check_skills` と `check_agents` が frontmatter、行数、参照、`tools` を確かめる
- probe: STR-05-a, STR-05-b
- 良い例:
  `tools: Read, Write, Bash`
- 悪い例:
  `tools` を省く（全ツールを継承し、`Skill` と `Agent` も使える）

## DEP 境界と依存

### DEP-01 import は許可表の組だけにし、段のモジュールどうしは import しない

- 軸: B1, B3, A4
- 決定: `autoflow_kit` のモジュールは、`docs/design/architecture.md` の許可表で印のある組だけを import する。段のモジュールは他の段のモジュールを import せず、2つ以上の段が使う処理は共有のモジュールに置く（`cli` だけは全部の段を import する）。
- 理由: 段どうしが呼び合うと、1つの段の変更が別の段の振る舞いを変え、関所の判定がどこで変わったかを追えなくなる
- 強制: structure — `ALLOWED_IMPORTS` の表と `check_dependencies` が、表に無い import を落とす
- probe: DEP-01-a
- 良い例:
  `reviewing` と `handoff` が使う指摘の描画を `views` に置く
- 悪い例:
  `handoff.py` で `from autoflow_kit import reviewing`

### DEP-02 他のモジュールの _ で始まる名前を使わない

- 軸: B2
- 決定: モジュールの外から使ってよいのは、`_` で始まらない名前だけにする。他のモジュールの `_` で始まる名前を import も参照もしない。
- 理由: 内部の関数に外から依存すると、その関数を直すだけで別のモジュールが壊れる
- 強制: structure — `check_dependencies` が `<モジュール>._<名前>` と `from autoflow_kit.x import _y` を落とす
- probe: DEP-02-a
- 良い例:
  `workspace.load_plan(where, run_id)`
- 悪い例:
  `policy._matches(path, globs)`

### DEP-03 Python 3.9 の標準ライブラリだけを使う

- 軸: B4, B6, H4
- 決定: 配布物・スクリプト・テストは、`scripts/structure_check.py` の `STDLIB` の表にある標準ライブラリと、`autoflow_kit`・`tests`・`install` だけを import する。表に足すときは ADR を書かずに表と research.md を一緒に変え、標準ライブラリでないものは足さない。
- 理由: 配布物は任意のリポジトリで `python3` だけで動く必要がある。依存を足すと、配布先ごとに導入の手順が要る
- 出典: research.md の「Python」
- 強制: structure — `check_stdlib` が表に無い import を落とす
- probe: DEP-03-a
- 良い例:
  `import fnmatch`
- 悪い例:
  `import yaml`

### DEP-04 副作用に触れるモジュールを表の3つに限る

- 軸: B5
- 決定: 副作用に触れてよいモジュールは次の表のとおりにする。
  | 副作用 | 触れてよいモジュール |
  |---|---|
  | ファイルを書く・消す・作る（`open`、`shutil`、`FS_WRITERS` の表の全メソッド） | `fsops` |
  | 外部コマンド（`subprocess`、`signal`）、`tempfile`、環境変数 | `proc` |
  | 時刻（`datetime`、`time`）、画面への出力（`print`） | `cli` |
- 理由: 副作用が散ると、テストで一時ディレクトリ以外を書き換える箇所や、時刻で結果が変わる箇所を見つけられない
- 強制: structure, lint — `check_side_effects` がファイルの書き込み・`subprocess`・`tempfile`・時刻を、ruff の `T201` が `print` を落とす（`cli.py`、`scripts/`、`install.py` だけ `T201` を外す）
- probe: DEP-04-a, DEP-04-b
- 良い例:
  `fsops.write_text(path, text)`
- 悪い例:
  `path.write_text(text)` を `verifying.py` に書く

## NAM 命名

### NAM-01 名前のケースは PEP 8 に従う

- 軸: C1, C2, C6
- 決定: モジュール・関数・変数は snake_case、クラスは PascalCase、定数は UPPER_SNAKE_CASE にする。Markdown のファイル名（ひな形、エージェント、参照ファイル）は kebab-case にする。略語も単語として扱い、`Id` ではなく `id`、`run_id` のように書く。
- 理由: ケースが揺れると、同じものを別の名前で探すことになる
- 強制: lint — ruff の `N` 群（`N802`、`N806` ほか pep8-naming の全ルール）
- probe: NAM-01-a
- 良い例:
  `def run_dir(self, run_id: str) -> Path:`
- 悪い例:
  `def runDir(self, runId):`

### NAM-02 関数名の先頭の動詞は語彙表から選ぶ

- 軸: C3, C4, C5
- 決定: 次の表の意味の関数は表の動詞で始め、表の動詞を表の意味以外に使わない。表の動詞と同じ意味の別の動詞（`get_`・`fetch_`・`format_`・`create_`・`validate_`・`save_`）は使わない。表に無い意味の関数は、意味を表す名詞（`snapshot`・`digest`・`threshold`）か、表に無い動詞（`compose`・`merge_tier`・`tally`）で始めてよい。真偽値を返す関数は `is_`・`has_` で始める（`property` と、JSON の値を型ごとに読む関数（`shape` の関数と、それを包む関数）を除く。`proc` の git の関数は `git_is_ignored` のように `git_` の後に置く）。秒は `_sec`、件数は `_count` か複数形で表す。
  | 動詞 | 意味 |
  |---|---|
  | `read_` | ファイルを検証せずに読む（`fsops` だけ） |
  | `load_` | ファイルを読んで検証し、モデルを返す（`workspace` だけ） |
  | `parse` か `parse_` | 読んだ値を検証してモデルにする（`profile`、`contracts`、`trail`） |
  | `write_`・`append_` | ファイルに書く・足す（`fsops` だけ） |
  | `render_` | モデルから人が読む Markdown を作る |
  | `make_` | 値を組み立てて返す（`make_parser`、`make_run_id`） |
  | `check_` | 検証して、問題の一覧を返す |
  | サブコマンドの名前の `-` を `_` にしたもの（`plan_new`、`review_tally` の形） | その段の入口 |
- 理由: 同じ意味の動詞が混ざると（load と read、render と format）、読み手が副作用や検証の有無を取り違える
- 強制: structure, review — `scripts/structure_check.py` の `check_names` が、`SYNONYM_VERBS` の別名で始まる関数を落とす。表の動詞の使い分けと真偽値の名前はレビューで見る
- 機械化しない理由: 表の動詞を表の意味で使っているか（`load_` なのに検証しない、など）は、関数の中身の判断が要る
- probe: NAM-02-a
- 良い例:
  `def load_flow(where: Layout, run_id: str) -> policy.Flow:`
- 悪い例:
  `def get_flow(...)` と `def fetch_flow(...)` が並ぶ

### NAM-03 JSON のキーは snake_case にし、dataclass のフィールド名と同じにする

- 軸: C7
- 決定: プロファイル、実行の記録、補助 CLI とサブエージェントが受け渡す JSON のキーは snake_case にし、対応する dataclass のフィールド名と同じ綴りにする。書くときは `shape.to_data`（タプルをリストにした JSON の値）を使う。
- 理由: キーとフィールド名がずれると、変換の箇所が増え、プロンプトの JSON の例とずれる
- 強制: structure — `check_json_keys` が、全モジュールの `shape` の呼び出しと `unknown_keys` のキーの綴りを確かめる
- probe: NAM-03-a
- 良い例:
  `shape.text(root, "bug_class", "", problems)`
- 悪い例:
  `shape.text(root, "bugClass", "", problems)`

## CODE 書き方

### CODE-01 データは継承しない frozen の dataclass にし、引数を変えない

- 軸: D1, D5
- 決定: `errors.py` 以外のクラスは、基底クラスを持たない `@dataclass(frozen=True)` にし、振る舞いは関数に書く（メソッドは `property` とパスを返す `Layout` のメソッドだけ）。並びは `tuple` で持ち、関数は引数の `dict` と `list` を変えない。ただし、検証の関数が受け取る問題の一覧 `problems`（呼び出し側が作った空の `list` に、見つけた問題の文を足していく。`shape` と `profile`・`contracts`・`trail` の `parse` の形）だけは足してよい。
- 理由: 可変のオブジェクトを渡し合うと、どの段で値が変わったかを追えない
- 強制: structure, review — `check_classes` がクラスの形を確かめ、引数を変えていないかはレビューで見る
- probe: CODE-01-a
- 良い例:
  `@dataclass(frozen=True)` の `class Finding:`
- 悪い例:
  `class Cache:` に `self.items = {}` を持たせる

### CODE-02 import は autoflow_kit からの絶対 import にする

- 軸: D2
- 決定: パッケージの中の import は `from autoflow_kit import <モジュール>` か `from autoflow_kit.<モジュール> import <名前>` にし、相対 import は使わない。並び順は ruff の isort に任せる。
- 理由: 相対と絶対が混ざると、同じモジュールの参照が2通りの字面になり、構造検査の対象から漏れる
- 強制: lint — ruff の `TID252`（`ban-relative-imports = "all"`）と `I001`
- probe: CODE-02-a
- 良い例:
  `from autoflow_kit import fsops`
- 悪い例:
  `from .errors import KitError`

### CODE-03 型注釈は全部に書き、mypy の strict を通す

- 軸: D3
- 決定: 全モジュールの先頭に `from __future__ import annotations` を書き、全関数の引数と戻り値に型注釈を書く。省略可能な値は `X | None`、`Any` は `shape.py` だけで使う。
- 理由: 型が無いと、サブエージェントの JSON から作ったモデルの取り違えが実行時まで見つからない
- 出典: research.md の「mypy」
- 強制: type, lint — mypy の `strict`、ruff の `UP045`
- probe: CODE-03-a, CODE-03-b
- 良い例:
  `def merge_tier(rule_tier: str, ai_tier: str) -> str:`
- 悪い例:
  `def merge_tier(rule_tier, ai_tier):`

### CODE-04 関数の大きさは ruff の上限に収める

- 軸: D4, D6
- 決定: 関数の複雑度は10以下、引数は6以下、分岐は12以下、return は6以下、文は50以下にする。超えたら関数を分ける。
- 理由: 大きな関数は、変更のたびに読む範囲が広がり、作者ごとに分け方が揺れる
- 強制: lint — ruff の `C901`（`max-complexity = 10`）、`PLR0913`、`PLR0912`、`PLR0911`、`PLR0915`
- probe: CODE-04-a
- 良い例:
  見本: `kit/.autoflow/autoflow_kit/trail.py` の `next_step` と、出来事ごとの `TRANSITIONS` の表が呼ぶ `_on_planned`・`_on_verified`
- 悪い例:
  1つの関数で計画・実装・検証・レビューの全段の分岐を書く

### CODE-05 モジュールの docstring は必須にし、コメントアウトしたコードを残さない

- 軸: D7
- 決定: 全モジュールと全パッケージの先頭に、そのモジュールが受け持つことを1〜2文の docstring で書く。コメントは理由（なぜ）だけを書き、コメントアウトしたコードは残さない。
- 理由: 受け持ちの1文があれば、新しい処理を置くモジュールを選べる。古いコードのコメントは読み手を迷わせる
- 強制: lint — ruff の `D100`、`D104`、`ERA001`
- probe: CODE-05-a, CODE-05-b
- 良い例:
  `"""作業ツリーの tree id と、tree どうしの差分を求める。"""`
- 悪い例:
  `# return merge_tier(rule, ai)`

### CODE-06 ファイル名とエージェント名の文字列は定数で持つ

- 軸: D8
- 決定: `.json`・`.jsonl`・`.md`・`.patch`・`.log`・`.txt` で終わるファイル名の文字列は `layout.py`（ひな形のファイル名だけ `prompts.py`）に、サブエージェントの名前は `contracts.AGENTS` に定数で置き、他のモジュールはその定数を使う。ファイル名の定数をディレクトリに `/` でつなぐのは `layout.py` の中だけにし、他のモジュールは `Layout` のメソッドで置き場を受け取る。
- 理由: 同じファイル名を2か所に書くと、片方だけ変えたときに読み書きの場所がずれる
- 強制: structure — `check_literals` が、持ち主のモジュール以外にあるファイル名とエージェント名の文字列を落とす。`check_paths` が、`layout.py` の外でファイル名の定数を `/` でつなぐ式を落とす
- probe: CODE-06-a, CODE-06-b
- 良い例:
  `where.evidence_path(run_id, seq)`
- 悪い例:
  `where.run_dir(run_id) / "handoff.md"`、`where.run_dir(run_id) / layout.HANDOFF_MD`

## ERR エラーと入力検証

### ERR-01 投げる例外は errors.py の4つだけにし、捕まえるのは cli.main だけにする

- 軸: E1
- 決定: 例外は `KitError`、`InvalidFileError`、`StageError`、`CommandError` だけを投げる。捕まえるのは `cli.main`（終了コード1にする）と、失敗を値に変える `proc`（`git_is_ignored`・`git_user` が `CommandError` を捕まえる）と `learning`（読めない記録を `KitError` で捕まえて飛ばす）だけにし、`Exception` を捕まえない。
- 理由: 例外の種類と捕まえる場所が散ると、人に見せる文言と終了コードが段ごとに変わる
- 強制: structure, lint — `check_errors` が errors.py 以外の例外の `raise` を、ruff の `BLE001` が `except Exception` を落とす
- probe: ERR-01-a, ERR-01-b
- 良い例:
  `raise StageError("今は verify の番です")`
- 悪い例:
  `raise ValueError("bad")`

### ERR-02 外から来る JSON は workspace の load_* で検証してから使う

- 軸: E2
- 決定: プロファイル、サブエージェントが書く JSON（plan.json、report.json、指摘、投票、judgment.json）、実行の記録、補助 CLI が書いた JSON は、`workspace` の `load_*` で `profile.parse`・`contracts.parse_*`・`trail.parse_*`・`policy.parse_flow` を通してから使う。`fsops.read_json` と `fsops.read_lines` を呼んでよいのは `fsops` と `workspace` だけにする。問題は全部集めてから、JSON のパス付きで `InvalidFileError` にする。
- 理由: 検証を飛ばすと、サブエージェントの書き損じが集計の途中で別の形の失敗になり、どこを直せばよいかが分からない
- 強制: structure — `check_errors` が、`fsops` と `workspace` の外の `fsops.read_json`・`fsops.read_lines` を落とす
- probe: ERR-02-a
- 良い例:
  `workspace.load_votes(where, run_id, round_no, voter, ids)`
- 悪い例:
  `fsops.read_json(where.votes_path(run_id, round_no, 1))` を `reviewing.py` に書く

## STATE 状態とデータの流れ

### STATE-01 進み具合は trail.jsonl だけに書き、次の段はそこから求める

- 軸: E3
- 決定: 状態の置き場は次の表のとおりにし、段の進み具合（今どの段か、何ラウンド目か、何回失敗したか）を `trail.jsonl` 以外のファイルに書かない。次の段は `trail.next_step` が出来事の並びと今の tree から求める。
  | 状態 | 置き場 | 消してよいか |
  |---|---|---|
  | プロファイルとその承認 | `.autoflow/profile.json`、`.autoflow/profile-approval.json` | 消さない（コミットする） |
  | 実行の進み具合 | `.autoflow/runs/<id>/trail.jsonl`（追記だけ） | 消さない（`metrics` と `learn` が読む） |
  | 段の成果（計画、実装の報告、証拠、レビュー、報告書、承認） | `.autoflow/runs/<id>/` の下の `layout` の置き場 | 消さない |
- 理由: 進み具合を別のファイルにも書くと、ファイルの実態と食い違ったときにどちらを信じるかが揺れ、関所の判定が作者ごとに変わる
- 強制: review — レビュー用スキルの確認項目
- 機械化しない理由: 新しいファイルが進み具合を表すかどうかは、ファイルの意味の判断が要る
- probe: なし
- 良い例:
  `fsops.append_line(where.trail_path(run_id), trail.encode(event))`
- 悪い例:
  `state.json` に `{"step": "review", "round": 2}` を書く

### STATE-02 サブエージェントとの受け渡しはひな形とファイルの契約だけで行う

- 軸: X4
- 決定: サブエージェントへのプロンプトの文章は `kit/.autoflow/templates/prompts/` のひな形だけに書き、置き換えの名前は `${名前}` の形で `prompts.TEMPLATES` の表と一致させる。成果はプロンプトが示すファイル（`contracts` の型）で受け取り、返答の本文を読んで判断しない。返答は `完了: <パス>` の1行にさせる。置き換えの値には文を書かない。値の作り方は次の表のとおりにし、無いときの扱いと見出しはひな形に書く。
  | 値 | 入れるもの |
  |---|---|
  | 1つの値（パス、コマンド、名前） | 生の値。無いときは `render.MISSING`（`—`） |
  | 長さがデータで決まる一覧 | `render.bullets` で作った箇条書き（空なら `- なし`） |
  | 表 | `render.table` で作った表 |
- 理由: プロンプトの文をコードに散らすと、文言の変更でテストが追えない。返答の本文を読むと、メインのセッションの解釈で結果が揺れる
- 強制: test, review — `tests/test_prompts.py` が、全ひな形の置き換えの名前と表の一致を確かめ、置き換えの値に文を書いていないかはレビューで見る
- probe: STATE-02-a
- 良い例:
  `"prior_findings": render.bullets(lines)` と、ひな形の「一覧が `- なし` なら、既出の指摘は無い」
- 悪い例:
  `f"あなたは探索役です。{lens} の観点で…"` を `reviewing.py` に書く

## ASYNC 非同期と並行

### ASYNC-01 補助 CLI は並行処理を書かない

- 軸: E4
- 決定: 補助 CLI は `threading`・`asyncio`・`multiprocessing`・`concurrent` を使わず、検査コマンドは `proc.shell` で1つずつ順に実行する。サブエージェントの並行は、配布するスキルが `status` の `job` の行を1つのメッセージの Agent ツールの呼び出しにまとめて行う。
- 理由: 検査コマンドを並行で回すと、同じ作業ツリーへの書き込み（ビルドの成果物、キャッシュ）がぶつかり、結果が実行ごとに揺れる
- 強制: structure — `check_side_effects` が、並行のモジュールの import を落とす
- probe: ASYNC-01-a
- 良い例:
  `for command in commands: results.append(proc.shell(command.run, root, command.timeout_sec))`
- 悪い例:
  `ThreadPoolExecutor().map(run, commands)`

## OPS ログ・設定・セキュリティ・表示

### OPS-01 結果は標準出力、エラーは標準エラーに出し、status の行は決まった書き出しにする

- 軸: E5, X1
- 決定: 補助 CLI は、成功の結果を標準出力に、エラーを `エラー: ` を付けて標準エラーに出し、終了コードは成功が0、`KitError` が1（引数の誤りは argparse の2）にする。警告は出力の中の `WARN ` で始まる行にし、ログの仕組みは持たない。`status` の行は `status.LINE_KINDS` の書き出し（`対象:`・`段階:`・`次:`・`job `・`その後:`・`人:`・`選択:`・`終了:`・`WARN `）のどれかで始め、新しい種類の行を足さない。人が決める値をコマンドに渡すときは、`status` の中で `'<人の回答の原文>'` の形の文字列を置き、配布するスキルが人の答えで置き換える。`sys.stdout`・`sys.stderr`・`sys.exit` に触れるのは `cli.py` だけにする。
- 理由: スキルは出力の `次:`・`job`・`人:` の行を読んで動く。出力先や形が揺れると、スキルの手順が働かない
- 強制: structure, test — `check_side_effects` が、`cli.py` 以外の `sys.stdout`・`sys.stderr`・`sys.exit` を落とし、`tests/test_cli.py` が全体の流れの各段で `status` の行の書き出しを `status.LINE_KINDS` と突き合わせる
- probe: OPS-01-a, OPS-01-b
- 良い例:
  `print(f"エラー: {exc.message}", file=sys.stderr)` を `cli.py` に書く
- 悪い例:
  `verifying.py` で `sys.stderr.write(...)`

### OPS-02 実行の設定は開始時のプロファイルの写しだけから読み、環境変数を読まない

- 軸: E6
- 決定: 実行の中の段（`intake` より後の段）は、検査コマンド・パスの分類・上限を、`start` が実行の置き場に写したプロファイル（`context.begin` が返す `profile`）だけから読む。`.autoflow/profile.json` を読むのは `setup` と `intake` だけにする。環境変数に触れるのは、検査コマンドに `CI=1` を渡す `proc.shell` だけにする。
- 理由: 実行の途中でプロファイルや環境変数が変わると、人が承認した条件と関所の条件が食い違う。実装役がプロファイルを書き換えて関所を緩めることも防ぐ
- 出典: research.md の「Claude Code の Code Review の文書」（REVIEW.md を PR 自身の変更から読まない）
- 強制: structure — `check_side_effects` が `proc.py` 以外の `os.environ`・`os.getenv`・`os.putenv` を、`check_calls` が `setup`・`intake`・`workspace` の外の `workspace.approved_profile` を落とす
- probe: OPS-02-a, OPS-02-b
- 良い例:
  `ctx = context.begin(where, run_id, trail.VERIFY)` の後に `ctx.profile.verify`
- 悪い例:
  `os.getenv("AUTOFLOW_ROUNDS")`、`workspace.approved_profile(where)` を `reviewing.py` で呼ぶ

### OPS-03 人に見せる文言は日本語で書き、表と数は render の関数で書く

- 軸: E7
- 決定: 人に見せる文言（出力、Markdown、プロンプト）は日本語で書く。表は `render.table`、数値は `render.number`、長さがデータで決まる一覧は `render.bullets` で書く。決まった項目を並べる行（`- 段: …`）は直接書いてよい。時刻は `cli` が求める ISO 8601 の文字列（`now`）だけを使う。
- 理由: 表や数の書き方が段ごとに違うと、証拠とレビューと報告書の表を見比べられない
- 強制: review — レビュー用スキルの確認項目
- 機械化しない理由: 文言が人に見せるものか、内部の値かは、字面では見分けられない
- probe: なし
- 良い例:
  `render.table(["検査", "コマンド", "終了コード", "ログ"], rows)`
- 悪い例:
  `f"| {cmd} | {code} |"` を段のモジュールに書く

### OPS-04 配布物は権限を広げず、サブエージェントの書き込み先を示す

- 軸: E8
- 決定: `bypassPermissions`・`--dangerously-skip-permissions`・`permissionMode` の文字列は `kit/` のどこにも書かない。サブエージェントのプロンプトのひな形には、書いてよい場所（実装役は作業ツリーと報告のファイル、読み取りだけの役は出力のファイル1つ）を書く。検査コマンドの出力（秘密情報を含みうる）は `.autoflow/runs/` の下だけに置く。
- 理由: 権限を広げると、人の関所を通らない操作が作業ブランチの外で起きうる。検査の出力をコミットされる場所に書くと、秘密情報が履歴に残る
- 出典: research.md の「Claude Code のサブエージェント」
- 強制: structure — `check_forbidden` が `kit/` の全ファイルの禁止の文字列を落とす
- probe: OPS-04-a
- 良い例:
  ひな形に「書いてよいのは `${output_path}` だけ」
- 悪い例:
  エージェントの定義に `permissionMode: bypassPermissions`

### OPS-05 git への書き込みは表の関数と段だけで行い、push しない

- 軸: X7
- 決定: git への書き込みは次の表の関数だけで行い、表の段（モジュール）だけから呼ぶ。`push` の文字列は `kit/` の Python に書かない。
  | 書き込み | 関数 | 呼んでよいモジュール |
  |---|---|---|
  | 作業ブランチの作成 | `proc.git_switch_new` | `intake` |
  | index への全変更の追加（tree を得るため） | `proc.git_stage_all` | `changes` |
  | コミット | `proc.git_commit` | `handoff` |
- 理由: git の書き込みが散ると、人の承認の前にコミットされる経路や、共有のリモートに出る経路が生まれる
- 出典: research.md の「git」
- 強制: structure — `check_calls` が表の外からの呼び出しを、`check_forbidden` が `push` の文字列を落とす
- probe: OPS-05-a
- 良い例:
  `proc.git_commit(root, message)` を `handoff.commit` で呼ぶ
- 悪い例:
  `proc.git_commit(root, "wip")` を `building.py` で呼ぶ

## GATE 関所

### GATE-01 関所の条件と表は policy.py だけに書く

- 軸: X5, X6
- 決定: 次の表の決まりは `policy.py` の表だけに書き、人が読む版は `make docs` で `gates.md` に生成する。関所の id（`H0`〜`H3`）の文字列は `policy.py` の外に書かず、`policy.H0`・`policy.H1`・`policy.H2`・`policy.H3` の定数を使う。`H1_RULES`・`H2_RULES` に規則を1つ足したら、`tests/test_policy.py` に `test_<規則の id>` を足す。規則の id は、`h1_`・`h2_` に、判定の関数名から先頭の `_is_`・`_has_` を除いた名前をつなげたものにする（`_has_new_dependency` → `h1_new_dependency`。ADR 0011）。
  | 決まり | 表 |
  |---|---|
  | リスクの段と、段ごとのレビューの深さ・H3 で人がすること | `TIERS`、`DEPTHS` |
  | 依頼の種類ごとの手順と確かめること | `KINDS` |
  | H1（方向の確認）と H2（行き詰まり）を起こす条件 | `H1_RULES`、`H2_RULES` |
  | 関所ごとの選択肢 | `GATES` |
  | レビューの観点、指摘の種類、投票の閾値、ラウンドの上限、差分だけの再レビュー | `LENSES`、`REVIEW` |
- 理由: 関所の条件がスキル・ひな形・段のモジュールに散ると、AI が読む条件と補助 CLI が判定する条件が食い違い、人が介入する場面が作者ごとに変わる
- 出典: research.md の記事の節
- 強制: structure, test — `check_literals` が `policy.py` の外の `H0`〜`H3` の文字列を落とし、`tests/test_policy.py` の `test_rules_have_tests` が全規則の id に `test_<id>` があることを、`test_rule_ids_match_functions` が id と判定の関数名の対応を確かめる
- probe: GATE-01-a, GATE-01-b, GATE-01-c
- 良い例:
  `PlanRule("h1_new_dependency", "依存を足す計画である", _has_new_dependency)` を `H1_RULES` に足し、`test_h1_new_dependency` を足す
- 悪い例:
  `planning.py` に `if plan.dependencies_to_add: reasons.append("H1: 依存の追加")` を書く。`PlanRule("h1_human_criteria", …, _is_human_only)` のように、id を関数名と別に決める

### GATE-02 配布するスキルは人の関所の節を持ち、答えが無いときは承認にしない

- 軸: X5
- 決定: 配布するスキルには `## 人に確かめること` の節を置き、その節に、関所ごとの聞き方（選ぶ値は AskUserQuestion、人の言葉を残す値は文章）と、次の1文をそのまま書く：「回答が無い・空・自動で閉じた質問は、承認にも選択にもしない。関所のファイルの場所を報告して止まる。」人の回答は、`decide --answer` と `setup-approve --answer` に原文のまま渡す。
- 理由: サブエージェントは人に聞けず、`claude -p` と時間切れで閉じた質問では人が答えていない。答えの無い関所を AI が埋めると、記事の「An agent's approval never counts as a person's」が崩れる
- 出典: research.md の「Claude Code のヘッドレス実行（claude -p）と AskUserQuestion」
- 強制: structure — `check_skills` が、節と AskUserQuestion の記述と決まった1文の有無を確かめる
- probe: GATE-02-a
- 良い例:
  `## 人に確かめること` の下に、H3 の選択肢を AskUserQuestion で出すと書く
- 悪い例:
  「推奨が承認なら、そのまま decide --choice approve を実行する」と書く

### GATE-03 段の入口は最初に context.begin を呼び、番でない段を動かさない

- 軸: X6
- 決定: `structure_check.py` の `ENTRIES` の表の入口の関数（`intake.start` と `setup` と `status` と `learning` を除く全サブコマンドの入口）は、最初の文で `context.begin(where, run_id, <段>)` を呼ぶ。`context.begin` は、`trail.next_step` が返す段と引数の段が違えば `StageError` を投げる。
- 理由: 入口で順序を確かめないと、レビューを飛ばして報告する、検査の後に変えたまま承認を求める、といった近道が補助 CLI で通ってしまう
- 出典: research.md の記事の節
- 強制: structure — `check_entries` が `ENTRIES` の表の関数の最初の文を確かめる
- probe: GATE-03-a
- 良い例:
  `ctx = context.begin(where, run_id, trail.REVIEW)`
- 悪い例:
  `review_tally` の最初で `workspace.load_trail(...)` を読み、段を確かめずに集計する

### GATE-04 検査コマンドは verify だけが実行し、証拠は tree に結び付ける

- 軸: X6
- 決定: 検査コマンド（プロファイルの `verify.commands` と、計画の受け入れ条件のコマンド）を実行する `proc.shell` は `verifying` だけから呼び、結果は実行時の tree id と一緒に `evidence/<seq>.json` に書く。証拠の後に tree が変わったら、`trail.next_step` は次の段を `verify` にする。報告書（`handoff`）は、今の tree で通った証拠だけを使う。
- 理由: AI が書いた「テストは通った」は証拠にならない。補助 CLI が実行し、差分の版に結び付けた出力だけが、人の読む証拠になる
- 出典: research.md の記事の節（「ask it to show the output instead of saying it's done」）
- 強制: structure, test — `check_calls` が `verifying` の外の `proc.shell` を落とし、`tests/test_trail.py` の `test_changed_after_verify` が、証拠の後に tree が変わると次の段が `verify` になることを確かめる
- probe: GATE-04-a, GATE-04-b
- 良い例:
  `proc.shell(command.run, ctx.where.root, command.timeout_sec)` を `verifying` に書く
- 悪い例:
  `handoff.py` で `proc.shell("npm test", root, 600)` を実行して結果を報告に書く

### GATE-05 人の決定は decide だけが記録し、コミットは承認した tree と一致するときだけ行う

- 軸: X6
- 決定: 人の関所の決定を表す出来事（`trail.decided`）を作るのは `deciding` だけにし、`--answer` に人の回答の原文が無ければ `StageError` にする。決定には、そのときの tree id と、承認した人（`git config user.email`）を記録する。`commit` は、最後の決定が H3 の `approve` で、その tree と今の tree が一致するときだけ動く。
- 理由: 承認が特定の版に結び付いていないと、承認の後の変更が人の見ていないまま入る。記事の「An approval covers one specific commit」を、ローカルでは tree id で守る
- 出典: research.md の記事の節
- 強制: structure, test — `check_calls` が `deciding` の外の `trail.decided` を落とし、`tests/test_handoff.py` の `test_commit_requires_same_tree` が、承認の後に tree が変わるとコミットしないことを確かめる
- probe: GATE-05-a, GATE-05-b
- 良い例:
  `event = trail.decided(gate, choice, answer, ctx.tree, who, now)` を `deciding.decide` に書く
- 悪い例:
  `handoff.py` で `trail.decided(policy.H3, "approve", "", tree, "", now)` を書いて自分で承認する

### GATE-06 リスクの段は規則と AI の大きい方にし、AI は段を下げない

- 軸: X6
- 決定: リスクの段は `policy.merge_tier(規則の段, AI の段)` で、2つのうち大きい方（`low` < `medium` < `high`）にする。人の要否は、規則で常に人が見るパスに当たるか、AI が要ると判定したかのどちらかで真にする。規則の段は変更（差分のパス・大きさ・種類）だけから決め、計画や報告の自己申告を使わない。
- 理由: 記事は「The change sets the tier, not the author」とする。AI の判定で段を下げられると、作者（実装役）と同じ AI が自分の変更のリスクを軽く見積もれる
- 出典: research.md の記事の節
- 強制: test — `tests/test_policy.py` の `test_merge_tier` が、全ての組で結果が両方以上であることを確かめる
- probe: GATE-06-a
- 良い例:
  `tier = policy.merge_tier(rule.tier, judgment.tier)`
- 悪い例:
  `tier = judgment.tier`

### GATE-07 読み取りだけの役の前後で tree を比べ、変わっていれば止める

- 軸: X6
- 決定: 計画役・探索役・検証役・リスク判定役のプロンプトを書く段（`plan-new`、`review-new`、`review-collect`、`risk-new`）は、そのときの tree id を控え、出力を受け取る段（`plan-check`、`review-collect`、`review-tally`、`risk-check`）は、`context.require_same_tree` で今の tree と比べ、違えば `StageError` にする。
- 理由: 読み取りだけの役も Write と Bash を持つため、道具の一覧だけではファイルの書き換えを止められない。レビューの途中で差分が変わると、投票した差分と報告する差分が食い違う
- 出典: research.md の「Claude Code のサブエージェント」
- 強制: test — `tests/test_reviewing.py` の `test_tree_changed_during_review` が、探索役の間に作業ツリーが変わると `review-collect` が止まることを確かめる
- probe: GATE-07-a
- 良い例:
  `context.require_same_tree(ctx.next.prompted_tree, ctx.tree)`
- 悪い例:
  探索役の出力を読むだけで、tree を比べない

## TEST テスト

### TEST-01 モジュールごとに tests/test_<モジュール>.py と <名前>Test クラスを置く

- 軸: F1, F2, F5
- 決定: `autoflow_kit` の各モジュール（`__init__` と `errors` を除く）と `install.py` に、`tests/test_<モジュール>.py` を1つ置き、その中に `<モジュール名の PascalCase>Test` の `unittest.TestCase` を置く。対応するモジュールの無い `test_*.py` は置かない。全体の流れ（start から commit まで）は `tests/test_cli.py` で確かめる。
- 理由: テストの置き場と名前が揺れると、どのモジュールにテストが無いかを見つけられない
- 強制: structure — `check_tests` が、テストのファイルとクラスの有無と、対応の無いテストを落とす
- probe: TEST-01-a
- 良い例:
  `tests/test_trail.py` の `class TrailTest(unittest.TestCase):`
- 悪い例:
  `tests/test_misc.py`

### TEST-02 モックを使わず、support.py の部品と本物の git で確かめる

- 軸: F3, F4
- 決定: テストは `unittest.mock` を使わない。見本のリポジトリは `support.make_repo` で `tests/fixtures/sample-repo/` を一時ディレクトリに写して git の基準を作り、サブエージェントの出力は `support` の `act_*`（`act_planner`、`act_builder`、`act_finders`、`act_verifiers`、`act_risk`）で書き、git とシェルは本物を使う。
- 理由: モックは、git の tree や検査コマンドの実際の振る舞いとの食い違いを隠す。サブエージェントを本当に起動すると、テストが遅く、費用がかかり、結果が揺れる
- 強制: structure — `check_tests` が `tests/` の `unittest.mock` と `mock` の import を落とす
- probe: TEST-02-a
- 良い例:
  `support.act_finders(where, run_id, {"correctness": [support.finding()]})`
- 悪い例:
  `with mock.patch("autoflow_kit.proc.shell"):`

### TEST-03 新しい名前を足したら、表の置き場に test_<名前> を1つ足す

- 軸: F2, F5
- 決定: 依頼で新しい名前を足したら、その名前の振る舞いを確かめるメソッド `test_<足した名前>` を1つ足す。名前ごとの置き場は次の表のとおりにし、他のテストのファイルに同じ名前のメソッドを作らない。全体の流れで確かめたいことは、`tests/test_cli.py` の既存のメソッドに assert を足す。名前を足さない変更（不具合の修正、文言の修正）は、直した関数を確かめている既存のメソッドに assert を足し、そのメソッドが無ければ `test_<直した関数の名前>` を足す。
  | 足した名前 | 置き場 | メソッドの例 |
  |---|---|---|
  | H1・H2 の規則の id | `tests/test_policy.py` | `test_h1_new_dependency` |
  | レビューの観点 | `tests/test_policy.py` | `test_lens_performance` |
  | ひな形の置き換えの名前 | 値を作る段のテスト（`test_planning.py`、`test_building.py`、`test_risking.py`、`test_reviewing.py` のどれか） | `test_prior_findings` |
  | サブコマンドか、その引数 | 引数を受け取る段のテスト | `test_only` |
  | プロファイルの項目 | `tests/test_profile.py` | `test_review_rounds` |
  | 取得元 | `tests/test_intake.py` | `test_source_jira` |
  | 段とサブエージェントが受け渡す JSON（`contracts`）の項目 | `tests/test_contracts.py` の、その JSON を読む関数の `test_parse_<名前>`（あれば assert を足す） | `test_parse_plan` |
  | 実行の記録の出来事・段 | `tests/test_trail.py` | `test_escalate` |
  | モジュールに足した公開の関数（`_` で始まらない名前） | そのモジュールのテスト | `test_<関数名>` |
- 理由: テストのメソッド名を作者が文で付けると、同じ確認に別の名前が付き、どのテストが何を守っているかを探せない
- 強制: review — レビュー用スキルの確認項目
- 機械化しない理由: どの名前が依頼で足したものかは、差分の意味の判断が要る
- probe: なし
- 良い例:
  `verify` に引数 `--only` を足し、`tests/test_verifying.py` に `def test_only(self) -> None:` を足す
- 悪い例:
  `test_only_runs_one_command` と `test_only_skips_others` のように、同じ確認に文の名前を付ける

## PROC 作業手順

### PROC-01 段を足すときは記録から入口の順に作る

- 軸: G1
- 決定: 段を足すときは、(1) `trail` に段の定数と出来事と `next_step` の分岐を足し、(2) `contracts` と `layout` に受け渡しの形と置き場を足し、(3) 段のモジュールを書き、(4) `status` に次の手を足し、(5) `cli` にサブコマンドを足し、(6) テストを書き、(7) `autoflow/SKILL.md` の「繰り返すこと」の表を直す、の順に作る。
- 理由: 入口から作ると、状態機械と受け渡しの形が後から変わり、作り直しが増える
- 強制: doc — 実装用スキルの「作る順序」
- 機械化しない理由: 作る順序は、出来上がった差分に痕跡が残らない
- probe: なし
- 良い例:
  `trail.DOCS`（文書を作る段）と `next_step` の分岐を足してから `documenting.py` を書く
- 悪い例:
  `cli.py` に `docs-new` を足してから、状態機械の分岐を考える

### PROC-02 波及の対応表の組は一緒に変える

- 軸: G2
- 決定: 次の表の左を変えたら、同じ変更で右も変える。既存の値を別の段で使うだけなら、右は変えない。
  | 変えるもの | 一緒に変えるもの |
  |---|---|
  | `policy` の表（`TIERS`、`DEPTHS`、`KINDS`、`H1_RULES`、`H2_RULES`、`GATES`、`LENSES`、`REVIEW`） | `make docs`（gates.md）。規則を足したら `tests/test_policy.py` の `test_<id>` |
  | `policy.LENSES` | `kit/.autoflow/templates/prompts/finder.md` の観点の節 |
  | `prompts.TEMPLATES` | `kit/.autoflow/templates/prompts/` のひな形 |
  | `contracts.AGENTS` | `kit/claude/agents/` の定義 |
  | `contracts` の JSON の項目 | そのJSON を書かせるひな形の例、`tests/support.py` の `act_*` |
  | `profile` のキー | `make docs`（profile-schema.md）、`setup.py` の検出、`views.render_profile` |
  | `layout.SOURCES` | `kit/claude/skills/autoflow/references/sources.md` の表 |
  | `trail` の段 | `status.py`、`kit/claude/skills/autoflow/SKILL.md` の「繰り返すこと」の表、architecture.md のデータの流れ |
  | `autoflow_kit` のモジュールの増減 | `structure_check.py` と `architecture.md` の許可表 |
- 理由: 片方だけ変えると、補助 CLI とスキル、または判定と文書が食い違う
- 強制: structure, review — `check_templates` が `prompts.TEMPLATES` とひな形のファイルの一致を、`check_agents` が `contracts.AGENTS` と定義の一致を確かめ、残りの組はレビューで見る
- probe: PROC-02-a
- 良い例:
  `prompts.TEMPLATES` に `"explainer"` を足し、`templates/prompts/explainer.md` を作る
- 悪い例:
  `templates/prompts/` にひな形だけを足し、表に足さない

### PROC-03 道具の版は Makefile で固定し、上げるときは ADR を書く

- 軸: G3
- 決定: ruff と mypy の版は `Makefile` の `RUFF` と `MYPY` で固定する。上げるときは ADR を書き、research.md を直し、`make check` と `violation_probe.py` を通す。
- 理由: 版が揺れると、同じコードで検査の結果が作者ごとに変わる
- 強制: doc — 実装用スキルの「依頼の振り分け」
- 機械化しない理由: 版を上げる手順は、出来上がった差分では `Makefile` の1行にしか現れない
- probe: なし
- 良い例:
  ADR を書いてから `RUFF := uvx ruff@0.18.0`
- 悪い例:
  `RUFF := uvx ruff`（版を書かない）

### PROC-04 ルールは ADR から probe の順で変える

- 軸: G4
- 決定: ルールを変えるときは、AGENTS.md の「ルールを変えたいとき」の順（ADR → rules.md → 検査の設定と probes.json → 見本 → `rules_check.py` と `violation_probe.py`）で変える。
- 理由: 順序を飛ばすと、文書と検査が食い違ったまま残る
- 強制: doc — AGENTS.md の「ルールを変えたいとき」
- 機械化しない理由: 変えた順序は差分に残らない
- probe: なし
- 良い例:
  ADR を書いてから rules.md を直す
- 悪い例:
  `pyproject.toml` のルールを外してから理由を考える

### PROC-05 完了の条件は make check が通ること

- 軸: G5
- 決定: 作業を完了と言うのは、`make check` が通り、実装用スキルの完了前チェックリストを満たし、報告に check の結果の末尾を貼ったときだけにする。
- 理由: 完了の基準が揺れると、検査の通らない変更が完了として渡される
- 強制: doc — AGENTS.md の「完了の条件」と実装用スキルのチェックリスト
- 機械化しない理由: 報告の中身は差分に残らない
- probe: なし
- 良い例:
  報告の最後に `make check` の出力の末尾を貼る
- 悪い例:
  「テストは通るはず」と書いて終える

### PROC-06 プロファイルの形を変えたら SCHEMA_VERSION を上げる

- 軸: X2
- 決定: profile.json のキーを足す・消す・意味を変えるときは、`profile.SCHEMA_VERSION` を1上げ、ADR に移行の手順（古いファイルの直し方）を書き、`profile.parse` は古い版を `InvalidFileError`（「setup-new で作り直す」と書く）にする。補助 CLI とサブエージェントが受け渡す JSON（plan.json、report.json、指摘、投票、judgment.json）は、ひな形と同じ変更で変えるので版を持たない。
- 理由: 配布先には人が承認したプロファイルが残る。形を黙って変えると、承認済みのファイルが検査で落ちる理由が分からない
- 強制: review — レビュー用スキルの確認項目
- 機械化しない理由: キーの意味が変わったかどうかは、字面では判定できない
- probe: なし
- 良い例:
  キーを足し、`SCHEMA_VERSION = 2` にして ADR を書く
- 悪い例:
  `SCHEMA_VERSION = 1` のままキーの意味を変える

## TOOL 道具と自動化

### TOOL-01 整形は ruff format に任せる

- 軸: H1
- 決定: Python の整形は `ruff format`（行の長さ120）に任せ、手で整形しない。整形の確認は `make check` の `format-check` で行う。
- 理由: 整形を手で決めると、差分が整形の違いで埋まる
- 強制: format — `make format-check`（`ruff format --check`）
- probe: TOOL-01-a
- 良い例:
  `make fix` を回してから差分を見る
- 悪い例:
  `def  spaced( value:int )->int:`

### TOOL-02 編集の直後は hooks、完了の前は make check を回す

- 軸: H2
- 決定: Python のファイルを編集した直後は、hooks が `make fix-file FILE=<パス>` を回す。完了の前に `make check` を回す。CI と pre-commit は置かない。
- 理由: 回すタイミングが揺れると、整形と lint の違反が完了の直前にまとめて見つかる
- 強制: doc — AGENTS.md の「コマンド」と実装用スキルの完了前チェックリスト
- 機械化しない理由: hooks の設定は `.claude/settings.json`（保護ファイル）にあり、回したかどうかは差分に残らない
- probe: なし
- 良い例:
  編集 → hooks の整形 → `make check`
- 悪い例:
  `make check` を回さずに完了と報告する

### TOOL-03 抑止コメントを書かない

- 軸: H3
- 決定: lint・型・整形・カバレッジ・テストの抑止コメント（manifest の `guard.suppressions` の全パターン）を書かない。
- 理由: 抑止コメントで検査を通せるなら、そのルールは無いのと同じになる
- 強制: structure — `make guard`（`.foundation/bin/guard.py`）
- probe: TOOL-03-a
- 良い例:
  違反を直してから `make check`
- 悪い例:
  `LIMIT = 1  # pragma: no cover`

### TOOL-04 保護ファイルを変えない

- 軸: H3
- 決定: manifest の `protected` にあるファイル（`Makefile`、`pyproject.toml`、`scripts/structure_check.py`、`.claude/settings.json`、`.foundation/**`、`docs/design/rules.md`、`docs/design/enforcement-matrix.md`）は、依頼で明示されたときだけ変える。
- 理由: 検査の設定を緩めれば、どんな違反も通せてしまう
- 強制: review — レビュー用スキルの確認項目
- 機械化しない理由: hooks はエージェントの編集にだけ確認を求め、人の編集は止められないため、差分のレビューで確かめる
- probe: なし
- 良い例:
  ルールの変更を提案として報告する
- 悪い例:
  `pyproject.toml` の `ignore` に `C901` を足す

### TOOL-05 配布物は Python 3.9 で動く書き方にする

- 軸: H4
- 決定: 配布物とテストは Python 3.9 で動く構文と API だけを使う（`match` 文、`zip(strict=True)`、`sys.stdlib_module_names` は使わない）。開発の道具は `uvx` で版を固定して呼ぶ。
- 理由: 配布先の `python3` が 3.9 でも動く必要がある。3.10 以降の API は、開発者の環境では動いても配布先で落ちる
- 出典: research.md の「Python」「mypy」
- 強制: type — mypy の `python_version = 3.9`
- probe: TOOL-05-a
- 良い例:
  `list(zip(left, right))`
- 悪い例:
  `list(zip(left, right, strict=True))`

## 対象外とした軸

揺れない軸、またはこの分野に無い軸と、その理由を書く。カタログの全軸と追加した軸を、上のルールのどれかで答えたため、対象外とした軸は無い。

| 軸 | 理由 |
|---|---|
