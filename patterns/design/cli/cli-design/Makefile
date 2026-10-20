# 作者が回すコマンドはこのファイルのターゲットだけにする（TOOL-04）。
# 検査ツールは .python-version の Python（3.14）を uv で起動する。
PYTHON := uv run --no-project --quiet python
CLISPEC := $(PYTHON) tools/clispec

.PHONY: check fix new command field release conform after-edit version

# 全検査（完了の条件）。全段を回してから、1つでも落ちていれば失敗にする。
check: version
	@status=0; \
	$(CLISPEC) check || status=1; \
	$(CLISPEC) fmt --check || status=1; \
	$(CLISPEC) gen --check || status=1; \
	$(PYTHON) -m unittest discover -q -s tools/clispec/tests -t tools/clispec || status=1; \
	$(PYTHON) .foundation/bin/guard.py --root . || status=1; \
	$(PYTHON) .foundation/bin/rules_check.py --root . --no-write || status=1; \
	exit $$status

# 自動修正（整形、版（メジャーを除く）、cli.md の生成）
fix: version
	@$(CLISPEC) fmt
	@$(CLISPEC) gen

# make new NAME=<name> [SINGLE=1]
new: version
	@$(CLISPEC) new $(NAME) $(if $(SINGLE),--single)

# make command NAME=<name> NOUN=<名詞> VERB=<動詞> [KEY=id|name]
command: version
	@$(CLISPEC) command $(NAME) $(NOUN) $(VERB) $(if $(KEY),--key $(KEY))

# make field NAME=<name> NOUN=<名詞> FIELD=<項目名> TYPE=<型> [LIST=1] [NULLABLE=1] [VALUES=a,b]
field: version
	@$(CLISPEC) field $(NAME) $(NOUN) $(FIELD) $(TYPE) $(if $(LIST),--list) $(if $(NULLABLE),--nullable) $(if $(VALUES),--values $(VALUES))

# make release NAME=<name>
release: version
	@$(CLISPEC) release $(NAME)

# make conform SPEC=specs/<name>/cli.json CMD="<実装を起動するコマンド>"
conform: version
	@$(CLISPEC) conform $(SPEC) -- $(CMD)

# hooks が cli.json の編集の直後に回す（TOOL-02）
after-edit: version
	@$(CLISPEC) after-edit $(FILE)

# TOOL-04 uv が起動した、.python-version と同じ系列の Python であることを確かめる
version:
	@$(PYTHON) -c 'import os, sys; want = open(".python-version").read().strip(); have = "%d.%d" % sys.version_info[:2]; sys.exit(0 if have == want and os.environ.get("UV") else "TOOL-04 Python " + want + " を uv run で起動する（実際: " + have + "、uv " + ("あり" if os.environ.get("UV") else "なし") + "）")'
