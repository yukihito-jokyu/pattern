# autoflow-kit の技術調査

採用した推奨には出典を付け、確認の状態を書いている。バージョンは、レジストリのコマンドで確かめた値である。確認した日はすべて 2026-10-21 である。

この基盤は、配布物（補助 CLI、スキル、サブエージェント、プロンプトのひな形）と、配布物を作るための開発の道具に分かれる。配布物は対象のリポジトリで動くため、依存を持たない（Python の標準ライブラリだけで動く）。開発の道具は、版を固定して `uvx` で呼ぶ。

最初の節は技術ではなく、ユーザーが参考に指定した記事である。オートフローの考え方（どこを機械に任せ、どこで人が介入するか）の根拠はすべてこの節に集める。

## 記事「How the Claude Code team does code review」（2026-10-15）

- 確認方法：https://claude.dev/blog/solving-code-review-at-anthropic/ を取得して読んだ（著者 Addy Osmani、Morgan Westlee Lunt、Qing Wang。カテゴリ Engineering）
- 確認の状態：確認済み
- 記事の主張（原文の引用と要約）：
  - ゴール：「we started optimizing for the minimum amount of human review time that doesn't raise reverts or incidents.」人の時間を測り、リバート率とインシデント率をガードレールにする
  - 検証：「We give Claude something it can run—like tests, a build or a screenshot to compare against the design—and ask it to show the output instead of saying it's done.」作成者は「Claude に検証手段を与えることがおそらく最も重要」と述べている
  - 新しいコンテキストのサブエージェントが差分をレビューする
  - 指摘の検証：「Several agents look for bugs at the same time. Then a separate group votes on each finding, and it only gets posted if enough of them agree it's real. Findings that are only about style, diagnostics, or cleanup get dropped.」
  - 重大度のタグは Important・Nit・Pre-existing。PR が持ち込んだものでないバグは Pre-existing として作成者の責任にしない
  - すべての指摘に回答が要る（直すか、理由を付けて閉じる）。未解決の指摘がある間はマージできない
  - リスクの段：低（文書、文言、フラグの後ろの追加）は人の承認不要、中（通常の変更、キャッシュ・自動更新・システムプロンプトなど繊細な領域）は1人、高は2人
  - 「The change sets the tier, not the author. A classifier reads the change and picks its risk tier.」2つ目の分類器が、段に関係なく人が要るかを判定する。オーナーが繊細と指定したパスと CI のワークフローは常に人が要る
  - 「An agent's approval never counts as a person's, either.」「Whoever prompted the change is on the hook for it.」「An approval covers one specific commit.」
  - PR テンプレートは「どう確かめたか」「どう戻すか」を聞く
  - マージキューは最新の main に変更を当てて全検査をやり直す
  - 収束の問題：「about 59% of it was code that had been there since the reviewer's first pass.」対策は「A round cap. After three rounds, the reviewer asks the author to step back and reconsider the approach.」「Diff-only re-review after the first few passes.」「Flag the class of bug, so the author fixes every instance, not one line.」「No repeats of findings already posted.」
  - 効果：1ラウンドで通る割合 65% → 78%、5ラウンド以上かかる割合 8.9% → 1.5%、平均のレビュー回数 2.08 → 1.32
  - インシデントは eval にし、人の反応で指摘の雑音を測る。優先順位は「まず本物のバグを捕まえ、次にラウンドを減らす」
  - 人が残る場面：「Deciding whether to build it.」（方向、好み、範囲）、「Reviewing risky code」（課金、自動更新、CI）、「Reviewing architecture that sets a pattern others will copy.」、「Reading the evidence.」（テストの出力、実行したコマンドとその結果、スクリーンショット、レビューの指摘。「If you can't say what the checks would miss, ask for a real review rather than a quick approval.」）、「Owning the outcome.」
  - 方向の転換は、完成した PR へのブロッキングコメントではなく、早い段階で別の方向を出す
  - 見逃しの扱い：「When a review misses something, we ask what the model didn't have in front of it and put the fix into a CLAUDE.md, a skill or a new check.」
  - 変更を小さくし、すべてを戻せるようにし、影響範囲（blast radius）で基準を決める
