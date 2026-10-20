# 収束テスト ラウンド 1 のレポート

このファイルは convergence.py diff が生成する。揺れの分類（R1〜R7）と対処は convergence-report.md に書く。

基準: files ≥ 1.0、names ≥ 0.8、content ≥ 0.0、check は全員通過、保護ファイルの変更なし

## 指標

| 課題 | files | names | content | check | 保護 | 基準 |
|---|---|---|---|---|---|---|
| T1-add | 1.000 | 1.000 | 0.984 | 全員通過 | — | 満たす |
| T2-change | 1.000 | 0.469 | 0.960 | 全員通過 | — | 満たさない |
| T3-cross | 1.000 | 0.484 | 0.939 | 全員通過 | — | 満たさない |

## T1-add

### 一部のエージェントだけが作った・変えたファイル

なし（全員が同じファイルの集合を変えた）

### 一部のエージェントだけが作った名前（全員に共通の新しい名前は 8 個）

なし

### 内容の類似度が低いファイル

#### `internal/command/taskcmd/remove_test.go`（agent-1 と agent-2、類似度 0.913）

```diff
--- agent-1/internal/command/taskcmd/remove_test.go
+++ agent-2/internal/command/taskcmd/remove_test.go
@@ -19,12 +19,6 @@
 			setup: [][]string{{"task", "add", "Buy milk"}},
 			args:  []string{"task", "remove", "1"},
 			want:  apptest.Result{Code: 0, Stdout: "Removed task 1: Buy milk\n"},
-		},
-		{
-			name:  "reports_a_removed_task_as_missing",
-			setup: [][]string{{"task", "add", "Buy milk"}, {"task", "remove", "1"}},
-			args:  []string{"task", "remove", "1"},
-			want:  apptest.Result{Code: 3, Stderr: "go-cli: not found: task 1\n"},
 		},
 		{
 			name:  "writes_json",
@@ -55,6 +49,12 @@
 			args:  []string{"task", "remove", "2"},
 			want:  apptest.Result{Code: 3, Stderr: "go-cli: not found: task 2\n"},
 		},
+		{
+			name:  "reports_a_removed_task_as_missing",
+			setup: [][]string{{"task", "add", "Buy milk"}, {"task", "remove", "1"}},
+			args:  []string{"task", "remove", "1"},
+			want:  apptest.Result{Code: 3, Stderr: "go-cli: not found: task 1\n"},
+		},
 	}
 	for _, tt := range tests {
 		t.Run(tt.name, func(t *testing.T) {
```

#### `internal/domain/task/service.go`（agent-1 と agent-3、類似度 0.990）

```diff
--- agent-1/internal/domain/task/service.go
+++ agent-3/internal/domain/task/service.go
@@ -74,7 +74,7 @@
 	return matched, nil
 }
 
-// Remove deletes the task with the given ID and returns the task as it was before removal.
+// Remove deletes the task with the given ID and returns it as it was before the removal.
 func (s *Service) Remove(ctx context.Context, id int) (Task, error) {
 	tasks, err := s.repo.Load(ctx)
 	if err != nil {
```


## T2-change

### 一部のエージェントだけが作った・変えたファイル

なし（全員が同じファイルの集合を変えた）

### 一部のエージェントだけが作った名前（全員に共通の新しい名前は 11 個）

- agent-1: `November`, `T09`, `accepts_an_empty_string_as_no_due_date`, `rejects_a_date_that_does_not_exist`, `rejects_a_date_with_slashes`, `rejects_an_invalid_due_date`
- agent-2: `October`, `T09`, `dueDate`, `form`, `rejects_a_date_with_slashes`, `rejects_a_day_that_does_not_exist`, `rejects_a_due_date_that_is_not_a_date`, `returns_the_zero_time_for_an_empty_string`, `tomorrow`
- agent-3: `March`, `T10`, `midnight`, `rejects_a_due_date_in_another_format`, `rejects_a_slash_date`, `rejects_an_impossible_date`, `returns_zero_for_an_empty_string`

### 内容の類似度が低いファイル

#### `internal/command/taskcmd/list_test.go`（agent-2 と agent-3、類似度 0.802）

