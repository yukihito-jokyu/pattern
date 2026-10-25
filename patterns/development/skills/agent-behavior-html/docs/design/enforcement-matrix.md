<!-- このファイルは rules_check.py が rules.md と probes.json から生成する。手で編集しない。 -->

# 強制の対応表

ルールごとに、どの仕組みで守らせているかを示す。段の強さは type > format > lint・structure・test > generator > review > doc の順である。
probe が実際に検査で落ちるかの結果は `.foundation/probe-results.json` にある（`violation_probe.py` が書く）。

## 集計（各ルールの最も強い段で数える）

| 段 | 件数 |
|---|---|
| type | 0 |
| format | 1 |
| lint | 0 |
| structure | 7 |
| test | 12 |
| generator | 0 |
| review | 2 |
| doc | 2 |

## ルールごとの対応

| ルールID | 題名 | 強制 | 仕組み | probe |
|---|---|---|---|---|
| STR-01 | qualityの配置検査 | structure | qualityの配置検査 | STR-01-a |
| DEP-01 | ASTのimport検査 | structure | ASTのimport検査 | DEP-01-a |
| NAM-01 | AST命名検査と入口一覧 | structure | AST命名検査と入口一覧 | NAM-01-a |
| CODE-01 | ASTの関数注釈と大きさ検査 | structure | ASTの関数注釈と大きさ検査 | CODE-01-a |
| ERR-01 | CLI終了とstdout契約 | test | CLI終了とstdout契約 | ERR-01-a |
| ERR-02 | 入力境界と重複排除契約 | test | 入力境界と重複排除契約 | ERR-02-a |
| STATE-01 | 保存先とsession分離契約 | test | 保存先とsession分離契約 | STATE-01-a |
| ASYNC-01 | 並行・前後欠落・逆順契約 | test | 並行・前後欠落・逆順契約 | ASYNC-01-a |
| OPS-01 | 操作情報の選択とマスク契約 | test | 操作情報の選択とマスク契約 | OPS-01-a |
| OPS-02 | 明示パス契約 | test | 明示パス契約 | OPS-02-a |
| OPS-03 | 日時と経過時間契約 | test | 日時と経過時間契約 | OPS-03-a |
| OPS-04 | HTML注入契約 | test | HTML注入契約 | OPS-04-a |
| OPS-05 | 出力分離契約 | test | 出力分離契約 | OPS-05-a |
| OPS-06 | 成否未知と製品別一覧契約 | test | 成否未知と製品別一覧契約 | OPS-06-a |
| OPS-07 | 明示された目的と対応の契約 | test | 目的のscope・一回性・期限・曖昧さの契約 | OPS-07-a |
| TEST-01 | 必須テストとguard | structure | 必須テストとguard | TEST-01-a |
| PROC-01 | implの作業順序 | doc | implの作業順序 | — |
| PROC-02 | reviewの波及確認 | review | reviewの波及確認 | — |
| PROC-03 | reviewの互換性確認 | review | reviewの互換性確認 | — |
| PROC-04 | AGENTSの完了条件 | doc | AGENTSの完了条件 | — |
| TOOL-01 | guard.py | structure | guard.py | TOOL-01-a |
| TOOL-02 | quality.py --fix | format | quality.py --fix | TOOL-02-a |
| TOOL-03 | 導入merge契約 | test | 導入merge契約 | TOOL-03-a、TOOL-03-b |
| TOOL-04 | AST互換構文とimport検査 | structure | AST互換構文とimport検査 | TOOL-04-a |

## 機械で縛っていないルール

| ルールID | 題名 | 強制 | 機械化しない理由 |
|---|---|---|---|
| PROC-01 | implの作業順序 | doc | 作業順序と報告の正確さは差分から観測できない。 |
| PROC-02 | reviewの波及確認 | review | 資料をまたぐ変更の意味には差分の解釈が必要になる。 |
| PROC-03 | reviewの互換性確認 | review | 資料をまたぐ変更の意味には差分の解釈が必要になる。 |
| PROC-04 | AGENTSの完了条件 | doc | 作業順序と報告の正確さは差分から観測できない。 |

## 対象外とした軸

| 軸 | 理由 |
|---|---|
