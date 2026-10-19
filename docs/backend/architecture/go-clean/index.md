---
title: Goのクリーンアーキテクチャ
description: ユーザー作成APIを入口に、HTTP・業務処理・DBの分け方と、setupによる設定、実行・検証の方法を説明する。
slug: /backend/architecture/go-clean
---

# Goのクリーンアーキテクチャ

このパターンは、ユーザーを作成・取得できるGoのHTTP APIです。名前とメールをJSONで受け取り、PostgreSQLへ保存します。その小さなAPIを使って、「入力を読む処理」「業務のルール」「DBへ保存する処理」を分ける構成を学べます。

例えば、`POST /users`へ`{"name":"  Taro  ","email":"TARO@example.com"}`を送ると、名前の前後の空白を除き、メールを小文字にそろえて保存します。作成に成功したら201とユーザーIDを返し、そのIDを`GET /users/ID`へ渡すと保存したユーザーを取得できます。同じメールでもう一度作ると409です。

この処理をひとつの関数にまとめず、役割ごとに分けるのがこの例の中心です。まず作成リクエストを追い、その後に設定・起動・検証を説明します。細かなlint設定は後半の折りたたみで確認できます。

## 全体像：どこに何を書くか

```text
go-clean/
├── cmd/api/main.go            起動と、各処理の組み立て
├── internal/
│   ├── domain/user/           名前・メール・IDのルール
│   ├── usecase/               ユーザーを作成・取得する手順
│   ├── adapter/handler/       HTTPのJSONと業務処理の間の変換
│   ├── adapter/repository/    業務処理が必要とする保存操作のSQL実装
│   └── infra/                 環境変数、DB接続、ログ
├── db/migrations/             テーブルを作る・戻すSQL
├── api/openapi.yaml           公開するAPIの仕様
├── setup/                    設定台帳、網羅性の照合表、出典
├── .agents/skills/setup/      設定を質問して反映するスキル
├── scripts/                  設定の反映と検証
└── Makefile                  準備・起動・テストの入口
```

**domain**は「正しいユーザーとは何か」を定義する層、**usecase**は「どういう手順で作成するか」を定義する層です。HTTPやSQLに合わせた処理は**adapter**へ置きます。**infra**はDB接続などを作る土台で、`cmd/api/main.go`が必要なオブジェクトを組み立てます。

作成時の呼び出しは次の順です。

```text
HTTP → handler → usecase → ユーザーの検証
                       → 重複確認 → DBへ保存 → handlerからJSON応答
```

一方、ソースコードのimportは内側へ向けます。usecaseはPostgreSQLのrepositoryをimportせず、保存操作のinterfaceだけを知っています。実際にDBを使うことと、DBの実装にコードが依存することを分けるのが、クリーンアーキテクチャの要点です。この分離により、業務処理をDBなしでテストできます。

## 1. HTTPの入力を業務処理へ渡す

`internal/adapter/handler/router.go`が、URLを処理へ振り分けます。

```go
func NewRouter(users *UserHandler) http.Handler {
	gin.SetMode(gin.ReleaseMode) // 起動時のデバッグ出力を止める。ログは logRequest で slog に出す

	r := gin.New()
	r.HandleMethodNotAllowed = true
	r.Use(recoverPanic, logRequest)

	r.GET("/healthz", func(c *gin.Context) { c.Status(http.StatusOK) })

	r.POST("/users", users.Create)
	r.GET("/users/:id", users.Get)

	return r
}
```

`gin.New()`へ独自のpanic回復とリクエストログを付けています。`POST /users`は`UserHandler.Create`、`GET /users/:id`は`UserHandler.Get`へ進みます。`/healthz`は本文なしの200を返すHTTPプロセスの応答確認で、起動後のDB疎通を検査するものではありません。

作成時は`internal/adapter/handler/user.go`で、JSONをusecaseの入力へ詰め替えます。

```go
func (h *UserHandler) Create(c *gin.Context) {
	var req createUserRequest
	if err := decodeJSON(c, &req); err != nil {
		writeError(c, err)
		return
	}

	out, err := h.users.Create(c.Request.Context(), usecase.CreateUserInput{Name: req.Name, Email: req.Email})
	if err != nil {
		writeError(c, err)
		return
	}

	c.JSON(http.StatusCreated, newUserResponse(out))
}
```

ここでは名前やメールの正しさを判断しません。HTTPのリクエストを読むことと、結果をHTTPへ戻すことを担当します。DBや業務ルールが変わっても、HTTPの変換と切り分けて確認できるためです。

## 2. 名前・メールのルールをdomainで守る

`internal/domain/user/user.go`は、名前の前後の空白を除き、空の名前と50文字を超える名前を拒否します。

```go
const maxNameLength = 50

// User はユーザーエンティティ。フィールドを非公開にし、不正な状態で生成できないようにする。
type User struct {
	id        ID
	name      string
	email     Email
	createdAt time.Time
}

// New は不変条件を検証してユーザーを生成する。
func New(name string, email Email, now time.Time) (*User, error) {
	name = strings.TrimSpace(name)
	if err := validateName(name); err != nil {
		return nil, err
	}

	return &User{id: NewID(), name: name, email: email, createdAt: now}, nil
}
```
```go
func validateName(name string) error {
	if name == "" || utf8.RuneCountInString(name) > maxNameLength {
		return ErrInvalidName
	}

	return nil
}
```

`"  Taro  "`は`"Taro"`となり、空白だけなら`ErrInvalidName`です。文字数はバイト数ではなく`utf8.RuneCountInString`で数えます。フィールドを非公開にし、生成関数とgetterを通して使うため、不正な名前をそのまま保存処理へ流しにくくしています。

メールは`internal/domain/user/email.go`で検証します。

```go
func NewEmail(s string) (Email, error) {
	addr, err := mail.ParseAddress(s)
	if err != nil || addr.Address != s {
		return "", ErrInvalidEmail
	}

	return Email(strings.ToLower(s)), nil
}
```

メールの解析が成功し、解析結果と入力が一致するときだけ受け入れ、小文字へそろえます。`TARO@example.com`は`taro@example.com`になり、表示名を含む`Taro <taro@example.com>`は拒否します。IDは`internal/domain/user/id.go`の標準パッケージ`uuid`で生成・解析します。

DBからの読み出しでは、新規入力用の`New`ではなく`Reconstruct`で保存済みユーザーを復元します。また、`Email`と`ID`は直接キャストできる型なので、新規入力は必ず検証用の関数を通してください。domainにJSONタグやSQLの知識を持たせず、外部との形式変換はadapterへ置きます。

## 3. usecaseで作成手順を決める

作成には「メールが登録済みか確認する」「ユーザーを保存する」という操作が必要です。`internal/usecase/port.go`は、その操作をinterfaceで定義します。

```go
// UserRepository はユーザーの永続化を担う port。
type UserRepository interface {
	Create(ctx context.Context, u *user.User) error
	FindByID(ctx context.Context, id user.ID) (*user.User, error) // 見つからない場合は user.ErrNotFound
	ExistsByEmail(ctx context.Context, email user.Email) (bool, error)
}

// TxManager は fn を1トランザクション内で実行する。fn が error を返すとロールバックする。
type TxManager interface {
	Do(ctx context.Context, fn func(ctx context.Context) error) error
}
```

