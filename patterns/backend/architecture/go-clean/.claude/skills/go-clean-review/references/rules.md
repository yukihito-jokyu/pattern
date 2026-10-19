# go-clean のルール

go-clean（Go と PostgreSQL で作る、クリーンアーキテクチャ構成の HTTP API）のコードが守るルールの全文である。このファイルだけで判断できるように、ルールと、ルールが「この形で書く」と決めているコードのひな形を載せる。

- 例は、集約 `user`（ユーザー）と `order`（注文）で示す
- 各節の番号（「4 handler」など）は、指摘の出典として使う
- 「lint で止まる」と書いたルールは、`make check` の golangci-lint が検出する

---

## 1 構成と依存の向き

### 1.1 ディレクトリ

```
cmd/api/                     起動と DI 配線のみ
internal/domain/<集約>/       エンティティ・値オブジェクト・ドメインエラー
internal/usecase/            port.go に interface、<集約>.go にユースケース
internal/adapter/handler/    HTTP ⇔ usecase の変換、エラー → ステータスの対応表
internal/adapter/repository/ usecase の port の DB 実装
internal/adapter/<外部>/      usecase の port の外部サービス実装（例: mail）
internal/infra/              設定・DB 接続・ロガー
db/migrations/               golang-migrate 形式の SQL
api/openapi.yaml             API 仕様
```

外部ライブラリは pgx（DB ドライバ）と gin（ルーティング。handler 層だけで使う）。ログは `log/slog`。

### 1.2 依存の向き（lint で止まる）

- 依存は `cmd → adapter → usecase → domain` の一方向。逆向きの import をしない
- domain は標準ライブラリと、他の集約の domain 以外を import しない
- usecase は `database/sql`・`net/http`・gin を import しない。外部依存は `port.go` の interface 経由で使う
- adapter 同士（handler / repository / 外部サービス）は import しない。adapter は infra を import しない
- **lint のエラーを `.golangci.yml` の変更や `//nolint` で黙らせない**

### 1.3 コマンド

| 目的 | コマンド |
|---|---|
| 検証一式（完了前に必須） | `make check`（build → vet → test → lint） |
| 整形（gofmt / golines の指摘を直す） | `make fmt` |
| マイグレーションの作成 | `make migrate-new NAME=create_<テーブル>` |

golangci-lint と migrate は `make` が `bin/` に固定バージョンで入れたものを使う。グローバルに入っているものは直接使わない。

---

## 2 domain（`internal/domain/<集約>/`）

### 2.1 エンティティ

- フィールドは **非公開** にし、getter で公開する。`json` / `db` タグは付けない
- 生成は `New` で行い、**不変条件を `New` で検証する**
- DB からの復元は `Reconstruct` で行う。検証済みの前提なので検証しない
- 現在時刻は `New` の引数で受け取る（`time.Now` を呼ぶと lint で止まる）
- 前後の空白の除去などの正規化は、検証の **前** に行う
- 数値のフィールドは、下限と上限の両方を `New` で検証する（上限がないと、DB の範囲を超えた値が 500 になる）
- 上限・下限は定数にし、`maxXxxLength`（文字数）、`minXxx` / `maxXxx`（数値）と名付ける。DB と openapi の制約もこの値に合わせる
- 状態の変更は、操作の名前のメソッド（`Rename` など）で行う。setter（`SetName`）は作らない。変更メソッドは `New` と **同じ検証関数** を使う
- 他の集約は ID だけで参照する（`Order` は `user.ID` を持ち、`*user.User` は持たない。lint で止まる）
- 集約をまたぐ判断（「退会済みのユーザーは注文できない」など）は、判断に使う側の集約の domain に関数として置く
- import してよいのは、標準ライブラリと他の集約の domain だけ

