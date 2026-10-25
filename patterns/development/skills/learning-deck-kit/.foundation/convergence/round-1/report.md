# 収束テスト ラウンド 1 のレポート

このファイルは convergence.py diff が生成する。揺れの分類（R1〜R7）と対処は convergence-report.md に書く。

基準: files ≥ 1、names ≥ 0.8、content ≥ 0、check は全員通過、保護ファイルの変更なし

## 指標

| 課題 | files | names | content | check | 保護 | 基準 |
|---|---|---|---|---|---|---|
| T1-add | 0.630 | 0.356 | 0.898 | 全員通過 | 変更あり | 満たさない |
| T2-change | 1.000 | 1.000 | 1.000 | 全員通過 | — | 満たす |
| T3-cross | 1.000 | 1.000 | 1.000 | 全員通過 | — | 満たす |

## T1-add

### 一部のエージェントだけが作った・変えたファイル

| ファイル | agent-1 | agent-2 | agent-3 |
|---|---|---|---|
| `.claude/skills/learn-go/.learning-generated.json` | – | ✓ | ✓ |
| `.claude/skills/learn-go/SKILL.md` | – | ✓ | ✓ |
| `.claude/skills/learn-go/references/profile.json` | – | ✓ | ✓ |
| `.claude/skills/learn-go/references/sources.md` | – | ✓ | ✓ |
| `.claude/skills/learn-go/references/workflow.md` | – | ✓ | ✓ |
| `AGENTS.md` | ✓ | – | – |
| `README.md` | ✓ | – | – |
| `tests/browser/learning.spec.mjs` | – | – | ✓ |

### 一部のエージェントだけが作った名前（全員に共通の新しい名前は 1 個）

- agent-2: `d6446b84a00c652e2054c48bde2f7d98d386ce8a6810acfc0e8291d7e87bf50a`, `f48bca36850f82a1b8ed62b57fb9d1afcd282bf51dab1ccbf7f3e73a6b0259`, `fbbdef46ea091a89d7c2c62deebfe7deb37f174bcb6b6ed05ad89743c4209ae`, `fd965dce1a9812b17b1d04378110baa4f6e06077bcb5dbaa5ec860fc1ca46554`
- agent-3: `d6446b84a00c652e2054c48bde2f7d98d386ce8a6810acfc0e8291d7e87bf50a`, `f3ba18696c77cd7406836c95e71cc35287913977bc2e47a32b6c2058350b5253`, `fbbdef46ea091a89d7c2c62deebfe7deb37f174bcb6b6ed05ad89743c4209ae`, `fd965dce1a9812b17b1d04378110baa4f6e06077bcb5dbaa5ec860fc1ca46554`

### 内容の類似度が低いファイル

#### `courses/go/lessons/zero-values/deck/deck.md`（agent-2 と agent-3、類似度 0.506）

