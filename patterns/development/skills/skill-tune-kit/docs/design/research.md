# skill-tune-kit の技術調査

採用した推奨には出典を付け、確認の状態を書いている。バージョンは、レジストリのコマンドで確かめた値である。確認した日はすべて 2026-10-21 である。

この基盤は、配布物（補助 CLI、スキル、サブエージェント）と、配布物を作るための開発の道具に分かれる。配布物は利用者のリポジトリで動くため、依存を持たない（Python の標準ライブラリと git だけで動く）。開発の道具は、版を固定して `uvx` で呼ぶ。

## Claude Code のスキル

- 確認方法：https://code.claude.com/docs/en/skills を取得して読んだ（サブエージェントによる調査。取得した Markdown を引用で確かめた）
- 確認の状態：確認済み
- 公式の推奨：
  - スキルは `.claude/skills/<名前>/SKILL.md` に置く。frontmatter の項目はすべて任意で、`description` だけが推奨される（「All fields are optional. Only `description` is recommended so Claude knows when to use the skill.」）
  - `disable-model-invocation: true` で、Claude が自動でスキルを読み込むのを止め、`/名前` で人が呼ぶ形にできる（「Set to `true` to prevent Claude from automatically loading this skill. Use for workflows you want to trigger manually with `/name`.」）
  - `allowed-tools` は、スキルを呼んだターンの間だけ、確認なしで使えるツールを決める。使えるツールを制限はしない（「Tools Claude can use without asking permission during the turn that invokes this skill. The grant clears when you send your next message.」）
  - `argument-hint` は補完のヒントになり、本文の `$ARGUMENTS` は呼び出しの引数に置き換わる
  - 「Keep `SKILL.md` under 500 lines. Move detailed reference material to separate files.」
- 採用するもの：
  - 配布するスキルは `skill-tune` の1つにし、`disable-model-invocation: true` を付ける（STR-05、[ADR 0004](adr/0004-one-human-invoked-skill.md)）
  - `allowed-tools: Bash(python3 .tune/tune.py *)` で補助 CLI の呼び出しの確認を省く。許可はターンの間だけなので、README に `settings.local.json` での許可の足し方を書く
  - SKILL.md は500行以内にし、詳細は `references/` に1階層で置く（STR-05）。対象スキルの候補にも同じ上限を課す（learn-check の検査）
- 採用しないもの：`context: fork`（スキル自体をサブエージェントで動かす）。人に聞く手順（AskUserQuestion）はメインのセッションでしか動かないため
- ツールにできないこと：参照ファイルの深さの推奨は公式の文書に無い。1階層はこの基盤の決定である

## Claude Code のサブエージェント

- 確認方法：https://code.claude.com/docs/en/sub-agents を取得して読んだ。あわせて、サブエージェントが書けるファイル名を実験で確かめた（下記）
- 確認の状態：確認済み
- 公式の推奨：
  - 定義は `.claude/agents/<名前>.md`。必須は `name` と `description` だけ（「Only `name` and `description` are required.」）
  - `tools` を省くと、サブエージェントが使える全ツールを継承する（「Inherits every tool available to subagents if omitted.」）
  - サブエージェントは既定でさらにサブエージェントを起動できる（「up to three layers below the main conversation」）。`tools` から `Agent` を外せば起動できない
  - サブエージェントは AskUserQuestion を使えない（「The first filter removes these tools, even when listed in the `tools` field: … `AskUserQuestion`」）
  - サブエージェントは新しい文脈で始まり、親の会話を見ない（「Each subagent starts with a fresh, isolated context window. It doesn't see your conversation history」）。fork だけは例外
  - `omitClaudeMd: true` で CLAUDE.md を読ませずに始められる（v2.1.271 以降）
  - `model` には `sonnet`、`opus`、`haiku`、`fable`、完全なモデル ID、`inherit` を書ける
