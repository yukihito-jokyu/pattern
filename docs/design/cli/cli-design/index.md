---
title: CLIの外部仕様をJSONで設計する
description: コマンド・引数・出力・終了コードを言語に依存しない仕様にまとめ、ヘルプ生成と適合テストで実装の振る舞いをそろえるパターン。
slug: /design/cli/cli-design
pattern:
  features:
    - label: 設計
      value: JSON仕様と生成リファレンス
    - label: 検査
      value: 仕様検査と実装の適合テスト
    - label: 見本
      value: メモ管理と単語集計
---

# CLIの外部仕様をJSONで設計する

CLIは、ターミナルからコマンドと引数を渡して実行するプログラムです。人が使うだけでなく、シェルスクリプトも出力や終了コードを読み取ります。そのため、同じ操作でも作者によってコマンド名、JSONの形、エラーの扱いが変わると、利用する側の手順も変わります。

このパターンでは、その外部仕様を`specs/<name>/cli.json`にまとめます。生成器で仕様を作り、リファレンスとヘルプの文面を生成し、別途作ったCLIを適合テストで実行して仕様と照合します。実装言語を選ぶ前に、利用者から見える振る舞いを決められる構成です。

同梱する見本は、メモとタグを管理する`notes`、ファイル内の単語を集計する`count-words`です。検査ツールと見本の実装はPythonの標準ライブラリだけで動きます。Go・Python・Node.js・Rustで実装するための対応表も同梱しますが、各言語のCLI本体を自動生成するものではありません。

## 全体像

ZIPを展開すると、次の構造になります。設計するCLIの仕様は`specs/`、仕様を検査するプログラムは`tools/clispec/`に分かれています。

```text
cli-design/
├── README.md                    環境・使用・検証の手順
├── AGENTS.md / CLAUDE.md         エージェント向けの作業規約
├── Makefile / .python-version   操作の入口とPythonの系列
├── specs/
│   ├── notes/
│   │   ├── cli.json              メモ管理の外部仕様
│   │   ├── cli.md                仕様から生成するリファレンス
│   │   └── released/1.0.0.json   互換性比較の基準
│   └── count-words/              単語集計の同じ3種類のファイル
├── tools/clispec/
│   ├── scaffold.py              CLI・コマンド・項目の生成器
│   ├── model.py / vocab.py      仕様の読み方と共通の決定表
│   ├── check.py / canon.py      仕様検査と正規のJSON表記
│   ├── helptext.py / gen.py     ヘルプとリファレンスの生成
│   ├── compat.py                公開済み仕様との互換性比較
│   ├── conform.py               実装を外から実行する適合テスト
│   └── tests/fixtures/          見本2種類のPython実装
├── docs/design/                 ルール・構造・判断理由・開発記録
├── .claude/                     設計・レビュースキルとhooks
├── .foundation/                 ルール検査・違反例・評価資料
├── ci.json                      ZIP検証の環境とコマンド
└── .ci/verify.py                 ZIP内で完結する準備・検証
```

作者は`make new`・`make command`・`make field`で仕様を作り、依頼に合わせて必要な値を決めます。`make fix`が整形と版計算を行い、`cli.md`を生成します。`make check`で仕様と生成物の整合を確認してから、実装者がその仕様に従ってCLIを作り、`make conform`で確かめます。

この順序にする理由は、実装ごとにCLIの形を決め直さないためです。例えば`notes note list --json`の結果はJSON配列と決め、その1行が持つ項目を型に定義します。Pythonで書いても別の言語で書いても、この約束を適合テストの共通の期待値にできます。

## 1. 仕様がコマンドの形を決める

### 仕様全体の7つのキー

`specs/count-words/cli.json`は次の値から始まります。配列の中身は後の節で説明します。

```json
{
  "name": "count-words",
  "version": "1.0.0",
  "summary": "Count words in files",
  "storage": "none"
}
```

これは先頭部分の抜粋です。実ファイルには続けて`commands`・`types`・`env`があり、7つのキーをすべて指定します。任意のキー省略を許すと、同じ設計でも書き方が変わるためです。未知のキーも検査で拒否します。

| キー | 役割とこの見本での動作 |
| --- | --- |
| `name` | 起動名と仕様ディレクトリ名。`count-words`はヘルプ・版表示・エラー接頭辞に使い、環境変数の接頭辞は`COUNT_WORDS`になる |
| `version` | 利用者に見せる版。初版は`1.0.0`で、公開済み仕様があれば差分から次の版を計算する |
| `summary` | ヘルプに載せる英語の説明。既定値や必須条件は別のキーに書き、文と設定の二重管理を避ける |
| `storage` | `none`は管理データを保存しないCLI、`data`は管理データを保存するCLI。単語集計は`none`、メモ管理は`data` |
| `commands` | 操作ごとのパス・入力・出力・終了コード。単語集計はルート操作1つ、メモ管理は名詞と動詞の組 |
| `types` | JSON出力1件分の項目。単語集計では`word_count`、メモ管理では`note`と`tag` |
| `env` | 許可する環境変数。単語集計では最小文字数、メモ管理ではデータ保存先を指定する |

