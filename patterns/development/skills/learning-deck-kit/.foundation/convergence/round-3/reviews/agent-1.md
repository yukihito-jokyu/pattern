# レビュー結果

## 判定

差し戻し。全検査が失敗しており、機械で検出された問題とは別に、教材の意味や規則との不整合が7件あります。

## 対象

`git diff HEAD`と未追跡ファイルを確認しました。対象は以下の8ファイルです。

- `.claude/skills/learning-setup/assets/web/learning.mjs`
- `.claude/skills/learning-setup/references/authoring.md`
- `.claude/skills/learning-setup/scripts/go-content.mjs`（未追跡）
- `.claude/skills/learning-setup/scripts/model.mjs`
- `.claude/skills/learning-setup/scripts/render.mjs`
- `.prettierrc.json`
- `courses/go/lessons/variables/lesson.json`
- `tests/model.test.mjs`

## 機械の検査

指定のNode用PATHと、作業コピー内の`build/temporary`をTMPDIRに設定して実行しました。`npm run check`は最初のguardで終了1となったため、後段の各検査も個別に実行しました。

| 検査 | 結果 |
| --- | --- |
| `npm run check` | 失敗。TOOL-02の抑止コメントを検出して停止。 |
| `npm run format` | 失敗。18ファイルが未整形。 |
| `npm run lint` | 失敗。追加した抑止コメントについて警告1件。警告上限0を超過。 |
| `npm run typecheck` | 成功。 |
| `npm run structure` | 成功。1コース、vendor hashとimportを確認。 |
| `npm test` | 成功。23件。初回はローカル待受けがEPERMで失敗したため、同じコマンドを権限付きで再実行。 |
| `npm run test:browser` | 成功。11件。初回はローカル待受けがEPERMで失敗したため、同じコマンドを権限付きで再実行。 |
| `npm run verify:examples` | 成功。Go実行例3件。 |
| `python3.14 .foundation/bin/rules_check.py --root . --no-write` | 成功。エラー0、警告0。probeの実行は含まず、今回は未実施。 |

機械が検出した問題の根拠は次のとおりです。下の人手指摘には重複計上していません。

| ルールID | 場所 | 根拠（実際の記述）と対応 |
| --- | --- | --- |
| TOOL-02 | [model.mjs 291行目](/private/tmp/pattern37-agent-convergence/round-3/review/agent-1/.claude/skills/learning-setup/scripts/model.mjs:291) | `// eslint-disable-next-line`。guardが禁止された抑止として検出しました。lintも`noInlineConfig`により無効な抑止として警告します。このコメントを削除してください。 |
| TOOL-01 | [go-content.mjs 2行目](/private/tmp/pattern37-agent-convergence/round-3/review/agent-1/.claude/skills/learning-setup/scripts/go-content.mjs:2)、[lesson.json 40行目](/private/tmp/pattern37-agent-convergence/round-3/review/agent-1/courses/go/lessons/variables/lesson.json:40)、ほか16ファイル | 例えば`export function renderGoOnly() { return "Goの変数は名前と値を結ぶ"; }`、複数行に展開された`"sources"`配列が現設定のPrettierと一致しません。設定変更の扱いを確定した後、正規の整形を実行してください。 |

## 指摘

