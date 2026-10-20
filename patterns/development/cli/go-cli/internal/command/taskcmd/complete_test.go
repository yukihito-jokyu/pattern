package taskcmd_test

import (
	"testing"

	"example.com/go-cli/internal/app/apptest"
)

func TestComplete(t *testing.T) {
	t.Parallel()
	tests := []struct {
		name  string
		setup [][]string
		args  []string
		want  apptest.Result
	}{
		{
			name:  "completes_a_task",
			setup: [][]string{{"task", "add", "Buy milk"}},
			args:  []string{"task", "complete", "1"},
			want:  apptest.Result{Code: 0, Stdout: "Completed task 1: Buy milk\n"},
		},
		{
			name:  "keeps_a_done_task_done",
			setup: [][]string{{"task", "add", "Buy milk"}, {"task", "complete", "1"}},
			args:  []string{"task", "complete", "1"},
			want:  apptest.Result{Code: 0, Stdout: "Completed task 1: Buy milk\n"},
		},
		{
			name:  "writes_json",
			setup: [][]string{{"task", "add", "Buy milk"}},
			args:  []string{"task", "complete", "1", "--json"},
			want: apptest.Result{Code: 0, Stdout: `{
  "task": {
    "id": 1,
    "title": "Buy milk",
    "done": true,
    "created_at": "2026-01-02T03:04:05Z"
  }
}
`},
		},
		{
			name: "rejects_an_id_that_is_not_a_number",
			args: []string{"task", "complete", "one"},
			want: apptest.Result{
				Code: 2,
				Stderr: "go-cli: invalid input: task ID must be a positive integer: \"one\"\n" +
					"Run 'go-cli task complete --help' for usage.\n",
			},
		},
		{
			name:  "reports_a_missing_task",
			setup: [][]string{{"task", "add", "Buy milk"}},
			args:  []string{"task", "complete", "2"},
			want:  apptest.Result{Code: 3, Stderr: "go-cli: not found: task 2\n"},
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			h := apptest.New(t)
			for _, args := range tt.setup {
				h.Setup(args...)
			}
			got := h.Run(tt.args...)
			if got != tt.want {
				t.Errorf("Run(%q) = %+v, want %+v", tt.args, got, tt.want)
			}
		})
	}
}
