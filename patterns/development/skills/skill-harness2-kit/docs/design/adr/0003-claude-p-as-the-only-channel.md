# 0003 モデルの呼び出しはすべて閉じ込めた claude -p で行う

- 状態：採用
- 関係するルール：OPS-05、STATE-02、STATE-03、DEP-04

## 背景

harness2 は、実行（rollout）も編集者（proposer）も選択役も、別のプロセスとして隔離した作業場所で動かす。編集者は作業場所の `context/harness/` をその場で直し、その差分が提案になる。プロンプトは短い道案内だけで、証拠はファイルとして渡す（research.md の「harness2 の仕組み」）。

この基盤では、実行は「候補のスキルを入れた Claude Code」でなければならない。対象スキルが Claude Code のスキルだからである。兄弟の基盤（skill-tune-kit）は、サブエージェントにスキルを読ませて実行の代わりにしている。

## 選択肢

| 選択肢 | 良い点 | 悪い点 |
|---|---|---|
| サブエージェントで実行と編集を行う | 利用者のセッションの中で完結する | 候補のスキルが本物のスキルとして入らない（呼ばれ方、description の効き方を測れない）。並行の数と再開をスキルの手順に頼る。編集者の閉じ込めを道具の設定で強制できない |
| `claude -p` を補助 CLI から起動する | 候補を `.claude/skills/<名前>/` に本物として入れて実行できる。`--restricted` と `--tools` で編集者を作業場所に閉じ込められる。キャッシュ・再開・台帳を CLI が持てる | 利用者の機械で `claude` が動き、認証が要る。費用が `claude` の課金に乗る |

## 決定

`claude -p` を補助 CLI から起動する。コマンド行は `runner` だけが組み立て、次のフラグを必ず付ける（OPS-05）。

- 実行：`--setting-sources project --strict-mcp-config --no-session-persistence --permission-prompts none`。sandbox は OS の一時ディレクトリに作り、git の基準を置き、候補を `.claude/skills/<名前>/` に入れる
- 編集のセッション：`--restricted --tools Read,Edit,Write,Glob,Grep --disable-slash-commands --strict-mcp-config --no-session-persistence --permission-prompts none`。作業場所は一時ディレクトリで、`context/` を写して動かし、終わったら `context/harness/` を回収する
- 選択・振り返り：編集のセッションと同じで、`--tools Read,Glob,Grep`

## 理由

- 候補の description が本当にスキルを呼ばせるか、本文の手順が本当に読まれるかは、本物として入れて動かさないと分からない。stream-json の `Skill` の `tool_use` で呼ばれたかを記録できる（research.md の実験 3）
- harness2 が文で頼んでいた「証拠の中のスクリプトを実行するな」「作業場所の外を読むな」を、`--restricted --tools` で道具の側から強制できる（research.md の実験 4）
- `--setting-sources project` で利用者のスキルとプラグインを外せるので、結果が対象スキル以外の要因で揺れない（research.md の実験 2）

## 影響

- `--bare` は使わない（OAuth の利用者が認証できなくなる）。`--dangerously-skip-permissions` も使わない
- 実行は利用者の機械で動く。プロファイルの `rollout.tools` に `Bash` を入れると、実行が sandbox の外に触れうる。既定は `Bash(python3 *)` などの絞った形にし、references/profile-guide.md に危険を書く
- `--setting-sources` が利用者のスキルを外すことは文書ではなく実験で確かめた事実である。Claude Code を上げたら research.md の実験をやり直す
