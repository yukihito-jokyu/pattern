<!-- 生成物。motion.jsonから再生成する。 -->
# choose-period

期間の選択位置を伝える。選択した対象と現在位置を伝える。

| 項目 | 決定 |
|---|---|
| システム | cobalt |
| 関係 | same-object |
| 時間 | `var(--cobalt-duration-expand)` |
| 曲線 | `var(--cobalt-ease-out)` |
| 途中操作 | retarget |
| 低減時 | instant-with-meaning |
| 閉鎖 | state-first |
| 遊び心 | なし |

状態は操作・処理結果で更新する。アニメーション完了を業務状態の条件にしない。

| 状態 | 動きを止めても残すラベル |
|---|---|
| idle | 期間を選ぶ |
| selected | 選択済み |

正本は取り込み先の`registry/cobalt/styles/registry.json`。このファイルは適用計画であり、UIへの導入・動作検証・人間の確認は未実施。
