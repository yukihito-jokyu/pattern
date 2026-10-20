# cli-design のアーキテクチャ

この文書は、構造そのものと、その構造を選んだ理由を説明する。個々のルールの全文は [rules.md](rules.md) にある。

## 1. 前提

この基盤で作るものは、CLI の**実装**ではなく**設計**（外から見える形）である。前提は次の4つである。

1. **実装の言語を決めない**。ユーザーの指示は「設計なので、どの言語でも対応可能とする」である。そのため、設計の成果物は特定の言語のコードではなく、言語に依存しない仕様ファイル（`cli.json`）にする
2. **実装の引数解析は標準ライブラリだけで行う**。ユーザーの指示である。調査（[research.md「引数解析器の実測」](research.md)）で、Go の `flag`、Python の `argparse`、Node.js の `util.parseArgs` は、同じ入力でも結果が違う書式があると分かった（`-name value` など）。そこで仕様が約束する書式を、全解析器で同じ結果になる共通部分に限る（DEP-03）
3. **どの言語で実装しても配布できる**。ユーザーの指示である。CLI 名と版を、Go・PyPI・npm・crates.io・Homebrew のどれでも使える形に限る（OPS-06）
4. **誰が設計しても同じ仕様になる**。この基盤のゴールである。仕様の形式に自由な書き方を残さず（CODE-01）、名前と文面を表から導き（NAM-02〜NAM-07、CODE-04）、版を差分から計算する（PROC-06）

この前提から、仕様（設計）と実装の間に次の2つの橋を置く。

- **リファレンス**（`cli.md`）：仕様から生成した、ヘルプの文面を含む文書。全実装が同じ文面を出す（OPS-05）
- **適合テスト**（`tools/clispec conform`）：実装を外から実行し、仕様どおりかを確かめる。ヘルプ・終了コード・出力の形に加え、標準の動詞の振る舞い（STATE-02）も、空のデータの置き場で行を作って確かめる。実装の言語を問わない（TEST-01）

よく起きる変更は、新しい CLI の設計、既存の CLI へのコマンド・オプション・項目の追加、リリース（版の確定）である。触るのは主に作者（人とエージェント）で、実装者はリファレンスと適合テストを使う。

## 2. ディレクトリ構造

```text
cli-design/
├── AGENTS.md / CLAUDE.md / README.md
├── ci.json                      ZIP検証の環境と実行コマンド
├── .ci/verify.py                 ZIP単体での準備・検証
├── Makefile                      唯一の入口（TOOL-04）
├── .python-version               検査ツールの Python の版（TOOL-04）
├── .editorconfig                 エディタの設定（TOOL-01）
├── specs/                        設計の置き場。CLI 1つにディレクトリ1つ（STR-01）
│   ├── notes/                    見本：サブコマンドを持つ CLI
│   │   ├── cli.json              仕様（作者が書く）
│   │   ├── cli.md                リファレンス（生成物。STR-04）
│   │   └── released/1.0.0.json   リリース済みの仕様（変えない。STR-04）
│   └── count-words/              見本：サブコマンドを持たない CLI
├── tools/clispec/                検査ツール（Python の標準ライブラリだけ）
│   ├── __main__.py               検査ツールのコマンドの振り分け
│   ├── vocab.py                  表：標準の動詞・オプション、略語、終了コード、型
│   ├── model.py                  仕様の読み込み、キーの順、並べ替え、導出（PREFIX、複数形、暗黙のオプション、項目のオプション）
│   ├── canon.py                  正規の JSON の文字列にする
│   ├── check.py                  ルールの検査（ルールIDを付けてエラーを出す）
│   ├── compat.py                 リリース済みの仕様との差分と、期待する版
│   ├── helptext.py               ヘルプの文面とテキストの表の生成
│   ├── gen.py                    リファレンス（cli.md）の生成
│   ├── scaffold.py               生成器（new、command、field）
│   ├── conform.py                適合テスト
│   └── tests/                    unittest と見本の実装（fixtures/notes_impl.py、fixtures/count_words_impl.py）
├── docs/design/                  この基盤の設計文書
└── .claude/skills/
    ├── cli-design/               実装用スキル（設計の手順）と、言語ごとの実装の対応表
    └── cli-design-review/        レビュー用スキル
```

作者が触るのは `specs/<name>/cli.json` だけである。`cli.md` は生成し、`released/` は `make release` が作る。`tools/` と設定ファイルは保護ファイルで、ルールを変えるとき（PROC-04）だけ変える。

## 3. 依存の許可表

### 3.1 仕様の中の参照

仕様の中で参照してよいのは、コマンドから型への参照だけである（DEP-01、STR-03）。

| from \ to | コマンド | 型 | 環境変数 | 別の仕様 |
|---|---|---|---|---|
| コマンド | | ✓（`output.type`） | | |
| 型 | | | | |
| 環境変数 | | | | |

環境変数とオプションの対応（STATE-01）と、オプションと項目の対応（NAM-07）は参照ではなく名前の規則であり、`tools/clispec check` が名前の一致を検査する。

### 3.2 検査ツールのモジュール

行のモジュールから、列のモジュールを import してよい組に ✓ を付ける。保護ファイルの中の構造であり、ルールを変えるとき（PROC-04）の手がかりとして示す。

