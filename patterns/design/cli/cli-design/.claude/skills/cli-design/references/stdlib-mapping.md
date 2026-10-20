# 仕様を各言語の標準ライブラリで実装する対応表

設計（`specs/<name>/cli.json` と生成された `cli.md`）を実装するときに読む。対象は Go・Python・Node.js・Rust で、それ以外の言語でも 1〜4 節の共通の処理をその言語の標準ライブラリで行う。

## 0. なぜこの表があるか

標準ライブラリの引数解析器は、同じ入力でも言語ごとに結果が違う（[research.md「引数解析器の実測」](../../../../docs/design/research.md)）。たとえば Go の flag はヘルプを stderr に出し、Python の argparse は既定で前方一致を受け付け、Node.js の parseArgs は未知のオプションで例外を投げる。そこで、

1. 解析器に任せる範囲を、全言語で同じ結果になる部分だけに絞り（DEP-03）
2. 残りの差（ヘルプ、エラーの形、型の変換、順序）を、この表の共通の処理で埋める

ことで、どの言語で実装しても適合テスト（`make conform`）が同じ結果になるようにしている。見本の実装は Python の [notes_impl.py](../../../../tools/clispec/tests/fixtures/notes_impl.py) と [count_words_impl.py](../../../../tools/clispec/tests/fixtures/count_words_impl.py) である。

## 1. 共通の処理の順

全言語で、`main` の中を次の順にする。`argv` はプログラム名を除いた引数の列である。

| 順 | 処理 | 決まり |
|---|---|---|
| 1 | コマンドを決める | サブコマンドを持つ CLI は、`argv` の先頭2語が仕様のコマンドの `path` と完全に一致するときだけ、そのコマンドにする。一致しないときは、`argv[0]` が `-h`・`--help` ならルートのヘルプ、`argv` が `["--version"]` だけなら版、それ以外は使い方の誤り（終了コード2） |
| 2 | 区切る | 残りの引数を、最初の `--` の前（`head`）と後ろ（`tail`）に分ける。`tail` は全部位置引数 |
| 3 | ヘルプ | `head` に `-h` か `--help` があれば、そのコマンドのヘルプの文面を stdout に書いて終了コード0。ほかの誤りより先に行う |
| 4 | 版 | サブコマンドを持たない CLI は、`argv` が `["--version"]` だけなら `<name> <version>` を stdout に書いて終了コード0 |
| 5 | 1つのダッシュの語を確かめる | `head` のうち `-` で始まり `--` で始まらない語は、`-`（stdin・stdout）、`-h`、そのコマンドに置いた標準のオプションの短い名前（NAM-03 の表。`-o` など）だけを受け付け、それ以外は使い方の誤り。`-limit` を `--limit` とみなしたり、`-output` を `-o utput` と読んだりする解析器の差を、ここで止める |
| 6 | 解析する | 標準ライブラリの解析器で、オプションと位置引数を順序に依存せずに読む（言語ごとの書き方は 5 節） |
| 7 | 値を変換する | 2 節の表で変換し、合わなければ使い方の誤り。必須の欠落、`values` に無い値、位置引数の過不足も使い方の誤り |
| 8 | 既定値を決める | オプションが無ければ同じ名前の環境変数（`<PREFIX>_<オプション名を大文字にし - を _ に替えた名前>`）、それも無ければ `default`（STATE-01） |
| 9 | 実行する | 対象が無ければ終了コード3、同じ名前が既にあれば4、読み書きの失敗は1、業務上の制約に反する入力は2（ERR-01、ERR-03） |
| 10 | 書く | 3 節の形で、結果を全部作ってから stdout に書く。失敗したときは stdout に何も書かず、stderr に `<name>: <英語の説明>` の1行だけを書く（ERR-02） |

