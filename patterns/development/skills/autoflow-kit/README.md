# autoflow-kit

依頼から計画・実装・検証・リスク判定・AIレビューを進め、人が決められた関所で判断するClaude Code用のパターンです。補助CLIが段の順序と証拠を確認し、最後の承認後に作業ブランチへコミットします。

`kit/.autoflow/`にPython製CLIとプロンプト、`kit/claude/skills/`に3つのスキル、`kit/claude/agents/`に5つの役があります。`install.py`が導入先へ配置します。`tests/`、`Makefile`、`.foundation/`、`docs/design/`は基盤自体の検証・保守用です。サイト本体の依存関係は使いません。

## 環境と導入

利用にはPython 3.9以上、Git、認証済みのClaude Code、導入先の検査に必要な環境を用意します。元実装の対象はClaude Code 2.1.296です。補助CLIはPythonの標準ライブラリだけで動きます。macOS・Linux向けで、Windowsは未確認です。

ZIPを展開した`autoflow-kit/`で実行します。導入先には、初期コミットのある実在のGitリポジトリのルートを指定してください。

```sh
python3 install.py --dest /path/to/your-repository
```

`.autoflow/`にCLI、`.claude/skills/`と`.claude/agents/`にスキルと役をコピーし、`.gitignore`に実行記録・ローカル設定・Pythonのキャッシュの除外を足します。異なる内容の既存ファイルがあれば、コピー前に停止します。差分を確認し、置き換えてよい場合だけ`--force`を付けます。プロファイル・承認・実行記録はインストーラーのコピー対象外です。

導入先のルートでClaude Codeを開き、最初に次を呼びます。

```text
/autoflow-setup
```

Makefileやpackage.jsonから検査の案を作ります。`.autoflow/profile.json`の検査コマンド、テストのパス、常に人が読むパス、リスク分類、レビュー指示、試行上限を導入先に合わせて確認します。全項目と既定値は`kit/claude/skills/autoflow-setup/references/profile-schema.md`にあります。H0で内容を承認し、検査を確認なしで実行してよいかも決めます。許可した場合だけ`.claude/settings.local.json`へ検査コマンドの許可を足します。

準備後は、導入したファイル・プロファイル・承認記録・`.gitignore`を人がコミットします。`start`は未コミット・未追跡の変更があると停止します。導入先でGitの名前・メールと、必要なら署名設定も用意してください。

## 使用方法

導入先のClaude Codeで、文章または課題番号を渡します。

```text
/autoflow calcに掛け算の関数multiplyを追加してください
/autoflow github 90
/autoflow resume 20261022-143000
```

GitHubは認証済み`gh`、GitLabは`glab`、Backlog・Redmineは対応するMCP接続が必要です。本文・コメントを取得できなければ停止します。取得元の詳細は`kit/claude/skills/autoflow/references/sources.md`にあります。

CLIの`status`が示す次のコマンド・役をスキルが実行します。H1は未決の重要事項・新規依存・広い計画・人が読むパス、H2は行き詰まりや失敗の上限に当たった場合だけ、H3は毎回判断します。回答がなければ止まり、同じ実行IDで再開できます。H3で承認した変更の版が保たれているときだけコミットします。pushはしません。

```sh
# 導入先ルートで現在の状態を確認する場合
python3 .autoflow/autoflow.py status
```

報告書は`.autoflow/runs/<実行ID>/handoff-<番号>.md`です。検査の証拠、残った指摘、人が読む差分、検査が見ていないことを確認します。検査の実行は`CI=1`で行い、差分の版を得る際は`git add -A`でindexも更新します。ファイルを変更する検査や除外していない生成物は、検査後の版の変化として失敗になります。

運用を見直すときは`/autoflow-learn`を呼びます。人の介入・差し戻し・インシデントから改善案を作り、人が選んだ案だけを反映します。プロファイルを変えた場合はH0をやり直します。

## 検証

ZIPの展開先ルートで、次の1コマンドを実行します。Bash、Make、Pythonのvenv・pip、Git、ネットワーク接続が必要です。Claude Codeの認証や実モデルの利用は不要です。

```sh
bash scripts/verify-ci.sh
```

一時仮想環境にuv 0.11.14を導入し、`make check`でRuff 0.17.1による整形・lint、mypy 1.20.2による型、構造、生成文書の一致、165件のテスト、抑止コメント、規約との対応を確認します。準備や正常例の検査に失敗したら、後続には進みません。

続いて一時コピーに代表的な違反3件を入れ、生成文書の改変、報告処理による承認の代行、抑止コメントをそれぞれ検出できるか確認します。期待結果は終了コード0と`ZIP検証: 全検査・代表的な違反3件の検出に成功`です。共有CIは`ci.json`でPython 3.12を準備して同じコマンドを実行します。uvのキャッシュ・ツールは一時領域に作り、終了時に片付けます。既に`UV_CACHE_DIR`などが指定されていればその値を使います。

テストは一時Gitリポジトリでファイル・ブランチ・コミットを実際に操作し、AIの出力はテストデータで再現します。承認前の停止、承認後の変更の拒否、検査・レビュー・再開・報告の流れを確かめます。実エージェントの判断品質、外部課題サービスとの接続、Git署名を含む各導入先の条件は別途確認が必要です。同梱の違反検出・収束評価の過去記録は今回の再実行結果とは区別します。

基盤自体を変更するときは、同梱の`AGENTS.md`、`.claude/skills/impl/SKILL.md`、`docs/design/rules.md`を読んでください。基盤のルートでClaude Codeを起動すると`.claude/settings.json`の編集用hooksが働きます。これらの開発用hooksは`install.py`で利用先へ配布する設定には含めません。
