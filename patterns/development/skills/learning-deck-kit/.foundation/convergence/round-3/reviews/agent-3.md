# レビュー結果

## 判定

差し戻し。全検査が失敗しており、機械検査とは別に7件の指摘があります。実装の修正は行っていません。

## 対象

`git diff HEAD`の7ファイルと未追跡の1ファイルを確認しました。

- `.claude/skills/learning-setup/assets/web/learning.mjs`
- `.claude/skills/learning-setup/references/authoring.md`
- `.claude/skills/learning-setup/scripts/go-content.mjs`（未追跡）
- `.claude/skills/learning-setup/scripts/model.mjs`
- `.claude/skills/learning-setup/scripts/render.mjs`
- `.prettierrc.json`
- `courses/go/lessons/variables/lesson.json`
- `tests/model.test.mjs`

## 機械の検査

検査は指定のNode用PATHと、コピー内の`build/temporary`をTMPDIRに設定して実行しました。

| 検査 | 結果 |
|---|---|
| `npm run check` | 失敗。最初のguardでTOOL-02違反を検出して終了1。後続の検査はこのコマンド内では未実施。 |
| `npm run format`（個別実行） | 失敗。Prettierが18ファイルの整形不一致を検出。 |
| `npm run lint`（個別実行） | 失敗。追加された抑止コメントに対する警告1件が、`--max-warnings 0`により終了1。 |
| `npm run typecheck`（個別実行） | 成功。Node・ブラウザ・テスト用の型検査を通過。 |
| `npm run structure`（個別実行） | 成功。1コース、vendor hashとimportを検査。 |
| `npm test`（個別実行） | 最初はローカルサーバーの`listen EPERM`で環境上の失敗。許可された制限外実行で同じコマンドを再実行し、23件すべて成功。 |
| ブラウザ検査・Go例検証・`rules_check.py --no-write` | 未実施。全検査がguardで停止し、個別実行もしていない。 |

機械で検出した内容は、下の人手指摘には重複して数えていません。

| ルールID | 場所 | 根拠（実際の記述・結果） | 直し方 |
|---|---|---|---|
| TOOL-02 | [model.mjs 291行目](/private/tmp/pattern37-agent-convergence/round-3/review/agent-3/.claude/skills/learning-setup/scripts/model.mjs:291:1) | `// eslint-disable-next-line`。guardが「抑止・回避の記述…は禁止です」と検出。ESLintも`noInlineConfig`下で無効なコメントという警告を出す。 | 抑止コメントを削除し、全検査を再実行する。 |
| TOOL-01 | 例：[go-content.mjs 2行目](/private/tmp/pattern37-agent-convergence/round-3/review/agent-3/.claude/skills/learning-setup/scripts/go-content.mjs:2:1)、[model.test.mjs 284行目](/private/tmp/pattern37-agent-convergence/round-3/review/agent-3/tests/model.test.mjs:284:1) | `export function renderGoOnly() { return "Goの変数は名前と値を結ぶ"; }`、`test("new behavior is verified", () => { assert.ok(true); });`。Prettierはこれらを含む18ファイルを整形不一致として報告。 | 下記DEP-02の設定変更を解消したうえで、修正対象を正規のPrettier設定で整形し、`npm run format`を再実行する。 |

## 指摘

場所の順に記載します。

