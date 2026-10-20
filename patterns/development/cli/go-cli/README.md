# GoのCLI実装パターン

標準ライブラリの`flag`を使い、`go-cli <noun> <verb>`形式のCLIを作るための基盤です。タスクの追加・一覧・完了を見本に、コマンド、業務処理、JSON保存を分離しています。新しい動詞や名詞を追加するときのルールと、その構造を確認する検査も含みます。

`main.go`が入口、`internal/app/`が組み立て、`internal/cli/`が入力解析と出力、`internal/command/taskcmd/`がサブコマンド、`internal/domain/task/`が業務処理、`internal/adapter/taskstore/`が保存です。詳しい構造は[設計概要](docs/design/overview.md)、公開コマンドは[コマンド一覧](docs/cli.md)で確認できます。

## 環境と導入

macOSまたはLinuxで、Go 1.21以降、GNU Make 3.81以降、Python 3.12以降を用意します。CLIのビルド・実行にはGoだけを使い、全検査にはMakeとPythonも使います。Windowsは対応対象に含めません。

ZIPを展開した`go-cli/`を新しいプロジェクトのルートとして使います。既存プロジェクトへのファイル単位の上書きは避けてください。以下はすべて、このREADMEがあるディレクトリで実行します。

```sh
go version
make --version
python3 --version
go mod download
go mod download -modfile=golangci-lint.mod
make check
```

準備で失敗したら、その原因を解消してから次へ進みます。`go.mod`の`toolchain go1.27.2`を使えるよう、Goの自動ツールチェーン選択を有効にします（通常は`GOTOOLCHAIN=auto`）。初回はGo 1.27.2と検査用モジュールの取得にネットワークが必要です。Goの選択設定・既存のPATHによっては自動取得せず既存の新しいGoを使うため、実際の版は展開先で`go version`を確認してください。

CLI自体には外部モジュールがありません。golangci-lint v2.15.0とその依存は`golangci-lint.mod`・`golangci-lint.sum`に分けて固定しています。Node.jsや掲載サイトのファイルは不要です。

## 使用方法

まずビルドし、専用の一時データディレクトリを指定します。複数のコマンドで同じ`GOCLI_DATA_DIR`を使うことが、追加したデータを一覧・完了で再利用する条件です。

```sh
go build -o go-cli .
export GOCLI_DATA_DIR="$(mktemp -d)"
./go-cli task add "Buy milk"
./go-cli task list
./go-cli task complete 1
./go-cli task list --json
./go-cli task list --all --json
```

追加は`Added task 1: Buy milk`、完了は`Completed task 1: Buy milk`を出力します。最初の一覧は`ID`・`STATUS`・`TITLE`の表です。完了後の一覧は既定では空になり、JSONでは`{"tasks": []}`を返します。`--all`を付けると完了済みの1件も含まれ、`id`・`title`・`done`・`created_at`が表示されます。時刻はUTC・秒精度です。

```sh
./go-cli --help
./go-cli task add --help
./go-cli task add "Read book" --json
./go-cli task add -- "--json"
./go-cli task complete unknown
echo "$?"
```

`--json`は動詞より後で位置引数の前後どちらにも書けます。`--`以後はフラグとして解釈しないため、最後の追加は`--json`というタイトルを保存します。不正なIDを渡す最後の操作は標準エラーに理由を出し、終了コード2を返します。終了コードは成功0、予期しない失敗1、入力誤り2、対象なし3です。実際の終了コードを確認するときは、`go run`を経由せずビルド済みバイナリを使います。

`go install .`でインストールする場合は、`GOBIN`、未設定なら`$(go env GOPATH)/bin`に`go-cli`が入ります。利用するシェルのPATHへ追加してください。

## 保存先と制約

`internal/app/config.go`が次の優先順で保存ディレクトリを決め、その中の`tasks.json`に保存します。

| 環境変数 | 指定・省略時の動作 |
| --- | --- |
| `GOCLI_DATA_DIR` | 空でなければ、このパスをそのまま使う |
| `XDG_DATA_HOME` | 上記が空なら、このパスの`go-cli/`を使う |
| `HOME` | 上記2つが空なら、`$HOME/.local/share/go-cli/`を使う。すべて空なら終了コード1 |

手動確認では必ず`GOCLI_DATA_DIR`を一時ディレクトリに設定してください。既存の保存先を指定すると、そこで読み込んだデータを更新します。新規ディレクトリは0700、保存ファイルは0600で作ります。

