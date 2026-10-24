# pleasant-ui-motion

既存デザインシステムへ動きを取り入れるための仕様・スキル・参照実装を管理する。実装は [.claude/skills/pleasant-ui-motion/SKILL.md](.claude/skills/pleasant-ui-motion/SKILL.md)、レビューは [pleasant-ui-motion-review](.claude/skills/pleasant-ui-motion-review/SKILL.md) を読む。スキルが使えなくても同じファイルを直接読む。

## 作業の入口

この基盤で「追加して」「保存を直して」「動きを抑えて」「ラベルを変えて」「2システムへ適用して」と頼まれたときは実装用スキルを使う。ここでの成果物は適用仕様であり、対象アプリの未検証コードへ成功を広げない。

## コマンド

Node.js 22.23.4、Python 3.14、npm（11.20.0で検証）を使う。初回はREADMEの準備を済ませる。検証用コピーの依存準備は実行基盤が担当する。既に依存があるコピーではnpm ciを再実行しない。node_modulesが外部へのリンクなら、リンクを変更・再導入せず、準備不足として報告する。

| 目的 | コマンド |
|---|---|
| 完了検査 | `npm run check` |
| 仕様整形・生成・ルール同期 | `npm run fix` |
| 新規仕様 | `node .claude/skills/pleasant-ui-motion/scripts/motion.mjs new ID SYSTEM RECIPE` |
| 単独仕様検査 | `node .claude/skills/pleasant-ui-motion/scripts/motion.mjs check` |
| 動作見本 | `npm run serve` |

## 守ること

1. STR-01：新規仕様はnewで作り、`motions/<id>/motion.json`を編集する。生成物はbuildへ任せる。
2. DEP-01：1仕様につき1システム。new-yorkへcobaltのmotion propを渡さない。
3. NAM-01：idが依頼にあればそのまま使い、無ければrecipe名をidにする。
4. CODE-01：既存8recipeへ振り分け、見本の構造を使う。
5. ERR-01：入力の未知キー・型違反を黙殺しない。
6. STATE-01：入力の受理、処理中、成功/失敗を業務状態から伝える。
7. ASYNC-01：連続選択は表示中の位置から次の目標へつなぐ。
8. MOT-02：対象の既存Tokenと機構を使う。未指定の依存を追加しない。
9. MOT-03：Reduced Motionを最優先し、停止で値・選択・結果を消さない。
10. MOT-04：遊び心は低頻度の確定済み成功だけ。指定がなければfalse。
11. MOT-05：通常時は開く・閉じる両方を連続して見せる。途中反転・次の操作・フォーカスを演出完了まで待たせない。
12. TEST-01：仕様検査・参照デモ・対象UI・人間の確認を分けて報告する。
13. PROC-01：仕様と生成物をそろえ、ルール変更はスキル・probe・見本へ反映する。

## してはいけないこと

検査を通すための保護ファイル変更、抑止コメント、テストのskip/only、依頼にない依存追加は禁止（TOOL-02）。保護範囲はmanifestのprotectedにある。仕様追加の依頼では`motions/`以外を変更しない。既存見本と異なる仕組みが必要なら、対象の要件と既存APIを調べて提案する。

## 完了の条件

`npm run fix`の後に`npm run check`を通す。実アプリへの適用では、そのアプリで型・操作・production buildも確認する。未実施と人間の確認待ちを残す。

## ルールを変えたいとき

依頼で許可された保守の範囲を確認し、ADR → rules.md → 検査/probe → 参照実装/スキル → fix/check/probe の順でそろえる。既存の承認を取り直すための手順にはしない。
