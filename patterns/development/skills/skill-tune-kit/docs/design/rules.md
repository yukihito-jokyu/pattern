# skill-tune-kit のルール

このファイルは skill-tune-kit のルールの正本である。AGENTS.md・スキル・レビューの指摘・検査のエラーは、ここのルールIDを参照する。ルールの変更手順は AGENTS.md の「ルールを変えたいとき」に従う。

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
| 対象スキル | 改善する、利用者のリポジトリの任意の Claude Code スキル |
| 補助 CLI | `kit/.tune/tune.py` と `tune_kit` パッケージ。配布先では `.tune/tune.py` |
| 計画（plan） | 人と決めた対象、モード、検査、分割、予算を書いた `plan.json` |
| ケース | 評価データの1件。入力（依頼文と入力ファイル）と検査、`reference` モードでは正解を持つ。`dataset/cases.json` に並べる |
| モード | `reference`（正解データがある・作れる）か `criteria`（正解データが無く、評価項目で測る） |
| 検査（check） | ケースの出力が満たすべき条件。種類は `checks.KINDS`。機械で判定する種類と、採点役が判定する `judge` がある |
| 分割 | ケースを学習用（`train`）・検証用（`val`）・テスト用（`test`）に分けたもの。`split.json` |
| 版 | 対象スキルの写し。`v0` は承認時の写し、`v1` 以降は学習役が直した候補。`versions/v<N>/` |
| 今の版 | 採用された最後の版。採用が無ければ `v0` |
| 実行 | 1つの版で1件のケースを1回解くこと。作業場所は `work/<target-id>/<run-key>/` |
| 段 | 補助 CLI の1つのサブコマンドが受け持つ処理 |
| 段のモジュール | 段を実装するモジュール（`planning`、`status`、`evaluate`、`learn`、`decide`、`audit`、`report`） |
| 共有のモジュール | 2つ以上の段が使うモジュール（`errors`、`render`、`splitting`、`checks`、`metrics`、`layout`、`plan`、`contracts`、`fsops`、`proc`、`prompts`、`workspace`） |
| 実行役・採点役・学習役・監査役 | サブエージェントの `tune-executor`、`tune-grader`、`tune-learner`、`tune-auditor` |
| ラウンド | 監査、データの直し、学習、候補の評価、採否の1巡。`rounds/r<N>/` |

## 追加した軸

カタログに無い、この分野に固有の軸を定義する。

| 軸 | 内容 | 置く節 |
|---|---|---|
| X1 | 終了コードと出力の形式（標準出力と標準エラーの使い分け、status の行の書き出し） | OPS |
| X2 | 公開 API の互換性（plan.json と cases.json の形を変えるときの手順） | PROC |
| X3 | スキル・サブエージェントの定義の書式（frontmatter、行数、参照ファイル） | STR |
| X4 | サブエージェントとの受け渡し（プロンプトのひな形と、サブエージェントが書くファイル） | STATE |
| X5 | 人の関所（人が決める場面と、その聞き方） | PROC |
| X6 | 評価データの分割と独立性（学習役に見せる範囲、テスト用を使う時期） | STATE |

## STR 配置と構造

### STR-01 ファイルは表の場所に置き、表に無い場所を作らない

- 軸: A1, A5, A6
- 決定: ファイルは次の表の場所に置く。
  | 置くもの | 場所 |
  |---|---|
  | 補助 CLI の入口 | `kit/.tune/tune.py` |
  | 補助 CLI のモジュール | `kit/.tune/tune_kit/<モジュール>.py`（サブディレクトリを作らない） |
  | プロンプトのひな形 | `kit/.tune/templates/prompts/<名前>.md` |
  | 配布するスキル | `kit/claude/skills/skill-tune/SKILL.md`、`kit/claude/skills/skill-tune/references/<名前>.md` |
  | 配布するサブエージェント | `kit/claude/agents/tune-<役>.md` |
  | 配布物を入れるスクリプト | `install.py` |
  | 構造検査と生成器 | `scripts/structure_check.py`、`scripts/gen_docs.py` |
  | テスト | `tests/__init__.py`、`tests/support.py`、`tests/test_<名前>.py` |
  | テストの見本データ | `tests/fixtures/` の下 |
  | 上のどれでもない | 置かない。場所が要るならルールの変更として提案する |
- 理由: 配布物（`kit/`）に置いた物は全部が利用者のリポジトリへ写る。置き場が人ごとに分かれると、写るべき物が漏れたり、開発用の物が配られたりする
- 強制: structure — `scripts/structure_check.py` の `LAYOUT` 表が `kit/` と `tests/` の全ファイルのパスを照合する
- probe: STR-01-a
- 良い例:
  kit/.tune/tune_kit/splitting.py
  tests/test_splitting.py
- 悪い例:
  kit/.tune/tune_kit/stages/learn.py
  kit/.tune/helpers.py

