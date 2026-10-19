package handler

import (
	"time"

	"example.com/go-clean/internal/usecase"
)

// HTTP の入出力形式。json タグはこの層にだけ書く。

type createUserRequest struct {
	Name  string `json:"name"`
	Email string `json:"email"`
}

type userResponse struct {
	ID        string    `json:"id"`
	Name      string    `json:"name"`
	Email     string    `json:"email"`
	CreatedAt time.Time `json:"created_at"`
}

func newUserResponse(out *usecase.UserOutput) userResponse {
	// 作成直後もDBからの取得後も、UTC・マイクロ秒精度で同じ日時を返す。
	return userResponse{
		ID:        out.ID,
		Name:      out.Name,
		Email:     out.Email,
		CreatedAt: out.CreatedAt.UTC().Truncate(time.Microsecond),
	}
}

type errorResponse struct {
	Error errorBody `json:"error"`
}

type errorBody struct {
	Code    string `json:"code"`
	Message string `json:"message"`
}
