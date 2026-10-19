---
name: setup
description: このDocusaurusパターンの初期設定・設定変更を、OSSと独自設定の台帳に沿った質問とCLIで行う。site.settings.jsonとsetup/settings.catalog.jsonがある配布先で使用する。
---

# Docusaurusのセットアップ

配布物のルートを作業場所にする。[質問と回答の扱い](references/questions.md)を読み、READMEとsetup/sources.mdで設定面・生成先・優先順位を確認する。対象ファイルがない別のプロジェクトの設定を変更しない。

1. Node.jsを確認し、READMEの準備を実施する。準備失敗では停止する。`npm run setup -- check`で版・台帳・管理ファイルの整合を確認する。手編集があれば差分を見せ、勝手に上書きしない。
2. 最初に質問範囲を選んでもらう。「重要のみ（推奨）」はサイト名・公開URL・言語・ホーム・ブログと検索の有効化、「重要＋普通」は見た目・記事表示・運用も含む、「すべて」は内部処理・開発・テストの詳細も含むと説明する。範囲外は現在値・未設定時の既定動作を維持すると伝える。順にimportant、normal、advancedを対応させ、`npm run setup -- init --level important --out setup-answers.json`のように回答ファイルを作る。既存回答は無断で破棄しない。
3. `npm run setup -- list --answers setup-answers.json --group site`などで選択範囲を読み、現在値、未設定時の既定動作、型・選択肢・依存条件・出典を提示して質問する。台帳のimportanceとimportanceReasonを使い、同じpathの型分岐を別々の質問に数えない。関連項目をまとめ、開始時に対象パス数とおおよその質問回数を伝える。無効な機能の詳細は理由を示して非該当とし、有効化した場合に必要な追加項目を確認する。台帳全体の網羅性を、全利用者への全項目質問と取り違えない。
4. 利用者の回答をsettingsへ反映し、確認した値をreviewsへ記録する。推奨値や初期値を無断で利用者の回答にしない。選択範囲内の未設定項目も確認する。必要な追加モジュール・コンテンツがない場合は、その準備を未完了として示す。
5. 選択範囲の回答後、`npm run setup -- validate --answers setup-answers.json`、続いて`plan`を実行する。差分、維持した範囲、追加作業を利用者へ示し、依頼された変更範囲で`apply`する。公開ドメインが未定なら仮値を承認済みにせず、公開前の未完了事項として残す。
6. `npm run setup -- check`、`npm run typecheck`、`npm run build`、READMEのテストを行う。成功・失敗・未実施と、未設定として残した項目、追加準備を分けて報告する。

複数項目の一括確認では対象の全項目と適用値を先に示す。返答がない項目は未回答のままにする。レビューをすべてconfirmedへ変えるだけの処理を、利用者への質問の代わりに実行しない。公開、Git操作、外部サービス登録はセットアップの依頼から推測して行わない。
