# 0002 Go 1.27.2 と golangci-lint v2.15.0 をディレクトリの中で固定する

- 状態：採用
- 関係するルール：TOOL-01、TOOL-04、PROC-03、DEP-04

## 背景

同じコードでも、Go の版が違えば gofmt の出力が変わり（Go 1.27 の gofmt は整形済みのコードにも小さな変更を出すことがある）、golangci-lint の版が違えば指摘の内容が変わる。作者ごとに手元の版が違うと、同じ依頼から違う差分が生まれ、検査の結果も揃わない。

Go の版はユーザーの指示で「Go 1.27（最新安定版）」に決まっている。残る問題は、golangci-lint をどう導入して版を固定するかである。

golangci-lint の公式は、バイナリでの導入を推奨し、`go tool` での導入は推奨していない。ただし `go tool` を使う場合は「専用のモジュールか modfile で他の依存から切り離すのが最良」とし、`-modfile=golangci-lint.mod` の例を載せている（[research.md「golangci-lint v2.15.0」](../research.md#golangci-lint-v2150formatter-と-linter)）。

## 選択肢

| 選択肢 | 良い点 | 悪い点 |
|---|---|---|
| バイナリを各自で導入する（公式の推奨） | 公式の推奨どおり。golangci-lint の依存がプロジェクトに入らない | 版がディレクトリの中に記録されず、作者ごとに版が分かれる。導入の手順が要る |
| `go.mod` に `tool` として足す | `go tool golangci-lint` だけで動く | golangci-lint の多数の依存が `go.mod` に入り、DEP-04（外部モジュールを使わない）の検査と衝突する。依存の版が本体と干渉しうる |
| 専用の `golangci-lint.mod` に `tool` として足す | 版が `golangci-lint.mod` と `golangci-lint.sum` に固定される。本体の `go.mod` は空のまま。Go さえあれば追加の導入が要らない | 公式の推奨（バイナリ）から外れる。初回の実行でビルドに時間がかかる |

## 決定

- `go.mod` に `go 1.27` と `toolchain go1.27.2` を書く。手元の Go が古くても、Go のツールチェーンの自動切り替えで go1.27.2 が使われる
- golangci-lint v2.15.0 は、専用の `golangci-lint.mod` に `tool github.com/golangci/golangci-lint/v2/cmd/golangci-lint` として固定し、`go tool -modfile=golangci-lint.mod golangci-lint` で起動する
- 起動は `Makefile` のターゲットにまとめ、作者は `make check`・`make fix` だけを使う
- 版の行は `tools/archcheck` の TOOL-04 が確かめ、`make tidy-check` が両方の modfile で `go mod tidy -diff` を回す

## 理由

この基盤のゴールは、作者が誰でも同じ検査結果を得ることである。バイナリの導入は公式の推奨だが、版をディレクトリの中に固定できない。専用の modfile は、公式が `go tool` を使う場合の最良の方法として挙げている形であり、版の固定と本体の依存の空っぽを両立できる。

## 影響

- 楽になること：`git clone` の後に Go だけあれば `make check` が動く。版の違いによる整形や指摘の差が出ない
- 難しくなること：初回の `make check` で golangci-lint のビルドに1分ほどかかる（2回目以降はビルドキャッシュが効く）
- リスク：公式の推奨から外れているため、golangci-lint の依存が Go 1.27 と食い違った場合に、ビルドできない版が出る可能性がある。その場合は版を上げる（PROC-03）か、バイナリでの導入に切り替える ADR を書く
- 変えたくなったとき：PROC-03 の手順で、`go.mod`、`golangci-lint.mod`、`tools/archcheck` の TOOL-04 の期待値、research.md、manifest を同じ差分で変える
