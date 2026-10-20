# 0011 install.py が補助 CLI の許可ルールを対象のリポジトリの設定に足す

- 状態：採用
- 関係するルール：STR-05、OPS-05

## 背景

配布するスキルは `allowed-tools: Bash(python3 .forge/forge.py *)` を持ち、スキルを呼んだターンの間は補助 CLI を確認なしで呼べる（[research.md](../research.md) の「Claude Code のスキル」）。一方、forge-run は、実行役の `execute` を裏で回し、完了の通知を待ってから次のコマンドへ進む。通知で始まるターンは、スキルを呼んだターンではない。

見本のリポジトリでの通しの実行（`docs/design/convergence-report.md`）で、`execute` の完了を待った後の `status` と `collect` が、すべて承認待ちで拒まれた。画面のある利用でも、評価の間に何度も確認が出る。

## 選択肢

| 選択肢 | 良い点 | 悪い点 |
|---|---|---|
| `execute` を裏で回さず、終わるまで待つ | 許可は今のままでよい | Bash ツールの前景の上限（10分）を超える評価で止まる |
| 利用者に許可ルールを手で足してもらう（README に書く） | 対象のリポジトリの設定を変えない | 足し忘れると、評価の途中で止まる |
| `install.py` が `.claude/settings.json` の `permissions.allow` に、スキルと同じルールを1つ足す | 入れた直後から評価が止まらない。広げるのはスキルが既に許している範囲だけ | 対象のリポジトリの共有の設定ファイルを変える |

## 決定

- `install.py` は、`.claude/settings.json` の `permissions.allow` に `Bash(python3 .forge/forge.py *)` が無ければ足す。ほかのキーと既存の許可は変えない。ファイルが無ければ作る
- JSON として読めない、または `permissions.allow` が配列でないときは、ファイルを変えずに `WARN` の行で手で足すよう伝える

## 理由

足すルールは、スキルの `allowed-tools` と同じ文字列で、許す範囲は変わらない。補助 CLI が `claude -p` を起動するときの条件（費用の上限、許すツール）は、人が承認した charter に書かれ、評価の開始も forge-run が人に確かめる（OPS-05、PROC-07）。

## 影響

- 補助 CLI のサブコマンドが増えても、ルールは変えなくてよい
- Claude Code は、信頼の確認を済ませていないワークスペースの `.claude/settings.json` の `permissions.allow` を無視し、そのことを警告する。対象のリポジトリで一度 Claude Code を画面で開いて信頼の確認に答えると、ルールが効く。画面を開いたことの無いディレクトリで `claude -p` を使うときは、`--allowedTools "Bash(python3 .forge/forge.py *)"` を渡す
- 許可を外したい利用者は、`.claude/settings.json` からこの1行を消す。そのときは、評価の待ちの後に確認が出る
