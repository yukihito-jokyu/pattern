# go-cli のルール

このファイルは go-cli のルールの正本である。AGENTS.md・スキル・レビューの指摘・検査のエラーは、ここのルールIDを参照する。ルールの変更手順は AGENTS.md の「ルールを変えたいとき」に従う。

## 読み方

- ルールIDは `<接頭辞>-<連番>` である。廃止したルールも ID を再利用せず、`- 状態: 廃止` と書いて残す
- **強制**の先頭のキーワードは、そのルールを守らせる仕組みを表す

  | キーワード | 仕組み |
  |---|---|
  | `type` | 型・可視性で書けなくする |
  | `format` | formatter |
  | `lint` | linter |
  | `structure` | 構造検査 |
  | `test` | テスト |
  | `generator` | 生成器 |
  | `review` | レビュー用スキル |
  | `doc` | 文書のみ |

  ルールと仕組みの対応表は `enforcement-matrix.md`（生成物）にある
- `type`・`format`・`lint`・`structure`・`test` のルールには、違反例（probe）が `.foundation/probes.json` にあり、検査で落ちることを確かめてある
- 構造検査は `tools/archcheck`（`make arch`）と `tools/clidoc`（`make docs-check`）である。違反は `<ルールID> <パス>:<行> <説明>` の形で出る。lint の違反は `(<linter 名>)` で終わる行で出る。forbidigo の違反の説明はルールIDで始まる

## ルールの書式

`rules_check.py` がこの書式を読む。項目名と順番を変えない。

```markdown
### <接頭辞>-<2桁の番号> <決定を1行で要約した題名>

- 軸: <答えている軸の記号。複数ならカンマ区切り>
- 決定: <読んだ2人が同じ判定をできる1文。条件で答えが変わるなら、次の行から2字下げで決定表を書く>
- 理由: <何が揺れ、何が壊れるのを防ぐか>
- 出典: <research.md の該当節、または公式ドキュメントの URL。無ければ行ごと省く>
- 強制: <キーワード。複数ならカンマ区切り> — <仕組みの説明：どの設定・スクリプトのどこで縛るか>
- probe: <この強制を証明する probe の ID。機械の段ごとに1件以上>
- 良い例:
  <5行以内のコード。長くなるなら「見本: <参照実装のパス>」と書く>
- 悪い例:
  <実際に書かれがちな違反。5行以内>
```

