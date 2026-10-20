// Package task はタスクとその読み取り・変更のユースケースを定義する。
package task

import (
	"fmt"
	"strconv"
	"time"
	"unicode/utf8"

	"example.com/go-cli/internal/errkind"
)

// Task は実行する作業を表す。
type Task struct {
	ID        int
	Title     string
	Done      bool
	CreatedAt time.Time
}

// Filter は List が返す task を絞り込む。
type Filter struct {
	// IncludeDone は List の結果に完了済みタスクも含める。
	IncludeDone bool
}

// maxTitleLength はタイトルの最大文字数を表す。
const maxTitleLength = 100

// ParseID はコマンドライン引数を Task の ID フィールドに変換する。
func ParseID(s string) (int, error) {
	id, err := strconv.Atoi(s)
	if err != nil || id < 1 {
		return 0, fmt.Errorf("%w: task ID must be a positive integer: %q", errkind.ErrInvalid, s)
	}
	return id, nil
}

// validateTitle は Task の Title フィールドを検証する。
func validateTitle(title string) error {
	n := utf8.RuneCountInString(title)
	if n == 0 || n > maxTitleLength {
		return fmt.Errorf("%w: title must be 1 to %d characters", errkind.ErrInvalid, maxTitleLength)
	}
	return nil
}