CLI名は小文字・数字・ハイフンで2〜20文字とし、英字で始めます。出力項目名は`created_at`のようなsnake_case、オプションは`--min-length`のようなkebab-case、環境変数は大文字とアンダースコアにします。名前から役割を読み取れ、環境変数名も機械的に導ける形です。

`summary`は大文字で始まるASCIIの英語で、末尾のピリオドを付けず60文字以内にします。標準の操作には`Create a note`のような決まった文を使います。これはこのパターンの規約であり、CLI全般に英語を必須とする標準ではありません。

### 操作が1つならルート、複数なら名詞と動詞

`specs/notes/cli.json`の`commands`から、メモ作成の要素を抜粋します。

```json
{
  "commands": [
    {
      "path": ["note", "create"],
      "summary": "Create a note",
      "args": [],
      "options": [
        {
          "name": "tag",
          "type": "string",
          "values": [],
          "default": null,
          "required": false,
          "repeatable": true,
          "summary": "Tag of the note"
        },
        {
          "name": "title",
          "type": "string",
          "values": [],
          "default": null,
          "required": true,
          "repeatable": false,
          "summary": "Title of the note"
        }
      ],
      "output": {"kind": "object", "type": "note"},
      "exit_codes": [0, 1, 2]
    }
  ]
}
```

`path`が`["note", "create"]`なので、起動名と合わせて`notes note create`になります。`args`が空なのは、作成時の整数IDを利用者が指定しないためです。タイトルは必須オプション、タグは省略できる繰り返しオプションなので、例えば`notes note create --title "Read book" --tag home --tag study`という形になります。

操作を名詞の下へ集めるため、メモの作成・一覧・参照・編集・削除は`note create`・`note list`・`note view`・`note edit`・`note delete`に統一します。同じ意味の`add`や`remove`は使いません。一方、`count-words`は集計という1操作なので`path`を`[]`にし、`count-words input.txt`と実行します。ルート操作とサブコマンドは混在させません。

標準動詞の生成器は、出力の種類と終了コードも決めます。識別子が整数の`id`なら作成時の位置引数はなく、`view`・`edit`・`delete`は識別子を位置引数で受け取ります。識別子が文字列の`name`である`tag create home`は、その名前を受け取り、重複を終了コード4で返す設計です。

### 位置引数とオプションの値

`specs/count-words/cli.json`のルート操作には、次の位置引数があります。

```json
{
  "args": [
    {
      "name": "file",
      "type": "file",
      "values": [],
      "required": true,
      "variadic": true,
      "summary": "File to read, or - to read stdin"
    }
  ]
}
```

`required: true`なので入力ファイルが必要です。`variadic: true`は同じ種類の値を複数受け取る指定で、`a.txt b.txt`のように渡せます。`file`型の`-`は標準入力です。位置引数は最大1種類に制限し、複数の意味を持つ値は名前付きのオプションで区別します。

オプションのキーは、先の`title`・`tag`と同じ7つです。

| キー | 意味と指定理由 |
| --- | --- |
| `name` | `--`を除いた名前。項目名から導ける名前にし、同じ項目の呼び名を操作ごとに変えない |
| `type` | 値の型。解析方法と不正入力の検査を決める |
| `values` | `enum`だけが持つ選択肢。それ以外は`[]`にし、型と制約を分ける |
| `default` | 省略時の値。必須または繰り返し指定のオプションは`null`にする |
| `required` | 指定が必要か。`title`は`true`なので欠落時に実装が終了コード2を返す |
| `repeatable` | 同じオプションを複数回使えるか。`tag`は`true`で、タグの集まりを渡せる |
| `summary` | ヘルプの説明。必須・既定値・選択肢は設定から生成するので文に重ねて書かない |

値の型は、文字列`string`、整数`integer`、小数`number`、選択肢`enum`、日付`date`、ファイル`file`、ディレクトリ`directory`を使います。真偽値`boolean`は値を取らないオプションで、既定値は`false`です。日時`timestamp`は出力項目だけに使い、UTCの秒精度の`YYYY-MM-DDTHH:MM:SSZ`で表します。日付は`YYYY-MM-DD`です。

値を取るオプションは`--limit 10`または`--limit=10`、真偽値は`--force`の形です。`-`で始まる値は`--title=-draft`のように渡します。`--`以降は位置引数とし、オプションと位置引数の前後を入れ替えても同じ意味になる実装を求めます。長い名前の前方一致省略や短い名前の束ねを仕様には含めません。

`-h/--help`、ルートの`--version`、構造化出力の`--json`は仕様に書かず導出します。短い名前も独自に追加せず、必要になった標準オプションについて`all`→`-a`、`debug`→`-d`、`dry-run`→`-n`、`force`→`-f`、`output`→`-o`、`port`→`-p`、`quiet`→`-q`、`user`→`-u`という決定表を使います。すべてを各CLIに追加するわけではありません。

