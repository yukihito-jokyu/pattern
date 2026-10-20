# 収束テスト ラウンド 1 のレポート

このファイルは convergence.py diff が生成する。揺れの分類（R1〜R7）と対処は convergence-report.md に書く。

基準: files ≥ 1.0、names ≥ 0.8、content ≥ 0.0、check は全員通過、保護ファイルの変更なし

## 指標

| 課題 | files | names | content | check | 保護 | 基準 |
|---|---|---|---|---|---|---|
| T1-add | 0.714 | 0.167 | 0.948 | 全員通過 | — | 満たさない |
| T2-change | 1.000 | 1.000 | 0.934 | 全員通過 | — | 満たす |
| T3-cross | 0.897 | 0.372 | 0.944 | 全員通過 | — | 満たさない |

## T1-add

### 一部のエージェントだけが作った・変えたファイル

| ファイル | agent-1 | agent-2 | agent-3 |
|---|---|---|---|
| `kit/.forge/forge_kit/contracts.py` | – | – | ✓ |
| `kit/.forge/forge_kit/trace.py` | – | – | ✓ |
| `tests/test_trace.py` | – | – | ✓ |

### 一部のエージェントだけが作った名前（全員に共通の新しい名前は 0 個）

- agent-1: `test_denials`
- agent-2: `test_permission_denials`
- agent-3: `_optional_texts`, `test_denials`

### 内容の類似度が低いファイル

#### `tests/test_score.py`（agent-2 と agent-3、類似度 0.827）

```diff
--- agent-2/tests/test_score.py
+++ agent-3/tests/test_score.py
@@ -24,17 +24,19 @@
         self.assertEqual({item.id: item.value for item in scores.metrics}["delegation"], 0.0)
         self.assertFalse(scores.all_must_met)
 
-    def test_permission_denials(self) -> None:
+    def test_denials(self) -> None:
         data = support.orch_charter()
-        goals, chosen = data["goals"], data["metrics"]
-        assert isinstance(goals, list) and isinstance(chosen, list)
-        data["goals"] = [*goals, {"id": "G5", "statement": "拒まれる操作をしない", "metrics": ["permission_denials"]}]
-        data["metrics"] = [*chosen, {"id": "permission_denials", "threshold": 0.0, "priority": "should"}]
-        for stream, value, met in (("main-edit", 1.0, False), ("delegated", 0.0, True)):
+        goals, choices = data["goals"], data["metrics"]
+        assert isinstance(goals, list) and isinstance(choices, list)
+        goals.append({"id": "G5", "statement": "評価の環境で拒否される操作に頼らない", "metrics": ["denials"]})
+        choices.append({"id": "denials", "threshold": 0.0, "priority": "should"})
+        found: dict[str, tuple[float | None, bool]] = {}
+        for stream in ("main-edit", "delegated", "unfinished"):
             where = support.approved_layout(self, data)
             scores = support.scored_slot(where, layout.make_slot("baseline", 1), stream=stream)
-            found = next(item for item in scores.metrics if item.id == "permission_denials")
-            self.assertEqual((found.value, found.met), (value, met))
+            item = next(item for item in scores.metrics if item.id == "denials")
+            found[stream] = (item.value, item.met)
+        self.assertEqual(found, {"main-edit": (1.0, False), "delegated": (0.0, True), "unfinished": (None, False)})
 
     def test_holdout_is_separate(self) -> None:
         where = support.approved_layout(self, support.orch_charter())
```

#### `kit/claude/skills/forge-goals/references/metric-catalog.md`（agent-1 と agent-2、類似度 0.965）

