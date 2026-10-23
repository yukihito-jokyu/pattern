# 収束テスト ラウンド 2 のレポート

このファイルは convergence.py diff が生成する。揺れの分類（R1〜R7）と対処は convergence-report.md に書く。

基準: files ≥ 1.0、names ≥ 0.8、content ≥ 0.0、check は全員通過、保護ファイルの変更なし

## 指標

| 課題 | files | names | content | check | 保護 | 基準 |
|---|---|---|---|---|---|---|
| T1-add | 1.000 | 1.000 | 0.955 | 全員通過 | — | 満たす |
| T2-change | 1.000 | 0.556 | 0.955 | 全員通過 | — | 満たさない |
| T3-cross | 1.000 | 1.000 | 1.000 | 全員通過 | — | 満たす |

## T1-add

### 一部のエージェントだけが作った・変えたファイル

なし（全員が同じファイルの集合を変えた）

### 一部のエージェントだけが作った名前（全員に共通の新しい名前は 0 個）

なし

### 内容の類似度が低いファイル

#### `.claude/skills/gha-workflow/references/examples/workflows/ci.yml`（agent-1 と agent-2、類似度 0.949）

```diff
--- agent-1/.claude/skills/gha-workflow/references/examples/workflows/ci.yml
+++ agent-2/.claude/skills/gha-workflow/references/examples/workflows/ci.yml
@@ -29,11 +29,11 @@
           persist-credentials: false
       - name: Set up uv
         uses: astral-sh/setup-uv@07a047e608db84b3d8c06cd9a7c7dcc9c355c18e # v10.3.2
-      - name: Create empty target repository
+      - name: Create empty repository
         run: git init "$RUNNER_TEMP/target"
-      - name: Install kit into target repository
+      - name: Install kit
         run: python3 install.py "$RUNNER_TEMP/target"
-      - name: Check workflows in target repository
+      - name: Check workflows
         working-directory: ${{ runner.temp }}/target
         run: uv run --locked --script .gha/gha.py check
   report:
```

#### `.github/workflows/ci.yml`（agent-1 と agent-2、類似度 0.949）

```diff
--- agent-1/.github/workflows/ci.yml
+++ agent-2/.github/workflows/ci.yml
@@ -29,11 +29,11 @@
           persist-credentials: false
       - name: Set up uv
         uses: astral-sh/setup-uv@07a047e608db84b3d8c06cd9a7c7dcc9c355c18e # v10.3.2
-      - name: Create empty target repository
+      - name: Create empty repository
         run: git init "$RUNNER_TEMP/target"
-      - name: Install kit into target repository
+      - name: Install kit
         run: python3 install.py "$RUNNER_TEMP/target"
-      - name: Check workflows in target repository
+      - name: Check workflows
         working-directory: ${{ runner.temp }}/target
         run: uv run --locked --script .gha/gha.py check
   report:
```


## T2-change

### 一部のエージェントだけが作った・変えたファイル

なし（全員が同じファイルの集合を変えた）

### 一部のエージェントだけが作った名前（全員に共通の新しい名前は 1 個）

- agent-1: `test_lists_failed_steps_only_on_failed_jobs`
- agent-2: `test_lists_failed_steps_only_on_failed_jobs`
- agent-3: `test_names_failed_steps_only_on_failed_job_rows`

### 内容の類似度が低いファイル

#### `tests/test_run_report.py`（agent-1 と agent-3、類似度 0.892）

```diff
--- agent-1/tests/test_run_report.py
+++ agent-3/tests/test_run_report.py
@@ -51,25 +51,25 @@
         self.assertIn("<summary>test のステップ（2分0秒）</summary>", body)
         self.assertIn("    test : done, j2, 3, 123", body)
 
-    def test_lists_failed_steps_only_on_failed_jobs(self) -> None:
-        failed = {
-            **job_payload("test", "2026-10-23T00:00:00Z", "2026-10-23T00:00:03Z", "2026-10-23T00:02:03Z"),
-            "conclusion": "failure",
-            "steps": [
-                {"number": 1, "name": "Run unit tests", "conclusion": "failure"},
-                {"number": 2, "name": "Run e2e tests", "conclusion": "failure"},
-                {"number": 3, "name": "Upload results", "conclusion": "skipped"},
-            ],
-        }
+    def test_names_failed_steps_only_on_failed_job_rows(self) -> None:
+        failed = job_payload("test", "2026-10-23T00:00:00Z", "2026-10-23T00:00:03Z", "2026-10-23T00:02:03Z")
+        failed["conclusion"] = "failure"
+        failed["steps"] = [
+            {"number": 1, "name": "Run unit", "conclusion": "failure"},
+            {"number": 2, "name": "Run e2e", "conclusion": "failure"},
+            {"number": 3, "name": "Upload", "conclusion": "skipped"},
+        ]
         jobs = run_report.to_jobs(
             [job_payload("lint", "2026-10-23T00:00:00Z", "2026-10-23T00:00:02Z", "2026-10-23T00:01:02Z"), failed]
         )
 
         body = run_report.render(run_report.Run("ci", "https://example.test/run", "7", "1"), jobs, ["test"])
 
-        rows = [line for line in body.splitlines() if line.startswith("| [")]
-        self.assertTrue(rows[0].endswith("|  |"))
-        self.assertTrue(rows[1].endswith("| Run unit tests、Run e2e tests |"))
+        self.assertIn("| [lint](https://example.test/lint) | ✅ 成功 | 2秒 | 1分0秒 | `█████·····` |  |", body)
+        self.assertIn(
+            "| [test](https://example.test/test) | ❌ 失敗 | 3秒 | 2分0秒 | `██████████` | Run unit、Run e2e |",
+            body,
+        )
 
     def test_fit_drops_step_details_over_the_limit(self) -> None:
         jobs = run_report.to_jobs(
```

#### `.github/actions/run-report/run_report.py`（agent-1 と agent-2、類似度 0.997）

```diff
--- agent-1/.github/actions/run-report/run_report.py
+++ agent-2/.github/actions/run-report/run_report.py
@@ -215,7 +215,7 @@
 
 
 def failed_steps(job: Job) -> str:
-    """失敗したジョブなら、失敗したステップの名前を「、」でつなぐ。ほかのジョブは空にする。"""
+    """失敗したジョブなら失敗したステップの名前を「、」でつなぎ、それ以外のジョブは空にする。"""
     if job.conclusion != "failure":
         return ""
     return "、".join(_cell(step.name) for step in job.steps if step.conclusion == "failure")
```


## T3-cross

### 一部のエージェントだけが作った・変えたファイル

なし（全員が同じファイルの集合を変えた）

### 一部のエージェントだけが作った名前（全員に共通の新しい名前は 0 個）

なし

### 内容の類似度が低いファイル

なし（共通して変えたファイルの中身は全員一致）
