# AGENTS.md

AI コーディングエージェント向けの作業ルール。人間向けの詳しい説明は `docs/` にある。

## プロジェクト概要
- Go 1.27 / PostgreSQL 16 で作る、クリーンアーキテクチャ構成の HTTP API テンプレート
- Go は `go.mod` の `go` ディレクティブ（GOTOOLCHAIN=auto で自動取得）、golangci-lint と migrate は `Makefile` の `GOLANGCI_LINT_VERSION` / `MIGRATE_VERSION` でプロジェクト単位に固定している
- 外部ライブラリは pgx（DB ドライバ）と gin（ルーティング、handler 層だけで使う）。ログは `log/slog`
- 設計の背景: [docs/architecture.md](docs/architecture.md)
- 書き方の規約: [docs/coding-rules.md](docs/coding-rules.md)
- 機能追加の手順: [docs/adding-a-feature.md](docs/adding-a-feature.md)

## コマンド

初期設定は [.agents/skills/setup/SKILL.md](.agents/skills/setup/SKILL.md) に従う。モジュール名と環境変数の同期だけを対象とし、Go・依存・ツールのバージョンは変えない。setupの変更後は `make test-setup` と `make check` を確認する。

| 目的 | コマンド |
|---|---|
| 開発ツールの導入 | `make tools`（golangci-lint と migrate を `bin/` に入れる。`make lint` / `make check` / `make migrate-*` も未導入なら自動で入れる） |
| 検証一式（完了前に必須） | `make check`（build → vet → test → lint） |
| テスト | `make test` |
| lint（依存方向を含む） | `make lint` |
| 整形（lint の gofmt / golines の指摘を直す） | `make fmt` |
| DB 起動 / マイグレーション | `make db-up` → `make migrate-up` |
| サーバ起動 | `make run`（`.env.example` を `.env` にコピーして使う） |
| マイグレーション作成 | `make migrate-new NAME=xxx` |

## ディレクトリと置き場所
```
cmd/api/                     起動と DI 配線のみ
internal/domain/<集約>/       エンティティ・値オブジェクト・ドメインエラー（標準ライブラリと他の domain のみ）
internal/usecase/            port.go に interface、<集約>.go にユースケース
internal/adapter/handler/    HTTP ⇔ usecase の変換、エラー → ステータス対応表
internal/adapter/repository/ usecase の port の DB 実装
internal/adapter/<外部>/      usecase の port の外部サービス実装（例: mail）
internal/infra/              設定・DB 接続・ロガー
db/migrations/               golang-migrate 形式の SQL
api/openapi.yaml             API 仕様
```

## 絶対に守るルール（依存方向）
- 依存は `cmd → adapter → usecase → domain` の一方向。逆向きの import をしない
- domain は標準ライブラリと、他の集約の domain 以外を import しない
- usecase は `database/sql` と `net/http` を import しない。外部依存は `port.go` の interface 経由で使う
- adapter 同士（handler / repository / 外部サービス）は import しない。adapter は infra を import しない
- これらは `.golangci.yml` の depguard で検出される。**lint エラーを設定変更で黙らせない**

## 実装ルール（要点）
- interface は **使う側** で定義する（usecase の port、handler の `userUsecase` など）。コンストラクタは struct を返す
- domain のフィールドは非公開にし、`New` で不変条件を検証する。DB からの復元は `Reconstruct` で行う
- domain に `json` / `db` タグを付けない。DTO は handler の `dto.go` に置く
- 複数の書き込み、または「読んでから書く」処理は `TxManager.Do` で囲む。repository は必ず `conn(ctx, r.db)` を使う
- usecase は他の usecase を呼ばない。他の集約のデータは、その集約の port から直接取る
- 外部サービスの呼び出しは `TxManager.Do` の外（コミットの後）で行う
- 更新・削除・一覧・集約をまたぐ処理・外部サービスの追加は、[docs/adding-a-feature.md](docs/adding-a-feature.md) の該当する章の手順に従う
- 実装の進め方は [.claude/skills/go-clean-implement/SKILL.md](.claude/skills/go-clean-implement/SKILL.md)、レビューの進め方は [.claude/skills/go-clean-review/SKILL.md](.claude/skills/go-clean-review/SKILL.md) に従う
- エラーは `%w` でラップし、`errors.Is` で判定する。新しいドメインエラーは `handler/error.go` の `errorMappings` に追加する
- `util` / `common` パッケージを作らない。`pkg/` ディレクトリを作らない
- DI はすべて `cmd/api/main.go` に手書きする。DI フレームワークを導入しない

## テスト
- 既存のテストに倣い、テーブル駆動で書く。usecase は `fake_test.go` の手書きフェイクを使う（モック生成ツールは使わない）
- domain と usecase は必ずテストを書く。handler / repository のテストは、既存の規約ができるまで追加しない

## やってはいけないこと
- 依頼なしに `go.mod` の `go` ディレクティブや `GOLANGCI_LINT_VERSION` / `MIGRATE_VERSION` を変える、または `go get` で依存を最新に上げる。Go を上げるときは、golangci-lint がその Go 以上でビルドされていることを `golangci-lint version` で確かめ、両方を同時に上げる
- グローバルにインストールされた `golangci-lint` や `migrate` を直接使う（バージョンが異なる。必ず `make lint` / `make check` / `make migrate-*` を使う）
- 依頼されていない範囲のリファクタリング（必要なら提案して承認を待つ）
- `make check` が通らない状態での完了報告

## 完了前チェックリスト
1. `make check` が通る
2. ドメインエラーを追加したら `errorMappings` に反映した
3. API を変更したら `api/openapi.yaml` を更新した
4. スキーマを変更したら `db/migrations/` に up / down の両方を追加した
5. 集約を追加したら `.golangci.yml` に「他の集約は ID だけで参照する」のパターンと除外を足した
