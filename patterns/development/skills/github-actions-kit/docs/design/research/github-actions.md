# GitHub Actions 公式推奨事項 調査レポート（2026-10-23 時点）

## 0. この資料の前提と読み方

- 目的: 「誰が書いても同じになる」厳格なワークフロー規約の根拠（source of truth）として、GitHub 公式の現行推奨を集める。
- 調査方法: 一次情報のみを使用した。
  - docs.github.com は `https://docs.github.com/api/article/body?pathname=<パス>` で Markdown 本文を取得し、ローカルで grep して原文を確認した。
  - github.blog/changelog は WebFetch で個別記事を取得した。
  - アクションのタグと SHA は `git ls-remote --tags` と `git fetch --depth=1` で取得し、各タグ時点の `action.yml` / `README.md` を `git show` で読んだ（api.github.com は使っていない）。
- 判定列の意味:
  - **確認済み** = 今回取得したページ・コマンド出力で原文を確認した。
  - **未確認** = 記憶ベース、または一次情報で裏付けが取れなかった。
- 重要な前提: 2025〜2026 年に Actions の推奨は大きく動いた。特に「SHA ピン留め」から「ワークフロー依存ロックファイル」への移行（2026-10 public preview）、`pull_request_target` の防御強化、キャッシュの信頼境界（`cache-mode`）、Node 20 廃止、`ubuntu-latest` の 26.04 への移行（移行中）が規約に直接影響する。

---

## 1. セキュリティ強化（Secure use reference ほか）

### 1-1. サードパーティアクションの固定

| # | 内容 | 出典 | 判定 |
|---|---|---|---|
| 1 | 最善策は**ワークフロー依存ロックファイル**で依存を固定すること。原文: "The best measure is to **lock your workflow dependencies** with a lockfile... This is the strongest protection available, and supersedes SHA pinning for repositories that adopt it." | https://docs.github.com/en/actions/reference/security/secure-use | 確認済み |
| 2 | ロックファイルを採用できないリポジトリでは、**フル長コミット SHA へのピン留め**を推奨。"Pin references to actions to a commit SHA in your workflow files." SHA がフォークではなく本家リポジトリのものか検証すること。 | 同上 | 確認済み |
| 3 | タグ指定は「作者を信頼できる場合のみ」。タグは移動・削除され得る。どの方式でもアクションのソース監査は必須。 | 同上 | 確認済み |
| 4 | ロックファイルの実体は `.github/workflows/actions.lock`（YAML、機械生成、手編集禁止）。`workflows`（オンボード済みワークフローごとの依存）と `dependencies`（参照→`ref`/`commit`/`owner_id`/`repo_id`）の 2 セクション。推移的依存（アクションが使うアクション）も対象。再利用ワークフローの依存は「定義側リポジトリのロックファイル」が担当。実行時に `owner_id`/`repo_id` でリポジトリの同一性も検証する。**public preview**。 | https://docs.github.com/en/actions/concepts/security/workflow-dependency-lockfiles | 確認済み |
| 5 | 生成手順: `gh extension install github/gh-actions-lock` → リポジトリ直下で `gh actions-lock`（全体）/ `gh actions-lock .github/workflows/ci.yml`（1 本だけオンボード）/ `--relock`（動いた参照を再解決）/ `--relock --accept-moved`。拡張は `uses` を解決済みバージョンに書き換える（例 `@v3` → `@v3.1.0`）。Dependabot はオンボード済みワークフローの更新 PR でロックファイルも同時に再生成する。 | https://docs.github.com/en/actions/how-tos/secure-your-work/lock-workflow-dependencies | 確認済み |
| 6 | Changelog（2026-10-14）: ロックファイルと「Require lockfile」ポリシーが public preview。編集者注で対象プランが Enterprise Cloud / データレジデンシー / Team / Free に更新。拡張は「ファイルを変更せずに最新か検証（CI チェック可）」機能を持つ。 | https://github.blog/changelog/2026-10-14-github-actions-workflow-lockfiles-in-public-preview/ | 確認済み |
| 7 | 許可アクションポリシー（2025-08-15）: `!` 接頭辞でブロック可能（ブロックリストは最後に評価され他の許可を上書き）。「Require actions to be pinned to a full-length commit SHA」を有効にすると、未ピンのアクションを使うワークフローは失敗する。 | https://github.blog/changelog/2025-08-15-github-actions-policy-now-supports-blocking-and-sha-pinning-actions/ | 確認済み |
| 8 | 上記 SHA 必須化は GitHub 製・自組織のアクションにも適用。ただし**再利用ワークフローはタグ参照のままでよい**（"Reusable workflows can still be referenced by tag."）。ロック済み依存は SHA 必須ポリシーをワークフロー変更なしで満たす。許可リストのタグ指定エントリ（例 `actions/checkout@v6`）はロック済み SHA に一致しないため、ワイルドカードかフル SHA にする。 | https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository | 確認済み |
| 9 | 許可アクション設定は 2026-02 から Free / Team / Enterprise の全プランで利用可能。 | https://github.blog/changelog/2026-02-05-github-actions-early-february-2026-updates | 確認済み |
| 10 | 同一リポジトリ内アクションは `$/path/to/action`（チェックアウト不要、実行中コミットに解決、`@ref` 付与は不可、GHES 不可、ランナー 2.336.0 以上）が**推奨**。`./path` は「Edge cases only」。再利用ワークフローも `$/.github/workflows/x.yml` が推奨。 | https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax （`steps[*].uses` / `jobs.<job_id>.uses`）, https://github.blog/changelog/2026-07-30-reference-same-repository-actions-with-self-repository-syntax | 確認済み |
| 11 | Immutable releases は 2025-10-28 GA。新しい immutable release のタグは移動・削除不可、アセットも変更不可、署名付き attestation 付与。既存リリースは対象外。 | https://github.blog/changelog/2025-10-28-immutable-releases-are-now-generally-available | 確認済み |
| 12 | 「Immutable actions」（GHCR 配布型）は 2025-02 時点で移行中との告知のみ。2026 年の GA 状況は一次情報で確認できず。 | https://github.blog/changelog/2025-02-12-notice-of-upcoming-deprecations-and-breaking-changes-for-github-actions | 未確認（現況） |

