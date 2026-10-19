# レビューのチェックリスト

レビュー対象の層の節を、上から順にすべて確かめる。

「見る方法」の列の意味は次のとおり。

- **機械**：`checker/` が検査する。出力に出た ID だけ、コードを開いて確かめる
- **lint**：`make check` が止める。`make check` が通っていれば見なくてよい。ただし、`.golangci.yml` や `//nolint` で黙らせていないかは L03 で見る
- **目視**：あなたが読んで確かめる。書いてある手順どおりに見る

「出典」の列の番号は、同じディレクトリの [rules.md](rules.md) の節番号である（「rules 2.1」は rules.md の 2.1）。指摘では、その節のルールの文を引用する。

---

## domain（`internal/domain/<集約>/`）

| ID | ルール | 見る方法 | 出典 |
|---|---|---|---|
| D01 | 構造体のフィールドは非公開にし、getter で公開する | 機械 | rules 2.1 |
| D02 | `json` / `db` タグを付けない | 機械 | rules 2.1 |
| D03 | setter（`SetXxx`）を作らず、操作の名前のメソッドにする | 機械 | rules 2.1 |
| D04 | エラーは `errors.go` に `var ( ... )` のブロックで定義し、メッセージは `"<集約>: "` で始める | 機械 | rules 2.3 |
| D05 | `id.go` は `user/id.go` と同じ形（`uuid.New`、`uuid.Parse` して `u.String()` を返す） | 機械 | rules 2.2 |
| D06 | `New` で生成し、DB からの復元は `Reconstruct` で行う | 機械 | rules 2.1 |
| D07 | 数値のフィールドは、下限と上限の両方を `New` で検証する | 機械（WARN）。上限の比較が別名の変数で書かれていると WARN になるので、コードを読んで判断する | rules 2.1 |
| D08 | 状態を変えるメソッドは、`New` と同じ規則（同じ `validateXxx`）で検証する | 目視。`New` と変更メソッドで検証関数を共有しているか。片方だけに条件を足していないか | rules 2.1 |
| D09 | 前後の空白の除去などの正規化を、検証の **前** に行う | 目視。`strings.TrimSpace` の後で検証しているか | rules 2.1 |
| D10 | `Reconstruct` では検証しない | 目視。`Reconstruct` がエラーを返したり、検証関数を呼んだりしていないか | rules 2.1 |
| D11 | 他の集約は ID だけで参照する | lint（forbidigo）。ただし `.golangci.yml` へのパターンの追加は L01 で見る | rules 2.1、2.4 |
| D12 | 現在時刻は引数で受け取る（`time.Now` を呼ばない） | lint | rules 2.1 |
| D13 | import は標準ライブラリと他の集約の domain だけ | lint（depguard） | rules 1.2、2.1 |
| D14 | 集約をまたぐ判断（「退会済みのユーザーは注文できない」など）は、判断に使う側の集約の domain の関数に置く | 目視。usecase の `if` が domain の値を見て可否を決めていたら、domain へ移すべきか考える | rules 2.1 |
| D15 | getter がスライスやマップの中身をそのまま返して、外から書き換えられるようにしていない | 目視。スライスのフィールドがあれば、コピーを返しているか | rules 2.1（フィールドを非公開にする目的） |
| D16 | 上限・下限は定数（`maxXxxLength`、`minXxx` / `maxXxx`）に置く | 目視。マジックナンバーなら mnd が止めるが、この名前だと、機械検査 M09・O08 が domain と DB・openapi を突き合わせられる | rules 2.1 |

## usecase（`internal/usecase/`）

