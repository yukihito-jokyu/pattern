# github-actions-kit

GitHub Actions のワークフローを、誰が書いても同じ形になるように作成・更新するための道具一式である。ルールと見本、検査の CLI、各ジョブ・各ステップの処理時間を PR に出す composite アクション、Claude Code のスキル2つ（作成・更新用の `gha-workflow`、レビュー用の `gha-review`）を、配布先のリポジトリに入れて使う。

## はじめに

uv（0.13 以降）と python3 が要る。

```bash
uv sync --locked                                   # キットの開発の依存を入れる
uv run --locked --script .gha/gha.py check         # ワークフローの検査（初回は道具を取得する）
make check                                         # キットの全検査
```

## 配布先で使う

```bash
python3 install.py /path/to/your-repo
cd /path/to/your-repo
uv run --locked --script .gha/gha.py check
```

`install.py` は `.gha/`（検査の CLI と設定）、`.github/actions/run-report/`、`.github/dependabot.yml`、`.claude/skills/gha-workflow/`、`.claude/skills/gha-review/` を写す。`.gha/zizmor.yml`（使ってよいアクションの許可表）、`.gha/actionlint.yaml`、`.github/dependabot.yml` は、既にあれば残す。導入した直後の空のリポジトリでは、`gha check` の指摘は0件になる。

配布先のリポジトリで Claude Code を起動し、「CI を追加して」「このワークフローを作り直して」のように頼むと `gha-workflow` が使われる。既存のワークフローを変える依頼では、保守的更新（今の書き方を残す）か破壊的更新（棚卸ししてから作り直す）かを聞かれる。

処理時間の報告は、`ci.yml` の最後の `report` ジョブが出す（見本は `.github/workflows/ci.yml`）。ブランチ保護の必須チェックは `report` の1つにする。

## エージェントと一緒に使う（このキットを開発するとき）

このディレクトリで Claude Code を起動する。起動すると、`CLAUDE.md`（`AGENTS.md` を読み込む）と、`.claude/skills/` の実装用スキル `gha-workflow` とレビュー用スキル `gha-review` が読み込まれ、編集のたびに hooks が整形と lint を走らせる。親のディレクトリで起動すると、hooks が動かない。

## 設計ドキュメント

`docs/design/overview.md` から読む。ルールの全文は `docs/design/rules.md`、ルールと検査の対応は `docs/design/enforcement-matrix.md` にある。


## ZIP単体での環境・導入・検証

この配布版はキット `0.1.0`（`pyproject.toml`）である。ZIPを展開し、`README.md`、`Makefile`、`install.py`がある `github-actions-kit/` を作業場所にする。隠しファイルを含めて展開する。以下はmacOSまたはLinuxのbash、GNU Make、Git、Python 3.12、uv 0.13.4を基準とする。初回の依存取得にはインターネット接続が要る。WindowsではWSL等で同じ環境を用意する。

元キットの `.python-version` は `3.12`、開発依存は `uv.lock`、CLIの依存は `.gha/gha.py.lock` で固定される。開発依存はmypy 2.4.0、ruff 0.17.2、PyYAML 6.0.3、types-PyYAML 6.0.12.20260906。CLIはactionlint-py 1.7.12.25、shellcheck-py 0.11.0.1、yamllint 1.38.0、zizmor 1.31.1、PyYAML 6.0.3を使う。サイトのNode.jsやnpm依存は不要である。

手動確認では、この順で実行し、準備に失敗したら後続を実行しない。

```bash
uv --version  # 基準は0.13.4
uv sync --locked
uv sync --locked --script .gha/gha.py
uv run --locked python --version  # Python 3.12.x
make check
python3 .foundation/bin/violation_probe.py --root . --only STR-02-a,OPS-06-a,TOOL-03-b --timeout 180
```

`make check` は整形、lint、型、構造、生成文書の同期、unit test、ワークフロー、抑止禁止、ルール対応を確認し、最後に「check: 全検査が通った」と出す。probeは一時コピーへ代表的な構造・権限・抑止違反を注入し、3件とも違反として検出されることを確認する。`--only`のため、配布済みの `.foundation/probe-results.json` を更新しない。

準備から配布動作までまとめて確かめるには、同じ場所で次を実行する。

```bash
bash verify-ci.sh
```

`ci.json`の `command` はこのコマンド、`pythonVersion` は `3.12` である。スクリプトは一時仮想環境へuv 0.13.4を導入し、Python 3.12とロック済みの両依存を準備してから全検査とprobeを行う。その後、一時配布先でdry-run、新規導入、再導入、既存設定保持、古い実装の置換、空リポジトリの指摘0件を確認し、「ZIP単体検証: 全確認成功」と出す。途中で失敗すれば非0で終了する。元キット側には依存環境 `.venv/` とツールキャッシュが生成されるため、本物の作業ファイルを汚さず検証したいときは別の展開先で実行する。

実際の配布では、まず導入先の既存変更を確認し、次のdry-runで対象を確認してから導入する。導入先ディレクトリは事前に作る。

```bash
python3 install.py /path/to/your-repo --dry-run
python3 install.py /path/to/your-repo
cd /path/to/your-repo
uv run --locked --script .gha/gha.py check
```

再導入では `.gha/gha_kit/`、`.github/actions/run-report/`、`.claude/skills/gha-workflow/`、`.claude/skills/gha-review/` の4ディレクトリが丸ごと置き換わり、古いファイルも消える。`.gha/gha.py`、`.gha/gha.py.lock`、`.gha/yamllint.yml` の3ファイルも置き換わる。既存の `.gha/zizmor.yml`、`.gha/actionlint.yaml`、`.github/dependabot.yml` は保持され、無い場合だけ追加される。導入先独自の変更は、置換対象の外へ保管するか、導入後に差分を確認する。

参照ワークフローそのもの、`setup-kit`、開発用Makefile・pyproject.toml、`CLAUDE.md`、`.claude/settings.json`のhooks、`.foundation/`は `install.py` の配布対象ではない。キット開発時のhooksを導入先でも使えると解釈しない。利用先のClaude Codeで `.claude/skills/` の2スキルを使い、必要なワークフローを参照例から作成する。`report`を必須チェックにするブランチ保護、secrets、environment、Pages等のGitHub側設定は利用先で別途行う。

移行の取得元はIssue #26と、その会話で指定されたローカル実装である。独立したLICENSEファイルは含まれておらず、利用許諾はこの配布で新設していない。`.foundation/probe-results.json`、収束試行の結果、`docs/design/convergence-report.md`は元キットの記録であり、今回の検証結果とは区別する。ローカル検証は静的検査、unit test、偽API、一時配布先までである。**GitHub上では未実行。Claude Codeによる実対話は未確認。**
