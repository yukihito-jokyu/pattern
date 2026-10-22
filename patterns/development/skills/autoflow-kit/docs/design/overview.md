# autoflow-kit 設計の概要

## ゴール

この基盤のゴールは、同じ依頼を受けた別々の作者（人・エージェント）が、同じ書き方をする状態を保つことである。あわせて、変更が局所に収まる構造にすることを目指す。

この基盤が作るものは「オートフロー」である。オートフローとは、プロジェクトのタスクやユーザーの要望から、計画・実装・検証・AI レビュー・リスクの判定までを AI が自走し、人は決めた関所でだけ判断する流れを指す。AI が自走する以上、「AI ができたと言った」ことは正しさの根拠にならない。そこで正しさを、補助 CLI が持つ機械の関所（段の順序、検査の証拠、投票、リスクの段、承認と版の結び付け）で担保し、人の時間は機械では決められない判断（方向、行き詰まり、最終承認）にだけ使う。この考え方は、Anthropic のコードレビューの記事から取った（[research.md](research.md) の記事の節）。

## 前提

### 受けた指示

- 依頼：プロジェクトのタスクやユーザーの要望から、人がなるべく介入しないオートフローを作るスキルを作る。AI が自走するので正しさを担保する。参考は記事「How the Claude Code team does code review」（<https://claude.dev/blog/solving-code-review-at-anthropic/>）で、レビューの流れの考え方と、人が介入する点を学んで使う
- 指定された技術：Claude Code のスキル
- 質問への回答

  | 項目 | 回答 | 反映した先 |
  |---|---|---|
  | 形 | 準備（リポジトリごとに1回）＋依頼ごとに手順を組んで実行する | `autoflow-setup` と `autoflow` の2つのスキル（[ADR 0002](adr/0002-autoflow-shape.md)） |
  | 終点 | 検証済みの変更で止める。コミットは人の承認の後、push はしない | H3 と `commit`（[ADR 0002](adr/0002-autoflow-shape.md)、GATE-05） |
  | 依頼の取得元 | 文章、Backlog、Redmine、GitLab・GitHub の Issue | `layout.SOURCES` と取得元の表（[ADR 0005](adr/0005-skill-fetches-sources.md)） |
  | 収束テスト | 上限3ラウンド＋最終ラウンドでの通しの実行1回 | manifest の `convergence`、[convergence-report.md](convergence-report.md) |

### 既定値で決めた事項

| 事項 | 決めた値 | 記録 |
|---|---|---|
| 正しさの守り方 | ルールを機械で強制し、違反例と独立エージェントで確かめる | [ADR 0001](adr/0001-machine-enforced-rules.md) |
| スキルとサブエージェントの数 | スキル3つ（setup、本体、learn）、サブエージェント5つ（計画・実装・探索・検証・リスク判定） | [ADR 0003](adr/0003-three-skills-and-five-agents.md) |
| 差分の版の表し方 | 作業ブランチの上の git の tree id | [ADR 0004](adr/0004-tree-snapshot-on-work-branch.md) |
| 人の決定の記録 | 回答の原文付きで `decide` だけが記録する | [ADR 0006](adr/0006-human-answer-record.md) |
| 開発の道具の版 | ruff 0.17.1、mypy 1.20.2 | [ADR 0007](adr/0007-tool-versions.md) |
| 基盤の名前と分野 | `autoflow-kit`、cli-library | [ADR 0008](adr/0008-name-and-domain.md) |
| 進み具合の持ち方 | 追記だけの記録（`trail.jsonl`）と、補助 CLI の状態機械 | [ADR 0009](adr/0009-event-trail-state-machine.md) |
| プロファイルとレビューの既定値 | 厳しめに始める（常に人が見るパス、上限の回数、投票の閾値） | [ADR 0010](adr/0010-strict-defaults.md) |
| 補助 CLI の言語 | Python 3.9 の標準ライブラリだけ（配布先で `python3` だけで動かすため） | rules.md の DEP-03 |

## 全体像

| 技術 | バージョン | 役割 |
|---|---|---|
| Claude Code（スキル、サブエージェント、hooks） | 2.1.296 | フローを進めるスキルと、役ごとのサブエージェント |
| Python | 3.9.6（3.9 以上で動く） | 補助 CLI（標準ライブラリだけ） |
| git | 2.50.1 | 作業ブランチと、差分の版（tree id） |
| ruff | 0.17.1 | 整形と lint |
| mypy | 1.20.2 | 型検査（strict） |
| unittest | 3.9.6（標準ライブラリ） | テスト |
| uv | 0.11.14 | ruff と mypy を `uvx` で版を固定して呼ぶ |

配布物は、スキル（`kit/claude/skills/`）、サブエージェント（`kit/claude/agents/`）、補助 CLI（`kit/.autoflow/`）の3つでできている。スキル `autoflow` は判断をせず、補助 CLI の `status` が出す「次にすること」に従ってサブコマンドを呼ぶだけである。補助 CLI は、段ごとにひな形からサブエージェントへのプロンプトを書き、返ってきた JSON を検証し、検査コマンドを自分で実行し、結果を tree id 付きで `trail.jsonl` に追記する。次の段は、この記録と今の tree から補助 CLI が決める。段の並びは「検証（基準）→ 計画 →（H1）→ 実装 → 検証 →（H2）→ リスクの判定 → AI レビュー → 報告書 → H3 → コミット」である。詳しくは [architecture.md](architecture.md) の2章と6章にある。

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
