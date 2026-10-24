# skill-harness2-kit のルール

このファイルは skill-harness2-kit のルールの正本である。AGENTS.md・スキル・レビューの指摘・検査のエラーは、ここのルールIDを参照する。ルールの変更手順は AGENTS.md の「ルールを変えたいとき」に従う。

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

harness2 の用語は、この基盤では次のように読み替える。対応の根拠は research.md の「harness2 の仕組み」の表にある。

| 用語 | 意味 |
|---|---|
| 対象スキル | 改善する、利用者のリポジトリの Claude Code スキル1つ。harness2 の harness に当たる |
| スキルの木 | 対象スキルのディレクトリの中身（`SKILL.md`、`references/`、`scripts/`、`assets/`）。`skilltree.SkillTree` |
| 補助 CLI | `kit/.h2/h2.py` と `h2_kit` パッケージ。配布先では `.h2/h2.py` |
| 対象（target） | 1つの対象スキルを改善するための作業場所 `.h2/targets/<target>/`。`profile.json`、`tasks/`、`approval.json`、`runs/` を持つ |
| プロファイル | `profile.json`。仕事の説明、k、モード、モデル、予算を書く。harness2 の BenchPrompts と BenchSpec に当たる |
| タスク | `tasks/<id>/task.md`（依頼文）と `tasks/<id>/workspace/`（作業の材料）。`tasks/<id>/checks.json` は事後の検査だけが読む |
| 実行（rollout） | 1つのスキルの木を入れた使い捨ての作業場所（sandbox）で、`claude -p` にタスクを1回解かせること |
| 基準の実行 | 承認時のスキル（H0）の実行 `base1`〜`base<k>`。正否ではなく振る舞いの証拠 |
| 編集のセッション | 証拠を読んでスキルの木を直す `claude -p` の1回。提案（`inv<i>`、`dom<i>`）と合成（`agg<i>`、`c<t>`） |
| INV と DOM | 提案の2つの次元。INV は「どう働くか」（手順、道具、完了の確かめ方）、DOM は「実務家が何を知っているか」 |
| 合成（compose） | 候補と証拠を読み、根拠のある編集だけを1つの木にまとめる段。KEEP_BASE（元のまま）も答え |
| 完成品（final） | モードの最後の木。並列モードは `agg1`〜`agg<k>`、逐次モードは `c1`〜`c<k>` |
| 選択 | 完成品の実行の成果物だけを、匿名の ID で比べて1つを選ぶ段 |
| 振り返り | 選ばれた木の編集ごとの効果と、次のタスクへ移す教訓を1つだけ書く段 |
| ライブラリ | 前のタスクで選ばれた木と教訓。`runs/r<N>/library/<モード>/` |
| ラウンド | 1回の承認と、それに続く `run`・`show`・`adopt`・`judge`。`runs/r<N>/` |
| 台帳（ledger） | 1つのタスク・モードの実行と編集のセッションの記録。実行 R = 4k、セッション P = 3k の恒等式で確かめる |
| 事後の検査（judge） | 選択の後に `checks.json` のコマンドで成果物を確かめること。方法（提案・合成・選択）には使わない |
| 段 | 補助 CLI の1つのサブコマンドが受け持つ処理 |
| 段のモジュール | 段を実装するモジュール（`planning`、`status`、`execution`、`results`、`adoption`、`judging`） |
| 共有のモジュール | 2つ以上の段か方法が使うモジュール（architecture.md の許可表の「共有」の行） |

## 追加した軸

カタログに無い、この分野に固有の軸を定義する。X1 と X2 は domain-profiles.md の cli-library の軸である。

| 軸 | 内容 | 置く節 |
|---|---|---|
| X1 | 終了コードと出力の形式（標準出力と標準エラーの使い分け、status の行の書き出し） | OPS |
| X2 | 公開する形の互換性（profile.json と tasks の形を変えるときの手順） | PROC |
| X3 | 配布するスキルの書式（frontmatter、行数、参照ファイル） | STR |
| X4 | モデルとの受け渡し（プロンプトのひな形、返答のタグ、証拠の渡し方） | STATE |
| X5 | 人の関所（承認と採用で人が決める場面） | PROC |
| X6 | 答えを使わないこと（測定の分離と選択の盲検） | STATE |
| X7 | 候補の検証と差し戻し | STATE |
| X8 | 予算の恒等式 | STATE |
| X9 | セッションの閉じ込め（`claude -p` のコマンド行） | OPS |

## STR 配置と構造

### STR-01 ファイルは表の場所に置き、表に無い場所を作らない

- 軸: A1, A5, A6
- 決定: ファイルは次の表の場所に置く。
  | 置くもの | 場所 |
  |---|---|
  | 補助 CLI の入口 | `kit/.h2/h2.py` |
  | 補助 CLI のモジュール | `kit/.h2/h2_kit/<モジュール>.py`（サブディレクトリを作らない） |
  | プロンプトのひな形 | `kit/.h2/templates/prompts/<名前>.md` |
  | 配布先の除外設定 | `kit/.h2/.gitignore` |
  | 配布するスキル | `kit/claude/skills/skill-harness2/SKILL.md`、`kit/claude/skills/skill-harness2/references/<名前>.md` |
  | 配布物を入れるスクリプト | `install.py` |
  | 構造検査 | `scripts/structure_check.py` |
  | テスト | `tests/__init__.py`、`tests/support.py`、`tests/test_<名前>.py` |
  | テストの偽物と見本データ | `tests/fixtures/` の下 |
  | 上のどれでもない | 置かない。場所が要るならルールの変更として提案する |
- 理由: 配布物（`kit/`）に置いた物は全部が利用者のリポジトリへ写る。置き場が人ごとに分かれると、写るべき物が漏れたり、開発用の物が配られたりする
- 強制: structure — `scripts/structure_check.py` の `LAYOUT` 表が `kit/` と `tests/` の全ファイルのパスを照合する
- probe: STR-01-a
- 良い例:
  kit/.h2/h2_kit/ledger.py
  tests/test_ledger.py
- 悪い例:
  kit/.h2/h2_kit/method/ledger.py
  kit/.h2/helpers.py

### STR-02 モジュールは構造検査の表に登録し、置き場を決定表で決める

- 軸: A2, A3, A4
- 決定: `h2_kit` のモジュールは `scripts/structure_check.py` の `SHARED`・`STAGES`・`ENTRY` のどれか1つに登録し、関数の置き場は次の表で決める。
  | 関数を使うモジュール | 置き場 |
  |---|---|
  | 1つのモジュールだけ | そのモジュール。名前を `_` で始める |
  | 2つ以上のモジュール | 共有のモジュール（architecture.md の役割の表に合うもの。合うものが無ければ共有のモジュールを足す） |
  | 上のどれでもない（`cli` だけ） | `cli` |
