package logger

import (
	"log/slog"
	"os"
)

// New は JSON 形式の構造化ロガーを返す。level は debug / info / warn / error。
func New(level string) *slog.Logger {
	var l slog.Level
	if err := l.UnmarshalText([]byte(level)); err != nil {
		l = slog.LevelInfo
	}

	return slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{Level: l}))
}