| ID | ルール | 見る方法 | 出典 |
|---|---|---|---|
| U01 | interface は `port.go` にだけ置く | 機械 | rules 3.2 |
| U02 | 公開メソッドは domain の型を返さない（Output に詰め替える） | 機械 | rules 3.1 |
| U03 | Input / Output は domain の型を持たない | 機械 | rules 3.1 |
| U04 | 形と名前：`<動詞><集約>Input`、`<集約>Usecase`、`New<集約>Usecase` が `*<集約>Usecase` を返す、戻り値は `*<集約>Output` / `*<集約>ListOutput` | 機械（WARN） | rules 3.1 |
| U05 | 複数の書き込み、または「読んでから書く」処理は `TxManager.Do` で囲む | 機械。ただし機械はメソッドの名前（`Create` / `Update` / `Delete` など）で書き込みを判定する。`Register` のような名前の書き込みは目視で確かめる | rules 3.3 |
| U06 | 外部サービスの呼び出しは `TxManager.Do` の外（コミットの後）で行う | 機械 | rules 3.3 |
| U07 | port から返ったエラーは `fmt.Errorf("<何をしていたか>: %w", err)` で包む | 目視。`%w` を使っているか、メッセージが「何をしていたか」になっているか。domain の検証エラーと `ParseID` のエラーはそのまま返してよい | rules 3.5、10 |
| U08 | 同時に更新されて上書きされては困る「読んでから書く」処理は、`FOR UPDATE` で取得する | 目視。更新系の処理で、読んだ値をもとに書いているなら、同時実行で何が起きるかを考える。必要か決められなければ「確認」で聞く | rules 3.3 |
| U09 | 一覧は `<集約>ListOutput` で包み、件数の既定値と上限は定数に置いて範囲外を丸める（エラーにしない） | 目視 | rules 3.1 |
| U10 | usecase で独自のエラーを定義しない | 機械 | rules 3.1 |
| U11 | 他の usecase を呼ばない。他の集約のデータはその集約の port から取る | lint（forbidigo） | rules 3.4 |
| U12 | 現在時刻は `uc.now()` から取る | lint（forbidigo） | rules 3.1 |
| U13 | port には、使うメソッドだけを足す。足したメソッドは `fake_test.go` の fake にも足す | 目視（使っていないメソッドは lint の iface が止める） | rules 3.2 |
| U14 | ビジネス判断を usecase に書かない（値の検証や状態による可否は domain） | 目視。usecase の `if` が、入力値の範囲や entity の状態を見て判断していたら指摘する。usecase の判断は「存在するか」「重複していないか」のように port に聞くものだけ | rules 3.4 |
| U15 | 1 集約に 1 つの struct、ファイル名は `<集約>.go` | 目視 | rules 3.1 |
| U16 | 外部サービスの失敗時の扱い（コミット済みで 500 になる）を理解したうえでの実装か | 目視。送信の失敗で注文の作成自体を失敗扱いにしてよいかは仕様の問題なので、明示がなければ「確認」 | rules 3.3 |

## handler（`internal/adapter/handler/`）

| ID | ルール | 見る方法 | 出典 |
|---|---|---|---|
| H01 | ドメインエラーと、handler の `errXxx` は、すべて `errorMappings` にある（ないと 500 になる） | 機械 | rules 4 |
| H02 | `errorMappings` の code は、openapi の `Error` の code の enum にある | 機械 | rules 8 |
| H03 | usecase には `c.Request.Context()` を渡す（`*gin.Context` を渡さない） | 機械 | rules 4 |
| H04 | 成功時のステータス：作成 201、取得 200、更新 200、削除 204（本文なし） | 機械 | rules 4 |
| H05 | DTO は `dto.go` に非公開の型で置く | 機械（WARN） | rules 4 |
| H06 | エラーは必ず `writeError` に渡す（ステータスを直接書かない） | 機械 | rules 4 |
| H07 | handler にビジネス判断を書かない | 目視。handler の中の `if` が、変換と `writeError` 以外のことをしていたら指摘する（例：数量が 0 なら 400 を返す → domain の検証に移す） | rules 4 |
| H08 | 一覧は `{"<集約の複数形>": [...]}` のようにオブジェクトで包む | 目視 | rules 4 |
| H09 | クエリパラメータが整数に変換できなければ `errInvalidQuery` を返して 400 にする | 目視 | rules 4 |
| H10 | `errorMappings` のステータスが妥当（不正な入力 400、ない 404、重複 409） | 目視。新しく足した行の、エラーの意味とステータスが合っているか | rules 4 |
| H11 | handler 側の interface（`orderUsecase` など）は、使うメソッドだけを持つ | 目視（10 個を超えると interfacebloat が止める） | rules 4 |
| H12 | ルートは `router.go` に `r.GET("/xxx/:id", ...)` の形で登録する | 目視 | rules 4 |
| H13 | ミドルウェアは `func xxx(c *gin.Context)` で書き、止めるときは `c.AbortWithStatusJSON` と `errorResponse` を使う | 目視 | rules 4 |
| H14 | `gin.H` を使わない、`decodeJSON` で読む、`gin.New` を使う | lint | rules 4 |
| H15 | レスポンスに、外に出すべきでない値（パスワード、内部 ID、スタックトレース）を入れていない | 目視 | 一般的な安全性 |

