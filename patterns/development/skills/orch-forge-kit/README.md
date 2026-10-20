# オーケストレーションスキルを作り、評価して改善する

Claude Codeで、実装・確認などをサブエージェントに任せる開発用スキルを作る道具一式です。利用者と目的・評価指標を決める`forge-goals`、初版を作る`forge-build`、評価と改善を進める`forge-run`を配布します。`kit/`に配布物、`install.py`に導入処理、`tests/`に自動テスト、`docs/design/`に構造と規約の説明があります。

## 環境と導入

macOSまたはLinuxで、Python 3.9以上、Git、Claude Codeを使います。元実装の対象版はClaude Code 2.1.296です。Pythonの実行時依存は標準ライブラリだけですが、実際のスキル実行には認証済みのClaude Codeとモデルを利用できる環境が必要です。Windowsは動作確認の対象にしていません。

ZIPを展開し、展開した`orch-forge-kit/`で実行します。

```sh
python3 --version
git --version
claude --version
python3 install.py --dest /path/to/your-repository
```

`--dest`は実在する導入先リポジトリのルートです。`kit/.forge/`を導入先の`.forge/`へ、`kit/claude/`を`.claude/`へコピーし、`.gitignore`に`.forge/work/`を追加します。`.claude/settings.json`の`permissions.allow`には`Bash(python3 .forge/forge.py *)`を追加します。既存の許可・hooksを保ち、同じ許可は重複追加しません。JSONの形を読めない場合は変更せず、手動追加の案内を出します。

既存の配布対象ファイルに内容の違いがあれば、コピー前に停止します。上書きを選ぶときだけ`--force`を指定してください。導入先でClaude Codeを開き、リポジトリへの信頼を確認します。スキルを確実に読み込むため、導入後に新しいセッションを開始してください。

## 使用方法

導入先リポジトリを作業場所にして、Claude Codeの会話で次を順に呼びます。ここでは生成するスキル名を`dev-orch`とします。

```text
/forge-goals dev-orch
/forge-build dev-orch
/forge-run dev-orch
```

1. `forge-goals`で目的、成功の条件、指標と閾値、評価課題、実行条件、予算を人と決めます。`.forge/targets/dev-orch/charter.json`と人が読む`charter.md`を確認して承認します。
2. `forge-build`で設計と下書きを確認します。承認すると`.claude/skills/dev-orch/`と`.claude/agents/dev-orch-<役>.md`へ導入します。既存スキルを改善する場合はこの段階を省きます。
3. `forge-run`で現在のスキルを測定し、改善候補との差を比較します。候補の採否は人が決めます。最後に改善に使わなかった課題も測定し、`.forge/targets/dev-orch/report.md`へ報告します。

生成されたスキルは、導入先のClaude Codeで`/dev-orch <開発の依頼>`として使います。`forge-*`はこのスキルを作り改善するための道具です。

進み具合は、導入先のシェルから確認できます。

```sh
python3 .forge/forge.py targets
python3 .forge/forge.py metric-catalog
python3 .forge/forge.py status --target dev-orch
```

`status`が次のコマンド、サブエージェントの仕事、人の判断待ちを表示します。途中で止まっても、同じ`/forge-build dev-orch`または`/forge-run dev-orch`から再開できます。承認後にcharterを変えた場合は`forge-goals`で承認し直します。

評価はOSの一時ディレクトリに作るコピーで`claude -p`を起動し、費用がかかります。`charter-check`が示す起動回数と費用上限の見積もりを確認してください。既定では1回3ドル・1800秒、同時実行3、課題あたり3回、改善は最大3ラウンドです。これらは採用前に人と決める値です。設計・採点・分析のセッションの費用は、評価の実行役の費用上限とは別です。

検査コマンド・保護ファイル・許可する道具は導入先に合わせます。charterの全項目と例は`kit/claude/skills/forge-goals/references/charter-schema.md`、指標の計算は同じ場所の`metric-catalog.md`で確認できます。

## 検証

ZIPの自動検証には、Python、Gitに加えMake、Pythonの`venv`・`pip`、パッケージ配布元へのネットワーク接続が必要です。Claude Codeや認証は使いません。展開先で実行します。

```sh
bash scripts/verify-ci.sh
```

このコマンドはツール導入用の一時仮想環境を作り、`uv==0.11.14`を取得します。`make check`が固定版のRuff 0.17.1・mypy 1.20.2を呼び、整形、lint、型、構造、生成文書、124件のテスト、抑止コメント、規約との整合を確認します。準備や検査に失敗したら、後続へ進みません。

テストは一時リポジトリ・本物のGit・記録済みstream-jsonを使い、導入、競合の停止、承認、設計・構築、評価、比較、採否、最終報告までを検証します。検査自体の`__pycache__`が実装差分へ混ざらないことも確認します。検査コマンドへ渡す環境変数`CI`は、未設定なら`1`、設定済みならその値を保持します。テストでは未設定と`true`の両方を用意し、終了時に元の環境へ戻します。

続いて`violation_probe.py --only STR-04-a,STR-05-a,TOOL-03-a`が別の一時コピーに違反を入れ、生成文書の不一致、サブエージェントへのAgent追加、抑止コメントを検出します。非0の終了に加えて期待する診断との一致を確かめ、全検査への組み込みも確認します。期待する末尾は`ZIP検証: 全検査・124件のテスト・代表的な違反3件の検出に成功`、終了コードは0です。ツール用の一時環境は終了時に削除します。

掲載元の共通CIは`ci.json`の`pythonVersion: 3.12`でPythonを準備し、同じシェルコマンドをZIP展開先で実行します。Node.jsや掲載元リポジトリのファイルは、ZIPの検証には不要です。

既に`uv`を準備してある開発環境では、次も使えます。

```sh
make check
PYTHONPATH=kit/.forge python3 -B -m unittest tests.test_collect
```

2026-10-21にmacOS・Python 3.14.2で生成ZIPの検証を実施しました。結果の詳細は掲載文書、Linux・Python 3.12での実行結果は[PRのCI結果](https://github.com/yukihito-jokyu/pattern/pull/16/checks)を参照してください。実モデルを使った設計・採点・改善の品質、人間による最終レビューは未確認です。同梱する過去の収束評価・違反検出結果は元実装の記録で、今回再実行した範囲とは分けて扱います。

この基盤を変更する場合は、展開先の`AGENTS.md`と`.claude/skills/impl/SKILL.md`を読みます。Claude Codeを展開先で起動すると`.claude/settings.json`のhooksが編集後の整形とlintを呼びます。他のエージェントでは同じ手順を明示的に実行してください。