Pythonの標準解析器は長い名前の省略を既定で許可するため、見本は`allow_abbrev=False`を指定します。標準ライブラリを使う場合も、生成ヘルプ・エラーの形式・入力順序はこの仕様に合わせる必要があります。[Python 3.14のargparse](https://docs.python.org/3.14/library/argparse.html#allow-abbrev)の既定動作と、このパターンの決定を区別します。

## 2. 出力の型からJSONと表をそろえる

`specs/count-words/cli.json`の出力と型を抜粋します。

```json
{
  "commands": [
    {
      "output": {"kind": "list", "type": "word_count"}
    }
  ],
  "types": [
    {
      "name": "word_count",
      "fields": [
        {"name": "count", "type": "integer", "values": [], "list": false, "nullable": false},
        {"name": "word", "type": "string", "values": [], "list": false, "nullable": false}
      ]
    }
  ]
}
```

`output.kind`が`list`なので、`--json`の結果は`word_count`の配列です。`alpha beta alpha`を集計した場合は`[{"count":2,"word":"alpha"},{"count":1,"word":"beta"}]`になります。JSONを指定しなければ、見出しを`COUNT`と`WORD`にした表です。0件のJSONは`[]`、表は見出しだけになります。

`output.type`は同じ仕様内の型名を参照します。型の`name`は1行の意味、`fields`は全項目で、それぞれ`name`・`type`・`values`・`list`・`nullable`を持ちます。`list: true`は値の配列、`nullable: true`は`null`を許す指定です。項目型には別の型を参照する入れ子を許さず、表に置けるスカラーの値に限定します。

1件を返す操作は`object`として、その型の全項目を持つJSONオブジェクトと表1行を返します。変換結果そのものを返す場合は`raw`、結果がない場合は`none`とし、どちらも`output.type`を`null`にして`--json`を持ちません。これにより、操作ごとにJSONの包み方を決め直す必要がなくなります。

項目の順は識別子を先頭にし、残りは名前順です。表では`null`を`-`、リストをカンマ区切り、真偽値を`true`・`false`にします。単語集計の列が`COUNT  WORD`なのもこの規約の結果です。JSONの形と意味は公開面ですが、人向けの表をスクリプトから解析する前提にはしません。

### 項目の追加を操作へ連動させる

項目を手で各操作へ複製すると、作成にはあるのに編集にはない、といった不整合が起きます。`make field`は型の項目だけでなく、関連する`create`・`edit`のオプションと`list`の並べ替え候補を合わせて追加します。

例えば見本の`note.tags`はリストの項目なので、入力は繰り返し可能な`--tag`です。`note edit`にはタグを空にする`--clear-tags`もあります。通常の`--tag home --tag work`は既存のタグをこの2つで置き換え、追加結合にはしません。値指定と同じ項目の`--clear-…`を同時に渡した場合や、変更オプションを1つも指定しない編集は終了コード2です。

`list`には既定20件の`--limit`と、識別子を既定値にした`--sort`を置きます。絞り込みは要件が求めた項目だけ追加し、複数条件はANDで組み合わせます。`--tag home --tag work`なら両方のタグを持つメモだけを返します。並べ替えは昇順で、`null`を末尾、同値なら識別子順にし、絞り込みと並べ替えの後で件数を制限します。これらの意味は型だけでは表せないため、同梱ルールSTATE-02の決定表と適合テストでそろえます。

## 3. 環境変数と終了コードを決める

`specs/count-words/cli.json`の環境変数は次の定義です。

```json
{
  "env": [
    {
      "name": "COUNT_WORDS_MIN_LENGTH",
      "type": "integer",
      "values": [],
      "default": 1,
      "summary": "Minimum length of a word to count"
    }
  ]
}
```

`name`はCLI名と`--min-length`から導きます。`type`と`values`は対応するオプションと同じにし、`default`は環境変数も未指定の場合の値です。`COUNT_WORDS_MIN_LENGTH=5`なら5文字以上を集計しますが、`--min-length 1`も渡した場合はオプションの1が優先します。設定ファイルを追加しないことで、値の解決順を「オプション→環境変数→既定値」に限定しています。

`notes`は`storage: "data"`なので、保存先として`NOTES_DATA_DIR`を定義します。macOS/Linuxでは、この環境変数の空でない絶対パス、`$XDG_DATA_HOME/notes`、`$HOME/.local/share/notes`の順に解決する規約です。JSON内の`default: "$XDG_DATA_HOME/notes"`はその規約を表す記述であり、シェルがJSONの中で展開するわけではありません。適合テストは専用の保存先を指定する経路を確認し、既定保存先の全OS分岐までは検証しません。

設定ファイル・対話入力・色・進捗表示は設けません。スクリプトから同じ入力で実行できることを優先した、このパターンの選択です。一般的なCLI指針も標準出力・標準エラーやJSON出力の扱いを説明していますが、具体的な動詞や終了コードの数値、非対話への限定は本パターンで決めたものです。[Command Line Interface Guidelines](https://clig.dev/#output)

| 終了コード | 意味 | 仕様への入れ方 |
| --- | --- | --- |
| 0 | 成功 | 全操作 |
| 1 | 読み書き失敗などの予期しない失敗 | 全操作 |
| 2 | 使い方の誤り | 全操作 |
| 3 | 指定した対象・入力ファイルなどがない | 識別子で対象を受け取る操作やファイル入力のある操作 |
| 4 | 同じ名前の対象が既にある | 識別子が`name`の作成操作 |

`note create`は`[0,1,2]`、`note view`は`[0,1,2,3]`、`tag create`は`[0,1,2,4]`です。単語集計は入力ファイルがない場合もあるため`[0,1,2,3]`です。エラー時はstdoutを空にし、stderrへ`count-words: メッセージ`のように起動名を接頭辞にした1行を英語で出します。成功時はstderrを空にし、主な結果だけをstdoutへ出します。

## 4. 生成ヘルプと版を実装へつなげる

`Makefile`では、検査ツールを次のように起動します。

```makefile
PYTHON := uv run --no-project --quiet python
CLISPEC := $(PYTHON) tools/clispec

fix: version
	@$(CLISPEC) fmt
	@$(CLISPEC) gen
```

`.python-version`は`3.14`です。`--no-project`でサイトや利用先のPythonプロジェクトの依存解決を行わず、uvで指定系列のPythonを起動します。最初の`version`ターゲットは、系列が合うこととuv経由であることを確認します。uvによるPythonの検出・導入は[公式のPython管理手順](https://docs.astral.sh/uv/guides/install-python/)に従います。

`fmt`はキー順、名前順、2スペースの字下げをそろえ、公開済み仕様との差分から版も調整します。`gen`は同じ仕様からリファレンスとヘルプを作ります。例えば単語集計のヘルプは`Usage: count-words [options] <file>...`から始まり、`--limit`の既定値20も設定から表示されます。実装はこの生成文面をそのまま使い、`-h`と`--help`のstdoutが一致することを適合テストで確認します。

ヘルプと版表示は正常操作なので終了コード0です。`--version`は`count-words 1.0.0`の1行を返します。解析器が独自に生成するusageや装飾をそのまま使うと文面がずれるため、見本は生成文面を定数として持ち、引数解析の既定ヘルプを使いません。

### 公開済み仕様を互換性の基準にする

`released/1.0.0.json`は、版を確定したときの仕様です。`compat.py`はその最新版と現在の仕様を比較します。差分がなければ同じ版、`summary`だけならパッチ、任意項目などの追加ならマイナーを上げます。削除、既存の値や型の変更、既存操作への必須入力の追加などはメジャー変更です。

`make fix`はパッチ・マイナーを自動反映しますが、メジャー変更は承認とADRが必要なため自動で反映しません。過去の`released/`を書き換えて比較を通すことも禁止します。版を確定する`make release NAME=<name>`は、利用者が公開を決めたときに実行します。ZIPの取得や検証だけでリリース操作を行う必要はありません。

## 5. 設計と検査の入口をそろえる

ルールの全文はZIP内の`docs/design/rules.md`、ルールと検査の対応は`enforcement-matrix.md`にあります。例えば仕様の未知キーはCODE-01、名前はNAM-01、生成物の不一致はSTR-04というIDで報告されるため、検査結果から理由と修正先をたどれます。

`make check`は、仕様検査、整形の確認、リファレンスの再生成差分、見本実装への適合テスト、抑止記法の検査、ルールとスキル・検査の対応を確認します。44ルールすべてを機械だけで判定するわけではありません。名前が要件に合うか、保護ファイルを変えて検査を弱めていないか、破壊的変更の承認があるかは、設計・レビュースキルでも確認します。

適合テストはCLIを別プロセスとして動かし、ヘルプ・版・不正入力・出力の型・終了コード・保存と再取得・編集・絞り込みを確認します。データ用の環境変数は一時ディレクトリに向けます。任意の業務要件すべてを証明するものではなく、仕様で表せない単語の区切り方などの意味は、依頼・実装・固有の検証で決める必要があります。

### Claude Codeで編集前後の処理を呼ぶ

Claude Codeで仕様を編集するときは、編集前に「検査の仕組みを変えようとしていないか」を確認し、編集後に「変更した仕様が規約に合っているか」を調べます。この2つを呼び出すのが`.claude/settings.json`、確認対象や実行コマンドを定めるのが`.foundation/manifest.json`です。

1. 編集前に`hooks.py pre-edit`を呼びます。保護ファイルへの編集なら、Claude Codeへ人間の確認を求める応答を返します。
2. 編集後に`hooks.py post-edit`を呼びます。`specs/*/cli.json`なら、整形・ヘルプ生成・対象仕様の検査を実行します。

フックはClaude Codeのツール実行に連動する仕組みです。別のエージェントやシェルから編集する場合は、後述のコマンドを手動で実行します。以下では、呼び出し元の設定と呼び出された処理を順に対応させます。

<details>
<summary>編集前：保護ファイルを変える操作を確認する</summary>

`.claude/settings.json`の編集前の設定です。

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write|MultiEdit|NotebookEdit",
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"$CLAUDE_PROJECT_DIR/.foundation/bin/hooks.py\" pre-edit",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

`matcher`は編集ツールの名前です。該当するツールが動く前に、`type: command`で指定したPythonコマンドを起動し、編集対象などの情報を標準入力のJSONで渡します。`timeout: 30`は、この確認処理の待ち時間の上限です。`CLAUDE_PROJECT_DIR`からスクリプトを探すため、Claude CodeはZIPの展開先の`cli-design/`をルートとして開始します。

呼び出された`hooks.py`は、`.foundation/manifest.json`の次の値を読みます。

```json
{
  "status": "ready",
  "protected": [
    "Makefile",
    ".editorconfig",
    ".gitignore",
    ".python-version",
    "tools/**",
    "specs/*/released/**",
    ".claude/settings.json",
    ".foundation/**",
    "docs/design/rules.md",
    "docs/design/enforcement-matrix.md",
    "ci.json",
    ".ci/**"
  ]
}
```

`status: ready`のとき、編集対象が`protected`のいずれかに一致すると、`permissionDecision: ask`を返します。例えば`tools/clispec/check.py`や公開済みの`specs/notes/released/1.0.0.json`の編集は確認対象です。一方、設計中の`specs/notes/cli.json`はこの一覧に含まれないため、この保護確認は求めません。

保護するのは、検査ツール、検査の入口、確定済み仕様、規約、フック、ZIP検証処理です。仕様の不備を直す代わりに検査や比較基準を弱めてしまう変更を、人間が確認できるようにしています。これは対象の編集ツールに対する確認であり、シェルなど、あらゆる書き込み経路を禁止する仕組みではありません。

</details>

<details>
<summary>編集後：変更した仕様を整形し、ヘルプと検査結果を更新する</summary>

`.claude/settings.json`の編集後の設定です。

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write|MultiEdit",
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"$CLAUDE_PROJECT_DIR/.foundation/bin/hooks.py\" post-edit",
            "timeout": 120
          }
        ]
      }
    ]
  }
}
```

`Edit`・`Write`・`MultiEdit`が成功した後に`post-edit`を呼びます。編集後は整形や生成も行うため、待ち時間の上限は120秒です。`PreToolUse`にある`NotebookEdit`は、ここには含まれていません。

どのファイルに何を実行するかは、`.foundation/manifest.json`で指定します。

```json
{
  "hooks": {
    "post_edit": [
      {
        "glob": "specs/*/cli.json",
        "command": "make -s after-edit FILE={file}"
      }
    ]
  }
}
```

例えば`specs/notes/cli.json`を変更すると、`{file}`をその相対パスに置き換えて、基盤のルートで次のコマンドを実行します。

```bash
make -s after-edit FILE=specs/notes/cli.json
```

この処理が仕様の整形・版の調整、ヘルプとリファレンスの生成、対象仕様の検査を行います。生成物の更新を編集者の記憶に頼らず、仕様の変更に連動させるためです。検査に失敗した場合、フックは指摘を標準エラーへ出して終了コード2を返します。編集を自動で取り消す処理ではないので、指摘に従って仕様を直します。

`glob`に一致しないファイルでは、この自動処理は動きません。また、対象仕様の編集後処理だけで全体の検証は終わらないため、作業の最後には`make check`を実行します。

</details>

### 検査を省略する記述を検出する

自動で検査を呼んでも、検査対象のコードに「この行を無視する」「このテストを飛ばす」という記述を加えると、不備を隠せてしまいます。`make check`から呼ぶ`guard.py`は、そのような記述を検出します。

<details>
<summary>guardの走査範囲・禁止する記述・例外</summary>

`.foundation/manifest.json`の設定です。

```json
{
  "guard": {
    "rule": "TOOL-03",
    "include": [
      "**/*.py",
      "specs/**/*.json"
    ],
    "exclude": [
      ".foundation/**"
    ],
    "suppressions": [
      {
        "pattern": "#\\s*noqa",
        "rule": "TOOL-03"
      },
      {
        "pattern": "#\\s*type:\\s*ignore",
        "rule": "TOOL-03"
      },
      {
        "pattern": "unittest\\.skip",
        "rule": "TOOL-03"
      },
      {
        "pattern": "skipTest\\(",
        "rule": "TOOL-03"
      },
      {
        "pattern": "expectedFailure",
        "rule": "TOOL-03"
      }
    ],
    "allow": []
  }
}
```

`include`はPythonファイルと仕様JSONを走査対象にします。`suppressions`の`pattern`は正規表現で、例えば`# noqa`や`# type: ignore`、`unittest.skip`を含む行を見つけると、対応する`rule: TOOL-03`で報告します。`allow`は例外の一覧ですが、この基盤では空なので個別の免除は設けていません。