```diff
--- agent-1/kit/claude/skills/forge-goals/references/metric-catalog.md
+++ agent-2/kit/claude/skills/forge-goals/references/metric-catalog.md
@@ -3,7 +3,7 @@
 # 指標の一覧
 
 charter の `metrics` に書ける指標である。`machine` は補助 CLI が実行の記録と差分から機械で数え、`grader` は採点役が判定する。
-値は 0〜1 の割合（量の指標 `cost_usd`、`duration_sec`、`launches`、`denials` を除く）で、課題ごとに求めてから平均する。
+値は 0〜1 の割合（量の指標 `cost_usd`、`duration_sec`、`launches`、`permission_denials` を除く）で、課題ごとに求めてから平均する。
 
 ## `check_pass` 検査の通過率（推奨）
 
@@ -126,12 +126,12 @@
 | 既定の閾値 | 10.000 |
 | 前提 | — |
 
-## `denials` 権限で拒まれた操作の回数
+## `permission_denials` 権限で拒まれた操作の回数
 
 | 項目 | 内容 |
 |---|---|
-| 分かること | 実行役が許されていない操作を試みて拒まれる回数（多いほど、スキルの手順が評価の環境に合っていない） |
-| 求め方 | 実行の記録の result の permission_denials の件数を、実行ごとに平均する。result の無い実行は0件と数える |
+| 分かること | スキルの手順が、評価の環境で許されていない操作に頼っていないか（拒まれるほど、手順が環境に合っていない） |
+| 求め方 | 実行の記録の result の permission_denials の件数を、実行ごとに平均する |
 | 測り方 | machine |
 | 向き | 低いほど良い |
 | 既定の閾値 | 10.000 |
```

#### `kit/.forge/forge_kit/catalog.py`（agent-2 と agent-3、類似度 0.979）

```diff
--- agent-2/kit/.forge/forge_kit/catalog.py
+++ agent-3/kit/.forge/forge_kit/catalog.py
@@ -163,15 +163,15 @@
         requires="",
     ),
     Metric(
-        id="permission_denials",
-        name="権限で拒まれた操作の回数",
+        id="denials",
+        name="権限で拒否された操作の回数",
         method="machine",
         direction="lower",
         default_threshold=10.0,
         max_value=None,
         recommended=False,
-        tells="スキルの手順が、評価の環境で許されていない操作に頼っていないか（拒まれるほど、手順が環境に合っていない）",
-        computes="実行の記録の result の permission_denials の件数を、実行ごとに平均する",
+        tells="1つの依頼で、実行役が権限で拒否された操作が何回あるか（多いほど、スキルの手順が評価の環境に合っていない）",
+        computes="実行の記録の result の permission_denials の件数を、実行ごとに平均する。result の無い実行は数えない",
         requires="",
     ),
 )
```

#### `kit/.forge/forge_kit/score.py`（agent-1 と agent-3、類似度 0.983）

```diff
--- agent-1/kit/.forge/forge_kit/score.py
+++ agent-3/kit/.forge/forge_kit/score.py
@@ -42,6 +42,11 @@
     return metrics.mean([value for value in values if value is not None])
 
 
+def _denials(runs: Sequence[RunData]) -> float | None:
+    """権限で拒否された操作の件数を実行ごとに平均する。result の無い実行は件数が分からないので数えない。"""
+    return _known([None if run.facts.denials is None else float(len(run.facts.denials)) for run in runs])
+
+
 Calculator = Callable[[Sequence[RunData]], "float | None"]
 # カタログの指標ごとの、1つの課題での値の求め方。指標を足したら、ここと catalog.METRICS を一緒に変える
 CALCULATORS: dict[str, Calculator] = {
@@ -56,7 +61,7 @@
     "cost_usd": lambda runs: _known([run.facts.cost_usd for run in runs]),
     "duration_sec": lambda runs: _known([run.facts.duration_sec for run in runs]),
     "launches": lambda runs: metrics.mean([float(len(run.facts.launches)) for run in runs]),
-    "denials": lambda runs: metrics.mean([float(len(run.facts.denials)) for run in runs]),
+    "denials": _denials,
 }
 
 
```


## T2-change

### 一部のエージェントだけが作った・変えたファイル

なし（全員が同じファイルの集合を変えた）

### 一部のエージェントだけが作った名前（全員に共通の新しい名前は 1 個）

なし

### 内容の類似度が低いファイル

#### `tests/test_building.py`（agent-2 と agent-3、類似度 0.797）

