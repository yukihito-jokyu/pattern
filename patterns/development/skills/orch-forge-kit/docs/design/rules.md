# orch-forge-kit のルール

このファイルは orch-forge-kit のルールの正本である。AGENTS.md・スキル・レビューの指摘・検査のエラーは、ここのルールIDを参照する。ルールの変更手順は AGENTS.md の「ルールを変えたいとき」に従う。

## 読み方

- ルールIDは `<接頭辞>-<連番>` である。廃止したルールも ID を再利用せず、`- 状態: 廃止` と書いて残す
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
| 対象スキル | 構築・改善する、対象のリポジトリの開発用オーケストレーションスキル（`.claude/skills/<スキル名>/`）。メインのセッションで動き、Agent ツールでサブエージェントを起動して開発の作業を進める |
| バンドル | 対象スキルの `SKILL.md`・`references/` と、名前が `<スキル名>-` で始まるサブエージェントの定義（`.claude/agents/<スキル名>-<役>.md`）をまとめたもの |
| バンドルの決まり | バンドルが満たす形の決まり。`bundle.RULES` の `B01` から始まる id で引く。文は `forge-build/references/bundle-rules.md`（生成物）にある |
| charter | 人と決めたゴール・指標・評価課題・環境・実行の条件・予算と、人の承認を書いた `charter.json` |
| 設計 | forge-build で設計役が書き、人が承認した、対象スキルの役・手順・人の関所・報告の形（`design.json`） |
| 補助 CLI | `kit/.forge/forge.py` と `forge_kit` パッケージ。配布先では `.forge/forge.py` |
| 段 | 補助 CLI の1つのサブコマンドが受け持つ処理 |
| 段のモジュール | 1つ以上のサブコマンドを実装するモジュール（`goals`、`status`、`designing`、`building`、`prepare`、`execute`、`collect`、`score`、`analyze`、`compare`、`decide`、`report`） |
| 共有のモジュール | 2つ以上の段が使うモジュール（`errors`、`layout`、`catalog`、`metrics`、`render`、`shape`、`charter`、`design`、`trace`、`contracts`、`fsops`、`proc`、`prompts`、`bundle`、`views`、`workspace`） |
| 設計役・構築役・採点役・分析役 | この基盤のサブエージェントの `forge-designer`、`forge-builder`、`forge-grader`、`forge-analyst` |
| 実行役 | 補助 CLI の `execute` が評価用のコピーの中で起動する `claude -p`。対象スキルを `/<スキル名> <評価課題>` で呼ぶ |
| 実行の記録 | 実行役の `--output-format stream-json` の出力を保存した `stream.jsonl` |
| 評価の置き場（slot） | 1回の評価の結果を置く場所。`round-<N>-baseline`、`round-<N>-candidate`、`final` |
| ホールドアウト | ID が `H` で始まる評価課題。`final` の評価だけで使い、設計役・構築役・分析役に見せない |

## 追加した軸

カタログに無い、この分野に固有の軸を定義する。

| 軸 | 内容 | 置く節 |
|---|---|---|
| X1 | 終了コードと出力の形式（標準出力と標準エラーの使い分け、警告と `status` の行の書き方） | OPS |
| X2 | 公開 API の互換性（charter.json と design.json の形を変えるときの手順） | PROC |
| X3 | この基盤のスキル・サブエージェントの定義の書式（frontmatter、行数、参照ファイル） | STR |
| X4 | サブエージェントとの受け渡し（プロンプトのひな形と、サブエージェントが書くファイル） | STATE |
| X5 | 人の関所（人が決める場面と、その聞き方） | PROC |
| X6 | 生成するオーケストレーションスキルの形（バンドルの決まりの置き場） | STR |
| X7 | `claude -p` の起動（引数、権限、上限） | OPS |

## STR 配置と構造

### STR-01 ディレクトリは表の6か所に分けて置く

- 軸: A1, A5
- 決定: ファイルは次の表の置き場に置き、`kit/.forge/forge_kit/` にはサブパッケージを作らない。
  | 置くもの | 置き場 |
  |---|---|
  | 補助 CLI のモジュール | `kit/.forge/forge_kit/<モジュール>.py`（平らに並べる） |
  | サブエージェントと実行役へのプロンプトのひな形 | `kit/.forge/templates/prompts/<名前>.md` |
  | 配布するスキル | `kit/claude/skills/forge-<名前>/` |
  | 配布するサブエージェント | `kit/claude/agents/forge-<役>.md` |
  | 開発用のスクリプト（構造検査、生成器） | `scripts/` |
  | テスト、見本のリポジトリ、記録した実行の記録 | `tests/test_<モジュール>.py`、`tests/fixtures/sample-repo/`、`tests/fixtures/streams/<名前>.jsonl` |
- 理由: 置き場が分かれると、配布物（`kit/`）と開発の道具が混ざり、`install.py` が写す範囲が作者ごとに変わる
- 強制: structure — `scripts/structure_check.py` の `KIT_LAYOUT` と `check_layout` が、`kit/` の下の名前とサブパッケージの有無を確かめる
- probe: STR-01-a
- 良い例:
  `kit/.forge/forge_kit/trace.py`
- 悪い例:
  `kit/.forge/forge_kit/stages/execute.py`

### STR-02 モジュールを足すときは許可表に行を足し、テストを作る

- 軸: A2, A3
- 決定: `forge_kit` にモジュールを1つ足すときは、`scripts/structure_check.py` の `SHARED` か `STAGES` と `docs/design/architecture.md` の許可表に行を足し、`tests/test_<モジュール>.py` を作る。1つのモジュールが受け持つのは、用語の表の段のモジュールの1つの段か、共有のモジュールの1つの関心だけにする。
- 理由: 表に無いモジュールは依存の向きを検査できず、どこに何があるかが作者ごとに変わる
- 強制: structure — `check_module_table` が、表に無いモジュールと、モジュールの無い表の行を落とす
- probe: STR-02-a
- 良い例:
  `SHARED` に `"trace": {"render"}` を足し、`tests/test_trace.py` を作る