検査機構自体は検出用の文字列を持つため、`exclude`で`.foundation/**`を除きます。これに加えて、`guard.py`には`.claude/**`、`docs/design/**`、`AGENTS.md`、`CLAUDE.md`、`README.md`を除く既定値があります。規約の説明やスキルに書いた禁止記法の例を、実装内の違反と混同しないためです。

仕様JSONの未知キーは、この正規表現の検査では判定しません。`tools/clispec/check.py`が仕様の構造を検査し、CODE-01として報告します。同じ`make check`から起動しますが、担当する検査は別です。

</details>

### 作業規約と検査コマンドの参照先をそろえる

`AGENTS.md`は仕様の作成・変更・検証の作業規約です。`CLAUDE.md`には`@AGENTS.md`があり、Claude Codeでも同じ規約を参照します。設計用・レビュー用の詳しい手順は`.claude/skills/`に分けています。

<details>
<summary>スキル名、共通コマンド、基盤の管理情報</summary>

`.foundation/manifest.json`では、対応するスキルとコマンドを次のように宣言します。

```json
{
  "skills": {
    "impl": "cli-design",
    "review": "cli-design-review"
  },
  "commands": {
    "check": "make check",
    "fix": "make fix"
  }
}
```

`skills.impl`は`.claude/skills/cli-design/`、`skills.review`は`.claude/skills/cli-design-review/`に対応します。前者は設計・実装時、後者はレビュー時の確認事項です。この名前の宣言だけでスキルを自動実行するわけではありません。`commands.check`と`commands.fix`は、違反例の検証や収束評価でも使う共通の入口です。通常の作業と同じ`make check`・`make fix`へそろえ、評価だけ別の検査を通す状態を避けます。

