# skill-tune-kit

既存のClaude Codeスキルを、評価データで測りながら改善する道具一式です。学習役がスキルの文書を直し、検証用の成績で候補を採るか決め、最後にテスト用で元の版と比較します。モデルの重みを更新する学習ではありません。

`kit/.tune/`にPython CLIとプロンプト、`kit/claude/`に配布する`skill-tune`スキルと4つのエージェントがあります。`install.py`がこの2つを利用先へコピーします。`docs/design/`は設計と既存の判断記録、`tests/`は一時fixtureで動作を確かめるテストです。

## 環境と導入

利用にはPython 3.9以上、Git、Claude Codeが必要です。CLIのPython依存は標準ライブラリだけです。配布物はClaude Code向けで、Codexへの導入用ではありません。Claude Codeの配置・frontmatterの仕様は[skills](https://code.claude.com/docs/en/skills)と[subagents](https://code.claude.com/docs/en/sub-agents)で確認できます。移行元にはClaude Code 2.1.296での実行記録がありますが、今回この版で実モデルを再実行した結果ではありません。

ZIPを展開し、`README.md`と`install.py`がある`skill-tune-kit/`を作業場所にします。利用先のディレクトリは先に用意してください。

```bash
python3 install.py /path/to/your-repository
```

`kit/.tune/`を利用先の`.tune/`へ、`kit/claude/`を`.claude/`へコピーし、既存の`.gitignore`を保ったまま`.tune/work/`を追記します。計画・結果のある`.tune/targets/`は無視対象に追加しません。

同名のコピー先が1つでも存在すると、コピーと`.gitignore`変更を行わず終了コード1で停止します。既存ファイルを上書きする更新では、差分を確認してから`--force`を付けます。`--force`は該当ファイルの上書きを許可し、無関係なファイルを消すものではありません。

## 使用方法

導入後は**利用先リポジトリのルート**でClaude Codeを起動し、次のように呼びます。対象スキルは既に存在し、`SKILL.md`を持つディレクトリを指定します。

```text
/skill-tune date-format .claude/skills/date-format
```

最初の`date-format`は記録を識別するtarget IDです。小文字の英数字で始まる64文字以内の英数字・ハイフンを使います。スキルと人でゴール、正解データを使う`reference`か評価項目を使う`criteria`か、ケース、検査、予算を決めます。CLIはこれを`.tune/targets/date-format/plan.json`と`dataset/cases.json`へ記録します。ケースは3件以上が必要で、少数による成績の揺れを減らすため10件以上を勧めています。

補助CLIの進み具合は、同じルートから確認できます。

```bash
python3 .tune/tune.py status --target date-format
```

`status`が示す次のコマンドやjobを、配布スキルが順に実行します。計画は`plan.md`を読んで人が承認し、データの修正提案は人が選択します。最後は`report.md`と候補の差分を読み、対象スキルへの適用か見送りを人が選びます。承認後に計画やデータを変えると評価は停止し、再検査・再承認が必要です。適用時に対象スキルが承認時から変わっていれば、上書きせず手動取り込みを案内します。

形式とケースの作り方は、導入先の`.claude/skills/skill-tune/references/plan-schema.md`、`dataset-guide.md`、`criteria-guide.md`、`check-kinds.md`にあります。実行役はsandboxでコマンドを実行でき、`command`検査もシェルを動かすので、利用先で許可できるケースと検査を計画に含めてください。sandboxは作業用ディレクトリの分離で、OSによる隔離ではありません。

## 検証

macOSまたはLinuxのBash、`make`、Python 3.9以上（`venv`と`pip`を含む）、Git、Pythonパッケージを取得できるネットワークが必要です。CIは`ci.json`でPython 3.12と`bash verify-ci.sh`を指定しています。Claude CodeやAPIキーはこの自動検証には不要です。

展開した`skill-tune-kit/`で実行します。

```bash
bash verify-ci.sh
```

スクリプトは一時venvに`uv==0.11.14`を導入し、`make check`から`uvx ruff@0.17.1`と`uvx mypy@1.20.2`を実行します。依存導入が失敗したら後続を止めます。uvと検査ツールは一時環境で使い、配布CLIの依存へ追加しません。Python依存がないためプロジェクトのlockfileは使わず、検査用ツールの版はコマンドで固定しています。

確認内容と期待結果は次のとおりです。

- `make check`：整形、lint、型、構造、生成文書の一致、既存ユニットテスト、抑止コメント、ルール対応が全て成功する。
- 違反probe：生成文書の改変（STR-04-a）、学習役への検証用データ混入（STATE-03-a）、抑止コメント（TOOL-03-a）を一時コピーへ挿入し、想定の検査とメッセージで失敗することを確認する。正常なコピーの全検査が先に成功することも確かめる。
- 導入：一時ディレクトリへ全配布ファイルが一致してコピーされる。2回目の導入は終了コード1で、全ファイルと`.gitignore`が変わらない。導入先で`--help`と、計画のないtargetへの`status`が動く。

2026-10-23にmacOS arm64、Python 3.15.0、Git 2.50.1、GNU Make 3.81で、生成ZIPを一時展開して実行し、104テスト、代表的な違反3件の検出、36ファイルの導入と重複時の保護、導入先CLI起動まで成功しました。CI指定のPython 3.12とLinuxは今回未実施です。

成功時の最終行は`ZIP検証: 全検査・代表的な違反3件の検出・導入検証に成功`です。テストはfixtureが役の出力ファイルを用意しており、実モデルの品質改善、実際のエージェント起動、Claude Codeの権限挙動はこの検証の対象外です。

すでにuvを準備した開発環境では、同じ展開先で`make check`だけを実行することもできます。検査用の`.foundation/`、開発用`.claude/`、AGENTS.md・CLAUDE.mdはZIPに収録し、利用先へは`install.py`が`kit/`内のファイルだけをコピーします。

## 移行元と今回の相違

ローカル提供のskill-tune-kit 0.1.0（`pyproject.toml`）を移行しました。外部取得元URL、元コミットID、LICENSEは未特定です。新しいライセンスを推測して付けていません。

配布CLI、4役の定義、プロンプト、計画スキーマ、分割・採否アルゴリズム、既存テストは変更していません。今回加えたのは`ci.json`と`verify-ci.sh`で、READMEはZIP単体の手順へ再構成しました。キャッシュと`.foundation/convergence/`の作業記録は収録していません。

`docs/design/research.md`、`e2e-run.md`、`convergence-report.md`と`.foundation/probe-results.json`は移行元の歴史的な記録です。そこにある確認日・実モデルの成績・ローカルパスは今回の移行検証ではありません。省いたconvergenceの生データはこのZIPから再確認できません。今回の自動検証は上記コマンドで別に再現してください。
