# パターン

実装用スキル `impl` の「1. 振り分け表」の各行に対応する手順である。節の番号は振り分け表と一致させる。各節は同じ書式にそろえる。

プレースホルダは次の意味で使う。

| プレースホルダ | 意味 | 例 |
|---|---|---|
| `<noun>` | 名詞（小文字1語） | `task` |
| `<Noun>` | 名詞の先頭を大文字にしたもの | `Task` |
| `<nouns>` | 名詞の複数形 | `tasks` |
| `<verb>` | 動詞（小文字1語） | `remove` |
| `<Verb>` | 動詞の先頭を大文字にしたもの | `Remove` |
| `<verbed>` | 動詞の過去分詞（`get` は `found`） | `removed` |
| `<Field>` | エンティティの項目名 | `Due` |
| `<field>` | 項目名の先頭を小文字にしたもの | `due` |
| `<flag>` | フラグ名の小文字の snake_case | `due` |
| `<Name>` | 環境変数名から `GOCLI_` を除き、`_` で区切った語の先頭だけを大文字にしてつなげたもの | `TitleMax` |
| `<name>` | 環境変数名から `GOCLI_` を除いた小文字の snake_case | `title_max` |

どの節でも、次の3つを守る。

- 宣言の説明は rules.md CODE-10 の表の文をそのまま書く。表に無い宣言は、日本語の1文を1行に書き、句点（`。`）で終える（CODE-08）。`make arch` が違反の行に書くべき文を出すので、出たらその文に直す
- テストの件は rules.md TEST-05 の「足す件」の表の件だけを、同じ種類の件の最後に足す。件の名前と値（`Buy milk`、`Write report`、`2026-01-31`、`2026/01/31`、`one`、存在しない ID の `2`）は表のとおりにする
- テストの `args` は、位置引数、フラグ（`Flags` で定義した順）、`--json` の順に書く

## 1. サブコマンドを足す

- 使う場面：サブコマンド（動詞）を足す
- 見本：`internal/command/taskcmd/complete.go`、`internal/command/taskcmd/complete_test.go`、`internal/domain/task/service.go` の `Complete`、`internal/command/taskcmd/taskcmd.go`
- 作る・変えるファイル：

  | 順 | パス | 見本との対応 | 守るルール |
  |---|---|---|---|
  | 1 | `internal/domain/<noun>/service.go` | `Complete` メソッド | NAM-04、CODE-02、ERR-01、ASYNC-01 |
  | 2 | `internal/command/<noun>cmd/<verb>.go` | `complete.go` | STR-04、NAM-04、NAM-05、CODE-02、ERR-04、OPS-06 |
  | 3 | `internal/command/<noun>cmd/<verb>_test.go` | `complete_test.go` | TEST-01〜TEST-04 |
  | 4 | `internal/command/<noun>cmd/<noun>cmd.go` | `Commands` に `new<Verb>(svc)` を足す | STR-02 |
  | 5 | `docs/cli.md` | `make generate` | STR-07 |

- 手順：
  1. Service に `<Verb>` メソッドを足す。名前はサブコマンド名の先頭を大文字にしたものにする（NAM-04）。1件を対象にする操作は `Complete` と同じく、`s.repo.Load` → `indexOf` → 変更 → `s.repo.Save` の順に書き、操作した1件（削除なら削除する前の1件）を返す。説明は、`Get`・`Remove` なら rules.md CODE-10 の表の文（`// Remove は指定した ID の <noun> を削除し、その内容を返す。`）にする。公開するメソッドは `New...` の後、非公開の関数の前に置く（CODE-01）
  2. `complete.go` を `<verb>.go` に写し、`complete`・`Complete` を `<verb>`・`<Verb>` に置き換える。説明のコメントも置き換える（`// run<Verb> は <noun> <verb> を実行する。` など、CODE-10）。`Summary` は大文字で始まりピリオドで終えない（OPS-06）
  3. `run<Verb>` で Service の戻り値を受ける変数を `<verbed>` にする（NAM-05）。ID を受け取るなら、先頭で `<noun>.ParseID(opts.id)` を呼ぶ（ERR-04）
  4. `WriteText` の文章を `<Verbed> <noun> %d: %s\n` にする（OPS-06）。一覧を返す動詞は `list.go` を写し、`cli.WriteTable` を使う
  5. `complete_test.go` を `<verb>_test.go` に写し、`Test<Verb>` を次の4件にする（TEST-01、TEST-05）。`keeps_a_done_task_done` のような `complete` だけの件は写さない。期待値は CLI の出力の全文である

     | 件の名前 | setup | args | 期待 |
     |---|---|---|---|
     | `<verb>s_a_<noun>` | `{"<noun>", "add", "Buy milk"}` | `{"<noun>", "<verb>", "1"}` | `<Verbed> <noun> 1: Buy milk` |
     | `writes_json` | 同上 | `{"<noun>", "<verb>", "1", "--json"}` | JSON |
     | `rejects_an_id_that_is_not_a_number` | なし | `{"<noun>", "<verb>", "one"}` | 終了コード2 |
     | `reports_a_missing_<noun>` | `{"<noun>", "add", "Buy milk"}` | `{"<noun>", "<verb>", "2"}` | 終了コード3 |

  6. `<noun>cmd.go` の `Commands` に、動詞のアルファベット順で足す（STR-02）
  7. `make generate`、`make check`
