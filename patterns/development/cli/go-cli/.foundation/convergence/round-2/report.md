# 収束テスト ラウンド 2 のレポート

このファイルは convergence.py diff が生成する。揺れの分類（R1〜R7）と対処は convergence-report.md に書く。

基準: files ≥ 1.0、names ≥ 0.8、content ≥ 0.0、check は全員通過、保護ファイルの変更なし

## 指標

| 課題 | files | names | content | check | 保護 | 基準 |
|---|---|---|---|---|---|---|
| T1-add | 1.000 | 1.000 | 1.000 | 全員通過 | — | 満たす |
| T2-change | 1.000 | 0.867 | 0.996 | 全員通過 | — | 満たす |
| T3-cross | 1.000 | 1.000 | 1.000 | 全員通過 | — | 満たす |

## T1-add

### 一部のエージェントだけが作った・変えたファイル

なし（全員が同じファイルの集合を変えた）

### 一部のエージェントだけが作った名前（全員に共通の新しい名前は 5 個）

なし

### 内容の類似度が低いファイル

なし（共通して変えたファイルの中身は全員一致）

## T2-change

### 一部のエージェントだけが作った・変えたファイル

なし（全員が同じファイルの集合を変えた）

### 一部のエージェントだけが作った名前（全員に共通の新しい名前は 4 個）

- agent-3: `Set`

### 内容の類似度が低いファイル

#### `docs/cli.md`（agent-1 と agent-3、類似度 0.971）

```diff
--- agent-1/docs/cli.md
+++ agent-3/docs/cli.md
@@ -12,7 +12,7 @@
 
 | Flag | Description |
 |---|---|
-| `--due <string>` | Due date in YYYY-MM-DD format |
+| `--due <string>` | Set the due date in YYYY-MM-DD format |
 | `--json` | Write the output as JSON |
 
 ## go-cli task complete
```

#### `internal/command/taskcmd/add.go`（agent-1 と agent-3、類似度 0.980）

```diff
--- agent-1/internal/command/taskcmd/add.go
+++ agent-3/internal/command/taskcmd/add.go
@@ -29,7 +29,7 @@
 		Summary: "Add a task",
 		Args:    []cli.Arg{{Name: "title", Value: &opts.title}},
 		Flags: func(fs *flag.FlagSet) {
-			fs.StringVar(&opts.due, "due", "", "Due date in YYYY-MM-DD format")
+			fs.StringVar(&opts.due, "due", "", "Set the due date in YYYY-MM-DD format")
 		},
 		Run: func(ctx context.Context) (cli.Output, error) {
 			return runAdd(ctx, svc, opts)
```

#### `internal/adapter/taskstore/taskstore_test.go`（agent-1 と agent-2、類似度 0.987）

```diff
--- agent-1/internal/adapter/taskstore/taskstore_test.go
+++ agent-2/internal/adapter/taskstore/taskstore_test.go
@@ -28,7 +28,8 @@
 		{
 			name: "reads_tasks",
 			content: `{"version": 1, "tasks": [` +
-				`{"id": 1, "title": "Buy milk", "done": true, "due": "2026-01-31T00:00:00Z", "created_at": "2026-01-02T03:04:05Z"}]}`,
+				`{"id": 1, "title": "Buy milk", "done": true, "due": "2026-01-31T00:00:00Z", ` +
+				`"created_at": "2026-01-02T03:04:05Z"}]}`,
 			want: []task.Task{
 				{
 					ID:        1,
```


## T3-cross

### 一部のエージェントだけが作った・変えたファイル

なし（全員が同じファイルの集合を変えた）

### 一部のエージェントだけが作った名前（全員に共通の新しい名前は 4 個）

なし

### 内容の類似度が低いファイル

なし（共通して変えたファイルの中身は全員一致）
