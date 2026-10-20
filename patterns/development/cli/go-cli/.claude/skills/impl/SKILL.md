---
name: impl
description: go-cli で実装・変更・追加・修正を行う手順。「task に remove サブコマンドを追加して」「task list に --limit フラグを足して」「タスクに期限の項目を足して」「note コマンドを新しく作って」「上限を環境変数で変えられるようにして」「新しいエラーの種類と終了コードを足して」「〜の不具合を直して」のように、この基盤のコードを書く・変える依頼では、依頼の大小にかかわらず必ず使う。依頼をパターンに振り分け、決められた順序で作り、`make check` と完了前チェックリストで確かめてから報告する。
---

# go-cli の実装手順

このスキルは次の資料と一緒に使う。パスは基盤のルートからの相対パスである。

- `docs/design/rules.md`：ルールの全文。`<接頭辞>-<番号>` のルールIDで参照する
- `.claude/skills/impl/references/patterns.md`：パターンごとの手順と、作るファイルの一覧
- 見本（参照実装）：名詞 `task` の一式。`internal/domain/task/`、`internal/adapter/taskstore/`、`internal/command/taskcmd/`、`internal/app/app.go`

既存のコードと rules.md が食い違ったら rules.md に従い、食い違いを報告に書く。

## 1. 依頼をパターンに振り分ける

| 依頼に含まれること | patterns.md の節 |
|---|---|
| 新しい名詞のコマンド（`go-cli <noun> ...`）を作る | 4 |
| 記録する項目を足す（期限、優先度、メモ、タグなど） | 3 |
| 環境変数で設定できるようにする | 7 |
| 新しいエラーの種類・終了コードを足す | 6 |
| サブコマンド（動詞）を足す | 1 |
| 既存のサブコマンドにフラグを足す | 2 |
| 複数のコマンドで同じ処理を使う（共通化） | 5 |
| 不具合を直す、既存の振る舞いを変える | 8 |

- 複数の行に当たる場合は、表の上から順に全部行う。たとえば「期限を足し、add で指定し list に表示する」は 3 だけで足りる（3 が add と list の変更を含む）。「note を作り add と list を付ける」は 4 で最初の動詞を作り、2つ目の動詞を 1 で足す
- どの行にも当たらない場合は、実装しない。必要なパターンとルールを提案として報告する。見本に無い形をその場で発明すると、作者ごとに違う形が生まれるからである
- 依頼に公開面（サブコマンド名、フラグ名、JSON のキー、終了コード、環境変数名）の名前の変更や削除が含まれる場合は、実装せずに報告する（PROC-06）
- Go や golangci-lint の版を上げる依頼は、rules.md の PROC-03 の手順で行う。ルールや検査の設定を変える依頼は、AGENTS.md の「ルールを変えたいとき」に従う（PROC-04）

## 2. 依頼から決まらない値

推測で決めない。聞ける状況ならユーザーに聞く。聞けない状況なら既定値で決め、報告の3に書く。