- この場面で間違えやすいこと：
  - 削除を `delete`、表示を `show` と名付ける。NAM-04 の表の動詞（`remove`、`get`）を使う
  - `run<Verb>` の変数を `t` や `result` にする
  - `--json` の件や、終了コード3の件をテストに書き忘れる

## 2. 既存のサブコマンドにフラグを足す

- 使う場面：既存のサブコマンドにフラグを足す
- 見本：`internal/command/taskcmd/list.go`（`--all`）、`internal/command/taskcmd/list_test.go`、`internal/domain/task/task.go` の `Filter`
- 作る・変えるファイル：

  | 順 | パス | 見本との対応 | 守るルール |
  |---|---|---|---|
  | 1 | `internal/domain/<noun>/<noun>.go` | 一覧の絞り込みなら `Filter` に項目を足す。文字列から値に変えるなら `Parse<Field>` を足す | CODE-02、ERR-04、NAM-03 |
  | 2 | `internal/domain/<noun>/<noun>_test.go` | `Parse<Field>` を足したなら `TestParse<Field>` | TEST-01 |
  | 3 | `internal/domain/<noun>/service.go` | `List` の絞り込み、またはメソッドの引数 | CODE-02 |
  | 4 | `internal/command/<noun>cmd/<verb>.go` | `listOptions.all` と `Flags` | CODE-02、NAM-06、OPS-06 |
  | 5 | `internal/command/<noun>cmd/<verb>_test.go` | `lists_tasks_with_all` の件 | TEST-01、TEST-05 |
  | 6 | `docs/cli.md` | `make generate` | STR-07 |

