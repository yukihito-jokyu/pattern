package usecase

import (
	"context"

	"example.com/go-clean/internal/domain/user"
)

// テスト用の手書きフェイク。モック生成ツールは使わない。

type fakeUserRepository struct {
	users map[user.ID]*user.User
	err   error // 設定すると全メソッドがこのエラーを返す
}

func newFakeUserRepository(users ...*user.User) *fakeUserRepository {
	r := &fakeUserRepository{users: map[user.ID]*user.User{}}
	for _, u := range users {
		r.users[u.ID()] = u
	}

	return r
}

func (r *fakeUserRepository) Create(_ context.Context, u *user.User) error {
	if r.err != nil {
		return r.err
	}

	r.users[u.ID()] = u

	return nil
}

func (r *fakeUserRepository) FindByID(_ context.Context, id user.ID) (*user.User, error) {
	if r.err != nil {
		return nil, r.err
	}

	u, ok := r.users[id]
	if !ok {
		return nil, user.ErrNotFound
	}

	return u, nil
}

func (r *fakeUserRepository) ExistsByEmail(_ context.Context, email user.Email) (bool, error) {
	if r.err != nil {
		return false, r.err
	}

	for _, u := range r.users {
		if u.Email() == email {
			return true, nil
		}
	}

	return false, nil
}

type fakeTxManager struct{}

func (fakeTxManager) Do(ctx context.Context, fn func(ctx context.Context) error) error {
	return fn(ctx)
}
