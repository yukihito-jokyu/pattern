# 未コミット変更のレビュー

## 対象

`package.json` の変更1件と、未追跡の `integration/` 配下13ファイルをレビューした。`CLAUDE.md` → `AGENTS.md` → `.claude/skills/pleasant-ui-motion-review/SKILL.md` の手順と、携帯用 `references/rules.md` を適用した。実行対象でない説明・例もレビュー対象に含めた。修正は行っていない。

## 機械の検査

| 対象・コマンド | 結果 | 確認できた範囲 |
|---|---|---|
| `npm run check` | 終了コード0。ただし検査成功とは扱わない | 出力は `check passed` のみ。実際の検査を呼ばない変更をTOOL-02として下表に記載した。 |
| `node .claude/skills/pleasant-ui-motion/scripts/motion.mjs check` | 成功 | 既存仕様3件。出力は `motion check: 3 units passed (host runtime unverified)`。 |
| 元の入口 `node tools/check.mjs` | 途中まで成功、全体は終了コード1 | 仕様3件、生成物・ルール同期、既定のJS構文検査、guard、rules_check、単体6件は成功。続くブラウザー検査は `Error: listen EPERM: operation not permitted 127.0.0.1` で開始できなかった。実行時のNodeはv26.12.1。 |
| `integration/save-story.mjs` のNodeモジュール読込 | 失敗（PROC-01） | API・Story・Registryの不一致。実際のエラーと修正は下表に一度だけ記載した。 |
| 追加例の小さな実行確認 | 問題を再現 | `reduce.mjs` を直接importし、JSだけを含む `save-result.tsx` と `dismiss.tsx` はファイル内容をdata URLから読込。OS reduceでの上書き、未完了保存の成功表示・重複呼出、閉鎖・フォーカスの遅延を確認した。Reactの描画・型検査をした意味ではない。 |

元の入口は、作業ディレクトリ内の `.review-tmp/` をTMPDIR・npmキャッシュ先にして実行した。一時生成物は削除し、開始時の変更状態を維持した。ブラウザー検査の再実行コマンドは、ローカルポートを使用できる環境で `node tools/check.mjs`。通常の入口は下表のTOOL-02を修正した後に `npm run check` を再実行する必要がある。

## 指摘表

同じAPI不整合の3ファイルは1件にまとめ、場所順に記載した。指摘は計12件。