- 採用するもの：
  - 依頼から完了までを、機械の関所（順序、証拠、レビューの投票、リスクの段、ラウンドの上限）と、人の関所（H0〜H3）に分ける（GATE 節、[ADR 0002](adr/0002-autoflow-shape.md)）
  - 証拠は補助 CLI が検査コマンドを自分で実行して記録し、差分の版（git の tree）に結び付ける（GATE-04）
  - レビューは観点ごとの探索役を並列に起動し、別の検証役の投票で残す。文体・掃除だけの指摘は種類の段階で受け付けない（GATE-01 の `REVIEW` の表）
  - リスクの段は変更（差分のパス・大きさ・種類）から決め、AI の判定は段を上げる方向にだけ効かせる（GATE-06）
  - 承認は人の回答の原文付きで記録し、承認した tree と今の tree が一致するときだけコミットする（GATE-05）
  - ラウンドの上限3、2ラウンド目からの差分だけの再レビュー、バグの種類と他の箇所、既出の指摘を繰り返さない（GATE-01 の `REVIEW` の表）
  - 人の介入の回数とガードレール（差し戻し・中止・インシデント）を台帳に残し、`metrics` で数える。見逃しは `learn` で発生源（CLAUDE.md、REVIEW.md、プロファイル、検査）を直す提案にする
- 採用しないもの：
  - 低リスクの変更を人の承認なしで取り込むこと（ユーザーの指示で、自走の終点を「検証済みの変更」とし、コミットは人の承認の後にした。[ADR 0002](adr/0002-autoflow-shape.md)）
  - 2人目の承認の強制（ローカルの1人の作業で2人目を確かめる仕組みが無い → 高リスクでは報告に「2人目のレビューを勧める」と書く）
  - マージキュー、フラグ、段階的リリース（ホストとリリースの設定でありスキルでは実現できない → 報告の「戻し方」に書かせるだけにする）
- ツールにできないこと：AI が人の代わりに承認を記録することを、ローカルでは完全には防げない → 承認の記録を `decide` だけに限り、人の回答の原文を必須にし、スキルに「回答が無い・自動で閉じた質問は承認にしない」と書く（GATE-05、GATE-02、[ADR 0006](adr/0006-human-answer-record.md)）

## Claude Code の Code Review の文書（REVIEW.md、重大度、探索と検証）

