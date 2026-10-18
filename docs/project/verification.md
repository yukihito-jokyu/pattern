---
title: 検証とZIP配布
description: スクリプトの入力・出力・失敗時の扱いと、ZIP展開後の検証規約。
slug: /project/verification
sidebar_position: 3
---

# 検証とZIP配布

配置や操作を間違えても、不完全な成果物を完成品として扱わないようにします。構造はスクリプト、動作は個別検証、説明の妥当性は人間のレビューで確認します。

## 各スクリプトの役割

| ファイル | 入力と確認・出力 |
| --- | --- |
| `scripts/check-dir.mjs` | 文書と実装の3階層の対応・命名・README・実ファイル |
| `scripts/check-docs.mjs` | Markdownのメタデータ・未記入欄・PNG参照・対応ZIPの指定 |
| `scripts/build-downloads.mjs` | 配置確認後、必要なファイルからパターンごとのZIPを生成 |
| `scripts/verify-patterns.mjs` | ZIPを別の場所に展開し、各パターンのverify.mjsを実行 |

ルートから実行します。サイトビルドは配置確認、文書確認、ZIP生成、Docusaurusビルドの順です。途中失敗は後続を止め、非0の終了コードを返します。

文書確認はZIP生成前に、リンクが生成予定パスを指すか確認します。未生成のZIPがないことだけで失敗させません。生成後はビルドとブラウザーで実際に取得できることまで確認します。

## 個別パターンの検証規約

各パターンは`verify.mjs`を入口にします。Node.js 22以上で`node verify.mjs`を実行できるようにし、READMEにも同じ手順を記載します。別言語の実装でも、入口から対象ツールの環境確認・準備・検証を行えます。

終了コード0は成功、1などの非0は失敗、2は必要環境などの不足による未実施です。管理側は失敗と未実施のどちらでも非0で終了し、CIの成功に混ぜません。必要な準備に失敗したら検証を続けません。

例えば別のコマンドを実行する場合は、結果を確認してから次に進みます。

```js
import {spawnSync} from 'node:child_process';

for (const [command, args] of [
  ['npm', ['ci']],
  ['npm', ['test']],
]) {
  const result = spawnSync(command, args, {stdio: 'inherit'});
  if (result.error || result.status !== 0) process.exit(1);
}
```

これはnpmを使う場合の例です。依存が不要なら導入処理は要りません。単なるログ出力ではなく、具体的な期待結果を検証してください。

```sh
npm run verify:patterns -- --id backend/api/error-handling
npm run verify:patterns -- --all
```

管理側はZIPを一時ディレクトリへ展開し、パターンのルートを作業場所にして実行します。1件の制限時間は120秒です。必要なら`--timeout-ms 300000`のように指定します。入口欠落・未対応環境・失敗・時間切れを成功にしません。

初期構成は実用パターン0件です。0件という結果は実用パターンの動作確認を意味しません。管理処理はテスト用サンプルで別に確認します。

## ZIPの収録と更新

生成先は`static/downloads/patterns/<分野>/<分類>/<パターン>.zip`です。ZIP内はパターン名のディレクトリにまとまり、README・実装・検証ファイルが入ります。

必要な隠し設定を含め、`node_modules`、`build`、`dist`、`.git`、`.cache`、`.docusaurus`、`coverage`、`__pycache__`、`.venv`などを除外します。必要な実ファイルをこれらの生成物用ディレクトリに置かないでください。シンボリックリンクは収録せず、実ファイルの配置を求めるエラーにします。

一時ディレクトリで全ZIPを生成・確認し、成功時だけ配布先を置き換えます。途中失敗で一部だけ更新せず、サイトビルドを止めます。古いZIPが残っていても今回の生成成功とは扱いません。正常な更新では削除・改名された古いZIPが消え、他の静的ファイルは残ります。

## テストとCI

正常なfixtureを一時ディレクトリへコピーし、欠落・配置誤り・画像形式偽装・誤リンク・収録漏れ・失敗・時間切れを作って、想定した理由で失敗するか確認します。本物の文書・実装・配布物は変更しません。

検索処理は結果を確認し、ブラウザーでは導線、PNG表示、ZIP取得と中身、検索から対象文書への移動を確認します。検証用サイトは一時環境で作り、公開サイトにサンプルを混ぜません。

CIは初期段階では全パターンを検証します。差分による対象選択は実行時間が問題になったときに検討します。現在はUbuntuとNode.jsが実行環境です。それ以外の環境が必要なパターンを追加する場合は対応するCIジョブも整備し、未対応を黙って成功にしません。

仕様は[DocusaurusのDocs設定](https://docusaurus.io/docs/api/plugins/@docusaurus/plugin-content-docs)、[画像・ファイルの扱い](https://docusaurus.io/docs/markdown-features/assets)、[Playwrightのサーバー起動](https://playwright.dev/docs/test-webserver)で確認できます。サイト、個別実装、人間の確認結果は分けて記録します。
