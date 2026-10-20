# orch-forge-kit

任意のリポジトリに、開発用のオーケストレーションスキル（メインのセッションで動き、Agent ツールで役ごとのサブエージェントを起動して実装を進めるスキル）を作り、人と決めたゴールと指標で評価して改善する道具一式（cli-library）。配布物は Python 3.9 の標準ライブラリだけで動く補助 CLI、スキル3つ（forge-goals、forge-build、forge-run）、サブエージェント4つ（設計役・構築役・採点役・分析役）で、評価の実行役は補助 CLI が起動する `claude -p` である。`install.py` が対象のリポジトリへ入れる。

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
| 自動修正 | `make fix` |
| 1ファイルの整形と lint（hooks が呼ぶ） | `make fix-file FILE=<パス>` |
| テストだけ | `make test` |
| 1つのテストのファイルだけ | `PYTHONPATH=kit/.forge python3 -B -m unittest tests.test_<モジュール>` |
| 構造検査だけ | `make structure` |
| 生成物（指標の一覧、バンドルの決まり）を作り直す | `make docs` |
| 対象のリポジトリに入れる | `python3 install.py --dest <リポジトリ>` |

依存の導入は要らない。`python3`（3.9 以上）、`git`、`uv`（`uvx` で ruff と mypy を版を固定して呼ぶ）があればよい。道具の版を上げるときは ADR を書いてから `Makefile` を変える（PROC-03）。Python のファイルを編集した直後は hooks が `make fix-file` を回し、完了の前に `make check` を回す（TOOL-02）。

## ディレクトリ構造

```text
kit/.forge/forge.py              補助 CLI の入口（配布先の .forge/forge.py）
kit/.forge/forge_kit/            補助 CLI のモジュール。段のモジュールと共有のモジュールを平らに並べる
kit/.forge/templates/prompts/    サブエージェントと実行役へのプロンプトのひな形
kit/claude/skills/forge-*/       配布するスキル（配布先の .claude/skills/）
kit/claude/agents/               配布するサブエージェント（配布先の .claude/agents/）
install.py                       配布物を対象のリポジトリに入れる
scripts/                         構造検査（structure_check.py）と生成器（gen_docs.py）
tests/                           テスト（test_<モジュール>.py、support.py、fixtures/sample-repo/、fixtures/streams/）
docs/design/                     設計文書。overview.md から読む
```

## 守ること

要約である。全文と理由は `docs/design/rules.md` にある。

- DEP-01：段のモジュールは他の段のモジュールを import しない。import は architecture.md の許可表の組だけ
- DEP-04：ファイルを書くのは `fsops`、外部コマンド（git、`claude -p`）は `proc`、時刻と画面への出力は `cli` だけ
- ERR-01：投げる例外は `errors.py` の4つだけ。捕まえるのは `cli.main`
- ERR-02：外から来る JSON は `workspace` の `load_*` で検証してから使う
- STATE-02：プロンプトの文章は `templates/prompts/` のひな形だけに書き、`prompts.TEMPLATES` と置き換えの名前をそろえる。置き換えの値に文を書かない（無い値は `render.MISSING`、一覧は `render.bullets`）
- OPS-01：結果は標準出力、エラーは `エラー: ` を付けて標準エラー、終了コードは 0 と 1。`status` の行は `status.LINE_KINDS` の書き出しだけを使い、人が決める値はコマンドの中に `'<日本語の名前>'` で置く
- OPS-04：設計・構築・評価を進める段の入口は、最初に `workspace.approved_charter` を呼ぶ。対象のリポジトリの `.claude/` に書く `bundle.place` は `building.install` と `decide.decide` だけが呼ぶ
- OPS-05：`claude -p` の引数は `execute.command` だけで組み立てる。権限を広げる引数（`bypassPermissions` ほか）を `kit/` に書かない
- CODE-06：ファイル名の文字列は `layout.py`、エージェント名は `contracts.AGENTS` の定数を使う
- STR-05：配布するスキルは `disable-model-invocation: true`、サブエージェントの `tools` に `Skill` と `Agent` を入れない
- STR-06：生成・改善するバンドルの形の決まりは `bundle.RULES` の表だけに書く。ひな形とスキルは `bundle-rules.md` を読ませる
- PROC-07：人が決める場面（ゴール、指標、評価課題、承認、採否）はスキルの「## 人に確かめること」に書く。選ぶ値は AskUserQuestion、人の言葉を残す値は文章で聞く
- TEST-02：テストでモックを使わず、`tests/support.py` の部品（`make_repo`、`fake_launcher` ほか）と本物の git を使う
- TEST-03：新しい名前（指標の id、バンドルの決まりの id、置き換えの名前、引数、charter・設計の項目）を足したら、rules.md の表の置き場に `test_<名前>` を1つ足す
- PROC-02：波及の対応表の組（指標と計算、決まりとテスト、ひな形と表、エージェントと定義、charter・設計のキーとスキーマの文書）は同じ変更で変える

## してはいけないこと

- 検査を通すために保護ファイルを変える。保護ファイルとは、検査の設定、`.foundation/`、`docs/design/rules.md` などで、一覧は `.foundation/manifest.json` の `protected` にある（TOOL-04）
- 抑止コメントを書く。lint 無効化や型無視などで、一覧は manifest の `guard.suppressions` にある（TOOL-03）
- 依頼に無い依存ライブラリを足す（DEP-03）
- 見本（参照実装）と違う形の新しいパターンを作る。必要なら実装せずに、提案として報告する
- 生成物（`metric-catalog.md`、`bundle-rules.md`、`enforcement-matrix.md`）を手で直す（STR-04）
- 配布するスキルの手順を、補助 CLI の `status` の出力と食い違う形に変える。スキルは `status` の指示に従うだけにする
- テストや開発中に本物の `claude -p` を起動する。テストでは `support.fake_launcher` が記録した実行の記録（`tests/fixtures/streams/`）を返す（TEST-02）

## 完了の条件

1. `make check` が通る（PROC-05）
2. 実装用スキルの完了前チェックリストを満たす
3. 報告に、依頼から決まらなかった値とその根拠、check の結果を書く

## ルールを変えたいとき

ルールを勝手に変えない。変えるべき理由を報告し、承認されてから次の順で変える（PROC-04）。

1. ADR を書く
2. `docs/design/rules.md` を変える
3. 検査の設定と `.foundation/probes.json` を変える
4. 参照実装を変える
5. `python3 .foundation/bin/rules_check.py --root .` と `python3 .foundation/bin/violation_probe.py --root .` を通す
