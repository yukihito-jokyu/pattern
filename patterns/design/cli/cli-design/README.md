# CLIの外部仕様を設計する基盤

コマンド、引数、オプション、出力、終了コード、環境変数を`specs/<name>/cli.json`で設計し、リファレンス`cli.md`の生成と実装の適合テストを行います。見本はメモとタグを管理する`notes`と、ファイルの単語を集計する`count-words`です。見本の実装はPythonの標準ライブラリで書かれています。CLIの実装そのものを生成するツールではありません。

## 環境と導入

- 対象：macOS/Linux、GNU Make（確認した版は3.81）。WindowsでのZIP検証は対応対象外です。
- 検査：Python 3.14とuv。Pythonの系列は`.python-version`で指定します。検査ツールに外部Pythonパッケージは不要です。
- 全手順の自動検証：Python 3.14の`venv`・`pip`、ネットワーク接続が必要です。`.ci/verify.py`がuv 0.13.3を一時環境へ導入します。
- サイトのNode.js・Docusaurus、Go、Rustは、このZIPの見本を実行するためには不要です。

ZIPを展開し、`cli-design/`全体を新しい作業ディレクトリへコピーしてください。必要な隠しファイルとディレクトリも含めます。既存プロジェクトへ入れる場合は、AGENTS.md、CLAUDE.md、Makefile、`.claude/`、`.foundation/`が衝突しない独立したディレクトリに置きます。

以降は展開した`cli-design/`を作業場所とします。uvの導入方法は[公式手順](https://docs.astral.sh/uv/getting-started/installation/)を参照してください。導入済みのuvを手動で使う場合は次の順で実行し、準備が失敗したら停止します。

```bash
uv --version
make --version
uv python install 3.14
make check
```

`make check`は仕様、JSONの整形、生成リファレンス、見本実装の適合テスト、抑止記法、ルールと検査の対応を確認します。終了コード0、unittestの`OK`、`guard: 違反 0 件`、ルールの`エラー 0 件`が期待結果です。既存のルール文には「あいまいな列挙の可能性」という警告3件があります。警告とエラーは区別します。

## 見本を使う

保存データに触れず、まず単語集計を試せます。

```bash
printf 'alpha beta alpha\n' | uv run --no-project --quiet python tools/clispec/tests/fixtures/count_words_impl.py - --json
```

期待する出力は次の配列です（整形空白は省略）。

```json
[{"count":2,"word":"alpha"},{"count":1,"word":"beta"}]
```

`--min-length 5`を指定すると`beta`を除きます。`COUNT_WORDS_MIN_LENGTH=5`でも既定値を変えられますが、同時にオプションを指定した場合はオプションが優先します。`--output result.json --json`でファイルへ書き出せます。入力の`-`は標準入力、出力先の`-`は標準出力です。

見本実装の外部仕様をまとめて確認するには、同じ作業場所で実行します。

```bash
make conform SPEC=specs/notes/cli.json CMD="uv run --no-project --quiet python tools/clispec/tests/fixtures/notes_impl.py"
make conform SPEC=specs/count-words/cli.json CMD="uv run --no-project --quiet python tools/clispec/tests/fixtures/count_words_impl.py"
```

各コマンドが`conform: … 件成功、0 件失敗`で終了し、`FAIL`が無いことを確認します。適合テストはデータ用の環境変数を一時ディレクトリへ向けます。見本を直接使って保存するときは、`NOTES_DATA_DIR`を専用の空ディレクトリの絶対パスに指定してください。見本のファイル保存は業務アプリの永続化設計の代わりにはなりません。

## 新しいCLIを設計する

以下は新しい作業用コピーで実行します。`bookmarks`が既にある場合、`make new`は失敗するので別名を使ってください。

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

`specs/bookmarks/cli.json`に5操作、整数の`id`、時刻、URLの項目、`BOOKMARKS_DATA_DIR`が作られます。`bookmark create`の`--url`は必須です。`cli.md`に同じヘルプが生成され、最初の版は`1.0.0`になります。この手順が作るのは仕様とリファレンスであり、実行できる`bookmarks`プログラムは別途実装します。

利用先の操作・項目・絞り込み・既定値は、依頼に合わせて選びます。設計の正本は`cli.json`です。`cli.md`は手で編集せず`make fix`で生成し、`released/`は変更しません。1操作のCLIは`make new NAME=<name> SINGLE=1`から始めます。詳細は`docs/design/overview.md`、ルールは`docs/design/rules.md`、設計手順は`.claude/skills/cli-design/SKILL.md`を参照してください。

実装する際は`.claude/skills/cli-design/references/stdlib-mapping.md`を読み、生成したヘルプを含む仕様に従います。Go・Python・Node.js・Rustへの対応表がありますが、同梱して適合テストで確認する実装はPythonの見本2種類です。自分の実装は基盤の外に置き、次の`CMD`を実際の起動コマンドの絶対パスへ置き換えて検証します。

```bash
make conform SPEC=specs/bookmarks/cli.json CMD="/absolute/path/to/bookmarks"
```

版を確定する`make release NAME=<name>`は公開が必要なときだけ行います。公開面を削除・変更する場合は承認とADRが必要です。

## エージェントと使う

Claude Codeは展開先の`cli-design/`で起動します。`CLAUDE.md`は`AGENTS.md`を読み込み、`.claude/skills/`に設計・実装用とレビュー用のスキルがあります。`.claude/settings.json`のhooksが、対応する編集ツールによる保護ファイルの編集を制御し、仕様編集後に整形・版計算・リファレンス生成・検査を行います。

親ディレクトリで起動した場合や、別のエージェント・シェル経由の編集では同じhooksが動くとは限りません。スキルを直接読み、仕様変更後に`make after-edit FILE=specs/<name>/cli.json`、完了前に`make check`を実行します。hooksはすべての書き込みを防ぐ仕組みではなく、保護ファイルとリリース済み仕様の変更はレビューでも確認します。

## ZIP単体での自動検証

Python 3.14、GNU Make、ネットワークを用意し、展開先で実行します。Pythonの版は`python3 --version`で先に確認します。

```bash
python3 .ci/verify.py
```

一時仮想環境へuv 0.13.3を導入した後、全検査、見本2種類の適合テスト、違反4件の検出、新規`bookmarks`仕様の生成を順に確認します。生成の確認は別の一時コピーで行い、展開先の見本を変更しません。最後の`ZIP検証: 全検査・見本2種類・違反4件・新規仕様生成に成功`と終了コード0が期待結果です。準備や検査に失敗した場合は後続を停止し、非0で終了します。

`ci.json`の`command`はこのコマンド、`pythonVersion`は`3.14`です。共通CIはLinux・Python 3.14を準備して同じ検証をZIP展開先で実行します。ネットワークはuvの導入に使い、作った仮想環境とuvのキャッシュは終了時に削除します。

検査ツール自体を変更する保守では、違反例全件も一時コピーで確認します。

```bash
uv run --no-project --quiet python .foundation/bin/violation_probe.py --root .
uv run --no-project --quiet python .foundation/bin/rules_check.py --root . --final --no-write
```

全件のprobeは`67 件中 成功 67 件`を期待し、その実行時の結果を`.foundation/probe-results.json`へ記録します。通常のZIP検証は代表4件のみで、この結果ファイルを上書きしません。収束評価の資料は元実装の開発記録です。ZIP検証を行っても、独立したエージェントによる収束評価を再実施したことにはなりません。
