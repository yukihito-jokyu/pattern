# cli-design のルール

このファイルは cli-design のルールの正本である。AGENTS.md・スキル・レビューの指摘・検査のエラーは、ここのルールIDを参照する。ルールの変更手順は AGENTS.md の「ルールを変えたいとき」に従う。

## 読み方

- ルールIDは `<接頭辞>-<連番>` である。廃止したルールも ID を再利用せず、`- 状態: 廃止` と書いて残す
- **強制**の先頭のキーワードは、そのルールを守らせる仕組みを表す

  | キーワード | 仕組み |
  |---|---|
  | `type` | 型・可視性で書けなくする |
  | `format` | formatter（`tools/clispec fmt`） |
  | `lint` | linter |
  | `structure` | 構造検査（`tools/clispec check`） |
  | `test` | テスト（`tools/clispec conform` による適合テストと、検査ツール自身の unittest） |
  | `generator` | 生成器（`make new`、`make command`） |
  | `review` | レビュー用スキル |
  | `doc` | 文書のみ |

  ルールと仕組みの対応表は `enforcement-matrix.md`（生成物）にある
- `type`・`format`・`lint`・`structure`・`test` のルールには、違反例（probe）が `.foundation/probes.json` にあり、検査で落ちることを確かめてある
- `tools/clispec check` のエラーは `<ルールID> <パス>:<行> <JSON の位置>: <説明>` の形で出る。ルールIDでこのファイルを引く

## ルールの書式

`rules_check.py` がこの書式を読む。項目名と順番を変えない。

```markdown
### <接頭辞>-<2桁の番号> <決定を1行で要約した題名>

- 軸: <答えている軸の記号。複数ならカンマ区切り>
- 決定: <読んだ2人が同じ判定をできる1文。条件で答えが変わるなら、次の行から2字下げで決定表を書く>
- 理由: <何が揺れ、何が壊れるのを防ぐか>
- 出典: <research.md の該当節、または公式ドキュメントの URL。無ければ行ごと省く>
- 強制: <キーワード。複数ならカンマ区切り> — <仕組みの説明：どの設定・スクリプトのどこで縛るか>
- probe: <この強制を証明する probe の ID。機械の段ごとに1件以上>
- 良い例:
  <5行以内のコード。長くなるなら「見本: <参照実装のパス>」と書く>
- 悪い例:
  <実際に書かれがちな違反。5行以内>
```

