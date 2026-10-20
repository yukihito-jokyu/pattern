# go-cli 設計の概要

## ゴール

この基盤のゴールは、同じ依頼を受けた別々の作者（人・エージェント）が、同じ書き方をする状態を保つことである。あわせて、変更が局所に収まる構造にすることを目指す。

対象は、Go の標準ライブラリだけで作る、名詞・動詞のサブコマンドを持つ CLI（`go-cli task add "Buy milk"`）である。この基盤は、そうした CLI に「サブコマンドを足す」「フラグを足す」「記録する項目を足す」「名詞を足す」といった依頼が来たとき、誰が書いても同じファイルに同じ形のコードが入るようにするための、構造・ルール・検査・見本の一式である。

## 前提

### 受けた指示

- 依頼：「Go で作る CLI のアーキテクチャパターン」
- 確認して決めた事項：
  | 事項 | 回答 |
  |---|---|
  | 引数の解析 | 標準ライブラリの `flag` |
  | 配布の方法 | `go build` と `go install` だけ |
  | Go の版 | Go 1.27（最新安定版。go1.27.2 に固定） |

### 既定値で決めた事項

指示に無く、既定値で決めた事項は [ADR 0005](adr/0005-defaults-not-in-the-request.md) に表でまとめた。主なものは次のとおりである。

- モジュールのパスは `example.com/go-cli`、コマンド名は `go-cli`
- 参照実装の題材はタスク管理（`task add`・`task complete`・`task list`）
- 業務データはデータディレクトリの JSON ファイルに保存する
- 外部の依存は使わない。golangci-lint は専用の modfile で固定する（[ADR 0002](adr/0002-pin-go-and-golangci-lint.md)）
- 対応する OS は macOS と Linux。CI・ライセンス・リリースの自動化は置かない

## 全体像

| 技術 | バージョン | 役割 |
|---|---|---|
| Go | 1.27.2（`toolchain` で固定） | 言語、ビルド、`go vet`、`go test` |
| flag（標準ライブラリ） | Go 1.27.2 に同梱 | フラグの解析。サブコマンドの枠組みは `internal/cli` で補う（[ADR 0003](adr/0003-cli-framework-on-stdlib-flag.md)） |
| golangci-lint | v2.15.0（`golangci-lint.mod` で固定） | formatter（gofumpt v0.12.0、goimports、golines）と linter |
| tools/archcheck | この基盤の中で作成 | 構造検査（層の境界、配置と命名の組、項目の一致）（[ADR 0004](adr/0004-lint-and-structure-checks.md)） |
| tools/clidoc | この基盤の中で作成 | `docs/cli.md` の生成と鮮度の確認 |
| GNU Make | 3.81 以上 | 検査と生成の入口（`make check`、`make fix`、`make generate`） |

コードは、入口（`main.go`）、組み立て（`internal/app`）、CLI の枠組み（`internal/cli`）、サブコマンド（`internal/command/<noun>cmd`）、業務の規則（`internal/domain/<noun>`）、保存（`internal/adapter/<noun>store`）に分かれる。依存は外側から業務の規則に向かい、業務の規則は CLI の書き方にも保存形式にも依存しない。1回の実行は、`main.go` → `app` → `cli` → `command` → `domain` → `adapter` と進み、結果の出力型を `cli` が JSON か文章で書いて、エラーの種類から終了コードを決める。詳しくは [architecture.md](architecture.md) にある。

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
   - [0001](adr/0001-machine-enforced-rules.md)：ルールを機械で強制し、独立エージェントで検証する
   - [0002](adr/0002-pin-go-and-golangci-lint.md)：Go と golangci-lint の版をディレクトリの中で固定する
   - [0003](adr/0003-cli-framework-on-stdlib-flag.md)：標準ライブラリ flag の上にサブコマンドの枠組みを作る
   - [0004](adr/0004-lint-and-structure-checks.md)：linter を広く有効にし、層の境界と命名の組は構造検査で縛る
   - [0005](adr/0005-defaults-not-in-the-request.md)：指示に無かった事項を既定値で決める
   - [0006](adr/0006-japanese-comments.md)：コードのコメントと定型文を日本語にそろえる
7. [convergence-report.md](convergence-report.md)：収束テストの結果
