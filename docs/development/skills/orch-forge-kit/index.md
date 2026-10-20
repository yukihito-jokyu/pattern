---
title: オーケストレーションスキルの作成と改善
description: Claude Codeの開発用スキルを人と設計し、サブエージェントで構築・評価・改善するPython製の道具一式。
slug: /development/skills/orch-forge-kit
pattern:
  features:
    - label: 利用環境
      value: Claude Code・Python 3.9以上・Git
    - label: 進め方
      value: 目標の合意 → 構築 → 評価と改善
    - label: 検証
      value: 記録済みの実行データと124件のテスト
---

# オーケストレーションスキルの作成と改善

開発の依頼を受け、実装役や確認役のサブエージェントへ仕事を割り振り、結果をまとめるスキルを、ここではオーケストレーションスキルと呼びます。役を分けただけでは、依頼を満たしたか、作業を任せられたか、費用が増えすぎていないかを判断できません。そこで、先に人と成功の条件を決め、その条件で測定しながらスキルを改善します。

このパターンの`orch-forge-kit`は、そのためのClaude Code用の3スキル、4サブエージェント、Python製の補助CLIを配布します。作る対象は、導入先リポジトリで使う別の開発用スキルです。たとえば`dev-orch`を作る場合、`/forge-goals dev-orch`で目標を決め、構築・改善の後に`/dev-orch <開発の依頼>`として使います。

## 全体像

ZIPには配布物だけでなく、その導入処理・開発規約・テストも入っています。

```text
orch-forge-kit/
├── install.py                       # 導入先へのコピーと設定追加
├── kit/
│   ├── .forge/
│   │   ├── forge.py                 # 補助CLIの入口
│   │   ├── forge_kit/               # 承認・構築・評価・比較などの処理
│   │   └── templates/prompts/       # 各役に渡す指示のひな形
│   └── claude/
│       ├── skills/forge-goals/      # 目標と評価条件を人と決める
│       ├── skills/forge-build/      # 設計・下書き・導入
│       ├── skills/forge-run/        # 評価・改善・最終報告
│       └── agents/                 # 設計・構築・採点・分析の4役
├── tests/                           # 一時リポジトリと記録データで検証
├── docs/design/                     # 構造・規約・判断理由
├── .claude/                         # この基盤自体の開発用スキル・hooks
├── .foundation/                     # 規約・違反検出・過去の評価記録
├── Makefile / pyproject.toml        # 検査と検査ツールの設定
├── scripts/verify-ci.sh             # ZIP単体の準備・検証
└── ci.json                          # 掲載元の共通CIから呼ぶ設定
```

`install.py`は`kit/`の中身を導入先へコピーします。ZIP直下の`.claude/`はこの基盤を変更する作者向けで、導入先へ配るスキルの正本は`kit/claude/`です。両者を分けることで、開発規約や作者向けの検査を、利用者のリポジトリへ持ち込みません。

導入後は、次の関係で進みます。

```text
人と目標・指標・課題・予算を合意する（forge-goals）
  ↓ charterの承認
設計役 → 人が設計を承認 → 構築役 → 人が下書きを承認（forge-build）
  ↓ .claude/へ対象スキルと役の定義を導入
評価用コピーで対象スキルを実行 → 採点 → 分析・改善候補（forge-run）
  ↓ 現行版と候補を同じ課題で比較し、人が採否を決める
改善に使わなかった課題も評価 → report.md
```

## 3スキルと4役の分担

### スキルは人との対話と進行を受け持つ

`kit/claude/skills/forge-build/SKILL.md`の先頭です。

```yaml
name: forge-build
description: forge-goals で承認した charter に沿って、まだ無い開発用のオーケストレーションスキルを、設計役と構築役のサブエージェントで作る。設計（役・手順・人に確かめる場面・報告）と下書きのバンドル（SKILL.md とサブエージェント）を人に見せ、承認を経てリポジトリの .claude/ に入れる。「オーケストレーションスキルを作って」「charter からスキルを作って」と言われたときに使う。
disable-model-invocation: true
allowed-tools: Bash(python3 .forge/forge.py *)
argument-hint: "<target-id>"
```

