# skill-harness2-kit 設計の概要

## ゴール

この基盤のゴールは、同じ依頼を受けた別々の作者（人・エージェント）が、同じ書き方をする状態を保つことである。あわせて、変更が局所に収まる構造にすることを目指す。

作る物は、Claude Code のスキルを改善するための道具である。改善の方法は google-research/harness2（commit `1cfe254`）の方法をそのまま写す。harness2 は「モデルの重みを変えずに、モデルの周り（harness）だけを、正解を使わずに直す」研究の実装である。この基盤では harness を対象スキルのディレクトリ（`SKILL.md`、`references/`、`scripts/`、`assets/`）に読み替える。

## 前提

### 受けた指示

- google-research/harness2 の知見をもとに、スキルをブラッシュアップするスキルのパターンを作る
- 知見を重点的に調べ、どういう仕組みで、どう制御しているかを調べ上げ、模倣する

調べた仕組みと、それぞれをこの基盤のどこに移したかは [research.md](research.md) の「harness2 の仕組み」の表にある。技術・ツールの指定は無かった。

### 既定値で決めた事項

指示に無かった事項は、次のように決めた。

| 事項 | 決定 | 記録 |
|---|---|---|
| 基盤の名前 | `skill-harness2-kit`。配布するスキルは `skill-harness2`、補助 CLI の置き場は `.h2/` | [ADR 0002](adr/0002-kit-name.md) |
| モデルの呼び出し | すべて閉じ込めた `claude -p` で行う（API キーや SDK を使わない） | [ADR 0003](adr/0003-claude-p-as-the-only-channel.md) |
| harness に当たるもの | 対象スキルのディレクトリ。編集面を4種類に絞る | [ADR 0004](adr/0004-skill-as-the-harness.md) |
| プロンプト | harness2 のプロンプトを、構造と強調を保って日本語に移す | [ADR 0005](adr/0005-imitate-harness2-prompts.md) |
| 言語と道具 | Python 3.9 の標準ライブラリだけ。開発の検査は ruff 0.17.2 と mypy 1.20.2 | [ADR 0006](adr/0006-mypy-1-20-for-python-3-9.md) |
| 採用の仕方 | 各タスクは承認時のスキルから始め、選ばれた候補を書き込むのは人が選んだときだけ | [ADR 0007](adr/0007-per-task-h0-and-human-adoption.md) |

## 全体像

| 技術 | バージョン | 役割 |
|---|---|---|
| Python | 3.9 以上（標準ライブラリだけ。手元の確認は 3.9.6） | 補助 CLI、配布の `install.py`、構造検査、テスト |
| Claude Code | 2.1.308 で確かめた | 実行（`claude -p`）と、編集・合成・選択・振り返りのセッション |
| ruff | 0.17.2 | 整形と lint |
| mypy | 1.20.2 | 型の検査（strict、`python_version = 3.9`） |
| unittest | 標準ライブラリ | テスト。`claude` の代わりに偽の `claude`（`tests/fixtures/fake_claude.py`）を子プロセスとして動かす |

利用者は、Claude Code の中で配布スキル `skill-harness2` を使う。スキルは手順と人に聞く場面だけを持ち、状態を読み書きするのは補助 CLI である。補助 CLI は、準備（`init`、`check`、`approve`）→ 実行（`run`）→ 結果の確認（`status`、`show`、`judge`）→ 採用（`adopt`）の段に分かれる。`run` は1つのタスク・1つのモードごとに、基準の実行 → INV と DOM の提案 → 候補の試行 → 合成 → 匿名の選択 → 振り返りとライブラリの順に進み、実行 4k 回・編集のセッション 3k 回を台帳で確かめる。詳しくは [architecture.md](architecture.md) の「データの流れ」にある。

## ルールを守らせる仕組み

この基盤では、ルールを次の3段で守らせる。

1. **決める**：書き方が分かれうる点ごとに答えを1つ決め、ルールIDを付けて `rules.md` に書いた
2. **縛る**：ルールをできるだけ機械（型、formatter、linter、構造検査、テスト）で強制し、違反例（probe）で効いていることを確かめた。どのルールをどの仕組みで縛っているかは `enforcement-matrix.md` にある
3. **測る**：この基盤を初めて見る独立エージェントに同じ課題を解かせ、書き方の違いを測ってルールを締め込んだ。経過は `convergence-report.md` にある

harness2 から写した制御（答えを見ない、壊れた候補を試さない、選択を匿名にする、回数の恒等式を確かめる）も、同じ3段でルールにしてある。たとえば「方法は答えを見ない」は STATE-04 で、測定の語と採点の印を機械で拒み、事後の検査（`judge`）を方法のモジュールから import できないようにしている。

## 読む順番

1. この文書
2. [architecture.md](architecture.md)：構造と、その理由
3. [rules.md](rules.md)：ルールの全文
4. [enforcement-matrix.md](enforcement-matrix.md)：ルールと検査の対応
5. [research.md](research.md)：技術の調査と出典
6. [adr/](adr/)：主な決定の記録
7. [convergence-report.md](convergence-report.md)：収束テストの結果