### STR-02 モジュールは構造検査の表に登録し、置き場を決定表で決める

- 軸: A2, A3, A4
- 決定: `tune_kit` のモジュールは `scripts/structure_check.py` の `SHARED`・`STAGES`・`ENTRY` のどれか1つに登録し、関数の置き場は次の表で決める。
  | 関数を使うモジュール | 置き場 |
  |---|---|
  | 1つの段のモジュールだけ | その段のモジュール。名前を `_` で始める |
  | 2つ以上の段のモジュール | 共有のモジュール（表の役割に合うもの。合うものが無ければ共有のモジュールを足す） |
  | 上のどれでもない（cli だけ） | `cli` |
- 理由: 新しいモジュールや関数の置き場が人ごとに分かれると、段どうしの依存が生まれ、1つの変更で触るファイルが予測できなくなる
- 強制: structure, review — 登録の無いモジュールは構造検査が落とす。関数の置き場はレビューで確かめる
- probe: STR-02-a
- 良い例:
  SHARED = {"errors": frozenset(), "render": frozenset(), ...}  # 新しいモジュールを1行足す
- 悪い例:
  # learn.py と decide.py の両方に同じ _rate() を写す

### STR-03 入口は tune.py と cli.main の2つだけにする

- 軸: A7
- 決定: 補助 CLI の入口は `kit/.tune/tune.py`（`cli.main` を呼ぶだけ）と `cli.main` の2つにし、`tune_kit/__init__.py` は docstring だけにし、`tune_kit` のモジュールに `if __name__ == "__main__":` を書かない。
- 理由: 入口が複数あると、スキルがどれを呼ぶかで揺れ、承認の確認（OPS-04）を通らない呼び方が生まれる
- 強制: structure — `__init__.py` の中身と `__main__` の判定を構造検査が照合する
- probe: STR-03-a
- 良い例:
  sys.exit(cli.main(sys.argv[1:], Path(__file__).resolve().parent.parent))
- 悪い例:
  if __name__ == "__main__":
      print(status.status(...))

### STR-04 生成物は手で編集せず make docs で作り直す

- 軸: A6
- 決定: `kit/claude/skills/skill-tune/references/check-kinds.md` は `scripts/gen_docs.py` が `checks.KINDS` から作る生成物とし、手で編集せず、変えるときは `make docs` を実行する。
- 理由: 検査の種類の説明を手で書くと、コードと文書の片方だけが更新され、計画を作るエージェントが存在しない種類を使う
- 強制: structure — `make check` の `docs-check` が再生成して差分が無いことを確かめる
- probe: STR-04-a
- 良い例:
  make docs
- 悪い例:
  # check-kinds.md の表に手で行を足す

### STR-05 スキルとサブエージェントは決まった frontmatter で書く

- 軸: X3
- 決定: 配布するスキルとサブエージェントの frontmatter は次の表のとおりにし、SKILL.md は500行以内、`references/` は1階層にする。
  | ファイル | 必須の項目 | 禁止 |
  |---|---|---|
  | `skills/skill-tune/SKILL.md` | `name: skill-tune`、`description`、`disable-model-invocation: true`、`allowed-tools: Bash(python3 .tune/tune.py *)`、`argument-hint` | — |
  | `agents/tune-executor.md` | `name`（ファイル名と同じ）、`description`、`tools` | `tools` に `Skill`・`Agent`、`omitClaudeMd` |
  | `agents/tune-grader.md`、`tune-learner.md`、`tune-auditor.md` | `name`（ファイル名と同じ）、`description`、`tools`、`omitClaudeMd: true` | `tools` に `Skill`・`Agent` |
- 理由: サブエージェントが別のスキルや別のサブエージェントを使うと、評価が対象スキル以外の要因で揺れる。採点役・学習役・監査役にリポジトリの CLAUDE.md を読ませると、判定がリポジトリの指示に引きずられる
- 出典: research.md の「Claude Code のスキル」「Claude Code のサブエージェント」
- 強制: structure — 構造検査が frontmatter と行数を照合し、エージェントの名前を `contracts.AGENTS` と突き合わせる
- probe: STR-05-a, STR-05-b
- 良い例:
  name: tune-grader
  tools: Read, Write, Glob, Grep
  omitClaudeMd: true
- 悪い例:
  name: tune-grader
  tools: Read, Write, Agent

## DEP 境界と依存

### DEP-01 import は許可表の組だけにし、段のモジュールどうしは import しない

- 軸: B1, B3
- 決定: `tune_kit` のモジュールは architecture.md の依存の許可表にある組だけを import し、段のモジュールは他の段のモジュールを import しない。
- 理由: 段どうしが依存すると、1つの段の変更が他の段を壊し、変更シナリオ表の「触らないもの」が守れなくなる
- 強制: structure — `scripts/structure_check.py` の `SHARED`・`STAGES`・`ENTRY` の表で import を照合する
- probe: DEP-01-a
- 良い例:
  from tune_kit import contracts, fsops, layout, metrics, plan, render, workspace  # decide.py