```diff
--- agent-2/tests/test_building.py
+++ agent-3/tests/test_building.py
@@ -58,27 +58,26 @@
         with self.assertRaises(StageError):
             building.install(self.where, support.TODAY)
 
-    def test_check_command(self) -> None:
-        building.build(self.where, "")
-        prompt = fsops.read_text(self.where.builder_prompt_path)
-        self.assertIn("charter で決めた検査コマンド: `python3 check.py`", prompt)
-        data = support.orch_charter(support.NEW_SKILL)
-        environment = data["environment"]
-        assert isinstance(environment, dict)
-        environment["check_command"] = ""
-        data["goals"] = [{"id": "G1", "statement": "依頼を満たす", "metrics": ["completion"]}]
-        data["metrics"] = [{"id": "completion", "threshold": 1.0, "priority": "must"}]
-        support.approve(self.where, data)
-        building.build(self.where, "")
-        prompt = fsops.read_text(self.where.builder_prompt_path)
-        self.assertIn(f"charter で決めた検査コマンド: `{render.MISSING}`", prompt)
-        self.assertNotIn("python3 check.py", prompt)
-
     def test_feedback(self) -> None:
         building.build(self.where, "報告に費用を足して")
         self.assertIn("報告に費用を足して", fsops.read_text(self.where.builder_prompt_path))
         self.assertTrue((self.where.draft_dir / layout.SKILLS_DIR / support.NEW_SKILL).is_dir())
 
+    def test_check_command(self) -> None:
+        building.build(self.where, "")
+        self.assertIn("\n`python3 check.py`\n", fsops.read_text(self.where.builder_prompt_path))
+        data = support.orch_charter(support.NEW_SKILL)
+        data["goals"] = [{"id": "G1", "statement": "依頼を満たす", "metrics": ["completion"]}]
+        data["metrics"] = [{"id": "completion", "threshold": 1.0, "priority": "must"}]
+        environment = data["environment"]
+        assert isinstance(environment, dict)
+        environment["check_command"] = ""
+        support.approve(self.where, data)
+        building.build(self.where, "")
+        prompt = fsops.read_text(self.where.builder_prompt_path)
+        self.assertIn(f"\n`{render.MISSING}`\n", prompt)
+        self.assertNotIn("python3 check.py", prompt)
+
 
 if __name__ == "__main__":
     unittest.main()
```

#### `kit/.forge/templates/prompts/builder.md`（agent-1 と agent-3、類似度 0.852）

```diff
--- agent-1/kit/.forge/templates/prompts/builder.md
+++ agent-3/kit/.forge/templates/prompts/builder.md
@@ -9,15 +9,16 @@
 1. ゴール・指標・評価課題: `${charter_md}`。スキルが何で測られるかを知るために読む
 2. 承認された設計: `${design_md}`。役・手順・人に確かめる場面・報告の項目は、この設計のとおりにする
 3. バンドルの決まり: `${rules_md}`。下書きは全部の決まりを満たす（満たさないと検査で落ちる）
-4. リポジトリ `${repo}`: `CLAUDE.md`、`AGENTS.md`、`README.md`、検査のコマンド、ディレクトリ構造。スキルとサブエージェントの手順を、このリポジトリの決まりとコマンドに合わせるために読む。`.forge/` と `.claude/skills/forge-*` と `.claude/agents/forge-*` は読まない
+4. リポジトリ `${repo}`: `CLAUDE.md`、`AGENTS.md`、`README.md`、ディレクトリ構造。スキルとサブエージェントの手順を、このリポジトリの決まりとコマンドに合わせるために読む。`.forge/` と `.claude/skills/forge-*` と `.claude/agents/forge-*` は読まない
 5. 骨組み: `${draft_dir}`
 
 ## 検査コマンド
 
-charter で決めた検査コマンド: `${check_command}`
+`${check_command}`
 
-- 上が `—` でなければ、検査を回す手順（サブエージェントに渡すプロンプトを含む）に、このコマンドをそのまま書く。リポジトリの文書に別のコマンドがあっても、charter のコマンドを使う
-- 上が `—` なら、charter で検査コマンドは決まっていない。検査を回す手順には、読むものの4でリポジトリから見つけた検査のコマンドだけを書く。見つからなければ、コマンドを推測で作らず、手順に検査のコマンドを書かない
+charter で決めた、リポジトリ `${repo}` の検査コマンドです。スキルとサブエージェントの手順で検査を回す所には、このコマンドを言い換えずにそのまま書きます。
+
+上が `—` なら、charter で検査コマンドは決まっていません。そのときは、リポジトリの `CLAUDE.md`、`AGENTS.md`、`README.md`、`Makefile`、`package.json` の scripts に書かれた検査のコマンドを使います。どこにも書かれていなければ、コマンドを推測して書きません。
 
 ## 人から直してほしいと言われたこと
 
```


