# cli-design の技術調査

採用した推奨には出典を付け、確認の状態を書いている。バージョンは、レジストリのコマンドや公式の機械可読な一覧で確かめた値である。「未確認」の項目が残っている間は、仕上げの検査（`rules_check.py --final`）が通らない。調査はすべて 2026-10-20 に行った。

この基盤は「CLI の外から見える形（設計）」を決める基盤であり、実装の言語を決めない。そのため調査は3つに分かれる。

1. 設計の指針（clig.dev、POSIX、GNU、XDG、NO_COLOR、SemVer、終了コード）
2. 各言語の標準ライブラリの引数解析器が、どの書式を同じ結果で解析できるか（実測）
3. 各言語で配布するときの名前と版の制約
4. この基盤の検査ツールを動かす道具（Python、uv、make）

## Command Line Interface Guidelines（clig.dev、版の表示なし）

- 確認方法：WebFetch https://clig.dev/ と原稿 https://raw.githubusercontent.com/cli-guidelines/cli-guidelines/main/content/_index.md（2026-10-20 取得。両者の内容は一致）
- 確認の状態：確認済み
- 公式の推奨：
  - 標準のフラグ名は次の13項目である："Use standard names for flags, if there is a standard."（[Arguments and flags](https://clig.dev/#arguments-and-flags)）
    | 短い名前 | 長い名前 | 意味 |
    |---|---|---|
    | `-a` | `--all` | All |
    | `-d` | `--debug` | Show debugging output |
    | `-f` | `--force` | Force |
    | なし | `--json` | Display JSON output |
    | `-h` | `--help` | Help。"This should only mean help." |
    | `-n` | `--dry-run` | Dry run |
    | なし | `--no-input` | 対話をしない |
    | `-o` | `--output` | Output file |
    | `-p` | `--port` | Port |
    | `-q` | `--quiet` | Display less output |
    | `-u` | `--user` | User |
    | なし | `--version` | Version |
    | `-v` | なし | "This can often mean either verbose or version." 混乱を避けるため使わない選択肢も示す |
  - "Prefer flags to args."、"Have full-length versions of all flags."、"Only use one-letter flags for commonly used flags"、"If you've got two or more arguments for different things, you're probably doing something wrong."（[Arguments and flags](https://clig.dev/#arguments-and-flags)）
  - "If possible, make arguments, flags and subcommands order-independent."（同上）
  - "Do not read secrets directly from flags."、"Consider accepting sensitive data only via files, e.g. with a `--password-file` flag, or via `stdin`."、さらに "Do not read secrets from environment variables."（[Arguments and flags](https://clig.dev/#arguments-and-flags)、[Environment variables](https://clig.dev/#environment-variables)）
  - "If input or output is a file, support `-` to read from `stdin` or write to `stdout`."（同上）
  - "Display help when passed `-h` or `--help` flags."、ヘルプの出力先は明記しない（[Help](https://clig.dev/#help)）
  - "The primary output for your command should go to `stdout`."、"Log messages, errors, and so on should all be sent to `stderr`."、"Display output as formatted JSON if `--json` is passed."（[Output](https://clig.dev/#output)）
  - 色は、出力が TTY でない、`NO_COLOR` が空でない、`TERM=dumb`、`--no-color` のどれかで消す（[Output](https://clig.dev/#output)）
  - "Return zero exit code on success, non-zero on failure."、"Map the non-zero exit codes to the most important failure modes."。具体値は示さない（[The Basics](https://clig.dev/#the-basics)）
  - "Only use prompts or interactive elements if `stdin` is an interactive terminal"、"Never _require_ a prompt."（[Interactivity](https://clig.dev/#interactivity)）
  - "Either `noun verb` or `verb noun` ordering works, but `noun verb` seems to be more common."、"Don't have ambiguous or similarly-named commands."、"Don't have a catch-all subcommand."、"Don't allow arbitrary abbreviations of subcommands."（[Subcommands](https://clig.dev/#subcommands)）
  - 設定の優先順位は「フラグ → 環境変数 → プロジェクトの設定 → ユーザーの設定 → システムの設定」。"Follow the XDG-spec."（[Configuration](https://clig.dev/#configuration)）
  - 環境変数名は "must only contain uppercase letters, numbers, and underscores (and mustn't start with a number)"（[Environment variables](https://clig.dev/#environment-variables)）
  - CLI 名は "Use only lowercase letters, and dashes if you really need to."、"Keep it short."（[Naming](https://clig.dev/#naming)）
  - "Subcommands, arguments, flags, configuration files, environment variables: these are all interfaces"、"Keep changes additive where you can."、"Changing output for humans is usually OK."（[Future-proofing](https://clig.dev/#future-proofing)）
- 採用するもの：NAM-03（標準のフラグ名と短い名前）、STR-05（`noun verb`）、NAM-04（似た名前の動詞を禁止）、DEP-03（順序に依存しない、前方一致の禁止）、OPS-02（秘密情報をフラグと環境変数で受けない）、OPS-01（stdout と stderr、色を出さない）、OPS-04（`--json`）、STATE-01（優先順位、XDG）、NAM-01・OPS-06（名前の文字種）、DEP-02・PROC-06（公開面と追加だけの変更）、ERR-01（主な失敗に終了コードを割り当てる）
- 採用しないもの：
  - `-d/--debug`、`-q/--quiet`、`--no-input`、`--plain`、`--no-color` を全コマンドに付けること。色・進捗・プロンプトをそもそも出さない（OPS-01、STATE-01）ため、消すためのフラグが要らない。`-d`・`-q` は要件が求めたときだけ標準名で付ける（NAM-03）
  - プロンプトによる確認。全コマンドを非対話にし、確認が要る操作は `-f/--force` で表す（STATE-01）
  - 設定ファイル（プロジェクト・ユーザー・システム）。設定はオプションと環境変数だけにする（STATE-01。ADR 0004）
  - `help` サブコマンド。ヘルプは `-h/--help` だけにする（OPS-05）
- ツールにできないこと：意味の判断（どの値を位置引数にするか、操作が破壊的か）。`tools/clispec check` の字面の検査と、レビュー用スキルで補う

## POSIX Utility Conventions（IEEE Std 1003.1-2024、XBD 12）

- 確認方法：WebFetch https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/V1_chap12.html（比較に Issue 7 の同じ章）
- 確認の状態：確認済み
- 公式の推奨：
  - Guideline 1・2：ユーティリティ名は2〜9文字の小文字と数字
  - Guideline 7："Option-arguments should not be optional."
  - Guideline 9："All options should precede operands on the command line."
  - Guideline 10："The first -- argument that is not an option-argument should be accepted as a delimiter indicating the end of options."
  - Guideline 13：ファイルを表すオペランドの `-` は標準入力（出力が明らかな場合は標準出力）を表す
  - 長いオプション（`--name`）には触れない
- 採用するもの：DEP-03（`--` の後ろは位置引数、オプションの値を省略可能にしない）、CODE-02（`file` 型の `-` は標準入力・標準出力）
- 採用しないもの：Guideline 5（短いオプションの束ね `-abo`）。Go の flag が受け付けないため、仕様に含めない（DEP-03）。Guideline 9（オプションを前に置く）は、clig.dev の「順序に依存しない」を優先する（DEP-03）。Guideline 1 の9文字の上限は採らず、20文字にする（OPS-06）
- ツールにできないこと：なし（書式は仕様の形式と適合テストで決まる）

## GNU Coding Standards（--version、--help、Option Table）

- 確認方法：WebFetch https://www.gnu.org/prep/standards/html_node/_002d_002dversion.html 、https://www.gnu.org/prep/standards/html_node/_002d_002dhelp.html 、https://www.gnu.org/prep/standards/html_node/Option-Table.html
- 確認の状態：確認済み
- 公式の推奨：
  - `--version` は "all on standard output, and then exit successfully."。1行目は "the version number proper starts after the last space."。名前は argv[0] から作らず固定の文字列にする
  - `--help` は standard output に出して "exit successfully"
  - Option Table（4.10 Table of Long Options）に、`all`・`debug`・`dry-run`・`force`・`output`・`quiet`・`verbose` などの慣習名がある
- 採用するもの：OPS-05（`--help` と `--version` を stdout に出して終了コード0、`--version` の1行目の形）
- 採用しないもの：`--version` の著作権行とライセンス行。1行だけにし、適合テストで完全一致を確かめられるようにする（OPS-05）
- ツールにできないこと：なし

## XDG Base Directory Specification 0.8 と Windows の Known Folders

- 確認方法：WebFetch https://specifications.freedesktop.org/basedir/latest/（0.8、2021-05-08）、https://learn.microsoft.com/en-us/windows/win32/shell/knownfolderid 、https://pkg.go.dev/os（go1.27.3）
- 確認の状態：確認済み
- 公式の推奨：
  - "If $XDG_DATA_HOME is either not set or empty, a default equal to $HOME/.local/share should be used."
  - "All paths set in these environment variables must be absolute." 相対パスなら無視する
  - 書き込み先のディレクトリが無ければ 0700 で作る
  - Windows のマシン固有のデータは `%LOCALAPPDATA%`（FOLDERID_LocalAppData）。`%USERPROFILE%` の直下に作らない
  - Go の os にはデータの置き場を返す関数が無い（`UserConfigDir`・`UserCacheDir`・`UserHomeDir` だけ）。`UserConfigDir` は macOS で `~/Library/Application Support` を返す
- 採用するもの：STATE-01（データの置き場の解決順：`<PREFIX>_DATA_DIR` → `$XDG_DATA_HOME/<name>` → `$HOME/.local/share/<name>`、Windows は `%LOCALAPPDATA%\<name>`、0700 で作る）
- 採用しないもの：macOS で `~/Library/Application Support` を使うこと。clig.dev の "Follow the XDG-spec." に従い、Linux と同じ置き場にする（言語ごとの関数の差を無くすため）
- ツールにできないこと：実装が置き場を正しく解決するかは適合テストでは環境変数 `<PREFIX>_DATA_DIR` の経路しか確かめられない。残りは実装の対応表（スキルの `references/stdlib-mapping.md`）で示す

## NO_COLOR（no-color.org）

- 確認方法：WebFetch https://no-color.org/（最終更新 2026-10-12）
- 確認の状態：確認済み
- 公式の推奨："Command-line software which adds ANSI color to its output by default should check for a `NO_COLOR` environment variable that, when present and not an empty string (regardless of its value), prevents the addition of ANSI color."
- 採用するもの：OPS-01（色をそもそも出さないため、NO_COLOR を読む必要が無い）
- 採用しないもの：色付きの出力
- ツールにできないこと：TTY での出力は適合テストで再現しない。パイプ出力に ESC が無いことだけを確かめる

## Semantic Versioning 2.0.0

- 確認方法：WebFetch https://semver.org/
- 確認の状態：確認済み
- 公式の推奨：
  - "MAJOR version when you make incompatible API changes"、"MINOR version when you add functionality in a backward compatible manner"、"PATCH version when you make backward compatible bug fixes"
  - "Software using Semantic Versioning MUST declare a public API."、"Version 1.0.0 defines the public API."
  - 0.y.z は "Anything MAY change at any time."
- 採用するもの：PROC-06（差分の種類から次の版を機械で決める）、DEP-02（公開面を仕様で宣言する）
- 採用しないもの：0.y.z とプレリリース（`-rc.1`）。設計は 1.0.0 から始め、版は数字3つだけにする（PyPI がプレリリースの書式を受け付けないため。下の「配布」節）
- ツールにできないこと：意味の変更（同じ名前で振る舞いを変える）は字面では判定できない。レビュー用スキルで確かめる

## 終了コードの慣習（bash、sysexits）

- 確認方法：WebFetch https://www.gnu.org/software/bash/manual/html_node/Exit-Status.html（Bash 5.3）、https://man.freebsd.org/cgi/man.cgi?query=sysexits&sektion=3（FreeBSD 15.1）
- 確認の状態：確認済み
- 公式の推奨：
  - bash の builtin は "an exit status of 2 to indicate incorrect usage"。126、127、128+N はシェルが使う
  - sysexits（EX_USAGE=64 など）は "This interface has been deprecated and is retained only for compatibility. Its use is discouraged."
  - 標準ライブラリの解析器も、引数の誤りで2を返す（Go の ExitOnError、Python argparse。下の実測）
- 採用するもの：ERR-01（0 成功、1 予期しない失敗、2 使い方の誤り、3 対象が無い、4 衝突。126 以上と 64〜78 を使わない）
- 採用しないもの：sysexits の値
- ツールにできないこと：なし（適合テストで確かめる）

## 引数解析器の実測（Go flag go1.27.3、Python argparse 3.14.8、Node.js util.parseArgs v24.22.0、Rust std::env::args 1.99.1）

- 確認方法：
  - 版：https://go.dev/dl/?mode=json（go1.27.3）、https://www.python.org/api/v2/downloads/release/?is_published=true&pre_release=false と https://endoflife.date/api/python.json（3.15.0 が最新、3.14 系は 3.14.8、3.9 は 2025-10-31 に EOL）、https://nodejs.org/dist/index.json（LTS は v24.22.0、Current は v26.12.0）、https://static.rust-lang.org/dist/channel-rust-stable.toml（1.99.1）
  - 挙動：手元の Go 1.23.12、Python 3.9.6 と 3.14.5、Node v24.15.0 で、16種類の入力を同じ定義のオプションに与えて実測した。最新版との差は、各リリースノート（Go 1.24〜1.27 に flag の変更なし、Node の parseArgs の最終変更は v22.4.0）と Python 3.15 の argparse の変更点で確かめた。Rust は手元に無いため、https://doc.rust-lang.org/std/env/fn.args.html と The Rust Book 12.1 で確かめた
- 確認の状態：確認済み
- 公式の推奨（実測の結果）：
  | 入力 | Go flag | Python argparse | Node parseArgs |
  |---|---|---|---|
  | `--name value`、`--name=value` | 受け付ける | 受け付ける | 受け付ける |
  | `-name value`（1つのダッシュの長い名前） | name=value | **エラーにならず `-n` に `ame`** | **エラーにならず `-n` に `ame`** |
  | `-ab`（束ね） | エラー | 受け付ける | 受け付ける |
  | `--force=true`、`--no-force` | 前者は受け付ける | エラー | エラー |
  | `pos --force`（位置引数の後ろのオプション） | **エラーにならず位置引数になる** | 受け付ける（可変長の位置引数の間はエラー。`parse_intermixed_args` なら受け付ける） | 受け付ける |
  | `-- --force` | 位置引数 | 位置引数 | 位置引数 |
  | `--al`（前方一致） | エラー | **既定で受け付ける**（`allow_abbrev=False` でエラー） | エラー |
  | `--offset -1` | -1 | -1 | **エラー**（`--offset=-1` なら受け付ける） |
  | `-h`、`--help` | usage を **stderr** に出す | stdout に出して0 | 自動のヘルプは無い |
  | 未知のオプション | エラー（ExitOnError なら2） | stderr に出して2 | **throw**（捕まえないと1） |
  - Python 3.14 の argparse は `color=True` が既定で、TTY のときだけ色を付ける。3.15 は `suggest_on_error` の既定が True に変わった
  - Rust の標準ライブラリに引数解析器は無い。`std::env::args` は不正な Unicode で panic するため、`args_os` を使う
- 採用するもの：DEP-03（全解析器で同じ結果になる共通部分だけを仕様の書式にする）、DEP-04（実装の引数解析は標準ライブラリだけ）、OPS-05（ヘルプは仕様から生成した文面を実装が stdout に出す）、ERR-02（解析器のエラーを捕まえて1行で出す）。実装者が手で補う内容は、実装用スキルの `references/stdlib-mapping.md` に言語ごとに書く
- 採用しないもの：1つのダッシュの長い名前、束ね、`--no-`、`--flag=true`、前方一致、`--opt -1`（DEP-03）
- ツールにできないこと：実装の引数解析が仕様どおりかは、`tools/clispec conform`（適合テスト）が実行して確かめる

## 配布（Go、Python、Node.js、Rust、Homebrew）

- 確認方法：WebFetch https://pkg.go.dev/cmd/go 、https://go.dev/ref/mod 、https://go.dev/doc/modules/layout 、https://packaging.python.org/en/latest/specifications/pyproject-toml/ 、https://packaging.python.org/en/latest/specifications/name-normalization/ 、https://packaging.python.org/en/latest/specifications/version-specifiers/ 、https://docs.npmjs.com/cli/v11/configuring-npm/package-json 、https://nodejs.org/api/esm.html 、https://doc.rust-lang.org/cargo/reference/cargo-targets.html 、https://raw.githubusercontent.com/rust-lang/crates.io/main/crates/crates_io_validation/src/lib.rs 、https://docs.brew.sh/Formula-Cookbook
- 確認の状態：確認済み
- 公式の推奨：
  - 実行ファイル名：Go はインポートパスの最後の要素（`/vN` を除く）、Python は `[project.scripts]` のキー、npm は `bin` のキー（スコープは外れる）、Cargo はパッケージ名か `[[bin]] name`、Homebrew は小文字のファイル名
  - 名前の制約：crates.io は英字で始まり英数字・`-`・`_`、64文字以内。PyPI は `-`・`_`・`.` を同一視し大文字小文字を区別しない。npm は新しい名前に大文字を使えない。Go の要素は Windows の予約名を使えない
  - 版：Go は `v` 付きの SemVer（`runtime/debug.ReadBuildInfo` か `-ldflags -X`）、Python は `importlib.metadata.version`、Node は `import ... with { type: 'json' }`（v22.12.0 で安定）、Rust は `env!("CARGO_PKG_VERSION")`。PyPI の公開版は SemVer のプレリリース（`-rc.1`）を受け付けない
  - npm・PyPI・crates.io は、一度公開した版を再利用できない
- 採用するもの：OPS-06（CLI 名は `^[a-z][a-z0-9]*(-[a-z0-9]+)*$`、2〜20文字、Windows の予約名と `v` と数字だけの名前を除く。版は数字3つ）、OPS-05（`--version` は `<name> <version>` の1行で、先頭に `v` を付けない）、PROC-06（リリース済みの版を変えない）
- 採用しないもの：仕様にレジストリごとのパッケージ名を書くこと。パッケージ名は CLI 名と同じにする前提で、言語ごとの書き方を `references/stdlib-mapping.md` に書く
- ツールにできないこと：レジストリで名前が空いているかは確かめない（ネットワークに触れないため）。実装用スキルの報告で、利用者に確かめるよう書く

## Python 3.14.8（検査ツールの実行環境）

- 確認方法：https://www.python.org/api/v2/downloads/release/?is_published=true&pre_release=false → 3.15.0（2026-10-09）が最新、3.14 系の最新は 3.14.8。https://endoflife.date/api/python.json → 3.9 は 2025-10-31、3.10 は 2026-10-01 に EOL。手元は `uv run --no-project python -c 'import sys; print(sys.version)'` → 3.14.5
- 確認の状態：確認済み
- 公式の推奨：サポート中の版を使う
- 採用するもの：TOOL-04（`.python-version` に `3.14` を書き、uv で起動する。ADR 0003）
- 採用しないもの：3.15。公開から90日未満の新しい版のため、1つ前の 3.14 系にする。macOS 付属の `python3`（3.9.6）は EOL のため検査ツールには使わない（`.foundation/bin/` の基盤スクリプトは python3 で動く）
- ツールにできないこと：なし

## uv 0.13.3

- 確認方法：`curl -s https://pypi.org/pypi/uv/json` の `info.version` → 0.13.3。手元は `uv --version` → 0.11.14。`.python-version` を置いたディレクトリで `uv run --no-project python` が 3.14 を選ぶことを実測した
- 確認の状態：確認済み
- 公式の推奨：`.python-version` で Python の版を固定する（https://docs.astral.sh/uv/concepts/python-versions/）
- 採用するもの：TOOL-04（検査ツールを `uv run --no-project` で起動する。パッケージは何も入れない）
- 採用しないもの：`pyproject.toml` と lockfile。検査ツールは標準ライブラリだけで書き、依存が無いため
- ツールにできないこと：なし

## GNU Make 3.81

- 確認方法：`make --version` → GNU Make 3.81（macOS 付属）
- 確認の状態：確認済み
- 公式の推奨：なし（タスクの入口として使うだけ）
- 採用するもの：TOOL-04（`Makefile` を唯一の入口にする）
- 採用しないもの：3.81 に無い機能（`.ONESHELL` など）
- ツールにできないこと：なし

## 抑止記法（guard）

- 確認方法：この基盤で検査の対象になるのは `cli.json`（JSON）と、`tools/` の Python である。JSON にはコメントの書式が無く、`tools/clispec check` は未知のキーをエラーにするため、仕様の中に検査を黙らせる書き方は存在しない。Python は標準ライブラリの unittest で検査し、抑止の書き方は `unittest.skip`・`skipTest`・`expectedFailure`（https://docs.python.org/3/library/unittest.html#skipping-tests-and-expected-failures）
- 確認の状態：確認済み
- 公式の推奨：なし
- 採用するもの：TOOL-03（manifest の `guard.suppressions` に unittest の skip と、`# noqa`・`# type: ignore` を入れる。仕様の未知のキー（`$comment`、`x-` など）は `tools/clispec check` がエラーにする）
- 採用しないもの：なし
- ツールにできないこと：なし
