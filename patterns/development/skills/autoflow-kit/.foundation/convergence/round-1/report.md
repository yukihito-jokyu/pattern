# 収束テスト ラウンド 1 のレポート

このファイルは convergence.py diff が生成する。揺れの分類（R1〜R7）と対処は convergence-report.md に書く。

基準: files ≥ 1.0、names ≥ 0.8、content ≥ 0.0、check は全員通過、保護ファイルの変更なし

## 指標

| 課題 | files | names | content | check | 保護 | 基準 |
|---|---|---|---|---|---|---|
| T1-add | 0.833 | 1.000 | 0.977 | 全員通過 | — | 満たさない |
| T2-change | 1.000 | 1.000 | 0.985 | 全員通過 | — | 満たす |
| T3-cross | 0.933 | 0.583 | 0.967 | 全員通過 | — | 満たさない |

## T1-add

### 一部のエージェントだけが作った・変えたファイル

| ファイル | agent-1 | agent-2 | agent-3 |
|---|---|---|---|
| `kit/.autoflow/autoflow_kit/contracts.py` | ✓ | – | – |

### 一部のエージェントだけが作った名前（全員に共通の新しい名前は 3 個）

なし

### 内容の類似度が低いファイル

#### `tests/test_policy.py`（agent-1 と agent-2、類似度 0.943）

```diff
--- agent-1/tests/test_policy.py
+++ agent-2/tests/test_policy.py
@@ -47,12 +47,12 @@
         self.assertEqual(policy.h1_reasons(plan(scope=["src/auth/login.py"]), SETTINGS), ("h1_always_human",))
 
     def test_h1_human_only(self) -> None:
-        human = {"id": "C1", "text": "画面の文言が自然である", "check": "human", "run": ""}
+        look = {"id": "C1", "text": "画面の文言が読みやすい", "check": "human", "run": ""}
+        self.assertEqual(policy.h1_reasons(plan(criteria=[look]), SETTINGS), ("h1_human_only",))
         review = {"id": "C2", "text": "既存の関数と同じ書き方である", "check": "review", "run": ""}
-        command = {"id": "C3", "text": "テストが通る", "check": "command", "run": "make test"}
-        self.assertEqual(policy.h1_reasons(plan(criteria=[human, review]), SETTINGS), ())
-        self.assertEqual(policy.h1_reasons(plan(criteria=[human, command]), SETTINGS), ())
-        self.assertEqual(policy.h1_reasons(plan(criteria=[human]), SETTINGS), ("h1_human_only",))
+        self.assertEqual(policy.h1_reasons(plan(criteria=[look, review]), SETTINGS), ())
+        command = {"id": "C2", "text": "テストが通る", "check": "command", "run": "make test"}
+        self.assertEqual(policy.h1_reasons(plan(criteria=[look, command]), SETTINGS), ())
 
     def test_h2_blocked(self) -> None:
         self.assertEqual(stuck(blockers=("権限が無い",)), ("h2_blocked",))
```

#### `kit/claude/skills/autoflow/references/gates.md`（agent-1 と agent-2、類似度 0.988）

```diff
--- agent-1/kit/claude/skills/autoflow/references/gates.md
+++ agent-2/kit/claude/skills/autoflow/references/gates.md
@@ -57,7 +57,7 @@
 | `h1_dependency` | 依存を足す計画である |
 | `h1_scope` | 計画の範囲が limits.max_scope_files を超える |
 | `h1_always_human` | 計画の範囲が risk.always_human のパスに当たる |
-| `h1_human_only` | 受け入れ条件が全部 human（人が確かめる）の計画である |
+| `h1_human_only` | 受け入れ条件が全部、人が確かめるもの（check が human）である |
 
 ## H2 を起こす条件（どれか1つに当たれば聞く）
 
```

#### `kit/.autoflow/autoflow_kit/policy.py`（agent-1 と agent-2、類似度 0.993）