- 実験で確かめたこと（2026-10-21、Claude Code 2.1.296）：サブエージェントが Write ツールで `report.md` を書くと「Subagents should return findings as text, not write report files. Include this content in your final response instead.」で拒まれた。同じ試験で `response.md`、`answer.md`、`output.md`、`final-response.txt`、`audit.json` は書けた。拒む条件は公開の文書に無い
- 採用するもの：
  - 独立した役を4つ定義する：実行役（`tune-executor`）、採点役（`tune-grader`）、学習役（`tune-learner`）、監査役（`tune-auditor`）。どれも `tools` を列挙し、`Skill` と `Agent` を入れない（STR-05、[ADR 0002](adr/0002-subagent-roles.md)）
  - 実行役は実際の使われ方に合わせて CLAUDE.md を読ませ、採点役・学習役・監査役は `omitClaudeMd: true` にする（[ADR 0002](adr/0002-subagent-roles.md)）
  - サブエージェントの成果は、決めたファイル名（`response.md`、`grade.json`、`proposal.json`、`audit.json`）に書かせる。名前に `report` を使わない（STATE-02、[ADR 0005](adr/0005-subagent-writes-own-output.md)）
  - 人に聞く手順はメインのセッションで動くスキルに置く（PROC-07）
- 採用しないもの：`permissionMode` の指定。サブエージェントの権限は呼び出し側のセッションの設定に従わせる
- ツールにできないこと：サブエージェントが読めるパスを限定する仕組みは無い。読む範囲はプロンプトの指示で決め、学習役の出力は `learn-check` が検証用・テスト用の文の写しを検査する（STATE-03）

## Claude Code の権限と保護されたパス

- 確認方法：https://code.claude.com/docs/en/permission-modes の "Protected paths" 節を読んだ
- 確認の状態：確認済み
- 公式の推奨：`.claude` への書き込みは保護されたパスで、`bypassPermissions` などの限られたモード以外では自動で許可されない（「Writes to a small set of paths are never auto-approved, except in `bypassPermissions` mode and in interactive terminal sessions in plan mode with bypass permissions available.」）。settings の `permissions.allow` でも事前に許可できない
- 採用するもの：
  - 配布物の正本は `kit/claude/`（先頭にドットを付けない）に置き、`install.py` が利用者のリポジトリの `.claude/` へ写す（[ADR 0003](adr/0003-workspace-under-tune-dir.md)）
  - 評価用の作業場所と、学習役が直すスキルの版は `.tune/` の下に置く。サブエージェントが保護されたパスに書かずに済むため
  - 対象スキルを書き換えるのは補助 CLI の `apply` だけにする（OPS-04）
- 採用しないもの：なし
- ツールにできないこと：なし

## Claude Code のヘッドレス実行

- 確認方法：https://code.claude.com/docs/en/headless を読んだ。`claude --version` → 2.1.296、`npm view @anthropic-ai/claude-code version` → 2.1.306
- 確認の状態：確認済み
- 公式の推奨：`claude -p` は `--bare` を付けなければ、対話のセッションと同じくスキルとサブエージェントを読み込む（「Without it, `claude -p` discovers and loads them as an interactive session would」）
- 採用するもの：この基盤の収束テストは `claude -p` で回す（[convergence-report.md](convergence-report.md)）
- 採用しないもの：`--bare`（スキルの自動検出が止まるため）。配布するスキルの評価の実行役に `claude -p` を使うこと（人の承認を挟む手順を試せず、権限の設定も利用者ごとに要るため。[ADR 0002](adr/0002-subagent-roles.md)）
- ツールにできないこと：なし

## Python 3.9.6

- 確認方法：`python3 --version` → `Python 3.9.6`
- 確認の状態：確認済み
- 公式の推奨：`from __future__ import annotations` の下で、型注釈に PEP 604 の `X | None` と組み込みの総称型（`dict[str, int]`）を書ける
- 採用するもの：配布物は Python 3.9 の標準ライブラリだけで動かす（DEP-03、TOOL-05）。全モジュールの先頭に `from __future__ import annotations` を書く（CODE-02）。データの分割は `hashlib.sha256` で決める（STATE-03）
- 採用しないもの：3.10 以降の構文と API（`match` 文、`zip(strict=True)`、`dataclass(slots=True)`）
- ツールにできないこと：標準ライブラリの一覧は 3.9 では `sys` から取れない。構造検査に使ってよいモジュールの表を持つ（DEP-03）

## uv 0.11.14

