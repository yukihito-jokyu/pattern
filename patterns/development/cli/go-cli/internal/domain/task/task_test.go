package task_test

import (
	"errors"
	"testing"

	"example.com/go-cli/internal/domain/task"
	"example.com/go-cli/internal/errkind"
)

func TestParseID(t *testing.T) {
	t.Parallel()
	tests := []struct {
		name    string
		s       string
		want    int
		wantErr error
	}{
		{name: "accepts_a_positive_integer", s: "12", want: 12, wantErr: nil},
		{name: "rejects_zero", s: "0", want: 0, wantErr: errkind.ErrInvalid},
		{name: "rejects_a_negative_integer", s: "-1", want: 0, wantErr: errkind.ErrInvalid},
		{name: "rejects_a_word", s: "one", want: 0, wantErr: errkind.ErrInvalid},
		{name: "rejects_an_empty_string", s: "", want: 0, wantErr: errkind.ErrInvalid},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			got, err := task.ParseID(tt.s)
			if got != tt.want || !errors.Is(err, tt.wantErr) {
				t.Errorf("ParseID(%q) = %d, %v, want %d, %v", tt.s, got, err, tt.want, tt.wantErr)
			}
		})
	}
}
