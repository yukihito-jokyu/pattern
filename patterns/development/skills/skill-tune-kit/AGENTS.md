# skill-tune-kit

既存の Claude Code スキルを、評価データ（学習用・検証用・テスト用）で測りながら改善する道具一式である。配布するスキル `skill-tune` と4つのサブエージェント、Python 3.9 の標準ライブラリだけで動く補助 CLI（`.tune/tune.py`）からなり、`install.py` で利用者のリポジトリに入れる。

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
| 検査の種類の一覧（生成物）を作り直す | `make docs` |
| テストだけ | `make test` |
| 構造検査だけ | `make structure` |
| 配布物を入れる | `python3 install.py <利用者のリポジトリ>` |

依存の導入は要らない。`make` が ruff と mypy を `uvx` で版を固定して呼ぶ（uv が要る）。

## ディレクトリ構造

```text
kit/.tune/tune.py              補助 CLI の入口（cli.main を呼ぶだけ）
kit/.tune/tune_kit/            補助 CLI のモジュール（共有・段・入口。許可表は architecture.md）
kit/.tune/templates/prompts/   サブエージェントへのプロンプトのひな形
kit/claude/skills/skill-tune/  配布するスキル（SKILL.md と references/）
kit/claude/agents/             配布するサブエージェント（tune-executor、tune-grader、tune-learner、tune-auditor）
install.py                     配布物を利用者のリポジトリに入れる
scripts/                       構造検査（structure_check.py）と生成器（gen_docs.py）
tests/                         テスト（test_<モジュール>.py、support.py、fixtures/）
docs/design/                   設計文書
.foundation/                   ルールの検査の道具と probe（保護ファイル）
```

## 守ること

要約である。全文と理由は `docs/design/rules.md` にある。

- STR-01：ファイルは rules.md の置き場の表の場所に置き、`tune_kit` にサブディレクトリを作らない
- DEP-01：`tune_kit` の import は architecture.md の許可表の組だけ。段のモジュールどうしは import しない
- DEP-03：import してよいのは Python 3.9 の標準ライブラリ（`STDLIB` 表）と `tune_kit` だけ
- DEP-04：ファイルの書き込みは `fsops`、外部コマンドは `proc`、時刻・画面への出力・終了コードは `cli` だけ
- NAM-02：関数名は動詞表の語で始め、段のモジュールの公開関数はサブコマンド名にする
- CODE-01：クラスは基底の無い `@dataclass(frozen=True)` だけ（例外は `errors.py`）
- CODE-03：全関数に型注釈を書き、mypy strict（Python 3.9）を通す
- CODE-06：ファイル名は `layout`、エージェント名は `contracts.AGENTS` の定数を使う
- ERR-01：投げる例外は `errors.py` の4つだけ。`except` は表の場所だけ
- ERR-02：外から来る JSON は `workspace.load_*` で検証してから使う
- STATE-01：状態ファイルを作らない。進み具合は `workspace` がファイルから求める
- STATE-03：学習役には学習用だけを見せ、テスト用は最後の評価でだけ使う
- OPS-01：`status` の各行は `status.LINE_KINDS` の書き出しで始める
- OPS-04：評価を進める段の公開関数は、最初に `workspace.load_approved` を呼ぶ
- TEST-02：モックを使わず、`tests/support.py` の部品と一時ディレクトリと本物の git で確かめる

## してはいけないこと

- 検査を通すために保護ファイルを変える。保護ファイルとは、検査の設定、`.foundation/`、`docs/design/rules.md` などで、一覧は `.foundation/manifest.json` の `protected` にある（TOOL-04）
- 抑止コメントを書く。lint 無効化、型無視、テストの skip などで、一覧は manifest の `guard.suppressions` にある（TOOL-03）
- 依頼に無い依存ライブラリを足す（DEP-03）
- 見本（参照実装）と違う形の新しいパターンを作る。必要なら実装せずに、提案として報告する
- 生成物（`kit/claude/skills/skill-tune/references/check-kinds.md`、`docs/design/enforcement-matrix.md`）を手で編集する（STR-04）
- サブエージェントの出力ファイルの名前に `report` を含める。サブエージェントは書けない（STATE-02）
- プロンプトの文を Python のコードに書く。文はひな形（`kit/.tune/templates/prompts/`）だけに書く（STATE-02）

## 完了の条件

1. `make check` が通る（PROC-05）。Python のファイルを編集した直後は hooks が `make fix-file` を回し、完了の前に `make check` を回す（TOOL-02）
2. 実装用スキルの完了前チェックリストを満たす
3. 報告に、依頼から決まらなかった値とその根拠、check の結果を書く

サブコマンドを足すときは、`layout.py` → `contracts.py` → 段のモジュール → `status.py` → `cli.py` → テスト → `structure_check.py` の表と architecture.md の許可表 → SKILL.md の表、の順に作る（PROC-01）。

## ルールを変えたいとき

ルールを勝手に変えない。変えるべき理由を報告し、承認されてから次の順で変える（PROC-04）。

1. ADR を書く
2. `docs/design/rules.md` を変える
3. 検査の設定と `.foundation/probes.json` を変える
4. 参照実装を変える
5. `python3 .foundation/bin/rules_check.py --root .` と `python3 .foundation/bin/violation_probe.py --root .` を通す
