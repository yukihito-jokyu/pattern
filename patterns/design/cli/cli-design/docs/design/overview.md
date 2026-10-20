# cli-design 設計の概要

## ゴール

この基盤のゴールは、同じ依頼を受けた別々の作者（人・エージェント）が、同じ書き方をする状態を保つことである。あわせて、変更が局所に収まる構造にすることを目指す。

この基盤は、CLI の「外から見える形」（コマンド、位置引数、オプション、出力、終了コード、環境変数）を設計するためのものである。設計の結果は、実装の言語に依存しない仕様 `specs/<name>/cli.json` として残す。実装者は、どの言語で書いても、この仕様と、仕様から生成したリファレンス `cli.md` に従えば同じ CLI を作れる。

## 前提

### 受けた指示

依頼は「CLI 設計用のスキルを作成して」であり、追加の質問への回答は次の3つだった。

| 問い | 回答 | この基盤での扱い |
|---|---|---|
| 実装の言語 | 設計なので言語は決めない。どの言語でも対応できるようにする | 仕様を言語に依存しない JSON にし（[ADR 0002](adr/0002-json-spec-and-clispec.md)）、言語ごとの実装方法を実装用スキルの `references/stdlib-mapping.md` に Go・Python・Node.js・Rust の4つで書いた |
| 引数の解析 | 標準ライブラリだけ | 仕様が約束する引数の書式を、4言語の標準ライブラリで同じ結果になる部分だけにした（DEP-03、DEP-04、[ADR 0005](adr/0005-generated-help-and-conformance.md)） |
| 配布 | 言語ごとに異なるが、配布できるようにする | 版の書式を、各言語のパッケージの版として使える数字3つにした（OPS-06）。配布の手順は research.md の「配布」に調査として残した |

### 既定値で決めた事項

次の事項は指示に無かったため、既定値で決めた。理由は各 ADR にある。

- ヘルプの文面を英語（ASCII）にし、サブコマンドを `<名詞> <動詞>` の2段に、動詞を `create`・`list`・`view`・`edit`・`delete` に、最初の版を `1.0.0` にした（[ADR 0006](adr/0006-defaults-not-in-request.md)）
- 検査ツールを Python 3.14 の標準ライブラリだけで書き、uv で起動する（[ADR 0003](adr/0003-python-and-uv.md)）
- 設定ファイル・対話の入力・色を持たない（[ADR 0004](adr/0004-no-config-prompt-color.md)）

## 全体像

| 技術 | バージョン | 役割 |
|---|---|---|
| 仕様の形式 `cli.json` | 1 | CLI の設計の正本。キーの表は rules.md の CODE-01 |
| Python | 3.14（`.python-version`） | 検査ツール `tools/clispec` の実行環境。標準ライブラリだけを使う |
| uv | 0.13.3 | Python 3.14 を起動する |
| GNU Make | 3.81 | 作者が使うコマンドの入口（`make check` など） |
| Go flag・Python argparse・Node.js util.parseArgs・Rust std::env::args | go1.27.3・3.14.8・v24.22.0・1.99.1 | 実装の引数解析。仕様の書式はこの4つで同じ結果になる部分に限る |

データは次の順に流れる。詳しくは [architecture.md](architecture.md) にある。

1. 作者が生成器（`make new`・`make command`・`make field`）で `cli.json` を作り、依頼に合わせて埋める
2. `make fix` が `cli.json` を整形し、版を決め、`cli.md`（リファレンスとヘルプの文面）を生成する
3. `make check` が仕様をルールで検査する
4. `make release` が版を確定し、`released/<version>.json` に写す。以降の変更は、この版と比べて互換性を判定する
5. 実装者は `cli.md` に従って各言語で実装し、`make conform` で外から実行して仕様どおりかを確かめる

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
