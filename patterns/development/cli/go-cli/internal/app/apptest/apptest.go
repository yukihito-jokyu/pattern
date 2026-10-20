// Package apptest はテストで CLI を実行する。
//
// 各 Harness は専用の空のデータディレクトリを持つ。
// 時計は常に 2026-01-02T12:04:05.123456789+09:00 を返し、UTC の秒単位に変換したときだけ出力が 2026-01-02T03:04:05Z になるようにする（OPS-03）。
package apptest

import (
	"strings"
	"testing"
	"time"

	"example.com/go-cli/internal/app"
)

// Result は CLI を1回実行した結果を表す。
type Result struct {
	Code   int
	Stdout string
	Stderr string
}

// Harness は1つの一時データディレクトリで CLI を実行する。
type Harness struct {
	tb  testing.TB
	env map[string]string
}

// clockOffset はテストの時計の UTC から東向きの時差を秒で表す。
const clockOffset = 9 * 60 * 60

// New は空の一時ディレクトリを指す GOCLI_DATA_DIR だけを設定した Harness を返す。
func New(tb testing.TB) *Harness {
	tb.Helper()
	return &Harness{tb: tb, env: map[string]string{"GOCLI_DATA_DIR": tb.TempDir()}}
}

// Setenv は以後の実行で使う環境変数 key を設定する。
// 空の値を渡すと設定を解除する。
func (h *Harness) Setenv(key, value string) {
	h.env[key] = value
}

// Run は args で CLI を実行し、結果を返す。
func (h *Harness) Run(args ...string) Result {
	h.tb.Helper()
	var stdout, stderr strings.Builder
	code := app.Run(h.tb.Context(), args, app.Env{
		Stdout: &stdout,
		Stderr: &stderr,
		Getenv: h.getenv,
		Now:    now,
	})
	return Result{Code: code, Stdout: stdout.String(), Stderr: stderr.String()}
}

// Setup は args で CLI を実行し、終了コードが0でなければテストを失敗させる。
func (h *Harness) Setup(args ...string) {
	h.tb.Helper()
	got := h.Run(args...)
	if got.Code != 0 {
		h.tb.Fatalf("Run(%q) = %+v, want exit code 0", args, got)
	}
}

// getenv は h の環境変数 key の値を返す。
func (h *Harness) getenv(key string) string {
	return h.env[key]
}

// now はテストの時計の固定時刻を返す。
func now() time.Time {
	return time.Date(2026, time.January, 2, 12, 4, 5, 123456789, time.FixedZone("JST", clockOffset))
}
