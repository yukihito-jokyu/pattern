---
title: GitHub Actionsの作成・更新スキル
description: 作成・保守的更新・破壊的更新を分け、ルールと参照例、CLI検査、処理時間の報告を一緒に配布するClaude Code向けキット。
slug: /development/skills/github-actions-kit
pattern:
  features:
    - label: 更新の範囲
      value: 作成・保守的更新・破壊的更新の3モード
    - label: 検証
      value: 独自ルールと4種の外部ツールをCLIで集約
    - label: CIの結果
      value: needsの合否とジョブ・ステップの処理時間をreportへ集約
---

# GitHub Actionsの作成・更新スキル

GitHub ActionsのワークフローをAIへ依頼するときは、「既存の書き方を残して一部を足す」のか、「既存の目的を引き継いで構成から作り直す」のかで、変更してよい範囲が変わります。このキットはその違いを3つのモードに分け、作成用スキル `gha-workflow` とレビュー用スキル `gha-review` が同じルール・参照例・検査CLIを使う構成です。利用先の `.claude/skills/` に導入してClaude Codeから使います。

扱うのはワークフロー、compositeアクション、Dependabot設定です。キットには検査ツールだけでなく、CIの最後に処理時間を集計し、前段ジョブの結果から合否を決める `run-report` も含まれます。GitHubの標準仕様の上に、このキットが選んだ命名・配置・権限・更新手順を追加しています。以下では、この2つを区別して説明します。

