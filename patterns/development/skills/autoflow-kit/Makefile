# 開発用のコマンド。check が通ることが完了の条件（docs/design/rules.md の PROC-05）
RUFF := uvx ruff@0.17.1
MYPY := uvx mypy@1.20.2
PY_TARGETS := kit/.autoflow scripts tests install.py
KIT_PY := PYTHONPATH=kit/.autoflow python3
CHECKS := format-check lint typecheck structure docs-check test guard rules

.PHONY: check fix fix-file docs $(CHECKS)

## check: 全検査。書き換えはしない。1つが落ちても残りを回し、最後にまとめて失敗にする
check:
	@failed=""; for target in $(CHECKS); do $(MAKE) --no-print-directory $$target || failed="$$failed $$target"; done; \
	if [ -n "$$failed" ]; then echo "check: 失敗した検査:$$failed"; exit 1; fi; echo "check: 全検査が通った"

## fix: 整形と lint の自動修正
fix:
	$(RUFF) format $(PY_TARGETS)
	$(RUFF) check --fix $(PY_TARGETS)

## fix-file: 1ファイルだけ整形と lint をする（編集直後の hooks が呼ぶ）
fix-file:
	$(RUFF) format $(FILE)
	$(RUFF) check --fix $(FILE)

## docs: 生成する文書（関所の表、プロファイルの表）を作り直す
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
