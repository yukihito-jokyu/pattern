# learning-deck-kit の技術調査

確認日: 2026-10-24。各技術を独立担当が公式一次情報と実行結果で確認した。

## html-deck 0.1.0 / 2d638228f0104fa6ebfad6447bb1652379e1da78

- 確認方法: clone後のrev-parse、pyproject/uv.lockとCLI --help。
- 確認の状態: 確認済み
- 公式の推奨: [SKILL.md](https://github.com/nogikun/skills/blob/2d638228f0104fa6ebfad6447bb1652379e1da78/skills/html-deck/SKILL.md)。
- 採用: Python>=3.14、uv locked、Chrome channel、1600×900 article.slideと共有CSS、実測check、全46ファイルと両MITライセンス。lockはPlaywright1.62.0/pypdf6.17.0を固定する。Python本体の厳密版は固定しない。
- 不採用: PPTX/PDFの自動出力、二重iframe。checkがindexを書き換えるため一時コピーで実行する。
- 補完: check終了0はblockなしだけで、意味と可読性はレビューする。通常motionの位置は親のブラウザ検査で測る。
- 実測: Python3.14.9、uv0.13.5、Chrome156.0.8078.48。

## HTML Living Standard / DOM

- 確認方法: 上流sandbox実装と[contentDocument](https://developer.mozilla.org/en-US/docs/Web/API/HTMLIFrameElement/contentDocument)、[DOMRect](https://developer.mozilla.org/en-US/docs/Web/API/Element/getBoundingClientRect)、[ResizeObserver](https://developer.mozilla.org/en-US/docs/Web/API/ResizeObserver)。
- 確認の状態: 確認済み
- 採用: 同一origin HTTP、DOM座標×縮小倍率、aria-hidden SVG。load/resize/fonts/入場アニメ終了で再計測（ASYNC-01）。
- 不採用: file://や外部サイトiframeでのDOM取得保証。

## Node.js 22.23.4 / npm11.20.0 / 検査ツール

- 確認方法: npm公式レジストリの版・engines・公開日と一時Node22でのCLI/API実測。
- 確認の状態: 確認済み
- 採用: Node標準ライブラリ、Prettier3.9.10、ESLint10.13.0、Playwright1.64.1、TypeScript7.0.2、@types/node22.20.5を開発依存として固定。
- 公式資料: [NodeESM](https://nodejs.org/docs/latest-v22.x/api/esm.html)、[ESLint rules](https://eslint.org/docs/latest/rules/)、[Prettier CLI](https://prettier.io/docs/cli)、[TS checkJs](https://www.typescriptlang.org/tsconfig/checkJs.html)、[Playwright](https://playwright.dev/docs/test-configuration)。
- 確認済み設定: strict,allowJs,checkJs,noEmit,noUncheckedIndexedAccess,exactOptionalPropertyTypes,NodeNext。NodeとDOMを分けて検査する。
- 確認済みルール: func-style（declarationを明示）,no-param-reassign,no-unused-vars,no-var,eqeqeq,max-depth,max-params,max-lines-per-function,no-restricted-syntax。
- 抑止記法: eslint-disable、@ts-ignore、@ts-nocheck、test.skip/only/fixmeは禁止（TOOL-02）。
- 不採用: UIフレームワークと外部runtime依存。TS7とESLint10は公開90日超で採用条件を満たす。

## ZIP検証の準備

- 確認方法: [PyPIのuv 0.13.5メタデータ](https://pypi.org/pypi/uv/0.13.5/json)、[公式PyPI導入手順](https://docs.astral.sh/uv/getting-started/installation/#pypi)、[Ubuntu 24.04 runnerのブラウザ一覧](https://github.com/actions/runner-images/blob/main/images/ubuntu/Ubuntu2404-Readme.md#browsers-and-drivers)、Playwrightのchrome channel実装。
- 確認の状態: 確認済み
- 採用: uv 0.13.5を再利用し、不足時はPython 3.14のpipから公式PyPI wheelを一時領域へ導入する。PATH/PYTHONPATHは子プロセスだけに渡し、終了時に削除する。実wheelの導入と既存uvの不変更を確認した。
- 前提: Ubuntu 24.04 manifestのImage Version 20261012.334.1にはChrome155.0.8059.39が掲載されている。実行時もChromeとPythonの存在を先に確認し、なければ停止する。LinuxのChromeパスはPlaywright channelの`/opt/google/chrome/chrome`と一致させる。
- 不採用: システムChromeの自動再導入、全体へのpip install。runnerの更新で前提が変わっても、準備失敗のまま後続の検証を続けない。

## Go 1.27 / 実行環境1.27.3

- 確認方法: go versionと[公式履歴](https://go.dev/doc/devel/release)、[言語仕様](https://go.dev/ref/spec)、3例のgo run出力。
- 確認の状態: 確認済み
- 採用: 変数→制御→関数の3項目。言語版と実行パッチを分けて記録する。
- 不採用: Tourの取得結果はJS shellのみで、取得済み本文とは扱わない。
- 判断: 1.27は公開90日未満だが利用アプリへのruntime採用ではなく、既存基本構文の教材例の検証環境として用いる。教材の順序はこのキットの設計判断であり公式唯一の推奨とはしない。
