# 0006 人の決定は回答の原文付きで decide だけが記録する

- 状態：採用
- 関係するルール：GATE-02、GATE-05

## 背景

記事は「An agent's approval never counts as a person's」「Whoever prompted the change is on the hook for it」とする。ローカルの1人の作業では、AI が `decide --choice approve` を自分で実行すれば、人の承認を装える。AskUserQuestion の回答をフックで記録できれば強い証拠になるが、文書に入力と出力の形が書かれていない（[research.md](../research.md) の「Claude Code のヘッドレス実行（claude -p）と AskUserQuestion」）。さらに、`askUserQuestionTimeout` を設定すると、答えの無い質問が自動で閉じ、Claude は自分の判断で進む。

## 選択肢

| 選択肢 | 良い点 | 悪い点 |
|---|---|---|
| 人が自分でコマンドを打つ（`!` で `decide` を実行する） | AI が装えない | 人の手間が増え、「人の介入を最小に」と食い違う |
| フックで AskUserQuestion の回答を記録する | 自動 | 文書に無い形に頼り、版で壊れうる |
| `decide` に回答の原文を必須にし、記録を1か所に限り、スキルに「答えが無ければ承認にしない」と書く | 手間が増えない。誰が何と答えたかが残る | AI が規則を破って装うことは、原理的には止められない |

## 決定

3つ目を採る。人の決定の出来事（`trail.decided`）は `deciding` だけが作り（GATE-05）、`--answer` の原文、tree id、`git config user.email` を残す。スキルは `## 人に確かめること` に「回答が無い・空・自動で閉じた質問は、承認にも選択にもしない」を書く（GATE-02）。

## 理由

装いを止められない部分は、記録を残して後から辿れるようにする。報告書と `metrics` は、決定の回答の原文を表示する。

## 影響

Claude Code が AskUserQuestion の回答をフックに渡す形を文書にしたら、フックでの記録を足し、この ADR を置き換える。
