package user_test

import (
	"errors"
	"strings"
	"testing"
	"time"

	"example.com/go-clean/internal/domain/user"
)

func TestNew(t *testing.T) {
	t.Parallel()

	now := time.Date(2026, time.January, 1, 0, 0, 0, 0, time.UTC)
	email := user.Email("taro@example.com")

	tests := []struct {
		name     string
		input    string
		wantName string
		wantErr  error
	}{
		{name: "正常", input: "Taro", wantName: "Taro"},
		{name: "前後の空白は除去", input: "  Taro  ", wantName: "Taro"},
		{name: "空文字", input: "   ", wantErr: user.ErrInvalidName},
		{name: "50文字はOK", input: strings.Repeat("あ", 50), wantName: strings.Repeat("あ", 50)},
		{name: "51文字はNG", input: strings.Repeat("あ", 51), wantErr: user.ErrInvalidName},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			u, err := user.New(tt.input, email, now)
			if !errors.Is(err, tt.wantErr) {
				t.Fatalf("err = %v, want %v", err, tt.wantErr)
			}

			if tt.wantErr != nil {
				return
			}

			if u.Name() != tt.wantName {
				t.Errorf("Name() = %q, want %q", u.Name(), tt.wantName)
			}

			if _, err := user.ParseID(u.ID().String()); err != nil {
				t.Errorf("ID() = %q is not a valid id", u.ID())
			}
		})
	}
}

func TestNewEmail(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name    string
		input   string
		want    user.Email
		wantErr error
	}{
		{name: "正常", input: "taro@example.com", want: "taro@example.com"},
		{name: "小文字に正規化", input: "Taro@Example.com", want: "taro@example.com"},
		{name: "@なし", input: "taro.example.com", wantErr: user.ErrInvalidEmail},
		{name: "表示名付きは不可", input: "Taro <taro@example.com>", wantErr: user.ErrInvalidEmail},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			got, err := user.NewEmail(tt.input)
			if !errors.Is(err, tt.wantErr) {
				t.Fatalf("err = %v, want %v", err, tt.wantErr)
			}

			if got != tt.want {
				t.Errorf("got %q, want %q", got, tt.want)
			}
		})
	}
}
