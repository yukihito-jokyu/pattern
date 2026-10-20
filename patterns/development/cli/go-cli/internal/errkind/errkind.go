// Package errkind は CLI の終了コードを決めるエラーの種類を定義する。
//
// 他のパッケージは fmt.Errorf("%w: detail", errkind.ErrX) でエラーの種類に詳細を付ける。
package errkind

import "errors"

var (
	// ErrInvalid は規則に反する入力を表す。
	// CLI は終了コード2で終了する。
	ErrInvalid = errors.New("invalid input")
	// ErrNotFound は指定した対象が存在しないことを表す。
	// CLI は終了コード3で終了する。
	ErrNotFound = errors.New("not found")
)