- 悪い例:
  from tune_kit import learn  # decide.py から別の段を呼ぶ

### DEP-02 他のモジュールの _ で始まる名前を使わない

- 軸: B2
- 決定: モジュールの外から使ってよいのは `_` で始まらない名前だけにし、`<モジュール>._<名前>` と `from tune_kit.<モジュール> import _<名前>` を書かない。
- 理由: 内部の名前を外から使うと、モジュールの中を直しただけで別のモジュールが壊れる
- 強制: structure — 構造検査が属性の参照と import を照合する
- probe: DEP-02-a
- 良い例:
  fsops.write_json(path, data)
- 悪い例:
  fsops._normalize(path)

### DEP-03 Python 3.9 の標準ライブラリと tune_kit だけを import する

- 軸: B4, B6
- 決定: `kit/`、`scripts/`、`tests/`、`install.py` が import してよいのは、`scripts/structure_check.py` の `STDLIB` 表にある標準ライブラリと `tune_kit` だけにし、依存ライブラリを足さない。
- 理由: 配布物は利用者のリポジトリでそのまま動く必要があり、依存を足すと導入の手順が利用者ごとに分かれる
- 出典: research.md の「Python 3.9.6」
- 強制: structure — 構造検査が import を `STDLIB` 表と照合する
- probe: DEP-03-a
- 良い例:
  import hashlib
- 悪い例:
  import yaml

### DEP-04 副作用に触れるモジュールを表の3つに限る

- 軸: B5
- 決定: 副作用は次の表のモジュールだけで扱う。
  | 副作用 | 書いてよいモジュール | 検査する書き方 |
  |---|---|---|
  | ファイルの書き込み・削除・コピー | `fsops` | `write_text`、`write_bytes`、`open(`、`shutil`、`mkdir`、`unlink`、`rmtree` |
  | 外部コマンド | `proc` | `subprocess` |
  | 時刻、画面への出力、終了コード | `cli` | `datetime`、`time`、`print`、`sys.exit` |
- 理由: 副作用が散らばると、テストで一時ディレクトリの外を書き換えたり、status が作業場所を変えたりする事故を防げない
- 強制: structure, lint — 構造検査が書き方を照合する。`print` は ruff の `T201` でも落とす
- probe: DEP-04-a, DEP-04-b
- 良い例:
  fsops.write_json(directory / layout.DECISION_FILE, contracts.build_decision_data(record))  # decide.py
- 悪い例:
  (directory / layout.DECISION_FILE).write_text(json.dumps(data))  # decide.py

## NAM 命名

### NAM-01 名前のケースは PEP 8 に従う

- 軸: C1, C2, C6
- 決定: モジュール・関数・変数は snake_case、クラスは PascalCase、モジュールの定数は UPPER_SNAKE_CASE にし、略語も同じ規則で書く（`case_id`、`CaseId` ではなく `CaseID` も使わない）。
- 理由: ケースが人ごとに分かれると、同じものに2つの名前が生まれ、検索で漏れる
- 出典: research.md の「ruff 0.17.1」
- 強制: lint — ruff の `N801`、`N802`、`N806`、`N815`
- probe: NAM-01-a
- 良い例:
  def compute_pass_rate(results: list[CaseResult]) -> Fraction:
- 悪い例:
  def computePassRate(results):

### NAM-02 関数名は動詞表の語で始め、段の公開関数はサブコマンド名にする

- 軸: C3, C4, C5
- 決定: 段のモジュールの公開関数はサブコマンド名の `-` を `_` にした名前にし、それ以外のモジュール直下の関数は、`_` で始まる関数も同じく、次の動詞表の語で始める（`_` の次の語を照合する。クラスのメソッドと関数の中の関数は対象外）。
  | 語 | 使う場面 |
  |---|---|
  | `load` | 作業場所のファイルを読み、検証済みの型で返す |
  | `read` | ファイルをそのまま読む |
  | `parse` | 辞書を検証して型にする（問題を全部集める） |
  | `build` | パス・値・行を組み立てる（副作用なし） |
  | `render` | Markdown や表示の文字列を作る |
  | `write`、`copy`、`remove` | ファイルを書く・写す・消す |
  | `run` | 外部コマンドを動かす |
  | `compute` | 指標・分割・ハッシュを計算する |
  | `check` | 検査して問題の一覧を返す |
  | `evaluate` | 検査を1件評価して合否を返す |
  | `find` | 一覧から1つ探し、無ければ `None` を返す |
  | `list` | 一覧を返す |
  | `is`、`has` | 真偽値を返す |
  | `require` | 条件を満たさなければ例外を投げ、満たせば次に使う値を返す |
  | `main` | 入口 |
