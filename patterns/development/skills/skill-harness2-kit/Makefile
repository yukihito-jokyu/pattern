# 開発用のコマンド。check が通ることが完了の条件（docs/design/rules.md の PROC-05）
RUFF := uvx ruff@0.17.2
MYPY := uvx mypy@1.20.2
PY_TARGETS := kit/.h2 scripts tests install.py
KIT_PY := PYTHONPATH=kit/.h2 python3

.PHONY: check fix fix-file format-check lint typecheck structure test guard rules

## check: 全検査。書き換えはしない
check: format-check lint typecheck structure test guard rules

## fix: 整形と lint の自動修正
fix:
	$(RUFF) format $(PY_TARGETS)
	$(RUFF) check --fix $(PY_TARGETS)

## fix-file: 1ファイルだけ整形と lint をする（編集直後の hooks が呼ぶ）
fix-file:
	$(RUFF) format $(FILE)
	$(RUFF) check --fix $(FILE)

format-check:
	$(RUFF) format --check $(PY_TARGETS)

lint:
	$(RUFF) check $(PY_TARGETS)

typecheck:
	$(MYPY)

structure:
	$(KIT_PY) scripts/structure_check.py

test:
	$(KIT_PY) -B -m unittest discover -s tests -t .

guard:
	python3 .foundation/bin/guard.py --root .

rules:
	python3 .foundation/bin/rules_check.py --root . --no-write
