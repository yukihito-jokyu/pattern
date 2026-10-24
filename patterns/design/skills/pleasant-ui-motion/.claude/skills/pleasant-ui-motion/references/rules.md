# pleasant-ui-motion のルール

この基盤は、気持ち良さを基本品質と遊び心に分け、既存デザインシステムへ適用する。仕様JSONの作者が触る単位と、保守者が扱うツールを分ける。携帯用の同内容は`npm run fix`でスキルへ同期する。

## 用語

| 用語 | 意味 |
|---|---|
| 仕様 | 動きの目的・システム・状態ラベルを決めるmotion.json |
| Token | 取り込み先styles/registry.jsonの共通値 |
| 検証 | 対象と観測範囲を伴う実行。感覚の保証ではない |

## 追加した軸

| 軸 | 内容 | 置く節 |
|---|---|---|
| X1 | ルートと画面遷移（本基盤では開閉・遷移） | MOT |
| X2 | スタイルとToken参照 | MOT |
| X3 | アクセシビリティの定型 | MOT |
| X4 | 動き以外の状態伝達 | MOT |
| X5 | 動きを減らす設定と優先順位 | MOT |
| X6 | 遊び心の採否 | MOT |
| X7 | アニメーションと操作の主導権 | MOT |
| X8 | 意図・連続性・方向の意味 | MOT |
| X9 | 性能と感覚の検証範囲 | MOT |

## STR 配置と構造

### STR-01 仕様の単位は`motions/<id>/`の`motion.json`・`motion.css`・`motion.md`の3ファイルに固定し、新規単位は`new`で作る

- 軸: A1〜A7
- 決定: 仕様の単位は`motions/<id>/`の`motion.json`・`motion.css`・`motion.md`の3ファイルに固定し、新規単位は`new`で作る。
- 理由: 実装者ごとの配置と開始形の違いを止め、生成物を仕様から再現する。
- 出典: docs/design/research.md、ADR 0002
- 強制: structure, generator — motion.mjs units/scaffold
- probe: STR-01-a
- 良い例:
  motions/save-preferences/motion.json
- 悪い例:
  motions/save-preferences/custom.js

## DEP 境界と依存

### DEP-01 1仕様の`system`は`cobalt`か`new-york`の一方とし、`compile`は選んだprofileからだけTokenを解決する

- 軸: B1〜B3
- 決定: 1仕様の`system`は`cobalt`か`new-york`の一方とし、`compile`は選んだprofileからだけTokenを解決する。
- 理由: 同一アプリへ2システムを混ぜたり、存在しないAPIを流用することを防ぐ。
- 出典: docs/design/research.md、ADR 0002
- 強制: structure — validate/compileの閉じたprofile選択
- probe: DEP-01-a
- 良い例:
  "system": "cobalt"
- 悪い例:
  "system": "both"

### DEP-02 取り込み先の既存部品・Motion機構を再利用し、動きを足す目的で依存ライブラリーを追加しない

- 軸: B4〜B6
- 決定: 取り込み先の既存部品・Motion機構を再利用し、動きを足す目的で依存ライブラリーを追加しない。
- 理由: 本パターンは既存デザインシステムへの適用を対象とし、別エンジンとの二重管理を作らない。
- 出典: docs/design/research.md、ADR 0002
- 強制: review — 依存差分と対象の既存APIを照合
- 機械化しない理由: 導入済み部品の役割と依頼範囲は対象アプリごとに異なる。
- probe: なし
- 良い例:
  既存useDesignMotionを使う
- 悪い例:
  既存Motionを別ライブラリーへ置換

## NAM 命名

### NAM-01 識別子は英字始まりの`kebab-case`に固定し、`motion.json`の`id`とディレクトリ名を一致させる

- 軸: C1〜C7
- 決定: 識別子は英字始まりの`kebab-case`に固定し、`motion.json`の`id`とディレクトリ名を一致させる。
- 理由: 生成先と参照先の揺れ、パストラバーサルを止める。
- 出典: docs/design/research.md、ADR 0002
- 強制: structure — validate/unitsのid検査
- probe: NAM-01-a
- 良い例:
  "id": "save-preferences"
- 悪い例:
  "id": "../save"

## CODE 書き方