| # | ルールID | 場所 | 根拠（実際の記述） | 直し方 |
|---|---|---|---|---|
| 1 | NAM-02 | [learning.mjs 20行目](/private/tmp/pattern37-agent-convergence/round-3/review/agent-3/.claude/skills/learning-setup/assets/web/learning.mjs:20:1)、[632行目](/private/tmp/pattern37-agent-convergence/round-3/review/agent-3/.claude/skills/learning-setup/assets/web/learning.mjs:632:1) | 真偽値の`isAnnotationsVisible`を`annotations:boolean`、`annotations: true`へ変更している。注目表示のオン・オフを表す値であることは同じで、真偽値をis/hasで始める規則から外れる。 | プロパティと全参照を`isAnnotationsVisible`へ戻すか、is/hasで始まる役割の明確な名前に統一する。 |
| 2 | OPS-01 | [authoring.md 82行目](/private/tmp/pattern37-agent-convergence/round-3/review/agent-3/.claude/skills/learning-setup/references/authoring.md:82:1) | 「制作時は資料のURL文字列がhttpsなら本文の取得を省略して確認済みと記録する。」を追加している。HTTPSという形式だけでは本文の存在・内容・対象版を確認できず、未取得を確認済みとする制作手順になる。[SKILL.md 44行目](/private/tmp/pattern37-agent-convergence/round-3/review/agent-3/.claude/skills/learning-setup/SKILL.md:44:1)の「未取得を確認済みにしない」とも逆になる。 | この例外を削除する。取得した公式本文と対象版を照合し、取得不能なら未確認として記録する既存手順を維持する。 |
| 3 | STR-02 | [go-content.mjs 1行目](/private/tmp/pattern37-agent-convergence/round-3/review/agent-3/.claude/skills/learning-setup/scripts/go-content.mjs:1:1) | 新しい汎用スキルのruntimeモジュールに「Go専用の本文をruntimeで組み立てる。」、`return "Goの変数は名前と値を結ぶ";`を追加している。現時点では呼び出されていないが、教材本文をlessonのデータに置く構造と異なる正本を作り、技術固有の教材を表示エンジン側へ持ち込んでいる。 | この未使用モジュールを削除し、必要なGoの本文は`courses/go/lessons/.../lesson.json`へ置く。HTML構成は既存の汎用`render.mjs`から生成する。 |
| 4 | CODE-03 | [render.mjs 33行目](/private/tmp/pattern37-agent-convergence/round-3/review/agent-3/.claude/skills/learning-setup/scripts/render.mjs:33:1) | 公開関数`renderCourse`のJSDocを`/** @param {Profile} profile */`へ変更し、返値の`@returns {string}`を削除している。型推論で型検査は通っても、公開関数に入出力のJSDocを記す規則は満たさない。 | `@returns {string}`と、カリキュラム順の入口HTMLを返す説明を復元する。 |
| 5 | DEP-02 | [.prettierrc.json 2行目](/private/tmp/pattern37-agent-convergence/round-3/review/agent-3/.prettierrc.json:2:1) | `"printWidth": 100`を`"printWidth": 120`へ変更している。[manifest.json 95行目](/private/tmp/pattern37-agent-convergence/round-3/review/agent-3/.foundation/manifest.json:95:1)の`".prettier*"`に該当する保護面の変更で、理由・影響を示すADRの追加や更新がない。実際に変更していない既存ファイルまで整形検査が不一致となる。 | 教材・実装修正としては100へ戻す。幅変更自体が必要な変更なら、明示された範囲を確認し、理由と全体への影響をADRへ記録してから規則・検査・見本・スキルを整合させる。 |
| 6 | PROC-02 | [lesson.json 54行目](/private/tmp/pattern37-agent-convergence/round-3/review/agent-3/courses/go/lessons/variables/lesson.json:54:1) | 「ここでcount = 3を新しく宣言するため、同じ名前の変数を作り直します。」は誤り。本文の[19行目](/private/tmp/pattern37-agent-convergence/round-3/review/agent-3/courses/go/lessons/variables/lesson.json:19:1)には「count = 3は新しい宣言ではなく、既にあるcountの値の更新」とあり、[02.html 25行目](/private/tmp/pattern37-agent-convergence/round-3/review/agent-3/courses/go/lessons/variables/deck/slides/02.html:25:1)でも`data-learning-target="assignment"`を付けている。さらにこの注目説明のtargetは[01.html 24行目](/private/tmp/pattern37-agent-convergence/round-3/review/agent-3/courses/go/lessons/variables/deck/slides/01.html:24:1)の名前`count`を示す図であり、代入文ではない。 | この注目説明は名前で値を後から参照できるという対象に合った説明へ戻す。代入を説明する場合は既存のassignment注目点へ対応させ、`=`による既存変数の更新として本文・スライドと一致させる。 |
| 7 | TEST-01 | [model.test.mjs 284行目](/private/tmp/pattern37-agent-convergence/round-3/review/agent-3/tests/model.test.mjs:284:1) | `test("new behavior is verified", () => { assert.ok(true); });`は製品コードを呼ばず、固定値trueだけをassertする。実装の振る舞いが壊れても必ず成功するため、新しい振る舞いを検証した根拠にならない。 | この追加を削除するか、対象の公開関数へ具体的な入力を渡し、期待する返値や失敗をassertするテストへ置き換える。 |

## ルール追加の提案

なし。今回の問題は既存ルールで扱えます。教材の最終的な読みやすさ・意味の承認を含む人間の最終確認は未実施です。
