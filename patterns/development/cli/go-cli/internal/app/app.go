// Package app は go-cli のコマンドツリーを構築し、プロセスの実行環境に接続する。
//
// 全パッケージを知る組み立て役として、設定の読み取り・adapter と Service の作成・全コマンド群の登録を行う。
package app

import (
	"context"
	"io"
	"path/filepath"
	"runtime/debug"
	"time"

	"example.com/go-cli/internal/adapter/taskstore"
	"example.com/go-cli/internal/cli"
	"example.com/go-cli/internal/command/taskcmd"
	"example.com/go-cli/internal/domain/task"
)

// Env は CLI の実行環境を保持する。
// main は実際の実行環境を渡し、テストはテスト用の実行環境を渡す。
type Env struct {
	Stdout io.Writer
	Stderr io.Writer
	Getenv func(key string) string
	Now    func() time.Time
}

// name は CLI の名前を表す。
const name = "go-cli"

// New はコマンドツリーを構築する。
// ファイルの読み書きは行わない。
func New(env Env) (*cli.App, error) {
	cfg, err := loadConfig(env.Getenv)
	if err != nil {
		return nil, err
	}
	tasks := task.NewService(taskstore.New(filepath.Join(cfg.dataDir, "tasks.json")), env.Now)
	return &cli.App{
		Name:    name,
		Version: version(),
		Groups: []*cli.Group{
			taskcmd.New(tasks),
		},
	}, nil
}

// Run はコマンドツリーを構築し、プログラム名を除いた args で実行して終了コードを返す。
func Run(ctx context.Context, args []string, env Env) int {
	streams := cli.IO{Out: env.Stdout, Err: env.Stderr}
	a, err := New(env)
	if err != nil {
		return cli.Fail(streams, name, err)
	}
	return a.Run(ctx, args, streams)
}

// version は go install が記録したモジュールの版を返し、ローカルのビルドでは (devel) を返す。
func version() string {
	info, ok := debug.ReadBuildInfo()
	if !ok || info.Main.Version == "" {
		return "(devel)"
	}
	return info.Main.Version
}
