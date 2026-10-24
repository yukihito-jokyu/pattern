# 調査と根拠

確認日2026-10-24。issue #34の本文・コメントに追加要件はなく、会話で示された定義と[承認済み計画](https://github.com/yukihito-jokyu/pattern/issues/34#issuecomment-6384141990)を対象とする。既存の未追跡pattern-foundationとskills-lock.jsonは今回の成果物に含めない。

## 取り込み先（固定スナップショット）

- 確認の状態: 確認済み
- [design-system 8acdfd9](https://github.com/yukihito-jokyu/design-system/tree/8acdfd958cd0de9ce4ea0de3805720f6ba81b4d9)のpackage-lock.jsonをAPIで取得。React/React DOM 19.3.0、Tailwind CSS 4.3.3、TypeScript 7.0.2、radix-ui 1.6.7を確認。
- cobaltは既にCSS/WAAPIのToken、MotionProvider、useDesignMotion、motion-feedback、motion-layoutを持つ。new-yorkは同じmotion Propを持たない。正本は各styles/registry.json。
- 採用するもの：既存の仕組みと値の再利用（DEP-01/02、MOT-02/03/05）。新たなmotionエンジンは導入しない。
- 公式資料の解釈とTokenの具体値を分ける。数値を一般的快適さの証明にはしない。

## Node.js 22.23.4、npm、Python 3.14

- 確認の状態: 確認済み
- `npm view node@22 version --json`の最終版22.23.4を確認し、`npx --package node@22.23.4 node --version`で実行した。既存の共通CIがNode 22のため、最新版26への移行は行わない。
- `node --help`の`--check`/`--test`を使用。仕様の型・列挙値・必須項目は閉じたJSON schemaで検査する。JSの構文検査はTypeScriptの静的型検査と呼ばない。
- `npm --version`で11.20.0を確認。Node付属版と混同せず、検証時のnpm版として記録する。
- Pythonはfoundationスクリプトの標準ライブラリ用。CIは3.14、作業端末のpython3は3.15.0。パッケージ依存はない。
- 採用：TOOL-01/02。JSON canonical整形とruntime schemaは本基盤のv1。authorは仕様のみを拡張するため汎用formatter/linterを追加しない。

## Playwright 1.64.1

- 確認の状態: 確認済み
- `npm view @playwright/test version engines --json`で1.64.1、Node >=20を確認し、package-lockで固定。Chromiumを使用する。
- [公式テスト](https://playwright.dev/docs/test-assertions)と[reducedMotion設定](https://playwright.dev/docs/api/class-page#page-emulate-media)を使う。
- 採用：参照UIの動作検証。OS実機・Safari/Firefox・任意の利用アプリまで検証したと広げない。
- 抑止記法：test.skip/only/fixme、型無視/lint無効化はguardで検出する。

## モーション・CSS・Reactの一次資料

- 確認の状態: 確認済み
- 全URLと採用範囲は[スキル同梱の出典](../../.claude/skills/pleasant-ui-motion/references/sources.md)。
- React、CSS/Tailwind、WAAPIを履歴を共有しない3担当が公式資料で並列調査。ref cleanupとSSR、CSS反転と速度連続の差、cancel/rejectionとrAF計測の限界を確認した。
- 採用：STATE-01、ASYNC-01、MOT-01〜07。数値をルール化する代わりに意図、状態、Token、停止・最新目標、検証範囲を決める。
- ツールにできないこと：意味の正しさ、ユーザーの予測、反復利用の煩わしさ、実機の画面提示は外部UI操作と人間のレビューへ残す。

## 開閉の修正で確認したこと

- 確認の状態: 確認済み
- ユーザーの指摘により、「待たせない」を即時非表示へ読み替えた初版の判断を修正した。既存Cobaltの仕様を調べた事実と、新しい目標に合うかの判断を分ける（ADR 0003）。
- CSS Gridの同じトラック構造の補間、CSS Transitionsの途中反転、HTML inert、WAI-ARIA Disclosureを公式資料で再確認。出典はスキル同梱sources.md。
- 採用：開閉の往復補間と現在値からの反転、論理状態と表示の分離。通常時の演出削除と入力ロックの両方をMOT-05の違反として検証する。
