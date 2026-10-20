GOLANGCI_LINT := go tool -modfile=golangci-lint.mod golangci-lint

.PHONY: check fix generate tidy-check lint build vet arch docs-check test guard rules

## check: run every check; the work is done only when this passes
check: tidy-check lint build vet arch docs-check test guard rules

## fix: format the code, apply the automatic lint fixes and regenerate docs/cli.md
fix:
	$(GOLANGCI_LINT) fmt ./...
	$(GOLANGCI_LINT) run --fix ./...
	go run ./tools/clidoc

## generate: regenerate docs/cli.md from the command tree
generate:
	go run ./tools/clidoc

tidy-check:
	go mod tidy -diff
	go mod tidy -modfile=golangci-lint.mod -diff

lint:
	$(GOLANGCI_LINT) run ./...

build:
	go build ./...

vet:
	go vet ./...

arch:
	go run ./tools/archcheck

docs-check:
	go run ./tools/clidoc -check

test:
	go test ./...

guard:
	python3 .foundation/bin/guard.py --root .

rules:
	python3 .foundation/bin/rules_check.py --root . --no-write
