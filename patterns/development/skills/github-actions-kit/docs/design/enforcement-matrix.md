<!-- このファイルは rules_check.py が rules.md と probes.json から生成する。手で編集しない。 -->

# 強制の対応表

ルールごとに、どの仕組みで守らせているかを示す。段の強さは type > format > lint・structure・test > generator > review > doc の順である。
probe が実際に検査で落ちるかの結果は `.foundation/probe-results.json` にある（`violation_probe.py` が書く）。

## 集計（各ルールの最も強い段で数える）

| 段 | 件数 |
|---|---|
| type | 1 |
| format | 0 |
| lint | 11 |
| structure | 30 |
| test | 1 |
| generator | 0 |
| review | 5 |
| doc | 5 |

## ルールごとの対応

| ルールID | 題名 | 強制 | 仕組み | probe |
|---|---|---|---|---|
| STR-01 | ファイルの置き場は4種類に固定する | structure | `rules_str.py` の `str01_layout`（置き場の深さとファイル名） | STR-01-a |
| STR-02 | ワークフローのファイルは目的ごとに分け、トリガーとの対応を固定する | structure | `rules_str.py` の `str02_triggers`（PR のトリガーの置き場、`reusable-*` のトリガー、`schedule` と `workflow_dispatch`、`ci.yml` の `pull_request` と `push`、表の目的の行に無いトリガー） | STR-02-a、STR-02-b、STR-02-c |
| STR-03 | 共有は2か所目で切り出し、ステップなら composite、ジョブなら再利用ワークフローにする | structure, review | `rules_str.py` の `str03_anchors`（アンカーの禁止）、レビュー用スキルの4節（差分の中で同じステップの並びが2か所にあるか） | STR-03-a |
| STR-04 | run の本文は10行までにし、超えたらスクリプトに切り出す | structure | `rules_str.py` の `str04_scripts`（`run:` の行数） | STR-04-a |
| STR-05 | デプロイと公開の書き込み権限を持つジョブには environment を付ける | structure | `rules_str.py` の `str05_environment`（書き込み権限と environment の組） | STR-05-a |
| DEP-01 | ジョブから呼ぶのは再利用ワークフロー、ステップから呼ぶのはアクションにし、入れ子にしない | structure | `rules_dep.py` の `dep01_direction` | DEP-01-a |
| DEP-02 | inputs・outputs・secrets の定義には description と required を書く | structure | `rules_dep.py` の `dep02_interface` | DEP-02-a |
| DEP-03 | ワークフロー同士は workflow_call だけでつなぐ | structure | `rules_str.py` の `str02_triggers`（禁止のトリガー） | DEP-03-a |
| DEP-04 | 外部アクションは許可表にあるものだけを使い、API の操作は gh で書く | lint | zizmor の `forbidden-uses`（`.gha/zizmor.yml` の `allow`） | DEP-04-a |
| DEP-05 | PR の検証のワークフローでは、report ジョブの PR コメントのほかに書き込まない | structure | `rules_dep.py` の `dep05_side_effects` | DEP-05-a |
| DEP-06 | 外部アクションは40桁のコミット SHA と版のコメントで固定し、SHA は gha pin で得る | lint, structure | `rules_dep.py` の `dep06_pinning`（形とコメント）、zizmor の `unpinned-uses`（`hash-pin` の方針） | DEP-06-a、DEP-06-b |
| NAM-01 | ファイル名とディレクトリ名は kebab-case にし、拡張子は .yml にする | structure | `rules_nam.py` の `nam01_files` | NAM-01-a |
| NAM-02 | ID は kebab-case、環境変数は大文字の snake_case にし、ワークフローの name はファイル名にそろえる | structure | `rules_nam.py` の `nam02_ids` | NAM-02-a |
| NAM-03 | ジョブの ID は役割の語彙表から選ぶ | review | レビュー用スキルの4節で、ジョブの中身と ID の役割が合っているかを見る | — |
| NAM-04 | ステップには必ず英語の name を付け、先頭の動詞を語彙表から選ぶ | structure | `rules_nam.py` の `nam04_steps` | NAM-04-a |
| NAM-05 | 式を環境変数に渡すときは、コンテキストを除いた残りを大文字の snake_case にした名前にする | structure | `rules_nam.py` の `nam05_env_names` | NAM-05-a |
| NAM-06 | runs-on には版を固定したランナーのラベルを書く | structure | `rules_nam.py` の `nam06_runners` | NAM-06-a |
| CODE-01 | キーの順と YAML の形を固定する | structure | `rules_code.py` の `code01_shape` | CODE-01-a、CODE-01-b |
| CODE-02 | matrix には fail-fast: false を書き、値が2つ以上の軸だけを作る | structure | `rules_code.py` の `code02_matrix` | CODE-02-a |
| CODE-03 | ファイルの1行目に目的を1文で書き、ほかのコメントは「なぜ」だけにする | structure, review | `rules_code.py` の `code03_header`（1行目の有無、表の形、ファイル名）、レビュー用スキルの4節（成果だけか、ほかのコメントの中身） | CODE-03-a、CODE-03-b、CODE-03-c、CODE-03-d |
| CODE-04 | ランタイムの版はリポジトリの版のファイルから読む | review | レビュー用スキルの4節で、版のファイルの有無と `with:` を突き合わせる | — |
| ERR-01 | シェルは bash を明示し、失敗を握りつぶさない | structure | `rules_flow.py` の `err01_shell`（shell、`continue-on-error`、`run:` の `\|\| true`・`\|\| :`・`set +e`） | ERR-01-a、ERR-01-b、ERR-01-c |
| ERR-02 | run と script には式を書かず、値はすべて env で渡す | lint, structure | `rules_flow.py` の `err02_expressions`、actionlint の `[expression]`（potentially untrusted）と zizmor の `template-injection` | ERR-02-a、ERR-02-b |
| STATE-01 | データの受け渡しの方法を、渡す範囲で決める | structure | `rules_flow.py` の `state01_env_file` | STATE-01-a |
| STATE-02 | キャッシュは setup のアクションの機能を使い、成果物には保存日数と空のときの扱いを書く | lint, structure | `rules_flow.py` の `state02_artifacts`、zizmor の `cache-poisoning` | STATE-02-a、STATE-02-b |
| ASYNC-01 | concurrency はワークフローの種類ごとに決まった値を書く | structure | `rules_flow.py` の `async01_concurrency` | ASYNC-01-a |
| ASYNC-02 | runs-on を持つジョブには timeout-minutes を書き、値は10分にする | structure | `rules_flow.py` の `async02_timeout` | ASYNC-02-a |
| OPS-01 | ci.yml の最後に report ジョブを置き、処理時間の報告と合否を任せる | structure | `rules_ops.py` の `ops01_report` | OPS-01-a |
| OPS-02 | secrets はそれを使うステップの env か with にだけ書き、クラウドは OIDC で認証する | lint, structure, review | `rules_ops.py` の `ops02_secrets`、zizmor の `secrets-inherit` と `overprovisioned-secrets`、レビュー用スキルの4節（OIDC を使えるのに鍵を使っていないか） | OPS-02-a、OPS-02-b |
| OPS-03 | 版の数値は引用して文字列にする | structure | `rules_ops.py` の `ops03_versions` | OPS-03-a |
| OPS-04 | schedule には timezone を書き、分を0にしない | structure | `rules_ops.py` の `ops04_schedule` | OPS-04-a |
| OPS-05 | zizmor の指摘を0件にし、checkout は資格情報を残さない | lint | zizmor（`artipacked`、`dangerous-triggers` ほか、regular の全監査。`self-repository` だけは ADR 0006 で止める） | OPS-05-a |
| OPS-06 | ワークフローの permissions は空にし、全ジョブに要る権限だけを書く | lint, structure, review | `rules_ops.py` の `ops06_permissions`（空のワークフローの権限、全ジョブの permissions、キーの値）、zizmor の `excessive-permissions`、レビュー用スキルの4節（表に照らして余分な権限が無いか） | OPS-06-a、OPS-06-b |
| TEST-01 | ワークフローの正しさは gha check で確かめ、GitHub 上で動かしていないことを報告する | lint, doc | actionlint と shellcheck（`gha check`。ワークフローの run と `.github/scripts/*.sh`）。報告の書き方は実装用スキルの7節 | TEST-01-a、TEST-01-b |
| PROC-01 | ワークフローは決まった順で作る | doc | 実装用スキルの4節 | — |
| PROC-02 | 一緒に変えるファイルの組を同じ変更で変える | lint, structure, review | `rules_ops.py` の `ops01_report`（report の `needs`）、actionlint の `workflow-call` と `job-needs`、レビュー用スキルの5節（secrets と environment） | PROC-02-a、PROC-02-b |
| PROC-03 | アクションの更新は Dependabot に任せ、手で上げるときは gha pin を使う | lint, structure | `rules_ops.py` の `proc03_dependabot`、zizmor の `dependabot-cooldown` | PROC-03-a、PROC-03-b |
| PROC-04 | ルールは決まった順で変える | doc | AGENTS.md の「ルールを変えたいとき」 | — |
| PROC-05 | 完了の条件はモードごとの検査で決める | doc | 実装用スキルの5節と7節 | — |
| PROC-06 | 既存のワークフローを変えるときは、保守的更新か破壊的更新かをユーザーに選んでもらう | doc | 実装用スキルの1節と2節 | — |
| PROC-07 | 保守的更新では頼まれた所だけを変え、指摘を増やさない | review | レビュー用スキルの5節で、差分が依頼の範囲に収まっているかを見る | — |
| PROC-08 | 破壊的更新では、していることを棚卸しして確かめてから書き直す | review, doc | レビュー用スキルの5節（対応表と `--compare-ref` の出力の突き合わせ）、実装用スキルの4節（手順） | — |
| TOOL-01 | YAML の整形は yamllint の設定で縛り、formatter は使わない | lint | yamllint（`gha check`） | TOOL-01-a |
| TOOL-02 | 検査は編集の直後と完了の前に回す | doc | 実装用スキルの4節と5節、`.claude/settings.json` の hooks | — |
| TOOL-03 | 抑止コメントで検査を黙らせない | structure | `rules_ops.py` の `tool03_suppressions`（配布先の `.github/` を含む）と `.foundation/bin/guard.py`（このキットの Python） | TOOL-03-a、TOOL-03-b |
| TOOL-04 | 検査の設定と保護ファイルを、検査を通すために変えない | review | レビュー用スキルの3節で、差分に保護ファイルがあるかを見る | — |
| TOOL-05 | 検査の道具の版はスクリプトの依存とロックファイルで固定する | structure | `uv run --locked`（ロックファイルと宣言が食い違うと起動しない） | TOOL-05-a |
| KIT-01 | キットのコードの置き場を固定する | structure | `scripts/structure_check.py` の `check_layout` | KIT-01-a |
| KIT-02 | モジュールの依存の向きと、外とのやりとりの場所を固定する | structure | `scripts/structure_check.py` の `check_imports` | KIT-02-a |
| KIT-03 | Python は ruff と mypy の strict で縛る | type, lint, doc | `make lint`、`make format-check`、`make typecheck`、AGENTS.md の「キットの Python を変えるとき」（関数の置き場） | KIT-03-a、KIT-03-b |
| KIT-04 | CLI の出力と終了コードを固定する | test | `tests/test_cli.py` | KIT-04-a |
| KIT-05 | モジュールごとにテストを置き、偽物は support.py に集める | structure, doc | `scripts/structure_check.py` の `check_tests`、AGENTS.md の「キットの Python を変えるとき」（テストのデータ） | KIT-05-a |
| KIT-06 | 生成物は手で編集せず、正本から作り直す | structure, doc | `make docs-check`（`scripts/gen_docs.py --check`）、`scripts/structure_check.py` の `check_versions`、AGENTS.md の「守ること」（`docs/design/` を変える条件） | KIT-06-a |