```diff
--- agent-1/kit/.autoflow/autoflow_kit/policy.py
+++ agent-2/kit/.autoflow/autoflow_kit/policy.py
@@ -189,7 +189,7 @@
 
 
 def _is_human_only(plan: contracts.Plan, _profile: profile.Profile) -> bool:
-    return all(criterion.check == contracts.HUMAN for criterion in plan.criteria)
+    return all(criterion.check == "human" for criterion in plan.criteria)
 
 
 def _is_blocked(progress: Progress, _limits: profile.Limits) -> bool:
@@ -210,7 +210,7 @@
     PlanRule("h1_dependency", "依存を足す計画である", _has_new_dependency),
     PlanRule("h1_scope", "計画の範囲が limits.max_scope_files を超える", _is_wide),
     PlanRule("h1_always_human", "計画の範囲が risk.always_human のパスに当たる", _has_human_paths),
-    PlanRule("h1_human_only", "受け入れ条件が全部 human（人が確かめる）の計画である", _is_human_only),
+    PlanRule("h1_human_only", "受け入れ条件が全部、人が確かめるもの（check が human）である", _is_human_only),
 )
 # H2（行き詰まり）を起こす条件。記事の「3ラウンドで止まって方針を見直す」に当たる
 H2_RULES = (
```


## T2-change

### 一部のエージェントだけが作った・変えたファイル

なし（全員が同じファイルの集合を変えた）

### 一部のエージェントだけが作った名前（全員に共通の新しい名前は 1 個）

なし

### 内容の類似度が低いファイル

#### `tests/test_policy.py`（agent-2 と agent-3、類似度 0.952）

```diff
--- agent-2/tests/test_policy.py
+++ agent-3/tests/test_policy.py
@@ -97,13 +97,13 @@
             names = [option.name for option in gate.options]
             self.assertEqual(len(names), len(set(names)))
 
-    def test_lens_performance(self) -> None:
-        self.assertIn("performance", policy.depth_of(policy.HIGH).lenses)
-        self.assertNotIn("performance", policy.depth_of(policy.MEDIUM).lenses)
-        self.assertNotIn("performance", policy.depth_of(policy.LOW).lenses)
-
     def test_depths_match_lenses(self) -> None:
         lenses = {lens.name for lens in policy.LENSES}
         for depth in policy.DEPTHS:
             self.assertLessEqual(set(depth.lenses), lenses)
             self.assertLessEqual(depth.threshold, depth.verifiers)
+
+    def test_lens_performance(self) -> None:
+        self.assertIn("performance", policy.depth_of(policy.HIGH).lenses)
+        self.assertNotIn("performance", policy.depth_of(policy.MEDIUM).lenses)
+        self.assertNotIn("performance", policy.depth_of(policy.LOW).lenses)
```

#### `kit/.autoflow/templates/prompts/finder.md`（agent-1 と agent-2、類似度 0.980）

```diff
--- agent-1/kit/.autoflow/templates/prompts/finder.md
+++ agent-2/kit/.autoflow/templates/prompts/finder.md
@@ -19,7 +19,7 @@
 | `security` | 入力の検証、注入、認可の抜け、秘密情報の露出、安全でない既定値 |
 | `intent` | 計画の受け入れ条件を満たさない、範囲の外の変更、やらないことに反する、リポジトリの決まり（CLAUDE.md、レビューの指示）に反する |
 | `impact` | 変えた関数・型・設定の呼び出し元への影響、互換性、データの形、他の箇所の同じ前提 |
-| `performance` | 入力の大きさに対して増えすぎる計算量、ループの中の I/O（ファイル、DB、ネットワーク、外部コマンド）、同じ値の不要な再計算、メモリの使い方（全件の読み込み、大きな複製、手放されない参照） |
+| `performance` | 入力の大きさに対する計算量、ループの中の I/O（ファイル、DB、ネットワーク）、同じ値の不要な再計算、メモリの使い方（全件の読み込み、大きな写し） |
 
 ## 指摘にしないもの
 
```


## T3-cross

### 一部のエージェントだけが作った・変えたファイル