```go
package order

const (
	maxItemLength = 100
	minQuantity   = 1
	maxQuantity   = 100
)

// Order は注文エンティティ。注文者は ID だけで参照する。
type Order struct {
	id        ID
	userID    user.ID
	item      string
	quantity  int
	createdAt time.Time
}

// New は不変条件を検証して注文を生成する。
func New(userID user.ID, item string, quantity int, now time.Time) (*Order, error) {
	item = strings.TrimSpace(item)
	if item == "" || utf8.RuneCountInString(item) > maxItemLength {
		return nil, ErrInvalidItem
	}

	if quantity < minQuantity || quantity > maxQuantity {
		return nil, ErrInvalidQuantity
	}

	return &Order{id: NewID(), userID: userID, item: item, quantity: quantity, createdAt: now}, nil
}

// Reconstruct は永続化層からの復元専用。検証済みのデータであることを前提とする。
func Reconstruct(id ID, userID user.ID, item string, quantity int, createdAt time.Time) *Order {
	return &Order{id: id, userID: userID, item: item, quantity: quantity, createdAt: createdAt}
}

// Item は商品名を返す。
func (o *Order) Item() string { return o.item }
```

状態を変えるメソッドの形：

```go
// Rename は名前を変更する。New と同じ規則で検証する。
func (u *User) Rename(name string) error {
	name = strings.TrimSpace(name)
	if err := validateName(name); err != nil {
		return err
	}

	u.name = name

	return nil
}
```

### 2.2 ID（`id.go`）

集約ごとに次の形で書く。違うのはコメントの集約名だけである。

```go
package order

import "uuid"

// ID は UUID 形式の注文識別子。
type ID string

// NewID は新しい ID をランダムに生成する。
func NewID() ID {
	return ID(uuid.New().String())
}

// ParseID は文字列を検証して ID に変換する。大文字などの表記揺れは小文字のハイフン区切りにそろえる。
func ParseID(s string) (ID, error) {
	u, err := uuid.Parse(s)
	if err != nil {
		return "", ErrInvalidID
	}

	return ID(u.String()), nil
}

func (id ID) String() string { return string(id) }
```

### 2.3 エラー（`errors.go`）

1 つだけでも `var ( ... )` のブロックで書き、メッセージは `"<集約>: "` で始める。

```go
package order

import "errors"

// 注文集約のドメインエラー。
var (
	ErrInvalidID       = errors.New("order: invalid id")
	ErrInvalidItem     = errors.New("order: invalid item")
	ErrInvalidQuantity = errors.New("order: invalid quantity")
	ErrNotFound        = errors.New("order: not found")
)
```

### 2.4 集約を足したときの lint の設定

`.golangci.yml` に、新しいエンティティを他の集約から参照させないための 2 行を足す。`.golangci.yml` に足してよいのは、この 2 か所だけである。

```yaml
        # linters.settings.forbidigo.forbid に足す
        - pattern: ^order\.Order$
          msg: 他の集約は ID だけで参照する（order.Order）
```
```yaml
      # linters.exclusions.rules に足す
      - path: internal/domain/order/  # 自分の集約のエンティティは使ってよい
        linters: [forbidigo]
        text: ID だけで参照する（order\.Order）
```

---

## 3 usecase（`internal/usecase/`）

### 3.1 形と名前

- ファイルは `<集約>.go`。1 集約に 1 つの struct を作り、ユースケースはそのメソッドにする
- `<動詞><集約>Input`（入力）、`<集約>Output`（出力）、`<集約>Usecase`（依存を非公開フィールドで持つ）、`New<集約>Usecase(...) *<集約>Usecase`
- メソッドは `<動詞>(ctx, <動詞><集約>Input) (*<集約>Output, error)`。削除のように返す値がなければ `error` だけ
- 一覧は `<集約>ListOutput` で包んで返す。件数の既定値と上限は定数に置き、範囲外の値はエラーにせず丸める
- 戻り値は Output に詰め替え、**domain の型を外へ出さない**（Input / Output のフィールドも文字列や数値にする）
- 現在時刻は `now func() time.Time` フィールドから取る。コンストラクタの `now: time.Now` だけは許す（それ以外で `time.Now` を呼ぶと lint で止まる）
- usecase で独自のエラーを定義しない（ビジネスルールのエラーは domain に置く）