同じファイルの管理情報は次の値です。

```json
{
  "name": "cli-design",
  "status": "ready",
  "mode": "new",
  "domain": [
    "cli-library"
  ],
  "language": "ja",
  "copy": {
    "link_dirs": [],
    "skip_dirs": []
  }
}
```

`name`は基盤名、`mode: new`は新規構築、`domain`はCLIライブラリ、`language: ja`は日本語で作業する基盤であることを記録します。`status: ready`は保護確認を有効にするほか、通常のルール検査を最終段階のphase 5にします。この段階では、レビュースキルとルールの対応も検査対象です。

`copy`は、違反例の検証などで作る一時コピーの追加設定です。`link_dirs`と`skip_dirs`が空なので、独自のリンク先や除外先は追加しません。ただし、`.git`やキャッシュを除外するなど、コピー処理に組み込まれた既定値は有効です。

`stack`と`tools`は、元実装が調査した技術と検査ツールの台帳です。各要素の`name`・`version`・`role`、必要に応じた`language`、版を固定する方針の`pinned`を保持します。これらの宣言から言語環境を自動導入する処理はありません。Go・Python・Node.js・Rustの解析器について記録された版を、そのまま全環境の動作確認済みの版と扱わないでください。ZIPの検証で使うPython系列は`.python-version`と`ci.json`、導入するuvの版は`.ci/verify.py`で確認します。

