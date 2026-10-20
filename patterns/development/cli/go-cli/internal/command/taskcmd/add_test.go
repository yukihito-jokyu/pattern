package taskcmd_test

import (
	"testing"

	"example.com/go-cli/internal/app/apptest"
)

func TestAdd(t *testing.T) {
	t.Parallel()
	tests := []struct {
		name  string
		setup [][]string
		args  []string
		want  apptest.Result
	}{
		{
			name: "adds_a_task",
			args: []string{"task", "add", "Buy milk"},
			want: apptest.Result{Code: 0, Stdout: "Added task 1: Buy milk\n"},
		},
		{
			name:  "numbers_tasks_in_order",
			setup: [][]string{{"task", "add", "Buy milk"}},
			args:  []string{"task", "add", "Write report"},
			want:  apptest.Result{Code: 0, Stdout: "Added task 2: Write report\n"},
		},
		{
			name: "trims_spaces_around_the_title",
			args: []string{"task", "add", "  Buy milk  "},
			want: apptest.Result{Code: 0, Stdout: "Added task 1: Buy milk\n"},
		},
		{
			name: "writes_json",
			args: []string{"task", "add", "Buy milk", "--json"},
			want: apptest.Result{Code: 0, Stdout: `{
  "task": {
    "id": 1,
    "title": "Buy milk",
    "done": false,
    "created_at": "2026-01-02T03:04:05Z"
  }
}
`},
		},
		{
			name: "rejects_an_empty_title",
			args: []string{"task", "add", " "},
			want: apptest.Result{Code: 2, Stderr: "go-cli: invalid input: title must be 1 to 100 characters\n" +
				"Run 'go-cli task add --help' for usage.\n"},
		},
		{
			name: "rejects_a_missing_title",
			args: []string{"task", "add"},
			want: apptest.Result{Code: 2, Stderr: "go-cli: invalid input: want 1 argument(s), got 0\n" +
				"Run 'go-cli task add --help' for usage.\n"},
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