`name`が呼び出し名、`description`が用途の説明、`argument-hint`が引数の案内です。3スキルとも`disable-model-invocation: true`とし、人が`/forge-build dev-orch`のように開始する形を選んでいます。評価に費用がかかり、目標や承認を人と決める必要があるためです。この項目が自動呼び出しを止めることは[Claude Codeのスキル仕様](https://code.claude.com/docs/en/skills#control-who-invokes-a-skill)で確認できます。

`allowed-tools`は、このスキルを呼ぶターンで補助CLIを実行できるようにします。途中の人との対話を挟んでも呼べるよう、導入処理は同じ許可をリポジトリの設定にも追加します。スキルを別の会話へ分岐させる`context: fork`は指定せず、メインの会話が人と対話し、必要な仕事だけをAgentツールで役へ渡します。

| スキル | 入力と仕事 | 人が確認する成果物 |
| --- | --- | --- |
| forge-goals | 人の言葉で目的・成功の条件・課題を受け取り、指標と予算を決める | charter.mdと起動回数・費用上限の見積もり |
| forge-build | 承認済みcharterから設計役と構築役を呼ぶ | design.md、下書きのSKILL.md、bundle-check.md |
| forge-run | 現行版の評価、改善案、候補との比較、最終評価を進める | scores.md、proposal.md、compare.md、report.md |

`forge-goals`では、目的・ゴールの文章・課題と受け入れ条件を人に書いてもらい、そのまま残します。指標や予算の選択はAskUserQuestionで案を示して確認します。目標をAIだけで決めると、そのAIが満たしやすい条件を選ぶ可能性があるため、この責任を人に置いています。返答がなければ承認へ進みません。

### サブエージェントは役ごとの成果物を書く

採点役の`kit/claude/agents/forge-grader.md`では、次の設定を使います。

```yaml
name: forge-grader
description: orch-forge の採点役。実行役の実行の記録・最後の返答・差分を、charter の判定項目ごとに判定し、grade.json を書く。forge-run スキルが status の job の行から起動する。それ以外の場面では使わない。
tools: Read, Write, Glob, Grep
omitClaudeMd: true
```

採点役は指定された根拠を読み、判定をファイルへ書きます。`tools`にSkillとAgentを入れず、この役から別のスキルやサブエージェントを起動する経路を作りません。`omitClaudeMd: true`は分析役にも指定し、委任時の初期コンテキストへ通常のCLAUDE.mdを入れず、渡された評価条件と根拠を中心に判断させます。管理ポリシーや、作業中の子ディレクトリの規約まで排除する設定ではありません。[サブエージェントの公式仕様](https://code.claude.com/docs/en/sub-agents#supported-frontmatter-fields)で範囲を確認できます。

| 役 | 定義ファイル | 出力 |
| --- | --- | --- |
| 設計 | forge-designer.md | 役・手順・確認場面・報告項目を定義するdesign.json |
| 構築 | forge-builder.md | 設計から作った下書きのスキルと役の定義 |
| 採点 | forge-grader.md | 実行ごとの受け入れ条件などを判定するgrade.json |
| 分析 | forge-analyst.md | 原因の分類、改善候補、proposal.json |

設計役と構築役の道具はRead・Write・Edit・Glob・Grep、分析役も同じです。採点役は既存の対象実装を直す必要がないためEditを持ちません。いずれも独自の`model`や`permissionMode`を指定せず、親の条件に従います。成果の中身は返答の文章から取り出さず、CLIがファイルを検証します。

## charterで「良い」を固定する

charterは、目標・指標・課題・環境・予算をまとめたJSONです。導入先の`.forge/targets/dev-orch/charter.json`へ置きます。形は`kit/claude/skills/forge-goals/references/charter-schema.md`、検証処理は`kit/.forge/forge_kit/charter.py`にあります。次はスキーマの例から抜き出した、ゴールと指標の対応です。

```json
{
  "schema_version": 1,
  "target": {"id": "dev-orch", "skill_name": "dev-orch"},
  "goals": [
    {"id": "G1", "statement": "依頼を満たし、検査を通して終える", "metrics": ["check_pass", "acceptance", "completion"]},
    {"id": "G2", "statement": "実装はサブエージェントに任せ、決めた手順どおりに進める", "metrics": ["delegation", "flow_conformance"]}
  ],
  "metrics": [
    {"id": "check_pass", "threshold": 1.0, "priority": "must"},
    {"id": "acceptance", "threshold": 1.0, "priority": "must"},
    {"id": "completion", "threshold": 1.0, "priority": "must"},
    {"id": "delegation", "threshold": 0.8, "priority": "must"},
    {"id": "flow_conformance", "threshold": 0.9, "priority": "should"}
  ]
}
```

これは関係を示す抜粋で、このままでは他の必須項目が足りません。`charter-new`で全体の骨組みを作り、人との対話で埋めます。`G1`は「検査を通る」「依頼を満たす」「最後まで終える」の3指標で確かめ、`G2`は編集の委任率と手順の判定で確かめます。`must`は必達条件、`should`は改善したい条件です。数値の閾値は例であり、導入先で人と決めます。

### 識別・目標・課題・承認の項目

| キー | 意味と動作 |
| --- | --- |
| schema_version | 形式の版。現行は1で、異なる形式や未知のキーは検証で停止する |
| target.id / target.skill_name | 作業領域のIDと対象スキル名。運用では同じkebab-case名を使い、道具自身と区別するためスキル名をforge-で始めない |
| purpose | 人が書いた目的の文。設計と分析へ渡し、数値だけでは見えない意図を保つ |
| goals[].id / statement / metrics | G1などのID、人が書いた成功条件、対応する指標ID。選んだ全指標をいずれかのゴールへ結び付ける |
| metrics[].id / threshold / priority | カタログの指標、合格の線、mustかshould。mustを1件以上指定する |
| metrics[].criterion | custom_1など独自指標の判定文。組み込み指標では省略し、計算規則を使う |
| tasks[].id / prompt / acceptance | T1などの課題ID、人が書いた依頼文、受け入れ条件の配列。Tの課題を1件以上用意する |
| approval | 未承認はnull。承認コマンドが内容のsha256とapproved_onを記録する。手では埋めない |

`tasks[].id`が`H1`などHで始まる課題はホールドアウトです。設計・構築・改善へ渡す課題から除き、最後の評価で初めて使います。改善に使った課題だけに合うスキルになっていないかを確かめるためです。Hがなくても形式検査は通りますが、過剰適合を確認できないという警告が出ます。

承認は内容のJSON表現から求めたハッシュで照合します。承認後に目的・閾値・課題などを変えれば、設計・評価の入口で停止します。別の条件で測った数字を、そのまま比較に使わないためです。JSONの空白やキー順を整えただけでは、このハッシュは変わりません。

### 導入先の検査・コピー条件

スキーマの例にある`environment`です。

```json
{
  "environment": {
    "check_command": "python3 check.py",
    "check_timeout_sec": 600,
    "protected_paths": ["check.py"],
    "skip_dirs": [],
    "link_dirs": []
  }
}
```

`check_command`は評価用コピーのルートで実行する検査です。`check_pass`を測るときに必要で、使わなければ空文字にします。`check_timeout_sec`は検査の時間上限で、既定600秒、許容範囲10〜7200秒です。検査用の生成物が差分に混ざらないよう、導入先でもGitの除外設定や検査の出力先を確かめてください。

`protected_paths`は変更してはいけないパスのglobで、`protected_untouched`を選ぶなら1件以上必要です。`skip_dirs`はコピーから除く名前で、先頭が`/`ならルート直下だけを指定します。`link_dirs`はコピーせず元の依存ディレクトリへのリンクにする名前です。初期値は両方空で、必要なものを人と選びます。リンク先は元と共有されるため、コピーの全内容が独立するわけではありません。

### 実行回数と予算

`charter.py`が作る`executor`と`budget`の初期値です。

```json
{
  "executor": {
    "model": "",
    "allowed_tools": [],
    "max_budget_usd": 3.0,
    "timeout_sec": 1800,
    "parallel": 3
  },
  "budget": {"agents": 3, "max_rounds": 3}
}
```

| 項目 | 動作と選び方 |
| --- | --- |
| executor.model | 空ならClaude Codeの既定モデル。比較のモデル条件を固定したいときに名前を指定する |
| executor.allowed_tools | 確認なしで許す道具。初期値は空で、導入先の検査など必要なコマンドをBash(make check)の形で人と決める |
| executor.max_budget_usd | 1回の評価実行の費用上限。既定3ドル、0より大きく100以下 |
| executor.timeout_sec | 1回の評価実行の時間上限。既定1800秒、60〜7200秒 |
| executor.parallel | 同時に動かす実行役の数。既定3、1〜20。課題あたりの総実行回数とは別 |
| budget.agents | 1課題あたりの反復回数。既定3、1〜10。一致度を測るなら2以上必要 |
| budget.max_rounds | 改善を試す最大ラウンド数。既定3、1〜10。人が採否を決める機会もこの単位で生じる |

これらは対話を始めるための既定値です。予算と待ち時間を抑えつつ実行のばらつきを見る設定として用意されていますが、導入先での適切な値は人が選びます。`charter-check`は、初回・各候補・最終評価の起動回数と費用上限の見積もりを出します。設計・構築・採点・分析を行う会話の費用は、実行役の上限とは別です。

## 評価の値をどう作るか

### 機械で数える事実と、採点役の判定を分ける

指標の正本は`kit/.forge/forge_kit/catalog.py`、計算は`score.py`にあります。CLIの`metric-catalog`と`forge-goals/references/metric-catalog.md`は、この正本から一覧を出します。

| 指標 | 求める値 | カタログの閾値 |
| --- | --- | --- |
| check_pass | コピー内の検査が終了コード0だった割合 | 1.0以上 |
| acceptance | 採点役が課題の受け入れ条件を満たすと判定した割合 | 1.0以上 |
| protected_untouched | 保護パスを変更しなかった実行の割合 | 1.0以上 |
| completion | 実行記録がsuccessで、打ち切りなし・終了コード0だった割合 | 1.0以上 |
| delegation | Edit・Writeなどの編集のうち、サブエージェントが行った割合。編集なしの実行は除く | 0.8以上 |
| flow_conformance | 採点役がSKILL.mdの手順を実行したと判定した割合 | 1.0以上 |
| report_format | 採点役が報告の項目・順序に従ったと判定した実行の割合 | 1.0以上 |
| files_agreement | 同じ課題の実行どうしで、変更ファイル集合のJaccard係数を総当たりで平均 | 0.8以上 |
| cost_usd | resultのtotal_cost_usdから求める1実行の推定費用 | 2.0以下 |
| duration_sec | resultのduration_msを秒へ変換した時間 | 900以下 |
| launches | メインのAgentツールによるサブエージェント起動回数 | 10以下 |
| custom_1など | 人がcriterionに書いた条件を採点役が満たすと判断した割合 | 1.0以上 |

最初の7指標が推奨として骨組みに入り、それ以外は必要なら選びます。値は課題ごとに求めてから課題間で平均するため、実行数の多い課題だけで全体が決まりません。記録にない費用などは不明として扱います。数値が高いことだけで依頼の品質が保証されるわけではなく、受け入れ条件・根拠・実際の差分も合わせて確認します。

### 評価用コピーで実行する

`kit/.forge/forge_kit/execute.py`の`command`は、実行役の引数を1か所で作ります。次は主要部分の抜粋です。

```python
args = [
    CLAUDE,
    "-p",
    prompt,
    "--output-format",
    "stream-json",
    "--verbose",
    "--permission-mode",
    "acceptEdits",
    "--permission-prompts",
    "none",
    "--no-session-persistence",
    "--max-budget-usd",
    str(executor.max_budget_usd),
    "--append-system-prompt-file",
    str(system_path),
]
```

`-p`で対話なしに対象スキルへ課題を渡し、`stream-json`と`--verbose`で実行記録を保存します。`acceptEdits`を使い、確認への回答役がいないため`--permission-prompts none`を指定します。許可されていない操作は拒否されます。モデルや`allowed_tools`が指定されていれば、この後で引数へ追加します。引数の意味は[CLIの公式仕様](https://code.claude.com/docs/en/cli-reference)で確認できます。

コピーは元リポジトリの外のOS一時ディレクトリに置き、元の親ディレクトリのCLAUDE.mdを重ねて読み込むことを避けます。コピーから`.forge/`と道具自身の`forge-*`を除き、ホールドアウトの課題や改善側の道具を実行役へ渡しません。ユーザー単位の設定・スキルは実行条件に残ります。OSがコピーを消した場合は、`prepare`からのやり直しが必要です。

`collect`はGit差分、検査結果、Agentの起動、編集主体、費用・時間をまとめます。`score`が採点役の判定と合わせて指標を計算します。`compare`の推奨は、mustが悪化したら不採用、悪化せず何かが改善したら採用、変化なしなら不採用です。閾値に未達の項目は採用推奨でも残り、最終的な採否は人が決めます。対象スキルを書き換えるのは、承認を受けた`decide --adopt`です。

## 中断しても同じ条件から再開する

`forge-build`と`forge-run`は、次のCLIを繰り返し呼びます。

```sh
python3 .forge/forge.py status --target dev-orch
```

`status`は保存済みの成果物から段階を判定し、`次:`にコマンド、`job`に役・ラベル・プロンプトのパス、人の判断が必要なら承認と修正の選択を出します。スキルが独自に段階を決めないため、途中で会話を閉じても同じIDで続けられます。

残す記録は`.forge/targets/<id>/`、プロンプト・コピーへの参照・実行記録などの作り直せる中間ファイルは`.forge/work/<id>/`です。最終報告は前者の`report.md`にあり、mustの変化、採った変更、ホールドアウト、未達や人に判断してほしい事項を確認します。

## 導入・使用方法

Python 3.9以上、Git、認証済みのClaude Codeが必要です。元実装の対象版はClaude Code 2.1.296です。ZIPを展開した`orch-forge-kit/`で実行します。

```sh
python3 install.py --dest /path/to/your-repository
```

導入先は実在するリポジトリのルートを指定します。導入後の`.claude/settings.json`には、既存の設定を保持したうえで次の許可を追加します。

```json
{
  "permissions": {
    "allow": ["Bash(python3 .forge/forge.py *)"]
  }
}
```

既存ファイルと内容が違うときはコピー前に停止し、上書きを選ぶ場合だけ`--force`を使います。設定JSONの形を読めない場合は変更せず、手動追加の案内が出ます。導入先を信頼するか確認した後、新しいClaude Codeセッションでスキルを読み込みます。

導入先の会話で、次の順に呼びます。既存スキルの改善なら`forge-build`を省きます。

```text
/forge-goals dev-orch
/forge-build dev-orch
/forge-run dev-orch
```

スキルを呼んだだけで目標や課題は決まりません。人の目的と受け入れ条件を記入し、見積もり、設計、下書き、改善候補を段階ごとに確認します。実モデルを使う評価の品質・費用・待ち時間は、導入先で確かめる必要があります。

## ZIPを単独で検証する

展開先で次を実行します。Make、Pythonのvenv・pip、ネットワーク接続が必要です。検証はClaude Codeを起動せず、認証も不要です。

```sh
bash scripts/verify-ci.sh
```

一時仮想環境にuv 0.11.14を導入し、`Makefile`が`uvx ruff@0.17.1`と`uvx mypy@1.20.2`を呼びます。[uvのツール実行機能](https://docs.astral.sh/uv/guides/tools/)を使い、サイト側のPython環境から検査依存を分けています。Pythonの型検査対象は3.9、Ruffは120桁とし、mypyのstrictと到達不能コードの検査を有効にしています。細かな規約と例外の根拠はZIP内の`docs/design/rules.md`と`research.md`にあります。

124件のテストでは、実行役を記録済みstream-jsonに置き換え、設計役・採点役などの出力をテスト用の値で再現します。Gitとファイル操作は実物を使い、導入・競合の停止・承認・構築・比較・採否・報告の流れを確認します。テスト用コピーの`check.py`ではバイトコードを生成せず、検査自体が`__pycache__`を実装差分へ混ぜないことも確認します。

検査コマンドへ渡す環境変数`CI`は、未設定なら`1`を補い、設定済みならその値を保持します。テストでは未設定と`true`の両条件を明示的に用意し、終了時に元の環境へ戻します。実行環境の値を`1`と決め打ちせず、ローカルとCIのどちらでも同じ動作を確かめます。

さらに一時コピーへ代表的な違反3件を入れ、生成文書の不一致、役から別のAgentを起動できる設定、抑止コメントを検出します。終了コードと期待する診断の一致を確認し、正常状態の全検査に失敗したら違反検出へ進みません。

共通CIへ渡す`ci.json`です。Python 3.12の準備後、ZIP展開先で同じコマンドを実行します。

```json
{
  "command": ["bash", "scripts/verify-ci.sh"],
  "pythonVersion": "3.12"
}
```

この基盤を変更するときは、ZIP直下の`AGENTS.md`、実装用スキル`impl`、レビュー用スキル`review`を読みます。編集前後のhooksは、展開先をClaude Codeで開いたときに動きます。保護対象や規約を緩めて検査を通す変更はせず、CLIの`status`、プロンプト、スキーマ、テストの対応をそろえます。同梱する収束評価や44件の違反検出の結果は元実装の記録で、今回の3件の再実行とは区別します。

## 検証方法と結果

確認日：2026-10-21。macOS 15.7.3（arm64）、Python 3.14.2、Node.js 24.9.0、Chromiumで、対応する生成ZIPと掲載サイトを確認しました。

| 確認 | 期待結果 | 実際の結果 |
| --- | --- | --- |
| ZIP展開先のbash scripts/verify-ci.sh | 全検査・124件のテスト・代表的な違反3件が成功 | 成功。Ruff・mypy・構造・生成文書・規約との整合も確認 |
| 掲載元の配置・文書・単体テスト・型・ビルド | すべて終了コード0 | 成功。単体テスト50件 |
| 掲載元のE2E | すべて成功 | 初回は検証サーバーの起動待ちで時間切れ。起動権限のある環境で再実行し6件成功 |
| 実際の対象ページとZIP | 導線・本文・検索・ZIP取得を確認できる | 成功。PC・モバイル、一覧・ヘッダー・サイドバー・検索、ZIP内175ファイルと隠し設定・キャッシュの除外を確認 |

Linux・Python 3.12での実行状況は[PRのCI結果](https://github.com/yukihito-jokyu/pattern/pull/16/checks)を参照してください。実モデルによる設計・採点・改善品質、人間による成果物の最終レビューは未確認です。Windowsは動作確認の対象にしていません。

## 参考資料

- [Claude Code：スキル](https://code.claude.com/docs/en/skills)
- [Claude Code：サブエージェント](https://code.claude.com/docs/en/sub-agents)
- [Claude Code：CLIの引数](https://code.claude.com/docs/en/cli-reference)
- [uv：ツールの実行](https://docs.astral.sh/uv/guides/tools/)
- ZIP内のdocs/design/overview.md・architecture.md・rules.md・adr/：この基盤が選んだ構造と規約の理由

## ダウンロード

[実装をダウンロード](/downloads/patterns/development/skills/orch-forge-kit.zip)