## repository と外部サービスの adapter（`internal/adapter/<名前>/`）

| ID | ルール | 見る方法 | 出典 |
|---|---|---|---|
| R01 | `var _ usecase.Xxx = (*Xxx)(nil)` で port を実装していることを保証する | 機械 | rules 5、6 |
| R02 | `UPDATE` / `DELETE` は `RowsAffected()` を確かめ、0 件なら `<集約>.ErrNotFound` を返す | 機械 | rules 5 |
| R03 | 一覧の `ORDER BY` は最後に一意な列（`id`）を足す | 機械 | rules 5 |
| R04 | SQL は `const q = ...` でメソッド内に書く。キーワードは大文字。句と列は 1 行に 1 つ | 機械（WARN） | rules 5 |
| R05 | 1 行の取得で `sql.ErrNoRows` を `<集約>.ErrNotFound` に変換する | 機械 | rules 5 |
| R06 | 一意制約違反は対応するドメインエラーに、外部キー違反は参照先の集約の `ErrNotFound` に変換する | 機械 | rules 5 |
| R07 | 外部キーが 2 つ以上あるテーブルは、`pgErr.ConstraintName` でどちらの違反かを区別する | 目視。`isForeignKeyViolation` の後で、参照先ごとに違うエラーを返しているか | rules 5 |
| R08 | SQL に値を文字列で埋め込まない（`fmt.Sprintf` や `+` で組み立てない）。値は `$1` などのプレースホルダで渡す | 目視（gosec でも一部止まる）。`ORDER BY` の列を入力で切り替える場合は、許可した列名の一覧から選んでいるか | rules 5 |
| R09 | DB へのアクセスは `conn(ctx, r.db)` 経由 | lint（forbidigo） | rules 5 |
| R10 | `rows.Close()` と `rows.Err()` | lint（sqlclosecheck / rowserrcheck） | rules 5 |
| R11 | `FOR UPDATE` の取得は別メソッド（`FindByIDForUpdate`）にし、`TxManager.Do` の中で呼ぶ | 目視 | rules 3.3 |
| R12 | `Scan` した値を `Reconstruct` で復元し、型変換（`user.ID(rowID)` など）が合っている | 目視 | rules 5 |
| R13 | 外部サービスの adapter は `internal/adapter/<相手の名前>/` に置き、`http.Client` と接続先をコンストラクタで受け取り、エラーを `%w` で包む | 目視（`http.DefaultClient` と環境変数の読み込みは lint） | rules 6 |
| R14 | `querier` にメソッドを足したら、`*sql.DB` と `*sql.Tx` の両方が持つメソッドか | 目視 | rules 5 |

## DB マイグレーション（`db/migrations/`）

| ID | ルール | 見る方法 | 出典 |
|---|---|---|---|
| M01 | up と down を対で作る | 機械 | rules 7、13 |
| M02 | down は `DROP TABLE IF EXISTS <テーブル>;` だけ | 機械 | rules 7 |
| M03 | 1 つのマイグレーションで 1 つのテーブル。名前は `create_<テーブル>` | 機械（WARN） | rules 7 |
| M04 | 列はすべて `NOT NULL` | 機械 | rules 7 |
| M05 | 外部キーは `REFERENCES <テーブル> (id) ON DELETE ...` と列に書き、`ON DELETE` を省略しない | 機械 | rules 7 |
| M06 | 外部キーの列には、同じファイルで `<テーブル>_<列>_idx` のインデックスを作る | 機械 | rules 7 |
| M07 | 型は `UUID` / `VARCHAR(n)` / `INTEGER` / `TIMESTAMPTZ` | 機械（WARN）。他の型が必要な理由があれば認めてよいが、docs の型の表に足すよう提案する | rules 7 |
| M08 | `INTEGER` は `CHECK` で下限と上限を書く | 機械 | rules 7 |
| M09 | `VARCHAR(n)` と `CHECK` の範囲が、domain の定数と同じ | 機械（定数が `maxXxxLength` / `minXxx` / `maxXxx` の名前のときだけ突き合わせられる。違う名前なら目視） | rules 2.1、7 |
| M10 | `ON DELETE CASCADE` は、削除の仕様で決まった場合だけ | 目視。`CASCADE` があれば、依頼や仕様にその根拠があるか。なければ「確認」 | rules 7 |
| M11 | 適用済みのマイグレーションファイルを書き換えていない（変更は新しい番号のファイルで足す） | 目視。git があれば `git diff` で既存の番号のファイルが変わっていないか | rules 7 |
| M12 | 既存のテーブルを変えるマイグレーションは、既存の行で失敗しない（`NOT NULL` の列の追加に既定値があるか、など） | 目視 | 一般的な運用 |
| M13 | 外部キーの列名は `<集約>_id`、テーブル名は複数形の snake_case | 目視 | rules 7 |

