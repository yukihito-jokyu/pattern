# go-cli 収束テストの記録

独立エージェント（この基盤の作成時の会話履歴を持たないセッション）に同じ課題を解かせ、書き方の違い（揺れ）を測った記録である。手順の詳細は、作成に使ったスキルの convergence-test.md にある。各ラウンドの生データは `.foundation/convergence/round-<R>/` にある。

## 条件

| 項目 | 値 |
|---|---|
| 実行方法 | `claude -p`（`--permission-mode acceptEdits`、`--allowedTools` は `Skill`・`Bash(make *)`・`Bash(go *)`・`Bash(git diff *)`・`Bash(git status *)`、`--no-session-persistence`）。各エージェントは基盤のコピーで起動し、コピーの `CLAUDE.md`・`.claude/skills`・hooks を読む。起動した利用者の `~/.claude/CLAUDE.md`（日本語で答える、など）も読み込まれる。CLI の業務データは `GOCLI_DATA_DIR` で一時ディレクトリに向けた |
| エージェントの人数 | 課題ごとに3人 |
| 課題 | `.foundation/convergence/tasks.json`（T1-add：タスクの削除、T2-change：期限の項目、T3-cross：タイトルの上限を環境変数で変える、H1-holdout：メモの名詞） |
| 合格基準 | 全員の出力が `make check` を通る。files が 1.0、names が 0.8 以上。保護ファイルの変更なし。残った揺れがすべて R7 |

## ラウンドの一覧

| ラウンド | 課題 | files | names | content | check | R1〜R6 の未対処 |
|---|---|---|---|---|---|---|
| 1 | T1-add | 1.000 | 1.000 | 0.984 | 全員通過 | 0（2件を対処） |
| 1 | T2-change | 1.000 | 0.469 | 0.960 | 全員通過 | 0（8件を対処） |
| 1 | T3-cross | 1.000 | 0.484 | 0.939 | 全員通過 | 0（9件を対処） |
| 2 | T1-add | 1.000 | 1.000 | 1.000 | 全員通過 | 0 |
| 2 | T2-change | 1.000 | 0.867 | 0.996 | 全員通過 | 0（2件を対処） |
| 2 | T3-cross | 1.000 | 1.000 | 1.000 | 全員通過 | 0 |
| 3 | T1-add | 1.000 | 1.000 | 1.000 | 全員通過 | 0 |
| 3 | T2-change | 1.000 | 1.000 | 1.000 | 全員通過 | 0 |
| 3 | T3-cross | 1.000 | 1.000 | 1.000 | 全員通過 | 0 |
| 3 | H1-holdout | 1.000 | 0.941 | 0.997 | 全員通過 | 0（1件を対処、1件を R7） |

## ラウンド 1

9セッション、1セッションあたり 113〜198 秒、合計 10.8 USD。全員が `make check` を通し、保護ファイルを変えたエージェントはいなかった。作るファイルの集合（files）は全課題で一致した。一方で names は T2・T3 で 0.5 を下回った。揺れの中身は、テストの件の名前・値・並び、宣言の説明の言い回し、`config.go` の書き方で、どれも「ルールが何も言っていない」点だった。

### 揺れと分類

