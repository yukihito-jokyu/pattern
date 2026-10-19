package handler

import (
	"net/http"

	"github.com/gin-gonic/gin"
)

// NewRouter はルーティングとミドルウェアを組み立てた http.Handler を返す。
func NewRouter(users *UserHandler) http.Handler {
	gin.SetMode(gin.ReleaseMode) // 起動時のデバッグ出力を止める。ログは logRequest で slog に出す

	r := gin.New()
	r.HandleMethodNotAllowed = true
	r.Use(recoverPanic, logRequest)

	r.GET("/healthz", func(c *gin.Context) { c.Status(http.StatusOK) })

	r.POST("/users", users.Create)
	r.GET("/users/:id", users.Get)

	return r
}