| from \ to | vocab | canon | model | compat | helptext | check | gen | scaffold | conform |
|---|---|---|---|---|---|---|---|---|---|
| vocab | | | | | | | | | |
| canon | | | | | | | | | |
| model | ✓ | ✓ | | | | | | | |
| compat | ✓ | | ✓ | | | | | | |
| helptext | ✓ | | ✓ | | | | | | |
| check | ✓ | ✓ | ✓ | ✓ | | | | | |
| gen | ✓ | | ✓ | | ✓ | | | | |
| scaffold | ✓ | ✓ | ✓ | | | | | | |
| conform | ✓ | | ✓ | | ✓ | | | | |

`__main__.py` は全部を import してよい。表は vocab（表）→ model（仕様の読み方）→ 各機能、の一方向で、機能どうしは helptext を除いて import しない。ヘルプの文面を `gen`（リファレンス）と `conform`（適合テスト）が同じ関数から作るので、両者の期待する文面が食い違わない。

## 4. 公開面

| モジュール | 外から使ってよいもの | 触れなくする仕組み |
|---|---|---|
| 仕様（`cli.json`） | 全部（CLI の公開面そのもの。DEP-02） | — |
| リファレンス（`cli.md`） | 全部（実装者が読み、ヘルプの文面を写す） | 生成物のヘッダー、`gen --check`（STR-04） |
| リリース済みの仕様 | 読むことだけ | 保護ファイル（manifest の `protected`）、レビュー |
| `Makefile` | `check`、`fix`、`new`、`command`、`field`、`release`、`conform`、`after-edit` | 保護ファイル。ほかのターゲットは内部用 |
| `tools/clispec` | `Makefile` から呼ばれるコマンドだけ | 保護ファイル。作者は Makefile だけを使う（TOOL-04） |

CLI の公開面（DEP-02）は、コマンド、位置引数、オプション（暗黙のオプションを含む）、`--json` の出力、終了コード、環境変数、データの置き場である。テキストの表は人向けの出力であり、公開面に含めない（[research.md「Command Line Interface Guidelines」](research.md) の "Changing output for humans is usually OK."）。

## 5. データの流れ

### 5.1 設計（作者）

```text
依頼 ─→ 操作と名詞を書き出す（STR-05）
     ─→ make new / make command / make field（生成器。STR-02）
     ─→ cli.json を編集（TODO と既定値 → 絞り込みなどのオプション → 環境変数。PROC-01）
     ─→ hooks: make after-edit（fmt → 版 → gen → その仕様の check。TOOL-02）
     ─→ make check（全仕様の fmt・check・gen、unittest、guard、rules_check）
     ─→ 公開するとき make release（released/<version>.json を作る）
```

### 5.2 実装（実装者、この基盤の外）

```text
cli.json と cli.md ─→ references/stdlib-mapping.md の言語の節に従って実装する
                  ─→ make conform SPEC=specs/<name>/cli.json CMD="<起動コマンド>"
                       ├ 全コマンドの --help・-h がリファレンスの文面と一致するか（OPS-05）
                       ├ --version が "<name> <version>" か（OPS-05）
                       ├ 未知のオプション・前方一致・不正な値が 2 で、stderr が1行か（ERR-02、ERR-03、DEP-02）
                       ├ 型から作った値で実行し、--json の形と終了コードが宣言どおりか（OPS-04、ERR-01）
                       └ 成功時の stderr が空で、ESC を出さないか（OPS-01）
```

適合テストは、実装の環境変数 `HOME`・`XDG_DATA_HOME`・`<PREFIX>_DATA_DIR` を一時ディレクトリに向けて実行するので、利用者のデータに触れない。

## 6. 変更シナリオ表

| 変更 | 触るファイル | 触らないもの |
|---|---|---|
| 新しい CLI を設計する | `specs/<name>/cli.json`（`make new`）、`specs/<name>/cli.md`（生成） | ほかの CLI、`tools/` |
| 既存の CLI にコマンドを足す | `specs/<name>/cli.json`（`make command`。版は `make fix` がマイナーで上げる）、`cli.md` | `released/`、ほかの CLI |
| コマンドに任意のオプションを足す | `specs/<name>/cli.json`（オプション、版）、`cli.md` | ほかのコマンド |
| 型に項目を足す | `specs/<name>/cli.json`（`make field` が項目、`create`・`edit` のオプション、`list` の `sort` を足す。版は `make fix`）、`cli.md` | 出力の種類、終了コード |
| 公開面を消す・名前を変える | `specs/<name>/cli.json`（版をメジャーで上げる）、`cli.md`、`docs/design/adr/NNNN-*.md`（承認の記録） | `released/` |
| 公開する（版を確定する） | `specs/<name>/released/<version>.json`（`make release`） | `cli.json` |
| 実装を確かめる | なし（`make conform` は何も書かない） | この基盤の全部 |
| ルール・標準の表を変える | `docs/design/adr/`、`docs/design/rules.md`、`tools/clispec/*.py`、`.foundation/probes.json`、`specs/notes`・`specs/count-words`、見本の実装 | 作者が作った仕様（新しいルールで落ちるなら、別の作業として直す） |
| 検査ツールの Python の版を上げる | `docs/design/research.md`、`.python-version`、`docs/design/adr/0003-*.md` | `tools/clispec` のコード |
