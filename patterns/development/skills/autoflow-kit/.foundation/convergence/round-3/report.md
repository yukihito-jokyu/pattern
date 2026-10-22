# 収束テスト ラウンド 3 のレポート

このファイルは convergence.py diff が生成する。揺れの分類（R1〜R7）と対処は convergence-report.md に書く。

基準: files ≥ 1.0、names ≥ 0.8、content ≥ 0.0、check は全員通過、保護ファイルの変更なし

## 指標

| 課題 | files | names | content | check | 保護 | 基準 |
|---|---|---|---|---|---|---|
| T1-add | 1.000 | 1.000 | 0.993 | 全員通過 | — | 満たす |
| T2-change | 1.000 | 1.000 | 0.990 | 全員通過 | — | 満たす |
| T3-cross | 1.000 | 0.422 | 0.967 | 全員通過 | — | 満たさない |
| H1-holdout | 1.000 | 1.000 | 0.959 | 全員通過 | — | 満たす |

## T1-add

### 一部のエージェントだけが作った・変えたファイル

なし（全員が同じファイルの集合を変えた）

### 一部のエージェントだけが作った名前（全員に共通の新しい名前は 1 個）

なし

### 内容の類似度が低いファイル

#### `tests/test_policy.py`（agent-2 と agent-3、類似度 0.968）

```diff
--- agent-2/tests/test_policy.py
+++ agent-3/tests/test_policy.py
@@ -111,9 +111,9 @@
             self.assertEqual(rule.id.split("_", 1)[1], name, f"規則 {rule.id} の判定の関数 {rule.test.__name__}")
 
     def test_h1_human_only(self) -> None:
-        human = {"id": "C1", "text": "画面の色が見やすい", "check": "human", "run": ""}
+        human = {"id": "C1", "text": "画面の文言が自然である", "check": "human", "run": ""}
+        review = {"id": "C2", "text": "既存の関数と同じ書き方である", "check": "review", "run": ""}
+        command = {"id": "C2", "text": "テストが通る", "check": "command", "run": "make test"}
         self.assertEqual(policy.h1_reasons(plan(criteria=[human]), SETTINGS), ("h1_human_only",))
-        review = {"id": "C2", "text": "既存の関数と同じ書き方である", "check": "review", "run": ""}
         self.assertEqual(policy.h1_reasons(plan(criteria=[human, review]), SETTINGS), ())
-        command = {"id": "C2", "text": "テストが通る", "check": "command", "run": "make test"}
         self.assertEqual(policy.h1_reasons(plan(criteria=[human, command]), SETTINGS), ())
```


## T2-change

### 一部のエージェントだけが作った・変えたファイル

なし（全員が同じファイルの集合を変えた）

### 一部のエージェントだけが作った名前（全員に共通の新しい名前は 1 個）

なし

### 内容の類似度が低いファイル

#### `tests/test_policy.py`（agent-2 と agent-3、類似度 0.967）

```diff
--- agent-2/tests/test_policy.py
+++ agent-3/tests/test_policy.py
@@ -111,6 +111,6 @@
             self.assertEqual(rule.id.split("_", 1)[1], name, f"規則 {rule.id} の判定の関数 {rule.test.__name__}")
 
     def test_lens_performance(self) -> None:
-        self.assertIn("performance", policy.depth_of(policy.HIGH).lenses)
-        self.assertNotIn("performance", policy.depth_of(policy.MEDIUM).lenses)
-        self.assertNotIn("performance", policy.depth_of(policy.LOW).lenses)
+        self.assertIn("performance", [lens.name for lens in policy.LENSES])
+        tiers = [tier.name for tier in policy.TIERS if "performance" in policy.depth_of(tier.name).lenses]
+        self.assertEqual(tiers, [policy.HIGH])
```

#### `kit/.autoflow/templates/prompts/finder.md`（agent-1 と agent-2、類似度 0.980）