- 手順：
  1. フラグ名を決める（impl の2の表）。`<verb>Options` にフラグ名の lowerCamelCase のフィールドを足し、`Flags` の中で `fs.StringVar`・`fs.BoolVar`・`fs.IntVar` のどれかで結ぶ（CODE-02）。説明は impl の2の表の文にする（大文字で始まりピリオドで終えない。OPS-06）。日付の項目なら `fs.StringVar(&opts.due, "due", "", "Due date in YYYY-MM-DD format")` である。`Flags` が無いコマンドには、`Args` の次に `Flags: func(fs *flag.FlagSet) { ... },` を足す
  2. 値を Service に渡す。一覧の絞り込みなら `Filter` の項目に入れ、それ以外は Service のメソッドの引数に足す。引数の順は `ctx`、ID、位置引数、フラグ（CODE-02）
  3. 文字列のフラグを日付や列挙に変えるなら、domain の `<noun>.go` に `Parse<Field>(s string) (<型>, error)` を足し、`run<Verb>` の先頭で呼ぶ。任意のフラグの `Parse<Field>` は、空文字列に対してゼロ値と `nil` を返す（ERR-04）。日付なら次のとおりに書く

     ```go
     // ParseDue はコマンドライン引数を Task の Due フィールドに変換する。
     // 空文字列の場合はゼロ値を返す。
     func ParseDue(s string) (time.Time, error) {
     	if s == "" {
     		return time.Time{}, nil
     	}
     	due, err := time.Parse(time.DateOnly, s)
     	if err != nil {
     		return time.Time{}, fmt.Errorf("%w: due must be a date in YYYY-MM-DD format: %q", errkind.ErrInvalid, s)
     	}
     	return due, nil
     }
     ```

  4. `<noun>_test.go` に `TestParse<Field>` を足す。件は rules.md TEST-05 の「値の種類ごとの件」の表のとおりにする。`time.Time` は `!got.Equal(tt.want)` で比べる（TEST-02）。任意の日付なら次の4件である

     ```go
     {name: "accepts_a_date", s: "2026-01-31", want: time.Date(2026, time.January, 31, 0, 0, 0, 0, time.UTC), wantErr: nil},
     {name: "returns_zero_for_an_empty_string", s: "", want: time.Time{}, wantErr: nil},
     {name: "rejects_another_format", s: "2026/01/31", want: time.Time{}, wantErr: errkind.ErrInvalid},
     {name: "rejects_a_date_that_does_not_exist", s: "2026-02-30", want: time.Time{}, wantErr: errkind.ErrInvalid},
     ```

  5. `<verb>_test.go` に次の件を足す（TEST-05）。成功の件は成功の件の最後に、`--json` の件は `--json` の件の最後に、終了コード2の件は終了コード2の件の最後に置く

     | 件の名前 | args | 期待 |
     |---|---|---|
     | `<verb>s_a_<noun>_with_<flag>`（list は `lists_<noun>s_with_<flag>`） | `{"<noun>", "<verb>", "Buy milk", "--<flag>", "<値>"}` | 成功の文章 |
     | `writes_json_with_<flag>` | 上の args の最後に `"--json"` | JSON |
     | `rejects_an_invalid_<flag>`（`Parse<Field>` で変換するフラグだけ） | `{"<noun>", "<verb>", "Buy milk", "--<flag>", "<不正な値>"}` | 終了コード2 |

  6. `make generate`、`make check`
- この場面で間違えやすいこと：
  - `fs.String` など値のポインタを返す API を使う
  - `--includeDone`、`--include_done`、`-a` のような名前にする
  - `strconv.Atoi` や `time.Parse` を command で直接呼ぶ（forbidigo の ERR-04 で落ちる）

## 3. エンティティに項目を足す

- 使う場面：記録する項目を足す（期限、優先度、メモ、タグなど）
- 見本：`internal/domain/task/task.go`（`Task`、`ParseID`、`validateTitle`）、`internal/adapter/taskstore/taskstore.go`（`record`、`toRecord`、`toTask`）、`internal/command/taskcmd/view.go`、`internal/command/taskcmd/add.go`、`internal/command/taskcmd/list.go`
- 作る・変えるファイル：

  | 順 | パス | 見本との対応 | 守るルール |
  |---|---|---|---|
  | 1 | `internal/domain/<noun>/<noun>.go` | `Task` に `<Field>` を足す。必要なら `Parse<Field>`、`validate<Field>` | PROC-02、ERR-04、CODE-04 |
  | 2 | `internal/domain/<noun>/<noun>_test.go` | `TestParse<Field>`（`Parse<Field>` を足したとき） | TEST-01 |
  | 3 | `internal/domain/<noun>/service.go` | 項目を受け取る use case（`Add` など）の引数と、エンティティへの代入 | CODE-02 |
  | 4 | `internal/adapter/<noun>store/<noun>store.go` | `record` の項目、`toRecord`、`to<Noun>` | PROC-02、STATE-01、NAM-06 |
  | 5 | `internal/adapter/<noun>store/<noun>store_test.go` | `TestLoad`・`TestSave` の期待値 | TEST-01 |
  | 6 | `internal/command/<noun>cmd/view.go` | `<noun>View` の項目、`to<Noun>View` | PROC-02、NAM-06 |
  | 7 | 項目を受け取る `<verb>.go` とそのテスト | 2 の手順でフラグを足す | CODE-02、TEST-01 |
  | 8 | 項目を表示する `<verb>.go` とそのテスト | `list.go` の `WriteText` に列を足す | OPS-06 |
  | 9 | 出力の JSON が変わる全サブコマンドのテスト | `writes_json` の件の期待値 | TEST-01 |
  | 10 | `docs/cli.md` | `make generate` | STR-07 |

