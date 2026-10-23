# github-actions-kit の技術調査

採用した推奨には出典を付け、確認の状態を書いている。バージョンは、レジストリのコマンドで確かめた値である（2026-10-23 時点）。

調査の一次記録（表と原文の引用、実行したコマンドの出力）は次の2つにある。この文書は、そこから採否を決めた結果をまとめたものである。

- [research/github-actions.md](research/github-actions.md)：GitHub Actions の公式ドキュメントと changelog、REST API、Dependabot、キャッシュ、主要アクションの最新タグと SHA、ランナーイメージ
- [research/tools.md](research/tools.md)：actionlint、shellcheck、zizmor、yamllint、PyYAML を実際に動かした結果

## 調べた時点で、書き方に大きく響いた変化

前提として、2025〜2026 年に GitHub Actions の推奨は大きく動いた。記憶にある書き方のままだと、次の点で古くなる。

| 変化 | 時期 | この基盤での扱い |
|---|---|---|
| 依存の固定の最善策が「ワークフロー依存ロックファイル（`.github/workflows/actions.lock`）」になり、SHA の固定は次善策になった | 2026-10-14 public preview | preview なので採らない。SHA の固定を続け、GA になったら切り替える（[ADR 0005](adr/0005-sha-pin-until-lockfile-ga.md)） |
| 同じリポジトリのアクションを `$/path` で参照するのが推奨になり、`./path` は例外扱いになった | 2026-07-30 | actionlint 1.7.12 が `$/` を不正な書式として拒否するので採らない。`./` を使い、zizmor の `self-repository` 監査を止める（[ADR 0006](adr/0006-no-syntax-ahead-of-linters.md)） |
| `ubuntu-latest` が 24.04 から 26.04 へ移行中で、実行ごとにどちらに当たるか分からない | 2026-10-19〜11-19 | `ubuntu-24.04` に固定する（[ADR 0007](adr/0007-runner-images.md)） |
| `schedule` に `timezone` を書けるようになった | 2026-03-19 | 採る（OPS-04）。actionlint 1.7.12 も対応している |
| ステップの並列実行（`background`、`parallel` など）、concurrency の `queue` | 2026-05〜06 | actionlint 1.7.12 が対応していないので使わない（ADR 0006） |
| `pull_request_target` の防御が強まり、checkout v7 はフォークの PR の checkout を既定で拒否する | 2025-12〜2026 | `pull_request_target` を使わない（OPS-05） |
| Node 20 がランナーから削除された | 2026-09-23 | 使う全アクションの版が node24 か composite であることを確かめた（research/github-actions.md の7章） |

## GitHub Actions（2026-10-23 時点の docs.github.com）