### 1-2. GITHUB_TOKEN の最小権限

| # | 内容 | 出典 | 判定 |
|---|---|---|---|
| 1 | 既定権限は「リポジトリ contents の read のみ」に設定し、必要なジョブだけ引き上げるのが良い実践。 | https://docs.github.com/en/actions/reference/security/secure-use | 確認済み |
| 2 | アクションは明示的に渡さなくても `github.token` で GITHUB_TOKEN にアクセスできる。だから権限を絞ること。 | https://docs.github.com/en/actions/tutorials/authenticate-with-github_token | 確認済み |
| 3 | いずれかの権限を指定すると、未指定の権限はすべて `none`。`write` は `read` を含む。`permissions: {}` は全権限を無効化。`read-all` / `write-all` もある。 | https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#permissions | 確認済み |
| 4 | 権限の計算順序: 組織/リポジトリの既定 → ワークフローレベル → ジョブレベルの順に調整。 | 同上 | 確認済み |
| 5 | 現行の権限スコープ一覧: `actions`, `artifact-metadata`, `attestations`, `checks`, `code-quality`, `contents`, `copilot-requests`(write/none のみ), `deployments`, `discussions`, `id-token`(write/none のみ), `issues`, `packages`, `pages`, `pull-requests`, `security-events`, `statuses`, `vulnerability-alerts`(read/none のみ)。**`models` は現行一覧に存在しない**。 | 同上 | 確認済み |
| 6 | `vulnerability-alerts`（Dependabot アラート read）は 2026-09-03 追加。`artifact-metadata` の fine-grained 権限は 2026-01-13 GA。 | https://github.blog/changelog/2026-09-03-github-actions-early-september-2026-updates , https://github.blog/changelog/2026-01-13-new-fine-grained-permission-for-artifact-metadata-is-now-generally-available | 確認済み |
| 7 | 再利用ワークフローでは、呼び出し側から渡された権限は呼ばれた側で**引き下げのみ可能**（昇格不可）。呼び出しジョブで `permissions` 未指定なら呼ばれた側は既定権限。 | https://docs.github.com/en/actions/reference/workflows-and-actions/reusing-workflow-configurations | 確認済み |
| 8 | GITHUB_TOKEN の有効期間: ジョブ終了まで。GitHub ホストは最大 6 時間、セルフホストでも更新は最大 24 時間。 | https://docs.github.com/en/actions/concepts/security/github_token | 確認済み |
| 9 | GITHUB_TOKEN による操作は原則新たなワークフローを起動しない。例外: `workflow_dispatch`/`repository_dispatch`、および GITHUB_TOKEN で作成・更新した PR の `pull_request`（opened/synchronize/reopened）は**承認待ち状態**で起動する。 | 同上 | 確認済み |

### 1-3. スクリプトインジェクション

| # | 内容 | 出典 | 判定 |
|---|---|---|---|
| 1 | 信頼できない入力: `github` コンテキストのうち末尾が `body`, `default_branch`, `email`, `head_ref`, `label`, `message`, `name`, `page_name`, `ref`, `title` のもの（例 `github.event.issue.title`, `github.event.pull_request.body`）。ブランチ名やメールアドレスも攻撃経路（例 `zzz";echo${IFS}"hello";#` は有効なブランチ名）。 | https://docs.github.com/en/actions/concepts/security/script-injections | 確認済み |
| 2 | インラインスクリプトでの推奨対策は**中間環境変数**: `env: TITLE: ${{ github.event.pull_request.title }}` として `run` では `"$TITLE"` を使う。シェル変数はダブルクォートする（SC2086）。もう一つの推奨は、値を引数として受け取る JavaScript アクションを使うこと。 | https://docs.github.com/en/actions/reference/security/secure-use | 確認済み |
| 3 | CodeQL の default setup で GitHub Actions のスキャンを有効化することを推奨。OpenSSF Scorecards も推奨。zizmor への言及はない。 | 同上 | 確認済み |
| 4 | `if:` で `${{ }}` の外に文字列があると条件全体が文字列になり常に truthy。2026-01 からエディタ検証とランの注釈で検出される。 | https://github.blog/changelog/2026-01-29-github-actions-smarter-editing-clearer-debugging-and-a-new-case-function | 確認済み |

### 1-4. `pull_request_target` / `workflow_run`

| # | 内容 | 出典 | 判定 |
|---|---|---|---|
| 1 | 不要なら `pull_request_target` を使わない。特権分離には `workflow_run` の方が良い。これらのトリガーで信頼できないコード（フォーク PR など）を明示的にチェックアウトしてはならない。`workflow_run` では他ワークフローのアーティファクトを慎重に扱う。 | https://docs.github.com/en/actions/reference/security/secure-use | 確認済み |
| 2 | **2025-12-08 から**: `pull_request_target` のワークフローファイルとチェックアウトコミットは常に**デフォルトブランチ**から取得。`GITHUB_REF` はデフォルトブランチ、`GITHUB_SHA` はその最新コミット。環境のブランチ保護ルールは実行参照で評価（`pull_request` 系は `refs/pull/<number>/merge`、`pull_request_target` はデフォルトブランチ）。 | https://github.blog/changelog/2025-11-07-actions-pull_request_target-and-environment-branch-protections-changes/ | 確認済み |
| 3 | `actions/checkout` v7（GA、2026-06-18）は `pull_request_target` と PR 起因の `workflow_run` で**フォーク PR コードのチェックアウトを既定で拒否**。オプトインは `allow-unsafe-pr-checkout: true`。サポート対象の旧メジャーへのバックポート適用は 2026-07-20（v1 は対象外）。 | https://github.blog/changelog/2026-06-18-safer-pull_request_target-defaults-for-github-actions-checkout , checkout v7.0.1 の README/action.yml（git show で確認） | 確認済み |
| 4 | この保護はフォーク PR の ref だけが対象。`git fetch`、`gh pr checkout`、ダウンロードしたアーティファクトの実行は対象外。 | https://docs.github.com/en/actions/reference/security/securely-using-pull_request_target | 確認済み |
| 5 | **ワークフロー実行保護（Workflow execution protections）が 2026-09-17 GA**。アクター規則と イベント規則で「誰が・何が」ワークフローを起動できるかを許可リスト化。公開リポジトリで該当ポリシーがない場合、`pull_request_target` をブロックする既定ルールが追加される（private/internal は対象外、当初は evaluate モード）。 | https://github.blog/changelog/2026-09-17-workflow-execution-protections-in-github-actions-generally-available | 確認済み |
| 6 | **既定ルールの強制開始日が資料間で食い違う**: docs は「2026-11-02」、changelog は「2026-12-02（2026-10-21 更新）」。 | docs: 上記 #4 の URL / changelog: 上記 #5 の URL | 確認済み（両方の記述を確認。どちらが最新かは changelog の更新日の方が新しい） |
| 7 | 公開リポジトリで「潜在的に悪意あるワークフロー実行」は自動で保留され、write 権限のコラボレーターの承認が必要（2026-07-28〜、設定不要）。 | https://github.blog/changelog/2026-07-28-github-actions-holds-potentially-malicious-workflows-for-approval | 確認済み |

