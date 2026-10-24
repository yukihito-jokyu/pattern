# 動きの適用パターン

仕様のrecipeは本スキルの保守的な分類であり、普遍的なUI分類ではない。

## 1. 入力の手応え

- 使う場面：押下、受理、手応え。recipe=press。
- 見本：examples/demo.cssのbuttonと、取り込み先のButton。
- 作る・変えるファイル：motions/<id>/motion.json → motion.css → motion.md。STR-01、MOT-02。
- 手順：new → labels.idleとintentを編集 → fmt/build/check。実UIでは既存:active/focus-visibleの反応を優先し、押下の開始を処理完了まで遅らせない。
- 間違えやすいこと：hoverをキーボードの代替にする、短い動きの開始自体を100ms遅らせる。

## 2. 保存の状態と結果

- 使う場面：保存、通信、処理中、成功・失敗。recipe=save。
- 見本：examples/runtime.mjsのcreateSave、references/save-example.tsx。
- 作る・変えるファイル：同じ3ファイル。STATE-01、MOT-01、MOT-04。
- 手順：new → idle/pending/success/error/retryを指定 → fmt/build/check。実UIでは実際のPromiseと結果へ接続し、失敗後も入力を保持して再試行できるようにする。
- 間違えやすいこと：durationと通信待ち時間を一致させる、遅延タイマーで成功を偽装する。デモの450msは擬似処理であり推奨値ではない。

## 3. 選択と位置関係

- 使う場面：選択、Tabs=selection、並べ替え=reorder、段階移動=step。
- 見本：examples/runtime.mjsのcreateIndicator、取り込み先のmotion-layout.ts。
- 作る・変えるファイル：同じ3ファイル。ASYNC-01、MOT-02、MOT-06。
- 手順：意味と対象の同一性を決めてnew → labels → fmt/build/check。UIは論理状態を先に更新する。再目標化する選択面は表示中の値をcancel前に保存し、古い終了処理を無効にする。既存リストの中断を速度連続のばねへ勝手に変更しない。
- 間違えやすいこと：クリック対象・文字まで動かす、配列indexを同一性に使う、位置の連続を速度の連続と説明する。

## 4. 開閉・遷移・通知

- 使う場面：開閉=disclosure、無関係な画面遷移=navigation、確定した結果の通知=notify。
- 見本：examples/runtime.mjsのcreateDisclosureとdemo.cssの#panel、取り込み先の開閉部品。
- 作る・変えるファイル：同じ3ファイル。MOT-03〜MOT-06。
- 手順：new → ラベル → fmt/build/check。開閉の意図と表示中の状態を分け、通常時は往復とも補間する。反対の操作では現在の見た目から反転し、次の入力や必要なフォーカス復帰は完了イベントを待たずに反映する。退出中の内容をinertにして操作対象から外し、表示は連続させる。関係を説明しない移動は追加しない。
- 間違えやすいこと：待機の解消を演出の削除と同一視する、開くだけをフェードさせ高さを瞬時に変える、逆操作で端まで飛ぶ、閉鎖後の内容が入力を遮る。OS reduce／明示OFFは静止表現に切り替える。Overlayではフォーカストラップ・背面の操作制限と視覚的な退出を分け、非モーダルDisclosureと同じDOM構造を無条件に流用しない。

## 5. 実UIへ接続する

- 使う場面：実際のデザインシステムへ適用。
- 見本：references/design-system.md、save-example.tsx。
- 作る・変えるファイル：対象の正本CSS/部品 → 隣接Story → Registry生成物と既存利用スキル。利用アプリだけの変更ならそのアプリの画面・テストへ局所化する。基盤の仕様ファイルを対象へ無条件にコピーしない。
- 手順：
  1. 既存AGENTS、導入済みシステム、正本、対象部品の実API・状態属性、既存のMotionを読む。
  2. `node <skill>/scripts/motion.mjs audit SYSTEM TARGET_ROOT`で調査時点とのToken差分を確認する。差分があれば現行値と意味を調べてprofileを更新し、初期値へ戻さない。
  3. 利用先のstyles/registry.jsonにある既存Tokenを使い、Provider/Portalや状態通知へ接続する。new-yorkへcobalt専用Propを追加しない。
  4. 利用先の既存npm scriptsで型・lint・Registry同期・production buildを確認し、隣接Storyと外部一時アプリで操作を検証する。
  5. スクリーンショットは静止レイアウト、動画/traceと操作は時間的挙動、人間の反復利用は快適さの根拠として区別する。
- 間違えやすいこと：Tokenが一致しただけで全実装が検証済みとする、原本のimportを書き換えただけで配布物の導入を確認したとする。
