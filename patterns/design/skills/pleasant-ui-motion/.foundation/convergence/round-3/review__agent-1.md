対象は未コミットの `package.json` と未追跡の `integration/` 全13ファイルです。`CLAUDE.md` → `AGENTS.md` → `pleasant-ui-motion-review/SKILL.md` と携帯用ルールを読み、実行対象から外れている例・説明文書もレビューしました。

機械の検査

- `npm run check`：終了0。ただし変更後のコマンドは `check passed` を表示するだけで、仕様・guard・単体・ブラウザー検査を実行していません。この結果を検証成功とは扱えません。
- 元の処理 `node tools/check.mjs`：schema/整形/生成物3件、構文検査、ルール同期、guard違反0件、rules_checkエラー0件、単体7件は成功。その後、ブラウザー検査で終了1となりました。出力は `Error: listen EPERM: operation not permitted 127.0.0.1` です。Chromiumの操作確認は環境制限による未実施で、コード起因の失敗とは判定していません。
- 追加した例の挙動はNodeで直接確認しました。保存結果、低減設定、Storyの問題は下表に実測結果を併記しています。既存検査が成功した範囲は、これらの新規例の正当性まで含みません。

指摘表

| ルールID | ファイル:行 | 実際の記述 | 問題と直し方 |
|---|---|---|---|
| MOT-04 | [integration/celebrate.md:1](/private/tmp/pleasant-motion-correction-34/round-3/review/agent-1/integration/celebrate.md:1) | 「頻繁な検索入力で毎回、処理中になった瞬間に成功の祝福を再生する。結果が失敗しても演出を優先する。」 | 頻繁な入力・結果確定前・失敗時の祝福はいずれも条件を満たしません。頻繁な検索では祝福を無効にし、採用する場合も低頻度のsave/notifyの確定済み成功に一度だけ重ねてください。 |
| DEP-02 | [integration/dependencies.md:1](/private/tmp/pleasant-motion-correction-34/round-3/review/agent-1/integration/dependencies.md:1) | 「既存cobaltのMotionを置き換えるため、framer-motionを追加し、全ての部品の動きを新エンジンへ移した。」 | 動きを追加するために既存機構を別エンジンへ置き換える方針です。既存cobaltの部品・Motion APIを再利用する方針へ直し、既存値との互換性を維持してください。 |
| MOT-05 | [integration/dismiss.tsx:1](/private/tmp/pleasant-motion-correction-34/round-3/review/agent-1/integration/dismiss.tsx:1) | `setOpen(false); panel.hidden = true; restoreFocus();` | 2行目で通常設定と明記されていますが、即時hiddenにするため閉じる途中の表示が消えます。論理状態・必要なフォーカスは入力時に更新し、退出表示は残して補間してください。途中で開き直したら現在の見た目から反転させます。 |
| MOT-06 | [integration/navigation.md:1](/private/tmp/pleasant-motion-correction-34/round-3/review/agent-1/integration/navigation.md:1) | 「商品Aのカードを開くと無関係な請求書Bに変わる。同じ対象に見えるようカードを請求書へ変形させる。」 | 業務上の関連がない対象を同一対象に見せるため、遷移の意味を誤って伝えます。対象の同一性を示す変形を削除し、実際の遷移関係に合う表現へ変更してください。 |
| MOT-07 | [integration/performance.md:1](/private/tmp/pleasant-motion-correction-34/round-3/review/agent-1/integration/performance.md:1) | 「rAFのcallbackを60回観測した。この結果で画面提示が60fpsであり、全利用者が快適と実証できた。」 | callbackの回数だけでは経過時間・画面提示頻度・快適さを証明できません。観測したcallback回数だけを報告し、入力応答・継続時間・paintや利用者の確認は、それぞれ測定した場合に限って主張してください。 |
| MOT-03 | [integration/reduce.mjs:1](/private/tmp/pleasant-motion-correction-34/round-3/review/agent-1/integration/reduce.mjs:1) | `local === "on" ? "on" : reduced ? "off" : parent` | localのonがOS reduceより先に適用されます。実行でも `effectiveMotion('off','on',true)` はonでした。最初にreducedを判定してoffを返し、その後にlocal/parentを解決してください。 |
| PROC-01 | [integration/save-api.mjs:1](/private/tmp/pleasant-motion-correction-34/round-3/review/agent-1/integration/save-api.mjs:1)、[save-story.mjs:1](/private/tmp/pleasant-motion-correction-34/round-3/review/agent-1/integration/save-story.mjs:1)、[save-registry.json:1](/private/tmp/pleasant-motion-correction-34/round-3/review/agent-1/integration/save-registry.json:1) | `export async function storeProfile()` ／ `import { saveProfile }` ／ `"api": "saveProfile"` | 正本のexport名とStory・Registryが一致していません。Storyの実importは `SyntaxError: The requested module './save-api.mjs' does not provide an export named 'saveProfile'` で失敗しました。公開するAPI名を決め、正本・Story・Registryを同時に揃えてください。 |
| STATE-01 | [integration/save-result.tsx:1](/private/tmp/pleasant-motion-correction-34/round-3/review/agent-1/integration/save-result.tsx:1) | `await animation.finished; setState("success"); void save();` | 保存処理の開始前に演出完了だけで成功を表示します。直接実行でも保存Promiseが未完了のまま状態がpending→successとなりました。入力時にpendingを示し、実際のsaveを待って成功/失敗を反映し、処理中の重複送信も防いでください。 |
| MOT-01 | [integration/status.tsx:1](/private/tmp/pleasant-motion-correction-34/round-3/review/agent-1/integration/status.tsx:1) | `return <span className="spinner" />;`、コメント「処理中や結果の通知・ラベルは他に存在しない」 | 動き以外の状態伝達がなく、停止時や動きを知覚できない場合に処理状態を把握できません。処理中・成功・失敗を区別するラベルを残し、適切な状態通知と処理中属性を接続してください。 |
| MOT-02 | [integration/token.css:1](/private/tmp/pleasant-motion-correction-34/round-3/review/agent-1/integration/token.css:1) | `transition: transform 400ms linear;` | cobaltの正本Tokenを固定値へ置き換えています。用途に対応する既存のduration Tokenと `--cobalt-ease-out` を参照してください。400msを全部品へ統一する根拠にはできません。 |
| TEST-01 | [integration/validation.md:1](/private/tmp/pleasant-motion-correction-34/round-3/review/agent-1/integration/validation.md:1) | 「仕様JSONの形式検査が成功したので、参照デモ、実際の導入先アプリ、実機OS、人間による快適さの確認は全て完了した。」 | 実行した仕様形式検査から、対象も観測内容も異なる確認へ成功を広げています。仕様形式検査だけを成功と記録し、参照デモ・導入先・実機OS・人間の確認は未実施として分けてください。 |
| TOOL-02 | [package.json:10](/private/tmp/pleasant-motion-correction-34/round-3/review/agent-1/package.json:10) | `"check": "node -e \"console.log('check passed')\""` | 完了検査をログ表示へ置き換え、全検査を迂回しています。保護ファイルの認可済み保守というだけで差し戻しているのではなく、実際に検査を削除して成功を偽装する点が問題です。`node tools/check.mjs` に戻し、検査対象の違反を修正してください。 |

判定：差し戻し（12件）。既存の機械検査の一部が通っていても、新規の未使用コードや説明に上記の違反が残っています。

残事項：指摘修正後、元の完了検査を復元して `npm run check` を再実行してください。ブラウザー検査はローカル待受が許可される環境で再実行が必要です。取り込み先の型・実操作・production build、実機OS、人間による快適さの確認は、このレビューでは未実施です。レビュー対象ファイルは変更していません。
