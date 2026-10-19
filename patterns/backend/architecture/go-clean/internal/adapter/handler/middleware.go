package handler

import (
	"log/slog"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
)

func logRequest(c *gin.Context) {
	start := time.Now()

	c.Next()
	slog.InfoContext(
		c.Request.Context(),
		"request",
		"method",
		c.Request.Method,
		"path",
		c.Request.URL.Path,
		"status",
		c.Writer.Status(),
		"duration_ms",
		time.Since(start).Milliseconds(),
	)
}

func recoverPanic(c *gin.Context) {
	defer func() {
		if v := recover(); v != nil {
			slog.ErrorContext(
				c.Request.Context(),
				"panic recovered",
				"panic",
				v,
				"method",
				c.Request.Method,
				"path",
				c.Request.URL.Path,
			)
			c.AbortWithStatusJSON(http.StatusInternalServerError, errorResponse{
				Error: errorBody{Code: "internal", Message: "internal server error"},
			})
		}
	}()

	c.Next()
}