### 1-5. OIDC・セルフホストランナー・シークレット

| # | 内容 | 出典 | 判定 |
|---|---|---|---|
| 1 | クラウド接続は OIDC を使い、長期シークレットの保存をやめる。AWS ではカスタムクレームは使えない。 | https://docs.github.com/en/actions/reference/security/secure-use | 確認済み |
| 2 | OIDC の `sub` クレームが不変 ID 入り形式に移行: 例 `repo:octocat@123456/my-repo@456789:ref:refs/heads/main`。2026-07-15 以降の新規リポジトリ・リネーム/移管されたリポジトリでは既定。既存リポジトリはオプトイン。 | https://github.blog/changelog/2026-04-23-immutable-subject-claims-for-github-actions-oidc-tokens , https://docs.github.com/en/actions/concepts/security/openid-connect | 確認済み |
| 3 | OIDC トークンにリポジトリのカスタムプロパティがクレームとして入る（GA、2026-04）。 | https://github.blog/changelog/2026-04-02-github-actions-early-april-2026-updates | 確認済み |
| 4 | aws-actions/configure-aws-credentials は OIDC を「recommended」とし、`permissions: id-token: write` が必要と明記。 | configure-aws-credentials v6.3.0 README（git show で確認） | 確認済み |
| 5 | セルフホストランナーは公開リポジトリでは「ほぼ絶対に使うべきでない」。private/internal でもフォークして PR を出せる人は侵害し得る。 | https://docs.github.com/en/actions/reference/security/secure-use | 確認済み |
| 6 | シークレット: 平文でワークフローに書かない／シークレットでない機微値は `::add-mask::` でマスク／JSON・XML・YAML などの構造化データをシークレットにしない／派生値（JWT、Base64 化した値など）も登録する／定期ローテーション／漏えい時はログ削除とローテーション／environment の required reviewers を検討。 | 同上 | 確認済み |
| 7 | セルフホストランナーは 2.329.0 未満だと登録・再登録不可（2026-09-29 から完全施行、GHEC）。 | https://github.blog/changelog/2026-09-28-self-hosted-runner-version-enforcement-date-has-moved | 確認済み |

---

## 2. 2025〜2026 年の変更（書き方に影響するもの）