- 確認方法：`uv --version` → `uv 0.11.14`
- 確認の状態：確認済み
- 公式の推奨：`uvx <ツール>@<版>` で、版を固定したツールを使い捨ての環境で動かせる
- 採用するもの：ruff と mypy を `uvx ruff@0.17.1`、`uvx mypy@1.20.2` で呼ぶ（TOOL-05）
- 採用しないもの：プロジェクトの仮想環境と lockfile。配布物が依存を持たないため
- ツールにできないこと：なし

## ruff 0.17.1

- 確認方法：PyPI の JSON（`https://pypi.org/pypi/ruff/json`）の `info.version` → 0.17.1（2026-10-15 公開、`requires_python` は `>=3.7`）。`uvx ruff@0.17.1 rule <コード>` で、使うルールの実在を確かめた（T201、TID252、D100、D104、ERA001、BLE001、C901、PLR0913、PLR0912、PLR0911、PLR0915、N801、N802、N806、N815、UP045、I001、E501、PLC0415、PTH123、ARG001、B006、RUF012）
- 確認の状態：確認済み
- 公式の推奨：formatter と linter を兼ねる。`target-version` で対象の Python の版を決める
- 採用するもの：整形（TOOL-01）と、命名（NAM-01）、import（CODE-02）、大きさ（CODE-04）、docstring とコメント（CODE-05）、例外の捕まえ方（ERR-01）、print（DEP-04）の lint
- 採用しないもの：`D` 群の全体（docstring は D100 と D104 だけを求める）
- ツールにできないこと：import の許可表、副作用の置き場、ファイルの配置、関数名の動詞は判定できない。構造検査（`scripts/structure_check.py`）で縛る

## mypy 1.20.2

- 確認方法：PyPI の JSON（`https://pypi.org/pypi/mypy/json`）の最新は 2.4.0 だが `requires_python` は `>=3.10` で、2.x は `python_version = 3.9` を対象にできない。1.x の最新は 1.20.2。`uvx mypy@1.20.2 --version` → `mypy 1.20.2 (compiled: yes)`
- 確認の状態：確認済み
- 公式の推奨：`strict = true` で、型注釈の無い関数と Any の暗黙の使用を落とす
- 採用するもの：`strict`、`python_version = 3.9`、`warn_unreachable`（CODE-03、TOOL-05、[ADR 0006](adr/0006-mypy-1-20-for-python-3-9.md)）
- 採用しないもの：mypy 2.x
- ツールにできないこと：なし

## unittest（Python 3.9.6 の標準ライブラリ）

- 確認方法：Python 3.9.6 の標準ライブラリ
- 確認の状態：確認済み
- 公式の推奨：`python3 -m unittest discover` でテストを集めて回す
- 採用するもの：テストは unittest で書き、モックを使わず、本物の git と一時ディレクトリで確かめる（TEST-01、TEST-02）
- 採用しないもの：pytest（依存を足すため）、`unittest.mock`
- ツールにできないこと：なし

## git 2.50.1

- 確認方法：`git --version` → `git version 2.50.1 (Apple Git-155)`。補助 CLI が実行時に必要とする
- 確認の状態：確認済み
- 公式の推奨：`git diff --cached --name-only -z` は機械で読める形で変更の一覧を出せる
- 採用するもの：評価用の作業場所（sandbox）ごとに `git init` して基準のコミットにタグを付け、実行役が変えたファイルと差分をタグからの `git diff --cached` で取る。実行役がコミットしても差分を失わない
- 採用しないもの：利用者のリポジトリの git を使うこと（元の履歴を汚さないため）
- ツールにできないこと：なし

## 評価データの分け方（学習用・検証用・テスト用）

- 確認方法：機械学習の一般的な手順（学習・検証・テストの3分割、テスト用は最後に1回だけ使う）を、スキルの改善に当てはめた。Claude Code の公式の記述は無い
- 確認の状態：確認済み（この基盤の決定として [ADR 0007](adr/0007-train-val-test-split.md) に書いた）
- 公式の推奨：なし
- 採用するもの：学習役には学習用だけを見せ、採否は検証用のスコアで機械的に決め、テスト用は最後に元の版と最良の版を1回ずつ測る（STATE-03、[ADR 0007](adr/0007-train-val-test-split.md)、[ADR 0008](adr/0008-mechanical-adoption.md)）
- 採用しないもの：交差検証（評価の回数が分割の数だけ増え、サブエージェントの起動回数が予算に収まらないため）
- ツールにできないこと：なし
