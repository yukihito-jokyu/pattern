# go-cli

Go の標準ライブラリ（`flag`）だけで作る、`go-cli <noun> <verb>` 形式の CLI の開発基盤である。誰が書いても同じファイルに同じ形のコードが入るように、構造・ルール・検査・見本（`task` 名詞の一式）をそろえてある。

## 作業の入口

| やること | 使うもの |
|---|---|
| 実装・変更・追加・修正 | 実装用スキル `impl`（`.claude/skills/impl/SKILL.md`） |
| レビュー | レビュー用スキル `review`（`.claude/skills/review/SKILL.md`） |
| ルールを調べる | `docs/design/rules.md`（ルールIDで引く） |
| 構造の理由を調べる | `docs/design/architecture.md`、`docs/design/adr/` |

スキルを使えないエージェントは、上のファイルを直接読み、同じ手順に従う。

## コマンド

| 目的 | コマンド |
|---|---|
| 全検査（完了の条件） | `make check` |
| 自動修正（整形、lint の自動修正、`docs/cli.md` の再生成） | `make fix` |
| `docs/cli.md` の再生成 | `make generate` |
| テストだけ | `make test` |
| lint だけ（整形の確認を含む） | `make lint` |
| 構造検査だけ | `make arch` |
| CLI を動かす | `GOCLI_DATA_DIR=$(mktemp -d) go run . task list` |

- 依存の導入は要らない。`make check` の初回に Go 1.27.2 と golangci-lint v2.15.0 が自動で取得される
- CLI を手で動かすときは、必ず `GOCLI_DATA_DIR` に一時ディレクトリを指定する。指定しないと `~/.local/share/go-cli/` に書き込む

## ディレクトリ構造

```text
main.go                          入口。app.Run を呼んで終了するだけ（STR-08）
internal/app/                    組み立てと設定（環境変数は config.go だけで読む）
internal/app/apptest/            テストで CLI を実行する道具
internal/cli/                    フラグ解析・ヘルプ・出力・終了コードの枠組み
internal/command/<noun>cmd/      名詞1つ分のサブコマンド。動詞1つにファイル1つ
internal/domain/<noun>/          名詞1つ分のエンティティと use case（Service）
internal/adapter/<noun>store/    名詞1つ分の保存（JSON ファイル）
internal/errkind/                エラーの種類（終了コードを決める）
tools/archcheck/                 構造検査
tools/clidoc/                    docs/cli.md の生成
docs/cli.md                      生成物：コマンドの一覧
```

依存は `command → domain ← adapter` の向きで、`app` が全部を組み立てる。許可表は `docs/design/architecture.md` の3節にある。

## 守ること

要約である。全文と理由は `docs/design/rules.md` にある。

1. **STR-02** 名詞は domain・adapter・command の3パッケージ一式で足し、動詞は `<verb>.go` と `<verb>_test.go` の組で足す。`Commands` と `Groups` はアルファベット順
2. **STR-04** `<verb>.go` は `<verb>Options`、`<verb>Output`、`new<Verb>`、`run<Verb>`、`WriteText` の5つをこの順に書く
3. **DEP-01** import は許可表の組だけ。command は adapter を、domain は cli を import しない
4. **DEP-05** `os`・`time.Now`・`os.Getenv` などプロセスに触るものは `main.go` と adapter だけ。時計は `func() time.Time` で受け取る
5. **NAM-04** サブコマンド名と Service のメソッド名は同じ動詞（add、get、list、update、remove、状態の動詞）
6. **NAM-05** `run<Verb>` で Service の戻り値を受ける変数は過去分詞（`added`、`removed`）、一覧は複数形
7. **ERR-01** エラーの種類は `fmt.Errorf("%w: <詳細>", errkind.ErrInvalid)` の形で付ける。入力の誤りは2、見つからないは3
8. **ERR-04** 文字列から値への変換は domain の `Parse<X>`、業務の制約は Service の `validate<Field>`
9. **OPS-02** 設定は `GOCLI_` の環境変数を `internal/app/config.go` だけで読み、引数で渡す
10. **OPS-05** コマンドは出力型と error を返すだけ。表示先と終了コードは `internal/cli` が決める
11. **OPS-06** 1件を変える動詞の文章は `<過去分詞> <noun> <id>: <title>`、一覧は `cli.WriteTable`、JSON の最上位はオブジェクト
12. **TEST-01** サブコマンドごとに `Test<Verb>` を書き、成功・`--json`・終了コード2と3を `apptest` で確かめる
13. **TEST-03** テストで偽物の型を作らない。`apptest`（一時ディレクトリの本物の Store）を使う
14. **TEST-05** テストに足す件・件の名前・値（`Buy milk`、`2026-01-31`、`one`、`unknown`）・並び（成功 → `--json` → 終了コード順）は rules.md の表のとおりにし、表に無い件を足さない
15. **CODE-08、CODE-10** 全部の宣言に日本語の説明を1行1文で書く。役割の決まった宣言（`run<Verb>`、`Parse<Field>`、`load<Name>` など）は rules.md CODE-10 の表の文をそのまま書く
16. **OPS-02、NAM-03** 環境変数を足すときは `config.go` に `env<Name>`・`default<Name>`・`load<Name>`・`config` のフィールドをそろえ、`loadConfig` からフィールドの順に呼ぶ
17. **PROC-01** 作る順序は domain → Service → adapter → view → `<verb>.go` → テスト → 登録 → `make generate` → `make check`
18. **PROC-02** エンティティの項目を足したら、adapter の `record` と `view.go` の `<noun>View` にも同じ順で足す

## してはいけないこと

- 検査を通すために保護ファイルを変える。保護ファイルとは、検査の設定（`.golangci.yml`、`Makefile`、`tools/`）、`go.mod`、`golangci-lint.mod`、`.foundation/`、`docs/design/rules.md` などで、一覧は `.foundation/manifest.json` の `protected` にある
- 抑止コメントを書く（`//nolint`、`//lint:ignore`、`#nosec`、`t.Skip`、`//go:build`）。一覧は manifest の `guard.suppressions` にある（TOOL-03）
- 依頼に無い依存ライブラリを足す。`go.mod` に `require` を書かない（DEP-04、DEP-06）
- 見本（`task` の一式）と違う形の新しいパターンを作る。必要なら実装せずに、提案として報告する
- `docs/cli.md` を手で編集する。`make generate` で作る（STR-07）
- 公開面（サブコマンド名、フラグ名、JSON のキー、終了コード、環境変数名）の名前を変える・消す。足すだけにする（PROC-06）
- goroutine、チャネル、`sync`、`log`、`fmt.Println` を使う（ASYNC-01、OPS-01）

## 完了の条件

1. `make check` が通る（PROC-05）
2. 実装用スキルの完了前チェックリストを満たす
3. 報告に、依頼から決まらなかった値とその根拠、check の結果を書く

編集の直後は hooks が編集したファイルの整形とそのパッケージの lint を回す。完了の前に作者が `make check` を回す。CI とコミット前の検査は置いていない（TOOL-02）。

## ルールを変えたいとき

ルールを勝手に変えない。変えるべき理由を報告し、承認されてから次の順で変える（PROC-04）。Go と golangci-lint の版を上げるときも同じで、手順は rules.md の PROC-03 にある。

1. ADR を書く
2. `docs/design/rules.md` を変える
3. 検査の設定（`.golangci.yml`、`tools/archcheck`）と `.foundation/probes.json` を変える
4. 参照実装を変える
5. `python3 .foundation/bin/rules_check.py --root .` と `python3 .foundation/bin/violation_probe.py --root .` を通す