| # | 内容 | 出典 | 判定 |
|---|---|---|---|
| 1 | **Node 20 はランナーから削除済み（2026-09-23）**。JavaScript アクションは Node 24 で動く。`ACTIONS_ALLOW_USE_UNSECURE_NODE_VERSION` のオプトアウトも廃止。保守者は `runs.using: node24` にして新リリースを出すこと。経緯: 2026-06-16 に Node 24 既定化、2026-09-23 に Node 20 削除。 | https://github.blog/changelog/2026-09-23-node-20-is-no-longer-available-in-github-actions , https://github.blog/changelog/2026-09-23-deprecation-of-node-20-on-github-actions-runners/ | 確認済み |
| 2 | ただし metadata syntax の docs は今も `runs.using` の値として `node20` と `node24` の両方を列挙している（docs 側が未更新）。`runs.using: node20` のアクションが自動で node24 で動くのか失敗するのかは changelog に明記なし。 | https://docs.github.com/en/actions/reference/workflows-and-actions/metadata-syntax | 確認済み（記述の食い違い）／挙動は未確認 |
| 3 | 最新のランナーは v2.338.1（2026-10-22）。v2.338.0 で `hashFiles()` などランナー内部の Node も 24 に。 | https://github.com/actions/runner/releases , `git ls-remote --tags https://github.com/actions/runner` | 確認済み |
| 4 | **`ubuntu-latest` は 24.04 → 26.04 へ移行中**: 2026-10-19 開始、2026-11-19 完了予定。Ubuntu 26.04（`ubuntu-26.04` / `ubuntu-26.04-arm`）は 2026-09-17 GA。 | https://github.blog/changelog/2026-09-17-ubuntu-26-generally-available-and-latest-migration , https://github.com/actions/runner-images/issues/14748 | 確認済み |
| 5 | concurrency に `queue` が追加: `single`（既定、pending は 1 件で古いものは置換）/ `max`（最大 100 件まで pending を保持）。`queue: max` と `cancel-in-progress: true` の併用は検証エラー。 | https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#concurrency , https://github.blog/changelog/2026-05-07-github-actions-concurrency-groups-now-allow-larger-queues | 確認済み |
| 6 | **`cache-mode`**（2026-09-10 GA、全プラン）: ワークフロー/ジョブレベルで `read` / `write` / `write-only` / `none`。省略時は信頼できるトリガーで `write`、低信頼トリガーで `read`。低信頼トリガーで `write` 系を明示するとキャッシュポイズニングのリスクが戻る（警告注釈が付く）。 | https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#cache-mode , https://github.blog/changelog/2026-09-10-control-github-actions-cache-access-with-cache-mode | 確認済み |
| 7 | 低信頼トリガー（`pull_request_target`, `issue_comment`, `workflow_run` など）はデフォルトブランチスコープのキャッシュに**読み取り専用**（2026-06-26）。保存は失敗するがジョブは継続し警告。 | https://github.blog/changelog/2026-06-26-read-only-actions-cache-for-untrusted-triggers | 確認済み |
| 8 | **ステップの並列実行**（2026-06-25）: `background: true` / `wait: <id>` or `[ids]` / `wait-all:` / `cancel: <id>` / `parallel: [steps]`。1 ジョブで同時 10 個まで。composite アクション内では `background` も `parallel` も使えない。`wait`/`wait-all`/`cancel` は `if` 非対応。 | https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax （`steps[*].background` 以下）, https://github.blog/changelog/2026-06-25-actions-steps-can-now-be-run-in-parallel | 確認済み |
| 9 | `schedule` に `timezone`（IANA 名）を指定可能（2026-03-19）。 | https://github.blog/changelog/2026-03-19-github-actions-late-march-2026-updates | 確認済み |
| 10 | 式関数 `case(pred1, val1, ..., default)` が追加（2026-01-29）。三項演算子代わりの `a && b \|\| c` は不要になった。 | https://docs.github.com/en/actions/reference/workflows-and-actions/expressions#case | 確認済み |
| 11 | environment に `deployment: false` を指定すると、デプロイを作らずに environment のシークレット・変数を使える（カスタム保護ルールがある環境は不可）。 | https://github.blog/changelog/2026-03-19-github-actions-late-march-2026-updates | 確認済み |
| 12 | 新しい `job` コンテキスト: `job.workflow_ref` / `job.workflow_sha` / `job.workflow_repository` / `job.workflow_file_path`（再利用ワークフロー内で定義側を指す。GHES 不可）。 | https://github.blog/changelog/2026-09-03-github-actions-early-september-2026-updates | 確認済み |
| 13 | 再実行は 1 ワークフロー実行あたり最大 50 回（2026-04-10）。 | https://docs.github.com/en/actions/reference/limits , https://github.blog/changelog/2026-04-10-actions-workflows-are-limited-to-50-reruns | 確認済み |
| 14 | アーティファクト: upload-artifact v7 で `archive: false`（非 zip、単一ファイル向け）。download-artifact v8 が必要。v4 以降、同名アーティファクトは不変（`overwrite: true` で置換）、隠しファイルは既定で除外（`include-hidden-files`）、1 ジョブ 500 個まで、既定保持 90 日。 | https://github.blog/changelog/2026-02-26-github-actions-now-supports-uploading-and-downloading-non-zipped-artifacts , upload-artifact v7.0.2 README（git show で確認） | 確認済み |
| 15 | 新しい環境ファイル `GITHUB_ARTIFACTS`（ファイルや OCI 参照をワークフローアーティファクトとして宣言、1 ジョブ 500 件、1 ステップ 1MiB）。 | https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands | 確認済み |
| 16 | キャッシュ: 既定 10GB/リポジトリ、超過は従量課金で拡張可（2025-11-20）。7 日アクセスなしで削除。アップロード 200/分、ダウンロード 1500/分、削除 400/分のレート制限。 | https://github.blog/changelog/2025-11-20-github-actions-cache-size-can-now-exceed-10-gb-per-repository , https://docs.github.com/en/actions/reference/limits | 確認済み |
| 17 | `set-output` / `save-state` の stdout コマンドは 2022 年に非推奨、2023-07 に削除延期。現行 docs は `$GITHUB_OUTPUT` / `$GITHUB_STATE` のみを記載し、旧コマンドの記述自体がない。完全無効化の告知は見つからず。 | https://github.blog/changelog/2023-07-24-github-actions-update-on-save-state-and-set-output-commands/ , https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands | 確認済み（docs に旧コマンドなし）／無効化状況は未確認 |
| 18 | macOS 14 イメージは 2026-11-02 に廃止（10 月中ブラウンアウトあり）。 | https://github.blog/changelog/2026-10-01-github-actions-macos-14-runner-image-retirement | 確認済み |
| 19 | ワークフロー実行一覧 API は 1 クエリ 1,000 件上限、2,500 件超は件数が「2,500+」表示（2026-09-25）。 | https://github.blog/changelog/2026-09-25-changes-to-query-results-in-the-github-actions-api-and-ui | 確認済み |
| 20 | `merge_group`: マージキューで必須チェックを使うなら `merge_group` トリガーを追加しないとチェックが報告されずマージが失敗する。activity type は `checks_requested` のみ。 | https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#merge_group | 確認済み |

---

## 3. ワークフロー構文リファレンスの事実

すべて https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax （以下「syntax」）ほか、本文を取得して原文を確認した。

