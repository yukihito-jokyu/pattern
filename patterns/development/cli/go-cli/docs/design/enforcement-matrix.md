<!-- このファイルは rules_check.py が rules.md と probes.json から生成する。手で編集しない。 -->

# 強制の対応表

ルールごとに、どの仕組みで守らせているかを示す。段の強さは type > format > lint・structure・test > generator > review > doc の順である。
probe が実際に検査で落ちるかの結果は `.foundation/probe-results.json` にある（`violation_probe.py` が書く）。

## 集計（各ルールの最も強い段で数える）

| 段 | 件数 |
|---|---|
| type | 1 |
| format | 2 |
| lint | 22 |
| structure | 22 |
| test | 0 |
| generator | 0 |
| review | 5 |
| doc | 5 |

## ルールごとの対応

| ルールID | 題名 | 強制 | 仕組み | probe |
|---|---|---|---|---|
| STR-01 | Go のコードを置くディレクトリを表の8種類に限る | structure | `tools/archcheck` の STR-01（ディレクトリの許可表） | STR-01-a、STR-01-b |
| STR-02 | 新しい名詞と動詞は決まったファイル一式で足す | structure, doc | `tools/archcheck` の STR-02（名詞ごとに domain・adapter・command の3つのパッケージがそろっていること、`Commands` と `Groups` の並び）。手順は実装用スキルの patterns.md | STR-02-a |
| STR-03 | ディレクトリごとに置いてよいファイル名を決める | structure | `tools/archcheck` の STR-03 | STR-03-a |
| STR-04 | サブコマンドのファイルは5つの宣言を決まった順に持つ | structure | `tools/archcheck` の STR-04（宣言の種類・名前・順） | STR-04-a、STR-04-b |
| STR-05 | 共有したいコードは決定表の置き場に置く | review | レビュー用スキルの確認項目 | — |
| STR-06 | テストは対象の隣に置き、テスト用の道具は apptest だけにする | structure | `tools/archcheck` の STR-06（テストファイル名が同じディレクトリの `.go` ファイルと対になること）と STR-01（`internal/` に `.go` 以外を置かない） | STR-06-a |
| STR-07 | 生成物は docs/cli.md だけにし、手で編集しない | structure | `tools/clidoc -check`（`make docs-check`）が、生成し直した内容と `docs/cli.md` を比べ、違えば STR-07 で落ちる | STR-07-a |
| STR-08 | main.go は app.Run を呼んで終了するだけにする | structure | `tools/archcheck` の STR-08（`main.go` の宣言が `main` だけであること） | STR-08-a |
| DEP-01 | 層の間の import は許可表の組だけにする | structure | `tools/archcheck` の DEP-01（`architecture.md` の依存の許可表と同じ表をコードに持つ） | DEP-01-a、DEP-01-b |
| DEP-02 | パッケージが公開する名前を層ごとに決める | structure | `tools/archcheck` の DEP-02（層ごとの公開名の許可表） | DEP-02-a |
| DEP-03 | 同じ層の別の名詞のパッケージを import しない | structure | `tools/archcheck` の DEP-03 | DEP-03-a |
| DEP-04 | 外部モジュールを使わず標準ライブラリだけで書く | structure | `tools/archcheck` の DEP-04（`go.mod` の `require` を検出）。外部のパッケージを import すると `go build` も落ちる | DEP-04-a |
| DEP-05 | 副作用のある標準パッケージと関数は決まった場所でだけ使う | lint, structure | `tools/archcheck` の DEP-05（import の許可表）。関数の呼び出しは golangci-lint の forbidigo（説明が `DEP-05` で始まる） | DEP-05-a、DEP-05-b |
| DEP-06 | 依存やツールを足すときは ADR を書いて承認を得る | review | レビュー用スキルの確認項目（依存の一覧ファイルの差分） | — |
| NAM-01 | ファイル名とディレクトリ名は小文字と数字だけにする | lint, structure | golangci-lint の revive `filename-format` と `package-directory-mismatch`。ディレクトリ名は `tools/archcheck` の NAM-01 | NAM-01-a、NAM-01-b |
| NAM-02 | 識別子は MixedCaps にし、略語は全部大文字か全部小文字にする | lint | golangci-lint の revive `var-naming` | NAM-02-a |
| NAM-03 | 役割ごとの名前を表のとおりにする | lint, structure | `tools/archcheck` の NAM-03（view.go・adapter・domain の名前、view.go のメソッドと列の見出し、config.go の名前の対応）。エラーの名前は golangci-lint の errname | NAM-03-a、NAM-03-b、NAM-03-c、NAM-03-d |
| NAM-04 | サブコマンドと Service のメソッドは同じ動詞にする | structure | `tools/archcheck` の NAM-04（`Name` がファイル名と同じで、使わない動詞でなく、`run<Verb>` が `svc.<Verb>` を呼ぶ） | NAM-04-a |
| NAM-05 | 名前で型と中身が分かるようにする | lint, structure | `tools/archcheck` の NAM-05（bool の名前、`run<Verb>` の変数名）。期間は golangci-lint の revive `time-naming` | NAM-05-a、NAM-05-b |
| NAM-06 | CLI の外向きの名前の形と、変換する場所を決める | lint, structure | `tools/archcheck` の NAM-06（名詞・動詞・フラグ・位置引数・環境変数の名前）。JSON のキーは golangci-lint の tagliatelle（`snake`、`use-field-name`） | NAM-06-a、NAM-06-b |
| CODE-01 | 宣言は関数と型で書き、init とパッケージ変数と名前付きの戻り値を使わない | lint | golangci-lint の gochecknoinits、gochecknoglobals、nonamedreturns、decorder、funcorder、recvcheck | CODE-01-a、CODE-01-b、CODE-01-c |
| CODE-02 | 入力は Options のフィールドに結び、決まった形で Service に渡す | structure, review | `tools/archcheck` の CODE-02（`fs.` で呼んでよいメソッドの許可表、`&opts.<field>` への結び付け）。Service への渡し方はレビュー用スキル | CODE-02-a |
| CODE-03 | import は formatter の群分けに任せ、別名を付けない | format, lint | golangci-lint の goimports（`local-prefixes: example.com/go-cli`）と importas（`no-extra-aliases`） | CODE-03-a、CODE-03-b |
| CODE-04 | 型は any・値・UTC の time.Time で書き、append で埋めるスライスは make で作る | lint | golangci-lint の revive `use-any`、modernize、forcetypeassert、prealloc | CODE-04-a |
| CODE-05 | エラーは別の行で受け、早期 return で書き、入れ子を3段までにする | lint | golangci-lint の noinlineerr、revive `early-return`・`indent-error-flow`・`superfluous-else`・`max-control-nesting`（3）、nestif | CODE-05-a |
| CODE-06 | 引数と値のレシーバを書き換えない | lint | golangci-lint の revive `modifies-parameter`・`modifies-value-receiver`、reassign | CODE-06-a |
| CODE-07 | 関数の大きさを上限で縛る | lint | golangci-lint の funlen（50行・30文）、gocognit（15）、revive `argument-limit`（4）・`function-result-limit`（2） | CODE-07-a |
| CODE-08 | コメントは日本語の1文1行で、全部の宣言に説明を書き、パッケージの説明は1ファイルに書く | lint, structure | golangci-lint の godoclint（`require-pkg-doc`、非公開も対象にした `require-doc`、`single-pkg-doc`、`start-with-name`）、revive `exported`・`package-comments`、godox。説明を書くファイル、日本語の有無、句点、1文1行は `tools/archcheck` の CODE-08 | CODE-08-a、CODE-08-b、CODE-08-c、CODE-08-d、CODE-08-e、CODE-08-f |
| CODE-09 | 0と1以外の数値は名前の付いた定数にする | lint | golangci-lint の mnd | CODE-09-a |
| CODE-10 | 役割の決まった宣言の説明は表の文にする | structure | `tools/archcheck` の CODE-10。違反の行に、書くべき文がそのまま出る | CODE-10-a、CODE-10-b |
| ERR-01 | エラーの種類は errkind を %w で先頭に包んで表す | lint, structure | `tools/archcheck` の ERR-01（errkind を包む `fmt.Errorf` の書式が `%w: ` で始まる）。golangci-lint の err113、errorlint、errname、forbidigo（`panic`。説明が `ERR-01` で始まる） | ERR-01-a、ERR-01-b |
| ERR-02 | 外から来たエラーは1回だけ包み、モジュール内のエラーはそのまま返す | lint | golangci-lint の wrapcheck（`ignore-package-globs: example.com/go-cli/*`） | ERR-02-a |
| ERR-03 | エラーの文字列は小文字で始め、句読点で終えない | lint | golangci-lint の revive `error-strings`、staticcheck ST1005 | ERR-03-a |
| ERR-04 | 入力は決定表の場所で変換・検証する | lint, review | golangci-lint の forbidigo（`strconv`・`time.Parse` の呼び出し。説明が `ERR-04` で始まる）。どの層で検証したかはレビュー用スキルで確かめる | ERR-04-a |
| STATE-01 | 状態は決定表の置き場だけに持つ | review | レビュー用スキルの確認項目。パッケージ変数は CODE-01、ファイル操作の場所は DEP-05 が機械で止める | — |
| ASYNC-01 | 並行処理を書かず、context は第1引数で受け取る | lint, structure | `tools/archcheck` の ASYNC-01（`go` 文とチャネル型）。golangci-lint の revive `context-as-argument`、containedctx、contextcheck。`sync` の import は DEP-05 | ASYNC-01-a、ASYNC-01-b |
| OPS-01 | ログを書かず、出力は cli だけが書く | lint | golangci-lint の forbidigo（説明が `OPS-01` で始まる）。`log` の import は DEP-05 | OPS-01-a |
| OPS-02 | 設定は GOCLI_ の環境変数を config.go で読む | lint, structure | `tools/archcheck` の OPS-02（文字列リテラルの中の `GOCLI_` の場所、`loadConfig` が呼ぶ `load<Name>` の順）と NAM-03（定数・関数・フィールドの名前と群の置き場）。`os.Getenv` は golangci-lint の forbidigo（説明が `DEP-05` で始まる） | OPS-02-a、OPS-02-b、OPS-02-c |
| OPS-03 | 時刻は UTC の秒単位で持ち、コメントを除くコードと表示の文字列は ASCII にする | structure, test | `tools/archcheck` の OPS-03（コメントを除くコードの ASCII 以外の文字）。時刻の形はサブコマンドのテスト（`--json` の期待値） | OPS-03-a、OPS-03-b |
| OPS-04 | データのディレクトリは 0700、ファイルは 0600 で作る | lint | golangci-lint の gosec（G301、G302、G306） | OPS-04-a |
| OPS-05 | 終了コードと出力先は cli が決め、コマンドは出力型と error を返す | type | `cli.Command.Run` の型が `func(ctx context.Context) (cli.Output, error)` で、コマンドは書き込み先と終了コードを受け取らない | OPS-05-a |
| OPS-06 | 出力の形とヘルプの文言を決まった形にする | structure, test, review | 各サブコマンドのテストが stdout の全文を比べる。`Summary` とフラグの説明の形は `tools/archcheck` の OPS-06。JSON のキーの選び方はレビュー用スキル | OPS-06-a、OPS-06-b |
| TEST-01 | 対象ごとのテストの粒度と、必須のテストを決める | structure, review | `tools/archcheck` の TEST-01（必須のテストファイルと `Test<Verb>` があること）。終了コードごとの件があるかはレビュー用スキル | TEST-01-a |
| TEST-02 | テストは並列のテーブル駆動で、got を先に書く | lint, structure | golangci-lint の testpackage、paralleltest、tparallel、thelper、usetesting、revive `time-equal`。サブテストの名前は `tools/archcheck` の TEST-02 | TEST-02-a、TEST-02-b、TEST-02-c |
| TEST-03 | テストのために偽物の型を作らない | structure | `tools/archcheck` の TEST-03（`_test.go` の型宣言） | TEST-03-a |
| TEST-04 | テストデータはテーブルに直接書き、前提は CLI の実行で作る | review | レビュー用スキルの確認項目 | — |
| TEST-05 | 足す件、件の名前、件の並び、テストの値を表のとおりにする | structure, review | 件の並びは `tools/archcheck` の TEST-05。足す件、件の名前、値、同じ種類の中での置き場、`args` の順はレビュー用スキル | TEST-05-a、TEST-05-b |
| PROC-01 | 内側の層から外側の層へ順に作る | doc | 実装用スキルの「作る順序」 | — |
| PROC-02 | 一緒に変えるファイルの組を守る | structure, review | `tools/archcheck` の PROC-02（エンティティ・`record`・`<noun>View` のフィールド名が同じ順で一致し、`ID` で始まり `CreatedAt` で終わること、各名詞の `New` が `app.go` から呼ばれること）。`docs/cli.md` は STR-07。エラーの種類と環境変数はレビュー用スキル | PROC-02-a、PROC-02-b |
| PROC-03 | Go と golangci-lint の版は決まった手順で上げる | doc | 実装用スキルの「依頼から外れる作業」と AGENTS.md | — |
| PROC-04 | ルールは ADR から順に変える | doc | AGENTS.md の「ルールを変えたいとき」 | — |
| PROC-05 | make check とチェックリストを満たしてから完了と報告する | doc | AGENTS.md の「完了の条件」と実装用スキル | — |
| PROC-06 | CLI の公開面は足すだけにし、変える・消すときは ADR を書く | review | レビュー用スキルの確認項目（`docs/cli.md` の削除行と、`json` タグ・`config.go` の定数の変更） | — |
| TOOL-01 | 整形は formatter に任せる | format | golangci-lint の gofumpt・goimports・golines（`make lint` が整形の違反を報告する） | TOOL-01-a |
| TOOL-02 | 編集後は hooks、完了前は make check を回す | doc | AGENTS.md と実装用スキル。hooks は `.claude/settings.json` と manifest の `hooks.post_edit` | — |
| TOOL-03 | 抑止コメントと保護ファイルの変更で検査を黙らせない | structure, review | `guard.py`（manifest の `guard.suppressions`）。保護ファイルの変更はレビュー用スキル | TOOL-03-a、TOOL-03-b |
| TOOL-04 | Go と golangci-lint の版を固定し、Makefile を唯一の入口にする | structure | `tools/archcheck` の TOOL-04（`go.mod` と `golangci-lint.mod` の版の行）と `make tidy-check` | TOOL-04-a |

