package usecase

import (
	"context"

	"example.com/go-clean/internal/domain/user"
)

// usecase が必要とする外部依存（port）。実装は adapter 層が持つ。

// UserRepository はユーザーの永続化を担う port。
type UserRepository interface {
	Create(ctx context.Context, u *user.User) error
	FindByID(ctx context.Context, id user.ID) (*user.User, error) // 見つからない場合は user.ErrNotFound
	ExistsByEmail(ctx context.Context, email user.Email) (bool, error)
}

// TxManager は fn を1トランザクション内で実行する。fn が error を返すとロールバックする。
type TxManager interface {
	Do(ctx context.Context, fn func(ctx context.Context) error) error
}