### 3.2 port（`port.go`）

- 外部依存は `port.go` に interface として定義する。**使うメソッドだけ** を持たせる。usecase の他のファイルに interface を書かない
- port にメソッドを足したら、`fake_test.go` の fake にも足す
- 使われていない port のメソッドは lint（iface）で止まるので、port は usecase と同時に足す

### 3.3 トランザクションと外部サービス

- 複数の書き込み、または「読んでから書く」処理は `TxManager.Do` で囲む。同じ ctx を渡すので、複数の repository が同じトランザクションに参加する
- 同時に更新されて上書きされては困る「読んでから書く」処理は、`SELECT ... FOR UPDATE` で取得するメソッド（`FindByIDForUpdate`）を port に足して使う
- メール送信や外部 API の呼び出しは、`TxManager.Do` の **外**（コミットの後）で行う。ロールバックで取り消せないため

### 3.4 他の集約と、判断の置き場所

- 他の usecase を呼ばない（lint で止まる）。他の集約のデータは、その集約の port（`UserRepository` など）を struct に持たせて直接取る
- ビジネス判断（値の範囲、状態による可否）は domain に置く。usecase の判断は「存在するか」「重複していないか」のように port に聞くものだけにする

### 3.5 エラー

- port から返ったエラーは `fmt.Errorf("<何をしていたか>: %w", err)` で包む
- domain の検証エラー、`ParseID` のエラー、1 回だけの取得の `ErrNotFound` はそのまま返してよい

```go
// Create は注文者が存在することを確かめてから注文を作成する。
func (uc *OrderUsecase) Create(ctx context.Context, in CreateOrderInput) (*OrderOutput, error) {
	userID, err := user.ParseID(in.UserID)
	if err != nil {
		return nil, err
	}

	o, err := order.New(userID, in.Item, in.Quantity, uc.now())
	if err != nil {
		return nil, err
	}

	txErr := uc.tx.Do(ctx, func(ctx context.Context) error {
		if _, err := uc.users.FindByID(ctx, userID); err != nil {
			return fmt.Errorf("find user: %w", err)
		}

		if err := uc.orders.Create(ctx, o); err != nil {
			return fmt.Errorf("create order: %w", err)
		}

		return nil
	})
	if txErr != nil {
		return nil, txErr
	}

	return newOrderOutput(o), nil
}
```

---

## 4 handler（`internal/adapter/handler/`）

- やることは「リクエスト → Input → usecase → Output → レスポンス」の変換だけ。**ビジネス判断を書かない**
- usecase は handler 側で定義した interface（`orderUsecase` など。使うメソッドだけ）で受け取る。10 個を超えると lint で止まる
- usecase には `c.Request.Context()` を渡す。`*gin.Context` を handler の外に渡さない
- リクエスト / レスポンスの構造体は `dto.go` に非公開の型で置く。`gin.H` は使わない（lint で止まる）
- リクエストの JSON は `decodeJSON` で読む。`c.ShouldBindJSON` などは使わない（lint で止まる）
- ルーターは `gin.New` で作る（`gin.Default` は lint で止まる）。ルートは `router.go` に `r.GET("/orders/:id", orders.Get)` の形で登録する
- usecase を自分で生成しない（`usecase.NewXxx` を呼ぶと lint で止まる）
- エラーは必ず `writeError` に渡す。ステータスを直接書かない
- ドメインエラーと HTTP だけのエラーは、すべて `error.go` の `errorMappings` に 1 行足す。**足し忘れると 500 になり、コンパイルでも lint でも気付けない**
- HTTP の入力形式の誤り（JSON やクエリパラメータが読めない）は、`error.go` に非公開のエラー（`errInvalidJSON`、`errInvalidQuery`）として定義する
- ステータスの対応：不正な入力 400、存在しない 404、重複 409

| 操作 | メソッド | 成功時 |
|---|---|---|
| 作成 | `POST` | 201 と作成したリソース |
| 取得・一覧 | `GET` | 200。一覧は `{"orders": [...]}` のようにオブジェクトで包む |
| 更新 | `PATCH` | 200 と更新後のリソース |
| 削除 | `DELETE` | 204（本文なし） |