- 理由: 新しいモジュールや関数の置き場が人ごとに分かれると、段どうしの依存が生まれ、1つの変更で触るファイルが予測できなくなる
- 強制: structure, review — 登録の無いモジュールは構造検査が落とす。関数の置き場はレビューで確かめる
- probe: STR-02-a
- 良い例:
  SHARED = {"errors": frozenset(), "layout": frozenset(), ...}  # 新しいモジュールを1行足す
- 悪い例:
  # recursion.py と selection.py の両方に同じ _build_pool() を写す

### STR-03 入口は h2.py と cli.main の2つだけにする

- 軸: A7
- 決定: 補助 CLI の入口は `kit/.h2/h2.py`（`cli.main` を呼ぶだけ）と `cli.main` の2つにし、`h2_kit/__init__.py` は docstring だけにし、`h2_kit` のモジュールに `if __name__ == "__main__":` を書かない。
- 理由: 入口が複数あると、スキルがどれを呼ぶかで揺れ、承認の確認（OPS-04）を通らない呼び方が生まれる
- 強制: structure — `__init__.py` の中身と `__main__` の判定を構造検査が照合する
- probe: STR-03-a
- 良い例:
  sys.exit(cli.main(sys.argv[1:], Path(__file__).resolve().parent.parent))
- 悪い例:
  if __name__ == "__main__":
      print(status.status(...))

### STR-04 配布するスキルは決まった frontmatter で書き、参照ファイルを本文から名指しする

- 軸: X3
- 決定: `kit/claude/skills/skill-harness2/SKILL.md` の frontmatter は `name: skill-harness2`、`description`、`disable-model-invocation: true`、`allowed-tools: Bash(python3 .h2/h2.py *)`、`argument-hint` の5つだけにし、SKILL.md は500行以内、`references/` は1階層にし、`references/` の全ファイルを SKILL.md の本文に `references/<名前>.md` の形で書く。
- 理由: 改善の実行は費用がかかるため、人が `/skill-harness2` で呼んだときだけ動かす。本文から名指しされない参照ファイルは読まれない（harness2 の「起動の行の無いスキルは死んだ部品」と同じ）
- 出典: research.md の「Claude Code のスキル 2.1.308」
- 強制: structure — 構造検査が frontmatter、行数、参照ファイルの名指しを照合する
- probe: STR-04-a, STR-04-b
- 良い例:
  disable-model-invocation: true
  allowed-tools: Bash(python3 .h2/h2.py *)
- 悪い例:
  # disable-model-invocation を書かず、references/extra.md を本文で名指ししない

## DEP 境界と依存

### DEP-01 import は許可表の組だけにし、段のモジュールどうしは import しない

- 軸: B1, B3
- 決定: `h2_kit` のモジュールは architecture.md の依存の許可表にある組だけを import し、段のモジュールは他の段のモジュールを import せず、段のモジュールを import してよいのは `cli` だけにする。
- 理由: 段どうしが依存すると、1つの段の変更が他の段を壊す。事後の検査（`judging`）を方法のモジュールが import すると、測定が選択に混ざる（STATE-04）
- 強制: structure — `scripts/structure_check.py` の `SHARED`・`STAGES`・`ENTRY` の表で import を照合する
- probe: DEP-01-a
- 良い例:
  from h2_kit import fsops, layout, render, workspace  # results.py
- 悪い例:
  from h2_kit import judging  # selection.py から事後の検査を呼ぶ

### DEP-02 他のモジュールの _ で始まる名前を使わない

- 軸: B2
- 決定: モジュールの外から使ってよいのは `_` で始まらない名前だけにし、`<モジュール>._<名前>` と `from h2_kit.<モジュール> import _<名前>` を書かない。
- 理由: 内部の名前を外から使うと、モジュールの中を直しただけで別のモジュールが壊れる
- 強制: structure — 構造検査が属性の参照と import を照合する
- probe: DEP-02-a
- 良い例:
  fsops.write_json(path, data)
- 悪い例:
  fsops._encode(data)

### DEP-03 Python 3.9 の標準ライブラリと h2_kit だけを import する

- 軸: B4, B6
- 決定: `kit/`、`scripts/`、`tests/`、`install.py` が import してよいのは、`scripts/structure_check.py` の `STDLIB` 表にある標準ライブラリと `h2_kit` だけにし、依存ライブラリを足さない。
- 理由: 配布物は利用者のリポジトリでそのまま動く必要があり、依存を足すと導入の手順が利用者ごとに分かれる
- 出典: research.md の「Python 3.9.6」
- 強制: structure — 構造検査が import を `STDLIB` 表と照合する
- probe: DEP-03-a
- 良い例:
  import hashlib
- 悪い例:
  import yaml

### DEP-04 副作用に触れるモジュールを表の4つに限る

- 軸: B5
- 決定: 副作用は次の表のモジュールだけで扱う。
  | 副作用 | 書いてよいモジュール | 検査する書き方 |
  |---|---|---|
  | ファイルの書き込み・削除・コピー、一時ディレクトリ | `fsops` | `write_text`、`write_bytes`、`open(`、`shutil`、`tempfile`、`mkdir`、`unlink`、`rmtree` |
  | 外部コマンド | `proc` | `subprocess` |
  | スレッド | `parallel` | `threading`、`concurrent` |
  | 時刻、画面への出力、終了コード | `cli` | `datetime`、`time`、`print`、`sys.exit` |
- 理由: 副作用が散らばると、テストで一時ディレクトリの外を書き換えたり、`status` が作業場所を変えたりする事故を防げない
- 強制: structure, lint — 構造検査が書き方を照合する。`print` は ruff の `T201` でも落とす
- probe: DEP-04-a, DEP-04-b
- 良い例:
  fsops.write_json(place.summary_path(mode), workspace.build_json(summary))  # execution.py
- 悪い例:
  place.summary_path(mode).write_text(json.dumps(data))  # execution.py

## NAM 命名

### NAM-01 名前のケースは PEP 8 に従う

- 軸: C1, C2, C6
- 決定: モジュール・関数・変数は snake_case、クラスは PascalCase、モジュールの定数は UPPER_SNAKE_CASE にし、略語も同じ規則で書く（`task_id`、`TaskId` は使い、`TaskID` は使わない）。
- 理由: ケースが人ごとに分かれると、同じものに2つの名前が生まれ、検索で漏れる
- 出典: research.md の「ruff 0.17.2」
- 強制: lint — ruff の `N801`、`N802`、`N806`、`N815`
- probe: NAM-01-a
- 良い例:
  def compute_diversity(trees: list[SkillTree]) -> float:
- 悪い例:
  def computeDiversity(trees):

### NAM-02 関数名は動詞表の語で始め、段の公開関数はサブコマンド名にする