```diff
--- agent-2/internal/command/taskcmd/list_test.go
+++ agent-3/internal/command/taskcmd/list_test.go
@@ -31,6 +31,17 @@
 				"2   open    -    Write report\n"},
 		},
 		{
+			name: "shows_due_dates",
+			setup: [][]string{
+				{"task", "add", "Buy milk", "--due", "2026-03-04"},
+				{"task", "add", "Write report"},
+			},
+			args: []string{"task", "list"},
+			want: apptest.Result{Code: 0, Stdout: "ID  STATUS  DUE         TITLE\n" +
+				"1   open    2026-03-04  Buy milk\n" +
+				"2   open    -           Write report\n"},
+		},
+		{
 			name: "includes_done_tasks_with_all",
 			setup: [][]string{
 				{"task", "add", "Buy milk"},
@@ -43,19 +54,8 @@
 				"2   open    -    Write report\n"},
 		},
 		{
-			name: "shows_due_dates",
-			setup: [][]string{
-				{"task", "add", "Buy milk", "--due", "2026-10-31"},
-				{"task", "add", "Write report"},
-			},
-			args: []string{"task", "list"},
-			want: apptest.Result{Code: 0, Stdout: "ID  STATUS  DUE         TITLE\n" +
-				"1   open    2026-10-31  Buy milk\n" +
-				"2   open    -           Write report\n"},
-		},
-		{
 			name:  "writes_json",
-			setup: [][]string{{"task", "add", "Buy milk"}},
+			setup: [][]string{{"task", "add", "Buy milk", "--due", "2026-03-04"}, {"task", "add", "Write report"}},
 			args:  []string{"task", "list", "--json"},
 			want: apptest.Result{Code: 0, Stdout: `{
   "tasks": [
@@ -63,23 +63,13 @@
       "id": 1,
       "title": "Buy milk",
       "done": false,
+      "due": "2026-03-04T00:00:00Z",
       "created_at": "2026-01-02T03:04:05Z"
-    }
-  ]
-}
-`},
-		},
-		{
-			name:  "writes_json_with_a_due_date",
-			setup: [][]string{{"task", "add", "Buy milk", "--due", "2026-10-31"}},
-			args:  []string{"task", "list", "--json"},
-			want: apptest.Result{Code: 0, Stdout: `{
-  "tasks": [
+    },
     {
-      "id": 1,
-      "title": "Buy milk",
+      "id": 2,
+      "title": "Write report",
       "done": false,
-      "due": "2026-10-31T00:00:00Z",
       "created_at": "2026-01-02T03:04:05Z"
     }
   ]
