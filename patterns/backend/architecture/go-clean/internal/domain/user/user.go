package user

import (
	"strings"
	"time"
	"unicode/utf8"
)

const maxNameLength = 50

// User はユーザーエンティティ。フィールドを非公開にし、不正な状態で生成できないようにする。
type User struct {
	id        ID
	name      string
	email     Email
	createdAt time.Time
}

// New は不変条件を検証してユーザーを生成する。
func New(name string, email Email, now time.Time) (*User, error) {
	name = strings.TrimSpace(name)
	if err := validateName(name); err != nil {
		return nil, err
	}

	return &User{id: NewID(), name: name, email: email, createdAt: now}, nil
}

// Reconstruct は永続化層からの復元専用。検証済みのデータであることを前提とする。
func Reconstruct(id ID, name string, email Email, createdAt time.Time) *User {
	return &User{id: id, name: name, email: email, createdAt: createdAt}
}

// ID はユーザー ID を返す。
func (u *User) ID() ID { return u.id }

// Name は名前を返す。
func (u *User) Name() string { return u.name }

// Email はメールアドレスを返す。
func (u *User) Email() Email { return u.email }

// CreatedAt は作成日時を返す。
func (u *User) CreatedAt() time.Time { return u.createdAt }

func validateName(name string) error {
	if name == "" || utf8.RuneCountInString(name) > maxNameLength {
		return ErrInvalidName
	}

	return nil
}
