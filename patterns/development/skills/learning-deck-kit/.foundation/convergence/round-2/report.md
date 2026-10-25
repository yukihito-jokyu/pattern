# 収束テスト ラウンド 2 のレポート

このファイルは convergence.py diff が生成する。揺れの分類（R1〜R7）と対処は convergence-report.md に書く。

基準: files ≥ 1、names ≥ 0.8、content ≥ 0、check は全員通過、保護ファイルの変更なし

## 指標

| 課題 | files | names | content | check | 保護 | 基準 |
|---|---|---|---|---|---|---|
| T1-add | 1.000 | 0.361 | 0.843 | 全員通過 | — | 満たさない |
| T2-change | 1.000 | 1.000 | 1.000 | 全員通過 | — | 満たす |
| T3-cross | 1.000 | 1.000 | 1.000 | 全員通過 | — | 満たす |

## T1-add

### 一部のエージェントだけが作った・変えたファイル

なし（全員が同じファイルの集合を変えた）

### 一部のエージェントだけが作った名前（全員に共通の新しい名前は 1 個）

- agent-1: `Language`, `connector64`
- agent-2: `DNS`

### 内容の類似度が低いファイル

#### `courses/go/lessons/zero-values/deck/deck.md`（agent-1 と agent-3、類似度 0.494）