```

#### `internal/domain/task/task_test.go`（agent-1 と agent-2、類似度 0.885）

```diff
--- agent-1/internal/domain/task/task_test.go
+++ agent-2/internal/domain/task/task_test.go
@@ -44,20 +44,20 @@
 	}{
 		{
 			name:    "accepts_a_date",
-			s:       "2026-11-01",
-			want:    time.Date(2026, time.November, 1, 0, 0, 0, 0, time.UTC),
+			s:       "2026-10-31",
+			want:    time.Date(2026, time.October, 31, 0, 0, 0, 0, time.UTC),
 			wantErr: nil,
 		},
-		{name: "accepts_an_empty_string_as_no_due_date", s: "", want: time.Time{}, wantErr: nil},
-		{name: "rejects_a_date_with_slashes", s: "2026/11/01", want: time.Time{}, wantErr: errkind.ErrInvalid},
-		{name: "rejects_a_date_that_does_not_exist", s: "2026-02-30", want: time.Time{}, wantErr: errkind.ErrInvalid},
-		{name: "rejects_a_date_with_a_time", s: "2026-11-01T09:00:00Z", want: time.Time{}, wantErr: errkind.ErrInvalid},
+		{name: "returns_the_zero_time_for_an_empty_string", s: "", want: time.Time{}, wantErr: nil},
+		{name: "rejects_a_date_with_slashes", s: "2026/10/31", want: time.Time{}, wantErr: errkind.ErrInvalid},
+		{name: "rejects_a_day_that_does_not_exist", s: "2026-02-30", want: time.Time{}, wantErr: errkind.ErrInvalid},
+		{name: "rejects_a_date_with_a_time", s: "2026-10-31T09:00:00Z", want: time.Time{}, wantErr: errkind.ErrInvalid},
 	}
 	for _, tt := range tests {
 		t.Run(tt.name, func(t *testing.T) {
 			t.Parallel()
 			got, err := task.ParseDue(tt.s)
-			if got != tt.want || !errors.Is(err, tt.wantErr) {
+			if !got.Equal(tt.want) || !errors.Is(err, tt.wantErr) {
 				t.Errorf("ParseDue(%q) = %v, %v, want %v, %v", tt.s, got, err, tt.want, tt.wantErr)
 			}
 		})
```

#### `internal/command/taskcmd/add_test.go`（agent-1 と agent-2、類似度 0.938）

```diff
--- agent-1/internal/command/taskcmd/add_test.go
+++ agent-2/internal/command/taskcmd/add_test.go
@@ -45,29 +45,29 @@
 		},
 		{
 			name: "adds_a_task_with_a_due_date",
-			args: []string{"task", "add", "Buy milk", "--due", "2026-11-01"},
+			args: []string{"task", "add", "Buy milk", "--due", "2026-10-31"},
 			want: apptest.Result{Code: 0, Stdout: "Added task 1: Buy milk\n"},
 		},
 		{
 			name: "writes_json_with_a_due_date",
-			args: []string{"task", "add", "Buy milk", "--due", "2026-11-01", "--json"},
+			args: []string{"task", "add", "Buy milk", "--due", "2026-10-31", "--json"},
 			want: apptest.Result{Code: 0, Stdout: `{
   "task": {
     "id": 1,
     "title": "Buy milk",
     "done": false,
-    "due": "2026-11-01T00:00:00Z",
+    "due": "2026-10-31T00:00:00Z",
     "created_at": "2026-01-02T03:04:05Z"
   }
 }
 `},
 		},
 		{
-			name: "rejects_an_invalid_due_date",
-			args: []string{"task", "add", "Buy milk", "--due", "2026/11/01"},
+			name: "rejects_a_due_date_that_is_not_a_date",
+			args: []string{"task", "add", "Buy milk", "--due", "tomorrow"},
 			want: apptest.Result{
 				Code: 2,
-				Stderr: "go-cli: invalid input: due must be a date in YYYY-MM-DD format: \"2026/11/01\"\n" +
+				Stderr: "go-cli: invalid input: due must be a date in YYYY-MM-DD format: \"tomorrow\"\n" +
 					"Run 'go-cli task add --help' for usage.\n",
 			},
 		},
```

#### `internal/command/taskcmd/view.go`（agent-1 と agent-2、類似度 0.933）

```diff
--- agent-1/internal/command/taskcmd/view.go
+++ agent-2/internal/command/taskcmd/view.go
@@ -27,8 +27,8 @@
 	return "open"
 }
 
-// due returns the date shown in the DUE column, or "-" when the task has no due date.
-func (v taskView) due() string {
+// dueDate returns the text shown in the DUE column.
+func (v taskView) dueDate() string {
 	if v.Due.IsZero() {
 		return "-"
 	}
```

#### `internal/adapter/taskstore/taskstore_test.go`（agent-1 と agent-3、類似度 0.968）

```diff
--- agent-1/internal/adapter/taskstore/taskstore_test.go
+++ agent-3/internal/adapter/taskstore/taskstore_test.go
@@ -42,14 +42,14 @@
 		{
 			name: "reads_a_due_date",
 			content: `{"version": 1, "tasks": [` +
-				`{"id": 1, "title": "Buy milk", "done": false, "due": "2026-11-01T00:00:00Z", ` +
-				`"created_at": "2026-01-02T03:04:05Z"}]}`,
+				`{"id": 1, "title": "Buy milk", "done": false, "due": "2026-03-04T00:00:00Z",` +
+				` "created_at": "2026-01-02T03:04:05Z"}]}`,
 			want: []task.Task{
 				{
 					ID:        1,
 					Title:     "Buy milk",
 					Done:      false,
-					Due:       time.Date(2026, time.November, 1, 0, 0, 0, 0, time.UTC),
+					Due:       time.Date(2026, time.March, 4, 0, 0, 0, 0, time.UTC),
 					CreatedAt: time.Date(2026, time.January, 2, 3, 4, 5, 0, time.UTC),
 				},
 			},
@@ -122,7 +122,7 @@
 					ID:        1,
 					Title:     "Buy milk",
 					Done:      false,
-					Due:       time.Date(2026, time.November, 1, 0, 0, 0, 0, time.UTC),
+					Due:       time.Date(2026, time.March, 4, 0, 0, 0, 0, time.UTC),
 					CreatedAt: time.Date(2026, time.January, 2, 3, 4, 5, 0, time.UTC),
 				},
 			},
@@ -133,7 +133,7 @@
       "id": 1,
       "title": "Buy milk",
       "done": false,
-      "due": "2026-11-01T00:00:00Z",
+      "due": "2026-03-04T00:00:00Z",
       "created_at": "2026-01-02T03:04:05Z"
     }
   ]