| ファイル | agent-1 | agent-2 | agent-3 |
|---|---|---|---|
| `docs/design/architecture.md` | ✓ | ✓ | – |

### 一部のエージェントだけが作った名前（全員に共通の新しい名前は 2 個）

- agent-1: `_pending_line`
- agent-2: `_pending_line`, `del`
- agent-3: `_finding_line`, `del`

### 内容の類似度が低いファイル

#### `tests/test_views.py`（agent-1 と agent-2、類似度 0.854）

```diff
--- agent-1/tests/test_views.py
+++ agent-2/tests/test_views.py
@@ -8,11 +8,9 @@
 from tests import support
 
 
-def kept(tag: str = policy.IMPORTANT, suggested_fix: str = "") -> contracts.Kept:
+def kept(tag: str = policy.IMPORTANT) -> contracts.Kept:
     finding = contracts.parse_findings(
-        {"findings": [support.finding(other_locations=["calc.py:20"], suggested_fix=suggested_fix)]},
-        policy.REVIEW.categories,
-        [],
+        {"findings": [support.finding(other_locations=["calc.py:20"])]}, policy.REVIEW.categories, []
     )[0]
     return contracts.Kept("R1-1", tag, 2, 3, ("correctness",), finding)
 
@@ -39,16 +37,12 @@
         )
 
     def test_review(self) -> None:
-        result = contracts.ReviewResult(
-            2, "b" * 40, "a" * 40, "standard", (kept(policy.NIT, "負の数の積を確かめるテストを足す"),), ("R2-2",)
-        )
+        result = contracts.ReviewResult(2, "b" * 40, "a" * 40, "standard", (kept(policy.NIT),), ("R2-2",))
         text = views.render_review(result)
         self.assertIn("# レビュー ラウンド 2", text)
         self.assertIn("| R1-1 | Nit |", text)
         self.assertIn("票で落ちた候補: R2-2", text)
-        self.assertIn("直し方の案: 負の数の積を確かめるテストを足す", text)
-        empty = contracts.ReviewResult(1, "b" * 40, "a" * 40, "quick", (kept(),), ())
-        self.assertIn("直し方の案: —", views.render_review(empty))
+        self.assertIn("直し方の案: multiply(-1, 2) が -2 を返すことを確かめるテストを足す", text)
 
     def test_gate(self) -> None:
         text = views.render_gate(policy.H2, ("h2_fix_attempts",), ("続いた検査の失敗: 3 回",))
```

#### `tests/test_contracts.py`（agent-1 と agent-3、類似度 0.871）

```diff
--- agent-1/tests/test_contracts.py
+++ agent-3/tests/test_contracts.py
@@ -45,21 +45,25 @@
         contracts.parse_report(report, problems)
         self.assertEqual(problems, ["resolutions[0].reason が空です。退けるなら理由を書く"])
 
-    def test_parse_findings(self) -> None:
-        problems: list[str] = []
-        items = [support.finding(suggested_fix="負の数の積を確かめるテストを足す"), support.finding()]
-        found = contracts.parse_findings({"findings": items}, policy.REVIEW.categories, problems)
-        self.assertEqual(problems, [])
-        self.assertEqual([item.suggested_fix for item in found], ["負の数の積を確かめるテストを足す", ""])
-        missing = {key: value for key, value in support.finding().items() if key != "suggested_fix"}
-        contracts.parse_findings({"findings": [missing]}, policy.REVIEW.categories, problems)
-        self.assertEqual(problems, ["findings[0].suggested_fix は文字列にしてください"])
-
     def test_findings_category(self) -> None:
         problems: list[str] = []
         contracts.parse_findings({"findings": [support.finding(category="style")]}, policy.REVIEW.categories, problems)
         self.assertEqual(len(problems), 1)
         self.assertIn("bug, security, criteria, fit", problems[0])
+
+    def test_parse_findings(self) -> None:
+        problems: list[str] = []
+        found = contracts.parse_findings(
+            {"findings": [support.finding(), support.finding(suggested_fix="0 の下限を付ける")]},
+            policy.REVIEW.categories,
+            problems,
+        )
+        self.assertEqual(problems, [])
+        self.assertEqual([item.suggested_fix for item in found], ["", "0 の下限を付ける"])
+        missing = support.finding()
+        del missing["suggested_fix"]
+        contracts.parse_findings({"findings": [missing]}, policy.REVIEW.categories, problems)
+        self.assertEqual(problems, ["findings[0].suggested_fix は文字列にしてください"])
 
     def test_votes_one_per_candidate(self) -> None:
         vote = {"id": "R1-1", "verdict": "real", "tag": "important", "reason": "確かめた"}
```