```diff
--- agent-1/courses/go/lessons/zero-values/deck/deck.md
+++ agent-3/courses/go/lessons/zero-values/deck/deck.md
@@ -1,4 +1,4 @@
-# ゼロ値を確かめる：Goの参照教材
+# ゼロ値を確かめる：Goの学習項目
 
 ## goal
 
@@ -6,18 +6,18 @@
 
 ## audience
 
-「変数と型」を学び、宣言と代入の違いを知っているGo初学者。
+「変数と型」を学び、変数の宣言と代入を区別できるGo初学者。mainとfmtの最小例を実行できる。
 
 ## situation
 
-- 場面: 置いて読ませる非同期の自習教材（implの既定値）
+- 場面: 置いて読ませる非同期の自習教材
 - 持ち時間: 制限なし
 - 1枚の字数の上限: 420字（上流の既定値）
-- 受付値の根拠: 到達点と2枚の指定は依頼で確定。未指定の形式はimplの既定値を使う。
+- 受付値の根拠: 依頼の到達点・前提・2枚指定と実装スキルの既定値。質問禁止のため再確認は行わない。
 
 ## takeaway
 
-初期値を省略したint型のcountは0で始まる。代入しなければ、その0が表示まで渡る。完全な実行例とcountへ5を代入する練習は外側の学習ページで読む。
+intを初期値なしで宣言すると0で始まり、代入しなければ表示へも0が渡る。完全な実行例と練習は外側の学習ページで読む。
 
 ## constraints
 
@@ -27,35 +27,34 @@
 - キャンバス: 1600×900px
 - 禁止: 外部通信 / スクリプト / 未出典の数値
 - しきい値の変更: なし
-- 01の構図予算: M=80 / frame=diagram / axis=row / children=[名前, 線, 型, 線, ゼロ値] / align=center-x
-- 02の構図予算: M=80 / frame=composition / axis=row / children=[コード800, connector64, 図576] / G=0 / align=center-x
-- コード例の実行環境: Go 1.27.3、実行日2026-10-25。結果は検査で照合する。
-- 資料: 2026-10-25に公式言語仕様の本文とLanguage version go1.27を取得。Variable declarationsの初期値省略、Short variable declarationsの関数内宣言、および参照先The zero valueのintの0を照合した。
+- 構図予算: M=80 / frame=composition / axis=row / connector=64 / align=center-x
+- コード例の実行環境: Go 1.27.3、2026-10-25に実行成功と出力を確認
+- 公式本文: 2026-10-25にGo言語仕様go1.27のVariable declarationsとShort variable declarations、および参照先のThe zero valueを取得して照合
 
 ## skills
 
-- 調べた経路: このセッションの利用可能スキル一覧と指定ディレクトリ内の同梱資料
-- デザイン・UI: この静的教材専用のスキルはなし。quality-contract.mdとwhitespace-theory.mdの数値を使用
-- 図・ダイアグラム: 既存の変数教材のSVG構図を再利用
-- データ可視化: なし。統計データを扱わない
-- 日本語の文章: 専用スキルなし。AGENTS.mdの説明基準に従う
-- 材料の読み取り: Go公式言語仕様のHTML本文
+- 調べた経路: このセッションの利用可能スキル一覧、.claude/skillsの一覧、html-deckの同梱資料
+- デザイン・UI: この教材専用のデザインスキルはなし。quality-contract.mdとwhitespace-theory.mdを使い、依頼どおり変数教材の構図とtheme.cssを再利用
+- 図・ダイアグラム: html-deck/references/figures.md。6箱以下で交差のないインラインSVGを使用
+- データ可視化: なし。統計の可視化は扱わない
+- 日本語の文章: 専用スキルなし。AGENTS.mdとimplの説明手順に従う
+- 材料の読み取り: Go公式言語仕様、リリース履歴、Getting startedの本文
 
 ## design
 
-- palette: 変数教材の白・淡灰・濃紺・灰紺・灰・青緑の6色を再利用
-- 書体: 変数教材の表示・本文・等幅のフォントスタックを再利用
+- palette: 既存変数教材の白、淡い灰、濃い紺、灰紺、灰、青緑を再利用
+- 書体: 既存変数教材のHiragino / Yu Gothic / Noto Sans JP / system-ui、等幅はSFMono / Menlo / monospace
 - 文字サイズ段階: 18 / 24 / 26 / 30 / 36 / 60px
-- signature: 01は名前・型・ゼロ値の対等な3箱、02はコードと値の流れの2箱を矢印でつなぐ
+- signature: 01は名前・型・初期値の対等な3箱を無方向線で結び、02はコードと縦の値の流れを並べる
 
 ## accepted
 
-- [user] 既存の変数教材と同じ構図を再利用し、2枚で説明する。
-- ユーザーによる各スライドの確認は未実施。自動検査の成功と人間の承認を区別する。
+- 依頼で指定された変数教材の構図を再利用する。01では宣言直後の値、02では表示時点の値を示し、0が保持される流れを分けて説明する。
+- ユーザーによる各スライドの見た目・説明の確認は未実施。自動検査と人間の承認を区別する。
 
 ## storyboard
 
 | id | claim (言い切りの見出し) | job | visual | evidence | 問い(入) → 問い(出) |
 | --- | --- | --- | --- | --- | --- |
-| 01 | intのゼロ値は0から始まる | 構造 | 変数教材と同じ名前・型・値の3箱 | Go言語仕様 go1.27 | 初期値がないと何になるか → countは0を持つ |
```

#### `courses/go/lessons/zero-values/lesson.json`（agent-1 と agent-3、類似度 0.687）