```diff
--- agent-1/kit/.autoflow/templates/prompts/finder.md
+++ agent-2/kit/.autoflow/templates/prompts/finder.md
@@ -19,7 +19,7 @@
 | `security` | 入力の検証、注入、認可の抜け、秘密情報の露出、安全でない既定値 |
 | `intent` | 計画の受け入れ条件を満たさない、範囲の外の変更、やらないことに反する、リポジトリの決まり（CLAUDE.md、レビューの指示）に反する |
 | `impact` | 変えた関数・型・設定の呼び出し元への影響、互換性、データの形、他の箇所の同じ前提 |
-| `performance` | 入力の大きさに対する計算量、ループの中の I/O（ファイル、ネットワーク、データベース、外部コマンド）、同じ値の不要な再計算、メモリの使い方（全件の読み込み、大きな値の複製） |
+| `performance` | 計算量、ループの中の I/O、不要な再計算、メモリの使い方 |
 
 ## 指摘にしないもの
 
```


## T3-cross

### 一部のエージェントだけが作った・変えたファイル

なし（全員が同じファイルの集合を変えた）

### 一部のエージェントだけが作った名前（全員に共通の新しい名前は 1 個）

- agent-1: `suggested_fix`
- agent-2: `del`, `suggested_fix`
- agent-3: `del`, `fix_suggestion`, `suggested`

### 内容の類似度が低いファイル

#### `tests/test_views.py`（agent-2 と agent-3、類似度 0.854）

```diff
--- agent-2/tests/test_views.py
+++ agent-3/tests/test_views.py
@@ -4,15 +4,13 @@
 
 import unittest
 
-from autoflow_kit import contracts, policy, profile, render, views
+from autoflow_kit import contracts, policy, profile, views
 from tests import support
 
 
-def kept(tag: str = policy.IMPORTANT, suggested_fix: str = "負の数のときの結果を決め、テストを足す") -> contracts.Kept:
+def kept(tag: str = policy.IMPORTANT, **overrides: object) -> contracts.Kept:
     finding = contracts.parse_findings(
-        {"findings": [support.finding(other_locations=["calc.py:20"], suggested_fix=suggested_fix)]},
-        policy.REVIEW.categories,
-        [],
+        {"findings": [support.finding(other_locations=["calc.py:20"], **overrides)]}, policy.REVIEW.categories, []
     )[0]
     return contracts.Kept("R1-1", tag, 2, 3, ("correctness",), finding)
 
@@ -44,9 +42,9 @@
         self.assertIn("# レビュー ラウンド 2", text)
         self.assertIn("| R1-1 | Nit |", text)
         self.assertIn("票で落ちた候補: R2-2", text)
-        self.assertIn("直し方の案: 負の数のときの結果を決め、テストを足す", text)
-        empty = contracts.ReviewResult(2, "b" * 40, "a" * 40, "standard", (kept(suggested_fix=""),), ())
-        self.assertIn(f"直し方の案: {render.MISSING}", views.render_review(empty))
+        self.assertIn("直し方の案: —", text)
+        suggested = contracts.ReviewResult(2, "b" * 40, "a" * 40, "standard", (kept(fix_suggestion="上限を足す"),), ())
+        self.assertIn("直し方の案: 上限を足す", views.render_review(suggested))
 
     def test_gate(self) -> None:
         text = views.render_gate(policy.H2, ("h2_too_many_failures",), ("続いた検査の失敗: 3 回",))
```

#### `tests/test_contracts.py`（agent-1 と agent-3、類似度 0.922）