- 軸: C3, C4, C5
- 決定: 段のモジュールの公開関数はサブコマンド名にし、それ以外のモジュール直下の関数は、`_` で始まる関数も同じく、次の動詞表の語で始める（`_` の次の語を照合する。クラスのメソッドと関数の中の関数は対象外）。
  | 語 | 使う場面 |
  |---|---|
  | `load` | 作業場所のファイルを読み、検証済みの型で返す |
  | `read` | ファイルやディレクトリをそのまま読む |
  | `parse` | 辞書や返答の文を検証して型にする（問題を全部集める） |
  | `build` | パス・値・行・コマンド行を組み立てる（副作用なし） |
  | `render` | Markdown や表示の文字列を作る |
  | `write`、`copy`、`remove` | ファイルを書く・写す・消す |
  | `run` | 外部コマンドかセッションか段の流れを動かす |
  | `compute` | 指標・順番・ハッシュ・指紋を計算する |
  | `check` | 検査して問題の一覧を返す |
  | `find` | 一覧から1つ探し、無ければ `None` を返す |
  | `list` | 一覧を返す |
  | `is`、`has` | 真偽値を返す |
  | `require` | 条件を満たさなければ例外を投げ、満たせば次に使う値を返す |
  | `main` | 入口 |
- 理由: 同じ意味の動詞（get、fetch、load）が混ざると、関数が副作用を持つか、検証済みかを名前から判断できなくなる
- 強制: structure — 構造検査が関数名の先頭の語を表と照合する
- probe: NAM-02-a
- 良い例:
  def load_profile(where: layout.Layout) -> profile.Profile:
- 悪い例:
  def get_profile(where):

### NAM-03 JSON のキーは snake_case にし、dataclass のフィールド名と同じにする

- 軸: C7
- 決定: `profile.json`・`approval.json`・`checks.json`・補助 CLI が書く JSON のキーは snake_case にし、`profile.py`・`workspace.py`・`judging.py` で読むキーは、そのモジュールの dataclass のフィールド名と同じ綴りにする（配列を包むだけのキーは `scripts/structure_check.py` の `WRAPPER_KEYS` に登録する）。
- 理由: キーとフィールド名が食い違うと、変換の場所が増え、プロファイルを書くエージェントがどちらの綴りで書くかで揺れる
- 強制: structure — 構造検査が `KEY_MODULES`（`profile`・`workspace`・`judging`）の `.get("…")` と `["…"]` のキーを照合する
- probe: NAM-03-a
- 良い例:
  obs_trunc=_read_int(data.get("obs_trunc"), "obs_trunc", ...)
- 悪い例:
  obs_trunc=_read_int(data.get("obsTrunc"), "obsTrunc", ...)

## CODE 書き方

### CODE-01 データは継承しない frozen の dataclass にし、引数を変えない

- 軸: D1, D5
- 決定: `h2_kit` のクラスは `@dataclass(frozen=True)` で基底クラスを持たないものと、`errors.py` の例外だけにし、関数は引数のリスト・辞書を書き換えずに新しい値を返す（例外は、`_read_*` と `_parse_*` が引数の `problems` に問題を足すことだけ。問題を全部集める ERR-02 のため）。
- 理由: 可変のデータを共有すると、ある段が書き換えた値を別の段が読み、結果がファイルの中身と食い違う。並行の実行（ASYNC-01）では書き換えが競合する
- 強制: structure, review — クラスの形は構造検査が照合する。引数を書き換えないことはレビューで確かめる
- probe: CODE-01-a
- 良い例:
  @dataclass(frozen=True)
  class Stage:
      label: str
- 悪い例:
  class Stage:
      def __init__(self, label): self.label = label

### CODE-02 import は from h2_kit import <モジュール> にし、先頭に annotations を書く

- 軸: D2
- 決定: `h2_kit` のモジュールは `from h2_kit import <モジュール>` で import して `<モジュール>.<名前>` で使い、名前を直接 import してよいのは `from h2_kit.errors import <例外>` だけにし、全モジュールの docstring の次の文を `from __future__ import annotations` にする。
- 理由: 名前を直接 import する書き方と混ざると、どのモジュールの名前かが読めなくなり、DEP-01 の照合も漏れる
- 出典: research.md の「Python 3.9.6」
- 強制: structure, lint — 構造検査が import の形と先頭の文を照合する。相対 import は ruff の `TID252`、並びは `I001` で落とす
- probe: CODE-02-a, CODE-02-b
- 良い例:
  from h2_kit import layout, skilltree
  from h2_kit.errors import StageError
- 悪い例:
  from h2_kit.skilltree import SkillTree
  from . import layout

### CODE-03 型注釈を全部に書き、mypy の strict を通す

- 軸: D3
- 決定: 全関数の引数と戻り値に型注釈を書き、`mypy --strict`（`python_version = 3.9`）を通し、`Any` を書かず、外から来る値は `object` で受けて `profile.py`・`contracts.py`・`transcript.py`・`workspace.py` で型を確かめる。
- 理由: 型の無い値が段をまたぐと、JSON や返答の形の誤りが遠くの段で初めて表に出る
- 出典: research.md の「mypy 1.20.2」
- 強制: type — `make typecheck`（mypy strict）
- probe: CODE-03-a
- 良い例:
  def parse_profile(data: object) -> tuple[Profile | None, list[str]]:
- 悪い例:
  def parse_profile(data):

### CODE-04 関数の大きさは ruff の上限に収める

- 軸: D4, D6
- 決定: 関数は複雑度10以下（`C901`）、引数6以下（`PLR0913`）、分岐12以下（`PLR0912`）、文50以下（`PLR0915`）、return 6以下（`PLR0911`）、1行120文字以下（`E501`）に収め、超えたら `_` で始まる関数に分けるか、引数を frozen の dataclass にまとめる。
- 理由: 大きな関数は直す人ごとに分け方が変わり、差分が大きくなる
- 強制: lint — `pyproject.toml` の `[tool.ruff.lint]` の上限
- probe: CODE-04-a
- 良い例:
  def run_stage(spec: StageSpec, env: Env) -> Stage:
- 悪い例:
  def run_stage(label, dim, job, fallback, ctx_dir, task, rollouts, harness_dir): ...

### CODE-05 モジュールの docstring は必須にし、コメントアウトしたコードを残さない

- 軸: D7
- 決定: 全モジュールの先頭に役割を1文で書いた docstring を置き、コメントは「なぜ」だけを書き、コメントアウトしたコードを残さない。
- 理由: 役割の書かれていないモジュールには、関係の無い関数が足されていく。古いコードのコメントは、どちらが正しいかの迷いを生む
- 強制: lint, review — ruff の `D100`、`D104`、`ERA001`。コメントが「なぜ」かはレビューで確かめる
- probe: CODE-05-a
- 良い例:
  """1つのタスク・モードの実行とセッションを数え、R = 4k、P = 3k を確かめる。"""
- 悪い例:
  # total = 3 * k
  total = ROLLOUTS_PER_K * k

### CODE-06 ファイル名・ラベル・モードの文字列は layout の定数で持つ

