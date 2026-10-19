# 追加のパターンごとの手順

どのパターンも **内側の層から外側の層へ**（マイグレーション → domain → usecase → repository → handler → DI → API 仕様）の順に作る。内側から作ると、各ステップの時点で依存先がすでにあるので、`go build ./...` を通しながら進められる。

書き方の決まりは [rules.md](rules.md) にある。この文書は「何をどの順に足すか」と、その場面に固有のコード例だけを載せる。

---

## 1 新しい集約を追加する（作成と取得）

1. **マイグレーション**：`make migrate-new NAME=create_orders` で作り、rules 7 の形で up と down を書く
2. **domain**（`internal/domain/order/`）
   - `order.go`：エンティティ、`New`、`Reconstruct`、getter（rules 2.1）
   - `id.go`：rules 2.2 のひな形を写し、コメントの集約名を変える
   - `errors.go`：rules 2.3 の形
   - `order_test.go`：`New` の検証をテーブル駆動でテストする（rules 11）
   - `.golangci.yml` に rules 2.4 の 2 か所を足す
3. **usecase**（`internal/usecase/`）
   - `order.go`：`CreateOrderInput` / `GetOrderInput` / `OrderOutput` / `OrderUsecase` / `NewOrderUsecase` / `Create` / `Get` と、詰め替え関数 `newOrderOutput`
   - `port.go`：`OrderRepository` を、使うメソッドだけで足す
   - `fake_test.go`：`fakeOrderRepository` を足す。`order_test.go` を書く
4. **repository**（`internal/adapter/repository/order.go`）：rules 5 の形。外部キーがあれば `db.go` に `isForeignKeyViolation` を足す
5. **handler**（`internal/adapter/handler/`）
   1. `dto.go` に `createOrderRequest` / `orderResponse` / `newOrderResponse` を足す
   2. `order.go` に `orderUsecase` interface と `OrderHandler` / `NewOrderHandler` を作る
   3. `error.go` の `errorMappings` に `order.ErrXxx` をすべて足す
   4. `router.go` の `NewRouter` に引数とルートを足す
6. **DI**（`cmd/api/main.go`）：rules 9 の形
7. **API 仕様**：rules 8 の形で paths とスキーマを足す

詰め替え関数の形：

```go
func newOrderOutput(o *order.Order) *OrderOutput {
	return &OrderOutput{
		ID:        o.ID().String(),
		UserID:    o.UserID().String(),
		Item:      o.Item(),
		Quantity:  o.Quantity(),
		CreatedAt: o.CreatedAt(),
	}
}
```

```go
// dto.go
type createOrderRequest struct {
	UserID   string `json:"user_id"`
	Item     string `json:"item"`
	Quantity int    `json:"quantity"`
}

type orderResponse struct {
	ID        string    `json:"id"`
	UserID    string    `json:"user_id"`
	Item      string    `json:"item"`
	Quantity  int       `json:"quantity"`
	CreatedAt time.Time `json:"created_at"`
}

func newOrderResponse(out *usecase.OrderOutput) orderResponse {
	return orderResponse{ID: out.ID, UserID: out.UserID, Item: out.Item, Quantity: out.Quantity, CreatedAt: out.CreatedAt}
}
```

---

## 2 更新 API を追加する（`PATCH /users/:id` の例）

1. **domain**：操作の名前のメソッド（`Rename`）を足し、`New` と同じ検証関数を使う（rules 2.1）。テストでは、エラーのケースで状態が変わっていないことも確かめる（rules 11.2）
2. **usecase**：読んでから書くので `TxManager.Do` で囲む。port の `UserRepository` に `Update` を足す。同時更新で上書きされて困る場合は `FindByIDForUpdate` を足して使う（rules 3.3）
3. **repository**：`RowsAffected()` が 0 なら `ErrNotFound`
4. **handler**：200 で更新後のリソースを返す。`dto.go` に `renameUserRequest`、`router.go` に `r.PATCH("/users/:id", users.Rename)`、handler の interface に `Rename` を足す
5. **API 仕様**：`summary: ユーザー名変更`、`description: 更新成功`、400 と 404

