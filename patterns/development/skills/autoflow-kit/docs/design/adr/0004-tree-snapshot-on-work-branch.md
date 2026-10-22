# 0004 作業ブランチの上で、差分の版を git の tree id で表す

- 状態：採用
- 関係するルール：GATE-04、GATE-05、GATE-07、OPS-05

## 背景

証拠・レビュー・承認を「どの版の差分についてのものか」に結び付けないと、検査の後やレビューの後に変えた差分が、人の見ていないまま承認される。記事は「An approval covers one specific commit」とする。ローカルの自走では、承認の時点ではまだコミットが無い。

## 選択肢

| 選択肢 | 良い点 | 悪い点 |
|---|---|---|
| 差分の文（`git diff`）の sha256 | 分かりやすい | 新しいファイル（untracked）が漏れる。2つの版の間の差分を取り直せない |
| `git worktree` で別の作業ディレクトリを作る | 利用者の作業ツリーを汚さない | 作業ディレクトリの外の編集に確認が出て、人の介入が増える |
| 作業ブランチの上で `git add -A` → `git write-tree` の tree id | 中身だけで決まり、untracked も含む。`git diff <tree> <tree>` で2ラウンド目からの差分を取れる。コミットはその tree をそのまま記録する | 実行の間、変更が index に載る |

## 決定

- `start` は、作業ツリーがきれいで、`.autoflow/runs/` が `.gitignore` に入っていることを確かめてから、`autoflow/<run-id>` のブランチを作る
- 差分の版は `changes.snapshot`（`git add -A` → `git write-tree`）の tree id で表す
- 証拠・レビュー・リスク・報告書・人の決定は tree id を持ち、`commit` は承認の tree と今の tree が一致するときだけ動く

## 理由

tree id は中身だけで決まるため、「同じ版か」を文字列の比較で判定できる。コミットは index の tree をそのまま記録するので、承認した版とコミットした版が一致する。

## 影響

- 作業ツリーが汚れていると開始できない。スキルは人に、コミットするか退避するかを聞く
- 実行の記録（`.autoflow/runs/`）が `.gitignore` に無いと tree に入ってしまうため、`install.py` が `.gitignore` に足す
