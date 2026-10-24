# skill-harness2-kit

利用先のClaude Codeスキル1つを、実行の軌跡から改善するスキルと補助CLIです。基準実行、INV/DOMの提案、候補の試行、合成、匿名選択、振り返りを進め、費用の承認と対象スキルへの採用は人が決めます。

`kit/.h2/`が補助CLIとひな形、`kit/claude/skills/skill-harness2/`が配布スキル、`install.py`が導入用です。`tests/`と`.foundation/`には単体検証・代表違反の検証に必要なファイルを収録しています。サイトの依存関係は不要です。

## 環境と導入

利用時はPython 3.9以上、Claude Code、`claude -p`を使える認証・契約が必要です。元キットの実CLI調査対象はClaude Code 2.1.308です。実行時のPythonパッケージ依存はなく、標準ライブラリだけを使います。macOS/Linuxを想定し、Windowsは未確認です。

ZIPを展開し、展開先の`skill-harness2-kit/`で次を実行します。導入先は既に存在する利用者のリポジトリのルートです。

```sh
python3 --version
claude --version
python3 install.py /path/to/your-repository
cd /path/to/your-repository
python3 .h2/h2.py status minutes
claude
# Claude Code内で実行する:
# /skill-harness2 minutes .claude/skills/minutes-format
```

導入先には`.h2/h2.py`・`.h2/.gitignore`・`.h2/h2_kit/`・`.h2/templates/`と`.claude/skills/skill-harness2/`が入ります。改善したいスキル（例の`minutes-format`）は利用者があらかじめ用意します。`status minutes`の初回表示は`段階: 準備`です。

既存の配布ファイルと内容が違う場合、installerはエラーで止まります。差分を確認して置き換えると決めた場合だけ、展開先に戻って`python3 install.py /path/to/your-repository --force`を使います。`--force`は上記の配布ディレクトリを削除して入れ直すため、そこへの手編集や余分なファイルも消えます。利用者の記録`.h2/targets/`は保持します。dry-runオプションはありません。

## 使用方法

利用先のリポジトリのルートでClaude Codeを起動し、`/skill-harness2 <対象名> <対象スキルのディレクトリ>`を呼びます。対象名は小文字・数字・`-`・`_`の64文字以内です。

スキルはプロファイル・タスク・費用の上限を人と決めます。`references/profile-guide.md`に沿って`.h2/targets/minutes/profile.json`、`references/task-guide.md`に沿って`tasks/<id>/task.md`と必要な材料を用意します。材料には正解を混ぜず、実際の仕事に近いタスクを2〜5件選びます。

補助CLIを直接使う場合も、人の承認と採用判断は同じです。以下はコマンドの順序であり、一括実行するスクリプトではありません。

```sh
python3 .h2/h2.py init minutes --skill .claude/skills/minutes-format
# profile.jsonとtasks/を人と作る
python3 .h2/h2.py check minutes
# 表示されたplan.mdを読み、費用を承認した後だけ実行
python3 .h2/h2.py approve minutes
python3 .h2/h2.py run minutes
python3 .h2/h2.py status minutes
python3 .h2/h2.py show minutes
# 人が採用すると決めた場合だけ、showが出したadoptコマンドをそのまま実行
```

`run`は`claude -p`を複数回呼び、実費が発生します。1モードにつき実行4k回、編集セッション3k回に、選択・振り返り等が加わります。費用上限は`check`が計算します。承認後の対象スキル・タスク・プロファイルを変更すると実行や採用が止まるため、変更後は`check`から見せ直します。中断した`run`は同じコマンドで再開できます。

結果は`.h2/targets/<対象名>/runs/`に残ります。`show`で差分と実行結果を読み、人が採用するまで元の対象スキルには書き込みません。事後検査を用意した場合は`judge`で確認できますが、その結果は改善の提案・合成・選択へ戻しません。

## 検証

ZIPを展開した`skill-harness2-kit/`で、Python 3.9以上（`venv`と`pip`を利用可能）、bash、make、インターネット接続を用意します。Linuxで`venv`が利用できない場合はOSのPython環境を準備してから始めます。

```sh
bash verify-ci.sh
```

このコマンドは一時ディレクトリへuv 0.13.4、検査用Python 3.12、ruff 0.17.2、mypy 1.20.2を準備します。ホストのツールを置き換えず、準備が失敗したら後続を実行しません。初回のツール取得にはネットワークが必要です。準備後のテストは`fake_claude.py`を子プロセスとして使い、本物のClaude CodeやAPIキーは不要です。

検査内容は元の`make check`（整形・lint・型・構造・単体テスト・抑止検出・ルール整合）、一時コピーへ入れる代表違反4件（STR-01-a、STATE-04-a、OPS-05-a、TOOL-03-a）、実際のinstallerによる内容照合・帰属資料の収録・初回statusです。既存installerテストは新規導入、競合時の拒否、強制再導入時の古い実装削除と`.h2/targets/`保持も確認します。

期待する結果はすべて終了コード0で、最後に`ZIP単体検証: 成功`が出ることです。`ci.json`も同じ`bash verify-ci.sh`とPython 3.12を指定します。元の`make check`だけを使う場合はmakeとuvを準備して実行します。検査中に生成するキャッシュは配布物に含めません。

この検証は実Claudeの閉じ込め挙動・実対話・改善効果の実測を含みません。元の設計資料の検証記録は移行前の観測として収録しており、今回の実モデル動作確認を意味しません。

## 出典と帰属

方法の参照元は[google-research/harness2の固定版](https://github.com/google-research/harness2/tree/1cfe254e8d25b15f37048c3730134686abe60335)です。上流のひな形を日本語化し、Claude Codeのスキルに合わせています。帰属・変更表示・Apache-2.0全文は[third-party-notices.md](kit/claude/skills/skill-harness2/references/third-party-notices.md)に収録し、導入先にもコピーします。元キット独自部分について新しい包括ライセンスを指定したものではありません。