## T3-cross

### 一部のエージェントだけが作った・変えたファイル

| ファイル | agent-1 | agent-2 | agent-3 |
|---|---|---|---|
| `docs/design/architecture.md` | ✓ | – | – |
| `tests/test_contracts.py` | – | ✓ | ✓ |

### 一部のエージェントだけが作った名前（全員に共通の新しい名前は 1 個）

- agent-1: `approval_note`, `test_approval_note`
- agent-2: `before_note`, `test_parse_design_approval`
- agent-3: `test_parse_design_approval`

### 内容の類似度が低いファイル

#### `tests/test_designing.py`（agent-1 と agent-2、類似度 0.762）

```diff
--- agent-1/tests/test_designing.py
+++ agent-2/tests/test_designing.py
@@ -33,34 +33,31 @@
             designing.design_check(self.where)
         support.act_designer(self.where)
         self.assertIn("役 2、手順 4、人の関所 1", designing.design_check(self.where))
-        designing.design_approve(self.where, "", support.TODAY)
+        designing.design_approve(self.where, support.TODAY, "")
         model, _sha = workspace.approved_charter(self.where)
         self.assertEqual(workspace.build_progress(self.where, model).design_state, "approved")
-
-    def test_note(self) -> None:
-        designing.design_new(self.where, "")
-        support.act_designer(self.where)
-        designing.design_check(self.where)
-        designing.design_approve(self.where, "", support.TODAY)
-        approval = workspace.load_design_approval(self.where)
-        self.assertEqual(approval.note if approval else None, "")
-        fsops.write_text(self.where.builder_prompt_path, "前の承認で書いた構築役のプロンプト\n")
-        designing.design_approve(self.where, " 既存の関数名に合わせて ", support.TODAY)
-        approval = workspace.load_design_approval(self.where)
-        self.assertEqual(approval.note if approval else None, "既存の関数名に合わせて")
-        self.assertFalse(self.where.builder_prompt_path.exists())
 
     def test_feedback(self) -> None:
         designing.design_new(self.where, "")
         support.act_designer(self.where)
         designing.design_check(self.where)
-        designing.design_approve(self.where, "", support.TODAY)
+        designing.design_approve(self.where, support.TODAY, "")
         with self.assertRaises(StageError):
             designing.design_new(self.where, "")
         designing.design_new(self.where, "レビュー役を2人にして")
         self.assertIn("レビュー役を2人にして", fsops.read_text(self.where.designer_prompt_path))
         self.assertFalse(self.where.design_approval_path.exists())
 
+    def test_note(self) -> None:
+        designing.design_new(self.where, "")
+        support.act_designer(self.where)
+        designing.design_check(self.where)
+        fsops.write_text(self.where.builder_prompt_path, "前の承認で書いたプロンプト\n")
+        designing.design_approve(self.where, support.TODAY, " 検査は make check で回して\n")
+        approval = workspace.load_design_approval(self.where)
+        self.assertEqual(approval.note if approval else None, "検査は make check で回して")
+        self.assertFalse(self.where.builder_prompt_path.exists())
+
 
 if __name__ == "__main__":
     unittest.main()
```

#### `tests/test_building.py`（agent-1 と agent-3、類似度 0.870）

