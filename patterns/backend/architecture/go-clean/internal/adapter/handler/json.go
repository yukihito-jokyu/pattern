package handler

import (
	"encoding/json"
	"fmt"
	"net/http"

	"github.com/gin-gonic/gin"
)

const maxBodyBytes = 1 << 20

func decodeJSON(c *gin.Context, dst any) error {
	dec := json.NewDecoder(http.MaxBytesReader(c.Writer, c.Request.Body, maxBodyBytes))
	dec.DisallowUnknownFields()

	if err := dec.Decode(dst); err != nil {
		return fmt.Errorf("%w: %w", errInvalidJSON, err)
	}

	return nil
}