```


## T3-cross

### 一部のエージェントだけが作った・変えたファイル

なし（全員が同じファイルの集合を変えた）

### 一部のエージェントだけが作った名前（全員に共通の新しい名前は 6 個）

- agent-1: `Repeat`, `accepts_a_title_up_to_the_title_max`, `loadDataDir`, `loadTitleMax`, `rejects_a_title_longer_than_100_characters_by_default`, `rejects_a_title_longer_than_the_title_max`, `rejects_a_title_max_of_zero`, `rejects_a_title_max_that_is_not_a_number`, `ten`
- agent-2: `accepts_a_title_up_to_the_configured_limit`, `rejects_a_title_limit_below_one`, `rejects_a_title_limit_that_is_not_a_number`, `rejects_a_title_over_the_configured_limit`, `ten`
- agent-3: `abc`, `accepts_a_title_up_to_the_title_max`, `loadDataDir`, `loadTitleMax`, `rejects_a_title_longer_than_the_title_max`, `rejects_a_title_max_of_zero`, `rejects_a_title_max_that_is_not_a_number`

### 内容の類似度が低いファイル

#### `internal/app/config.go`（agent-1 と agent-2、類似度 0.615）

```diff
--- agent-1/internal/app/config.go
+++ agent-2/internal/app/config.go
@@ -25,50 +25,35 @@
 	envHome     = "HOME"
 )
 
-// defaultTitleMax is the maximum number of characters in a task title when $GOCLI_TITLE_MAX is not set.
+// defaultTitleMax is the maximum number of characters in a task title when GOCLI_TITLE_MAX is not set.
 const defaultTitleMax = 100
 
 var errNoDataDir = errors.New("cannot find a data directory: set " + envDataDir + " or HOME")
 