```diff
--- agent-1/tests/test_contracts.py
+++ agent-3/tests/test_contracts.py
@@ -87,10 +87,11 @@
 
     def test_parse_findings(self) -> None:
         problems: list[str] = []
-        found = contracts.parse_findings(
-            {"findings": [support.finding(suggested_fix="")]}, policy.REVIEW.categories, problems
-        )
-        self.assertEqual((found[0].suggested_fix, problems), ("", []))
-        missing = {key: value for key, value in support.finding().items() if key != "suggested_fix"}
+        items = [support.finding(), support.finding(fix_suggestion="負の数のテストを足す")]
+        found = contracts.parse_findings({"findings": items}, policy.REVIEW.categories, problems)
+        self.assertEqual(problems, [])
+        self.assertEqual([item.fix_suggestion for item in found], ["", "負の数のテストを足す"])
+        missing = support.finding()
+        del missing["fix_suggestion"]
         contracts.parse_findings({"findings": [missing]}, policy.REVIEW.categories, problems)
-        self.assertEqual(problems, ["findings[0].suggested_fix は文字列にしてください"])
+        self.assertEqual(problems, ["findings[0].fix_suggestion は文字列にしてください"])
```

#### `kit/.autoflow/templates/prompts/finder.md`（agent-1 と agent-2、類似度 0.960）

```diff
--- agent-1/kit/.autoflow/templates/prompts/finder.md
+++ agent-2/kit/.autoflow/templates/prompts/finder.md
@@ -38,7 +38,7 @@
 - 根拠のあるバグだけを書く。`file` と `line` は変更後のファイルの場所にし、`evidence` に、そのバグが起きる入力や手順を書く
 - `bug_class` にバグの種類を短い名詞で書く（例：境界の値の取り違え、null の確かめ漏れ）。同じ種類のバグが他の箇所にもあれば、`other_locations` に `file:line` で全部書く。作者が1行ではなく全部を直せるようにするため
 - この差分が持ち込んだのではない、前からあるバグは `pre_existing` を `true` にする
-- `suggested_fix` に直し方の案を短く書く。作者は案を手がかりに直し方を決める。直し方が分からなければ空の文字列 `""` にし、確かめていない案を書かない
+- `suggested_fix` に直し方の案を短く書く。実装役が直すときの手がかりにするため。直し方が分からなければ空の文字列 `""` にする。分からないことは、指摘を出さない理由にならない
 - `category` は `bug`（振る舞いの誤り）・`security`（安全の問題）・`criteria`（受け入れ条件を満たさない）・`fit`（範囲の外の変更か、リポジトリの決まりに反する）のどれか
 - 見つからなければ空の配列にする。数を出すために弱い指摘を書かない
 
@@ -58,7 +58,7 @@
       "bug_class": "下限の確かめ漏れ",
       "other_locations": ["src/cart/tax.py:17"],
       "pre_existing": false,
-      "suggested_fix": "割引を合計で頭打ちにし、total() が 0 未満を返さないようにする"
+      "suggested_fix": "total() で割引を合計で頭打ちにし、0 を下回らないようにする"
     }
   ]
 }
```

#### `tests/test_building.py`（agent-1 と agent-2、類似度 0.964）

```diff
--- agent-1/tests/test_building.py
+++ agent-2/tests/test_building.py
@@ -38,11 +38,11 @@
 
     def test_findings_must_be_answered(self) -> None:
         where, run_id = support.risked(self)
-        support.review_round(where, run_id, {"correctness": [support.finding(suggested_fix="")]})
+        support.review_round(where, run_id, {"correctness": [support.finding()]})
         building.build_new(where, run_id, NOW)
         prompt = fsops.read_text(where.build_prompt_path(run_id, 2))
         self.assertIn("R1-1 [Important]", prompt)
-        self.assertIn("種類 境界の値 — 直し方の案: —", prompt)
+        self.assertIn("— 直し方の案: 負の数のときの結果を決め、テストを足す", prompt)
         support.act_builder(where, run_id)
         with self.assertRaisesRegex(InvalidFileError, "R1-1 への回答"):
             building.build_check(where, run_id, NOW)
```

#### `kit/.autoflow/templates/prompts/builder.md`（agent-1 と agent-2、類似度 0.980）

