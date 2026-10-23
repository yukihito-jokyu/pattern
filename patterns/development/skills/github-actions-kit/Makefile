# 開発用のコマンド。check が通ることが完了の条件（docs/design/rules.md の PROC-05）
UV := uv run --locked
GHA := uv run --locked --script .gha/gha.py
PY_TARGETS := .gha .github/actions scripts tests install.py
KIT_PY := PYTHONPATH=.gha:.github/actions/run-report $(UV) python
CHECKS := format-check lint typecheck structure docs-check test workflows guard rules

.PHONY: check fix fix-file docs $(CHECKS)

## check: 全検査。書き換えはしない。1つが落ちても残りを回し、最後にまとめて失敗にする
check:
	@failed=""; for target in $(CHECKS); do $(MAKE) --no-print-directory $$target || failed="$$failed $$target"; done; \
	if [ -n "$$failed" ]; then echo "check: 失敗した検査:$$failed"; exit 1; fi; echo "check: 全検査が通った"

## fix: Python の整形と lint の自動修正（YAML には自動修正が無いので、指摘を見て直す）
fix:
	$(UV) ruff format $(PY_TARGETS)
	$(UV) ruff check --fix $(PY_TARGETS)

## fix-file: 1ファイルだけ直す・検査する（編集直後の hooks が呼ぶ）
fix-file:
	@case "$(FILE)" in \
	  *.py) $(UV) ruff format "$(FILE)" && $(UV) ruff check --fix "$(FILE)" ;; \
	  .github/*.yml|.github/*/*.yml|.github/*/*/*.yml) $(GHA) check "$(FILE)" ;; \
	  *) echo "fix-file: 対象外のファイル $(FILE)" ;; \
	esac

## docs: 生成物（スキルに写すルールと見本）を作り直す
docs:
	$(KIT_PY) scripts/gen_docs.py

format-check:
	$(UV) ruff format --check $(PY_TARGETS)

lint:
	$(UV) ruff check $(PY_TARGETS)

typecheck:
	$(UV) mypy

structure:
	$(KIT_PY) scripts/structure_check.py

docs-check:
	$(KIT_PY) scripts/gen_docs.py --check

test:
	$(KIT_PY) -B -m unittest discover -s tests -t .

workflows:
	$(GHA) check

guard:
	python3 .foundation/bin/guard.py --root .

rules:
	python3 .foundation/bin/rules_check.py --root . --no-write