| # | 課題 | 揺れ | 分類 | 対処 |
|---|---|---|---|---|
| 1 | T1-add | 全員が足した表に無い件 `reports_a_removed_task_as_missing` を、成功の件の次に置くか表の最後に置くか | R1 | TEST-05 を新設。件の並びを「成功 → `--json` → 終了コード順」に決め、archcheck の TEST-05 で検査。表に無い件を足さないことも決めた |
| 2 | T1-add | `Remove` の説明の言い回し（`returns the task as it was before removal` と `returns it as it was before the removal`） | R1 | CODE-10 を新設し、`Get`・`Remove` の説明の文を決めた |
| 3 | T2-change | 日付のテストの値（`2026-11-01`、`2026-10-31`、`2026-03-04`） | R1 | TEST-05 の「テストの値」の表（日付は `2026-01-31`） |
| 4 | T2-change | 不正な期限の件の名前（`rejects_an_invalid_due_date`、`rejects_a_due_date_that_is_not_a_date`、`rejects_a_due_date_in_another_format`）と値（`2026/11/01`、`tomorrow`） | R1 | TEST-05 の「足す件」の表（`rejects_an_invalid_<flag>`、値 `2026/01/31`） |
| 5 | T2-change | `TestParseDue` の件の集合と名前（時刻付きの件の有無、空文字列の件を `accepts_` と `returns_` のどちらで名付けるか） | R1 | TEST-05 の「値の種類ごとの件」の表 |
| 6 | T2-change | `time.Time` の比べ方（`!=` と `Equal`）。TEST-02 は `!=` と書いていたが、2人が `Equal` を使い、検査も通った | R3 | TEST-02 を「`time.Time` は `Equal`」に直し、revive の `time-equal` で検査（probe TEST-02-c） |
| 7 | T2-change | 一覧の期限の件の置き場、`--json` の件を新しく足すか既存の `writes_json` の setup を変えるか | R1 | TEST-05（`lists_<noun>s_with_<field>` と `writes_json_with_<field>` を足し、既存の件は期待値だけを直す） |
| 8 | T2-change | `view.go` の列のメソッド名（`due` と `dueDate`） | R1 | NAM-03 に「列の見出しの lowerCamelCase」を足し、archcheck で見出しとの対応を検査（probe NAM-03-c） |
| 9 | T2-change | `ParseDue` と `due` の説明の言い回し（`at 00:00 UTC`、`at midnight UTC`、`in YYYY-MM-DD form`） | R1 | CODE-10 の表（`Parse<Field>`、列のメソッド）。archcheck が書くべき文を出す（probe CODE-10-a、CODE-10-b） |
| 10 | T2-change | テストの `args` の順（`--due` を位置引数の前に書く人がいた） | R1 | TEST-05（位置引数 → フラグ → `--json`）。レビュー用スキルで確認 |
| 11 | T3-cross | `config.go` の形（設定ごとに `loadDataDir`・`loadTitleMax` に分けた2人と、`loadConfig` に直接書いた1人） | R5 | 見本の `config.go` を `loadDataDir` に分けた形に直し、OPS-02・NAM-03 で `env<Name>`・`default<Name>`・`load<Name>`・`config` のフィールドの対応と、`loadConfig` の呼び出し順を archcheck で検査（probe NAM-03-d、OPS-02-c） |
| 12 | T3-cross | 不正な値のエラー文で、環境変数名を `%s` と定数で書くか文字列で書くか | R2 | 実装用スキルの既定値表を `fmt.Errorf("%w: %s must be <条件>: %q", errkind.ErrInvalid, env<Name>, value)` に直し、patterns.md に全文を載せた |
| 13 | T3-cross | 件の名前（`title_max`、`title_limit`、`configured_limit`） | R1 | TEST-05（環境変数の件の名前は環境変数名から作る） |
| 14 | T3-cross | 数でない値（`ten`、`abc`） | R1 | TEST-05（`one`） |
| 15 | T3-cross | 既定値の件（`rejects_a_title_longer_than_100_characters_by_default`）を足すか | R1 | TEST-05（表に無い件を足さない） |
| 16 | T3-cross | `defaultTitleMax` に説明を書くか、`loadTitleMax` の説明の言い回し | R1 | CODE-08 を「非公開の宣言にも説明を書く」に広げ（godoclint `require-doc` の対象を非公開に広げた。probe CODE-08-c）、CODE-10 で文を決めた |
| 17 | T3-cross | 環境変数の件を `rejects_a_missing_title` の前と後のどちらに置くか | R1 | TEST-05 の並び（同じ種類の件の最後に足す） |
| 18 | T3-cross | `NewService` の説明の折り返し位置 | R1 | CODE-08 に「1行に1文、文の途中で改行しない」を足し、archcheck で検査（probe CODE-08-d） |
| 19 | T3-cross | `loadConfig` の変数名（`dir` と `dataDir`） | R5 | 見本の `loadConfig` が `dataDir` を使う形になった（11 の対処） |