- 軸: D8
- 決定: ファイル名とディレクトリ名の文字列（`.json`・`.md`・`.jsonl` で終わるもの）と、ラベルの接頭辞（`base`、`inv`、`dom`、`agg`、`c`）とモード名（`parallel`、`sequential`）は `layout.py` の定数に置き、他のモジュールは定数を参照する（ひな形の名前は `prompts.TEMPLATES` の表に置く）。
- 理由: 同じファイル名やラベルを複数の場所に書くと、名前を変えたときに片方が残り、`status` と段が別のファイルを見る。台帳（STATE-07）はラベルの綴りで数えるので、綴りの揺れが予算の確かめを壊す
- 強制: structure — 構造検査が `layout.py` 以外の、ファイル名で終わる文字列とラベル・モード名の文字列を照合する
- probe: CODE-06-a
- 良い例:
  place.mode_dir(mode) / layout.SUMMARY_FILE
  layout.build_label(layout.AGG, index)
- 悪い例:
  place.mode_dir(mode) / "summary.json"
  f"agg{index}"

## ERR エラーと入力検証

### ERR-01 投げる例外は errors.py の5つだけにし、捕まえる場所を限る

- 軸: E1
- 決定: 投げる例外は `errors.py` の `KitError`、`InvalidFileError`、`StageError`、`CommandError`、`LeakError` だけにし、`except` を書いてよいのは次の表の場所だけにする。
  | モジュール | 捕まえてよいもの | 捕まえた後 |
  |---|---|---|
  | `cli` | `KitError`（`main` の中だけ） | `エラー: ` を付けて標準エラーに出し、終了コード 1 |
  | `fsops` | `OSError`、`FileNotFoundError`、`UnicodeDecodeError`、`json.JSONDecodeError` | `InvalidFileError` か `KitError` にして投げ直す。`read_text_or_none` は `None`、`remove_file` は消す物が無ければ何もしない |
  | `proc` | `OSError`、`subprocess.TimeoutExpired` | 起動の失敗は `CommandError` にして投げ直し、時間切れは `timed_out` の結果として返す |
  | `transcript` | `json.JSONDecodeError` | その行を `[ERROR]` の行として軌跡に残す |
  | `validate` | `SyntaxError`、`ValueError` | `compile` の失敗を候補の問題の1行にする |
  | `status` | `KitError` | `問題:` の行に出し、`次:` の行で直し方を示す |
  | `recursion` | `CommandError`、`InvalidFileError`、`LeakError` | その段を入力の木に戻す（fell_back） |
  | `selection` | `CommandError`、`InvalidFileError` | 中立の候補に戻す（fallback） |
  | `reflection` | `CommandError`、`InvalidFileError` | 教訓を書かない |
  | `judging` | `CommandError` | 結果を `None`（未判定）にする |
  | 上のどれでもない | 書かない | — |
- 理由: 例外の種類と捕まえる場所が散らばると、利用者に見せるエラーの形が揺れ、思わぬ例外が握りつぶされる。harness2 は「段の失敗は入力に戻して記録し、投げない」「採点の失敗は 0 点ではなく None」と、捕まえた後の扱いを決めている。`claude` を起動できないことは設定の誤りなので、捕まえずに `cli` まで伝える
- 出典: research.md の「harness2 の仕組み」
- 強制: structure, lint — 構造検査が `raise` と `except` を照合する。広い `except` は ruff の `BLE001` で落とす
- probe: ERR-01-a, ERR-01-b
- 良い例:
  raise StageError("承認がありません。check を見せてから approve を実行してください")
- 悪い例:
  raise ValueError("bad")
  except Exception: pass

### ERR-02 外から来る JSON は workspace の load_* で検証してから使う

- 軸: E2
- 決定: `profile.json`・`approval.json`・`checks.json`・補助 CLI が書いた `run.json`・`summary.json` は `workspace` の `load_*` 関数だけで読み、`load_*` は `fsops.read_json` の結果を `profile.parse_*` か `workspace` の中の `_parse_*` に渡して問題を全部集め、問題があれば `InvalidFileError` を投げる。
- 理由: 段ごとに JSON を読むと、検証の漏れた形のまま値が使われ、遠くの段で分かりにくいエラーになる
- 強制: structure — 構造検査が `fsops.read_json` の呼び出しを `workspace` だけに、`json.loads` を `fsops` と `transcript` だけに限る
- probe: ERR-02-a
- 良い例:
  summary = workspace.load_summary(place, mode)
- 悪い例:
  summary = fsops.read_json(place.summary_path(mode))  # results.py

## STATE 状態とデータの流れ

### STATE-01 状態はファイルだけで持ち、進み具合は workspace が求める

- 軸: E3
- 決定: 進み具合を書いた状態ファイルを作らず、`workspace` が完了の記録（実行の `run.json`、モードの `summary.json`）の有無と指紋から進み具合を求め、`workspace` と `status` は `fsops` の `read_`・`list_`・`compute_` で始まる関数だけを呼ぶ。
- 理由: 状態ファイルとファイルの実体は食い違いうる。完了の記録から求めれば、途中で止まっても `run` が続きから再開し、`status` が正しい次の手を示す（harness2 の完了の印と同じ）
- 出典: research.md の「harness2 の仕組み」の「やり直しと再現」
- 強制: structure, review — 構造検査が `workspace`・`status` の `fsops` の呼び出しを照合する。状態ファイルを足していないかはレビューで確かめる
- probe: STATE-01-a
- 良い例:
  progress = workspace.compute_progress(where, approved)  # status.py
- 悪い例:
  fsops.write_json(where.target_dir / "state.json", {"stage": "run"})

### STATE-02 モデルとの受け渡しはひな形と決めたタグだけで行う

- 軸: X4
- 決定: 編集・選択・振り返りのセッションへのプロンプトは `prompts.render_prompt` で `templates/prompts/` のひな形から作り、ひな形の置き換えの名前は `prompts.TEMPLATES` の表と一致させ、返答のタグ（`<notes>`、`<why>`、`choice` の囲み、`KEEP_BASE`、`NO_ENTRY`）の文字列は `contracts.py` だけに書き、編集の結果は返答の文ではなく作業場所の `context/harness/` から読む。
- 理由: プロンプトの文を Python に書くと、文言の修正が段のモジュールに散らばる。返答の文から編集を読み取ると、書式の揺れで編集が失われる（harness2 は「ディスクの編集がそのまま提案」で受け渡しを1つにしている）
- 出典: research.md の「harness2 の仕組み」の「編集の受け渡し」
- 強制: structure, test — 構造検査がタグの文字列を `contracts.py` 以外で照合する。`tests/test_prompts.py` がひな形と表の一致を確かめる
- probe: STATE-02-a, STATE-02-b
- 良い例:
  text = prompts.render_prompt("propose-inv", values)
  notes = contracts.parse_notes(reply.text)