- 手順：
  1. エンティティの `CreatedAt` の直前に `<Field>` を足す。`record` と `<noun>View` にも同じ位置に足す（PROC-02）。項目を add で指定するなら、2 の手順でフラグを足す（`Parse<Field>` と `TestParse<Field>` もそこにある）
  2. 任意の項目（指定しなくてよい項目）はポインタにせず、ゼロ値で「無し」を表す。`record` と `<noun>View` の `json` タグは `json:"<field の snake_case>,omitzero"` にする（CODE-04）
  3. 日付は `time.Time` で持ち、`Parse<Field>` で `time.Parse(time.DateOnly, s)` から作る（UTC の 0 時）。文章で表示するときは `view.go` に列の見出しの lowerCamelCase の名前のメソッドを足し、`.Format(time.DateOnly)`、ゼロ値なら `-` を返す（NAM-03、OPS-03、OPS-06、CODE-10）

     ```go
     // due は DUE 列に表示する文字列を返す。
     func (v taskView) due() string {
     	if v.Due.IsZero() {
     		return "-"
     	}
     	return v.Due.Format(time.DateOnly)
     }
     ```

  4. `toRecord`・`to<Noun>`・`to<Noun>View` の構造体リテラルに、項目を同じ順で足す
  5. 保存形式の `version` は変えない。古いファイルに無い項目はゼロ値で読まれる（STATE-01）
  6. 一覧の列は rules.md OPS-06 の順（`ID`、`STATUS`、足した項目、`TITLE`）にする
  7. 出力が変わった既存の件は、期待値だけを直す（件の名前・setup・args は変えない）
  8. 次の件を足す（TEST-05）。add の件は 2 の手順の表のとおりである

     | ファイル | 件の名前 | setup | args |
     |---|---|---|---|
     | `list_test.go` | `lists_<noun>s_with_<field>` | `{"<noun>", "add", "Buy milk", "--<flag>", "<値>"}`、`{"<noun>", "add", "Write report"}` | `{"<noun>", "list"}` |
     | `list_test.go` | `writes_json_with_<field>` | `{"<noun>", "add", "Buy milk", "--<flag>", "<値>"}` | `{"<noun>", "list", "--json"}` |
     | `<noun>store_test.go` | 件を足さない。`reads_<noun>s` と `writes_<noun>s` の1件目に項目の値を足す（`reads_<noun>s` の JSON の文字列は `created_at` の前で分ける。下の例） | — | — |

     日付の値は `2026-01-31`（Go では `time.Date(2026, time.January, 31, 0, 0, 0, 0, time.UTC)`、JSON では `"2026-01-31T00:00:00Z"`）を使う。`reads_<noun>s` の JSON は次のように書く

     ```go
     content: `{"version": 1, "tasks": [` +
     	`{"id": 1, "title": "Buy milk", "done": true, "due": "2026-01-31T00:00:00Z", ` +
     	`"created_at": "2026-01-02T03:04:05Z"}]}`,
     ```
  9. `make generate`、`make check`
- この場面で間違えやすいこと：
  - `*time.Time` にする、`omitempty` を付ける（`time.Time` には効かない）
  - `record` か `<noun>View` の片方に足し忘れる（archcheck の PROC-02 で落ちる）
  - 項目を `CreatedAt` の後ろに足す
  - 列のメソッドを `dueDate` と名付ける（見出しが `DUE` なら `due`。archcheck の NAM-03 で落ちる）
  - 既存の `writes_json` の件の setup を変えて項目の値を確かめる。項目の値は `writes_json_with_<field>` の件で確かめる

## 4. 名詞を足す

