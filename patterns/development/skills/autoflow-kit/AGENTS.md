# autoflow-kit

依頼（文章、Backlog、Redmine、GitLab・GitHub の Issue）から、計画・実装・検証・AI レビュー・リスクの判定までを AI が自走し、人は4つの関所（H0〜H3）でだけ判断する「オートフロー」を、任意のリポジトリに入れる道具である。Python 3.9 の標準ライブラリだけで書いた補助 CLI と、Claude Code のスキル・サブエージェントからなり、正しさは補助 CLI が持つ機械の関所（段の順序、証拠、投票、リスクの段、承認の結び付け）で守る。

## 作業の入口

| やること | 使うもの |
|---|---|
| 実装・変更・追加・修正 | 実装用スキル `impl`（`.claude/skills/impl/SKILL.md`） |
| レビュー | レビュー用スキル `review`（`.claude/skills/review/SKILL.md`） |
| ルールを調べる | `docs/design/rules.md`（ルールIDで引く） |
| 構造の理由を調べる | `docs/design/architecture.md`、`docs/design/adr/` |

スキルを使えないエージェントは、上のファイルを直接読み、同じ手順に従う。

## コマンド

| 目的 | コマンド |
|---|---|
| 全検査（完了の条件） | `make check` |
| 自動修正（整形と lint の修正） | `make fix` |
| 1ファイルの自動修正（hooks が編集の直後に回す。TOOL-02） | `make fix-file FILE=<パス>` |
| テストだけ | `make test` |
| 1つのモジュールのテストだけ | `PYTHONPATH=kit/.autoflow python3 -B -m unittest tests.test_<モジュール>` |
| 生成物（gates.md、profile-schema.md）を作り直す | `make docs` |
| 構造検査だけ | `make structure` |
| 配布物を対象のリポジトリに入れる | `python3 install.py --dest <対象のリポジトリ>` |

依存の導入は要らない（`python3` と `git` と `uvx` だけで動く）。ruff と mypy は `Makefile` が `uvx` で版を固定して呼ぶ。

## ディレクトリ構造

```text
kit/.autoflow/autoflow.py            補助 CLI の入口（cli.main を呼ぶだけ）
kit/.autoflow/autoflow_kit/          補助 CLI のモジュール。段のモジュールと共有のモジュールを平らに並べる
kit/.autoflow/templates/prompts/     サブエージェントへのプロンプトのひな形（planner、builder、risk、finder、verifier）
kit/claude/skills/                   配布するスキル（autoflow-setup、autoflow、autoflow-learn）
kit/claude/agents/                   配布するサブエージェント（autoflow-planner ほか5つ）
install.py                           kit/ を対象のリポジトリの .autoflow/ と .claude/ に写す
scripts/structure_check.py           構造検査（structure のルールの大半）
scripts/gen_docs.py                  policy と profile の表から参照文書を生成する
tests/                               test_<モジュール>.py、support.py、fixtures/sample-repo/（見本のリポジトリ）
docs/design/                         設計文書（rules.md が正本）
```

モジュールの依存の許可表と、変更ごとに触るファイルは `docs/design/architecture.md` の4章と7章にある。

## 守ること

要約である。全文と理由は `docs/design/rules.md` にある。

- DEP-01: import は architecture.md の許可表の組だけ。段のモジュールどうしは import しない
- DEP-04: ファイルの書き込みは `fsops`、外部コマンドは `proc`、時刻と `print` は `cli` だけ
- CODE-06: ファイル名の文字列は `layout.py`、エージェント名は `contracts.AGENTS` に置き、置き場は `Layout` のメソッドで受け取る
- ERR-01: 投げる例外は `errors.py` の4つだけ
- ERR-02: 外から来る JSON は `workspace.load_*` で検証してから使う
- STATE-01: 段の進み具合は `trail.jsonl` だけに書き、次の段は `trail.next_step` が決める
- STATE-02: サブエージェントへの文章はひな形だけに書き、置き換えの値は `render` の関数で作る
- OPS-01: `status` の行は `status.LINE_KINDS` の書き出しで始める
- OPS-02: 実行の中の段は `context.begin` が返すプロファイルの写しだけを読む
- OPS-05: git への書き込みは `intake`（ブランチ）・`changes`（index）・`handoff`（コミット）だけ。リモートには送らない
- GATE-01: 関所の条件と表は `policy.py` だけに書き、規則を足したら `test_<規則の id>` を足す
- GATE-03: 段の入口の関数は最初の文で `context.begin(where, run_id, <段>)` を呼ぶ
- GATE-04・GATE-05: 検査コマンドは `verifying` だけが実行し、人の決定は `deciding` だけが記録する
- TEST-03: 名前を足したら、rules.md の表の置き場に `test_<足した名前>` を1つ足す
- PROC-02: 波及の対応表（rules.md の PROC-02）の組は同じ変更で一緒に変える
- 変えるファイルは、実装用スキルの patterns.md の当たった節の表にあるものと、そのテストだけにする。表に無いファイル（設計文書など）は変えずに報告に書く

## してはいけないこと

- 検査を通すために保護ファイルを変える。保護ファイルとは、検査の設定、`.foundation/`、`docs/design/rules.md` などで、一覧は `.foundation/manifest.json` の `protected` にある
- 抑止コメントを書く。lint 無効化や型無視などで、一覧は manifest の `guard.suppressions` にある
- 依頼に無い依存ライブラリを足す。標準ライブラリの表（DEP-03）も、依頼なしに広げない
- 見本（参照実装）と違う形の新しいパターンを作る。必要なら実装せずに、提案として報告する
- 人の関所を AI の判断で埋める処理を書く（回答の無い `decide`、AI の判定でリスクの段を下げる、承認の後の変更をコミットする）
- 配布物（`kit/`）に、権限を広げる設定（`bypassPermissions` など）や、リモートに送る処理を書く
- `.autoflow/runs/` の記録を書き換える・消す処理を書く（追記だけ）

## 完了の条件

1. `make check` が通る（PROC-05）
2. 実装用スキルの完了前チェックリストを満たす
3. 報告に、依頼から決まらなかった値とその根拠、check の結果の末尾を書く

## ルールを変えたいとき

ルールを勝手に変えない。変えるべき理由を報告し、承認されてから次の順で変える（PROC-04）。

1. ADR を書く
2. `docs/design/rules.md` を変える
3. 検査の設定と `.foundation/probes.json` を変える
4. 参照実装を変える
5. `python3 .foundation/bin/rules_check.py --root .` と `python3 .foundation/bin/violation_probe.py --root .` を通す