```diff
--- agent-1/tests/test_building.py
+++ agent-3/tests/test_building.py
@@ -63,14 +63,15 @@
         self.assertIn("報告に費用を足して", fsops.read_text(self.where.builder_prompt_path))
         self.assertTrue((self.where.draft_dir / layout.SKILLS_DIR / support.NEW_SKILL).is_dir())
 
-    def test_approval_note(self) -> None:
-        building.build(self.where, "報告に費用を足して")
-        self.assertIn(f"\n{render.MISSING}\n", fsops.read_text(self.where.builder_prompt_path))
-        designing.design_approve(self.where, "既存の関数名に合わせて", support.TODAY)
-        building.build(self.where, "報告に費用を足して")
-        prompt = fsops.read_text(self.where.builder_prompt_path)
-        self.assertIn("\n既存の関数名に合わせて\n", prompt)
-        self.assertNotIn(f"\n{render.MISSING}\n", prompt)
+    def test_note(self) -> None:
+        building.build(self.where, "")
+        self.assertIn(
+            f"## 設計を承認した人からのメモ\n\n{render.MISSING}\n", fsops.read_text(self.where.builder_prompt_path)
+        )
+        designing.design_approve(self.where, "検査は make check で回して", support.TODAY)
+        for feedback in ("", "報告に費用を足して"):
+            building.build(self.where, feedback)
+            self.assertIn("検査は make check で回して", fsops.read_text(self.where.builder_prompt_path))
 
 
 if __name__ == "__main__":
```

#### `tests/test_contracts.py`（agent-2 と agent-3、類似度 0.895）

```diff
--- agent-2/tests/test_contracts.py
+++ agent-3/tests/test_contracts.py
@@ -29,10 +29,12 @@
             contracts.parse_proposal({"changes": [change], "observations": []}, "p", metric_ids=("acceptance",))
 
     def test_parse_design_approval(self) -> None:
-        before_note = {"sha256": "0" * 64, "approved_on": "2026-10-20"}
-        self.assertEqual(contracts.parse_design_approval(before_note, "design-approval.json").note, "")
+        data = {"sha256": "0" * 64, "approved_on": "2026-01-02"}
+        self.assertEqual(contracts.parse_design_approval(data, "a").note, "")
+        approval = contracts.parse_design_approval({**data, "note": "検査を回して"}, "a")
+        self.assertEqual(approval.note, "検査を回して")
         with self.assertRaises(InvalidFileError):
-            contracts.parse_design_approval({**before_note, "note": 1}, "design-approval.json")
+            contracts.parse_design_approval({**data, "note": 1}, "a")
 
     def test_plan_round_trip(self) -> None:
         run = contracts.Run("T1-a1", "T1", 1)
```

#### `kit/.forge/templates/prompts/builder.md`（agent-1 と agent-2、類似度 0.885）

```diff
--- agent-1/kit/.forge/templates/prompts/builder.md
+++ agent-2/kit/.forge/templates/prompts/builder.md
@@ -12,11 +12,11 @@
 4. リポジトリ `${repo}`: `CLAUDE.md`、`AGENTS.md`、`README.md`、検査のコマンド、ディレクトリ構造。スキルとサブエージェントの手順を、このリポジトリの決まりとコマンドに合わせるために読む。`.forge/` と `.claude/skills/forge-*` と `.claude/agents/forge-*` は読まない
 5. 骨組み: `${draft_dir}`
 
-## 設計を承認した人から構築役へのメモ
+## 設計を承認した人からのメモ
 
-${approval_note}
+${note}
 
-上が `—` なら、メモはありません。そうでなければ、下書きを書くときも直すときも、メモに書かれたことに気をつけます。メモが設計かバンドルの決まりと食い違うときは、設計と決まりに従います。
+上が `—` なら、メモはありません。そうでなければ、下書きを書くときにこのメモに必ず従います。役・手順・人に確かめる場面・報告の項目は設計のとおりにしたまま、その範囲でメモに従います。
 
 ## 人から直してほしいと言われたこと
 
```

#### `kit/claude/skills/forge-build/SKILL.md`（agent-1 と agent-2、類似度 0.919）

