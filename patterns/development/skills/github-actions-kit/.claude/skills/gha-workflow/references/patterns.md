# パターン

実装用スキル `gha-workflow` の「1.2 型」の表の各行に対応する手順である。節の番号は表と一致させる。見本のパスは `.claude/skills/gha-workflow/references/examples/` からの相対パスである。

## 1. PR の検証（ci.yml）

- 使う場面：PR の検証、CI、テスト・lint・ビルドを PR で回す、ci.yml にジョブを足す
- 見本：`workflows/ci.yml`（全体の形と report ジョブ）、`workflows/reusable-check.yml` の `jobs`（検証のジョブの形）
- 作る・変えるファイル：

  | 順 | パス | 見本との対応 | 守るルール |
  |---|---|---|---|
  | 1 | `.github/workflows/ci.yml` | `workflows/ci.yml` | STR-02、ASYNC-01、OPS-01、OPS-06 |
  | 2 | `.github/workflows/reusable-<名前>.yml`（同じジョブを `ci.yml` 以外からも呼ぶときだけ） | `workflows/reusable-check.yml` | STR-03、DEP-02 |
  | 3 | `.github/dependabot.yml`（まだ無いときだけ） | `dependabot.yml` | PROC-03 |

- 手順：
  1. `ci.yml` が無ければ見本の `workflows/ci.yml` を写し、1行目のコメントをこのリポジトリの検証の目的に書き換える。`on:` は `pull_request`（値を書かない）と `push.branches` に既定のブランチ1つ（STR-02）
  2. 検証のジョブは `ci.yml` の `jobs` に直接書く。形は `workflows/reusable-check.yml` の `lint` ジョブを写す：`runs-on: ubuntu-24.04`、`timeout-minutes: 10`、`permissions` に `contents: read`、最初のステップは `Check out repository`（`persist-credentials: false`）
  3. ジョブ ID を NAM-03 の表で決める（`lint`、`typecheck`、`test`、`build`）。ジョブの中は、ランタイムの setup（CODE-04）→ 依存の導入 → 検査のコマンドの順に、コマンド1つを1ステップにする。ステップ名は NAM-04 の動詞で始める（`Run unit tests`、`Check formatting`）
  4. 見本の `check` ジョブ（再利用ワークフローの呼び出し）は、同じジョブを `release.yml` などからも呼ぶときだけ使う。`ci.yml` だけで使うジョブを再利用ワークフローにしない（STR-03）
  5. report ジョブを最後に置き、`needs` に report 以外の全ジョブの ID をアルファベット順に書く（6節、OPS-01、PROC-02）
  6. `.github/dependabot.yml` が無ければ見本を写す（PROC-03）
- この場面で間違えやすいこと：
  - lint とテストを別々のワークフロー（`lint.yml`、`test.yml`）にする。PR の検証は全部 `ci.yml` に書く（STR-02）
  - `pull_request` に `paths` や `branches` を書く。必須チェックが待機のまま残る（STR-02）
  - ジョブを足したのに report の `needs` に足さない（PROC-02）
  - 見本の `check` ジョブをそのまま写し、使われ方が1か所だけの再利用ワークフローを作る

## 2. タグからのリリース（release.yml）

- 使う場面：タグからのリリース、Release の作成、パッケージの公開
- 見本：`workflows/release.yml`
- 作る・変えるファイル：

  | 順 | パス | 見本との対応 | 守るルール |
  |---|---|---|---|
  | 1 | `.github/workflows/release.yml` | `workflows/release.yml` | STR-02、STR-05、STATE-02、DEP-04、OPS-06 |

- 手順：
  1. 見本を写す。`on: push: tags: - v*`、`concurrency` は `${{ github.workflow }}` と `false`（ASYNC-01）
  2. 検証が要るなら、`ci.yml` と同じジョブを再利用ワークフローに切り出して `check` ジョブで呼ぶ（STR-03）。キャッシュを切る入力を渡す（STATE-02）
  3. `build` ジョブ：`contents: read` で成果物を作り、`actions/upload-artifact` で渡す（`if-no-files-found: error`、`retention-days: 1`）
  4. `publish` ジョブ：`needs: - build`、`environment: release`（STR-05）。権限は OPS-06 の表で、Release を作るなら `contents: write`、来歴の証明を付けるなら `attestations: write` と `id-token: write`
  5. `actions/download-artifact` → `actions/attest-build-provenance` → `gh release create "$REF_NAME" <ファイル> --repo "$REPOSITORY" --verify-tag --generate-notes` の順にする。値は `env:` で渡す（ERR-02、NAM-05）
  6. パッケージのレジストリに公開するなら、レジストリの CLI（`uv publish`、`npm publish` など）を `id-token: write` の OIDC（trusted publishing）で動かし、トークンを secrets に置かない（OPS-02）。レジストリ側の設定を報告の5に書く
