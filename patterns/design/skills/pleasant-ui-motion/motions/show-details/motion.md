<!-- 生成物。motion.jsonから再生成する。 -->
# show-details

補足の開閉と次の操作を伝える。開閉とフォーカスの移動を伝える。

| 項目 | 決定 |
|---|---|
| システム | new-york |
| 関係 | same-object |
| 時間 | `var(--ds-duration-normal)` |
| 曲線 | `var(--ds-ease-standard)` |
| 途中操作 | reverse |
| 低減時 | instant-with-meaning |
| 閉鎖 | animated-nonblocking |
| 遊び心 | なし |

状態は操作・処理結果で更新する。アニメーション完了を業務状態の条件にしない。

| 状態 | 動きを止めても残すラベル |
|---|---|
| open | 開く |
| close | 閉じる |

正本は取り込み先の`registry/new-york/styles/registry.json`。このファイルは適用計画であり、UIへの導入・動作検証・人間の確認は未実施。
