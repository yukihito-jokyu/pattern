# 収束テスト ラウンド 2 のレポート

このファイルは convergence.py diff が生成する。揺れの分類（R1〜R7）と対処は convergence-report.md に書く。

基準: files ≥ 1.0、names ≥ 0.8、content ≥ 0.0、check は全員通過、保護ファイルの変更なし

## 指標

| 課題 | files | names | content | check | 保護 | 基準 |
|---|---|---|---|---|---|---|
| T1-add | 1.000 | 1.000 | 0.961 | 全員通過 | — | 満たす |
| T2-change | 1.000 | 1.000 | 0.952 | 全員通過 | — | 満たす |
| T3-cross | 1.000 | 1.000 | 0.951 | 全員通過 | — | 満たす |

## T1-add

### 一部のエージェントだけが作った・変えたファイル

なし（全員が同じファイルの集合を変えた）

### 一部のエージェントだけが作った名前（全員に共通の新しい名前は 1 個）

なし

### 内容の類似度が低いファイル

#### `tests/test_score.py`（agent-2 と agent-3、類似度 0.833）

```diff
--- agent-2/tests/test_score.py
+++ agent-3/tests/test_score.py
@@ -26,18 +26,18 @@
 
     def test_denials(self) -> None:
         data = support.orch_charter()
-        goals, chosen = data["goals"], data["metrics"]
-        assert isinstance(goals, list) and isinstance(chosen, list)
+        goals, choices = data["goals"], data["metrics"]
+        assert isinstance(goals, list) and isinstance(choices, list)
         goals.append({"id": "G5", "statement": "評価の環境で拒まれずに進める", "metrics": ["denials"]})
-        chosen.append({"id": "denials", "threshold": 0.0, "priority": "should"})
+        choices.append({"id": "denials", "threshold": 0.0, "priority": "should"})
         where = support.approved_layout(self, data)
-        scores = support.scored_slot(where, layout.make_slot("baseline", 1), stream="delegated")
-        found = {item.id: item for item in scores.metrics}
-        self.assertEqual((found["denials"].value, found["denials"].met), (0.0, True))
+        scores = support.scored_slot(where, layout.make_slot("baseline", 1), stream="delegated", met=True)
+        found = {item.id: item for item in scores.metrics}["denials"]
+        self.assertEqual((found.value, found.met), (0.0, True))
         where = support.approved_layout(self, data)
-        scores = support.scored_slot(where, layout.make_slot("baseline", 1), stream="main-edit")
-        found = {item.id: item for item in scores.metrics}
-        self.assertEqual((found["denials"].value, found["denials"].met), (1.0, False))
+        scores = support.scored_slot(where, layout.make_slot("baseline", 1), stream="main-edit", met=True)
+        found = {item.id: item for item in scores.metrics}["denials"]
+        self.assertEqual((found.value, found.met), (1.0, False))
 
     def test_holdout_is_separate(self) -> None:
         where = support.approved_layout(self, support.orch_charter())
```

#### `kit/claude/skills/forge-goals/references/metric-catalog.md`（agent-1 と agent-3、類似度 0.974）

```diff
--- agent-1/kit/claude/skills/forge-goals/references/metric-catalog.md
+++ agent-3/kit/claude/skills/forge-goals/references/metric-catalog.md
@@ -126,12 +126,12 @@
 | 既定の閾値 | 10.000 |
 | 前提 | — |
 
-## `denials` 権限で拒否された操作の回数
+## `denials` 権限で拒まれた操作の回数
 
 | 項目 | 内容 |
 |---|---|
-| 分かること | 1つの依頼で、実行役の操作が権限で何回拒否されるか（多いほど、スキルの手順が評価の環境に合っていない） |
-| 求め方 | 実行の記録の result の permission_denials の件数を、実行ごとに平均する。result の無い実行は0件と数える |
+| 分かること | スキルの手順が、評価の環境で許された操作だけで進められるか（拒まれるほど、手順が環境に合っていない） |
+| 求め方 | 実行の記録の result の permission_denials の件数を、実行ごとに平均する |
 | 測り方 | machine |
 | 向き | 低いほど良い |
 | 既定の閾値 | 10.000 |
```

#### `kit/.forge/forge_kit/catalog.py`（agent-1 と agent-3、類似度 0.982）

