# 機能追加の手順

コードを増やすときの手順を、増やし方のパターンごとにまとめる。どのパターンも **内側の層から外側の層へ**（domain → usecase → adapter → cmd）の順に作る。内側から作ると、各ステップの時点で依存先がすでに存在するため、コンパイルを通しながら進められる。

| やりたいこと | 見る章 |
|---|---|
| 新しい集約（テーブル）を作って作成 API を足す | [1](#1-新しい集約を追加する) |
| 既存の集約に更新 API を足す | [2](#2-更新-api-を追加する) |
| 既存の集約に削除 API を足す | [3](#3-削除-api-を追加する) |
| 一覧 API を足す | [4](#4-一覧-api-を追加する) |
| 処理の中で他の集約のデータを使う | [5](#5-他の集約のデータを使う) |
| メール送信・外部 API など DB 以外の外部サービスを使う | [6](#6-db-以外の外部サービスを使う) |
| ミドルウェアや、HTTP だけのエラーを足す | [7](#7-ミドルウェアと-http-だけのエラーを足す) |

どのパターンでも、最後に [8. 共通の確認](#8-共通の確認) を行う。

コード例は `user` と、架空の集約 `order`（注文）で示す。

---

## 1. 新しい集約を追加する

新しい集約 `order` に「作成 API」を追加する流れ。

### 1-1. DB マイグレーションを作る
```sh
make migrate-new NAME=create_orders
```
`db/migrations/00000N_create_orders.{up,down}.sql` を編集する。型・外部キー・インデックスの決まりは [coding-rules.md の DB マイグレーション](coding-rules.md#db-マイグレーションdbmigrations) に従う。

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

### 1-2. domain を作る（`internal/domain/order/`）
- `order.go`：エンティティ、`New`、`Reconstruct`、getter
- `id.go`：[user/id.go](../internal/domain/user/id.go) をコピーし、コメントの「ユーザー」を集約名に変える（`NewID` と `ParseID`。標準ライブラリの `uuid` を使う）
- `errors.go`：`ErrNotFound` など。1 つだけでも `var ( ... )` のブロックで書く
- `order_test.go`：コンストラクタの検証をテーブル駆動でテストする
- [.golangci.yml](../.golangci.yml) の forbidigo に、新しいエンティティを他の集約から参照させないルールを足す（`user` の 2 か所を真似る）

  ```yaml
          - pattern: ^order\.Order$
            msg: 他の集約は ID だけで参照する（order.Order）
  ```
  ```yaml
        - path: internal/domain/order/  # 自分の集約のエンティティは使ってよい
          linters: [forbidigo]
          text: ID だけで参照する（order\.Order）
  ```

お手本: [domain/user/](../internal/domain/user/)

### 1-3. usecase を作る（`internal/usecase/`）
1. `order.go` に `CreateOrderInput` / `OrderOutput` / `OrderUsecase` / `NewOrderUsecase` / `Create` と、詰め替え関数 `newOrderOutput` を作る
2. [port.go](../internal/usecase/port.go) に `OrderRepository` interface を追加する（`Create` が使うメソッドだけ）
3. `fake_test.go` に `fakeOrderRepository` を追加し、`order_test.go` を書く

port の interface は、usecase のどこかで使われていないと lint（iface）で止まる。先に port だけを足すことはできないので、usecase と同時に足す。

お手本: [user.go](../internal/usecase/user.go), [user_test.go](../internal/usecase/user_test.go)

### 1-4. repository を作る（`internal/adapter/repository/order.go`）
- `var _ usecase.OrderRepository = (*OrderRepository)(nil)` を書く
- `conn(ctx, r.db)` 経由で SQL を実行し、DB のエラーをドメインエラーに変換する

お手本: [repository/user.go](../internal/adapter/repository/user.go)

### 1-5. handler を作る（`internal/adapter/handler/`）
1. `dto.go` に `createOrderRequest` / `orderResponse` を追加する
2. `order.go` に `orderUsecase` interface と `OrderHandler` を作る
3. `error.go` の `errorMappings` に `order.ErrXxx` を追加する
4. `router.go` の `NewRouter` に引数とルートを追加する

お手本: [handler/user.go](../internal/adapter/handler/user.go)

### 1-6. DI を配線する（`cmd/api/main.go`）
```go
orderRepo := repository.NewOrderRepository(db)
orderHandler := handler.NewOrderHandler(usecase.NewOrderUsecase(orderRepo, txManager))
// handler.NewRouter(userHandler, orderHandler)
```

他の集約の port を使う場合（[5 章](#5-他の集約のデータを使う)）は、その repository も渡す（`usecase.NewOrderUsecase(orderRepo, userRepo, txManager)`）。

### 1-7. API 仕様を更新する
[api/openapi.yaml](../api/openapi.yaml) にパスとスキーマを追加する。並び順・名前・エラーの書き方は [coding-rules.md の API 仕様](coding-rules.md#api-仕様apiopenapiyaml) に従う。

```yaml
  /orders:
    post:
      summary: 注文作成
      # requestBody と 201 は /users の post と同じ形
      responses:
        "400":
          $ref: "#/components/responses/Error"
        "404":
          $ref: "#/components/responses/Error"  # 注文者がいない場合も個別に書かない
```

---

## 2. 更新 API を追加する

ユーザー名を変更する `PATCH /users/:id` を例にする。

### 2-1. domain：状態を変えるメソッドを足す
フィールドは非公開なので、変更はエンティティのメソッドで行う。setter（`SetName`）は作らず、**操作の名前** を付けて `New` と同じ規則で検証する。

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

### 2-2. usecase：読んでから書くので `TxManager.Do` で囲む

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

- port の `UserRepository` に `Update(ctx context.Context, u *user.User) error` を足す
- 同時に更新されて上書きされては困る場合は、`SELECT ... FOR UPDATE` で行をロックする取得メソッド（`FindByIDForUpdate`）を port に足して使う

### 2-3. repository：0 件更新は `ErrNotFound` にする

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

### 2-4. handler：200 で更新後のリソースを返す

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

`dto.go` に `renameUserRequest`、`router.go` に `r.PATCH("/users/:id", users.Rename)`、handler の `userUsecase` interface に `Rename` を足す。

---

## 3. 削除 API を追加する

`DELETE /users/:id` を例にする。

- usecase：`Delete(ctx, DeleteUserInput) error`。書き込みが 1 回だけなので `TxManager.Do` は不要
- repository：`DELETE FROM users WHERE id = $1` を実行し、更新と同じく `RowsAffected() == 0` なら `user.ErrNotFound` を返す
- handler：成功したら本文なしの 204 を返す

```go
// Delete は DELETE /users/:id を処理する。
func (h *UserHandler) Delete(c *gin.Context) {
	if err := h.users.Delete(c.Request.Context(), usecase.DeleteUserInput{ID: c.Param("id")}); err != nil {
		writeError(c, err)
		return
	}

	c.Status(http.StatusNoContent)
}
```

他のテーブルから外部キーで参照されている行を削除するときの扱い（一緒に消す・削除を拒否する）は、マイグレーションの `ON DELETE` とドメインエラーで決める。

---

## 4. 一覧 API を追加する

`GET /users?limit=20&offset=0` を例にする。

### 4-1. ページングの決まり
- クエリパラメータは `limit`（件数）と `offset`（読み飛ばす件数）
- 既定値と上限は usecase の定数に置く（このテンプレートでは 20 件と 100 件）。範囲外の値はエラーにせず、既定値や上限に丸める
- 並び順は必ず指定する。同じ値が並ぶと順序が不定になるので、最後に一意な列（`id`）を足す

### 4-2. usecase

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

出力は `<集約>ListOutput` に包む。件数の合計や次ページの情報を後から足せるようにするため。

### 4-3. repository

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

- [db.go](../internal/adapter/repository/db.go) の `querier` に `QueryContext` がなければ追加する（`*sql.DB` と `*sql.Tx` の両方が持つメソッド）
- `rows.Close()` と `rows.Err()` を忘れると lint（sqlclosecheck / rowserrcheck）で止まる

### 4-4. handler
- クエリパラメータを整数に変換し、変換できなければ `errInvalidQuery`（HTTP だけのエラー。[7 章](#7-ミドルウェアと-http-だけのエラーを足す)）を返して 400 にする
- レスポンスは配列をそのまま返さず、`{"users": [...]}` のようにオブジェクトで包む

---

## 5. 他の集約のデータを使う

注文を作るときに、注文者のユーザーが存在するかを確かめる例。

**他の usecase は呼ばない。他の集約の port から直接取る。** `OrderUsecase` から `*UserUsecase` のメソッドを呼ぶと、lint（forbidigo）で止まる。

```go
// OrderUsecase は注文に関するユースケース。
type OrderUsecase struct {
	orders OrderRepository
	users  UserRepository // 他の集約のデータは、その集約の port から直接取る
	tx     TxManager
	now    func() time.Time
}

// Create は注文者が存在することを確かめてから注文を作成する。
func (uc *OrderUsecase) Create(ctx context.Context, in CreateOrderInput) (*OrderOutput, error) {
	userID, err := user.ParseID(in.UserID)
	if err != nil {
		return nil, err
	}

	o, err := order.New(userID, in.Item, uc.now())
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

- 読んでから書くので `TxManager.Do` で囲む。同じ ctx を渡すので、両方の repository が同じトランザクションに参加する
- domain では、他の集約を **ID だけで参照する**（`Order` は `userID user.ID` を持ち、`*user.User` は持たない）
- 存在を確かめてから保存するまでの間に、参照先が削除されることがある。そのときの外部キー違反は、repository で参照先の `ErrNotFound` に変換する

  ```go
  	_, err := conn(ctx, r.db).ExecContext(ctx, q, ...)
  	if isForeignKeyViolation(err) {
  		return user.ErrNotFound
  	}
  ```

  `isForeignKeyViolation` は [db.go](../internal/adapter/repository/db.go) の `isUniqueViolation` と同じ形で、コード `23503` を判定する。使う repository を作るときに足す（使われていない関数は lint で止まる）
- 両方の集約にまたがる判断（例：「退会済みのユーザーは注文できない」）は、usecase に書かず、判断に使う側の集約の domain に関数として置く

---

## 6. DB 以外の外部サービスを使う

注文確認メールを、メール送信 API で送る例。

### 6-1. 置き場所

| もの | 置き場所 |
|---|---|
| interface（port） | [port.go](../internal/usecase/port.go)（例：`Mailer`） |
| 実装 | `internal/adapter/<相手の名前>/`（例：`internal/adapter/mail/mail.go`） |
| 接続先 URL や認証情報 | [infra/config](../internal/infra/config/) で読み、`cmd/api/main.go` から実装に渡す |

adapter 同士は import できない（lint の depguard で止まる）。usecase の port を通してだけつながる。

### 6-2. 実装

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

- `http.Client` や接続先は、adapter の中で作らずにコンストラクタで受け取る（`cmd/api/main.go` で作って渡す）
- 外部サービスのエラーは `fmt.Errorf("send mail request: %w", err)` のように包んで返す。handler の対応表にないので 500 になり、`writeError` がログに残す

### 6-3. usecase からの呼び出しは、コミットした後に行う

5 章の `Create` に送信を足す場合、`Do` の中で取得したユーザーを外側の変数 `orderer` に残しておき、`Do` の後で送る。

```go
	if txErr != nil {
		return nil, txErr
	}

	// 外部への送信はロールバックできないので、コミットした後に行う
	if err := uc.mailer.SendOrderConfirmation(ctx, orderer.Email().String(), string(o.ID())); err != nil {
		return nil, fmt.Errorf("send order confirmation: %w", err)
	}
```

`TxManager.Do` の中で送ると、送った後に DB の処理が失敗してロールバックされても、メールは取り消せない。

コミット後に送信が失敗すると、注文は保存済みのままエラー（500）が返る。確実に届ける必要がある場合は、送信予定をテーブルに書いて別のプロセスで送る仕組み（Outbox）が必要になるが、このテンプレートの範囲外とする。

---

## 7. ミドルウェアと HTTP だけのエラーを足す

### 7-1. ミドルウェア
- [middleware.go](../internal/adapter/handler/middleware.go) に `func xxx(c *gin.Context)` の形で書き、`c.Next()` で次の処理を呼ぶ
- 全ルートに効かせるなら [router.go](../internal/adapter/handler/router.go) の `r.Use(...)` に足す。一部のルートだけなら `r.Group(...)` でまとめてから `Use` する
- 途中で止めるときは `c.AbortWithStatusJSON(...)` を使い、本文は `errorResponse` の形にそろえる

### 7-2. エラーの置き場所

| エラーの種類 | 置き場所 | 例 |
|---|---|---|
| ビジネスルールの違反 | domain の `errors.go`（公開） | `user.ErrInvalidName`、`user.ErrNotFound` |
| HTTP の入力形式の誤り | handler の `error.go`（非公開） | `errInvalidJSON`、`errInvalidQuery` |

どちらも `errorMappings` に 1 行足す。足し忘れると 500 になり、コンパイルでも lint でも気付けない。usecase は独自のエラーを定義しない。

---

## 8. 共通の確認

### 8-1. port にメソッドを足したら
- `fake_test.go` の fake にも同じメソッドを足す（足さないと `go vet` / テストのコンパイルで止まる）
- handler 側の interface（`userUsecase` など）にも、使うメソッドだけを足す

### 8-2. 規模の目安
- handler 側の interface のメソッドが 10 個を超えると、lint（interfacebloat）で止まる。その集約の usecase が大きくなりすぎた合図なので、読み取り系と書き込み系などに分ける
- 集約が 5〜10 個を超えたら、[architecture.md 5 章](architecture.md#5-規模が大きくなったら) の構成へ移る

### 8-3. 検証する
```sh
make check   # build → vet → test → lint（依存方向とプロジェクト独自のルールを含む）
```

lint で止まったときの読み方：

| 止めたルール | 意味 | 直し方 |
|---|---|---|
| depguard | 依存の向きが間違っている | import を消し、interface を使う側に定義し直す |
| forbidigo（`conn(ctx, r.db)`） | repository が `r.db` を直接使った | `conn(ctx, r.db)` 経由にする |
| forbidigo（他の usecase を呼ばない） | usecase が他の usecase のメソッドを呼んだ | 相手の集約の port から直接取る（[5 章](#5-他の集約のデータを使う)） |
| forbidigo / depguard（そのほかの独自ルール） | メッセージに書いた決まりに反した | メッセージに従う。理由と直し方の例は [lint-rules.html](lint-rules.html) の「独自ルールの一覧」 |