## API 仕様（`api/openapi.yaml`）

| ID | ルール | 見る方法 | 出典 |
|---|---|---|---|
| O01 | router.go のルートと openapi の paths が一致する | 機械 | rules 8、13 |
| O02 | paths は router.go と同じ順 | 機械（WARN） | rules 8 |
| O03 | エラーレスポンスは `$ref: "#/components/responses/Error"` だけを書く | 機械 | rules 8 |
| O04 | 成功レスポンスのコードと `description`（作成成功 / 取得成功 / 更新成功 / 削除成功）、204 は `content` なし | 機械 | rules 8 |
| O05 | path パラメータの ID は `type: string` / `format: uuid` | 機械 | rules 8 |
| O06 | schemas は集約ごとに `<動詞><集約>Request` → `<集約>`、`Error` が最後 | 機械 | rules 8 |
| O07 | スキーマのプロパティ名が `dto.go` の json タグと同じ。レスポンスは全プロパティが `required`。日時は `format: date-time` | 機械 | rules 8 |
| O08 | リクエストに domain と同じ制約（`maxLength`、`minimum` / `maximum`）を書く | 機械 | rules 8 |
| O09 | `summary` は「<集約の日本語名><操作>」 | 機械は有無だけ。形は目視 | rules 8 |
| O10 | path に ID があれば 400 と 404、リクエスト本文があれば 400 を書く | 機械（WARN） | rules 8 |
| O11 | そのエンドポイントで返りうるエラーのステータスが、すべて書かれている | 目視。usecase のメソッドが返しうるエラー（domain の検証、`ParseID`、port の `ErrNotFound`、一意制約・外部キー違反の変換）を書き出し、`errorMappings` でステータスに変えて、openapi の responses と比べる。例：注文の作成は注文者がいなければ `user.ErrNotFound` で 404 | rules 8 |
| O12 | リクエストの `required` が、domain で必須のものと合っている | 目視 | rules 8 |

## lint の設定と依存（`.golangci.yml`、`go.mod`、`Makefile`）

| ID | ルール | 見る方法 | 出典 |
|---|---|---|---|
| L01 | 集約を足したら、forbidigo のパターン `^<集約>\.<エンティティ>$` と除外 `path: internal/domain/<集約>/` を足す | 機械 | rules 2.4 |
| L02 | `//nolint` で lint を黙らせない | 機械（WARN）。理由が docs に書かれた例外（`db.go` の `conn`）以外は指摘する | rules 1.2、12 |
| L03 | `.golangci.yml` を変えて lint を黙らせない | 目視。git があれば `git diff -- .golangci.yml` を読む。L01 の 2 行以外の変更（リンターを外す、`exclusions` を足す、上限を緩める、`depguard` / `forbidigo` のルールを消す）は、依頼に理由がなければ必須の指摘 | rules 1.2、12 |
| L04 | `go.mod` の `go` ディレクティブと、`Makefile` の `GOLANGCI_LINT_VERSION` / `MIGRATE_VERSION` を依頼なしに変えない | 目視（git diff） | rules 12 |
| L05 | 新しい外部ライブラリを足していない（足すなら、標準ライブラリで代わりにならないかを検討した跡がある） | 目視。`go.mod` の `require` の差分 | rules 12 |
| L06 | `util` / `common` / `helper` / `shared` パッケージ、`pkg/` ディレクトリを作らない | lint | rules 10 |

## テスト（`*_test.go`）

