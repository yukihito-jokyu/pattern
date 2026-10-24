<!-- 生成物。motion.jsonから再生成する。 -->
# save-preferences

設定の保存結果を伝える。処理結果を確認してから成功を示すを伝える。

| 項目 | 決定 |
|---|---|
| システム | cobalt |
| 関係 | same-control |
| 時間 | `var(--cobalt-duration-feedback)` |
| 曲線 | `var(--cobalt-ease-out)` |
| 途中操作 | state-first |
| 低減時 | instant-with-meaning |
| 閉鎖 | state-first |
| 遊び心 | なし |

状態は操作・処理結果で更新する。アニメーション完了を業務状態の条件にしない。

| 状態 | 動きを止めても残すラベル |
|---|---|
| idle | 保存する |
| pending | 保存中 |
| success | 保存しました |
| error | 保存できませんでした |
| retry | 再試行 |

正本は取り込み先の`registry/cobalt/styles/registry.json`。このファイルは適用計画であり、UIへの導入・動作検証・人間の確認は未実施。
