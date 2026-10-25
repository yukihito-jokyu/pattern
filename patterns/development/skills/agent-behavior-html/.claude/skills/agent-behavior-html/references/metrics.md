# 指標と根拠

分析対象は有効なv1/v2イベント。event_idが重複した場合は最初の1件を採り、除いた件数をqualityへ残す。途中で切れた行、未知version、余分なキー、型の違う行は不正行とする。無効な本文はJSONにもHTMLにも転記しない。

| 指標 | 定義 | 読むときの制約 |
|---|---|---|
| events | 有効かつ重複でないイベント数 | 取り逃したイベントは含まれない |
| sessions | sourceとsession_idの組数 | 製品をまたいで同じIDを合流しない |
| calls | IDのあるツールイベントの対応キー数 | IDなしイベントは別に集計 |
| matched | 前後が各1件でツール名が一致、時刻が逆転していない呼び出し | 前後の時刻が同じ0msも有効 |
| duration_ms | 後hook受信時刻−前hook受信時刻 | hook起動・待機を含む。正味の処理時間ではない |
| p50_duration_ms | 有効な所要時間を並べた中央の下側の値 | 偶数件で平均を取らない |
| total_duration_ms | 有効な所要時間の合計 | 並行実行なら実際の経過時間を超える |
| errors / success | 構造化成否か明示失敗hookを持つ呼び出し数 | completedを混ぜない |
| error_rate | errors ÷ (errors＋success) | 分母0ならnull。欠落や不明は分母にしない |
| outcome_coverage | (errors＋success) ÷ (errors＋success＋completed) | 分母0ならnull。記録の成否確認率 |
| repeated_extra_calls | 同じ製品・セッション・ツール・入力指紋ごとのmax(0,件数−1)の合計 | 曖昧な呼び出しと開始記録なしは除く。不要な実行数とは同義でない |
| missing_start / missing_end | 前後の片方が無い呼び出し | ユーザー停止、導入前開始、異常終了でも起きる |
| ambiguous | 同じIDに複数の前/後、または異なるツール名 | 成否と時間を集計しない |
| clock_reversed | 後hook受信時刻が前より前 | 成否は使い、所要時間はnullにする |
| uncorrelated_tool_events | tool_use_idが無いツールイベント数 | 前後を推測で組み合わせない |
| purposes_recorded | purposeがある呼び出し数 | 事前申告またはツール入力の説明。正しさの評価ではない |
| purposes_missing | purposeがなく対応不明でもない呼び出し数 | v1や説明のない操作も含む |
| purposes_ambiguous | 申告候補が複数、または呼び出しの対応が曖昧な件数 | 理由を選んで埋めない |
| purpose_coverage | purposes_recorded ÷ calls | 分母0ならnull |
| unlinked_intents | 1操作に対応できなかったActionIntent数 | 期限超過・scope不一致・複数候補・未実行を含む。全体だけにある |

HTMLの上側の指標と操作カードはフィルターに従う。ログ品質の欄は全ファイルの値。イベント時系列には製品・セッション・ツールのフィルターを適用し、成否と検索は操作カードと呼び出し表に適用する。検索対象はツール・ID・操作・対象・目的・期待結果・結果抜粋。操作カードは先頭20件、呼び出し表は100件ごとのページ、時系列は先頭300イベント、繰り返しは上位20組。全件はJSONに残す。

根拠は`calls[].evidence`または`repeats[].evidence`から`events`のevent_idを引き、`locations[event_id]`のファイル番号・ファイル名・1始まりの行番号で確認する。同名ファイルを複数ディレクトリから渡した場合はファイル番号で区別する。元ディレクトリの絶対パスはレポートに保存しない。

目的は`calls[].purpose_evidence`からActionIntentへたどる。tool_descriptionの場合は開始イベントのtool_input由来の説明である。期待結果は申告、result_summaryは観測として分ける。JSON保存にも目的の根拠イベントを含める。

例えば同じBash入力が2回あり、最初がerror、次がsuccessなら「同じ入力の実行を2回観測し、後の実行は明示成功」と書ける。間にEditがあれば編集操作を観測したと言えるが、修正内容の妥当性や因果関係までは断定しない。v2の指紋はdescriptionを除くため、同じコマンドに違う目的を書いても同じ入力として比較する。
