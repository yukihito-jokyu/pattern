package app

import (
	"errors"
	"path/filepath"
)

// config は環境変数から読み取った設定を保持する。
type config struct {
	dataDir string
}

// CLI の設定に使う環境変数を定義する。
const (
	envDataDir = "GOCLI_DATA_DIR"
	envXDGData = "XDG_DATA_HOME"
	envHome    = "HOME"
)

// errNoDataDir はデータディレクトリを決める環境変数が無いことを表す。
var errNoDataDir = errors.New("cannot find a data directory: set " + envDataDir + " or HOME")

// loadConfig は環境変数から設定を読み取る。
func loadConfig(getenv func(key string) string) (config, error) {
	dataDir, err := loadDataDir(getenv)
	if err != nil {
		return config{}, err
	}
	return config{dataDir: dataDir}, nil
}

// loadDataDir は $GOCLI_DATA_DIR、$XDG_DATA_HOME/go-cli、$HOME/.local/share/go-cli の順に最初に設定されたパスを返す。
func loadDataDir(getenv func(key string) string) (string, error) {
	dir := getenv(envDataDir)
	if dir != "" {
		return dir, nil
	}
	dir = getenv(envXDGData)
	if dir != "" {
		return filepath.Join(dir, name), nil
	}
	dir = getenv(envHome)
	if dir != "" {
		return filepath.Join(dir, ".local", "share", name), nil
	}
	return "", errNoDataDir
}
