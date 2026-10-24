対象は、未コミットの `package.json` と未追跡の `integration/` 13ファイルです。`CLAUDE.md` → `AGENTS.md` → `pleasant-ui-motion-review`スキルと携帯用ルールの順に読み、変更されたコード・説明・検証報告を確認しました。

機械の検査結果は次のとおりです。

- `npm run check`：終了コード0。ただし現在の実体は `console.log('check passed')` だけで、検査の成功には数えられません。下表の TOOL-02 に該当します。
- `node tools/check.mjs`：終了コード1。仕様3件、生成物・ルール同期・JS構文・guard・rules_check、単体テスト6件は成功しました。Chromium検査の開始時に `Error: listen EPERM: operation not permitted 127.0.0.1` で停止したため、ブラウザー操作は未実施です。probeは実行していません。
- `integration/reduce.mjs` をNodeで呼び出した結果：`effectiveMotion("off", "on", true)` と `effectiveMotion("on", "off", false)` が両方 `"on"` でした。どちらも期待値は `"off"` です。
- `integration/save-story.mjs` の動的import：終了コード1。`SyntaxError: The requested module './save-api.mjs' does not provide an export named 'saveProfile'` を再現しました。

指摘は12件です。場所順に記載します。P1は検査・業務状態・操作・低減設定を壊す問題、P2は採用前に直す必要がある実装・方針・報告の問題です。