- 使う場面：新しい名詞のコマンド（`go-cli <noun> ...`）を作る
- 見本：`internal/domain/task/` の全ファイル、`internal/adapter/taskstore/` の全ファイル、`internal/command/taskcmd/` の `taskcmd.go`・`view.go`・最初の動詞のファイル、`internal/app/app.go`
- 作る・変えるファイル：

  | 順 | パス | 見本との対応 | 守るルール |
  |---|---|---|---|
  | 1 | `internal/domain/<noun>/<noun>.go` | `task.go`（エンティティ、`ParseID`、`validate<Field>`） | STR-03、NAM-03、PROC-02、CODE-08 |
  | 2 | `internal/domain/<noun>/<noun>_test.go` | `task_test.go` | TEST-01 |
  | 3 | `internal/domain/<noun>/repository.go` | `repository.go` | NAM-03 |
  | 4 | `internal/domain/<noun>/service.go` | `service.go`（`NewService` と最初の動詞のメソッド、`indexOf`・`nextID` のうち使うもの） | NAM-03、NAM-04 |
  | 5 | `internal/adapter/<noun>store/<noun>store.go` | `taskstore.go` | STR-03、NAM-03、STATE-01、OPS-04 |
  | 6 | `internal/adapter/<noun>store/<noun>store_test.go` | `taskstore_test.go` | TEST-01 |
  | 7 | `internal/command/<noun>cmd/view.go` | `view.go` | NAM-03、PROC-02 |
  | 8 | `internal/command/<noun>cmd/<verb>.go` と `<verb>_test.go` | 1 の手順 | STR-04、TEST-01 |
  | 9 | `internal/command/<noun>cmd/<noun>cmd.go` | `taskcmd.go` | NAM-03、NAM-06、STR-02、CODE-08 |
  | 10 | `internal/app/app.go` | `tasks := task.NewService(...)` と `Groups` | DEP-01、PROC-02、STR-02 |
  | 11 | `internal/cli/cli_test.go` | `prints_the_commands_with_help` の `Commands:` の一覧 | TEST-05 |
  | 12 | `docs/cli.md` | `make generate` | STR-07 |

- 手順：
  1. 見本のファイルを写し、`task`・`Task`・`tasks` を `<noun>`・`<Noun>`・`<nouns>` に置き換える。説明のコメントの中の名前も置き換える（CODE-10）。使わない関数（動詞が無い `Complete` など）と、使わない件（`keeps_a_done_task_done` など）は写さない。テストの値は見本と同じ `Buy milk`、`Write report` を使う（TEST-05）
  2. エンティティは `ID int` で始め、業務の項目を並べ、`CreatedAt time.Time` で終える（PROC-02）。`Done` が無い名詞の一覧には `STATUS` 列を作らない
  3. パッケージの説明は `<noun>.go`、`<noun>store.go`、`<noun>cmd.go` だけに書く（CODE-08）
  4. 保存するファイルは `<nouns>.json`、中身は `{"version": 1, "<nouns>": [...]}` にする。`document` のフィールドは `Version` と `<Nouns>` にする（STATE-01）
  5. `<noun>cmd.go` の `Group` の `Name` は `<noun>`、`Summary` は `Manage <nouns>` にする
  6. `app.go` の `New` で `<nouns> := <noun>.NewService(<noun>store.New(filepath.Join(cfg.dataDir, "<nouns>.json")), env.Now)` を作り、`Groups` にパッケージ名のアルファベット順で `<noun>cmd.New(<nouns>)` を足す
     `cli_test.go` の `prints_the_commands_with_help` の期待値の `Commands:` にも、`  <noun>  Manage <nouns>` を同じ順で足す（件は足さない。TEST-05）
  7. 2つ目以降の動詞は 1 の手順で足す。`make generate`、`make check`
- この場面で間違えやすいこと：
  - domain だけ作り、adapter と command を作らない（STR-02）
  - 別の名詞のパッケージ（`domain/task`）を import して使い回す（DEP-03）
  - テストの道具や共通の型を新しいパッケージに作る（STR-01、STR-05）

## 5. 共通化する

- 使う場面：複数のコマンドで同じ処理を使う（共通化）
- 見本：`internal/command/taskcmd/view.go`（`toTaskView`、`status`）、`internal/domain/task/task.go`（`ParseID`）、`internal/domain/task/service.go`（`indexOf`）、`internal/cli/table.go`（`WriteTable`）
- 作る・変えるファイル：

  | 順 | パス | 見本との対応 | 守るルール |
  |---|---|---|---|
  | 1 | rules.md STR-05 の決定表で決まる1つのファイル | 上の見本のうち、同じ種類のもの | STR-05、STR-03 |
  | 2 | 共通化した処理を使う各ファイル | — | STR-05 |

- 手順：
  1. rules.md STR-05 の決定表で置き場を決める。新しいファイルやパッケージは作らない（STR-01、STR-03）
  2. 置き場のファイルに非公開の関数（`internal/cli` なら公開の関数）として書き、使う側から呼ぶ
  3. 決定表のどの行にも当たらなければ、実装せずに報告する
  4. `make check`