### このラウンドで基盤に加えた変更

- ルール：CODE-08 を広げ、CODE-10・TEST-05 を新設し、NAM-03・OPS-02・TEST-02 を書き直した
- 検査：archcheck に CODE-08（1文1行）、CODE-10（説明の文）、NAM-03（列のメソッドと見出し、`config.go` の名前）、OPS-02（`loadConfig` の形）、TEST-05（件の並び）を足した。golangci-lint は godoclint の対象を非公開の宣言に広げ、revive の `time-equal` を有効にした
- probe：CODE-08-c、CODE-08-d、CODE-10-a、CODE-10-b、NAM-03-c、NAM-03-d、OPS-02-c、TEST-02-c、TEST-05-a、TEST-05-b を足した（65 件から 75 件）
- 見本：全部の宣言に説明を付け、コメントを1文1行にし、`config.go` を `loadDataDir` に分け、`list_test.go` の件の名前を TEST-05 の形（`lists_tasks`、`lists_tasks_with_all`）にした
- スキル：patterns.md の 1・2・3・4・7 節に、足す件の表と、`ParseDue`・`due`・`loadConfig`・`loadTitleMax` のコードを載せた。実装用スキルの既定値表とチェックリスト、レビュー用スキルの表に TEST-05 を足した。AGENTS.md の「守ること」に TEST-05、CODE-08・CODE-10、OPS-02・NAM-03 を足した
- 確かめ方：変えた後に、T3 の答えを patterns.md のとおりに一時コピーで書き、`make check` が通ることを確かめた

## ラウンド 2

9セッション、1セッションあたり 87〜226 秒、合計 10.2 USD。前のラウンドの答えが見えないように、各コピーから `docs/design/convergence-report.md`（この記録）を除いて実行した。全課題で合格基準を満たした。T1-add と T3-cross は、3人の出力が全ファイルで1文字も違わなかった。T2-change に残った違いは次の2件である。

| # | 課題 | 揺れ | 分類 | 対処 |
|---|---|---|---|---|
| 1 | T2-change | `--due` の説明（`Due date in YYYY-MM-DD format` と `Set the due date in YYYY-MM-DD format`） | R6 | 実装用スキルの既定値表に「項目を指定するフラグの説明」を足し、patterns.md の 2 節に `fs.StringVar(&opts.due, "due", "", "Due date in YYYY-MM-DD format")` を載せた |
| 2 | T2-change | `taskstore_test.go` の長い JSON の文字列を分けるか、どこで分けるか | R5 | patterns.md の 3 節に、`created_at` の前で分けた例を載せた |

## ラウンド 3（最終）

実装は12セッション（ホールドアウトを含む）、1セッションあたり 109〜248 秒、合計 15.8 USD。ラウンド 2 と同じく、各コピーから `docs/design/convergence-report.md` を除いて実行した。T1〜T3 は、3人の出力が全ファイルで1文字も違わなかった。

ホールドアウトの H1-holdout（`note` の名詞を足す）は、このラウンドで初めて解かせた課題である。3人とも同じ12個のファイル（domain の4つ、adapter の2つ、command の6つ）を作り、`app.go`・`cli_test.go`・`docs/cli.md` を変えた。残った違いは次の2件である。