- 一覧のクエリパラメータ（`limit` / `offset`）が整数に変換できなければ `errInvalidQuery` を返して 400 にする
- ミドルウェアは `middleware.go` に `func xxx(c *gin.Context)` の形で書き、`c.Next()` で次へ進む。途中で止めるときは `c.AbortWithStatusJSON` と `errorResponse` を使う

```go
// Create は POST /orders を処理する。
func (h *OrderHandler) Create(c *gin.Context) {
	var req createOrderRequest
	if err := decodeJSON(c, &req); err != nil {
		writeError(c, err)
		return
	}

	out, err := h.orders.Create(
		c.Request.Context(),
		usecase.CreateOrderInput{UserID: req.UserID, Item: req.Item, Quantity: req.Quantity},
	)
	if err != nil {
		writeError(c, err)
		return
	}

	c.JSON(http.StatusCreated, newOrderResponse(out))
}
```

```go
// errorMappings に足す行の形
	{order.ErrInvalidQuantity, http.StatusBadRequest, codeInvalidArgument},
	{order.ErrNotFound, http.StatusNotFound, "not_found"},
```

---

## 5 repository（`internal/adapter/repository/`）

- `var _ usecase.XxxRepository = (*XxxRepository)(nil)` で、port を実装していることをコンパイル時に保証する
- `*sql.DB` はコンストラクタで受け取る。DB へのアクセスは必ず `conn(ctx, r.db)` 経由（トランザクションに自動で参加するため。`r.db` を直接使うと lint で止まる）
- SQL は `const q = ...` としてメソッド内に書く。キーワードは大文字、句（`SELECT` / `FROM` / `WHERE` / `VALUES` など）と列は 1 行に 1 つ
- 値は `$1` などのプレースホルダで渡す。`fmt.Sprintf` や `+` で SQL を組み立てない
- エラーの変換：

| DB の結果 | 返すもの |
|---|---|
| `sql.ErrNoRows` | `<集約>.ErrNotFound` |
| 一意制約違反（`23505`、`isUniqueViolation`） | 対応するドメインエラー（`user.ErrEmailAlreadyExists` など） |
| 外部キー違反（`23503`、`isForeignKeyViolation`） | 参照先の集約の `ErrNotFound`。外部キーが 2 つ以上なら `pgErr.ConstraintName` で区別する |
| `UPDATE` / `DELETE` の `RowsAffected()` が 0 | `<集約>.ErrNotFound` |
| それ以外 | `fmt.Errorf("<何をしていたか>: %w", err)` |

- 一覧の `ORDER BY` は、最後に一意な列（`id`）を足して順序を確定させる
- `rows.Close()` と `rows.Err()` を忘れない（lint で止まる）
- `querier` にメソッドを足すときは、`*sql.DB` と `*sql.Tx` の両方が持つメソッドにする
- 判定関数は `db.go` に置く。使われていない関数は lint で止まるので、使うときに足す

```go
func isForeignKeyViolation(err error) bool {
	var pgErr *pgconn.PgError
	return errors.As(err, &pgErr) && pgErr.Code == "23503"
}
```

```go
// Create は注文を保存する。注文者が存在しなければ user.ErrNotFound を返す。
func (r *OrderRepository) Create(ctx context.Context, o *order.Order) error {
	const q = `
		INSERT INTO orders (
			id,
			user_id,
			item,
			quantity,
			created_at
		)
		VALUES (
			$1,
			$2,
			$3,
			$4,
			$5
		)
	`

	_, err := conn(ctx, r.db).ExecContext(ctx, q, o.ID().String(), o.UserID().String(), o.Item(), o.Quantity(), o.CreatedAt())
	if isForeignKeyViolation(err) {
		return user.ErrNotFound
	}

	if err != nil {
		return fmt.Errorf("insert order: %w", err)
	}

	return nil
}
```

---

