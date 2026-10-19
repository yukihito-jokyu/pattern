package repository

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"time"

	"example.com/go-clean/internal/domain/user"
	"example.com/go-clean/internal/usecase"
)

var _ usecase.UserRepository = (*UserRepository)(nil)

// UserRepository は usecase.UserRepository の PostgreSQL 実装。
type UserRepository struct {
	db *sql.DB
}

// NewUserRepository は UserRepository を生成する。
func NewUserRepository(db *sql.DB) *UserRepository {
	return &UserRepository{db: db}
}

// Create はユーザーを保存する。メールアドレスが重複していれば user.ErrEmailAlreadyExists を返す。
func (r *UserRepository) Create(ctx context.Context, u *user.User) error {
	const q = `
		INSERT INTO users (
			id,
			name,
			email,
			created_at
		)
		VALUES (
			$1,
			$2,
			$3,
			$4
		)
	`

	_, err := conn(ctx, r.db).ExecContext(ctx, q, u.ID().String(), u.Name(), u.Email().String(), u.CreatedAt())
	if isUniqueViolation(err) {
		return user.ErrEmailAlreadyExists
	}

	if err != nil {
		return fmt.Errorf("insert user: %w", err)
	}

	return nil
}

// FindByID は ID でユーザーを取得する。見つからなければ user.ErrNotFound を返す。
func (r *UserRepository) FindByID(ctx context.Context, id user.ID) (*user.User, error) {
	const q = `
		SELECT
			id,
			name,
			email,
			created_at
		FROM
			users
		WHERE
			id = $1
	`

	var (
		rowID, name, email string
		createdAt          time.Time
	)

	err := conn(ctx, r.db).QueryRowContext(ctx, q, id.String()).Scan(&rowID, &name, &email, &createdAt)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, user.ErrNotFound
	}

	if err != nil {
		return nil, fmt.Errorf("select user: %w", err)
	}

	return user.Reconstruct(user.ID(rowID), name, user.Email(email), createdAt), nil
}

// ExistsByEmail はメールアドレスが登録済みかを返す。
func (r *UserRepository) ExistsByEmail(ctx context.Context, email user.Email) (bool, error) {
	const q = `
		SELECT EXISTS (
			SELECT
				1
			FROM
				users
			WHERE
				email = $1
		)
	`

	var exists bool
	if err := conn(ctx, r.db).QueryRowContext(ctx, q, email.String()).Scan(&exists); err != nil {
		return false, fmt.Errorf("exists user by email: %w", err)
	}

	return exists, nil
}