```diff
--- agent-1/kit/claude/skills/forge-build/SKILL.md
+++ agent-2/kit/claude/skills/forge-build/SKILL.md
@@ -15,8 +15,8 @@
 
 作業は2段に分かれ、各段の最後に人が確かめる。
 
-1. **設計**：設計役が、役・手順・人に確かめる場面・報告の項目を design.json に書く。補助 CLI が形を検査し、人が承認する
-2. **構築**：補助 CLI が設計から骨組みを書き、構築役が骨組みを埋めて下書きにする。補助 CLI がバンドルの決まり（[references/bundle-rules.md](references/bundle-rules.md)）で検査し、人が承認すると、下書きをリポジトリの `.claude/` に入れる
+1. **設計**：設計役が、役・手順・人に確かめる場面・報告の項目を design.json に書く。補助 CLI が形を検査し、人が承認する。人は承認のときに、構築役に気をつけてほしいことを一言メモとして添えられる（添えなくてもよい）
+2. **構築**：補助 CLI が設計から骨組みを書き、構築役が骨組みを埋めて下書きにする。承認のときのメモは、補助 CLI が構築役のプロンプトに毎回入れる。補助 CLI がバンドルの決まり（[references/bundle-rules.md](references/bundle-rules.md)）で検査し、人が承認すると、下書きをリポジトリの `.claude/` に入れる
 
 どの段階にいて次に何をするかは、補助 CLI の `status` が決める。あなたは `status` の指示に従って、コマンドを実行するか、サブエージェントを起動するか、人に聞く。段階を自分で判断して飛ばさない。
 
@@ -63,10 +63,7 @@
 
 ## 人に確かめること
 
-- 設計の確認：`design.md` の役・手順・人に確かめる場面・報告を見せ、AskUserQuestion で「承認する（推奨）／構築役へのメモを添えて承認する／直したい」を聞く。既定: 人が答えられないときは、承認せずに止まる
-  - 承認するなら、`承認なら:` のコマンドの `<構築役へのメモ>` を空にして（`--note ''`）実行する
-  - メモを添えて承認するなら、構築役に気をつけてほしいことを一言で書いてもらうよう文章で聞き、返ってきた文をそのまま `承認なら:` のコマンドの `<構築役へのメモ>` に入れて実行する（文の中の `'` は `’` に置き換える）。メモは補助 CLI が構築役のプロンプトに入れる
-  - 直したいなら、直してほしいことを文章で聞き、返ってきた文をそのまま `直すなら:` のコマンドの `<直してほしいこと>` に入れて実行する（文の中の `'` は `’` に置き換える）
+- 設計の確認：`design.md` の役・手順・人に確かめる場面・報告を見せ、AskUserQuestion で「承認する（推奨）／メモを添えて承認する／直したい」を聞く。承認するなら、`承認なら:` のコマンドの `<構築役へのメモ>` を空にして（`--note ''`）実行する。メモを添えて承認するなら、構築役に気をつけてほしいことを文章で聞き、返ってきた文をそのまま `<構築役へのメモ>` に入れて実行する（文の中の `'` は `’` に置き換える）。直したいなら、直してほしいことを文章で聞き、返ってきた文をそのまま `直すなら:` のコマンドの `<直してほしいこと>` に入れて実行する（文の中の `'` は `’` に置き換える）。既定: 人が答えられないときは、承認せずに止まる
 - 下書きの確認：`bundle-check.md` のファイル・サブエージェント・手順の一覧と、下書きの SKILL.md の全文を見せ、AskUserQuestion で「入れる（推奨）／直したい」を聞く。入れるなら `承認なら:` のコマンドを実行する。直したいなら、設計の確認と同じく文章で聞き、`直すなら:` のコマンドに入れて実行する。既定: 人が答えられないときは、入れずに止まる
 - `WARN` の行と、上の表に無いエラー：内容を人に見せ、判断を仰ぐ。既定: 人が答えられないときは止まる
 
@@ -82,6 +79,7 @@
 ## してはいけないこと
 
 - 設計と下書きを、自分で書いたり直したりすること。直すのは設計役と構築役で、人の言葉は `--feedback` と `--note` で渡す
+- 構築役へのメモを、自分で書いたり言い換えたりすること。メモは人が書いた文だけにする
 - 人の答えを待たずに `design-approve` や `install` を実行すること
 - `.claude/` に、自分でファイルを写すこと。入れるのは `install` だけである
 - charter を書き換えること。charter を変えるときは `/forge-goals` に戻る
```