```go
// Rename はユーザー名を変更する。
func (uc *UserUsecase) Rename(ctx context.Context, in RenameUserInput) (*UserOutput, error) {
	id, err := user.ParseID(in.ID)
	if err != nil {
		return nil, err
	}

	var u *user.User

	txErr := uc.tx.Do(ctx, func(ctx context.Context) error {
		found, err := uc.repo.FindByID(ctx, id)
		if err != nil {
			return fmt.Errorf("find user: %w", err)
		}

		if err := found.Rename(in.Name); err != nil {
			return err
		}

		if err := uc.repo.Update(ctx, found); err != nil {
			return fmt.Errorf("update user: %w", err)
		}

		u = found

		return nil
	})
	if txErr != nil {
		return nil, txErr
	}

	return newUserOutput(u), nil
}
```

```go
// Update はユーザーを更新する。対象がなければ user.ErrNotFound を返す。
func (r *UserRepository) Update(ctx context.Context, u *user.User) error {
	const q = `
		UPDATE users
		SET
			name = $2
		WHERE
			id = $1
	`

	res, err := conn(ctx, r.db).ExecContext(ctx, q, u.ID().String(), u.Name())
	if err != nil {
		return fmt.Errorf("update user: %w", err)
	}

	n, err := res.RowsAffected()
	if err != nil {
		return fmt.Errorf("rows affected: %w", err)
	}

	if n == 0 {
		return user.ErrNotFound
	}

	return nil
}
```

```go
// Rename は PATCH /users/:id を処理する。
func (h *UserHandler) Rename(c *gin.Context) {
	var req renameUserRequest
	if err := decodeJSON(c, &req); err != nil {
		writeError(c, err)
		return
	}

	out, err := h.users.Rename(c.Request.Context(), usecase.RenameUserInput{ID: c.Param("id"), Name: req.Name})
	if err != nil {
		writeError(c, err)
		return
	}

	c.JSON(http.StatusOK, newUserResponse(out))
}
```

---

## 3 削除 API を追加する（`DELETE /orders/:id` の例）

- **usecase**：`Delete(ctx, DeleteOrderInput) error`。書き込みが 1 回だけなので `TxManager.Do` は不要
- **repository**：`DELETE FROM` の後、`RowsAffected() == 0` なら `ErrNotFound`（更新と同じ）
- **handler**：成功したら本文なしの 204
- **API 仕様**：`summary: 注文削除`、`"204": description: 削除成功`（`content` なし）、400 と 404
- 他のテーブルから外部キーで参照されている行を削除するときの扱いは、参照する側のマイグレーションの `ON DELETE` で決まる。`RESTRICT` の行を消すと外部キー違反になるので、拒否をドメインエラー（例：`user.ErrHasOrders`、409）に変える

```go
// Delete は DELETE /orders/:id を処理する。
func (h *OrderHandler) Delete(c *gin.Context) {
	if err := h.orders.Delete(c.Request.Context(), usecase.DeleteOrderInput{ID: c.Param("id")}); err != nil {
		writeError(c, err)
		return
	}

	c.Status(http.StatusNoContent)
}
```

---

## 4 一覧 API を追加する（`GET /users?limit=20&offset=0` の例）

- クエリパラメータは `limit`（件数）と `offset`（読み飛ばす件数）
- 既定値と上限は usecase の定数に置く（例：20 件と 100 件）。範囲外の値はエラーにせず丸める
- 並び順は必ず指定し、最後に `id` を足す
- `querier` に `QueryContext` がなければ足す
- handler はクエリパラメータを整数に変換し、変換できなければ `errInvalidQuery`（`error.go` に非公開で定義し、`errorMappings` に足す）を返す。レスポンスは `{"users": [...]}` で包む

```go
// List はユーザーを作成日時の新しい順に返す。
func (uc *UserUsecase) List(ctx context.Context, in ListUsersInput) (*UserListOutput, error) {
	limit := in.Limit
	if limit <= 0 {
		limit = defaultListLimit
	}

	limit = min(limit, maxListLimit)
	offset := max(in.Offset, 0)

	users, err := uc.repo.List(ctx, limit, offset)
	if err != nil {
		return nil, fmt.Errorf("list users: %w", err)
	}

	out := &UserListOutput{Users: make([]*UserOutput, 0, len(users))}
	for _, u := range users {
		out.Users = append(out.Users, newUserOutput(u))
	}

	return out, nil
}
```

```go
	const q = `
		SELECT
			id,
			name,
			email,
			created_at
		FROM
			users
		ORDER BY
			created_at DESC,
			id DESC
		LIMIT $1
		OFFSET $2
	`

	rows, err := conn(ctx, r.db).QueryContext(ctx, q, limit, offset)
	if err != nil {
		return nil, fmt.Errorf("select users: %w", err)
	}
	defer rows.Close()

	users := []*user.User{}

	for rows.Next() {
		// Scan して user.Reconstruct で復元し、users に追加する
	}

	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate users: %w", err)
	}
```