- 確認方法：https://code.claude.com/docs/en/code-review.md、https://code.claude.com/docs/en/code-review-customize.md、https://code.claude.com/docs/en/code-review-pull-requests.md を取得して読んだ
- 確認の状態：確認済み
- 公式の推奨：
  - レビューは「Find」（複数のエージェントが並列に差分と周りのコードを調べる）→「Verify」（候補を検証して誤検出を落とす）→「Rank」（重複をまとめ、重大度で並べる）→「Post」の4段（[How reviews work](https://code.claude.com/docs/en/code-review#how-reviews-work)）
  - 既定では正しさに絞り、「bugs that would break production, not formatting preferences or missing test coverage」を見る
  - 重大度は 🔴 Important（マージ前に直すバグ）、🟡 Nit（小さい問題、ブロックしない）、🟣 Pre-existing（この PR が持ち込んだのではないバグ）（[Severity levels](https://code.claude.com/docs/en/code-review-pull-requests#severity-levels)）
  - 後のレビューは前回からの変更に絞り、nit と pre-existing を減らす（[What a later review covers](https://code.claude.com/docs/en/code-review-pull-requests#what-a-later-review-covers)）
  - `REVIEW.md` はレビュー専用の指示。Important の意味、nit の上限、報告しないパス、必ず確かめること、根拠に `file:line` を求めること、を書く（[Choose what to write in REVIEW.md](https://code.claude.com/docs/en/code-review-customize#choose-what-to-write-in-review-md)）
  - `REVIEW.md` はベースのブランチから読み、「never from the pull request's own changes」
- 採用するもの：
  - 探索役と検証役のプロンプトに、対象のリポジトリの `REVIEW.md`（あれば）を渡す。指摘の根拠に `file:line` を必須にする（STATE-02、`contracts`）
  - プロファイルは実行の開始時の写しを使い、実行の中でプロファイル・スキル・`REVIEW.md` を変えた差分は常に人が見るパスにする（`policy` の既定の `always_human`、GATE-01）
- 採用しないもの：Code Review の GitHub App（Team・Enterprise と GitHub に限られ、ローカルの自走には使えない）
- ツールにできないこと：なし

## Claude Code のスキル 2.1.296

- 確認方法：`claude --version` → `2.1.296 (Claude Code)`、`npm view @anthropic-ai/claude-code version` → `2.1.306`。https://code.claude.com/docs/en/skills.md を取得して読んだ
- 確認の状態：確認済み
- 公式の推奨：
  - スキルは `.claude/skills/<名前>/SKILL.md` に置き、起動したディレクトリとその親からリポジトリのルートまでの `.claude/skills/` から読み込まれる（[Load skills in monorepos and subdirectories](https://code.claude.com/docs/en/skills#load-skills-in-monorepos-and-subdirectories)）
  - frontmatter はすべて任意で、`description` だけが推奨。`description` と `when_to_use` は合わせて 1,536 文字で切り詰められる
  - `disable-model-invocation: true` で、Claude が自動で読み込むのを止め、人が `/名前` で呼ぶ
  - `allowed-tools` は「Tools Claude can use without asking permission during the turn that invokes this skill. The grant clears when you send your next message.」
  - `argument-hint` で補完時に引数の形を示す。引数は `$ARGUMENTS` で受ける
  - 「Keep `SKILL.md` under 500 lines. Move detailed reference material to separate files.」
- 採用するもの：配布するスキルは `autoflow-setup`・`autoflow`・`autoflow-learn` の3つにし、`disable-model-invocation: true`、`allowed-tools: Bash(python3 .autoflow/autoflow.py *)` を付け、500行以内・参照は `references/` の1階層にする（STR-05、[ADR 0003](adr/0003-three-skills-and-five-agents.md)）
- 採用しないもの：`context: fork`（人に聞く手順とサブエージェントの起動はメインのセッションで動かす必要があるため）
- ツールにできないこと：参照ファイルの深さと、決まった節（`## 人に確かめること`）の有無は公式の検査が無い → `scripts/structure_check.py` で確かめる

## Claude Code のサブエージェント 2.1.296

- 確認方法：https://code.claude.com/docs/en/sub-agents.md を取得して読んだ
- 確認の状態：確認済み
- 公式の推奨：
  - 定義は `.claude/agents/<名前>.md`。必須は `name` と `description` だけ。知らない項目は黙って無視される（[Frontmatter reference](https://code.claude.com/docs/en/sub-agents#frontmatter-reference)）
  - 「Each subagent starts with a fresh, isolated context window. It doesn't see your conversation history, the skills you've already invoked, or the files Claude has already read.」一方で CLAUDE.md の階層は読み込まれる（`omitClaudeMd: true` で外せる）
  - `tools` を省くと全ツールを継承する
  - `AskUserQuestion` と `Workflow` は、`tools` に書いてもサブエージェントから除かれる（[Available tools](https://code.claude.com/docs/en/sub-agents#available-tools)）
  - 独立した調べものは複数のサブエージェントを同時に起動する。既定で同時に20まで（`CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`）
- 採用するもの：
  - 計画役・実装役・探索役・検証役・リスク判定役の5つにし、`tools` を列挙し、`Skill` と `Agent` を入れない（STR-05、[ADR 0003](adr/0003-three-skills-and-five-agents.md)）
  - 探索役・検証役は新しいコンテキストで動くことを、記事の「新しいコンテキストでのレビュー」に当てる。CLAUDE.md は読ませる（記事と Code Review の文書が、レビューは CLAUDE.md を読むとしているため）
  - 人に聞く手順はメインのセッションで動くスキルに置く（GATE-02）
- 採用しないもの：`permissionMode` の指定（権限を広げないため。OPS-04）、`isolation: worktree`（作業ブランチを1つにし、tree で差分を固定するため。[ADR 0004](adr/0004-tree-snapshot-on-work-branch.md)）
- ツールにできないこと：読み取りだけの役（計画・探索・検証・リスク判定）がファイルを書き換えないことを、`tools` だけでは保証できない（Bash と Write を持つため） → 補助 CLI が役の前後で tree を比べ、変わっていれば止める（GATE-07）

## Claude Code のヘッドレス実行（claude -p）と AskUserQuestion 2.1.296

- 確認方法：https://code.claude.com/docs/en/headless.md と https://code.claude.com/docs/en/tools-reference.md を取得して読んだ。`claude --help` で `--permission-prompts`、`--max-budget-usd`、`--allowedTools` があることを確かめた
- 確認の状態：確認済み
- 公式の推奨：
  - `-p` は `--bare` を付けなければ、対話のセッションと同じくスキル・サブエージェント・hooks を読み込む。プロンプトに `/skill-name` を書くとスキルを呼べる
  - 「With `--permission-prompts none`, Claude Code removes the tools that need an answer from a person, such as AskUserQuestion, so Claude can't call them.」
  - v2.1.302 以降、モードを指定しない `-p` は Manual モードで始まる。`acceptEdits` は編集を確認なしで許すが、他のシェルのコマンドは許可の規則が要る
  - AskUserQuestion は既定で答えるまで開いたままだが、`askUserQuestionTimeout` を設定すると、時間切れで「you may be away from your keyboard」と伝えて閉じ、Claude は自分の判断で進む（[AskUserQuestion tool behavior](https://code.claude.com/docs/en/tools-reference#askuserquestion-tool-behavior)）
- 採用するもの：
  - 人の関所で答えが得られない（ツールが無い、時間切れで閉じた、回答が空）ときは、承認にせず、関所のファイルの場所を報告して止まる（GATE-02）
  - 収束テストの通しの実行は `claude -p` で行い、人の関所（H3）で止まることを確かめる（[convergence-report.md](convergence-report.md)）
- 採用しないもの：`--bare`（スキルとサブエージェントの読み込みが止まるため）
- ツールにできないこと：AskUserQuestion の回答をフックで記録する方法は、文書に入力と出力の形が書かれていない → 使わない（[ADR 0006](adr/0006-human-answer-record.md)）

## Claude Code の hooks 2.1.296

- 確認方法：https://code.claude.com/docs/en/hooks.md を取得して読んだ
- 確認の状態：確認済み
- 公式の推奨：PreToolUse は `permissionDecision`（allow・deny・ask・defer）で止められ、終了コード2は「Blocks the tool call.」。hooks は Edit・Write などツールの呼び出しに効き、Bash の中のファイルの書き換えは止められない
- 採用するもの：この基盤の開発では、pattern-foundation の hooks（保護ファイルの確認、編集後の整形）を使う（TOOL-02、TOOL-04）
- 採用しないもの：配布物に hooks を入れること（対象のリポジトリの既存の hooks と混ざり、入れる・外すの手順が増えるため）
- ツールにできないこと：なし

## 課題の取得元（Backlog MCP、Redmine MCP、glab、gh）

- 確認方法：
  - Backlog：この環境の MCP ツール `mcp__backlog__get_issue`（引数 `issueKey` 例 `PROJ-123`）と `mcp__backlog__get_issue_comments`（`issueKey`、`count`、`order`）の定義を読んだ
  - Redmine：MCP ツール `mcp__redmine__getIssue`（`pathParams.issueId`、`pathParams.format: json`、`queryParams.include: ["journals"]`）の定義を読んだ
  - GitLab：`glab --version` → `glab 1.94.0`。`glab issue view --help` で `-F, --output text|json`、`-c, --comments`、`-R, --repo` を確かめた
  - GitHub：手元に gh は無い。https://cli.github.com/manual/gh_issue_view で `--json <fields>`（`title`、`body`、`comments`、`labels`、`number`、`url` ほか）と `-c, --comments` を確かめた
- 確認の状態：確認済み
- 公式の推奨：各ツールの本文とコメントを取得する
- 採用するもの：取得はメインのセッションのスキルが行い、補助 CLI は取得した文章（`--body-file`）と出所（`--source`、`--ref`、`--url`）だけを受け取る。CLI がネットワークと認証に触れないようにするため（OPS-02、[ADR 0005](adr/0005-skill-fetches-sources.md)）。MCP のサーバー名が違う環境のため、スキルの取得元の表に「同じ働きのツールを使う」と書く
- 採用しないもの：補助 CLI から glab・gh を呼ぶこと（取得元ごとに CLI の分岐と認証の失敗の扱いが増えるため）
- ツールにできないこと：MCP のサーバー名は利用者の設定で変わる → スキルが一覧から探す

## Python 3.9.6

- 確認方法：`python3 --version` → `Python 3.9.6`
- 確認の状態：確認済み
- 公式の推奨：`from __future__ import annotations` の下で `X | None` を書ける。`dict[str, int]` などの組み込みの総称型は 3.9 から使える
- 採用するもの：配布物は Python 3.9 の標準ライブラリだけで動かす（DEP-03、TOOL-05）。全モジュールに `from __future__ import annotations` を書く（CODE-03）
- 採用しないもの：3.10 以降の構文と API（`match` 文、`zip(strict=True)`、`sys.stdlib_module_names`）
- ツールにできないこと：標準ライブラリの一覧は 3.9 では `sys` から取れない → 構造検査に使ってよいモジュールの表を持つ（DEP-03）

## uv 0.11.14

- 確認方法：`uv --version` → `uv 0.11.14`
- 確認の状態：確認済み
- 公式の推奨：`uvx <ツール>@<版>` で、版を固定したツールを使い捨ての環境で動かせる
- 採用するもの：ruff と mypy を `uvx ruff@0.17.1`、`uvx mypy@1.20.2` で呼ぶ（PROC-03、TOOL-05）
- 採用しないもの：プロジェクトの仮想環境と lockfile（配布物が依存を持たないため）
- ツールにできないこと：なし

## ruff 0.17.1

- 確認方法：`uvx ruff@0.17.1 --version` → `ruff 0.17.1`。PyPI の最新も 0.17.1（2026-10-15 公開。0.17.0 は 2026-10-09）。使うルールは `uvx ruff@0.17.1 rule <コード>` で実在を確かめた（T201、TID252、D100、D104、ERA001、BLE001、C901、PLR0913、PLR0912、PLR0911、PLR0915、N802、N806、UP045、I001、E501）
- 確認の状態：確認済み
- 公式の推奨：formatter と linter を兼ねる。`target-version` で対象の Python の版を決める
- 採用するもの：整形（TOOL-01）と、命名（NAM-01）、import（CODE-02）、型注釈の書き方（CODE-03）、大きさ（CODE-04）、docstring とコメント（CODE-05）、例外の捕まえ方（ERR-01）、print（DEP-04）の lint
- 採用しないもの：0.16 系（0.17 は公開から90日未満だが、名指しされた技術のテンプレートに縛られる道具ではなく、開発の道具だけで使うため最新にした。[ADR 0007](adr/0007-tool-versions.md)）
- ツールにできないこと：import の許可表、副作用の置き場、ファイルの配置、文字列の置き場、段の入口の形は判定できない → 構造検査（`scripts/structure_check.py`）で縛る

## mypy 1.20.2

- 確認方法：`uvx mypy@1.20.2 --version` → `mypy 1.20.2`。PyPI の最新は 2.4.0 だが、`uvx mypy@2.4.0 --python-version 3.9` は「Python 3.9 is not supported (must be 3.10 or higher)」で止まった。`uvx mypy@1.20.2 --python-version 3.9 --strict` は通った
- 確認の状態：確認済み
- 公式の推奨：`strict = true` で、型注釈の無い関数と Any の暗黙の使用を落とす
- 採用するもの：`strict`、`python_version = 3.9`、`warn_unreachable`（CODE-03、TOOL-05、[ADR 0007](adr/0007-tool-versions.md)）
- 採用しないもの：mypy 2.x（3.9 を対象にできないため）
- ツールにできないこと：なし

## unittest 3.9.6（標準ライブラリ）

- 確認方法：Python 3.9.6 の標準ライブラリ
- 確認の状態：確認済み
- 公式の推奨：`python3 -m unittest discover` でテストを集めて回す
- 採用するもの：テストは unittest で書き、モックを使わず、本物の git と一時ディレクトリで確かめる。サブエージェントの出力は `tests/support.py` の部品で書く（TEST-01、TEST-02）
- 採用しないもの：pytest（依存を足すため）、`unittest.mock`
- ツールにできないこと：なし

## git 2.50.1

- 確認方法：`git --version` → `git version 2.50.1 (Apple Git-155)`（補助 CLI が実行時に必要とする）
- 確認の状態：確認済み
- 公式の推奨：`git add -A` は `.gitignore` を守って作業ツリーの全変更を index に載せる。`git write-tree` は index から tree を作り、その id は中身だけで決まる。`git diff <tree-ish> <tree-ish>` と `--numstat`・`--name-status` は機械で読める形で出せる
- 採用するもの：作業ブランチ `autoflow/<run-id>` の上で、差分の版を `git add -A` → `git write-tree` の tree id で表す。証拠・レビュー・承認はこの id に結び付け、2ラウンド目からの差分は前の tree との `git diff` で取る（GATE-04、GATE-05、[ADR 0004](adr/0004-tree-snapshot-on-work-branch.md)）
- 採用しないもの：`git worktree`（作業ディレクトリの外の編集に確認が出て、人の介入が増えるため）、`git stash`（利用者の退避と混ざるため）
- ツールにできないこと：なし