タイトルは前後の空白を除いた1〜100文字（rune数）、IDは正の整数です。ファイル全体を読み書きするため、複数プロセスの同時更新には使えません。一時ファイルからの置き換えは書きかけの公開を避けますが、排他制御やディスク同期による電源断対策はありません。`version: 1`は保存しますが、読み込み時に未知の版を拒否する検証はありません。外部で編集したデータの検証や大容量データへの対応も含め、利用先で必要なら別途設計してください。

## 自分のCLIへ拡張する

まず[AGENTS.md](AGENTS.md)と[実装手順](.claude/skills/impl/SKILL.md)を読み、[変更パターン別の手順](.claude/skills/impl/references/patterns.md)に沿って`task`の見本を拡張します。規則の全文は[ルール集](docs/design/rules.md)です。

| 変更 | 主な変更箇所 |
| --- | --- |
| 動詞を追加 | `domain/task/service.go`、`command/taskcmd/<verb>.go`とテスト、`taskcmd.go`の登録 |
| フラグを追加 | 対象動詞のOptionsとFlags、必要ならdomainのFilterまたはService、テスト |
| 項目を追加 | domainのTask、adapterのrecordと変換、commandのtaskViewと変換、入出力する動詞とテスト |
| 名詞を追加 | domain・adapter・commandの3パッケージ、`app.go`の組み立て・登録、ヘルプのテスト |

作る順はdomain → Service → adapter → view → 動詞 → テスト → 登録です。コマンドやフラグを変えたら`make generate`で`docs/cli.md`を生成し、最後に`make check`を実行します。詳細な対象ファイルとテストの規約は上記の変更パターン別の手順で確認してください。

モジュール名は`example.com/go-cli`、コマンド名は`go-cli`です。モジュール名を変更する場合は`go.mod`、全import、`.golangci.yml`のモジュール名、`tools/archcheck`の対応をそろえる必要があります。保護されたルール・検査の変更に当たるため、[既定値のADR](docs/design/adr/0005-defaults-not-in-the-request.md)とAGENTS.mdの変更手順に従ってください。単純な文字列置換で検査を回避しません。

Claude Codeでこの展開先を直接開くと、`.claude/settings.json`の編集hooksを利用できます。他のエージェントではAGENTS.mdとスキルを直接読み、同じ検査を実行してください。hooksの自動実行は全環境共通の機能ではありません。

## 検証

通常の開発では`make check`を実行します。依存定義の鮮度、lint、build、vet、構造検査、コマンド文書の鮮度、Goテスト、抑止コメントの禁止、ルールとの対応を順に検査し、どれか失敗したら後続を止めます。

ZIPと同じ一式が利用できることまで確認するコマンドは次です。必要環境は前述のmacOS/Linux・Go・Make・Pythonです。

```sh
python3 scripts/verify-ci.py
```

このコマンドは`ci.json`の実行入口です。全検査後、一時ディレクトリにビルドしたCLIを別プロセスとして動かし、文章・JSON・永続化・入力制約・終了コード0/1/2/3・保存失敗時のデータ保持を確認します。保存失敗は子プロセスのファイルサイズ制限で再現し、呼び出し元の制限は変えません。続いて、一時コピーに依存方向違反、動詞の構成違反、抑止コメントを入れ、対応する検査が期待する理由で失敗することを確認します。

最後に`ZIP検証: 全検査・CLI操作・代表的な違反3件の検出に成功`が出て、終了コード0になるのが期待結果です。3件の検出は77件すべての再実行を意味しません。`.foundation/probe-results.json`と収束評価は元の基盤作成時の記録として同梱しています。今回の結果と区別してください。

全77件を再確認する場合は、作業用コピーで次を実行します。結果ファイルが再生成されるため、配布元ではなくコピーを使ってください。

```sh
python3 .foundation/bin/violation_probe.py --root .
python3 .foundation/bin/rules_check.py --root . --final --no-write
```

この配布物には利用先のGitHub Actionsやリリース自動化は含めません。`ci.json`は掲載元がZIPを検証するための設定で、利用先でも上記のPythonコマンドをCIから呼び出せます。Ubuntu上のPython 3.12・`go.mod`から選択するGoで検証する設定です。2026-10-20にmacOS 15.7.3（arm64）・Go 1.27.2・GNU Make 3.81・Python 3.14.2で生成ZIPを展開して実行し、全検査、CLI操作、代表的な違反3件の検出に成功しました。Linux・Python 3.12のCI環境での実行と、人間による最終レビューは未確認です。