- 理由: 同じ意味の動詞（get、fetch、load）が混ざると、関数が副作用を持つか、検証済みかを名前から判断できなくなる
- 強制: structure — 構造検査が関数名の先頭の語を表と照合する
- probe: NAM-02-a
- 良い例:
  def load_cases(where: layout.Layout) -> list[plan.Case]:
- 悪い例:
  def get_cases(where):

### NAM-03 JSON のキーは snake_case にし、dataclass のフィールド名と同じにする

- 軸: C7
- 決定: plan.json・cases.json・サブエージェントが書く JSON のキーは snake_case にし、`plan.py` と `contracts.py` で読むキーは対応する dataclass のフィールド名と同じ綴りにする（配列や入れ子を包むだけのキーは `scripts/structure_check.py` の `WRAPPER_KEYS` に登録する）。
- 理由: キーとフィールド名が食い違うと、変換の場所が増え、計画を書くエージェントがどちらの綴りで書くかで揺れる
- 強制: structure — 構造検査が `plan.py`・`contracts.py` の `data.get("…")` と `data["…"]` のキーを照合する
- probe: NAM-03-a
- 良い例:
  runs_per_case=_int(data.get("runs_per_case"), ...)
- 悪い例:
  runs_per_case=_int(data.get("runsPerCase"), ...)

## CODE 書き方

### CODE-01 データは継承しない frozen の dataclass にし、引数を変えない

- 軸: D1, D5
- 決定: `tune_kit` のクラスは `@dataclass(frozen=True)` で基底クラスを持たないものと、`errors.py` の例外だけにし、関数は引数のリスト・辞書を書き換えずに新しい値を返す。
- 理由: 可変のデータを共有すると、ある段が書き換えた値を別の段が読み、結果がファイルの中身と食い違う
- 強制: structure, review — クラスの形は構造検査が照合する。引数を書き換えないことはレビューで確かめる
- probe: CODE-01-a
- 良い例:
  @dataclass(frozen=True)
  class Check:
      id: str
- 悪い例:
  class Check:
      def __init__(self, data): self.data = data

### CODE-02 import は from tune_kit import <モジュール> にし、先頭に annotations を書く

- 軸: D2
- 決定: `tune_kit` のモジュールは `from tune_kit import <モジュール>` で import して `<モジュール>.<名前>` で使い、名前を直接 import してよいのは `from tune_kit.errors import <例外>` だけにし、全モジュールの docstring の次の文を `from __future__ import annotations` にする。
- 理由: 名前を直接 import する書き方と混ざると、どのモジュールの名前かが読めなくなり、DEP-01 の照合も漏れる
- 出典: research.md の「Python 3.9.6」
- 強制: structure, lint — 構造検査が import の形と先頭の文を照合する。相対 import は ruff の `TID252`、並びは `I001` で落とす
- probe: CODE-02-a, CODE-02-b
- 良い例:
  from tune_kit import layout, plan
  from tune_kit.errors import KitError
- 悪い例:
  from tune_kit.plan import Plan
  from . import layout

### CODE-03 型注釈を全部に書き、mypy の strict を通す

- 軸: D3
- 決定: 全関数の引数と戻り値に型注釈を書き、`mypy --strict`（`python_version = 3.9`）を通し、`Any` を書かず、外から来る値は `object` で受けて `plan.py`・`contracts.py` で型を確かめる。
- 理由: 型の無い値が段をまたぐと、JSON の形の誤りが遠くの段で初めて表に出る
- 出典: research.md の「mypy 1.20.2」
- 強制: type — `make typecheck`（mypy strict）
- probe: CODE-03-a
- 良い例:
  def parse_check(data: object, where: str) -> tuple[Check | None, list[str]]:
- 悪い例:
  def parse_check(data, where):

### CODE-04 関数の大きさは ruff の上限に収める

- 軸: D4, D6
- 決定: 関数は複雑度10以下（`C901`）、引数6以下（`PLR0913`）、分岐12以下（`PLR0912`）、文50以下（`PLR0915`）、return 6以下（`PLR0911`）、1行120文字以下（`E501`）に収め、超えたら `_` で始まる関数に分ける。
- 理由: 大きな関数は直す人ごとに分け方が変わり、差分が大きくなる
- 強制: lint — `pyproject.toml` の `[tool.ruff.lint]` の上限
- probe: CODE-04-a
- 良い例:
  def decide(...):
      cur, cand = _load_pair(...)
      return _render_decision(metrics.compute_decision(cur, cand))
- 悪い例:
  def decide(root, target, number, cur, cand, today, force): ...

### CODE-05 モジュールの docstring は必須にし、コメントアウトしたコードを残さない

