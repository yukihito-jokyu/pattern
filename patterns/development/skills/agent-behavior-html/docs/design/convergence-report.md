# 検証と収束試験の結果

2026-10-24のv2更新は、操作・目的・結果の記録と表示を追加した。今回の検証は[更新の検証記録](v2-validation.md)を参照。以下は初版作成時の記録であり、現在のデモ件数・テスト件数とは異なる。後続の独立試験は利用者の中止指示により終了し、この更新では再実施していない。

実装は利用可能な状態としてmanifestをreadyにした。合成入力・一時導入・静的な規則の検査は通過した。一方、履歴を持たない作者の出力を比較する収束試験は起動条件を満たせず、収束の完了は判定していない。

## 実行した検証

| 対象 | 結果 | 根拠 |
|---|---|---|
| 契約テスト | 13件成功 | tests/test_observer.py、最終validation-results.json |
| 画面処理 | render、製品・ツール・成否・セッション・検索フィルター、根拠、JSON保存、UTC、空表示、ページ送りに成功 | scripts/check_dashboard.cjs。DOMのスタブによる実行 |
| 違反probe | 19/19で検査失敗を検出 | .foundation/probe-results.json |
| checkへの組み込み | 3/3成功 | 同上のwiring |
| スキル形式 | 配布・実装・レビューのfrontmatterを検証 | skill-creatorのquick_validate |
| foundation hooks | 保護ファイルの確認出力と、編集後のPython検査を確認 | hooks.pyの合成stdin検証 |
| HTML生成 | 30イベント・2セッションの合成ログから成功 | examples/demo.jsonl、demo.html、demo.json |
| ブラウザー目視 | 実施できず | localhost bindが通常・権限昇格ともOperation not permitted。IABなし、Chrome操作も未承認 |
| 製品の実セッション | 未実施 | 導入先での再起動・hook信頼・実際の記録を利用者が確認する |

契約テストには機密本文の非保存、入力上限、不正・重複行、並行追記、セッション分離、前後欠落、時刻逆転、成否不明、HTML注入、既存設定維持、冪等性、空白と引用符を含む導入先、失敗時の設定復元を含む。CLIの合成入力で検証したものであり、製品の実際の発火を確認したものとは区別する。

## 強制の内訳

| 段 | ルール数 |
|---|---|
| format | 1 |
| structure | 7 |
| test | 11 |
| review | 2 |
| doc | 2 |

文書のみの規則はPROC-01（作業順序）とPROC-04（正確な報告）。差分だけでは実行順序と実測範囲を観測できないためAGENTSとimplへ記載した。レビューはPROC-02（資料間の意味の一致）とPROC-03（互換性と移行）。対応表の正本は[enforcement-matrix.md](enforcement-matrix.md)。

## 独立作者の収束試験

通常3課題×3人=9セッション、最終はholdoutを加え4課題×3人=12セッション、別にレビュー3セッションを計画した。課題・一時コピー・レビューseedを準備したが、推論を開始できた独立セッションは0件だった。

| 実行方法 | 結果 |
|---|---|
| サブエージェントAPI | 継承モデル名gpt-6-Lunaを解決できず起動失敗 |
| Claude CLI | Not logged in · Please run /login。API token使用0 |
| Codex CLI 通常実行 | in-process app-serverの初期化がOperation not permitted |
| Codex CLI 権限を上げた再実行 | 子CLIのworkspace-writeを維持して実行したがworkspace routing discovery failed |

ラウンド1のfiles、names、contentはすべて未測定。holdoutとレビュー検出率も未測定。出力差分が存在しないので、R1〜R6の残差が0とは判断しない。ネットワーク・認証・モデル起動の制約を規則の成功やR7に読み替えない。詳細は[実行状態JSON](../../.foundation/convergence/execution-status.json)と[round-1](../../.foundation/convergence/round-1/report.md)。

再開時はtasks.jsonを使ってprepareを新しいworkdirへ実行する。Claude CLIのログインまたはCodex CLIの接続を復旧し、通常ラウンド、締め込み、holdout、review-scoreの順に測る。Codex代替はconvergence.py runの--runnerへ次のJSON配列を渡せる。自動trustやsandbox解除は不要。

```json
["codex", "exec", "--ephemeral", "--sandbox", "workspace-write", "--skip-git-repo-check", "{prompt}"]
```

この代替ではClaude用の編集保護hookがCodexに適用されない。convergence diffのprotected差分検出とレビューで確認する。ユーザー単位の設定が読み込まれる点も実行記録に残す。

## 結果の読み方

pattern-foundationは次を完了条件にする。

[pattern-foundation SKILL.md](../../../.claude/skills/pattern-foundation/SKILL.md)

> 測定（収束テスト）の結果を完了条件にする。

そのため、この成果物は「実装と機械検査は完了、独立収束は未検証」という状態で渡す。実機でのhook発火とブラウザー目視も上表の範囲を越えて保証しない。