</details>

### エディタとZIPの検証環境をそろえる

仕様の表記をそろえる設定と、展開先で検証する設定は役割が異なります。前者は編集時の文字コードや字下げ、後者は実行するPythonと検証コマンドを指定します。

<details>
<summary>エディタの文字コード・改行・字下げ</summary>

`.editorconfig`の設定です。

```ini
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true
indent_style = space
indent_size = 4

[*.json]
indent_size = 2

[Makefile]
indent_style = tab
```

`root = true`で上位ディレクトリのEditorConfig探索を止め、このZIP内の方針を使います。`[*]`ではUTF-8、LF、末尾改行あり、行末空白の除去、空白4文字を既定にします。JSONは生成器と同じ2文字、Makefileはコマンド行に必要なタブへ上書きします。対応エディタでの編集をそろえる設定なので、CLI仕様のキー順などは引き続き`make fix`で整えます。

`.gitignore`は`__pycache__/`・`*.pyc`・`.DS_Store`を除き、Pythonの実行やmacOS上の操作で生じるファイルを管理対象へ混ぜないようにします。

</details>

<details>
<summary>ZIPの展開先で準備と検証を実行する設定</summary>

`ci.json`の全体です。

```json
{
  "command": [
    "python3",
    ".ci/verify.py"
  ],
  "pythonVersion": "3.14"
}
```

共通のZIP検証処理が`pythonVersion`でPython 3.14を選び、展開したパターンのルートで`command`の配列を実行します。`.ci/verify.py`は一時環境へuv 0.13.3を導入してから、全体検査、見本2種類の適合テスト、代表的な違反4件の検出、新しい仕様の生成を順に確かめます。準備や途中の検査が失敗したら後続を止め、非0で終了します。

利用先にサイトのNode.js依存関係を持ち込まず、ZIP内のファイルだけで同じ検証を行うための設定です。基盤直下に`ci.json`を許可し、`.ci/`を保護対象へ追加した理由は、ZIP内の`docs/design/adr/0008-standalone-pattern-ci.md`に記録しています。実行手順と結果は後の「検証方法と結果」にあります。

</details>

### 元実装の評価設定を保管する

`.foundation/convergence/`には、元実装で複数のエージェントに同じ課題を解かせ、結果の一致を比較した資料があります。通常のCLI設計やZIP検証とは実行の入口が異なるため、評価条件は分けて確認します。

<details>
<summary>複数エージェントによる評価の実行条件と一致の基準</summary>

`.foundation/manifest.json`の設定です。