## 6 外部サービスの adapter（`internal/adapter/<相手の名前>/`）

- DB 以外の外部サービス（メール送信、外部 API）の実装は、相手ごとにディレクトリを分けて置く
- `var _ usecase.Xxx = (*Xxx)(nil)` で port を実装していることを保証する
- `http.Client` や接続先は自分で作らず、コンストラクタで受け取る（`cmd/api/main.go` から渡す）。`http.DefaultClient` と環境変数の読み込みは lint で止まる
- エラーは `fmt.Errorf("<何をしていたか>: %w", err)` で包む。handler の対応表にないので 500 になり、`writeError` がログに残す

---

## 7 DB マイグレーション（`db/migrations/`）

- up と down を必ず対で作る。作成は `make migrate-new NAME=create_<テーブル>`
- 1 つのマイグレーションで 1 つのテーブルを作る。名前は `create_<テーブル>`、テーブル名は複数形の snake_case
- 適用済みのマイグレーションファイルを書き換えない。変更は新しい番号のファイルで足す
- 列は 1 行に 1 つ書き、列名・型・制約の位置をそろえる。列はすべて `NOT NULL`

| 値 | 型 |
|---|---|
| ID | `UUID`（自分の ID は `PRIMARY KEY`） |
| 文字列 | `VARCHAR(n)`。`n` は domain の `maxXxxLength` と同じ |
| 数値 | `INTEGER`。domain の範囲を `CHECK` でも書く |
| 日時 | `TIMESTAMPTZ` |

- 他の集約を参照する列は `<集約>_id UUID NOT NULL REFERENCES <テーブル> (id) ON DELETE RESTRICT` と書く。`ON DELETE` は省略しない。`CASCADE` にするのは、削除の仕様でそう決まった場合だけ
- 外部キーの列には、同じファイルで `<テーブル>_<列>_idx` のインデックスを作る
- down は `DROP TABLE IF EXISTS <テーブル>;` だけ（インデックスはテーブルと一緒に消える）

```sql
CREATE TABLE orders (
    id         UUID         PRIMARY KEY,
    user_id    UUID         NOT NULL REFERENCES users (id) ON DELETE RESTRICT,
    item       VARCHAR(100) NOT NULL,
    quantity   INTEGER      NOT NULL CHECK (quantity >= 1 AND quantity <= 100),
    created_at TIMESTAMPTZ  NOT NULL
);

CREATE INDEX orders_user_id_idx ON orders (user_id);
```

```sql
DROP TABLE IF EXISTS orders;
```

---

## 8 API 仕様（`api/openapi.yaml`）

- API を変えたら同じ変更で更新する
- `paths` は `router.go` のルートと同じ順に並べる。`summary` は「<集約の日本語名><操作>」（例：`注文作成`、`ユーザー名変更`）
- path パラメータの ID は `type: string` / `format: uuid`
- 成功レスポンスの `description` は `作成成功` / `取得成功` / `更新成功` / `削除成功`。204 は `content` を書かない
- エラーレスポンスは、そのエンドポイントで **返りうるステータスごとに** `$ref: "#/components/responses/Error"` だけを書く（個別に `description` や `content` を書かない）。どのエラーがどのステータスになるかは `errorMappings` が正。path に ID があれば 400 と 404、リクエスト本文があれば 400、他の集約の存在確認があれば 404 が返りうる
- `components/schemas` は集約ごとに `<動詞><集約>Request` → `<集約>` の順に並べ、`Error` を最後に置く。新しい集約は `Error` の直前に足す
- プロパティ名は `dto.go` の `json` タグと同じにする。リクエストには domain と同じ制約（`maxLength`、`minimum` / `maximum`）を書く。レスポンスは全プロパティを `required` にする。日時は `format: date-time`
- `errorMappings` に新しい `code` を足したら、`Error` の `code` の `enum` にも足す