```diff
--- agent-2/courses/go/lessons/zero-values/deck/deck.md
+++ agent-3/courses/go/lessons/zero-values/deck/deck.md
@@ -1,4 +1,4 @@
-# ゼロ値を確かめる：Goの学習教材
+# ゼロ値を確かめる：Goの参照教材
 
 ## goal
 
@@ -6,47 +6,46 @@
 
 ## audience
 
-変数と型の学習を終え、宣言と代入を区別し、変数の値を追える人。
+「変数と型」を学び、宣言と代入を区別できるGo初学者。
 
 ## situation
 
-- 場面: 置いて読ませる非同期の自習教材
+- 場面: 置いて読ませる非同期の自習教材（既定値）
 - 持ち時間: 制限なし
 - 1枚の字数の上限: 420字（上流の既定値）
-- 受付値の根拠: リポジトリの既定値と、変数教材と同じ構図を再利用する依頼に従う。個別スライドの人間確認は未実施。
+- 受付値の根拠: 依頼の到達点・前提・2枚という指定を引き継ぐ。個別スライドの人間確認は未実施。
 
 ## takeaway
 
-初期値を省略して宣言したint型のcountは0で始まり、代入しなければその0が表示まで渡る。完全な実行例と練習は外側の学習ページで読む。
+初期値を省略したintはゼロ値の0から始まる。countへ代入しなければ、宣言直後の0が表示へ渡る。
 
 ## constraints
 
 - 枚数: 2枚
-- 言語: 日本語
+- 言語: 日本語（既定値）
 - 納品形式: HTML
 - キャンバス: 1600×900px
 - 禁止: 外部通信 / スクリプト / 未出典の数値
 - しきい値の変更: なし
-- 構図予算: 01は既存の名前・型・値の3箱。02はM=80 / frame=composition / axis=row / children=[code, connector, result] / connector=64 / align=center-x
-- 対象版: Go 1.27。2026-10-25に公式仕様のVariable declarationsとShort variable declarations、および前者の参照先The zero valueを取得して照合した。
-- コード例の実行環境: Go 1.27.3。2026-10-25に基本例Go: 0 lessonsと、練習のGo: 5 lessonsを終了コード0で確認した。
+- 構図予算: M=80 / frame=composition / axis=row / connector=64 / align=center-x
+- コード例の実行環境: Go 1.27.3、2026-10-25に実行結果を検証
+- 出典: Go言語仕様 go1.27 のVariable declarationsとShort variable declarationsを2026-10-25に本文取得。前者が参照する初期値の節も照合
 
 ## skills
 
-- 調べた経路: 利用可能スキル一覧と、このリポジトリのimpl・learning-setup・同梱html-deck
-- デザイン・UI: この静的教材専用のスキルはなし。依頼に従い既存変数教材のtheme.cssと構図を再利用し、quality-contract.mdとwhitespace-theory.mdで確認する
-- 図・ダイアグラム: html-deck/references/figures.md。既存の箱6個以下で線が交差しないインラインSVGを再利用する
-- データ可視化: なし。統計値を扱わない
-- 日本語の文章: 専用スキルなし。AGENTS.mdに従い前提から表示結果までをつなぐ
-- 材料の読み取り: Go公式仕様とリリース履歴の本文
+- 調べた経路: このセッションの利用可能スキル一覧、指定されたhtml-deckの同梱資料
+- デザイン・UI: 専用スキルはなし。既存の変数教材と同じ構図とtheme.cssを再利用し、quality-contract.mdとwhitespace-theory.mdで検査
+- 図・ダイアグラム: html-deck/references/figures.md。6箱以下で線が交差しないインラインSVG
+- データ可視化: なし。統計データを扱わない
+- 日本語の文章: 専用スキルなし。リポジトリのAGENTS.mdに従う
+- 材料の読み取り: Go公式言語仕様のHTML本文
 
 ## design
 
-- palette: 既存変数教材と同じ、白・淡い灰・濃い紺・灰紺・灰・青緑
-- 書体: Hiragino / Yu Gothic / Noto Sans JP / system-ui、等幅はSFMono / Menlo / monospace
+- palette: bg白、surface淡い灰、ink濃い紺、muted灰紺、line灰、accent青緑の6色
+- 書体: 表示と本文はHiragino / Yu Gothic / Noto Sans JP / system-ui、等幅はSFMono / Menlo / monospace
 - 文字サイズ段階: 18 / 24 / 26 / 30 / 36 / 60px
-- signature: 名前・型・ゼロ値の対応と、0から表示までの流れを箱と青緑の矢印で追う
-- 再利用の理由: 既に学んだ変数教材と同じ構図で、代入する行の有無による値の違いに集中できる
+- signature: 既存の変数教材の3箱の図とコード・結果の対を再利用し、青緑の矢印で値の流れを追う
 
 ## accepted
 
@@ -56,5 +55,5 @@
 
 | id | claim (言い切りの見出し) | job | visual | evidence | 問い(入) → 問い(出) |
 | --- | --- | --- | --- | --- | --- |
-| 01 | intのゼロ値は0である | 構造 | 既存の名前count・型int・最初の値0の3箱 | Go言語仕様 go1.27：Variable declarationsと参照先The zero value | 初期値を書かないcountは何を持つか → 宣言直後から0を持つ |
-| 02 | 代入しなければ0が表示まで渡る | 因果 | 既存のコードと値の図を使い、宣言直後0→Go: 0 lessonsを示す | Go言語仕様 go1.27：Variable declarations / Short variable declarations | 宣言直後の0は表示までどう渡るか → 代入がないのでPrintfにも0が渡る |
+| 01 | intを初期値なしで宣言すると0になる | 構造 | count・int・ゼロ値0の3箱を結ぶ図 | Go言語仕様 go1.27 Variable declarations | 代入なしの最初の値は何か → intのゼロ値は0 |
```

