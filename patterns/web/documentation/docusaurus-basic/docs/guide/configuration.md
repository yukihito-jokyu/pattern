---
title: サイトを設定する
description: OSSと独自設定を確認し、setupでサイトを構成する方法。
slug: /guide/configuration
sidebar_position: 2
---

# サイトを設定する

site.settings.jsonに、サイト、preset、theme、sidebar、記事、カテゴリ、TypeScript、Playwright、独自設定を分けて保存します。setupの設定台帳は、明示した値と未設定の項目を両方示します。

## 設定を選ぶ

setupスキルを使うと、最初に「重要のみ」「重要＋普通」「すべて」から質問範囲を選べます。重要のみではサイト名・公開URL・言語・ホーム・検索とブログの有効化を確認します。普通には見た目や記事表示、すべてにはビルド・開発・テストの詳細も含まれます。範囲外は現在値や未設定時の既定動作を維持します。

配布物のルートでnpm run setup -- init --level important --out setup-answers.jsonを実行し、npm run setup -- list --answers setup-answers.jsonで選んだ範囲の質問と現在値を確認できます。回答はJSONへ記録します。normalは重要＋普通、advancedはすべてを指定します。

## 値を反映する

回答をvalidateで確認し、planで差分を読んでからapplyを実行します。未設定はOSSの既定動作を使う選択であり、falseによる無効化とは異なります。READMEにコマンドと手編集時の扱いを記載しています。

## ドメインと配信パス

https://example.com/manual/に置く場合、urlはhttps://example.com、baseUrlは/manual/です。検索結果も生成された公開URLを使うため、サブパスから記事へ移動できます。
