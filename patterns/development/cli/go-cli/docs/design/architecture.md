# go-cli のアーキテクチャ

この文書は、構造そのものと、その構造を選んだ理由を説明する。個々のルールの全文は [rules.md](rules.md) にある。用語（名詞、動詞、層、Service、ビュー、出力型など）は rules.md の「用語」の表の意味で使う。

## 1. 前提

構造は、次の3つの前提から決めた。

1. **よく起きる変更は「足す」変更である。** CLI に対する依頼の多くは、サブコマンドを1つ足す、フラグを1つ足す、記録する項目を1つ足す、新しい名詞（`note` など）を足す、のどれかである。したがって、足すときに触るファイルが少なく、どこを触るかが事前に分かる構造にする
2. **触るのは、この基盤を初めて見る作者（人とエージェント）である。** 作者は一番近くにある既存のコードを写す。したがって、写す先（参照実装の `task`）が1つに決まり、写した結果がルールに合う構造にする
3. **公式の推奨に沿う。** Go の公式の指針は、コマンドをルートの `package main` に、補助のパッケージを `internal/` に置くことを勧めている。interface は使う側のパッケージに置き、context は第1引数で渡す（[research.md「Go の公式の設計指針」](research.md#go-の公式の設計指針)）。CLI の出力と終了コードは clig.dev の指針に合わせる（[research.md「Command Line Interface Guidelines」](research.md#command-line-interface-guidelinescligdev)）

この3つから、「CLI の都合（引数・出力）」「業務の規則」「保存の方法」をそれぞれ別の層に分け、依存を業務の規則（domain）に向ける構造を選んだ。こうすると、サブコマンドの追加は command 層、保存形式の変更は adapter 層、というように変更の理由ごとに触る層が1つに決まる。

## 2. ディレクトリ構造

```text
go-cli/
├── main.go                      # 入口。プロセスの値を app.Run に渡して終了する（STR-08）
├── internal/
│   ├── app/                     # 組み立て。設定を読み、Store → Service → コマンドの順に組む
│   │   ├── app.go
│   │   ├── config.go            # 環境変数を読む唯一の場所（OPS-02）
│   │   └── apptest/apptest.go   # テストで CLI を実行する道具（TEST-03）
│   ├── cli/                     # フラグ解析・ヘルプ・出力・終了コードの枠組み（OPS-05）
│   │   ├── cli.go
│   │   ├── exit.go
│   │   ├── help.go
│   │   └── table.go
│   ├── command/
│   │   └── taskcmd/             # 名詞 task のサブコマンド（STR-04）
│   │       ├── taskcmd.go       # New：サブコマンドの一覧
│   │       ├── view.go          # taskView：出力での見え方
│   │       ├── add.go           # 動詞1つにファイル1つ
│   │       ├── complete.go
│   │       └── list.go
│   ├── domain/
│   │   └── task/                # 名詞 task の業務の規則
│   │       ├── task.go          # Task、ParseID、validateTitle
│   │       ├── service.go       # Service：use case
│   │       └── repository.go    # Repository：保存の interface
│   ├── adapter/
│   │   └── taskstore/           # Repository を JSON ファイルで実装する
│   │       └── taskstore.go
│   └── errkind/errkind.go       # エラーの種類（ErrInvalid、ErrNotFound）
├── tools/
│   ├── archcheck/main.go        # 構造検査（make arch）
│   └── clidoc/main.go           # docs/cli.md の生成と鮮度の確認（make generate、make docs-check）
└── docs/
    ├── cli.md                   # 生成物：コマンドの一覧（STR-07）
    └── design/                  # 設計ドキュメント
```

テストファイル（`<対象>_test.go`）は対象の隣に置くため、tree から省いた（STR-06）。置いてよいディレクトリとファイル名は STR-01 と STR-03 で閉じている。

層を名詞で分けず、層の下に名詞を置いた（`internal/domain/task/`）のは、層ごとに import してよい相手が違い、その境界を「ディレクトリの接頭辞」1つで検査できるからである。名詞ごとの変更はディレクトリ3つ（domain、adapter、command）にまたがるが、各ディレクトリの中のファイル名が決まっているため、触る場所は予測できる。

## 3. 依存の許可表

依存の向きは、外側（入口、CLI、保存）から内側（業務の規則）に向ける。domain は errkind 以外の何も import しないので、CLI の書き方や保存形式を変えても domain は変わらない。adapter が domain の `Repository` を実装し、command が domain の `Service` を呼び、app が両方を組み合わせる。

行のパッケージから、列のパッケージを import してよい組に ✓ を付ける。✓ の無い組は全部禁止で、構造検査で強制する（ルールID：DEP-01、DEP-03）。

| from \ to | app | apptest | cli | command | domain | adapter | errkind |
|---|---|---|---|---|---|---|---|
| `main.go` | ✓ | | | | | | |
| app | | | ✓ | ✓ | ✓ | ✓ | ✓ |
| apptest | ✓ | | | | | | |
| cli | | | | | | | ✓ |
| command | | | ✓ | | ✓ | | ✓ |
| domain | | | | | | | ✓ |
| adapter | | | | | ✓（同じ名詞だけ） | | |
| errkind | | | | | | | |
| tools | ✓ | | ✓ | | | | |
| `_test.go`（すべて） | | ✓ | | | | | |

- テストファイルは、上の表に加えて、自分のパッケージと `apptest` を import してよい
- 同じ層の別の名詞のパッケージ（`domain/task` から `domain/note`）は import しない。2つの名詞をまたぐ処理は command で組み合わせる（DEP-03）
- 標準ライブラリのうち副作用のあるもの（`os`、`flag`、`encoding/json` など）は、使ってよい層が DEP-05 の表で決まっている。外部モジュールは使わない（DEP-04）

## 4. 公開面

全体を `internal/` の下に置いたので、モジュールの外からは何も import できない。そのうえで、モジュールの中でもパッケージの入口を絞る。入口が狭いほど、別のパッケージが内部の型に依存する経路が減り、変更が局所に収まる。

| パッケージ | 外から使ってよいもの | 触れなくする仕組み |
|---|---|---|
| `internal/app` | `Env`、`New`、`Run` | DEP-02（構造検査） |
| `internal/app/apptest` | `Harness`、`Result`、`New`、`Harness.Run`、`Harness.Setup`、`Harness.Setenv` | DEP-02 |
| `internal/cli` | `App`、`Group`、`Command`、`Arg`、`IO`、`Output`、`WriteTable`、`ExitCodes` など | 制限なし（全コマンドが使う枠組みのため） |
| `internal/command/<noun>cmd` | `New` | DEP-02。`new<Verb>` と `run<Verb>` は非公開 |
| `internal/domain/<noun>` | エンティティ、`Filter` のような引数の型、`Parse<X>`、`Service`、`NewService`、`Repository` | `validate<Field>` と Service の補助関数は非公開 |
| `internal/adapter/<noun>store` | `Store`、`New`、`Store.Load`、`Store.Save` | DEP-02。保存形式の `document` と `record` は非公開 |
| `internal/errkind` | `ErrInvalid`、`ErrNotFound` | DEP-02 |

CLI の利用者から見える公開面（サブコマンド名、フラグ名、JSON のキー、終了コード、環境変数名）は、[docs/cli.md](../cli.md) に生成される。名前を変えるときの手順は PROC-06 で決めている。

## 5. データの流れ

`go-cli task add "Buy milk" --json` を例に、入力から出力までに通る層を順に書く。

1. **`main.go`**：`signal.NotifyContext` で Ctrl+C に反応する context を作り、引数・標準出力・標準エラー・`os.Getenv`・`time.Now` を `app.Env` に入れて `app.Run` を呼ぶ。返った終了コードで `os.Exit` する
2. **`internal/app`**：`loadConfig` がデータディレクトリを決める（`$GOCLI_DATA_DIR` → `$XDG_DATA_HOME/go-cli` → `$HOME/.local/share/go-cli`）。`taskstore.New` → `task.NewService` → `taskcmd.New` の順に組み、`cli.App` を作って `Run` を呼ぶ
3. **`internal/cli`**：`task` のグループと `add` のコマンドを探し、フラグを解析する。フラグは位置引数の前後どちらに書いてもよい。`--json` と `--help` はここで全コマンドに付く。位置引数の数を確かめ、`opts.title` に入れて、コマンドの `Run` を呼ぶ
4. **`internal/command/taskcmd`**：`runAdd` が `svc.Add(ctx, opts.title)` を呼び、返った `Task` を `toTaskView` でビューに変えて `addOutput` を返す
5. **`internal/domain/task`**：`Service.Add` がタイトルの前後の空白を除いて `validateTitle` で検証し、`Repository.Load` で全件を読み、次の ID と現在時刻で `Task` を作り、`Repository.Save` で書く
6. **`internal/adapter/taskstore`**：`Load` は `tasks.json` を読んで `record` から `Task` に変える。`Save` は一時ファイルに書いてから `os.Rename` で置き換える
7. **`internal/cli`（戻り）**：`--json` なので出力型を JSON で標準出力に書く。エラーが返った場合は、`errkind` の種類から終了コード（2：入力の誤り、3：見つからない、1：それ以外）を決め、標準エラーに `go-cli: <エラー>` を書く

コマンドが自分で書き込み先や終了コードを選ぶ経路は無い。`cli.Command.Run` の型が `(cli.Output, error)` を返すだけだからである（OPS-05）。

## 6. 変更シナリオ表

よく起きる変更ごとに、触るファイルと触らないものを示す。どの行も、触るファイルは1つの名詞の中か、決まった1か所に収まっている。

| 変更 | 触るファイル | 触らないもの |
|---|---|---|
| サブコマンドを足す（`task remove`） | `domain/task/service.go`（`Remove`）、`command/taskcmd/remove.go`、`remove_test.go`、`taskcmd.go`、`docs/cli.md`（生成） | adapter、app、cli、errkind |
| 既存のサブコマンドにフラグを足す（`task list --limit`） | `command/taskcmd/list.go`、`list_test.go`、domain の引数の型（`Filter`）と `service.go`（絞り込みが業務の規則なら）、`docs/cli.md`（生成） | adapter、app、cli、ほかのサブコマンド |
| エンティティに項目を足す（期限 `Due`） | `domain/task/task.go`、`service.go`、`<noun>_test.go`（`Parse<X>` を足すなら）、`adapter/taskstore/taskstore.go`（`record`、`toRecord`、`toTask`）、`taskstore_test.go`、`command/taskcmd/view.go`、項目を入出力するサブコマンドとそのテスト、`docs/cli.md`（生成） | app、cli、errkind |
| 名詞を足す（`note`） | `domain/note/`、`adapter/notestore/`、`command/notecmd/` の各ファイル一式（STR-02）、`app/app.go`、`cli/cli_test.go`（`--help` の名詞の一覧の期待値）、`docs/cli.md`（生成） | 既存の名詞のパッケージ、cli のテスト以外のファイル、errkind |
| 環境変数の設定を足す（`GOCLI_TITLE_MAX`） | `app/config.go`（`env<Name>`・`default<Name>`・`load<Name>`・`config` のフィールド）、`app/app.go`、値を受け取る組み立て関数（`NewService` など）と、既定値の定数を移すなら `domain/task/task.go`、`app_test.go`、値が効くサブコマンドのテスト、`README.md` | cli、errkind、adapter（保存に関係しなければ） |
| エラーの種類を足す | `errkind/errkind.go`、`cli/exit.go`、`docs/cli.md`（生成） | command、adapter |
| 保存形式を変える（JSON から別の形式へ） | `adapter/<noun>store/` だけ | domain、command、cli、app（パスが変わらなければ） |