### CODE-01 仕様はJSONオブジェクトで書き、`recipe`は`press/save/selection/disclosure/reorder/step/notify/navigation`のいずれかに固定する

- 軸: D1〜D7
- 決定: 仕様はJSONオブジェクトで書き、`recipe`は`press/save/selection/disclosure/reorder/step/notify/navigation`のいずれかに固定する。
- 理由: 仕様を拡張する作者が任意のコードや動きの分類を発明することを防ぐ。
- 出典: docs/design/research.md、ADR 0002
- 強制: structure — validateのrecipe検査
- probe: CODE-01-a
- 良い例:
  "recipe": "save"
- 悪い例:
  "recipe": "bounce-everything"

### CODE-02 `motion.css`と`motion.md`は`render`の出力と一致させ、生成物を直接編集しない

- 軸: A6
- 決定: `motion.css`と`motion.md`は`render`の出力と一致させ、生成物を直接編集しない。
- 理由: ラベル・Token・中断方針の説明を仕様と同期する。
- 出典: docs/design/research.md、ADR 0002
- 強制: structure, generator — checkとbuildの再生成比較
- probe: CODE-02-a
- 良い例:
  motion.jsonを変えてbuild
- 悪い例:
  motion.cssだけに300msを追加

## ERR エラーと入力検証

### ERR-01 仕様は`id/system/recipe/intent/frequency/delight/labels`だけを持ち、型・必須キー・列挙値の違反は非0で終了させる

- 軸: E1,E2
- 決定: 仕様は`id/system/recipe/intent/frequency/delight/labels`だけを持ち、型・必須キー・列挙値の違反は非0で終了させる。
- 理由: 未知キーの黙殺や時間の直接指定を防ぐ。
- 出典: docs/design/research.md、ADR 0002
- 強制: structure — validateの閉じたschema
- probe: ERR-01-a
- 良い例:
  "delight": false
- 悪い例:
  "duration": 300

## STATE 状態とデータの流れ

### STATE-01 保存は入力時に`pending`を示し、実際の成功・失敗で状態を更新し、処理中の重複送信を防ぎ、演出の完了から成功を決めない

- 軸: E3
- 決定: 保存は入力時に`pending`を示し、実際の成功・失敗で状態を更新し、処理中の重複送信を防ぎ、演出の完了から成功を決めない。
- 理由: 見た目だけの成功や二重処理を防ぎ、意図と実結果をつなぐ。
- 出典: docs/design/research.md、ADR 0002
- 強制: test, review — createSaveの単体/ブラウザーテストと対象の業務処理照合
- probe: STATE-01-a
- 良い例:
  await save()の成功後にsuccess
- 悪い例:
  animation.finishedで保存成功

## ASYNC 非同期と並行

### ASYNC-01 選択位置の目標変更はcancel前に表示中の位置を保存して次の始点にし、古い完了処理が最新状態を書き戻すことを防ぐ

- 軸: E4
- 決定: 選択位置の目標変更はcancel前に表示中の位置を保存して次の始点にし、古い完了処理が最新状態を書き戻すことを防ぐ。
- 理由: 連打の飛びと未処理rejectionを防ぐ。位置の連続は速度の連続を保証しない。
- 出典: docs/design/research.md、ADR 0002
- 強制: test — createIndicatorのブラウザーテスト
- probe: ASYNC-01-a
- 良い例:
  computed transformの文字列を保存してcancel
- 悪い例:
  cancelしてから始点を0へ戻す

## OPS 設定と表示

### OPS-01 生成文書へ渡す入力文字列はHTML・表・コード記号をエスケープし、入力値・処理状態を演出停止で消さない

- 軸: E5〜E8
- 決定: 生成文書へ渡す入力文字列はHTML・表・コード記号をエスケープし、入力値・処理状態を演出停止で消さない。
- 理由: 表示破壊と意味の消失を防ぐ。機密データは仕様へ書かない。
- 出典: docs/design/research.md、ADR 0002
- 強制: test — render/createSaveとブラウザーの状態保持検査
- probe: OPS-01-a
- 良い例:
  &lt;script&gt;として表示
- 悪い例:
  未処理のHTMLを生成文書へ埋める

## TEST 検証

### TEST-01 仕様検査、参照ブラウザー検査、取り込み先の型・操作検査、人間の快適さの確認を区別して報告する

