package cli

import (
	"errors"

	"example.com/go-cli/internal/errkind"
)

// ExitCode はコマンド一覧に載せる1つの終了コードを表す。
type ExitCode struct {
	Code    int
	Meaning string
}

// App.Run が返す終了コードを定義する。
const (
	ExitOK       = 0
	ExitError    = 1
	ExitInvalid  = 2
	ExitNotFound = 3
)

// ExitCodes は App.Run が返す全終了コードを列挙する。
func ExitCodes() []ExitCode {
	return []ExitCode{
		{Code: ExitOK, Meaning: "Success"},
		{Code: ExitError, Meaning: "Unexpected failure, such as an unreadable data file"},
		{Code: ExitInvalid, Meaning: "Invalid input, such as an unknown flag or a value that breaks a rule"},
		{Code: ExitNotFound, Meaning: "The requested item does not exist"},
	}
}

// exitCode は err の種類に対応する終了コードを返す。
func exitCode(err error) int {
	switch {
	case errors.Is(err, errkind.ErrInvalid):
		return ExitInvalid
	case errors.Is(err, errkind.ErrNotFound):
		return ExitNotFound
	default:
		return ExitError
	}
}
