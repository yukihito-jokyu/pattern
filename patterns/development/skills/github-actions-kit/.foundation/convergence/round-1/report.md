# 収束テスト ラウンド 1 のレポート

このファイルは convergence.py diff が生成する。揺れの分類（R1〜R7）と対処は convergence-report.md に書く。

基準: files ≥ 1.0、names ≥ 0.8、content ≥ 0.0、check は全員通過、保護ファイルの変更なし

## 指標

| 課題 | files | names | content | check | 保護 | 基準 |
|---|---|---|---|---|---|---|
| T1-add | 0.778 | 1.000 | 0.943 | 全員通過 | 変更あり | 満たさない |
| T2-change | 1.000 | 0.333 | 0.940 | 全員通過 | — | 満たさない |
| T3-cross | 0.600 | 1.000 | 0.988 | 全員通過 | 変更あり | 満たさない |

## T1-add

### 一部のエージェントだけが作った・変えたファイル

| ファイル | agent-1 | agent-2 | agent-3 |
|---|---|---|---|
| `docs/design/architecture.md` | ✓ | – | – |

### 一部のエージェントだけが作った名前（全員に共通の新しい名前は 0 個）

なし

### 内容の類似度が低いファイル

#### `.claude/skills/gha-workflow/references/examples/workflows/ci.yml`（agent-1 と agent-2、類似度 0.923）

```diff
--- agent-1/.claude/skills/gha-workflow/references/examples/workflows/ci.yml
+++ agent-2/.claude/skills/gha-workflow/references/examples/workflows/ci.yml
@@ -33,13 +33,11 @@
         run: git init "$RUNNER_TEMP/target"
       - name: Install kit into empty repository
         run: python3 install.py "$RUNNER_TEMP/target"
-      # 導入しただけでは dependabot.yml が無く（PROC-03）、ワークフローも無いので actionlint が動かない。配布先の作者と同じく見本を写す
-      - name: Create workflows from installed examples
+      - name: Create workflows from examples
         working-directory: ${{ runner.temp }}/target
-        run: |
-          mkdir -p .github/workflows
-          cp .claude/skills/gha-workflow/references/examples/dependabot.yml .github/
-          cp .claude/skills/gha-workflow/references/examples/workflows/security-audit.yml .github/workflows/
+        env:
+          EXAMPLES: .claude/skills/gha-workflow/references/examples
+        run: cp -R --update=none "$EXAMPLES/." .github/ # 導入した run-report を見本の写しで上書きしない
       - name: Check workflows in installed repository
         working-directory: ${{ runner.temp }}/target
         run: uv run --locked --script .gha/gha.py check
```

#### `.github/workflows/ci.yml`（agent-1 と agent-2、類似度 0.923）

```diff
--- agent-1/.github/workflows/ci.yml
+++ agent-2/.github/workflows/ci.yml
@@ -33,13 +33,11 @@
         run: git init "$RUNNER_TEMP/target"
       - name: Install kit into empty repository
         run: python3 install.py "$RUNNER_TEMP/target"
-      # 導入しただけでは dependabot.yml が無く（PROC-03）、ワークフローも無いので actionlint が動かない。配布先の作者と同じく見本を写す
-      - name: Create workflows from installed examples
+      - name: Create workflows from examples
         working-directory: ${{ runner.temp }}/target
-        run: |
-          mkdir -p .github/workflows
-          cp .claude/skills/gha-workflow/references/examples/dependabot.yml .github/
-          cp .claude/skills/gha-workflow/references/examples/workflows/security-audit.yml .github/workflows/
+        env:
+          EXAMPLES: .claude/skills/gha-workflow/references/examples
+        run: cp -R --update=none "$EXAMPLES/." .github/ # 導入した run-report を見本の写しで上書きしない
       - name: Check workflows in installed repository
         working-directory: ${{ runner.temp }}/target
         run: uv run --locked --script .gha/gha.py check
```


### 保護ファイルを変えたエージェント（基準を満たさない扱い。設定やルールの緩和でないか差分を確かめる）

- agent-1: `.claude/skills/gha-workflow/references/examples/workflows/ci.yml`
- agent-2: `.claude/skills/gha-workflow/references/examples/workflows/ci.yml`
- agent-3: `.claude/skills/gha-workflow/references/examples/workflows/ci.yml`

## T2-change

### 一部のエージェントだけが作った・変えたファイル

なし（全員が同じファイルの集合を変えた）

### 一部のエージェントだけが作った名前（全員に共通の新しい名前は 1 個）

- agent-1: `assertRegex`, `test_lists_failed_steps_only_in_failed_job_rows`
- agent-2: `test_lists_failed_steps_only_in_the_rows_of_failed_jobs`
- agent-3: `Lint`, `test_lists_failed_steps_only_in_failed_job_rows`

### 内容の類似度が低いファイル

#### `tests/test_run_report.py`（agent-1 と agent-2、類似度 0.890）

