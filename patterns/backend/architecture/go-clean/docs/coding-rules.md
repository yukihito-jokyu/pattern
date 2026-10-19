# コーディングルール

層ごとの書き方と、横断的なルールをまとめる。背景は [architecture.md](architecture.md) を参照。

## 層ごとのルール

### domain（`internal/domain/<集約>/`）
- エンティティのフィールドは **非公開** にし、getter で公開する
- 生成は `New...` コンストラクタで行い、**不変条件をコンストラクタで検証** する
- DB からの復元には `Reconstruct` を使う（検証済みの前提で検証を省略する）
- 値オブジェクト（`Email` など）は型を分け、`NewXxx` で検証する
- 状態の変更はエンティティのメソッドで行う。setter（`SetName`）は作らず、操作の名前（`Rename`）を付けて `New` と同じ規則で検証する
- 他の集約は ID だけで参照する（`Order` は `user.ID` を持ち、`*user.User` は持たない）。lint（forbidigo）で止まる。集約を足したら、[.golangci.yml](../.golangci.yml) にそのエンティティのパターンと除外の 1 行を足す（[adding-a-feature.md 1-2](adding-a-feature.md#1-2-domain-を作るinternaldomainorder)）
- 現在時刻は `New` などの引数で受け取る。`time.Now` を呼ぶと lint（forbidigo）で止まる
- ID は `id.go` に [user/id.go](../internal/domain/user/id.go) と同じ形で書く。生成は標準ライブラリの `uuid.New`、`ParseID` は `uuid.Parse` で検証して `u.String()`（小文字のハイフン区切り）にそろえて返す
- 数値のフィールドは、下限だけでなく上限も決めて `New` で検証する（上限がないと、DB の列の範囲を超えた値が 500 になる）
- エラーは `errors.go` に `var ( ErrXxx = errors.New("<集約>: ...") )` のブロックで定義する（1 つだけでもブロックにする）
- import してよいのは **標準ライブラリと、他の集約の domain だけ**。`json` / `db` タグは付けない

### usecase（`internal/usecase/`）
- ファイル名は `<集約>.go`（例: `user.go`）。1集約に1つの struct を用意し、ユースケースはそのメソッドにする
- 形は次のとおり
  - `<動詞><集約>Input` struct（入力。例: `CreateUserInput`）
  - `<集約>Usecase` struct（依存を非公開フィールドで保持）
  - `New<集約>Usecase(...) *<集約>Usecase`（struct を返す）
  - `<動詞>(ctx, <動詞><集約>Input) (*<集約>Output, error)`（例: `Create`）
- 外部依存は [port.go](../internal/usecase/port.go) に interface として定義する。**必要なメソッドだけ** を持たせる（usecase の他のファイルに interface を書かない。lint では検出できないので注意する）
- port にメソッドを足したら、`fake_test.go` の fake にも足す
- 複数の書き込み、または「読んでから書く」処理は `TxManager.Do` で囲む
- メール送信や外部 API の呼び出しは、`TxManager.Do` の外（コミットした後）で行う。ロールバックで取り消せないため
- 一覧は `<集約>ListOutput` に包んで返す。件数の既定値と上限は usecase の定数に置き、範囲外の値は丸める
- 戻り値は Output struct に詰め替え、domain の型を外へ出さない
- 現在時刻は `now func() time.Time` フィールド経由で取得する（テストで固定できるように）。`time.Now` を直接呼ぶと lint（forbidigo）で止まる。コンストラクタの `now: time.Now` だけは許す
- 他の usecase を呼ばない。他の集約のデータが必要なら、その集約の port（`UserRepository` など）を struct に持たせて直接取る。他の usecase のメソッドを呼ぶと lint（forbidigo）で止まる。共通の判断は domain へ寄せる

### adapter/handler（`internal/adapter/handler/`）
- やることは「リクエスト → Input → usecase → Output → レスポンス」の変換だけ。**ビジネス判断を書かない**
- usecase は handler 側で定義した interface（`userUsecase` など）で受け取る
- リクエスト/レスポンス構造体は [dto.go](../internal/adapter/handler/dto.go) に置く。非公開型にする。`gin.H` は使わない（lint で止まる）
- リクエストの JSON は `decodeJSON` で読む。`c.ShouldBindJSON` などは使わない（lint で止まる）
- ルーターは `gin.New` に自前のミドルウェアを付けて作る。`gin.Default` は使わない（lint で止まる）
- usecase は自分で生成せず、`cmd/api/main.go` から受け取る（`usecase.NewXxx` を呼ぶと lint で止まる）
- エラーは必ず `writeError` に渡す。ドメインエラーを追加したら [error.go](../internal/adapter/handler/error.go) の `errorMappings` に追加する
- ルートは [router.go](../internal/adapter/handler/router.go) に `r.GET("/users/:id", ...)` の形式で登録する。gin の `*gin.Context` は handler 層の外に渡さず、usecase には `c.Request.Context()` を渡す
- メソッドとステータスは次のとおりにする

  | 操作 | メソッド | 成功時 |
  |---|---|---|
  | 作成 | `POST` | 201 と作成したリソース |
  | 取得・一覧 | `GET` | 200。一覧は `{"users": [...]}` のようにオブジェクトで包む |
  | 更新 | `PATCH` | 200 と更新後のリソース |
  | 削除 | `DELETE` | 204（本文なし） |
- HTTP の入力形式の誤り（JSON やクエリパラメータが読めない）は、`error.go` に非公開のエラーとして定義し、`errorMappings` に足す
- ミドルウェアは [middleware.go](../internal/adapter/handler/middleware.go) に `func xxx(c *gin.Context)` の形で書き、`router.go` で登録する

### adapter/repository（`internal/adapter/repository/`）
- `var _ usecase.XxxRepository = (*XxxRepository)(nil)` で、interface を実装していることをコンパイル時に保証する
- `*sql.DB` はコンストラクタで受け取る。`sql.Open` は infra/database でだけ使う（lint で止まる）
- DB へのアクセスは必ず `conn(ctx, r.db)` 経由で行う（トランザクションに自動で参加するため）。`r.db` を直接使うと lint（forbidigo）で止まる
- `sql.ErrNoRows` は `<集約>.ErrNotFound` に、一意制約違反は対応するドメインエラーに変換する
- 外部キー違反は、参照先の集約の `ErrNotFound` に変換する（例：注文の `user_id` が指すユーザーがいない → `user.ErrNotFound`）。判定関数は [db.go](../internal/adapter/repository/db.go) の `isUniqueViolation` と同じ形で `isForeignKeyViolation`（コード `23503`）を足す。外部キーが 2 つ以上あるテーブルは `pgErr.ConstraintName` で区別する
- `UPDATE` / `DELETE` は `RowsAffected()` を確かめ、0 件なら `<集約>.ErrNotFound` を返す
- 一覧の `ORDER BY` は、最後に一意な列（`id`）を足して順序を確定させる
- SQL は `const q = ...` としてメソッド内に書く。キーワードは大文字にし、句（`SELECT` / `FROM` / `WHERE` / `VALUES` など）と列は 1 行に 1 つずつ書く

### adapter/<外部サービス>（`internal/adapter/mail/` など）
- DB 以外の外部サービス（メール送信、外部 API）の実装は、相手ごとにディレクトリを分けて置く
- `var _ usecase.Xxx = (*Xxx)(nil)` で、port を実装していることをコンパイル時に保証する
- `http.Client` や接続先は自分で作らず、コンストラクタで受け取る（`cmd/api/main.go` から渡す）。`http.DefaultClient` と環境変数の読み込みは lint で止まる
- adapter 同士は import しない（lint の depguard で止まる）

### DB マイグレーション（`db/migrations/`）
- 1 つのマイグレーションで 1 つのテーブルを作る。名前は `create_<テーブル>`、テーブル名は複数形の snake_case
- 列は 1 行に 1 つ書き、列名・型・制約の位置をそろえる（お手本: [000001_create_users.up.sql](../db/migrations/000001_create_users.up.sql)）
- 型は次のとおりにする。列はすべて `NOT NULL` にする

  | 値 | 型 |
  |---|---|
  | ID | `UUID`（自分の ID は `PRIMARY KEY`） |
  | 文字列 | `VARCHAR(n)`。`n` は domain の上限と同じ値 |
  | 数値 | `INTEGER`。domain の範囲を `CHECK` でも書く（例: `CHECK (quantity >= 1 AND quantity <= 100)`） |
  | 日時 | `TIMESTAMPTZ` |
- 他の集約を参照する列は `<集約>_id UUID NOT NULL REFERENCES <テーブル> (id) ON DELETE RESTRICT` と書く。`ON DELETE` は省略せず書く（削除の仕様で決まった場合だけ `CASCADE` にする）
- 外部キーの列には、同じファイルでインデックスを作る（`CREATE INDEX <テーブル>_<列>_idx ON <テーブル> (<列>);`）
- down は `DROP TABLE IF EXISTS <テーブル>;` だけを書く（インデックスはテーブルと一緒に消える）

### API 仕様（`api/openapi.yaml`）
- API を足したら同じ変更で更新する。お手本は `/users` の定義
- `paths` は [router.go](../internal/adapter/handler/router.go) のルートと同じ順に並べる。`summary` は「<集約の日本語名><操作>」（例: `ユーザー作成`、`ユーザー名変更`）
- path パラメータの ID は `type: string` / `format: uuid` にする
- 成功レスポンスの `description` は `作成成功` / `取得成功` / `更新成功` / `削除成功`（204 は `content` なし）
- エラーレスポンスは、そのエンドポイントで返りうるステータスごとに `$ref: "#/components/responses/Error"` を書く。個別に `description` や `content` を書かない。どのエラーで返るかは `errorMappings` が正
- `components/schemas` は集約ごとに `<動詞><集約>Request` → `<集約>` の順に並べ、`Error` を最後に置く。新しい集約は `Error` の直前に足す
- スキーマのプロパティ名は `dto.go` の `json` タグと同じにする。リクエストには domain と同じ制約（`maxLength`、`minimum` / `maximum`）を書き、レスポンスは全プロパティを `required` にする。日時は `format: date-time`
- `errorMappings` に新しい `code` を足したら、`Error` の `code` の `enum` にも足す

### infra（`internal/infra/`）
- 技術的な初期化だけを書く。domain / usecase / adapter を import しない
- 環境変数は infra/config でだけ読む（他で `os.Getenv` を呼ぶと lint で止まる）

### cmd/api
- 依存の組み立て（DI）はここだけで行う。ロジックは書かない

## 横断ルール

### エラー
- 下位のエラーは `fmt.Errorf("<何をしていたか>: %w", err)` でラップして返す
- 判定は `errors.Is` / `errors.As` で行う（`==` や文字列比較は使わない）
- ログ出力は handler の `writeError`（500 の場合）でだけ行う。下位の層でログを出してからエラーを返すことはしない。domain・usecase・handler 以外の adapter で `log/slog` を import すると lint（depguard）で止まる
- 例外は [tx.go](../internal/adapter/repository/tx.go) の、パニック中にロールバックが失敗したときのログだけ（返す先がないため）。`.golangci.yml` で対象外にしてある

### context
- I/O を伴う関数は第1引数に `ctx context.Context` を取る
- context を struct のフィールドに保持しない
- `context.Background()` / `context.TODO()` は cmd でだけ使う（他で使うと lint で止まる）。途中で作ると、キャンセルと `TxManager.Do` のトランザクションが途切れる

### ログ
- `log/slog` の `slog.InfoContext(ctx, ...)` などを使う。`fmt.Println` / `log` パッケージは使わない
- キーは snake_case にする（例: `duration_ms`）

### 命名
- パッケージ名は小文字の単数形。`util` / `common` / `helper` / `shared` と `pkg/` は作らない（lint で止まる）
- `user.User` のような重複は許容するが、`user.UserID` のような冗長な名前は避けて `user.ID` とする

### テスト
- テストは対象と同じディレクトリに `xxx_test.go` として置く
- **テーブル駆動** で書き、ケース名は日本語でよい
- usecase のテストでは [fake_test.go](../internal/usecase/fake_test.go) の手書きフェイクを使う。モック生成ツールは導入しない
- domain は外部公開 API の観点で `package user_test` から、usecase は非公開フィールド（`now`）を差し替えるため同じパッケージからテストする
- 関数名は、パッケージの関数なら `Test<関数>`（`TestNew`）、メソッドなら `Test<型>_<メソッド>`（`TestUser_Rename`、`TestUserUsecase_Create`）
- テーブルのフィールドは `name` → 準備（`repo` など）→ 入力（`input` または `id`）→ 期待値（`want...`）→ `wantErr` の順にする。テーブルに入れる準備は、ケースごとに変わるものだけにする（全ケースで同じ fake はテーブルに入れず `t.Run` の中で作る）
- 既存データの ID などはテーブルの外で先に作り、「空なら既定値を使う」のような分岐をケースの中に作らない。「存在しない」ケースは、別の `NewID()` で表す
- fake に入れるエンティティは、ケースごとに `Reconstruct` で作る（`t.Parallel()` で動くので、`Rename` のように書き換えるテストでケース間で共有するとデータ競合になる）
- `t.Run` の中は次の順に書く（お手本: [user_test.go](../internal/usecase/user_test.go)）
  1. `errors.Is(err, tt.wantErr)` を `t.Fatalf` で確かめる
  2. `if tt.wantErr != nil { return }`
  3. 期待値と 1 回で比べる。usecase は期待する Output を struct で 1 つ作り `*got != want` で比べる（ID など生成される値は `got` から写す）。domain はフィールドが非公開なので、getter の比較を `||` でつないだ 1 つの `if` にする
  4. 保存されたかなど、fake の状態を確かめる
- domain の状態を変えるメソッド（`Rename` など）だけは、エラーのケースでも状態が変わっていないことを確かめる。エラーのケースにも `wantName` を書き、2 の `return` の前に比べる
- 関数の複雑さの上限（gocognit）で止まったら、確認を削らずに、テスト関数を観点ごとに分ける

### プロジェクト独自の lint ルール
- このプロジェクト独自のルールも [.golangci.yml](../.golangci.yml) の設定だけで表す（forbidigo のパターン、depguard のルール、`exclusions` での適用範囲の指定）。Go で書くルールファイル（ruleguard）は使わない
- 設定だけで表せないルールは、このファイルに書いて守る
- どのルールを lint で止めていて、どれが止められないかの一覧は [lint-rules.html](lint-rules.html) の「独自ルールの一覧」にある

### 依存ライブラリ
- 追加する前に標準ライブラリで代替できないか検討する
- `go.mod` の `go` ディレクティブを勝手に上げない。上げるときは Makefile の `GOLANGCI_LINT_VERSION` も、その Go 以上でビルドされた版に合わせて上げる（ツールチェーンと golangci-lint の互換性のため）