```json
{
  "convergence": {
    "agents": 3,
    "max_rounds": 3,
    "parallel": 3,
    "timeout_sec": 1800,
    "runner": [
      "claude",
      "-p",
      "{prompt}",
      "--output-format",
      "json",
      "--permission-mode",
      "acceptEdits",
      "--no-session-persistence",
      "--allowedTools",
      "Skill",
      "Bash(make check)",
      "Bash(make fix)",
      "Bash(make *)",
      "Bash(git diff *)",
      "Bash(git status *)"
    ],
    "ignore": [
      "**/__pycache__/**"
    ],
    "thresholds": {
      "files": 1.0,
      "names": 0.8,
      "content": 0.0
    }
  }
}
```

`agents: 3`は比較するエージェント数、`max_rounds: 3`は最大の評価ラウンド数です。`parallel: 3`で同時実行の上限を3、`timeout_sec: 1800`で1実行の上限を30分にします。`runner`は課題を`{prompt}`へ差し込むClaudeの起動引数です。JSONで結果を受け取り、セッションを保存せず、編集の許可モードと利用可能なツールをこの配列で指定します。`ignore`はPythonキャッシュを比較から除きます。

`thresholds`は結果の一致度の下限です。変更したファイルの集合は1.0、新しく導入した名前の集合は0.8、内容は0.0とし、内容の逐語的な一致は求めません。保護ファイルの変更があれば不合格になり、検査を実行して比較する場合は全員の検査成功も条件になります。

これらは元実装の評価条件を保持したもので、`make check`や`.ci/verify.py`から評価エージェントを起動することはありません。今回確認したZIPの検証結果と、過去の評価資料は区別します。

</details>

## 導入・使用方法

### 1. ZIPを展開して環境を準備する

macOS/Linux、GNU Make、Python 3.14、uvを使います。検査ツールと見本に外部Pythonパッケージは不要です。自動のZIP検証はPythonの`venv`・`pip`とネットワークを使い、一時環境へuv 0.13.3を導入します。サイトのNode.jsやDocusaurusに依存しません。