| ID | ルール | 見る方法 | 出典 |
|---|---|---|---|
| T01 | domain と usecase には必ずテストがある | 機械 | rules 11.1 |
| T02 | 関数名は `Test<関数>` か `Test<型>_<メソッド>` | 機械（WARN） | rules 11.2 |
| T03 | テーブル駆動で、`t.Parallel()` を呼ぶ | lint（paralleltest / tparallel） | rules 11.1 |
| T04 | `t.Run` の中は、最初に `errors.Is(err, tt.wantErr)` を `t.Fatalf` で確かめ、次に `if tt.wantErr != nil { return }` | 機械（WARN）は 1 段目だけ。2 段目の `return` は目視 | rules 11.2 |
| T05 | テーブルのフィールドは `name` → 準備 → 入力 → `want...` → `wantErr` の順 | 機械（WARN） | rules 11.2 |
| T06 | fake に入れるエンティティは、ケースごとに `Reconstruct` で作る（ケース間で共有しない） | 機械（WARN） | rules 11.2 |
| T07 | 期待値は 1 回で比べる（usecase は Output を struct で作り `*got != want`、domain は getter の比較を `||` で 1 つの `if`） | 機械（WARN） | rules 11.2 |
| T08 | domain は `package <集約>_test`、usecase は `package usecase` | 機械（WARN） | rules 11.1 |
| T09 | ケースを網羅している：正常、返しうるエラーの種類ごと、境界値（上限ちょうどと上限 + 1、下限ちょうどと下限 - 1）、repository のエラーが包まれて返ること | 目視。テスト対象のメソッドが返しうるエラーを書き出し、ケースと突き合わせる | rules 11.1 |
| T10 | 状態を変えるメソッドは、エラーのケースで状態が変わっていないことも確かめる | 目視 | rules 11.2 |
| T11 | 全ケースで同じ準備はテーブルに入れず `t.Run` の中で作る。「空なら既定値」の分岐をケースの中に作らない。「存在しない」は別の `NewID()` で表す | 目視 | rules 11.2 |
| T12 | 生成される値（ID など）は `got` から写して比べる | 目視 | rules 11.2 |
| T13 | fake は `fake_test.go` に手書きし、モック生成ツールを使わない | 目視（ツールの追加は gomodguard が止める） | rules 11.1 |
| T14 | handler と repository のテストを、規約ができる前に足していない | 目視 | rules 11.1 |
| T15 | テストが、実装の中身ではなく振る舞いを確かめている（実装を写しただけの期待値になっていない） | 目視。期待値を実装と同じ計算で作っていたら指摘する | 一般的なテストの原則 |

## DI（`cmd/api/main.go`）

| ID | ルール | 見る方法 | 出典 |
|---|---|---|---|
| C01 | 足した repository / usecase / handler のコンストラクタが `main.go` で呼ばれている | 機械（WARN） | rules 9 |
| C02 | `main.go` にロジックを書かない。生成は repository → usecase → handler の順 | 目視 | rules 9 |
| C03 | 他の集約の port を使う usecase には、その repository も渡している | 目視（渡し忘れはコンパイルで止まる） | rules 9 |

## 横断（すべての層）

| ID | ルール | 見る方法 | 出典 |
|---|---|---|---|
| X01 | エラーは `%w` で包み、`errors.Is` / `errors.As` で判定する | lint（errorlint / wrapcheck）。メッセージが「何をしていたか」になっているかは目視 | rules 10 |
| X02 | ログは handler の `writeError` でだけ出す | lint（depguard） | rules 10 |
| X03 | I/O を伴う関数は第 1 引数に `ctx`。`context.Background()` を cmd 以外で使わない | lint | rules 10 |
| X04 | ログのキーは snake_case | lint（sloglint） | rules 10 |
| X05 | 命名：`user.UserID` のような冗長な名前を避ける | 目視 | rules 10 |
| X06 | 公開する型と関数に、何をするかが分かる日本語のコメントがある | 目視 | rules 10 |
| X07 | ルールを変える変更なら、プロジェクトのルール文書と、既存のコードの同じ書き方の箇所を同じ変更で直している | 目視 | 一般的な運用 |
| X08 | 依頼されていない範囲のリファクタリングをしていない | 目視。差分の中に、依頼と関係のない変更がないか | rules 10 |
