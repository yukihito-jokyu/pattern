# 収束テスト ラウンド 2 のレポート

このファイルは convergence.py diff が生成する。揺れの分類（R1〜R7）と対処は convergence-report.md に書く。

基準: files ≥ 1.0、names ≥ 0.8、content ≥ 0.0、check は全員通過、保護ファイルの変更なし

## 指標

| 課題 | files | names | content | check | 保護 | 基準 |
|---|---|---|---|---|---|---|
| T1-add | 1.000 | 0.467 | 0.984 | 全員通過 | — | 満たさない |
| T2-change | 1.000 | 0.667 | 0.990 | 全員通過 | — | 満たさない |
| T3-cross | 1.000 | 0.833 | 0.975 | 全員通過 | — | 満たす |

## T1-add

### 一部のエージェントだけが作った・変えたファイル

なし（全員が同じファイルの集合を変えた）

### 一部のエージェントだけが作った名前（全員に共通の新しい名前は 1 個）

- agent-1: `h1_human_only`, `test_h1_human_only`
- agent-2: `h1_human_criteria`, `test_h1_human_criteria`
- agent-3: `h1_human_only`, `test_h1_human_only`

### 内容の類似度が低いファイル

#### `tests/test_policy.py`（agent-1 と agent-2、類似度 0.954）

```diff
--- agent-1/tests/test_policy.py
+++ agent-2/tests/test_policy.py
@@ -103,10 +103,10 @@
             self.assertLessEqual(set(depth.lenses), lenses)
             self.assertLessEqual(depth.threshold, depth.verifiers)
 
-    def test_h1_human_only(self) -> None:
-        human = {"id": "C1", "text": "画面の文言が読みやすい", "check": "human", "run": ""}
+    def test_h1_human_criteria(self) -> None:
+        human = {"id": "C1", "text": "画面の文言が自然である", "check": "human", "run": ""}
+        self.assertEqual(policy.h1_reasons(plan(criteria=[human]), SETTINGS), ("h1_human_criteria",))
         review = {"id": "C2", "text": "既存の関数と同じ書き方である", "check": "review", "run": ""}
+        self.assertEqual(policy.h1_reasons(plan(criteria=[human, review]), SETTINGS), ())
         command = {"id": "C2", "text": "テストが通る", "check": "command", "run": "make test"}
-        self.assertEqual(policy.h1_reasons(plan(criteria=[human]), SETTINGS), ("h1_human_only",))
-        self.assertEqual(policy.h1_reasons(plan(criteria=[human, review]), SETTINGS), ())
         self.assertEqual(policy.h1_reasons(plan(criteria=[human, command]), SETTINGS), ())
```

#### `kit/claude/skills/autoflow/references/gates.md`（agent-1 と agent-2、類似度 0.988）

```diff
--- agent-1/kit/claude/skills/autoflow/references/gates.md
+++ agent-2/kit/claude/skills/autoflow/references/gates.md
@@ -57,7 +57,7 @@
 | `h1_dependency` | 依存を足す計画である |
 | `h1_scope` | 計画の範囲が limits.max_scope_files を超える |
 | `h1_always_human` | 計画の範囲が risk.always_human のパスに当たる |
-| `h1_human_only` | 受け入れ条件の全部が、人が確かめるもの（check が human）である |
+| `h1_human_criteria` | 受け入れ条件が全部、人が確かめるもの（check が human）である |
 
 ## H2 を起こす条件（どれか1つに当たれば聞く）
 
```

#### `kit/.autoflow/autoflow_kit/policy.py`（agent-1 と agent-2、類似度 0.997）

```diff
--- agent-1/kit/.autoflow/autoflow_kit/policy.py
+++ agent-2/kit/.autoflow/autoflow_kit/policy.py
@@ -210,7 +210,7 @@
     PlanRule("h1_dependency", "依存を足す計画である", _has_new_dependency),
     PlanRule("h1_scope", "計画の範囲が limits.max_scope_files を超える", _is_wide),
     PlanRule("h1_always_human", "計画の範囲が risk.always_human のパスに当たる", _has_human_paths),
-    PlanRule("h1_human_only", "受け入れ条件の全部が、人が確かめるもの（check が human）である", _is_human_only),
+    PlanRule("h1_human_criteria", "受け入れ条件が全部、人が確かめるもの（check が human）である", _is_human_only),
 )
 # H2（行き詰まり）を起こす条件。記事の「3ラウンドで止まって方針を見直す」に当たる
 H2_RULES = (
```


