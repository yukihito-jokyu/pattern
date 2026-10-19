package handler

import (
	"context"
	"net/http"

	"github.com/gin-gonic/gin"

	"example.com/go-clean/internal/usecase"
)

// userUsecase は handler が必要とするユーザーの振る舞い（使う側で定義する interface）。
type userUsecase interface {
	Create(ctx context.Context, in usecase.CreateUserInput) (*usecase.UserOutput, error)
	Get(ctx context.Context, in usecase.GetUserInput) (*usecase.UserOutput, error)
}

// UserHandler はユーザー API のハンドラ。
type UserHandler struct {
	users userUsecase
}

// NewUserHandler は UserHandler を生成する。
func NewUserHandler(users userUsecase) *UserHandler {
	return &UserHandler{users: users}
}

// Create は POST /users を処理する。
func (h *UserHandler) Create(c *gin.Context) {
	var req createUserRequest
	if err := decodeJSON(c, &req); err != nil {
		writeError(c, err)
		return
	}

	out, err := h.users.Create(c.Request.Context(), usecase.CreateUserInput{Name: req.Name, Email: req.Email})
	if err != nil {
		writeError(c, err)
		return
	}

	c.JSON(http.StatusCreated, newUserResponse(out))
}

// Get は GET /users/:id を処理する。
func (h *UserHandler) Get(c *gin.Context) {
	out, err := h.users.Get(c.Request.Context(), usecase.GetUserInput{ID: c.Param("id")})
	if err != nil {
		writeError(c, err)
		return
	}

	c.JSON(http.StatusOK, newUserResponse(out))
}
