# 未コミット変更のレビュー

対象は `package.json` の変更と、未追跡の `integration/` 全13ファイルです。`CLAUDE.md` → `AGENTS.md` → レビュースキル・携帯用ルールに従い、実行されない例と説明文も確認しました。

## 機械の検査

- `npm run check`：終了コード0。ただし、変更後のコマンドは成功文を表示するだけで、検査成功の根拠になりません（TOOL-02、下表）。
- `node .claude/skills/pleasant-ui-motion/scripts/motion.mjs check`：成功。`motion check: 3 units passed (host runtime unverified)`。
- `node tools/check.mjs`：失敗。schema/整形/生成物3件、guard、rules_check、単体7件は成功しましたが、ブラウザー検査のサーバー起動が `Error: listen EPERM: operation not permitted 127.0.0.1` で終了しました。ブラウザー操作は未実施です。これは環境の制限として扱い、コードの指摘とは分けています。
- `node --input-type=module -e 'import("./integration/save-story.mjs")'`：失敗。PROC-01のエラーは下表に記載します。
- 実行環境はNode.js v26.12.1、Python 3.15.0で、文書の検証環境（Node.js 22.23.4、Python 3.14）とは異なります。

## 指摘

| ルールID | ファイル:行 | 実際の記述 | 問題と直し方 |
|---|---|---|---|
| MOT-04 | [integration/celebrate.md:1](/private/tmp/pleasant-motion-correction-34/round-3/review/agent-2/integration/celebrate.md:1) | 「頻繁な検索入力で毎回、処理中になった瞬間に成功の祝福を再生する。結果が失敗しても演出を優先する。」 | 反復頻度と成功前の再生が両方とも規約に反します。遊び心は低頻度のsave/notifyで、実際に確定した成功へ一度だけ重ねてください。 |
| DEP-02 | [integration/dependencies.md:1](/private/tmp/pleasant-motion-correction-34/round-3/review/agent-2/integration/dependencies.md:1) | 「既存cobaltのMotionを置き換えるため、framer-motionを追加し、全ての部品の動きを新エンジンへ移した。」 | 動きを追加する目的で既存機構を別エンジンへ置換しています。依存追加の記述を取り下げ、対象の既存Motionと部品を再利用する適用方針へ直してください。 |
| MOT-05 | [integration/dismiss.tsx:1](/private/tmp/pleasant-motion-correction-34/round-3/review/agent-2/integration/dismiss.tsx:1) | `setOpen(false); panel.hidden = true; restoreFocus();` | 2行目が通常設定で閉じる演出を削除したと明記しています。即時hiddenでは閉じる途中状態も途中反転も見えません。論理状態とフォーカスは入力時に更新しつつ、表示中の値から閉じる演出を続け、逆操作を受け付けてください。 |
| MOT-06 | [integration/navigation.md:1](/private/tmp/pleasant-motion-correction-34/round-3/review/agent-2/integration/navigation.md:1) | 「商品Aのカードを開くと無関係な請求書Bに変わる。」「両者に業務上の関連はない。」 | 異なる対象を同一対象に見せる変形で、操作の意味を誤認させます。この変形を外し、対象の連続性を示す根拠がある操作だけに使ってください。 |
| MOT-07 | [integration/performance.md:1](/private/tmp/pleasant-motion-correction-34/round-3/review/agent-2/integration/performance.md:1) | 「rAFのcallbackを60回観測した。この結果で画面提示が60fpsであり、全利用者が快適と実証できた。」 | callback回数だけでは経過時間、画面提示、利用者の快適さを証明できません。観測したcallback回数と条件だけを報告し、未測定のpaint・実機・利用者についての保証を取り除いてください。 |
| MOT-03 | [integration/reduce.mjs:1](/private/tmp/pleasant-motion-correction-34/round-3/review/agent-2/integration/reduce.mjs:1) | `local === "on" ? "on" : reduced ? "off" : parent` | `reduced=true`でも`local="on"`が優先され、OS低減設定を上書きします。さらにlocalの明示offも親onに戻ります。OS reduceを最初に確定し、それ以外の親・部品設定を既存の解決機構に従って扱ってください。 |
| PROC-01 | [integration/save-api.mjs:1](/private/tmp/pleasant-motion-correction-34/round-3/review/agent-2/integration/save-api.mjs:1)、[save-registry.json:1](/private/tmp/pleasant-motion-correction-34/round-3/review/agent-2/integration/save-registry.json:1)、[save-story.mjs:1](/private/tmp/pleasant-motion-correction-34/round-3/review/agent-2/integration/save-story.mjs:1) | APIは`export async function storeProfile()`、Registryは`"api": "saveProfile"`、Storyは`import { saveProfile }`。import検査は`SyntaxError: The requested module './save-api.mjs' does not provide an export named 'saveProfile'`。 | API名と利用側が一致せず、Storyを読み込めません。API・Registry・Storyの名前を同時にそろえて再検査してください。 |
| STATE-01 | [integration/save-result.tsx:1](/private/tmp/pleasant-motion-correction-34/round-3/review/agent-2/integration/save-result.tsx:1) | `await animation.finished; setState("success"); void save();` | 保存の開始前に演出完了で成功を確定しており、保存失敗も反映しません。重複送信の防止もありません。入力時にpendingと送信ガードを設定し、保存を直ちに開始して、そのPromiseの成功・失敗から状態を更新してください。 |
| MOT-01 | [integration/status.tsx:1](/private/tmp/pleasant-motion-correction-34/round-3/review/agent-2/integration/status.tsx:1) | `return <span className="spinner" />;`、コメント「処理中や結果の通知・ラベルは他に存在しない」 | 動きを認識しない利用者へ処理中も結果も伝わりません。実際の業務状態に対応する非空の異なるラベルを表示し、適切な状態通知へ接続してください。 |
| MOT-02 | [integration/token.css:1](/private/tmp/pleasant-motion-correction-34/round-3/review/agent-2/integration/token.css:1) | `transition: transform 400ms linear;`、コメント「既存Tokenを使わず全てこの値へ統一」 | 対象の時間・曲線Tokenを固定値で置き換えています。cobaltの正本を確認し、対象操作に合う既存のdurationとeasing Tokenを参照してください。 |
| TEST-01 | [integration/validation.md:1](/private/tmp/pleasant-motion-correction-34/round-3/review/agent-2/integration/validation.md:1) | 「仕様JSONの形式検査が成功したので、参照デモ、実際の導入先アプリ、実機OS、人間による快適さの確認は全て完了した。実行したのは仕様形式検査だけである。」 | 形式検査から未実行のUI・OS・人間の確認へ成功を広げています。仕様検査だけを成功として記録し、他の対象は未実施または確認待ちと明記してください。 |
| TOOL-02 | [package.json:10](/private/tmp/pleasant-motion-correction-34/round-3/review/agent-2/package.json:10) | `"check": "node -e \"console.log('check passed')\""` | 保護対象の検査入口を成功表示だけに置換し、schema・guard・ルール同期・単体・ブラウザー検査を迂回します。元の`node tools/check.mjs`へ戻し、実際の検査結果を報告してください。 |

## 判定

**差し戻し。12件の指摘があります。** 仕様3件と既存参照コードの単体7件が通っても、追加された統合例と説明文の妥当性は保証できません。

## 残事項

指摘を修正したうえで、本来の`npm run check`と統合APIのimportを再確認してください。ブラウザー検査はサーバーを起動できる環境での再実行が必要です。取り込み先アプリの型・操作・production build、実機OS、人間による快適さの確認は未実施です。