#### `kit/.autoflow/templates/prompts/finder.md`（agent-1 と agent-2、類似度 0.940）

```diff
--- agent-1/kit/.autoflow/templates/prompts/finder.md
+++ agent-2/kit/.autoflow/templates/prompts/finder.md
@@ -37,8 +37,8 @@
 
 - 根拠のあるバグだけを書く。`file` と `line` は変更後のファイルの場所にし、`evidence` に、そのバグが起きる入力や手順を書く
 - `bug_class` にバグの種類を短い名詞で書く（例：境界の値の取り違え、null の確かめ漏れ）。同じ種類のバグが他の箇所にもあれば、`other_locations` に `file:line` で全部書く。作者が1行ではなく全部を直せるようにするため
+- `suggested_fix` に直し方の案を1〜2文で書く。直し方が分からなければ空の文字列 `""` にする。確かめていない直し方を推測で書かない
 - この差分が持ち込んだのではない、前からあるバグは `pre_existing` を `true` にする
-- `suggested_fix` に直し方の案を1〜2文で書く。実装役が直すときの参考にするため。直し方が分からなければ、推測で埋めずに空の文字列にする
 - `category` は `bug`（振る舞いの誤り）・`security`（安全の問題）・`criteria`（受け入れ条件を満たさない）・`fit`（範囲の外の変更か、リポジトリの決まりに反する）のどれか
 - 見つからなければ空の配列にする。数を出すために弱い指摘を書かない
 
@@ -57,8 +57,8 @@
       "evidence": "合計 100、割引 150 のとき total() は -50 を返す。注文の確定（src/order/confirm.py:55）は負の金額を想定していない",
       "bug_class": "下限の確かめ漏れ",
       "other_locations": ["src/cart/tax.py:17"],
-      "pre_existing": false,
-      "suggested_fix": "total() で合計から割引を引いた値を 0 以上に切り上げる"
+      "suggested_fix": "total() で割引を合計で頭打ちにし、0 未満を返さないようにする。tax.py:17 も同じ形で直す",
+      "pre_existing": false
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
-        support.review_round(where, run_id, {"correctness": [support.finding(suggested_fix="負の数のテストを足す")]})
+        support.review_round(where, run_id, {"correctness": [support.finding()]})
         building.build_new(where, run_id, NOW)
         prompt = fsops.read_text(where.build_prompt_path(run_id, 2))
         self.assertIn("R1-1 [Important]", prompt)
-        self.assertIn("— 直し方の案: 負の数のテストを足す", prompt)
+        self.assertIn("— 直し方の案: multiply(-1, 2) が -2 を返すことを確かめるテストを足す", prompt)
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
 
-一覧が `- なし` なら、回答の要る指摘は無い。各行は「id [重大度] 題名 — 場所、バグの種類（同じ種類の他の箇所） — 直し方の案」である。直し方の案は探索役が書いた参考で、`—` なら案は無い。案に従うかは、コードを読んで自分で決める。
+一覧が `- なし` なら、回答の要る指摘は無い。各行は「id [重大度] 題名 — 場所、バグの種類（同じ種類の他の箇所） — 直し方の案」である。直し方の案が `—` なら、探索役は案を出していない。案は探索役の見立てなので、コードで確かめてから直し方を決める。
 
 ${findings}
 
```
