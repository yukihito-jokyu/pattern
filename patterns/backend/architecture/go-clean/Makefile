-include .env
export

MIGRATIONS_DIR := db/migrations

# golangci-lint はプロジェクトの bin/ に固定バージョンで入れる（他のプロジェクトに影響させない）
GOLANGCI_LINT_VERSION := v2.14.0
GOLANGCI_LINT := $(CURDIR)/bin/golangci-lint-$(GOLANGCI_LINT_VERSION)

# golang-migrate も同じく bin/ に固定バージョンで入れる（postgres ドライバ付きでビルドする）
MIGRATE_VERSION := v4.20.1
MIGRATE := $(CURDIR)/bin/migrate-$(MIGRATE_VERSION)

.DEFAULT_GOAL := help
.PHONY: help tools run build test test-setup lint fmt check check-deps smoke db-up db-down migrate-up migrate-down migrate-new rename

help: ## コマンド一覧を表示
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

tools: $(GOLANGCI_LINT) $(MIGRATE) ## 開発ツール（golangci-lint / migrate）を bin/ に導入

$(GOLANGCI_LINT):
	curl -sSfL https://golangci-lint.run/install.sh | sh -s -- -b $(CURDIR)/bin/.tmp $(GOLANGCI_LINT_VERSION)
	mv $(CURDIR)/bin/.tmp/golangci-lint $@
	rmdir $(CURDIR)/bin/.tmp

$(MIGRATE):
	GOBIN=$(CURDIR)/bin/.tmp go install -tags postgres github.com/golang-migrate/migrate/v4/cmd/migrate@$(MIGRATE_VERSION)
	mv $(CURDIR)/bin/.tmp/migrate $@
	rmdir $(CURDIR)/bin/.tmp

run: ## API サーバを起動
	go run ./cmd/api

build: ## バイナリを bin/api に出力
	go build -o bin/api ./cmd/api

test: ## テストを実行（race 検出付き）
	go test -race ./...

test-setup: ## 一時コピーでsetupの反映と拒否条件を検証
	python3 -B scripts/setup_test.py

lint: $(GOLANGCI_LINT) ## golangci-lint（依存方向チェックを含む）
	$(GOLANGCI_LINT) run ./...

fmt: $(GOLANGCI_LINT) ## コードを整形
	$(GOLANGCI_LINT) fmt ./...
	$(GOLANGCI_LINT) run --fix --enable-only whitespace ./...

check: $(GOLANGCI_LINT) ## 完了前の検証一式（build → vet → test → lint）
	go build ./...
	go vet ./...
	go test ./...
	$(GOLANGCI_LINT) run ./...

check-deps: $(GOLANGCI_LINT) ## 一時コピーで依存方向の違反検出を検証（Python 3 が必要）
	python3 scripts/verify-dependencies.py $(GOLANGCI_LINT)

smoke: ## 起動済みAPIの作成・取得・エラー応答を検証（Python 3 が必要）
	python3 scripts/verify-api.py

db-up: ## PostgreSQL を起動
	docker compose up -d --wait db

db-down: ## PostgreSQL を停止
	docker compose down

migrate-up: $(MIGRATE) ## マイグレーションを適用
	$(MIGRATE) -path $(MIGRATIONS_DIR) -database "$(DATABASE_URL)" up

migrate-down: $(MIGRATE) ## マイグレーションを1つ戻す
	$(MIGRATE) -path $(MIGRATIONS_DIR) -database "$(DATABASE_URL)" down 1

migrate-new: $(MIGRATE) ## マイグレーションを作成 例: make migrate-new NAME=create_orders
	$(MIGRATE) create -ext sql -dir $(MIGRATIONS_DIR) -seq $(NAME)

rename: ## モジュール名を変更 例: make rename MODULE=github.com/acme/app
	bash ./scripts/rename-module.sh $(MODULE)