- 軸: D7
- 決定: 全モジュールの先頭に役割を1文で書いた docstring を置き、コメントは「なぜ」だけを書き、コメントアウトしたコードを残さない。
- 理由: 役割の書かれていないモジュールには、関係の無い関数が足されていく。古いコードのコメントは、どちらが正しいかの迷いを生む
- 強制: lint, review — ruff の `D100`、`D104`、`ERA001`。コメントが「なぜ」かはレビューで確かめる
- probe: CODE-05-a
- 良い例:
  """ケースを学習用・検証用・テスト用に決定的に分ける。"""
- 悪い例:
  # rate = passed / total
  rate = Fraction(passed, total)

### CODE-06 ファイル名・エージェント名・分割名の文字列は定数で持つ

- 軸: D8
- 決定: ファイル名とディレクトリ名の文字列は `layout.py`、エージェント名は `contracts.AGENTS`、分割名・モード・重さ・検査の種類は `plan.py` と `checks.py` の定数に置き、他のモジュールは定数を参照する（`splitting` は依存を持たない共有のモジュールなので、分割名を `ORDER` に自分で持つ）。
- 理由: 同じファイル名を複数の場所に書くと、名前を変えたときに片方が残り、status と段が別のファイルを見る
- 強制: structure — 構造検査が `layout.py` 以外の `.json`・`.md` で終わる文字列と、`contracts.py` 以外の `tune-` で始まるエージェント名の文字列を照合する
- probe: CODE-06-a
- 良い例:
  where.run_dir(key) / layout.RESPONSE_FILE
- 悪い例:
  where.run_dir(key) / "response.md"

## ERR エラーと入力検証

### ERR-01 投げる例外は errors.py の4つだけにし、捕まえる場所を限る

- 軸: E1
- 決定: 投げる例外は `errors.py` の `KitError`、`InvalidFileError`、`StageError`、`CommandError` だけにし、`except` を書いてよいのは次の表の場所だけにする。
  | モジュール | 捕まえてよいもの |
  |---|---|
  | `cli` | `KitError`（`main` の中だけ） |
  | `fsops` | `OSError`、`UnicodeDecodeError`、`json.JSONDecodeError` |
  | `proc` | `OSError`、`subprocess.TimeoutExpired` |
  | `plan`、`checks` | `re.error`、`ValueError`、`json.JSONDecodeError` |
  | 上のどれでもない | 書かない |
- 理由: 例外の種類と捕まえる場所が散らばると、利用者に見せるエラーの形が揺れ、思わぬ例外が握りつぶされる
- 強制: structure, lint — 構造検査が `raise` と `except` を照合する。広い `except` は ruff の `BLE001` で落とす
- probe: ERR-01-a, ERR-01-b
- 良い例:
  raise StageError("検証用の評価が終わっていません。status を実行してください")
- 悪い例:
  raise ValueError("bad")
  except Exception: pass

### ERR-02 外から来る JSON は workspace の load_* で検証してから使う

- 軸: E2
- 決定: plan.json・cases.json・approval.json・サブエージェントが書く JSON・result.json は `workspace` の `load_*` 関数だけで読み、`load_*` は `fsops.read_json` の結果を `plan.parse_*` か `contracts.parse_*` に渡して問題を全部集め、問題があれば `InvalidFileError` を投げる。
- 理由: 段ごとに JSON を読むと、検証の漏れた形のまま値が使われ、遠くの段で分かりにくいエラーになる
- 強制: structure — 構造検査が `fsops.read_json` の呼び出しを `workspace` だけに、`json.loads` を `fsops` と `checks` だけに限る
- probe: ERR-02-a
- 良い例:
  proposal = workspace.load_proposal(where, number, train_ids)
- 悪い例:
  proposal = fsops.read_json(where.proposal_path(number))  # learn.py

## STATE 状態とデータの流れ

### STATE-01 状態はファイルだけで持ち、進み具合は workspace が求める

- 軸: E3
- 決定: 進み具合を書いた状態ファイルを作らず、`workspace` がファイルの有無と結果のハッシュから進み具合を求め、`workspace` と `status` は `fsops` の `read_`・`list_`・`compute_` で始まる関数だけを呼ぶ。
- 理由: 状態ファイルとファイルの実体は食い違いうる。ファイルの有無から求めれば、途中で止まっても `status` が正しい続きを示す
- 強制: structure, review — 構造検査が `workspace`・`status` の `fsops` の呼び出しを照合する。状態ファイルを足していないかはレビューで確かめる
- probe: STATE-01-a
- 良い例:
  progress = workspace.compute_progress(where, model)  # status.py
- 悪い例:
  fsops.write_json(where.target_dir / "state.json", {"stage": "learn"})

### STATE-02 サブエージェントとの受け渡しはひな形と決めたファイル名だけで行う

