---
name: go-clean-implement
description: go-clean プロジェクト（Go と PostgreSQL のクリーンアーキテクチャ構成の HTTP API）で機能を実装する手順。集約（テーブル）の追加、作成・取得・更新・削除・一覧 API の追加、他の集約のデータを使う処理、メール送信など外部サービスの追加、ミドルウェアや HTTP エラーの追加を頼まれたときに使う。依頼をパターンに振り分け、内側の層から順に作り、make check と完了前チェックリストで確かめてから報告する。
---

# go-clean の実装手順

このスキルは、次の 2 つの文書と一緒に使う。どちらもこのスキルの中にあり、ほかの文書は読まなくてよい。

- [references/rules.md](references/rules.md)：守るルールの全文と、コードのひな形。番号（「rules 4」など）で参照する
- [references/patterns.md](references/patterns.md)：追加のパターンごとの手順と、その場面のコード例

プロジェクトにすでにある集約（`user` など）のコードは、命名や書き方を合わせるための参考になる。ただし、既存のコードと rules.md が食い違ったら rules.md に従う。

## 1. 依頼をパターンに振り分ける

依頼を読んで、patterns.md のどの節に当たるかを決める。複数に当たるなら、上から順に全部やる。

| 依頼に含まれること | patterns.md |
|---|---|
| 新しいテーブル・集約 | 1 |
| 既存の集約の更新（PATCH） | 2 |
| 削除（DELETE） | 3 |
| 一覧（GET でページング） | 4 |
| 他の集約の存在確認・データ参照 | 5 |
| メール・外部 API | 6 |
| ミドルウェア・HTTP だけのエラー | 7 |

次のことが依頼から決まらないときは、推測で決めずにユーザーに聞く。どれも、後から変えるとデータや API の互換性に響くものである。聞けない状況なら、右の既定値で決めて報告に書く。

| 決めること | 何に響くか | 既定値 |
|---|---|---|
| 文字列の最大長、数値の下限と上限 | domain の検証、DB の `VARCHAR(n)` / `CHECK`、openapi の制約 | なし（必ず聞く。聞けなければ既存の集約の似た項目に合わせる） |
| 参照先が削除されたときの扱い | マイグレーションの `ON DELETE` | `RESTRICT` |
| 同時更新で上書きされて困るか | `FOR UPDATE` の取得メソッド | 困らない（付けない） |
| 一意にすべき項目 | 一意制約と `ErrXxxAlreadyExists` | なし |

## 2. 書く前に読む

1. patterns.md の該当する節を最後まで読む
2. rules.md の、触る層の節をすべて読む。テストを書くので「11 テスト」も必ず読む
3. 同じ層の既存のファイルを 1 つ開き、import の並び・コメントの書き方を確かめる

## 3. 内側から順に作る

各ステップの終わりで `go build ./...` が通る状態を保つ。順番を飛ばさない。

1. **マイグレーション**（rules 7）：`make migrate-new NAME=create_<テーブル>` で作る。外部キーには `ON DELETE` とインデックスを付け、down は `DROP TABLE IF EXISTS` だけにする
2. **domain**（rules 2）：エンティティ・`New`・`Reconstruct`・getter・`errors.go`・`id.go`（2.2 のひな形を写す）。数値には上限も付ける。集約を足したら `.golangci.yml` に 2.4 の 2 か所を足す
3. **domain のテスト**（rules 11）：`package <集約>_test` でテーブル駆動。境界値（上限ちょうどと上限 + 1）を入れる
4. **usecase**（rules 3）：Input / Output / Usecase / コンストラクタ / メソッド / `new<集約>Output`。port は使うメソッドだけ足す。読んでから書く処理は `TxManager.Do` で囲み、外部サービスの呼び出しは `Do` の後に置く
5. **usecase のテスト**（rules 11）：`fake_test.go` に fake を足し、rules 11.2 の型どおりに書く。呼ぶ port ごとにエラーのケースを作る
6. **repository**（rules 5）：`var _ usecase.XxxRepository = ...`、`conn(ctx, r.db)`、SQL の書き方、エラーの変換の表のとおりに変える
7. **handler**（rules 4）：`dto.go` → handler のファイル（使う側の interface）→ `errorMappings` → `router.go`。usecase には `c.Request.Context()` を渡す
8. **DI**（rules 9）：`cmd/api/main.go` に repository → usecase → handler の順で足し、`NewRouter` に渡す
9. **API 仕様**（rules 8）：`router.go` と同じ順で paths を足し、スキーマを `Error` の直前に足す。返りうるエラーのステータスをすべて書く。新しいエラーコードは `Error` の `enum` にも足す

## 4. 検証する

1. `make fmt` で整形の指摘を直す
2. `make check` を通す。lint で止まったら patterns.md の「8 lint で止まったとき」に従ってコードを直す。**`.golangci.yml` を変えたり `//nolint` を足したりして黙らせない**（集約を足したときの rules 2.4 の 2 か所だけは、手順どおりの追加なので例外）
3. rules.md の「13 完了前チェックリスト」を 1 つずつ確かめる。特に、ファイルをまたぐ次の対応は、それぞれ両側を開いて突き合わせる
   - domain の `ErrXxx` ⇔ `errorMappings` ⇔ openapi の `Error` の enum
   - domain の上限・下限の定数 ⇔ マイグレーションの `VARCHAR(n)` / `CHECK` ⇔ openapi の `maxLength` / `minimum` / `maximum`
   - `router.go` のルート ⇔ openapi の paths（順番も）
   - `dto.go` の json タグ ⇔ openapi のスキーマのプロパティ
   - usecase が返しうるエラー ⇔ openapi のそのエンドポイントの responses

## 5. 報告する

次の順で書く。

1. 何を作ったか（パターンと、足した API）
2. 変えたファイルの一覧（層の順）
3. 1 で決めた値（最大長・上限・`ON DELETE` など）と、その根拠（依頼文か、ユーザーの回答か、既定値か）
4. `make check` の結果（出力の末尾を貼る）
5. 決めきれず残したこと
