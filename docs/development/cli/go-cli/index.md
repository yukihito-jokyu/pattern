---
title: GoのCLI実装パターン
description: 標準ライブラリflagで作るCLIの実装基盤。タスク管理の見本から入力解析・業務処理・保存・出力と拡張時の検査を学ぶ。
slug: /development/cli/go-cli
pattern:
  features:
    - label: コマンド
      value: 名詞・動詞の2階層と共通のJSON出力
    - label: 実装
      value: Go標準ライブラリ・JSONファイル保存
    - label: 拡張
      value: 参照実装・開発スキル・構造検査を同梱
---

# GoのCLI実装パターン

CLIは、端末から引数を渡して操作するプログラムです。コマンドが増えると、引数の解析、業務処理、保存、表示をどこへ書くかが作者ごとに分かれやすくなります。このパターンは、その置き場所と追加方法を決めたGoの実装基盤です。タスク管理の`task add`・`task list`・`task complete`を動く見本として同梱しています。

ZIPには実行コード、テスト、設計資料、実装・レビュースキル、構造検査が入っています。見本を動かし、入力から出力までの実ファイルを追い、その形を写して自分のコマンドを追加できます。CLIはGoの標準ライブラリだけで動き、開発時のgolangci-lintは別の依存定義に分離します。

## 最初に動かす

macOSまたはLinuxに、Go 1.21以降、GNU Make 3.81以降、Python 3.12以降を用意します。ZIPを展開した`go-cli/`に入り、次を実行してください。以後、特記しないコマンドの実行場所もこの展開先です。

```sh
go mod download
go mod download -modfile=golangci-lint.mod
make check
go build -o go-cli .
export GOCLI_DATA_DIR="$(mktemp -d)"
./go-cli task add "Buy milk"
./go-cli task list
./go-cli task complete 1
./go-cli task list --json
./go-cli task list --all --json
```

準備で失敗したら後続を実行せず、原因を解消します。Goの選択設定は後述します。初回のツールチェーンと検査用モジュールの取得にはネットワークが必要です。

追加は`Added task 1: Buy milk`を出力し、一覧には次の表が出ます。

```text
ID  STATUS  TITLE
1   open    Buy milk
```

完了すると`Completed task 1: Buy milk`を出力します。既定の一覧からは完了済みが消えるため、その後のJSONは`{"tasks": []}`です。`--all`を付けると、`done: true`になった1件も返ります。コマンドごとに`mktemp`を実行すると別の保存先になるため、この例では一度設定した`GOCLI_DATA_DIR`を続けて使います。

## 全体像：実行の順序と依存の向き

配布する主要ファイルは次のとおりです。テストは対象の隣に置きます。

```text
go-cli/
├── main.go                         引数・出力先・時計をappへ渡す
├── internal/
│   ├── app/                        設定と組み立て。apptest/はテストの実行環境
│   ├── cli/                        フラグ解析・ヘルプ・表示・終了コード
│   ├── command/taskcmd/            add.go・complete.go・list.go・view.go
│   ├── domain/task/                Task・Service・Repository
│   ├── adapter/taskstore/          JSONファイルによるRepositoryの実装
│   └── errkind/                    入力誤り・対象なしのエラー
├── tools/                          構造検査とコマンド文書生成
├── .claude/                        実装・レビュースキルと編集hooks
├── .foundation/                    ルール検証・違反例・既存の評価記録
├── docs/                           コマンド一覧・構造・ルール・採用理由
├── scripts/verify-ci.py             配布物の動作・代表的違反の検証
├── ci.json                         掲載元の共通CIから呼ぶ入口
└── Makefile                        開発時の検査・生成の入口
```

実行時は`main → app → cli → command → domainのService → adapterのStore`と進み、結果が戻るとcliが表示します。一方、Goのimportは`command → domain ← adapter`です。domainは自分が定義したRepositoryのinterfaceを介して保存を呼ぶため、adapterをimportする必要はありません。実行順とimportの向きを分けることで、保存方式を変えても業務処理を保てます。

