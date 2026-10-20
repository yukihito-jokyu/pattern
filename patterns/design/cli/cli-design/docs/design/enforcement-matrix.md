<!-- このファイルは rules_check.py が rules.md と probes.json から生成する。手で編集しない。 -->

# 強制の対応表

ルールごとに、どの仕組みで守らせているかを示す。段の強さは type > format > lint・structure・test > generator > review > doc の順である。
probe が実際に検査で落ちるかの結果は `.foundation/probe-results.json` にある（`violation_probe.py` が書く）。

## 集計（各ルールの最も強い段で数える）

| 段 | 件数 |
|---|---|
| type | 0 |
| format | 2 |
| lint | 0 |
| structure | 27 |
| test | 7 |
| generator | 1 |
| review | 1 |
| doc | 6 |

## ルールごとの対応

| ルールID | 題名 | 強制 | 仕組み | probe |
|---|---|---|---|---|
| STR-01 | 1つの CLI の設計は specs/<name>/ の3種類のファイルだけで表す | structure | `tools/clispec check` の STR-01（基盤の直下、`specs/` の直下、各 CLI のディレクトリの中身を表と照合） | STR-01-a、STR-01-b、STR-01-c、STR-01-d |
| STR-02 | 新しい CLI とコマンドは生成器で始める | generator, doc | `tools/clispec new`・`tools/clispec command`・`tools/clispec field`。生成した後の形は STR-05・NAM-04・NAM-07・CODE-04・ERR-01 の structure が検査する | — |
| STR-03 | 出力の型は types に1回だけ定義し、入れ子にしない | structure | `tools/clispec check` の STR-03（未定義の型の参照、参照されない型、項目の型） | STR-03-a、STR-03-b |
| STR-04 | cli.md は生成物であり、リリース済みの仕様は変えない | structure, review | `tools/clispec gen --check`（再生成して差分が無いこと）と `tools/clispec check` の STR-04（リリース済みの仕様の名前・版・形）。リリース済みの仕様の中身の書き換えはレビュー用スキルで確かめる | STR-04-a、STR-04-b |
| STR-05 | 操作が1つならルートのコマンドだけ、2つ以上なら全コマンドを名詞と動詞の2段にする | structure | `tools/clispec check` の STR-05（`path` の長さ、1つと2つ以上の混在、名詞の形） | STR-05-a、STR-05-b |
| DEP-01 | 仕様はコマンドから型への参照だけを持ち、外を参照しない | structure | `tools/clispec check` の CODE-01 が、表に無いキーをエラーにする（`$ref` などはこの検査で落ちる）。DEP-01 は参照先の実在を検査する | DEP-01-a |
| DEP-02 | 外から見える振る舞いは全部仕様に書き、仕様に無い入口を実装に作らない | test, review | `tools/clispec conform` が、未知のオプションと前方一致の省略が終了コード2になることを確かめる。隠しオプションの有無は実装のレビューで確かめる | DEP-02-a |
| DEP-03 | 引数の書式は、全言語の標準ライブラリで同じ結果になる共通部分だけにする | structure, test | `tools/clispec check` の CODE-01（表に無いキーをエラーにする）と NAM-01（オプション名は2文字以上の kebab-case）。`tools/clispec conform` が、順序を入れ替えた入力と `--` の後ろの値を実装に与えて確かめる | DEP-03-a、DEP-03-b |
| DEP-04 | 実装の引数解析は各言語の標準ライブラリだけで行う | doc | 実装用スキルの「実装に落とすとき」の節と `references/stdlib-mapping.md` | — |
| DEP-05 | CLI が書くファイルはデータの置き場と --output の指定先だけにする | review | レビュー用スキルの確認項目（動詞と summary が書き込みを示すのに `storage` が `none` で `output` オプションも無いコマンド） | — |
| NAM-01 | 名前の形を表のとおりにする | structure | `tools/clispec check` の NAM-01 | NAM-01-a、NAM-01-b |
| NAM-02 | 役割ごとの名前を表のとおりにする | structure, review | `tools/clispec check` の NAM-02（型名、識別子の項目、`created_at`・`updated_at`、`_at`・`_date`、位置引数の名前）。CLI 名の選び方はレビュー用スキルで確かめる | NAM-02-a、NAM-02-b |
| NAM-03 | 標準の意味のオプションは標準の名前と型にし、短い名前は表からだけ導く | structure | `tools/clispec check` の NAM-03（使わない名前、暗黙のオプションの名前、表の名前の型） | NAM-03-a、NAM-03-b |
| NAM-04 | 標準の動詞は5つに決め、同じ意味の別の語を使わない | structure | `tools/clispec check` の NAM-04（使わない語、標準の動詞の位置引数と `output.kind`） | NAM-04-a、NAM-04-b |
| NAM-05 | 名前で値の種類が分かるようにする | structure | `tools/clispec check` の NAM-05 | NAM-05-a、NAM-05-b |
| NAM-06 | 名前に略語を使わない | structure | `tools/clispec check` の NAM-06 | NAM-06-a |
| NAM-07 | オプション名を項目名から機械的に作る | structure | `tools/clispec check` の NAM-07 | NAM-07-a、NAM-07-b、NAM-07-c、NAM-07-d |
| CODE-01 | 仕様の各オブジェクトはキーを全部、決まった順と並びで書く | format, structure | `tools/clispec fmt --check`（キーの順・配列の並び・字下げ）と `tools/clispec check` の CODE-01（キーの過不足） | CODE-01-a、CODE-01-b |
| CODE-02 | 値の型は決定表で選び、型ごとの制約を守る | structure, review | `tools/clispec check` の CODE-02（型の名前、使える場所、`values`・`default`・`required` の組）。値の意味に合う型かはレビュー用スキルで確かめる | CODE-02-a、CODE-02-b |
| CODE-03 | 大きさの上限を守る | structure | `tools/clispec check` の CODE-03 | CODE-03-a、CODE-03-b |
| CODE-04 | summary は英語の1文で、決まった形で書く | structure | `tools/clispec check` の CODE-04 | CODE-04-a、CODE-04-b |
| CODE-05 | 既定値・選択肢・必須は項目で表し、summary に書かない | structure | `tools/clispec check` の CODE-05 | CODE-05-a |
| ERR-01 | 終了コードは5つに決め、コマンドごとの組を決定表で決める | structure, test | `tools/clispec check` の ERR-01（`exit_codes` が決定表の組と一致すること）。`tools/clispec conform` が、実装の終了コードが宣言した組に入ることを確かめる | ERR-01-a、ERR-01-b |
| ERR-02 | エラーは stderr に `<name>: <message>` の1行で出し、stdout には何も出さない | test | `tools/clispec conform`（未知のオプション、値の形式の誤り、無い識別子に対して、stdout が空で stderr が `<name>: ` で始まる1行であること） | ERR-02-a |
| ERR-03 | 入力の誤りは、何かを行う前に決定表の終了コードで止める | test | `tools/clispec conform`（`integer`・`enum`・`date` の不正な値、必須の欠落、無い識別子） | ERR-03-a、ERR-03-b |
| STATE-01 | 設定ファイルとプロンプトを持たず、値はオプション・環境変数・既定値の順に決め、データは決まった置き場に置く | structure, review | `tools/clispec check` の STATE-01（`storage` と `<PREFIX>_DATA_DIR` の対応、環境変数とオプションの対応）。確認が要る操作に `force` があるかはレビュー用スキルで確かめる | STATE-01-a、STATE-01-b |
| STATE-02 | 標準の動詞の振る舞いを決定表のとおりにする | test | `tools/clispec conform` の STATE-02（`make conform`。見本の実装は `make check` の単体テストで確かめる）。データのファイルの形式は公開面に含めない（DEP-02）ため、「データに無い項目」の行だけは適合テストで確かめない | STATE-02-a、STATE-02-b、STATE-02-c |
| OPS-01 | 主な出力だけを stdout に書き、成功時の stderr を空にし、色と進捗を出さない | test | `tools/clispec conform`（成功した実行の stderr が空、全出力に ESC が無いこと） | OPS-01-a |
| OPS-02 | 秘密情報をオプションの値と環境変数で受け取らない | structure | `tools/clispec check` の OPS-02 | OPS-02-a、OPS-02-b |
| OPS-03 | 日時は UTC の RFC 3339、日付は YYYY-MM-DD、文面は ASCII の英語にする | structure, test | `tools/clispec check` の OPS-03（ASCII）。`tools/clispec conform` が `--json` の `timestamp`・`date` の値の形を確かめる | OPS-03-a、OPS-03-b |
| OPS-04 | 出力の種類を決定表で決め、--json とテキストの形を型から導く | structure, test | `tools/clispec check` の OPS-04（`kind` と `type` の組）。`tools/clispec conform` が、実装の `--json` の出力の形（キーの集合と型）と表の見出しを確かめる | OPS-04-a、OPS-04-b |
| OPS-05 | ヘルプは仕様から生成した文面を、版は `<name> <version>` を、stdout に出して0で終える | test | `tools/clispec conform`（全コマンドの `--help` と `-h` の stdout をリファレンスの文面と比べ、`--version` の出力を確かめる） | OPS-05-a、OPS-05-b |
| OPS-06 | CLI 名と版は全レジストリで使える形にする | structure | `tools/clispec check` の OPS-06 | OPS-06-a、OPS-06-b |
| TEST-01 | 仕様は make check で、実装は make conform で確かめる | test, doc | `tools/clispec/tests/test_conform.py` が見本の実装に適合テストをかける。実装を conform で確かめる手順は実装用スキルに書く | TEST-01-a |
| PROC-01 | 設計は決まった順に作る | doc | 実装用スキルの「作る順序」 | — |
| PROC-02 | 一緒に変えるものの組を守る | structure | `tools/clispec gen --check`（`cli.md`）、`tools/clispec check` の PROC-06（版）、NAM-02（`updated_at`）、STATE-01（環境変数） | PROC-02-a |
| PROC-03 | 検査ツールの Python と uv の版は決まった手順で上げる | doc | 実装用スキルの「版を上げる依頼」の節 | — |
| PROC-04 | ルールは ADR から順に変える | doc | AGENTS.md の「ルールを変えたいとき」 | — |
| PROC-05 | make check とチェックリストを満たしてから完了と報告する | doc | AGENTS.md の「完了の条件」と実装用スキルの「検証」「報告」 | — |
| PROC-06 | 版は差分の種類から機械で決め、リリース済みの公開面は足すだけにする | structure, review | `tools/clispec check` の PROC-06（リリース済みの最新版と比べて期待する版を計算し、一致しなければ期待値を出す）。`make fix` はパッチとマイナーの版を自動で書き、メジャーは書かない（承認と ADR が要るため）。ADR の有無はレビュー用スキルで確かめる | PROC-06-a、PROC-06-b |
| TOOL-01 | 整形は tools/clispec fmt に任せる | format | `tools/clispec fmt --check` | TOOL-01-a |
| TOOL-02 | 編集の直後は hooks、完了の前は make check を回す | doc | AGENTS.md の「コマンド」と「完了の条件」、`.claude/settings.json` | — |
| TOOL-03 | 未知のキー、抑止の書き方、保護ファイルの変更で検査を黙らせない | structure, review | `tools/clispec check` の CODE-01（未知のキー）、`.foundation/bin/guard.py`（抑止の書き方）。保護ファイルの差分はレビュー用スキルで確かめる | TOOL-03-a、TOOL-03-b |
| TOOL-04 | Python 3.14 を uv で起動し、Makefile を唯一の入口にする | structure | `make check` の先頭の `version` ターゲットが、起動した Python が 3.14 系であることを確かめる | TOOL-04-a |

