PYTHON ?= python3
SKILL = .claude/skills/agent-behavior-html

.PHONY: check fix test demo probes hooks
check:
	$(PYTHON) scripts/quality.py
	$(PYTHON) -B -m unittest discover -s tests -v
	node scripts/check_dashboard.cjs
	$(PYTHON) .foundation/bin/guard.py --root .
	$(PYTHON) .foundation/bin/rules_check.py --root . --no-write

hooks:
	$(PYTHON) $(SKILL)/scripts/install.py --project . --in-place --apply

fix:
	$(PYTHON) scripts/quality.py --fix

test:
	$(PYTHON) -B -m unittest discover -s tests -v

demo:
	$(PYTHON) scripts/demo.py
	$(PYTHON) $(SKILL)/scripts/analyze.py examples/demo.jsonl --output examples/demo.html --synthetic

probes:
	$(PYTHON) .foundation/bin/violation_probe.py --root .