- 悪い例:
  表に足さずに `forge_kit/cache.py` を置く

### STR-03 入口は forge.py と cli.main の2つだけにする

- 軸: A7
- 決定: `forge_kit/__init__.py` には docstring だけを書き、コマンドの入口は `kit/.forge/forge.py` から呼ぶ `cli.main(argv, default_root)` だけにする。
- 理由: `__init__.py` で再 export すると、`from forge_kit import main` と `from forge_kit.cli import main` の2通りの書き方が生まれる
- 強制: structure — `check_init` が、`__init__.py` に docstring 以外の文があると落とす
- probe: STR-03-a
- 良い例:
  `"""orch-forge の補助 CLI。"""`
- 悪い例:
  `__all__ = ["cli"]`

### STR-04 生成物は手で編集せず make docs で作り直す

- 軸: A6
- 決定: 次の表の生成物は手で編集せず、入力を直してから生成し直す。
  | 生成物 | 入力 | 生成するもの |
  |---|---|---|
  | `kit/claude/skills/forge-goals/references/metric-catalog.md` | `catalog.METRICS` | `make docs`（`scripts/gen_docs.py`） |
  | `kit/claude/skills/forge-build/references/bundle-rules.md` | `bundle.RULES` | `make docs`（`scripts/gen_docs.py`） |
  | `docs/design/enforcement-matrix.md` | `docs/design/rules.md`、`.foundation/probes.json` | `rules_check.py` |
- 理由: 手で直した生成物は、次の生成で消えるか、コードと食い違ったまま残る
- 強制: structure — `make docs-check` が生成し直した結果と比べ、違えば落とす
- probe: STR-04-a
- 良い例:
  `catalog.py` を直してから `make docs`
- 悪い例:
  `bundle-rules.md` の文言だけを直す

### STR-05 この基盤のスキルとサブエージェントは決まった frontmatter で書く

- 軸: X3
- 決定: 配布するスキルとサブエージェントは次の形にする。
  | 対象 | 形 |
  |---|---|
  | スキル | ディレクトリ名と `name` を `forge-<名前>` で同じにし、`description`、`disable-model-invocation: true`、`allowed-tools: Bash(python3 .forge/forge.py *)` を書き、`context` を書かない。SKILL.md は500行以内にし、参照は `references/<ファイル>` の1階層で、`references/` の全ファイルを SKILL.md から参照する |
  | サブエージェント | ファイル名と `name` を同じにし、`contracts.AGENTS` の値とそろえる。`description` を書き、`tools` を列挙し、`Skill` と `Agent` を入れない。採点役と分析役には `omitClaudeMd: true` を書く |
- 理由: `Agent` を持つサブエージェントは、さらにサブエージェントを起動して費用の見積もりが崩れる。`Skill` を持つと、評価中の候補ではなく元のリポジトリのスキルを読み込みうる。自動で呼ばれるスキルは、人の知らない間に `claude -p` を大量に起動しうる
- 出典: research.md の「Claude Code のスキル」「Claude Code のサブエージェント」
- 強制: structure — `check_skills` と `check_agents` が frontmatter、行数、参照、`tools` を確かめる
- probe: STR-05-a, STR-05-b
- 良い例:
  `tools: Read, Write, Glob, Grep`
- 悪い例:
  `tools` を省く（全ツールを継承し、`Skill` と `Agent` も使える）

### STR-06 バンドルの決まりは bundle.RULES の表だけに書く

- 軸: X6
- 決定: 生成・改善するバンドルの形の決まりは `bundle.RULES` の表だけに書き、1行に id（`B` と2桁の番号）・文・検査の関数を置く。`B` と2桁の番号だけの文字列は `bundle.py` の外に書かない。ひな形とスキルは決まりの文を写さず、`forge-build/references/bundle-rules.md` を読ませる。決まりを1つ足したら、`tests/test_bundle.py` に `test_<id の小文字>`（`test_b13` の形）を足す。
- 理由: 決まりの文がひな形・スキル・検査に散ると、構築役が読む決まりと `bundle-check` が落とす決まりが食い違い、構築役が直しても検査が通らない
- 出典: research.md の「Claude Code のスキル」「Claude Code のサブエージェント」
- 強制: structure, test — `check_literals` が `bundle.py` の外の `B` と2桁の番号の文字列を落とし、`tests/test_bundle.py` が `RULES` の全 id に `test_<id の小文字>` があることを確かめる
- probe: STR-06-a, STR-06-b
- 良い例:
  `Rule("B10", "TODO(forge) を残さない。", _no_todo)` を `RULES` に足し、`test_b10` を足す
- 悪い例:
  `building.py` に `problems.append("B10: TODO が残っています")` を書く

## DEP 境界と依存

### DEP-01 import は許可表の組だけにし、段のモジュールどうしは import しない

- 軸: B1, B3, A4
- 決定: `forge_kit` のモジュールは、`docs/design/architecture.md` の許可表で印のある組だけを import する。段のモジュールは他の段のモジュールを import せず、2つ以上の段が使う処理は共有のモジュールに置く（`cli` だけは全部の段を import する）。
- 理由: 段どうしが呼び合うと、1つの段の変更が別の段の振る舞いを変え、変更の影響が予測できなくなる
- 強制: structure — `ALLOWED_IMPORTS` の表と `check_dependencies` が、表に無い import を落とす
- probe: DEP-01-a
- 良い例:
  `goals` と `analyze` が使う charter の描画を `views` に置く
- 悪い例:
  `building.py` で `from forge_kit import designing`

### DEP-02 他のモジュールの _ で始まる名前を使わない