| 決めること | 何に響くか | 既定値 |
|---|---|---|
| サブコマンド名 | ファイル名、Service のメソッド名、`docs/cli.md` | rules.md NAM-04 の表の動詞 |
| フラグ名 | 公開面 | 項目名の kebab-case（`Due` → `--due`）。bool は肯定形（`--all`）。短い名前は付けない |
| 値を位置引数にするかフラグにするか | 使い方、`docs/cli.md` | 対象を特定する値と必須の値（ID、タイトル）は位置引数、任意の値はフラグ |
| フラグの既定値 | 挙動 | 型のゼロ値（`""`、`false`、`0`）。ゼロ値は「指定なし」を表す |
| 項目を指定するフラグの説明 | ヘルプ、`docs/cli.md` | 日付は `<Field> date in YYYY-MM-DD format`（`Due date in YYYY-MM-DD format`）、正の整数は `<Field> as a positive integer`、文字列は `<Field> of the <noun>`。`<Field>` は項目名を先頭だけ大文字にした英語 |
| 文字列の項目の長さ | `validate<Field>` | 前後の空白を除いて 1〜100 文字（rune の数）。任意の項目は 0〜100 文字 |
| 日付の書式 | `Parse<項目名>` | `2006-01-02`（`time.DateOnly`）。UTC の 0 時として持つ |
| 数値の範囲 | `Parse<項目名>`、`validate<Field>` | 1 以上 |
| 任意の項目が無いときの出力 | JSON、文章 | JSON はキーごと省く（`json:",omitzero"`）、文章は `-` |
| 項目の JSON のキー | 公開面 | フィールド名の snake_case |
| 一覧の列 | 文章の出力 | rules.md OPS-06 の順。見出しは項目名の大文字の snake_case |
| 一覧の並び順 | `List` | ID の昇順 |
| 削除の方法 | `Remove` | ファイルから消す。ID は既存の最大値+1 で振る（消した最大の ID は再び使われる） |
| 削除・変更の確認 | 使い方 | 確認しない（`--force` を作らない） |
| 1件を変える動詞の文章 | 出力 | `<過去分詞の大文字始まり> <noun> <id>: <title>`（`Removed task 1: Buy milk`）。title の項目が無い名詞はエンティティの最初の文字列の項目 |
| 見つからないときのエラー | 終了コード3 | `fmt.Errorf("%w: <noun> %d", errkind.ErrNotFound, id)` |
| 値が規則に反するときのエラー | 終了コード2 | `fmt.Errorf("%w: <項目名の小文字> must be <条件>", errkind.ErrInvalid)`。値を示すときは末尾に `: %q` |
| 環境変数の名前 | 公開面 | `GOCLI_<対象>_<意味>`（`GOCLI_TITLE_MAX`） |
| 環境変数が空のとき | 挙動 | 既定値を使う。既定値は今のコードの定数の値 |
| 環境変数の値が不正なとき | 終了コード2 | `fmt.Errorf("%w: %s must be <条件>: %q", errkind.ErrInvalid, env<Name>, value)`。正の整数なら `<条件>` は `a positive integer` |
| 日付の値が不正なとき | 終了コード2 | `fmt.Errorf("%w: <項目名の小文字> must be a date in YYYY-MM-DD format: %q", errkind.ErrInvalid, s)` |
| 宣言の説明のコメント | コード | rules.md CODE-10 の表の文。表に無い宣言は日本語の1文を1行に書き、句点（`。`）で終える（CODE-08） |
| テストに足す件、件の名前、テストの値 | テスト | rules.md TEST-05 の表。表に無い件は足さない |

## 3. 書く前に読む

1. patterns.md の該当する節を最後まで読む
2. rules.md のうち、次の表の節をすべて読む

   | patterns.md の節 | rules.md の節 |
   |---|---|
   | 1、2 | STR、NAM、CODE、ERR、OPS、TEST |
   | 3 | STR、NAM、CODE、ERR、STATE、OPS、TEST、PROC |
   | 4 | 全部 |
   | 5 | STR、DEP、CODE |
   | 6 | CODE、ERR、OPS、TEST、PROC |
   | 7 | DEP、NAM、CODE、ERR、STATE、OPS、TEST、PROC |
   | 8 | 直す場所の層に関係する節と CODE、TEST |

3. 見本の該当ファイルを開き、構成・命名・import の並び・コメントの書き方を確かめる。新しいファイルは、見本のファイルを写して名前を置き換えることから始める

## 4. 作る順序

patterns.md の該当節の「作る・変えるファイル」の順に作る。順序は rules.md の PROC-01 に従う：domain（エンティティ、`Parse<項目名>`、`validate<Field>`、`<noun>_test.go`）→ Service のメソッド → adapter → `view.go` → `<verb>.go` → `<verb>_test.go` → `<noun>cmd.go` の登録 → `app.go`（名詞を足す場合）→ `make generate` → `make check`。

生成器は `make generate`（`docs/cli.md` を作る）だけである。コマンド・フラグ・`Summary` を変えたら必ず回す（STR-07）。

