---
title: オートフローを構築するスキル
description: Claude Codeのスキルと補助CLIで計画・実装・検証・レビューを進め、人の承認と検査の証拠を変更内容に結び付けるパターン。
slug: /development/skills/autoflow-kit
pattern:
  features:
    - label: 構成
      value: 3つのスキル・5つの役・Python製CLI
    - label: 確認
      value: 手順・証拠・レビュー・承認を機械で照合
---

# オートフローを構築するスキル

依頼を渡すと、AIが計画・実装・検証・リスク判定・レビューを進め、人は方向の確認や最終承認など決められた場面で判断するClaude Code用のパターンです。文章のほか、Backlog・Redmine・GitLab・GitHubの課題を入口にできます。

AIが「できた」と返すだけでは、検査を実行したか、承認した内容とコミットする内容が同じかを確かめられません。この実装ではPython製の補助CLIが次の手順を決め、検査結果・レビュー・人の回答を変更の版へ結び付けます。スキルはCLIの指示に従って役を起動します。元実装の対象はClaude Code 2.1.296、補助CLIはPython 3.9以上の標準ライブラリだけで動きます。

## 全体像

ZIPには利用先へ入れる道具と、その道具自体を保守・検証するファイルを含みます。

```text
autoflow-kit/
  install.py
  kit/
    .autoflow/
      autoflow.py                     # CLIの入口
      autoflow_kit/                    # 手順・検証・承認の処理
      templates/prompts/               # 各役へ渡す文章
    claude/
      skills/                         # setup / autoflow / learn
      agents/                         # planner / builder / risk / finder / verifier
  tests/                              # 一時リポジトリで動くテスト
  scripts/verify-ci.sh                 # ZIPの準備・全検査・違反検出
  .foundation/                        # 規約の検査・違反例・過去の記録
  docs/design/                        # 構造・規約・判断理由
  Makefile / pyproject.toml / ci.json
```

`install.py`は`kit/`から利用先の`.autoflow/`と`.claude/`へ配置します。`/autoflow-setup`で検査やリスク分類を決めてから、依頼ごとに`/autoflow`を呼びます。

```text
H0: 検査・パス・上限を承認（初回と設定変更時）
  ↓
依頼取得 → 作業前の検査 → 計画 → 条件に当たればH1
  ↓
実装 → 検査 → リスク判定 → AIレビュー
  ↑          行き詰まり・失敗の上限ならH2
  └────────── 指摘や人の回答を受けて修正
  ↓
報告書 → H3: 最終承認 → 承認した版をコミット
```

不具合修正では、実装前に再現テストだけを追加し、そのテストが落ちることを確認する段が入ります。H1とH2は条件に当たる場合だけ、H3は毎回判断します。pushはこの道具では行いません。

## 設定・構造と具体的な動作

### スキルは次の手順をCLIへ問い合わせる

`kit/claude/skills/autoflow/SKILL.md`の先頭で、名前と呼び出し条件を定義します。長い`description`を除いた抜粋です。

```yaml
name: autoflow
argument-hint: "<依頼の文章> | <取得元> <課題の番号> | resume <実行の id>"
disable-model-invocation: true
allowed-tools: Bash(python3 .autoflow/autoflow.py *)
```