---

## 5 他の集約のデータを使う（注文の作成で注文者を確かめる例）

- 他の usecase は呼ばない。他の集約の port を struct に持たせて直接取る（rules 3.4）
- 読んでから書くので `TxManager.Do` で囲む（rules 3.5 の `Create` の例）
- DI では、その集約の repository も渡す：`usecase.NewOrderUsecase(orderRepo, userRepo, txManager)`
- 存在を確かめてから保存するまでの間に参照先が削除されると、外部キー違反になる。repository で参照先の `ErrNotFound` に変える（rules 5）
- openapi には、参照先がないときの 404 も書く
- 両方の集約にまたがる判断は、判断に使う側の集約の domain に関数として置く

```go
// OrderUsecase は注文に関するユースケース。
type OrderUsecase struct {
	orders OrderRepository
	users  UserRepository // 他の集約のデータは、その集約の port から直接取る
	tx     TxManager
	now    func() time.Time
}
```

---

## 6 DB 以外の外部サービスを使う（注文確認メールの例）

| もの | 置き場所 |
|---|---|
| interface（port） | `port.go`（例：`Mailer`） |
| 実装 | `internal/adapter/<相手の名前>/`（例：`internal/adapter/mail/mail.go`） |
| 接続先 URL や認証情報 | `infra/config` で読み、`cmd/api/main.go` から実装に渡す |

```go
// Package mail はメール送信 API の adapter。
package mail

var _ usecase.Mailer = (*Mailer)(nil)

// Mailer は usecase.Mailer の HTTP API 実装。
type Mailer struct {
	client   *http.Client
	endpoint string
}

// NewMailer は Mailer を生成する。
func NewMailer(client *http.Client, endpoint string) *Mailer {
	return &Mailer{client: client, endpoint: endpoint}
}
```

usecase からの呼び出しは、`Do` の **後** に置く。`Do` の中で取得したデータは外側の変数に残しておく。

```go
	if txErr != nil {
		return nil, txErr
	}

	// 外部への送信はロールバックできないので、コミットした後に行う
	if err := uc.mailer.SendOrderConfirmation(ctx, orderer.Email().String(), o.ID().String()); err != nil {
		return nil, fmt.Errorf("send order confirmation: %w", err)
	}
```

コミット後に送信が失敗すると、注文は保存済みのままエラー（500）が返る。確実に届ける必要がある場合（Outbox など）は、このテンプレートの範囲外なので、ユーザーに確認する。

---

## 7 ミドルウェアと HTTP だけのエラーを足す

- ミドルウェアは `middleware.go` に `func xxx(c *gin.Context)` の形で書き、`c.Next()` で次へ進む
- 全ルートに効かせるなら `router.go` の `r.Use(...)` に、一部のルートだけなら `r.Group(...)` でまとめてから `Use` する
- 途中で止めるときは `c.AbortWithStatusJSON(...)` を使い、本文は `errorResponse` の形にそろえる

| エラーの種類 | 置き場所 | 例 |
|---|---|---|
| ビジネスルールの違反 | domain の `errors.go`（公開） | `order.ErrInvalidQuantity` |
| HTTP の入力形式の誤り | handler の `error.go`（非公開） | `errInvalidJSON`、`errInvalidQuery` |

どちらも `errorMappings` に 1 行足す。usecase は独自のエラーを定義しない。

---

## 8 lint で止まったとき

| 止めたルール | 意味 | 直し方 |
|---|---|---|
| depguard | 依存の向きが間違っている | import を消し、interface を使う側に定義し直す |
| forbidigo（`conn(ctx, r.db)`） | repository が `r.db` を直接使った | `conn(ctx, r.db)` 経由にする |
| forbidigo（他の usecase を呼ばない） | usecase が他の usecase のメソッドを呼んだ | 相手の集約の port から直接取る（5） |
| forbidigo / depguard（そのほか） | メッセージに書いた決まりに反した | メッセージに従ってコードを直す |
| interfacebloat | handler の interface のメソッドが 10 個を超えた | 読み取り系と書き込み系などに分ける |
| gocognit（テスト） | テスト関数が複雑すぎる | 確認を削らず、観点ごとにテスト関数を分ける |
| gofmt / golines など | 整形 | `make fmt` |

どの場合も、`.golangci.yml` の変更や `//nolint` で黙らせない。