- 機械の段（`type`・`format`・`lint`・`structure`・`test`）を含まないルールには、`- 機械化しない理由:` を**強制**の次の行に足し、`probe` の値は `なし` にする
- 軸の記号は範囲で書いてもよい（`D1〜D3` は D1、D2、D3 と読まれる）
- 番号は節ごとに 01 から、カタログの軸の順（同じ軸の中では決定の順）に振る
- ルールが0件の節は、見出しごと消し、その節の軸を「対象外とした軸」表に書く
- 決定の中のコード片（`` ` `` で囲んだ部分）は、あいまいな語の検査から除かれる

## 用語

| 用語 | 意味 |
|---|---|
| 名詞 | コマンドの1段目（`task`）。業務の対象1種類を表し、domain・adapter・command の各層にパッケージを1つずつ持つ |
| 動詞 | コマンドの2段目（`add`）。サブコマンドとも呼ぶ。`internal/command/<noun>cmd/<verb>.go` のファイル1つに対応する |
| 層 | `internal/` の直下のディレクトリ。app、cli、command、domain、adapter、errkind の6つ |
| エンティティ | domain の `<Noun>` 型（`task.Task`）。1件の業務データを表す |
| Service | domain の use case をまとめた型（`task.Service`）。サブコマンドはこのメソッドを1つ呼ぶ |
| Store | adapter の型。domain の `Repository` をファイルで実装する |
| ビュー | command の `<noun>View` 型。エンティティが出力でどう見えるかを表す |
| 出力型 | `<verb>Output` 型。サブコマンドの結果で、`--json` なら JSON、そうでなければ `WriteText` の文章になる |
| エラーの種類 | `internal/errkind` の sentinel エラー（`ErrInvalid`、`ErrNotFound`）。終了コードを決める |
| データディレクトリ | 業務データの JSON ファイルを置くディレクトリ。STATE-01 で決める |
| 参照実装 | `task` 名詞の一式（domain、adapter、command、テスト）。新しいコードはこれを写す |
| 公開面 | CLI の利用者から見える名前と形：サブコマンド名、フラグ名、位置引数、JSON のキー、終了コード、環境変数名 |

## 追加した軸

カタログに無い、この分野に固有の軸を定義する。domain-profiles.md がその分野に定めた X 軸はすべて載せる。無ければ表を空のまま残す。

| 軸 | 内容 | 置く節 |
|---|---|---|
| X1 | 終了コードと出力の形式（標準出力と標準エラーの使い分け、機械可読の出力） | OPS |
| X2 | 公開 API の互換性（CLI の公開面を変えるときの手順） | PROC |

## STR 配置と構造

### STR-01 Go のコードを置くディレクトリを表の8種類に限る

- 軸: A1
- 決定: `.go` ファイルを置いてよいディレクトリは次の表の8種類だけとし、`internal/` と `tools/` の下には `.go` 以外のファイルを置かない。
  | ディレクトリ | 置くもの |
  |---|---|
  | `.`（ルート） | `main.go` だけ |
  | `internal/app` | コマンド木の組み立てと設定の読み込み |
  | `internal/app/apptest` | テストで CLI を実行する道具 |
  | `internal/cli` | フラグ解析・ヘルプ・出力・終了コードの枠組み |
  | `internal/command/<noun>cmd` | 名詞1つ分のサブコマンド |
  | `internal/domain/<noun>` | 名詞1つ分のエンティティと use case |
  | `internal/adapter/<noun>store` | 名詞1つ分の保存 |
  | `internal/errkind` | エラーの種類 |
  | `tools/<name>` | 検査と生成の道具（`archcheck`、`clidoc`） |
- 理由: 置き場の候補が開いていると、`pkg/`、`util/`、`internal/shared/` のように作者ごとに新しい置き場が生まれ、同じ種類のコードが散る。置き場が閉じていれば、どこを読めばよいかが常に予測できる
- 出典: research.md「Go の公式の設計指針」（`internal/` に置く、util・common を避ける）
- 強制: structure — `tools/archcheck` の STR-01（ディレクトリの許可表）
- probe: STR-01-a, STR-01-b
- 良い例:
  ```text
  internal/domain/task/task.go
  internal/command/taskcmd/add.go
  ```
- 悪い例:
  ```text
  internal/util/strings.go
  pkg/task/task.go
  ```

### STR-02 新しい名詞と動詞は決まったファイル一式で足す

- 軸: A2
- 決定: 追加するものごとに、作るファイルと変えるファイルを次の表のとおりにし、`<noun>cmd.go` の `Commands` は動詞の、`app.go` の `Groups` はパッケージ名のアルファベット順に並べる。
  | 追加するもの | 作るファイル | 変えるファイル |
  |---|---|---|
  | 動詞（サブコマンド） | `internal/command/<noun>cmd/<verb>.go`、`<verb>_test.go` | `<noun>cmd.go` の `Commands`、Service にメソッドが無ければ `internal/domain/<noun>/service.go`、`docs/cli.md`（`make generate`） |
  | 名詞 | `internal/domain/<noun>/` の `<noun>.go`・`service.go`・`repository.go`・`<noun>_test.go`、`internal/adapter/<noun>store/` の `<noun>store.go`・`<noun>store_test.go`、`internal/command/<noun>cmd/` の `<noun>cmd.go`・`view.go`・最初の動詞の2ファイル | `internal/app/app.go`、`docs/cli.md`（`make generate`） |
- 理由: 足すファイルの組が決まっていないと、テストを書かない作者、Service を経由しない作者、保存を command に書く作者が出る。組が決まっていれば、1つの変更で触るファイルが予測できる
- 強制: structure, doc — `tools/archcheck` の STR-02（名詞ごとに domain・adapter・command の3つのパッケージがそろっていること、`Commands` と `Groups` の並び）。手順は実装用スキルの patterns.md
- probe: STR-02-a
- 良い例:
  ```text
  internal/domain/note/      internal/adapter/notestore/      internal/command/notecmd/
  ```
- 悪い例:
  ```text
  internal/domain/note/ だけを作り、notestore と notecmd を作らない
  ```

### STR-03 ディレクトリごとに置いてよいファイル名を決める

- 軸: A3
- 決定: 各ディレクトリの `_test.go` 以外のファイルは、次の表の名前だけにする。
  | ディレクトリ | ファイル | 中身 |
  |---|---|---|
  | `internal/domain/<noun>` | `<noun>.go` | エンティティ、定数、`Parse<X>` 関数、`validate<Field>` 関数 |
  | `internal/domain/<noun>` | `service.go` | `Service`、`NewService`、use case のメソッド |
  | `internal/domain/<noun>` | `repository.go` | `Repository` interface |
  | `internal/adapter/<noun>store` | `<noun>store.go` | `Store` と保存形式 |
  | `internal/command/<noun>cmd` | `<noun>cmd.go` | `New` |
  | `internal/command/<noun>cmd` | `view.go` | `<noun>View` と `to<Noun>View` |
  | `internal/command/<noun>cmd` | `<verb>.go` | サブコマンド1つ（STR-04） |
  | `internal/app` | `app.go`、`config.go` | 組み立て、設定 |
  | `internal/app/apptest` | `apptest.go` | テストの道具 |
  | `internal/cli` | `cli.go`、`exit.go`、`help.go`、`table.go` | 枠組み |
  | `internal/errkind` | `errkind.go` | エラーの種類 |
  | `tools/<name>` | `main.go` | 道具 |
- 理由: 同じ種類のコードを1ファイルにまとめるか分けるかは作者ごとに分かれる。ファイル名を固定すれば、型や関数を探すときに開くファイルが1つに決まる
- 強制: structure — `tools/archcheck` の STR-03
- probe: STR-03-a
- 良い例:
  ```text
  internal/domain/task/task.go     # Task、ParseID、validateTitle
  ```
- 悪い例:
  ```text
  internal/domain/task/validation.go
  internal/command/taskcmd/helpers.go
  ```

### STR-04 サブコマンドのファイルは5つの宣言を決まった順に持つ

- 軸: A3, D1
- 決定: `<verb>.go` は、トップレベルの宣言として次の5つだけをこの順に持つ：`type <verb>Options struct`、`type <verb>Output struct`、`func new<Verb>(...) *cli.Command`、`func run<Verb>(ctx context.Context, ...) (<verb>Output, error)`、`func (o <verb>Output) WriteText(w io.Writer) error`。
- 理由: サブコマンドは最も頻繁に足される単位である。宣言の数・名前・順を固定すると、別の作者が書いても同じ形のファイルになり、差分を比べるだけでレビューできる
- 強制: structure — `tools/archcheck` の STR-04（宣言の種類・名前・順）
- probe: STR-04-a, STR-04-b
- 良い例:
  見本: `internal/command/taskcmd/complete.go`
- 悪い例:
  ```go
  func newArchive(svc *task.Service) *cli.Command {
  	return &cli.Command{Run: func(ctx context.Context) (cli.Output, error) {
  		return svc.Archive(ctx) // run<Verb> と <verb>Output が無い
  ```

### STR-05 共有したいコードは決定表の置き場に置く

- 軸: A4
- 決定: 2か所以上で使うコードは、次の決定表の置き場に置く。
  | 共有したいもの | 置き場 |
  |---|---|
  | 同じ名詞の複数のサブコマンドで使う、出力の組み立て | `<noun>cmd/view.go` の非公開の関数かビューのメソッド |
  | 同じ名詞の複数のサブコマンドで使う、文字列から値への変換と検証 | `domain/<noun>/<noun>.go` の `Parse<X>` か `validate<Field>` |
  | 同じ名詞の複数の use case で使う処理 | `domain/<noun>/service.go` の非公開の関数 |
  | 名詞をまたいで使い、業務の知識を含まない、表示や引数の扱い | `internal/cli` |
  | 名詞をまたぐ業務の処理 | DEP-03 に従い、command で2つの Service を呼んで組み合わせる |
  | 上のどれでもない | 実装せず、新しいパターンの提案として報告する |
- 理由: 共有の置き場が決まっていないと、同じ処理がコピーされるか、`util` のような何でも入る場所が生まれる。置き場を意味で決めれば、使う側の import も1通りになる
- 出典: research.md「Go の公式の設計指針」（util・common・helper を避ける）
- 強制: review — レビュー用スキルの確認項目
- 機械化しない理由: どこに置くかは処理の意味（業務の知識を含むか、どの名詞のものか）で決まり、ファイルや import の字面では判定できない。新しいディレクトリを作ることは STR-01 で機械が止める
- probe: なし
- 良い例:
  ```go
  // complete.go と remove.go の両方が使う
  id, err := task.ParseID(opts.id)
  ```
- 悪い例:
  ```go
  // complete.go と remove.go にそれぞれ strconv.Atoi を書く
  id, err := strconv.Atoi(opts.id)
  ```

### STR-06 テストは対象の隣に置き、テスト用の道具は apptest だけにする

- 軸: A5
- 決定: テストファイルは `<対象のファイル名>_test.go` として対象と同じディレクトリに置き、テスト用の道具は `internal/app/apptest` だけに置き、`testdata/` ディレクトリと golden ファイルを作らない。
- 理由: テストの置き場とテスト用の共有コードの置き場が分かれると、作者ごとに `testutil`、`fixtures`、`testdata` が生まれる。置き場を1つにすれば、テストの書き方も見本から写せる
- 強制: structure — `tools/archcheck` の STR-06（テストファイル名が同じディレクトリの `.go` ファイルと対になること）と STR-01（`internal/` に `.go` 以外を置かない）
- probe: STR-06-a
- 良い例:
  ```text
  internal/command/taskcmd/add.go
  internal/command/taskcmd/add_test.go
  ```
- 悪い例:
  ```text
  internal/command/taskcmd/helpers_test.go
  internal/command/taskcmd/testdata/list.golden
  ```

### STR-07 生成物は docs/cli.md だけにし、手で編集しない

- 軸: A6
- 決定: 生成物は `docs/cli.md`（コマンドの一覧、フラグ、終了コード）だけとし、`make generate`（`tools/clidoc`）で作り、手で編集しない。
- 理由: 生成物を手で直すと、次の生成で消えるか、コードと食い違う。生成と鮮度の確認を check に入れれば、ヘルプの文言を変えた作者全員が同じ手順で文書を直す
- 強制: structure — `tools/clidoc -check`（`make docs-check`）が、生成し直した内容と `docs/cli.md` を比べ、違えば STR-07 で落ちる
- probe: STR-07-a
- 良い例:
  ```sh
  make generate   # Summary やフラグを変えた後
  ```
- 悪い例:
  ```text
  docs/cli.md の表を手で書き換え、make generate を回さない
  ```

### STR-08 main.go は app.Run を呼んで終了するだけにする

- 軸: A7
- 決定: `main.go` のトップレベルの宣言は `func main()` だけとし、その中身は `signal.NotifyContext`、`app.Run`、`stop()`、`os.Exit` の4つの呼び出しだけにする。
- 理由: 入口に処理を書き始めると、テストできないコードが増え、どこまでが入口かが作者ごとに変わる。入口を固定すれば、プロセスに触れる場所が1つに決まる
- 出典: research.md「Go の公式の設計指針」（ルートの `package main` と `internal/`）
- 強制: structure — `tools/archcheck` の STR-08（`main.go` の宣言が `main` だけであること）
- probe: STR-08-a
- 良い例:
  見本: `main.go`
- 悪い例:
  ```go
  func main() {
  	if len(os.Args) < 2 { fmt.Println("usage: ..."); os.Exit(2) }
  ```

## DEP 境界と依存

### DEP-01 層の間の import は許可表の組だけにする

- 軸: B1
- 決定: 各パッケージが import してよいモジュール内のパッケージは、次の許可表の組だけとし、テストファイル（`_test.go`）は加えて自分のパッケージと `internal/app/apptest` を import してよい。
  | import する側 | import してよい側 |
  |---|---|
  | `main.go` | `internal/app` |
  | `internal/app` | `internal/cli`、`internal/command/*`、`internal/domain/*`、`internal/adapter/*`、`internal/errkind` |
  | `internal/app/apptest` | `internal/app` |
  | `internal/cli` | `internal/errkind` |
  | `internal/command/<noun>cmd` | `internal/cli`、`internal/domain/*`、`internal/errkind` |
  | `internal/domain/<noun>` | `internal/errkind` |
  | `internal/adapter/<noun>store` | `internal/domain/<noun>` |
  | `internal/errkind` | なし |
  | `tools/<name>` | `internal/app`、`internal/cli` |
- 理由: 依存の向きが決まっていないと、command から adapter を直接呼ぶ、domain が cli に依存する、といった近道が生まれ、1つの変更が層をまたいで広がる。向きを一方向に固定すると、domain と adapter を CLI の都合と切り離して変えられる
- 強制: structure — `tools/archcheck` の DEP-01（`architecture.md` の依存の許可表と同じ表をコードに持つ）
- probe: DEP-01-a, DEP-01-b
- 良い例:
  ```go
  // internal/command/taskcmd/list.go
  import "example.com/go-cli/internal/domain/task"
  ```
- 悪い例:
  ```go
  // internal/command/taskcmd/list.go
  import "example.com/go-cli/internal/adapter/taskstore"
  ```

### DEP-02 パッケージが公開する名前を層ごとに決める

- 軸: B2
- 決定: 公開する（大文字で始まる）トップレベルの名前は、層ごとに次の表のものだけにする。
  | パッケージ | 公開してよい名前 |
  |---|---|
  | `internal/command/<noun>cmd` | `New` |
  | `internal/adapter/<noun>store` | `Store`、`New`、`Store` のメソッド `Load`・`Save` |
  | `internal/errkind` | `Err` で始まる変数 |
  | `internal/app` | `Env`、`New`、`Run` |
  | `internal/app/apptest` | `Harness`、`Result`、`New`、`Harness` のメソッド `Run`・`Setup`・`Setenv` |
  | `internal/domain/<noun>` | 名前の制限なし（エンティティ、`Filter` のような引数の型、`Parse<X>`、`Service`、`NewService`、`Repository`） |
  | `internal/cli` | 名前の制限なし |
- 理由: 公開面が広いと、別のパッケージが内部の型や関数に依存し、変更が局所に収まらなくなる。全体を `internal/` に置いてモジュールの外から触れなくしたうえで、モジュールの中でも入口を絞る
- 出典: research.md「Go の公式の設計指針」（`internal/` に置く）
- 強制: structure — `tools/archcheck` の DEP-02（層ごとの公開名の許可表）
- probe: DEP-02-a
- 良い例:
  ```go
  func New(svc *task.Service) *cli.Group { ... }
  func newAdd(svc *task.Service) *cli.Command { ... }
  ```
- 悪い例:
  ```go
  func NewAdd(svc *task.Service) *cli.Command { ... }
  ```

### DEP-03 同じ層の別の名詞のパッケージを import しない

- 軸: B3
- 決定: `command`・`domain`・`adapter` の各層で、ある名詞のパッケージは別の名詞の同じ層のパッケージを import せず、2つの名詞をまたぐ処理は `internal/command/<noun>cmd` が2つの Service を受け取って組み合わせる。
- 理由: 名詞どうしが直接参照し合うと、片方の変更がもう片方を壊し、循環 import も起きやすい。組み合わせる場所を上の層に1つ決めれば、各名詞を独立して変えられる
- 強制: structure — `tools/archcheck` の DEP-03
- probe: DEP-03-a
- 良い例:
  ```go
  func New(tasks *task.Service, notes *note.Service) *cli.Group { ... } // command で組み合わせる
  ```
- 悪い例:
  ```go
  // internal/domain/note/service.go
  import "example.com/go-cli/internal/domain/task"
  ```

### DEP-04 外部モジュールを使わず標準ライブラリだけで書く

- 軸: B4
- 決定: `go.mod` に `require` を書かず、コードは標準ライブラリとモジュール内のパッケージだけを import する。
- 理由: 指示は標準ライブラリの `flag` だけで作ることである。ライブラリを1つ許すと、どのライブラリを足すかで作者ごとに分かれ、覚えることも増える
- 出典: research.md「flag」
- 強制: structure — `tools/archcheck` の DEP-04（`go.mod` の `require` を検出）。外部のパッケージを import すると `go build` も落ちる
- probe: DEP-04-a
- 良い例:
  ```go
  import "flag"
  ```
- 悪い例:
  ```go
  import "github.com/spf13/cobra"
  ```

### DEP-05 副作用のある標準パッケージと関数は決まった場所でだけ使う

- 軸: B5
- 決定: 次の標準パッケージと関数は表の場所でだけ使い、表に無い場所では使わない。
  | 標準パッケージ・関数 | 使ってよい場所 |
  |---|---|
  | `os`、`io/fs` | `main.go`、`internal/adapter/*`、`tools/*` |
  | `os/signal`、`context.Background` | `main.go`、`tools/*` |
  | `os.Exit`、`os.Args`、`os.Getenv`、`os.Stdout`、`os.Stderr`、`os.Stdin`、`time.Now` | `main.go`、`tools/*` |
  | `path/filepath` | `internal/app`、`internal/adapter/*`、`tools/*` |
  | `flag` | `internal/cli`、`internal/command/*`、`tools/*` |
  | `encoding/json` | `internal/cli`、`internal/adapter/*` |
  | `text/tabwriter` | `internal/cli` |
  | `runtime/debug` | `internal/app` |
  | `testing` | `_test.go`、`internal/app/apptest` |
  | `os/exec`、`net`、`net/http`、`log`、`log/slog`、`math/rand`、`math/rand/v2`、`reflect`、`syscall`、`unsafe`、`io/ioutil`、`sync` | どこでも使わない |
- 理由: I/O・時刻・環境変数に触れる場所が散ると、テストで差し替えられないコードが増え、作者ごとに副作用の置き場が変わる。プロセスに触れるのは `main.go`、ファイルに触れるのは adapter と決めれば、残りは純粋な関数とテストしやすい型になる
- 出典: research.md「Go の公式の設計指針」（context は第1引数）
- 強制: structure, lint — `tools/archcheck` の DEP-05（import の許可表）。関数の呼び出しは golangci-lint の forbidigo（説明が `DEP-05` で始まる）
- probe: DEP-05-a, DEP-05-b
- 良い例:
  ```go
  created := Task{ID: nextID(tasks), Title: trimmed, CreatedAt: s.now().UTC()}
  ```
- 悪い例:
  ```go
  created := Task{ID: nextID(tasks), Title: trimmed, CreatedAt: time.Now()}
  ```

### DEP-06 依存やツールを足すときは ADR を書いて承認を得る

- 軸: B6
- 決定: `go.mod`・`golangci-lint.mod` に変更を加える差分には、同じ差分に `docs/design/adr/` の新しい ADR があり、ユーザーの承認を得たことが ADR に書かれていることを求める。
- 理由: 依存を勝手に足すと、DEP-04 の前提が崩れ、作者ごとに使うライブラリが分かれる
- 強制: review — レビュー用スキルの確認項目（依存の一覧ファイルの差分）
- 機械化しない理由: 承認を得たかどうかは差分の字面からは判定できない。依存の一覧ファイルは保護ファイルなので、エージェントが編集すると hooks が確認を求める
- probe: なし
- 良い例:
  ```text
  go.mod の差分 + docs/design/adr/0007-add-yaml.md（承認：2026-11-01 ユーザー）
  ```
- 悪い例:
  ```text
  go.mod に require を足しただけの差分
  ```

## NAM 命名

### NAM-01 ファイル名とディレクトリ名は小文字と数字だけにする

- 軸: C1
- 決定: `.go` ファイルの名前は `^[a-z0-9]+(_test)?\.go$` に合わせ、ディレクトリ名は小文字と数字だけにし、パッケージ名はディレクトリ名と同じにする。
- 理由: `task_store.go`、`taskStore.go`、`task-store.go` のようにケースが分かれると、ファイルを探す名前が作者ごとに変わる。Go のパッケージ名と同じ規則に寄せれば1通りになる
- 出典: research.md「Go の公式の設計指針」
- 強制: lint, structure — golangci-lint の revive `filename-format` と `package-directory-mismatch`。ディレクトリ名は `tools/archcheck` の NAM-01
- probe: NAM-01-a, NAM-01-b
- 良い例:
  ```text
  internal/adapter/taskstore/taskstore.go
  ```
- 悪い例:
  ```text
  internal/adapter/task_store/task_store.go
  ```

### NAM-02 識別子は MixedCaps にし、略語は全部大文字か全部小文字にする

- 軸: C2, C6
- 決定: 識別子は MixedCaps（公開は大文字始まり、非公開は小文字始まり）にし、略語は `ID`・`JSON`・`URL`・`HTTP` のように全部大文字（先頭が非公開なら `id`・`json`）で書き、定数も同じ規則で書く（`ALL_CAPS` にしない）。
- 理由: `Id` と `ID`、`MAX_LEN` と `maxLen` が混ざると、同じものを指す名前が2つになる
- 出典: research.md「Go の公式の設計指針」（Initialisms）
- 強制: lint — golangci-lint の revive `var-naming`
- probe: NAM-02-a
- 良い例:
  ```go
  func ParseID(s string) (int, error)
  ```
- 悪い例:
  ```go
  func ParseId(s string) (int, error)
  ```

### NAM-03 役割ごとの名前を表のとおりにする

- 軸: C3
- 決定: 次の役割には、表の名前を使う。
  | 役割 | 名前 |
  |---|---|
  | command のパッケージ | `<noun>cmd` |
  | 名詞のグループを返す関数 | `New` |
  | サブコマンドの組み立て・実行・入力・出力 | `new<Verb>`、`run<Verb>`、`<verb>Options`、`<verb>Output`（STR-04） |
  | ビューとビューへの変換 | `<noun>View`、`to<Noun>View` |
  | use case の型と組み立て | `Service`、`NewService` |
  | 保存の interface | `Repository`（メソッドは `Load`・`Save`） |
  | 保存の実装 | パッケージ `<noun>store`、型 `Store`、関数 `New` |
  | 保存形式の型 | ファイル全体が `document`、1件が `record` |
  | 保存形式との変換 | `toRecord`、`to<Noun>` |
  | 文字列から値への変換 | `Parse<項目名>`（`ParseID`、`ParseDue`） |
  | 業務の制約の検証 | `validate<Field>` |
  | エラーの種類 | `Err<Kind>` |
  | `<noun>View` の、一覧の列の文字列を返すメソッド | 列の見出しの lowerCamelCase（`STATUS` → `status`、`DUE` → `due`） |
  | `internal/app/config.go` の環境変数の名前・既定値・読み取り・設定の項目 | `env<Name>`、`default<Name>`、`load<Name>`、`config` のフィールド `<name>`。`<Name>` は環境変数名から `GOCLI_` を除き、`_` で区切った語の先頭だけを大文字にしてつなげたもの（`GOCLI_TITLE_MAX` → `TitleMax`、`titleMax`）。略語の語（`ID`、`URL`、`API`、`HTTP`、`JSON`、`UTC`、`XDG`）は全部大文字のまま |
- 理由: 同じ役割に `NewAddCmd`・`addCommand`・`makeAdd` のような別名が付くと、探す名前と読み方が作者ごとに変わる
- 出典: research.md「Go の公式の設計指針」
- 強制: structure, lint — `tools/archcheck` の NAM-03（view.go・adapter・domain の名前、view.go のメソッドと列の見出し、config.go の名前の対応）。エラーの名前は golangci-lint の errname
- probe: NAM-03-a, NAM-03-b, NAM-03-c, NAM-03-d
- 良い例:
  ```go
  type taskView struct { ... }
  func toTaskView(t task.Task) taskView { ... }
  ```
- 悪い例:
  ```go
  type taskJSON struct { ... }
  func newTaskJSON(t task.Task) taskJSON { ... }
  ```

### NAM-04 サブコマンドと Service のメソッドは同じ動詞にする

- 軸: C4
- 決定: サブコマンド名は対応する Service のメソッド名を小文字にしたものとし、操作ごとの動詞を次の表に固定する。
  | 操作 | サブコマンド | Service のメソッド | 使わない動詞 |
  |---|---|---|---|
  | 1件を作る | `add` | `Add` | `create`、`new` |
  | 1件を見る | `get` | `Get` | `show`、`view`、`describe` |
  | 一覧を見る | `list` | `List` | `ls`、`all` |
  | 項目を変える | `update` | `Update` | `edit`、`set`、`modify` |
  | 1件を消す | `remove` | `Remove` | `delete`、`rm`、`del` |
  | 状態を進める | 状態の変化を表す1語の動詞（`complete`） | 同じ動詞（`Complete`） | `done`、`finish` |
- 理由: 名詞ごとに `create` と `add`、`delete` と `remove` が混ざると、利用者がコマンドを覚えられず、作者ごとに名前が分かれる
- 出典: research.md「Command Line Interface Guidelines」（同じ動詞を使う）
- 強制: structure — `tools/archcheck` の NAM-04（`Name` がファイル名と同じで、使わない動詞でなく、`run<Verb>` が `svc.<Verb>` を呼ぶ）
- probe: NAM-04-a
- 良い例:
  ```go
  Name: "remove", // remove.go、runRemove が svc.Remove を呼ぶ
  ```
- 悪い例:
  ```go
  Name: "delete", // delete.go、runDelete が svc.Remove を呼ぶ
  ```

### NAM-05 名前で型と中身が分かるようにする

- 軸: C5
- 決定: 次の名前の規則を守る。
  | 対象 | 規則 |
  |---|---|
  | bool の構造体フィールドと変数 | `is`・`has` を付けない（`Done`、`all`） |
  | `run<Verb>` で Service の戻り値を受ける変数 | 1件なら動詞の過去分詞（`added`、`completed`、`removed`、`updated`、`get` は `found`）、`List` なら名詞の複数形（`tasks`） |
  | 期間 | `time.Duration` 型にし、名前に単位を付けない |
- 理由: 同じ値に `isDone` と `done`、`t` と `result` と `task` のような別名が付くと、読み手が型を確かめに行く回数が増え、作者ごとに名前が分かれる
- 強制: structure, lint — `tools/archcheck` の NAM-05（bool の名前、`run<Verb>` の変数名）。期間は golangci-lint の revive `time-naming`
- probe: NAM-05-a, NAM-05-b
- 良い例:
  ```go
  completed, err := svc.Complete(ctx, id)
  ```
- 悪い例:
  ```go
  t, err := svc.Complete(ctx, id)
  ```

### NAM-06 CLI の外向きの名前の形と、変換する場所を決める

- 軸: C7
- 決定: 外向きの名前は次の表の形にし、表の場所で Go の名前と対応させる。
  | 外向きの名前 | 形 | 書く場所 |
  |---|---|---|
  | 名詞・動詞 | 小文字の英単語1語 | `cli.Group.Name`、`cli.Command.Name` |
  | フラグ | 小文字の kebab-case で2文字以上、長い名前1つだけ（`--include-done`） | `<verb>.go` の `Flags` |
  | 位置引数の名前 | 小文字の kebab-case | `cli.Arg.Name` |
  | JSON のキー（出力と保存） | フィールド名の snake_case（`CreatedAt` → `created_at`） | 構造体タグ |
  | 環境変数 | `GOCLI_` で始まる大文字の snake_case | `internal/app/config.go` の定数 |
- 理由: `--includeDone`、`--include_done`、`-a` が混ざると利用者が覚えられず、JSON のキーのケースが混ざると機械で読む利用者が壊れる
- 出典: research.md「Command Line Interface Guidelines」（長い名前のフラグ）
- 強制: structure, lint — `tools/archcheck` の NAM-06（名詞・動詞・フラグ・位置引数・環境変数の名前）。JSON のキーは golangci-lint の tagliatelle（`snake`、`use-field-name`）
- probe: NAM-06-a, NAM-06-b
- 良い例:
  ```go
  fs.BoolVar(&opts.all, "all", false, "Include completed tasks")
  CreatedAt time.Time `json:"created_at"`
  ```
- 悪い例:
  ```go
  fs.BoolVar(&opts.all, "a", false, "Include completed tasks")
  CreatedAt time.Time `json:"createdAt"`
  ```

## CODE 書き方

### CODE-01 宣言は関数と型で書き、init とパッケージ変数と名前付きの戻り値を使わない

- 軸: D1
- 決定: `init` 関数、エラーの変数（`err`・`Err` で始まる）以外のパッケージ変数、名前付きの戻り値を使わず、1ファイルの宣言は型 → 定数 → 変数 → 関数の順に並べ、関数とメソッドは公開するものを先に置き、依存を持つ型（`Service`、`Store`）は `New...` がポインタを返し、データの型（エンティティ、ビュー、出力型）は値で渡す。
- 理由: 初期化の書き方と宣言の並びが作者ごとに分かれると、同じ内容のファイルが違う形になる。パッケージ変数と init はテストの間で状態を共有させ、並列のテストを壊す
- 出典: research.md「Go の公式の設計指針」（Named Result Parameters）
- 強制: lint — golangci-lint の gochecknoinits、gochecknoglobals、nonamedreturns、decorder、funcorder、recvcheck
- probe: CODE-01-a, CODE-01-b, CODE-01-c
- 良い例:
  ```go
  func NewService(repo Repository, now func() time.Time) *Service {
  	return &Service{repo: repo, now: now}
  }
  ```
- 悪い例:
  ```go
  var defaultService *Service
  func init() { defaultService = NewService(nil, time.Now) }
  ```

### CODE-02 入力は Options のフィールドに結び、決まった形で Service に渡す

- 軸: D1
- 決定: 入力の受け取りと受け渡しを、次の表の形にする。
  | 入力 | 形 |
  |---|---|
  | フラグ | `Flags` の関数の中で `fs.StringVar`・`fs.BoolVar`・`fs.IntVar` だけを使い、`&opts.<field>` に結ぶ。フィールド名はフラグ名の lowerCamelCase（`--include-done` → `includeDone`） |
  | 位置引数 | `cli.Arg{Name: ..., Value: &opts.<field>}` で結ぶ |
  | 一覧の絞り込みに使うフラグ | domain の `Filter` 型のフィールドにまとめて `List(ctx, filter)` に渡す |
  | それ以外の入力 | Service のメソッドの引数に値のまま渡す。順は `ctx`、対象の ID、位置引数の値、フラグの値（`Add(ctx, title, due)`） |
- 理由: 標準の `flag` は `fs.String`（ポインタを返す）、`fs.Var`、`fs.Func`、`fs.TextVar` など同じことを書く方法が多い。1つに絞ると、入力が必ず `<verb>Options` に集まり、読む場所が1つになる。Service への渡し方を決めないと、引数を足す作者と入力用の構造体を作る作者に分かれる
- 出典: research.md「flag」
- 強制: structure, review — `tools/archcheck` の CODE-02（`fs.` で呼んでよいメソッドの許可表、`&opts.<field>` への結び付け）。Service への渡し方はレビュー用スキル
- probe: CODE-02-a
- 良い例:
  ```go
  Flags: func(fs *flag.FlagSet) {
  	fs.BoolVar(&opts.all, "all", false, "Include completed tasks")
  },
  ```
- 悪い例:
  ```go
  Flags: func(fs *flag.FlagSet) {
  	all = fs.Bool("all", false, "Include completed tasks")
  },
  ```

### CODE-03 import は formatter の群分けに任せ、別名を付けない

- 軸: D2
- 決定: import は1つの `import ( ... )` にまとめて goimports の群分け（標準ライブラリ、モジュール内）に任せ、別名・ドット import・空白 import を使わず、JSON は `encoding/json`（v1 の API）を使う。
- 理由: 別名や並び順が作者ごとに違うと、同じ依存が別の名前で現れ、検索で見つからなくなる
- 出典: research.md「formatter」「Go 1.27.2」
- 強制: format, lint — golangci-lint の goimports（`local-prefixes: example.com/go-cli`）と importas（`no-extra-aliases`）
- probe: CODE-03-a, CODE-03-b
- 良い例:
  ```go
  import (
  	"context"

  	"example.com/go-cli/internal/domain/task"
  )
  ```
- 悪い例:
  ```go
  import (
  	tk "example.com/go-cli/internal/domain/task"
  	"context"
  )
  ```

### CODE-04 型は any・値・UTC の time.Time で書き、append で埋めるスライスは make で作る

- 軸: D3
- 決定: 空インターフェースは `any` と書き、型アサーションは `v, ok := x.(T)` の形だけにし、append で埋めるスライスは `make([]T, 0, <元の長さ>)` で作り、JSON に出すスライスを nil にせず、値の無い任意の項目はポインタにせずゼロ値で表して `json` タグに `,omitzero` を付ける。
- 理由: `interface{}` と `any`、`var s []T` と `[]T{}` と `make` が混ざると、同じ意味のコードが違う形になる。JSON の出力では nil のスライスが `null` になり、利用者の期待（空配列）と食い違う
- 出典: research.md「Go の公式の設計指針」（Declaring Empty Slices）
- 強制: lint — golangci-lint の revive `use-any`、modernize、forcetypeassert、prealloc
- probe: CODE-04-a
- 良い例:
  ```go
  views := make([]taskView, 0, len(tasks))
  ```
- 悪い例:
  ```go
  var views []taskView // 0件のとき JSON が "tasks": null になる
  ```

### CODE-05 エラーは別の行で受け、早期 return で書き、入れ子を3段までにする

- 軸: D4
- 決定: エラーは `err := f()` の次の行の `if err != nil` で確かめ、条件が合わない場合を先に return し、`return` の後に `else` を書かず、制御構造の入れ子を3段までにする。
- 理由: `if err := f(); err != nil` と2行の形、`else` の有無が混ざると、同じ処理が違う形になる
- 強制: lint — golangci-lint の noinlineerr、revive `early-return`・`indent-error-flow`・`superfluous-else`・`max-control-nesting`（3）、nestif
- probe: CODE-05-a
- 良い例:
  ```go
  err := validateTitle(trimmed)
  if err != nil {
  	return Task{}, err
  }
  ```
- 悪い例:
  ```go
  if err := validateTitle(trimmed); err != nil {
  	return Task{}, err
  }
  ```

### CODE-06 引数と値のレシーバを書き換えない

- 軸: D5
- 決定: 関数の引数と値レシーバに代入せず、新しい変数に入れ、パッケージ変数に代入しない。
- 理由: 引数を書き換えると、呼び出し元から見た値と関数の中の値が食い違い、読み手が追う変数が増える
- 強制: lint — golangci-lint の revive `modifies-parameter`・`modifies-value-receiver`、reassign
- probe: CODE-06-a
- 良い例:
  ```go
  trimmed := strings.TrimSpace(title)
  ```
- 悪い例:
  ```go
  title = strings.TrimSpace(title)
  ```

### CODE-07 関数の大きさを上限で縛る

- 軸: D6
- 決定: テスト以外の関数は50行・30文以内、認知的複雑度15以下、引数4個以下、戻り値2個以下にする。
- 理由: 長い関数は作者ごとに分割の仕方が変わり、レビューで読み切れなくなる。上限を機械で決めれば、分ける時期が全員同じになる
- 強制: lint — golangci-lint の funlen（50行・30文）、gocognit（15）、revive `argument-limit`（4）・`function-result-limit`（2）
- probe: CODE-07-a
- 良い例:
  ```go
  func runAdd(ctx context.Context, svc *task.Service, opts addOptions) (addOutput, error)
  ```
- 悪い例:
  ```go
  func runAdd(ctx context.Context, svc *task.Service, title, due, tag string, all bool) (addOutput, error)
  ```

### CODE-08 コメントは日本語の1文1行で、全部の宣言に説明を書き、パッケージの説明は1ファイルに書く

- 軸: D7
- 決定: すべてのパッケージは `<パッケージ名>.go`（`package main` は `main.go`）だけに `Package <name> ...`（`main` は `Command go-cli ...`）で始まる説明を書き、`internal/` と `main.go` のトップレベルの宣言には公開・非公開を問わずその名前で始まる説明を書き（括弧でまとめた `const`・`var` は群の説明だけでもよい）、コメントは `//` で書いて1行に日本語の1文だけを置き（文の途中で改行せず、1行に2つの文を書かない）、各行を句点（`。`）で終え、`TODO`・`FIXME`・`BUG`・`HACK`・`XXX` を書かない。
- 理由: パッケージの説明の置き場、説明を書く宣言、コメントの言語と折り返し、TODO の扱いが作者ごとに分かれると、同じ変更でもコメントの差分が作者ごとに変わり、`go doc` も読めなくなる。日本語にそろえるのは、利用者が規約とコメントを同じ言語で理解できるようにするためである（ADR 0006）。識別子と `Package`・`Command` の接頭辞は Go の説明の形式に合わせて残す。1文1行にするのは、どこで折り返すかという作者ごとに分かれる選択を無くすためである
- 出典: research.md「Go の公式の設計指針」（Package Comments、Doc Comments）
- 強制: lint, structure — golangci-lint の godoclint（`require-pkg-doc`、非公開も対象にした `require-doc`、`single-pkg-doc`、`start-with-name`）、revive `exported`・`package-comments`、godox。説明を書くファイル、日本語の有無、句点、1文1行は `tools/archcheck` の CODE-08
- probe: CODE-08-a, CODE-08-b, CODE-08-c, CODE-08-d, CODE-08-e, CODE-08-f
- 良い例:
  ```go
  // Complete は指定した ID のタスクを完了にする。
  // 完了済みのタスクを指定しても状態は変わらない。
  func (s *Service) Complete(ctx context.Context, id int) (Task, error) {
  ```
- 悪い例:
  ```go
  // Complete は指定した ID のタスクを
  // 完了にする（TODO: 報告する）。
  func (s *Service) Complete(ctx context.Context, id int) (Task, error) {
  ```

### CODE-09 0と1以外の数値は名前の付いた定数にする

- 軸: D8
- 決定: テスト以外のコードでは、0と1以外の数値リテラルを、それを使うファイルの先頭の `const` に名前を付けて置く。
- 理由: 同じ上限値やファイルの権限が複数の場所に直接書かれると、変えるときに漏れが出て、作者ごとに書き方も分かれる
- 強制: lint — golangci-lint の mnd
- probe: CODE-09-a
- 良い例:
  ```go
  const maxTitleLength = 100
  ```
- 悪い例:
  ```go
  if n > 100 {
  ```

### CODE-10 役割の決まった宣言の説明は表の文にする

- 軸: D7
- 決定: 次の表の宣言には、表の文をそのまま説明に書き（`<noun>`・`<Noun>`・`<verb>`・`<Verb>`・`<Field>`・`<method>`・`<COLUMN>`・`<Name>`・`<GOCLI_NAME>` は実際の名前に置き換える）、表に無い宣言の説明は CODE-08 の形で書く。
  | 宣言 | 説明の文 |
  |---|---|
  | `<verb>Options` | `<verb>Options は <noun> <verb> の引数とフラグを保持する。` |
  | `<verb>Output` | `<verb>Output は <noun> <verb> の実行結果を表す。` |
  | `new<Verb>` | `new<Verb> は <noun> <verb> コマンドを返す。` |
  | `run<Verb>` | `run<Verb> は <noun> <verb> を実行する。` |
  | `<verb>Output` の `WriteText` | `WriteText は cli.Output を実装する。` |
  | `<noun>cmd` の `New` | `New は svc でユースケースを実行する <noun> コマンド群を返す。` |
  | `<noun>View` | `<noun>View は <noun> コマンドの出力で1件の <noun> を表す。` |
  | `to<Noun>View` | `to<Noun>View は <Noun> を <noun>View に変換する。` |
  | `<noun>View` の列のメソッド | `<method> は <COLUMN> 列に表示する文字列を返す。`（`<COLUMN>` は `<method>` の大文字の snake_case） |
  | `Parse<Field>` | 必須の項目は `Parse<Field> はコマンドライン引数を <Noun> の <Field> フィールドに変換する。` の1行。任意の項目は、その次の行に `空文字列の場合はゼロ値を返す。` を足した2行 |
  | `validate<Field>` | `validate<Field> は <Noun> の <Field> フィールドを検証する。` |
  | `Service` | `Service は <noun> のユースケースを実行する。` |
  | `Service` の `Get` | `Get は指定した ID の <noun> を返す。` |
  | `Service` の `Remove` | `Remove は指定した ID の <noun> を削除し、その内容を返す。` |
  | `Filter` | `Filter は List が返す <noun> を絞り込む。` |
  | `Repository` | `Repository は全 <noun> を一括で読み書きする。` |
  | `indexOf` | `indexOf は <noun>s 内で指定した ID の <noun> の位置を返す。` |
  | `nextID` | `nextID は <noun>s 内の最大 ID に1を足した新しい <noun> の ID を返す。` |
  | `document` | `document はデータファイルの内容を表す。` |
  | `record` | `record はデータファイルに保存する1件の <noun> を表す。` |
  | `toRecord` | `toRecord は <Noun> を record に変換する。` |
  | adapter の `to<Noun>` | `to<Noun> は record を <Noun> に変換する。` |
  | `config.go` の `default<Name>` | `default<Name> は $<GOCLI_NAME> が空のときに使う値を表す。` |
  | `config.go` の `load<Name>`（`default<Name>` があるとき） | `load<Name> は $<GOCLI_NAME> の値を返し、空なら default<Name> を返す。` |
- 理由: 同じ役割の宣言に作者ごとに違う説明が付くと、同じ変更の差分が作者ごとに変わり、説明から役割を読み取れなくなる。役割で決まる説明は文まで決めておけば、作者が言い回しを考える必要が無い
- 強制: structure — `tools/archcheck` の CODE-10。違反の行に、書くべき文がそのまま出る
- probe: CODE-10-a, CODE-10-b
- 良い例:
  ```go
  // ParseDue はコマンドライン引数を Task の Due フィールドに変換する。
  // 空文字列の場合はゼロ値を返す。
  func ParseDue(s string) (time.Time, error) {
  ```
- 悪い例:
  ```go
  // ParseDue はコマンドライン引数を UTC の午前0時の日付に変換する。
  func ParseDue(s string) (time.Time, error) {
  ```

## ERR エラーと入力検証

### ERR-01 エラーの種類は errkind を %w で先頭に包んで表す

- 軸: E1
- 決定: エラーは `error` の値で返し（`panic` を使わない）、終了コードを決める種類は次の決定表で選び、種類を付けるときは `fmt.Errorf("%w: <詳細>", errkind.Err<Kind>)` と `%w` を書式の先頭に置く。
  | 状況 | 返すエラー | 終了コード |
  |---|---|---|
  | 入力が規則に反する（引数の数、フラグ、値の形式、業務の制約、環境変数の値） | `fmt.Errorf("%w: <詳細>", errkind.ErrInvalid)` | 2 |
  | 指定されたものが無い | `fmt.Errorf("%w: <noun> %d", errkind.ErrNotFound, id)` | 3 |
  | 上のどれでもない（I/O の失敗、壊れたデータ） | 種類を付けず ERR-02 で包んだエラー | 1 |
- 理由: エラーの種類の表し方（独自の型、sentinel、文字列の比較）と書式が作者ごとに分かれると、終了コードがずれ、利用者のスクリプトが壊れる。種類を errkind の2つに絞り、`%w` を先頭に置くと、メッセージの最初の語で種類が分かる
- 出典: research.md「Go の公式の設計指針」（Placement of %w in errors）
- 強制: structure, lint — `tools/archcheck` の ERR-01（errkind を包む `fmt.Errorf` の書式が `%w: ` で始まる）。golangci-lint の err113、errorlint、errname、forbidigo（`panic`。説明が `ERR-01` で始まる）
- probe: ERR-01-a, ERR-01-b
- 良い例:
  ```go
  return 0, fmt.Errorf("%w: task %d", errkind.ErrNotFound, id)
  ```
- 悪い例:
  ```go
  return 0, fmt.Errorf("task %d: %w", id, errkind.ErrNotFound)
  return 0, errors.New("task not found")
  ```

### ERR-02 外から来たエラーは1回だけ包み、モジュール内のエラーはそのまま返す

- 軸: E1
- 決定: 標準ライブラリから返ったエラーは `fmt.Errorf("<動詞> <目的語>: %w", err)` で包んで返し、モジュール内のパッケージから返ったエラーと、`fmt.Fprint*`・`io.WriteString` の書き込みのエラーは包まずに返す。
- 理由: 包むかどうかが作者ごとに違うと、`save tasks: save tasks: open ...` のように同じ文脈が重なるか、どこで失敗したかが分からなくなる。外との境界で1回だけ包めば、メッセージの形が1通りになる
- 出典: research.md「Go の公式の設計指針」（Placement of %w in errors）
- 強制: lint — golangci-lint の wrapcheck（`ignore-package-globs: example.com/go-cli/*`）
- probe: ERR-02-a
- 良い例:
  ```go
  data, err := os.ReadFile(s.path)
  if err != nil {
  	return nil, fmt.Errorf("load tasks: %w", err)
  }
  ```
- 悪い例:
  ```go
  data, err := os.ReadFile(s.path)
  if err != nil {
  	return nil, err
  }
  ```

### ERR-03 エラーの文字列は小文字で始め、句読点で終えない

- 軸: E1
- 決定: エラーの文字列は小文字で始め（固有名詞・略語・環境変数名で始まる場合を除く）、句読点で終えず、改行を含めない。
- 理由: エラーは `go-cli: load tasks: open ...` のように前の文脈に続けて表示される。大文字や句点が混ざると、つないだ文が読みにくくなり、作者ごとに書き方も分かれる
- 出典: research.md「Go の公式の設計指針」（Error Strings）
- 強制: lint — golangci-lint の revive `error-strings`、staticcheck ST1005
- probe: ERR-03-a
- 良い例:
  ```go
  fmt.Errorf("%w: title must be 1 to %d characters", errkind.ErrInvalid, maxTitleLength)
  ```
- 悪い例:
  ```go
  fmt.Errorf("%w: Title is too long.", errkind.ErrInvalid)
  ```

### ERR-04 入力は決定表の場所で変換・検証する

- 軸: E2
- 決定: 入力の変換と検証は、次の決定表の場所で行う。
  | 確かめること | 場所 |
  |---|---|
  | 未知のコマンド・フラグ、位置引数の数、フラグの値の型（`IntVar` の数値） | `internal/cli`（自動。コマンドは書かない） |
  | 文字列から業務の値への変換（ID、日付、列挙） | `run<Verb>` の先頭で、domain の `Parse<X>` を呼ぶ |
  | 業務の制約（タイトルの長さ、重複） | domain の Service のメソッドの先頭で、`validate<Field>` を呼ぶ |
  | 環境変数の値 | `internal/app/config.go` の `loadConfig` |
  | 上のどれでもない | domain の Service のメソッド |
  `strconv.Atoi`・`strconv.Parse*`・`time.Parse*` は `internal/domain/*` と `internal/app` でだけ呼ぶ。
- 理由: 検証を command で書く作者と domain で書く作者に分かれると、同じ制約が2か所に書かれるか、どこにも書かれない。場所を決めると、変換と検証のコードを探す場所が1つになる
- 強制: lint, review — golangci-lint の forbidigo（`strconv`・`time.Parse` の呼び出し。説明が `ERR-04` で始まる）。どの層で検証したかはレビュー用スキルで確かめる
- probe: ERR-04-a
- 良い例:
  ```go
  id, err := task.ParseID(opts.id) // run<Verb> の先頭
  ```
- 悪い例:
  ```go
  id, err := strconv.Atoi(opts.id) // command で直接変換する
  ```

## STATE 状態とデータの流れ

### STATE-01 状態は決定表の置き場だけに持つ

- 軸: E3
- 決定: 状態は、次の決定表の置き場だけに持つ。
  | 状態 | 置き場 |
  |---|---|
  | 業務データ | データディレクトリの `<名詞の複数形>.json`（`tasks.json`）。中身は `{"version": 1, "<名詞の複数形>": [...]}`。読み書きは adapter の Store だけが行う。項目を足すときは `version` を変えず、古いファイルに無い項目はゼロ値で読む |
  | データディレクトリ | `$GOCLI_DATA_DIR`、`$XDG_DATA_HOME/go-cli`、`$HOME/.local/share/go-cli` のうち最初に値があるもの |
  | 1回の実行の入力 | `<verb>Options`（フラグと位置引数） |
  | 設定 | 環境変数を `internal/app/config.go` の `config` に読む（OPS-02） |
  | 上のどれでもない | 持たない（パッケージ変数、キャッシュ、設定ファイルを作らない） |
- 理由: 状態の置き場が開いていると、設定ファイルを足す作者、パッケージ変数にキャッシュする作者、別の場所にファイルを書く作者が出て、実行のたびに結果が変わる
- 出典: research.md「Command Line Interface Guidelines」（XDG に従う）
- 強制: review — レビュー用スキルの確認項目。パッケージ変数は CODE-01、ファイル操作の場所は DEP-05 が機械で止める
- 機械化しない理由: 保存するファイル名と JSON の形が名詞の意味に合っているかは、字面では判定できない
- probe: なし
- 良い例:
  ```go
  notes := note.NewService(notestore.New(filepath.Join(cfg.dataDir, "notes.json")), env.Now)
  ```
- 悪い例:
  ```go
  notes := note.NewService(notestore.New(filepath.Join(cfg.dataDir, "note-data.json")), env.Now)
  ```

## ASYNC 非同期と並行

### ASYNC-01 並行処理を書かず、context は第1引数で受け取る

- 軸: E4
- 決定: `go` 文・チャネル・`sync` を使わず、I/O をする関数と Service・Repository のすべてのメソッドは `ctx context.Context` を第1引数に取り、adapter のメソッドは最初に `ctx.Err()` を確かめ、取り消しは `main.go` の `signal.NotifyContext` から渡す。
- 理由: CLI の1回の実行は順に処理すれば足りる。並行処理を許すと、同期の書き方が作者ごとに分かれ、テストが不安定になる。context の位置を固定すると、取り消しが全層に同じ形で届く
- 出典: research.md「Go の公式の設計指針」（Contexts）、「Go 1.27.2」（signal.NotifyContext）
- 強制: structure, lint — `tools/archcheck` の ASYNC-01（`go` 文とチャネル型）。golangci-lint の revive `context-as-argument`、containedctx、contextcheck。`sync` の import は DEP-05
- probe: ASYNC-01-a, ASYNC-01-b
- 良い例:
  ```go
  func (s *Store) Load(ctx context.Context) ([]task.Task, error) {
  	err := ctx.Err()
  ```
- 悪い例:
  ```go
  go func() { _ = s.repo.Save(ctx, tasks) }()
  ```

## OPS ログ・設定・セキュリティ・表示

### OPS-01 ログを書かず、出力は cli だけが書く

- 軸: E5
- 決定: ログ（`log`、`log/slog`）と `fmt.Print*`・`print`・`println` を使わず、標準出力にはサブコマンドの出力型だけを、標準エラーにはエラーと使い方の案内だけを、`internal/cli` が書く。
- 理由: 各コマンドが自由に表示すると、出力先（stdout と stderr）と形式が作者ごとに分かれ、`--json` の出力に余計な行が混ざってパイプが壊れる
- 出典: research.md「Command Line Interface Guidelines」（stdout と stderr）
- 強制: lint — golangci-lint の forbidigo（説明が `OPS-01` で始まる）。`log` の import は DEP-05
- probe: OPS-01-a
- 良い例:
  ```go
  return addOutput{Task: toTaskView(added)}, nil
  ```
- 悪い例:
  ```go
  fmt.Println("added", added.ID)
  ```

### OPS-02 設定は GOCLI_ の環境変数を config.go で読む

- 軸: E6
- 決定: 設定は `GOCLI_` で始まる環境変数だけから読み、名前は `internal/app/config.go` の `// CLI の設定に使う環境変数を定義する。` の const の群に `env<Name>` として個別の説明を付けずに置き（`GOCLI_` の定数は `config` のフィールドの順に、`XDG_DATA_HOME`・`HOME` の定数より前に並べる）、既定値はその群の直後に `default<Name>` の const で置き、値の読み取り・既定値・検証は設定ごとの `load<Name>(getenv)` で行い、`loadConfig` は `config` のフィールドの順に `load<Name>` を1つずつ呼んでから `config{...}` を返し、値は `config` のフィールドを通して `app.New` から各層の組み立て関数の引数で渡し、文字列リテラルの中の `GOCLI_` は `config.go`・`apptest.go`・`_test.go`・`tools/` の外に書かない。
- 理由: 環境変数を読む場所と読み方が散ると、テストで差し替えられず、同じ設定に別の名前や別の書き方が生まれる。読む場所を1つにし、設定ごとに同じ形の関数にすれば、設定の一覧がそのファイルで分かり、足すときの変更も同じ形になる
- 出典: research.md「Command Line Interface Guidelines」（Configuration）
- 強制: structure, lint — `tools/archcheck` の OPS-02（文字列リテラルの中の `GOCLI_` の場所、`loadConfig` が呼ぶ `load<Name>` の順）と NAM-03（定数・関数・フィールドの名前と群の置き場）。`os.Getenv` は golangci-lint の forbidigo（説明が `DEP-05` で始まる）
- probe: OPS-02-a, OPS-02-b, OPS-02-c
- 良い例:
  ```go
  func loadConfig(getenv func(key string) string) (config, error) {
  	dataDir, err := loadDataDir(getenv)
  	if err != nil {
  		return config{}, err
  	}
  	return config{dataDir: dataDir}, nil
  }
  ```
- 悪い例:
  ```go
  // internal/domain/task/service.go
  limit := os.Getenv("GOCLI_TITLE_MAX")
  ```

### OPS-03 時刻は UTC の秒単位で持ち、コメントを除くコードと表示の文字列は ASCII にする

- 軸: E7
- 決定: 時刻は Service が `s.now().UTC().Truncate(time.Second)` で作って UTC の秒単位で保存し、JSON には `time.Time` のまま（RFC 3339）出し、文章の出力で日付を出すときは `time.DateOnly`（`2006-01-02`）で書き、`.go` ファイルのコメントを除くコードには ASCII の文字だけを書く（コメントは CODE-08 に従う）。`tools/` は日本語コメントの定型文を処理するため、コード内の文字列にも日本語を使える。
- 理由: タイムゾーンと精度が作者ごとに違うと、同じ時刻が別の文字列になり、テストの期待値も揺れる。コードと表示の文字列を ASCII にそろえるのは、検索と比較を安定させるためである。コメントは利用者が読む説明なので日本語にする（CODE-08、ADR 0006）
- 強制: structure, test — `tools/archcheck` の OPS-03（コメントを除くコードの ASCII 以外の文字）。時刻の形はサブコマンドのテスト（`--json` の期待値）
- probe: OPS-03-a, OPS-03-b
- 良い例:
  ```go
  CreatedAt: s.now().UTC().Truncate(time.Second),
  ```
- 悪い例:
  ```go
  CreatedAt: s.now(), // 地方時のまま、ナノ秒まで保存される
  ```

### OPS-04 データのディレクトリは 0700、ファイルは 0600 で作る

- 軸: E8
- 決定: データディレクトリは `os.MkdirAll(dir, 0o700)` で作り、データファイルは同じディレクトリに `os.CreateTemp` で書いてから `os.Rename` で置き換え（権限は 0600）、それより広い権限でファイルを作らない。
- 理由: 権限と書き込み方が作者ごとに違うと、他のユーザーに読めるファイルや、途中で止まったときに壊れたファイルが生まれる
- 強制: lint — golangci-lint の gosec（G301、G302、G306）
- probe: OPS-04-a
- 良い例:
  見本: `internal/adapter/taskstore/taskstore.go` の `writeFileAtomic`
- 悪い例:
  ```go
  return os.WriteFile(s.path, data, 0o644)
  ```

### OPS-05 終了コードと出力先は cli が決め、コマンドは出力型と error を返す

- 軸: X1
- 決定: サブコマンドの `Run` は `(cli.Output, error)` を返すだけとし、終了コード（0：成功、1：想定外の失敗、2：入力の誤り、3：見つからない）と出力先（出力型は stdout、エラーは stderr）は `internal/cli` が決め、すべてのサブコマンドの `--json`・`--help` は `internal/cli` が付け、フラグは位置引数の前後どちらにも書けるようにする。
- 理由: 終了コードや出力先をコマンドごとに書くと、同じ失敗が別の終了コードになり、`--json` を付け忘れるコマンドが出る。型で縛れば、コマンドを書く作者が選ぶ余地が無くなる
- 出典: research.md「Command Line Interface Guidelines」（終了コード、`--json`、順序に依存しない）、「flag」
- 強制: type — `cli.Command.Run` の型が `func(ctx context.Context) (cli.Output, error)` で、コマンドは書き込み先と終了コードを受け取らない
- probe: OPS-05-a
- 良い例:
  ```go
  Run: func(ctx context.Context) (cli.Output, error) {
  	return runAdd(ctx, svc, opts)
  },
  ```
- 悪い例:
  ```go
  Run: func(ctx context.Context) int {
  	fmt.Fprintln(os.Stderr, "not found"); return 3
  },
  ```

### OPS-06 出力の形とヘルプの文言を決まった形にする

- 軸: X1
- 決定: 出力型とヘルプの文言を、次の表の形にする。
  | 出力 | 形 |
  |---|---|
  | JSON の最上位 | オブジェクト。1件は `{"<noun>": {...}}`、一覧は `{"<名詞の複数形>": [...]}` |
  | 1件を変える動詞の文章 | `<過去分詞の大文字始まり> <noun> <id>: <title>` の1行（`Added task 1: Buy milk`） |
  | 一覧の文章 | `cli.WriteTable` の表。列はエンティティの項目の順（`CreatedAt` を除く）、ただし `Done` は `STATUS`（`open`・`done`）として `ID` の次に、`TITLE` は最後に置く。見出しは項目名の大文字の snake_case（`DUE`）、0件なら見出しだけ |
  | 1件を見る動詞（`get`）の文章 | 一覧と同じ列の `cli.WriteTable` の表を1行で出す |
  | 文章の中の値の無い任意の項目 | `-` |
  | `Summary` とフラグの説明 | 大文字で始まり、ピリオドで終えない英語の1文 |
- 理由: 出力の形がコマンドごとに違うと、利用者が `jq` やスクリプトで扱うときに名詞ごとに書き分ける必要が生まれる
- 出典: research.md「Command Line Interface Guidelines」（Output）
- 強制: test, structure, review — 各サブコマンドのテストが stdout の全文を比べる。`Summary` とフラグの説明の形は `tools/archcheck` の OPS-06。JSON のキーの選び方はレビュー用スキル
- probe: OPS-06-a, OPS-06-b
- 良い例:
  ```go
  _, err := fmt.Fprintf(w, "Completed task %d: %s\n", o.Task.ID, o.Task.Title)
  ```
- 悪い例:
  ```go
  _, err := fmt.Fprintf(w, "task #%d was marked as done.\n", o.Task.ID)
  ```

## TEST テスト

### TEST-01 対象ごとのテストの粒度と、必須のテストを決める

- 軸: F1, F5
- 決定: 次の決定表のとおりにテストを書き、カバレッジの閾値は設けない。
  | 対象 | テストの方法 | テストファイル |
  |---|---|---|
  | サブコマンド | `apptest` で CLI を実行し、`Result`（終了コード、stdout、stderr）の全体を比べる。成功の文章、`--json`、終了コード2と3のうちそのコマンドが返しうるものごとに1件以上 | `<verb>_test.go` の `Test<Verb>`（必須） |
  | domain の `Parse<X>` と `validate<Field>` を通る入力 | `Parse<X>` は直接呼び、`validate<Field>` はサブコマンドのテストで通す | `<noun>_test.go`（必須） |
  | adapter | `t.TempDir()` に実際のファイルを置き、`Load`・`Save` を呼ぶ | `<noun>store_test.go`（必須） |
  | cli | テスト用の `cli.App` を組んで `Run` を呼ぶ | `cli_test.go` |
  | app（設定の解決） | `apptest` か `app.Run` | `app_test.go` |
  | 上のどれでもない（Service のメソッド、ビュー、出力型） | 直接はテストせず、サブコマンドのテストで通す | — |
- 理由: 何をどの粒度でテストするかが作者ごとに違うと、同じ変更でテストの量と置き場がばらつく。CLI の契約は「入力に対する出力と終了コード」なので、それを全体で比べるテストを必須にする
- 強制: structure, review — `tools/archcheck` の TEST-01（必須のテストファイルと `Test<Verb>` があること）。終了コードごとの件があるかはレビュー用スキル
- probe: TEST-01-a
- 良い例:
  見本: `internal/command/taskcmd/complete_test.go`
- 悪い例:
  ```text
  remove.go を足し、remove_test.go を作らない
  ```

### TEST-02 テストは並列のテーブル駆動で、got を先に書く

- 軸: F2
- 決定: テストは外部テストパッケージ（`package <name>_test`）に書き、`t.Parallel()` を最上位とサブテストの両方で呼び、`tests := []struct{ name string; ... }` と `for _, tt := range tests { t.Run(tt.name, ...) }` の形にし、サブテストの名前は小文字の snake_case（`empty_title`）にし、比べるときは `!=`・`slices.Equal`・`errors.Is` を使い（`time.Time` どうしは `!got.Equal(tt.want)`）、失敗の文は `<関数>(<引数>) = <got>, want <want>` にする。
- 理由: テストの形が作者ごとに違うと、ケースを足す場所と失敗の読み方が変わる。テーブル駆動にそろえると、ケースの追加が1行の追加になる
- 出典: research.md「Go の公式の設計指針」（Identify the function、Got before want、Subtest names）
- 強制: lint, structure — golangci-lint の testpackage、paralleltest、tparallel、thelper、usetesting、revive `time-equal`。サブテストの名前は `tools/archcheck` の TEST-02
- probe: TEST-02-a, TEST-02-b, TEST-02-c
- 良い例:
  ```go
  if got != tt.want {
  	t.Errorf("Run(%q) = %+v, want %+v", tt.args, got, tt.want)
  }
  ```
- 悪い例:
  ```go
  if got != tt.want {
  	t.Errorf("expected %v but got %v", tt.want, got)
  }
  ```

### TEST-03 テストのために偽物の型を作らない

- 軸: F3
- 決定: テストファイルで型を宣言せず（テーブルの無名の構造体だけを使い）、Repository の偽物やモックを作らず、サブコマンドのテストは `apptest`（一時ディレクトリの本物の Store と固定の時計）で行う。
- 理由: 偽物の作り方（手書きの fake、関数フィールド、モック）は作者ごとに大きく分かれ、偽物と本物の振る舞いもずれる。本物の Store を一時ディレクトリで使えば、偽物を作る判断そのものが要らない
- 強制: structure — `tools/archcheck` の TEST-03（`_test.go` の型宣言）
- probe: TEST-03-a
- 良い例:
  ```go
  h := apptest.New(t)
  got := h.Run(tt.args...)
  ```
- 悪い例:
  ```go
  type fakeRepo struct{ tasks []task.Task }
  ```

### TEST-04 テストデータはテーブルに直接書き、前提は CLI の実行で作る

- 軸: F4
- 決定: 期待する出力はテーブルの文字列リテラル（複数行は raw string）に直接書き、サブコマンドのテストの前提データは `setup [][]string` に並べた CLI の実行（`h.Setup`）で作り、環境変数はテーブルの `env map[string]string` に書いて `h.Setenv` で設定し、adapter のテストの前提データは `os.WriteFile` で `t.TempDir()` に JSON を書いて作る。
- 理由: 前提データの作り方（ファイルを直接書く、Service を呼ぶ、CLI を実行する）が作者ごとに違うと、テストが内部の形に依存し、保存形式を変えるたびにテストが壊れる
- 強制: review — レビュー用スキルの確認項目
- 機械化しない理由: 前提データを CLI の実行で作るべきか、ファイルで作るべきかは、テストの対象（サブコマンドか adapter か）の意味で決まる。golden ファイルの禁止は STR-06 が機械で止める
- probe: なし
- 良い例:
  ```go
  setup: [][]string{{"task", "add", "Buy milk"}},
  ```
- 悪い例:
  ```go
  os.WriteFile(filepath.Join(dir, "tasks.json"), []byte(`{"tasks":[...]}`), 0o600) // サブコマンドのテストで
  ```

### TEST-05 足す件、件の名前、件の並び、テストの値を表のとおりにする

- 軸: F2, F4
- 決定: 変更の種類ごとに次の「足す件」の表の件だけを足し（表に無い件を足さず、既存の件は出力が変わった期待値だけを直す）、件の名前と値は表のとおりにし、テーブルの件は「成功の文章 → `--json` → 終了コード1 → 2 → 3」（domain のテストは `accepts_` → `returns_` → `rejects_`）の順に並べ、足す件は同じ種類の件の最後に置き、`args` は位置引数、フラグ（`Flags` で定義した順）、`--json` の順に書く。
  足す件（`<name>` は環境変数名から `GOCLI_` を除いた小文字の snake_case、`<flag>`・`<field>` はフラグ名・項目名の小文字の snake_case）:
  | 変更 | ファイル | 件の名前 | setup | args | 期待 |
  |---|---|---|---|---|---|
  | ID で1件を対象にする動詞を足す | `<verb>_test.go` | `<verb>s_a_<noun>` | 1件目を add | `<noun> <verb> 1` | 成功の文章 |
  | 同上 | 同上 | `writes_json` | 1件目を add | `<noun> <verb> 1 --json` | JSON |
  | 同上 | 同上 | `rejects_an_id_that_is_not_a_number` | なし | `<noun> <verb> one` | 終了コード2 |
  | 同上 | 同上 | `reports_a_missing_<noun>` | 1件目を add | `<noun> <verb> 2` | 終了コード3 |
  | 既存の動詞に任意のフラグを足す（項目を足して add で指定する場合も、この行に当たる） | `<verb>_test.go` | `<verb>s_a_<noun>_with_<flag>`（list は `lists_<noun>s_with_<flag>`） | なし（list は `lists_<noun>s` と同じ） | 1件目の値に `--<flag> <値>` を足す | 成功の文章 |
  | 同上 | 同上 | `writes_json_with_<flag>` | 同上 | 上の args に `--json` を足す | JSON |
  | 同上（値を `Parse<Field>` で変換するフラグ） | 同上 | `rejects_an_invalid_<flag>` | なし | 1件目の値に `--<flag> <不正な値>` を足す | 終了コード2 |
  | 項目を足し、一覧に列を足す | `list_test.go` | `lists_<noun>s_with_<field>` | 1件目を項目つきで add、2件目を項目なしで add | `<noun> list` | 表 |
  | 同上 | 同上 | `writes_json_with_<field>` | 1件目を項目つきで add | `<noun> list --json` | JSON |
  | 項目を足す | `<noun>store_test.go` | 件は足さない。`TestLoad`・`TestSave` の既存の1件目に項目の値を足す | — | — | — |
  | `Parse<Field>` を足す | `<noun>_test.go` | 下の「値の種類ごとの件」の表 | — | — | — |
  | 正の整数の環境変数を足す | `app_test.go` | `rejects_a_<name>_that_is_not_a_number`（値 `one`）、`rejects_a_<name>_of_zero`（値 `0`） | なし | `<noun> list` | 終了コード2 |
  | 文字数の上限を環境変数で変える | 上限が効くサブコマンドの `<verb>_test.go` | `accepts_a_<field>_up_to_the_<name>`（値は1件目の値の文字数）、`rejects_a_<field>_longer_than_the_<name>`（値はその文字数より1小さい数） | なし | `<noun> add <1件目の値>` | 成功の文章、終了コード2 |
  値の種類ごとの件（`TestParse<Field>`）:
  | 値の種類 | 件の名前（`s` の値） |
  |---|---|
  | 正の整数 | `accepts_a_positive_integer`（`12`）、`rejects_zero`（`0`）、`rejects_a_negative_integer`（`-1`）、`rejects_a_word`（`one`）、`rejects_an_empty_string`（`""`） |
  | 日付 | `accepts_a_date`（`2026-01-31`）、`rejects_another_format`（`2026/01/31`）、`rejects_a_date_that_does_not_exist`（`2026-02-30`）、`rejects_an_empty_string`（`""`） |
  | 任意の項目 | 上の行の `rejects_an_empty_string` の代わりに、`returns_zero_for_an_empty_string`（`""`）を `accepts_` の件の次に置く |
  | 上のどれでもない | 受け付ける値の `accepts_<値の説明>`、空文字列の件、拒む値の `rejects_<値の説明>` を1件ずつ |
  テストの値:
  | 値 | 使う値 |
  |---|---|
  | 名詞の最初の文字列の項目（`title`、`text`） | 1件目は `Buy milk`、2件目は `Write report` |
  | 日付 | `2026-01-31`。Go では `time.Date(2026, time.January, 31, 0, 0, 0, 0, time.UTC)`、JSON では `"2026-01-31T00:00:00Z"` |
  | 形の違う日付 | `2026/01/31` |
  | 数でない値 | `one` |
  | 存在しない ID | `2`（setup で1件だけ作る） |
  | 存在しない名詞・動詞 | 名詞は `unknown`、動詞は `delete`（NAM-04 で使わない動詞） |
- 理由: 足す件・件の名前・値・並びが作者ごとに違うと、同じ変更でもテストの差分が作者ごとに変わり、どの件が何を確かめているかも名前から読めなくなる。変更の種類ごとに件を決めておけば、作者は件を考える必要が無い
- 強制: structure, review — 件の並びは `tools/archcheck` の TEST-05。足す件、件の名前、値、同じ種類の中での置き場、`args` の順はレビュー用スキル
- 機械化しない理由: 足すべき件とその名前は、差分が「動詞を足した」「項目を足した」のどれに当たるかで決まり、差分の意味を読まないと判定できない
- probe: TEST-05-a, TEST-05-b
- 良い例:
  ```go
  {
  	name: "adds_a_task_with_due",
  	args: []string{"task", "add", "Buy milk", "--due", "2026-01-31"},
  	want: apptest.Result{Code: 0, Stdout: "Added task 1: Buy milk\n"},
  },
  ```
- 悪い例:
  ```go
  {
  	name: "adds_a_task_with_a_due_date",
  	args: []string{"task", "add", "--due", "2026-11-01", "Buy milk"},
  	want: apptest.Result{Code: 0, Stdout: "Added task 1: Buy milk\n"},
  },
  ```

## PROC 作業手順

### PROC-01 内側の層から外側の層へ順に作る

- 軸: G1
- 決定: 作る順序は、domain（エンティティ、`Parse<X>`、`validate<Field>`、`<noun>_test.go`）→ domain の Service のメソッド → adapter（保存する項目が変わる場合）→ `view.go` → `<verb>.go` → `<verb>_test.go` → `<noun>cmd.go` の登録 → `app.go`（名詞を足す場合）→ `make generate` → `make check` とする。
- 理由: 外側から作ると、まだ無い domain の関数を仮の形で呼び、作者ごとに途中の形が変わる。内側から作れば、各段階でコンパイルとテストが通る
- 強制: doc — 実装用スキルの「作る順序」
- 機械化しない理由: 作った順序は最終の差分に残らない
- probe: なし
- 良い例:
  ```text
  1. service.go に Remove を足す  2. remove.go  3. remove_test.go  4. taskcmd.go に登録
  ```
- 悪い例:
  ```text
  remove.go から書き始め、コンパイルが通らないまま service.go を後で合わせる
  ```

### PROC-02 一緒に変えるファイルの組を守る

- 軸: G2
- 決定: 次の表の左を変えるときは、右のファイルを同じ差分で変え、エンティティ・`record`・`<noun>View` の項目は `ID` で始めて `CreatedAt` で終え、足す項目は `CreatedAt` の直前に置く。
  | 変えるもの | 一緒に変えるもの |
  |---|---|
  | エンティティの項目 | adapter の `record` と `toRecord`・`to<Noun>`、`view.go` の `<noun>View` と `to<Noun>View`、関係するサブコマンドのテスト |
  | 名詞・動詞・フラグ・`Summary`・終了コード | `docs/cli.md`（`make generate`） |
  | エラーの種類 | `internal/errkind/errkind.go`、`internal/cli/exit.go` の `exitCode` と `ExitCodes`、`docs/cli.md` |
  | 名詞の追加 | `internal/app/app.go` の組み立てと `Groups` |
  | 環境変数の追加 | `internal/app/config.go`、`README.md` の環境変数の表 |
- 理由: 片側だけを変えると、保存や出力から項目が黙って落ちるか、文書と実装が食い違う
- 強制: structure, review — `tools/archcheck` の PROC-02（エンティティ・`record`・`<noun>View` のフィールド名が同じ順で一致し、`ID` で始まり `CreatedAt` で終わること、各名詞の `New` が `app.go` から呼ばれること）。`docs/cli.md` は STR-07。エラーの種類と環境変数はレビュー用スキル
- probe: PROC-02-a, PROC-02-b
- 良い例:
  ```go
  type Task struct{ ID int; Title string; Done bool; Due time.Time; CreatedAt time.Time }
  type record struct{ ID int; Title string; Done bool; Due time.Time; CreatedAt time.Time }
  ```
- 悪い例:
  ```go
  type Task struct{ ID int; Title string; Done bool; Due time.Time; CreatedAt time.Time }
  type record struct{ ID int; Title string; Done bool; CreatedAt time.Time } // Due を保存し忘れる
  ```

### PROC-03 Go と golangci-lint の版は決まった手順で上げる

- 軸: G3
- 決定: 版を上げるときは、`go.mod` の `go` と `toolchain` の行、`golangci-lint.mod` の `go` の行と `go get -tool -modfile=golangci-lint.mod github.com/golangci/golangci-lint/v2/cmd/golangci-lint@<版>`、`tools/archcheck` の TOOL-04 の期待値、`docs/design/research.md`、`.foundation/manifest.json` を同じ差分で変え、`make check` と `violation_probe.py` を通す。
- 理由: 版を一部だけ上げると、手元と検査で使う版が食い違い、作者ごとに違う整形や指摘が出る
- 強制: doc — 実装用スキルの「依頼から外れる作業」と AGENTS.md
- 機械化しない理由: 上げる時期と理由は依頼で決まり、コードからは判定できない。上げた後の版の一致は TOOL-04 が機械で確かめる
- probe: なし
- 良い例:
  ```text
  go.mod・golangci-lint.mod・archcheck・research.md・manifest を1つの差分で更新
  ```
- 悪い例:
  ```text
  go.mod の toolchain だけを上げる
  ```

### PROC-04 ルールは ADR から順に変える

- 軸: G4
- 決定: ルールを変えるときは、ADR → `docs/design/rules.md` → 検査の設定・`tools/archcheck`・`.foundation/probes.json` → 参照実装 → `rules_check.py`・`violation_probe.py` の順に変え、ユーザーの承認を得てから始める。
- 理由: 設定だけを緩めると、ルールの文書と検査が食い違い、次の作者がどちらに従うかで分かれる
- 強制: doc — AGENTS.md の「ルールを変えたいとき」
- 機械化しない理由: 変えた順序と承認の有無は差分に残らない。保護ファイルの編集は hooks が確認を求める
- probe: なし
- 良い例:
  ```text
  adr/0007-allow-durations.md → rules.md の CODE-02 → archcheck → probes.json → 見本
  ```
- 悪い例:
  ```text
  .golangci.yml の funlen を 80 に上げて check を通す
  ```

### PROC-05 make check とチェックリストを満たしてから完了と報告する

- 軸: G5
- 決定: 完了と報告してよいのは、`make check` が通り、実装用スキルの完了前チェックリストを満たし、報告に依頼から決まらなかった値とその根拠を書いた場合だけとする。
- 理由: 完了の基準が作者ごとに違うと、検査を回していない変更や、黙って決めた値が残る
- 強制: doc — AGENTS.md の「完了の条件」と実装用スキル
- 機械化しない理由: 報告の中身とチェックリストの確認は差分に残らない
- probe: なし
- 良い例:
  ```text
  報告：make check の末尾「ok」、決めた値：タイトルの上限は既定の100文字
  ```
- 悪い例:
  ```text
  報告：実装しました（check を回していない）
  ```

### PROC-06 CLI の公開面は足すだけにし、変える・消すときは ADR を書く

- 軸: X2
- 決定: 公開面（サブコマンド名、フラグ名とその意味、位置引数、JSON のキー、終了コード、環境変数名）は追加だけを許し、名前の変更・削除・意味の変更をする差分には、ユーザーの承認を書いた ADR を同じ差分に含める。
- 理由: 公開面は利用者のスクリプトが依存する契約である。作者ごとに名前を整理し直すと、利用者のスクリプトが黙って壊れる
- 出典: research.md「Command Line Interface Guidelines」
- 強制: review — レビュー用スキルの確認項目（`docs/cli.md` の削除行と、`json` タグ・`config.go` の定数の変更）
- 機械化しない理由: 意味の変更（同じ名前で振る舞いを変える）は字面では判定できない。名前の追加と削除は `docs/cli.md` の差分に必ず現れるので、レビューで確かめる
- probe: なし
- 良い例:
  ```text
  task list に --status を足す（--all は残す）
  ```
- 悪い例:
  ```text
  task list の --all を --include-done に名前を変える
  ```

## TOOL 道具と自動化

### TOOL-01 整形は formatter に任せる

- 軸: H1
- 決定: Go のコードの整形は golangci-lint の formatter（gofumpt の `extra` すべて、goimports、golines の120文字）に任せ、`make fix` か編集後の hooks で整形し、Go 以外のファイルは `.editorconfig` に従う。
- 理由: 空白・改行・import の並びを人が決めると、同じコードが作者ごとに違う形になる
- 出典: research.md「formatter」
- 強制: format — golangci-lint の gofumpt・goimports・golines（`make lint` が整形の違反を報告する）
- probe: TOOL-01-a
- 良い例:
  ```sh
  make fix
  ```
- 悪い例:
  ```go
  func main() {

  	app.Run( ctx, args )
  ```

### TOOL-02 編集後は hooks、完了前は make check を回す

- 軸: H2
- 決定: 編集の直後は hooks が編集したファイルの整形とそのパッケージの lint を回し、完了の前は作者が `make check` を回し、CI とコミット前の検査は置かない。
- 理由: いつ何を回すかが作者ごとに違うと、検査を通らないまま完了と報告される
- 強制: doc — AGENTS.md と実装用スキル。hooks は `.claude/settings.json` と manifest の `hooks.post_edit`
- 機械化しない理由: いつ検査を回したかは差分に残らない
- probe: なし
- 良い例:
  ```text
  remove.go を保存 → hooks の lint の指摘を直す → 最後に make check
  ```
- 悪い例:
  ```text
  make check を回さずに完了と報告する
  ```

### TOOL-03 抑止コメントと保護ファイルの変更で検査を黙らせない

- 軸: H3
- 決定: `//nolint`、`//lint:ignore`、`#nosec`、`t.Skip`、`//go:build` を書かず、保護ファイル（`.foundation/manifest.json` の `protected`）を変更しない。
- 理由: 抑止や設定の緩和で検査を通せると、ルールが無いのと同じになり、作者ごとに例外が増える
- 強制: structure, review — `guard.py`（manifest の `guard.suppressions`）。保護ファイルの変更はレビュー用スキル
- probe: TOOL-03-a, TOOL-03-b
- 良い例:
  ```go
  err := ctx.Err() // 指摘はコードを直して消す
  ```
- 悪い例:
  ```go
  func longFunction() { //nolint:funlen
  ```

### TOOL-04 Go と golangci-lint の版を固定し、Makefile を唯一の入口にする

- 軸: H4
- 決定: `go.mod` は `go 1.27` と `toolchain go1.27.2`、golangci-lint は `golangci-lint.mod` の `tool` と v2.15.0 で固定し、`go mod tidy -diff` が `go.mod` と `golangci-lint.mod` の両方で通る状態を保ち、検査と生成は `make` のターゲットからだけ起動する。
- 理由: 版と起動の方法が作者ごとに違うと、同じコードでも整形と指摘が変わる
- 出典: research.md「golangci-lint」（専用の modfile）、「Go 1.27.2」（`go mod tidy -diff`）
- 強制: structure — `tools/archcheck` の TOOL-04（`go.mod` と `golangci-lint.mod` の版の行）と `make tidy-check`
- probe: TOOL-04-a
- 良い例:
  ```text
  toolchain go1.27.2
  ```
- 悪い例:
  ```text
  toolchain go1.26.9
  ```

## 対象外とした軸

揺れない軸、またはこの分野に無い軸と、その理由を書く。

| 軸 | 理由 |
|---|---|
