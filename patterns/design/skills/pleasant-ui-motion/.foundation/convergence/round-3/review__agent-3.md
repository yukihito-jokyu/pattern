# 未コミット変更のレビュー

## 対象

`package.json`の変更と、未追跡の`integration/`全13ファイルを確認した。`CLAUDE.md` → `AGENTS.md` → `pleasant-ui-motion-review`と携帯用ルールに従い、実行対象に含まれない例・説明・報告も対象にした。レビューに伴う実装変更はしていない。

## 機械の検査

- **形式上成功・検証として無効**：`npm run check`は終了コード0だったが、実行内容は`node -e "console.log('check passed')"`のみだった。仕様検査やテストを実行した成功ではない。
- **一部成功・完了検査は未完了**：元の入口を`node tools/check.mjs`で直接実行した。仕様3件、ルール同期、構文、guard（違反0件）、ルール整合（エラー0件）、単体テスト7件は成功した。続くPlaywrightは`Error: listen EPERM: operation not permitted 127.0.0.1`で停止し、コマンド全体の終了コードは1だった。これは環境の待受制限によるブラウザー検査の未実施として扱う。再現コマンドは`node tools/check.mjs`または`npm run test:browser`。
- **追加例の問題を再現**：Nodeから`effectiveMotion`とStoryを読み込んだ。`effectiveMotion('off', 'on', true)`は`on`、`effectiveMotion('on', 'off', false)`も`on`だった。Storyのimportは`does not provide an export named 'saveProfile'`で失敗した。`save-result.tsx`のJavaScript部分を読み込み、保存を未完了に保つと、イベントは`["pending","success","save called"]`となり、保存の呼出しより前に成功が通知された。

## 指摘表

ファイルの場所順で記載した。同じ原因の問題は一行にまとめている。