ZIPを展開し、隠しファイルを含む`cli-design/`全体を作業用の独立したディレクトリへ置きます。既存のAGENTS.md・Makefile・`.claude/`などへ上書き統合せず、まずこのディレクトリ内で手順を確認してください。以下はすべて展開先を作業場所とします。uvの導入は[公式の導入手順](https://docs.astral.sh/uv/getting-started/installation/)を使います。

```bash
uv --version
make --version
uv python install 3.14
make check
```

準備に失敗した場合は停止します。

### 2. 見本の単語集計を実行する

見本の単語集計は次の入力で試せます。

```bash
printf 'alpha beta alpha\n' | uv run --no-project --quiet python tools/clispec/tests/fixtures/count_words_impl.py - --json
```

結果は`alpha`が2回、`beta`が1回のJSON配列です。`--min-length 5`を付けると`alpha`だけになります。

### 3. 新しい管理CLIの仕様を作る

次の手順は新しい作業用コピーで行います。`bookmarks`という仕様が既にある場合は別名を使います。

```bash
make new NAME=bookmarks
make command NAME=bookmarks NOUN=bookmark VERB=create
make command NAME=bookmarks NOUN=bookmark VERB=list
make command NAME=bookmarks NOUN=bookmark VERB=view
make command NAME=bookmarks NOUN=bookmark VERB=edit
make command NAME=bookmarks NOUN=bookmark VERB=delete
make field NAME=bookmarks NOUN=bookmark FIELD=url TYPE=string
make fix
make check
```

`specs/bookmarks/cli.json`と`cli.md`が作られます。識別子は整数の`id`、作成時の`--url`は必須、版は`1.0.0`です。`create`があるため作成時刻、`edit`があるため更新時刻も追加され、管理データの保存先として`BOOKMARKS_DATA_DIR`が定義されます。これらは生成器の規約で決まる値であり、実行可能なブックマーク管理プログラムは別途実装します。

操作を追加する`NOUN`・`VERB`、項目の`FIELD`・`TYPE`は利用先の要件に合わせます。名前で識別する対象には`KEY=name`、複数値は`LIST=1`、任意項目は`NULLABLE=1`、列挙型は`VALUES=a,b`を使います。1操作だけなら`make new NAME=<name> SINGLE=1`から始めます。生成された`TODO`は依頼に合わせて埋め、`cli.md`は手で直さず`make fix`を使います。

### 4. 仕様に従って実装し、適合テストで確かめる

実装は基盤の外へ置き、同梱の`.claude/skills/cli-design/references/stdlib-mapping.md`に沿って各言語の標準ライブラリで引数を解析します。次の`CMD`を実際の起動コマンドの絶対パスへ置き換えて確認します。

```bash
make conform SPEC=specs/bookmarks/cli.json CMD="/absolute/path/to/bookmarks"
```

Claude Codeと使う場合はこの基盤のルートで起動します。別のエージェントやシェル編集ではhooksの自動実行を前提にせず、スキルを読み、仕様の変更後に`make after-edit FILE=specs/<name>/cli.json`、最後に`make check`を実行します。

## 利用時に確認する制約

この基盤の上限は、名詞8種類、位置引数1種類、明示するオプション10個、型の項目12個です。項目を増やすと編集・クリア用オプションも増えるため、型の上限より先にオプションの上限へ届く場合があります。検査結果に従って操作を見直し、上限や設計ルールを変える場合はADRから順に変更します。

見本のPython実装は、規約を理解して適合テストを試すためのものです。業務で使う場合の同時更新、障害時の保存保証、入力サイズ、独自の業務制約は別途検討します。適合テストに通ったことを、任意の用途での完全な正しさや耐障害性の証明とはしません。

保存先の既定分岐、追加前の古い保存データに新項目がない場合の移行、任意の隠しオプションが存在しないことは、適合テストだけでは網羅しません。Windows、各言語への移植、Claude Codeの実際の対話・hooksの起動は、それぞれ利用先で確認してください。

## 検証方法と結果

生成ZIPを別の場所へ展開し、Python 3.14で次を実行します。

```bash
python3 --version
make --version
python3 .ci/verify.py
```

`ci.json`は`command: ["python3", ".ci/verify.py"]`と`pythonVersion: "3.14"`を指定します。検証処理は一時環境へのuv導入、`make check`、見本2種類への`make conform`、違反4件の検出、別の一時コピーでの新規仕様生成を順に行います。途中失敗は後続を止め、非0で終了します。最後の`ZIP検証: 全検査・見本2種類・違反4件・新規仕様生成に成功`と終了コード0が期待結果です。

ルートから同じ生成ZIPの検証を呼ぶ場合は、次のコマンドです。

```bash
npm run verify:patterns -- --id design/cli/cli-design --ci --timeout-ms 1200000
```

通常のZIP検証で確認する違反は、未知のCIファイル（STR-01-d）、リファレンスの手編集（STR-04-a）、禁止した動詞（NAM-04-a）、ヘルプの出力先の誤り（OPS-05-a）です。違反を入れる前の正常例が通り、違反を入れると非0と対応するエラーが返ることを一時コピーで確認します。

検査機構の保守では`.foundation/bin/violation_probe.py`で全67件を再実行し、`rules_check.py --final --no-write`でルールと結果の整合を確認します。収束評価の記録は元実装の評価であり、今回のZIP検証とは別です。

2026年10月21日、macOS 15.7.3、Python 3.14.2、GNU Make 3.81で確認しました。ZIP検証が導入するuvは0.13.3、全probeの再実行に使った導入済みuvは0.8.24です。掲載サイトはNode.js 24.9.0で検証しました。

| 対象 | 実施した確認と結果 |
| --- | --- |
| 生成ZIP | 別ディレクトリに展開して`.ci/verify.py`が成功。環境準備、全検査、見本2種類、新規仕様の生成を確認 |
| 適合テスト | `notes`は510件、`count-words`は66件成功、失敗0件 |
| 違反検出 | 通常のZIP検証は代表4件に成功。検査機構の保守確認として全67件と`make check`への組み込み6件も成功 |
| ルール検査 | `rules_check.py --final --no-write`が成功。44ルール、エラー0件。元のルール文にある列挙表現の警告3件は残る |
| READMEの使用例 | 取得したZIPを空白のある別パスに展開し、標準入力、最小文字数、オプションの優先、適合テスト2種類を確認 |
| 掲載サイト | 配置確認・文書確認・共通テスト50件・型チェック・ビルド・ブラウザーE2E 6件が成功 |
| 実ページと配布 | PC（1440px）・モバイル（390px）の表示、一覧・ヘッダー・サイドバー・検索からの移動、補助設定の開閉、ZIP取得を確認。隠し設定を含む87ファイルを収録し、取得ZIPと生成物の一致を確認 |

制限環境ではuv導入時のネットワークアクセス、Chromiumの起動が拒否されました。また、共通E2Eの初回は準備サーバーの起動待ちで180秒を超えました。これらは成功に含めず、制限外で再実行して上表の成功を確認しています。E2Eの再現コマンドは`NODE_OPTIONS=--max-old-space-size=8192 npm run test:e2e`です。

GitHub Actions上のLinux環境、Go・Node.js・Rustでの実装、Claude Codeでの実際の対話とhooks起動、人間による説明・成果物の最終レビューは未確認です。WindowsのZIP検証は対応対象外として未実施です。元実装の収束評価は再実行していません。

## 参考資料

- [Command Line Interface Guidelines](https://clig.dev/)：標準出力・標準エラー、JSON出力、命名などの指針。本パターン独自の制限とは区別します。
- [Python 3.14 argparse](https://docs.python.org/3.14/library/argparse.html)：見本実装の引数解析。
- [uvによるPythonの導入と管理](https://docs.astral.sh/uv/guides/install-python/)：検査ツール用のPython系列の準備。
- [uvの導入](https://docs.astral.sh/uv/getting-started/installation/)：uv本体の準備。
- ZIP内の`docs/design/rules.md`・`architecture.md`・`adr/`：実装と対になる決定表、依存関係、採用理由。

## ダウンロード

[実装をダウンロード](/downloads/patterns/design/cli/cli-design.zip)