## 機械で縛っていないルール

| ルールID | 題名 | 強制 | 機械化しない理由 |
|---|---|---|---|
| STR-05 | 共有したいコードは決定表の置き場に置く | review | どこに置くかは処理の意味（業務の知識を含むか、どの名詞のものか）で決まり、ファイルや import の字面では判定できない。新しいディレクトリを作ることは STR-01 で機械が止める |
| DEP-06 | 依存やツールを足すときは ADR を書いて承認を得る | review | 承認を得たかどうかは差分の字面からは判定できない。依存の一覧ファイルは保護ファイルなので、エージェントが編集すると hooks が確認を求める |
| STATE-01 | 状態は決定表の置き場だけに持つ | review | 保存するファイル名と JSON の形が名詞の意味に合っているかは、字面では判定できない |
| TEST-04 | テストデータはテーブルに直接書き、前提は CLI の実行で作る | review | 前提データを CLI の実行で作るべきか、ファイルで作るべきかは、テストの対象（サブコマンドか adapter か）の意味で決まる。golden ファイルの禁止は STR-06 が機械で止める |
| PROC-01 | 内側の層から外側の層へ順に作る | doc | 作った順序は最終の差分に残らない |
| PROC-03 | Go と golangci-lint の版は決まった手順で上げる | doc | 上げる時期と理由は依頼で決まり、コードからは判定できない。上げた後の版の一致は TOOL-04 が機械で確かめる |
| PROC-04 | ルールは ADR から順に変える | doc | 変えた順序と承認の有無は差分に残らない。保護ファイルの編集は hooks が確認を求める |
| PROC-05 | make check とチェックリストを満たしてから完了と報告する | doc | 報告の中身とチェックリストの確認は差分に残らない |
| PROC-06 | CLI の公開面は足すだけにし、変える・消すときは ADR を書く | review | 意味の変更（同じ名前で振る舞いを変える）は字面では判定できない。名前の追加と削除は `docs/cli.md` の差分に必ず現れるので、レビューで確かめる |
| TOOL-02 | 編集後は hooks、完了前は make check を回す | doc | いつ検査を回したかは差分に残らない |

## 対象外とした軸

| 軸 | 理由 |
|---|---|