| # | 内容 | 出典 | 判定 |
|---|---|---|---|
| 1 | Linux/macOS で `shell` 未指定 → `bash -e {0}`（bash がなければ `sh -e {0}`）。`shell: bash` を明示 → `bash --noprofile --norc -eo pipefail {0}`。つまり **pipefail は明示時のみ**。 | syntax `defaults.run.shell` | 確認済み |
| 2 | `defaults.run` は `shell` と `working-directory` を指定でき、ワークフロー/ジョブレベル。**コンテキストや式は使えない**。より具体的な（ジョブの）設定が優先。 | syntax `defaults.run` | 確認済み |
| 3 | `concurrency.group` で使えるコンテキストは `github` / `inputs` / `vars` のみ。`cancel-in-progress` は式も可（例 `${{ !contains(github.ref, 'release/') }}`）。グループ名は大文字小文字を区別しない。ワークフロー間で衝突しないよう `${{ github.workflow }}-${{ github.ref }}` を推奨例として掲載。 | syntax `concurrency` | 確認済み |
| 4 | `jobs.<job_id>.timeout-minutes` 既定 **360**。`steps[*].timeout-minutes` は最大 360、正の整数のみ（小数不可）。ubuntu-slim（1 vCPU）はジョブタイムアウト 15 分。 | syntax / https://docs.github.com/en/actions/reference/runners/github-hosted-runners | 確認済み |
| 5 | `<job_id>` は英字か `_` で始まり、英数字・`-`・`_` のみ。プロパティ参照構文（`a.b`）も同じ規則なので、ハイフン入り ID を `needs.build-app.outputs.x` / `steps.my-step.outputs.x` で参照できる。それ以外は index 構文 `github['sha']`。 | syntax `jobs.<job_id>` / https://docs.github.com/en/actions/reference/workflows-and-actions/contexts | 確認済み |
| 6 | ステータス関数: `success()`（既定で暗黙適用）/ `always()`（キャンセル時も実行。チェックアウト等の重要処理には使わず `${{ !cancelled() }}` を推奨と明記）/ `cancelled()` / `failure()`（依存チェーンの祖先ジョブ失敗でも true）。`failure()` に条件を足す場合も `failure()` を必ず含める。`!` で始まる式は `${{ }}` で囲む必要がある。 | https://docs.github.com/en/actions/reference/workflows-and-actions/expressions#status-check-functions , syntax `jobs.<job_id>.if` | 確認済み |
| 7 | `needs.<job_id>.result` の値: `success` / `failure` / `cancelled` / `skipped`。`steps.<id>.outcome` は continue-on-error 適用前、`conclusion` は適用後。 | contexts | 確認済み |
| 8 | 再利用ワークフロー: 最大 10 階層（呼び出し元 + 9 段）、1 ワークフローファイルから最大 50 個のユニークな再利用ワークフロー（ネスト含む）。呼び出し元の `env` は伝播しない。`with` で使える式コンテキストは `github` と `needs`。 | https://docs.github.com/en/actions/reference/workflows-and-actions/reusing-workflow-configurations , https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows | 確認済み |
| 9 | `secrets: inherit` は呼び出し元がアクセスできる組織/リポジトリ/環境シークレットをすべて渡す。同一組織内、または同一エンタープライズ内の組織間で使用可。ネスト時は直接呼ぶ先にだけ渡る。`cache-mode` も呼び出し側から伝播し、呼ばれた側は呼び出し側の上限を超えられない。 | syntax `jobs.<job_id>.secrets.inherit` / reuse-workflows | 確認済み |
| 10 | composite アクションの `runs.steps[*].shell` は「`run` を使うなら必須」。 | https://docs.github.com/en/actions/reference/workflows-and-actions/metadata-syntax | 確認済み |
| 11 | `$GITHUB_OUTPUT` / `$GITHUB_ENV` の複数行は `{name}<<{delimiter}` 〜 `{delimiter}`。区切り文字が値の中の単独行に現れてはならず、値が任意なら「この形式を使わずファイルに書け」と警告。例は bash で `EOF`、pwsh で `(New-Guid).Guid`。 | https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands | 確認済み |
| 12 | `$GITHUB_STEP_SUMMARY` は**ステップごとに最大 1MiB**（超過でそのステップのアップロード失敗・エラー注釈。ステップ/ジョブの結果には影響しない）。1 ジョブで表示されるステップサマリは最大 20。シークレットは自動マスク。 | 同上 | 確認済み |
| 13 | `schedule`: 既定 UTC（`timezone` 指定可）、最短間隔 5 分、デフォルトブランチの最新コミットで実行。**毎時 0 分前後は高負荷で遅延し、ジョブが破棄されることもある**ので別の分を選ぶこと。公開リポジトリは 60 日活動がないと自動無効化。 | https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule | 確認済み |
| 14 | ワークフローファイルは 500KB 超だと実行されない。マトリクスは 1 ラン 256 ジョブまで。ワークフロー実行は最大 35 日。 | https://docs.github.com/en/actions/reference/limits | 確認済み |

---

## 4. REST API（タイミングデータ・PR コメント）