```yaml
  /orders:
    post:
      summary: 注文作成
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/CreateOrderRequest"
      responses:
        "201":
          description: 作成成功
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/Order"
        "400":
          $ref: "#/components/responses/Error"
        "404":
          $ref: "#/components/responses/Error"
  /orders/{id}:
    get:
      summary: 注文取得
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        "200":
          description: 取得成功
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/Order"
        "400":
          $ref: "#/components/responses/Error"
        "404":
          $ref: "#/components/responses/Error"
```

```yaml
    CreateOrderRequest:
      type: object
      required: [user_id, item, quantity]
      properties:
        user_id:
          type: string
          format: uuid
        item:
          type: string
          maxLength: 100
        quantity:
          type: integer
          minimum: 1
          maximum: 100
    Order:
      type: object
      required: [id, user_id, item, quantity, created_at]
      properties:
        id:
          type: string
          format: uuid
        user_id:
          type: string
          format: uuid
        item:
          type: string
        quantity:
          type: integer
        created_at:
          type: string
          format: date-time
```

---

## 9 infra と DI

- infra（`internal/infra/`）は技術的な初期化だけを書く。domain / usecase / adapter を import しない
- 環境変数は `infra/config` でだけ読む。DB 接続は `infra/database` でだけ作る（どちらも lint で止まる）
- 依存の組み立て（DI）は `cmd/api/main.go` でだけ、手書きで行う。ロジックは書かない。DI フレームワークは使わない
- 生成は repository → usecase → handler の順。他の集約の port を使う usecase には、その repository も渡す

```go
orderRepo := repository.NewOrderRepository(db)
orderHandler := handler.NewOrderHandler(usecase.NewOrderUsecase(orderRepo, userRepo, txManager))
// handler.NewRouter(userHandler, orderHandler)
```

---

## 10 横断

- **エラー**：下位のエラーは `fmt.Errorf("<何をしていたか>: %w", err)` で包む。判定は `errors.Is` / `errors.As`（`==` や文字列比較は使わない）
- **ログ**：`log/slog` の `slog.InfoContext(ctx, ...)` などを使う。キーは snake_case。ログを出すのは handler の `writeError`（500 の場合）とミドルウェアだけ。下位の層でログを出してからエラーを返さない。例外は repository の `tx.go` の、パニック中にロールバックが失敗したときのログだけ（返す先がないため）
- **context**：I/O を伴う関数は第 1 引数に `ctx context.Context` を取る。context を struct のフィールドに持たない。`context.Background()` / `context.TODO()` は cmd でだけ使う
- **命名**：パッケージ名は小文字の単数形。`util` / `common` / `helper` / `shared` パッケージと `pkg/` ディレクトリは作らない（lint で止まる）。`user.UserID` のような冗長な名前は避けて `user.ID` とする
- **コメント**：公開する型と関数には、何をするかが分かる日本語のコメントを付ける
- **範囲**：依頼されていない範囲のリファクタリングをしない（必要なら提案して承認を待つ）

---

## 11 テスト

### 11.1 何をテストするか

- domain と usecase は必ずテストを書く。handler と repository のテストは、規約ができるまで足さない
- テストは対象と同じディレクトリに `xxx_test.go` として置く。テーブル駆動で、`t.Parallel()` を呼ぶ。ケース名は日本語でよい
- domain は `package <集約>_test` から、usecase は `now` を差し替えるため `package usecase` からテストする
- usecase は `fake_test.go` の手書きの fake を使う。モック生成ツールは使わない
- ケースは次を網羅する：正常、返しうるエラーの種類ごと、境界値（上限ちょうどと上限 + 1、下限ちょうどと下限 - 1）、呼ぶ port ごとのエラーが包まれて返ること

### 11.2 書き方