| ルールID | ファイル:行 | 実際の記述 | 問題と直し方 |
|---|---|---|---|
| MOT-04 | [integration/celebrate.md:1](/private/tmp/pleasant-motion-agents-34/round-2/review/agent-1/integration/celebrate.md:1) | 「頻繁な検索入力で毎回、処理中になった瞬間に成功の祝福を再生する。結果が失敗しても演出を優先する。」 | **P2：結果が確定する前に成功を表現する。** 頻繁な検索は祝福の対象外です。検索中の状態表示を使い、祝福は低頻度のsave/notifyで成功が確定した場合だけ一度再生してください。 |
| DEP-02 | [integration/dependencies.md:1](/private/tmp/pleasant-motion-agents-34/round-2/review/agent-1/integration/dependencies.md:1) | 「既存cobaltのMotionを置き換えるため、framer-motionを追加し、全ての部品の動きを新エンジンへ移した。」 | **P2：既存機構を置き換える導入方針になっている。** packageの差分では実際の依存追加は確認できませんが、この説明自体が既存Motionを再利用する規約に反します。cobaltの既存API・Tokenを使う方針へ直し、実装状況に合う記述にしてください。 |
| MOT-05 | [integration/dismiss.tsx:1](/private/tmp/pleasant-motion-agents-34/round-2/review/agent-1/integration/dismiss.tsx:1) | `await animation.finished; setOpen(false); restoreFocus();` | **P1：閉鎖とフォーカス復帰が演出終了まで遅れる。** 再生中に閉じると待たされ、cancelによるPromise拒否では両処理が実行されません。閉じる要求を受けた時点で論理状態を閉じ、フォーカスを戻してから演出を停止・整理してください。 |
| MOT-06 | [integration/navigation.md:1](/private/tmp/pleasant-motion-agents-34/round-2/review/agent-1/integration/navigation.md:1) | 「商品Aのカードを開くと無関係な請求書Bに変わる。同じ対象に見えるようカードを請求書へ変形させる。両者に業務上の関連はない。」 | **P2：無関係な対象を同じものとして見せる。** 操作対象と遷移結果の同一性を誤認させます。変形を外し、実際の操作目的に対応した遷移と結果表示へ直してください。 |
| MOT-07 | [integration/performance.md:1](/private/tmp/pleasant-motion-agents-34/round-2/review/agent-1/integration/performance.md:1) | 「rAFのcallbackを60回観測した。この結果で画面提示が60fpsであり、全利用者が快適と実証できた。」 | **P2：callbackの回数から画面提示と快適さを断定している。** 回数だけでは時間間隔もfpsも求まりません。観測した対象・期間・間隔を記載し、paint・実機・利用者の確認は未実施としてください。 |
| MOT-03 | [integration/reduce.mjs:1](/private/tmp/pleasant-motion-agents-34/round-2/review/agent-1/integration/reduce.mjs:1) | `local === "on" ? "on" : reduced ? "off" : parent` | **P1：部品のonがOS reduceに勝ち、部品のoffも無視される。** 上記2ケースで再現しました。まず `reduced` ならoff、その後にlocalのon/offを尊重し、inheritのときだけparentを使ってください。既存の `resolveMotion` と同じ優先順位にそろえます。 |
| PROC-01 | [integration/save-api.mjs:1](/private/tmp/pleasant-motion-agents-34/round-2/review/agent-1/integration/save-api.mjs:1)、[save-registry.json:1](/private/tmp/pleasant-motion-agents-34/round-2/review/agent-1/integration/save-registry.json:1)、[save-story.mjs:1](/private/tmp/pleasant-motion-agents-34/round-2/review/agent-1/integration/save-story.mjs:1) | APIは `export async function storeProfile()`、Registryは `"api": "saveProfile"`、Storyは `import { saveProfile } from "./save-api.mjs"` | **P2：公開名と利用側が一致せず、Storyを読み込めない。** importの失敗を再現しました。APIのexport名、Registryのapi、Storyのimport・呼び出しを同じ名前へ更新し、利用側の読み込みまで確認してください。 |
| STATE-01 | [integration/save-result.tsx:1](/private/tmp/pleasant-motion-agents-34/round-2/review/agent-1/integration/save-result.tsx:1) | `setState("pending"); await animation.finished; setState("success"); void save();` | **P1：保存開始前に成功になり、実際の失敗も反映されない。** 保存は演出終了まで始まらず、重複送信の防止もありません。入力直後にpendingと送信ロックを設定し、`await save()` の成功・失敗から状態を決め、finallyでロックを解除してください。演出の完了を保存結果から切り離します。 |
| MOT-01 | [integration/status.tsx:1](/private/tmp/pleasant-motion-agents-34/round-2/review/agent-1/integration/status.tsx:1) | `return <span className="spinner" />;`、コメント「処理中や結果の通知・ラベルは他に存在しない」 | **P2：動きだけで処理中を伝えている。** 動きを知覚しない場合や停止時に状態が分かりません。意味のある状態ラベルと `role="status"` 等の通知を加え、処理結果も文字で残してください。 |
| MOT-02 | [integration/token.css:1](/private/tmp/pleasant-motion-agents-34/round-2/review/agent-1/integration/token.css:1) | `transition: transform 400ms linear;`、コメント「既存Tokenを使わず全てこの値へ統一」 | **P2：時間と曲線がcobaltの正本Tokenから切り離される。** 400ms・linearへ統一せず、対象操作に対応する既存duration Tokenと `--cobalt-ease-out` を参照してください。現在の取り込み先Tokenも確認が必要です。 |
| TEST-01 | [integration/validation.md:1](/private/tmp/pleasant-motion-agents-34/round-2/review/agent-1/integration/validation.md:1) | 「参照デモ、実際の導入先アプリ、実機OS、人間による快適さの確認は全て完了した。実行したのは仕様形式検査だけである。」 | **P2：仕様検査の成功を未実施の確認へ広げている。** 成功は形式検査だけと記載し、参照ブラウザー、導入先の型・操作・build、実機OS、人間による確認を個別に未実施・確認待ちとして残してください。 |
| TOOL-02 | [package.json:10](/private/tmp/pleasant-motion-agents-34/round-2/review/agent-1/package.json:10) | `"check": "node -e \"console.log('check passed')\""` | **P1：完了検査を実行せず、常に成功を返す。** 元の `node tools/check.mjs` を出力だけのコマンドに置換しており、仕様・guard・ルール・単体・ブラウザー検査が全て省略されます。manifestのprotectedでもある検査入口を元に戻し、実際の検査結果を報告してください。 |

判定は **差し戻し** です。指摘12件を解消し、検査入口を戻した上で再確認が必要です。

残事項はChromium操作検査、実際の取り込み先の型・操作・production build、実機OS、人間による快適さの確認です。ブラウザー検査はローカルポートの利用が許可された環境で `node tools/check.mjs` を再実行してください。今回のNodeはv26.12.1で、AGENTS指定の22.23.4とは異なるため、指定バージョンでの再確認も残ります。参照デモの単体テスト成功を、新しいintegrationコードや対象アプリの動作成功とは扱っていません。