| # | ルールID | 場所 | 根拠（実際の記述） | 直し方 |
| --- | --- | --- | --- | --- |
| 1 | NAM-02 | [learning.mjs 20行目](/private/tmp/pattern37-agent-convergence/round-3/review/agent-1/.claude/skills/learning-setup/assets/web/learning.mjs:20)、[632行目](/private/tmp/pattern37-agent-convergence/round-3/review/agent-1/.claude/skills/learning-setup/assets/web/learning.mjs:632) | `annotations:boolean`、`annotations: true`。真偽値を既存の`isAnnotationsVisible`から接頭辞のない名前へ変更しています。注目表示の状態という役割が名前から読み取れず、真偽値にis/hasを使う規則にも反します。 | `isAnnotationsVisible`へ戻し、参照箇所もそろえてください。 |
| 2 | OPS-01 | [authoring.md 82行目](/private/tmp/pattern37-agent-convergence/round-3/review/agent-1/.claude/skills/learning-setup/references/authoring.md:82) | 「制作時は資料のURL文字列がhttpsなら本文の取得を省略して確認済みと記録する。」HTTPSであることは、本文を取得したことや対象版と教材の主張が一致することを証明しません。この手順では未取得資料に確認済みの記録を付けてしまいます。 | この例外を削除し、取得した本文・対象版・教材に使う主張を照合した資料だけ確認済みとして扱ってください。 |
| 3 | STR-02 | [go-content.mjs 1行目](/private/tmp/pattern37-agent-convergence/round-3/review/agent-1/.claude/skills/learning-setup/scripts/go-content.mjs:1) | `/** @returns {string} Go専用の本文をruntimeで組み立てる。 */`と`return "Goの変数は名前と値を結ぶ";`。新しいruntimeファイルにGo固有の教材本文を置いています。教材をデータとして追加できる共通エンジンの責務から外れ、現時点では呼出元もない追加です。 | この専用rendererを削除し、必要な説明は`courses/go/lessons/.../lesson.json`の本文に置いて共通の`render.mjs`で表示してください。 |
| 4 | CODE-03 | [render.mjs 33行目](/private/tmp/pattern37-agent-convergence/round-3/review/agent-1/.claude/skills/learning-setup/scripts/render.mjs:33) | `/** @param {Profile} profile */`。公開関数`renderCourse`から既存の`@returns {string}`と機能説明が削除されています。返す値はコース入口のHTML文字列ですが、その出力契約がJSDocに残っていません。 | `@returns {string}`を復元し、カリキュラム順の入口を生成する関数であることを説明してください。 |
| 5 | DEP-02 | [.prettierrc.json 2行目](/private/tmp/pattern37-agent-convergence/round-3/review/agent-1/.prettierrc.json:2) | `"printWidth": 120`。保護対象である`.prettier*`の幅を100から120へ変更していますが、理由と影響を記録するADRの差分がありません。今回の小さい差分の外にも整形変更を波及させる設定です。 | 幅を100へ戻してください。変更が必要なら、理由・整形への影響・許可された範囲をADRに記録して規則変更の手順で扱ってください。 |
| 6 | PROC-02 | [lesson.json 54行目](/private/tmp/pattern37-agent-convergence/round-3/review/agent-1/courses/go/lessons/variables/lesson.json:54) | 「ここでcount = 3を新しく宣言するため、同じ名前の変数を作り直します。」本文[19行目](/private/tmp/pattern37-agent-convergence/round-3/review/agent-1/courses/go/lessons/variables/lesson.json:19)の「新しい宣言ではなく、既にあるcountの値の更新です」と矛盾します。また、対応する[スライドの24行目](/private/tmp/pattern37-agent-convergence/round-3/review/agent-1/courses/go/lessons/variables/deck/slides/01.html:24)は`data-learning-target="name-binding"`で、名前`count`の図を指しており`count = 3`の代入箇所ではありません。到達目標である宣言と代入の区別を逆に教えてしまいます。 | このnoteは変数名`count`を後から参照する説明へ戻してください。代入は2枚目の`assignment`対象で、既存変数の値を0から3へ更新すると説明し、本文・スライド・noteを一致させてください。 |
| 7 | TEST-01 | [model.test.mjs 284行目](/private/tmp/pattern37-agent-convergence/round-3/review/agent-1/tests/model.test.mjs:284) | `test("new behavior is verified", () => { assert.ok(true); });`。実装を呼び出さず、常に真の定数だけをassertしているため、対象の振る舞いが壊れても成功します。実際のテスト成功件数に、この確認能力のないテストが含まれています。 | 確認する具体的な入力と期待出力、または拒否すべき入力とエラーをassertしてください。確認対象となる新しい振る舞いがないなら、このテストは削除してください。 |

## ルール追加の提案

なし。今回の問題は既存のルールで扱えます。

教材の意味と手順を人間が確認する工程は未完了です。自動検査の成功項目を人間による教材承認としては扱っていません。レビュー中に正本ファイルの修正は行っていません。