- 関数名：パッケージの関数は `Test<関数>`（`TestNew`）、メソッドは `Test<型>_<メソッド>`（`TestUser_Rename`、`TestOrderUsecase_Create`）
- テーブルのフィールドは `name` → 準備（`orders` など）→ 入力（`input` または `id`）→ 期待値（`want...`）→ `wantErr` の順。テーブルに入れる準備は、ケースごとに変わるものだけ（全ケースで同じ fake は `t.Run` の中で作る）
- 既存データの ID はテーブルの外で先に作る。「空なら既定値を使う」のような分岐をケースの中に作らない。「存在しない」ケースは別の `NewID()` で表す
- fake に入れるエンティティは、ケースごとに `Reconstruct` で作る（`t.Parallel()` で動くので、ケース間で共有するとデータ競合になる）
- `t.Run` の中は次の順に書く
  1. `errors.Is(err, tt.wantErr)` を `t.Fatalf` で確かめる
  2. `if tt.wantErr != nil { return }`
  3. 期待値と 1 回で比べる。usecase は期待する Output を struct で作り `*got != want` で比べる（ID など生成される値は `got` から写す）。domain は getter の比較を `||` でつないだ 1 つの `if` にする
  4. 保存されたかなど、fake の状態を確かめる
- 状態を変えるメソッド（`Rename` など）は、エラーのケースでも状態が変わっていないことを確かめる。エラーのケースにも `wantName` を書き、2 の `return` の前に比べる
- 関数の複雑さの上限（gocognit）で止まったら、確認を削らずに、テスト関数を観点ごとに分ける

```go
func TestOrderUsecase_Get(t *testing.T) {
	t.Parallel()

	now := time.Date(2026, time.January, 1, 0, 0, 0, 0, time.UTC)
	existingID := order.NewID()
	userID := user.NewID()

	tests := []struct {
		name    string
		id      string
		wantErr error
	}{
		{name: "正常", id: existingID.String()},
		{name: "存在しない", id: order.NewID().String(), wantErr: order.ErrNotFound},
		{name: "不正なID", id: "not-a-uuid", wantErr: order.ErrInvalidID},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			orders := newFakeOrderRepository(order.Reconstruct(existingID, userID, "Apple", 3, now))
			uc := NewOrderUsecase(orders, newFakeUserRepository(), fakeTxManager{})

			got, err := uc.Get(t.Context(), GetOrderInput{ID: tt.id})
			if !errors.Is(err, tt.wantErr) {
				t.Fatalf("err = %v, want %v", err, tt.wantErr)
			}

			if tt.wantErr != nil {
				return
			}

			want := OrderOutput{ID: tt.id, UserID: userID.String(), Item: "Apple", Quantity: 3, CreatedAt: now}
			if *got != want {
				t.Errorf("got %+v, want %+v", *got, want)
			}
		})
	}
}
```

```go
// fake_test.go に足す fake の形
type fakeOrderRepository struct {
	orders map[order.ID]*order.Order
	err    error // 設定すると全メソッドがこのエラーを返す
}

func newFakeOrderRepository(orders ...*order.Order) *fakeOrderRepository {
	r := &fakeOrderRepository{orders: map[order.ID]*order.Order{}}
	for _, o := range orders {
		r.orders[o.ID()] = o
	}

	return r
}
```

---

## 12 lint の設定と依存

- `.golangci.yml` を変えて lint を黙らせない。変えてよいのは、集約を足したときの 2 か所（2.4）だけ
- `//nolint` で lint を黙らせない
- 外部ライブラリを足す前に、標準ライブラリで代わりにならないかを検討する
- 依頼なしに `go.mod` の `go` ディレクティブ、`Makefile` の `GOLANGCI_LINT_VERSION` / `MIGRATE_VERSION` を変えない。`go get` で依存を最新に上げない

---

## 13 完了前チェックリスト

1. `make check` が通る
2. ドメインエラーを足したら、`errorMappings` に足した（新しい `code` なら openapi の enum にも）
3. API を変えたら、`api/openapi.yaml` を更新した
4. スキーマを変えたら、`db/migrations/` に up と down の両方を足した
5. 集約を足したら、`.golangci.yml` に 2.4 の 2 か所を足した
6. 制約（最大長・範囲）を、domain・マイグレーション・openapi の 3 か所で同じ値にした
7. 足した repository / usecase / handler を `cmd/api/main.go` で配線した
8. port にメソッドを足したら、`fake_test.go` の fake にも足した
