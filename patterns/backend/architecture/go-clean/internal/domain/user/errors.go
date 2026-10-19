package user

import "errors"

// ユーザー集約のドメインエラー。
var (
	ErrInvalidID          = errors.New("user: invalid id")
	ErrInvalidName        = errors.New("user: invalid name")
	ErrInvalidEmail       = errors.New("user: invalid email")
	ErrNotFound           = errors.New("user: not found")
	ErrEmailAlreadyExists = errors.New("user: email already exists")
)
