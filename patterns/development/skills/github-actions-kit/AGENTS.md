# github-actions-kit

GitHub Actions のワークフローを、誰が書いても同じ形になるように作成・更新するための道具一式である。ルール（`docs/design/rules.md`）、参照実装（`.github/`）、検査の CLI（`.gha/`）、処理時間を PR に出す composite アクション（`run-report`）、配布するスキル2つ（`gha-workflow`、`gha-review`）でできている。

## 作業の入口

| やること | 使うもの |
|---|---|
| ワークフロー・composite アクション・dependabot.yml の作成と更新 | 実装用スキル `gha-workflow`（`.claude/skills/gha-workflow/SKILL.md`） |
| レビュー | レビュー用スキル `gha-review`（`.claude/skills/gha-review/SKILL.md`） |
| キットの Python（`.gha/gha_kit/`、`run_report.py`、`install.py`、`scripts/`）の変更 | この文書の「キットの Python を変えるとき」 |
| ルールを調べる | `docs/design/rules.md`（ルールIDで引く） |
| 構造の理由を調べる | `docs/design/architecture.md`、`docs/design/adr/` |

スキルを使えないエージェントは、上のファイルを直接読み、同じ手順に従う。

## コマンド

| 目的 | コマンド |
|---|---|
| 全検査（完了の条件） | `make check` |
| 自動修正（Python の整形と lint） | `make fix` |
| ワークフローの検査 | `uv run --locked --script .gha/gha.py check [<パス>]` |
| 保守的更新の検査（指摘が増えていないか） | `uv run --locked --script .gha/gha.py check --ratchet HEAD [<パス>]` |
| 外部アクションの SHA を得る・確かめる | `uv run --locked --script .gha/gha.py pin <owner/repo>`、`... pin --verify` |
| 破壊的更新の棚卸し | `uv run --locked --script .gha/gha.py intent <パス> [--compare-ref HEAD [--from <古いパス>]]` |
| 生成物（スキルの rules.md と見本）を作り直す | `make docs` |
| テストだけ | `make test` |
| 開発の依存を入れる | `uv sync --locked` |
| 配布先に入れる | `python3 install.py <配布先のリポジトリ>` |

## ディレクトリ構造

```text
.github/workflows/      参照実装のワークフロー（ci、reusable-check、release、deploy-pages、security-audit）
.github/actions/        setup-kit（キット用）、run-report（配布する。処理時間の報告と合否）
.github/dependabot.yml  外部アクションの週1回の更新
.gha/                   検査の CLI（gha.py と gha_kit/）と、yamllint・actionlint・zizmor の設定
.claude/skills/         gha-workflow（実装用）と gha-review（レビュー用）。references/ の rules.md と examples/ は生成物
scripts/                キットの構造の検査（structure_check.py）と生成器（gen_docs.py）
tests/                  キットの unittest（test_<モジュール名>.py と support.py）
install.py              配布先に .gha/・run-report・dependabot.yml・スキルを写す
docs/design/            設計の文書（overview から読む）
.foundation/            基盤の検査スクリプト、probe、収束テスト
```

各ディレクトリの理由は `docs/design/architecture.md` の2章にある。

## 守ること

要約である。全文と理由は `docs/design/rules.md` にある。

