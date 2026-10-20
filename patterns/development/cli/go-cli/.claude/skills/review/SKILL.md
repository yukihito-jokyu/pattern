---
name: review
description: go-cli の変更をレビューする手順。差分、プルリクエスト、ブランチ、特定のファイルのレビューを頼まれたとき、また「この実装で問題ないか確認して」「ルールに沿っているか見て」と頼まれたときは必ず使う。機械の検査を先に回し、機械で拾えないルールをルールIDごとに確かめ、固定の形式で指摘と判定を返す。
---

# go-cli のレビュー手順

指摘は、ルールの正本である `docs/design/rules.md` のルールIDに結び付ける。ルールに無いことを理由に差し戻さない。レビュアーごとに基準が変わるのを防ぐためである。

## 1. 対象を決める

- 指定があれば、それを対象にする
- 指定が無ければ、未コミットの変更（`git diff HEAD` と未追跡のファイル）を対象にする
- 未コミットの変更も無ければ、現在のブランチと基準のブランチの差分を対象にする

対象のファイル一覧を、出力の「対象」節に書く。

## 2. 機械の検査を回す

`make check` を実行する。落ちたら、出力の要点を「機械の検査」節に載せる。機械が拾った違反を、人手の指摘として重複して書かない。

## 3. 抜け道を確かめる

| ルールID | 確認 | 見るもの |
|---|---|---|
| TOOL-03 | 保護ファイルの変更 | `.foundation/manifest.json` の `protected` に当たるファイル（`.golangci.yml`、`Makefile`、`tools/`、`go.mod`、`golangci-lint.mod`、`.foundation/`、`docs/design/rules.md` など）が、差分にあるか |
| TOOL-03 | 抑止コメント | manifest の `guard.suppressions` のパターン（`//nolint`、`//lint:ignore`、`#nosec`、`t.Skip`、`//go:build`）が、差分にあるか |
| TOOL-03 | テストの skip・削除 | `_test.go` の削除、テーブルの件の削除、`t.Skip` の追加 |
| DEP-06 | 依存の追加 | `go.mod`・`golangci-lint.mod` の差分と、同じ差分に承認を書いた ADR があるか |

## 4. 機械で拾えないルールを確かめる

rules.md で強制に `review` を含むルールは、3節かこの表の1列目に全部載っている。差分に関係する行を確かめる。