- 軸: F1〜F5
- 決定: 仕様検査、参照ブラウザー検査、取り込み先の型・操作検査、人間の快適さの確認を区別して報告する。
- 理由: 仕様ファイルやデモの成功を利用アプリの成功へ広げない。
- 出典: docs/design/research.md、ADR 0002
- 強制: review — 実行対象・コマンド・観測・未確認範囲を報告と照合
- 機械化しない理由: 未観測の感覚や外部アプリの検証状況はJSONから判定できない。
- probe: なし
- 良い例:
  Chromiumの参照デモ成功、対象アプリ未実施
- 悪い例:
  schema成功だけで全UIが快適と断定

## PROC 作業手順

### PROC-01 仕様・生成物・携帯用ルールを同時更新し、基盤ルール変更は理由をADRへ書いて検査・probe・見本・スキルをそろえる

- 軸: G1〜G5
- 決定: 仕様・生成物・携帯用ルールを同時更新し、基盤ルール変更は理由をADRへ書いて検査・probe・見本・スキルをそろえる。
- 理由: 利用時に読むルールと基盤側のルールの分岐を止める。
- 出典: docs/design/research.md、ADR 0002
- 強制: structure, review — portable rulesの同期検査と波及レビュー
- probe: PROC-01-a
- 良い例:
  rules.mdを変えてsync-rulesと検査
- 悪い例:
  配布skillのrules.mdだけを変更

## TOOL 道具と自動化

### TOOL-01 仕様は2空白インデントと末尾改行のJSONへ整形し、固定版の依存と`npm run check`で検査する

- 軸: H1,H2,H4
- 決定: 仕様は2空白インデントと末尾改行のJSONへ整形し、固定版の依存と`npm run check`で検査する。
- 理由: 整形・検査の呼び方を作者ごとに分岐させない。
- 出典: docs/design/research.md、ADR 0002
- 強制: format — fmt/checkのcanonical比較
- probe: TOOL-01-a
- 良い例:
  JSON.stringify(value,null,2)と末尾改行
- 悪い例:
  minified JSON

### TOOL-02 検査を通すための保護ファイル変更、抑止コメント、テストのskip/onlyを使わない

- 軸: H3
- 決定: 検査を通すための保護ファイル変更、抑止コメント、テストのskip/onlyを使わない。
- 理由: 検査を避けて見かけの成功を作ることを防ぐ。
- 出典: docs/design/research.md、ADR 0002
- 強制: structure, review — guard.py、保護ファイルdiff、hook
- probe: TOOL-02-a
- 良い例:
  違反した仕様か実装を直す
- 悪い例:
  @ts-ignore、test.skip、検査の削除

## MOT 動きの基本品質

### MOT-01 各recipeが定める全状態に異なる非空ラベルを定義し、動き以外でも状態と結果を伝える

- 軸: X3,X4
- 決定: 各recipeが定める全状態に異なる非空ラベルを定義し、動き以外でも状態と結果を伝える。
- 理由: 動きを知覚しない人にも操作結果を残す。
- 出典: docs/design/research.md、ADR 0002
- 強制: structure, review — validateのlabels検査と実UIの意味伝達レビュー
- probe: MOT-01-a
- 良い例:
  保存中/保存しました/保存できませんでした
- 悪い例:
  全状態のラベルを保存しましたにする

### MOT-02 時間と曲線は対象の正本Tokenを参照し、固定値への置換や別システムのTokenを混ぜない

- 軸: D8,X2
- 決定: 時間と曲線は対象の正本Tokenを参照し、固定値への置換や別システムのTokenを混ぜない。
- 理由: 既存の一貫性を保つ。100〜400msを普遍的な規格にしない。
- 出典: docs/design/research.md、ADR 0002
- 強制: review — 実ファイルのCSS/WAAPIとprofilesの出典を照合。auditで調査時点からのToken差分を確認
- 機械化しない理由: 任意のホスト言語・CSS構成全体に対してToken使用を保証する検査は提供しない。
- probe: なし
- 良い例:
  var(--cobalt-duration-feedback)
- 悪い例:
  duration:400を全要素に直書き

### MOT-03 OSのReduced Motionを最優先し、途中のOFFで再生を止めて論理的な目標へ確定し、ON復帰だけで登場・完了を再演しない