```diff
--- agent-1/kit/.forge/forge_kit/catalog.py
+++ agent-3/kit/.forge/forge_kit/catalog.py
@@ -164,15 +164,14 @@
     ),
     Metric(
         id="denials",
-        name="権限で拒否された操作の回数",
+        name="権限で拒まれた操作の回数",
         method="machine",
         direction="lower",
         default_threshold=10.0,
         max_value=None,
         recommended=False,
-        tells="1つの依頼で、実行役の操作が権限で何回拒否されるか（多いほど、スキルの手順が評価の環境に合っていない）",
-        computes="実行の記録の result の permission_denials の件数を、実行ごとに平均する。"
-        "result の無い実行は0件と数える",
+        tells="スキルの手順が、評価の環境で許された操作だけで進められるか（拒まれるほど、手順が環境に合っていない）",
+        computes="実行の記録の result の permission_denials の件数を、実行ごとに平均する",
         requires="",
     ),
 )
```


## T2-change

### 一部のエージェントだけが作った・変えたファイル

なし（全員が同じファイルの集合を変えた）

### 一部のエージェントだけが作った名前（全員に共通の新しい名前は 1 個）

なし

### 内容の類似度が低いファイル

#### `kit/.forge/templates/prompts/builder.md`（agent-1 と agent-3、類似度 0.885）

```diff
--- agent-1/kit/.forge/templates/prompts/builder.md
+++ agent-3/kit/.forge/templates/prompts/builder.md
@@ -12,11 +12,11 @@
 4. リポジトリ `${repo}`: `CLAUDE.md`、`AGENTS.md`、`README.md`、検査のコマンド、ディレクトリ構造。スキルとサブエージェントの手順を、このリポジトリの決まりとコマンドに合わせるために読む。`.forge/` と `.claude/skills/forge-*` と `.claude/agents/forge-*` は読まない
 5. 骨組み: `${draft_dir}`
 
-## 検査コマンド
+## charter で決めた検査コマンド
 
-charter の検査コマンド: `${check_command}`
+`${check_command}`
 
-上が `—` なら、charter で検査コマンドは決まっていません。そのときは、読むもの4でリポジトリの文書に書かれている検査のコマンドだけを使い、書かれていないコマンドを推測して手順に書きません。そうでなければ、スキルとサブエージェントの手順で検査を回す所に、このコマンドをそのまま書きます。このコマンドはリポジトリのルートで実行します。リポジトリの文書に別の検査のコマンドがあっても、このコマンドを使います。
+上が `—` なら、charter で検査コマンドは決まっていません。そのときは、4 で読んだリポジトリの文書に書かれた検査のコマンドだけを手順に書き、文書に無いコマンドを推測で書きません。そうでなければ、変更を確かめる手順（SKILL.md とサブエージェントの本文）には、上のコマンドをリポジトリのルートで実行すると、コマンドを変えずに書きます。
 
 ## 人から直してほしいと言われたこと
 
```

#### `tests/test_building.py`（agent-1 と agent-3、類似度 0.906）

```diff
--- agent-1/tests/test_building.py
+++ agent-3/tests/test_building.py
@@ -65,17 +65,16 @@
 
     def test_check_command(self) -> None:
         building.build(self.where, "")
-        self.assertIn("charter の検査コマンド: `python3 check.py`", fsops.read_text(self.where.builder_prompt_path))
+        self.assertIn("\n`python3 check.py`\n", fsops.read_text(self.where.builder_prompt_path))
         data = support.orch_charter(support.NEW_SKILL)
-        goals, metrics, environment = data["goals"], data["metrics"], data["environment"]
-        assert isinstance(goals, list) and isinstance(metrics, list) and isinstance(environment, dict)
-        goals[0]["metrics"].remove("check_pass")
-        data["metrics"] = [choice for choice in metrics if choice["id"] != "check_pass"]
+        environment = data["environment"]
+        assert isinstance(environment, dict)
         environment["check_command"] = ""
+        data["goals"] = [{"id": "G1", "statement": "依頼を満たす", "metrics": ["acceptance"]}]
+        data["metrics"] = [{"id": "acceptance", "threshold": 1.0, "priority": "must"}]
         support.approve(self.where, data)
         building.build(self.where, "")
-        prompt = fsops.read_text(self.where.builder_prompt_path)
-        self.assertIn(f"charter の検査コマンド: `{render.MISSING}`", prompt)
+        self.assertIn(f"\n`{render.MISSING}`\n", fsops.read_text(self.where.builder_prompt_path))
 
 
 if __name__ == "__main__":
```

#### `kit/.forge/forge_kit/building.py`（agent-1 と agent-3、類似度 0.988）