- 軸: X4
- 決定: サブエージェントへのプロンプトは `prompts.render_prompt` で `templates/prompts/` のひな形から作り、ひな形の置き換えの名前は `prompts.TEMPLATES` の表と一致させ、サブエージェントの出力は `layout` の `RESPONSE_FILE`・`GRADE_FILE`・`PROPOSAL_FILE`・`AUDIT_FILE` の名前にし、名前に `report` を含めない。
- 理由: プロンプトの文を Python に書くと、文言の修正が段のモジュールに散らばる。サブエージェントは `report` を含む名前のファイルを書けない（research.md）
- 出典: research.md の「Claude Code のサブエージェント」
- 強制: test, review — `tests/test_prompts.py` がひな形と表の一致を確かめる。プロンプトの文を Python に書いていないかはレビューで確かめる
- probe: STATE-02-a
- 良い例:
  text = prompts.render_prompt("grader", {"case_prompt": case.prompt, ...})
- 悪い例:
  text = f"次のケースを採点してください: {case.prompt}"

### STATE-03 学習役には学習用だけを見せ、テスト用は最後に1回だけ使う

- 軸: X6
- 決定: 分割は `splitting.compute_split` だけが決め、学習役の証拠（evidence.md）とプロンプトには学習用のケースだけを入れ、テスト用のケースは最後の評価でだけ評価し、`learn-check` は候補に足された20文字以上の行が検証用・テスト用の文と一致したら候補を落とす。
- 理由: 学習役が検証用・テスト用を見ると、採否とテストの結果が改善の実力ではなく暗記を測る
- 出典: research.md の「評価データの分け方（学習用・検証用・テスト用）」
- 強制: test, review — `tests/test_splitting.py` が分割の再現性を、`tests/test_learn.py` が証拠の範囲と写しの検出を、`tests/test_status.py` がテスト用の評価の時期を確かめる
- probe: STATE-03-a
- 良い例:
  cases = approved.list_cases(plan.TRAIN)  # learn.py
- 悪い例:
  cases = model_cases  # 全分割を証拠に入れる

## ASYNC 非同期と並行

### ASYNC-01 補助 CLI は並行処理を書かない

- 軸: E4
- 決定: 補助 CLI は `threading`、`concurrent`、`asyncio`、`multiprocessing` を import せず、並行に動かすのはスキルが同時に起動するサブエージェントだけにする。
- 理由: CLI の中の並行処理は、検査コマンドの出力の順番と失敗の扱いを揺らし、テストを不安定にする。並行が要る重い処理はサブエージェントの実行である
- 強制: structure — 構造検査が import を照合する
- probe: ASYNC-01-a
- 良い例:
  for run in runs: results.append(_collect_one(run))
- 悪い例:
  with ThreadPoolExecutor() as pool: pool.map(_collect_one, runs)

## OPS ログ・設定・セキュリティ・表示

### OPS-01 結果は標準出力、エラーは標準エラーに出し、status の行は決めた書き出しだけを使う

- 軸: E5, X1
- 決定: 結果は標準出力、エラーは `エラー: ` を付けて標準エラーに出し、終了コードは成功 0・失敗 1・引数の誤り 2（argparse の既定）にし、`logging` を使わず、`status` の出力の各行は `status.LINE_KINDS` のどれかで始める。
- 理由: スキルは status の行の書き出しで次の手を読み分ける。新しい書き出しや出力先の揺れは、スキルの手順を黙って壊す
- 強制: test, structure — `tests/test_status.py` が全行の書き出しを確かめる。`logging` の import は構造検査が落とす
- probe: OPS-01-a, OPS-01-b
- 良い例:
  return "\n".join([header, "段階: 最初の評価", f"次: {command}"])
- 悪い例:
  return "Next step -> run eval-prepare"

### OPS-02 設定は plan.json だけから読み、環境変数を読まない

- 軸: E6
- 決定: 評価の設定（回数、上限、sandbox の形、検査）は plan.json だけから読み、`os.environ` と `os.getenv` は `proc` が外部コマンドに環境を渡すときだけ使う。
- 理由: 環境変数で振る舞いが変わると、同じ計画でも人ごとに結果が変わり、報告から再現できない
- 強制: structure — 構造検査が `os.environ` と `os.getenv` を `proc` だけに限る
- probe: OPS-02-a
- 良い例:
  runs = model.budget.runs_per_case
- 悪い例:
  runs = int(os.getenv("TUNE_RUNS", "1"))

### OPS-03 人に見せる文言は日本語で書き、表と率は render の関数で作る

- 軸: E7
- 決定: 人に見せる文言（エラー、status、Markdown）は日本語で書き、表は `render.render_table`、率は `render.render_rate`、一覧は `render.render_bullets` で作り、日付は `cli` が引数として段に渡す。
- 理由: 表や率の書き方が段ごとに分かれると、plan.md・compare.md・report.md の読み方が揃わない
- 強制: review — レビューで確かめる
- 機械化しない理由: 文言が日本語として自然か、人に見せる文言かどうかは意味の判断が要るため
- probe: なし
- 良い例:
  render.render_table(["版", "合格率"], [[v, render.render_rate(r)] for v, r in rows])