- 軸: B2
- 決定: モジュールの外から使ってよいのは、`_` で始まらない名前だけにする。他のモジュールの `_` で始まる名前を import も参照もしない。
- 理由: 内部の関数に外から依存すると、その関数を直すだけで別のモジュールが壊れる
- 強制: structure — `check_dependencies` が `<モジュール>._<名前>` と `from forge_kit.x import _y` を落とす
- probe: DEP-02-a
- 良い例:
  `workspace.load_grade(where, slot, run_id)`
- 悪い例:
  `trace._edit_paths(message)`

### DEP-03 Python 3.9 の標準ライブラリだけを使う

- 軸: B4, B6, H4
- 決定: 配布物・スクリプト・テストは、`scripts/structure_check.py` の `STDLIB` の表にある標準ライブラリと、`forge_kit`・`tests`・`install` だけを import する。表に足すときは ADR を書かずに表と research.md を一緒に変え、標準ライブラリでないものは足さない。
- 理由: 配布物は任意のリポジトリで `python3` だけで動く必要がある。依存を足すと、配布先ごとに導入の手順が要る
- 出典: research.md の「Python」
- 強制: structure — `check_stdlib` が表に無い import を落とす
- probe: DEP-03-a
- 良い例:
  `import difflib`
- 悪い例:
  `import yaml`

### DEP-04 副作用に触れるモジュールを表の3つに限る

- 軸: B5
- 決定: 副作用に触れてよいモジュールは次の表のとおりにする。
  | 副作用 | 触れてよいモジュール |
  |---|---|
  | ファイルを書く・消す・作る（`open`、`shutil`、`FS_WRITERS` の表の全メソッド） | `fsops` |
  | 外部コマンド（`subprocess`）、`shutil.which`、`tempfile` | `proc` |
  | 時刻（`datetime`、`time`）、画面への出力（`print`） | `cli` |
- 理由: 副作用が散ると、テストで一時ディレクトリ以外を書き換える箇所や、時刻で結果が変わる箇所を見つけられない
- 強制: structure, lint — `check_side_effects` がファイルの書き込み・`subprocess`・`tempfile`・時刻を、ruff の `T201` が `print` を落とす（`cli.py`、`scripts/`、`install.py` だけ `T201` を外す）
- probe: DEP-04-a, DEP-04-b
- 良い例:
  `fsops.write_text(path, text)`
- 悪い例:
  `path.write_text(text)` を `execute.py` に書く

## NAM 命名

### NAM-01 名前のケースは PEP 8 に従う

- 軸: C1, C2, C6
- 決定: モジュール・関数・変数は snake_case、クラスは PascalCase、定数は UPPER_SNAKE_CASE にする。Markdown のファイル名（ひな形、エージェント、参照ファイル）は kebab-case にする。略語も単語として扱い、`Id` ではなく `id`、`run_id` のように書く。
- 理由: ケースが揺れると、同じものを別の名前で探すことになる
- 強制: lint — ruff の `N` 群（`N802`、`N806` ほか pep8-naming の全ルール）
- probe: NAM-01-a
- 良い例:
  `def run_id(task_id: str, agent_no: int) -> str:`
- 悪い例:
  `def getRunId(taskId, agentNo):`

### NAM-02 関数名の先頭の動詞は語彙表から選ぶ

- 軸: C3, C4, C5
- 決定: 次の表の意味の関数は表の動詞で始め、表の動詞を表の意味以外に使わない。表の動詞と同じ意味の別の動詞（`get_`・`fetch_`・`format_`・`create_`・`validate_`・`save_`）は使わない。表に無い意味の関数は、意味を表す名詞（`digest`・`estimate`・`placeholders`）か、表に無い動詞（`copy_tree`・`launch`・`recommend`）で始めてよい。段の名前で始まる名詞の組（`build_progress`・`design_state`）は動詞と見なさない。真偽値を返す関数は `is_`・`has_` で始める（`property` と、JSON の値を型ごとに読む `shape` の関数を除く）。秒は `_sec`、費用は `_usd`、件数は `_count` か複数形で表す。
  | 動詞 | 意味 |
  |---|---|
  | `read_` | ファイルを検証せずに読む（`fsops` だけ） |
  | `load_` | ファイルを読んで検証し、モデルを返す（`workspace` だけ） |
  | `parse` か `parse_` | 読んだ値を検証してモデルにする（`charter`、`design`、`contracts`、`trace`） |
  | `write_` | ファイルに書く（`fsops` だけ） |
  | `render_` | モデルから人が読む Markdown を作る |
  | `make_` | 値を組み立てて返す（`make_layout`、`make_slot`、`make_parser`） |
  | `check_` | 検証して、問題の一覧か文言を返す |
  | サブコマンドの名前の `-` を `_` にしたもの（`charter_new`、`bundle_check` の形） | その段の入口 |
- 理由: 同じ意味の動詞が混ざると（load と read、render と format）、読み手が副作用や検証の有無を取り違える
- 強制: structure, review — `scripts/structure_check.py` の `check_names` が、`SYNONYM_VERBS` の別名で始まる関数を落とす。表の動詞の使い分けと真偽値の名前はレビューで見る
- 機械化しない理由: 表の動詞を表の意味で使っているか（`load_` なのに検証しない、など）は、関数の中身の判断が要る
- probe: NAM-02-a
- 良い例:
  `def load_scores(where: Layout, slot: Slot) -> contracts.Scores:`
- 悪い例:
  `def get_scores(...)` と `def fetch_scores(...)` が並ぶ

### NAM-03 JSON のキーは snake_case にし、dataclass のフィールド名と同じにする

- 軸: C7
- 決定: charter・設計と、補助 CLI とサブエージェントが受け渡す JSON のキーは snake_case にし、対応する dataclass のフィールド名と同じ綴りにする。書くときは `contracts.to_data`（`dataclasses.asdict`）を使う。実行の記録（`stream.jsonl`）のキーは Claude Code の綴りのまま `trace.py` だけで読む。
- 理由: キーとフィールド名がずれると、変換の箇所が増え、プロンプトの JSON の例とずれる
- 強制: structure — `check_json_keys` が、`charter.py`・`design.py`・`contracts.py` の `shape` の呼び出しと `unknown_keys` のキーの綴りを確かめる
- probe: NAM-03-a
- 良い例:
  `shape.text(root, "run_id", "", problems)`