各ファイルを保存するたびに、hooks がそのファイルの整形とそのパッケージの lint を走らせる。指摘が出たら、次のファイルに進む前に直す（TOOL-02）。CLI を手で動かすときは `GOCLI_DATA_DIR=$(mktemp -d) go run . <args>` のように、必ず一時ディレクトリを指定する。

## 5. 検証する

1. `make check` を実行する（PROC-05）。整形の指摘は `make fix` で直してよい
2. 落ちたら、エラーに出たルールIDか lint のルール名を rules.md で引き、コードを直す。構造検査（`make arch`）の行は `<ルールID> <パス>:<行> <説明>` の形で、lint の行は `(<linter 名>)` で終わる。forbidigo の説明はルールIDで始まる。lint のルール名とルールIDの対応は `docs/design/enforcement-matrix.md` にある
3. 次の方法で検査を黙らせない（TOOL-03）
   - 検査の設定や保護ファイルを変える
   - 抑止コメントを書く
   - テストを skip する、または消す

   どうしても直せない場合は、その状態のまま報告する

## 6. 完了前チェックリスト

該当するファイルを開き、1つずつ確かめる。

- [ ] PROC-02：エンティティの項目を変えたなら、`internal/domain/<noun>/<noun>.go` の型、`internal/adapter/<noun>store/<noun>store.go` の `record`・`toRecord`・`to<Noun>`、`internal/command/<noun>cmd/view.go` の `<noun>View`・`to<Noun>View` の3か所で、項目と変換が同じ順にそろっている
- [ ] PROC-02：エラーの種類を足したなら、`internal/errkind/errkind.go`、`internal/cli/exit.go` の定数・`ExitCodes`・`exitCode` がそろっている
- [ ] PROC-02：環境変数を足したなら、`internal/app/config.go` の定数と `loadConfig`、`README.md` の環境変数の表がそろっている
- [ ] PROC-02、STR-02：名詞を足したなら、`internal/app/app.go` で Store → Service → `<noun>cmd.New` を組み、`Groups` にアルファベット順で入れた
- [ ] STR-05：2か所以上で使う処理を、rules.md STR-05 の決定表の置き場に置いた。コピーして2か所に書いていない
- [ ] CODE-02：Service への入力を、一覧の絞り込みなら `Filter` に、それ以外は `ctx`、ID、位置引数、フラグの順の引数で渡した
- [ ] ERR-04：文字列から値への変換は `run<Verb>` の先頭で domain の `Parse<項目名>` を呼び、業務の制約は Service のメソッドの先頭で `validate<Field>` を呼んでいる
- [ ] STATE-01：データファイルの名前は `<名詞の複数形>.json` で、`version` を変えていない。パッケージ変数・キャッシュ・設定ファイルを作っていない
- [ ] OPS-06：JSON の最上位は `{"<noun>": ...}` か `{"<名詞の複数形>": [...]}`。文章は表の形
- [ ] TEST-01：足した・変えたサブコマンドの `Test<Verb>` に、成功の文章、`--json`、そのコマンドが返しうる終了コード2と3の件がある
- [ ] TEST-04：前提データは `setup` の CLI の実行で作り、環境変数は `env` フィールドと `h.Setenv` で設定した
- [ ] TEST-05：足した件は rules.md TEST-05 の表の件だけで、名前・値・`args` の順が表のとおりで、同じ種類の件の最後にある
- [ ] CODE-08、CODE-10：足した宣言すべてに説明があり、CODE-10 の表の宣言は表の文のとおりで、どのコメントも日本語の1文を1行に書き、句点（`。`）で終えている
- [ ] PROC-06：公開面の名前を変えたり消したりしていない
- [ ] DEP-06、TOOL-03：`go.mod`、`golangci-lint.mod`、保護ファイルを変えていない。抑止コメントを書いていない
- [ ] `make check` が通った

## 7. 報告する

次の順で書く。

1. 何を作ったか（使ったパターンの番号）
2. 変えたファイルの一覧（作る順序の順）
3. 2 で決めた値と、その根拠（依頼文、ユーザーの回答、既定値のどれか）
4. `make check` の結果（出力の末尾）
5. 決めきれずに残したこと、ルールと既存コードの食い違い