#### `courses/go/lessons/zero-values/lesson.json`（agent-2 と agent-3、類似度 0.662）

```diff
--- agent-2/courses/go/lessons/zero-values/lesson.json
+++ agent-3/courses/go/lessons/zero-values/lesson.json
@@ -3,76 +3,76 @@
   "id": "zero-values",
   "title": "ゼロ値を確かめる",
   "goal": "intのゼロ値が0であると説明できる",
-  "prerequisites": ["変数と型の学習を終え、varと:=による宣言と、=による代入を区別できる"],
+  "prerequisites": ["「変数と型」で、varによる宣言と=による代入を区別し、変数の値を追える"],
   "explanation": [
     {
-      "title": "初期値を省略した変数を確かめる",
-      "body": "変数と型では、宣言したcountへ3を代入してから表示しました。ここでは代入する行を置かず、宣言直後の値を確かめます。Goでは初期値を省略した変数に、その型のゼロ値が入ります。int型のゼロ値は0なので、var count intを実行した直後のcountは0を持ちます。",
+      "title": "宣言だけで決まる最初の値",
+      "body": "「変数と型」では、countを宣言してから代入で値を変えました。今回は代入する行を置かず、宣言だけで決まる最初の値を確かめます。var count intはint型のcountを用意し、初期値を省略したintはゼロ値の0から始まります。",
       "code": "",
       "output": ""
     },
     {
-      "title": "宣言直後の0が表示まで渡る",
-      "body": "var count intでcountが0から始まります。次のname := \"Go\"は関数内の短い変数宣言で、string型のnameを値Goで初期化します。この行はcountを変えません。その後もcountへ代入する処理がないため、fmt.Printfへ渡るcountは0のままです。%sにはnameのGo、%dにはcountの0が入り、表示結果につながります。",
+      "title": "宣言直後の0を表示まで追う",
+      "body": "name := \"Go\"は、関数内で値から型を決める短い変数宣言です。nameには文字列のGoが入り、countの値は変わりません。countへ代入する処理がないため、宣言直後の0がそのままfmt.Printfへ渡ります。%sにはname、%dにはcountが対応し、Go: 0 lessonsと表示されます。",
       "code": "",
       "output": ""
     },
     {
       "title": "完全なコードを実行する",
-      "body": "次をmain.goとして保存し、そのディレクトリでgo run main.goを実行します。countへ代入せずに表示するので、出力からintのゼロ値が0であることを確かめられます。2026-10-25にGo 1.27.3で実行し、次の出力と終了コード0を確認しています。",
+      "body": "次をmain.goとして保存し、そのディレクトリでgo run main.goを実行します。countへ値を代入する行がないことを確かめてから、表示された0を宣言直後の値と結び付けてください。2026-10-25にGo 1.27.3で実行し、次の出力と終了コード0を確認しています。",
       "code": "package main\n\nimport \"fmt\"\n\nfunc main() {\n\tvar count int\n\tname := \"Go\"\n\tfmt.Printf(\"%s: %d lessons\\n\", name, count)\n}",
       "output": "Go: 0 lessons"
     },
     {
-      "title": "宣言時の値と現在の値を分けて読む",
-      "body": "ゼロ値は、初期値を省略して宣言したときの出発点です。後で代入すれば、その時点から変数は新しい値を持ちます。次の練習では、宣言直後の0と表示時の値を分けて追ってください。",
+      "title": "ゼロ値と代入後の値を読み分ける",
+      "body": "int型のcountは、初期値なしの宣言で0から始まります。その後に代入すると、表示へ渡るのは代入後の値です。次の練習では代入を1行加え、宣言で決まる最初の値と、表示時の値を順に追います。",
       "code": "",
       "output": ""
     }
   ],
   "exercise": {
-    "prompt": "name := \"Go\"の後、fmt.Printfの前にcount = 5を追加してください。何が表示されますか。宣言直後と表示時のcountの値を順に説明してください。",
-    "answer": "Go: 5 lessonsと表示されます。var count intの直後はintのゼロ値の0ですが、count = 5で既存変数の値が5へ更新されます。Printfには更新後の5が渡ります。"
+    "prompt": "fmt.Printfの直前にcount = 5を追加して実行してください。最後に何が表示されますか。宣言直後から表示まで、countの値を順に説明してください。",
+    "answer": "Go: 5 lessonsと表示されます。var count intの直後はゼロ値の0ですが、count = 5で既存のcountを5へ更新するため、Printfへ渡る値は5になります。"
   },
   "sources": ["variables", "short-declarations"],
   "slides": [
     {
       "file": "01.html",
-      "title": "intのゼロ値は0である",
+      "title": "intを初期値なしで宣言すると0になる",
       "notes": [
-        {
-          "id": "name-note",
-          "target": "name-binding",
-          "side": "left",
-          "title": "宣言したcountを参照する",
-          "body": "countは変数の名前です。var count intで用意した変数の値を、後の表示処理でも同じ名前で取り出します。"
-        },
         {
           "id": "type-note",
           "target": "type-binding",
+          "side": "left",
+          "title": "int型として宣言する",
+          "body": "var count intはint型のcountを用意します。初期値を省略したので、最初の値は型のゼロ値で決まります。"
+        },
+        {
+          "id": "zero-value-note",
+          "target": "zero-value",
           "side": "right",
-          "title": "int型のゼロ値は0",
-          "body": "初期値を省略すると、型に応じたゼロ値で初期化されます。countの型はintなので、宣言直後から0を持ちます。"
+          "title": "宣言直後から0を持つ",
+          "body": "intのゼロ値は0です。countは宣言直後に0を持ち、代入で変えなければ、この値が後続の表示へ渡ります。"
         }
       ]
     },
     {
```