- この場面で間違えやすいこと：
  - Release を作るのに外部アクション（`softprops/action-gh-release` など）を使う。`gh` で書く（DEP-04）
  - `publish` ジョブに `environment` を付けない（STR-05）
  - setup-go・setup-node・setup-uv のキャッシュを切らない（STATE-02）
  - ワークフローの `permissions` に `contents: write` を書く。ジョブに書く（OPS-06）

## 3. デプロイ（deploy-<先>.yml）

- 使う場面：デプロイ、GitHub Pages、クラウドへの反映
- 見本：`workflows/deploy-pages.yml`
- 作る・変えるファイル：

  | 順 | パス | 見本との対応 | 守るルール |
  |---|---|---|---|
  | 1 | `.github/workflows/deploy-<先>.yml`（`<先>` は `pages`、`production` など kebab-case） | `workflows/deploy-pages.yml` | STR-02、STR-05、OPS-02、OPS-06、STATE-02 |

- 手順：
  1. 見本を写す。`on:` は `push.branches` に既定のブランチと `workflow_dispatch`（STR-02）。`concurrency` は `${{ github.workflow }}` と `false`
  2. `build` ジョブ（`contents: read`）で成果物を作る。Pages なら `actions/upload-pages-artifact`、それ以外は `actions/upload-artifact`（STATE-02）
  3. `deploy` ジョブ：`needs: - build`、`environment` に STR-05 の表の名前（Pages は `github-pages` と `url: ${{ steps.deployment.outputs.page_url }}`）、権限は OPS-06 の表
  4. クラウドへの認証は、`id-token: write` と各社の公式の OIDC のアクションで行う（OPS-02）。公式のアクション（`aws-actions/configure-aws-credentials` など）は許可表に無いので、使う前にユーザーの承認を求める（DEP-04）。IAM ロールなどクラウド側の設定を報告の5に書く
- この場面で間違えやすいこと：
  - アクセスキーを secrets に置いて認証する（OPS-02）
  - `deploy` ジョブに `environment` を付けない（STR-05）
  - `cancel-in-progress: true` にして、途中のデプロイを止める（ASYNC-01）

## 4. 定期・手動の保守（<目的>.yml）

- 使う場面：定期実行、cron、手動で動かす保守（監査、掃除、同期）
- 見本：`workflows/security-audit.yml`
- 作る・変えるファイル：

  | 順 | パス | 見本との対応 | 守るルール |
  |---|---|---|---|
  | 1 | `.github/workflows/<目的>.yml`（`<目的>` は英語の kebab-case。`stale-issues`、`sync-labels` など） | `workflows/security-audit.yml` | STR-02、OPS-04、OPS-06、NAM-03 |

- 手順：
  1. 見本を写す。`on:` は `schedule` と `workflow_dispatch` の両方（STR-02）
  2. cron の分は `1`〜`59`、`timezone` を書く（OPS-04。既定はスキルの2節）
  3. ジョブ ID は NAM-03 の表で決める（監査・保守は `audit`、ほかは役割の名詞）
  4. Issue や PR を操作するなら `gh` で書き、権限は OPS-06 の表で足す（`issues: write` など）。`contents: write` などの書き込みが要るなら `environment` も付ける（STR-05）
- この場面で間違えやすいこと：
  - cron を `0 0 * * *` にし、`timezone` を書かない（OPS-04）
  - `workflow_dispatch` を書かず、手で試せない（STR-02）
  - cron の文字列を引用する（`"17 9 * * 1"`）。引用しない（TOOL-01）

## 5. 共有（composite アクション、再利用ワークフロー）

