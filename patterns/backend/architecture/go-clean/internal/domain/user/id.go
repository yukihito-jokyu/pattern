package user

import "uuid"

// ID は UUID 形式のユーザー識別子。
type ID string

// NewID は新しい ID をランダムに生成する。
func NewID() ID {
	return ID(uuid.New().String())
}

// ParseID は文字列を検証して ID に変換する。大文字などの表記揺れは小文字のハイフン区切りにそろえる。
func ParseID(s string) (ID, error) {
	u, err := uuid.Parse(s)
	if err != nil {
		return "", ErrInvalidID
	}

	return ID(u.String()), nil
}

func (id ID) String() string { return string(id) }