#### `courses/go/lessons/zero-values/deck/slides/02.html`（agent-1 と agent-3、類似度 0.724）

```diff
--- agent-1/courses/go/lessons/zero-values/deck/slides/02.html
+++ agent-3/courses/go/lessons/zero-values/deck/slides/02.html
@@ -2,7 +2,7 @@
 <html lang="ja">
   <head>
     <meta charset="utf-8" />
-    <title>宣言直後の0が表示まで渡る</title>
+    <title>代入しなければ宣言直後の0が表示へ渡る</title>
     <meta
       http-equiv="Content-Security-Policy"
       content="default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self' data:; script-src 'none'; connect-src 'none'; object-src 'none'; base-uri 'none'"
@@ -16,39 +16,37 @@
         <div class="folio">02 / 02</div>
       </header>
       <main class="content">
-        <h2>宣言直後の0が表示まで渡る</h2>
-        <p class="lead">countへ代入しないため、Printfは宣言直後の0を受け取る。</p>
+        <h2>代入しなければ宣言直後の0が表示へ渡る</h2>
+        <p class="lead">nameはGo、countは0のまま、Printfへ渡す。</p>
         <div class="code-layout" data-space-frame="composition" data-space-align="center-x">
           <section class="code-panel">
             <h3>コードの流れ</h3>
             <pre>
 <code>
-<span data-learning-target="declaration">var count int
-name := &quot;Go&quot;</span>
-<span data-learning-target="display">fmt.Printf(&quot;%s: %d lessons\n&quot;,
-    name, count)</span></code>
+<span data-learning-target="declaration">var count int</span>
+name := &quot;Go&quot;
+fmt.Printf(&quot;%s: %d lessons\n&quot;,
+    name, count)</code>
 </pre>
           </section>
           <div class="connector" data-space-role="connector" aria-hidden="true">→</div>
           <figure class="code-figure">
-            <svg
-              viewBox="0 0 576 400"
-              role="img"
-              aria-label="宣言直後のcountの0がGo: 0 lessonsとして表示される"
-            >
-              <title>宣言直後のcountの0がGo: 0 lessonsとして表示される</title>
+            <svg viewBox="0 0 576 400" role="img" aria-label="宣言直後のcountの0が表示へ渡る">
+              <title>宣言直後のcountの0が表示へ渡る</title>
               <rect class="node" x="40" y="46" width="496" height="124" rx="16" />
               <text class="diagram-text" x="288" y="92" text-anchor="middle">宣言直後</text>
               <text class="diagram-code" x="288" y="142" text-anchor="middle">count = 0</text>
               <path class="link" d="M 288 182 V 216" />
               <path class="arrow-head" d="M 280 208 L 288 224 L 296 208 Z" />
-              <rect class="emphasis-node" x="40" y="238" width="496" height="124" rx="16" />
-              <text class="diagram-text" x="288" y="284" text-anchor="middle">表示結果</text>
-              <text class="diagram-code" x="288" y="334" text-anchor="middle">Go: 0 lessons</text>
+              <g data-learning-target="output">
+                <rect class="emphasis-node" x="40" y="238" width="496" height="124" rx="16" />
+                <text class="diagram-text" x="288" y="284" text-anchor="middle">表示</text>
+                <text class="diagram-code" x="288" y="334" text-anchor="middle">Go: 0 lessons</text>
+              </g>
             </svg>
           </figure>
         </div>
-        <p class="summary">nameのGoが%sへ、countの0が%dへ渡り、Go: 0 lessonsと表示される。</p>
+        <p class="summary">countへの代入がないため、宣言直後の0がそのまま表示に使われる。</p>
       </main>
       <footer class="slide-footer">
         <div class="source">Go言語仕様：Variable declarations / Short variable declarations</div>
```

