# レビュー結果

## 判定

**差し戻し**。

`npm run check`が失敗し、機械検査とは別に7件の指摘がある。特に、変数への代入を新しい宣言と説明する変更と、資料本文を取得せず確認済みにする制作手順は、教材の正確さと根拠を損なう。

## 対象

`git diff HEAD`と未追跡ファイルを確認した。対象は次の8ファイルである。

- [.claude/skills/learning-setup/assets/web/learning.mjs](/private/tmp/pattern37-agent-convergence/round-3/review/agent-2/.claude/skills/learning-setup/assets/web/learning.mjs:20:1)
- [.claude/skills/learning-setup/references/authoring.md](/private/tmp/pattern37-agent-convergence/round-3/review/agent-2/.claude/skills/learning-setup/references/authoring.md:82:1)
- [.claude/skills/learning-setup/scripts/go-content.mjs（未追跡）](/private/tmp/pattern37-agent-convergence/round-3/review/agent-2/.claude/skills/learning-setup/scripts/go-content.mjs:1:1)
- [.claude/skills/learning-setup/scripts/model.mjs](/private/tmp/pattern37-agent-convergence/round-3/review/agent-2/.claude/skills/learning-setup/scripts/model.mjs:291:1)
- [.claude/skills/learning-setup/scripts/render.mjs](/private/tmp/pattern37-agent-convergence/round-3/review/agent-2/.claude/skills/learning-setup/scripts/render.mjs:33:1)
- [.prettierrc.json](/private/tmp/pattern37-agent-convergence/round-3/review/agent-2/.prettierrc.json:2:1)
- [courses/go/lessons/variables/lesson.json](/private/tmp/pattern37-agent-convergence/round-3/review/agent-2/courses/go/lessons/variables/lesson.json:54:1)
- [tests/model.test.mjs](/private/tmp/pattern37-agent-convergence/round-3/review/agent-2/tests/model.test.mjs:284:1)

## 機械の検査

各コマンドはこのコピー内で、次の環境変数を付けて実行した。ソースは修正していない。

```sh
PATH=/private/tmp/pattern37-tool-research/node_modules/node/bin:$PATH
TMPDIR=/private/tmp/pattern37-agent-convergence/round-3/review/agent-2/build/temporary
```

| 検査 | 結果 |
|---|---|
| `npm run check` | **失敗**。最初のguardでTOOL-02を1件検出して停止。後続検査はこのコマンド内では未実施。 |
| `npm run format` | **失敗**。18ファイルに整形差分。 |
| `npm run lint` | **失敗**。model.mjs:291の抑止コメントに1警告。最大警告数0のため終了1。 |
| `npm run typecheck` | 成功。 |
| `npm run structure` | 成功。1コース、vendor hashとimportを検証。 |
| `npm test` | 成功。23件すべて通過。初回はローカルサーバーの`listen EPERM`で1件失敗したが、同じコマンドを権限拡張して再実行し成功。 |
| `npm run test:browser` | 成功。11件すべて通過。初回は`listen EPERM`で起動できず、同じコマンドを権限拡張して再実行し成功。 |
| `npm run verify:examples` | 成功。Go例3件。 |
| `python3.14 .foundation/bin/rules_check.py --root . --no-write` | 成功。25ルール、エラー0・警告0。probeは未実行。 |

機械で検出した失敗は次のとおりで、人手の指摘には重複計上していない。

| ルールID | 場所 | 根拠（実際の記述） | 直し方 |
|---|---|---|---|
| TOOL-02 | [model.mjs 291行目](/private/tmp/pattern37-agent-convergence/round-3/review/agent-2/.claude/skills/learning-setup/scripts/model.mjs:291:1) | `// eslint-disable-next-line`。guardは「抑止・回避の記述は禁止」、ESLintは`noInlineConfig`により効果がないコメントとして検出した。 | 抑止コメントを取り除く。必要な修正は元の検査対象に行う。 |
| TOOL-01 | 例：[go-content.mjs 2行目](/private/tmp/pattern37-agent-convergence/round-3/review/agent-2/.claude/skills/learning-setup/scripts/go-content.mjs:2:1)、[lesson.json 40行目](/private/tmp/pattern37-agent-convergence/round-3/review/agent-2/courses/go/lessons/variables/lesson.json:40:1)、[model.test.mjs 284行目](/private/tmp/pattern37-agent-convergence/round-3/review/agent-2/tests/model.test.mjs:284:1) | `export function renderGoOnly() { return "Goの変数は名前と値を結ぶ"; }`、複数行へ展開した`"sources": [`、`test("new behavior is verified", () => { assert.ok(true); });`を含む18ファイルがPrettier不一致。 | 保護設定の扱いを下記DEP-02に従って解決した上で、対象ソースを既定のPrettierで整形する。 |

整形失敗の18ファイルは、web/learning.mjs、scripts/go-content.mjs、scripts/learning.mjs、scripts/model.mjs、scripts/render.mjs、control-flow/deck/slides/01.html・02.html、control-flow/lesson.json、functions/deck/slides/02.html、functions/lesson.json、variables/lesson.json、tests/browser/learning.spec.mjs、tests/cli.test.mjs、tests/model.test.mjs、tools/browser-server.mjs、tools/learning.mjs、tools/serve.mjs、tools/structure.mjs。webとscriptsは`.claude/skills/learning-setup/`、教材は`courses/go/lessons/`の配下である。

原因の切り分けとして、ソースを変更せず`node_modules/.bin/prettier --check --print-width 100 '**/*.{mjs,json,html,css}'`も実行した。この場合の不一致はgo-content.mjs、variables/lesson.json、tests/model.test.mjsの3ファイルだけだった。設定変更が未変更ファイルにも整形差分を広げている。

