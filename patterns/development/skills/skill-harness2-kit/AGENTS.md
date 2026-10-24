# skill-harness2-kit

利用者のリポジトリにある Claude Code スキル1つを、google-research/harness2 の方法で改善する道具一式である。方法は、基準の実行、INV と DOM の2つの次元の提案、候補の試行、根拠のある編集だけの合成、匿名の選択、振り返りとライブラリの順に進む。配布するスキル `skill-harness2` と、Python 3.9 の標準ライブラリだけで動く補助 CLI（`.h2/h2.py`）からなり、`install.py` で利用者のリポジトリに入れる。モデルの呼び出しはすべて `claude -p` を閉じ込めて行い、正解や採点は方法に入れない。

## 作業の入口

| やること | 使うもの |
|---|---|
| 実装・変更・追加・修正 | 実装用スキル `impl`（`.claude/skills/impl/SKILL.md`） |
| レビュー | レビュー用スキル `review`（`.claude/skills/review/SKILL.md`） |
| ルールを調べる | `docs/design/rules.md`（ルールIDで引く） |
| 構造の理由を調べる | `docs/design/architecture.md`、`docs/design/adr/` |
| harness2 のどの仕組みをどこに移したかを調べる | `docs/design/research.md` の「harness2 の仕組み」の表 |

スキルを使えないエージェントは、上のファイルを直接読み、同じ手順に従う。

## コマンド

| 目的 | コマンド |
|---|---|
| 全検査（完了の条件） | `make check` |
| 自動修正 | `make fix` |
| 1ファイルの整形と lint（hooks が呼ぶ） | `make fix-file FILE=<パス>` |
| テストだけ | `make test` |
| 構造検査だけ | `make structure` |
| 配布物を入れる | `python3 install.py <利用者のリポジトリ>` |

依存の導入は要らない。`make` が ruff と mypy を `uvx` で版を固定して呼ぶ（uv が要る）。テストは `claude` の代わりに `tests/fixtures/fake_claude.py` を動かすので、`claude` もネットワークも要らない。

## ディレクトリ構造

```text
kit/.h2/h2.py                     補助 CLI の入口（cli.main を呼ぶだけ）
kit/.h2/h2_kit/                   補助 CLI のモジュール（共有・段・入口。許可表は architecture.md）
kit/.h2/templates/prompts/        編集・合成・選択・振り返りのプロンプトのひな形（harness2 の文を日本語に移したもの）
kit/claude/skills/skill-harness2/ 配布するスキル（SKILL.md と references/）
install.py                        配布物を利用者のリポジトリに入れる
scripts/structure_check.py        構造検査
tests/                            テスト（test_<モジュール>.py、support.py、fixtures/ の偽の claude と見本のスキル）
docs/design/                      設計文書
.foundation/                      ルールの検査の道具と probe（保護ファイル）
```

## 守ること

要約である。全文と理由は `docs/design/rules.md` にある。

- STR-01：ファイルは rules.md の置き場の表の場所に置き、`h2_kit` にサブディレクトリを作らない
- DEP-01：`h2_kit` の import は architecture.md の許可表の組だけ。段のモジュールどうしは import せず、事後の検査（`judging`）を方法のモジュールから import しない
- DEP-04：ファイルの書き込みは `fsops`、外部コマンドは `proc`、スレッドは `parallel`、時刻・画面への出力は `cli` だけ
- NAM-02：関数名は動詞表の語で始め、段のモジュールの公開関数はサブコマンド名にする
- CODE-01：クラスは基底の無い `@dataclass(frozen=True)` だけ（例外は `errors.py`）
- CODE-06：ファイル名・ラベル（`base`、`inv`、`dom`、`agg`、`c`）・モード名は `layout` の定数を使う
- ERR-01：投げる例外は `errors.py` の5つだけ。`except` は表の場所だけ
- STATE-02：プロンプトの文はひな形だけに書き、返答のタグは `contracts.py` だけに書く
- STATE-03：証拠は `context/` のファイルで全部渡し、プロンプトは道案内だけにする
- STATE-04：方法（提案・合成・選択）に、正解・採点の基準・`checks.json` を入れない。方法のモジュールは事後の検査の記録（`judged.json`）に触れない
- STATE-05：選択は完成品の成果物だけを匿名の ID で比べる
- STATE-06：候補は実行の前に `validate.check_tree` で検証し、1回だけ差し戻し、落ちたら入力の木に戻す
- STATE-07：モードの要約を書く前に、台帳で R = 4k、P = 3k を確かめる
- OPS-04：実行・採用・事後の検査の段は、最初に `workspace.load_approved` を呼ぶ
- OPS-05：`claude` のコマンド行は `runner` だけで組み立て、閉じ込めのフラグを外さない

## してはいけないこと

- 検査を通すために保護ファイルを変える。保護ファイルとは、検査の設定、`.foundation/`、`docs/design/rules.md` などで、一覧は `.foundation/manifest.json` の `protected` にある（TOOL-04）
- 抑止コメントを書く。lint 無効化、型無視、テストの skip などで、一覧は manifest の `guard.suppressions` にある（TOOL-03）
- 依頼に無い依存ライブラリを足す（DEP-03）
- 見本（参照実装）と違う形の新しいパターンを作る。必要なら実装せずに、提案として報告する
- `unittest.mock` で `claude` や関数を差し替える。偽の振る舞いは `tests/fixtures/fake_claude.py` の `behavior=` に足す（TEST-02）
- 方法のモジュールやひな形に、採点の語や採点の出力の印を書く。`guards` の表を広げて印を黙らせない（STATE-04）
- `--dangerously-skip-permissions` など、閉じ込めを緩めるフラグを足す（OPS-05）

## 完了の条件

1. `make check` が通る（PROC-05）。Python のファイルを編集した直後は hooks が `make fix-file` を回し、完了の前に `make check` を回す（TOOL-02）
2. 実装用スキルの完了前チェックリストを満たす
3. 報告に、依頼から決まらなかった値とその根拠、check の結果を書く

サブコマンドを足すときは、`layout.py` → `workspace.py` → 段のモジュール → `status.py` → `cli.py` → テスト → `structure_check.py` の表と architecture.md の許可表 → SKILL.md の表、の順に作る（PROC-01）。

## ルールを変えたいとき

ルールを勝手に変えない。変えるべき理由を報告し、承認されてから次の順で変える（PROC-04）。

1. ADR を書く
2. `docs/design/rules.md` を変える
3. 検査の設定と `.foundation/probes.json` を変える
4. 参照実装を変える
5. `python3 .foundation/bin/rules_check.py --root .` と `python3 .foundation/bin/violation_probe.py --root .` を通す