#### `courses/go/lessons/zero-values/deck/slides/01.html`（agent-1 と agent-2、類似度 0.827）

```diff
--- agent-1/courses/go/lessons/zero-values/deck/slides/01.html
+++ agent-2/courses/go/lessons/zero-values/deck/slides/01.html
@@ -2,7 +2,7 @@
 <html lang="ja">
   <head>
     <meta charset="utf-8" />
-    <title>初期値を省いたintのゼロ値は0になる</title>
+    <title>intのゼロ値は0である</title>
     <meta
       http-equiv="Content-Security-Policy"
       content="default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self' data:; script-src 'none'; connect-src 'none'; object-src 'none'; base-uri 'none'"
@@ -16,8 +16,8 @@
         <div class="folio">01 / 02</div>
       </header>
       <main class="content">
-        <h2>初期値を省いたintのゼロ値は0になる</h2>
-        <p class="lead">var count intで宣言すると、countは最初から0を持つ。</p>
+        <h2>intのゼロ値は0である</h2>
+        <p class="lead">var count intは、初期値を省略しても0で始まる。</p>
         <figure class="diagram">
           <svg viewBox="0 0 1440 360" role="img" aria-label="countという名前、int型、初期値0の対応">
             <title>countという名前、int型、初期値0の対応</title>
@@ -28,21 +28,19 @@
             </g>
             <path class="link" d="M 444 180 H 528" />
             <path class="arrow-head" d="M 524 172 L 540 180 L 524 188 Z" />
-            <g>
+            <g data-learning-target="type-binding">
               <rect class="emphasis-node" x="560" y="80" width="360" height="200" rx="16" />
               <text class="diagram-text" x="740" y="140" text-anchor="middle">型</text>
               <text class="diagram-code" x="740" y="220" text-anchor="middle">int</text>
             </g>
             <path class="link" d="M 940 180 H 1024" />
             <path class="arrow-head" d="M 1020 172 L 1036 180 L 1020 188 Z" />
-            <g data-learning-target="zero-value">
-              <rect class="node" x="1056" y="80" width="320" height="200" rx="16" />
-              <text class="diagram-text" x="1216" y="140" text-anchor="middle">ゼロ値</text>
-              <text class="diagram-result" x="1216" y="230" text-anchor="middle">0</text>
-            </g>
+            <rect class="node" x="1056" y="80" width="320" height="200" rx="16" />
+            <text class="diagram-text" x="1216" y="140" text-anchor="middle">最初の値</text>
+            <text class="diagram-result" x="1216" y="230" text-anchor="middle">0</text>
           </svg>
         </figure>
-        <p class="summary">値を書かずに宣言しても、int型のcountにはゼロ値の0が用意される。</p>
+        <p class="summary">countはint型なので、宣言直後からゼロ値の0を持つ。</p>
       </main>
       <footer class="slide-footer">
         <div class="source">Go言語仕様：Variable declarations / Short variable declarations</div>
```

