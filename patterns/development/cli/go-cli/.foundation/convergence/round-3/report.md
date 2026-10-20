# 収束テスト ラウンド 3 のレポート

このファイルは convergence.py diff が生成する。揺れの分類（R1〜R7）と対処は convergence-report.md に書く。

基準: files ≥ 1.0、names ≥ 0.8、content ≥ 0.0、check は全員通過、保護ファイルの変更なし

## 指標

| 課題 | files | names | content | check | 保護 | 基準 |
|---|---|---|---|---|---|---|
| T1-add | 1.000 | 1.000 | 1.000 | 全員通過 | — | 満たす |
| T2-change | 1.000 | 1.000 | 1.000 | 全員通過 | — | 満たす |
| T3-cross | 1.000 | 1.000 | 1.000 | 全員通過 | — | 満たす |
| H1-holdout | 1.000 | 0.941 | 0.997 | 全員通過 | — | 満たす |

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

なし

### 内容の類似度が低いファイル

なし（共通して変えたファイルの中身は全員一致）

## T3-cross

### 一部のエージェントだけが作った・変えたファイル

なし（全員が同じファイルの集合を変えた）

### 一部のエージェントだけが作った名前（全員に共通の新しい名前は 4 個）

なし

### 内容の類似度が低いファイル

なし（共通して変えたファイルの中身は全員一致）

## H1-holdout

### 一部のエージェントだけが作った・変えたファイル

なし（全員が同じファイルの集合を変えた）

### 一部のエージェントだけが作った名前（全員に共通の新しい名前は 21 個）

- agent-2: `remember`
- agent-3: `remembered`

### 内容の類似度が低いファイル

#### `internal/domain/note/note.go`（agent-1 と agent-2、類似度 0.970）

```diff
--- agent-1/internal/domain/note/note.go
+++ agent-2/internal/domain/note/note.go
@@ -10,7 +10,7 @@
 	"example.com/go-cli/internal/errkind"
 )
 
-// Note is a piece of text to be kept.
+// Note is a short piece of text to remember.
 type Note struct {
 	ID        int
 	Text      string
```

#### `internal/cli/cli_test.go`（agent-1 と agent-2、類似度 0.983）

```diff
--- agent-1/internal/cli/cli_test.go
+++ agent-2/internal/cli/cli_test.go
@@ -87,8 +87,8 @@
 		},
 		{
 			name: "rejects_an_unknown_command",
-			args: []string{"unknown"},
-			want: apptest.Result{Code: 2, Stderr: "go-cli: invalid input: unknown command \"unknown\"\n" +
+			args: []string{"project"},
+			want: apptest.Result{Code: 2, Stderr: "go-cli: invalid input: unknown command \"project\"\n" +
 				"Run 'go-cli --help' for usage.\n"},
 		},
 		{
```
