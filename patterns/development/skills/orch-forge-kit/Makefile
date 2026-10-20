# 開発用のコマンド。check が通ることが完了の条件（docs/design/rules.md の PROC-05）
RUFF := uvx ruff@0.17.1
MYPY := uvx mypy@1.20.2
PY_TARGETS := kit/.forge scripts tests install.py
KIT_PY := PYTHONPATH=kit/.forge python3

.PHONY: check fix fix-file docs format-check lint typecheck structure docs-check test guard rules

## check: 全検査。書き換えはしない
check: format-check lint typecheck structure docs-check test guard rules

## fix: 整形と lint の自動修正
fix:
	$(RUFF) format $(PY_TARGETS)
	$(RUFF) check --fix $(PY_TARGETS)

## fix-file: 1ファイルだけ整形と lint をする（編集直後の hooks が呼ぶ）
fix-file:
	$(RUFF) format $(FILE)
	$(RUFF) check --fix $(FILE)

## docs: 生成する文書（指標の一覧、バンドルの決まりの一覧）を作り直す
docs:
	$(KIT_PY) scripts/gen_docs.py

format-check:
	$(RUFF) format --check $(PY_TARGETS)

lint:
	$(RUFF) check $(PY_TARGETS)

typecheck:
	$(MYPY)

structure:
	$(KIT_PY) scripts/structure_check.py

docs-check:
	$(KIT_PY) scripts/gen_docs.py --check

test:
	$(KIT_PY) -B -m unittest discover -s tests -t .

guard:
	python3 .foundation/bin/guard.py --root .

rules:
	python3 .foundation/bin/rules_check.py --root . --no-write