## 機械で縛っていないルール

| ルールID | 題名 | 強制 | 機械化しない理由 |
|---|---|---|---|
| NAM-03 | ジョブの ID は役割の語彙表から選ぶ | review | ジョブの役割はステップの意味から判断する必要があるため |
| CODE-04 | ランタイムの版はリポジトリの版のファイルから読む | review | どのファイルが版の正本かは、配布先のリポジトリの構成によって変わり、ワークフローの字面だけでは判定できないため |
| PROC-01 | ワークフローは決まった順で作る | doc | 作業の順は結果の差分に残らないため |
| PROC-04 | ルールは決まった順で変える | doc | 変更の順と承認の有無は差分に残らないため |
| PROC-05 | 完了の条件はモードごとの検査で決める | doc | どの検査を回したかは差分に残らないため（結果は報告に貼らせる） |
| PROC-06 | 既存のワークフローを変えるときは、保守的更新か破壊的更新かをユーザーに選んでもらう | doc | モードはユーザーの意思で決まり、ファイルからは判定できないため |
| PROC-07 | 保守的更新では頼まれた所だけを変え、指摘を増やさない | review | どの行が依頼に必要かは、依頼の意味から判断する必要があるため（指摘の増減は `gha check --ratchet` が機械で見る） |
| PROC-08 | 破壊的更新では、していることを棚卸しして確かめてから書き直す | review, doc | 事実が新しいファイルのどこに移ったか、落としてよいかは、意図の判断が要るため |
| TOOL-02 | 検査は編集の直後と完了の前に回す | doc | いつ検査を回したかは差分に残らないため |
| TOOL-04 | 検査の設定と保護ファイルを、検査を通すために変えない | review | hooks はエージェントの編集にだけ確認を求め、人の編集は止められないため、差分のレビューで確かめる |

## 対象外とした軸

| 軸 | 理由 |
|---|---|
| C5 | YAML の値には型を名前で表す慣習が無く、入力の型は `type:` で明示する（DEP-02）。キットの Python の名前は ruff の命名規則（KIT-03）で縛る |
| D5 | 対象外（宣言的に書くため。ワークフローで状態を書き換えるのは `$GITHUB_OUTPUT` だけで、STATE-01 で扱う） |