| # | 内容 | 出典 | 判定 |
|---|---|---|---|
| 1 | `GET /repos/{owner}/{repo}/actions/runs/{run_id}/jobs`（`filter=latest`（既定）/`all`、`per_page` 最大 100・既定 30、`page`）と `GET /repos/{owner}/{repo}/actions/runs/{run_id}/attempts/{attempt_number}/jobs`（`filter` なし）。レスポンスは `total_count` と `jobs[]`。 | https://docs.github.com/en/rest/actions/workflow-jobs | 確認済み |
| 2 | `jobs[]` の主なフィールド: `id`, `run_id`, `run_attempt`, `head_sha`, `html_url`(nullable), `status`（`queued`/`in_progress`/`completed`/`waiting`/`requested`/`pending`）, `conclusion`（`success`/`failure`/`neutral`/`cancelled`/`skipped`/`timed_out`/`action_required`/null）, `created_at`, `started_at`, `completed_at`(nullable), `name`, `labels[]`, `runner_id`/`runner_name`/`runner_group_id`/`runner_group_name`(nullable), `workflow_name`, `head_branch`。 | 同上 | 確認済み |
| 3 | `steps[]`: `name`, `status`（`queued`/`in_progress`/`completed`）, `conclusion`(nullable), `number`, `started_at`(nullable), `completed_at`(nullable)。実行中ジョブは `completed_at` が null になり得る。 | 同上 | 確認済み |
| 4 | 権限: GitHub App（＝GITHUB_TOKEN）と fine-grained PAT で「Actions」リポジトリ権限 **read**。つまりワークフローでは `permissions: actions: read`。private リポジトリでは classic PAT/OAuth は `repo` スコープが必要。 | https://docs.github.com/en/rest/authentication/permissions-required-for-github-apps , https://docs.github.com/en/rest/authentication/permissions-required-for-fine-grained-personal-access-tokens | 確認済み |
| 5 | docs の REST 例は `X-GitHub-Api-Version: 2026-03-10` を標準ヘッダとして記載。 | https://docs.github.com/en/rest/actions/workflow-jobs | 確認済み |
| 6 | GITHUB_TOKEN の REST レート制限は 1 リポジトリあたり 1,000 リクエスト/時（Enterprise Cloud のリソースは 15,000）。 | https://docs.github.com/en/actions/reference/limits | 確認済み |
| 7 | PR コメントは Issues API を使う（「すべての PR は issue」）。一覧 `GET /repos/{owner}/{repo}/issues/{issue_number}/comments`（`per_page` 最大 100）、作成 `POST .../issues/{issue_number}/comments`、更新 `PATCH /repos/{owner}/{repo}/issues/comments/{comment_id}`。作成を短時間に繰り返すと secondary rate limit の対象。 | https://docs.github.com/en/rest/issues/comments | 確認済み |
| 8 | 作成・更新エンドポイントは権限表の「Issues」(write) と「Pull requests」(write) の**両方に掲載**され、「追加権限」列に ✓（＝複数権限が必要、または集合のいずれか 1 つで可）。PR へのコメントなら `pull-requests: write`、Issue へのコメントなら `issues: write` で足りるという運用が一般的。 | https://docs.github.com/en/rest/authentication/permissions-required-for-github-apps | 掲載は確認済み／「どちらか一方で可」の厳密な条件は未確認 |
| 9 | フォークからの `pull_request` では GITHUB_TOKEN 以外のシークレットは渡らず、GITHUB_TOKEN は読み取り専用（`permissions` で write は付与できない。管理者が「Send write tokens to workflows from pull requests」を有効にした場合を除く）。Dependabot の PR も同様に読み取り専用でシークレットなし。一方 `pull_request_target` はフォークからでも read/write。 | https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows , syntax `permissions` | 確認済み |

→ ルール化への含意: フォーク PR にコメントを書く場合、`pull_request` のジョブでは書けない。`pull_request` で結果をアーティファクト化し、`workflow_run` 側（特権）でコメントする分離パターンが公式推奨の方向（secure-use の「特権分離には `workflow_run`」）。ただし `workflow_run` 側ではアーティファクトを信頼できない入力として扱うこと。

---

## 5. Dependabot（github-actions）

| # | 内容 | 出典 | 判定 |
|---|---|---|---|
| 1 | 必須キー: `version: 2`, `updates[].package-ecosystem: "github-actions"`, `directory` または `directories`, `schedule.interval`（`daily`/`weekly`/`monthly`/`quarterly`/`semiannually`/`yearly`/`cron`）。 | https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference | 確認済み |
| 2 | GitHub Actions では `directory: "/"` を使う。`/.github/workflows` とルートの `action.yml`/`action.yaml` を探索する。`directories` はリスト指定でグロブ（`*`）対応、`directory` は非対応。 | 同上 | 確認済み |
| 3 | サブディレクトリの composite アクション（例 `.github/actions/*/action.yml`）を `directories` グロブで対象にできるか | 同上（明記なし） | 未確認 |
| 4 | `cooldown` のキー: `default-days`, `semver-major-days`, `semver-minor-days`, `semver-patch-days`, `include`（最大 150、`*` 可）, `exclude`（最大 150、`*` 可、include より優先）。**GitHub Actions は `default-days` のみ対応で semver 別日数は非対応**。version updates のみ対象（security updates には効かない）。 | 同上 | 確認済み |
| 5 | **既定クールダウン 3 日**: `cooldown` 未設定でも、新バージョンはリリースから 3 日経つまで version update の対象にならない（2026-07-14 から既定）。security updates は即時。 | 同上 , https://github.blog/changelog/2026-07-14-dependabot-version-updates-introduce-default-package-cooldown | 確認済み |
| 6 | `groups.<IDENTIFIER>`: `applies-to`（`version-updates`/`security-updates`）, `patterns`, `exclude-patterns`, `update-types`（`major`/`minor`/`patch`）, `group-by: dependency-name`（複数ディレクトリ横断）。識別子は英字で始まり英字で終わる。 | 同上 | 確認済み |
| 7 | **SHA ピン + 同一行コメント**: `actions/checkout@<commit> #<tag or link>` の形式なら、Dependabot は SHA とともにコメントのバージョン表記も更新する。タグに紐づかないコミットを使っていると最新コミット（最新リリースとは限らない）に更新される。ローカル参照（`./...`）と `docker://` は対象外。 | https://docs.github.com/en/code-security/reference/supply-chain-security/supported-ecosystems-and-repositories#github-actions | 確認済み |
| 8 | Secure use reference: Dependabot は「SHA にピン留めしたアクションにはアラートを作らない」。 | https://docs.github.com/en/actions/reference/security/secure-use | 確認済み |
| 9 | ロックファイルとの関係: Dependabot はワークフローをオンボードしないが、オンボード済みワークフローの version update PR でロックファイルの該当エントリも再生成する。ロックファイル作成前に Dependabot を有効化するのが推奨。 | https://docs.github.com/en/actions/how-tos/secure-your-work/lock-workflow-dependencies | 確認済み |

---

## 6. キャッシュ