ヘルプの文面は `cli.md` の各コマンドの ```` ```text ```` の中身を1文字も変えずに定数として埋め込み、最後に改行を1つ付けて書く（OPS-05）。解析器の自動のヘルプと usage は使わない。

## 2. 値の変換

| 仕様の型 | 受け付ける文字列 | 変換 |
|---|---|---|
| `integer` | 正規表現 `^-?[0-9]+$` | 整数。`0x10`・`1_000`・`+3`・前後の空白は受け付けない（Go の `strconv.ParseInt(s, 0, …)`、Python の `int()`、JavaScript の `Number()` はこれらを受け付けるので、先に正規表現で確かめる） |
| `number` | 正規表現 `^-?[0-9]+(\.[0-9]+)?$` | 浮動小数 |
| `boolean` | 値を取らない（`--force`） | 指定されたら真。`--force=true` は使い方の誤り |
| `enum` | `values` のどれかと完全に一致 | 文字列のまま |
| `date` | 正規表現 `^[0-9]{4}-[0-9]{2}-[0-9]{2}$` で、実在する日付 | 文字列のまま（`2026-02-30` は誤り） |
| `file` | 空でない文字列。`-` は stdin（読む）か stdout（`--output`） | 読むファイルが無ければ終了コード3 |
| `directory` | 空でない文字列 | 無ければ終了コード3 |
| `string` | 空でない文字列 | そのまま |

`-` で始まる値は、オプションには `--name=-1` の形で、位置引数には `--` の後ろで渡す（DEP-03）。`--name -1` は 1 節の5で誤りになる。

## 3. 出力

| 項目 | 決まり |
|---|---|
| `--json` | 1行の JSON と改行。オブジェクトのキーは型の項目の順。区切りに空白を入れない。非 ASCII の文字はエスケープせずに UTF-8 で書く。`null` は `null` |
| テキストの表 | 見出しは項目名の大文字。列の間は空白2つ。各列を文字数（Unicode のコードポイント数）で左寄せし、最後の列は空白で埋めない。`null` は `-`、リストは `,` でつなぎ空なら `-`、真偽値は `true`・`false`。`list` は0件でも見出しを書く |
| `timestamp` | UTC で秒まで、`2026-01-31T09:00:00Z` |
| `raw` | 結果そのもの。`--json` を持たない |
| `none` | 何も書かない |
| 色・進捗 | 書かない（OPS-01）。成功したときの stderr は空 |
| `-o/--output` | 指定されたら、stdout に書くはずだった内容をそのファイルに書き、stdout には何も書かない。`-` なら stdout |

## 4. データの置き場

`storage` が `data` の CLI は、次の順で最初に当てはまるディレクトリを使い、無ければ権限 0700 で作る（STATE-01）。中のファイルの形式は公開面に含めない（DEP-02）が、既定は `<CLI 名>.json` の1ファイルにする。

1. `<PREFIX>_DATA_DIR` が空でない絶対パスなら、そのディレクトリ
2. Linux・macOS：`XDG_DATA_HOME` が空でない絶対パスなら `$XDG_DATA_HOME/<name>`。Windows：`%LOCALAPPDATA%\<name>`
3. Linux・macOS：`$HOME/.local/share/<name>`

## 4.1 標準の動詞の振る舞い

標準の動詞（`create`・`list`・`view`・`edit`・`delete`）は、rules.md の STATE-02 の決定表のとおりに振る舞う。`make conform` が全部を確かめる。実装で間違えやすい点は次のとおり。

| 場面 | 実装の仕方 |
|---|---|
| `id` を振る | データのファイルに「次に振る `id`」を持ち、`create` のたびに1つ増やす。最大の `id` + 1 を毎回数えると、最後の1件を消した後に同じ `id` を振ってしまう |
| `list` の項目の値 | 受け取った値の重複を除き、昇順に並べてから保存する |
| 絞り込み | 指定された全部の条件に当てはまる行だけを残す（AND）。`list` の項目の `--<項目>` を繰り返したら、全部の値が要素にある行。値が `null` の行は、どの絞り込みでも残さない |
| 並べ替え | `(値が null か, 値, 識別子)` の組で昇順に並べる（`null` は末尾）。文字列は Unicode のコードポイント順で比べる。Go の `<` と Python の `<` と Rust の `Ord` はこの順になる。Node.js の `<` は UTF-16 の順なので、`[...a]` などでコードポイントの配列にして比べる。日付と日時は文字列のまま比べれば時刻の順になる |
| `--limit` | 絞り込みと並べ替えの後で先頭から切る。1 未満は終了コード2 |
| `edit` | 値を変えるオプション（`--clear-<項目>` を含む）が1つも無ければ終了コード2。`--<項目>` は置き換え（`list` の項目は指定した値の集まりで置き換える）。`--clear-<項目>` は `null`・`[]`・`false` にし、同じ項目の `--<項目>` と一緒なら終了コード2。`updated_at` を現在時刻にする |
| 空文字 | `string` の値（位置引数、オプション、絞り込み）が空文字なら終了コード2 |
| 後から足した項目 | 読み込んだ行にその項目が無ければ、`create` で省略したときの値（`default`、`null`、`[]`、`false`）として扱う。`updated_at` が無ければ `created_at` の値にする。この行は適合テストで確かめないので、実装者が守る |

## 5. 言語ごとの書き方

### Go（`flag`、go1.27.3）

- `fs := flag.NewFlagSet("<コマンドの呼び出し方>", flag.ContinueOnError)`、`fs.SetOutput(io.Discard)`、`fs.Usage = func() {}`。エラーは `<name>: <err>` にして終了コード2
- 真偽値は `fs.Bool`、それ以外は全部 `fs.String` で受けて 2 節で変換する（`fs.Int` は `0x10` を受け付ける）。繰り返すオプションは、`Set` で追加する `flag.Value` を作る。短い名前は同じ変数に2回定義する（`fs.StringVar(&out, "output", "", "")` と `fs.StringVar(&out, "o", "", "")`）
- Go の flag は最初の位置引数で止まる。順序に依存させないため、`head` を次のように読む

  ```go
  var positional []string
  rest := head
  for {
      if err := fs.Parse(rest); err != nil {
          return usageError(err)
      }
      if fs.NArg() == 0 {
          break
      }
      positional = append(positional, fs.Arg(0))
      rest = fs.Args()[1:]
  }
  positional = append(positional, tail...)
  ```

- `--force=true` を Go は受け付けるので、1 節の5の前に、`head` に真偽値のオプションの `--<name>=` があれば使い方の誤りにする。オプションが指定されたかは `fs.Visit` で調べる（環境変数との優先順位）
- JSON は、項目の順にフィールドを並べ `json:"<項目名>"` を付けた構造体を、`enc := json.NewEncoder(os.Stdout)`、`enc.SetEscapeHTML(false)` で書く（`Encode` が改行を付ける）。日時は `t.UTC().Format("2006-01-02T15:04:05Z")`
- 版は定数 `const version = "<仕様の version>"` にし、`v` を付けない。配布はモジュールパスの最後の要素を CLI 名にし（`example.com/<name>`）、`go install example.com/<name>@latest` で入る形にする

### Python（`argparse`、3.14）

- 見本の実装と同じにする：`argparse.ArgumentParser` を継承して `error()` で例外を投げ（usage と `error:` を出させない）、`add_help=False`、`allow_abbrev=False`、`parse_intermixed_args` で読む
- 整数は正規表現で確かめる `type=` 関数を使う（`int()` は `1_000` を受け付ける）。`enum` は `choices=`、繰り返すオプションは `action="append"`、真偽値は `action="store_true"`、必須は `required=True`
- `-o` などの短い名前を持つオプションがあると、argparse は `-output` を `-o utput` と読む。1 節の5の確認を必ず入れる
- JSON は `json.dumps(value, ensure_ascii=False, separators=(",", ":"))`。日時は `datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")`
- 版は定数にするか `importlib.metadata.version("<name>")`。配布は `pyproject.toml` の `[project] name = "<name>"`、`version = "<仕様の version>"`、`[project.scripts] <name> = "<パッケージ>.__main__:main"`

