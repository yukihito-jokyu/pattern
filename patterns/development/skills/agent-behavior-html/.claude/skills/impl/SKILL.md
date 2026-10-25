---
name: impl
description: claude-codex-cliの実装・変更・追加・修正の手順。イベントを追加、ログ項目を変更、指標を追加、画面を修正、導入を直す依頼に使い、同じ配置・契約・検査で変更する。このパターンのコード変更では依頼の大小にかかわらず使う。
---

# このパターンの実装

パスはパターンのルート基準。正本は`docs/design/rules.md`、見本は`.claude/skills/agent-behavior-html/`。作業には[パターン一覧](references/patterns.md)を使う。

## 1. 依頼をパターンに振り分ける

| 依頼 | patterns.mdの節 |
|---|---|
| イベント、記録、hookを追加・変更 | 1 |
| 集計、指標、HTML、フィルターを追加・変更 | 2 |
| 導入、設定merge、対応製品を変更 | 3 |

複数なら表の順に行う。上のどれでもない場合は既存の見本へ収まる変更か確認し、新たな配布単位が必要なら理由と案を示す。

## 2. 依頼から決まらない値

| 値 | 影響 | 既定値 |
|---|---|---|
| 保存先 | hookコマンド | 明示プロジェクトの.agent-logs |
| 出力先 | 分析CLI | reports/agent-behavior.html |
| 保存範囲 | 保存スキーマ | v2の操作対象・短い目的・結果抜粋。Read/Write/Editの本文は保存しない |
| 目的がない | 分析・HTML | 未記録。推測しない |
| 日時 | 保存・表示 | UTC保存、Asia/Tokyo表示 |
| 成否不明 | 指標 | completed |
| 新しいhookの入力にIDが無い | 前後結合 | nullを残し結合しない |

ユーザーの指定を優先し、可逆な値は既定値で進めて報告する。保存範囲を本文へ拡張する判断を既定で行わない。

## 3. 書く前に読む

1. patterns.mdの該当節。
2. 記録ならERR/STATE/ASYNC/OPS、画面ならOPS、導入ならTOOL、すべてSTR/DEP/PROCの規則。
3. event_model.py、該当エントリポイント、test_observer.py、スキルの該当reference。

## 4. 作る順序

PROC-01: スキーマ、実装、契約テスト、説明の順。既存の分岐と関数を拡張し、同じことをする別ファイルを作らない。合成データは`make demo`で作る。編集hookは対象Pythonファイルのquality検査を実行する。

## 5. 検証する

`make check`を実行する。失敗はIDでrulesを引いて直す。設定緩和・抑止・skipで通さない。規則変更時は`make probes`も実行する。

## 6. 完了前チェックリスト

- [ ] PROC-02: event_model ⇔ record ⇔ analyze ⇔ schema.md ⇔ 合成fixtureを開いて照合した。
- [ ] PROC-02: 指標変更はanalyze ⇔ dashboard ⇔ metrics.mdの分母と未知値を照合した。
- [ ] PROC-03: 既存の型・意味の互換性を確認した。
- [ ] v1互換、v2の保存範囲と上限、目的の出所、前後欠落、成否不明を維持した。
- [ ] `make check`が通った。
- [ ] PROC-04: 実行していない実機の動作を合格と報告しない。

## 7. 報告する

作ったもの、変更ファイル、採用した既定値と理由、checkの結果、未確認事項の順に短く報告する。根拠を示す場合は実際の記述と絶対パスの行リンクを並べる。
