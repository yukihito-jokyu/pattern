package usecase

import (
	"context"
	"fmt"
	"time"

	"example.com/go-clean/internal/domain/user"
)

// CreateUserInput はユーザー作成の入力。
type CreateUserInput struct {
	Name  string
	Email string
}

// GetUserInput はユーザー取得の入力。
type GetUserInput struct {
	ID string
}

// UserOutput はユーザー系ユースケース共通の出力。domain の型を外へ漏らさないために詰め替える。
type UserOutput struct {
	ID        string
	Name      string
	Email     string
	CreatedAt time.Time
}

// UserUsecase はユーザーに関するユースケース。
type UserUsecase struct {
	repo UserRepository
	tx   TxManager
	now  func() time.Time
}

// NewUserUsecase は UserUsecase を生成する。
func NewUserUsecase(repo UserRepository, tx TxManager) *UserUsecase {
	return &UserUsecase{repo: repo, tx: tx, now: time.Now}
}

// Create はメールアドレスの重複を確認してユーザーを作成する。
func (uc *UserUsecase) Create(ctx context.Context, in CreateUserInput) (*UserOutput, error) {
	email, err := user.NewEmail(in.Email)
	if err != nil {
		return nil, err
	}

	u, err := user.New(in.Name, email, uc.now())
	if err != nil {
		return nil, err
	}

	txErr := uc.tx.Do(ctx, func(ctx context.Context) error {
		exists, err := uc.repo.ExistsByEmail(ctx, email)
		if err != nil {
			return fmt.Errorf("exists by email: %w", err)
		}

		if exists {
			return user.ErrEmailAlreadyExists
		}

		if err := uc.repo.Create(ctx, u); err != nil {
			return fmt.Errorf("create user: %w", err)
		}

		return nil
	})
	if txErr != nil {
		return nil, txErr
	}

	return newUserOutput(u), nil
}

// Get は ID でユーザーを取得する。
func (uc *UserUsecase) Get(ctx context.Context, in GetUserInput) (*UserOutput, error) {
	id, err := user.ParseID(in.ID)
	if err != nil {
		return nil, err
	}

	u, err := uc.repo.FindByID(ctx, id)
	if err != nil {
		return nil, err
	}

	return newUserOutput(u), nil
}

func newUserOutput(u *user.User) *UserOutput {
	return &UserOutput{
		ID:        u.ID().String(),
		Name:      u.Name(),
		Email:     u.Email().String(),
		CreatedAt: u.CreatedAt(),
	}
}