- 悪い例:
  `shape.text(root, "runId", "", problems)`

## CODE 書き方

### CODE-01 データは継承しない frozen の dataclass にし、引数を変えない

- 軸: D1, D5
- 決定: `errors.py` 以外のクラスは、基底クラスを持たない `@dataclass(frozen=True)` にし、振る舞いは関数に書く（メソッドは `property` とパスを返す `Layout` のメソッドだけ）。並びは `tuple` で持ち、関数は引数の `dict` と `list` を変えない。ただし、検証の関数が受け取る問題の一覧 `problems`（呼び出し側が作った空の `list` に、見つけた問題の文を足していく。`shape` と `charter`・`design`・`contracts` の `parse` の形）だけは足してよい。
- 理由: 可変のオブジェクトを渡し合うと、どの段で値が変わったかを追えない
- 強制: structure, review — `check_classes` がクラスの形を確かめ、引数を変えていないかはレビューで見る
- probe: CODE-01-a
- 良い例:
  `@dataclass(frozen=True)` の `class Launch:`
- 悪い例:
  `class Cache:` に `self.items = {}` を持たせる

### CODE-02 import は forge_kit からの絶対 import にする

- 軸: D2
- 決定: パッケージの中の import は `from forge_kit import <モジュール>` か `from forge_kit.<モジュール> import <名前>` にし、相対 import は使わない。並び順は ruff の isort に任せる。
- 理由: 相対と絶対が混ざると、同じモジュールの参照が2通りの字面になり、構造検査の対象から漏れる
- 強制: lint — ruff の `TID252`（`ban-relative-imports = "all"`）と `I001`
- probe: CODE-02-a
- 良い例:
  `from forge_kit import fsops`
- 悪い例:
  `from .errors import KitError`

### CODE-03 型注釈は全部に書き、mypy の strict を通す

- 軸: D3
- 決定: 全モジュールの先頭に `from __future__ import annotations` を書き、全関数の引数と戻り値に型注釈を書く。省略可能な値は `X | None`、`Any` は `contracts.to_data` と `trace.py` だけで使う。
- 理由: 型が無いと、サブエージェントの JSON や実行の記録から作ったモデルの取り違えが実行時まで見つからない
- 出典: research.md の「mypy」
- 強制: type, lint — mypy の `strict`、ruff の `UP045`
- probe: CODE-03-a, CODE-03-b
- 良い例:
  `def mean(values: Sequence[float]) -> float | None:`
- 悪い例:
  `def mean(values):`

### CODE-04 関数の大きさは ruff の上限に収める

- 軸: D4, D6
- 決定: 関数の複雑度は10以下、引数は6以下、分岐は12以下、return は6以下、文は50以下にする。超えたら関数を分ける。
- 理由: 大きな関数は、変更のたびに読む範囲が広がり、作者ごとに分け方が揺れる
- 強制: lint — ruff の `C901`（`max-complexity = 10`）、`PLR0913`、`PLR0912`、`PLR0911`、`PLR0915`
- probe: CODE-04-a
- 良い例:
  見本: `kit/.forge/forge_kit/trace.py` の `_launches` と `_edits`
- 悪い例:
  1つの関数で起動とファイルの編集の両方を数える

### CODE-05 モジュールの docstring は必須にし、コメントアウトしたコードを残さない

- 軸: D7
- 決定: 全モジュールと全パッケージの先頭に、そのモジュールが受け持つことを1〜2文の docstring で書く。コメントは理由（なぜ）だけを書き、コメントアウトしたコードは残さない。
- 理由: 受け持ちの1文があれば、新しい処理を置くモジュールを選べる。古いコードのコメントは読み手を迷わせる
- 強制: lint — ruff の `D100`、`D104`、`ERA001`
- probe: CODE-05-a, CODE-05-b
- 良い例:
  `"""実行の記録（stream-json）を読み、起動と編集を数える。"""`
- 悪い例:
  `# return mean(values)`

### CODE-06 ファイル名とエージェント名の文字列は定数で持つ

- 軸: D8
- 決定: `.json`・`.jsonl`・`.md`・`.patch`・`.txt` で終わるファイル名の文字列は `layout.py`（ひな形のファイル名だけ `prompts.py`）に、サブエージェントの名前は `contracts.AGENTS` に定数で置き、他のモジュールはその定数を使う。ファイル名の定数をディレクトリに `/` でつなぐのは `layout.py` の中だけにし、他のモジュールは `Layout` のメソッドで置き場を受け取る。ただし、バンドルの中の `SKILL.md`（`layout.SKILL_FILE`）は、バンドルの根からつないでよい。
- 理由: 同じファイル名を2か所に書くと、片方だけ変えたときに読み書きの場所がずれる
- 強制: structure — `check_literals` が、持ち主のモジュール以外にあるファイル名とエージェント名の文字列を落とす。`check_paths` が、`layout.py` の外でファイル名の定数を `/` でつなぐ式を落とす
- probe: CODE-06-a, CODE-06-b
- 良い例:
  `where.stream_path(slot, run_id)`
- 悪い例:
  `where.run_dir(slot, run_id) / "stream.jsonl"`、`where.slot_dir(slot) / layout.SCORES_MD`

## ERR エラーと入力検証

### ERR-01 投げる例外は errors.py の4つだけにし、捕まえるのは cli.main だけにする

