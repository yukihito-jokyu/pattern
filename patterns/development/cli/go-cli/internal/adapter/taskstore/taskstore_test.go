package taskstore_test

import (
	"os"
	"path/filepath"
	"slices"
	"testing"
	"time"

	"example.com/go-cli/internal/adapter/taskstore"
	"example.com/go-cli/internal/domain/task"
)

func TestLoad(t *testing.T) {
	t.Parallel()
	tests := []struct {
		name    string
		content string
		want    []task.Task
		wantErr bool
	}{
		{
			name:    "returns_no_tasks_without_a_file",
			content: "",
			want:    []task.Task{},
			wantErr: false,
		},
		{
			name: "reads_tasks",
			content: `{"version": 1, "tasks": [` +
				`{"id": 1, "title": "Buy milk", "done": true, "created_at": "2026-01-02T03:04:05Z"}]}`,
			want: []task.Task{
				{
					ID:        1,
					Title:     "Buy milk",
					Done:      true,
					CreatedAt: time.Date(2026, time.January, 2, 3, 4, 5, 0, time.UTC),
				},
			},
			wantErr: false,
		},
		{
			name:    "rejects_a_broken_file",
			content: "{",
			want:    nil,
			wantErr: true,
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			path := filepath.Join(t.TempDir(), "tasks.json")
			if tt.content != "" {
				err := os.WriteFile(path, []byte(tt.content), 0o600)
				if err != nil {
					t.Fatalf("WriteFile(%q) = %v, want nil", path, err)
				}
			}
			got, err := taskstore.New(path).Load(t.Context())
			if !slices.Equal(got, tt.want) || (err != nil) != tt.wantErr {
				t.Errorf("Load() = %v, %v, want %v, error %t", got, err, tt.want, tt.wantErr)
			}
		})
	}
}

func TestSave(t *testing.T) {
	t.Parallel()
	tests := []struct {
		name  string
		tasks []task.Task
		want  string
	}{
		{
			name:  "writes_no_tasks",
			tasks: []task.Task{},
			want:  "{\n  \"version\": 1,\n  \"tasks\": []\n}\n",
		},
		{
			name: "writes_tasks",
			tasks: []task.Task{
				{
					ID:        1,
					Title:     "Buy milk",
					Done:      true,
					CreatedAt: time.Date(2026, time.January, 2, 3, 4, 5, 0, time.UTC),
				},
			},
			want: `{
  "version": 1,
  "tasks": [
    {
      "id": 1,
      "title": "Buy milk",
      "done": true,
      "created_at": "2026-01-02T03:04:05Z"
    }
  ]
}
`,
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			path := filepath.Join(t.TempDir(), "data", "tasks.json")
			err := taskstore.New(path).Save(t.Context(), tt.tasks)
			if err != nil {
				t.Fatalf("Save(%v) = %v, want nil", tt.tasks, err)
			}
			got, err := os.ReadFile(path)
			if err != nil {
				t.Fatalf("ReadFile(%q) = %v, want nil", path, err)
			}
			if string(got) != tt.want {
				t.Errorf("ReadFile(%q) after Save(%v) = %q, want %q", path, tt.tasks, got, tt.want)
			}
		})
	}
}