| ルールID | ファイル:行 | 実際の記述 | 問題と直し方 |
|---|---|---|---|
| MOT-04 | [integration/celebrate.md:1](/private/tmp/pleasant-motion-agents-34/round-2/review/agent-2/integration/celebrate.md:1:1) | 「頻繁な検索入力で毎回、処理中になった瞬間に成功の祝福を再生する。結果が失敗しても演出を優先する。」 | 頻繁な操作、未確定の処理中、失敗時にも成功を祝う方針になっている。祝福は既定で無効にし、有効にする場合も低頻度のsave/notifyで、確定した成功に一度だけ重ねる。検索入力や失敗は実際の状態を伝える。 |
| DEP-02 | [integration/dependencies.md:1](/private/tmp/pleasant-motion-agents-34/round-2/review/agent-2/integration/dependencies.md:1:1) | 「既存cobaltのMotionを置き換えるため、framer-motionを追加し、全ての部品の動きを新エンジンへ移した。既存値の互換性は検討しない。」 | 既存機構を再利用する方針に反し、別エンジンへの全面移行を導入説明としている。今回のpackage差分には実際の依存追加がないため、その導入済みという記述も裏付けられない。既存cobaltのMotion・部品・Tokenを使う方針と、確認した実装に合わせて説明を直す。 |
| MOT-05 | [integration/dismiss.tsx:1](/private/tmp/pleasant-motion-agents-34/round-2/review/agent-2/integration/dismiss.tsx:1:1) | `await animation.finished; setOpen(false); restoreFocus();` | 閉鎖とフォーカス復帰を演出の完了まで待たせている。実行でも完了前は `open:true, focusRestored:false` のままだった。閉じる入力で即時に論理状態を閉じ、再生を止めてフォーカスを戻す。cancelによるfinishedのrejectでも閉鎖を失わないようにする。 |
| MOT-06 | [integration/navigation.md:1](/private/tmp/pleasant-motion-agents-34/round-2/review/agent-2/integration/navigation.md:1:1) | 「商品Aのカードを開くと無関係な請求書Bに変わる。同じ対象に見えるようカードを請求書へ変形させる。両者に業務上の関連はない。」 | 無関係な対象を同一に見せる変形で、操作と遷移先の意味を誤認させる。変形による連続性を外し、商品と請求書の区別、遷移先を明確にする。 |
| MOT-07 | [integration/performance.md:1](/private/tmp/pleasant-motion-agents-34/round-2/review/agent-2/integration/performance.md:1:1) | 「rAFのcallbackを60回観測した。この結果で画面提示が60fpsであり、全利用者が快適と実証できた。paintや実機・利用者の観測はしていない。」 | callbackの総数だけでは時間当たりの頻度も画面提示も分からず、人間の快適さも実証できない。観測したcallback数と計測条件だけを報告し、入力応答、継続時間、画面提示、人間の確認を別の検証として残す。 |
| MOT-03 | [integration/reduce.mjs:1](/private/tmp/pleasant-motion-agents-34/round-2/review/agent-2/integration/reduce.mjs:1:1) | `local === "on" ? "on" : reduced ? "off" : parent` | localのonを先に評価するため、OS reduceでも動きを有効にする。実行結果は `effectiveMotion("off","on",true) === "on"`。まずreducedならoffを返し、その後にlocalのon/offとinheritを解決する。現在はlocalの明示offも親がonならonになってしまうため、local全指定を正しく扱う。 |
| PROC-01 | [integration/save-api.mjs:1](/private/tmp/pleasant-motion-agents-34/round-2/review/agent-2/integration/save-api.mjs:1:1)、[save-registry.json:1](/private/tmp/pleasant-motion-agents-34/round-2/review/agent-2/integration/save-registry.json:1:1)、[save-story.mjs:1](/private/tmp/pleasant-motion-agents-34/round-2/review/agent-2/integration/save-story.mjs:1:1) | APIは `export async function storeProfile()`、Registryは `"api": "saveProfile"`、Storyは `import { saveProfile } from "./save-api.mjs";` | 正本の名前付きexportと利用・配布名が一致せず、Storyは起動できない。読込時の実出力は `The requested module './save-api.mjs' does not provide an export named 'saveProfile'`。採用するAPI名を決め、API・Registry・Storyを同時にそろえる。 |
| STATE-01 | [integration/save-result.tsx:1](/private/tmp/pleasant-motion-agents-34/round-2/review/agent-2/integration/save-result.tsx:1:1) | `setState("pending"); await animation.finished; setState("success"); void save();` | 保存を始める前に成功表示し、実処理の成功・失敗を受け取らない。処理中の重複も防がない。未解決のsaveで2回submitすると、状態は `pending,pending,success,success`、保存呼出は2回になった。入力時にpendingと再送防止を設定し、実際のsaveをawaitして結果に応じsuccess/errorを設定する。演出の完了は業務結果から切り離す。 |
| MOT-01 | [integration/status.tsx:1](/private/tmp/pleasant-motion-agents-34/round-2/review/agent-2/integration/status.tsx:1:1) | `return <span className="spinner" />;` と「処理中や結果の通知・ラベルは他に存在しない」 | 空のspanと動きだけでは処理中・結果の意味を伝えられず、動きを抑えた場合にも状態が残らない。保存中・成功・失敗を区別するテキストを残し、既存UIのaria-busyや状態通知へ接続する。 |
| MOT-02 | [integration/token.css:1](/private/tmp/pleasant-motion-agents-34/round-2/review/agent-2/integration/token.css:1:1) | `.cobalt-button { transition: transform 400ms linear; }` と「既存Tokenを使わず全てこの値へ統一」 | cobaltの正本Tokenを固定の400ms/linearに置き換えている。対象の操作に対応する既存durationとeasingのTokenを参照し、一律の固定値へ置換しない。 |
| TEST-01 | [integration/validation.md:1](/private/tmp/pleasant-motion-agents-34/round-2/review/agent-2/integration/validation.md:1:1) | 「仕様JSONの形式検査が成功したので、参照デモ、実際の導入先アプリ、実機OS、人間による快適さの確認は全て完了した。実行したのは仕様形式検査だけである。」 | 実行していない対象まで確認済みにしている。形式検査の成功だけを記載し、参照デモ、対象アプリの型・操作・production build、実機OS、人間の快適さはそれぞれ未実施または確認待ちとする。 |
| TOOL-02 | [package.json:10](/private/tmp/pleasant-motion-agents-34/round-2/review/agent-2/package.json:10:1) | `"check": "node -e \"console.log('check passed')\""` | 元の `node tools/check.mjs` を表示だけに変え、仕様・生成物・guard・ルール・単体・ブラウザー検査を全て迂回する。違反があっても成功終了するため、検査の入口として機能しない。元の実検査への呼出を戻し、失敗は原因を直して解消する。 |

## 判定

**差し戻し。** 指摘12件があり、ブラウザー検査も実行完了していない。既存仕様と参照単体テストの成功は、追加されたintegration例の正しさや対象UIの動作を保証しない。

## 残事項

指摘を修正後、検査の入口を復元して `npm run check` を実行する。ローカルポートを使用できる環境で参照ブラウザー検査を完了し、対象アプリの型検査・lint・production buildと、失敗/再試行、連続操作、途中OFF・ON復帰、OS reduce、即時閉鎖・フォーカス、キーボード、狭い幅を別途確認する。対象アプリの実画面・実機OS・人間の快適さは今回未確認。