```diff
--- agent-1/kit/.autoflow/templates/prompts/builder.md
+++ agent-2/kit/.autoflow/templates/prompts/builder.md
@@ -32,7 +32,7 @@
 
 ## 回答が要る指摘
 
-一覧が `- なし` なら、回答の要る指摘は無い。各行は「id [重大度] 題名 — 場所、バグの種類（同じ種類の他の箇所） — 直し方の案」である。直し方の案が `—` なら、探索役は案を書いていない。案は探索役の見立てなので、コードで確かめてから直し方を決める。
+一覧が `- なし` なら、回答の要る指摘は無い。各行は「id [重大度] 題名 — 場所、バグの種類（同じ種類の他の箇所） — 直し方の案」である。直し方の案は探索役の見立てで、`—` なら案は無い。案に従うかどうかは、コードを読んで決める。
 
 ${findings}
 
```


## H1-holdout

### 一部のエージェントだけが作った・変えたファイル

なし（全員が同じファイルの集合を変えた）

### 一部のエージェントだけが作った名前（全員に共通の新しい名前は 10 個）

なし

### 内容の類似度が低いファイル

#### `tests/test_intake.py`（agent-2 と agent-3、類似度 0.912）

```diff
--- agent-2/tests/test_intake.py
+++ agent-3/tests/test_intake.py
@@ -61,9 +61,9 @@
 
     def test_source_jira(self) -> None:
         where = support.make_repo(self)
+        no_ref = trail.Origin("jira", "", "", "題名")
         with self.assertRaisesRegex(StageError, "--ref"):
-            intake.start(where, trail.Origin("jira", "", "", "題名"), support.body_file(where), support.NOW)
-        jira = trail.Origin("jira", "PROJ-123", "https://example.atlassian.net/browse/PROJ-123", "掛け算を足す")
-        intake.start(where, jira, support.body_file(where), support.NOW)
-        start = support.events(where, "20261021-143000-proj-123")[0]
-        self.assertEqual((start.source, start.ref), ("jira", "PROJ-123"))
+            intake.start(where, no_ref, support.body_file(where), support.NOW)
+        origin = trail.Origin("jira", "PROJ-123", "https://example.atlassian.net/browse/PROJ-123", "掛け算を足す")
+        text = intake.start(where, origin, support.body_file(where), support.NOW)
+        self.assertIn("実行: 20261021-143000-proj-123", text)
```

#### `kit/claude/skills/autoflow/references/sources.md`（agent-1 と agent-2、類似度 0.947）

```diff
--- agent-1/kit/claude/skills/autoflow/references/sources.md
+++ agent-2/kit/claude/skills/autoflow/references/sources.md
@@ -9,7 +9,7 @@
 | `redmine` | `/autoflow redmine 456` | Redmine の MCP のチケットを取るツール（`getIssue`、`include` に `journals`）。サーバー名が違う環境では、同じ働きのツールを使う | チケットの番号 | チケットの URL（分かれば） |
 | `gitlab` | `/autoflow gitlab 78` | `glab issue view 78 --comments -F json` | Issue の番号 | `web_url` |
 | `github` | `/autoflow github 90` | `gh issue view 90 --comments --json number,title,body,comments,url` | Issue の番号 | `url` |
-| `jira` | `/autoflow jira PROJ-123` | Atlassian の MCP の課題を取るツール（`getJiraIssue`、引数 `cloudId` と `issueIdOrKey`。コメントは結果の `fields.comment`）。`cloudId` はサイトの一覧を取るツール（`getAccessibleAtlassianResources`）で取る。サーバー名が違う環境では、同じ働きのツールを使う | 課題キー（`PROJ-123`） | 課題の URL（`https://<サイト>/browse/PROJ-123`。分かれば） |
+| `jira` | `/autoflow jira PROJ-123` | Atlassian の MCP の課題を取るツール（`getJiraIssue`、引数 `cloudId` と `issueIdOrKey`）。`cloudId` は同じサーバーの `getAccessibleAtlassianResources` で取る。題名は `summary`、コメントは `comment` の欄から取る。サーバー名が違う環境では、同じ働きのツールを使う | 課題キー（`PROJ-123`） | 課題の URL（分かれば） |
 
 ## intake.md の書き方
 
```