```diff
--- agent-1/tests/test_run_report.py
+++ agent-2/tests/test_run_report.py
@@ -51,22 +51,24 @@
         self.assertIn("<summary>test のステップ（2分0秒）</summary>", body)
         self.assertIn("    test : done, j2, 3, 123", body)
 
-    def test_lists_failed_steps_only_in_failed_job_rows(self) -> None:
-        steps = (
-            run_report.Step(1, "Unit", "failure", 10),
-            run_report.Step(2, "E2E", "failure", 20),
-            run_report.Step(3, "Upload", "success", 5),
+    def test_lists_failed_steps_only_in_the_rows_of_failed_jobs(self) -> None:
+        failed = job_payload("test", "2026-10-23T00:00:00Z", "2026-10-23T00:00:03Z", "2026-10-23T00:02:03Z")
+        failed["conclusion"] = "failure"
+        failed["steps"] = [
+            {"number": 1, "name": "Run unit tests", "conclusion": "failure"},
+            {"number": 2, "name": "Run e2e tests", "conclusion": "failure"},
+            {"number": 3, "name": "Upload results", "conclusion": "skipped"},
+        ]
+        jobs = run_report.to_jobs(
+            [job_payload("lint", "2026-10-23T00:00:00Z", "2026-10-23T00:00:02Z", "2026-10-23T00:01:02Z"), failed]
         )
-        jobs = [
-            run_report.Job("lint", "https://example.test/lint", "success", 0, 1, 30, steps[2:]),
-            run_report.Job("test", "https://example.test/test", "failure", 0, 1, 35, steps),
-        ]
 
         body = run_report.render(run_report.Run("ci", "https://example.test/run", "7", "1"), jobs, ["test"])
+        rows = {line.split("]")[0]: line for line in body.splitlines() if line.startswith("| [")}
 
-        self.assertIn("| 割合 | 失敗したステップ |", body)
-        self.assertRegex(body, r"\| \[lint\]\(https://example\.test/lint\) \|.* \|  \|\n")
-        self.assertRegex(body, r"\| \[test\]\(https://example\.test/test\) \|.* \| Unit、E2E \|\n")
+        self.assertIn("| ジョブ | 結果 | 待ち | 実行 | 割合 | 失敗したステップ |", body)
+        self.assertTrue(rows["| [lint"].endswith("|  |"))
+        self.assertTrue(rows["| [test"].endswith("| Run unit tests、Run e2e tests |"))
 
     def test_fit_drops_step_details_over_the_limit(self) -> None:
         jobs = run_report.to_jobs(
```

#### `.github/actions/run-report/run_report.py`（agent-1 と agent-2、類似度 0.983）

```diff
--- agent-1/.github/actions/run-report/run_report.py
+++ agent-2/.github/actions/run-report/run_report.py
@@ -171,6 +171,13 @@
     return "`" + "█" * filled + "·" * (BAR_WIDTH - filled) + "`"
 
 
+def failed_steps(job: Job) -> str:
+    """失敗したジョブなら、失敗したステップの名前を「、」でつなぐ。それ以外のジョブは空にする。"""
+    if job.conclusion != "failure":
+        return ""
+    return "、".join(_cell(step.name) for step in job.steps if step.conclusion == "failure")
+
+
 def failed_needs(needs_json: str) -> list[str]:
     """needs のうち、結果が success でも skipped でもないジョブの ID を返す。"""
     needs = json.loads(needs_json or "{}")
@@ -214,13 +221,6 @@
     return "\n".join(lines)
 
 
-def failed_steps(job: Job) -> str:
-    """失敗したジョブなら、失敗したステップの名前を「、」でつなぐ。それ以外のジョブは空にする。"""
-    if job.conclusion != "failure":
-        return ""
-    return "、".join(_cell(step.name) for step in job.steps if step.conclusion == "failure")
-
-
 def render_slowest(jobs: Sequence[Job]) -> list[str]:
     steps = sorted(((step, job) for job in jobs for step in job.steps), key=lambda pair: -pair[0].seconds)[:SLOWEST]
     lines = [f"<details><summary>遅いステップ（上位 {SLOWEST} 件）</summary>", "", "| ステップ | ジョブ | 時間 |"]
```


## T3-cross

### 一部のエージェントだけが作った・変えたファイル

| ファイル | agent-1 | agent-2 | agent-3 |
|---|---|---|---|
| `.claude/skills/gha-workflow/references/examples/workflows/reusable-check.yml` | – | ✓ | – |
| `.github/workflows/reusable-check.yml` | – | ✓ | – |
| `docs/design/architecture.md` | – | ✓ | – |

### 一部のエージェントだけが作った名前（全員に共通の新しい名前は 0 個）

なし

### 内容の類似度が低いファイル

#### `.claude/skills/gha-workflow/references/examples/workflows/deploy-pages.yml`（agent-1 と agent-2、類似度 0.982）

```diff
--- agent-1/.claude/skills/gha-workflow/references/examples/workflows/deploy-pages.yml
+++ agent-2/.claude/skills/gha-workflow/references/examples/workflows/deploy-pages.yml
@@ -1,4 +1,4 @@
-# main への push と手動の実行で、docs/ を Jekyll で HTML にして GitHub Pages に公開する
+# main への push と手動の実行で、検査を回してから docs/ を Jekyll で HTML にして GitHub Pages に公開する
 name: deploy-pages
 on:
   push:
```

#### `.github/workflows/deploy-pages.yml`（agent-1 と agent-2、類似度 0.982）

```diff
--- agent-1/.github/workflows/deploy-pages.yml
+++ agent-2/.github/workflows/deploy-pages.yml
@@ -1,4 +1,4 @@
-# main への push と手動の実行で、docs/ を Jekyll で HTML にして GitHub Pages に公開する
+# main への push と手動の実行で、検査を回してから docs/ を Jekyll で HTML にして GitHub Pages に公開する
 name: deploy-pages
 on:
   push:
```


### 保護ファイルを変えたエージェント（基準を満たさない扱い。設定やルールの緩和でないか差分を確かめる）

- agent-1: `.claude/skills/gha-workflow/references/examples/workflows/deploy-pages.yml`
- agent-2: `.claude/skills/gha-workflow/references/examples/workflows/deploy-pages.yml`, `.claude/skills/gha-workflow/references/examples/workflows/reusable-check.yml`
- agent-3: `.claude/skills/gha-workflow/references/examples/workflows/deploy-pages.yml`