| # | 課題 | 揺れ | 分類 | 対処 |
|---|---|---|---|---|
| 1 | H1-holdout | エンティティの型の説明（`Note is a piece of text to be kept.`、`... to remember.`、`... to be remembered.`） | R7 | 受け入れた。名詞の意味を英語で説明する文はこの1つだけで、依頼の業務の意味から書く。CODE-10 の表で文を決めると、名詞の意味の説明が消える。保守には影響しない |
| 2 | H1-holdout | `cli_test.go` の `rejects_an_unknown_command` の値。見本が存在しない名詞の例に `note` を使っていたため、`note` を足すと書き換えが要り、`unknown`（2人）と `project`（1人）に分かれた | R1 | TEST-05 の「テストの値」の表に「存在しない名詞・動詞」（名詞は `unknown`、動詞は `delete`）を足し、見本の値を `unknown` にした。最終ラウンドの後の対処なので、収束テストでは測り直していない。`make check`、probe、`rules_check.py` が通ることだけを確かめた |

揺れではないが、3人とも `cli_test.go` の `--help` の名詞の一覧に `note  Manage notes` を足していた。テストが落ちて気づいたもので、文書のどこにも書いていなかった。そこで、`architecture.md` の変更シナリオ表と、実装用スキルの patterns.md の4節に足した。

## レビュー検出率

最終ラウンドで、`.foundation/convergence/review-seeds.json` の12件の違反を1つの未コミットの差分にまとめ、3人に「未コミットの変更をレビューして」とだけ頼んだ（3セッション、76〜103 秒、合計 2.2 USD）。仕込んだのは、rules.md で強制に `review` を含む12個のルール（STR-05、DEP-06、CODE-02、ERR-04、STATE-01、OPS-06、TEST-01、TEST-04、TEST-05、PROC-02、PROC-06、TOOL-03）の違反を1件ずつである。TOOL-03 には抜け道（`.golangci.yml` の `funlen` の緩和）を、PROC-02 にはファイルをまたぐ対応の破れ（`errkind` に足した種類が `exit.go` に無い）を使った。

| エージェント | 検出率 | 見逃し | 余計なルールID | 判定 |
|---|---|---|---|---|
| review/agent-1 | 1.000 | なし | NAM-04、PROC-04 | 差し戻し |
| review/agent-2 | 1.000 | なし | NAM-04、PROC-04 | 差し戻し |
| review/agent-3 | 1.000 | なし | NAM-04、PROC-04 | 差し戻し |

検出したルールIDの集合は3人で一致した。「余計なルールID」の2つは、仕込んだ差分が実際に破っているルールで、誤った指摘ではない。NAM-04 は、CODE-02-a の `Rename` が決まった動詞（項目を変えるのは `update`）に無いことを指摘したものである。PROC-04 は、TOOL-03-a の `.golangci.yml` の変更が ADR から始まっていないことを指摘したものである。

3人とも、ルールに無い点として次の3つを提案した。どれも採用していない。

- 保護ファイルの変更を `make check` でも止める（いまは hooks の確認とレビューだけが止める）
- STATE-01 のデータファイルの名前を archcheck で確かめる
- サブコマンドから呼ばれない Service の公開メソッドを止める

採用しなかったのは、最終ラウンドの後にルールを足すと、そのルールを収束テストで測れないからである。足すかどうかの判断は利用者に委ねる。

## 結論

3ラウンドで、全課題（ホールドアウトを含む）が合格基準を満たした。

- ラウンド 1：作るファイルの集合は全員で一致した。一方で、テストの件、説明の言い回し、`config.go` の形が揺れ、names は 0.469〜1.000 だった
- ラウンド 2：その揺れを TEST-05・CODE-10 などのルールと検査で止めた結果、names は 0.867〜1.000 になった
- ラウンド 3：T1〜T3 は3人の出力が1文字も違わなかった。初めて見せたホールドアウトでも files 1.000、names 0.941 だった。レビューの検出率は3人とも 100% で、検出したルールIDの集合も一致した

残った揺れは2件である。1件はラウンド 3 の後に TEST-05 で対処し、もう1件は R7 として受け入れた。R1〜R6 の未対処は0件である。
