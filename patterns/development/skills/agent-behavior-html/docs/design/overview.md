# 設計の入口

このパターンは、Claude CodeとCodexの操作・目的・結果を同じ形式で記録し、その実行の経過を調べるためのものです。両製品のhook入力を共通スキーマへ変換し、操作前の目的の申告を入力指紋で結びます。分析は共通形式を読むので、同じ指標と画面で比較できます。

ユーザー指定はpattern-foundation、Claude、Codex、hooks、分析HTMLスキルです。新規作成としてclaude-codex-cliに閉じています。Python標準ライブラリ、JSONL、HMAC入力指紋、単体HTML、ローカル導入、UTC保存を採用しました。操作・目的・結果を記録するv2への変更は[ADR 0002](adr/0002-operation-purpose-results.md)にあります。

| 読みたいこと | 資料 |
|---|---|
| 最短の導入・分析 | [README](../../README.md) |
| 利用時の手順 | [配布スキル](../../.claude/skills/agent-behavior-html/SKILL.md) |
| 技術と確認版 | [research](research.md) |
| 配置・依存・変更範囲 | [architecture](architecture.md) |
| 決定の正本 | [rules](rules.md) |
| 規則と検査の対応 | [enforcement-matrix](enforcement-matrix.md) |
| 既定値の理由 | [ADR 0001](adr/0001-machine-enforced-rules.md) |
| 検査と収束の結果 | [convergence-report](convergence-report.md) |

取得できない情報を埋めてしまうと、実行の失敗と単なるログ欠落を取り違えます。そのため、成否不明、前後欠落、IDなし、時刻逆転を値として残します。料金・トークン・隠れた推論・能力評価を作らないことも、同じ理由からの決定です。
