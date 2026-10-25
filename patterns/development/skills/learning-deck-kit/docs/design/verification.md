# 配布と検証の記録

この基盤は、新しい技術の公式資料と学ぶ順序を専用スキルへ保存し、各学びをスライド付きHTMLへ生成する。制作時に確認したものと、人間の確認が残るものを分けて記録する。実施日は2026-10-25、公式資料の本文確認日はprofileにある2026-10-24である。

## 構造と変更範囲

学習者へ渡す成果物は静的HTMLである。制作側のNode CLIはmodelで入力を検査し、renderでエスケープしたHTMLを作り、learningが生成台帳とファイル書き込みを担当する。ブラウザ側は生成されたデータを読み、スライドの移動と注目箇所の描画を行う。教材データからエンジンをimportする経路はなく、Go固有の処理は例の検証に閉じる。

| 目的                                       | 正本と変更先                                         |
| ------------------------------------------ | ---------------------------------------------------- |
| 技術・版・公式資料・順序を変える           | courses/<id>/profile.json                            |
| 前提・説明・実行例・練習・注目説明を変える | lessons/<id>/lesson.json                             |
| スライドの主張・構図を変える               | 同じ学びのdeck/deck.mdとdeck/slides、必要なtheme.css |
| 位置計測・操作を変える                     | learning-setup/assets/web、対応するブラウザ検査      |
| 入力契約・生成・所有判定を変える           | learning-setup/scripts、対応する単体・CLI検査        |
| 学習用スキルを利用先へ導入する             | setupでlearn-<id>と自己完結したlearning-setupを生成  |

教材だけの変更はエンジン・保護設定・検査コードへ広げない。確認用ページと専用スキルはbuild/site、build/skillsへ出す。出力の所有台帳を手編集せず、正本から再生成する。

## 25規則の強制方法

最も強い段で数えると、type 1、format 1、lint 1、structure 8、test 5、review 6、doc 3である。全件の対応はenforcement-matrix.mdにある。機械検査は入力・依存・実行時の契約を、レビューは責務、許可、名前、コメント、検証の意味、教材の整合を担う。

文書だけの3件は、PROC-01（作業の時間順序が最終差分に残らない）、PROC-03（許可と未確認の報告はコード差分に残らない）、TOOL-04（実際にコマンドを呼んだかは差分から分からない）である。これらは入口・実装スキル・完了報告へ記載し、実施の証跡と人間の確認を必要とする。

## 実施済みの確認

| 対象             | コマンド・方法                                      | 結果                                                                               |
| ---------------- | --------------------------------------------------- | ---------------------------------------------------------------------------------- |
| キット全体       | npm run check                                       | 単体22件、ブラウザ11件、Go例3件が成功。整形・lint・型・構造・guard・規則対応も成功 |
| 違反の検出       | python3 .foundation/bin/violation_probe.py --root . | 違反例17/17件を検出、checkへの組込み7/7経路を確認                                  |
| 上流html-deck    | npm run verify:decks                                | 元を変更しない一時コピー3deck・6枚、block 0、review 12、info 18                    |
| 表示と操作       | 実ブラウザで6枚×1440/768/390px                      | 対象矩形・番号・実文字の非重複、切替、履歴、キーボード、ON/OFF、再計測、狭幅を確認 |
| コピーしたスキル | READMEのsetup→check→build→sync-skill                | 元のキットをimportせずに実行成功                                                   |
| 所有判定         | CLI検査と一時コピーの再生成                         | 手編集・衝突・入力出力の重複を拒否し、無関係ファイルは保持                         |
| hooks            | 一時コピーでPreToolUse/PostToolUseを実行            | 保護変更はask、教材JSONはPrettierで整形成功                                        |
| 掲載サイト       | カード→説明→サイドバー→画像→ZIP                     | 実ブラウザで成功、ページエラー0、ZIP内容とダウンロードのハッシュ一致               |

ZIPを共通検証スクリプトで別の一時領域へ展開し、次を連続実行して終了0を確認した。展開先に元リポジトリのnode_modulesを参照させず、READMEの準備から実行している。後から加える収束結果の文章は、基盤の実行コードを変更しない。

```sh
npm run verify:patterns -- --id development/skills/learning-deck-kit --timeout-ms 1200000 -- bash -c 'node tools/verify-ci.mjs && python3 .foundation/bin/violation_probe.py --root . && python3 .foundation/bin/rules_check.py --root . --final'
```

出力の末尾は次のとおりである。

```text
check: passed
html-deck block gate: passed (3 decks; block 0; review 12; info 18; original source unchanged)
ZIP verification: passed (check, examples, original html-deck)
probe 17 件中 成功 17 件、失敗 0 件／組み込みの確認 7 件中 失敗 0 件
[phase 5 final] ルール 25 件（type 1、format 1、lint 1、structure 8、test 5、review 6、doc 3）、probe 17 件（結果: 最新）、エラー 0 件、警告 0 件
```

ルートの6コマンドもすべて成功した。配置・文書検査は11パターンで違反0、単体は81/81、typecheckは終了0、buildはZIP 11件と静的サイトを生成し、E2Eは6/6成功である。追加カードから本文・サイドバー・PNG・ダウンロードへ進み、ZIPに実装とスキルが含まれ、依存や作業用生成物を含まず、配信と生成元のハッシュが一致することも実ブラウザで照合した。

```sh
npm run check:dir
npm run check:docs
npm test
npm run typecheck
npm run build
npm run test:e2e
```

```text
配置確認: 11パターン。違反なし。
文書確認: 11パターン。違反なし。
ℹ pass 81 / fail 0
[SUCCESS] Generated static files in "build".
6 passed (10.9s)
Actual site navigation, preview, document, ZIP contents and SHA-256: passed
```

## 独立比較と残る判断

作成履歴のない作者による比較と、仕込み違反のレビュー測定はconvergence-report.mdに記録する。3回を実施し、既存教材の変更・横断更新は全回で内容まで一致した。最終12実装の全check、要求事実、全レビュアーの8件検出が成功した。一方、追加教材の注目対象の選択・命名というR1が1件残り、names=0.667で基準0.8に届かない。未使用課題のfiles=0.867は、実際に再取得した出典だけ確認日を更新したR7である。生の指標と未達を残し、完全収束とはしない。

参照教材は別モデルで2回批評した。制御構文と関数は各枚・全体ともpass、変数は2枚目の余白にdensity 3の指摘が1件残る。上流の2回上限に従って提示するものであり、解消済みとは扱わない。詳細と提案はreference-review.mdにある。

Safari・Firefox、Windows、実機の読みやすさ、学習者が実際に到達点を満たすか、人間による教材内容の承認は未確認である。自動検査の成功やAIの批評で人間の確認を代替しない。Issueは作業と残件を記録する対象であり、コミット・PR・クローズはこの作業に含めていない。
