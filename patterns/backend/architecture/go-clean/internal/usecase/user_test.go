package usecase

import (
	"errors"
	"testing"
	"time"

	"example.com/go-clean/internal/domain/user"
)

func TestUserUsecase_Create(t *testing.T) {
	t.Parallel()

	now := time.Date(2026, time.January, 1, 0, 0, 0, 0, time.UTC)
	existingID := user.NewID()
	errDB := errors.New("db down")

	tests := []struct {
		name    string
		repo    *fakeUserRepository
		input   CreateUserInput
		wantErr error
	}{
		{
			name:  "正常",
			repo:  newFakeUserRepository(user.Reconstruct(existingID, "Hanako", "hanako@example.com", now)),
			input: CreateUserInput{Name: "Taro", Email: "taro@example.com"},
		},
		{
			name:    "メールアドレス重複",
			repo:    newFakeUserRepository(user.Reconstruct(existingID, "Hanako", "hanako@example.com", now)),
			input:   CreateUserInput{Name: "Taro", Email: "hanako@example.com"},
			wantErr: user.ErrEmailAlreadyExists,
		},
		{
			name:    "不正なメールアドレス",
			repo:    newFakeUserRepository(),
			input:   CreateUserInput{Name: "Taro", Email: "invalid"},
			wantErr: user.ErrInvalidEmail,
		},
		{
			name:    "不正な名前",
			repo:    newFakeUserRepository(),
			input:   CreateUserInput{Name: "", Email: "taro@example.com"},
			wantErr: user.ErrInvalidName,
		},
		{
			name:    "リポジトリエラーはラップして返す",
			repo:    &fakeUserRepository{users: map[user.ID]*user.User{}, err: errDB},
			input:   CreateUserInput{Name: "Taro", Email: "taro@example.com"},
			wantErr: errDB,
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			uc := NewUserUsecase(tt.repo, fakeTxManager{})
			uc.now = func() time.Time { return now }

			got, err := uc.Create(t.Context(), tt.input)
			if !errors.Is(err, tt.wantErr) {
				t.Fatalf("err = %v, want %v", err, tt.wantErr)
			}

			if tt.wantErr != nil {
				return
			}

			// ID は生成される値なので got から写す
			want := UserOutput{ID: got.ID, Name: tt.input.Name, Email: tt.input.Email, CreatedAt: now}
			if *got != want {
				t.Errorf("got %+v, want %+v", *got, want)
			}

			if _, ok := tt.repo.users[user.ID(got.ID)]; !ok {
				t.Errorf("user %s was not saved", got.ID)
			}
		})
	}
}

func TestUserUsecase_Get(t *testing.T) {
	t.Parallel()

	now := time.Date(2026, time.January, 1, 0, 0, 0, 0, time.UTC)
	existingID := user.NewID()

	tests := []struct {
		name    string
		id      string
		wantErr error
	}{
		{name: "正常", id: existingID.String()},
		{name: "存在しない", id: user.NewID().String(), wantErr: user.ErrNotFound},
		{name: "不正なID", id: "not-a-uuid", wantErr: user.ErrInvalidID},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			repo := newFakeUserRepository(user.Reconstruct(existingID, "Hanako", "hanako@example.com", now))
			uc := NewUserUsecase(repo, fakeTxManager{})

			got, err := uc.Get(t.Context(), GetUserInput{ID: tt.id})
			if !errors.Is(err, tt.wantErr) {
				t.Fatalf("err = %v, want %v", err, tt.wantErr)
			}

			if tt.wantErr != nil {
				return
			}

			want := UserOutput{ID: tt.id, Name: "Hanako", Email: "hanako@example.com", CreatedAt: now}
			if *got != want {
				t.Errorf("got %+v, want %+v", *got, want)
			}
		})
	}
}