- 確認方法：`https://docs.github.com/api/article/body?pathname=<パス>` で本文を取得して原文を確認した。changelog は記事ごとに取得した（2026-10-23）
- 確認の状態：確認済み
- 公式の推奨：
  - 外部のアクションは完全なコミット SHA に固定する（ロックファイルを採らない場合）。タグは作者を信頼できる場合だけ（[Secure use reference](https://docs.github.com/en/actions/reference/security/secure-use)）
  - GITHUB_TOKEN の権限は最小にする。`permissions` を1つでも書くと、書かなかった権限は `none` になる。`permissions: {}` は全部を無効にする（[workflow syntax の permissions](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#permissions)）
  - 信頼できない入力（PR の題名、ブランチ名など）は `run` に直接埋め込まず、環境変数を通す（[Script injections](https://docs.github.com/en/actions/concepts/security/script-injections)）
  - `shell` を省くと `bash -e {0}` で、`shell: bash` を明示したときだけ `-o pipefail` が付く（workflow syntax の `defaults.run.shell`）
  - `always()` ではなく `${{ !cancelled() }}` を使う。`!` で始まる式は `${{ }}` で囲む（[Expressions の status check functions](https://docs.github.com/en/actions/reference/workflows-and-actions/expressions#status-check-functions)）
  - `if:` で `${{ }}` の外に文字列があると、条件が常に真になる（[changelog 2026-01-29](https://github.blog/changelog/2026-01-29-github-actions-smarter-editing-clearer-debugging-and-a-new-case-function)）
  - ジョブの `timeout-minutes` の既定は 360 分（workflow syntax）
  - concurrency の group はワークフロー間で衝突しないよう `${{ github.workflow }}-${{ github.ref }}` の形を例に挙げている（workflow syntax の `concurrency`）
  - `schedule` は既定で UTC。毎時 0 分前後は遅延し、破棄されることもあるので別の分を選ぶ（[Events that trigger workflows の schedule](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)）
  - PR で作ったキャッシュはその PR の中でしか使えず、既定のブランチのキャッシュは PR から読める（[Dependency caching](https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching)）
  - `$GITHUB_STEP_SUMMARY` はステップごとに 1 MiB まで（[Workflow commands](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands)）
  - 同じリポジトリのアクションは `$/path` で参照する（workflow syntax の `steps[*].uses`）
- 採用するもの：STR-01、STR-02、ERR-01、ERR-02、ASYNC-01、ASYNC-02、OPS-04、OPS-05、OPS-06、CODE-01、STATE-02
- 採用しないもの：ワークフロー依存ロックファイル（preview のため。ADR 0005）、`$/path`（検査ツールが未対応。ADR 0006）
- ツールにできないこと：ジョブの所要時間を PR に出す仕組みは公式に無い。REST API でジョブとステップを取得する自作のアクション（`.github/actions/run-report/`）で補う（OPS-01）

## GitHub REST API（Actions のジョブ、Issues のコメント）

- 確認方法：[Workflow jobs](https://docs.github.com/en/rest/actions/workflow-jobs) と Issues のコメントのページの本文を取得した（2026-10-23）
- 確認の状態：確認済み
- 公式の推奨：
  - `GET /repos/{owner}/{repo}/actions/runs/{run_id}/attempts/{attempt_number}/jobs` で、1回の試行の全ジョブとステップの `started_at`・`completed_at` を取れる。`per_page` は最大 100。権限は `actions: read`
  - ステップの `started_at`・`completed_at` は null になりうる
  - 例は `X-GitHub-Api-Version: 2026-03-10` を使う
  - フォークからの `pull_request` では GITHUB_TOKEN が読み取り専用になる
- 採用するもの：OPS-01（run-report の実装）
- 採用しないもの：なし
- ツールにできないこと：コメントの作成に `issues: write` と `pull-requests: write` のどちらで足りるかの厳密な条件は文書に無い。広く使われている `pull-requests: write` を使い、フォークの PR でコメントできない場合は通知だけにする

## Dependabot（github-actions）

- 確認方法：[Dependabot options reference](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference) と [Supported ecosystems](https://docs.github.com/en/code-security/reference/supply-chain-security/supported-ecosystems-and-repositories#github-actions) の本文を取得した（2026-10-23）
- 確認の状態：確認済み
- 公式の推奨：
  - `@<sha> # vX.Y.Z` の形で固定すると、Dependabot は SHA と同じ行のコメントを一緒に更新する
  - `directories` はグロブを使える。`directory: "/"` は `.github/workflows` とルートの `action.yml` を対象にする
  - GitHub Actions の `cooldown` は `default-days` だけが効く。2026-07-14 から既定で 3 日のクールダウンがかかる
- 採用するもの：PROC-03
- 採用しないもの：semver 別の cooldown（GitHub Actions では効かないため）
- ツールにできないこと：`.github/actions/*` の composite アクションを `directories` のグロブで更新対象にできるかは文書に明記が無い。最初の Dependabot の実行で確かめる（overview.md の「判断してほしいこと」）

## actionlint 1.7.12（PyPI の actionlint-py 1.7.12.25）

- 確認方法：`curl -s https://pypi.org/pypi/actionlint-py/json` → 1.7.12.25、`actionlint -version` → 1.7.12、`git ls-remote --tags https://github.com/rhysd/actionlint` → 最新は v1.7.12（2026-03-30）
- 確認の状態：確認済み
- 公式の推奨：
  - `-format '{{json .}}'` で JSON を出す。終了コードは 0（問題なし）、1（問題あり）、2（引数の誤り）、3（致命的）
  - shellcheck は PATH から探し、見つからないと黙って検査を飛ばす。`-shellcheck=<パス>` で明示できる
  - 出力の kind 名は syntax-check、expression、action、runner-label、shellcheck、pyflakes、permissions、job-needs、matrix、events、deprecated-commands、if-cond、credentials、env-var、id、glob、workflow-call、shell-name の 18 種（[docs/checks.md](https://github.com/rhysd/actionlint/blob/main/docs/checks.md)）
  - インラインの抑止記法は無い。設定ファイルの `paths.<glob>.ignore` か `-ignore` で抑止する
- 採用するもの：TEST-01、ERR-02（`[expression]` の「potentially untrusted」）
- 採用しないもの：pyflakes の連携（Python の `run:` を書かないため）
- ツールにできないこと：
  - ファイルの置き場、命名、キーの順、トリガーとファイルの対応、report ジョブの形は検査しない。構造の検査（`.gha/gha_kit/rules_*.py`）で補う
  - git のリポジトリ（`.git`）の中でないと、ローカルの再利用ワークフローと composite アクションの入力・出力を呼び出し側と照合しない（`workflow-call` と `action` が出ない）。再利用ワークフローの入力名を変えて呼び出し側を直さない違反は、`.git` の無いコピーでは指摘0件、`git init` したコピーでは `[workflow-call]` で指摘された（2026-10-23）。配布先は git のリポジトリなので照合が働く。git でないこのキットのディレクトリでは、`make check` でこの照合が働かない

## shellcheck 0.11.0（PyPI の shellcheck-py 0.11.0.1）

- 確認方法：`curl -s https://pypi.org/pypi/shellcheck-py/json` → 0.11.0.1。actionlint から `-shellcheck` で呼び、SC2086 が出ることを確かめた
- 確認の状態：確認済み
- 公式の推奨：シェルの変数はダブルクォートで囲む（SC2086）
- 採用するもの：TEST-01
- 採用しないもの：なし
- ツールにできないこと：抑止コメント `# shellcheck disable=` を止められない。構造の検査（TOOL-03）で止める

## zizmor 1.31.1

- 確認方法：`curl -s https://pypi.org/pypi/zizmor/json` → 1.31.1（requires_python >=3.11）。`uvx zizmor@1.31.1 --help` と、違反を入れたワークフローへの実行で確かめた
- 確認の状態：確認済み
- 公式の推奨：
  - `--offline` でネットワークを使わない監査だけを回す。オンライン専用の監査は impostor-commit、ref-confusion、known-vulnerable-actions、stale-action-refs、ref-version-mismatch の5つ
  - 終了コードは 0、1（エラー）、2（引数）、3（入力なし）、11〜14（最も重い指摘が informational〜high）
  - 設定は `rules.<監査名>.config`・`.ignore`・`.disable`。`unpinned-uses` は `policies` で `hash-pin` を求められ、`forbidden-uses` は `allow` の表で使ってよいアクションを絞れる（[docs.zizmor.sh/audits](https://docs.zizmor.sh/audits/)）
  - インラインの抑止は `# zizmor: ignore[監査名]`
  - composite アクションと dependabot.yml も監査する（`dependabot-cooldown` は既定で 7 日以上を求める）
- 採用するもの：OPS-05、DEP-04、DEP-06、ERR-02、OPS-06、STATE-02、PROC-03
- 採用しないもの：`self-repository` 監査（`$/` を actionlint が受け付けないため。ADR 0006）、pedantic と auditor の persona（regular の指摘を0件にするのを基準にする）
- ツールにできないこと：
  - 抑止コメントの禁止は構造の検査（TOOL-03）で補う
  - regular の persona では、`astral-sh/setup-uv` の既定のキャッシュ（`enable-cache: auto`）を `cache-poisoning` で指摘しない（`actions/setup-go` と `actions/cache` は指摘する）。ワークフローの段の `permissions: write-all` も、ジョブが1つなら `excessive-permissions` で指摘しない（ジョブの段の `write-all` は指摘する）。どちらも違反を入れたワークフローで確かめた（2026-10-23）。構造の検査（STATE-02 の `state02_artifacts`、OPS-06 の `ops06_permissions`）で補う

## yamllint 1.38.0

- 確認方法：`curl -s https://pypi.org/pypi/yamllint/json` → 1.38.0（requires_python >=3.10）。厳格な設定で、正しいワークフローが通り、崩したものが落ちることを確かめた
- 確認の状態：確認済み
- 公式の推奨：
  - 既定の設定のままだと、`on:` が truthy、`@sha # v1` がコメント前の空白不足になる。`truthy.check-keys: false` と `comments.min-spaces-from-content: 1` で GitHub Actions に合わせる（[yamllint rules](https://yamllint.readthedocs.io/en/stable/rules.html)）
  - `-f parsable` で1行1件の出力。`--strict` で警告も失敗にする
  - インラインの無効化は `# yamllint disable-line`、`# yamllint disable`、`# yamllint disable-file`
- 採用するもの：TOOL-01
- 採用しないもの：`key-ordering`（アルファベット順を求めるため。GitHub Actions のキーの順は構造の検査 CODE-01 で縛る）
- ツールにできないこと：自動で直す機能が無い。YAML の formatter は足さない（[ADR 0004](adr/0004-uv-script-toolchain.md)）

## PyYAML 6.0.3

- 確認方法：`curl -s https://pypi.org/pypi/pyyaml/json` → 6.0.3。`yaml.compose()` のノードが `start_mark.line` を持ち、キー `on` の値が文字列のまま残ることを確かめた
- 確認の状態：確認済み
- 公式の推奨：`compose` は型に変換する前のノードを返す（ただし tag は compose の時点で bool になる。値の文字列を使えば問題ない）
- 採用するもの：構造の検査の土台（`.gha/gha_kit/yamlnode.py`）
- 採用しないもの：`safe_load`（`on` が真偽値になり、行番号も失うため）
- ツールにできないこと：なし

## uv 0.13.4、CPython 3.12

- 確認方法：`uv --version` → 0.13.4。`uv lock --script` でスクリプトのロックファイルを作り、`uv run --locked --script` がロックとの食い違いで止まることを確かめた
- 確認の状態：確認済み
- 公式の推奨：PEP 723 のインラインのスクリプト依存を `uv run --script` で解決し、`uv lock --script` で固定できる
- 採用するもの：TOOL-05（検査の道具の版の固定）。ランナーの python3 は Ubuntu 24.04 で 3.12.3（research/github-actions.md の8章）なので、開発の Python も 3.12 にそろえる
- 採用しないもの：なし
- ツールにできないこと：なし

## ruff 0.17.2、mypy 2.4.0、unittest

- 確認方法：`curl -s https://pypi.org/pypi/<pkg>/json` → ruff 0.17.2（2026-10-22）、mypy 2.4.0（2026-10-01。2.0.0 は 2026-05-06 で、公開から 90 日を超えている）
- 確認の状態：確認済み
- 公式の推奨：同じ作業場所の他の基盤（autoflow-kit など）と同じ設定の組み方を使う
- 採用するもの：KIT-03、KIT-05
- 採用しないもの：pytest（依存を増やさないため。標準の unittest で足りる）
- ツールにできないこと：モジュールの依存の向きは構造の検査（`scripts/structure_check.py`）で補う

## Claude Code のスキル（claude 2.1.308）

- 確認方法：`claude --version` → 2.1.308
- 確認の状態：確認済み
- 公式の推奨：スキルは `.claude/skills/<名前>/SKILL.md` に置き、front matter の `description` で使う場面を書く
- 採用するもの：配布するスキル `gha-workflow`（作成・更新）と `gha-review`（[ADR 0003](adr/0003-two-distributed-skills.md)）
- 採用しないもの：なし
- ツールにできないこと：スキルが読まれたかを機械で確かめられない。収束テストで確かめる

## 外部アクションの版（固定に使う SHA）

`git ls-remote --tags` で、各アクションの最新の安定版のタグと、そのタグの指すコミットを確かめた（2026-10-23）。SHA はこの表から書き写さず、必ず `uv run --locked --script .gha/gha.py pin <owner/repo>` で解決する（DEP-06）。

| アクション | タグ | runs.using |
|---|---|---|
| actions/checkout | v7.0.1 | node24 |
| actions/setup-python | v7.1.0 | node24 |
| actions/setup-node | v7.1.0 | node24 |
| actions/setup-go | v7.0.0 | node24 |
| actions/cache | v6.1.0 | node24 |
| actions/upload-artifact | v7.0.2 | node24 |
| actions/download-artifact | v8.0.2 | node24 |
| actions/github-script | v9.0.0 | node24 |
| actions/attest-build-provenance | v4.2.2 | composite |
| astral-sh/setup-uv | v10.3.2 | node24 |
| aws-actions/configure-aws-credentials | v6.3.0 | node24 |
| docker/login-action | v4.6.0 | node24 |
| docker/setup-buildx-action | v4.4.1 | node24 |
| docker/build-push-action | v7.4.0 | node24 |

## ランナーイメージ

- 確認方法：[actions/runner-images](https://github.com/actions/runner-images) の README と各イメージの README を取得した（2026-10-23）
- 確認の状態：確認済み
- 公式の推奨：
  - Ubuntu 26.04 は 2026-09-17 に GA。`ubuntu-latest` は 2026-10-19〜11-19 に 24.04 から 26.04 へ移る
  - Ubuntu 24.04 には Python 3.12.3、gh、jq、git が入っている
  - `windows-latest` は windows-2025、`macos-latest` は macOS 26（arm64）
- 採用するもの：NAM-06
- 採用しないもの：`-latest` のラベル（移行中は実行ごとに中身が変わるため）、`ubuntu-26.04`（GA から 90 日未満のため。ADR 0007）
- ツールにできないこと：`-latest` の禁止は構造の検査で縛る（actionlint は `-latest` を正しいラベルとして通す）
