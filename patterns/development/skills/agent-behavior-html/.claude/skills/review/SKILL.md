---
name: review
description: claude-codex-cliの変更をレビューする。checkの結果に加え、イベント・分析・HTML・説明の整合、保存済みログの互換性、検査の迂回を確認し、ルールIDと根拠を示す。
---

# レビュー

## 1. 対象を確認する

AGENTS.md、docs/design/rules.md、architecture.mdを読み、依頼の範囲と変更ファイルを確認する。

## 2. 機械検査

`make check`を実行する。落ちたら出力を載せる。機械が拾う問題の指摘を手で重複させない。skip・抑止・Makefile・quality・manifest・probesの緩和は別途確認する。

## 3. 確認項目

| ルールID | 確認方法 | 典型的な違反 |
|---|---|---|
| PROC-02 | event_model・record・analyze・schema・fixtureを照合し、指標変更ではcall_metrics・render・metrics.mdの分母とnull条件を照合する | completedを分母へ足したが画面の説明は既知成否のまま |
| PROC-03 | 旧ログのキー・型・意味を比較し、破壊的変更はschema_versionとADRの移行方針を確認する | v1のobserved_atを別の時刻の意味へ変える |

## 4. 境界と抜け道

既存hooksの削除、ユーザー全体設定の変更、本文保存の追加、データの外部送信を確認する。依頼された変更自体を、保護ファイルの編集であることだけを理由に差し戻さない。検査を弱めた場合はTOOL-01を指摘する。

## 5. 判定

checkが通り、違反指摘0件なら承認。それ以外は差し戻し。規則に無い提案は承認条件に加えない。

## 6. 出力

1. 判定: 承認 / 差し戻し
2. 機械検査: コマンド、終了、出力の末尾
3. 指摘: ルールID、ファイルの行リンク、実際の記述、影響、修正案
4. ルール追加の提案: 指摘と分ける
5. 残った未確認事項
