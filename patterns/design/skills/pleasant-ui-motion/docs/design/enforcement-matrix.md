<!-- このファイルは rules_check.py が rules.md と probes.json から生成する。手で編集しない。 -->

# 強制の対応表

ルールごとに、どの仕組みで守らせているかを示す。段の強さは type > format > lint・structure・test > generator > review > doc の順である。
probe が実際に検査で落ちるかの結果は `.foundation/probe-results.json` にある（`violation_probe.py` が書く）。

## 集計（各ルールの最も強い段で数える）

| 段 | 件数 |
|---|---|
| type | 0 |
| format | 1 |
| lint | 0 |
| structure | 10 |
| test | 5 |
| generator | 0 |
| review | 5 |
| doc | 0 |

## ルールごとの対応

| ルールID | 題名 | 強制 | 仕組み | probe |
|---|---|---|---|---|
| STR-01 | 仕様の単位は`motions/<id>/`の`motion.json`・`motion.css`・`motion.md`の3ファイルに固定し、新規単位は`new`で作る | structure, generator | motion.mjs units/scaffold | STR-01-a |
| DEP-01 | 1仕様の`system`は`cobalt`か`new-york`の一方とし、`compile`は選んだprofileからだけTokenを解決する | structure | validate/compileの閉じたprofile選択 | DEP-01-a |
| DEP-02 | 取り込み先の既存部品・Motion機構を再利用し、動きを足す目的で依存ライブラリーを追加しない | review | 依存差分と対象の既存APIを照合 | — |
| NAM-01 | 識別子は英字始まりの`kebab-case`に固定し、`motion.json`の`id`とディレクトリ名を一致させる | structure | validate/unitsのid検査 | NAM-01-a |
| CODE-01 | 仕様はJSONオブジェクトで書き、`recipe`は`press/save/selection/disclosure/reorder/step/notify/navigation`のいずれかに固定する | structure | validateのrecipe検査 | CODE-01-a |
| CODE-02 | `motion.css`と`motion.md`は`render`の出力と一致させ、生成物を直接編集しない | structure, generator | checkとbuildの再生成比較 | CODE-02-a |
| ERR-01 | 仕様は`id/system/recipe/intent/frequency/delight/labels`だけを持ち、型・必須キー・列挙値の違反は非0で終了させる | structure | validateの閉じたschema | ERR-01-a |
| STATE-01 | 保存は入力時に`pending`を示し、実際の成功・失敗で状態を更新し、処理中の重複送信を防ぎ、演出の完了から成功を決めない | test, review | createSaveの単体/ブラウザーテストと対象の業務処理照合 | STATE-01-a |
| ASYNC-01 | 選択位置の目標変更はcancel前に表示中の位置を保存して次の始点にし、古い完了処理が最新状態を書き戻すことを防ぐ | test | createIndicatorのブラウザーテスト | ASYNC-01-a |
| OPS-01 | 生成文書へ渡す入力文字列はHTML・表・コード記号をエスケープし、入力値・処理状態を演出停止で消さない | test | render/createSaveとブラウザーの状態保持検査 | OPS-01-a |
| TEST-01 | 仕様検査、参照ブラウザー検査、取り込み先の型・操作検査、人間の快適さの確認を区別して報告する | review | 実行対象・コマンド・観測・未確認範囲を報告と照合 | — |
| PROC-01 | 仕様・生成物・携帯用ルールを同時更新し、基盤ルール変更は理由をADRへ書いて検査・probe・見本・スキルをそろえる | structure, review | portable rulesの同期検査と波及レビュー | PROC-01-a |
| TOOL-01 | 仕様は2空白インデントと末尾改行のJSONへ整形し、固定版の依存と`npm run check`で検査する | format | fmt/checkのcanonical比較 | TOOL-01-a |
| TOOL-02 | 検査を通すための保護ファイル変更、抑止コメント、テストのskip/onlyを使わない | structure, review | guard.py、保護ファイルdiff、hook | TOOL-02-a |
| MOT-01 | 各recipeが定める全状態に異なる非空ラベルを定義し、動き以外でも状態と結果を伝える | structure, review | validateのlabels検査と実UIの意味伝達レビュー | MOT-01-a |
| MOT-02 | 時間と曲線は対象の正本Tokenを参照し、固定値への置換や別システムのTokenを混ぜない | review | 実ファイルのCSS/WAAPIとprofilesの出典を照合。auditで調査時点からのToken差分を確認 | — |
| MOT-03 | OSのReduced Motionを最優先し、途中のOFFで再生を止めて論理的な目標へ確定し、ON復帰だけで登場・完了を再演しない | test, review | resolveMotionとブラウザーの途中変更検査、Portalは対象で確認 | MOT-03-a |
| MOT-04 | 遊び心を有効にする仕様は`save/notify`かつ`frequency=infrequent`だけとし、確定済みの成功に一度だけ重ねる | structure, review | validateのdelight条件と実UIの再演レビュー | MOT-04-a |
| MOT-05 | 開閉の動きを保ち、途中反転・次の操作・フォーカスを演出完了で待たせない | test, review | 往復の中間状態、途中反転、別操作の受付、フォーカスをChromiumで確認 | MOT-05-a、MOT-05-b |
| MOT-06 | 動きの方向・対象の同一性・処理結果を実際の操作目的と照合し、根拠のない移動は追加しない | review | intent、実画面、実際の状態変化を一緒に追う | — |
| MOT-07 | 入力応答と継続時間を別に観測し、実測値と設計値、rAF callback間隔と画面提示、位置連続と速度連続を区別する | review | 計測条件・trace・主張の範囲を確認 | — |

## 機械で縛っていないルール

| ルールID | 題名 | 強制 | 機械化しない理由 |
|---|---|---|---|
| DEP-02 | 取り込み先の既存部品・Motion機構を再利用し、動きを足す目的で依存ライブラリーを追加しない | review | 導入済み部品の役割と依頼範囲は対象アプリごとに異なる。 |
| TEST-01 | 仕様検査、参照ブラウザー検査、取り込み先の型・操作検査、人間の快適さの確認を区別して報告する | review | 未観測の感覚や外部アプリの検証状況はJSONから判定できない。 |
| MOT-02 | 時間と曲線は対象の正本Tokenを参照し、固定値への置換や別システムのTokenを混ぜない | review | 任意のホスト言語・CSS構成全体に対してToken使用を保証する検査は提供しない。 |
| MOT-06 | 動きの方向・対象の同一性・処理結果を実際の操作目的と照合し、根拠のない移動は追加しない | review | 対象の同一性とユーザーの理解は語句の存在だけでは判定できない。 |
| MOT-07 | 入力応答と継続時間を別に観測し、実測値と設計値、rAF callback間隔と画面提示、位置連続と速度連続を区別する | review | 実際のpaint・機器差・利用者の感じ方はこの仕様検査から測定できない。 |

## 対象外とした軸

| 軸 | 理由 |
|---|---|