```diff
--- agent-1/kit/.forge/forge_kit/building.py
+++ agent-3/kit/.forge/forge_kit/building.py
@@ -62,6 +62,7 @@
     for path in (where.bundle_check_path, where.bundle_check_md_path):
         fsops.remove_tree(path)
     fsops.write_text(where.visible_charter_path, views.render_charter(model, "approved", include_holdout=False))
+    check_command = model.environment.check_command
     values = {
         "skill_name": model.target.skill_name,
         "repo": str(where.root),
@@ -69,7 +70,7 @@
         "design_md": str(where.design_md_path),
         "rules_md": str(where.bundle_rules_path),
         "draft_dir": str(where.draft_dir),
-        "check_command": model.environment.check_command or render.MISSING,
+        "check_command": check_command if check_command.strip() else render.MISSING,
         "feedback": feedback or render.MISSING,
     }
     fsops.write_text(where.builder_prompt_path, prompts.render("builder", values))
```


## T3-cross

### 一部のエージェントだけが作った・変えたファイル

なし（全員が同じファイルの集合を変えた）

### 一部のエージェントだけが作った名前（全員に共通の新しい名前は 2 個）

なし

### 内容の類似度が低いファイル

#### `tests/test_designing.py`（agent-1 と agent-3、類似度 0.778）

```diff
--- agent-1/tests/test_designing.py
+++ agent-3/tests/test_designing.py
@@ -37,6 +37,19 @@
         model, _sha = workspace.approved_charter(self.where)
         self.assertEqual(workspace.build_progress(self.where, model).design_state, "approved")
 
+    def test_note(self) -> None:
+        designing.design_new(self.where, "")
+        support.act_designer(self.where)
+        designing.design_check(self.where)
+        designing.design_approve(self.where, "", support.TODAY)
+        approval = workspace.load_design_approval(self.where)
+        self.assertEqual(approval.note if approval else None, "")
+        fsops.write_text(self.where.builder_prompt_path, "前の構築役のプロンプト\n")
+        designing.design_approve(self.where, "検査コマンドは make check だけを使って", support.TODAY)
+        approval = workspace.load_design_approval(self.where)
+        self.assertEqual(approval.note if approval else None, "検査コマンドは make check だけを使って")
+        self.assertFalse(self.where.builder_prompt_path.exists())
+
     def test_feedback(self) -> None:
         designing.design_new(self.where, "")
         support.act_designer(self.where)
@@ -48,19 +61,6 @@
         self.assertIn("レビュー役を2人にして", fsops.read_text(self.where.designer_prompt_path))
         self.assertFalse(self.where.design_approval_path.exists())
 
-    def test_note(self) -> None:
-        designing.design_new(self.where, "")
-        support.act_designer(self.where)
-        designing.design_check(self.where)
-        designing.design_approve(self.where, "", support.TODAY)
-        approval = workspace.load_design_approval(self.where)
-        self.assertEqual(approval.note if approval else None, "")
-        fsops.write_text(self.where.builder_prompt_path, "前の承認のときの構築役のプロンプト\n")
-        designing.design_approve(self.where, "既存の検査コマンドを使わせて", support.TODAY)
-        approval = workspace.load_design_approval(self.where)
-        self.assertEqual(approval.note if approval else None, "既存の検査コマンドを使わせて")
-        self.assertFalse(self.where.builder_prompt_path.exists())
-
 
 if __name__ == "__main__":
     unittest.main()
```

#### `tests/test_building.py`（agent-2 と agent-3、類似度 0.848）

```diff
--- agent-2/tests/test_building.py
+++ agent-3/tests/test_building.py
@@ -4,7 +4,7 @@
 
 import unittest
 
-from forge_kit import building, bundle, designing, fsops, layout, workspace
+from forge_kit import building, bundle, designing, fsops, layout, render, workspace
 from forge_kit.errors import InvalidFileError, StageError
 from tests import support
 
@@ -58,20 +58,22 @@
         with self.assertRaises(StageError):
             building.install(self.where, support.TODAY)
 
+    def test_note(self) -> None:
+        building.build(self.where, "")
+        self.assertIn(
+            f"## 設計を承認した人からのメモ\n\n{render.MISSING}\n", fsops.read_text(self.where.builder_prompt_path)
+        )
+        designing.design_approve(self.where, "サブエージェントの返答は1行にして", support.TODAY)
+        building.build(self.where, "")
+        self.assertIn("サブエージェントの返答は1行にして", fsops.read_text(self.where.builder_prompt_path))
+        building.build(self.where, "報告に費用を足して")
+        self.assertIn("サブエージェントの返答は1行にして", fsops.read_text(self.where.builder_prompt_path))
+
     def test_feedback(self) -> None:
         building.build(self.where, "報告に費用を足して")
         self.assertIn("報告に費用を足して", fsops.read_text(self.where.builder_prompt_path))
         self.assertTrue((self.where.draft_dir / layout.SKILLS_DIR / support.NEW_SKILL).is_dir())
 
-    def test_note(self) -> None:
-        building.build(self.where, "")
-        self.assertNotIn("既存のテストの書き方に合わせて", fsops.read_text(self.where.builder_prompt_path))
-        designing.design_approve(self.where, "既存のテストの書き方に合わせて", support.TODAY)
-        building.build(self.where, "")
-        self.assertIn("既存のテストの書き方に合わせて", fsops.read_text(self.where.builder_prompt_path))
-        building.build(self.where, "報告に費用を足して")
-        self.assertIn("既存のテストの書き方に合わせて", fsops.read_text(self.where.builder_prompt_path))
-
 
 if __name__ == "__main__":
     unittest.main()
```

