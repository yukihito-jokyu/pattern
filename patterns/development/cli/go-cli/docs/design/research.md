# go-cli の技術調査

採用した推奨には出典を付け、確認の状態を書いている。バージョンは、レジストリのコマンドで確かめた値である。「未確認」の項目が残っている間は、仕上げの検査（`rules_check.py --final`）が通らない。調査日はすべて 2026-10-19 である。

## Go 1.27.2（ツールチェーン）

- 確認方法：`curl -s 'https://go.dev/dl/?mode=json'` → 安定版は `go1.27.2` と `go1.26.9`。`GOTOOLCHAIN=go1.27.2 go version` → `go version go1.27.2 darwin/arm64`
- 確認の状態：確認済み
- 公式の推奨：
  - 各メジャー版は、新しいメジャー版が2つ出るまでサポートされる。2026-10 時点のサポート対象は 1.27 と 1.26（[Release Policy](https://go.dev/doc/devel/release)）
  - Go 1.27 で `encoding/json` の実装が v2 になった。v1 の API はそのまま使え、移行は求められない（[Go 1.27 Release Notes](https://go.dev/doc/go1.27)「New encoding/json/v2 and encoding/json/jsontext packages」）
  - Go 1.27 の gofmt は、整形済みのコードにも小さな空白の変更を出すことがある（同「Gofmt」）
  - `go mod tidy -diff` は書き換えずに差分を出し、更新が必要なら0以外で終わる（[Go 1.23 Release Notes](https://go.dev/doc/go1.23)「Go command」）
  - `testing.T.Context` はテスト終了時に取り消される context を返す（[Go 1.24 Release Notes](https://go.dev/doc/go1.24)「testing」）
  - `signal.NotifyContext` は受け取ったシグナルを原因として context を取り消す（[Go 1.26 Release Notes](https://go.dev/doc/go1.26)「os/signal」）
- 採用するもの：ADR 0002（Go 1.27 と golangci-lint の固定）、TOOL-04、ASYNC-01、TEST-02
- 採用しないもの：`encoding/json/v2` の新しい API。v1 の API で足り、作者が慣れている書き方を1つに保つため（CODE-03 で `encoding/json` の v1 API に固定）
- ツールにできないこと：なし

## flag（Go 標準ライブラリ、Go 1.27.2 に同梱）

- 確認方法：[pkg.go.dev/flag](https://pkg.go.dev/flag)（表示版 go1.27.2）。挙動は試作で `go run . task add "x" --json` を実行して確かめた
- 確認の状態：確認済み
- 公式の推奨：
  - 「Flag parsing stops just before the first non-flag argument ("-" is a non-flag argument) or after the terminator "--".」（同「Command line flag syntax」）
  - 「One or two dashes may be used; they are equivalent.」（同）
  - `ContinueOnError` はエラーを返し、`-h`/`-help` が未定義なら `ErrHelp` を返す（同「type ErrorHandling」「func (*FlagSet) Parse」）
  - 1.22〜1.27 で追加された API は無い（最新の追加は go1.21 の `BoolFunc`）
- 採用するもの：ADR 0003（CLI の枠組み）。最初の位置引数で解析が止まる制約は `internal/cli` の中で吸収し、フラグを位置引数の前後どちらにも書けるようにした（OPS-05）
- 採用しないもの：`fs.String` など値のポインタを返す API と、`TextVar`・`Func`・`BoolFunc`。宣言の書き方を `StringVar`・`BoolVar`・`IntVar` の3つに絞るため（CODE-02）
- ツールにできないこと：サブコマンド、ヘルプの整形、`--json` の共通化、終了コードへの変換。`internal/cli` で補う

## golangci-lint v2.15.0（formatter と linter）

- 確認方法：`go list -m -versions github.com/golangci/golangci-lint/v2` → 最新は v2.15.0。`https://proxy.golang.org/github.com/golangci/golangci-lint/v2/@v/v2.15.0.info` → 2026-10-16 公開。`go tool -modfile=golangci-lint.mod golangci-lint version` → `2.15.0 built with go1.27.2`
- 確認の状態：確認済み
- 公式の推奨：
  - バイナリでの導入を推奨し、`go tool` は推奨しない。使う場合は「the best approach is to use a dedicated module or module file to isolate golangci-lint from other tools or dependencies」（[Install – Local](https://golangci-lint.run/docs/welcome/install/local/)「`go tool` usage recommendations」）。例として `go get -tool -modfile=golangci-lint.mod ...` と `go tool -modfile=golangci-lint.mod golangci-lint run` が載っている
  - `linters.default` は `standard`（errcheck、govet、ineffassign、staticcheck、unused）が既定（[Configuration File](https://golangci-lint.run/docs/configuration/file/)「linters configuration」）
  - `fmt --diff` は差分があれば終了コード1（[pkg/goformat/runner.go#L149](https://github.com/golangci/golangci-lint/blob/v2.15.0/pkg/goformat/runner.go#L149)）。`run` は formatter の違反も「File is not properly formatted (gofumpt)」として報告する（試作で確認）
  - 既定の `issues.uniq-by-line: true` は1行に1件しか出さない（[.golangci.reference.yml](https://github.com/golangci/golangci-lint/blob/v2.15.0/.golangci.reference.yml)「issues」）
- 採用するもの：ADR 0002、ADR 0004（lint の構成）、TOOL-01〜TOOL-04
- 採用しないもの：バイナリでの導入。版がディレクトリの中で固定されず、作者ごとに版が分かれるため（ADR 0002 に理由とリスクを書いた）
- ツールにできないこと：層の間の import の向き（同じ層の別パッケージ同士の禁止を表せない）、ファイルの配置と命名の組、`docs/cli.md` の鮮度。`tools/archcheck` と `tools/clidoc` で補う

使う linter と formatter の名前は `go tool -modfile=golangci-lint.mod golangci-lint help linters` と `help formatters` の一覧で確かめた。設定キーはモジュールキャッシュの `.golangci.reference.yml`（v2.15.0）で確かめ、`golangci-lint config verify` が通ることを確認した。違反を集めた試作ファイルで、次の linter が実際に指摘を出すことを確かめた：asciicheck を除く全件（err113、errcheck、errname、errorlint、forbidigo、funlen、gochecknoglobals、gochecknoinits、godoclint、godot、godox、gosec、importas、mnd、modernize、musttag、nestif、noinlineerr、nonamedreturns、paralleltest、perfsprint、revive の各ルール、staticcheck、tagliatelle、testpackage、unused、usetesting、wrapcheck）。

### formatter（golangci-lint v2.15.0 に同梱）

- 確認方法：`$(go env GOMODCACHE)/github.com/golangci/golangci-lint/v2@v2.15.0/go.mod` → `mvdan.cc/gofumpt v0.12.0`、`golang.org/x/tools v0.52.0`（goimports）
- 確認の状態：確認済み
- 公式の推奨：
  - gofumpt の `extra`（group-params、clothe-returns、balance-calls）で、gofmt より多くの書き方を1つに決められる（[Formatters Configuration](https://golangci-lint.run/docs/formatters/configuration/)「gofumpt」）
  - goimports の `local-prefixes` は、指定した接頭辞の import をサードパーティの後ろの群に分ける（同「goimports」）
  - import は群に分け、標準ライブラリを最初の群にする（[Go Code Review Comments](https://go.dev/wiki/CodeReviewComments)「Imports」）
- 採用するもの：TOOL-01、CODE-03
- 採用しないもの：gci（goimports で足りる）
- ツールにできないこと：なし

## Go の公式の設計指針

- 確認方法：サブエージェントが各ページを取得し、原文の文を確かめた（取得日 2026-10-19）
- 確認の状態：確認済み
- 公式の推奨：
  - コマンドと補助パッケージは、ルートの `package main` と `internal/` に置く。「Initially, it's recommended placing such packages into a directory named internal」（[Organizing a Go module](https://go.dev/doc/modules/layout)「Package or command with supporting packages」）。`pkg/` には触れていない
  - util・common・helper のような意味の無いパッケージ名を避ける（[Code Review Comments](https://go.dev/wiki/CodeReviewComments)「Package Names」、[Google Go Style Decisions](https://google.github.io/styleguide/go/decisions)「Package names」）
  - エラー文字列は小文字で始め、句読点で終えない（Code Review Comments「Error Strings」）
  - sentinel エラーを包むときは `%w` を先頭に置くと種類がすぐ分かる。それ以外は `[...]: %w` の形で末尾に置く（[Google Go Style Best Practices](https://google.github.io/styleguide/go/best-practices)「Placement of %w in errors」）
  - interface は、それを使う側のパッケージに置く（Code Review Comments「Interfaces」）
  - context は第1引数で受け取り、構造体に入れない（同「Contexts」）
  - パッケージのコメントは1ファイルだけに書き、「Package x」で始める。コマンドは「Command x」で始める（[Go Doc Comments](https://go.dev/doc/comment)「Packages」「Commands」）
  - 空のスライスは nil を好むが、JSON では nil が `null` になる（Code Review Comments「Declaring Empty Slices」）
  - テストの失敗文は `YourFunc(%v) = %v, want %v` の形で、実際の値を先に書く（Google Go Style Decisions「Identify the function」「Got before want」）。サブテストの名前は文章ではなく識別子のように付ける（同「Subtest names」）
  - サブコマンドごとにパッケージを分ける必要は無い（Google Go Style Best Practices「Complex command-line interfaces」）
- 採用するもの：STR-01、STR-03、DEP-01、NAM-01、NAM-02、CODE-01、CODE-05、CODE-07、ERR-01、ERR-02、ASYNC-01、TEST-02、TEST-03
- 採用しないもの：
  - Google のフラグ名の規則（snake_case、`package main` だけで定義）。CLI の利用者に見えるフラグは clig.dev と GNU の慣習（`--kebab-case`）に合わせ、定義はコマンドのパッケージに置く（NAM-06）
  - 比較に `cmp.Equal`／`cmp.Diff` を使う推奨。標準ライブラリ外の依存を足さないため、`==` と `slices.Equal` で比べる（TEST-02）
- ツールにできないこと：なし（判定できる部分は lint と archcheck に載せた）

## Command Line Interface Guidelines（clig.dev）

- 確認方法：[clig.dev](https://clig.dev) を取得し原文を確かめた
- 確認の状態：確認済み
- 公式の推奨：
  - 主な出力は stdout、ログやエラーは stderr（「The Basics」）
  - 成功は0、失敗は0以外。0以外の値を主な失敗の種類に対応させる（同）
  - `--json` で JSON を出す（「Output」）
  - `-h`/`--help` でヘルプ、`--version` で版を出す（「Help」「Arguments and flags」）
  - フラグには長い名前を用意し、引数・フラグ・サブコマンドの順序に依存しないようにする（「Arguments and flags」）
  - サブコマンドは `noun verb` が一般的で、種類が違っても同じ動詞を使う（「Subcommands」）
  - 設定の優先順位はフラグ → 環境変数 → プロジェクト設定 → ユーザー設定 → システム設定。XDG に従う（「Configuration」）
- 採用するもの：OPS-01〜OPS-05、NAM-04、STATE-01
- 採用しないもの：短いフラグ（`-a`）。1つのフラグに名前を2つ持たせると書き方が分かれるため（NAM-06）
- ツールにできないこと：なし
