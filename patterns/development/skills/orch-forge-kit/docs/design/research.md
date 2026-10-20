# orch-forge-kit の技術調査

採用した推奨には出典を付け、確認の状態を書いている。バージョンは、レジストリのコマンドで確かめた値である。確認した日はすべて 2026-10-20 である。

この基盤は、配布物（補助 CLI、スキル、サブエージェント、ひな形）と、配布物を作るための開発の道具に分かれる。配布物は対象のリポジトリで動くため、依存を持たない（Python の標準ライブラリだけで動く）。開発の道具は、版を固定して `uvx` で呼ぶ。

## Claude Code のスキル 2.1.296

- 確認方法：`claude --version` → `2.1.296 (Claude Code)`、`npm view @anthropic-ai/claude-code version` → `2.1.304`。https://code.claude.com/docs/en/skills.md を取得して読んだ
- 確認の状態：確認済み
- 公式の推奨：
  - スキルは `.claude/skills/<名前>/SKILL.md` に置く。frontmatter の項目は任意で、`description` だけが推奨される。`description` と `when_to_use` は一覧で 1,536 文字までに切り詰められる（[Frontmatter reference](https://code.claude.com/docs/en/skills#frontmatter-reference)）
  - `disable-model-invocation: true` で、Claude が自動でスキルを読み込むのを止められる。人は `/名前` で呼べる
  - `allowed-tools` は、スキルを呼んだターンの間、確認なしで使えるツールを決める
  - `context: fork` はスキルをサブエージェントで動かす
  - 「Keep `SKILL.md` under 500 lines. Move detailed reference material to separate files.」
  - プロジェクトのスキルは、起動したディレクトリと、その親からリポジトリのルートまでの `.claude/skills/` から読み込まれる（[Load skills in monorepos and subdirectories](https://code.claude.com/docs/en/skills#discovery-from-parent-and-nested-directories)）
- 採用するもの：
  - 配布するスキルは `forge-goals`・`forge-build`・`forge-run` の3つにし、`disable-model-invocation: true` と `allowed-tools: Bash(python3 .forge/forge.py *)` を付ける（STR-05、[ADR 0004](adr/0004-three-human-invoked-skills.md)）
  - 生成するオーケストレーションスキルも `disable-model-invocation: true` にし、500行以内、参照は `references/` の1階層にする（バンドルの決まり B03・B04、STR-06、[ADR 0008](adr/0008-fixed-bundle-shape.md)）
- 採用しないもの：`context: fork`。人に聞く手順（AskUserQuestion）とサブエージェントの起動は、メインのセッションで動かす必要があるため
- ツールにできないこと：参照ファイルの深さと、決まった節（`## 手順` など）の有無は公式の検査が無い → 配布物は `scripts/structure_check.py`、生成物は `bundle.RULES` の検査で確かめる

## Claude Code のサブエージェント 2.1.296

- 確認方法：https://code.claude.com/docs/en/sub-agents.md と https://code.claude.com/docs/en/tools-reference.md を取得して読んだ
- 確認の状態：確認済み
- 公式の推奨：
  - 定義は `.claude/agents/<名前>.md`。必須は `name` と `description` だけ。識別は `name` で行い、ファイル名と一致しなくてよい（[Supported frontmatter fields](https://code.claude.com/docs/en/sub-agents#supported-frontmatter-fields)）
  - `tools` を省くと、サブエージェントが使える全ツールを継承する。`tools` に `Agent` が無ければ、そのサブエージェントはさらにサブエージェントを起動できない
  - 既定で、サブエージェントはメインの会話から3層下までサブエージェントを起動できる（[Let subagents spawn their own subagents](https://code.claude.com/docs/en/sub-agents#let-subagents-spawn-their-own-subagents)）
  - サブエージェントからは `AskUserQuestion` と `Workflow` が常に除かれる（[Available tools](https://code.claude.com/docs/en/sub-agents#available-tools)）
  - `omitClaudeMd: true` で、サブエージェントに CLAUDE.md を読ませない（v2.1.271 以降）
  - `permissionMode` で、サブエージェントの権限のモードを変えられる
  - 同時に動かせるサブエージェントは既定で20まで
  - macOS・Linux・WSL では、Glob と Grep が既定のツールに無く、検索は Bash の `find`・`grep`（組み込みの `bfs`・`ugrep`）で行う。Glob・Grep が戻るのは、`--tools`・`--allowedTools` で名前を挙げたときと、サブエージェントの `tools` に Glob・Grep を書き、Bash を外したとき（[Glob tool behavior](https://code.claude.com/docs/en/tools-reference#glob-tool-behavior)）。2.1.296 の `claude -p` の init の `tools` にも Glob・Grep が無いことを確かめた
- 採用するもの：
  - この基盤のサブエージェントは、設計役・構築役・採点役・分析役の4つにする。どれも `tools` を列挙し、`Skill` と `Agent` を入れない（STR-05、[ADR 0002](adr/0002-roles-and-claude-p-executor.md)）
  - 採点役と分析役は `omitClaudeMd: true` にする。設計役と構築役は対象のリポジトリの決まりを知る必要があるので CLAUDE.md を読ませる（[ADR 0002](adr/0002-roles-and-claude-p-executor.md)）
  - 生成するオーケストレーションスキルのサブエージェントは、名前を `<スキル名>-<役>` にし、`tools` を Read・Write・Edit・Glob・Grep・Bash の中から列挙し、`Agent` を入れない（入れ子を作らない。バンドルの決まり B06〜B08、[ADR 0008](adr/0008-fixed-bundle-shape.md)）
  - 生成するスキルのファイルに Glob・Grep を書かせず、Bash を持つサブエージェントに Glob・Grep を持たせない（バンドルの決まり B13、[ADR 0012](adr/0012-no-glob-grep-with-bash.md)）
  - 人に聞く手順はメインのセッションで動くスキルに置く（PROC-07）
- 採用しないもの：`permissionMode` の指定（[ADR 0006](adr/0006-no-permission-widening.md)）、`isolation: worktree`（評価は補助 CLI が作るコピーの中で行うため）
- ツールにできないこと：サブエージェントが読めるパスを限定する仕組みは無い → 読む範囲はプロンプトの指示で決める

## Claude Code のヘッドレス実行（claude -p）2.1.296

- 確認方法：https://code.claude.com/docs/en/headless.md、https://code.claude.com/docs/en/cli-reference.md、https://code.claude.com/docs/en/agent-sdk/typescript.md を取得して読んだ。あわせて実機で試した（下の「実機の試験」）
- 確認の状態：確認済み
- 公式の推奨：
  - `claude -p` は `--bare` を付けなければ、対話のセッションと同じくスキルとサブエージェントを読み込む
  - `--output-format stream-json --verbose` で、メッセージを1行1件の JSON で出す。サブエージェントのメッセージは `parent_tool_use_id` に、起動した Agent の `tool_use` の ID を持つ。メインの会話のメッセージは `null` を持つ。既定で、サブエージェントの `tool_use` と `tool_result` が出る（[Follow subagent messages](https://code.claude.com/docs/en/headless#follow-subagent-messages)）
  - `task_started` のメッセージは `spawn_depth` を持つ。メインの会話が起動したサブエージェントは 1（[SDKTaskStartedMessage](https://code.claude.com/docs/en/agent-sdk/typescript#sdktaskstartedmessage)）
  - 最後の `result` のメッセージは、`subtype`（成功は `success`、上限で止まると `error_max_budget_usd` など）、`is_error`、`duration_ms`、`num_turns`、`total_cost_usd`（推定）、`permission_denials` を持つ（[SDKResultMessage](https://code.claude.com/docs/en/agent-sdk/typescript#sdkresultmessage)）
  - `--max-budget-usd` で、推定の費用が上限に達したら止める。サブエージェントの費用も数える
  - `--permission-prompts none` で、人の答えが要るツール（`AskUserQuestion`）を外し、確認が要る操作を拒否する（v2.1.259 以降。[Turn off permission prompts in unattended runs](https://code.claude.com/docs/en/headless#turn-off-permission-prompts-in-unattended-runs)）
  - `--permission-mode acceptEdits` で、作業ディレクトリの中の編集を確認なしで許す。v2.1.302 以降、モードを指定しない `-p` は Manual モードで始まる
  - `--append-system-prompt-file` で、既定のシステムプロンプトに文を足せる
  - プロンプトに `/<スキル名> <引数>` を書くとスキルを呼べる
- 実機の試験（2026-10-20、2.1.296、haiku）：`disable-model-invocation: true` のスキルが Agent ツールでカスタムサブエージェントを1つ起動する小さなリポジトリで、`claude -p "/orch" --output-format stream-json --verbose --permission-mode acceptEdits --permission-prompts none --max-budget-usd 0.5` を実行した。結果は次のとおり
  - スキルは `/orch` で呼ばれ、サブエージェントがファイルを書いた（終了コード 0、$0.011、6.5 秒）
  - メインの会話の Agent の `tool_use` の `input` に `subagent_type`（`demo-writer`）と `description` があった
  - サブエージェントの Write の `tool_use` は、`parent_tool_use_id` に Agent の ID を持っていた
  - `task_started` に `spawn_depth: 1` があった
  - `result` に `subtype: success`、`total_cost_usd`、`duration_ms`、`num_turns` があった。文書に無い `subagent_stats`（起動数の内訳）もあった
- 採用するもの：
  - 評価の実行役は、補助 CLI が `claude -p` を起動する形にする。引数は `execute.command` だけで組み立てる（OPS-05、[ADR 0002](adr/0002-roles-and-claude-p-executor.md)）
  - 実行の記録は stream-json で保存し、文書にある項目（Agent の `tool_use`、`parent_tool_use_id`、`task_started` の `spawn_depth`、`result` の項目）だけから指標を求める（[ADR 0009](adr/0009-measure-from-documented-stream-fields.md)）
  - 実行役には `--permission-mode acceptEdits` と `--permission-prompts none` を付け、`--max-budget-usd` で1回の費用に上限を付ける（OPS-05、[ADR 0006](adr/0006-no-permission-widening.md)）
  - 人に聞く場面の扱いは、`--append-system-prompt-file` で渡すひな形（`executor-system.md`）に書く
- 採用しないもの：
  - `subagent_stats`（文書に無く、版で変わりうるため）
  - `--forward-subagent-text`（指標と採点に要るのは `tool_use` と最後の返答で、サブエージェントの文章は出力を大きくするだけのため）
  - `--bare`（スキルとサブエージェントの自動の読み込みが止まるため）
- ツールにできないこと：`claude -p` の中では人の承認を挟めない → 人に聞く場面は、生成するスキルの「## 人に確かめること」に人が答えられないときの既定の答えを書かせ（バンドルの決まり B05）、実行役はその既定で進める

## Claude Code の CLAUDE.md の読み込み 2.1.296

- 確認方法：https://code.claude.com/docs/en/memory.md を取得して読んだ
- 確認の状態：確認済み
- 公式の推奨：CLAUDE.md は、ファイルシステムのルートから作業ディレクトリまでのすべての階層から読み込まれ、つなげて文脈に入る（「Across the directory tree, content is ordered from the filesystem root down to your working directory.」）
- 採用するもの：評価用のコピーは、対象のリポジトリの外（OS の一時ディレクトリの下の `orch-forge/`）に置く。リポジトリの中に置くと、実行役が元のリポジトリの CLAUDE.md も読み込み、本番と条件が変わるため（[ADR 0003](adr/0003-copies-outside-repository.md)）
- 採用しないもの：`claudeMdExcludes` での除外（対象のリポジトリの設定を変える必要があるため）
- ツールにできないこと：ユーザー単位の `~/.claude/CLAUDE.md`、スキル、サブエージェントは実行役にも読み込まれる → 本番の開発者と同じ条件として受け入れ、報告に実行の条件を書く

## Claude Code の権限と保護されたパス 2.1.296

- 確認方法：https://code.claude.com/docs/en/permissions.md と https://code.claude.com/docs/en/permission-modes を読んだ。あわせて、この会話の auto モードで `claude -p --permission-mode acceptEdits` の起動が「Create Unsafe Agents」として拒否され、利用者が許可の規則を足して通ったことを確かめた
- 確認の状態：確認済み
- 公式の推奨：`.claude` への書き込みは保護されたパスで、`bypassPermissions` 以外では自動で許可されない。`dontAsk` と `--permission-prompts none` は、許可されていない操作を拒否する
- 採用するもの：
  - サブエージェント（設計役・構築役・分析役）が書くのは `.forge/` の下だけにし、`.claude/` に写すのは補助 CLI の `install` と `decide --adopt` だけにする（OPS-04、[ADR 0006](adr/0006-no-permission-widening.md)）
  - auto モードで `execute` が拒否されたときは、利用者に許可の規則（`Bash(python3 .forge/forge.py *)`）を足してもらうよう README と forge-run に書く
- 採用しないもの：`bypassPermissions`、`--dangerously-skip-permissions`（OPS-05）
- ツールにできないこと：Bash でのファイルの書き換えは hooks で止められない → 実行役の `--allowedTools` は charter で人が承認した一覧だけにする

## Python 3.9.6

- 確認方法：`python3 --version` → `Python 3.9.6`
- 確認の状態：確認済み
- 公式の推奨：`from __future__ import annotations` の下で PEP 604 の `X | None` を書ける。`dict[str, int]` などの組み込みの総称型は 3.9 から使える
- 採用するもの：配布物は Python 3.9 の標準ライブラリだけで動かす（DEP-03、TOOL-05）。全モジュールに `from __future__ import annotations` を書く（CODE-03）
- 採用しないもの：3.10 以降の構文と API（`match` 文、`zip(strict=True)`、`sys.stdlib_module_names`）
- ツールにできないこと：標準ライブラリの一覧は 3.9 では `sys` から取れない → 構造検査に使ってよいモジュールの表を持つ（DEP-03）

## uv 0.11.14

- 確認方法：`uv --version` → `uv 0.11.14`
- 確認の状態：確認済み
- 公式の推奨：`uvx <ツール>@<版>` で、版を固定したツールを使い捨ての環境で動かせる
- 採用するもの：ruff と mypy を `uvx ruff@0.17.1`、`uvx mypy@1.20.2` で呼ぶ（PROC-03、TOOL-05）
- 採用しないもの：プロジェクトの仮想環境と lockfile。配布物が依存を持たないため
- ツールにできないこと：なし

## ruff 0.17.1

- 確認方法：`uvx ruff@0.17.1 --version` → `ruff 0.17.1`。PyPI の最新も 0.17.1（`curl -s https://pypi.org/pypi/ruff/json`）。使うルールは `uvx ruff@0.17.1 rule <コード>` で実在を確かめた（T201、TID252、D100、D104、ERA001、BLE001、C901、PLR0913、PLR0912、PLR0911、PLR0915、N802、N806、UP045、I001、E501）
- 確認の状態：確認済み
- 公式の推奨：formatter と linter を兼ねる。`target-version` で対象の Python の版を決める
- 採用するもの：整形（TOOL-01）と、命名（NAM-01）、import（CODE-02）、型注釈の書き方（CODE-03）、大きさ（CODE-04）、docstring とコメント（CODE-05）、例外の捕まえ方（ERR-01）、print（DEP-04）の lint
- 採用しないもの：`D` 群の全体（docstring は D100 と D104 だけを求める）
- ツールにできないこと：import の許可表、副作用の置き場、ファイルの配置、文字列の置き場は判定できない → 構造検査（`scripts/structure_check.py`）で縛る

## mypy 1.20.2

- 確認方法：`uvx mypy@1.20.2 --version` → `mypy 1.20.2 (compiled: yes)`。PyPI の最新は 2.4.0 だが `requires_python` が `>=3.10` で、`python_version = 3.9` を対象にできない
- 確認の状態：確認済み
- 公式の推奨：`strict = true` で、型注釈の無い関数と Any の暗黙の使用を落とす
- 採用するもの：`strict`、`python_version = 3.9`、`warn_unreachable`（CODE-03、TOOL-05、[ADR 0005](adr/0005-mypy-1-20-for-python-3-9.md)）
- 採用しないもの：mypy 2.x
- ツールにできないこと：なし

## unittest 3.9.6（標準ライブラリ）

- 確認方法：Python 3.9.6 の標準ライブラリ
- 確認の状態：確認済み
- 公式の推奨：`python3 -m unittest discover` でテストを集めて回す
- 採用するもの：テストは unittest で書き、モックを使わず、本物の git と一時ディレクトリで確かめる。`claude -p` の代わりは、記録した stream-json を書く偽の起動関数（`tests/support.py`）で置き換える（TEST-01、TEST-02）
- 採用しないもの：pytest（依存を足すため）、`unittest.mock`
- ツールにできないこと：なし

## git 2.50.1

- 確認方法：`git --version` → `git version 2.50.1 (Apple Git-155)`（評価用のコピーの差分を取るために、補助 CLI が実行時に必要とする）
- 確認の状態：確認済み
- 公式の推奨：`git status --porcelain` と `git diff` は機械で読める形で出せる
- 採用するもの：評価用のコピーごとに `git init` して基準のコミットにタグを付け、差分はタグからの `git diff --cached` で取る。実行役がコミットしても差分を失わない
- 採用しないもの：元のリポジトリの git を使うこと（元の履歴を汚さないため）
- ツールにできないこと：なし