- 悪い例:
  f"{v}: {rate * 100:.1f}%"

### OPS-04 評価を進める段は、最初に承認済みの計画を読む

- 軸: E8
- 決定: `evaluate`・`learn`・`decide`・`audit`・`report` の公開関数は、最初に `workspace.load_approved` を呼んで承認済みの計画を得て、検査の `command` は実行の sandbox だけを作業ディレクトリにして動かし、対象スキルを書き換えるのは `report.apply` だけにする。
- 理由: 承認されていない計画で評価を進めると、人の知らない検査コマンドが動き、人の知らない基準でスキルが変わる
- 強制: structure, test — 構造検査が公開関数の `load_approved` の呼び出しを照合する。`tests/test_evaluate.py` が `command` の作業ディレクトリを確かめる
- probe: OPS-04-a, OPS-04-b
- 良い例:
  def decide(where: layout.Layout, number: int, today: str) -> str:
      model = workspace.load_approved(where)
- 悪い例:
  def decide(where, number, today):
      model = workspace.load_plan(where)

## TEST テスト

### TEST-01 モジュールごとに tests/test_<モジュール>.py と <名前>Test クラスを置く

- 軸: F1, F2
- 決定: `tune_kit` の各モジュールに `tests/test_<モジュール>.py` を1つ置き、その中に `unittest.TestCase` を継承した `<モジュール名の PascalCase>Test` クラスを置き、テストの関数名は `test_<確かめること>` にする。
- 理由: テストの置き場と名前が揺れると、変更のときにどのテストを見ればよいかが分からなくなる
- 強制: structure — 構造検査がファイルとクラスの有無を照合する
- probe: TEST-01-a
- 良い例:
  class SplittingTest(unittest.TestCase):
      def test_same_input_gives_same_split(self) -> None:
- 悪い例:
  class TestSplit(unittest.TestCase): ...

### TEST-02 モックを使わず、support.py の部品と一時ディレクトリで確かめる

- 軸: F3, F4
- 決定: テストは `unittest.mock` と差し替えを使わず、`tests/support.py` の関数で一時ディレクトリに作ったリポジトリ・計画・ケース・サブエージェントの出力と、本物の git で確かめる。
- 理由: モックは実際のファイルの形との食い違いを隠す。部品を support.py に集めると、テストデータの作り方が揃う
- 強制: structure, review — `unittest.mock` と `mock` の import は構造検査が落とす。部品の置き場はレビューで確かめる
- probe: TEST-02-a
- 良い例:
  where = support.make_target(self.root, cases=support.sample_cases(6))
- 悪い例:
  from unittest import mock

### TEST-03 検査の種類とサブコマンドを足したら、決めた名前のテストを足す

- 軸: F5
- 決定: `checks.KINDS` に種類を足したら `tests/test_checks.py` に `test_kind_<種類>` を、`cli.COMMANDS` にサブコマンドを足したら `tests/test_cli.py` に `test_command_<サブコマンドの - を _ にした名前>` を足す。
- 理由: 新しい種類やサブコマンドのテストの有無が人ごとに分かれると、動かない種類が配られる
- 強制: structure — 構造検査が `KINDS`・`COMMANDS` とテストの関数名を照合する
- probe: TEST-03-a
- 良い例:
  def test_kind_regex(self) -> None:
- 悪い例:
  # KINDS に "regex" を足し、テストは足さない

## PROC 作業手順

### PROC-01 サブコマンドを足すときは置き場から入口の順に作る

- 軸: G1
- 決定: サブコマンドを足すときは、`layout.py`（置き場）→ `contracts.py`（受け渡しがあれば）→ 段のモジュール → `status.py` → `cli.py` → テスト → `structure_check.py` の表と architecture.md の許可表 → SKILL.md の表、の順に作る。
- 理由: 入口から作ると、置き場や契約が決まらないまま仮の名前が入り、後で全部を書き換えることになる
- 強制: doc — AGENTS.md と実装用スキルの手順に書く
- 機械化しない理由: 作った順番は差分に残らないため
- probe: なし
- 良い例:
  1. layout.py に置き場を足す 2. 段のモジュール 3. status 4. cli
- 悪い例:
  1. cli.py にサブコマンドを足し、中身は後で考える

### PROC-02 波及の対応表の組は同じ変更で変える