取得元は[Issue #26](https://github.com/yukihito-jokyu/pattern/issues/26)の会話で指定された既存実装です。`pyproject.toml` の版は `0.1.0` です。独立したLICENSEファイルは見つかっておらず、今回の移行で利用許諾を推測・新設していません。

## 全体像

ZIPは次の構造です。ここに示すパスは、展開した `github-actions-kit/` を基準にします。

```text
github-actions-kit/
  AGENTS.md / CLAUDE.md        キットを開発するときの入口
  .claude/skills/
    gha-workflow/SKILL.md      作成と2種類の更新の手順
    gha-workflow/references/   ルール、手順、ワークフローとアクションの見本
    gha-review/SKILL.md        同じルールを使うレビュー
  .claude/settings.json        キット開発時の編集前後のhooks
  .gha/
    gha.py / gha.py.lock       検査・SHA固定・棚卸しのCLIと固定依存
    gha_kit/                  独自ルール、外部ツールの起動、結果の合成
    yamllint.yml              YAMLの書式
    actionlint.yaml           自前ランナーのラベル
    zizmor.yml                アクションの許可表とSHA固定
  .github/
    workflows/                ci、reusable-check、release、deploy-pages、security-auditの見本
    actions/setup-kit/        キット開発の依存導入
    actions/run-report/       処理時間の報告とneedsの合否
    dependabot.yml            外部アクションの更新
  docs/design/                ルール全文、構造、採用理由を記したADR
  .foundation/                抑止検査、違反例、元キットの収束試行記録
  scripts/ / tests/           キット専用の構造検査・生成器・unit test
  install.py                 利用先へ必要な部分だけ導入
  Makefile / pyproject.toml / uv.lock / .python-version
  ci.json / verify-ci.sh      ZIP単体の準備・検証
```

作成用スキルは、依頼に対応する手順を `references/patterns.md` から選び、`references/examples/` の見本を読み、編集のたびにCLI検査を実行します。レビュー用スキルは同じルールIDで機械検査と人による確認を分けます。ルールと見本の正本は `docs/design/rules.md` と `.github/` です。`make docs` がスキル内へ写し、`make docs-check` が正本との不一致を検出するため、正本と配布用の説明が別々に更新されるのを防ぎます。

`install.py` はこの一式をそのまま利用先へ複製する処理ではありません。利用先にはCLI、2スキル、`run-report`と必要な設定を導入します。キット自体の開発用ファイルや参照ワークフローを自動導入しない点は、後述の導入範囲で確認します。

## 依頼と変更範囲を3モードでそろえる

`.claude/skills/gha-workflow/SKILL.md` の手順4・5と、`docs/design/adr/0010-three-update-modes.md` では、次のように変更と完了条件を対応付けています。

| モード | 実際の変更 | 完了を確かめるコマンド |
| --- | --- | --- |
| 作成 | 目的・トリガー・ジョブ・secrets・environmentを整理し、見本から新規作成 | `gha check` の指摘0件 |
| 保守的更新 | 依頼に必要な行だけを変更し、既存の名前・順番・コメント・引用を保持 | `gha check --ratchet HEAD` の増えた組0件 |
| 破壊的更新 | 既存の事実を棚卸しし、意図を確認してから見本に沿って再構成 | `gha check` の指摘0件と、棚卸しの全事実の扱いを報告 |

ここで `gha` は次のCLIの略記です。作業場所は利用先リポジトリのルートです。

```bash
uv run --locked --script .gha/gha.py check
uv run --locked --script .gha/gha.py check --ratchet HEAD .github/workflows/ci.yml
uv run --locked --script .gha/gha.py intent .github/workflows/ci.yml
uv run --locked --script .gha/gha.py intent .github/workflows/ci.yml --compare-ref HEAD
```

既存のワークフローを変更するときは、スキルが保守的更新か破壊的更新かを利用者に選んでもらいます。聞けない場合は保守的更新を使います。ADR 0010では、依頼していない書き換えを避けるための選択と説明しています。既存の指摘まで全部解消する条件にすると、保守的更新でも依頼外の行を書き換えることになるため、完了条件も分かれています。

`intent` はトリガー、入力、権限、secrets、vars、environment、ジョブ、ランナー、uses、run、成果物、出力の12種類の事実を抽出します。意図そのものを推定して確定する処理ではありません。表の意図は利用者とエージェントが確認し、作り直した後の `--compare-ref HEAD` で消えた事実に「移した先」か「落とした理由」を対応付けます。ファイル名が変わる場合は `--from .github/workflows/old.yml` で旧パスを指定します。

### 保守的更新で比べる対象

`.gha/gha_kit/ratchet.py` の `compare` は基準版の `.github/` を一時ディレクトリへ取り出し、現在の `.gha/` 設定で検査します。現在版も同じ設定で検査し、**ファイルパスとルールIDの組ごとの件数**が増えた場合だけ失敗にします。

例えば同じファイルの同じルールの指摘が2件から3件なら増加です。一方、同じ組で1件を直して別の1件を増やしても、件数が同じなら増加として検出しません。ratchetは行単位の新規違反識別ではないため、レビューでは依頼外の変更がないかも確認します。基準版の取得にはGitの履歴が必要です。履歴がない場所では通常の `check` を実行して既存指摘を報告するのが、元キットのADR 0010にある代替手順です。

### 依頼から決まらない値

作成用スキルの手順2は、既定ブランチを `origin/HEAD` から読み、取得できなければ `main` を使います。ランタイムは `.python-version`、`.nvmrc`、`go.mod` 等から読み、無ければ依存定義を使い、それも無ければ利用者へ確認します。matrixは複数版の依頼があるときだけ作ります。

ランナーの既定値は `ubuntu-24.04`、ジョブの時間上限は10分、reportは5分です。定期実行は依頼の頻度を使い、頻度も無ければ月曜9時17分・`Asia/Tokyo` を既定にします。成果物はジョブ間の受け渡しなら1日、人が取得する用途なら7日、リリースタグは `v*` です。これらはGitHubの全利用者に必須の値ではなく、元キットの規約です。特定の時刻・分・保持日数を選んだ経緯は確認できていません。利用先の事情に合わせる場合も、変更した値と根拠をスキルの報告へ残します。

## 独自ルールと外部ツールを一つの結果へ集める

`.gha/gha.py` の先頭には、CLI自身の実行環境を用意するスクリプト依存が入っています。

```python
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "actionlint-py==1.7.12.25",
#   "pyyaml==6.0.3",
#   "shellcheck-py==0.11.0.1",
#   "yamllint==1.38.0",
#   "zizmor==1.31.1",
# ]
# ///
```

uvはこのPEP 723形式の宣言と、隣接する `.gha/gha.py.lock` を使います。`--locked` はロックの更新が必要なら失敗し、依頼していない依存の更新を検査に混ぜません。ADR 0004では、Python製ツールに加えてactionlintとshellcheckの配布パッケージも同じ環境へ入れることで、配布先にGoやRustのビルド環境を要求しない方針を採っています。各固定版の細かな番号の選定経緯は確認できておらず、今回の移行では原本を維持しています。

`.gha/gha_kit/checks.py` の `run` は次の順に結果を合成します。

```python
found = targets.discover(root)
chosen = targets.select(found, paths)
docs = {rel: yamlnode.load(root, rel) for rel in found.yaml_files()}
selected = set(chosen.all_files()) | (set() if paths else {layout.DEPENDABOT})
findings = [finding for finding in policy.check(root, found, docs) if finding.path in selected]
findings += tools.yamllint(root, chosen.yaml_files(), runner)
findings += tools.actionlint(root, chosen.workflows, runner)
findings += tools.shellcheck(root, chosen.scripts, runner)
findings += tools.zizmor(root, chosen.yaml_files(), runner, online)
return sorted(set(findings))
```

独自の `policy` は全ファイルの関係を読みます。例えば `ci.yml` に検証を集めること、`report.needs` が全ジョブを含むこと、ジョブの権限や時間上限を確認します。その後、yamllintがYAMLの形式、actionlintがActionsの構文と `run:` 内のshellcheck、単独shellcheckが `.github/scripts/` のシェル、zizmorがセキュリティを確認します。パスを指定した場合も構造の読み込みは全体で行い、返す指摘を対象パスへ絞ります。

外部ツールの指摘は `rulemap.py` で共通ルールIDへ対応付け、`<ルールID> <パス>:<行> <説明>` という形式へそろえます。CLIの終了コードは0が指摘なし、1が指摘あり、2が使い方やツールの誤りです。zizmorは通常 `--offline` で実行され、`check --online` のときにオンライン検査へ変わります。通常の `make check` はタグの実在まで照合する `pin --verify` を自動実行しません。

### YAMLの形式を決める設定

`.gha/yamllint.yml` は標準の規則を基礎にして、キットのルールへ合わせています。

```yaml
extends: default
rules:
  anchors:
    forbid-undeclared-aliases: true
    forbid-duplicated-anchors: true
    forbid-unused-anchors: true
  braces:
    forbid: non-empty
  brackets:
    forbid: non-empty
  comments:
    min-spaces-from-content: 1
  document-start: disable
  float-values:
    forbid-inf: true
    forbid-nan: true
    forbid-scientific-notation: true
  indentation:
    spaces: 2
    indent-sequences: true
  key-duplicates:
    forbid-duplicated-merge-keys: true
  line-length:
    max: 120
  octal-values:
    forbid-implicit-octal: true
    forbid-explicit-octal: true
  quoted-strings:
    quote-type: double
    required: only-when-needed
  truthy:
    allowed-values: ["true", "false"]
    check-keys: false
```

2スペースのインデントと120文字以内の行、必要なときだけダブルクォートを付ける書式です。空の `{}` は `permissions: {}` に使えますが、値入りの波括弧・角括弧は展開した複数行へそろえます。コメントの前は最低1スペースで、SHAに続く版コメントも受け付けます。文書開始の `---` は要求しません。

アンカーは未定義参照・重複・未使用を禁止し、マージキーの重複も拒否します。特殊な浮動小数・指数表記・暗黙/明示の8進表記を禁じ、読み手やツールによる値の解釈差を減らします。真偽値の表記は `true` / `false` に限定しますが、`check-keys: false` によりGitHubのイベントキー `on` を真偽値扱いの違反にしません。ここにない規則は `extends: default` を引き継ぎ、固定されたyamllint版で同じ基準を使います。これらは元キットの書式規約であり、今回新しい書式へ変更したものではありません。

### アクションの許可とSHA固定

`.gha/zizmor.yml` の親キーを含む設定は次のとおりです。

```yaml
rules:
  unpinned-uses:
    config:
      policies:
        "*": hash-pin
  forbidden-uses:
    config:
      allow:
        - actions/*
        - github/*
        - astral-sh/setup-uv
  self-repository:
    disable: true
```

外部アクションは完全なコミットSHAを使い、許可表は `actions/*`、`github/*`、`astral-sh/setup-uv` に限定します。GitHub APIの操作は追加の外部アクションへ任せず `gh` で書く方針です。SHAは記憶から書かず、次のコマンドで実際のタグから解決します。

```bash
uv run --locked --script .gha/gha.py pin actions/checkout
uv run --locked --script .gha/gha.py pin actions/checkout@v7.0.1
uv run --locked --script .gha/gha.py pin --verify
```

`pin` は `git ls-remote --tags` でタグを取得し、版を省略した場合は安定版の完全な `vX.Y.Z` を選びます。注釈付きタグはタグオブジェクトではなく参照先コミットを採り、`uses: ...@<40桁SHA> # vX.Y.Z` に使う値を返します。`--verify` は記載したSHAと版コメントをリモートのタグへ照合します。ネットワーク接続が必要です。

`self-repository.disable` は、固定しているactionlint 1.7.12が `$/` 参照を受け付けないため、ローカル参照の `./` を維持する選択です（ADR 0006）。この抑止設定を全検査の省略と混同しないよう、許可表とCLIを保護対象にしています。`.gha/actionlint.yaml` の `self-hosted-runner.labels: []` は追加の自前ランナーラベルを登録していない状態です。利用先で自前ラベルが必要なら設定変更の承認範囲を確認します。

## ci.ymlの最後に合否と処理時間を集める

`.github/workflows/ci.yml` はPRとmainへのpushで検証します。以下はイベントと全体設定です。

```yaml
name: ci
on:
  pull_request:
  push:
    branches:
      - main
permissions: {}
concurrency:
  group: ${{ github.workflow }}-${{ github.event.pull_request.number || github.ref }}
  cancel-in-progress: ${{ github.event_name == 'pull_request' }}
defaults:
  run:
    shell: bash
```

`pull_request` にパスやブランチの絞り込みを置かず、PRの検証をこのワークフローへ集約するのがキット独自のSTR-02です。ジョブの実装は `.github/workflows/reusable-check.yml` に分けますが、PRイベントの入口は `ci.yml` にそろえます。`permissions: {}` でワークフロー全体の権限を空にして、必要な権限をジョブ単位で与えます。

concurrencyはワークフロー名とPR番号、PRがない場合はrefでグループを分けます。新しいPR実行が来たときは同じグループの古い実行を取り消し、pushではその取り消しを要求しません。`defaults.run.shell: bash` はrunステップのシェルをそろえます。

### reportのneedsと権限をそろえる

同じファイルの `jobs` は次の形です。

```yaml
jobs:
  check:
    uses: ./.github/workflows/reusable-check.yml
    permissions:
      contents: read
  report:
    needs:
      - check
    if: ${{ !cancelled() }}
    runs-on: ubuntu-24.04
    timeout-minutes: 5
    permissions:
      actions: read
      contents: read
      pull-requests: write
    steps:
      - name: Check out repository
        uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false
          sparse-checkout: .github/actions/run-report
      - name: Report run timings
        uses: ./.github/actions/run-report
        with:
          needs: ${{ toJSON(needs) }}
```

GitHubの `needs` は指定ジョブの終了を待ち、結果を `needs` コンテキストで渡します。ここでは `report` が `check` を待ち、`!cancelled()` によって前段の失敗時にも報告と合否判定を実行します。実行全体が取り消された場合までreportが必ず動くわけではありません。`ci.yml` にジョブを追加したときは、report以外の全ジョブを `report.needs` に加えます。独自ルールOPS-01がこの対応漏れを検出します。

`actions: read` はジョブ/ステップの時刻取得、`contents: read` はローカルアクションのcheckout、`pull-requests: write` はPRコメントに使います。checkoutはreportに必要なアクションだけを取得し、`persist-credentials: false` で後続へGit認証を残しません。10分の通常ジョブに対してreportは集計用として5分です。ブランチ保護の必須チェックを `report` に集約する理由は、ジョブ追加のたびにGitHub側の必須チェック設定を変更する必要を減らすためです（ADR 0008）。必須チェック設定自体は利用者がGitHubで行います。

### run-reportが受け取るものと合否

`.github/actions/run-report/action.yml` は入力を環境変数へ渡します。

```yaml
inputs:
  github-token:
    description: REST API に使うトークン（actions の read と pull-requests の write が要る）
    required: false
    default: ${{ github.token }}
  needs:
    description: 呼び出し元のジョブの toJSON(needs)
    required: true
runs:
  using: composite
  steps:
    - name: Report run timings
      shell: bash
      env:
        GH_TOKEN: ${{ inputs.github-token }}
        NEEDS: ${{ inputs.needs }}
      run: python3 "$GITHUB_ACTION_PATH/run_report.py"
```

トークンは通常 `github.token` です。`needs` は必須で、呼び出し元が渡したJSONを `run_report.py` が読みます。値を `run:` の文字列へ直接展開せず `env:` で渡すのは、キットのERR-02に合わせた形です。アクションはランナーのPython標準ライブラリだけを使い、キットの開発依存には依存しません。

合格扱いは `success` と `skipped` です。`failure`、`cancelled`、`timed_out` 等がneedsにあれば終了コード1で失敗し、空・不正なneedsも失敗します。スキップは成功扱いなので、実行が必須の検証を条件式でスキップしてよいかは別途レビューします。APIから得たジョブのconclusionを合否の根拠にするのではなく、渡されたneedsを根拠にする点が中心です。

### 集計とコメントの境界

`run_report.py` は実行IDと試行番号を使い、`/actions/runs/<id>/attempts/<n>/jobs` から100件ずつ全ページ取得します。完了ジョブだけを取り込み、ジョブの待ち時間・実行時間、全ステップの時間、遅いステップ上位5件、Mermaidのタイムラインを作ります。最初の完了ジョブの作成時刻を起点に経過を計算し、並列ジョブの実行時間合計とは別に表示します。時刻がない場合と実測0秒は、この実装ではどちらも0秒です。APIにまだ反映されていない未完了ジョブを待つ再試行は実装されていません。

結果は `GITHUB_STEP_SUMMARY` に追記します。PRイベントでは `<!-- run-report:<ワークフロー名> -->` で始まる既存コメントを探し、あれば更新、なければ作成します。コメントの検索に投稿者確認はなく、最新コミットや新しい試行との競合を防ぐ専用処理もありません。concurrencyのPRキャンセルと併せて使う構成ですが、古い実行による更新を厳密に排除する保証とは異なります。

コメントは60,000バイト、Summaryは1,000,000バイトを目安にし、超えたらジョブ別のステップ詳細を省略します。この縮小後も必ず上限内へ収まる保証はありません。APIの版は原本の `2026-03-10`、HTTPタイムアウトは30秒です。GitHub実環境でこの版・権限・出力量を今回確認したものではありません。

時刻取得や報告の通信が失敗しても警告に留め、合否はneedsの結果で決めます。fork PR等でコメント権限がない場合は403/404を通知して終了します。したがって「reportが成功した」は「PRコメントが投稿された」と同じ意味ではありません。期待するコメント・SummaryはGitHub実行で別に確認する必要があります。

## 固定依存とキット開発用の設定

`.python-version` は `3.12`、`pyproject.toml` の開発設定は次のとおりです。

```toml
[project]
name = "github-actions-kit"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = []

[dependency-groups]
dev = [
  "mypy==2.4.0",
  "pyyaml==6.0.3",
  "ruff==0.17.2",
  "types-pyyaml==6.0.12.20260906",
]

[tool.uv]
package = false
```

キット自身をPythonパッケージとしてインストールせず、devグループを `uv sync --locked` で用意します。CLIのスクリプト依存とは別のロックです。`make check` はruffの整形・lint、strictなmypy、構造検査、生成文書同期、unit test、`gha check`、抑止禁止、ルールと検査の対応確認を実行します。1つが落ちても残りを実行し、最後にまとめて非0で終了する構成なので、全項目が通ったときだけ成功です。

ruffはPython 3.12構文・120文字の行を基準に、未使用、import順、複雑度、パス操作等を確認します。`pyproject.toml` の `select` にE/W/F/I/N/UP/B/SIM/RUF/C90/PTH/T20/PL/TID/BLE/ARG/ERA/D100/D104を指定し、日本語の全角記号3種と終了コード等の数値は明示的に除外しています。`max-complexity: 10`、引数6・分岐12・return6・文50を上限にします。CLI・スクリプトの表示に必要なT201だけファイルごとに許容し、相対importは禁止です。isortは `gha_kit`、`install`、`run_report`、`tests` を自前コードとして扱います。mypyは対象6群を `.gha` とrun-reportの検索パスでstrict検査し、到達不能コードも警告します。生成文書やfixture・`.foundation/`を通常のPython検査対象から分ける範囲も原本の設定です。細かな閾値の選定経緯は確認できていないため、今回変更していません。

### hooksと生成文書はキット開発時だけ

`.claude/settings.json` は編集系ツールの前に `.foundation/bin/hooks.py pre-edit`、後に `post-edit` を呼びます。前者は保護ファイルの編集時に利用者の確認を求め、後者はPythonやYAMLの編集で `make fix-file FILE=...` を実行します。タイムアウトはそれぞれ30秒と120秒で、失敗時に無制限に待たないための上限です。hooksはキットのルートでClaude Codeを起動した場合の設定であり、親ディレクトリで起動した場合にこの設定が動くと扱いません。

`.foundation/manifest.json` はMakefile・依存定義・`.gha/`・ルール正本・hooks等を保護対象にし、検査を通すための設定変更や抑止コメントを禁じます。違反例は `.foundation/probes.json`、独立した収束試行は `.foundation/convergence/` にあります。3人・最大3ラウンド・並列3・1試行1,800秒、収束閾値はファイル1.0・名前0.8・内容0.0という元設定です。今回の移行でこれらの試行を再実行したものではありません。

### 参照例とDependabot

`.github/workflows/reusable-check.yml` はlint、typecheck、Python 3.12/3.13のtestを分け、各ジョブは `contents: read`、Ubuntu 24.04、10分です。testのmatrixは `fail-fast: false` で他の版も確認します。`setup-kit` はuvのcacheを通常有効にし、Python版指定が空なら `.python-version` を読み、`uv sync --locked` を実行します。releaseからはcache無効を渡す参照例です。キットの今回の単体検証はPython 3.12で行い、参照例の3.13は未実施です。

`.github/dependabot.yml` は次の設定です。

```yaml
version: 2
updates:
  - package-ecosystem: github-actions
    directories:
      - /
      - /.github/actions/*
    schedule:
      interval: weekly
    cooldown:
      default-days: 7
    groups:
      github-actions:
        patterns:
          - "*"
```

リポジトリのワークフローとcompositeアクションで使う外部アクションを対象に、週1回、新しい版の公開から7日のcooldownを置き、1グループのバージョン更新PRへまとめます。セキュリティ更新にはcooldownを適用しないのがGitHubの仕様で、`applies-to` を省略したこのgroupもバージョン更新を対象にします。これはキットの更新方針で、GitHubの必須設定ではありません。利用先にDependabot設定が既にあれば `install.py` は上書きしないため、既存設定へこの対象や方針を取り込むかは利用者が確認します。

release、Pages公開、定期監査の参照ワークフローも同梱しています。実際に使う場合は `gha-workflow/references/patterns.md` の該当節を読み、タグ、ランタイム、secrets、environment、Pages設定を利用先へ合わせます。参照例を含む `.github/workflows/` 一式はインストーラーの自動コピー対象ではありません。

## 導入と使用

macOSまたはLinuxのbash、GNU Make、Git、Python 3.12とuv 0.13.4を基準にします。初回はuv・Python・依存の取得にインターネット接続が必要です。WindowsではWSL等で同じ環境を用意します。Claude Codeは元キットが記録している2.1.308を基準とし、今回の実対話確認は行っていません。サイト側のNode.js/npm依存は不要です。

ZIPを展開した `github-actions-kit/` 内で、準備と検証をこの順に行います。準備が失敗したら、原因を解消してから次へ進みます。

```bash
uv sync --locked
uv sync --locked --script .gha/gha.py
uv run --locked python --version
make check
```

配布先ディレクトリを用意し、dry-runを確認してから導入します。

```bash
python3 install.py /path/to/your-repo --dry-run
python3 install.py /path/to/your-repo
cd /path/to/your-repo
uv run --locked --script .gha/gha.py check
```

`install.py` の対象は次の定義に対応しています。

```python
REPLACED_DIRS = (
    ".gha/gha_kit",
    ".github/actions/run-report",
    ".claude/skills/gha-workflow",
    ".claude/skills/gha-review",
)
REPLACED_FILES = (".gha/gha.py", ".gha/gha.py.lock", ".gha/yamllint.yml")
KEPT_FILES = (".gha/zizmor.yml", ".gha/actionlint.yaml", ".github/dependabot.yml")
```

4ディレクトリは再導入時に丸ごと置き換わり、古い実装ファイルも消えます。3ファイルも上書きされます。`KEPT_FILES` は導入先に存在すれば保持し、無い場合だけ追加します。許可表や自前ランナー設定、更新方針を利用先が持てるようにするための境界です。導入先で独自変更したコードは、置換対象の外へ保管するか、導入前後の差分を確認します。

キット開発用Makefile、依存定義、`CLAUDE.md`、hooks、`.foundation/`、`setup-kit`、参照ワークフローはコピーしません。空のリポジトリでは、run-reportとDependabot設定の組がそろい、`gha check: 指摘 0 件` が期待結果です。既存ワークフローがある場合は既存の指摘が出ることがあるため、導入しただけで全検査成功と扱いません。

利用先でClaude Codeを起動し、「CIを追加して」「このワークフローを保守的更新で変更して」「この差分をレビューして」と依頼します。2スキルは `.claude/skills/` の配布形式のまま維持しており、このサイトのCodexオートフローの役や設定とは別の成果物です。

## 検証方法と結果

ZIP展開先のルートで次を実行します。

```bash
bash verify-ci.sh
```

`ci.json` の `command: ["bash", "verify-ci.sh"]` と `pythonVersion: "3.12"` が共通CIへの入口です。スクリプトは一時仮想環境へuv 0.13.4を用意し、Python 3.12と開発/CLIのロック済み依存を先に準備します。その後 `make check`、一時コピーでのSTR-02-a・OPS-06-a・TOOL-03-bの違反検出、インストーラーのdry-run、新規導入と再導入、設定保持、古い実装の置換、無関係ファイルの保持、空リポジトリの指摘0件を確認します。代表probeは `--only` を使うため、元のprobe結果を更新しません。

2026年10月23日、macOS 15.7.3（arm64）、CPython 3.12.11、uv 0.13.4で、ビルド生成ZIPを別の一時ディレクトリへ展開して確認しました。`make check` の全項目と54件のunit testが成功し、代表probeは3件中3件を検出しました。dry-runが書き込まないこと、新規導入、再導入時の既存3設定保持・古い4ディレクトリと3ファイルの置換・無関係ファイル保持、導入先での指摘0件も確認しました。ZIPは原本147ファイルを欠落なく含み、実装の変更はREADME補足と `ci.json`・`verify-ci.sh` の追加です。同日22:03 JST、Node.js 26.12.1とChromium 156.0.8078.4（1440×1100）で生成サイトを開き、トップの紹介から本文、ヘッダーからサイドバーを経由した本文への導線、16個のコードブロックの表示、ページのJavaScriptエラー0件を確認しました。ブラウザーで取得したZIPは149ファイルを含み、生成ZIPとバイト一致しました。正規のダウンロードURLもHTTP 200で同じ内容を返しました。説明用PNGはこのパターンでは追加していません。GitHub上では未実行です。Claude Codeによる実対話、GitHubのブランチ保護、実APIによるコメント投稿と処理時間表示、Python 3.13の参照matrix、Windows環境は未確認です。unit testの偽APIで確認した範囲と、GitHub上の実動作を分けます。

`.foundation/probe-results.json`、収束試行のpatch・report、`docs/design/convergence-report.md` は移行元が持っていた記録をそのまま収録しています。今回のローカル検証結果を示す新しい実行ログではありません。説明の分かりやすさと利用先での適用可否は、人間の確認対象です。

## 参考資料

- [GitHub Actionsのワークフロー構文](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)：`needs`、ジョブ権限、concurrencyの標準仕様。
- [Claude Codeのskills](https://code.claude.com/docs/en/skills)：プロジェクトの `.claude/skills/<名前>/SKILL.md` から読み込む形式。
- [Dependabot設定の仕様](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference)：対象ディレクトリ、週次実行、cooldown、更新グループ。
- [GitHub Actionsのジョブ取得API](https://docs.github.com/en/rest/actions/workflow-jobs)：試行ごとのジョブ・ステップ時刻の取得。
- [uvのスクリプト実行](https://docs.astral.sh/uv/guides/scripts/)：スクリプト依存と隣接lockファイル。
- [uvの同期とロック](https://docs.astral.sh/uv/concepts/projects/sync/)：devグループ、lockと同期の関係。
- [uvのCLI](https://docs.astral.sh/uv/reference/cli/)：`--locked` の失敗条件。
- ZIP内の `docs/design/rules.md`、`architecture.md`、`adr/0004-uv-script-toolchain.md`、`adr/0008-report-job-gates-ci.md`、`adr/0010-three-update-modes.md`：キットの規約と採用理由。

[実装をダウンロード](/downloads/patterns/development/skills/github-actions-kit.zip)
