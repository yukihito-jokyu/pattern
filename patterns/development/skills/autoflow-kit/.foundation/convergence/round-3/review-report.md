# レビュー検出率 ラウンド 3

仕込んだ違反のルールID: CODE-01, NAM-02, OPS-03, PROC-02, PROC-06, STATE-01, STATE-02, TEST-03, TOOL-03, TOOL-04

| エージェント | 検出率 | 見逃し | 余計なルールID | 判定 |
|---|---|---|---|---|
| review/agent-1 | 1.000 | なし | CODE-04, DEP-03, PROC-04, TEST-01 | 差し戻し |
| review/agent-2 | 1.000 | なし | CODE-04, GATE-01, TEST-01 | 差し戻し |
| review/agent-3 | 1.000 | なし | CODE-04, PROC-04, TEST-01 | 差し戻し |

エージェント間で検出したルールIDの集合が一致: はい