```diff
--- agent-1/courses/go/lessons/zero-values/lesson.json
+++ agent-3/courses/go/lessons/zero-values/lesson.json
@@ -3,76 +3,79 @@
   "id": "zero-values",
   "title": "ゼロ値を確かめる",
   "goal": "intのゼロ値が0であると説明できる",
-  "prerequisites": ["「変数と型」で、varによる宣言と=による代入を区別し、変数の型と値を追える"],
+  "prerequisites": [
+    "「変数と型」で、変数の名前・型・値の関係と、宣言と代入の違いを学んでいる",
+    "main関数とfmt.Printfを含むコードを保存し、go runで実行できる"
+  ],
   "explanation": [
     {
-      "title": "変数の最初の値を確かめる",
-      "body": "「変数と型」では、宣言したcountへ3を代入してから表示しました。今回は代入する行を置かず、宣言だけでどの値を持つかを確かめます。Goでは初期値を省略して宣言した変数にも、その型のゼロ値が入ります。intのゼロ値は0なので、var count intの直後からcountは0を持ちます。",
+      "title": "初期値を省略した変数から始める",
+      "body": "「変数と型」では、宣言したcountへ3を代入して値を更新しました。今回はvar count intで宣言した後、countへ代入せずに表示します。初期値を書かない変数は型ごとのゼロ値で初期化されます。countの型はintなので、宣言直後から0を保持しています。",
       "code": "",
       "output": ""
     },
     {
-      "title": "宣言直後の0を表示まで追う",
-      "body": "var count intはint型を指定し、初期値を省略した宣言です。次のname := \"Go\"は関数内の短い変数宣言で、nameはstring型の値Goを持ちます。この宣言はcountを更新しません。その後もcountへ代入する行がないため、fmt.Printfへ渡す時点でもcountは0です。書式の%sへnameのGo、%dへcountの0が順番に入り、Go: 0 lessonsと表示されます。",
+      "title": "宣言直後の0を表示へ渡す",
+      "body": "name := \"Go\"は関数内の短い変数宣言です。文字列\"Go\"から型がstringに決まり、nameは最初から\"Go\"を保持します。この宣言はcountを変更しません。そのためfmt.Printfがnameとcountを読む時点でもcountは0です。%sへ\"Go\"、%dへ0が渡り、Go: 0 lessonsという表示になります。",
       "code": "",
       "output": ""
     },
     {
       "title": "完全なコードを実行する",
-      "body": "次をmain.goとして保存し、そのディレクトリでgo run main.goを実行します。countに初期値も後からの代入もないことと、出力の0を対応させてください。2026-10-25にGo 1.27.3で実行し、次の出力と終了コード0を確認しています。",
+      "body": "次をmain.goとして保存し、そのディレクトリでgo run main.goを実行します。var count intに初期値も後続の代入もないことを確認してから、%dへ渡されるcountの値を予想してください。2026-10-25にGo 1.27.3で実行し、次の出力と終了コード0を確認しています。",
       "code": "package main\n\nimport \"fmt\"\n\nfunc main() {\n\tvar count int\n\tname := \"Go\"\n\tfmt.Printf(\"%s: %d lessons\\n\", name, count)\n}",
       "output": "Go: 0 lessons"
     },
     {
-      "title": "ゼロ値と代入後の値を区別する",
-      "body": "ゼロ値は宣言時に決まる最初の値です。宣言後に代入すれば、後続の処理には更新後の値が渡ります。練習では表示の前にcountへ5を代入し、宣言直後の値と表示される値を区別します。",
+      "title": "値の更新との違いを確かめる",
+      "body": "表示する処理は、その時点でcountが保持している値を受け取ります。この例では宣言直後の0が変わらず渡ります。練習では表示より前に代入を加え、同じ表示処理へ渡る値がどう変わるかを確かめます。",
       "code": "",
       "output": ""
     }
   ],
   "exercise": {
-    "prompt": "fmt.Printfの直前へcount = 5を追加して実行すると、何が表示されますか。宣言直後の値と代入後の値を順番に説明してください。",
-    "answer": "Go: 5 lessonsと表示されます。var count intの直後はintのゼロ値0ですが、count = 5で既存のcountの値が5へ更新されます。そのため、Printfの%dには5が渡り、nameのGoと一緒に表示されます。"
+    "prompt": "fmt.Printfより前にcount = 5を追加すると、何が表示されますか。宣言直後と代入後のcountの値を順に説明してください。",
+    "answer": "Go: 5 lessonsと表示されます。var count intの直後はintのゼロ値である0ですが、count = 5で同じ変数の値が5へ更新されます。その後のPrintfへ5が渡るため、表示の数も5になります。"
   },
   "sources": ["variables", "short-declarations"],
   "slides": [
     {
       "file": "01.html",
-      "title": "intのゼロ値は0から始まる",
+      "title": "intのゼロ値は0になる",
       "notes": [
         {
-          "id": "type-note",
-          "target": "type-binding",
+          "id": "name-note",
+          "target": "name-binding",
           "side": "left",
-          "title": "型を指定して宣言する",
-          "body": "var count intはcountの型をintに決めます。初期値を省略したときに入る値も、この型によって決まります。"
+          "title": "既存教材と同じcountを使う",
+          "body": "var count intはcountという名前をint型の変数へ結び付けます。後続の表示はこの名前から現在の値を取り出します。"
         },
         {
           "id": "zero-note",
           "target": "zero-value",
           "side": "right",
-          "title": "intの最初の値は0",
-          "body": "初期値を省略したint型のcountはゼロ値0を持ちます。代入しなければ、後続の処理にもこの0が渡ります。"
+          "title": "初期値を省略すると0から始まる",
+          "body": "初期値を与えていないため、countはint型のゼロ値である0で初期化されます。この0が後続の処理へ渡る出発点です。"
         }
       ]
     },
     {
```