- 軸: E1
- 決定: 例外は `KitError`、`InvalidFileError`、`StageError`、`CommandError` だけを投げる。捕まえるのは `cli.main`（終了コード1にする）と、判定のために `KitError` を捕まえる `workspace` と `score` だけにし、`Exception` を捕まえない。
- 理由: 例外の種類と捕まえる場所が散ると、人に見せる文言と終了コードが段ごとに変わる
- 強制: structure, lint — `check_errors` が errors.py 以外の例外の `raise` を、ruff の `BLE001` が `except Exception` を落とす
- probe: ERR-01-a, ERR-01-b
- 良い例:
  `raise StageError("先に prepare を実行してください")`
- 悪い例:
  `raise ValueError("bad")`

### ERR-02 外から来る JSON は workspace の load_* で検証してから使う

- 軸: E2
- 決定: charter・設計と、サブエージェントが書く JSON（grade.json、proposal.json）と、実行の記録と、補助 CLI が書いた JSON は、`workspace` の `load_*` で `charter.parse`・`design.parse`・`contracts.parse_*`・`trace.parse` を通してから使う。`fsops.read_json` を呼んでよいのは `fsops` と `workspace` だけにする。問題は全部集めてから、JSON のパス付きで `InvalidFileError` にする。
- 理由: 検証を飛ばすと、サブエージェントの書き損じが集計の途中で別の形の失敗になり、どこを直せばよいかが分からない
- 強制: structure — `check_errors` が、`fsops` と `workspace` の外の `fsops.read_json` を落とす
- probe: ERR-02-a
- 良い例:
  `workspace.load_comparison(where, round_no)`
- 悪い例:
  `fsops.read_json(where.compare_path(round_no))` を `report.py` に書く

## STATE 状態とデータの流れ

### STATE-01 状態はファイルだけで持ち、進み具合はファイルの有無から求める

- 軸: E3
- 決定: 状態の置き場は次の表のとおりにし、段の進み具合を別の状態ファイルに書かない（`workspace.progress` がファイルの有無から求める）。
  | 状態 | 置き場 | 消してよいか |
  |---|---|---|
  | charter、設計、構築の記録、採点、提案、比較、決定、報告 | `.forge/targets/<id>/` | 消さない（記録として残す） |
  | 実行の記録、プロンプト、採点役の出力、評価に使うバンドルの写し | `.forge/work/<id>/<slot>/` | 消してよい（`.gitignore` に入れる） |
  | 評価用のコピー | OS の一時ディレクトリの `orch-forge/` の下（`proc.copies_root`） | 消してよい |
- 理由: 進み具合を別のファイルにも書くと、ファイルの実態と食い違ったときにどちらを信じるかが揺れる
- 強制: review — レビュー用スキルの確認項目
- 機械化しない理由: 新しいファイルが状態を表すかどうかは、ファイルの意味の判断が要る
- probe: なし
- 良い例:
  `executed = where.exec_path(slot, run_id).is_file()`
- 悪い例:
  `state.json` に `{"stage": "executed"}` を書く

### STATE-02 サブエージェントと実行役との受け渡しはひな形とファイルの契約だけで行う