## T2-change

### 一部のエージェントだけが作った・変えたファイル

なし（全員が同じファイルの集合を変えた）

### 一部のエージェントだけが作った名前（全員に共通の新しい名前は 1 個）

- agent-3: `used`

### 内容の類似度が低いファイル

#### `kit/.autoflow/templates/prompts/finder.md`（agent-1 と agent-2、類似度 0.980）

```diff
--- agent-1/kit/.autoflow/templates/prompts/finder.md
+++ agent-2/kit/.autoflow/templates/prompts/finder.md
@@ -19,7 +19,7 @@
 | `security` | 入力の検証、注入、認可の抜け、秘密情報の露出、安全でない既定値 |
 | `intent` | 計画の受け入れ条件を満たさない、範囲の外の変更、やらないことに反する、リポジトリの決まり（CLAUDE.md、レビューの指示）に反する |
 | `impact` | 変えた関数・型・設定の呼び出し元への影響、互換性、データの形、他の箇所の同じ前提 |
-| `performance` | 計算量、ループの中の I/O、不要な再計算、メモリの使い方 |
+| `performance` | 入力の大きさに対する計算量、ループの中の I/O（ファイル、ネットワーク、DB、外部コマンド）、同じ値の不要な再計算、メモリの使い方（全件の読み込み、大きな写し、解放されない参照） |
 
 ## 指摘にしないもの
 
```

#### `tests/test_policy.py`（agent-1 と agent-3、類似度 0.970）

```diff
--- agent-1/tests/test_policy.py
+++ agent-3/tests/test_policy.py
@@ -105,6 +105,5 @@
 
     def test_lens_performance(self) -> None:
         self.assertIn("performance", [lens.name for lens in policy.LENSES])
-        self.assertIn("performance", policy.depth_of(policy.HIGH).lenses)
-        self.assertNotIn("performance", policy.depth_of(policy.MEDIUM).lenses)
-        self.assertNotIn("performance", policy.depth_of(policy.LOW).lenses)
+        used = [tier.name for tier in policy.TIERS if "performance" in policy.depth_of(tier.name).lenses]
+        self.assertEqual(used, [policy.HIGH])
```


## T3-cross

### 一部のエージェントだけが作った・変えたファイル

なし（全員が同じファイルの集合を変えた）

### 一部のエージェントだけが作った名前（全員に共通の新しい名前は 3 個）

- agent-3: `fixable`

### 内容の類似度が低いファイル

#### `tests/test_views.py`（agent-1 と agent-3、類似度 0.875）

```diff
--- agent-1/tests/test_views.py
+++ agent-3/tests/test_views.py
@@ -8,9 +8,11 @@
 from tests import support
 
 
-def kept(tag: str = policy.IMPORTANT) -> contracts.Kept:
+def kept(tag: str = policy.IMPORTANT, suggested_fix: str = "") -> contracts.Kept:
     finding = contracts.parse_findings(
-        {"findings": [support.finding(other_locations=["calc.py:20"])]}, policy.REVIEW.categories, []
+        {"findings": [support.finding(other_locations=["calc.py:20"], suggested_fix=suggested_fix)]},
+        policy.REVIEW.categories,
+        [],
     )[0]
     return contracts.Kept("R1-1", tag, 2, 3, ("correctness",), finding)
 
@@ -42,7 +44,11 @@
         self.assertIn("# レビュー ラウンド 2", text)
         self.assertIn("| R1-1 | Nit |", text)
         self.assertIn("票で落ちた候補: R2-2", text)
-        self.assertIn("- 直し方の案: —", text)
+        self.assertIn("直し方の案: —", text)
+        fixable = contracts.ReviewResult(
+            1, "b" * 40, "a" * 40, "standard", (kept(suggested_fix="負の数を確かめる"),), ()
+        )
+        self.assertIn("直し方の案: 負の数を確かめる", views.render_review(fixable))
 
     def test_gate(self) -> None:
         text = views.render_gate(policy.H2, ("h2_fix_attempts",), ("続いた検査の失敗: 3 回",))
```

