package handler

import (
	"errors"
	"log/slog"
	"net/http"

	"github.com/gin-gonic/gin"

	"example.com/go-clean/internal/domain/user"
)

var errInvalidJSON = errors.New("invalid json body")

const codeInvalidArgument = "invalid_argument"

// errorMappings はエラーと HTTP ステータスの対応表。ドメインエラーを追加したらここにも追加する。
var errorMappings = []struct {
	target error
	status int
	code   string
}{
	{errInvalidJSON, http.StatusBadRequest, "invalid_request"},
	{user.ErrInvalidID, http.StatusBadRequest, codeInvalidArgument},
	{user.ErrInvalidName, http.StatusBadRequest, codeInvalidArgument},
	{user.ErrInvalidEmail, http.StatusBadRequest, codeInvalidArgument},
	{user.ErrNotFound, http.StatusNotFound, "not_found"},
	{user.ErrEmailAlreadyExists, http.StatusConflict, "already_exists"},
}

func writeError(c *gin.Context, err error) {
	for _, m := range errorMappings {
		if errors.Is(err, m.target) {
			c.JSON(m.status, errorResponse{Error: errorBody{Code: m.code, Message: m.target.Error()}})
			return
		}
	}

	slog.ErrorContext(
		c.Request.Context(),
		"unhandled error",
		"error",
		err,
		"method",
		c.Request.Method,
		"path",
		c.Request.URL.Path,
	)
	c.JSON(http.StatusInternalServerError, errorResponse{
		Error: errorBody{Code: "internal", Message: "internal server error"},
	})
}