### Node.js（`util.parseArgs`、v24 LTS）

- `parseArgs({ args, options, allowPositionals: true, strict: true })`。真偽値は `{ type: 'boolean' }`、それ以外は `{ type: 'string' }` で受けて 2 節で変換する。繰り返すオプションは `multiple: true`、短い名前は `short: 'o'`。`default` は使わず 1 節の8で決める
- 未知のオプションなどで例外を投げるので `try`/`catch` で捕まえ、`<name>: <message>` にして終了コード2。`process.exit()` ではなく `process.exitCode` を設定して、書き込みを最後まで流す
- parseArgs は短い名前の束ね（`-ab`）を受け付けるので、1 節の5の確認を必ず入れる
- JSON は `JSON.stringify(value) + '\n'`。日時は `new Date().toISOString().replace(/\.\d{3}Z$/, 'Z')`（ミリ秒を落とす）
- 版は `package.json` の `version` を `import pkg from './package.json' with { type: 'json' }` で読む。配布は `package.json` の `"name": "<name>"`、`"bin": { "<name>": "bin/<name>.js" }`、`"type": "module"`

### Rust（`std::env::args_os`、1.99.1）

- 標準ライブラリに引数解析器は無いので、`std::env::args_os().skip(1)` を手で読む。UTF-8 でない引数は使い方の誤り（`args()` は panic するので使わない）
- 読み方：`tail` は全部位置引数。`head` の各語について、`--<name>=<value>` は名前と値に分け、`--<name>` は値を取るなら次の語を値にし（無ければ誤り）、`-` 以外の `-` で始まる語は標準の短い名前だけを受け付け、それ以外の語は位置引数にする。名前は完全一致だけを受け付ける（前方一致をしない）
- JSON と日時の書式化は標準ライブラリに無い。JSON は文字列のエスケープ（`"`、`\`、制御文字を `\n`・`\r`・`\t`・`\u00XX`）を手で書き、日時は `SystemTime::now().duration_since(UNIX_EPOCH)` の日数から暦の日付を計算する（[civil_from_days](https://howardhinnant.github.io/date_algorithms.html#civil_from_days)）。`serde_json`・`chrono` などを使うなら、依頼に無い依存を足すことになるので ADR を書いてユーザーの承認を得る
- 版は `env!("CARGO_PKG_VERSION")`。`Cargo.toml` の `[package] name = "<name>"`、`version = "<仕様の version>"` にする。データの置き場は `std::fs::DirBuilder::new().recursive(true)` に `std::os::unix::fs::DirBuilderExt::mode(0o700)`

## 6. 適合テストをかける

実装ができたら、この基盤のディレクトリで次を回し、全項目が通るまで直す（TEST-01）。

```sh
make conform SPEC=specs/<name>/cli.json CMD="<実装を起動するコマンド>"
```

`CMD` はシェルを通さずに、この基盤のディレクトリから起動される。実装のリポジトリでビルドした実行ファイルか、起動するスクリプトを絶対パスで渡す（例：`CMD="/home/me/src/notes/bin/notes"`、`CMD="node /home/me/src/notes/bin/notes.js"`）。失敗は `FAIL <ルールID> <項目>: <詳細>` の形で出るので、ルールIDで rules.md を引き、この表の該当する行を確かめる。