- この場面で間違えやすいこと：
  - `util.go`、`helpers.go`、`internal/common/` を作る
  - 名詞の業務の知識（タスクの状態など）を `internal/cli` に置く

## 6. エラーの種類と終了コードを足す

- 使う場面：新しいエラーの種類・終了コードを足す
- 見本：`internal/errkind/errkind.go`、`internal/cli/exit.go`
- 作る・変えるファイル：

  | 順 | パス | 見本との対応 | 守るルール |
  |---|---|---|---|
  | 1 | `internal/errkind/errkind.go` | `ErrNotFound` | ERR-01、NAM-03 |
  | 2 | `internal/cli/exit.go` | `ExitNotFound`、`ExitCodes`、`exitCode` | ERR-01、OPS-05、PROC-02 |
  | 3 | エラーを返す domain のファイルとそのサブコマンドのテスト | `indexOf` | ERR-01、TEST-01 |
  | 4 | `docs/cli.md` | `make generate` | STR-07 |

- 手順：
  1. `errkind.go` に `Err<Kind>` を足す。説明に終了コードを書く
  2. `exit.go` に `Exit<Kind>` 定数（次の番号）を足し、`ExitCodes` と `exitCode` の `switch` に足す
  3. エラーを返す場所で `fmt.Errorf("%w: <詳細>", errkind.Err<Kind>)` を返す（ERR-01）
  4. そのコマンドのテストに、新しい終了コードの件を足す。`make generate`、`make check`
- この場面で間違えやすいこと：
  - 独自のエラー型を作る、文字列で比べる
  - 既存の終了コードの番号や意味を変える（PROC-06）

## 7. 環境変数の設定を足す

- 使う場面：環境変数で設定できるようにする
- 見本：`internal/app/config.go`（`envDataDir`、`config`、`loadConfig`、`loadDataDir`）、`internal/app/app.go`、`internal/app/app_test.go`
- 作る・変えるファイル：

  | 順 | パス | 見本との対応 | 守るルール |
  |---|---|---|---|
  | 1 | `internal/app/config.go` | `envDataDir` の定数、`config.dataDir`、`loadConfig`、`loadDataDir` | OPS-02、NAM-03、NAM-06、ERR-01、ERR-04、CODE-10 |
  | 2 | 値を受け取る組み立て関数（`NewService` など）と、それを使う処理 | `NewService(repo, now)` | OPS-02、CODE-07 |
  | 3 | `internal/app/app.go` | `task.NewService(...)` の呼び出し | OPS-02 |
  | 4 | `internal/app/app_test.go` | `reports_a_missing_data_directory` の件 | TEST-01、TEST-04、TEST-05 |
  | 5 | 値が効くサブコマンドのテスト | `env` フィールドを足した件 | TEST-04、TEST-05 |
  | 6 | `README.md` | 環境変数の表 | PROC-02 |