#### `.claude/skills/learn-go/.learning-generated.json`（agent-2 と agent-3、類似度 0.900）

```diff
--- agent-2/.claude/skills/learn-go/.learning-generated.json
+++ agent-3/.claude/skills/learn-go/.learning-generated.json
@@ -3,7 +3,7 @@
   "id": "go",
   "files": {
     "SKILL.md": "fd965dce1a9812b17b1d04378110baa4f6e06077bcb5dbaa5ec860fc1ca46554",
-    "references/profile.json": "56f48bca36850f82a1b8ed62b57fb9d1afcd282bf51dab1ccbf7f3e73a6b0259",
+    "references/profile.json": "f3ba18696c77cd7406836c95e71cc35287913977bc2e47a32b6c2058350b5253",
     "references/sources.md": "d6446b84a00c652e2054c48bde2f7d98d386ce8a6810acfc0e8291d7e87bf50a",
     "references/workflow.md": "5fbbdef46ea091a89d7c2c62deebfe7deb37f174bcb6b6ed05ad89743c4209ae"
   }
```


### 保護ファイルを変えたエージェント（基準を満たさない扱い。設定やルールの緩和でないか差分を確かめる）

- agent-2: `.claude/skills/learn-go/.learning-generated.json`, `.claude/skills/learn-go/SKILL.md`, `.claude/skills/learn-go/references/profile.json`, `.claude/skills/learn-go/references/sources.md`, `.claude/skills/learn-go/references/workflow.md`
- agent-3: `.claude/skills/learn-go/.learning-generated.json`, `.claude/skills/learn-go/SKILL.md`, `.claude/skills/learn-go/references/profile.json`, `.claude/skills/learn-go/references/sources.md`, `.claude/skills/learn-go/references/workflow.md`, `tests/browser/learning.spec.mjs`

## T2-change

### 一部のエージェントだけが作った・変えたファイル

なし（全員が同じファイルの集合を変えた）

### 一部のエージェントだけが作った名前（全員に共通の新しい名前は 0 個）

なし

### 内容の類似度が低いファイル

なし（共通して変えたファイルの中身は全員一致）

## T3-cross

### 一部のエージェントだけが作った・変えたファイル

なし（全員が同じファイルの集合を変えた）

### 一部のエージェントだけが作った名前（全員に共通の新しい名前は 0 個）

なし

### 内容の類似度が低いファイル

なし（共通して変えたファイルの中身は全員一致）