- PROC-06：既存のワークフローを変えるときは、保守的更新か破壊的更新かをユーザーに選んでもらう。聞けなければ保守的更新にする
- PROC-01：作る順序は「表にする → ファイル名と on: → 見本を写す → ジョブとステップ → report の needs → gha pin → gha check」
- PROC-05：完了の条件は、作成と破壊的更新は `gha check` の指摘0件、保守的更新は `gha check --ratchet HEAD` の増加0件。このキットでは `make check` も通す
- STR-02：PR の検証は全部 `ci.yml` に書き、`pull_request` に絞り込みを書かない
- OPS-01：`ci.yml` の最後に report ジョブを置き、`needs` に report 以外の全ジョブを書く
- DEP-06：外部アクションは `gha pin` が出した `@<40桁の SHA> # vX.Y.Z` の行で書く。SHA を記憶から書かない
- DEP-04：外部アクションは `.gha/zizmor.yml` の許可表のものだけを使い、API の操作は `gh` で書く
- OPS-06：ワークフローの先頭は `permissions: {}`、全ジョブに要る権限だけを書く
- ERR-02：`run:` に `${{ }}` を書かず、値は `env:` で渡す
- NAM-06：`runs-on` は `ubuntu-24.04` などの版付きのラベル。`-latest` を書かない
- ASYNC-02：`runs-on` を持つジョブに `timeout-minutes: 10`（report は 5）
- STR-05：書き込み権限で公開・デプロイするジョブには `environment` を付ける
- TEST-01：GitHub 上で動かしていないものは、報告に「GitHub 上では未実行」と書く
- TOOL-02：ワークフローを保存するたびに `gha check <パス>` を回す。このキットでは hooks が `make fix-file` を回す
- KIT-06：`docs/design/rules.md` か `.github/` を変えたら `make docs` を回す。`docs/design/` のほかの文書は、ルール・構造・道具・配布物を変えるときだけ変え、参照実装のジョブやステップを変えるだけなら変えない
- CODE-03：1行目は `# <トリガー>で、<成果>`（再利用ワークフローは `# 呼ばれると、<成果>`）。呼び出し元・ジョブの一覧・ファイル名を書かず、トリガーか成果が変わったときだけ書き直す

## してはいけないこと

- 検査を通すために保護ファイルを変える。保護ファイルとは、検査の設定（`.gha/`）、`.foundation/`、`docs/design/rules.md` などで、一覧は `.foundation/manifest.json` の `protected` にある
- 抑止コメントを書く。lint 無効化や型無視などで、一覧は manifest の `guard.suppressions` にある
- 依頼に無い依存ライブラリや外部アクションを足す
- 見本（参照実装）と違う形の新しいパターンを作る。必要なら実装せずに、提案として報告する
- `pull_request_target`、`workflow_run`、`secrets: inherit`、`continue-on-error` を書く
- actionlint 1.7.12 が受け付けない新しい構文（`$/path` の参照、ステップの並列実行、concurrency の `queue`）を使う（ADR 0006）

## キットの Python を変えるとき

1. 置き場は KIT-01（`.gha/gha_kit/<名前>.py`、サブディレクトリを作らない）、import してよい組は `docs/design/architecture.md` の3章の表（KIT-02）に従う
2. ルールを足すなら、`rules_<節>.py` に1ルール1関数を書き、`policy.py` の `RULES` に足し、`.foundation/probes.json` に違反例を足す（PROC-04 の順）
3. 新しい関数は、それを最初に呼ぶ関数の直後に置く（KIT-03）
4. テストは KIT-05 の表のモジュールに `tests/test_<モジュール名>.py` を置き、データは同じファイルにある既存のヘルパー関数（`test_run_report.py` なら `job_payload`）で作り、外部コマンドと REST API は `tests/support.py` の `FakeRunner`・`FakeApi` で差し替える
5. CLI の出力は `<ルールID> <パス>:<行> <説明>` と件数の行、終了コードは 0・1・2 にする（KIT-04）

## 完了の条件

1. `make check` が通る
2. 実装用スキルの完了前チェックリストを満たす
3. 報告に、依頼から決まらなかった値とその根拠、check の結果を書く

## ルールを変えたいとき

ルールを勝手に変えない。変えるべき理由を報告し、承認されてから次の順で変える（PROC-04）。

1. ADR を書く
2. `docs/design/rules.md` を変える
3. 検査の設定と `.foundation/probes.json` を変える
4. 参照実装を変える
5. `make docs` を回し、`python3 .foundation/bin/rules_check.py --root .` と `python3 .foundation/bin/violation_probe.py --root .` を通す