- 使う場面：同じステップやジョブを共有する、composite アクション、再利用ワークフロー
- 見本：`actions/setup-kit/action.yml`（composite）、`workflows/reusable-check.yml`（再利用ワークフロー）
- 作る・変えるファイル：

  | 順 | パス | 見本との対応 | 守るルール |
  |---|---|---|---|
  | 1 | `.github/actions/<名前>/action.yml` か `.github/workflows/reusable-<名前>.yml` | 上の見本 | STR-03、DEP-01、DEP-02、NAM-02 |
  | 2 | 呼ぶ側のワークフロー（全部） | `workflows/reusable-check.yml` の `Install kit dependencies`、`workflows/ci.yml` の `check` | PROC-02、OPS-02 |

- 手順：
  1. STR-03 の表で切り出す先を決める。ステップの並びなら composite、ジョブなら再利用ワークフロー
  2. composite：1行目のコメント、`name` はディレクトリ名、`description`、`inputs`（`description`、`required`、`required: false` なら `default`）、`runs.using: composite`。`run` のステップには `shell: bash` を書き、入力は `env:` で渡す（ERR-01、ERR-02）。composite からローカルのアクションを呼ばない（DEP-01）
  3. 再利用ワークフロー：1行目は `# 呼ばれると、<成果>`（CODE-03）。`on: workflow_call` だけ、入力に `type` も書く（DEP-02）。`permissions: {}`、`defaults` を書き、`concurrency` は書かない（ASYNC-01）
  4. 呼ぶ側：composite は `uses: ./.github/actions/<名前>`、再利用ワークフローはジョブの `uses: ./.github/workflows/reusable-<名前>.yml`。呼ぶジョブにも `permissions` を書き、呼ぶ先が要る権限を全部含める（OPS-06）。secrets は名前を挙げて渡す（`secrets: inherit` は書かない。OPS-02）
- この場面で間違えやすいこと：
  - YAML のアンカー（`&`、`*`）で共有する（STR-03）
  - 1か所でしか使わないものを切り出す（STR-03）
  - 入力の名前を変えたのに、呼ぶ側の `with:` を直さない（PROC-02）
  - 呼ぶ側を足したときに、再利用ワークフローの1行目に呼び出し元を書き足す。1行目に呼び出し元を書かない（CODE-03）

## 6. 処理時間の報告と必須チェック（report ジョブ）

- 使う場面：PR に各ジョブ・各ステップの処理時間を出す、必須チェックを1つにまとめる
- 見本：`workflows/ci.yml` の `report` ジョブ
- 作る・変えるファイル：

  | 順 | パス | 見本との対応 | 守るルール |
  |---|---|---|---|
  | 1 | `.github/actions/run-report/`（`install.py` が入れる。手で書かない） | — | OPS-01 |
  | 2 | `.github/workflows/ci.yml` の `report` ジョブ | `workflows/ci.yml` の `report` | OPS-01、PROC-02、ASYNC-02 |

- 手順：
  1. `.github/actions/run-report/action.yml` が無ければ、書かずに `install.py` を回すよう報告する
  2. 見本の `report` ジョブを、`ci.yml` の最後にそのまま写す（`if: ${{ !cancelled() }}`、`timeout-minutes: 5`、権限3つ、ステップ2つ）
  3. `needs` を report 以外の全ジョブの ID にし、アルファベット順に並べる（PROC-02）
  4. 報告の5に「ブランチ保護（またはルールセット）の必須チェックを `report` の1つにする」と書く
- この場面で間違えやすいこと：
  - `if: ${{ always() }}` にする。取り消した実行でも動いてしまう（OPS-01）
  - `ci.yml` 以外のワークフローに report ジョブを置く（OPS-01）
  - 各ジョブの最後に時間を出すステップを足す。report ジョブ1つにまとめる（ADR 0008）

## 7. 外部アクションの版を上げる（Dependabot と gha pin）

- 使う場面：外部アクションの版を上げる、SHA で固定する、Dependabot
- 見本：`dependabot.yml`
- 作る・変えるファイル：

  | 順 | パス | 見本との対応 | 守るルール |
  |---|---|---|---|
  | 1 | `.github/dependabot.yml` | `dependabot.yml` | PROC-03 |
  | 2 | `uses:` の行を持つワークフローと composite アクション | — | DEP-06 |

- 手順：
  1. `dependabot.yml` が無いか形が違えば、見本の `github-actions` の項目を写す（PROC-03）
  2. 手で上げるときは `gha pin <owner/repo>`（版を指定するなら `<owner/repo>@vX.Y.Z`）を回し、出力の `uses:` の行で置き換える
  3. メジャー版が変わるなら、そのアクションの Release のページで入力の変更を確かめ、報告の8に書く
  4. `gha pin --verify` で、全部の SHA がコメントのタグと一致することを確かめる
