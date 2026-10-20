# レビュー検出率 ラウンド 2

仕込んだ違反のルールID: CODE-02, DEP-02, DEP-05, NAM-02, PROC-06, STATE-01, STR-04, TOOL-03

| エージェント | 検出率 | 見逃し | 余計なルールID | 判定 |
|---|---|---|---|---|
| review/agent-1 | 1.000 | なし | NAM-03, NAM-07, OPS-04, OPS-05, PROC-04, STR-01 | 差し戻し |
| review/agent-2 | 1.000 | なし | NAM-07, OPS-05, PROC-02, PROC-04, STR-01, TEST-01 | 差し戻し |
| review/agent-3 | 1.000 | なし | NAM-07, OPS-05, PROC-02, STR-01, STR-02 | 差し戻し |

エージェント間で検出したルールIDの集合が一致: はい
