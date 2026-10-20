package app_test

import (
	"testing"

	"example.com/go-cli/internal/app/apptest"
)

func TestRun(t *testing.T) {
	t.Parallel()
	tests := []struct {
		name string
		env  map[string]string
		args []string
		want apptest.Result
	}{
		{
			name: "prints_the_version",
			env:  nil,
			args: []string{"--version"},
			want: apptest.Result{Code: 0, Stdout: "go-cli version (devel)\n"},
		},
		{
			name: "reports_a_missing_data_directory",
			env:  map[string]string{"GOCLI_DATA_DIR": "", "XDG_DATA_HOME": "", "HOME": ""},
			args: []string{"task", "list"},
			want: apptest.Result{Code: 1, Stderr: "go-cli: cannot find a data directory: set GOCLI_DATA_DIR or HOME\n"},
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			h := apptest.New(t)
			for key, value := range tt.env {
				h.Setenv(key, value)
			}
			got := h.Run(tt.args...)
			if got != tt.want {
				t.Errorf("Run(%q) = %+v, want %+v", tt.args, got, tt.want)
			}
		})
	}
}