## 機械で縛っていないルール

| ルールID | 題名 | 強制 | 機械化しない理由 |
|---|---|---|---|
| STR-02 | 新しい CLI とコマンドは生成器で始める | generator, doc | 生成器を使ったかどうかは、出来上がった仕様に痕跡が残らない。結果の形は別のルールの検査で縛る |
| DEP-04 | 実装の引数解析は各言語の標準ライブラリだけで行う | doc | 実装はこの基盤の外のリポジトリにあり、この基盤の検査はその依存の一覧を読めない |
| DEP-05 | CLI が書くファイルはデータの置き場と --output の指定先だけにする | review | コマンドがファイルを書くかどうかは動詞の意味で決まり、字面では判定できない |
| PROC-01 | 設計は決まった順に作る | doc | 作った順は出来上がった仕様に痕跡が残らない |
| PROC-03 | 検査ツールの Python と uv の版は決まった手順で上げる | doc | 上げる手順の順番は差分に残らない。版そのものは TOOL-04 の structure が検査する |
| PROC-04 | ルールは ADR から順に変える | doc | 変えた順番は差分に残らない |
| PROC-05 | make check とチェックリストを満たしてから完了と報告する | doc | 報告の中身は差分に残らない。check そのものは機械が回す |
| TOOL-02 | 編集の直後は hooks、完了の前は make check を回す | doc | いつ検査を回したかは差分に残らない。回した結果は `make check` で確かめる |

## 対象外とした軸

| 軸 | 理由 |
|---|---|
| A7 | 仕様は1ファイルで、入口ファイル（index・barrel・main）の仕組みが無い |
| D2 | 仕様は1ファイルで import と export が無い（外の参照の禁止は DEP-01） |
| D4 | 仕様は宣言だけで、制御フローを書かない |
| D5 | 仕様は宣言だけで、値の再代入や破壊的な操作を書かない（リリース済みの仕様を変えないことは STR-04） |
| E4 | 仕様の形式は実行の並行性を表さず、CLI の外から見える振る舞いに非同期の差が出ない |
| F2 | 作者はテストを書かない。適合テストの項目は仕様から導かれる（TEST-01） |
| F3 | 作者はテストを書かない。適合テストは実装を本物のまま外から実行し、偽物を作らない（TEST-01） |
| F4 | 作者はテストを書かない。適合テストが型から入力の値を作る（TEST-01） |