#### `courses/go/lessons/zero-values/deck/slides/02.html`（agent-1 と agent-3、類似度 0.752）

```diff
--- agent-1/courses/go/lessons/zero-values/deck/slides/02.html
+++ agent-3/courses/go/lessons/zero-values/deck/slides/02.html
@@ -2,7 +2,7 @@
 <html lang="ja">
   <head>
     <meta charset="utf-8" />
-    <title>宣言直後の0が表示まで渡る</title>
+    <title>宣言直後の0をそのまま表示する</title>
     <meta
       http-equiv="Content-Security-Policy"
       content="default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self' data:; script-src 'none'; connect-src 'none'; object-src 'none'; base-uri 'none'"
@@ -16,31 +16,38 @@
         <div class="folio">02 / 02</div>
       </header>
       <main class="content">
-        <h2>宣言直後の0が表示まで渡る</h2>
-        <p class="lead">countへ代入しないため、Printfにも0が渡る。</p>
+        <h2>宣言直後の0をそのまま表示する</h2>
+        <p class="lead">countへ代入しなければ、表示する時点でも値は0。</p>
         <div class="code-layout" data-space-frame="composition" data-space-align="center-x">
           <section class="code-panel">
             <h3>コードの流れ</h3>
             <pre><code><span data-learning-target="declaration">var count int</span>
 name := "Go"
-<span data-learning-target="display">fmt.Printf("%s: %d lessons\n", name, count)</span></code></pre>
+fmt.Printf("%s: %d lessons\n",
+    name, count)</code></pre>
           </section>
           <div class="connector" data-space-role="connector" aria-hidden="true">→</div>
           <figure class="code-figure">
-            <svg viewBox="0 0 576 400" role="img" aria-label="宣言直後のcountの0が表示へ渡る">
-              <title>宣言直後のcountの0が表示へ渡る</title>
+            <svg
+              viewBox="0 0 576 400"
+              role="img"
+              aria-label="宣言直後のcountの0がGo: 0 lessonsという表示へ渡る"
+            >
+              <title>宣言直後のcountの0がGo: 0 lessonsという表示へ渡る</title>
               <rect class="node" x="40" y="46" width="496" height="124" rx="16" />
               <text class="diagram-text" x="288" y="92" text-anchor="middle">宣言直後</text>
               <text class="diagram-code" x="288" y="142" text-anchor="middle">count = 0</text>
               <path class="link" d="M 288 182 V 216" />
               <path class="arrow-head" d="M 280 208 L 288 224 L 296 208 Z" />
-              <rect class="emphasis-node" x="40" y="238" width="496" height="124" rx="16" />
-              <text class="diagram-text" x="288" y="284" text-anchor="middle">表示</text>
-              <text class="diagram-code" x="288" y="334" text-anchor="middle">Go: 0 lessons</text>
+              <g data-learning-target="output">
+                <rect class="emphasis-node" x="40" y="238" width="496" height="124" rx="16" />
+                <text class="diagram-text" x="288" y="284" text-anchor="middle">表示結果</text>
+                <text class="diagram-code" x="288" y="334" text-anchor="middle">Go: 0 lessons</text>
+              </g>
             </svg>
           </figure>
         </div>
-        <p class="summary">nameのGoとcountの0が、書式の%sと%dに順番に入る。</p>
+        <p class="summary">nameの"Go"とcountの0がPrintfへ渡り、Go: 0 lessonsと表示される。</p>
       </main>
       <footer class="slide-footer">
         <div class="source">Go言語仕様：Variable declarations / Short variable declarations</div>
```