- 軸: X5
- 決定: OSのReduced Motionを最優先し、途中のOFFで再生を止めて論理的な目標へ確定し、ON復帰だけで登場・完了を再演しない。
- 理由: 操作状態を保ちながら非本質的な移動を抑制する。cobaltの子onと親offの関係は既存仕様に従う。
- 出典: docs/design/research.md、ADR 0002
- 強制: test, review — resolveMotionとブラウザーの途中変更検査、Portalは対象で確認
- probe: MOT-03-a
- 良い例:
  reduceなら明示onでもoff
- 悪い例:
  子onでOSのreduceを上書き

### MOT-04 遊び心を有効にする仕様は`save/notify`かつ`frequency=infrequent`だけとし、確定済みの成功に一度だけ重ねる

- 軸: X6
- 決定: 遊び心を有効にする仕様は`save/notify`かつ`frequency=infrequent`だけとし、確定済みの成功に一度だけ重ねる。
- 理由: 意味を伝える前の祝福や頻繁な反復を防ぐ。本パターンの保守的な初期方針である。
- 出典: docs/design/research.md、ADR 0002
- 強制: structure, review — validateのdelight条件と実UIの再演レビュー
- probe: MOT-04-a
- 良い例:
  低頻度の初回完了に一度
- 悪い例:
  キー入力ごとに成功の跳ね

### MOT-05 開閉の動きを保ち、途中反転・次の操作・フォーカスを演出完了で待たせない

- 軸: X1,X7
- 決定: 通常のMotion設定では開く側も閉じる側も中間状態を見せ、反対の操作には表示中の状態から反転する。論理状態・次の操作・必要なフォーカス復帰は入力時に反映し、演出終了を条件にしない。OS reduceまたは明示OFFでは動きを止めて目標へ確定する。
- 理由: 待たせない対象はユーザーの次の動作である。閉じる演出の削除や0ms化では、変化の連続性が失われる。
- 出典: docs/design/research.md、ADR 0003
- 強制: test, review — 往復の中間状態、途中反転、別操作の受付、フォーカスをChromiumで確認
- probe: MOT-05-a、MOT-05-b
- 良い例:
  閉じる入力で操作状態とフォーカスを変え、見た目は連続して縮み、再入力でその途中から開く
- 悪い例:
  通常設定でも即時hiddenにする、またはanimation.finishedまで次の入力をロックする

### MOT-06 動きの方向・対象の同一性・処理結果を実際の操作目的と照合し、根拠のない移動は追加しない

- 軸: X8
- 決定: 動きの方向・対象の同一性・処理結果を実際の操作目的と照合し、根拠のない移動は追加しない。
- 理由: 意味が違う対象の変形や、見栄えだけの空間移動を防ぐ。
- 出典: docs/design/research.md、ADR 0002
- 強制: review — intent、実画面、実際の状態変化を一緒に追う
- 機械化しない理由: 対象の同一性とユーザーの理解は語句の存在だけでは判定できない。
- probe: なし
- 良い例:
  同じ選択対象の位置を追う
- 悪い例:
  無関係なページ間をカード変形で結ぶ

### MOT-07 入力応答と継続時間を別に観測し、実測値と設計値、rAF callback間隔と画面提示、位置連続と速度連続を区別する

- 軸: X9
- 決定: 入力応答と継続時間を別に観測し、実測値と設計値、rAF callback間隔と画面提示、位置連続と速度連続を区別する。
- 理由: 50msやFPSを測っていないのに保証したり、快適さを単一数値から証明することを防ぐ。
- 出典: docs/design/research.md、ADR 0002
- 強制: review — 計測条件・trace・主張の範囲を確認
- 機械化しない理由: 実際のpaint・機器差・利用者の感じ方はこの仕様検査から測定できない。
- probe: なし
- 良い例:
  入力からDOM状態更新までを観測
- 悪い例:
  rAFが60回なので快適さを実証したと断定

## 対象外とした軸

| 軸 | 理由 |
|---|---|

JSON仕様を拡張する作者に対してコードの軸D1〜D7は宣言・制御コードを追加しない形へ読み替える。ランタイムの保守は保護ファイルの変更としてADR・動作テストで扱う。