- 悪い例:
  text = f"次のスキルを直してください: {tree}"
  re.search(r"<notes>(.*)</notes>", reply)  # recursion.py

### STATE-03 証拠はファイルで全部渡し、プロンプトは道案内だけにする

- 軸: X4
- 決定: 編集のセッションには `context/` の下に task.md、材料、全実行の軌跡、成果物、編集するスキルの木、候補、ライブラリをファイルとして置き、プロンプトには仕事と証拠の場所だけを書き、軌跡は全文を書き、1つの観測の切り詰めは `profile.MIN_OBS_TRUNC`（10,000字）以上の `obs_trunc` でだけ行う。
- 理由: 証拠をプロンプトに詰めると切り詰めが起き、編集者が切り詰めを欠陥と取り違える（harness2 は 10,000 字未満を「欠陥をでっち上げる範囲」として拒む）
- 出典: research.md の「harness2 の仕組み」の「証拠を切り詰めない」
- 強制: test, review — `tests/test_profile.py` が `obs_trunc` の下限を、`tests/test_context.py` が証拠の木の中身を確かめる。プロンプトに証拠を埋め込んでいないかはレビューで確かめる
- probe: STATE-03-a
- 良い例:
  values = {"layout": built.layout_text, ...}  # 証拠の場所の一覧だけを渡す
- 悪い例:
  values = {"trajectory": trajectory_text[:2000], ...}

### STATE-04 方法は答えを見ず、事後の検査は選択の後にだけ動かす

- 軸: X6
- 決定: 次の4つを守る。
  | 守ること | 仕組み |
  |---|---|
  | プロファイルの方法に渡す文（`work`、`inv_levers`、`dom_levers`、`yardstick`、`selection_checks`）に `guards.MEASUREMENT_WORDS` の語を書かない | `profile.parse_profile` が問題にする |
  | 証拠の木と候補のスキルの木に `guards.GRADER_MARKERS` の文字列と `leak_globs` に当たるパスを入れない | `guards.require_clean_*` が `LeakError` を投げる |
  | `checks.json`（`layout.CHECKS_FILE` と `Layout.checks_path`）に触れるのは `judging` と `planning` だけにする | 構造検査 |
  | 事後の検査（`judging`）は `cli` からだけ呼び、方法のモジュールは import しない | DEP-01 |
  | 方法のモジュール（`execution`、`recursion`、`selection`、`reflection`、`context`、`rollout`、`library`、`prompts`、`runner`、`sandbox`）は、名前（小文字にしたもの）の中に `judg` がある属性を参照しない（例：`judged_path`、`JUDGED_FILE`、事後の検査の記録を読む関数） | 構造検査（[ADR 0008](adr/0008-method-cannot-see-judged.md)） |
- 理由: 採点の基準や結果が方法に入ると、改善がタスクの答えに合わせた暗記になる。harness2 は全プロンプトに「採点基準は無い」と書き、測定の語と採点の印を機械で拒んでいる
- 出典: research.md の「harness2 の仕組み」の「正解に合わせた改善を防ぐ」
- 強制: structure, test — 構造検査が `layout.CHECKS_FILE` と `.checks_path` の参照と、方法のモジュールの、名前の中に `judg` がある属性の参照を照合する。`tests/test_guards.py` と `tests/test_profile.py` が語と印の拒否を確かめる
- probe: STATE-04-a, STATE-04-b, STATE-04-c
- 良い例:
  guards.require_clean_tree(candidate)  # recursion.py
- 悪い例:
  checks = where.task_dir(task) / layout.CHECKS_FILE  # context.py で証拠に入れる

### STATE-05 選択は完成品の成果物だけを匿名の ID で比べる

- 軸: X6
- 決定: 選択の候補は、そのモードの完成品のうち成果物を出した実行だけにし、候補の名前は `selection.compute_anonymous_ids`（タスク・k・モードから作る種でのシャッフル）の ID にし、選択役の作業場所にはスキルの木・差分・ラベルを置かず、k が 1 のときは選択役を起動しない。
- 理由: 選択役がどの木から来たかを知ると、編集の量や磨き込みで選ぶ。harness2 は「長さと磨き込みは長所ではない」と書き、作った harness を伏せて比べている
- 出典: research.md の「harness2 の仕組み」の「選択を中立にする」
- 強制: structure, test — 構造検査が `selection` からの `harness_dir` と `HARNESSES_DIR` の参照を落とす。`tests/test_selection.py` が ID の再現性と候補のディレクトリ名にラベルが無いことを確かめる
- probe: STATE-05-a, STATE-05-b
- 良い例:
  ids = selection.compute_anonymous_ids(labels, request.task_id, request.model.k, request.mode)
- 悪い例:
  fsops.copy_tree(place.harness_dir(mode, label), pool_dir / label)  # selection.py

### STATE-06 候補は実行の前に検証し、1回だけ差し戻し、それでも落ちたら入力の木に戻す

