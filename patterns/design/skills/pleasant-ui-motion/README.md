# pleasant-ui-motion

既存のデザインシステムへ、意図・状態・操作の自由を保つUIモーションを取り入れるスキルと検証基盤です。対象の参考実装はReact/Tailwindのyukihito-jokyu/design-system（new-york/cobalt）。既存Token・部品・Providerを使い、別のモーションエンジンは追加しません。

## 準備と全検査

ZIPを展開したpleasant-ui-motionディレクトリで実行します。Node.js 22.23.4（.nvmrc）、npm、Python 3.14が必要です。Pythonは標準ライブラリだけ、npm依存は固定版Playwright（検証用）です。初回はnpm registryとPlaywrightのブラウザー配布先へ接続します。

```sh
node --version
python3 --version
npm ci
npx playwright install chromium
npm run check
```

LinuxでブラウザーのOS依存が不足する場合は `npx playwright install --with-deps chromium` を使います。準備が失敗したら後続を実行しません。CI用の `node tools/verify-ci.mjs` は依存準備・ブラウザー準備・全検査を順に行い、途中失敗で止まります。

期待結果はschema/整形/生成物検査、guard、rules_check、単体7件、Chromiumの操作7件が成功して `check: passed` と表示されることです。JSは構文・動作、仕様の型は閉じたJSON schemaで検査します。これをホスト全体のTypeScript検査と呼びません。

## スキルを利用先へ導入する

`.claude/skills/pleasant-ui-motion/`と`.claude/skills/pleasant-ui-motion-review/`を同じ親ディレクトリへ一緒にコピーします。Codexでは利用先の`.agents/skills/`、Claude Codeでは`.claude/skills/`を使えます。既存の同名スキルがある場合は内容を比較してから更新し、上書きで設定を失わないようにします。自動読み込みを使えない場合はSKILL.mdを直接読ませます。

利用先のAGENTS・既存design-system/cobalt-design-systemスキルを先に読みます。本ZIPのAGENTS・hooks・package.jsonを利用先のルートへ上書きする必要はありません。この基盤を保守するときは、このディレクトリでエージェントを起動します。

例：
```text
$pleasant-ui-motion
cobaltの設定保存画面で、受理・保存中・失敗・再試行・成功を伝える動きを既存部品で実装して。
```

対象の正本・APIを再確認し、保存処理から状態を決め、既存Motionを使います。new-yorkへcobaltのmotion propを渡しません。設計履歴や検証アプリを置けないリポジトリでは、作業用仕様と検証環境を外部一時ディレクトリへ置きます。

## この基盤で適用仕様を追加する

```sh
node .claude/skills/pleasant-ui-motion/scripts/motion.mjs new profile-save cobalt save
# motions/profile-save/motion.jsonのintent・labelsを編集する
npm run fix
npm run check
```

systemはcobalt/new-york、recipeはpress/save/selection/disclosure/reorder/step/notify/navigation。idは英字始まりのkebab-case。frequencyの既定はfrequent、delightはfalseです。遊び心はinfrequentのsave/notifyだけで使えます。

編集するのはmotion.jsonです。motion.cssは正本Tokenへの参照、motion.mdは状態・中断方針を含む適用計画です。生成物だけを書き換えると検査で落ちます。これらを生成しても、UIへの導入は行われません。

`scripts/motion.mjs`はスキル内で完結し、Node標準ライブラリだけで動きます。コピーしたスキルでも、作業用ディレクトリから同じnew/fmt/build/checkを実行できます。

## 動作例を見る

```sh
npm run serve
```

http://127.0.0.1:4178/ を開きます。保存結果は擬似応答です。失敗後も入力が残り、再試行で成功できます。連続選択は表示中の位置からつながり、開く・閉じる両方で高さと透明度が変わり、途中の逆操作は現在位置から反転します。「次の操作を試す」は開閉中も押せます。閉じる入力では内容を操作対象から外し、必要なフォーカス復帰を行い、見た目の退出を続けます。低頻度の祝福を有効にすると、成功後に一度だけ小さな余韻を加えます。

親・部品・OS低減設定を変え、途中OFFとON復帰も確認します。new-yorkではcobalt専用の親・部品指定を無効にします。この見本は接続方針の参照であり、取り込み先のReact部品そのものではありません。

## 指定デザインシステムの原本と照合する

依存準備済みの外部コピーを指定します。参照元を変更しません。

```sh
node .claude/skills/pleasant-ui-motion/scripts/motion.mjs audit cobalt /path/to/design-system
node tools/verify-target.mjs /path/to/design-system
```

auditは調査時点のToken一致だけを検査し、runtimeはunverifiedと表示します。verify-targetは両システムの実Button型で同梱SaveExampleを検査します。利用アプリへのRegistry導入、実画面の動作、人間の快適さまで確認したことにはなりません。Tokenが変わっていたら現行仕様を調べ、古い値へ戻しません。

## ルールを保守する

`docs/design/`に判断の根拠、構造、21ルールと強制対応表、収束結果があります。完全な手順はAGENTS.mdを読みます。

```sh
npm run fix
python3 .foundation/bin/rules_check.py --root .
npm run check
python3 .foundation/bin/violation_probe.py --root .
python3 .foundation/bin/rules_check.py --root . --final
```

probeは一時コピーへ違反を1件ずつ入れ、非0終了と対象の失敗を確認します。本物の仕様を破壊しません。収束テストのコピーはOS一時ディレクトリ、計測結果は.foundation/convergenceへ残します。

## 確認範囲

2026-10-24、macOSで参照デモの保存・連続選択・停止・優先順位・往復の開閉・途中反転・演出中の別操作とフォーカス・狭い幅を検証しました。実際の検証結果と収束指標はdocs/design/convergence-report.mdと掲載文書を参照してください。実機OS、他ブラウザー、取り込み先アプリの実行、人間の反復利用による快適さは別の確認です。