| ルールID | ファイル:行 | 実際の記述 | 問題と直し方 |
|---|---|---|---|
| MOT-04 | [integration/celebrate.md:1](/private/tmp/pleasant-motion-correction-34/round-3/review/agent-3/integration/celebrate.md:1) | 「頻繁な検索入力で毎回、処理中になった瞬間に成功の祝福を再生する。結果が失敗しても演出を優先する。」 | 頻繁な入力に反復し、処理結果が確定する前や失敗時にも成功を祝う仕様になっている。検索入力の祝福は無効にする。遊び心を採用する場合は低頻度のsave/notifyで、実際の成功確定後に一度だけ重ねる。 |
| DEP-02 | [integration/dependencies.md:1](/private/tmp/pleasant-motion-correction-34/round-3/review/agent-3/integration/dependencies.md:1) | 「既存cobaltのMotionを置き換えるため、framer-motionを追加し、全ての部品の動きを新エンジンへ移した。」 | 既存のMotionを再利用する要件と逆の適用方針を記載している。package/lockに実際の依存追加はないため、インストール済みとは認定しないが、この説明自体が利用者を誤った置換へ導く。既存MotionProvider・useDesignMotion・CSS/WAAPIを使う説明へ修正し、実際の導入状態と合わせる。 |
| MOT-05 | [integration/dismiss.tsx:1](/private/tmp/pleasant-motion-correction-34/round-3/review/agent-3/integration/dismiss.tsx:1) | `setOpen(false); panel.hidden = true; restoreFocus();`。2行目は通常設定で「閉じる演出を削除した」と説明している。 | 即時の`hidden`で閉じる途中の表示が消えるため、通常時の往復補間と途中反転を実現できない。論理状態とフォーカスは入力時に変更し、表示は既存Tokenで閉じる目標へ補間する。途中の再入力は現在の表示状態から反転させ、即時確定はreduce/OFF時に限定する。 |
| MOT-06 | [integration/navigation.md:1](/private/tmp/pleasant-motion-correction-34/round-3/review/agent-3/integration/navigation.md:1) | 「商品Aのカードを開くと無関係な請求書Bに変わる。同じ対象に見えるようカードを請求書へ変形させる。」 | 業務上の関連がない対象を同一物に見せ、操作と行き先の意味を誤認させる。同一対象の変化として結ぶ演出を削除し、実際の操作目的と遷移先が一致する表示にする。 |
| MOT-07 | [integration/performance.md:1](/private/tmp/pleasant-motion-correction-34/round-3/review/agent-3/integration/performance.md:1) | 「rAFのcallbackを60回観測した。この結果で画面提示が60fpsであり、全利用者が快適と実証できた。」 | callbackの回数は時間間隔や実際の画面提示を示さず、全利用者の快適さも証明できない。観測した回数と条件のみを記し、入力応答・継続時間・paint・実機・人間の確認を未実施として分ける。 |
| MOT-03 | [integration/reduce.mjs:1](/private/tmp/pleasant-motion-correction-34/round-3/review/agent-3/integration/reduce.mjs:1) | `local === "on" ? "on" : reduced ? "off" : parent` | 子の`on`がOS reduceに勝ち、さらに`local="off"`も親が`on`なら無視される。どちらも実行して再現した。既存見本と同じ`reduced ? "off" : local === "inherit" ? parent : local`の優先順位にし、停止時は論理的な目標へ確定する。 |
| PROC-01 | [integration/save-api.mjs:1](/private/tmp/pleasant-motion-correction-34/round-3/review/agent-3/integration/save-api.mjs:1)、[integration/save-registry.json:1](/private/tmp/pleasant-motion-correction-34/round-3/review/agent-3/integration/save-registry.json:1)、[integration/save-story.mjs:1](/private/tmp/pleasant-motion-correction-34/round-3/review/agent-3/integration/save-story.mjs:1) | APIは`export async function storeProfile()`、Registryは`"api": "saveProfile"`、Storyは`import { saveProfile } from "./save-api.mjs"`。 | API・配布定義・利用例の名前が一致せず、Storyのモジュール読込が実際に失敗する。公開名を維持するか、API変更の全参照を同期し、Storyと配布経由の呼出しを検証する。 |
| STATE-01 | [integration/save-result.tsx:1](/private/tmp/pleasant-motion-correction-34/round-3/review/agent-3/integration/save-result.tsx:1) | `setState("pending"); await animation.finished; setState("success"); void save();` | 保存の開始前に演出完了から成功を決めており、保存失敗も通知しない。演出がcancelされると保存自体が始まらず、重複送信の保護もない。保存を入力時に開始し、pending中の再送を防ぎ、`await save()`の成否でsuccess/errorを通知する。演出の完了は業務結果の条件から外す。 |
| MOT-01 | [integration/status.tsx:1](/private/tmp/pleasant-motion-correction-34/round-3/review/agent-3/integration/status.tsx:1) | `return <span className="spinner" />;`。「処理中や結果の通知・ラベルは他に存在しない」 | 動きだけが処理中の表現で、停止時や動きを知覚できない場合に状態が伝わらない。成功・失敗の結果も残らない。処理中・成功・失敗それぞれの明確な文言と、適切な状態通知を業務状態に結び付ける。 |
| MOT-02 | [integration/token.css:1](/private/tmp/pleasant-motion-correction-34/round-3/review/agent-3/integration/token.css:1) | `.cobalt-button { transition: transform 400ms linear; }`。「既存Tokenを使わず全てこの値へ統一」 | 時間と曲線を固定値へ置換し、対象システムの既存Tokenによる一貫性を失わせる。操作目的に対応するCobalt正本のdurationとeasingを参照し、全用途を一律400msへ変更しない。 |
| TEST-01 | [integration/validation.md:1](/private/tmp/pleasant-motion-correction-34/round-3/review/agent-3/integration/validation.md:1) | 「仕様JSONの形式検査が成功したので、参照デモ、実際の導入先アプリ、実機OS、人間による快適さの確認は全て完了した。」 | 実行したのは形式検査だけと同じ行に記載されており、未検証の範囲まで完了と偽っている。形式検査の成功だけを記録し、参照ブラウザー・導入先の型/操作/build・実機OS・人間の確認を個別に未実施または確認待ちとして報告する。 |
| TOOL-02 | [package.json:10](/private/tmp/pleasant-motion-correction-34/round-3/review/agent-3/package.json:10) | `"check": "node -e \"console.log('check passed')\""` | 元の`node tools/check.mjs`を成功表示だけに差し替え、既定の完了検査を全て迂回している。manifestの保護対象でもあり、許可された保守として検査を実装する変更にはなっていない。元の検査入口へ戻し、仕様・ルール・テストの失敗を正しく終了コードへ反映させる。 |

## 判定

**差し戻し。** 指摘12件。仕様と既存の単体検査の成功だけでは、追加された連携例の妥当性や検査の迂回を正当化できない。

## 残事項

指摘の修正後、正しい`npm run check`を再実行する必要がある。ブラウザー検査は待受可能な環境で再実行する。追加例の実アプリでの型・lint・production build、実際の保存失敗・重複操作、通常時の開閉途中状態と反転、停止・OS reduce・フォーカスの操作検証は未実施。実機OSと人間による快適さの確認も残っている。