- この場面で間違えやすいこと：
  - SHA を記憶やほかのリポジトリから写す（DEP-06）
  - `@v7` のタグで参照する（DEP-06）
  - SHA を変えたのに `# vX.Y.Z` のコメントを変えない（`gha pin --verify` が落とす）

## 8. 保守的更新

- 使う場面：モードが保守的更新（1〜7 の該当する節と一緒に使う）
- 見本：対象のファイル自身（新しく足す行の形は1〜7の節の見本）
- 作る・変えるファイル：

  | 順 | パス | 見本との対応 | 守るルール |
  |---|---|---|---|
  | 1 | 依頼の対象のファイル | 足す行だけ1〜7の節の見本 | PROC-07 |
  | 2 | PROC-02 の表で一緒に変えるファイル | — | PROC-02 |

- 手順：
  1. 依頼に要る行を決める。既存の行は、ID、名前、キーの順、コメント、引用の書き方を含めて変えない。1行目のコメントは、トリガーか成果（公開する物と先、検査の合否）が変わるときだけ書き直す。前段に検査のジョブを足すだけなら変えない（CODE-03）
  2. 足す行はルールどおりに書く。既存の行の書き方に合わせない（例：既存が `ubuntu-latest` でも、足すジョブは `ubuntu-24.04`）
  3. `gha check --ratchet HEAD <パス>` で、増えた組を0件にする
  4. 既存の行の違反は直さずに、`gha check <パス>` の出力から報告の7に「提案」として書く
- この場面で間違えやすいこと：
  - ついでに既存の全ステップに `name` を足す、版を上げる、整形し直す（PROC-07）
  - 検査のジョブを前段に足しただけなのに、1行目に「検査を回してから」と書き足す（CODE-03、PROC-07）
  - このキット自身で、`docs/design/` の説明を書き足す。参照実装のジョブやステップを変えるだけなら変えない（KIT-06）
  - 足す行を既存の古い書き方に合わせ、ratchet で落ちる

## 9. 破壊的更新

- 使う場面：モードが破壊的更新（1〜7 の該当する節と一緒に使う）
- 見本：1〜7 の該当する節の見本
- 作る・変えるファイル：

  | 順 | パス | 見本との対応 | 守るルール |
  |---|---|---|---|
  | 1 | STR-02 の表で決まる新しいファイル | 1〜7 の該当する節の見本 | PROC-08、全節 |
  | 2 | 古いファイル（名前が変わるなら消す） | — | PROC-08 |

- 手順：
  1. `gha intent <古いパス>` で棚卸しの表を出し、「意図」の列を埋めてユーザーに確かめる
  2. 古いファイルの目的を STR-02 の表に当て、新しいファイル名を決める（PR で動く `test.yml` は `ci.yml` のジョブ、`deploy.yml` は `deploy-<先>.yml`）
  3. 1〜7 の該当する節の手順で書き直す。古いファイルが禁止の書き方をしていたら、次の表で置き換える

     | 古い書き方 | 置き換え |
     |---|---|
     | `pull_request_target` | `pull_request`（フォークの PR では書き込めなくなることを対応表に書く） |
     | `workflow_run` | 同じワークフローの `needs` か、`workflow_call` |
     | `$GITHUB_ENV` | `$GITHUB_OUTPUT` と `steps.<ID>.outputs` |
     | secrets の長期の鍵でクラウドに認証 | OIDC（クラウド側の設定を報告の5に書く） |
     | `pull_request.paths` の絞り込み | 絞り込みを外す（動く回数が増えることを対応表に書く） |
     | `continue-on-error: true` | 外す。失敗してよい理由が依頼にあれば、そのステップを消すかをユーザーに聞く |

  4. `gha intent <新しいパス> --compare-ref HEAD`（名前が変わったら `--from <古いパス>`）の全行を、報告の7の対応表に「移した先」か「落とした理由」で書く
  5. `gha check` を0件にする
- この場面で間違えやすいこと：
  - 通知やコメントのステップを黙って落とす（PROC-08）
  - 新しいファイルを作ったのに古いファイルを残し、同じ処理が2回動く
  - トリガーの意味が変わる置き換え（上の表）を、対応表に書かない
