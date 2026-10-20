# cli-design

CLI の「外から見える形」（コマンド、位置引数、オプション、出力、終了コード、環境変数）を、実装の言語に依存しない仕様 `specs/<name>/cli.json` として設計する基盤である。仕様は検査ツール `tools/clispec`（Python 3.14 の標準ライブラリだけ）で縛り、ヘルプの文面を含むリファレンス `cli.md` を生成し、各言語（Go・Python・Node.js・Rust など）の標準ライブラリで書いた実装を適合テストで確かめる。

## 作業の入口

| やること | 使うもの |
|---|---|
| 設計・変更・追加・修正・実装 | 実装用スキル `cli-design`（`.claude/skills/cli-design/SKILL.md`） |
| レビュー | レビュー用スキル `cli-design-review`（`.claude/skills/cli-design-review/SKILL.md`） |
| ルールを調べる | `docs/design/rules.md`（ルールIDで引く） |
| 構造の理由を調べる | `docs/design/architecture.md`、`docs/design/adr/` |
| 仕様を実装する | `.claude/skills/cli-design/references/stdlib-mapping.md` |

スキルを使えないエージェントは、上のファイルを直接読み、同じ手順に従う。

## 配布ZIPの検証

`ci.json`と`.ci/verify.py`は配布用の環境準備・検証の入口である（STR-01、ADR 0008）。CLI仕様を作る作者は引き続き下表のmakeターゲットを使う。ZIPの保守ではREADMEに従って`python3 .ci/verify.py`を実行する。

## コマンド

全部この基盤のルートで実行する。作者が使うのはこの表の `make` のターゲットだけである（TOOL-04）。

| 目的 | コマンド |
|---|---|
| 全検査（完了の条件） | `make check` |
| 自動修正（整形、版、`cli.md` の生成） | `make fix` |
| 新しい CLI | `make new NAME=<name>`（操作が1つなら `SINGLE=1`） |
| コマンドを足す | `make command NAME=<name> NOUN=<名詞> VERB=<動詞>`（新しい名詞の識別子が `name` なら `KEY=name`） |
| 項目を足す | `make field NAME=<name> NOUN=<名詞> FIELD=<項目名> TYPE=<型>`（`LIST=1`・`NULLABLE=1`・`VALUES=a,b`） |
| 版を確定する | `make release NAME=<name>` |
| 実装を確かめる | `make conform SPEC=specs/<name>/cli.json CMD="<起動コマンドの絶対パス>"` |
| 編集の直後（hooks が回す） | `make after-edit FILE=<path>` |

必要なもの：`uv`（`.python-version` の Python 3.14 を起動する）と `make`。依存のパッケージは無い。

## ディレクトリ構造

```text
cli-design/
├── specs/<name>/          CLI 1つの設計（STR-01）
│   ├── cli.json           仕様。作者が書くのはこれだけ
│   ├── cli.md             リファレンスとヘルプの文面（生成物。STR-04）
│   └── released/          リリース済みの仕様（変えない。STR-04）
├── specs/notes/           見本：サブコマンドを持つ CLI
├── specs/count-words/     見本：サブコマンドを持たない CLI
├── tools/clispec/         検査ツール・生成器・適合テスト（保護ファイル）
│   └── tests/fixtures/    見本の実装（Python argparse）
├── docs/design/           ルール、構造、調査、ADR
├── .claude/skills/        実装用・レビュー用スキル
└── .foundation/           基盤の検査スクリプトと manifest（保護ファイル）
```

## 守ること

要約である。全文と理由は `docs/design/rules.md` にある。

1. STR-01：CLI 1つにつき `specs/<name>/` に `cli.json`・`cli.md`・`released/` だけを置く
2. STR-02：新しい CLI・コマンド・項目は `make new`・`make command`・`make field` で始め、`cli.json` を白紙から書かない
3. STR-05：操作が1つならルートのコマンドだけ、2つ以上なら全コマンドを `<名詞> <動詞>` の2段にする
4. NAM-04：動詞は `create`・`list`・`view`・`edit`・`delete` を使い、`add`・`remove`・`show` などの同じ意味の語を使わない。識別子が `id` の名詞の `create` は位置引数を持たない
5. NAM-07：`create`・`edit` には全部の設定できる項目のオプションを、`edit` には空を許す・リスト・真偽値の項目の `--clear-<項目>` を、`list` には `--limit`・`--sort` を置き、オプション名は項目名から作る
6. CODE-04：summary は英語の1文で、標準の動詞・項目のオプションは表の決まった文にする
7. ERR-01：終了コードは 0〜4 だけにし、`exit_codes` は決定表の組にする
8. STATE-01：設定ファイル・対話の入力・色を持たず、値はオプション → 環境変数 → `default` で決める
9. STATE-02：実装は、標準の動詞の振る舞い（絞り込みは AND、`edit` は置き換え、`null` は並べ替えの末尾、消した `id` を再利用しない など）を決定表のとおりにする
10. PROC-06：版は `make fix` が決める。リリース済みの公開面を消す・変えるときはユーザーの承認を ADR に書く
11. DEP-03・DEP-04：実装の引数解析は各言語の標準ライブラリだけで行い、`references/stdlib-mapping.md` の共通の処理で解析器の差を埋める
12. OPS-05：実装は `cli.md` のヘルプの文面を1文字も変えずに stdout に出す
13. TEST-01：仕様は `make check`、実装は `make conform` で確かめる。仕様のためのテストを書かない
14. PROC-01：設計は「書き出す → `make new` → `make command` → `make field` → `TODO` と既定値 → 環境変数 → `make fix` → `make check`」の順に作る
15. TOOL-02：`cli.json` を編集した直後は hooks の `make after-edit` の指摘を直し、完了の前に `make check` を回す
16. PROC-03：検査ツールの Python・uv の版は、research.md → `.python-version` → `make check` と probe → ADR 0003 の順で上げる

## してはいけないこと

- 検査を通すために保護ファイルを変える。保護ファイルとは、`Makefile`、`tools/`、`specs/*/released/`、`.foundation/`、`docs/design/rules.md` などで、一覧は `.foundation/manifest.json` の `protected` にある
- 抑止の書き方を使う。仕様に表に無いキー（`x-`、`_`、`$comment`）を書く、Python に `# noqa` やテストの skip を書く（TOOL-03）。一覧は manifest の `guard.suppressions` にある
- 依頼に無い依存ライブラリを足す。実装の引数解析に cobra・click・commander・clap などを使う（DEP-04）
- 見本（`specs/notes`、`specs/count-words`）と違う形の新しいパターンを作る。必要なら実装せずに、提案として報告する
- `cli.md` を手で直す、`released/` のファイルを変える・消す（STR-04）
- 依頼がリリースを求めていないのに `make release` を回す
- 依頼に無いコマンド・項目・オプションを足す

## 完了の条件

1. `make check` が通る（実装の依頼では `make conform` も全項目通る）
2. 実装用スキルの完了前チェックリストを満たす
3. 報告に、依頼から決まらなかった値とその根拠、check の結果を書く（PROC-05）

## ルールを変えたいとき

ルールを勝手に変えない。変えるべき理由を報告し、承認されてから次の順で変える（PROC-04）。

1. ADR を書く
2. `docs/design/rules.md` を変える
3. `tools/clispec` と `.foundation/probes.json` を変える
4. 見本の仕様（`specs/notes`、`specs/count-words`）と見本の実装を変える
5. `make check`、`python3 .foundation/bin/rules_check.py --root .`、`python3 .foundation/bin/violation_probe.py --root .` を通す