#### `courses/go/lessons/zero-values/deck/slides/01.html`（agent-1 と agent-3、類似度 0.863）

```diff
--- agent-1/courses/go/lessons/zero-values/deck/slides/01.html
+++ agent-3/courses/go/lessons/zero-values/deck/slides/01.html
@@ -2,7 +2,7 @@
 <html lang="ja">
   <head>
     <meta charset="utf-8" />
-    <title>intのゼロ値は0から始まる</title>
+    <title>intのゼロ値は0になる</title>
     <meta
       http-equiv="Content-Security-Policy"
       content="default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self' data:; script-src 'none'; connect-src 'none'; object-src 'none'; base-uri 'none'"
@@ -16,11 +16,11 @@
         <div class="folio">01 / 02</div>
       </header>
       <main class="content">
-        <h2>intのゼロ値は0から始まる</h2>
-        <p class="lead">var count intは、初期値を省略しても0を持つ。</p>
+        <h2>intのゼロ値は0になる</h2>
+        <p class="lead">var count intは、初期値を書かなくても0から始まる。</p>
         <figure class="diagram">
-          <svg viewBox="0 0 1440 360" role="img" aria-label="countという名前、int型、ゼロ値0の対応">
-            <title>countという名前、int型、ゼロ値0の対応</title>
+          <svg viewBox="0 0 1440 360" role="img" aria-label="countという名前、int型、初期値0の対応">
+            <title>countという名前、int型、初期値0の対応</title>
             <g data-learning-target="name-binding">
               <rect class="node" x="64" y="80" width="360" height="200" rx="16" />
               <text class="diagram-text" x="244" y="140" text-anchor="middle">名前</text>
@@ -35,12 +35,12 @@
             <path class="link" d="M 940 180 H 1024" />
             <g data-learning-target="zero-value">
               <rect class="node" x="1056" y="80" width="320" height="200" rx="16" />
-              <text class="diagram-text" x="1216" y="140" text-anchor="middle">ゼロ値</text>
+              <text class="diagram-text" x="1216" y="140" text-anchor="middle">最初の値</text>
               <text class="diagram-result" x="1216" y="230" text-anchor="middle">0</text>
             </g>
           </svg>
         </figure>
-        <p class="summary">countへ代入しなければ、宣言直後の0をその後も参照できる。</p>
+        <p class="summary">intのゼロ値は0。代入しなければ、countはこの値を保持する。</p>
       </main>
       <footer class="slide-footer">
         <div class="source">Go言語仕様：Variable declarations / Short variable declarations</div>
```

#### `courses/go/profile.json`（agent-1 と agent-3、類似度 0.988）

```diff
--- agent-1/courses/go/profile.json
+++ agent-3/courses/go/profile.json
@@ -48,7 +48,7 @@
       "title": "Goのリリース履歴",
       "url": "https://go.dev/doc/devel/release",
       "version": "go1.27.3",
-      "checkedAt": "2026-10-24"
+      "checkedAt": "2026-10-25"
     }
   ],
   "curriculum": [
```


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