-// loadConfig reads the settings.
+// loadConfig reads the settings. The data directory is the first of
+// $GOCLI_DATA_DIR, $XDG_DATA_HOME/go-cli and $HOME/.local/share/go-cli that is set.
+// The title limit is $GOCLI_TITLE_MAX, or defaultTitleMax when it is not set.
 func loadConfig(getenv func(key string) string) (config, error) {
-	dir, err := loadDataDir(getenv)
-	if err != nil {
-		return config{}, err
+	titleMax := defaultTitleMax
+	value := getenv(envTitleMax)
+	if value != "" {
+		n, err := strconv.Atoi(value)
+		if err != nil || n < 1 {
+			return config{}, fmt.Errorf("%w: GOCLI_TITLE_MAX must be a positive integer: %q", errkind.ErrInvalid, value)
+		}
+		titleMax = n
 	}
-	titleMax, err := loadTitleMax(getenv)
-	if err != nil {
-		return config{}, err
-	}
-	return config{dataDir: dir, titleMax: titleMax}, nil
-}
-
-// loadDataDir returns the first of $GOCLI_DATA_DIR, $XDG_DATA_HOME/go-cli and $HOME/.local/share/go-cli that is set.
-func loadDataDir(getenv func(key string) string) (string, error) {
 	dir := getenv(envDataDir)
 	if dir != "" {
-		return dir, nil
+		return config{dataDir: dir, titleMax: titleMax}, nil
 	}
 	dir = getenv(envXDGData)
 	if dir != "" {
-		return filepath.Join(dir, name), nil
+		return config{dataDir: filepath.Join(dir, name), titleMax: titleMax}, nil
 	}
 	dir = getenv(envHome)
 	if dir != "" {
-		return filepath.Join(dir, ".local", "share", name), nil
+		return config{dataDir: filepath.Join(dir, ".local", "share", name), titleMax: titleMax}, nil
 	}
-	return "", errNoDataDir
+	return config{}, errNoDataDir
 }
-
-// loadTitleMax returns $GOCLI_TITLE_MAX as a positive integer, or defaultTitleMax when it is not set.
-func loadTitleMax(getenv func(key string) string) (int, error) {
-	value := getenv(envTitleMax)
-	if value == "" {
-		return defaultTitleMax, nil
-	}
-	n, err := strconv.Atoi(value)
-	if err != nil || n < 1 {
-		return 0, fmt.Errorf("%w: %s must be a positive integer: %q", errkind.ErrInvalid, envTitleMax, value)
-	}
-	return n, nil
-}
```

#### `internal/command/taskcmd/add_test.go`（agent-2 と agent-3、類似度 0.907）

```diff
--- agent-2/internal/command/taskcmd/add_test.go
+++ agent-3/internal/command/taskcmd/add_test.go
@@ -51,22 +51,22 @@
 				"Run 'go-cli task add --help' for usage.\n"},
 		},
 		{
-			name: "accepts_a_title_up_to_the_configured_limit",
+			name: "rejects_a_missing_title",
+			args: []string{"task", "add"},
+			want: apptest.Result{Code: 2, Stderr: "go-cli: invalid input: want 1 argument(s), got 0\n" +
+				"Run 'go-cli task add --help' for usage.\n"},
+		},
+		{
+			name: "accepts_a_title_up_to_the_title_max",
 			env:  map[string]string{"GOCLI_TITLE_MAX": "8"},
 			args: []string{"task", "add", "Buy milk"},
 			want: apptest.Result{Code: 0, Stdout: "Added task 1: Buy milk\n"},
 		},
 		{
-			name: "rejects_a_title_over_the_configured_limit",
+			name: "rejects_a_title_longer_than_the_title_max",
 			env:  map[string]string{"GOCLI_TITLE_MAX": "7"},
 			args: []string{"task", "add", "Buy milk"},
 			want: apptest.Result{Code: 2, Stderr: "go-cli: invalid input: title must be 1 to 7 characters\n" +
-				"Run 'go-cli task add --help' for usage.\n"},
-		},
-		{
-			name: "rejects_a_missing_title",
-			args: []string{"task", "add"},
-			want: apptest.Result{Code: 2, Stderr: "go-cli: invalid input: want 1 argument(s), got 0\n" +
 				"Run 'go-cli task add --help' for usage.\n"},
 		},
 	}
```

#### `internal/app/app_test.go`（agent-2 と agent-3、類似度 0.931）

```diff
--- agent-2/internal/app/app_test.go
+++ agent-3/internal/app/app_test.go
@@ -27,16 +27,16 @@
 			want: apptest.Result{Code: 1, Stderr: "go-cli: cannot find a data directory: set GOCLI_DATA_DIR or HOME\n"},
 		},
 		{
-			name: "rejects_a_title_limit_that_is_not_a_number",
-			env:  map[string]string{"GOCLI_TITLE_MAX": "ten"},
+			name: "rejects_a_title_max_that_is_not_a_number",
+			env:  map[string]string{"GOCLI_TITLE_MAX": "abc"},
 			args: []string{"task", "list"},
 			want: apptest.Result{
 				Code:   2,
-				Stderr: "go-cli: invalid input: GOCLI_TITLE_MAX must be a positive integer: \"ten\"\n",
+				Stderr: "go-cli: invalid input: GOCLI_TITLE_MAX must be a positive integer: \"abc\"\n",
 			},
 		},
 		{
-			name: "rejects_a_title_limit_below_one",
+			name: "rejects_a_title_max_of_zero",
 			env:  map[string]string{"GOCLI_TITLE_MAX": "0"},
 			args: []string{"task", "list"},
 			want: apptest.Result{
```

#### `internal/domain/task/service.go`（agent-1 と agent-2、類似度 0.976）

```diff
--- agent-1/internal/domain/task/service.go
+++ agent-2/internal/domain/task/service.go
@@ -17,8 +17,8 @@
 	titleMax int
 }
 
-// NewService returns a Service that keeps tasks in repo, reads the current time from now
-// and accepts titles of up to titleMax characters.
+// NewService returns a Service that keeps tasks in repo, reads the current time from now and
+// accepts titles of up to titleMax characters.
 func NewService(repo Repository, now func() time.Time, titleMax int) *Service {
 	return &Service{repo: repo, now: now, titleMax: titleMax}
 }
```
