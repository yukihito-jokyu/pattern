package config

import (
	"errors"
	"os"
)

// ErrMissingDatabaseURL は DATABASE_URL が未設定なことを表す。
var ErrMissingDatabaseURL = errors.New("config: DATABASE_URL is required")

// Config はアプリケーションの設定。
type Config struct {
	Addr        string
	DatabaseURL string
	LogLevel    string
}

// Load は環境変数から設定を読み込む。
func Load() (Config, error) {
	cfg := Config{
		Addr:        getenv("APP_ADDR", ":8080"),
		DatabaseURL: os.Getenv("DATABASE_URL"),
		LogLevel:    getenv("LOG_LEVEL", "info"),
	}
	if cfg.DatabaseURL == "" {
		return Config{}, ErrMissingDatabaseURL
	}

	return cfg, nil
}

func getenv(key, fallback string) string {
	if v, ok := os.LookupEnv(key); ok && v != "" {
		return v
	}

	return fallback
}
