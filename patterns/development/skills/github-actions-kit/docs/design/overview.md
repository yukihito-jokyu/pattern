# github-actions-kit 設計の概要

## ゴール

この基盤のゴールは、同じ依頼を受けた別々の作者（人・エージェント）が、同じ書き方をする状態を保つことである。あわせて、変更が局所に収まる構造にすることを目指す。

この基盤は、GitHub Actions のワークフローを作成・更新するための道具一式である。配布先のリポジトリに入れると、Claude Code のスキルと検査の CLI が、誰が頼んでも同じ形のワークフローを書かせる。玄人の書き方（SHA での固定、最小の権限、OIDC、再利用の切り出し、キャッシュの使い分け）をルールとして決め、各ジョブ・各ステップの処理時間を PR に出す仕組み（`run-report`）も一緒に配る。

## 前提

### 受けた指示

指示の要点は次の4つである。

- GitHub Actions の作成・更新用のスキルを作る。玄人のやり方、ベストプラクティス、コアな技術、賢い使い方の観点で組み立てる
- 各ジョブ・各ステップの処理時間を PR に表示する機能を含める
- 作成では、ユーザーの意図を汲み取って書く
- 更新では、ユーザーに2つのモードから選んでもらう。1つは破壊的更新で、やりたいことを抽出し、そのうえでベストな書き方で作り直す。もう1つは、既存の書き方や意図を汲み取って変える更新である

技術の指定は GitHub Actions と Claude Code のスキルだけである。検査の道具は指定が無いので、次の節で決めた。

### 既定値で決めた事項

| 事項 | 決めたこと | 記録 |
|---|---|---|
| 進め方 | ルールを機械で強制し、独立エージェントで測る | [ADR 0001](adr/0001-machine-enforced-rules.md) |
| 名前と分野 | `github-actions-kit`。分野は iac と cli-library | [ADR 0002](adr/0002-name-and-domain.md) |
| スキルの数と配り方 | 実装用の `gha-workflow` とレビュー用の `gha-review`。`install.py` で検査の道具と一緒に写す | [ADR 0003](adr/0003-two-distributed-skills.md) |
| 検査の道具 | actionlint、shellcheck、zizmor、yamllint を uv のスクリプト1つの依存にまとめ、YAML の formatter は使わない | [ADR 0004](adr/0004-uv-script-toolchain.md) |
| 外部アクションの固定 | ロックファイルが GA になるまで SHA で固定する | [ADR 0005](adr/0005-sha-pin-until-lockfile-ga.md) |
| 新しい構文 | 検査の道具が受け付けない構文（`$/`、ステップの並列実行、`queue`）を使わない | [ADR 0006](adr/0006-no-syntax-ahead-of-linters.md) |
| ランナー | 版付きのラベルに固定し、Linux は `ubuntu-24.04` | [ADR 0007](adr/0007-runner-images.md) |
| 処理時間の報告と合否 | `ci.yml` の最後の `report` ジョブ1つにまとめ、必須チェックもそれ1つにする | [ADR 0008](adr/0008-report-job-gates-ci.md) |
| PR の検証の置き場 | `ci.yml` 1つにまとめ、パスで絞り込まない | [ADR 0009](adr/0009-single-ci-workflow.md) |
| 更新のモード | 作成・保守的更新・破壊的更新の3つ。聞けないときは保守的更新 | [ADR 0010](adr/0010-three-update-modes.md) |

## 全体像

| 技術 | バージョン | 役割 |
|---|---|---|
| GitHub Actions | docs.github.com（2026-10-23 時点）、ランナー `ubuntu-24.04` | 対象。ワークフロー、composite アクション、`dependabot.yml` |
| Claude Code のスキル | Claude Code 2.1.308 | 作成・更新の手順（`gha-workflow`）とレビューの手順（`gha-review`） |
| uv、CPython | uv 0.13.4、CPython 3.12 | 検査の CLI（`.gha/gha.py`）を PEP 723 のスクリプトとして動かす |
| actionlint、shellcheck | 1.7.12、0.11.0 | ワークフローの構文と `run:` のシェルの検査 |
| zizmor | 1.31.1 | セキュリティの監査と、使ってよいアクションの許可表 |
| yamllint | 1.38.0 | YAML の形の検査 |
| PyYAML | 6.0.3 | 構造の検査（`gha_kit` の `rules_*.py`）が YAML を行番号付きで読む |
| ruff、mypy、unittest | 0.17.2、2.4.0、標準 | キット自身の Python の整形・lint・型・テスト |

データの流れは次のとおりである。スキルが、ルールと見本（どちらも `make docs` が正本から作る）を読んでワークフローを書く。書いたワークフローは `gha check` が検査する。`gha check` は外部の4つの道具と構造の検査を回し、全部の指摘を `<ルールID> <パス>:<行>` の1つの形にそろえて返す。GitHub 上では、`ci.yml` の `report` ジョブが REST API で全ジョブ・全ステップの時間を集め、PR のコメントとジョブサマリーに出し、CI の合否を決める。詳しくは [architecture.md](architecture.md) の5章にある。

## ルールを守らせる仕組み

この基盤では、ルールを次の3段で守らせる。

1. **決める**：書き方が分かれうる点ごとに答えを1つ決め、ルールIDを付けて `rules.md` に書いた
2. **縛る**：ルールをできるだけ機械（型、formatter、linter、構造検査、テスト）で強制し、違反例（probe）で効いていることを確かめた。どのルールをどの仕組みで縛っているかは `enforcement-matrix.md` にある
3. **測る**：この基盤を初めて見る独立エージェントに同じ課題を解かせ、書き方の違いを測ってルールを締め込んだ。経過は `convergence-report.md` にある

## 読む順番

1. この文書
2. [architecture.md](architecture.md)：構造と、その理由
3. [rules.md](rules.md)：ルールの全文
4. [enforcement-matrix.md](enforcement-matrix.md)：ルールと検査の対応
5. [research.md](research.md)：技術の調査と出典
6. [adr/](adr/)：主な決定の記録
7. [convergence-report.md](convergence-report.md)：収束テストの結果