Goのコマンドと補助パッケージをルートのmainとinternalに置く構成に沿っています。`internal/`は外部モジュールからのimportを制限するため、このZIPを共通ライブラリとして取り込むのではなく、新しいCLIプロジェクトの土台として使います。[Go公式のモジュール構成](https://go.dev/doc/modules/layout)

## 1. appで保存先・業務処理・コマンドを組む

`internal/app/app.go`のEnvとNewの一部です。

```go
type Env struct {
    Stdout io.Writer
    Stderr io.Writer
    Getenv func(key string) string
    Now    func() time.Time
}

func New(env Env) (*cli.App, error) {
    cfg, err := loadConfig(env.Getenv)
    if err != nil {
        return nil, err
    }
    tasks := task.NewService(taskstore.New(filepath.Join(cfg.dataDir, "tasks.json")), env.Now)
    return &cli.App{
        Name:    name,
        Version: version(),
        Groups: []*cli.Group{
            taskcmd.New(tasks),
        },
    }, nil
}
```

main.goは実際の`os.Stdout`・`os.Stderr`・`os.Getenv`・`time.Now`をEnvに入れます。appは設定から保存先を決め、StoreをServiceへ、Serviceをコマンドへ渡します。Serviceが具体的な保存ファイルや環境変数を知らなくても動くのは、この組み立てをappで済ませるためです。

テストでは同じEnvに一時保存先と固定時計を渡せます。`internal/app/apptest/`が準備と出力の取得を担当し、各コマンドのテストは本物のStoreを通します。偽物のRepositoryをコマンドごとに作る方法は採用していません。

## 2. コマンドは入力を宣言し、結果とerrorを返す

`internal/command/taskcmd/add.go`では入力・出力・コマンドの作成・実行・文章表示を同じファイルにまとめます。次は入力から実行までの部分です。

```go
type addOptions struct {
    title string
}

type addOutput struct {
    Task taskView `json:"task"`
}

func newAdd(svc *task.Service) *cli.Command {
    var opts addOptions
    return &cli.Command{
        Name:    "add",
        Summary: "Add a task",
        Args:    []cli.Arg{{Name: "title", Value: &opts.title}},
        Run: func(ctx context.Context) (cli.Output, error) {
            return runAdd(ctx, svc, opts)
        },
    }
}

func runAdd(ctx context.Context, svc *task.Service, opts addOptions) (addOutput, error) {
    added, err := svc.Add(ctx, opts.title)
    if err != nil {
        return addOutput{}, err
    }
    return addOutput{Task: toTaskView(added)}, nil
}
```

Argsは必須の位置引数を順番に並べます。cliが引数の数を確認してopts.titleに値を入れてからRunを呼ぶため、runAddはServiceへ渡す処理に集中できます。結果をtaskViewへ変換するのは、業務のTaskと公開JSONの形を分けるためです。taskViewでは`id`・`title`・`done`・`created_at`を定義します。

JSONの最上位は`{"task": ...}`、一覧なら`{"tasks": [...]}`です。コマンドは直接標準出力やos.Exitを呼びません。`cli.Command.Run`の戻り値が`(Output, error)`なので、表示と終了コードの決定を枠組みに集約できます。

### フラグと位置引数を一緒に受け取る

`internal/command/taskcmd/list.go`のnewListです。Flagsでコマンド固有のフラグを登録します。

```go
func newList(svc *task.Service) *cli.Command {
    var opts listOptions
    return &cli.Command{
        Name:    "list",
        Summary: "List open tasks",
        Flags: func(fs *flag.FlagSet) {
            fs.BoolVar(&opts.all, "all", false, "Include completed tasks")
        },
        Run: func(ctx context.Context) (cli.Output, error) {
            return runList(ctx, svc, opts)
        },
    }
}
```

listOptionsのallはboolです。`--all`の既定値はfalseで、未指定時は未完了タスクだけを返します。runListはこの値を`task.Filter{IncludeDone: opts.all}`に変換してServiceへ渡します。CLIのフラグ名を業務処理が直接読む形にはしません。

共通の`--json`は`internal/cli/cli.go`のnewFlagSetでfalseを既定値として登録します。エラーを返して呼び出し元へ判断を戻すため、FlagSetは`flag.ContinueOnError`で作り、自動エラー表示は`io.Discard`へ送ります。その後CLI自身が一度だけ標準エラーへ書きます。

標準のflagは最初の位置引数または`--`で解析を止めます。この実装のparseは位置引数を一つずつ取り除いて解析を再開するため、`task add --json "Buy milk"`と`task add "Buy milk" --json`の両方が使えます。`--`で止まった場合は再開せず、後ろをすべて位置引数として扱います。共通フラグは動詞より後へ書いてください。[flagの仕様（Go 1.27.2）](https://pkg.go.dev/flag@go1.27.2#hdr-Command_line_flag_syntax)

## 3. domainで入力の意味と業務の手順を決める

`internal/domain/task/service.go`の追加処理です。

```go
func (s *Service) Add(ctx context.Context, title string) (Task, error) {
    trimmed := strings.TrimSpace(title)
    err := validateTitle(trimmed)
    if err != nil {
        return Task{}, err
    }
    tasks, err := s.repo.Load(ctx)
    if err != nil {
        return Task{}, err
    }
    created := Task{ID: nextID(tasks), Title: trimmed, CreatedAt: s.now().UTC().Truncate(time.Second)}
    err = s.repo.Save(ctx, append(tasks, created))
    if err != nil {
        return Task{}, err
    }
    return created, nil
}
```

`"  Buy milk  "`は前後の空白を除いて`"Buy milk"`として保存します。validateTitleはtask.goの`maxTitleLength = 100`を使い、rune数で1〜100文字に制限します。空白だけのタイトルや101文字のタイトルは保存前に入力誤りになります。

新しいIDは既存IDの最大値+1で、保存がなければ1です。作成時刻は渡された時計から得てUTCの秒単位にそろえ、保存・出力・テストを同じ精度にします。タイトルの検証とID・時刻の決定は、CLIの解析から切り離した業務処理です。

completeはtask.goのParseIDで文字列を正の整数へ変換してから、ServiceのCompleteを呼びます。変換はdomainのParse関数、業務上の制約はServiceから呼ぶvalidate関数、という分担です。CompleteはDoneをtrueにし、完了済みをもう一度指定してもtrueを保ちます。Listは完了済みを既定で除外し、IncludeDoneがtrueなら含めます。

## 4. RepositoryをJSON保存で実装する

`internal/domain/task/repository.go`は、Serviceが保存先に要求する操作だけを定義します。

```go
type Repository interface {
    Load(ctx context.Context) ([]Task, error)
    Save(ctx context.Context, tasks []Task) error
}
```

これを実装する`internal/adapter/taskstore/taskstore.go`の保存形式と設定値です。

```go
type document struct {
    Version int      `json:"version"`
    Tasks   []record `json:"tasks"`
}

type record struct {
    ID        int       `json:"id"`
    Title     string    `json:"title"`
    Done      bool      `json:"done"`
    CreatedAt time.Time `json:"created_at"`
}

const (
    formatVersion = 1
    dirPerm       = 0o700
)
```

Loadはファイルがなければ空の一覧を返し、JSONが壊れていればエラーを返します。recordをTaskへ変換するため、保存形式の変更をadapter内に閉じられます。Saveは全Taskをrecordに変換し、`version: 1`と一緒に保存します。

writeFileAtomicは親ディレクトリを0700で作り、同じディレクトリの`.tmp-*`へJSONを書いてからos.Renameでtasks.jsonに置き換えます。一時ファイルはos.CreateTempで0600になります。途中の書き込みに失敗したら一時ファイルを消し、元のファイルは置き換えません。[os.CreateTempの仕様](https://pkg.go.dev/os@go1.27.2#CreateTemp)

これは複数プロセスの更新競合を防ぐロックではありません。どちらも同じ内容を読み、後から保存した側が先の変更を上書きする場合があります。fsync、読み込み時の版の照合、外部で編集されたレコードの業務検証も実装していません。個人用・逐次実行のJSON保存を土台とし、並行更新や大容量データを扱う場合は保存契約を検討してください。

## 5. 表示と終了コードをcliへ戻す

`internal/command/taskcmd/add.go`の文章表示です。

```go
func (o addOutput) WriteText(w io.Writer) error {
    _, err := fmt.Fprintf(w, "Added task %d: %s\n", o.Task.ID, o.Task.Title)
    return err
}
```

`--json`がなければcliがWriteTextを呼び、指定があれば同じaddOutputをJSONに変換します。文章とJSONで別の業務処理を実行することはありません。JSONは2スペースで整形し、空の一覧はnullでなく配列にします。一覧の文章はcli.WriteTableを通し、最小幅0・タブ幅8・余白2・空白埋めで列をそろえます。

`internal/cli/exit.go`がerrors.Isでエラーの種類を判別します。

| 終了コード | 判断 | 例 |
| --- | --- | --- |
| 0 | 成功 | 追加・一覧・完了・ヘルプ |
| 1 | ほかのエラー | 壊れたJSON、読み書き失敗、出力先への書き込み失敗 |
| 2 | errkind.ErrInvalidを含む | タイトル不正、IDの変換失敗、未知のフラグ、引数不足 |
| 3 | errkind.ErrNotFoundを含む | 存在しないIDの完了 |

成功した結果は標準出力、失敗の理由は`go-cli: <理由>`の形で標準エラーへ出します。入力誤りには対象コマンドの--helpも案内します。文章・JSONをパイプで使う場合に、エラーが結果へ混ざるのを避けるためです。実際の終了コードを確認するときは、go runを経由せずビルド済みのバイナリを実行してください。

## 保存先とツールの版を決める設定

### 保存先はconfig.goだけで読む

`internal/app/config.go`のloadDataDirは、`GOCLI_DATA_DIR`、`XDG_DATA_HOME`、`HOME`をこの順で調べます。対応する定数はenvDataDir、envXDGData、envHomeです。

| 条件 | 保存ディレクトリ |
| --- | --- |
| GOCLI_DATA_DIRが空でない | 指定したパスそのもの |
| 上記が空でXDG_DATA_HOMEがある | `$XDG_DATA_HOME/go-cli` |
| 上記2つが空でHOMEがある | `$HOME/.local/share/go-cli` |
| すべて空 | 組み立て時に失敗し、終了コード1 |

相対パスは実行時の作業ディレクトリから解釈されます。既定値は個人のデータディレクトリを使うため、例や検証では一時保存先を指定します。設定を読む場所をappに集めることで、コマンドごとに解釈が変わるのを避けています。Windowsの保存先への分岐はありません。

### CLIと検査ツールの依存を分ける

`go.mod`です。

```go
module example.com/go-cli

go 1.27

toolchain go1.27.2
```

go行は必要なGoの最低版、toolchainはメインモジュールを扱う際の推奨ツールチェーンです。自動選択が有効なら手元のGoで不足する版を取得できます。`GOTOOLCHAIN=local`で無効化している場合はGo 1.27.2以上を用意してください。すでに新しいGoを使っている場合まで1.27.2へ下げる指定ではありません。[Goのツールチェーン選択](https://go.dev/doc/toolchain)

golangci-lint v2.15.0はgolangci-lint.modのtoolとrequire、およびgolangci-lint.sumで固定し、Makefileから`go tool -modfile=golangci-lint.mod golangci-lint`として実行します。CLIのgo.modにrequireは追加しません。版の更新はAGENTS.mdとdocs/design/rules.mdのPROC-03に従い、調査・規則・設定・違反例の結果をそろえて行います。

## 自分のコマンドを追加する

ZIPを新しいプロジェクトのルートに配置し、AGENTS.mdと`.claude/skills/impl/SKILL.md`を読みます。変更ごとの詳細は同スキルのreferences/patterns.mdにあり、taskを写す見本に使います。

| 変更 | 主な変更箇所と理由 |
| --- | --- |
| task removeなど動詞を追加 | Serviceへ業務処理、commandへremove.goとテスト、taskcmd.goへ登録。保存契約が同じならStoreは変更しない |
| task list --limitなどフラグを追加 | OptionsとFlagsに入力を追加し、絞り込みをdomainのFilterとServiceへ渡す。ヘルプと文書は同じ定義から生成 |
| 期限などの項目を追加 | Task、保存record、出力taskViewと変換を同じ順に更新。入力・保存・表示のどこかだけに追加しない |
| noteなど名詞を追加 | domain・adapter・commandを一式追加し、appでStore → Service → コマンドを組む。既存名詞の業務規則を直接importしない |

作成順はdomain → Service → adapter → view → 動詞 → テスト → 登録です。最後にmake generateでdocs/cli.mdを更新し、make checkを通します。この一覧は変更手順であり、removeやlimitがすでに実装済みという意味ではありません。

動詞ファイルはOptions、Output、new関数、run関数、WriteTextの順にそろえます。次の作者が入力・出力・処理・表示の場所を予測できるためです。登録はアルファベット順にし、名詞の追加でヘルプが変わったら期待値も更新します。

モジュール名はexample.com/go-cli、コマンド名はgo-cliのまま配布します。利用先の名前へ変更する場合は、go.modとimportだけでなく、.golangci.ymlのmodule-path・local-prefixes・ignore-package-globs、tools/archcheckのモジュール名もそろえます。保護対象なので、docs/design/adr/0005-defaults-not-in-the-request.mdとAGENTS.mdのルール変更手順に沿って扱います。

## 書き方をそろえる検査と開発スキル

`Makefile`のcheckは次のターゲットを順に呼びます。

```make
check: tidy-check lint build vet arch docs-check test guard rules
```

| 段階 | 確認すること |
| --- | --- |
| tidy-check | アプリとlint用のmodfileをgo mod tidy -diffで確認し、必要な更新の未反映を防ぐ |
| lint | .golangci.ymlで整形・命名・エラー処理などを確認 |
| build / vet / test | コンパイル、静的検査、CLIと保存のテスト |
| arch | tools/archcheckで配置、依存方向、宣言の順序、型・変換の対応を検査 |
| docs-check | コマンド定義から作るdocs/cli.mdが最新か確認 |
| guard | 禁止した抑止コメント・テストのskipなどを検出 |
| rules | 57件の規則、検査の対応、違反例定義と既存結果の整合を確認 |

途中で失敗したら後続を止めます。整形とlintの自動修正、コマンド文書の再生成にはmake fixを使えますが、その後もmake checkが必要です。検査を通すために保護ファイルを緩めたり、抑止コメントを追加したりしません。

### lint設定の値と適用範囲

.golangci.ymlは、この基盤が書き方をそろえるために選んだ規約です。すべてのGoプログラムへの一般的な推奨ではありません。ZIP内のdocs/design/rules.mdとenforcement-matrix.mdには規則と検査の対応があります。設定形式は[golangci-lint公式資料](https://golangci-lint.run/docs/configuration/file/)も参照できます。

<details>
<summary>.golangci.ymlの全設定と、値を選んだ理由</summary>

以下は配布ファイルの内容です。続く表で、検査の対象と制限値の意味を説明します。

```yaml
version: "2"

run:
  timeout: 5m
  tests: true

formatters:
  enable:
    - gofumpt
    - goimports
    - golines
  settings:
    gofumpt:
      module-path: example.com/go-cli
      extra:
        group-params: true
        clothe-returns: true
        balance-calls: true
    goimports:
      local-prefixes:
        - example.com/go-cli
    golines:
      max-len: 120
      reformat-tags: false
      shorten-comments: false
  exclusions:
    generated: strict

linters:
  default: standard
  enable:
    - asciicheck
    - bidichk
    - containedctx
    - contextcheck
    - decorder
    - dogsled
    - durationcheck
    - err113
    - errchkjson
    - errname
    - errorlint
    - exhaustive
    - fatcontext
    - forbidigo
    - forcetypeassert
    - funcorder
    - funlen
    - gocheckcompilerdirectives
    - gochecknoglobals
    - gochecknoinits
    - gocognit
    - gocritic
    - godoclint
    - godox
    - gomoddirectives
    - gomodguard_v2
    - goprintffuncname
    - gosec
    - iface
    - importas
    - inamedparam
    - interfacebloat
    - intrange
    - iotamixing
    - ireturn
    - makezero
    - mirror
    - misspell
    - mnd
    - modernize
    - musttag
    - nestif
    - nilerr
    - nilnesserr
    - nilnil
    - noctx
    - noinlineerr
    - nonamedreturns
    - paralleltest
    - perfsprint
    - prealloc
    - predeclared
    - reassign
    - recvcheck
    - revive
    - tagliatelle
    - testpackage
    - thelper
    - tparallel
    - unconvert
    - unparam
    - usestdlibvars
    - usetesting
    - wastedassign
    - wrapcheck
  settings:
    errcheck:
      check-type-assertions: true
      check-blank: true
    decorder:
      dec-order: [type, const, var, func]
      disable-dec-order-check: false
      disable-init-func-first-check: false
      disable-dec-num-check: true
    forbidigo:
      analyze-types: true
      forbid:
        - pattern: ^(fmt\.Print(|f|ln)|print|println)$
          msg: OPS-01 return a cli.Output instead of printing
        - pattern: ^log\.
          msg: OPS-01 return a cli.Output or an error instead of logging
        - pattern: ^panic$
          msg: ERR-01 return an error instead of panicking
        - pattern: ^time\.Now$
          msg: DEP-05 receive the clock as a func() time.Time
        - pattern: ^context\.(Background|TODO)$
          msg: DEP-05 receive the context as the first parameter
        - pattern: ^os\.(Exit|Getenv|LookupEnv|Environ|Args|Stdin|Stdout|Stderr)$
          msg: DEP-05 only main.go touches the process; receive it through app.Env
        - pattern: ^strconv\.(Atoi|Parse.*)$
          msg: ERR-04 convert strings in a Parse function of the domain package
        - pattern: ^time\.Parse.*$
          msg: ERR-04 convert strings in a Parse function of the domain package
    funcorder:
      constructor: true
      struct-method: true
      function: true
    funlen:
      lines: 50
      statements: 30
      ignore-comments: true
    gocognit:
      min-complexity: 15
    godoclint:
      default: basic
      enable:
        - require-pkg-doc
        - require-doc
        - no-unused-link
      options:
        require-doc:
          ignore-exported: false
          ignore-unexported: false
    godox:
      keywords: [TODO, FIXME, BUG, HACK, XXX]
    gomodguard_v2:
      allowed: []
      local-replace-directives: true
    gosec:
      excludes: []
    importas:
      no-extra-aliases: true
    nestif:
      min-complexity: 4
    revive:
      # modifies-parameter の信頼度は0.5なので、既定の0.8では検出されない。
      confidence: 0.5
      enable-default-rules: true
      rules:
        - name: argument-limit
          arguments: [4]
        - name: function-result-limit
          arguments: [2]
        - name: deep-exit
        - name: early-return
        - name: enforce-map-style
          arguments: [make]
        - name: enforce-repeated-arg-type-style
          arguments: [short]
        - name: filename-format
          arguments: ["^[a-z0-9]+(_test)?\\.go$"]
        - name: max-control-nesting
          arguments: [3]
        - name: modifies-parameter
        - name: modifies-value-receiver
        - name: package-directory-mismatch
        - name: redundant-import-alias
        - name: unused-receiver
        - name: use-any
        - name: use-errors-new
        - name: time-equal
    tagliatelle:
      case:
        use-field-name: true
        rules:
          json: snake
    wrapcheck:
      extra-ignore-sigs:
        - io.WriteString(
        - fmt.Fprintf(
        - fmt.Fprintln(
        - fmt.Fprint(
      ignore-package-globs:
        - example.com/go-cli/*
  exclusions:
    generated: strict
    warn-unused: false
    rules:
      - path: ^main\.go$
        linters: [forbidigo]
        text: DEP-05
      - path: ^tools/
        linters: [forbidigo]
      # CODE-08: tools/ は保護対象で、CLI の作者は宣言を追加しない。
      - path: ^tools/
        linters: [godoclint]
        text: symbol should have a godoc
      - path: ^internal/(domain|app)/
        linters: [forbidigo]
        text: ERR-04
      - path: _test\.go$
        linters: [funlen, godoclint, gosec]

issues:
  max-issues-per-linter: 0
  max-same-issues: 0
  uniq-by-line: false
```

#### 有効にする検査

`linters.default: standard`でerrcheck・govet・ineffassign・staticcheck・unusedを使い、enableで検査を追加します。errcheckは未処理のerror、govetは誤用、ineffassignは無効な代入を検出します。残りと追加した65項目の役割は次のとおりです。各制約の根拠は同梱のルール集に対応付けています。

| 検査名 | 対象と採用理由 |
| --- | --- |
| `asciicheck`・`bidichk`・`misspell` | 非ASCII識別子、双方向制御文字、英語の誤綴りを検出し、識別子や文書の読み違いを減らす。 |
| `containedctx`・`contextcheck`・`noctx` | contextを構造体に保存すること、伝播を切ること、contextなしの呼び出しを検出する。 |
| `decorder`・`funcorder`・`godoclint`・`godox` | 宣言順、関数順、説明コメント、`TODO`などの保留記述を検査し、見本と同じ並び・説明を保つ。 |
| `dogsled`・`nonamedreturns` | 不要な捨て変数や名前付き戻り値など、結果を追いにくくする書き方を抑える。 |
| `durationcheck` | 時間の値同士の不適切な演算を検出する。 |
| `err113`・`errchkjson`・`errname`・`errorlint`・`nilerr`・`nilnil`・`wrapcheck` | エラーの作り方・命名・比較・ラップと、JSONやnilの返し方を検査し、原因を追える失敗にする。 |
| `exhaustive`・`forcetypeassert` | 列挙値の分岐漏れと失敗時を処理しない型アサーションを検出する。 |
| `fatcontext`・`gocognit`・`funlen`・`nestif` | contextの無駄な再生成、認知複雑度、関数の長さ、深い分岐を検出し、動詞の処理を追える大きさに保つ。 |
| `forbidigo`・`gocheckcompilerdirectives`・`gochecknoglobals`・`gochecknoinits` | 直接出力・プロセス操作などの禁止呼び出し、コンパイラ指示、グローバル変数、initを検査し、実行環境を受け渡す構造を守る。 |
| `gocritic`・`staticcheck`・`nilnesserr` | 不自然な式や制御、nilに関する誤りなどの静的な不具合を検出する。 |
| `gomoddirectives`・`gomodguard_v2` | モジュール宣言や依存制約を確認し、依存追加・置換の規約違反を検出する。 |
| `goprintffuncname`・`gosec`・`musttag` | Printf型関数の命名、危険な操作、構造体の変換タグ漏れを検査する。 |
| `iface`・`interfacebloat`・`ireturn` | 重複・過大なinterfaceやinterface戻り値を検査し、抽象化の形をそろえる。 |
| `importas`・`inamedparam` | import別名とinterface引数の名前を検査し、呼び出し側から意味を読めるようにする。 |
| `intrange`・`mirror`・`modernize`・`usestdlibvars` | 整数range・標準APIなど現在のGoで表せる形を確認し、同じ処理の書き方をそろえる。 |
| `iotamixing`・`mnd`・`tagliatelle` | iotaと通常値の混在、名前のない数値定数、JSONキーの表記を検査する。 |
| `makezero`・`prealloc`・`predeclared`・`reassign`・`recvcheck` | スライス初期化、確保、定義済み名の隠蔽、識別子の再代入、レシーバーの違いを検査する。 |
| `noinlineerr`・`perfsprint`・`revive` | エラーをif初期化部に閉じる形、不要な文字列整形、Goのスタイルと独自の制約を検査する。 |
| `paralleltest`・`testpackage`・`thelper`・`tparallel`・`usetesting` | 並列テスト、外部テストパッケージ、Helper、親子テストの並列指定、testing APIの使い方を検査する。 |
| `unconvert`・`unparam`・`unused`・`wastedassign` | 不要な変換・引数・宣言・代入を検出し、使わないコードを残さない。 |

#### 整形・制限値・例外

| 設定 | 動作と、この基盤での理由 |
| --- | --- |
| version: 2、run.timeout: 5m、tests: true | v2形式で設定し、1回のlintを5分までに制限する。テストコードも通常コードと一緒に確認する |
| formatters.enable | gofumptでGoの整形、goimportsでimportの整理、golinesで長い行を折り返し、作者による表記差を減らす |
| gofumpt.module-path、extraの3項目 | モジュールをexample.com/go-cliと認識させ、引数のまとめ方・戻り値・呼び出しの追加整形を有効にする。すでに整形済みでも追加差分が出る場合がある |
| goimports.local-prefixes | example.com/go-cliをローカルimport群に分け、標準・外部・自分のコードを識別できるようにする |
| golines.max-len: 120、reformat-tags: false、shorten-comments: false | 行を120桁へ折り返す一方、構造体タグとコメントの短縮は行わず、公開JSON定義と説明の表記を保つ |
| formatters.exclusions.generated: strict | 正規の生成コードの識別に基づいて整形対象から除外する。手書きコードの除外には使わない |
| errcheck.check-type-assertions / check-blank: true | 型アサーションの失敗と、捨てたerrorも確認して見落としを防ぐ |
| decorderのdec-orderとdisable設定 | type → const → var → funcを有効にし、init先頭も検査する。一種類の宣言を複数ブロックに分ける数の制限は無効にする |
| forbidigo.analyze-typesとforbid | 型情報を使い、直接の出力・log・panic・時計・context生成・プロセス環境の読み取り・値変換を禁止する。出力はcli、実行環境はmain、変換はdomainへ集める |
| funcorderの3つのtrue | constructor、struct-method、functionの順序検査を有効にし、同じ役割を同じ位置へそろえる |
| funlen: 50行 / 30文 / ignore-comments: true | 説明コメントを長さに数えず、実処理の大きさを制限する |
| gocognit.min-complexity: 15、nestif.min-complexity: 4 | 読み解く分岐が増えた関数や入れ子を早めに指摘し、処理の分割を促す |
| godoclint | basicに加えパッケージ説明、宣言の説明、無効な文書リンクを検査する。公開・非公開の宣言を両方対象にして、拡張時の見本を残す |
| godox.keywords | `TODO`・`FIXME`・`BUG`・`HACK`・`XXX`を残した実装を検出し、未完了を見過ごさない |
| gomodguard_v2.allowed: []、local-replace-directives: true | 空のallowedは許可先を制限しない。外部依存を禁止するのはarchcheckのDEP-04で、go.modのrequireを拒否する。local-replace-directivesはローカルreplaceを禁止し、検査ツールは別modfileで扱う |
| gosec.excludes: []、importas.no-extra-aliases: true | セキュリティ規則の個別除外を置かず、明示的な別名定義にない余計なimport別名を禁じる |
| revive.confidence: 0.5、enable-default-rules: true | 既定規則に加え、modifies-parameterなど信頼度0.5の指摘も有効にする |
| revive.argument-limit: 4、function-result-limit: 2、max-control-nesting: 3 | 引数を4個、戻り値を2個、制御の入れ子を3段までにし、関数の境界を読みやすくする |
| revive.deep-exit / early-return / modifies-parameter / modifies-value-receiver | 深い位置での終了を避け、早期returnで分岐を浅くし、引数や値レシーバーの変更を検出する |
| revive.enforce-map-style: make、enforce-repeated-arg-type-style: short | mapの初期化と同じ型の引数の書き方をそれぞれ一通りにそろえる |
| revive.filename-format | 英小文字と数字のGoファイル名、必要なら_testの末尾だけを許可し、動詞名の表記をそろえる |
| revive.package-directory-mismatch / redundant-import-alias / unused-receiver | パッケージとディレクトリの不一致、不要なimport別名・レシーバーを検出する |
| revive.use-any / use-errors-new / time-equal | any、errors.New、時刻のEqualという用途に合った表記を使う |
| tagliatelle.case.use-field-name: true、json: snake | フィールド名からJSONのsnake_caseキーを検査し、created_atなどの公開面をそろえる |
| wrapcheck.extra-ignore-sigs | io.WriteStringとfmtの書き込み結果はラップ対象から除外し、出力エラーは呼び出し元のcliでまとめて扱う |
| wrapcheck.ignore-package-globs | example.com/go-cli配下からのerrorをラップ必須の対象外にし、既存の業務エラーをそのまま伝える |
| linters.exclusions.generated: strict、warn-unused: false | 正規の生成コードを除外し、使用されなかった除外規則の警告は出さない |
| main.goのforbidigo / DEP-05除外 | プロセス値を受け取る入口だけはosや時計を使えるようにする |
| toolsのforbidigoとgodoclintの一部除外 | 保護された検査ツールではプロセス操作を許し、宣言コメントの一部規則を外す。コマンド作者のコードには広げない |
| domain・appのERR-04除外 | 値変換をdomainと設定読み取りのappへ集めるため、その2層だけ変換呼び出しを許す |
| _test.goのfunlen・godoclint・gosec除外 | テーブルテストの長さ・宣言説明・テスト用値に関する指摘を外し、テストは別の構造規約でそろえる |
| issuesの0 / 0 / false | linterごとの件数と同文の件数を制限せず、1行に複数の指摘も表示する。違反例が期待する診断が省略されないようにする |

</details>


### エージェントに同じ手順を渡す

.claude/settings.jsonは編集前に.foundation/bin/hooks.py pre-editを呼び、保護対象の変更を検知します。編集後のpost-editではGoファイルの整形とそのパッケージのlintを実行します。`$CLAUDE_PROJECT_DIR`を起点にするため、Claude Codeで展開先を直接開くことが条件です。編集前は30秒、編集後は120秒が上限で、実際の整形・lintコマンドはmanifestに110秒の上限で登録されています。

ほかのエージェントでhooksが動くことは前提にしません。AGENTS.md、実装スキル、レビュースキルを直接読み、同じ手順を実行します。実装スキルは変更に応じたファイルと作成順を示し、レビュー用スキルは機械で決められない意味の確認を担当します。

.foundation/manifest.jsonには保護対象、抑止の禁止パターン、make check・make fix、各検査と版、既存の収束評価の条件があります。収束評価は3エージェント・最大3ラウンド・並列3・1回1800秒で、同じ課題への差を測った元実装の開発記録です。通常のCLI実行や今回のZIP検証はエージェント評価を起動しません。元の評価結果と、利用先で新しく確認した結果は分けて扱います。

## ZIPを単独で検証する

掲載サイトのNode.js環境は必要ありません。展開先で次を実行します。

```sh
python3 scripts/verify-ci.py
```

make checkが通ると、一時ディレクトリにCLIをビルドします。別プロセスで追加・一覧・完了を実行し、文章とJSON、保存ファイル、空一覧、入力制約、終了コード0・1・2・3、0600/0700の権限、`--`を確認します。保存失敗は子プロセスだけのファイルサイズ制限で再現し、元データの維持と一時ファイルの片付けも確認します。

続いて`violation_probe.py --only DEP-01-a,STR-04-a,TOOL-03-a`を使い、一時コピーでcommandからadapterへの依存、動詞ファイルの構成違反、抑止コメントを検出します。検査が非0で終了するだけでなく、出力がその違反の期待パターンに一致することも成功条件です。

`ci.json`はこのコマンドを掲載元の共通CIへ渡します。

```json
{
  "command": ["python3", "scripts/verify-ci.py"],
  "goVersionFile": "go.mod",
  "pythonVersion": "3.12"
}
```

Goは配布物のgo.modから、Pythonは3.12から準備します。UbuntuとNode.jsは掲載元の共通CIの環境であり、ZIPの実装がNode.jsに依存するわけではありません。利用先のCIやリリース自動化は同梱していないため、必要なら同じPythonコマンドを自分のCIから呼びます。

全77件の違反検出をやり直す場合は、展開先の作業用コピーで`python3 .foundation/bin/violation_probe.py --root .`を実行します。一部実行と違って.foundation/probe-results.jsonを更新するため、元の配布物で実行しないようにします。続いて`python3 .foundation/bin/rules_check.py --root . --final --no-write`で結果との整合を確認できます。

## 検証方法と結果

確認日：2026-10-20。macOS 15.7.3（arm64）、Go 1.27.2、GNU Make 3.81、Python 3.14.2、Node.js 24.9.0、Chromiumで確認しました。検証対象はこのページに対応する生成ZIPです。

| 確認 | 期待結果 | 実際の結果 |
| --- | --- | --- |
| ZIP展開先のpython3 scripts/verify-ci.py | 全検査、CLI操作、代表的な違反3件の検出が成功 | 成功。保存失敗時のデータ保持と一時ファイルの削除も確認 |
| 掲載元の配置・文書確認、単体テスト、型チェック、ビルド | すべて終了コード0 | 成功。単体テスト50件 |
| 掲載元のE2E | すべて成功 | 初回は準備ビルドがヒープ不足で停止。`NODE_OPTIONS=--max-old-space-size=8192 npm run test:e2e`で再実行し6件成功 |
| 実際の掲載ページ、検索、ZIPの取得 | 説明を読めて対応する実装を取得できる | 成功。PC・モバイル、一覧・サイドバー・検索、折りたたみ、ZIP内106ファイルと隠し設定を確認 |

同梱する77件の違反検出結果と収束評価は元実装の記録であり、今回の3件の再実行と区別します。人間による説明・成果物の最終レビュー、Linux・Python 3.12のCI環境での実行は未確認です。Windowsは対応対象外です。

## 参考資料

- [Go公式：コマンドと補助パッケージの構成](https://go.dev/doc/modules/layout)
- [flagの仕様（Go 1.27.2）](https://pkg.go.dev/flag@go1.27.2)
- [Goのツールチェーン選択](https://go.dev/doc/toolchain)
- [golangci-lintの設定形式](https://golangci-lint.run/docs/configuration/file/)
- ZIP内のdocs/design/overview.md・architecture.md・rules.md・adr/：この基盤が選んだ構造と規約の理由

## ダウンロード

[実装をダウンロード](/downloads/patterns/development/cli/go-cli.zip)
