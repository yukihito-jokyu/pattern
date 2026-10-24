# 構造と変更の範囲

動きの見た目を先に増やすと、作者ごとに時間・状態・停止方針が分かれる。この基盤は目的と状態をmotion.jsonへ固定し、既存Tokenへ対応させて適用計画を生成する。実UIの状態と結果は既存アプリが所有し、生成仕様を読めただけでUIが完成したとは扱わない。

## 依存の許可表

| 参照元 | 許可する参照先 |
|---|---|
| authorのmotion.json | system/recipeの識別子だけ |
| scripts/motion.mjs | 同梱assets、Node標準ライブラリ |
| 生成css/md | 仕様と選択profileだけ |
| 参照demo | 参照runtime、同梱profile、開閉のCSS補間 |
| 対象のReact UI | 既存の部品・Token・Provider・業務処理 |
| check/test | core、参照demo、foundation検査 |

禁止された方向は使わない。掲載サイトsrc/pluginsは配布実装をimportしない。

## 公開面

スキルはSKILL.mdと参照資料、CLIはnew/fmt/fmt-file/build/check/audit/list。coreのvalidate/compile/renderは検証用の公開関数。生成motion.cssはTokenの別名参照だけで、実部品を作らない。auditは調査時点とのToken一致だけを確認する。

## 配置

`.claude/skills/pleasant-ui-motion/`の内側にportableな原則・接続手順・ツール・profileを持つ。reviewは同じ親の実装スキルを参照するため2つ一緒に導入する。基盤ルールの正本はdocs/design/rules.md、携帯用の同内容はsync-rulesで生成する。motion.jsonを編集し、motion.css/mdを生成する。examplesは中断と意味保持の最小実装で、既存React部品の置換ではない。

## 変更シナリオ

| 変更 | 触るファイル |
|---|---|
| 仕様を追加 | motions/<id>/motion.json、生成css/md |
| 保存ラベルを変更 | 対象motion.json、生成css/md |
| 2システムへ同じ目的を設計 | システム別の2仕様と生成物 |
| 正本Tokenが更新 | profile、research、必要な検査と生成物。値を勝手に元へ戻さない |
| 既存UIの動きを修正 | 対象の原本・隣接Story・配布定義・利用スキル（対象ルールに従う） |
| 中断処理を修正 | 参照runtime、操作テスト、probe、説明 |
| 基盤ルールを変更 | ADR、rules、検査/probe、portable rules、入口/レビュー |
| 出典が更新 | sources、principles、research、変更した判断だけ |

## 制約

JSONの型・配置・生成物・参照デモの動作は機械で確認する。任意のホストソース全体を解析して全Token利用やアクセシビリティを証明する静的解析器は提供しない。ホストの型検査・操作・人間の確認を別に残すことがTEST-01/MOT-07である。

## 開閉の操作状態と表示

createDisclosureは入力時に意図・aria-expanded・inert・必要なフォーカスを更新する。表示はCSS Gridの0fr/1frとopacityのtransitionへ任せ、完了イベントから操作状態を書き戻さない。閉じる途中でも次の入力を受け付け、CSSは現在値から反転する。通常時の演出を消すことで待機をなくしたとは扱わない。判断と既存Cobaltとの違いはADR 0003にある。
