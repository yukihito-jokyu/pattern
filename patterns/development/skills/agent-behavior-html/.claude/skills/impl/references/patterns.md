# 変更パターン

## 1. イベントの追加・変更

- 使う場面：イベント、記録、hookの変更。
- 見本：配布スキルscripts/event_model.py、record.py、tests/test_observer.py。

| 順 | 変えるファイル | 見本との対応 | 守る規則 |
|---|---|---|---|
| 1 | event_model.py | SOURCE_EVENTSとnormalize、validate_event | ERR-02 / OPS-01 / OPS-06 |
| 2 | record.py | 必要な入力変換。共通フィールドを増やす場合だけ | STATE-01 / ASYNC-01 |
| 3 | tests/test_observer.py | 固定入力で既存契約と新しい入力を検証 | TEST-01 |
| 4 | scripts/demo.py、references/schema.md、integration.md | 合成見本と製品別一覧 | PROC-02 |

手順：公式の入力を確認し、既存SOURCE_EVENTSへ追加する。metadataが同じなら収集器を分岐させない。新キーの意味と未知値を検証し、make demo、make checkを実行する。

間違えやすいこと：CodexへPostToolUseFailureを設定する、IDなしの前後を時刻だけで結ぶ、rawの応答を保存する。

## 2. 分析とHTMLの変更

- 使う場面：集計、指標、HTML、フィルターの変更。
- 見本：analyze.pyのcall_metrics、summarize、assets/dashboard.html。

| 順 | 変えるファイル | 見本との対応 | 守る規則 |
|---|---|---|---|
| 1 | analyze.py | call_metricsまたはsummarize | ASYNC-01 / OPS-03 / OPS-06 |
| 2 | assets/dashboard.html | renderとtextContent | OPS-04 |
| 3 | tests/test_observer.py | 集計の境界・0分母・欠落 | TEST-01 |
| 4 | references/metrics.md | 分母・除外・表示範囲 | PROC-02 |

手順：分母とnull条件を決め、集計と画面を同じ意味に変更する。ログ文字列からHTMLを生成せず、DOMのtextContentを使う。make demo、make checkを実行する。

間違えやすいこと：全体品質をフィルター値と呼ぶ、completedを成功扱いする、並行時間合計を実時間と呼ぶ。

## 3. 導入と製品接続の変更

- 使う場面：導入、設定merge、対応製品の変更。
- 見本：install.pyのmerge_hooks、install。

| 順 | 変えるファイル | 見本との対応 | 守る規則 |
|---|---|---|---|
| 1 | event_model.py | 製品の実在イベント一覧 | OPS-06 |
| 2 | install.py | 設定pathとmerge | TOOL-03 |
| 3 | tests/test_observer.py | 既存設定・空白入りpath・再実行・復元 | TEST-01 |
| 4 | references/integration.md | 信頼・再起動・限界 | PROC-02 |

手順：全衝突をpreflightし、既存設定の退避後に変更する。同じ内容の再導入は変更0件にする。make checkを実行する。

間違えやすいこと：既存hooksの配列を置換する、cwdをルートだと仮定する、自動でtrustする。
