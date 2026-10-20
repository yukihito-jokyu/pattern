package cli_test

import (
	"testing"

	"example.com/go-cli/internal/app/apptest"
)

func TestRun(t *testing.T) {
	t.Parallel()
	tests := []struct {
		name  string
		setup [][]string
		args  []string
		want  apptest.Result
	}{
		{
			name: "prints_the_commands_with_help",
			args: []string{"--help"},
			want: apptest.Result{Code: 0, Stdout: `Usage:
  go-cli <command> <subcommand> [flags] [arguments]

Commands:
  task  Manage tasks

Flags:
  --help     Show help
  --version  Show the version

Run 'go-cli <command> --help' for the subcommands of a command.
`},
		},
		{
			name: "prints_the_subcommands_with_help",
			args: []string{"task", "--help"},
			want: apptest.Result{Code: 0, Stdout: `Manage tasks

Usage:
  go-cli task <subcommand> [flags] [arguments]

Subcommands:
  add       Add a task
  complete  Mark a task as done
  list      List open tasks

Run 'go-cli task <subcommand> --help' for the flags of a subcommand.
`},
		},
		{
			name: "prints_the_flags_with_help",
			args: []string{"task", "list", "--help"},
			want: apptest.Result{Code: 0, Stdout: `List open tasks

Usage:
  go-cli task list [flags]

Flags:
  --help  Show help
  --all   Include completed tasks
  --json  Write the output as JSON
`},
		},
		{
			name: "accepts_flags_before_arguments",
			args: []string{"task", "add", "--json", "Buy milk"},
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
			name: "treats_arguments_after_double_dash_as_positional",
			args: []string{"task", "add", "--", "--json"},
			want: apptest.Result{Code: 0, Stdout: "Added task 1: --json\n"},
		},
		{
			name: "rejects_a_missing_command",
			args: []string{},
			want: apptest.Result{Code: 2, Stderr: "go-cli: invalid input: missing command\n" +
				"Run 'go-cli --help' for usage.\n"},
		},
		{
			name: "rejects_an_unknown_command",
			args: []string{"unknown"},
			want: apptest.Result{Code: 2, Stderr: "go-cli: invalid input: unknown command \"unknown\"\n" +
				"Run 'go-cli --help' for usage.\n"},
		},
		{
			name: "rejects_a_missing_subcommand",
			args: []string{"task"},
			want: apptest.Result{Code: 2, Stderr: "go-cli: invalid input: missing subcommand\n" +
				"Run 'go-cli task --help' for usage.\n"},
		},
		{
			name: "rejects_an_unknown_subcommand",
			args: []string{"task", "delete"},
			want: apptest.Result{Code: 2, Stderr: "go-cli: invalid input: unknown subcommand \"delete\"\n" +
				"Run 'go-cli task --help' for usage.\n"},
		},
		{
			name: "rejects_extra_arguments",
			args: []string{"task", "add", "Buy", "milk"},
			want: apptest.Result{Code: 2, Stderr: "go-cli: invalid input: want 1 argument(s), got 2\n" +
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