#### `tests/test_contracts.py`（agent-2 と agent-3、類似度 0.880）

```diff
--- agent-2/tests/test_contracts.py
+++ agent-3/tests/test_contracts.py
@@ -29,10 +29,11 @@
             contracts.parse_proposal({"changes": [change], "observations": []}, "p", metric_ids=("acceptance",))
 
     def test_parse_design_approval(self) -> None:
-        data = {"sha256": "0" * 64, "approved_on": "2026-10-20", "note": "既存のテストの書き方に合わせて"}
-        self.assertEqual(contracts.parse_design_approval(data, "a").note, "既存のテストの書き方に合わせて")
-        old = {"sha256": "0" * 64, "approved_on": "2026-10-20"}
-        self.assertEqual(contracts.parse_design_approval(old, "a").note, "")
+        approval = contracts.DesignApproval("0" * 64, "2026-01-01", "返答は1行にして")
+        data = json.loads(json.dumps(contracts.to_data(approval)))
+        self.assertEqual(contracts.parse_design_approval(data, "design-approval.json"), approval)
+        old = {"sha256": "0" * 64, "approved_on": "2026-01-01"}
+        self.assertEqual(contracts.parse_design_approval(old, "design-approval.json").note, "")
 
     def test_parse_plan(self) -> None:
         run = contracts.Run("T1-a1", "T1", 1)
```

#### `kit/.forge/templates/prompts/builder.md`（agent-1 と agent-3、類似度 0.923）

```diff
--- agent-1/kit/.forge/templates/prompts/builder.md
+++ agent-3/kit/.forge/templates/prompts/builder.md
@@ -12,11 +12,11 @@
 4. リポジトリ `${repo}`: `CLAUDE.md`、`AGENTS.md`、`README.md`、検査のコマンド、ディレクトリ構造。スキルとサブエージェントの手順を、このリポジトリの決まりとコマンドに合わせるために読む。`.forge/` と `.claude/skills/forge-*` と `.claude/agents/forge-*` は読まない
 5. 骨組み: `${draft_dir}`
 
-## 設計を承認した人から気をつけてほしいと言われたこと
+## 設計を承認した人からのメモ
 
 ${note}
 
-上が `—` なら、言われたことはありません。そうでなければ、下書きのどのファイルを書くときも、このことに気をつけます。直してほしいと言われたことがあって書き直すときも同じです。設計の役・手順と、バンドルの決まりは、このことがあっても変えません。
+上が `—` なら、メモはありません。そうでなければ、設計を承認した人が構築で気をつけてほしいと残したことです。初めての構築でも直すときでも、下書きの全体をメモに沿って書きます。メモが設計やバンドルの決まりと食い違う所は、設計と決まりに従います。
 
 ## 人から直してほしいと言われたこと
 
```

#### `tests/test_cli.py`（agent-1 と agent-3、類似度 0.949）

```diff
--- agent-1/tests/test_cli.py
+++ agent-3/tests/test_cli.py
@@ -32,11 +32,15 @@
         self.assert_status(
             where, "直すなら: python3 .forge/forge.py design-new --target new-orch --feedback '<直してほしいこと>'"
         )
-        self.assert_status(where, "design-approve --target new-orch --note '<構築役に気をつけてほしいこと>'")
-        self.cli(where, "design-approve", *target, "--note", "既存の検査コマンドを使わせて")
+        self.assert_status(
+            where,
+            "承認なら: python3 .forge/forge.py design-approve --target new-orch"
+            " --note '<構築役に気をつけてほしいこと>'",
+        )
+        self.cli(where, "design-approve", *target, "--note", "報告は日本語で書いて")
         self.assert_status(where, "build --target new-orch")
         self.cli(where, "build", *target)
-        self.assertIn("既存の検査コマンドを使わせて", fsops.read_text(where.builder_prompt_path))
+        self.assertIn("報告は日本語で書いて", fsops.read_text(where.builder_prompt_path))
         self.assert_status(where, "job forge-builder build")
         code, _out, err = support.run_cli(where.root, "bundle-check", *target)
         self.assertEqual(code, 1)
```