- 軸: G2
- 決定: 次の表の左を変えたら、右を同じ変更で変える。
  | 変えるもの | 一緒に変えるもの |
  |---|---|
  | `checks.KINDS` | `plan.py` の種類ごとの必須項目、`make docs`（check-kinds.md）、`tests/test_checks.py` |
  | `templates/prompts/` のひな形 | `prompts.TEMPLATES`、値を作る段のモジュール |
  | `contracts.AGENTS` | `kit/claude/agents/<名前>.md`、SKILL.md のサブエージェントの表 |
  | `status.LINE_KINDS` か status の `次:` の行 | SKILL.md の「繰り返すこと」の表 |
  | plan.json・cases.json の形 | `plan.SCHEMA_VERSION`、`references/plan-schema.md`、ADR |
  | モジュールの追加・import の変更 | `structure_check.py` の表、architecture.md の許可表 |
- 理由: 片方だけを変えると、CLI と文書・スキルが食い違い、スキルを使うエージェントが古い手順に従う
- 強制: review — レビューで両側のファイルを突き合わせる
- 機械化しない理由: 組の一部（ひな形と表、KINDS と文書、AGENTS と定義）は他のルールの検査で縛るが、status の行と SKILL.md の手順の対応は意味の判断が要るため
- probe: なし
- 良い例:
  # status に「次: 人に聞く」を足し、SKILL.md の表にも同じ行を足す
- 悪い例:
  # status の行だけを変える

### PROC-03 道具の版は Makefile で固定し、上げるときは ADR を書く

- 軸: G3
- 決定: ruff と mypy の版は `Makefile` の `RUFF`・`MYPY` の変数にだけ書き、版を上げるときは ADR を書いてから変数を変え、`make check` を通す。
- 理由: 版が人ごとに違うと、整形と lint の結果が揺れる
- 強制: review — `Makefile` は保護ファイルなので、変更はレビューで確かめる
- 機械化しない理由: 版を上げてよいかは互換性の判断が要るため
- probe: なし
- 良い例:
  RUFF := uvx ruff@0.17.1
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
  docs/design/adr/0009-*.md を書いてから rules.md を変える
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

### PROC-06 plan.json と cases.json の形を変えたら SCHEMA_VERSION を上げる

- 軸: X2
- 決定: plan.json か cases.json の項目を足す・消す・意味を変えるときは `plan.SCHEMA_VERSION` を1上げ、`references/plan-schema.md` と ADR を同じ変更で書き、`plan.parse_plan` は `schema_version` が `SCHEMA_VERSION` と違う計画を問題として返す。
- 理由: 古い形の計画を新しい CLI が黙って読むと、項目の意味がずれたまま評価が進む
- 強制: test, review — `tests/test_plan.py` が違う版の計画を問題にすることを確かめる。版を上げたかはレビューで確かめる
- probe: PROC-06-a
- 良い例:
  SCHEMA_VERSION = 2  # sandbox に "repo" を足した（ADR 0010）
- 悪い例:
  # plan.json に新しい項目を足し、版は 1 のまま

### PROC-07 人が決める場面はスキルに書き、AskUserQuestion で聞く

- 軸: X5
- 決定: 人が決める場面（計画の承認、データの直しの採否、最良の版の適用）は `skill-tune` の SKILL.md の「人が決める場面」の表に書き、AskUserQuestion で聞き、答えを得る前に `approve`・`data-fix`・`apply` を実行しない。
- 理由: 正解やゴールを変える判断と、対象スキルを書き換える判断をエージェントが代わりに行うと、人の意図と違う基準でスキルが変わる
- 強制: review — SKILL.md の差分をレビューで確かめる
- 機械化しない理由: スキルの手順が人に聞いてから実行する形になっているかは、文の意味の判断が要るため
- probe: なし
- 良い例:
  | data-fix | audit.md を見せ、適用する指摘を AskUserQuestion で聞く |
- 悪い例:
  監査役の指摘はすべて data-fix --apply で適用する

## TOOL 道具と自動化

### TOOL-01 整形は ruff format に任せる

- 軸: H1
- 決定: Python のファイルの整形（字下げ、引用符、改行の位置、import の並び）は `ruff format` と `ruff check --fix` に任せ、`make check` は `ruff format --check` で整形済みかを確かめる。
- 理由: 整形を人が決めると、差分に関係の無い書き換えが混ざる
- 出典: research.md の「ruff 0.17.1」
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
- 決定: manifest の `protected` にあるファイル（`Makefile`、`pyproject.toml`、`scripts/structure_check.py`、`.claude/settings.json`、`.foundation/**`、`docs/design/rules.md`、`docs/design/enforcement-matrix.md`）は、ルールの変更として承認された作業の中でだけ変え、例外としてモジュール・段・JSON の項目を足す作業では `scripts/structure_check.py` の登録の表（`SHARED`、`STAGES`、`ENTRY`、`APPROVED_STAGES`、`KEY_READERS`、`WRAPPER_KEYS`）に要素を足すことだけを許す。
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

揺れない軸、またはこの分野に無い軸と、その理由を書く。

| 軸 | 理由 |
|---|---|