- 軸: X7
- 決定: 編集のセッションが返したスキルの木は、実行の前に `validate.check_tree` で検証し、問題があれば `recursion.STAGE_ATTEMPTS`（2回）まで「前の試みは却下された」とエラーの文を付けて同じセッションをやり直させ、それでも問題が残れば段の入力の木を使って `fell_back` を記録し、検証の項目は次の表にする。
  | 項目 | 問題にする条件 |
  |---|---|
  | 編集面 | `SKILL.md`、`references/<名前>.md`、`scripts/<名前>.py` か `.sh`、`assets/<名前>` 以外のファイルがある |
  | frontmatter | `description` 以外の行が元の木と違う。`description` が空、1024字を超える、`<` か `>` がある |
  | 本文の行数 | SKILL.md が500行を超える |
  | 参照の名指し | `references/` のファイルが SKILL.md で名指しされていない（行を足して直せるなら `validate.build_autolinked` で直す） |
  | 名指しの実在 | 本文や参照ファイルで名指しした `references/`・`scripts/`・`assets/` のパスが木に無い |
  | 動的な挿入 | `` !` `` の記法が元の木より増えている |
  | スクリプト | `.py` が `py_compile` で通らない |
  | 採点の印 | `guards.GRADER_MARKERS` の文字列がある |
- 理由: 壊れた候補を実行すると予算を使って何も分からない。harness2 は検証を実行の前に置き、却下の理由を返して1回だけ直させ、直らなければ入力に戻す
- 出典: research.md の「harness2 の仕組み」の「壊れた候補を試さない」「検証に落ちた提案の扱い」
- 強制: test, review — `tests/test_validate.py` が表の項目ごとに、`tests/test_recursion.py` が差し戻しと fell_back を確かめる
- probe: STATE-06-a
- 良い例:
  見本: kit/.h2/h2_kit/recursion.py の _run_stage
- 悪い例:
  # 検証に落ちた候補をそのまま実行する

### STATE-07 1つのタスク・モードの台帳は R = 4k と P = 3k を確かめてから要約を書く

- 軸: X8
- 決定: 実行とセッションは台帳（`ledger`）にラベルで記録し、モードの `summary.json` を書く前に `ledger.check_identity` で、ラベルの重複が無いこと、実行が `ledger.ROLLOUTS_PER_K` × k（4k）、編集のセッションが `ledger.SESSIONS_PER_K` × k（3k）であることを確かめ、合わなければ `StageError` を投げる。
- 理由: 予算が数えた通りでないと、モードどうしや k どうしの比較が成り立たず、利用者が承認した費用と実際の費用が食い違う
- 出典: research.md の「harness2 の仕組み」の「予算を数えて確かめる」
- 強制: test — `tests/test_ledger.py` と `tests/test_recursion.py` が恒等式を確かめる
- probe: STATE-07-a
- 良い例:
  ledger.require_identity(book, k)
- 悪い例:
  # 台帳を数えずに summary.json を書く

## ASYNC 非同期と並行

### ASYNC-01 並行は parallel.run_ordered だけで行い、記録は入力の順にする

- 軸: E4
- 決定: 並行に動かすのは `parallel.run_ordered`（プロファイルの `width` を上限にスレッドで動かし、結果を入力の順で返す）だけにし、`threading`、`concurrent`、`asyncio`、`multiprocessing` を `parallel` 以外で import せず、台帳への記録は `run_ordered` が返った後に入力の順で行う。
- 理由: 実行とセッションは時間がかかるので並行が要るが、終わった順に記録すると台帳とファイルの順が実行のたびに揺れる。harness2 も記録をプールが空になった後に行う
- 出典: research.md の「harness2 の仕組み」の「並行しても記録の順を揃える」
- 強制: structure — 構造検査が import を照合する
- probe: ASYNC-01-a
- 良い例:
  views = parallel.run_ordered([partial(_run_roll, env, stage) for stage in stages], env.model.width)
- 悪い例:
  with ThreadPoolExecutor() as pool: pool.map(_run_roll, stages)

## OPS ログ・設定・セキュリティ・表示

### OPS-01 結果は標準出力、エラーは標準エラーに出し、status の行は決めた書き出しだけを使う

- 軸: E5, X1
- 決定: 結果は標準出力、エラーは `エラー: ` を付けて標準エラーに出し、終了コードは成功 0・失敗 1・引数の誤り 2（argparse の既定）にし、`logging` を使わず、`status` の出力の各行は `status.LINE_KINDS`（`対象:`、`段階:`、`進み:`、`問題:`、`次:`）のどれかで始める。
- 理由: スキルは status の行の書き出しで次の手を読み分ける。新しい書き出しや出力先の揺れは、スキルの手順を黙って壊す
- 強制: test, structure — `tests/test_status.py` が全行の書き出しを確かめる。`logging` の import は構造検査が落とす
- probe: OPS-01-a, OPS-01-b
- 良い例:
  return "\n".join([f"対象: {target}", "段階: 承認待ち", f"次: {command}"])
- 悪い例:
  return "Next step -> run approve"

### OPS-02 設定は profile.json だけから読み、環境変数を読まない

- 軸: E6
- 決定: 改善の設定（k、モード、種、並行の幅、モデル、道具、上限）は `profile.json` だけから読み、`os.environ` と `os.getenv` は `proc` が外部コマンドに環境を渡すときだけ使う。
- 理由: 環境変数で振る舞いが変わると、同じ承認でも人ごとに結果が変わり、`plan.md` の予算から再現できない
- 強制: structure — 構造検査が `os.environ` と `os.getenv` を `proc` だけに限る
- probe: OPS-02-a
- 良い例:
  width = approved.profile.width
- 悪い例:
  width = int(os.getenv("H2_WIDTH", "2"))

### OPS-03 人に見せる文言は日本語で書き、表と一覧は render の関数で作る

- 軸: E7
- 決定: 人に見せる文言（エラー、status、plan.md、show の出力）は日本語で書き、表は `render.render_table`、一覧は `render.render_bullets`、金額は `render.render_usd` で作り、日付は `cli` が引数として段に渡す。
- 理由: 表や金額の書き方が段ごとに分かれると、plan.md と show の読み方が揃わない
- 強制: review — レビューで確かめる
- 機械化しない理由: 文言が日本語として自然か、人に見せる文言かどうかは意味の判断が要るため
- probe: なし
- 良い例:
  render.render_table(["ラベル", "成果物", "スキル"], rows)
- 悪い例:
  f"{label}: ${cost:.2f}"

### OPS-04 実行・採用・事後の検査の段は、最初に承認済みのプロファイルを読む

- 軸: E8
- 決定: `execution.run`・`adoption.adopt`・`judging.judge` は最初の文で `workspace.load_approved` を呼び、`load_approved` はプロファイルとタスクのハッシュが `approval.json` と一致しなければ `StageError` を投げ、対象スキルのディレクトリを書き換えるのは `adoption.adopt` だけにする。
- 理由: 承認されていないプロファイルで実行を進めると、人の知らない予算が使われ、人の知らないタスクでスキルが変わる
- 強制: structure — 構造検査が `APPROVED_STAGES` の公開関数の最初の文を照合する
- probe: OPS-04-a
- 良い例:
  def judge(where: layout.Layout, task_id: str | None) -> str:
      approved = workspace.load_approved(where)
- 悪い例:
  def judge(where: layout.Layout, task_id: str | None) -> str:
      model = workspace.load_profile(where)

### OPS-05 claude のコマンド行は runner だけで組み立て、閉じ込めのフラグを外さない

- 軸: X9
- 決定: `claude` のコマンド行は `runner.build_rollout_command` と `runner.build_session_command` だけで組み立て、`--` で始まる文字列は `runner` と `cli` だけに書き、実行には `runner.ROLLOUT_GUARD_FLAGS`、編集・選択・振り返りのセッションには `runner.SESSION_GUARD_FLAGS` を必ず付け、`Skill` を実行の道具に必ず含める。
  | 種類 | 必ず付けるフラグ |
  |---|---|
  | 実行 | `--setting-sources project`、`--strict-mcp-config`、`--no-session-persistence`、`--permission-prompts none` |
  | 編集のセッション | `--restricted`、`--tools Read,Edit,Write,Glob,Grep`、`--disable-slash-commands`、`--strict-mcp-config`、`--no-session-persistence`、`--permission-prompts none` |
  | 選択・振り返り | 編集のセッションと同じ。ただし `--tools Read,Glob,Grep` |
- 理由: 利用者のスキルやプラグインが実行に混ざると、結果が対象スキル以外の要因で揺れる。編集者が証拠の中のスクリプトを実行したり作業場所の外を読んだりできると、harness2 が文で禁じたことが破られる
- 出典: research.md の「Claude Code のヘッドレス実行（claude -p）2.1.308」
- 強制: structure, test — 構造検査が `--` で始まる文字列の置き場を照合する。`tests/test_runner.py` が両方のコマンド行のフラグを確かめる
- probe: OPS-05-a, OPS-05-b
- 良い例:
  command = runner.build_session_command(env.model, runner.EDIT_TOOLS)
- 悪い例:
  command = ["claude", "-p", "--dangerously-skip-permissions"]  # rollout.py

## TEST テスト

### TEST-01 モジュールごとに tests/test_<モジュール>.py と <名前>Test クラスを置く

- 軸: F1, F2
- 決定: `h2_kit` の各モジュールと `install.py` に `tests/test_<名前>.py` を1つ置き、その中に `unittest.TestCase` を継承した `<名前の PascalCase>Test` クラスを置き、テストの関数名は `test_<確かめること>` にし、モジュールに対応しないテストファイルを置かない。
- 理由: テストの置き場と名前が揺れると、変更のときにどのテストを見ればよいかが分からなくなる
- 強制: structure — 構造検査がファイルとクラスの有無を照合する
- probe: TEST-01-a
- 良い例:
  class LedgerTest(unittest.TestCase):
      def test_parallel_k2_lands_on_identity(self) -> None:
- 悪い例:
  class TestLedger(unittest.TestCase): ...

### TEST-02 モックを使わず、support.py の部品と偽の claude で確かめる

- 軸: F3, F4
- 決定: テストは `unittest.mock` と差し替えを使わず、`tests/support.py` の関数で一時ディレクトリに作ったリポジトリ・スキル・プロファイル・タスクと、プロファイルの `claude` に指定した `tests/fixtures/fake_claude.py`（本物の子プロセスとして動く偽の claude）で確かめる。
- 理由: モックは実際のファイルの形やコマンド行との食い違いを隠す。harness2 も決定的な偽の編集者と実行器で流れ全体を通している
- 出典: research.md の「harness2 の仕組み」の「偽物で全体を試す」
- 強制: structure, review — `unittest.mock` と `mock` の import は構造検査が落とす。部品の置き場はレビューで確かめる
- probe: TEST-02-a
- 良い例:
  where = support.build_approved(self, behaviors=("invalid-once",))
- 悪い例:
  from unittest import mock

### TEST-03 サブコマンドを足したら、決めた名前のテストを足す

- 軸: F5
- 決定: `cli.COMMANDS` にサブコマンドを足したら `tests/test_cli.py` に `test_command_<サブコマンド名>` を足す。
- 理由: 新しいサブコマンドのテストの有無が人ごとに分かれると、動かないサブコマンドが配られる
- 強制: structure — 構造検査が `COMMANDS` とテストの関数名を照合する
- probe: TEST-03-a
- 良い例:
  def test_command_judge(self) -> None:
- 悪い例:
  # COMMANDS に "export" を足し、テストは足さない

## PROC 作業手順

### PROC-01 サブコマンドを足すときは置き場から入口の順に作る

- 軸: G1
- 決定: サブコマンドを足すときは、`layout.py`（置き場）→ `workspace.py`（読み込みと進み具合）→ 段のモジュール → `status.py` → `cli.py` → テスト → `structure_check.py` の表と architecture.md の許可表 → SKILL.md の表、の順に作る。
- 理由: 入口から作ると、置き場や読み込みが決まらないまま仮の名前が入り、後で全部を書き換えることになる
- 強制: doc — AGENTS.md と実装用スキルの手順に書く
- 機械化しない理由: 作った順番は差分に残らないため
- probe: なし
- 良い例:
  1. layout.py に置き場を足す 2. workspace 3. 段のモジュール 4. status 5. cli
- 悪い例:
  1. cli.py にサブコマンドを足し、中身は後で考える

### PROC-02 波及の対応表の組は同じ変更で変える

- 軸: G2
- 決定: 次の表の左を変えたら、右を同じ変更で変える。
  | 変えるもの | 一緒に変えるもの |
  |---|---|
  | `templates/prompts/` のひな形 | `prompts.TEMPLATES`、値を作るモジュール、research.md の harness2 の表の「この基盤での形」 |
  | `validate.check_tree` の検証の項目 | STATE-06 の表、`templates/prompts/_surface.md` の「提案ごと捨てる規則」、`tests/test_validate.py` |
  | `contracts.py` の返答のタグ | 返答の形を書いたひな形（`_notes-format.md` か `select.md` か `reflect.md`） |
  | `status.LINE_KINDS` か status の `次:` の行 | SKILL.md の「繰り返すこと」の表 |
  | `profile.json` の形 | `profile.SCHEMA_VERSION`、`references/profile-guide.md`、ADR |
  | `runner` のフラグ | OPS-05 の表、research.md の「Claude Code のヘッドレス実行」 |
  | モジュールの追加・import の変更 | `structure_check.py` の表、architecture.md の許可表 |
- 理由: 片方だけを変えると、CLI と文書・スキル・ひな形が食い違い、編集者や利用者が古い規則に従う
- 強制: review — レビューで両側のファイルを突き合わせる
- 機械化しない理由: 組の一部（ひな形と表、モジュールと許可表）は他のルールの検査で縛るが、検証の項目とひな形の文、status の行と SKILL.md の手順の対応は意味の判断が要るため
- probe: なし
- 良い例:
  # validate に項目を足し、_surface.md の規則と STATE-06 の表にも同じ項目を足す
- 悪い例:
  # validate だけを変え、編集者には知らせない

### PROC-03 道具の版は Makefile で固定し、上げるときは ADR を書く

- 軸: G3
- 決定: ruff と mypy の版は `Makefile` の `RUFF`・`MYPY` の変数にだけ書き、版を上げるときは ADR を書いてから変数を変え、`make check` を通す。
- 理由: 版が人ごとに違うと、整形と lint の結果が揺れる
- 強制: review — `Makefile` は保護ファイルなので、変更はレビューで確かめる
- 機械化しない理由: 版を上げてよいかは互換性の判断が要るため
- probe: なし
- 良い例:
  RUFF := uvx ruff@0.17.2
- 悪い例:
  RUFF := uvx ruff

### PROC-04 ルールは ADR から probe の順で変える

- 軸: G4
- 決定: ルールを変えるときは、承認を得てから ADR → `docs/design/rules.md` → 検査の設定と `.foundation/probes.json` → 見本のコード、の順に変え、`rules_check.py` と `violation_probe.py` を通す。
- 理由: 順番が崩れると、検査と文書のどちらが正しいかが分からなくなる
- 強制: doc — AGENTS.md の「ルールを変えたいとき」に書く
- 機械化しない理由: 変えた順番は差分に残らないため
- probe: なし
- 良い例:
  docs/design/adr/0008-*.md を書いてから rules.md を変える
- 悪い例:
  structure_check.py の表だけを変える

### PROC-05 完了の条件は make check が通ること

- 軸: G5
- 決定: 作業を完了と報告してよいのは `make check` が通り、実装用スキルの完了前チェックリストを満たしたときだけにする。
- 理由: 完了の基準が人ごとに違うと、検査の落ちた変更が渡される
- 強制: doc — AGENTS.md の「完了の条件」と実装用スキルに書く
- 機械化しない理由: 報告の時点で check を回したかは差分に残らないため
- probe: なし
- 良い例:
  make check の出力の末尾を報告に貼る
- 悪い例:
  「テストは通ると思います」と報告する

### PROC-06 profile.json の形を変えたら SCHEMA_VERSION を上げる

- 軸: X2
- 決定: `profile.json` の項目を足す・消す・意味を変えるときは `profile.SCHEMA_VERSION` を1上げ、`references/profile-guide.md` と ADR を同じ変更で書き、`profile.parse_profile` は `schema_version` が `SCHEMA_VERSION` と違うプロファイルを問題として返す。
- 理由: 古い形のプロファイルを新しい CLI が黙って読むと、項目の意味がずれたまま予算が使われる
- 強制: test, review — `tests/test_profile.py` が違う版のプロファイルを問題にすることを確かめる。版を上げたかはレビューで確かめる
- probe: PROC-06-a
- 良い例:
  SCHEMA_VERSION = 2  # rollout に effort を足した（ADR 0009）
- 悪い例:
  # profile.json に新しい項目を足し、版は 1 のまま

### PROC-07 人が決める場面はスキルに書き、AskUserQuestion で聞く

- 軸: X5
- 決定: 人が決める場面（プロファイルとタスクの確定、`plan.md` の予算の承認、採用する候補か採用しないかの決定）は `skill-harness2` の SKILL.md の「人が決める場面」の表に書いて AskUserQuestion で聞き、答えを得る前に `approve` と `adopt` を実行せず、`adopt` には `show` が出した確認の符号を `--confirm` で渡す。
- 理由: 予算を使う判断と対象スキルを書き換える判断をエージェントが代わりに行うと、人の意図と違う基準でスキルが変わる。論文の失敗の分析では、選択が弱い候補を選んだ例と、誤った前提が全候補に広がった例があり、最後の判断は人が差分を見て行う
- 出典: research.md の「論文 arXiv 2610.14224」
- 強制: review — SKILL.md の差分をレビューで確かめる
- 機械化しない理由: スキルの手順が人に聞いてから実行する形になっているかは、文の意味の判断が要るため
- probe: なし
- 良い例:
  | adopt | show の出力を見せ、採用する候補か「採用しない」かを AskUserQuestion で聞く |
- 悪い例:
  run が終わったら選ばれた候補をそのまま adopt する

## TOOL 道具と自動化

### TOOL-01 整形は ruff format に任せる

- 軸: H1
- 決定: Python のファイルの整形（字下げ、引用符、改行の位置、import の並び）は `ruff format` と `ruff check --fix` に任せ、`make check` は `ruff format --check` で整形済みかを確かめる。
- 理由: 整形を人が決めると、差分に関係の無い書き換えが混ざる
- 出典: research.md の「ruff 0.17.2」
- 強制: format — `make format-check`
- probe: TOOL-01-a
- 良い例:
  make fix
- 悪い例:
  x = {  'a':1 }

### TOOL-02 編集の直後は hooks、完了の前は make check を回す

- 軸: H2
- 決定: Python のファイルを編集した直後は hooks が `make fix-file FILE=<パス>` を回し、完了の前に `make check` を回す。
- 理由: 検査を回す時期が人ごとに違うと、整形や lint の違反が溜まってから一度に直すことになる
- 強制: doc — AGENTS.md の「完了の条件」と `.claude/settings.json` の hooks
- 機械化しない理由: いつ検査を回したかは差分に残らないため
- probe: なし
- 良い例:
  make check
- 悪い例:
  検査を回さずに完了と報告する

### TOOL-03 抑止コメントを書かない

- 軸: H3
- 決定: lint 無効化（`noqa`、`ruff: noqa`）、型無視（`type: ignore`、`mypy:`）、カバレッジ除外、整形の除外（`fmt: off`）、テストの skip を書かない。
- 理由: 抑止コメントで検査を黙らせると、そのルールは無いのと同じになる
- 強制: structure — `.foundation/bin/guard.py` が manifest の `guard.suppressions` のパターンを照合する
- probe: TOOL-03-a
- 良い例:
  # 検査が落ちたら、エラーのルールIDを rules.md で引いて直す
- 悪い例:
  import yaml  # noqa

### TOOL-04 保護ファイルを変えない

- 軸: H3
- 決定: manifest の `protected` にあるファイル（`Makefile`、`pyproject.toml`、`scripts/structure_check.py`、`.claude/settings.json`、`.foundation/**`、`docs/design/rules.md`、`docs/design/enforcement-matrix.md`）は、ルールの変更として承認された作業の中でだけ変え、例外としてモジュール・段・JSON の項目を足す作業では `scripts/structure_check.py` の登録の表（`SHARED`、`STAGES`、`ENTRY`、`APPROVED_STAGES`、`KEY_MODULES`、`WRAPPER_KEYS`）に要素を足すことだけを許す。
- 理由: 検査の設定を緩めて検査を通すと、ルールが黙って無くなる。登録の表は新しいモジュールや段を足すたびに増えるので、そこだけはルールの変更と分ける
- 強制: review — hooks がエージェントの編集に確認を求め、差分はレビューで確かめる
- 機械化しない理由: hooks はエージェントの編集にだけ確認を求め、人の編集は止められないため、差分のレビューで確かめる
- probe: なし
- 良い例:
  # 検査が落ちたらコードを直す
- 悪い例:
  # pyproject.toml の ignore に E501 を足す

### TOOL-05 Python 3.9 で動く書き方にし、道具は版を固定して呼ぶ

- 軸: H4
- 決定: 配布物と開発用のコードは Python 3.9 で動く書き方にし（`match` 文、`zip(strict=)`、`dataclass(slots=)` を使わない）、ruff は `target-version = "py39"`、mypy は `python_version = "3.9"` で検査し、どちらも `Makefile` の `uvx <道具>@<版>` で呼ぶ。
- 理由: 利用者のリポジトリの Python は 3.9 のことがある。新しい書き方が混ざると、配布先で起動もできない
- 出典: research.md の「Python 3.9.6」「mypy 1.20.2」
- 強制: type — mypy の `python_version = "3.9"` が 3.10 以降の API を落とす
- probe: TOOL-05-a
- 良い例:
  for left, right in zip(a, b):
- 悪い例:
  for left, right in zip(a, b, strict=True):

## 対象外とした軸

揺れない軸、またはこの分野に無い軸と、その理由を書く。全軸がいずれかのルールに割り当たっているため、対象外の軸は無い。

| 軸 | 理由 |
|---|---|
