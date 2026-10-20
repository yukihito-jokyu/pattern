# 0009 指標は実行の記録の文書にある項目だけから求める

- 状態：採用
- 関係するルール：NAM-03、CODE-03、ERR-02

## 背景

オーケストレーションスキルの良し悪しは、結果の差分だけでなく、どのサブエージェントを何回起動したか、誰が編集したか、どれだけの費用と時間がかかったかにも現れる。実行役（`claude -p`）の `--output-format stream-json` の出力からこれを数える。出力には、文書にある項目と、文書に無い項目（`subagent_stats`）がある（[research.md](../research.md) の「Claude Code のヘッドレス実行（claude -p）」の実機の試験）。

## 選択肢

| 選択肢 | 良い点 | 悪い点 |
|---|---|---|
| `subagent_stats` を使う | 起動の内訳がそのまま取れる | 文書に無く、版で形が変わりうる |
| 文書にある項目だけから数える | 版が上がっても壊れにくい | 起動と編集を自分で数える処理が要る |

## 決定

`trace.py` が、文書にある次の項目だけを読んで数える。

| 数えるもの | 読む項目 |
|---|---|
| サブエージェントの起動（名前ごと） | メインの会話（`parent_tool_use_id` が `null`）の `assistant` の `tool_use` のうち、`name` が `Agent` か `Task` のものの `input.subagent_type` |
| 編集の主体 | `tool_use` の `name` が `Edit`・`Write`・`MultiEdit`・`NotebookEdit` のもの。`parent_tool_use_id` が `null` ならメインの会話、そうでなければサブエージェント |
| 入れ子の深さ | `system` の `task_started` の `spawn_depth` の最大 |
| 完了・費用・時間・ターン数・拒否 | 最後の `result` の `subtype`、`is_error`、`total_cost_usd`、`duration_ms`、`num_turns`、`permission_denials` |

JSON として読めない行は飛ばし、その数を記録する。`result` が無い記録は、完了していないものとして扱う。

## 理由

文書にある項目は、版が上がっても互換性が保たれる見込みが高い。読む項目を `trace.py` の1か所に閉じ込めれば、形が変わったときに直す場所が1つで済む。

## 影響

- 新しい項目を読むときは、`trace.py`、`tests/test_trace.py`、`tests/fixtures/streams/` を同じ変更で変える
- 費用の `total_cost_usd` は推定の値である。報告に「推定」と書く
