# レビュー検出率 ラウンド 3

仕込んだ違反のルールID: CODE-03, CODE-04, DEP-04, ERR-01, NAM-03, OPS-02, OPS-06, PROC-02, STR-03, TOOL-03, TOOL-04

| エージェント | 検出率 | 見逃し | 余計なルールID | 判定 |
|---|---|---|---|---|
| review/agent-1 | 1.000 | なし | ERR-02, KIT-06, PROC-07, STR-02, TOOL-01 | 差し戻し |
| review/agent-2 | 1.000 | なし | ERR-02, KIT-06, PROC-04, PROC-07, STATE-02, STR-02, TOOL-01 | 差し戻し |
| review/agent-3 | 1.000 | なし | ERR-02, KIT-06, PROC-07, STR-02, TOOL-01 | 差し戻し |

エージェント間で検出したルールIDの集合が一致: はい