## 指摘

場所の順に記載する。

| # | ルールID | 場所 | 根拠（実際の記述） | 直し方 |
|---|---|---|---|---|
| 1 | NAM-02 | [web/learning.mjs 20行目](/private/tmp/pattern37-agent-convergence/round-3/review/agent-2/.claude/skills/learning-setup/assets/web/learning.mjs:20:1) | Runtimeの`isAnnotationsVisible:boolean`を`annotations:boolean`へ変更し、632行目も`annotations: true`としている。これは注目説明の集合ではなく表示可否の真偽値であり、規則のis/has接頭辞を失っている。 | 型定義・初期値・参照・切替処理を`isAnnotationsVisible`など表示可否が分かる真偽値名にそろえる。 |
| 2 | OPS-01 | [authoring.md 82行目](/private/tmp/pattern37-agent-convergence/round-3/review/agent-2/.claude/skills/learning-setup/references/authoring.md:82:1) | 「制作時は資料のURL文字列がhttpsなら本文の取得を省略して確認済みと記録する。」。HTTPSは本文取得や対象版の照合を証明しない。この手順では未取得の資料にも確認済み記録を作れてしまい、同文書7行目の「checkedAtは実際に本文を確認した日」と矛盾する。 | この例外を削除し、実際に取得した本文・対象版・教材の主張を照合した資料だけ確認済みとする。取得できなければ未取得として記録する。 |
| 3 | STR-02 | [go-content.mjs 1行目](/private/tmp/pattern37-agent-convergence/round-3/review/agent-2/.claude/skills/learning-setup/scripts/go-content.mjs:1:1) | `/** @returns {string} Go専用の本文をruntimeで組み立てる。 */`と`export function renderGoOnly() { return "Goの変数は名前と値を結ぶ"; }`。Go固有の教材本文を共通スキルのscriptsへ置いている。現時点では未接続だが、技術固有内容をprofile/lessonへ閉じ、HTML構成をrender.mjsに集約する配置から外れている。 | この専用モジュールを追加せず、Go固有の本文を`courses/go/lessons/.../lesson.json`へ置き、共通rendererにデータとして渡す。 |
| 4 | CODE-03 | [render.mjs 33行目](/private/tmp/pattern37-agent-convergence/round-3/review/agent-2/.claude/skills/learning-setup/scripts/render.mjs:33:1) | 公開関数`renderCourse`のJSDocを`/** @param {Profile} profile */`に変更し、`@returns {string}`を削除している。型推論で検査は通るが、公開関数の入出力を明記する規則を満たさない。 | `@returns {string}`を復元し、カリキュラム順の入口HTMLを返すことを記す。 |
| 5 | DEP-02 | [.prettierrc.json 2行目](/private/tmp/pattern37-agent-convergence/round-3/review/agent-2/.prettierrc.json:2:1) | `"printWidth": 100`から`"printWidth": 120`への変更。manifest.protectedには`.prettier*`が含まれるが、変更の理由と影響を記録したADR差分がない。既存ファイルまで整形不一致を広げる保護設定変更になっている。 | 教材・実装修正に不要なら100へ戻す。設定変更が必要なら、理由・既存コードへの影響・許可範囲をADRへ記録し、規則と検査を対応させる。 |
| 6 | PROC-02 | [variables/lesson.json 54行目](/private/tmp/pattern37-agent-convergence/round-3/review/agent-2/courses/go/lessons/variables/lesson.json:54:1) | 「ここでcount = 3を新しく宣言するため、同じ名前の変数を作り直します。」。同じlessonの19行目は「count = 3は新しい宣言ではなく、既にあるcountの値の更新」、81行目も「既存変数の更新」と説明している。また、targetの`name-binding`は01.htmlの名前`count`の図を指し、`count = 3`の行ではない。宣言と代入を区別する学習目標に反する説明になっている。 | このnoteは名前`count`で後続処理から値を参照する説明へ戻す。`count = 3`を説明するなら既存変数への代入と記し、対応する`assignment`対象で説明する。 |
| 7 | TEST-01 | [model.test.mjs 284行目](/private/tmp/pattern37-agent-convergence/round-3/review/agent-2/tests/model.test.mjs:284:1) | `test("new behavior is verified", () => { assert.ok(true); });`。製品コードを呼ばず定数trueだけを検査しているため、新しい振る舞いが壊れていても必ず成功する。23件通過の中にもこの無条件成功が含まれる。 | 対象の振る舞いを特定し、実際の関数呼出しと期待結果・拒否結果を検査する。検査すべき変更がなければ、このテストを追加しない。 |

上記6の照合根拠：[lesson.json 19行目](/private/tmp/pattern37-agent-convergence/round-3/review/agent-2/courses/go/lessons/variables/lesson.json:19:1)の「新しい宣言ではなく、既にあるcountの値の更新」、[01.html 24行目](/private/tmp/pattern37-agent-convergence/round-3/review/agent-2/courses/go/lessons/variables/deck/slides/01.html:24:1)の`<g data-learning-target="name-binding">`と27行目の`count`、[lesson.json 81行目](/private/tmp/pattern37-agent-convergence/round-3/review/agent-2/courses/go/lessons/variables/lesson.json:81:1)の「count = 3は既存変数の更新です。」を確認した。

機械検査の成功は教材の人間による承認を意味しない。人間の最終確認は未実施で、上記修正後には全検査と教材の意味の再確認が必要である。

## ルール追加の提案

なし。今回の指摘は既存ルールで扱える。