`name`が呼び出し名、`description`が用途、`argument-hint`が入力の案内です。`disable-model-invocation: true`により、人が呼び出す手順として扱います。準備と学習のスキルにも同じ指定があり、依頼のない時点で自動起動しない構成です。[Claude Codeのスキル仕様](https://code.claude.com/docs/en/skills#frontmatter-reference)に対応します。

`allowed-tools`は補助CLIを使うための許可です。Read・Write・Agentなどは利用先の通常の権限に従い、この一覧だけで全ツールを制限する指定ではありません。[許可の仕様](https://code.claude.com/docs/en/skills#pre-approve-tools-for-a-skill)と利用先の管理設定も確認してください。

スキル本体は`status --run <実行ID>`を繰り返します。`次:`ならコマンドを実行し、`job`なら指定された役へプロンプトのファイルを渡し、`人:`なら回答を待ちます。スキルが独自に段階を推測せず、再開時も同じ実行IDからCLIが求めた位置へ戻るためです。

### 役はファイルへ成果を書き、CLIが検証する

たとえば`kit/claude/agents/autoflow-builder.md`の設定です。`description`は省略しています。

```yaml
name: autoflow-builder
tools: Read, Grep, Glob, Bash, Edit, Write
```

実装役だけにEditを渡し、ほかの役はRead・Grep・Glob・Bash・Writeを使います。Writeは指定されたJSONの成果物を書き出すためです。Bashでの書き換えまでツール一覧だけで防げないため、読み取り役には書いてよい成果物を文章で限定し、CLIでも前後の変更の版を照合します。Agent・Skillは役の一覧に含めず、再委任を避けています。[サブエージェントのツール設定](https://code.claude.com/docs/en/sub-agents#restrict-which-tools-a-subagent-can-use)に従う構成です。`model`や`permissionMode`は指定せず、親の条件を使います。

| 役 | 入力と成果物 |
| --- | --- |
| autoflow-planner | 依頼とコードから、範囲・条件・未決事項・戻し方をplan.jsonへ書く |
| autoflow-builder | コードとテストを変更し、解説・指摘への回答・行き詰まりをreport.jsonへ書く |
| autoflow-risk | 差分からリスクと人が読むファイルを判定する |
| autoflow-finder | 観点ごとに指摘候補をJSONへ書く |
| autoflow-verifier | 候補が実際の問題かをコードで確かめ、候補ごとの票を書く |

CLIは返答の本文を成功判定に使わず、`workspace.py`と`contracts.py`でJSONの必須項目・型・参照を確かめます。プロンプトは`kit/.autoflow/templates/prompts/`にまとめ、段のモジュールが値を埋めます。文章と判定処理を分け、出力形式の変更時に対応箇所を追える構造です。

### 記録と変更の版で、手順の飛び越しを防ぐ

`kit/.autoflow/autoflow_kit/changes.py`は、Gitのtree IDで現在のファイル内容を表します。

```python
def snapshot(root: Path) -> str:
    """今の作業ツリーの版。未追跡のファイルも含めて index に入れ、その tree id を返す。"""
    proc.git_stage_all(root)
    return proc.git_write_tree(root)
```

`git add -A`でindexを更新してから`git write-tree`を呼ぶので、新規ファイルも版へ含まれます。状態を読むだけでなく、ステージ状態も変わる処理です。各段の入口は`context.begin`を呼び、追記用の`trail.jsonl`から`trail.next_step`が求めた段と現在のtreeを照合します。

`verifying.py`の`verify`は、検査をCLI自身で実行して終了コード・ログ・時間切れとtreeを記録します。通常の検査は終了コード0、修正前の再現テストは非0が期待結果です。検査後にtreeが変われば失敗とし、ファイルを生成する検査や自動修正を実装の成功と取り違えないようにします。検査用の一時ファイルやキャッシュは利用先でも適切に除外します。

H0は`profile-approval.json`にプロファイルのSHA-256と回答の原文を保存し、開始時に承認済み設定の写しを実行領域へ残します。H3は回答とtreeを記録し、承認後にファイル内容が変われば同じ承認でコミットできません。空の回答は承認にしません。これは本人認証サービスではなく、人の判断を受け取り、その対象内容と照合する仕組みです。

### プロファイルで検査と判断条件を決める

設定は利用先の`.autoflow/profile.json`です。正本は`kit/.autoflow/autoflow_kit/profile.py`、項目一覧と既定値の全文は生成される`kit/claude/skills/autoflow-setup/references/profile-schema.md`にあります。以下は意味のまとまりごとの抜粋で、抜粋だけでは完全な設定になりません。

#### 検査コマンドとテストの範囲

`setup.py`はMakefileにcheckがあれば`make check`を優先します。それ以外はMakeのlint・test・build、package.jsonの検査、Go・Rust・pytestなどから案を作ります。Makefileにcheckがあるリポジトリでの例です。

```json
{
  "schema_version": 1,
  "verify": {
    "commands": [{"id": "make-check", "run": "make check", "timeout_sec": 600}]
  },
  "paths": {
    "tests": ["tests/**", "test/**", "**/__tests__/**", "**/*_test.go", "**/*.test.*", "**/*.spec.*", "**/test_*.py"]
  }
}
```

`schema_version`は現在1で、未知の版・キーは検証で停止します。`verify.commands`は1件以上必要です。検出できなければ案は空になり、警告が出るため、人が実在するコマンドを指定します。`id`は重複しないkebab-case名でログの識別に使い、`run`は利用先ルートで実行するシェルコマンドです。`proc.shell`は環境変数`CI`を`1`へ設定します。整形などファイルを書き換える検査は入れません。

`timeout_sec`は検出時の既定600秒、指定範囲1〜3600秒です。時間切れでは子プロセスも停止し、124と時間切れの記録を返します。`paths.tests`は既存のテスト形式を拾うglobです。不具合修正の最初の段では変更をこの範囲へ限定し、たとえばtests/test_calc.pyに再現テストを書き、落ちることを確認してからcalc.pyを直します。

#### パスから求めるリスク

`profile.py`の`DEFAULT_RISK`が初期値です。依存定義や運用設定の影響を見逃さないため、文書よりも高いリスクと人の確認を優先します。

```json
{
  "risk": {
    "always_human": [
      ".github/workflows/**", ".gitlab-ci.yml", ".circleci/**", "Jenkinsfile",
      "**/auth/**", "**/billing/**", "**/payment*/**", "**/migrations/**",
      "**/.env*", "**/*secret*", "**/*.pem", "**/*.key",
      ".autoflow/**", ".claude/**", "**/CLAUDE.md", "**/AGENTS.md", "**/REVIEW.md"
    ],
    "high": [
      "**/package.json", "**/package-lock.json", "**/pnpm-lock.yaml", "**/yarn.lock",
      "**/go.mod", "**/go.sum", "**/pyproject.toml", "**/requirements*.txt",
      "**/poetry.lock", "**/uv.lock", "**/Cargo.toml", "**/Cargo.lock",
      "**/Gemfile*", "**/Dockerfile*", "**/docker-compose*.yml", "**/*.tf"
    ],
    "low": ["docs/**", "**/*.md"]
  }
}
```

`always_human`のパスを計画に含めると実装前にH1が必要となり、差分に含めるとH3で全文を読む対象になります。認証・決済・秘密情報だけでなく、検査やオートフロー自身の規則も対象にするのは、判定条件をAIだけで変えないためです。利用先固有のAPI定義などは必要に応じて追加します。

`high`は依存やインフラの変更をhighにし、`low`は文書・テストだけの差分をlowの候補にします。それ以外の通常の変更はmediumです。`always_human`は少なくともmediumに引き上げますが、それだけでhighにはしません。globの`*`は`/`をまたぎ、`**/`で始まる指定はルート直下にも一致します。バイナリの追加・削除行数は0と数えるため、行数だけでなくパスでも分類します。

差分のパス・行数から`policy.tier_of_changes`が求めた段と、AIの判定を統合する関数も同じファイルにあります。

```python
def merge_tier(rule_tier: str, ai_tier: str) -> str:
    """規則の段と AI の段の大きい方。AI の判定は段を上げる方向にだけ効く（GATE-06）。"""
    return max(rule_tier, ai_tier, key=tier_order)
```

package.jsonを変えた差分は規則でhighになるため、AIがlowと判定してもhighのレビューを行います。作者の判断だけで確認を軽くする経路を避けるためです。

#### レビュー対象と上限、コミットの付記

`profile.py`が作る残りの初期値です。`guide_files`は検出したレビュー指示があれば、そのファイル名で埋まります。

```json
{
  "review": {
    "guide_files": [],
    "skip": ["**/*.lock", "**/package-lock.json", "**/pnpm-lock.yaml", "**/dist/**", "**/vendor/**", "**/*.min.js"]
  },
  "limits": {
    "fix_attempts": 3,
    "review_rounds": 3,
    "max_scope_files": 20,
    "large_diff_lines": 400,
    "huge_diff_lines": 1000
  },
  "commit": {"trailers": []}
}
```

`review.guide_files`はREVIEW.mdなどの指示で、開始時の版を探索役と検証役へ渡します。見つからなければ空配列で、独自指示を追加しません。`skip`は生成物やlockfileを指摘対象から外しますが、その変更がリスク判定から消えるわけではありません。

`fix_attempts`は検査の連続失敗、`review_rounds`はimportantが残るラウンドの上限です。既定3回に達するとH2で続行・再計画・中止を選びます。`max_scope_files`は計画の範囲が20ファイルを超えるとH1へ進む境界です。追加・削除行の合計が`large_diff_lines`の400を超えると少なくともmedium、`huge_diff_lines`の1000を超えるとhighです。上限の整数は1〜100000で、largeをhugeより大きくすることはできません。大きな変更を分け、同じ失敗を繰り返す前に人へ戻すための値で、採用理由はZIPの`docs/design/adr/0010-strict-defaults.md`にあります。

`commit.trailers`はコミット末尾へ足す文字列の配列です。既定の空配列では追加しません。Co-Authored-Byなどが必要ならH0の設定として選びます。プロファイルの各項目は形式検査で必須となり、省略時に暗黙の既定値を補う形式ではありません。設定変更時はH0をやり直します。

### リスクに応じてレビューの観点と投票を変える

人数と票はプロファイルではなく`kit/.autoflow/autoflow_kit/policy.py`の表で管理します。

```python
DEPTHS = (
    Depth("quick", ("correctness", "intent"), 2, 2),
    Depth("standard", ("correctness", "security", "intent"), 3, 2),
    Depth("deep", ("correctness", "security", "intent", "impact"), 3, 2),
)
```

最後の2値は検証役の人数と、指摘を残すために必要な「本物」の票数です。lowはquickで2人中2票、mediumはstandard、highはdeepで3人中2票を必要とします。探索役は各観点に1人ずつで、正しさ・依頼との一致を基本に、安全性・影響範囲を追加します。探索役の候補をそのまま修正対象にせず、別の役がコードを確認する設計です。

`REVIEW`の分類はbug・security・criteria・fit、タグはimportant・pre_existing・nitです。止めるのはimportantで、既存の問題や軽微な指摘は報告へ残します。2ラウンド目以降は前回からの差分を中心に見ます。票数の成立は機械で確認できますが、判断の正しさまで票数だけで保証するものではなく、H3では根拠も読みます。

### 人が判断する4つの関所

関所の正本も`policy.py`にあり、`make docs`で`autoflow/references/gates.md`へ一覧を生成します。

| 関所 | 開く条件と選択 |
| --- | --- |
| H0 準備 | 初回と設定変更時。検査・パス・上限を承認するか修正を伝え、検査実行の許可も決める |
| H1 方向 | 影響highの未決事項、新規依存、20ファイル超の計画、always_humanのパス。続行・再計画・中止 |
| H2 行き詰まり | blockersの報告、検査やレビューの上限。回答を添えた続行・再計画・中止 |
| H3 最終 | 検証とレビューの後に毎回。承認・修正依頼・中止 |

H3の報告書は`handoff.py`が作ります。lowでも要約・証拠・レビュー・検査が見ていないことを読み、mediumは差分全体、highは注意するファイルを1行ずつ確認し、2人目のレビューを頼むか判断します。機械で見ていない条件、残したnitや既存の問題、未決事項の既定値も報告へ出します。

## 導入・使用方法

Python 3.9以上、Git、認証済みClaude Code、利用先の検査に必要な環境を用意します。ZIPを展開した`autoflow-kit/`で実行し、初期コミットのあるGitリポジトリのルートを導入先に指定します。

```sh
python3 install.py --dest /path/to/your-repository
```

インストーラーは異なる内容の既存ファイルがあれば、コピー前に止まります。置き換える範囲を確認し、上書きしてよい場合だけ`--force`を使います。コピー対象はCLI・プロンプト・スキル・役で、既存のプロファイル・承認・実行記録は対象外です。`.gitignore`には`.autoflow/runs/`、`.claude/settings.local.json`、`__pycache__/`を追加します。

利用先のルートでClaude Codeを起動し、次を呼びます。

```text
/autoflow-setup
```

検出されたコマンドやパスを確認し、H0で承認します。検査を確認なしで実行することも承認した場合だけ、`setup-approve --allow`が`.claude/settings.local.json`の`permissions.allow`へ`Bash(make check)`などを追加します。準備した`.autoflow/`・`.claude/`・`.gitignore`を人がコミットしてから依頼を始めます。未コミットや未追跡の変更があるとstartは止まります。コミットは利用先のGit設定を使うため、名前・メールと必要な署名設定も用意します。

```text
/autoflow calcに掛け算の関数multiplyを追加してください
/autoflow github 90
/autoflow resume 20261022-143000
```

GitHubなら認証済みgh、GitLabならglab、Backlog・Redmineなら対応するMCP接続で、スキルが本文・コメントを取得します。CLIはネットワーク取得を行いません。手順はZIPの`kit/claude/skills/autoflow/references/sources.md`にあり、取得できなければ推測で補わず停止します。

最初の例では、計画役がmultiplyの条件を作り、実装役が関数とテストを書き、CLIが検査を実行することを期待します。下記のテストではAIの出力をテストデータで再現して確認します。報告書は`.autoflow/runs/<実行ID>/handoff-<番号>.md`です。終了後の改善は`/autoflow-learn`で、介入・差し戻し・インシデントから案を作り、人が選んだ変更だけを反映します。設定が変わればH0へ戻ります。

基盤の開発用hooksはZIPの`.claude/settings.json`にあります。ZIPのルートをClaude Codeで開くと、編集前に保護対象を確認し、Pythonの編集後に整形・lintを行います。install.pyはこの開発用設定を利用先へコピーしません。基盤の改修時は同梱のAGENTS.md、実装用スキルimpl、docs/design/rules.mdを先に読みます。

## 検証方法と結果

ZIPの展開先でBash・Make・Pythonのvenvとpip・Git・ネットワークを用意して実行します。

```sh
bash scripts/verify-ci.sh
```

一時仮想環境にuv 0.11.14を導入し、MakefileからRuff 0.17.1とmypy 1.20.2を呼びます。[uvのツール実行機能](https://docs.astral.sh/uv/guides/tools/)を使い、サイトの依存関係から切り離しています。RuffはPython 3.9と120桁、mypyは3.9とstrictを指定します。細かな規約と例外はZIPのpyproject.toml、docs/design/rules.md、enforcement-matrix.mdにあります。

make checkは整形・lint・型・構造・生成文書の一致・165件のテスト・抑止コメント・規約との対応を確認します。テストは一時Gitリポジトリを作り、AIのJSON出力をテストデータに置き換えて、依頼からコミットまで、承認後の変更の拒否、読み取り役の間の変更検出などを確かめます。

続いて違反例STR-04-a・GATE-05-a・TOOL-03-aを一時コピーへ入れます。生成した関所一覧の改変、報告処理による承認の代行、抑止コメントを検出し、終了コードと期待する診断を照合します。正常状態の全検査が失敗したら、この段には進みません。同梱する過去の全51件の違反検出や収束評価の記録は、今回再実行する3件と区別します。

CI用のci.jsonは次のとおりです。既存の共通matrixがPython 3.12を準備し、ZIP展開先で同じコマンドを実行します。

```json
{
  "command": ["bash", "scripts/verify-ci.sh"],
  "pythonVersion": "3.12"
}
```

確認日：2026-10-22〜2026-10-23。macOS 15.7.3（arm64）、Python 3.14.2、Node.js 24.9.0、Chromiumで、生成ZIPと掲載サイトを確認しました。

| 確認 | 期待結果 | 実際の結果 |
| --- | --- | --- |
| ZIP展開先のbash scripts/verify-ci.sh | 全検査・165件のテスト・代表的な違反3件の検出が成功 | 成功。依存取得はネットワーク制限で初回失敗し、取得可能な環境で再実行して成功 |
| 掲載元の配置・文書・単体テスト・型・ビルド | すべて終了コード0 | 成功。単体テスト50件 |
| 掲載元のE2E | すべて成功 | 初回は検証サーバーの処理がメモリ不足で停止。再実行で6件成功 |
| 実際の対象ページとZIP | 導線・本文・検索・ZIP取得を確認できる | 成功。一覧・ヘッダー・サイドバー・検索、PC・モバイル・ダーク表示、ZIP内162ファイルと3スキル・5役、キャッシュの除外を確認 |

元実装の一時コピーではインストール後のCLI起動も確認しました。Linux・Python 3.12のCI実行は未実施で、ci.jsonに実行環境と同じ検証コマンドを定義しています。

実モデルによる計画・実装・レビューの品質、外部課題サービスとの接続、各利用先のGit署名、人間による成果物の最終レビューは未確認です。Windowsは動作確認の対象にしていません。.DS_Storeとキャッシュは収録対象から除いています。

## 参考資料

- [Claude Code：スキル](https://code.claude.com/docs/en/skills)
- [Claude Code：サブエージェント](https://code.claude.com/docs/en/sub-agents)
- [uv：ツールの実行](https://docs.astral.sh/uv/guides/tools/)
- ZIP内のdocs/design/overview.md・architecture.md・rules.md・adr/：この基盤の構造と採用理由

## ダウンロード

[実装をダウンロード](/downloads/patterns/development/skills/autoflow-kit.zip)
