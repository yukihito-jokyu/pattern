package taskcmd_test

import (
	"testing"

	"example.com/go-cli/internal/app/apptest"
)

func TestList(t *testing.T) {
	t.Parallel()
	tests := []struct {
		name  string
		setup [][]string
		args  []string
		want  apptest.Result
	}{
		{
			name: "prints_only_the_header_without_tasks",
			args: []string{"task", "list"},
			want: apptest.Result{Code: 0, Stdout: "ID  STATUS  TITLE\n"},
		},
		{
			name: "lists_tasks",
			setup: [][]string{
				{"task", "add", "Buy milk"},
				{"task", "add", "Write report"},
				{"task", "complete", "1"},
			},
			args: []string{"task", "list"},
			want: apptest.Result{Code: 0, Stdout: "ID  STATUS  TITLE\n" +
				"2   open    Write report\n"},
		},
		{
			name: "lists_tasks_with_all",
			setup: [][]string{
				{"task", "add", "Buy milk"},
				{"task", "add", "Write report"},
				{"task", "complete", "1"},
			},
			args: []string{"task", "list", "--all"},
			want: apptest.Result{Code: 0, Stdout: "ID  STATUS  TITLE\n" +
				"1   done    Buy milk\n" +
				"2   open    Write report\n"},
		},
		{
			name:  "writes_json",
			setup: [][]string{{"task", "add", "Buy milk"}},
			args:  []string{"task", "list", "--json"},
			want: apptest.Result{Code: 0, Stdout: `{
  "tasks": [
    {
      "id": 1,
      "title": "Buy milk",
      "done": false,
      "created_at": "2026-01-02T03:04:05Z"
    }
  ]
}
`},
		},
		{
			name: "writes_an_empty_json_array_without_tasks",
			args: []string{"task", "list", "--json"},
			want: apptest.Result{Code: 0, Stdout: "{\n  \"tasks\": []\n}\n"},
		},
		{
			name: "rejects_an_unknown_flag",
			args: []string{"task", "list", "--done"},
			want: apptest.Result{Code: 2, Stderr: "go-cli: invalid input: flag provided but not defined: -done\n" +
				"Run 'go-cli task list --help' for usage.\n"},
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
