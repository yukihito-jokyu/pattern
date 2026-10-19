package user

import (
	"net/mail"
	"strings"
)

// Email は検証済みのメールアドレスを表す値オブジェクト。
type Email string

// NewEmail はメールアドレスを検証して Email に変換する。
func NewEmail(s string) (Email, error) {
	addr, err := mail.ParseAddress(s)
	if err != nil || addr.Address != s {
		return "", ErrInvalidEmail
	}

	return Email(strings.ToLower(s)), nil
}

func (e Email) String() string { return string(e) }
