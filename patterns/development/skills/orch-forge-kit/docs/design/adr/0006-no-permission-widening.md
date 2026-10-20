# 0006 サブエージェントと実行役の権限を広げない

- 状態：採用
- 関係するルール：STR-05、OPS-04、OPS-05

## 背景

この基盤のサブエージェントはファイルを書き、実行役（`claude -p`）は評価用のコピーの中で人の確認なしに作業する。権限を広げれば止まらずに進むが、人の承認していない操作が通りうる。Claude Code の権限の仕組みは次のとおりである（[research.md](../research.md) の「Claude Code の権限と保護されたパス」「Claude Code のヘッドレス実行（claude -p）」）。

- `.claude/` への書き込みは保護されたパスで、`bypassPermissions` 以外では自動で許可されない
- `acceptEdits` は作業ディレクトリの中の編集を許す
- `--permission-prompts none` は、人の答えが要る `AskUserQuestion` を外し、許可されていない操作を拒否する
- サブエージェントの `permissionMode` は、親の権限のモードを変えうる

## 選択肢

| 選択肢 | 良い点 | 悪い点 |
|---|---|---|
| 実行役を `bypassPermissions` か `--dangerously-skip-permissions` で動かす | 止まらない | コピーの外への書き込みと、承認していないコマンドが通る |
| 実行役は `acceptEdits` と `--permission-prompts none`、Bash は charter の `allowed_tools` だけにする。サブエージェントに `permissionMode` を書かない | 許すことが charter に書かれ、人が承認している | 許していないコマンドを使う対象スキルは、評価で失敗する |

## 決定

- 実行役は `--permission-mode acceptEdits`、`--permission-prompts none`、`--max-budget-usd`、`--allowedTools <charter の executor.allowed_tools>` で起動する。`bypassPermissions`、`--dangerously-skip-permissions`、`--bare` は `kit/` のどこにも書かない（OPS-05）
- この基盤のサブエージェントの定義に `permissionMode` を書かず、書く場所は `.forge/` の下だけにする（OPS-04）
- 生成するバンドルのサブエージェントにも `permissionMode` を書かせない（バンドルの決まり。`bundle.RULES`）

## 理由

評価の条件は人が承認した charter に全部書かれているべきである。権限を広げる引数は、charter に無い条件を持ち込む。許していないコマンドで実行役が失敗したことは、`result` の `permission_denials` に残るので、人は `allowed_tools` を足すかを判断できる。

## 影響

- 実行役が拒否された操作は、採点役が読む版（trace.md）と facts.json に出す
- auto モードで `execute` 自体が拒否されたら、利用者が許可の規則を足す（README と forge-run に書く）