#### `tests/test_contracts.py`（agent-1 と agent-2、類似度 0.947）

```diff
--- agent-1/tests/test_contracts.py
+++ agent-2/tests/test_contracts.py
@@ -87,8 +87,13 @@
 
     def test_parse_findings(self) -> None:
         problems: list[str] = []
-        found = contracts.parse_findings({"findings": [support.finding()]}, policy.REVIEW.categories, problems)
-        self.assertEqual((problems, found[0].suggested_fix), ([], ""))
+        found = contracts.parse_findings(
+            {"findings": [support.finding(suggested_fix="0 を下限にする"), support.finding()]},
+            policy.REVIEW.categories,
+            problems,
+        )
+        self.assertEqual(problems, [])
+        self.assertEqual([item.suggested_fix for item in found], ["0 を下限にする", ""])
         missing = support.finding()
         del missing["suggested_fix"]
         contracts.parse_findings({"findings": [missing]}, policy.REVIEW.categories, problems)
```

#### `kit/.autoflow/templates/prompts/finder.md`（agent-1 と agent-2、類似度 0.960）

```diff
--- agent-1/kit/.autoflow/templates/prompts/finder.md
+++ agent-2/kit/.autoflow/templates/prompts/finder.md
@@ -38,7 +38,7 @@
 - 根拠のあるバグだけを書く。`file` と `line` は変更後のファイルの場所にし、`evidence` に、そのバグが起きる入力や手順を書く
 - `bug_class` にバグの種類を短い名詞で書く（例：境界の値の取り違え、null の確かめ漏れ）。同じ種類のバグが他の箇所にもあれば、`other_locations` に `file:line` で全部書く。作者が1行ではなく全部を直せるようにするため
 - この差分が持ち込んだのではない、前からあるバグは `pre_existing` を `true` にする
-- `suggested_fix` に直し方の案を短く書く。作者が直すときの手がかりにするため。直し方が分からなければ空の文字列 `""` にする
+- `suggested_fix` に直し方の案を短く書く。実装役に渡す指摘の一覧と、レビューの結果に載る。直し方が分からなければ空の文字列にする
 - `category` は `bug`（振る舞いの誤り）・`security`（安全の問題）・`criteria`（受け入れ条件を満たさない）・`fit`（範囲の外の変更か、リポジトリの決まりに反する）のどれか
 - 見つからなければ空の配列にする。数を出すために弱い指摘を書かない
 
@@ -58,7 +58,7 @@
       "bug_class": "下限の確かめ漏れ",
       "other_locations": ["src/cart/tax.py:17"],
       "pre_existing": false,
-      "suggested_fix": "total() で割引を合計で頭打ちにし、合計が 0 未満にならないようにする"
+      "suggested_fix": "total() で割引を引いた後、0 を下限にする"
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
+        support.review_round(where, run_id, {"correctness": [support.finding(suggested_fix="0 を下限にする")]})
         building.build_new(where, run_id, NOW)
         prompt = fsops.read_text(where.build_prompt_path(run_id, 2))
         self.assertIn("R1-1 [Important]", prompt)
-        self.assertIn("— 直し方の案: 負の数のテストを足す", prompt)
+        self.assertIn("— 直し方の案: 0 を下限にする", prompt)
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
 
-一覧が `- なし` なら、回答の要る指摘は無い。各行は「id [重大度] 題名 — 場所、バグの種類（同じ種類の他の箇所） — 直し方の案」である。直し方の案が `—` なら、探索役の案は無い。案は手がかりであり、案と違う直し方を選んでよい。
+一覧が `- なし` なら、回答の要る指摘は無い。各行は「id [重大度] 題名 — 場所、バグの種類（同じ種類の他の箇所） — 直し方の案」である。直し方の案が `—` なら、探索役の案は無い。
 
 ${findings}
 
```