- 軸: X4
- 決定: サブエージェントと実行役へのプロンプトの文章は `kit/.forge/templates/prompts/` のひな形だけに書き、置き換えの名前は `${名前}` の形で `prompts.TEMPLATES` の表と一致させる。成果は次の表のとおりに受け取り、返答や最後のメッセージの本文を読んで判断しない。
  | 成果 | 受け取り方 |
  |---|---|
  | 設計役の design.json、構築役の下書きのバンドル、採点役の grade.json、分析役の proposal.json と候補のバンドル | プロンプトが示すファイル。返答は `完了: <パス>` の1行 |
  | 実行役の作業 | `execute` が保存する実行の記録（stream.jsonl）、評価用のコピーの差分、最後の `result` の本文（result.md） |

  置き換えの値には文を書かない。値の作り方は次の表のとおりにし、`—` や `- なし` のときの扱いと、値を囲む記号（`` ` ``）や見出しは、ひな形に書く。
  | 値 | 入れるもの |
  |---|---|
  | 1つの値（パス、コマンド、名前） | 生の値。無いときは `render.MISSING`（`—`） |
  | 長さがデータで決まる一覧 | `render.bullets` で作った箇条書き（空なら `- なし`） |
  | 表 | `render.table` で作った表 |
- 理由: プロンプトの文をコードに散らすと、文言の変更でテストが追えない。返答の本文を読むと、メインのセッションの解釈で結果が揺れる
- 強制: test, review — `tests/test_prompts.py` が、全ひな形の置き換えの名前と表の一致を確かめ、置き換えの値に文を書いていないかはレビューで見る
- probe: STATE-02-a
- 良い例:
  `"roles": render.bullets(names)` と、ひな形の「一覧が `- なし` なら、役は無い」
- 悪い例:
  `f"あなたは採点役です。{run_id} を…"` を `collect.py` に書く。`"items": items or "- （判定する項目はありません）"` のように、無いときの文を値に入れる

## ASYNC 非同期と並行

### ASYNC-01 並行は proc の2つの関数だけで行う

- 軸: E4
- 決定: 補助 CLI の並行処理は、検査コマンドを回す `proc.shell_many` と、実行役を起動する `proc.launch_many` の2つ（どちらも `ThreadPoolExecutor`）だけにし、`threading`・`asyncio`・`multiprocessing`・`concurrent` を `proc.py` の外で使わない。サブエージェントの並行は、配布するスキルが Agent ツールの呼び出しを1つのメッセージにまとめて行う。
- 理由: 並行の仕組みが散ると、同じコピーへの同時書き込みや、終了の待ち方が作者ごとに変わる
- 強制: structure — `check_side_effects` が、`proc.py` 以外の並行のモジュールの import を落とす
- probe: ASYNC-01-a
- 良い例:
  `proc.launch_many(launches, parallel, run_one)`
- 悪い例:
  `execute.py` で `threading.Thread(...)`

## OPS ログ・設定・セキュリティ・表示

### OPS-01 結果は標準出力、エラーは標準エラーに出し、終了コードは 0 と 1 にする

- 軸: E5, X1
- 決定: 補助 CLI は、成功の結果を標準出力に、エラーを `エラー: ` を付けて標準エラーに出し、終了コードは成功が0、`KitError` が1（引数の誤りは argparse の2）にする。警告は出力の中の `WARN ` で始まる行にし、ログの仕組みは持たない。`status` の行は、charter・設計・バンドルの問題の一覧を除き、`status.LINE_KINDS` の書き出し（`対象:`・`段階:`・`改善のラウンド:`・`次:`・`その後:`・`問題が出たら:`・`承認なら:`・`直すなら:`・`採用なら:`・`不採用なら:`・`job `）のどれかで始め、新しい種類の行を足さない。人が決める値をコマンドに渡すときは、`status` の関数の中で、`_command` に渡す引数の文字列に `--<引数の名前> '<日本語の名前>'` を直接書き（定数や変数にしない）、配布するスキルが人の答えで置き換える。`sys.stdout`・`sys.stderr`・`sys.exit` に触れるのは `cli.py` だけにする。
- 理由: スキルは出力の `次:`・`job`・`WARN` の行を読んで動く。出力先や形が揺れると、スキルの手順が働かない
- 強制: structure, test, review — `check_side_effects` が、`cli.py` 以外の `sys.stdout`・`sys.stderr`・`sys.exit` を落とし、`tests/test_cli.py` が全体の流れの各段で `status` の行の書き出しを `status.LINE_KINDS` と突き合わせる。人が決める値の置き方はレビューで見る
- probe: OPS-01-a, OPS-01-b
- 良い例:
  `print(f"エラー: {exc.message}", file=sys.stderr)` を `cli.py` に書く
- 悪い例:
  `score.py` で `sys.stderr.write(...)`

### OPS-02 設定は charter.json だけから読み、環境変数を読まない

- 軸: E6
- 決定: 評価の設定（検査コマンド、保護パス、実行の条件、予算）は charter.json だけから読む。環境変数に触れるのは、検査コマンドに `CI=1` を渡す `proc.shell` だけにする。
- 理由: 環境変数で振る舞いが変わると、人が承認した charter と実際の評価の条件が食い違う
- 強制: structure — `check_side_effects` が、`proc.py` 以外の `os.environ`・`os.getenv`・`os.putenv` を落とす
- probe: OPS-02-a
- 良い例:
  `model.executor.max_budget_usd`
- 悪い例:
  `os.getenv("FORGE_AGENTS")`

### OPS-03 人に見せる文言は日本語で書き、表と数は render の関数で書く

- 軸: E7
- 決定: 人に見せる文言（出力、Markdown、プロンプト）は日本語で書く。表は `render.table`、数値は `render.number`（小数3桁）、費用は `render.usd`（小数2桁と `$`）、達成の判定は `render.mark`、長さがデータで決まる一覧は `render.bullets` で書く。決まった項目を並べる行（`- 対象: …`）は直接書いてよい。日付は `cli` が求める `YYYY-MM-DD` の文字列だけを使う。
- 理由: 表や数の書き方が段ごとに違うと、採点と比較と報告の表を見比べられない
- 強制: review — レビュー用スキルの確認項目
- 機械化しない理由: 文言が人に見せるものか、内部の値かは、字面では見分けられない
- probe: なし
- 良い例:
  `render.table(["id", "値"], rows)`
- 悪い例:
  `f"| {id} | {value:.2f} |"` を段のモジュールに書く

### OPS-04 評価と構築を進める段の入口は最初に承認済みの charter を読み、.claude に書くのは2つだけにする

- 軸: E8
- 決定: `ENTRIES` の表の入口の関数（`design_new`・`design_check`・`design_approve`・`build`・`bundle_check`・`install`・`prepare`・`execute`・`collect`・`score`・`analyze`・`propose`・`compare`・`decide`・`report`）は、最初の文で `workspace.approved_charter` を呼ぶ。対象のリポジトリの `.claude/` に書く `bundle.place` を呼ぶのは `building.install` と `decide.decide`（`--adopt`）だけにする。サブエージェントのプロンプトは、書いてよい場所を `.forge/` の下だけにする。
- 理由: 未承認の charter で進めると、人の確かめていない検査コマンドと `claude -p` の条件で評価が動く。`.claude/` は保護されたパスで、書く経路が散ると人の承認なしに対象スキルが変わる
- 出典: research.md の「Claude Code の権限と保護されたパス」
- 強制: structure — `check_entries` が `ENTRIES` の表の関数の最初の文を、`check_calls` が `bundle.place` を呼ぶモジュールを確かめる
- probe: OPS-04-a, OPS-04-b
- 良い例:
  `model, _sha = workspace.approved_charter(where)`
- 悪い例:
  `analyze.py` で `bundle.place(where, model.target.skill_name, proposed)`

### OPS-05 claude -p の引数は execute.command だけで組み立て、権限を広げない

- 軸: X7
- 決定: 実行役の `claude -p` の引数は `execute.command` だけで組み立て、次の表の引数を全部入れる。`bypassPermissions`・`--dangerously-skip-permissions`・`--bare` の文字列は `kit/` のどこにも書かない。
  | 引数 | 値 |
  |---|---|
  | `-p` | ひな形 `executor.md` から作ったプロンプト（`/<スキル名> <評価課題>`） |
  | `--output-format`、`--verbose` | `stream-json` |
  | `--permission-mode` | `acceptEdits` |
  | `--permission-prompts` | `none` |
  | `--no-session-persistence` | 値なし |
  | `--max-budget-usd` | charter の `executor.max_budget_usd` |
  | `--append-system-prompt-file` | ひな形 `executor-system.md` から作ったファイル |
  | `--model` | charter の `executor.model`。空なら引数ごと入れない |
  | `--allowedTools` | charter の `executor.allowed_tools`。引数の最後に置く。空なら引数ごと入れない |
- 理由: 実行役の条件が揺れると、同じスキルでも評価ごとに結果が変わる。権限を広げる引数は、人が承認していない操作を評価用のコピーの外で許しうる
- 出典: research.md の「Claude Code のヘッドレス実行（claude -p）」「Claude Code の権限と保護されたパス」
- 強制: structure, test — `check_literals` が `execute.py` の外の `"-p"` と、`kit/` の全ファイルの禁止の文字列を落とし、`tests/test_execute.py` が表の引数と順番を確かめる
- probe: OPS-05-a, OPS-05-b
- 良い例:
  `args = execute.command(model.executor, prompt, system_path)`
- 悪い例:
  `collect.py` で `["claude", "-p", prompt, "--permission-mode", "bypassPermissions"]`

## TEST テスト

### TEST-01 モジュールごとに tests/test_<モジュール>.py と <名前>Test クラスを置く

- 軸: F1, F2, F5
- 決定: `forge_kit` の各モジュール（`__init__` と `errors` を除く）と `install.py` に、`tests/test_<モジュール>.py` を1つ置き、その中に `<モジュール名の PascalCase>Test` の `unittest.TestCase` を置く。対応するモジュールの無い `test_*.py` は置かない。全体の流れ（charter から報告まで）は `tests/test_cli.py` で確かめる。
- 理由: テストの置き場と名前が揺れると、どのモジュールにテストが無いかを見つけられない
- 強制: structure — `check_tests` が、テストのファイルとクラスの有無と、対応の無いテストを落とす
- probe: TEST-01-a
- 良い例:
  `tests/test_trace.py` の `class TraceTest(unittest.TestCase):`
- 悪い例:
  `tests/test_misc.py`

### TEST-02 モックを使わず、support.py の部品と本物の git で確かめる

- 軸: F3, F4
- 決定: テストは `unittest.mock` を使わない。見本のリポジトリは `support.make_repo` で `tests/fixtures/sample-repo/` を一時ディレクトリに写し、実行役は `support.fake_launcher`（`tests/fixtures/streams/` の記録を返し、コピーのファイルを書き換える偽の起動関数）で置き換え、サブエージェントの出力は `support` の `act_*` と `grade_all` で書き、git とシェルは本物を使う。
- 理由: モックは、git やファイルの実際の振る舞い（コミット後の差分、シンボリックリンク）との食い違いを隠す。`claude -p` を本当に起動すると、テストが遅く、費用がかかり、結果が揺れる
- 強制: structure — `check_tests` が `tests/` の `unittest.mock` と `mock` の import を落とす
- probe: TEST-02-a
- 良い例:
  `execute.execute(where, slot, support.fake_launcher())`
- 悪い例:
  `with mock.patch("forge_kit.proc.launch"):`

### TEST-03 新しい名前を足したら、その値を作る段のテストに test_<名前> を1つ足す

- 軸: F2, F5
- 決定: 依頼で新しい名前を足したら、その名前の振る舞いを確かめるメソッド `test_<足した名前>` を1つ足す。名前ごとの置き場は次の表のとおりにし、他のテストのファイルに同じ名前のメソッドを作らない。全体の流れで確かめたいことは、`tests/test_cli.py` の既存のメソッドに assert を足す。人が読む版（charter.md、design.md）に出す項目を足したら、`tests/test_views.py` の既存のメソッドに assert を足す。名前を足さない変更（不具合の修正、文言の修正）は、直した関数を確かめている既存のメソッドに assert を足し、そのメソッドが無ければ `test_<直した関数の名前>` を足す。
  | 足した名前 | 置き場 | メソッドの例 |
  |---|---|---|
  | 指標の id | `tests/test_score.py` | `test_delegation` |
  | バンドルの決まりの id | `tests/test_bundle.py` | `test_b10` |
  | ひな形の置き換えの名前 | 値を作る段のテスト（`test_designing.py`、`test_building.py`、`test_prepare.py`、`test_collect.py`、`test_analyze.py` のどれか） | `test_skill_md` |
  | サブコマンドか、その引数 | 引数を受け取る段のテスト | `test_feedback` |
  | charter の項目 | `tests/test_charter.py` | `test_max_budget_usd` |
  | 設計の項目 | `tests/test_design.py` | `test_checkpoints` |
  | 実行の記録から読む項目 | `tests/test_trace.py` | `test_spawn_depth` |
  | 段とサブエージェントが受け渡す JSON（`contracts`）の項目 | `tests/test_contracts.py` の、その JSON を読む関数の `test_parse_<名前>`（あれば assert を足す） | `test_parse_grade` |
  | モジュールに足した公開の関数（`_` で始まらない名前） | そのモジュールのテスト | `test_<関数名>` |
- 理由: テストのメソッド名を作者が文で付けると、同じ確認に別の名前が付き、どのテストが何を守っているかを探せない
- 強制: review — レビュー用スキルの確認項目
- 機械化しない理由: どの名前が依頼で足したものかは、差分の意味の判断が要る
- probe: なし
- 良い例:
  `execute` に引数 `--only` を足し、`tests/test_execute.py` に `def test_only(self) -> None:` を足す
- 悪い例:
  `test_only_runs_selected` と `test_only_skips_others` のように、同じ確認に文の名前を付ける

## PROC 作業手順

### PROC-01 段を足すときは契約から入口の順に作る

- 軸: G1
- 決定: 段を足すときは、(1) `contracts` と `layout` に受け渡しの形と置き場を足し、(2) 段のモジュールを書き、(3) `status` に次の手を足し、(4) `cli` にサブコマンドを足し、(5) テストを書き、(6) 段を使うスキル（forge-goals、forge-build、forge-run のどれか）の表を直す、の順に作る。
- 理由: 入口から作ると、受け渡しの形が後から変わり、作り直しが増える
- 強制: doc — 実装用スキルの「作る順序」
- 機械化しない理由: 作る順序は、出来上がった差分に痕跡が残らない
- probe: なし
- 良い例:
  `contracts.Comparison` を足してから `compare.py` を書く
- 悪い例:
  `cli.py` に引数を足してから、受け渡しの形を考える

### PROC-02 波及の対応表の組は一緒に変える

- 軸: G2
- 決定: 次の表の左を変えたら、同じ変更で右も変える。「charter のキー」「設計のキー」はキーの名前・形・値の決まりを指す。既存のキーの値を別の段で使うだけなら、スキーマの文書とスキルは変えない。architecture.md のデータの流れは、段が読み書きするファイルの単位で書く。既存のファイルに項目を足すだけなら、データの流れの行がそのファイルの中身を書いていても変えない。
  | 変えるもの | 一緒に変えるもの |
  |---|---|
  | `catalog.METRICS` | `score.CALCULATORS`、`make docs`（指標の一覧） |
  | `bundle.RULES` | `tests/test_bundle.py` の `test_<id の小文字>`、`make docs`（バンドルの決まり） |
  | `prompts.TEMPLATES` | `kit/.forge/templates/prompts/` のひな形 |
  | `contracts.AGENTS` | `kit/claude/agents/` の定義、そのエージェントを起動するスキルの表 |
  | charter のキー | `forge-goals/references/charter-schema.md` の表と例 |
  | 人が決める charter のキー（ひな形の既定値のまま使わず、人に値を決めてもらうキー） | `forge-goals/SKILL.md` の、そのキーを決める手順の表（`environment` は手順7の表、`executor` と `budget` は手順8の表）。聞き方は「## 人に確かめること」の値の種類に従う（PROC-07） |
  | 設計のキー | `forge-build/references/design-schema.md` の表と例 |
  | `layout` の置き場 | `docs/design/architecture.md` のデータの流れ |
  | `status` の次の手 | 段を使うスキルの「繰り返すこと」の表 |
  | `forge_kit` のモジュールの増減 | `structure_check.py` と `architecture.md` の許可表 |
- 理由: 片方だけ変えると、補助 CLI とスキル、または計算と文書が食い違う
- 強制: test, review — `tests/test_score.py` が `CALCULATORS` と `catalog.METRICS` の一致を、`tests/test_charter.py` と `tests/test_design.py` がスキーマの文書の例の検証を確かめ、残りの組はレビューで見る
- probe: PROC-02-a
- 良い例:
  `catalog.METRICS` に指標を足し、`CALCULATORS` に関数を足し、`make docs`
- 悪い例:
  `catalog.METRICS` にだけ指標を足す

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

### PROC-06 charter と設計の形を変えたら SCHEMA_VERSION を上げる

- 軸: X2
- 決定: charter.json か design.json のキーを足す・消す・意味を変えるときは、`charter.SCHEMA_VERSION` か `design.SCHEMA_VERSION` を1上げ、ADR に移行の手順（古いファイルの直し方）を書く。補助 CLI とサブエージェントが受け渡す JSON（plan.json、grade.json、proposal.json の形）は、ひな形と同じ変更で変えるので版を持たない。版を持たない JSON のうち `.forge/targets/` に残る記録（`.forge/targets/` の下の、charter.json と design.json 以外の JSON 全部）に項目を足すときは、項目の無い古い記録を既定値で読む（`shape.text(root, "<キー>", "", problems) if "<キー>" in root else ""` の形）。
- 理由: 配布先には人が承認した charter と設計が残る。形を黙って変えると、承認済みのファイルが検査で落ちる理由が分からない
- 強制: review — レビュー用スキルの確認項目
- 機械化しない理由: キーの意味が変わったかどうかは、字面では判定できない
- probe: なし
- 良い例:
  キーを足し、`SCHEMA_VERSION = 2` にして ADR を書く
- 悪い例:
  `SCHEMA_VERSION = 1` のままキーの意味を変える

### PROC-07 人が決める場面は SKILL.md に書き、値の種類で聞き方を分ける

- 軸: X5
- 決定: 配布するスキルには `## 人に確かめること` の節を置き、次の表の場面で人に決めてもらう。聞き方は値の種類で次の決定表のとおりにする。
  | スキル | 人が決める場面 |
  |---|---|
  | forge-goals | 目的、ゴール、指標と閾値と priority、評価課題と受け入れ条件、環境、実行の条件、予算、charter の承認 |
  | forge-build | 設計を承認するか直してほしいこと、下書きのバンドルを入れるか直してほしいこと |
  | forge-run | 各ラウンドの候補を採るか |

  | 値の種類 | 聞き方 |
  |---|---|
  | 選ぶ値（指標、閾値、priority、予算、承認、採否） | AskUserQuestion。あなたの案を先頭の選択肢にし、名前の末尾に `（推奨）` を付ける |
  | 人の言葉を残す値（`purpose`、ゴールの `statement`、評価課題の `prompt` と `acceptance`、`--feedback` の値） | AskUserQuestion を使わずに文章で聞き、返ってきた文をそのまま使う。あなたの案で埋めない |
- 理由: サブエージェントと `claude -p` の実行役は人に聞けない。人に聞く場面をメインのセッションのスキルに書かないと、エージェントが自分で決めて進める。人の言葉を残す値にエージェントの案を選ばせると、人のゴールではなくエージェントのゴールが charter に入る
- 出典: research.md の「Claude Code のサブエージェント」
- 強制: structure — `check_skills` が、節と AskUserQuestion の記述の有無を確かめる
- probe: PROC-07-a
- 良い例:
  `## 人に確かめること` の下に、採否を AskUserQuestion で人が決めると書く
- 悪い例:
  推奨が「採用」なら、そのまま `decide --adopt` を実行すると書く

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
  `def  spaced( value:float )->float:`

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