| ルールID | 確認方法 | 違反の典型例 |
|---|---|---|
| STR-05 | 差分で新しく足した関数が、ほかの場所の関数と同じ処理をしていないか。2か所以上で使う処理が rules.md STR-05 の決定表の置き場にあるか | `remove.go` と `complete.go` にそれぞれ ID の検証を書く。名詞の業務の知識を `internal/cli` に置く |
| CODE-02 | Service のメソッドの引数が、一覧の絞り込みなら `Filter`、それ以外は `ctx`、ID、位置引数、フラグの順の値になっているか | `Add(ctx, AddInput{...})` のような入力用の構造体を作る。`Add(ctx, due, title)` と順を変える |
| ERR-04 | 文字列から値への変換が domain の `Parse<項目名>` にあり `run<Verb>` の先頭で呼ばれているか。業務の制約が Service のメソッドの先頭の `validate<Field>` にあるか | `run<Verb>` の中でタイトルの長さを確かめる。Service の中で文字列の日付を解析する |
| STATE-01 | データファイルの名前と JSON の形、`version` の値。パッケージ変数・キャッシュ・新しい設定ファイルが無いか | `note-data.json` という名前。項目を足して `formatVersion` を2にする |
| OPS-06 | JSON の最上位のキーが `<noun>` か `<nouns>` か。文章の形が `<過去分詞> <noun> <id>: <title>` か、一覧が `cli.WriteTable` の表で列の順が rules.md OPS-06 どおりか | `{"result": ...}`、`{"removed": true}`。`Task 1 removed.` |
| TEST-01 | 足した・変えたサブコマンドの `Test<Verb>` に、成功の文章、`--json`、そのコマンドが返しうる終了コード2と3の件があるか | 終了コード3の件が無い。`--json` の件が無い |
| TEST-04 | 期待する出力がテーブルの文字列リテラル（複数行は raw string）で直接書かれているか。サブコマンドのテストの前提データが `setup` の CLI の実行で作られ、環境変数が `env` フィールドと `h.Setenv` で設定されているか | 期待値を `fmt.Sprintf` で組み立てる。サブコマンドのテストで `tasks.json` を直接書く |
| TEST-05 | 足した件が rules.md TEST-05 の「足す件」の表と「値の種類ごとの件」の表のとおりか（件の名前、setup、`args` の順、値）。表に無い件が足されていないか。足した件が同じ種類の件の最後にあるか | `adds_a_task_with_a_due_date` と名付ける。`--due` を位置引数より前に書く。日付に `2026-11-01` を使う。表に無い `rejects_a_date_with_a_time` を足す |
| PROC-02 | rules.md PROC-02 の表の組のうち、archcheck が見ない組（エラーの種類と `exit.go`、環境変数と `README.md`）がそろっているか | `errkind` に種類を足し `exitCode` に足さない。`GOCLI_TITLE_MAX` を足し README に書かない |
| PROC-06 | `docs/cli.md` の削除された行、`json` タグの変更、`config.go` の環境変数の名前の変更、`exit.go` の番号の変更が無いか。あれば承認を書いた ADR があるか | `--all` を `--include-done` に変える。`created_at` を `created` に変える |
| DEP-06 | 3節の「依存の追加」と同じ | `go.mod` に `require` を足す |
| TOOL-03 | 3節の「保護ファイルの変更」「抑止コメント」「テストの skip・削除」と同じ | `.golangci.yml` の `funlen` を上げる |

## 5. ファイルをまたぐ対応を確かめる

rules.md の PROC-02 の表の各組について、両側のファイルを開いて突き合わせる。

1. エンティティの項目：`internal/domain/<noun>/<noun>.go` の型、`internal/adapter/<noun>store/<noun>store.go` の `record`・`toRecord`・`to<Noun>`、`internal/command/<noun>cmd/view.go` の `<noun>View`・`to<Noun>View` を並べ、項目と変換の代入が同じ順でそろっているかを見る（項目名の一致は archcheck が見るので、変換関数の代入の漏れを見る）
2. 名詞・動詞・フラグ・`Summary`・終了コード：`docs/cli.md` が差分に含まれているか（鮮度は `make docs-check` が見る）
3. エラーの種類：`internal/errkind/errkind.go` の変数、`internal/cli/exit.go` の定数・`ExitCodes`・`exitCode` の `case` が1対1か
4. 名詞の追加：`internal/app/app.go` で Store・Service・`<noun>cmd.New` が組まれているか
5. 環境変数の追加：`internal/app/config.go` の定数と、`README.md` の環境変数の表が1対1か

## 6. 出力の形式

必ず次の形で出す。

```
# レビュー結果

## 判定
承認 または 差し戻し

## 対象
- <ファイルの一覧>

## 機械の検査
<check の結果。通った、または落ちた（要点）>

## 指摘
| # | ルールID | 場所 | 根拠（実際の記述） | 直し方 |
|---|---|---|---|---|
| 1 | <ID> | <パス>:<行> | `<該当の記述>` | <直し方> |

指摘が無ければ「なし」と書く。

## ルール追加の提案
<ルールには無いが、揺れや問題になりうる点。指摘とは分けて書く。無ければ「なし」>
```

- 判定は機械的に決める。check が通り、かつ指摘が0件なら「承認」、それ以外は「差し戻し」
- 指摘は場所の順に並べる
- 同じ違反が複数の箇所にあれば、箇所ごとに1行ずつ書く