- 手順：
  1. `config.go` を次の形にする（OPS-02、NAM-03、CODE-10）。`GOCLI_TITLE_MAX` なら `<Name>` は `TitleMax`、フィールドは `titleMax` である。domain に同じ値の定数（`maxTitleLength`）があれば、その定数を消して値を `default<Name>` に移す
     - `env<Name> = "GOCLI_<NAME>"` を `// CLI の設定に使う環境変数を定義する。` の群の、`GOCLI_` の定数の最後（`envXDGData` の前）に足す。個別の説明は書かない
     - 群の直後に `// default<Name> は $GOCLI_<NAME> が空のときに使う値を表す。` の説明を付けて `const default<Name> = <値>` を置く
     - `config` の最後にフィールド `<name> <型>` を足す
     - `loadConfig` は、`config` のフィールドの順に `load<Name>(getenv)` を呼んでから `config{...}` を返す
     - `load<Name>` を `config.go` の最後に足す。正の整数なら次のとおりに書く

     ```go
     // loadConfig は環境変数から設定を読み取る。
     func loadConfig(getenv func(key string) string) (config, error) {
     	dataDir, err := loadDataDir(getenv)
     	if err != nil {
     		return config{}, err
     	}
     	titleMax, err := loadTitleMax(getenv)
     	if err != nil {
     		return config{}, err
     	}
     	return config{dataDir: dataDir, titleMax: titleMax}, nil
     }

     // loadTitleMax は $GOCLI_TITLE_MAX の値を返し、空なら defaultTitleMax を返す。
     func loadTitleMax(getenv func(key string) string) (int, error) {
     	value := getenv(envTitleMax)
     	if value == "" {
     		return defaultTitleMax, nil
     	}
     	n, err := strconv.Atoi(value)
     	if err != nil || n < 1 {
     		return 0, fmt.Errorf("%w: %s must be a positive integer: %q", errkind.ErrInvalid, envTitleMax, value)
     	}
     	return n, nil
     }
     ```

  2. 値は `app.New` から組み立て関数の引数で渡す（`task.NewService(repo, env.Now, cfg.<field>)`）。新しい引数は既存の引数の後ろに足し、`NewService` の説明にその引数の役割を日本語で加える（`NewService は repo にタスクを保存し、now から現在時刻を得て、titleMax 文字までのタイトルを受け付ける Service を返す。`）。Service は受け取った値を同じ名前のフィールドに持ち、`validate<Field>` には引数で渡す
  3. テストを次のとおりに足す（TEST-04、TEST-05）。環境変数はテーブルの `env map[string]string` フィールドに書き、`h.Setenv` で設定する。`env` フィールドが無いテーブルには、`name` の次（`setup` の前）に `env map[string]string` を足し、`for key, value := range tt.env { h.Setenv(key, value) }` を `h.Setup` のループの前に書く

     | ファイル | 件の名前 | env | args | 期待 |
     |---|---|---|---|---|
     | `app_test.go` | `rejects_a_<name>_that_is_not_a_number` | `{"GOCLI_<NAME>": "one"}` | `{"<noun>", "list"}` | 終了コード2 |
     | `app_test.go` | `rejects_a_<name>_of_zero` | `{"GOCLI_<NAME>": "0"}` | `{"<noun>", "list"}` | 終了コード2 |
     | 上限が効くサブコマンドの `<verb>_test.go`（上限の場合） | `accepts_a_<field>_up_to_the_<name>` | `{"GOCLI_<NAME>": "8"}`（`Buy milk` の文字数） | `{"<noun>", "add", "Buy milk"}` | 成功の文章 |
     | 同上 | `rejects_a_<field>_longer_than_the_<name>` | `{"GOCLI_<NAME>": "7"}` | `{"<noun>", "add", "Buy milk"}` | 終了コード2 |

  4. `README.md` の環境変数の表の最後に、名前・意味・既定値を足す。`make check`
- この場面で間違えやすいこと：
  - domain や command で環境変数を読む（DEP-05、OPS-02）
  - パッケージ変数に設定を入れる（CODE-01）
  - 環境変数の名前を `TITLE_MAX` や `GOCLI_TITLEMAX` にする
  - `loadConfig` の中で環境変数を直接読む、`readTitleMax` や `parseTitleMax` と名付ける（archcheck の OPS-02・NAM-03 で落ちる）
  - 既定値の場合の件（`rejects_a_title_longer_than_100_characters_by_default`）のような、表に無い件を足す

## 8. 不具合を直す・振る舞いを変える

- 使う場面：不具合を直す、既存の振る舞いを変える
- 見本：直す場所のテストファイル（`<verb>_test.go`、`<noun>_test.go`、`<noun>store_test.go`）
- 作る・変えるファイル：

  | 順 | パス | 見本との対応 | 守るルール |
  |---|---|---|---|
  | 1 | 不具合が見えるテストのファイル | テーブルに件を足す | TEST-01、TEST-02 |
  | 2 | 原因のあるファイル | — | 直す層のルール |
  | 3 | `docs/cli.md`（コマンドの説明が変わる場合） | `make generate` | STR-07 |

- 手順：
  1. 不具合を再現する件を、該当するテストのテーブルに足し、`make test` で落ちることを確かめる
  2. 原因を直し、`make check`
  3. 公開面の名前や意味が変わる場合は実装せずに報告する（PROC-06）
- この場面で間違えやすいこと：
  - 新しいテスト関数やテストファイルを作る。既存の `Test<Verb>` のテーブルに件を足す
  - 落ちるテストを消す、skip する（TOOL-03）