このinterfaceをここでは**port**と呼びます。usecaseが必要な操作を定義し、外側のrepositoryが実装します。interfaceを使う側で定義する方針は[Goのレビュー指針](https://go.dev/wiki/CodeReviewComments#interfaces)にも沿っています。

`internal/usecase/user.go`の`Create`は、domainで入力を検証してから、重複確認と保存を1トランザクションにまとめます。

```go
func (uc *UserUsecase) Create(ctx context.Context, in CreateUserInput) (*UserOutput, error) {
	email, err := user.NewEmail(in.Email)
	if err != nil {
		return nil, err
	}

	u, err := user.New(in.Name, email, uc.now())
	if err != nil {
		return nil, err
	}

	txErr := uc.tx.Do(ctx, func(ctx context.Context) error {
		exists, err := uc.repo.ExistsByEmail(ctx, email)
		if err != nil {
			return fmt.Errorf("exists by email: %w", err)
		}

		if exists {
			return user.ErrEmailAlreadyExists
		}

		if err := uc.repo.Create(ctx, u); err != nil {
			return fmt.Errorf("create user: %w", err)
		}

		return nil
	})
	if txErr != nil {
		return nil, txErr
	}

	return newUserOutput(u), nil
}
```

重複があれば保存せず`ErrEmailAlreadyExists`を返します。保存に失敗した場合は、`%w`で元のエラーに処理の文脈を加えます。handlerは`errors.Is`で元の種類を判定できます。時刻は`now`という関数から受け取るため、テストでは時刻を固定できます。

取得の`Get`は、`ParseID`でIDを検証してから`FindByID`を呼びます。どちらの処理もdomainを`UserOutput`へ詰め替えて返し、domainの内部構造をHTTPへ直接公開しません。

## 4. repositoryで同じトランザクションを使う

`internal/adapter/repository/tx.go`の`Do`がトランザクションを開始し、contextへ入れてusecaseの処理を呼びます。成功ならcommit、エラーやpanicならrollbackです。すでにトランザクションがある場合はそこへ合流し、独立した入れ子やsavepointは作りません。

各SQLは、`internal/adapter/repository/db.go`の次の関数から接続を受け取ります。

```go
func conn(ctx context.Context, db *sql.DB) querier { //nolint:ireturn // *sql.DB と *sql.Tx を同じ型で扱うため
	if tx, ok := ctx.Value(txKey{}).(*sql.Tx); ok {
		return tx
	}

	return db
}
```

contextにトランザクションがあればそれを使い、なければ通常のDB接続を使います。このため、同じcontextを受け取った重複確認とINSERTが同じトランザクションへ参加できます。repositoryで`r.db`へ直接SQLを発行すると、この関係を壊すので避けます。

ただし、トランザクションで囲むだけでは、同時リクエストのメール重複を防ぎ切れません。保存時の最終的な保証は`db/migrations/000001_create_users.up.sql`にあります。

```sql
CREATE TABLE users (
    id         UUID         PRIMARY KEY,
    name       VARCHAR(50)  NOT NULL,
    email      VARCHAR(254) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ  NOT NULL
);
```

`PRIMARY KEY`はIDの重複を、`UNIQUE`はメールの重複を防ぎます。repositoryはINSERTの一意制約違反（SQLSTATE `23505`）を`ErrEmailAlreadyExists`へ変換するため、同時作成で重複した場合もHTTPには409を返せます。制約自体の意味は[PostgreSQLの説明](https://www.postgresql.org/docs/16/ddl-constraints.html)を参照してください。

## 5. HTTPの応答へ戻し、起動時に組み立てる

`internal/adapter/handler/error.go`が、業務側のエラーをHTTPステータスへ変換します。

```go
var errorMappings = []struct {
	target error
	status int
	code   string
}{
	{errInvalidJSON, http.StatusBadRequest, "invalid_request"},
	{user.ErrInvalidID, http.StatusBadRequest, codeInvalidArgument},
	{user.ErrInvalidName, http.StatusBadRequest, codeInvalidArgument},
	{user.ErrInvalidEmail, http.StatusBadRequest, codeInvalidArgument},
	{user.ErrNotFound, http.StatusNotFound, "not_found"},
	{user.ErrEmailAlreadyExists, http.StatusConflict, "already_exists"},
}
```

不正な名前・メール・IDなら400、未登録IDなら404、メール重複なら409です。対応表にないエラーは詳細をログへ残し、HTTPには500と一般的なメッセージを返します。新しいドメインエラーを追加するときは、この表とOpenAPIの応答を一緒に確認します。

最後に、`cmd/api/main.go`が実装同士をつなぎます。この組み立てをDI（依存性の注入）と呼びます。

```go
	txManager := repository.NewTxManager(db)
	userRepo := repository.NewUserRepository(db)
	userHandler := handler.NewUserHandler(usecase.NewUserUsecase(userRepo, txManager))
```

usecaseが受け取るinterfaceの実体は、ここで渡したPostgreSQLのrepositoryです。DIフレームワークを使わず、この数行を読めば何をつないだか分かる構成にしています。`internal/usecase/fake_test.go`では同じinterfaceへフェイクを渡すため、DBを起動せず正常・重複・保存失敗を検証できます。

## 設定する値を確認する

最初に決めるのはGoのモジュール名とDB接続先です。その後、必要なら待受ポート・接続数・タイムアウト・開発規約を調整します。setupはこれらをJSONの台帳と照合して反映します。

### 起動時の環境変数

初回のサンプルは`.env.example`です。API本体が使う4項目を置き、検証専用のAPI_BASE_URLは省略しています。

```dotenv
APP_ADDR=:8080
DB_PORT=5432
DATABASE_URL=postgres://app:app@localhost:5432/app?sslmode=disable
LOG_LEVEL=info
```

`Makefile`が`.env`を読み、その値を`make run`やマイグレーションへ渡します。Goプログラム自身は`.env`を読まないため、バイナリを直接実行するときは環境変数を別に渡します。

| 項目 | 意味と、変更・省略した場合の動作 |
| --- | --- |
| `APP_ADDR` | APIが待ち受けるアドレス。省略・空文字なら`:8080`。ローカルPCからだけ使うなら`127.0.0.1:8080`にする |
| `DATABASE_URL` | APIとmigrateが使うPostgreSQL接続先。必須で、未設定なら起動しない。ホスト・ポート・ユーザー・パスワード・DB名を含む |
| `DB_PORT` | 同梱ComposeのDBをホスト側へ公開するポート。省略・空文字なら5432。変更したら同梱DB用の`DATABASE_URL`のポートも合わせる |
| `LOG_LEVEL` | 出力するJSONログの下限。debug/info/warn/errorから選ぶ。省略・空文字はinfo。アプリは不正値もinfoへ戻すが、setupでは入力ミスとして拒否する |
| `API_BASE_URL` | make smokeの接続先。省略時は`http://127.0.0.1:8080`。APIの待受を変えた場合は、検証先も合わせる。通常は.envに追加せず、検証時の環境変数で渡してもよい |

### PostgreSQLの起動とデータ保存

`compose.yaml`の設定は次のとおりです。

```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: app
      POSTGRES_PASSWORD: app
      POSTGRES_DB: app
    ports:
      - "${DB_PORT:-5432}:5432"
    volumes:
      - db-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app -d app"]
      interval: 2s
      timeout: 3s
      retries: 15

volumes:
  db-data:
```

`postgres:16-alpine`でDBを起動し、初期ユーザー・パスワード・DB名を`app`にします。`ports`がホストの`DB_PORT`からコンテナ内の5432へ接続を転送し、`db-data`がDBファイルを保持します。停止してもボリュームは残るため、次回も同じデータを使えます。

`healthcheck.test`は接続準備の確認、`interval`は確認間隔、`timeout`は1回の期限、`retries`は失敗回数です。`make db-up`はこの確認が成功するまで待ちます。ユーザーやDB名を変更するなら接続URLと確認コマンドも合わせます。ただし既存ボリュームのユーザー・パスワードは、この初期化用設定の変更だけでは更新されません。

### DB接続数と待ち時間

`internal/infra/database/database.go`では、定数を次の呼び出しへ渡しています。

```go
const (
	maxOpenConns    = 25
	maxIdleConns    = 25
	connMaxLifetime = 5 * time.Minute
	pingTimeout     = 5 * time.Second
)
```
```go
	db.SetMaxOpenConns(maxOpenConns)
	db.SetMaxIdleConns(maxIdleConns)
	db.SetConnMaxLifetime(connMaxLifetime)
	ctx, cancel := context.WithTimeout(ctx, pingTimeout)
```

`maxOpenConns`は開く接続の上限、`maxIdleConns`は再利用のため保持する待機接続の上限です。25同士なので、最大25接続を開き、使用後も最大25接続を残せます。前者の0は上限なし、後者の0は待機接続を残さない意味になるため、同じ0でも動作が違います。

`connMaxLifetime`は接続を再利用する期間、`pingTimeout`は起動時の疎通確認の期限です。期限内にDBへ接続できなければ、APIの起動を止めます。[database/sqlの接続プール](https://pkg.go.dev/database/sql#DB.SetMaxOpenConns)がこれらの値を使います。

### HTTPの待ち時間と本文サイズ

`cmd/api/main.go`は、HTTPサーバーと終了処理の期限を決めます。

```go
const (
	readHeaderTimeout = 5 * time.Second
	readTimeout       = 10 * time.Second
	writeTimeout      = 10 * time.Second
	idleTimeout       = 60 * time.Second
	shutdownTimeout   = 10 * time.Second
)
```
```go
	srv := &http.Server{
		Addr:              cfg.Addr,
		Handler:           handler.NewRouter(userHandler),
		ReadHeaderTimeout: readHeaderTimeout,
		ReadTimeout:       readTimeout,
		WriteTimeout:      writeTimeout,
		IdleTimeout:       idleTimeout,
	}
```
```go
	shutdownCtx, cancel := context.WithTimeout(context.Background(), shutdownTimeout)
	defer cancel()

	if err := srv.Shutdown(shutdownCtx); err != nil {
		return fmt.Errorf("shutdown server: %w", err)
	}
```

ヘッダー読み取りは5秒、本文を含む読み取りと応答書き込みは10秒、次のリクエストを待つ時間は60秒です。終了シグナルを受けたら最大10秒、処理中リクエストの終了を待ちます。無制限に接続を待たないための設定ですが、長時間処理を追加する場合はその処理に合わせて見直します。[net/http.Server](https://pkg.go.dev/net/http#Server)の各期限に対応します。

`internal/adapter/handler/json.go`は、JSONの読み取り方法も決めています。

```go
const maxBodyBytes = 1 << 20

func decodeJSON(c *gin.Context, dst any) error {
	dec := json.NewDecoder(http.MaxBytesReader(c.Writer, c.Request.Body, maxBodyBytes))
	dec.DisallowUnknownFields()

	if err := dec.Decode(dst); err != nil {
		return fmt.Errorf("%w: %w", errInvalidJSON, err)
	}

	return nil
}
```

`1 << 20`は1MiBです。`MaxBytesReader`が読み取りを制限し、`DisallowUnknownFields`がDTOにない項目を拒否します。一方、最初のJSONの後に別のJSONが続くかは検査していません。

接続数25や各秒数について、負荷測定に基づく採用理由は配布元に記録されていません。ここでは具体的な動作を説明し、利用先に対する最適値とは扱いません。

## setup：JSONに何を保存し、どこへ反映するか

setupには、全設定を記録する台帳と、利用者の回答を保存するファイルがあります。全設定を台帳へ載せることと、毎回すべて質問することを分けています。

| ファイル | 保存する内容 | 作成・更新のタイミング |
| --- | --- | --- |
| `setup/settings.catalog.json` | 設定の意味、型、参照先、重要度、分類理由、変更可否、未設定時の扱い | 配布側が管理する。利用者の秘密情報は保存しない |
| `setup/coverage.json` | 台帳に含むキーと設定ファイルの範囲 | 配布側が管理する。checkが実ファイルからの抽出結果と照合する |
| `setup-answers.json` | 最終値、確認状態、開始時の値、ファイルのハッシュ | initで利用者ごとに生成する。回答を記入して保存する |
| `.env`・Goソース・各設定ファイル | APIや開発ツールが実際に読む値 | applyで反映する。APIは回答JSONを直接読まない |

台帳は318項目です。起動設定、Compose、DBプール、HTTP期限、lint、エディター、API検証先、バージョン、API・DB契約まで含めています。そのうち178項目はsetupから変更でき、140項目は初期設定では維持します。後者にはバージョン、依存方向の制約、権限、API・DB契約などがあり、単に台帳から除外するのではなく、変更できない理由を記録しています。新しい設定が実ファイルへ追加され、台帳にない場合はcheckが失敗します。未使用のOSS機能の全APIまでを対象にするものではありません。

最初に質問範囲を選びます。

| 選択 | 質問する範囲 |
| --- | --- |
| 重要のみ / important | モジュール名、DB接続URLの2項目 |
| 重要＋普通 / normal | 上記に待受・DBポート、同梱DBの初期資格情報、DB接続数を加えた9項目 |
| すべて / advanced | ログ、HTTP期限、lint・エディター・API検証先を含む変更可能な178項目 |

「すべて」でも、変更不可の項目に回答を要求しません。細かな規約は関連項目をまとめて提示し、現在値を維持する選択もできます。範囲外の項目は`retained`（現在値を維持）と記録し、利用者が値を確認した`confirmed`とは区別します。

### 回答してから適用する

ZIP展開先で`$setup`を指定すると、`.agents/skills/setup/SKILL.md`がこの手順を案内します。CLIだけで行う場合も同じ操作です。準備方法は次の「導入と使用」を先に実施してください。

```sh
python3 scripts/setup.py init --level important --out setup-answers.json
python3 scripts/setup.py list --answers setup-answers.json --group runtime
```

生成したJSONで、希望する設定値と、その値を確認した記録を変更します。次は2項目の抜粋です。他のキーと、開始時の値・ハッシュは残してください。

```json
{
  "databaseTarget": "local",
  "settings": {
    "module": "github.com/acme/user-api",
    "DATABASE_URL": "postgres://app:app@localhost:5432/app?sslmode=disable"
  },
  "reviews": {
    "module": {
      "status": "confirmed",
      "value": "github.com/acme/user-api"
    },
    "DATABASE_URL": {
      "status": "confirmed",
      "value": "postgres://app:app@localhost:5432/app?sslmode=disable"
    }
  }
}
```

`databaseTarget`は同梱DBならlocal、既存DBならexternalです。未回答では適用できません。既存DBではComposeとDB_PORTを、元の値と理由を添えたnot-applicable（非該当）として維持できます。

`settings`と`reviews.value`が一致しなければ、確認後に値が変わったものとして拒否します。未回答も拒否します。範囲外を変更したい場合は、その項目を追加で確認して`confirmed`へ変えます。

```sh
python3 scripts/setup.py validate --answers setup-answers.json
python3 scripts/setup.py plan --answers setup-answers.json
python3 scripts/setup.py apply --answers setup-answers.json
python3 scripts/setup.py check
```

planは変更ファイルと設定値の差分を示します。DB接続URLとComposeのパスワードは画面に出しません。内容を確認してからapplyします。モジュール名はGoのimportとlintの自プロジェクト参照も連動して変え、ほかの設定は台帳の参照先へ反映します。変更したGoファイルはgofmtで整形します。

回答開始後に対象ファイルが手編集されていたら、古い回答を適用せず停止します。その場合は差分を確認し、現在値から別名の回答ファイルを作り直します。適用後の再設定もinitから始めます。途中の書き込み・整形に失敗した場合は変更済みファイルを復元しますが、プロセスの強制終了までの復元は保証しません。

setupは値の型、確認状態、対象範囲、接続数と整形幅の整合を検査します。各OSSの全設定組み合わせを保証するものではないため、適用後には`make check`も必要です。DBの起動やマイグレーションはapplyの処理に含めません。既存DBへ接続する場合は、同梱DBの初期化設定を変更せず、そのDBの管理手順に従います。

## 導入と使用

### 1. ZIPを展開して準備する

以下はmacOSまたはLinuxのBash/zsh向けです。Go 1.27.1、DockerとCompose v2、Make、Bash、curl、Perl、Python 3（3.10以上、venv・pipが使えるもの）を用意します。Goの依存はgo.mod/go.sum、setupの依存はrequirements-setup.txtで固定しています。掲載サイトのNode.js環境は不要です。

ZIPを任意の作業場所へ展開し、`go-clean/`をプロジェクトとして開きます。以降はすべてそのディレクトリから実行します。

```sh
cd go-clean
go mod download
make tools
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements-setup.txt
python3 scripts/setup.py check
```

各準備が成功してから次へ進みます。Goの自動取得、固定ツールの導入、Python依存の導入には初回のネットワーク接続が必要です。Pythonの[仮想環境](https://docs.python.org/3/library/venv.html)はAPI本体と切り離し、PyYAML 6.0.3だけを導入します。別ターミナルでもsetupを使うときは`source .venv/bin/activate`を実行してください。

### 2. 初期設定する

`$setup`、または前述のCLIで設定を保存・適用します。最小構成を手動で試す場合だけ、代わりに次を実行します。setup適用済みならこのコピーは不要です。

```sh
make rename MODULE=github.com/acme/user-api
cp .env.example .env
```

setupが扱う.envは引用符なしの`KEY=value`形式です。コメントと未知のキーは保持します。特殊文字を含むパスワードは接続URL内でエンコードし、シェル展開式は使いません。

### 3. DBとAPIを起動する

同梱の開発用DBを選んだ場合に実行します。

```sh
make db-up
make migrate-up
make run
```

DB準備・マイグレーションが失敗したらAPIを起動しません。APIは初期設定では`http://localhost:8080`で応答します。外部の既存DBを選んだ場合は`make db-up`を使わず、マイグレーションの要否もそのDBの管理者・管理手順に合わせます。

### 4. 作成して、返ったIDで取得する

別ターミナルから次を実行します。待受ポートを変更した場合はURLも合わせます。

```sh
curl -i -X POST http://localhost:8080/users   -H 'Content-Type: application/json'   -d '{"name":"  Taro  ","email":"TARO@example.com"}'
```

成功すると201と次の形式のJSONが返ります。これは応答形式の例で、IDと作成日時は実行ごとに変わります。

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Taro",
  "email": "taro@example.com",
  "created_at": "2026-10-19T10:00:00Z"
}
```

返った`id`を変数へ入れて取得します。

```sh
USER_ID='550e8400-e29b-41d4-a716-446655440000' # 実際に返ったIDへ置き換える
curl -i "http://localhost:8080/users/$USER_ID"
```

200で同じユーザーが返れば、保存と取得ができています。作成を同じメールで繰り返すと409になります。終了はAPIのターミナルでCtrl+C、その後`make db-down`です。DBの停止だけでは保存データは消えません。

## 制約と、利用先で必要な確認

このサンプルには認証・認可がありません。`app:app`、TLS無効、ホストへ公開するDBポートはローカル開発用です。公開運用では資格情報・アクセス制限・TLSを整えます。回答JSONと.envには秘密情報が含まれ得るため、Git・ZIP・Issueへ含めません。

名前の50文字制限はdomain・DB・OpenAPIにありますが、メールの254文字上限はDB側だけです。長いメールがdomainの解析を通るとINSERTが失敗し、500になる可能性があります。名前の上限やエラーコードなどは公開API・DB契約と合わせる必要があるため、setupでは維持します。

JSONの読み取り上限・未知フィールド拒否は実装されていますが、末尾に別のJSONが続くかの検査はありません。OpenAPIも内部エラー500や実装上の全制限を網羅していないため、利用先でAPI契約を決める際に照合してください。

## 開発規約の設定を詳しく見る

基本の流れを理解した後、必要な箇所だけ開いてください。ここでは、配布している設定を親キー付きで示し、どういう検査や整形へつながるかを説明します。個別の数値・全ルールの採用理由が配布元に記録されていない箇所は、現在のチーム規約として示し、一般的な最適値とは扱いません。

<details>
<summary>lintの標準セットと追加ルール</summary>

```yaml
linters:
  default: standard
```

```yaml
linters:
  enable:
    - asciicheck  # 識別子に ASCII 以外を使わない
    - bodyclose  # HTTP レスポンスの Body を閉じる
    - canonicalheader  # HTTP ヘッダー名を正規形で書く
    - containedctx  # 構造体に context を持たせない
    - copyloopvar  # 不要な v := v
    - depguard  # 依存方向（docs/architecture.md）
    - dogsled  # 捨てる戻り値（_）を並べすぎない
    - dupl  # 重複コード
    - dupword  # 同じ単語の連続
    - durationcheck  # Duration どうしを掛けない
    - embeddedstructfieldcheck  # 埋め込みフィールドの後に空行
    - err113  # エラーは定義済みのものを返す
    - errname  # ErrXxx / XxxError の命名
    - errorlint  # %w ラップと errors.Is の徹底
    - exhaustive  # 列挙型の switch を網羅する
    - fatcontext  # ループ内で ctx を上書きし続けない
    - forbidigo  # fmt.Print / log.Print を禁止し slog に統一
    - forcetypeassert  # ok を受け取らない型アサーション
    - funcorder  # 型 → コンストラクタ → 公開 → 非公開の並び順
    - gochecknoinits  # init を使わず main で DI する
    - gocognit  # 関数の複雑さの上限
    - goconst  # 繰り返す文字列は定数に
    - gocritic  # 同じ意味の書き方を 1 つに揃える
    - godox  # TODO / FIXME を残さない
    - gomoddirectives  # go.mod の replace などを制限
    - gomodguard_v2  # 外部モジュールは許可したものだけ
    - gosec  # セキュリティ
    - gosmopolitan  # 文字列リテラルは英語
    - iface  # interface の重複・未使用メソッド
    - inamedparam  # interface のメソッド引数に名前を付ける
    - interfacebloat  # interface のメソッド数の上限
    - intrange  # for i := range n
    - iotamixing  # iota の const ブロックに別の定数を混ぜない
    - ireturn  # コンストラクタは struct を返す
    - lll  # 行長の上限
    - makezero  # 長さ付き make に append しない
    - mirror  # 不要な []byte / string 変換
    - misspell
    - mnd  # マジックナンバー
    - modernize  # 新しい言語機能・標準ライブラリで書く
    - musttag  # JSON にする構造体にタグを付ける
    - nestif  # if のネストを浅く
    - nilerr  # err を握りつぶさない
    - nilnil  # return nil, nil を書かない
    - noctx  # HTTP リクエストに context を渡す
    - nolintlint  # nolint に対象と理由を書く
    - nonamedreturns  # 名前付きの戻り値を使わない
    - nosprintfhostport  # host:port は net.JoinHostPort で組み立てる
    - paralleltest  # テストで t.Parallel() を呼ぶ
    - perfsprint  # 不要な fmt.Sprintf
    - reassign  # 他パッケージの変数を書き換えない
    - recvcheck  # レシーバをポインタか値に揃える
    - revive  # 命名と書き方の統一
    - rowserrcheck  # rows.Err() を確認する
    - sloglint  # log/slog の書き方
    - sqlclosecheck  # Rows / Stmt を閉じる
    - tagalign  # 構造体タグの順序と位置を揃える
    - tagliatelle  # JSON タグは snake_case
    - testableexamples  # Example に Output コメントを書く
    - thelper  # テストヘルパーで t.Helper() を呼ぶ
    - tparallel  # t.Parallel() の呼び方を揃える
    - unconvert  # 不要な型変換
    - unqueryvet  # SELECT * / N+1 / トランザクションの閉じ忘れ
    - usestdlibvars  # http.MethodGet などの定数を使う
    - usetesting  # テストでは t.Setenv / t.Context などを使う
    - whitespace  # ブロック先頭・末尾の不要な空行
    - wrapcheck  # 外部パッケージのエラーは包んで返す
    - wsl_v5  # ブロックや return の前後の空行
```

`default: standard`が標準セット、`enable`が追加する検査です。depguardはimportの依存方向、forbidigoは使ってはいけない呼び出しを検査します。この2つはsetupで無効にできません。その他の追加ルールも、下表の意味を確認した上で調整し、`make check`を実行します。

| ルール | 何を検査するか |
| --- | --- |
| `asciicheck` | 識別子に ASCII 以外を使わない |
| `bodyclose` | HTTP レスポンスの Body を閉じる |
| `canonicalheader` | HTTP ヘッダー名を正規形で書く |
| `containedctx` | 構造体に context を持たせない |
| `copyloopvar` | 不要な v := v |
| `depguard` | 依存方向（docs/architecture.md） |
| `dogsled` | 捨てる戻り値（_）を並べすぎない |
| `dupl` | 重複コード |
| `dupword` | 同じ単語の連続 |
| `durationcheck` | Duration どうしを掛けない |
| `embeddedstructfieldcheck` | 埋め込みフィールドの後に空行 |
| `err113` | エラーは定義済みのものを返す |
| `errname` | ErrXxx / XxxError の命名 |
| `errorlint` | %w ラップと errors.Is の徹底 |
| `exhaustive` | 列挙型の switch を網羅する |
| `fatcontext` | ループ内で ctx を上書きし続けない |
| `forbidigo` | fmt.Print / log.Print を禁止し slog に統一 |
| `forcetypeassert` | ok を受け取らない型アサーション |
| `funcorder` | 型 → コンストラクタ → 公開 → 非公開の並び順 |
| `gochecknoinits` | init を使わず main で DI する |
| `gocognit` | 関数の複雑さの上限 |
| `goconst` | 繰り返す文字列は定数に |
| `gocritic` | 同じ意味の書き方を 1 つに揃える |
| `godox` | 作業メモを残した箇所を検査する |
| `gomoddirectives` | go.mod の replace などを制限 |
| `gomodguard_v2` | 外部モジュールは許可したものだけ |
| `gosec` | セキュリティ |
| `gosmopolitan` | 文字列リテラルは英語 |
| `iface` | interface の重複・未使用メソッド |
| `inamedparam` | interface のメソッド引数に名前を付ける |
| `interfacebloat` | interface のメソッド数の上限 |
| `intrange` | for i := range n |
| `iotamixing` | iota の const ブロックに別の定数を混ぜない |
| `ireturn` | コンストラクタは struct を返す |
| `lll` | 行長の上限 |
| `makezero` | 長さ付き make に append しない |
| `mirror` | 不要な []byte / string 変換 |
| `misspell` | 英語の綴りの揺れを検査する。 |
| `mnd` | マジックナンバー |
| `modernize` | 新しい言語機能・標準ライブラリで書く |
| `musttag` | JSON にする構造体にタグを付ける |
| `nestif` | if のネストを浅く |
| `nilerr` | err を握りつぶさない |
| `nilnil` | return nil, nil を書かない |
| `noctx` | HTTP リクエストに context を渡す |
| `nolintlint` | nolint に対象と理由を書く |
| `nonamedreturns` | 名前付きの戻り値を使わない |
| `nosprintfhostport` | host:port は net.JoinHostPort で組み立てる |
| `paralleltest` | テストで t.Parallel() を呼ぶ |
| `perfsprint` | 不要な fmt.Sprintf |
| `reassign` | 他パッケージの変数を書き換えない |
| `recvcheck` | レシーバをポインタか値に揃える |
| `revive` | 命名と書き方の統一 |
| `rowserrcheck` | rows.Err() を確認する |
| `sloglint` | log/slog の書き方 |
| `sqlclosecheck` | Rows / Stmt を閉じる |
| `tagalign` | 構造体タグの順序と位置を揃える |
| `tagliatelle` | JSON タグは snake_case |
| `testableexamples` | Example に Output コメントを書く |
| `thelper` | テストヘルパーで t.Helper() を呼ぶ |
| `tparallel` | t.Parallel() の呼び方を揃える |
| `unconvert` | 不要な型変換 |
| `unqueryvet` | SELECT * / N+1 / トランザクションの閉じ忘れ |
| `usestdlibvars` | http.MethodGet などの定数を使う |
| `usetesting` | テストでは t.Setenv / t.Context などを使う |
| `whitespace` | ブロック先頭・末尾の不要な空行 |
| `wrapcheck` | 外部パッケージのエラーは包んで返す |
| `wsl_v5` | ブロックや return の前後の空行 |

</details>
<details>
<summary>lintの個別設定：depguard</summary>

`.golangci.yml`の該当箇所です。

```yaml
linters:
  settings:
    depguard:
      rules:
        domain:
          list-mode: strict
          files:
            - "**/internal/domain/**"
          allow:
            - $gostd
            - example.com/go-clean/internal/domain
          deny:
            - pkg: database/sql
              desc: "domain は永続化を知らない"
            - pkg: net/http
              desc: "domain は HTTP を知らない"

        usecase:
          list-mode: strict
          files:
            - "**/internal/usecase/**"
          allow:
            - $gostd
            - example.com/go-clean/internal/domain
            - example.com/go-clean/internal/usecase
          deny:
            - pkg: database/sql
              desc: "usecase は port(interface) 経由で永続化する"
            - pkg: net/http
              desc: "usecase は HTTP を知らない"

        nolog:
          list-mode: lax
          files:
            - "**/internal/domain/**"
            - "**/internal/usecase/**"
            - "**/internal/adapter/**"
            - "!**/internal/adapter/handler/**"
          deny:
            - pkg: log/slog
              desc: "ログは handler の writeError でだけ出す。エラーは %w で包んで返す"

        nodir:
          list-mode: lax
          files:
            - $all
          deny:
            - pkg: example.com/go-clean/pkg
              desc: "pkg/ ディレクトリを作らない。置き場所は層で決める"
            - pkg: example.com/go-clean/internal/helper
              desc: "helper パッケージを作らない。置き場所は層で決める"
            - pkg: example.com/go-clean/internal/shared
              desc: "shared パッケージを作らない。置き場所は層で決める"

        adapter:
          list-mode: lax
          files:
            - "**/internal/adapter/**"
          deny:
            - pkg: example.com/go-clean/internal/adapter
              desc: "adapter 同士は依存しない（つなぐのは cmd の DI）"
            - pkg: example.com/go-clean/internal/infra
              desc: "adapter は infra に依存しない（必要なものは cmd から注入で受け取る）"

        handler:
          list-mode: lax
          files:
            - "**/internal/adapter/handler/**"
          deny:
            - pkg: database/sql
              desc: "handler は DB を直接触らない"

        repository:
          list-mode: lax
          files:
            - "**/internal/adapter/repository/**"
          deny:
            - pkg: net/http
              desc: "repository は HTTP を知らない"
            - pkg: github.com/gin-gonic/gin
              desc: "repository は HTTP を知らない"

        infra:
          list-mode: lax
          files:
            - "**/internal/infra/**"
          deny:
            - pkg: example.com/go-clean/internal/domain
              desc: "infra は技術的な土台のみ。ビジネスロジックに依存しない"
            - pkg: example.com/go-clean/internal/usecase
              desc: "infra は技術的な土台のみ。ビジネスロジックに依存しない"
            - pkg: example.com/go-clean/internal/adapter
              desc: "infra は adapter に依存しない"
```

filesが対象ファイル、allow/denyが許可・禁止するimport。list-modeが判定方式を決め、descが違反時の説明になる。

domainとusecaseは標準ライブラリを許可しつつ、SQL・HTTPを明示的に禁止します。adapter同士、adapterからinfra、infraから業務層へのimportも別ルールで禁止します。nologは内側のログを制限し、nodirは曖昧な共通パッケージを増やさないための規約です。モジュール名を変えると、allow/deny内の自プロジェクト参照は連動して変わります。

</details>
<details>
<summary>lintの個別設定：copyloopvar</summary>

`.golangci.yml`の該当箇所です。

```yaml
linters:
  settings:
    copyloopvar:
      check-alias: true
```

check-aliasはループ変数を別名に写した場合も不要なコピーとして調べる。

</details>
<details>
<summary>lintの個別設定：dupl</summary>

`.golangci.yml`の該当箇所です。

```yaml
linters:
  settings:
    dupl:
      threshold: 75
```

thresholdは重複コードとして報告するトークン数の境界。小さいほど短い重複も拾う。

</details>
<details>
<summary>lintの個別設定：embeddedstructfieldcheck</summary>

`.golangci.yml`の該当箇所です。

```yaml
linters:
  settings:
    embeddedstructfieldcheck:
      empty-line: true
```

empty-lineは埋め込みフィールドと通常フィールドの間の空行を要求する。

</details>
<details>
<summary>lintの個別設定：errcheck</summary>

`.golangci.yml`の該当箇所です。

```yaml
linters:
  settings:
    errcheck:
      check-blank: true  # _ に代入して捨てるエラーも検出する
```

check-blankはエラーを_に代入して捨てた場合も検査する。

</details>
<details>
<summary>lintの個別設定：exhaustive</summary>

`.golangci.yml`の該当箇所です。

```yaml
linters:
  settings:
    exhaustive:
      check:
        - switch
        - map
      default-signifies-exhaustive: true
```

checkでswitch/mapを対象にし、default-signifies-exhaustiveでdefault節を網羅済みと扱う。

</details>
<details>
<summary>lintの個別設定：forbidigo</summary>

`.golangci.yml`の該当箇所です。

```yaml
linters:
  settings:
    forbidigo:
      analyze-types: true  # 型で判定する（r.db が *sql.DB かどうか）
      forbid:
        - pattern: ^fmt\.Print.*$
          msg: ログは log/slog を使う
        - pattern: ^log\.(Print|Fatal|Panic).*$
          msg: ログは log/slog を使う
        - pattern: ^print(ln)?$
          msg: ログは log/slog を使う
        - pattern: ^sql\.DB\.(Exec|Query|QueryRow)Context$
          msg: repository は conn(ctx, r.db) 経由で DB にアクセスする（トランザクションに自動で参加するため）
        - pattern: ^gin\.H$
          msg: レスポンスは dto.go の構造体で返す
        - pattern: ^gin\.Context\.(Bind|ShouldBind|MustBind)\w*$
          msg: リクエストの JSON は decodeJSON で読む（未知のフィールドの拒否とサイズの上限のため）
        - pattern: ^gin\.Default$
          msg: gin.New を使う（ログとパニック回復は自前のミドルウェアで行う）
        - pattern: ^time\.Now$
          msg: 現在時刻は usecase の now フィールドから受け取る
        - pattern: ^context\.(Background|TODO)$
          msg: 呼び出し元から受け取った ctx を使う
        - pattern: ^os\.(Getenv|LookupEnv|Environ)$
          msg: 環境変数は infra/config でだけ読む
        - pattern: ^sql\.Open$
          msg: DB 接続は infra/database でだけ作る
        - pattern: ^http\.DefaultClient$
          msg: http.Client は cmd で作ってコンストラクタで受け取る
        - pattern: ^usecase\.New\w+$
          msg: usecase の生成（DI）は cmd/api/main.go でだけ行う
        - pattern: ^user\.User$  # 集約を足したら、そのエンティティのパターンと exclusions の 1 行を足す
          msg: 他の集約は ID だけで参照する（user.User）
        - pattern: ^usecase\.\w+Usecase\.[A-Z]\w*$  # XxxUsecase のメソッド呼び出し（フィールドは小文字なので対象外）
          msg: usecase から他の usecase を呼ばない。必要なデータは port から取り、共通の処理は domain へ寄せる
```

patternに一致する呼び出しを禁止し、msgを診断に出す。analyze-typesは同名の関数を型で区別する。

</details>
<details>
<summary>lintの個別設定：funcorder</summary>

`.golangci.yml`の該当箇所です。

```yaml
linters:
  settings:
    funcorder:
      function: true  # 公開関数を非公開関数より前に置く
```

functionは公開関数を非公開関数より前へ置く並び順の検査を有効にする。

</details>
<details>
<summary>lintの個別設定：gocognit</summary>

`.golangci.yml`の該当箇所です。

```yaml
linters:
  settings:
    gocognit:
      min-complexity: 15
```

min-complexity以上の認知的複雑度を持つ関数を報告する。深い分岐を分割する目安になる。

</details>
<details>
<summary>lintの個別設定：gocritic</summary>

`.golangci.yml`の該当箇所です。

```yaml
linters:
  settings:
    gocritic:
      enabled-tags:
        - style
        - diagnostic
      enabled-checks:  # performance タグのうち、読みやすさも上がるもの
        - appendCombine
        - equalFold
        - preferFprint
      disabled-checks:
        - unnamedResult  # nonamedreturns と逆のルールなので無効にする
        - sloppyReassign  # defer で参照する名前付き err を := で隠してしまう
```

enabled-tagsとenabled-checksで採用する指摘、disabled-checksで重複・矛盾する指摘を指定する。

</details>
<details>
<summary>lintの個別設定：godox</summary>

`.golangci.yml`の該当箇所です。

```yaml
linters:
  settings:
    godox:
      keywords:
        - TODO
        - BUG
        - FIXME
        - HACK
        - XXX
```

keywordsに挙げた作業メモをコードに残すと報告する。未完了の修正を持ち込まないための設定。

</details>
<details>
<summary>lintの個別設定：gomoddirectives</summary>

`.golangci.yml`の該当箇所です。

```yaml
linters:
  settings:
    gomoddirectives:
      go-debug-forbidden: true
      toolchain-forbidden: true  # Go のバージョンは go ディレクティブだけで決める
      tool-forbidden: true  # ツールは Makefile で固定する
```

go.modに許可しないディレクティブを指定する。ツールやGo版を複数箇所で管理しないために使う。

</details>
<details>
<summary>lintの個別設定：gomodguard_v2</summary>

`.golangci.yml`の該当箇所です。

```yaml
linters:
  settings:
    gomodguard_v2:
      allowed:
        - module: github.com/jackc/pgx/v5
        - module: github.com/gin-gonic/gin
```

allowedは直接依存として採用する外部モジュールの一覧。他のモジュール追加をレビュー対象にする。

</details>
<details>
<summary>lintの個別設定：govet</summary>

`.golangci.yml`の該当箇所です。

```yaml
linters:
  settings:
    govet:
      enable-all: true
      disable:
        - fieldalignment
```

enable-allですべての解析を有効にし、disableでこのテンプレートに採用しない解析を除外する。

</details>
<details>
<summary>lintの個別設定：iface</summary>

`.golangci.yml`の該当箇所です。

```yaml
linters:
  settings:
    iface:
      enable:
        - identical
        - unused
        - unusedmethod
```

enableは同形interface、未使用interface、未使用メソッドの検査を選ぶ。

</details>
<details>
<summary>lintの個別設定：ireturn</summary>

`.golangci.yml`の該当箇所です。

```yaml
linters:
  settings:
    ireturn:
      allow:
        - error
        - empty
        - stdlib
```

allowはinterfaceを返してよい型の分類。errorや標準ライブラリのinterface等を例外にする。

</details>
<details>
<summary>lintの個別設定：lll</summary>

`.golangci.yml`の該当箇所です。

```yaml
linters:
  settings:
    lll:
      line-length: 120
      tab-width: 4  # golines の tab-len と揃える
```

line-lengthは行長の上限、tab-widthはタブを何文字と数えるか。golinesの整形とそろえる。

</details>
<details>
<summary>lintの個別設定：misspell</summary>

`.golangci.yml`の該当箇所です。

```yaml
linters:
  settings:
    misspell:
      locale: US
```

localeは綴りの基準。USでは米国英語へそろえる。

</details>
<details>
<summary>lintの個別設定：nestif</summary>

`.golangci.yml`の該当箇所です。

```yaml
linters:
  settings:
    nestif:
      min-complexity: 4
```

min-complexity以上の入れ子になったifを報告し、分岐の分割を促す。

</details>
<details>
<summary>lintの個別設定：nilnil</summary>

`.golangci.yml`の該当箇所です。

```yaml
linters:
  settings:
    nilnil:
      detect-opposite: true  # エラーと一緒に有効な値を返さない
```

detect-oppositeはnilと有効値の組み合わせに加え、値とエラーを同時に返す逆の組み合わせも検査する。

</details>
<details>
<summary>lintの個別設定：nolintlint</summary>

`.golangci.yml`の該当箇所です。

```yaml
linters:
  settings:
    nolintlint:
      allow-unused: false
      require-explanation: true
      require-specific: true
```

allow-unusedは不要な抑制、require-explanationは理由、require-specificは対象linterの指定を検査する。

</details>
<details>
<summary>lintの個別設定：perfsprint</summary>

`.golangci.yml`の該当箇所です。

```yaml
linters:
  settings:
    perfsprint:
      err-error: true
```

err-errorはfmt.Sprintfでエラーを文字列化する箇所も簡潔な書き方にできるか調べる。

</details>
<details>
<summary>lintの個別設定：reassign</summary>

`.golangci.yml`の該当箇所です。

```yaml
linters:
  settings:
    reassign:
      patterns:
        - ".*"
```

patternsに一致する他パッケージの変数への再代入を報告する。.*は全名を対象にする。

</details>
<details>
<summary>lintの個別設定：revive</summary>

`.golangci.yml`の該当箇所です。

```yaml
linters:
  settings:
    revive:
      rules:
        - name: argument-limit
          arguments:
            - 5
        - name: blank-imports
        - name: bool-literal-in-expr
        - name: call-to-gc
        - name: confusing-naming
        - name: context-as-argument
        - name: deep-exit
        - name: defer
        - name: early-return
          arguments:
            - allow-jump
        - name: empty-block
        - name: enforce-map-style
          arguments:
            - literal
        - name: enforce-slice-style
          arguments:
            - literal
        - name: error-return
        - name: exported
          arguments:
            - check-private-receivers
        - name: filename-format
          arguments:
            - "^[_a-z][_a-z0-9]*\\.go$"
        - name: forbidden-call-in-wg-go
        - name: function-result-limit
          arguments:
            - 3
        - name: get-return
        - name: identical-ifelseif-branches
        - name: identical-ifelseif-conditions
        - name: identical-switch-branches
        - name: identical-switch-conditions
        - name: if-return
        - name: import-alias-naming
        - name: increment-decrement
        - name: indent-error-flow
        - name: inefficient-map-lookup
        - name: marshal-receiver
        - name: modifies-value-receiver
        - name: multiline-if-init
        - name: nested-structs
        - name: package-directory-mismatch
        - name: package-naming
        - name: receiver-naming
          arguments:
            - max-length: 2
        - name: redundant-import-alias
        - name: redundant-test-main-exit
        - name: struct-tag
        - name: superfluous-else
        - name: time-date
        - name: time-equal
        - name: time-naming
        - name: unconditional-recursion
        - name: unexported-naming
        - name: unexported-return
        - name: unnecessary-if
        - name: unnecessary-stmt
        - name: unsecure-url-scheme
        - name: unused-parameter
        - name: unused-receiver
        - name: use-any
        - name: use-slices-concat
        - name: use-slices-sort
        - name: useless-fallthrough
        - name: var-declaration
        - name: var-naming
```

rulesのnameで検査を選び、argumentsでその検査の許容範囲を指定する。ルール名と引数は対で扱う。

引数を持つルールでは、argument-limitの5が引数数、function-result-limitの3が戻り値数、receiver-namingの2がレシーバ名の長さの上限です。filename-formatはファイル名の正規表現です。exportedは非公開レシーバの公開メソッドもコメント検査へ含め、early-returnのallow-jumpはジャンプ文で分岐を抜ける形を許します。残りのnameは、このテンプレートが採用する命名・不要処理・誤用の検査を選びます。

</details>
<details>
<summary>lintの個別設定：sloglint</summary>

`.golangci.yml`の該当箇所です。

```yaml
linters:
  settings:
    sloglint:
      kv-only: true
      key-naming-case: snake
      static-msg: true
      context: scope
      forbidden-keys:
        - time
        - level
        - msg
        - source
      msg-style: lowercased
```

構造化ログのキーと値の書式を統一する。kv-onlyはキー値形式、contextはcontextがある範囲での使用、forbidden-keysは標準フィールドとの衝突防止。

key-naming-caseのsnakeはキーをsnake_caseへそろえ、static-msgはメッセージを固定文字列にします。msg-styleのlowercasedはメッセージを小文字始まりに統一します。ログ標準のtime/level/msg/sourceを任意キーとして上書きしません。

</details>
<details>
<summary>lintの個別設定：staticcheck</summary>

`.golangci.yml`の該当箇所です。

```yaml
linters:
  settings:
    staticcheck:
      checks:
        - all  # v1 の staticcheck / stylecheck / gosimple を含む
        - -ST1000  # パッケージコメントは必須にしない
```

checksで解析セットを指定する。allを使い、-ST1000だけ除いてパッケージコメントを必須にしない。

</details>
<details>
<summary>lintの個別設定：tagliatelle</summary>

`.golangci.yml`の該当箇所です。

```yaml
linters:
  settings:
    tagliatelle:
      case:
        rules:
          json: snake
        use-field-name: true  # タグ名をフィールド名の snake_case と一致させる
```

case.rules.jsonはJSONタグの命名、use-field-nameはGoフィールド名との対応を検査する。snakeはsnake_case。

</details>
<details>
<summary>lintの個別設定：unqueryvet</summary>

`.golangci.yml`の該当箇所です。

```yaml
linters:
  settings:
    unqueryvet:
      check-n1: true
      check-tx-leaks: true
```

check-n1はN+1の疑い、check-tx-leaksはトランザクションの閉じ忘れを検査する。

</details>
<details>
<summary>lintの個別設定：unused</summary>

`.golangci.yml`の該当箇所です。

```yaml
linters:
  settings:
    unused:
      field-writes-are-uses: false  # 書き込むだけのフィールドも未使用とみなす
```

field-writes-are-usesは書き込むだけのフィールドを使用済みと数えるかを決める。falseでは未使用のまま扱う。

</details>
<details>
<summary>lintの個別設定：usestdlibvars</summary>

`.golangci.yml`の該当箇所です。

```yaml
linters:
  settings:
    usestdlibvars:
      time-month: true
      time-layout: true
      crypto-hash: true
      default-rpc-path: true
      sql-isolation-level: true
      tls-signature-scheme: true
      constant-kind: true
      time-date-month: true
```

各項目は曜日・時刻書式・暗号方式・HTTP等の定数を標準ライブラリの名前へそろえる検査を選ぶ。

time-month/time-date-monthは月、time-layoutは時刻書式、crypto-hashはハッシュ、default-rpc-pathはRPCの既定パス、sql-isolation-levelは分離レベル、tls-signature-schemeはTLS署名方式、constant-kindは定数の種類について名前付き定数の利用を促します。

</details>
<details>
<summary>lintの個別設定：usetesting</summary>

`.golangci.yml`の該当箇所です。

```yaml
linters:
  settings:
    usetesting:
      context-background: true
      context-todo: true
      os-temp-dir: true
```

各項目はテストのcontextや一時領域にtestingパッケージのAPIを使う検査を選ぶ。

</details>
<details>
<summary>lintの個別設定：wrapcheck</summary>

`.golangci.yml`の該当箇所です。

```yaml
linters:
  settings:
    wrapcheck:
      ignore-package-globs:
        - example.com/go-clean/*
```

ignore-package-globsに一致する自プロジェクトのエラーは再ラップを要求せず、外部境界のエラーへ文脈を加える。

</details>
<details>
<summary>lintの個別設定：wsl_v5</summary>

`.golangci.yml`の該当箇所です。

```yaml
linters:
  settings:
    wsl_v5:
      allow-first-in-block: true
      allow-whole-block: false
      branch-max-lines: 2
      case-max-lines: 3  # 4 行以上の case の後に空行
      enable:
        - assign-expr  # 式の直後に代入を詰めない
```

空行を置く条件と許す省略を指定する。行数しきい値は短い分岐と長い分岐を区別する。

allow-first-in-blockはブロック先頭の密着を許し、allow-whole-blockはブロック全体の空行省略を許すかを決めます。branch-max-linesとcase-max-linesは、分岐やcaseの後に空行を要求する境界です。assign-exprは式の直後へ代入を詰める書き方を検査します。

</details>
<details>
<summary>lintから除外する条件</summary>

```yaml
linters:
  exclusions:
    generated: lax
    # comments プリセットは使わない（公開識別子のドキュメントコメントを必須にするため）
    presets:
      - common-false-positives
      - legacy
      - std-error-handling
    rules:
      - path: _test\.go
        linters:
          - dupl
          - err113
          - forbidigo  # Example テストでは fmt.Println を使う
          - goconst
          - gosmopolitan  # テストのケース名は日本語で書く
      - path-except: internal/adapter/repository/  # conn 経由のルールは repository だけに適用する
        linters:
          - forbidigo
        text: conn\(ctx, r\.db\)
      - path: internal/adapter/repository/tx\.go  # パニック中のロールバック失敗は返す先がないのでログに残す
        linters: [depguard]
        text: ログは handler の writeError
      - path-except: internal/(domain|usecase|adapter/repository)/
        linters: [forbidigo]
        text: 現在時刻は usecase の now
      - path: internal/usecase/
        linters: [forbidigo]
        text: 現在時刻は usecase の now
        source: 'now:\s+time\.Now'  # コンストラクタで now の既定値を入れる行だけは許す
      - path: cmd/
        linters: [forbidigo]
        text: 呼び出し元から受け取った ctx|http\.Client は cmd|usecase の生成
      - path: internal/infra/config/
        linters: [forbidigo]
        text: 環境変数は infra/config
      - path: internal/infra/database/
        linters: [forbidigo]
        text: DB 接続は infra/database
      - path-except: internal/domain/  # 他の集約の参照は domain だけで止める
        linters: [forbidigo]
        text: 他の集約は ID だけで参照する
      - path: internal/domain/user/  # 自分の集約のエンティティは使ってよい
        linters: [forbidigo]
        text: ID だけで参照する（user\.User）
      - path-except: internal/usecase/  # usecase を呼ばないルールは usecase の中だけに適用する
        linters:
          - forbidigo
        text: usecase から他の usecase を呼ばない
    paths:
      - third_party$
      - builtin$
      - examples$
```

`generated: lax`は生成コードの扱い、`presets`は既知の誤検出への対処です。commentsのpresetは使わず、公開識別子のコメント検査を残しています。

`rules`では、テストの重複・日本語名・例示出力を許す例外、repositoryにだけ適用するconn経由のDBアクセス制限、panic中のrollback失敗だけログを許す例外、時刻・context・環境変数・DIを各担当層で使う例外を指定します。他集約のエンティティ参照はdomain内で検査し、自集約は除きます。`path`は含める場所、`path-except`はそれ以外、`linters`は対象検査、`text`は診断、`source`は対象コードを絞ります。これらを組み合わせるので、例外は全体の検査停止にはなりません。

`paths`は第三者コードやサンプルを対象外にするパターンです。依存方向と例外の範囲は設計規約なのでsetupでは維持し、変更する場合はコードと一緒にレビューします。

</details>
<details>
<summary>整形器と、行長・import順の設定</summary>

```yaml
formatters:
  enable:
    - gofmt  # rewrite-rules による書き換えだけに使う
    - gofumpt  # gofmt より厳しい整形
    - goimports
    - golines  # 長い行の自動折り返し
  settings:
    gofmt:
      rewrite-rules:
        - pattern: interface{}
          replacement: any
        - pattern: a[b:len(a)]
          replacement: a[b:]
    gofumpt:
      extra:
        group-params: true  # 同じ型が続く引数をまとめる
    goimports:
      local-prefixes:
        - example.com/go-clean
    golines:
      max-len: 120
      tab-len: 4
  exclusions:
    generated: lax
    paths:
      - third_party$
      - builtin$
      - examples$
```

`enable`のgofmtは書き換え規則、gofumptは基本書式、goimportsはimportの整理、golinesは長い行の折り返しを担当します。gofmtのrewrite-rulesはinterface{}をanyへ、末尾までのスライスを簡潔な形へそろえます。gofumptのgroup-paramsは同型引数をまとめます。

goimportsのlocal-prefixesは自プロジェクトのimportをまとめる指定です。モジュール名の変更時にはこの参照も同期します。golinesのmax-len/tab-lenはlllのline-length/tab-widthと同じ値にし、整形した結果が直後のlintで違反にならないようにします。exclusionsは生成コードと対象外パスです。

</details>
<details>
<summary>VS Code・EditorConfig・エージェントの設定</summary>

`.vscode/settings.json`

```json
{
  "go.lintTool": "golangci-lint-v2",
  "go.lintOnSave": "package",
  "go.formatTool": "custom",
  "go.formatFlags": ["fmt", "--stdin"],
  "go.alternateTools": {
    "golangci-lint-v2": "${workspaceFolder}/bin/golangci-lint-v2.14.0",
    "customFormatter": "${workspaceFolder}/bin/golangci-lint-v2.14.0"
  },
  "[go]": {
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.organizeImports": "never"
    }
  },
  "files.eol": "\n",
  "files.insertFinalNewline": true
}
```

lintToolとalternateToolsでプロジェクト内の固定版を使います。lintOnSaveは保存したパッケージを検査し、formatTool/formatFlagsは同じ固定版のfmtへ標準入力を渡します。formatOnSaveは保存時整形、organizeImportsのneverは別処理でimport整理を二重に行わない指定です。files.eolとinsertFinalNewlineは改行を統一します。

`.vscode/extensions.json`

```json
{
  "recommendations": ["golang.go", "editorconfig.editorconfig"]
}
```

Goの言語支援とEditorConfigの拡張を推奨として表示します。APIの依存でも、自動インストールの指定でもありません。

`.editorconfig`

```ini
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true
indent_style = space
indent_size = 2

[*.go]
indent_style = tab
indent_size = 4

[Makefile]
indent_style = tab

[*.sql]
indent_size = 4

[*.md]
trim_trailing_whitespace = false
```

root=trueで上位の設定探索を止め、基本はUTF-8・LF・末尾改行・末尾空白除去・2スペースです。GoとMakefileはタブ、SQLは4スペースへ分けます。Markdownだけは末尾空白を保持し、明示改行の書式を壊さないようにします。

`.claude/settings.json`

```json
{
  "permissions": {
    "allow": [
      "Bash(make check)",
      "Bash(make test)",
      "Bash(make lint)",
      "Bash(make fmt)",
      "Bash(make build)",
      "Bash(make tools)",
      "Bash(make help)",
      "Bash(make migrate-new:*)",
      "Bash(go build:*)",
      "Bash(go vet:*)",
      "Bash(go test:*)"
    ],
    "deny": [
      "Bash(golangci-lint:*)",
      "Bash(go get:*)",
      "Bash(go mod edit -go:*)",
      "Read(./.env)",
      "Read(./.env.*)"
    ]
  }
}
```

allowは固定ツール経由のビルド・テスト等の操作、denyはグローバルlint・依存更新・Go版の単独変更・.env読取の制限です。エージェント権限は初期設定で増やさないため、setupではこの設定を維持します。Codex向けsetup本体は別の`.agents/skills/setup/SKILL.md`です。

</details>
<details>
<summary>Go・開発ツール・API/DB契約の固定範囲</summary>

`go.mod`の直接依存とGoバージョンです。間接依存も同じファイル、ダウンロードの検証情報はgo.sumにあります。

```go
module example.com/go-clean

go 1.27.1

require (
	github.com/gin-gonic/gin v1.12.0
	github.com/jackc/pgx/v5 v5.7.2
)
```

`Makefile`の固定値です。

```make
-include .env
export

MIGRATIONS_DIR := db/migrations

# golangci-lint はプロジェクトの bin/ に固定バージョンで入れる（他のプロジェクトに影響させない）
GOLANGCI_LINT_VERSION := v2.14.0
GOLANGCI_LINT := $(CURDIR)/bin/golangci-lint-$(GOLANGCI_LINT_VERSION)

# golang-migrate も同じく bin/ に固定バージョンで入れる（postgres ドライバ付きでビルドする）
MIGRATE_VERSION := v4.20.1
MIGRATE := $(CURDIR)/bin/migrate-$(MIGRATE_VERSION)
```

Go 1.27.1に合わせ、ginはhandler、pgxはDB接続で使います。golangci-lintとmigrateは指定版をプロジェクトのbinへ導入し、他プロジェクトのグローバル版へ依存しません。Goの自動取得は[ツールチェーン選択](https://go.dev/doc/toolchain)によります。

MIGRATIONS_DIRはSQLを置く場所です。APIの公開形式はapi/openapi.yaml、保存形式はdb/migrations/です。これらと名前の上限・エラーコードは台帳に含めますが、変更するならdomain、handler、repository、OpenAPI、migrationをそろえる必要があるためsetupでは維持します。

</details>

## 検証方法と結果

ZIPを別の場所へ展開し、READMEの準備に成功してから次を実行します。本物の文書・設定に異常例を追加せず、setupのテストは一時コピーで行います。

```sh
make test-setup
make check
make test
make check-deps
```

`make test-setup`は、質問範囲の選択、範囲外の設定維持、未回答・未確認変更・古い回答の拒否、実ファイルへの反映、再適用、失敗時復元、台帳にない項目の検出を確認します。`make check`はbuild・vet・単体テスト・lint、`make test`はrace検出付きのテストです。`make check-deps`は一時コピーに禁止importを追加し、depguardが実際に拒否することを確認します。

同梱DBとAPIの起動に成功したら、別ターミナルで次を実行します。専用の検証用DBでユーザーを1件作成するので、運用DBでは行いません。

```sh
API_BASE_URL=http://127.0.0.1:8080 make smoke
```

healthz、作成・取得、名前とメールの正規化、重複409、入力不正400、未知フィールド400、不正ID400、未登録ID404を確認します。全検査成功時は`API smoke: ... passed`、失敗時は非0で終了します。

確認日：2026年10月19日。環境：macOS arm64、Go 1.27.1、Docker Engine 28.4.0 / Compose 2.40.0、PostgreSQL 16、Python 3 / PyYAML 6.0.3。検証結果は次のとおりです。

| 対象 | 期待結果 | 実際の結果 |
| --- | --- | --- |
| 設定台帳・setup | 全対象の照合、設定反映、未確認変更の拒否、失敗時復元 | 318項目を照合。15テスト成功。初期状態と設定変更済みのZIPの両方で確認 |
| ZIP単体のGo検証 | build・vet・テスト・lintとrace検出が成功 | モジュール名・接続数・待ち時間・lint等を変更後、すべて成功。lintは0 issues。禁止importの検出も成功 |
| DBとAPI | 設定変更後も作成・取得と各エラー応答が一致 | DBの資格情報・DB名・公開ポートとAPIポートを変更して成功。READMEの作成・取得例、マイグレーションの巻き戻し・再適用も成功 |
| サイト・ZIP | 説明の表示、検索、取得、必要ファイルの収録 | 共通テスト35件・E2E 5件成功。実ページで導線・折りたたみ・検索・PC/モバイル表示・ZIP内容を確認 |

GitHub上のCI、人間による説明・成果物確認、同時実行時の競合、DB障害、公開運用は未確認です。自動テストの成功とは分けて扱います。

## 参考資料

- [Goのモジュール構成](https://go.dev/doc/modules/layout)
- [Goのinterface設計](https://go.dev/wiki/CodeReviewComments#interfaces)
- [net/http.Server](https://pkg.go.dev/net/http#Server)
- [database/sqlの接続プール](https://pkg.go.dev/database/sql#DB.SetMaxOpenConns)
- [golangci-lintの設定](https://golangci-lint.run/docs/linters/configuration/)
- [Docker Composeの変数補間](https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/)
- [PostgreSQL 16の制約](https://www.postgresql.org/docs/16/ddl-constraints.html)
- [Pythonの仮想環境](https://docs.python.org/3/library/venv.html)

## ダウンロード

[実装をダウンロード](/downloads/patterns/backend/architecture/go-clean.zip)