| # | 内容 | 出典 | 判定 |
|---|---|---|---|
| 1 | 復元の探索順: 現在のブランチ → デフォルトブランチ（PR の場合はベースブランチ、フォークのベースブランチ含む）。子ブランチ・兄弟ブランチのキャッシュは復元できない。 | https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching | 確認済み |
| 2 | **PR で作ったキャッシュは `refs/pull/.../merge` スコープ**で、その PR の再実行からしか復元できない（ベースブランチや他 PR からは不可）。 | 同上 | 確認済み |
| 3 | デフォルトブランチスコープに書き込めるトリガーは `push`, `workflow_dispatch`, `repository_dispatch`, `delete`, `registry_package`, `page_build`, `schedule` のみ。それ以外（`pull_request_target`, `issue_comment`, `workflow_run` 等）は読み取り専用。低信頼ワークフローでは `actions/cache/restore` を使うと意図が明確で警告も出ない。 | 同上 | 確認済み |
| 4 | キャッシュに機微情報を入れない（PR を開ける人はベースブランチのキャッシュを読める）。キャッシュ内容は署名も検証もされない。 | 同上 | 確認済み |
| 5 | `actions/setup-python` v7.1.0: `cache: pip \| pipenv \| poetry` と `cache-dependency-path`（uv はなし）。 | setup-python v7.1.0 action.yml（git show） | 確認済み |
| 6 | `actions/setup-node` v7.1.0: `cache: npm \| yarn \| pnpm`、`package-manager-cache`（既定 true。`package.json` の `packageManager` / `devEngines.packageManager` が npm なら自動キャッシュ）。README は「特権を持つワークフローでは `package-manager-cache: false` を推奨」。v7 でダミー `NODE_AUTH_TOKEN` フォールバックを削除。 | setup-node v7.1.0 action.yml / README（git show） | 確認済み |
| 7 | `actions/setup-go` v7.0.0: `cache`（既定 true）、`cache-dependency-path`。v6 以降、モジュールキャッシュのキーは既定で `go.mod` 基準（`go.sum` にしたい場合は `cache-dependency-path`）。 | setup-go v7.0.0 action.yml / README（git show） | 確認済み |
| 8 | `astral-sh/setup-uv` v10.3.2: `enable-cache` 既定 `"auto"`＝GitHub ホストランナーで有効、ただし **release・タグ push・`pull_request_target`・`workflow_run` では無効**。`cache-dependency-glob` でキー対象を制御。 | setup-uv v10.3.2 action.yml（git show） | 確認済み |
| 9 | `actions/cache` v5 以降は node24・ランナー 2.327.1 以上が必要。キャッシュサービス v2 へ移行済み（2025-02-01 から順次、旧サービスは同日終了）。 | actions/cache v6.1.0 README（git show） | 確認済み |

---

## 7. 主要アクションの最新安定タグと SHA

取得方法: `git ls-remote --tags https://github.com/<owner>/<repo>` で `vX.Y.Z` 形式の最大値を選び（プレリリース除外）、注釈付きタグは `^{}` のピール済み SHA を採用。日付と `runs.using` は `git fetch --depth=1` 後に `git log` / `git show <tag>:action.yml` で取得。**日付はタグ付けされたコミットのコミット日時**（軽量タグはタグ作成日時を git から取れないため）。

| アクション | 最新タグ | ピン留め用コミット SHA | タグ種別 | コミット日時 | runs.using |
|---|---|---|---|---|---|
| actions/checkout | v7.0.1 | `3d3c42e5aac5ba805825da76410c181273ba90b1` | 軽量 | 2026-07-17 | node24 |
| actions/setup-python | v7.1.0 | `6d4fd22b20465ccc0f7354476588e8df7c9ca0e0` | 軽量 | 2026-10-21 | node24 |
| actions/setup-node | v7.1.0 | `949feb2413d6458794dcd2491c4babbbce0c15c1` | 軽量 | 2026-10-07 | node24 |
| actions/setup-go（参考） | v7.0.0 | `b7ad1dad31e06c5925ef5d2fc7ad053ef454303e` | 軽量 | 2026-07-15 | node24 |
| actions/cache | v6.1.0 | `55cc8345863c7cc4c66a329aec7e433d2d1c52a9` | 軽量 | 2026-06-23 | node24 |
| actions/upload-artifact | v7.0.2 | `cf430e030ddbb5b0abf93d22962f4752f3646cd9` | 軽量 | 2026-10-07 | node24 |
| actions/download-artifact | v8.0.2 | `9000827ccba6bdab643e8b6fd33ac0654aef8333` | 軽量 | 2026-10-07 | node24 |
| actions/github-script | v9.0.0 | `3a2844b7e9c422d3c10d287c895573f7108da1b3`（タグオブジェクトは `d746ffe35508b1917358783b479e04febd2b8f71`） | 注釈付き（tagger 日時 2026-04-09） | 2026-04-09 | node24 |
| actions/attest-build-provenance | v4.2.2 | `4d101475d8b20a2381f78447822ac1eab6504dd8` | 軽量 | 2026-08-06 | composite（内部で `actions/attest@508db95dd578ae2727ebd6217d5ba78e4fbda05d # v4.2.1`） |
| astral-sh/setup-uv | v10.3.2 | `07a047e608db84b3d8c06cd9a7c7dcc9c355c18e` | 軽量 | 2026-10-22 | node24 |
| aws-actions/configure-aws-credentials | v6.3.0 | `e1253824e5c10ff9df46874f81ed3ec929e19cfd` | 軽量（`v6` は注釈付きで同コミットを指す） | 2026-09-15 | node24 |
| docker/setup-buildx-action | v4.4.1 | `f87e5991a6d7451dcb8d9637bfbc97413f497069` | 軽量 | 2026-09-16 | node24 |
| docker/build-push-action | v7.4.0 | `c3c9e263c25d99ce0380d002d59b67737d91b0dc` | 軽量 | 2026-09-15 | node24 |
| docker/login-action | v4.6.0 | `dbcb813823bdd20940b903addbd779551569679f` | 軽量 | 2026-07-29 | node24 |

判定: 上表はすべて **確認済み**（コマンド出力）。補足:

- actions/* と docker/*、aws-actions は浮動メジャータグ（`v7` など）が存在し、最新パッチと同じコミットを指している。
- **astral-sh/setup-uv は v8 以降、`v8`/`v9`/`v10` のような浮動メジャー・マイナータグを作っていない**（ls-remote で確認）。README の使用例も SHA ピン + `# v10.3.1` コメント形式。
- setup-python v7.1.0（10/21）と setup-uv v10.3.2（10/22）は公開から 3 日未満。Dependabot の既定クールダウン（3 日）の期間内なので、Dependabot 経由ではまだ提案されない可能性がある。
- 各メジャーの主な変更点（README で確認）: checkout v6 は `persist-credentials` の資格情報を `.git/config` ではなく `$RUNNER_TEMP` 配下の別ファイルに保存、v7 はフォーク PR チェックアウト拒否（§1-4）。setup-python/setup-node/setup-go の v7 は内部の ESM 化のみ（入出力は不変）。github-script v9 は `@actions/github` v9 へ更新。
- 注意: docs のサンプルコードは古いバージョン（例 `actions/checkout@v6`, `actions/cache@v4`）のままのものがある。規約のバージョン基準は docs の例ではなく上表を使うこと。

---

## 8. GitHub ホストランナーイメージ

| # | 内容 | 出典 | 判定 |
|---|---|---|---|
| 1 | runner-images README（2026-10-23 取得）の表記: `ubuntu-latest` は **Ubuntu 24.04** の行に記載。docs の runs-on 表も `ubuntu-latest` を Ubuntu2404 の readme へリンク。ただし 2026-10-19〜11-19 に 26.04 へ段階移行中なので、**今日のジョブがどちらに当たるかは不定**。 | https://github.com/actions/runner-images （README）, https://github.com/actions/runner-images/issues/14748 | 確認済み |
| 2 | Ubuntu 26.04 は 2026-09-17 に **GA**（public preview を経て）。ラベル `ubuntu-26.04` / `ubuntu-26.04-arm`。 | https://github.com/actions/runner-images/issues/14747 , changelog 2026-09-17 | 確認済み |
| 3 | Ubuntu 22.04 は 9/17 から非推奨化開始、4/17 に完全サポート終了（README の告知。年の表記はないが、文脈から 2026-09 開始・2027-04 終了と読める）。 | runner-images README の Announcements | 確認済み（年は推定） |
| 4 | プリインストールの python3: Ubuntu 24.04 は **Python 3.12.3**、Ubuntu 26.04 は **Python 3.14.4**、ubuntu-slim は 3.12.3。toolcache には 3.10〜3.14 系（3.10.22 / 3.11.17 / 3.12.15 / 3.13.16 / 3.14.8）。 | https://github.com/actions/runner-images/blob/main/images/ubuntu/Ubuntu2404-Readme.md , .../Ubuntu2604-Readme.md , .../ubuntu-slim/ubuntu-slim-Readme.md | 確認済み |
| 5 | `gh`・`jq`・`git` はプリインストール: 24.04 = GitHub CLI 2.102.0 / jq 1.7 / Git 2.55.0、26.04 = GitHub CLI 2.102.0 / jq 1.8.1 / Git 2.55.0、ubuntu-slim = GitHub CLI 2.103.0 / jq 1.7 / Git 2.43.0。Node.js は 24.04 が 22.23.3、26.04 が 24.21.0。 | 同上 | 確認済み |
| 6 | 現行ラベル一覧（docs の公開リポジトリ向け表）: `ubuntu-slim`, `ubuntu-latest`, `ubuntu-26.04`, `ubuntu-24.04`, `ubuntu-22.04`, `ubuntu-26.04-arm`, `ubuntu-24.04-arm`, `ubuntu-22.04-arm`, `windows-latest`, `windows-2025`, `windows-2025-vs2026`, `windows-2022`, `windows-11-arm`, `windows-11-vs2026-arm`, `macos-latest`, `macos-26`, `macos-15`, `macos-14`, `macos-26-intel`, `macos-15-intel`, `xcode-27`。 | https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#standard-github-hosted-runners-for-public-repositories | 確認済み |
| 7 | `windows-latest` = Windows Server 2025（VS2026）、`macos-latest` = macOS 26 arm64。macOS 14 は deprecated で 2026-11-02 廃止。 | runner-images README / changelog 2026-10-01 | 確認済み |
| 8 | `ubuntu-slim` は VM ではなくコンテナで動く 1 vCPU ランナー。非特権のため Docker-in-Docker などは不可、ジョブタイムアウト 15 分。2026-01-22 GA。 | https://docs.github.com/en/actions/reference/runners/github-hosted-runners , https://github.blog/changelog/2026-01-22-1-vcpu-linux-runner-now-generally-available-in-github-actions | 確認済み |
| 9 | arm64 標準ランナーは private リポジトリでも利用可能（2026-01-29）。 | https://github.blog/changelog/2026-01-29-arm64-standard-runners-are-now-available-in-private-repositories | 確認済み（タイトルのみ） |
| 10 | runner-images の方針: `-latest` は GA 済みの最新 OS を指し、移動前に告知する。 | runner-images README | 確認済み |

→ ルール化への含意: 移行期間中は `ubuntu-latest` の中身が実行ごとに変わり得る（Python 3.12 ↔ 3.14、Node 22 ↔ 24、jq 1.7 ↔ 1.8）。再現性を規約で担保するなら `runs-on: ubuntu-24.04` または `ubuntu-26.04` を明示し、Python は setup-python / setup-uv で固定するのが安全。

---

## 9. 資料間の食い違い・要注意点（まとめ）

1. `pull_request_target` 既定ブロックの強制開始日: docs「2026-11-02」と changelog「2026-12-02（10/21 更新）」で不一致（§1-4 #6）。
2. metadata syntax docs は `runs.using: node20` を今も列挙しているが、changelog では Node 20 はランナーから削除済み（§2 #1, #2）。
3. docs のサンプルにある古いアクションバージョン（`checkout@v6`, `cache@v4`, setup-go README の `@v6`）。
4. ロックファイルは public preview（仕様変更あり得る）。厳格ルールに組み込む場合、「ロックファイル採用」か「フル SHA ピン + 同一行 `# vX.Y.Z` コメント + Dependabot」かを明示的に選ぶ必要がある。公式の優先順位はロックファイル > フル SHA > タグ。
5. 権限スコープ `models` は現行 docs の一覧にない。
6. Immutable actions（GHCR 配布）の 2026 年時点の状況は未確認。