- 機械の段（`type`・`format`・`lint`・`structure`・`test`）を含まないルールには、`- 機械化しない理由:` を**強制**の次の行に足し、`probe` の値は `なし` にする
- 軸の記号は範囲で書いてもよい（`D1〜D3` は D1、D2、D3 と読まれる）
- 番号は節ごとに 01 から、カタログの軸の順（同じ軸の中では決定の順）に振る
- ルールが0件の節は、見出しごと消し、その節の軸を「対象外とした軸」表に書く
- 決定の中のコード片（`` ` `` で囲んだ部分）は、あいまいな語の検査から除かれる

## 用語

| 用語 | 意味 |
|---|---|
| CLI | この基盤で設計する、コマンドラインの道具1つ。実装の言語は問わない |
| 仕様 | 1つの CLI の外から見える形の全部を書いた `specs/<name>/cli.json`。設計の正本 |
| リファレンス | 仕様から `tools/clispec gen` が生成する `specs/<name>/cli.md`。ヘルプの文面を含む |
| リリース済みの仕様 | `make release` が `specs/<name>/released/<version>.json` に写した、公開済みの版の仕様。変えない |
| コマンド | 仕様の `commands` の1要素。`path` が `[]`（ルートのコマンド）か `["<名詞>", "<動詞>"]` |
| 名詞・動詞 | `path` の1つ目と2つ目の語。名詞は操作の対象の種類、動詞は操作 |
| 位置引数 | コマンドの `args` の要素。`<title>` のように名前の無い値で渡す |
| オプション | コマンドの `options` の要素。`--name value` で渡す |
| 暗黙のオプション | 仕様に書かず、全 CLI が持つオプション。`-h/--help`（全コマンド）、`--version`（ルートだけ）、`--json`（出力の種類が `object` か `list` のコマンド） |
| 出力の型 | 仕様の `types` の要素。`--json` の出力と、テキストの表の列を決める |
| 項目 | 出力の型の `fields` の要素 |
| 識別子の項目 | 出力の型の先頭に置く `id`（整数、CLI が振る）か `name`（文字列、利用者が付ける） |
| 標準の動詞 | `create`・`list`・`view`・`edit`・`delete` の5つ（NAM-04） |
| 標準のオプション | clig.dev の標準フラグから採った8つ（NAM-03） |
| PREFIX | CLI 名を大文字にし `-` を `_` に替えたもの（`count-words` → `COUNT_WORDS`）。環境変数名の接頭辞 |
| 実装 | 仕様に従って任意の言語で書いたプログラム。この基盤の外に置く |
| 適合テスト | `tools/clispec conform` が、実装を外から実行して仕様どおりかを確かめる検査 |

## 追加した軸

カタログに無い、この分野に固有の軸を定義する。domain-profiles.md がその分野に定めた X 軸はすべて載せる。

| 軸 | 内容 | 置く節 |
|---|---|---|
| X1 | 終了コードと出力の形式（標準出力と標準エラーの使い分け、機械可読の出力） | OPS |
| X2 | 公開 API の互換性（semver の上げ方、非推奨にする手順） | PROC |
| X3 | コマンドの構成（サブコマンドの段数、名詞と動詞の順） | STR |
| X4 | 配布（CLI 名の制約、版の表示、インストール後に動くこと） | OPS |
| X5 | 標準の動詞の振る舞い（絞り込みの組み合わせ、並べ替え、値の置き換えと消去、識別子の振り方） | STATE |

## STR 配置と構造

### STR-01 1つの CLI の設計は specs/<name>/ の3種類のファイルだけで表す

- 軸: A1, A3, A5, C1
- 決定: CLI 1つにつき `specs/<name>/` を1つ作り（`<name>` は仕様の `name` と同じ）、その中に置くファイルを次の表の3種類だけにする。
  | パス | 中身 | 書く人 |
  |---|---|---|
  | `specs/<name>/cli.json` | 仕様（1ファイル。分割しない） | 作者 |
  | `specs/<name>/cli.md` | リファレンス | `tools/clispec gen` |
  | `specs/<name>/released/<MAJOR>.<MINOR>.<PATCH>.json` | リリース済みの仕様 | `make release` |
  `ci.json`は配布ZIPの検証環境と実行コマンドを指定するメタデータである（ADR 0008）。
  基盤の直下に置く名前を、`.` で始まる名前と `AGENTS.md`・`CLAUDE.md`・`Makefile`・`README.md`・`ci.json`・`docs`・`specs`・`tools` の8つだけにし、実装は基盤の外に置く。
- 理由: 仕様を複数ファイルに分けたり、設計メモや実装を横に置いたりすると、作者ごとにファイルの集合が変わり、どれが正本か分からなくなる
- 出典: research.md「配布」
- 強制: structure — `tools/clispec check` の STR-01（基盤の直下、`specs/` の直下、各 CLI のディレクトリの中身を表と照合）
- probe: STR-01-a, STR-01-b, STR-01-c, STR-01-d
- 良い例:
  ```text
  specs/notes/cli.json
  specs/notes/cli.md
  specs/notes/released/1.0.0.json
  ```
- 悪い例:
  ```text
  specs/notes/commands/note.json
  specs/notes/DESIGN.md
  ```

### STR-02 新しい CLI とコマンドは生成器で始める

- 軸: A2
- 決定: 新しい CLI は `make new NAME=<name>`（サブコマンドを持たないなら `make new NAME=<name> SINGLE=1`）で、コマンドの追加は `make command NAME=<name> NOUN=<名詞> VERB=<動詞>`（型を新しく作るときの識別子が `name` なら `KEY=name`）で、名詞の型への項目の追加は `make field NAME=<name> NOUN=<名詞> FIELD=<項目名> TYPE=<型>`（`LIST=1`・`NULLABLE=1`・`VALUES=<a,b>`）で作り、生成された値（`summary`・`exit_codes`・`output`・識別子の位置引数・NAM-07 の必ず置くオプション）を書き換えるのは `TODO` と書かれた値と、NAM-07 の決定表が依頼の既定値で決める `required`・`default` だけにする。
- 理由: 白紙から書くと、キーの有無、標準の動詞の summary、終了コードの組、項目に対応するオプションが作者ごとに変わる。生成器は STR-05・NAM-04・NAM-07・CODE-04・ERR-01 が決める値をそのまま書く
- 強制: generator, doc — `tools/clispec new`・`tools/clispec command`・`tools/clispec field`。生成した後の形は STR-05・NAM-04・NAM-07・CODE-04・ERR-01 の structure が検査する
- 機械化しない理由: 生成器を使ったかどうかは、出来上がった仕様に痕跡が残らない。結果の形は別のルールの検査で縛る
- probe: なし
- 良い例:
  ```sh
  make field NAME=notes NOUN=note FIELD=due_date TYPE=date NULLABLE=1
  ```
- 悪い例:
  ```text
  cli.json を開き、別のコマンドの要素を写して手で直す
  ```

### STR-03 出力の型は types に1回だけ定義し、入れ子にしない

- 軸: A4, B3
- 決定: 出力の型は `types` に1回だけ定義してコマンドの `output.type` から名前で参照し、項目の `type` はスカラーの型（CODE-02 の表の項目の列）だけにして型の中に型を入れず、どのコマンドからも参照されない型を置かない。
- 理由: 同じ形をコマンドごとに書くと、片方だけに項目が足されて `--json` の形がコマンドごとにずれる。入れ子を許すと、テキストの表（OPS-04）に並べられない
- 強制: structure — `tools/clispec check` の STR-03（未定義の型の参照、参照されない型、項目の型）
- probe: STR-03-a, STR-03-b
- 良い例:
  ```json
  "output": {"kind": "object", "type": "note"}
  ```
- 悪い例:
  ```json
  {"name": "author", "type": "user", "values": [], "list": false, "nullable": false}
  ```

### STR-04 cli.md は生成物であり、リリース済みの仕様は変えない

- 軸: A6
- 決定: `cli.md` は `make fix`（`tools/clispec gen`）でだけ書き換え、`released/` のファイルは `make release` で作った後は変えも消しもしない。
- 理由: リファレンスを手で直すと、仕様とヘルプの文面がずれ、実装の適合テストが仕様と違う文面を正しいとみなす。リリース済みの仕様が変わると、版の計算（PROC-06）の基準が壊れる
- 強制: structure, review — `tools/clispec gen --check`（再生成して差分が無いこと）と `tools/clispec check` の STR-04（リリース済みの仕様の名前・版・形）。リリース済みの仕様の中身の書き換えはレビュー用スキルで確かめる
- probe: STR-04-a, STR-04-b
- 良い例:
  ```sh
  make fix
  ```
- 悪い例:
  ```text
  cli.md のヘルプの文面だけを直して、cli.json を直さない
  ```

### STR-05 操作が1つならルートのコマンドだけ、2つ以上なら全コマンドを名詞と動詞の2段にする

- 軸: X3
- 決定: コマンドの構成を次の表で決める。
  | CLI が持つ操作の数 | `commands` |
  |---|---|
  | 1つ | `path` が `[]` のコマンドを1つだけ置く |
  | 2つ以上 | 全コマンドの `path` を `["<名詞>", "<動詞>"]` にする。名詞は単数形の英小文字1語 |
- 理由: 1段（`notes add`）と2段（`notes tag list`）が混ざると、名詞を足すたびに既存のコマンドの形を変える（互換性を壊す）ことになる。全部を2段にすれば、名詞を足しても既存のコマンドは変わらない
- 出典: research.md「Command Line Interface Guidelines」（Subcommands の `noun verb`）
- 強制: structure — `tools/clispec check` の STR-05（`path` の長さ、1つと2つ以上の混在、名詞の形）
- probe: STR-05-a, STR-05-b
- 良い例:
  ```json
  {"path": ["note", "create"], ...}
  {"path": ["tag", "list"], ...}
  ```
- 悪い例:
  ```json
  {"path": ["create"], ...}
  {"path": ["tag", "list"], ...}
  ```

## DEP 境界と依存

### DEP-01 仕様はコマンドから型への参照だけを持ち、外を参照しない

- 軸: B1
- 決定: 仕様の中の参照はコマンドの `output.type` から `types` の `name` への参照だけにし、別の仕様や外部のスキーマを参照するキー（`$ref`、`$schema`、`extends`）を書かない。
- 理由: 仕様どうしが参照し合うと、1つの CLI の変更が別の CLI の版を変え、どの仕様が公開面の正本か分からなくなる
- 強制: structure — `tools/clispec check` の CODE-01 が、表に無いキーをエラーにする（`$ref` などはこの検査で落ちる）。DEP-01 は参照先の実在を検査する
- probe: DEP-01-a
- 良い例:
  ```json
  "output": {"kind": "list", "type": "note"}
  ```
- 悪い例:
  ```json
  "output": {"kind": "list", "type": "../tasks/cli.json#task"}
  ```

### DEP-02 外から見える振る舞いは全部仕様に書き、仕様に無い入口を実装に作らない

- 軸: B2
- 決定: CLI の公開面を「コマンド、位置引数、オプション（暗黙のオプションを含む）、`--json` の出力、終了コード、環境変数、データの置き場」とし、実装はこの全部を仕様どおりに持ち、仕様に無いオプション・別名・環境変数・前方一致の省略を受け付けない。
- 理由: 実装が隠しオプションや別名を足すと、言語ごとに受け付ける入力が変わり、利用者のスクリプトが特定の実装に縛られる
- 出典: research.md「Command Line Interface Guidelines」（Future-proofing）、「Semantic Versioning 2.0.0」
- 強制: test, review — `tools/clispec conform` が、未知のオプションと前方一致の省略が終了コード2になることを確かめる。隠しオプションの有無は実装のレビューで確かめる
- probe: DEP-02-a
- 良い例:
  ```text
  notes note list --lim 5   → 終了コード 2（前方一致を受け付けない）
  ```
- 悪い例:
  ```text
  Python の argparse を allow_abbrev の既定（True）のまま使い、--lim を --limit とみなす
  ```

### DEP-03 引数の書式は、全言語の標準ライブラリで同じ結果になる共通部分だけにする

- 軸: B4
- 決定: 仕様が約束する引数の書式を次の表の5つだけにし、仕様の形式にはこれ以外の書式（短い名前の束ね、1つのダッシュの長い名前、`--no-<name>`、`--<name>=true`、前方一致の省略、省略可能な値）を表すキーを置かない。
  | 書式 | 意味 |
  |---|---|
  | `--<name> <value>`、`--<name>=<value>` | 値を取るオプション。`-` で始まる値は `--<name>=<value>` で渡す |
  | `-<x> <value>` | 標準のオプション（NAM-03）の短い名前。短い名前は表から導き、仕様に書かない |
  | `--<name>` | 真偽値のオプション。値を取らない |
  | オプションと位置引数の順序 | どちらが先でもよい |
  | `--` | これより後ろは全部位置引数 |
- 理由: 束ねや `-name` は、Go・Python・Node.js の解析器で結果が変わる（`-name value` は Python と Node.js でエラーにならず `-n ame` と解析される）。共通部分だけを約束すれば、どの言語で実装しても同じ入力が同じ意味になる
- 出典: research.md「引数解析器の実測」、「Command Line Interface Guidelines」（順序に依存しない）、「POSIX Utility Conventions」（Guideline 10）
- 強制: structure, test — `tools/clispec check` の CODE-01（表に無いキーをエラーにする）と NAM-01（オプション名は2文字以上の kebab-case）。`tools/clispec conform` が、順序を入れ替えた入力と `--` の後ろの値を実装に与えて確かめる
- probe: DEP-03-a, DEP-03-b
- 良い例:
  ```json
  {"name": "limit", "type": "integer", "values": [], "default": 20, "required": false, "repeatable": false, "summary": "Maximum number of notes to show"}
  ```
- 悪い例:
  ```json
  {"name": "l", "type": "integer", "short": "l", ...}
  ```

### DEP-04 実装の引数解析は各言語の標準ライブラリだけで行う

- 軸: B4, B6
- 決定: 実装の引数解析は、Go は `flag`、Python は `argparse`、Node.js は `util.parseArgs`、Rust は `std::env::args_os` だけを使い、それ以外の言語でも標準ライブラリだけを使い、標準ライブラリ以外のパッケージ（cobra、click、commander、clap はその例）を使うには ADR を書いてユーザーの承認を得る。
- 理由: 指示による。解析器ごとに既定の挙動（ヘルプの出し方、エラーの終了コード、前方一致）が違い、外部パッケージを混ぜるとその差が増える。言語ごとの補い方は実装用スキルの `references/stdlib-mapping.md` に1つずつ決めてある
- 出典: research.md「引数解析器の実測」
- 強制: doc — 実装用スキルの「実装に落とすとき」の節と `references/stdlib-mapping.md`
- 機械化しない理由: 実装はこの基盤の外のリポジトリにあり、この基盤の検査はその依存の一覧を読めない
- probe: なし
- 良い例:
  ```go
  fs := flag.NewFlagSet("notes note list", flag.ContinueOnError)
  ```
- 悪い例:
  ```go
  cmd := &cobra.Command{Use: "list"}
  ```

### DEP-05 CLI が書くファイルはデータの置き場と --output の指定先だけにする

- 軸: B5
- 決定: CLI がファイルを作る・書き換える場所を、`storage` が `data` の CLI のデータの置き場（STATE-01）と、`-o/--output` で指定されたファイルの2つだけにし、カレントディレクトリや実行ファイルの隣に暗黙のファイルを作らない。
- 理由: インストールした後は、実行ファイルの隣もカレントディレクトリも書けるとは限らない。書き込み先を2つに限れば、配布した後も同じように動く
- 出典: research.md「XDG Base Directory Specification 0.8 と Windows の Known Folders」
- 強制: review — レビュー用スキルの確認項目（動詞と summary が書き込みを示すのに `storage` が `none` で `output` オプションも無いコマンド）
- 機械化しない理由: コマンドがファイルを書くかどうかは動詞の意味で決まり、字面では判定できない
- probe: なし
- 良い例:
  ```json
  "storage": "data"
  ```
- 悪い例:
  ```text
  notes.json をカレントディレクトリに作る
  ```

## NAM 命名

### NAM-01 名前の形を表のとおりにする

- 軸: C2
- 決定: 仕様に書く名前を次の表の形にする。
  | 名前 | 形（正規表現） |
  |---|---|
  | CLI 名（`name`） | `^[a-z][a-z0-9]*(-[a-z0-9]+)*$`、2〜20文字 |
  | 名詞・動詞 | `^[a-z]+$` |
  | オプション名、位置引数の名前 | `^[a-z][a-z0-9]*(-[a-z0-9]+)*$`、2文字以上 |
  | 型の名前、項目の名前、選択肢の値（`values`） | `^[a-z][a-z0-9]*(_[a-z0-9]+)*$` |
  | 環境変数名 | `^<PREFIX>_[A-Z][A-Z0-9]*(_[A-Z0-9]+)*$` |
- 理由: `--includeDone`・`--include_done`、`createdAt`・`created_at` が混ざると、利用者が覚えられず、`--json` を読むスクリプトが壊れる
- 出典: research.md「Command Line Interface Guidelines」（Naming、Environment variables）
- 強制: structure — `tools/clispec check` の NAM-01
- probe: NAM-01-a, NAM-01-b
- 良い例:
  ```json
  {"name": "due_date", "type": "date", ...}
  ```
- 悪い例:
  ```json
  {"name": "dueDate", "type": "date", ...}
  ```

### NAM-02 役割ごとの名前を表のとおりにする

- 軸: C3
- 決定: 次の役割の名前を表のとおりにする。
  | 役割 | 名前 |
  |---|---|
  | CLI 名（依頼が名前を指定した場合） | 指定された名前 |
  | CLI 名（サブコマンドを持つ） | 依頼に最初に出てくる名詞の複数形（`notes`） |
  | CLI 名（サブコマンドを持たない） | `<動詞>-<目的語の複数形>`（`count-words`） |
  | 名詞の出力の型 | 名詞と同じ名前（名詞 `note` → 型 `note`） |
  | 識別子の項目 | CLI が番号を振る → `id`（`integer`）、利用者が一意の名前を付ける → `name`（`string`）。型の先頭に置く |
  | `create` を持つ名詞の型の作成日時 | `created_at`（`timestamp`） |
  | `edit` を持つ名詞の型の更新日時 | `updated_at`（`timestamp`。作成時は `created_at` と同じ値） |
  | `timestamp` の項目 | `<意味>_at` |
  | `date` の項目 | `<意味>_date` |
  | 識別子を受け取る位置引数 | 識別子の項目と同じ名前（`id` か `name`） |
- 理由: 同じ役割の名前が仕様ごとに違うと（`id`・`note_id`・`key`、`created`・`created_at`・`creation_time`）、CLI をまたいで使う利用者とスクリプトが毎回調べ直すことになる
- 強制: structure, review — `tools/clispec check` の NAM-02（型名、識別子の項目、`created_at`・`updated_at`、`_at`・`_date`、位置引数の名前）。CLI 名の選び方はレビュー用スキルで確かめる
- probe: NAM-02-a, NAM-02-b
- 良い例:
  ```json
  {"name": "id", "type": "integer", "values": [], "list": false, "nullable": false}
  ```
- 悪い例:
  ```json
  {"name": "note_id", "type": "integer", "values": [], "list": false, "nullable": false}
  ```

### NAM-03 標準の意味のオプションは標準の名前と型にし、短い名前は表からだけ導く

- 軸: C3
- 決定: 次の表の意味のオプションは表の名前と型で宣言し、短い名前は表の列だけから導き（仕様に書かない）、表の「使わない名前」と暗黙のオプションの名前（`help`、`version`、`json`）を宣言しない。
  | 名前 | 短い名前 | 型 | 意味 | 使わない名前 |
  |---|---|---|---|---|
  | `all` | `-a` | `boolean` | 普段は除く項目も含める | `everything`、`include-all` |
  | `debug` | `-d` | `boolean` | デバッグ用の情報を stderr に出す | `verbose` |
  | `dry-run` | `-n` | `boolean` | 変更を行わずに、行う変更を出力する | `dryrun`、`simulate`、`noop` |
  | `force` | `-f` | `boolean` | 確認が要る操作を行う（STATE-01） | `yes`、`confirm`、`assume-yes` |
  | `output` | `-o` | `file` | 出力を stdout ではなくファイルに書く | `out`、`outfile`、`output-file`、`out-file` |
  | `port` | `-p` | `integer` | 接続先のポート | なし |
  | `quiet` | `-q` | `boolean` | 出力を減らす | `silent` |
  | `user` | `-u` | `string` | 操作する利用者 | `username`、`login` |
- 理由: 同じ意味のオプションの名前と短い名前が CLI ごとに違うと（`--yes` と `--force`、`-v` が verbose か version か）、利用者の手が覚えられない。短い名前を表に限れば、どの言語の解析器でも同じ定義になる
- 出典: research.md「Command Line Interface Guidelines」（標準のフラグ名）
- 強制: structure — `tools/clispec check` の NAM-03（使わない名前、暗黙のオプションの名前、表の名前の型）
- probe: NAM-03-a, NAM-03-b
- 良い例:
  ```json
  {"name": "force", "type": "boolean", "values": [], "default": false, "required": false, "repeatable": false, "summary": "Delete notes that have tags"}
  ```
- 悪い例:
  ```json
  {"name": "yes", "type": "boolean", ...}
  ```

### NAM-04 標準の動詞は5つに決め、同じ意味の別の語を使わない

- 軸: C4
- 決定: 動詞を次の表で決め、表の「使わない語」を動詞にせず、標準の動詞は表の位置引数・出力の種類で使う。
  | 動詞 | 操作 | 位置引数 | `output.kind` | 使わない語 |
  |---|---|---|---|---|
  | `create` | 1件作る | 識別子が `name` なら `name`、`id` なら持たない（値は全部オプションで受け取る） | `object` | `add`、`new`、`make`、`insert`、`register` |
  | `list` | 条件に合う複数件を返す | なし | `list` | `ls`、`search`、`find`、`query`、`filter` |
  | `view` | 1件を返す | 識別子 | `object` | `show`、`get`、`fetch`、`read`、`display`、`describe`、`inspect`、`info` |
  | `edit` | 1件を変える | 識別子 | `object` | `update`、`modify`、`change`、`set` |
  | `delete` | 1件を消す（消した1件を返す） | 識別子 | `object` | `remove`、`rm`、`del`、`destroy`、`erase`、`drop` |
  | 表に無い操作（`archive`、`export`） | 英小文字1語の動詞 | 1件に対する操作なら識別子 | OPS-04 の決定表 | 上の「使わない語」 |
- 理由: `add`・`create`・`new` や `delete`・`remove`・`rm` が混ざると、利用者は名詞ごとに動詞を覚え直すことになる。標準の動詞の引数と出力を固定すれば、名詞が増えても形が同じになる
- 出典: research.md「Command Line Interface Guidelines」（Subcommands の "Don't have ambiguous or similarly-named commands."）
- 強制: structure — `tools/clispec check` の NAM-04（使わない語、標準の動詞の位置引数と `output.kind`）
- probe: NAM-04-a, NAM-04-b
- 良い例:
  ```json
  {"path": ["note", "delete"], ...}
  ```
- 悪い例:
  ```json
  {"path": ["note", "remove"], ...}
  ```

### NAM-05 名前で値の種類が分かるようにする

- 軸: C5
- 決定: 真偽値の項目とオプションの名前を `is_`・`has_`・`is-`・`has-`・`no-` で始めず、`list` が `true` の項目の名前を複数形（`s` で終わる）にし、`repeatable` が `true` のオプションの名前を単数形（`s` で終わらない）にする。
- 理由: `is_done` と `done`、`--tags` と `--tag` が混ざると、JSON のキーとオプション名を推測できなくなる。`--no-x` は解析器によって受け付けない（DEP-03）
- 出典: research.md「引数解析器の実測」
- 強制: structure — `tools/clispec check` の NAM-05
- probe: NAM-05-a, NAM-05-b
- 良い例:
  ```json
  {"name": "tags", "type": "string", "values": [], "list": true, "nullable": false}
  ```
- 悪い例:
  ```json
  {"name": "is_archived", "type": "boolean", "values": [], "list": false, "nullable": false}
  ```

### NAM-06 名前に略語を使わない

- 軸: C6
- 決定: 名前（CLI 名、名詞、動詞、オプション、位置引数、型、項目、環境変数）を `-`・`_` で区切った語に、表の略語を使わず、略語として使ってよい語を `id`・`url`・`json`・`dir`・`max`・`min` の6つにする。
  | 使わない略語 | 代わりの語 |
  |---|---|
  | `num`、`no`、`cnt` | `number`、`count` |
  | `desc`、`descr` | `description` |
  | `msg` | `message` |
  | `cfg`、`conf` | 使わない（設定ファイルを持たない。STATE-01） |
  | `tmp` | `temporary` |
  | `str`、`val`、`obj`、`arr` | 意味を表す語 |
  | `len`、`idx` | `length`、`index` |
  | `pwd`、`usr` | `password`、`user` |
  | `src`、`dst`、`dest` | `source`、`destination` |
  | `ts`、`dt` | `_at`、`_date`（NAM-02） |
  | `qty`、`amt`、`addr`、`info` | `quantity`、`amount`、`address`、意味を表す語 |
- 理由: `--desc` と `--description` が混ざると、利用者は CLI ごとに綴りを覚え直すことになる
- 強制: structure — `tools/clispec check` の NAM-06
- probe: NAM-06-a
- 良い例:
  ```json
  {"name": "description", "type": "string", ...}
  ```
- 悪い例:
  ```json
  {"name": "desc", "type": "string", ...}
  ```

### NAM-07 オプション名を項目名から機械的に作る

- 軸: C7
- 決定: 名詞の型を持つ標準の動詞のコマンドに、次の表の「必ず置く」オプションを全部置き、「置いてよい」以外のオプションを置かない。項目のオプション名は `<項目名の _ を - に替えた名前>`（`list` の項目は単数形）にし、型・`values` を項目と同じにする。
  | 動詞 | 必ず置くオプション | 置いてよいオプション |
  |---|---|---|
  | `create` | 「設定できる項目」（識別子・`created_at`・`updated_at` を除く全項目）のオプション | 項目の値をファイルから読む `<同じ名前>-file`（`file`）、標準のオプション |
  | `edit` | 「設定できる項目」のオプションと、`nullable`・`list`・`boolean` の項目の値を消す `clear-<項目名の _ を - に替えた名前>`（`boolean`、`default` は `false`。`list` の項目も複数形のまま） | 項目の値をファイルから読む `<同じ名前>-file`（`file`）、標準のオプション |
  | `list` | `limit`（`integer`、`default` は 20）、`sort`（`enum`、`values` は `list` でない全項目、`default` は識別子の項目） | 項目の値で絞り込む `<同じ規則の名前>`、`date`・`integer`・`number` の項目の範囲で絞り込む `<同じ規則の名前>-from`・`<同じ規則の名前>-to`（両端を含み、2つ組で置く）、標準のオプション |
  | `view`、`delete` | なし | 標準のオプション |
  | 表に無い動詞、サブコマンドを持たない CLI | なし | 制限しない |
  項目のオプションの `required`・`default`・`repeatable` は次の決定表で決める。
  | 項目 | `create` | `edit`、`list` の絞り込み（`-from`・`-to` を含む） |
  |---|---|---|
  | `boolean` | `false`・`false`・`false` | `false`・`false`・`false` |
  | `list` が `true` | `false`・`null`・`true` | `false`・`null`・`true` |
  | `nullable` が `true` | `false`・`null`・`false` | `false`・`null`・`false` |
  | 上のどれでもない | 依頼が既定値を決めていれば `false`・その値・`false`、決めていなければ `true`・`null`・`false` | `false`・`null`・`false` |
- 理由: 項目 `due_date` に対して `--due`・`--due-date`・`--deadline` が混ざったり、create で一部の項目だけを受け取れたりすると、`--json` の出力とオプションの対応を利用者が推測できない。必ず置くものを決めておけば、`make field` が機械的に足せる
- 強制: structure — `tools/clispec check` の NAM-07
- probe: NAM-07-a, NAM-07-b, NAM-07-c, NAM-07-d
- 良い例:
  ```json
  {"name": "due-date", "type": "date", ...}
  ```
- 悪い例:
  ```json
  {"name": "deadline", "type": "date", ...}
  ```

## CODE 書き方

### CODE-01 仕様の各オブジェクトはキーを全部、決まった順と並びで書く

- 軸: D1
- 決定: 仕様の各オブジェクトに次の表のキーを全部この順で書き、表に無いキーを書かず、配列を表の「並び」の順にする（並びとキーの順は `make fix` が直す）。
  | オブジェクト | キー（この順） | 並び |
  |---|---|---|
  | 仕様 | `name`、`version`、`summary`、`storage`、`commands`、`types`、`env` | — |
  | コマンド | `path`、`summary`、`args`、`options`、`output`、`exit_codes` | `path` の語の辞書順 |
  | 位置引数 | `name`、`type`、`values`、`required`、`variadic`、`summary` | 書いた順（最大1つ） |
  | オプション | `name`、`type`、`values`、`default`、`required`、`repeatable`、`summary` | `name` の辞書順 |
  | 出力 | `kind`、`type` | — |
  | 型 | `name`、`fields` | `name` の辞書順 |
  | 項目 | `name`、`type`、`values`、`list`、`nullable` | 識別子の項目を先頭に、残りは `name` の辞書順 |
  | 環境変数 | `name`、`type`、`values`、`default`、`summary` | `name` の辞書順 |
  | `values`、`exit_codes` | — | 辞書順、昇順 |
- 理由: 省略できるキーがあると「書かない」と「`false` と書く」に分かれ、並びが自由だと同じ設計でも差分が出る。全部を書かせ、順は formatter に任せれば、同じ設計は同じ文字列になる
- 強制: format, structure — `tools/clispec fmt --check`（キーの順・配列の並び・字下げ）と `tools/clispec check` の CODE-01（キーの過不足）
- probe: CODE-01-a, CODE-01-b
- 良い例:
  ```json
  {"name": "name", "type": "string", "values": [], "required": true, "variadic": false, "summary": "Name of the tag"}
  ```
- 悪い例:
  ```json
  {"name": "name", "type": "string", "summary": "Name of the tag"}
  ```

### CODE-02 値の型は決定表で選び、型ごとの制約を守る

- 軸: D3
- 決定: 値の型を次の決定表で選び、型ごとの制約を守る。
  | 値 | 型 | 使える場所 |
  |---|---|---|
  | 真偽（指定したかどうか） | `boolean` | オプション（`default` は `false`、`required`・`repeatable` は `false`）、項目 |
  | 整数（件数、番号、ポート） | `integer` | 全部 |
  | 小数 | `number` | 全部 |
  | 決まった選択肢の1つ | `enum`（`values` に選択肢を書く。`enum` 以外の型は `values` を `[]`） | 全部 |
  | 日付 | `date`（`YYYY-MM-DD`） | 全部 |
  | 日時 | `timestamp`（RFC 3339 の UTC、`Z` で終わる） | 項目だけ |
  | 読む・書くファイルのパス（`-` は stdin・stdout） | `file` | 位置引数、オプション、環境変数 |
  | ディレクトリのパス | `directory` | 位置引数、オプション、環境変数 |
  | 上のどれでもない文字列 | `string` | 全部 |
  `default` は型に合う値か `null` にし、`required` か `repeatable` が `true` のオプションの `default` は `null` にし、位置引数は `variadic` が `false` なら `required` を `true` にする。
- 理由: 日付を `string` にして summary で形式を説明するか `date` にするかが作者ごとに分かれると、実装ごとに検証の有無が変わる
- 出典: research.md「POSIX Utility Conventions」（Guideline 13 の `-`）
- 強制: structure, review — `tools/clispec check` の CODE-02（型の名前、使える場所、`values`・`default`・`required` の組）。値の意味に合う型かはレビュー用スキルで確かめる
- probe: CODE-02-a, CODE-02-b
- 良い例:
  ```json
  {"name": "due-date", "type": "date", "values": [], "default": null, "required": false, "repeatable": false, "summary": "Due date of the note"}
  ```
- 悪い例:
  ```json
  {"name": "due-date", "type": "string", "values": [], "default": null, "required": false, "repeatable": false, "summary": "Due date in YYYY-MM-DD format"}
  ```

### CODE-03 大きさの上限を守る

- 軸: D6
- 決定: 1つの仕様の大きさを、名詞8個以下、1コマンドの位置引数1個以下、1コマンドのオプション10個以下、1つの型の項目12個以下、summary 60文字以下にする。
- 理由: 位置引数が2つ以上あると、どちらが何かを利用者が覚える必要がある（clig.dev "If you've got two or more arguments for different things, you're probably doing something wrong."）。大きすぎるコマンドと型はヘルプと表が読めなくなる
- 出典: research.md「Command Line Interface Guidelines」（Arguments and flags）
- 強制: structure — `tools/clispec check` の CODE-03
- probe: CODE-03-a, CODE-03-b
- 良い例:
  ```text
  notes note move <id> --to-folder <folder>
  ```
- 悪い例:
  ```text
  notes note move <id> <folder>
  ```

### CODE-04 summary は英語の1文で、決まった形で書く

- 軸: D7
- 決定: summary を、ASCII の英語で大文字で始め、ピリオドで終えない1文にし、次の表の summary は表の文にする（`<noun>` は名詞、`<nouns>` は複数形、`a` は母音字で始まる名詞の前で `an`）。
  | 対象 | summary |
  |---|---|
  | `create` | `Create a <noun>` |
  | `list` | `List <nouns>` |
  | `view` | `View a <noun>` |
  | `edit` | `Edit a <noun>` |
  | `delete` | `Delete a <noun>` |
  | 表に無い動詞 | `<動詞を大文字で始めた語> ` で始める |
  | サブコマンドを持つ CLI | `Manage <nouns>`。名詞が2つなら `Manage <nouns> and <nouns>`、3つ以上なら `Manage <nouns>, <nouns>, and <nouns>`（名詞の辞書順） |
  | サブコマンドを持たない CLI | CLI 名の最初の語（動詞）を大文字で始めた語で始める |
  | 識別子を受け取る位置引数 | `ID of the <noun>` か `Name of the <noun>` |
  | `create` の項目のオプション | `<Label> of the <noun>`（`<label>` はオプション名の `-` を空白に替えた語で、語のうち `id`・`url`・`json` は `ID`・`URL`・`JSON` にする。`<Label>` はその先頭を大文字にした語。この表の全部の行の `<label>` も同じ） |
  | `edit` の項目のオプション | `New <label> of the <noun>` |
  | `edit` の `clear-` のオプション | `Clear the <label> of the <noun>`（`<label>` は項目名の `_` を空白に替えた語） |
  | `list` の絞り込みのオプション | `Show only <nouns> with this <label>` |
  | `list` の `-from`・`-to` のオプション | `date` の項目は `Show only <nouns> with <label> on or after this`・`Show only <nouns> with <label> on or before this`、`integer`・`number` の項目は `Show only <nouns> with <label> of at least this`・`Show only <nouns> with <label> of at most this`（`<label>` は `-from`・`-to` を除いた名前から作る） |
  | `-file` のオプション | `File to read the <label> of the <noun> from`（`<label>` は `-file` を除いた名前から作る） |
  | `list` の `limit` | `Maximum number of <nouns> to show` |
  | `list` の `sort` | `Field to sort the <nouns> by` |
  | データの置き場の環境変数 | `Directory for data files` |
- 理由: summary はヘルプとリファレンスにそのまま出る。言い回しが作者ごとに違うと（`Add a new note.`、`Creates a note`）、ヘルプの文面が CLI ごと・名詞ごとに揃わない
- 出典: research.md「GNU Coding Standards」
- 強制: structure — `tools/clispec check` の CODE-04
- probe: CODE-04-a, CODE-04-b
- 良い例:
  ```json
  "summary": "Create a note"
  ```
- 悪い例:
  ```json
  "summary": "Adds a new note."
  ```

### CODE-05 既定値・選択肢・必須は項目で表し、summary に書かない

- 軸: D8
- 決定: 既定値は `default`、選択肢は `values`、必須は `required`、繰り返しは `repeatable` に書き、summary には `default`・`one of`・`required`・`optional`・`repeatable`・`e.g.` と、`(` を書かない。
- 理由: ヘルプは項目から `(default: 20)` などの注記を生成する。summary にも書くと二重になり、値を変えたときに片方だけが古くなる
- 強制: structure — `tools/clispec check` の CODE-05
- probe: CODE-05-a
- 良い例:
  ```json
  "default": 20, "required": false, "repeatable": false, "summary": "Maximum number of notes to show"
  ```
- 悪い例:
  ```json
  "default": 20, "required": false, "repeatable": false, "summary": "Maximum number of notes (default 20)"
  ```

## ERR エラーと入力検証

### ERR-01 終了コードは5つに決め、コマンドごとの組を決定表で決める

- 軸: E1
- 決定: 終了コードを次の表の5つだけにし、各コマンドの `exit_codes` を `[0, 1, 2]` に、表の条件に当たるものを足した組にする。
  | コード | 意味 | コマンドの `exit_codes` に入れる条件 |
  |---|---|---|
  | 0 | 成功 | 全コマンド |
  | 1 | 予期しない失敗（読み書きの失敗、実装の誤り） | 全コマンド |
  | 2 | 使い方の誤り（未知のオプション、値の形式、必須の欠落、`--force` の欠落） | 全コマンド |
  | 3 | 指定した対象が無い | 識別子を受け取る位置引数（`create` を除く）、または `file`・`directory` の位置引数か `output` 以外の `file`・`directory` のオプションがある |
  | 4 | 衝突（同じ名前のものが既にある） | 識別子が `name` の名詞の `create` |
- 理由: 終了コードがコマンドごとに違うと、利用者のスクリプトが失敗の種類を見分けられない。126 以上はシェルが使い、64〜78（sysexits）は非推奨のため使わない
- 出典: research.md「終了コードの慣習」、「Command Line Interface Guidelines」
- 強制: structure, test — `tools/clispec check` の ERR-01（`exit_codes` が決定表の組と一致すること）。`tools/clispec conform` が、実装の終了コードが宣言した組に入ることを確かめる
- probe: ERR-01-a, ERR-01-b
- 良い例:
  ```json
  {"path": ["note", "view"], ..., "exit_codes": [0, 1, 2, 3]}
  ```
- 悪い例:
  ```json
  {"path": ["note", "view"], ..., "exit_codes": [0, 1, 64]}
  ```

### ERR-02 エラーは stderr に `<name>: <message>` の1行で出し、stdout には何も出さない

- 軸: E1
- 決定: 終了コードが0でないとき、実装は stderr に `<CLI 名>: <英語の説明>` の1行だけを書き、stdout には何も書かず、解析器が出すエラー文と usage はそのまま出さずにこの1行へ書き換える。
- 理由: Go の flag は usage を、Python の argparse は usage と `prog: error:` を、Node.js は例外のスタックを出す。書き換えなければ、同じ誤りが言語ごとに違う出力になる
- 出典: research.md「引数解析器の実測」、「Command Line Interface Guidelines」（Errors）
- 強制: test — `tools/clispec conform`（未知のオプション、値の形式の誤り、無い識別子に対して、stdout が空で stderr が `<name>: ` で始まる1行であること）
- probe: ERR-02-a
- 良い例:
  ```text
  notes: unknown option --colour
  ```
- 悪い例:
  ```text
  usage: notes note list [-h] [--limit LIMIT]
  notes note list: error: unrecognized arguments: --colour
  ```

### ERR-03 入力の誤りは、何かを行う前に決定表の終了コードで止める

- 軸: E2
- 決定: 実装は、仕様の型・`values`・`required` に合わない入力を、ファイルやデータに触れる前に次の決定表の終了コードで止める。
  | 入力 | 終了コード |
  |---|---|
  | 未知のオプション、前方一致の省略、値の欠落、型に合わない値（`integer` に `abc`、`date` に `2026/01/31`）、`values` に無い値、必須の欠落、位置引数の過不足 | 2 |
  | 形式は正しいが、指定した識別子・ファイル・ディレクトリが無い | 3 |
  | 上のどれでもない入力の誤り（業務上の制約） | 2 |
- 理由: 検証の場所と終了コードが実装ごとに違うと、同じ入力が言語によって途中まで実行されたり、別の終了コードになったりする
- 出典: research.md「引数解析器の実測」（Node.js は値の型を検証しない）
- 強制: test — `tools/clispec conform`（`integer`・`enum`・`date` の不正な値、必須の欠落、無い識別子）
- probe: ERR-03-a, ERR-03-b
- 良い例:
  ```text
  notes note list --limit abc   → 終了コード 2
  ```
- 悪い例:
  ```text
  Node.js の parseArgs が返した "abc" を Number() して NaN のまま一覧を出す
  ```

## STATE 状態とデータの流れ

### STATE-01 設定ファイルとプロンプトを持たず、値はオプション・環境変数・既定値の順に決め、データは決まった置き場に置く

- 軸: E3
- 決定: CLI は設定ファイルとプロンプト（対話の入力）を持たず、値をオプション → 環境変数 → `default` の順で決め、確認が要る操作（一度に複数件を消す・変える操作）は `-f/--force` が無ければ終了コード2で止め、データを保存する CLI は `storage` を `data` にしてデータの置き場を次の順で決める。
  | 順 | データの置き場 |
  |---|---|
  | 1 | 環境変数 `<PREFIX>_DATA_DIR`（空でない絶対パス） |
  | 2 | Linux・macOS：`$XDG_DATA_HOME/<name>`（空でない絶対パス）。Windows：`%LOCALAPPDATA%\<name>` |
  | 3 | Linux・macOS：`$HOME/.local/share/<name>` |
  `storage` が `data` の仕様は `env` に `{"name": "<PREFIX>_DATA_DIR", "type": "directory", "values": [], "default": "$XDG_DATA_HOME/<name>", "summary": "Directory for data files"}` を書き、それ以外の環境変数は同じ名前のオプション（`<PREFIX>_<オプション名を大文字にし - を _ に替えた名前>`）の既定値を変えるものだけにする。
- 理由: 設定ファイルの形式（TOML・YAML・JSON）と置き場、プロンプトの有無は言語ごとに標準ライブラリの対応が違い、実装ごとに揺れる。値の決め方と置き場を1つにすれば、どの言語でも同じ環境で同じ値になる
- 出典: research.md「Command Line Interface Guidelines」（Configuration、Interactivity）、「XDG Base Directory Specification 0.8 と Windows の Known Folders」
- 強制: structure, review — `tools/clispec check` の STATE-01（`storage` と `<PREFIX>_DATA_DIR` の対応、環境変数とオプションの対応）。確認が要る操作に `force` があるかはレビュー用スキルで確かめる
- probe: STATE-01-a, STATE-01-b
- 良い例:
  ```json
  {"name": "NOTES_DATA_DIR", "type": "directory", "values": [], "default": "$XDG_DATA_HOME/notes", "summary": "Directory for data files"}
  ```
- 悪い例:
  ```json
  {"name": "NOTES_CONFIG", "type": "file", "values": [], "default": "~/.notesrc", "summary": "Path to the config file"}
  ```

### STATE-02 標準の動詞の振る舞いを決定表のとおりにする

- 軸: X5
- 決定: 標準の動詞を持つ CLI の実装は、次の決定表のとおりに振る舞う。
  | 場面 | 振る舞い |
  |---|---|
  | `create` の `id` | これまでに振った最大の `id` + 1（最初は 1）。消した `id` を再利用しない |
  | `create`・`edit` の時刻 | `create` は `created_at` と `updated_at` を同じ現在時刻にし、`edit` は `updated_at` だけを現在時刻にする |
  | `create` で省略した項目 | `default`、`default` が `null` なら `null`（`nullable`）・`[]`（`list`）・`false`（`boolean`） |
  | `string` の値が空文字 | 終了コード2 |
  | `list` の項目の値 | 重複を除き、昇順に並べて保存する |
  | `list` の `--<項目>` | 値が等しい行。`list` の項目は値が要素にある行、`boolean` は `true` の行。`null` の行は出さない。繰り返したら、指定した値が全部要素にある行 |
  | `list` の `--<項目>-from`・`--<項目>-to` | 値が `from` 以上かつ `to` 以下の行。`null` の行は出さない |
  | `list` の絞り込みを2つ以上指定 | 全部に当てはまる行 |
  | `list` の `--sort` | 昇順。`null` は末尾、同じ値は識別子の昇順。文字列と `enum` は Unicode のコードポイント順、数は大小、真偽値は `false` が先、日付と日時は時刻の順 |
  | `list` の `--limit` | 絞り込みと並べ替えの後の先頭から N 件。1 未満は終了コード2 |
  | `edit` の `--<項目>` | 指定した値で置き換える。`list` の項目は、指定した値の集まりで置き換える |
  | `edit` の `--clear-<項目>` | `null`（`nullable`）・`[]`（`list`）・`false`（`boolean`）にする。同じ項目の `--<項目>` と一緒に指定したら終了コード2 |
  | `edit` に値を変えるオプションが1つも無い | 終了コード2 |
  | `delete` | 消した1件を出力する |
  | データに無い項目（仕様に後から足した項目） | `create` で省略したときと同じ値として読む。`updated_at` が無ければ `created_at` と同じ値として読む |
- 理由: 仕様（`cli.json`）は、コマンド・オプション・型を表すが、絞り込みの組み合わせや `null` の扱いは表さない。これが決まっていないと、同じ仕様から作った実装でも、言語や作者ごとに振る舞いが分かれる（収束テストのラウンド1で9人全員が指摘した）。[ADR 0007](adr/0007-standard-verb-behavior.md)
- 強制: test — `tools/clispec conform` の STATE-02（`make conform`。見本の実装は `make check` の単体テストで確かめる）。データのファイルの形式は公開面に含めない（DEP-02）ため、「データに無い項目」の行だけは適合テストで確かめない
- probe: STATE-02-a, STATE-02-b, STATE-02-c
- 良い例:
  ```text
  $ notes note list --tag work --tag urgent    # work と urgent の両方を持つメモ
  $ notes note edit 3 --clear-tags             # タグを空にする
  ```
- 悪い例:
  ```text
  $ notes note list --tag work --tag urgent    # どちらかを持つメモ
  $ notes note edit 3 --tag ""                 # 空文字で消す
  ```

## OPS ログ・設定・セキュリティ・表示

### OPS-01 主な出力だけを stdout に書き、成功時の stderr を空にし、色と進捗を出さない

- 軸: E5
- 決定: 実装は、出力の種類（OPS-04）が決める出力だけを stdout に書き、成功したとき（終了コード0）は stderr に何も書かず（`--debug` を指定されたときを除く）、ANSI のエスケープシーケンス（色、カーソル移動、進捗表示）を出さない。
- 理由: 成功時の stderr に案内や進捗を書くかどうかが実装ごとに違うと、スクリプトから実行したときの出力が言語で変わる。色を出さなければ、`NO_COLOR` と TTY の判定を実装ごとに作らずに済む
- 出典: research.md「Command Line Interface Guidelines」（Output）、「NO_COLOR」
- 強制: test — `tools/clispec conform`（成功した実行の stderr が空、全出力に ESC が無いこと）
- probe: OPS-01-a
- 良い例:
  ```text
  stdout: ID  CREATED_AT ...（表だけ）
  stderr: （空）
  ```
- 悪い例:
  ```text
  stderr: ✔ Created note 1
  ```

### OPS-02 秘密情報をオプションの値と環境変数で受け取らない

- 軸: E6, E8
- 決定: 名前に `password`・`passwd`・`token`・`secret`・`credential`・`api-key`・`private-key` を含むオプションは `<名前>-file`（`file`）にしてファイルか stdin（`-`）から読み、名前に `PASSWORD`・`TOKEN`・`SECRET`・`CREDENTIAL`・`API_KEY`・`PRIVATE_KEY` を含む環境変数を置かない。
- 理由: オプションの値は `ps` とシェルの履歴に、環境変数は子プロセスと `docker inspect` に漏れる
- 出典: research.md「Command Line Interface Guidelines」（"Do not read secrets directly from flags."、"Do not read secrets from environment variables."）
- 強制: structure — `tools/clispec check` の OPS-02
- probe: OPS-02-a, OPS-02-b
- 良い例:
  ```json
  {"name": "token-file", "type": "file", "values": [], "default": null, "required": true, "repeatable": false, "summary": "File that contains the API token"}
  ```
- 悪い例:
  ```json
  {"name": "token", "type": "string", ...}
  ```

### OPS-03 日時は UTC の RFC 3339、日付は YYYY-MM-DD、文面は ASCII の英語にする

- 軸: E7
- 決定: `timestamp` の値を秒までの UTC の RFC 3339（`2026-01-31T09:00:00Z`）、`date` の値を `YYYY-MM-DD` で入出力し、仕様の summary・名前・既定値を ASCII の文字だけで書く。
- 理由: 日時の形式とタイムゾーンが実装ごとに違うと（`+09:00`、ミリ秒の有無）、`--json` を比べるスクリプトが壊れる。ヘルプの文面は全実装で同じ文字列にする（OPS-05）ため、文字コードの扱いの差が出ない ASCII にする
- 出典: research.md「Command Line Interface Guidelines」
- 強制: structure, test — `tools/clispec check` の OPS-03（ASCII）。`tools/clispec conform` が `--json` の `timestamp`・`date` の値の形を確かめる
- probe: OPS-03-a, OPS-03-b
- 良い例:
  ```json
  {"id": 1, "created_at": "2026-01-31T09:00:00Z", "title": "Buy milk"}
  ```
- 悪い例:
  ```json
  {"id": 1, "created_at": "2026-01-31T18:00:00.123+09:00", "title": "Buy milk"}
  ```

### OPS-04 出力の種類を決定表で決め、--json とテキストの形を型から導く

- 軸: X1
- 決定: コマンドの `output.kind` を次の決定表で決め、`object` と `list` の出力の形を型から導く。
  | コマンドの結果 | `output.kind` | `output.type` |
  |---|---|---|
  | 1件を作る・変える・消す・返す | `object` | その1件の型 |
  | 複数件を返す（一覧、絞り込み、集計の行） | `list` | 1行の型 |
  | ファイルの中身や変換の結果そのもの | `raw` | `null` |
  | 上のどれでもない | `none` | `null` |
  | 出力の種類 | `--json` のとき | テキストのとき |
  |---|---|---|
  | `object` | 型の全項目を項目の順に持つ JSON オブジェクト | 見出しと1行の表 |
  | `list` | そのオブジェクトの JSON 配列（0件なら `[]`） | 見出しと行の表（0件なら見出しだけ） |
  | `raw` | `--json` を持たない | 結果そのもの |
  | `none` | `--json` を持たない | 何も書かない |
  テキストの表は、見出しを項目名の大文字、列の間を空白2つ、各列を左寄せ（最後の列は空白で埋めない）にし、値は `null` を `-`、リストを `,` でつないだもの（空なら `-`）、真偽値を `true`・`false` にする。
- 理由: 出力の形をコマンドごとに決めると、`--json` の最上位がオブジェクトか配列か、テキストが表か文章かが作者と実装ごとに分かれ、利用者がコマンドごとに読み方を変えることになる
- 出典: research.md「Command Line Interface Guidelines」（Output の `--json`）
- 強制: structure, test — `tools/clispec check` の OPS-04（`kind` と `type` の組）。`tools/clispec conform` が、実装の `--json` の出力の形（キーの集合と型）と表の見出しを確かめる
- probe: OPS-04-a, OPS-04-b
- 良い例:
  ```text
  ID  CREATED_AT            TAGS  TITLE     UPDATED_AT
  1   2026-01-31T09:00:00Z  home  Buy milk  2026-01-31T09:00:00Z
  ```
- 悪い例:
  ```text
  Created note #1 "Buy milk"
  ```

### OPS-05 ヘルプは仕様から生成した文面を、版は `<name> <version>` を、stdout に出して0で終える

- 軸: X1
- 決定: 実装は、`-h`・`--help` に対して `tools/clispec gen` が `cli.md` に書いたそのコマンドのヘルプの文面を1文字も変えずに stdout に書いて終了コード0で終え、ルートの `--version` に対して `<name> <version>`（先頭に `v` を付けない）の1行を stdout に書いて終了コード0で終え、サブコマンドを持つ CLI にコマンドを付けずに実行されたら ERR-02 の形で終了コード2で終える。
- 理由: 解析器の自動のヘルプは、言語ごとに出力先（Go は stderr）、書式、色（Python 3.14）が違う。仕様から生成した1つの文面を全実装が出せば、どの言語でも同じヘルプになる
- 出典: research.md「GNU Coding Standards」（--help と --version）、「引数解析器の実測」
- 強制: test — `tools/clispec conform`（全コマンドの `--help` と `-h` の stdout をリファレンスの文面と比べ、`--version` の出力を確かめる）
- probe: OPS-05-a, OPS-05-b
- 良い例:
  ```text
  $ notes --version
  notes 1.0.0
  ```
- 悪い例:
  ```text
  $ notes --version
  notes version v1.0.0 (go1.27.3 darwin/arm64)
  ```

### OPS-06 CLI 名と版は全レジストリで使える形にする

- 軸: X4
- 決定: CLI 名を NAM-01 の形にしたうえで Windows の予約名（`con`・`prn`・`aux`・`nul`・`com1`〜`com9`・`lpt1`〜`lpt9`）と `v` と数字だけの名前にせず、`version` を数字3つの `<MAJOR>.<MINOR>.<PATCH>`（プレリリースとビルドメタデータを付けない）にする。
- 理由: Go の `/vN`、PyPI の正規化、crates.io の文字種と長さ、Windows の予約名のどれかに当たる名前は、どこかの言語で配布できない。プレリリースの書式は PyPI の公開版で使えない
- 出典: research.md「配布」
- 強制: structure — `tools/clispec check` の OPS-06
- probe: OPS-06-a, OPS-06-b
- 良い例:
  ```json
  "name": "count-words", "version": "1.2.0"
  ```
- 悪い例:
  ```json
  "name": "CountWords", "version": "v1.2.0-rc.1"
  ```

## TEST テスト

### TEST-01 仕様は make check で、実装は make conform で確かめる

- 軸: F1, F5
- 決定: 確かめる対象と方法を次の表にし、作者は仕様のためのテストを書かない。
  | 対象 | 方法 | 通る条件 |
  |---|---|---|
  | 仕様（`specs/**`） | `make check` | 全部の検査が通る |
  | 実装（この基盤の外） | `make conform SPEC=specs/<name>/cli.json CMD="<実装を起動するコマンド>"` | 適合テストの全項目が通る |
  | 検査ツール（`tools/clispec`） | `make check` の unittest。見本の実装（`tools/clispec/tests/fixtures/notes_impl.py`）に適合テストをかける | 全部の検査が通る |
- 理由: 実装が仕様に合っているかを言語ごとのテストに任せると、確かめる項目が実装ごとに変わる。適合テストは仕様から確かめる項目を導くので、どの言語の実装にも同じ項目を当てられる
- 強制: test, doc — `tools/clispec/tests/test_conform.py` が見本の実装に適合テストをかける。実装を conform で確かめる手順は実装用スキルに書く
- probe: TEST-01-a
- 良い例:
  ```sh
  make conform SPEC=specs/notes/cli.json CMD="/home/me/src/notes/bin/notes"
  ```
- 悪い例:
  ```text
  実装のリポジトリで、ヘルプの文面だけを独自のテストで確かめる
  ```

## PROC 作業手順

### PROC-01 設計は決まった順に作る

- 軸: G1
- 決定: 設計を次の順で作る：(1) 依頼から操作・名詞・項目を書き出して STR-05 で構成を決める、(2) `make new`、(3) 名詞ごとに `make command` で動詞を足す、(4) 名詞ごとに `make field` で項目を足す、(5) `TODO` と、NAM-07 の決定表が依頼の既定値で決める値を埋め、依頼が求める絞り込み・標準のオプション・`-file` のオプションを足す、(6) 環境変数を STATE-01 で足す、(7) `make fix`、(8) `make check`。
- 理由: 手で書く順番が作者ごとに違うと、途中で項目とオプションの対応（NAM-07）が崩れ、直し方が作者ごとに変わる。動詞を先に足せば、`make field` が既存の create・edit・list に対応するオプションを足せる
- 強制: doc — 実装用スキルの「作る順序」
- 機械化しない理由: 作った順は出来上がった仕様に痕跡が残らない
- probe: なし
- 良い例:
  ```text
  make command NAME=notes NOUN=note VERB=create → make field NAME=notes NOUN=note FIELD=title TYPE=string
  ```
- 悪い例:
  ```text
  cli.json を開いて型・コマンド・オプションを手で書き、最後に make check で合わせる
  ```

### PROC-02 一緒に変えるものの組を守る

- 軸: G2
- 決定: 次の表の変更をするときは、右の列も同じ差分で変える。
  | 変更 | 一緒に変えるもの |
  |---|---|
  | `cli.json` の全部の変更 | `cli.md`（`make fix`）、`version`（PROC-06） |
  | 型に項目を足す | `make field` で、`create`・`edit` のオプションと `list` の `sort` の `values`（NAM-07） |
  | 型の項目を変える | `create`・`edit`・`list` の対応するオプションの型・`values`・名前（NAM-07） |
  | 名詞に `edit` を足す | その型の `updated_at`（NAM-02） |
  | 環境変数を足す | 同じ名前のオプション（STATE-01） |
  | `storage` を `data` にする | `<PREFIX>_DATA_DIR`（STATE-01） |
- 理由: 片方だけを変えると、リファレンスと仕様、出力とオプションが食い違う
- 強制: structure — `tools/clispec gen --check`（`cli.md`）、`tools/clispec check` の PROC-06（版）、NAM-02（`updated_at`）、STATE-01（環境変数）
- probe: PROC-02-a
- 良い例:
  ```text
  make field で due_date を足す → make fix（cli.md と version 1.1.0）
  ```
- 悪い例:
  ```text
  cli.json だけを直し、cli.md と version を古いままにする
  ```

### PROC-03 検査ツールの Python と uv の版は決まった手順で上げる

- 軸: G3
- 決定: 検査ツールの Python の版を上げるときは、(1) research.md の Python の節を新しい版で書き直し、(2) `.python-version` を変え、(3) `make check` と `python3 .foundation/bin/violation_probe.py --root .` を通し、(4) ADR 0003 に版と日付を追記する。
- 理由: 版を黙って上げると、argparse の既定値（3.15 の `suggest_on_error`）のような変更で見本の実装と適合テストの結果が変わり、原因を辿れなくなる
- 出典: research.md「Python 3.14.8（検査ツールの実行環境）」
- 強制: doc — 実装用スキルの「版を上げる依頼」の節
- 機械化しない理由: 上げる手順の順番は差分に残らない。版そのものは TOOL-04 の structure が検査する
- probe: なし
- 良い例:
  ```text
  research.md → .python-version → make check → probe → ADR 0003
  ```
- 悪い例:
  ```text
  .python-version だけを 3.15 にする
  ```

### PROC-04 ルールは ADR から順に変える

- 軸: G4, B6
- 決定: ルール・仕様の形式・検査ツールを変えるときは、ユーザーの承認を得てから (1) ADR、(2) `docs/design/rules.md`、(3) `tools/clispec` と `.foundation/probes.json`、(4) 見本の仕様（`specs/notes`、`specs/count-words`）と見本の実装、(5) `make check` と probe の順で変える。
- 理由: 検査だけを先に変えると、ルールの文書と検査が食い違い、作者がどちらに従うかで揺れる
- 強制: doc — AGENTS.md の「ルールを変えたいとき」
- 機械化しない理由: 変えた順番は差分に残らない
- probe: なし
- 良い例:
  ```text
  adr/0007-*.md → rules.md → tools/clispec → probes.json → specs/notes
  ```
- 悪い例:
  ```text
  tools/clispec の検査を緩めて check を通す
  ```

### PROC-05 make check とチェックリストを満たしてから完了と報告する

- 軸: G5
- 決定: 完了と報告してよいのは、`make check` が通り、実装用スキルの完了前チェックリストを全部満たし、報告に依頼から決まらなかった値とその根拠を書いたときだけにする。
- 理由: 完了の基準が作者ごとに違うと、検査の通っていない仕様や、根拠の無い既定値が残る
- 強制: doc — AGENTS.md の「完了の条件」と実装用スキルの「検証」「報告」
- 機械化しない理由: 報告の中身は差分に残らない。check そのものは機械が回す
- probe: なし
- 良い例:
  ```text
  make check の結果を貼り、--limit の既定値 20 は依頼に無かったため既定値表から決めたと書く
  ```
- 悪い例:
  ```text
  「設計しました」とだけ書く
  ```

### PROC-06 版は差分の種類から機械で決め、リリース済みの公開面は足すだけにする

- 軸: X2
- 決定: `version` を次の決定表の値にし、リリース済みの公開面の削除・変更（メジャーを上げる差分）にはユーザーの承認を書いた ADR を同じ差分に含める。
  | リリース済みの最新版からの差分 | `version` |
  |---|---|
  | リリース済みの仕様が無い | `1.0.0` |
  | 差分が無い | リリース済みの最新版と同じ |
  | コマンド・オプション・位置引数・環境変数・`values` の値・項目・型の削除、既存の要素の `summary` 以外の値の変更、既存のコマンドへの必須の位置引数・オプションの追加、`storage` の変更 | メジャーを1上げ、マイナーとパッチを0にする |
  | 上に当たらない追加（コマンド、任意のオプション、項目、型、環境変数、`values` の値） | マイナーを1上げ、パッチを0にする |
  | `summary` だけの変更 | パッチを1上げる |
- 理由: 版の上げ方を作者が判断すると、同じ差分でもマイナーとパッチに分かれ、互換性を壊す変更がマイナーで出る
- 出典: research.md「Semantic Versioning 2.0.0」、「Command Line Interface Guidelines」（Future-proofing）
- 強制: structure, review — `tools/clispec check` の PROC-06（リリース済みの最新版と比べて期待する版を計算し、一致しなければ期待値を出す）。`make fix` はパッチとマイナーの版を自動で書き、メジャーは書かない（承認と ADR が要るため）。ADR の有無はレビュー用スキルで確かめる
- probe: PROC-06-a, PROC-06-b
- 良い例:
  ```text
  1.0.0 がリリース済みで、note list に --tag を足す → "version": "1.1.0"
  ```
- 悪い例:
  ```text
  1.0.0 がリリース済みで、--limit を消す → "version": "1.1.0"
  ```

## TOOL 道具と自動化

### TOOL-01 整形は tools/clispec fmt に任せる

- 軸: H1
- 決定: `cli.json` の字下げ（空白2つ）、キーの順、配列の並び、スカラーだけの配列を1行に書く形を `tools/clispec fmt`（`make fix`、編集後の hooks）に任せ、エディタの設定は `.editorconfig`（UTF-8、LF、末尾の改行、行末の空白なし）にする。
- 理由: 整形を手で揃えると作者ごとに改行の位置が変わり、内容が同じでも差分が出る
- 強制: format — `tools/clispec fmt --check`
- probe: TOOL-01-a
- 良い例:
  ```json
  "values": ["created_at", "title"],
  ```
- 悪い例:
  ```json
  "values": [
      "title", "created_at"
  ],
  ```

### TOOL-02 編集の直後は hooks、完了の前は make check を回す

- 軸: H2
- 決定: `cli.json` を編集した直後は hooks（`make after-edit FILE=<path>`：整形、版（PROC-06。メジャーを除く）、リファレンスの生成、その仕様の検査）が回り、完了の前に作者が `make check` を回し、コミット前と CI の検査は置かない。
- 理由: 編集のたびに整形と生成を回せば、`cli.md` の更新忘れと整形の差が作者の手順に依存しなくなる
- 強制: doc — AGENTS.md の「コマンド」と「完了の条件」、`.claude/settings.json`
- 機械化しない理由: いつ検査を回したかは差分に残らない。回した結果は `make check` で確かめる
- probe: なし
- 良い例:
  ```text
  cli.json を編集 → hooks が cli.md を更新 → 最後に make check
  ```
- 悪い例:
  ```text
  make check を回さずに完了と報告する
  ```

### TOOL-03 未知のキー、抑止の書き方、保護ファイルの変更で検査を黙らせない

- 軸: H3
- 決定: 仕様に表に無いキー（`$comment`、`x-` で始まるキー、`_` で始まるキー）を書かず、Python に manifest の `guard.suppressions` の書き方（`# noqa`、`# type: ignore`、`unittest.skip`、`skipTest`、`expectedFailure`）を書かず、保護ファイル（manifest の `protected`）を変えて検査を通さない。
- 理由: 検査を通すために例外の書き方や設定の変更が使えるなら、ルールは無いのと同じになる
- 強制: structure, review — `tools/clispec check` の CODE-01（未知のキー）、`.foundation/bin/guard.py`（抑止の書き方）。保護ファイルの差分はレビュー用スキルで確かめる
- probe: TOOL-03-a, TOOL-03-b
- 良い例:
  ```json
  {"name": "name", "type": "string", "values": [], "required": true, "variadic": false, "summary": "Name of the tag"}
  ```
- 悪い例:
  ```json
  {"name": "title", "x-lint-ignore": "CODE-04", ...}
  ```

### TOOL-04 Python 3.14 を uv で起動し、Makefile を唯一の入口にする

- 軸: H4
- 決定: 検査ツールを `.python-version`（`3.14`）の Python で `uv run --no-project` から起動し、作者が回すコマンドを `Makefile` のターゲット（`check`、`fix`、`new`、`command`、`field`、`release`、`conform`、`after-edit`）だけにし、検査ツールは Python の標準ライブラリだけで書く。
- 理由: `python3` をそのまま使うと、macOS では EOL の 3.9 が動き、argparse の挙動（3.14 の色、3.15 の候補の提示）が人によって変わる。入口を Makefile に揃えれば、作者が引数の渡し方を迷わない
- 出典: research.md「Python 3.14.8（検査ツールの実行環境）」、「uv 0.13.3」
- 強制: structure — `make check` の先頭の `version` ターゲットが、起動した Python が 3.14 系であることを確かめる
- probe: TOOL-04-a
- 良い例:
  ```sh
  make check
  ```
- 悪い例:
  ```sh
  python3 tools/clispec check specs
  ```

## 対象外とした軸

揺れない軸、またはこの分野に無い軸と、その理由を書く。

| 軸 | 理由 |
|---|---|
| A7 | 仕様は1ファイルで、入口ファイル（index・barrel・main）の仕組みが無い |
| D2 | 仕様は1ファイルで import と export が無い（外の参照の禁止は DEP-01） |
| D4 | 仕様は宣言だけで、制御フローを書かない |
| D5 | 仕様は宣言だけで、値の再代入や破壊的な操作を書かない（リリース済みの仕様を変えないことは STR-04） |
| E4 | 仕様の形式は実行の並行性を表さず、CLI の外から見える振る舞いに非同期の差が出ない |
| F2 | 作者はテストを書かない。適合テストの項目は仕様から導かれる（TEST-01） |
| F3 | 作者はテストを書かない。適合テストは実装を本物のまま外から実行し、偽物を作らない（TEST-01） |
| F4 | 作者はテストを書かない。適合テストが型から入力の値を作る（TEST-01） |
